"""Church administration (6a spec, `usecases/church_admin.py`): the writes an
owner or admin makes to the church itself. Slice 6a-1 has the profile
(PATCH /church); 6a-2, 6a-3 and 6b add their writes here.

Every write opens one session, starts with
usecases.members.lock_and_read_actor (the church-row lock and the caller's
role re-read under it) and then require_admin_role on that re-read role, so
an admin demoted after require_admin ran gets the role 403 and nothing is
written. No FastAPI, Starlette or Streamlit here (usecases/__init__.py).
"""
import re
import uuid
from collections.abc import Collection, Mapping

import scripture_fetcher
from db import session_scope
from bulletin_settings import NOT_ONE_LINE
from domain_errors import Forbidden, InvalidInput
from repos import churches
from repos import hymns as hymn_repo
from tenancy import is_admin
from timezones import is_valid_timezone
from usecases.members import lock_and_read_actor

# require_admin's message (api/deps.py): one wording for the role 403.
ADMINS_ONLY_MESSAGE = "Only church admins can do this."

# The church's name prints on one line (the bulletin's header and title): no control character (NUL, which
# Postgres refuses in text, among them), no C1 control and no U+2028/U+2029, as the bulletin settings' lines.
_NOT_ONE_LINE = re.compile(f"[{NOT_ONE_LINE}]")


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
    separator (bulletin_settings.NOT_ONE_LINE: it prints on one line); the time zone must be exactly an IANA name
    (timezones.is_valid_timezone, as POST /churches and GET /church's
    timezone_valid); the translation must be one of `translations` (offered on
    this deployment now) and the hymnal one of `church_hymnals`; the
    Benediction's line ends become "\\n" and it is trimmed, and "" is kept (the
    church then has no default Benediction). Returns (columns, settings_patch).
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
        settings["default_hymnal"] = changes["default_hymnal"].strip()
        if settings["default_hymnal"] not in church_hymnals:
            raise InvalidInput("Choose one of your church's hymnals.", field="default_hymnal")
    if "default_benediction" in changes:
        text = changes["default_benediction"].replace("\r\n", "\n").replace("\r", "\n")
        settings["default_benediction"] = text.strip()
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
