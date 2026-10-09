import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from db import session_scope
from db.ids import as_uuid
from db.models import Invite, User


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
    """Create an invite and return its code (insert_invite(...)["code"]).

    `reusable` lets several people join with the code until it expires or is
    revoked (slice 6b sets it); the default is single-use. Writes in the
    caller's `session` (flushed, not committed) or in its own scope.
    """
    fields = dict(church_id=church_id, created_by=created_by, role=role, email=email,
                  reusable=reusable, ttl_days=ttl_days)
    if session is not None:
        return insert_invite(**fields, session=session)["code"]
    with session_scope() as own:
        return insert_invite(**fields, session=own)["code"]


def insert_invite(*, church_id, created_by, role, email, reusable: bool, ttl_days=7,
                  now: Optional[datetime] = None, session: Session) -> dict:
    """Insert an invite in `session` (flushed, not committed) and return its
    row as a dict, created_at included. The code is >=128 bits of url-safe
    entropy (secrets.token_urlsafe(32) == 256 bits); the email is stored
    trimmed and lower-cased (None when blank); it expires `ttl_days` after
    `now`."""
    now = now if now is not None else datetime.now(timezone.utc)
    invite = Invite(
        church_id=as_uuid(church_id),
        code=secrets.token_urlsafe(32),
        email=_normalize_email(email),
        role=role,
        created_by=as_uuid(created_by) if created_by is not None else None,
        created_at=now,
        expires_at=now + timedelta(days=ttl_days),
        revoked=False,
        reusable=reusable,
    )
    session.add(invite)
    session.flush()
    return {**_to_dict(invite), "created_at": invite.created_at}


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
    """Stamp a live invite (unused, unrevoked, unexpired at `now`) as accepted
    by `user_id` at `now`; True when this call stamped it:

        UPDATE invites SET accepted_at = :now, accepted_by = :user_id
        WHERE id = :invite_id AND accepted_at IS NULL AND NOT revoked
          AND expires_at >= :now

    The portable race guard: on Postgres a concurrent claimer, or a removal
    or a delete revoking the invite (slice 6b-1), holds the row lock; this
    UPDATE waits, re-reads the row as committed and then matches zero rows;
    SQLite serializes writers.
    synchronize_session=False: the default would copy `user_id` into an Invite
    already loaded in `session` even when no row matched, so a caller that
    needs the stored values refreshes the row.
    """
    stmt = (
        update(Invite)
        .where(Invite.id == as_uuid(invite_id), Invite.accepted_at.is_(None), Invite.revoked.is_(False),
               Invite.expires_at >= as_utc(now))
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


def revoke_invite(invite_id, church_id, *, session: Optional[Session] = None) -> bool:
    """Revoke an invite, scoped to church_id so a caller can never revoke
    another church's invite by id (IDOR-safe). True when the church has the
    invite (revoked now or already); False for an unknown id or another
    church's. Ids go through as_uuid (a malformed id is NotFound). Runs in the
    caller's `session` or in its own scope."""
    iid, cid = as_uuid(invite_id), as_uuid(church_id)
    if session is not None:
        return _revoke_invite(session, iid, cid)
    with session_scope() as own:
        return _revoke_invite(own, iid, cid)


def _revoke_invite(session, invite_id, church_id) -> bool:
    inv = session.get(Invite, invite_id)
    if inv is None or inv.church_id != church_id:
        return False
    inv.revoked = True
    return True


# --- Slice 6b-1: the People routes' reads and revocations (6b spec, "Repo changes") ---

def _pending_email(church_id, email: str):
    """Pending invites of the church for `email` (lower-cased): email-bound,
    not revoked, not accepted (uq_invites_pending_email's rows)."""
    return (
        Invite.church_id == church_id,
        func.lower(Invite.email) == email.strip().lower(),
        Invite.revoked.is_(False),
        Invite.accepted_at.is_(None),
    )


def list_active_invites(church_id, *, now: datetime, session: Optional[Session] = None) -> list[dict]:
    """The church's live invites, newest first (created_at DESC, then id):
    not revoked, not expired at `now`, and not used unless reusable. Each is
    {id, code, email, role, reusable, created_at, expires_at, created_by},
    created_by being {user_id, name, email} of its creator, or None when the
    creator's account is gone."""
    cid = as_uuid(church_id)
    query = (
        select(Invite, User.id.label("creator_id"), User.name.label("creator_name"),
               User.email.label("creator_email"))
        .outerjoin(User, User.id == Invite.created_by)
        .where(
            Invite.church_id == cid,
            Invite.revoked.is_(False),
            Invite.expires_at > as_utc(now),
            or_(Invite.accepted_at.is_(None), Invite.reusable.is_(True)),
        )
        .order_by(Invite.created_at.desc(), Invite.id)
    )
    if session is not None:
        return _active_rows(session, query)
    with session_scope() as own:
        return _active_rows(own, query)


def _active_rows(session, query) -> list[dict]:
    return [
        {
            "id": row.Invite.id,
            "code": row.Invite.code,
            "email": row.Invite.email,
            "role": row.Invite.role,
            "reusable": row.Invite.reusable,
            "created_at": as_utc(row.Invite.created_at),
            "expires_at": as_utc(row.Invite.expires_at),
            "created_by": ({"user_id": row.creator_id, "name": row.creator_name, "email": row.creator_email}
                           if row.creator_id is not None else None),
        }
        for row in session.execute(query)
    ]


def find_pending_email_invite(church_id, email: str, *, now: datetime, session: Session) -> Optional[dict]:
    """The church's unexpired pending invite for `email`, or None."""
    inv = session.execute(
        select(Invite).where(*_pending_email(as_uuid(church_id), email), Invite.expires_at > as_utc(now))
    ).scalars().first()
    return _to_dict(inv) if inv is not None else None


def revoke_expired_email_invites(church_id, email: str, *, now: datetime, session: Session) -> int:
    """Revoke the church's pending invites for `email` that expired at or
    before `now` (expiry cannot sit in the unique index's predicate); returns
    how many."""
    return session.execute(
        update(Invite)
        .where(*_pending_email(as_uuid(church_id), email), Invite.expires_at <= as_utc(now))
        .values(revoked=True)
        .execution_options(synchronize_session=False)
    ).rowcount


def revoke_invites_created_by(church_id, user_id, *, session: Session) -> int:
    """Revoke every unrevoked invite of the church that `user_id` created
    (single-use or reusable, email-bound or not, any role); returns how many."""
    return session.execute(
        update(Invite)
        .where(Invite.church_id == as_uuid(church_id), Invite.created_by == as_uuid(user_id),
               Invite.revoked.is_(False))
        .values(revoked=True)
        .execution_options(synchronize_session=False)
    ).rowcount


def revoke_pending_email_invites(church_id, email: str, *, session: Session) -> int:
    """Revoke every pending invite of the church for `email` (compared
    lower-cased), whoever made it and expired or not; returns how many. A
    removal runs it for the removed person's email, so a link another admin
    made for them stops working too."""
    return session.execute(
        update(Invite)
        .where(*_pending_email(as_uuid(church_id), email))
        .values(revoked=True)
        .execution_options(synchronize_session=False)
    ).rowcount


def revoke_reusable_invites(church_id, *, session: Session) -> int:
    """Revoke every unrevoked reusable invite of the church; returns how many."""
    return session.execute(
        update(Invite)
        .where(Invite.church_id == as_uuid(church_id), Invite.reusable.is_(True), Invite.revoked.is_(False))
        .values(revoked=True)
        .execution_options(synchronize_session=False)
    ).rowcount
