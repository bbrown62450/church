"""Church administration (6a spec, `usecases/church_admin.py`): the writes an
owner or admin makes to the church itself. Slice 6a-1 has the profile
(PATCH /church); 6a-3a the liturgy prompts and the rubric (and their
reads); 6a-3b and 6b add their writes here (6b-1: transfer ownership,
leave and delete, which check usecases.role_policy instead of
require_admin_role).

Every write opens one session, starts with
usecases.members.lock_and_read_actor (the church-row lock and the caller's
role re-read under it) and then require_admin_role on that re-read role, so
an admin demoted after require_admin ran gets the role 403 and nothing is
written. No FastAPI, Starlette or Streamlit here (usecases/__init__.py).
"""
import logging
import re
import uuid
from collections.abc import Collection, Mapping

import liturgy_prompts
import scripture_fetcher
import service_rubric
from db import session_scope
from db.ids import as_uuid
from bulletin_settings import NOT_ONE_LINE
from domain_errors import Conflict, Forbidden, InvalidInput, NotFound
from liturgy_config import SECTION_LABELS
from repos import churches, memberships
from repos import hymns as hymn_repo
from repos.memberships import LastAdminError
from tenancy import is_admin
from timezones import is_valid_timezone
from usecases import archive, role_policy
from usecases.members import MEMBER_NOT_FOUND, lock_and_read_actor, member_out

logger = logging.getLogger(__name__)

# require_admin's message (api/deps.py): one wording for the role 403.
ADMINS_ONLY_MESSAGE = "Only church admins can do this."

# The church's name prints on one line (the bulletin's header and title): no control character (NUL, which
# Postgres refuses in text, among them), no C1 control and no U+2028/U+2029, as the bulletin settings' lines;
# and nothing a Word file cannot hold (U+FFFE, U+FFFF: archive._XML_BAD's noncharacters; lone surrogates never
# reach here, pydantic refuses them), so the stored name is the name that prints (6a-1 code review m3).
_NOT_ONE_LINE = re.compile(f"[{NOT_ONE_LINE}\ufffe\uffff]")


def require_admin_role(role: str) -> None:
    """Raise the role 403 (no details, so the client never treats it as a lost
    church) unless `role` is owner or admin."""
    if not is_admin(role):
        raise Forbidden(ADMINS_ONLY_MESSAGE)


def clean_profile_patch(changes: Mapping[str, str], *, translations: Collection[str],
                        church_hymnals: Collection[str]) -> tuple[dict[str, str], dict[str, str]]:
    """PATCH /church's provided fields, cleaned and checked (pure).

    `changes` holds only the fields sent (a null is not sent). The checks run
    in the order name, timezone, bible_translation, default_hymnal, and the
    first failure raises InvalidInput naming its field. The name and the time
    zone are trimmed; the name must hold no control character or line
    separator (bulletin_settings.NOT_ONE_LINE: it prints on one line) and no U+FFFE or U+FFFF (Word cannot hold
    them); the time zone must be exactly an IANA name
    (timezones.is_valid_timezone, as POST /churches and GET /church's
    timezone_valid); the translation must be one of `translations` (offered on
    this deployment now) and the hymnal one of `church_hymnals`, compared
    trimmed (a code stored with spaces around it can still be chosen; the
    church's own code is stored, so it resolves); the Benediction is made
    Word-safe as the bulletin settings' texts are (archive._xml_safe: its line
    ends become "\\n", a vertical tab or form feed a line break, and NUL, the
    other C0 controls, U+FFFE and U+FFFF go; 6a-1 code review m3) and
    trimmed, and "" is kept (the church then has no default Benediction).
    Returns (columns, settings_patch).
    """
    columns: dict[str, str] = {}
    settings: dict[str, str] = {}
    if "name" in changes:
        columns["name"] = changes["name"].strip()
        if not columns["name"]:
            raise InvalidInput("Church name is required.", field="name")
        if _NOT_ONE_LINE.search(columns["name"]):
            raise InvalidInput("Church name can't contain line breaks or control characters.", field="name")
    if "timezone" in changes:
        columns["timezone"] = changes["timezone"].strip()
        if not columns["timezone"]:
            raise InvalidInput("Timezone is required.", field="timezone")
        if not is_valid_timezone(columns["timezone"]):
            raise InvalidInput("Unknown timezone.", field="timezone")
    if "bible_translation" in changes:
        settings["bible_translation"] = changes["bible_translation"].strip()
        if settings["bible_translation"] not in translations:
            raise InvalidInput("Unknown or unavailable translation.", field="bible_translation")
    if "default_hymnal" in changes:
        wanted = changes["default_hymnal"].strip()
        matches = [code for code in church_hymnals if code.strip() == wanted] if wanted else []
        if not matches:
            raise InvalidInput("Choose one of your church's hymnals.", field="default_hymnal")
        settings["default_hymnal"] = wanted if wanted in matches else matches[0]
    if "default_benediction" in changes:
        settings["default_benediction"] = archive._xml_safe(changes["default_benediction"]).strip()
    return columns, settings


