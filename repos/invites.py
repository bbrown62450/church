import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

from sqlalchemy import select

from db import session_scope
from db.models import Invite, Church, Membership, User


def _normalize_email(email) -> Optional[str]:
    if email is None:
        return None
    normalized = email.strip().lower()
    return normalized or None


def _as_utc(value: datetime) -> datetime:
    """Normalize a stored timestamp to aware-UTC. SQLite returns naive
    datetimes; Postgres returns aware ones. Assume naive == UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


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
    }


def create_invite(*, church_id, created_by, role="member", email=None, ttl_days=7) -> str:
    """Create an invite and return its code. Code is >=128 bits of url-safe
    entropy (secrets.token_urlsafe(32) == 256 bits)."""
    code = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    with session_scope() as session:
        session.add(Invite(
            church_id=church_id,
            code=code,
            email=_normalize_email(email),
            role=role,
            created_by=created_by,
            expires_at=now + timedelta(days=ttl_days),
            revoked=False,
        ))
        return code


def get_invite_by_code(code) -> Optional[dict]:
    with session_scope() as session:
        inv = session.execute(
            select(Invite).where(Invite.code == code)
        ).scalar_one_or_none()
        return _to_dict(inv) if inv is not None else None


def accept_invite(code, user_id) -> Tuple[bool, str]:
    """Accept an invite for user_id. Returns (ok, message). No enumerable
    difference between distinct failure causes beyond the message text.

    Rejects: unknown/revoked/expired codes; a soft-deleted church; email-bound
    codes whose email does not match the accepting user, or that were already
    used (single-use). Accepting when already a member is a no-op success.
    """
    now = datetime.now(timezone.utc)
    with session_scope() as session:
        inv = session.execute(
            select(Invite).where(Invite.code == code)
        ).scalar_one_or_none()
        if inv is None:
            return (False, "Invalid invite code.")
        if inv.revoked:
            return (False, "This invite has been revoked.")
        if inv.expires_at is not None and _as_utc(inv.expires_at) < now:
            return (False, "This invite has expired.")

        email_bound = inv.email is not None
        if email_bound and inv.accepted_at is not None:
            return (False, "This invite has already been used.")

        church = session.get(Church, inv.church_id)
        if church is None or church.deleted_at is not None:
            return (False, "This church is no longer available.")

        if email_bound:
            user = session.get(User, user_id)
            user_email = user.email if user is not None else None
            if user_email is None or user_email.strip().lower() != inv.email:
                return (False, "This invite was issued for a different email address.")

        existing = session.get(
            Membership, {"church_id": inv.church_id, "user_id": user_id}
        )
        if existing is None:
            session.add(Membership(
                church_id=inv.church_id, user_id=user_id, role=inv.role
            ))
        if email_bound:
            inv.accepted_at = now  # single-use for email-bound invites
        return (True, f"Joined {church.name}.")


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
