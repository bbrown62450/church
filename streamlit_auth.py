"""Streamlit login shell around auth.upsert_from_claims (st.user / st.login).

Removed in the final migration slice together with the Streamlit app.
"""
import uuid
from typing import Optional

import streamlit as st
from sqlalchemy import select

from auth import _normalize_email, upsert_from_claims
from db import session_scope
from db.models import User


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
    from streamlit_tenancy import clear_all_church_state

    clear_all_church_state()
    st.logout()