def update_profile(church_id: uuid.UUID, actor_id: uuid.UUID, changes: Mapping[str, str]) -> dict:
    """PATCH /church (6a spec, Semantics): write the provided fields, all or
    nothing, in one transaction under the church-row lock, with the caller's
    role re-read under it. Returns {"name", "role"}: the name as stored and
    the caller's re-read role (for the answer, which GET /church's profile
    completes)."""
    with session_scope() as s:
        role = lock_and_read_actor(s, church_id, actor_id)
        require_admin_role(role)
        hymnals = ([h.code for h in hymn_repo.hymnal_summaries(church_id, session=s)]
                   if "default_hymnal" in changes else [])
        offered = [tid for tid, _label in scripture_fetcher.available_translations()]
        columns, settings_patch = clean_profile_patch(changes, translations=offered, church_hymnals=hymnals)
        churches.update_profile(church_id, **columns, settings_patch=settings_patch, session=s)
        name = churches.get_church(church_id, session=s)["name"]
    return {"name": name, "role": role}


# --- Liturgy prompts: GET and PUT /church/liturgy-prompts (slice 6a-3a; 6a spec UX §3, Semantics) ----------

# The system prompt's name in a message ("Overall voice prompt: …"); the page titles its card
# "Overall voice (system prompt)".
SYSTEM_PROMPT_LABEL = "Overall voice"


def prompt_label(key: str) -> str:
    """A prompt's name: "Overall voice" for the system prompt, else the section's label."""
    return SYSTEM_PROMPT_LABEL if key == "system" else SECTION_LABELS[key]


def get_prompts(church_id: uuid.UUID, *, can_edit: bool) -> dict:
    """GET /church/liturgy-prompts: every prompt in PROMPT_KEYS order (the
    system prompt first, then the sections), each with its default and the
    church's own wording when it has one. What counts as the church's own is
    what clean_prompt_overrides keeps of the stored overrides, the rule a save
    and generation use, so a stored value equal to its default (or blank, or
    under an unknown key) reads as not customized."""
    overrides = liturgy_prompts.clean_prompt_overrides(churches.get_church_prompts(church_id))
    defaults = liturgy_prompts.default_prompts()
    return {
        "placeholder_help": liturgy_prompts.PLACEHOLDER_HELP,
        "can_edit": can_edit,
        "fields": [{"key": key, "label": prompt_label(key), "default": defaults[key],
                    "override": overrides.get(key), "customized": key in overrides}
                   for key in liturgy_prompts.PROMPT_KEYS],
    }


def save_prompts(church_id: uuid.UUID, actor_id: uuid.UUID, prompts: Mapping[str, str]) -> dict:
    """PUT /church/liturgy-prompts (6a spec, Semantics): replace the church's
    prompt overrides, under the church-row lock with the caller's role re-read
    (an admin demoted meanwhile gets the role 403). Cleaning is slice 4's
    liturgy_prompts.clean_prompt_overrides, the one rule (no copy here): CRLF
    read as LF, trimmed, and a blank value or one equal to its default is not
    kept; so {} resets every prompt. Each kept prompt, in PROMPT_KEYS order,
    must pass liturgy_prompts.check_template (the system prompt is sent as
    written, so only its length is checked); the first that fails is a 422
    prompt_invalid "<Label> prompt: <reason>" naming prompts.<key>, and nothing
    is written. Returns the prompts as get_prompts does."""
    with session_scope() as s:
        role = lock_and_read_actor(s, church_id, actor_id)
        require_admin_role(role)
        cleaned = liturgy_prompts.clean_prompt_overrides(prompts)
        for key in liturgy_prompts.PROMPT_KEYS:
            reason = liturgy_prompts.check_template(key, cleaned[key]).message if key in cleaned else None
            if reason is not None:
                raise InvalidInput(f"{prompt_label(key)} prompt: {reason}", code="prompt_invalid",
                                   field=f"prompts.{key}")
        churches.set_church_prompts(church_id, cleaned, session=s)
    return get_prompts(church_id, can_edit=True)


# --- The service rubric: GET and PATCH /rubric (slice 6a-3a; 6a spec UX §6, Semantics → PATCH /rubric) -------


def rubric_out(overrides: object) -> dict:
    """GET and PATCH /rubric's answer (PR #4's, plus 6a's additive `defaults`):
    the merged rubric, the dotted names of the church's valid overrides, and
    the full default rubric, so the page can offer "Reset to default" and send
    null for an item put back to its default."""
    return {"rubric": service_rubric.merge_rubric(overrides),
            "customized": service_rubric.customized_keys(overrides),
            "defaults": service_rubric.default_rubric()}


