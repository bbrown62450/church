"""The church's members and invites (6b spec, `usecases/members.py`). Slice
6a-1 created the module with the helper every church write shares (6a and 6b
specs, "Assumed interfaces"); slice 6b-1 adds the member and invite
functions of GET /members, PATCH and DELETE /members/{user_id}, and GET,
POST and DELETE /invites.

lock_and_read_actor runs inside the write's own session: it locks the church
row (repos.churches.lock_church, SELECT ... FOR UPDATE) and re-reads the
caller's membership under that lock, so the role a write acts on is the one
stored now, never the snapshot require_church or require_admin read in an
earlier transaction. Every write here opens one session, starts with it,
then checks the role (church_admin.require_admin_role, or usecases.role_policy
after the target is looked up: a missing target is a 404), then writes.
Repos are called through their modules, so tests can patch one function.
Log lines carry ids, roles and counts only: never an email, a name or an
invite code. No FastAPI, Starlette or Streamlit here (usecases/__init__.py).
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db import session_scope
from db.ids import as_uuid
from domain_errors import Conflict, Forbidden, InvalidInput, NotFound
from email_addresses import InvalidAddress, normalize_address
from repos import churches, invites, memberships
from repos.memberships import LastAdminError
from usecases import role_policy

logger = logging.getLogger(__name__)

# require_church's own 403 (api/deps.py): a church soft-deleted, or a
# membership removed, after the guard ran looks exactly like no access.
NO_ACCESS_MESSAGE = "You don't have access to this church."


def lock_and_read_actor(s: Session, church_id: uuid.UUID, actor_id: uuid.UUID) -> str:
    """Lock the church row in `s` and return the caller's role read under the
    lock ("owner", "admin" or "member"). Raises Forbidden (403, details.reason
    no_church_access) when the church is missing or soft-deleted, or the
    caller is no longer a member."""
    if churches.lock_church(s, church_id) is None:
        raise Forbidden(NO_ACCESS_MESSAGE, details={"reason": "no_church_access"})
    role = memberships.get_role(actor_id, church_id, session=s)
    if role is None:
        raise Forbidden(NO_ACCESS_MESSAGE, details={"reason": "no_church_access"})
    return role


# --- Slice 6b-1: members (GET /members, PATCH and DELETE /members/{user_id}) ---

MEMBER_NOT_FOUND = "Member not found."


def member_out(row: dict, actor_id: uuid.UUID) -> dict:
    """A member as the API returns it: a blank name is None, and is_me."""
    name = row["name"] if row["name"] is not None and row["name"].strip() else None
    return {"user_id": row["user_id"], "email": row["email"], "name": name, "role": row["role"],
            "is_me": row["user_id"] == actor_id}


def list_members(church_id: uuid.UUID, actor_id: uuid.UUID) -> list[dict]:
    """GET /members (every member, with emails; decision 5): the owner, then
    admins, then members, each by name (the email when the name is blank)."""
    actor_id = as_uuid(actor_id)
    return [member_out(row, actor_id) for row in memberships.list_member_rows(church_id)]


def _require_admin(role: str) -> None:
    # church_admin imports this module (lock_and_read_actor), so it is imported here, when called.
    from usecases.church_admin import require_admin_role
    require_admin_role(role)


def _target(s: Session, church_id: uuid.UUID, target_id) -> dict:
    target = memberships.get_member(church_id, target_id, session=s)
    if target is None:
        raise NotFound(MEMBER_NOT_FOUND)
    return target


def change_role(church_id: uuid.UUID, actor_id: uuid.UUID, target_id, new_role: str) -> dict:
    """PATCH /members/{user_id}: under the church-row lock with the caller's
    role re-read, the role 403, then the target (404 when not a member of this
    church), then role_policy.check_role_change (self, the owner); a role the
    target already has writes nothing. Returns the target as GET /members
    shows it. repos.memberships' LastAdminError cannot fire here (the actor and
    an admin target are two owners or admins); if it does, it is a 409
    last_admin with the repo's words, never a 500."""
    actor_id, target_id = as_uuid(actor_id), as_uuid(target_id)
    with session_scope() as s:
        role = lock_and_read_actor(s, church_id, actor_id)
        _require_admin(role)
        target = _target(s, church_id, target_id)
        outcome = role_policy.check_role_change(actor_id=actor_id, actor_role=role, target_id=target_id,
                                                target_role=target["role"], new_role=new_role)
        if outcome == "change":
            try:
                memberships.set_role(target_id, church_id, new_role, session=s)
            except LastAdminError as exc:
                raise Conflict(str(exc), code="last_admin") from None
            logger.info("member_role_changed church_id=%s actor_id=%s target_id=%s old_role=%s new_role=%s",
                        church_id, actor_id, target_id, target["role"], new_role)
            target = {**target, "role": new_role}
    return member_out(target, actor_id)


