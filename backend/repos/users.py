import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select

from db import session_scope
from db.models import User


def _normalize_email(email) -> str:
    return (email or "").strip().lower()


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
