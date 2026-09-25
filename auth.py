"""Identity helpers shared by every front end.

upsert_from_claims turns a plain dict of identity claims (email, sub, name,
picture) into a persisted users row and returns its id. Users are keyed on the
normalized (lower-cased) email; google_sub is a stable secondary identifier.
Streamlit login helpers live in streamlit_auth.py.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select

from db import session_scope
from db.models import User


def _normalize_email(email: Optional[str]) -> str:
    return (email or "").strip().lower()


def upsert_from_claims(claims: dict) -> uuid.UUID:
    """Create or update the users row for a set of OIDC claims; return its id.

    Pure w.r.t. Streamlit: accepts a plain dict (email, sub, name, picture) so it
    is unit-testable with no running Streamlit session. Idempotent on the
    normalized email.
    """
    email = _normalize_email(claims.get("email"))
    if not email:
        raise ValueError("OIDC claims are missing an email address.")
    sub = (claims.get("sub") or "").strip() or None
    name = (claims.get("name") or "").strip() or None
    picture = (claims.get("picture") or "").strip() or None
    now = datetime.now(timezone.utc)

    with session_scope() as session:
        user = session.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()
        if user is None:
            user = User(
                email=email,
                google_sub=sub,
                name=name,
                picture=picture,
                last_login_at=now,
            )
            session.add(user)
            session.flush()          # populate python-side default id
        else:
            if sub:
                user.google_sub = sub
            if name:
                user.name = name
            if picture:
                user.picture = picture
            user.last_login_at = now
        return user.id               # captured before session_scope commits