def remove_member(church_id: uuid.UUID, actor_id: uuid.UUID, target_id, *, revoke_reusable: bool = False) -> int:
    """DELETE /members/{user_id}: under the church-row lock with the caller's
    role re-read, the role 403, the target (404), role_policy.check_remove
    (self, the owner), then in the same transaction: the membership goes (its
    services.created_by is nulled), every unrevoked invite of this church the
    removed person created is revoked, so is every pending invite of this
    church for the removed person's email (whoever made it), and with
    `revoke_reusable` every unrevoked reusable invite of the church too.
    Returns how many invites were revoked (each once)."""
    actor_id, target_id = as_uuid(actor_id), as_uuid(target_id)
    with session_scope() as s:
        role = lock_and_read_actor(s, church_id, actor_id)
        _require_admin(role)
        target = _target(s, church_id, target_id)
        role_policy.check_remove(actor_id=actor_id, actor_role=role, target_id=target_id,
                                 target_role=target["role"])
        try:
            memberships.remove_membership(target_id, church_id, session=s)
        except LastAdminError as exc:
            raise Conflict(str(exc), code="last_admin") from None
        revoked = invites.revoke_invites_created_by(church_id, target_id, session=s)
        revoked += invites.revoke_pending_email_invites(church_id, target["email"], session=s)
        if revoke_reusable:
            revoked += invites.revoke_reusable_invites(church_id, session=s)
    logger.info("member_removed church_id=%s actor_id=%s target_id=%s revoked_invites=%d",
                church_id, actor_id, target_id, revoked)
    return revoked


# --- Slice 6b-1: invites (GET, POST and DELETE /invites) ---

EMAIL_INVALID = "Enter a valid email address."
REUSABLE_WITH_EMAIL = "A link for one email address works once."
ROLE_INVALID = "Not a valid value."
ALREADY_MEMBER = "{email} is already a member of this church."
INVITE_EXISTS = "There's already a pending invite for {email}. Copy its link below or revoke it first."
INVITE_NOT_FOUND = "Invite not found."
ASSIGNABLE_ROLES = ("member", "admin")
PENDING_EMAIL_INDEX = "uq_invites_pending_email"   # the only IntegrityError create_invite answers as a 409
INVITE_TTL_DAYS = 7


def clean_invite_email(value: Optional[str]) -> Optional[str]:
    """An invite's email as stored: None when missing or blank, else
    email_addresses.normalize_address (the app's one address rule) and fully
    lower-cased (accept compares it with the caller's lower-cased email).
    An address the rule refuses is a 422 naming `email`."""
    if value is None or not value.strip():
        return None
    try:
        return normalize_address(value).lower()
    except InvalidAddress:
        raise InvalidInput(EMAIL_INVALID, field="email") from None


def _creator(row: Optional[dict]) -> Optional[dict]:
    if row is None:
        return None
    name = row["name"] if row["name"] is not None and row["name"].strip() else None
    return {"user_id": row["user_id"], "name": name, "email": row["email"]}


