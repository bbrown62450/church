import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from db import session_scope
from db.models import User
from db.upsert import insert_ignore

# users.last_login_at means "last seen, to the hour": ensure_user rewrites it
# only when the stored value is older than this (F §2.4).
LAST_SEEN_RESOLUTION = timedelta(hours=1)

_users = User.__table__


@dataclass(frozen=True)
class UserRow:
    id: uuid.UUID
    email: str
    name: Optional[str]
    picture: Optional[str]
    last_login_at: Optional[datetime]


def _normalize_email(email) -> str:
    return (email or "").strip().lower()


def _clean(value: Optional[str]) -> Optional[str]:
    """Strip; an empty string becomes None."""
    return (value or "").strip() or None


def _as_utc(value: Optional[datetime]) -> Optional[datetime]:
    """SQLite returns naive datetimes; every stored value was written as UTC."""
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)


def ensure_user(
    email: str,
    name: Optional[str] = None,
    picture: Optional[str] = None,
    *,
    google_sub: Optional[str] = None,
    now: Optional[datetime] = None,
    session: Optional[Session] = None,
) -> UserRow:
    """Return the users row for `email`, creating it if needed (F §2.4).

    One transaction (the caller's `session`, or its own scope):
    1. INSERT ... ON CONFLICT (email) DO NOTHING, so concurrent first calls
       never raise IntegrityError. The INSERT carries no google_sub: the
       arbiter covers only the email, not users_google_sub_key;
    2. SELECT the row by email;
    3. one UPDATE, only when a truthy name, picture or google_sub differs from
       the stored value, or last_login_at is NULL or older than
       LAST_SEEN_RESOLUTION. Concurrent UPDATEs of the same row wait on its
       row lock instead of conflicting.
    A falsy value never blanks a stored one. Only Streamlit passes google_sub
    (the API never does, see api.security.claims_to_profile); a google_sub
    already used by another email still raises IntegrityError (from the
    UPDATE), and the transaction rolls back.
    """
    normalized = _normalize_email(email)
    if not normalized:
        raise ValueError("email is required")
    name, picture, google_sub = _clean(name), _clean(picture), _clean(google_sub)
    now = now or datetime.now(timezone.utc)
    if session is not None:
        return _ensure_user(session, normalized, name, picture, google_sub, now)
    with session_scope() as own:
        return _ensure_user(own, normalized, name, picture, google_sub, now)


def _ensure_user(session, email, name, picture, google_sub, now) -> UserRow:
    session.execute(
        insert_ignore(_users)
        .values(id=uuid.uuid4(), email=email, name=name, picture=picture,
                created_at=now, last_login_at=now)   # no google_sub: see step 3
        .on_conflict_do_nothing(index_elements=["email"])
    )
    row = session.execute(
        select(_users.c.id, _users.c.email, _users.c.name, _users.c.picture,
               _users.c.google_sub, _users.c.last_login_at)
        .where(_users.c.email == email)
    ).one()
    changes = {}
    if name and name != row.name:
        changes["name"] = name
    if picture and picture != row.picture:
        changes["picture"] = picture
    if google_sub and google_sub != row.google_sub:
        changes["google_sub"] = google_sub
    last_seen = _as_utc(row.last_login_at)
    if last_seen is None or last_seen < now - LAST_SEEN_RESOLUTION:
        changes["last_login_at"] = last_seen = now
    if changes:
        session.execute(update(_users).where(_users.c.id == row.id).values(**changes))
    return UserRow(
        id=row.id,
        email=row.email,
        name=changes.get("name", row.name),
        picture=changes.get("picture", row.picture),
        last_login_at=last_seen,
    )


def _to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "google_sub": user.google_sub,
        "name": user.name,
        "picture": user.picture,
    }


def upsert_user(email, name=None, picture=None, google_sub=None) -> uuid.UUID:
    """Create or refresh a user keyed on the normalized (lower-cased) email.

    Returns the user's id. Idempotent on email: a repeat call updates the
    name/picture/google_sub (when provided) and stamps last_login_at.
    """
    normalized = _normalize_email(email)
    if not normalized:
        raise ValueError("email is required")
    now = datetime.now(timezone.utc)
    with session_scope() as session:
        user = session.execute(
            select(User).where(User.email == normalized)
        ).scalar_one_or_none()
        if user is None:
            user = User(
                email=normalized,
                google_sub=google_sub,
                name=name,
                picture=picture,
                last_login_at=now,
            )
            session.add(user)
        else:
            if google_sub is not None:
                user.google_sub = google_sub
            if name is not None:
                user.name = name
            if picture is not None:
                user.picture = picture
            user.last_login_at = now
        session.flush()
        return user.id


def get_user(user_id) -> Optional[dict]:
    with session_scope() as session:
        user = session.get(User, user_id)
        return _to_dict(user) if user is not None else None


def get_user_by_email(email) -> Optional[dict]:
    normalized = _normalize_email(email)
    if not normalized:
        return None
    with session_scope() as session:
        user = session.execute(
            select(User).where(User.email == normalized)
        ).scalar_one_or_none()
        return _to_dict(user) if user is not None else None
