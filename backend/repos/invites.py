import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from db import session_scope
from db.ids import as_uuid
from db.models import Invite


def _normalize_email(email) -> Optional[str]:
    if email is None:
        return None
    normalized = email.strip().lower()
    return normalized or None


def as_utc(value: datetime) -> datetime:
    """Normalize a stored timestamp to aware-UTC. SQLite returns naive
    datetimes; Postgres returns aware ones. Assume naive == UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


_as_utc = as_utc  # the private name stays for existing callers


def _to_dict(inv: Invite) -> dict:
    return {
        "id": inv.id,
        "church_id": inv.church_id,
        "code": inv.code,
        "email": inv.email,
        "role": inv.role,
        "created_by": inv.created_by,
        "expires_at": inv.expires_at,
        "revoked": inv.revoked,
        "accepted_at": inv.accepted_at,
        "reusable": inv.reusable,
        "accepted_by": inv.accepted_by,
    }


def create_invite(
    *,
    church_id,
    created_by,
    role="member",
    email=None,
    ttl_days=7,
    reusable: bool = False,
    session: Optional[Session] = None,
) -> str:
    """Create an invite and return its code. Code is >=128 bits of url-safe
    entropy (secrets.token_urlsafe(32) == 256 bits).

    `reusable` lets several people join with the code until it expires or is
    revoked (slice 6b sets it); the default is single-use. Writes in the
    caller's `session` (flushed, not committed) or in its own scope.
    """
    code = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    invite = Invite(
        church_id=church_id,
        code=code,
        email=_normalize_email(email),
        role=role,
        created_by=created_by,
        expires_at=now + timedelta(days=ttl_days),
        revoked=False,
        reusable=reusable,
    )
    if session is not None:
        session.add(invite)
        session.flush()
        return code
    with session_scope() as own:
        own.add(invite)
    return code


def get_invite_by_code(code) -> Optional[dict]:
    with session_scope() as session:
        inv = session.execute(
            select(Invite).where(Invite.code == code)
        ).scalar_one_or_none()
        return _to_dict(inv) if inv is not None else None


def find_by_code(code: str, *, session: Optional[Session] = None) -> Optional[Invite]:
    """The Invite row for `code` (the caller strips it), or None. A global
    lookup by secret: only usecases.onboarding calls it, never a route. Without
    `session` the row comes back detached, its columns loaded."""
    if session is not None:
        return _find_by_code(session, code)
    with session_scope() as own:
        return _find_by_code(own, code)


def _find_by_code(session, code) -> Optional[Invite]:
    return session.execute(
        select(Invite).where(Invite.code == code)
    ).scalar_one_or_none()


def claim(invite_id, user_id, now: datetime, *, session: Optional[Session] = None) -> bool:
    """Stamp an unaccepted invite as accepted by `user_id` at `now`; True when
    this call stamped it:

        UPDATE invites SET accepted_at = :now, accepted_by = :user_id
        WHERE id = :invite_id AND accepted_at IS NULL

    The portable race guard: on Postgres a concurrent claimer waits on the row
    lock and then matches zero rows; SQLite serializes writers.
    synchronize_session=False: the default would copy `user_id` into an Invite
    already loaded in `session` even when no row matched, so a caller that
    needs the stored values refreshes the row.
    """
    stmt = (
        update(Invite)
        .where(Invite.id == as_uuid(invite_id), Invite.accepted_at.is_(None))
        .values(accepted_at=now, accepted_by=as_uuid(user_id))
        .execution_options(synchronize_session=False)
    )
    if session is not None:
        return session.execute(stmt).rowcount == 1
    with session_scope() as own:
        return own.execute(stmt).rowcount == 1


def list_invites(church_id) -> list:
    """Active (pending) invites for a church: not revoked, not accepted, not
    expired. Newest first."""
    now = datetime.now(timezone.utc)
    with session_scope() as session:
        rows = session.execute(
            select(Invite)
            .where(Invite.church_id == church_id, Invite.revoked.is_(False))
            .order_by(Invite.created_at.desc())
        ).scalars().all()
        result = []
        for inv in rows:
            if inv.accepted_at is not None:
                continue
            if inv.expires_at is not None and _as_utc(inv.expires_at) < now:
                continue
            result.append({
                "id": inv.id,
                "code": inv.code,
                "email": inv.email,
                "role": inv.role,
                "created_by": inv.created_by,
                "expires_at": inv.expires_at,
            })
        return result


def revoke_invite(invite_id, church_id) -> None:
    """Revoke an invite, scoped to church_id so a caller can never revoke
    another church's invite by id (IDOR-safe)."""
    with session_scope() as session:
        inv = session.get(Invite, invite_id)
        if inv is None or inv.church_id != church_id:
            return
        inv.revoked = True