def _invite_out(row: dict, creator: Optional[dict]) -> dict:
    return {"id": row["id"], "code": row["code"], "email": row["email"], "role": row["role"],
            "reusable": row["reusable"], "created_at": invites.as_utc(row["created_at"]),
            "expires_at": invites.as_utc(row["expires_at"]), "created_by": _creator(creator)}


def list_invites(church_id: uuid.UUID, *, now: Optional[datetime] = None) -> list[dict]:
    """GET /invites (owners and admins): the live invites, newest first (not
    revoked, not expired, and unused unless reusable), each with its creator
    (None when the creator's account is gone)."""
    now = now if now is not None else datetime.now(timezone.utc)
    return [_invite_out(row, row["created_by"]) for row in invites.list_active_invites(church_id, now=now)]


def create_invite(church_id: uuid.UUID, actor_id: uuid.UUID, *, role: str = "member", email: Optional[str] = None,
                  reusable: bool = False, now: Optional[datetime] = None) -> dict:
    """POST /invites: under the church-row lock with the caller's role
    re-read, the role 403, then the body's checks in order (the role; the
    email, clean_invite_email; reusable with an email is a 422 naming
    `reusable`: an email-bound link works once), then for an email: a member
    of this church with it is a 409 conflict; its pending invites that have
    expired are revoked; a live pending one is a 409 invite_exists; and a
    unique-index race (an IntegrityError naming uq_invites_pending_email) is
    the same 409, while any other IntegrityError is raised as it is. Expires 7
    days from `now`. Returns the invite as GET /invites lists it. Logs the
    ids, the role and whether it is reusable or email-bound; never the code
    or the email."""
    actor_id = as_uuid(actor_id)
    now = now if now is not None else datetime.now(timezone.utc)
    with session_scope() as s:
        actor_role = lock_and_read_actor(s, church_id, actor_id)
        _require_admin(actor_role)
        if role not in ASSIGNABLE_ROLES:
            raise InvalidInput(ROLE_INVALID, field="role")
        email = clean_invite_email(email)
        if email is not None and reusable:
            raise InvalidInput(REUSABLE_WITH_EMAIL, field="reusable")
        if email is not None:
            if memberships.is_member_email(church_id, email, session=s):
                raise Conflict(ALREADY_MEMBER.format(email=email))
            invites.revoke_expired_email_invites(church_id, email, now=now, session=s)
            if invites.find_pending_email_invite(church_id, email, now=now, session=s) is not None:
                raise Conflict(INVITE_EXISTS.format(email=email), code="invite_exists")
        try:
            with s.begin_nested():
                row = invites.insert_invite(church_id=church_id, created_by=actor_id, role=role, email=email,
                                            reusable=reusable, ttl_days=INVITE_TTL_DAYS, now=now, session=s)
        except IntegrityError as exc:
            if PENDING_EMAIL_INDEX not in str(exc.orig):
                raise
            raise Conflict(INVITE_EXISTS.format(email=email), code="invite_exists") from None
        creator = memberships.get_member(church_id, actor_id, session=s)
    logger.info("invite_created church_id=%s invite_id=%s role=%s reusable=%s email_bound=%s",
                church_id, row["id"], role, reusable, email is not None)
    return _invite_out(row, creator)


def revoke_invite(church_id: uuid.UUID, actor_id: uuid.UUID, invite_id) -> None:
    """DELETE /invites/{invite_id}: under the church-row lock with the
    caller's role re-read, the role 403, then the invite is revoked when this
    church has it (already revoked, used or expired: still 200); another
    church's id, or an unknown or malformed one, is a 404."""
    actor_id = as_uuid(actor_id)
    with session_scope() as s:
        role = lock_and_read_actor(s, church_id, actor_id)
        _require_admin(role)
        if not invites.revoke_invite(invite_id, church_id, session=s):
            raise NotFound(INVITE_NOT_FOUND)
    logger.info("invite_revoked church_id=%s invite_id=%s actor_id=%s", church_id, invite_id, actor_id)