def get_rubric(church_id: uuid.UUID) -> dict:
    """GET /rubric (any member)."""
    return rubric_out(churches.get_church_rubric_overrides(church_id))


def update_rubric(church_id: uuid.UUID, actor_id: uuid.UUID, patch: object) -> dict:
    """PATCH /rubric (6a spec, Semantics): one session that takes the
    church-row lock and re-reads the caller's role (lock_and_read_actor, then
    require_admin_role), then repos.churches.update_church_rubric in that
    session: service_rubric.validate_patch (a ValueError is a 422
    invalid_rubric with its message and no field, PR #4's body, and nothing
    is written), the stored overrides read from the locked row (a non-dict as
    {}), apply_patch (null removes an override) and the write. Returns
    rubric_out of what is stored."""
    with session_scope() as s:
        role = lock_and_read_actor(s, church_id, actor_id)
        require_admin_role(role)
        try:
            churches.update_church_rubric(church_id, patch, session=s)
        except ValueError as exc:
            raise InvalidInput(str(exc), code="invalid_rubric") from None
        overrides = churches.get_church_rubric_overrides(church_id, session=s)
    return rubric_out(overrides)


# --- Ownership, leaving and deleting (slice 6b-1; 6b spec, "Transactions and locking") ---------------------

NAME_MISMATCH = "Church name did not match."


def transfer_ownership(church_id: uuid.UUID, actor_id: uuid.UUID, target_id) -> list[dict]:
    """POST /church/transfer-ownership: in one transaction under the
    church-row lock, with the caller's role re-read under it,
    role_policy.check_transfer (only the owner; not to oneself, a 422 naming
    user_id), then the target must be a member of this church (404), then
    repos.memberships.transfer_ownership demotes the caller to admin and then
    promotes the target to owner. Two transfers at once serialize on the lock:
    the second re-reads its role as admin and gets the owner-only 403.
    Returns the members as GET /members lists them, afterwards."""
    actor_id, target_id = as_uuid(actor_id), as_uuid(target_id)
    with session_scope() as s:
        role = lock_and_read_actor(s, church_id, actor_id)
        role_policy.check_transfer(actor_id=actor_id, actor_role=role, target_id=target_id)
        if memberships.get_member(church_id, target_id, session=s) is None:
            raise NotFound(MEMBER_NOT_FOUND)
        memberships.transfer_ownership(church_id, actor_id, target_id, session=s)
        rows = memberships.list_member_rows(church_id, session=s)
    logger.info("ownership_transferred church_id=%s from_user_id=%s to_user_id=%s", church_id, actor_id, target_id)
    return [member_out(row, actor_id) for row in rows]


def leave_church(church_id: uuid.UUID, actor_id: uuid.UUID) -> None:
    """POST /church/leave: under the church-row lock with the caller's role
    re-read, role_policy.check_leave with the church's owner and admin count
    (the owner must transfer first; the only admin of a church with no owner
    may not leave), then the membership goes, its services.created_by nulled.
    The invites the leaver made stay: they were sent to other people."""
    actor_id = as_uuid(actor_id)
    with session_scope() as s:
        role = lock_and_read_actor(s, church_id, actor_id)
        role_policy.check_leave(role=role, admin_count=memberships.count_owner_admins(church_id, session=s))
        try:
            memberships.remove_membership(actor_id, church_id, session=s)
        except LastAdminError as exc:   # check_leave refuses first; a backstop, never a 500
            raise Conflict(str(exc), code="last_admin") from None
    logger.info("church_left church_id=%s user_id=%s role=%s", church_id, actor_id, role)


def delete_church(church_id: uuid.UUID, actor_id: uuid.UUID, confirm_name: str) -> None:
    """DELETE /church: under the church-row lock with the caller's role
    re-read, only the owner (403), and `confirm_name` must equal the church's
    name, both trimmed, exactly, case included (a 422 naming confirm_name), then
    repos.churches.soft_delete_church in the same transaction: the church is
    soft-deleted and every unrevoked invite of it revoked. Nothing is
    hard-deleted."""
    actor_id = as_uuid(actor_id)
    with session_scope() as s:
        role = lock_and_read_actor(s, church_id, actor_id)
        if role != "owner":
            raise Forbidden(role_policy.OWNER_ONLY)
        if (confirm_name or "").strip() != (churches.get_church(church_id, session=s)["name"] or "").strip():
            raise InvalidInput(NAME_MISMATCH, field="confirm_name")
        churches.soft_delete_church(church_id, session=s)
    logger.info("church_deleted church_id=%s user_id=%s", church_id, actor_id)
