"""Identity/auth helpers built on Streamlit's native OIDC (st.user / st.login).

The Streamlit surface (require_login / current_user_id / do_logout) is a thin
shell around one pure, unit-tested function: upsert_from_claims, which turns a
plain dict of OIDC claims into a persisted users row and returns its id. Users
are keyed on the normalized (lower-cased) email; google_sub is a stable
secondary identifier.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

import streamlit as st
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


def require_login() -> dict:
    """Ensure a signed-in Streamlit user; render a gate and stop otherwise.

    On success upserts the users row and returns
    {"user_id": UUID, "email": str, "name": str, "picture": str}.
    """
    if not getattr(st.user, "is_logged_in", False):
        st.title("Worship Service Builder")
        st.write("Please sign in with Google to continue.")
        st.button("Sign in with Google", on_click=st.login)
        st.stop()

    user_id = upsert_from_claims(
        {
            "email": st.user.email,
            "sub": getattr(st.user, "sub", None),
            "name": getattr(st.user, "name", None),
            "picture": getattr(st.user, "picture", None),
        }
    )
    return {
        "user_id": user_id,
        "email": _normalize_email(st.user.email),
        "name": getattr(st.user, "name", None),
        "picture": getattr(st.user, "picture", None),
    }


def current_user_id() -> Optional[uuid.UUID]:
    """The signed-in user's id via a read-only lookup, or None if not logged in."""
    if not getattr(st.user, "is_logged_in", False):
        return None
    email = _normalize_email(st.user.email)
    if not email:
        return None
    with session_scope() as session:
        user = session.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()
        return user.id if user else None


def do_logout() -> None:
    """Clear church-scoped session state, then the app's local identity cookie.

    Clearing church state first matters on a shared browser: the next user must
    not inherit the previous user's active church / cached hymnal.
    """
    from tenancy import clear_all_church_state

    clear_all_church_state()
    st.logout()
