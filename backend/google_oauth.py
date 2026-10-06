"""Google OAuth 2.0 for per-user Gmail sending (slice 5b spec, "google_oauth.py
after the refactor"; slice 5b-2).

Each user connects their own Google account and grants the `gmail.send` scope,
so the bulletin is emailed from their own mailbox. The refresh token is kept in
`gmail_tokens`, one row per user (user-scoped: one connection works in every
church the user belongs to). Google sends the user back to the frontend page
`/gmail/callback`, which posts the code and the state to `POST
/gmail-connection` (usecases.email).

This module holds:
- GoogleOAuthConfig: the client id, secret and redirect URI (from Railway's
  GOOGLE_* variables, read by api.settings, never by this module);
- the single-use CSRF states (`oauth_states`, 10 minutes) and the token store;
- build_auth_url, and (Task 3) the Google calls: the code exchange, the token
  refresh, the Gmail send and the revoke, each through integrations.http with
  its own timeout, each failure a GoogleOAuthError of one kind.

The Streamlit app's functions (the root-URL callback check, send_email, the
old exchange that stored the token itself, disconnect, is_configured) are
gone: production Streamlit is retired and nothing on `main` runs it (5b
amendment 2026-10-06, answer 4). Nothing here logs a code, a state, a token
or an address. No FastAPI, Starlette or Streamlit.
"""
from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

from sqlalchemy import delete
from sqlalchemy.orm import Session

from db import session_scope
from db.models import GmailToken, OAuthState

# openid and userinfo.email identify the Google account (the callback checks it is
# the signed-in user's); gmail.send lets the app send mail as them, nothing more.
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/gmail.send",
]
GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"

AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"
USERINFO_URI = "https://www.googleapis.com/oauth2/v2/userinfo"
GMAIL_SEND_URI = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
REVOKE_URI = "https://oauth2.googleapis.com/revoke"

# A single-use CSRF state lives this long.
STATE_TTL = timedelta(minutes=10)


@dataclass(frozen=True)
class GoogleOAuthConfig:
    """The Google OAuth client (the one Streamlit used: same id and secret, so a
    stored refresh token keeps working) and this deployment's redirect URI."""

    client_id: str
    client_secret: str
    redirect_uri: str

    @property
    def configured(self) -> bool:
        """All three are set."""
        return bool(self.client_id and self.client_secret and self.redirect_uri)


@dataclass(frozen=True)
class GmailConnection:
    """A user's stored connection: the Google address mail is sent from, and the refresh token."""

    google_email: str
    refresh_token: str


# --------------------------------------------------------------------------- #
# The consent URL and the CSRF states
# --------------------------------------------------------------------------- #
def build_auth_url(config: GoogleOAuthConfig, state: str, *, login_hint: Optional[str] = None) -> str:
    """Google's consent screen for this app's scopes, returning to the
    configured redirect URI with `state`. Offline access and a consent prompt,
    so Google returns a refresh token; `login_hint` pre-selects the signed-in
    Google account."""
    params = {
        "client_id": config.client_id,
        "redirect_uri": config.redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    if login_hint:
        params["login_hint"] = login_hint
    return f"{AUTH_URI}?{urlencode(params)}"


def purge_expired_states(session: Session) -> int:
    """Delete every expired state (abandoned connects); returns how many."""
    result = session.execute(delete(OAuthState).where(OAuthState.expires_at < datetime.now(timezone.utc)))
    return result.rowcount or 0


def create_state(user_id: uuid.UUID, *, session: Optional[Session] = None) -> str:
    """A new single-use state bound to the user (10 minutes); expired states
    are purged first. Returns the opaque token."""
    if session is None:
        with session_scope() as own:
            return create_state(user_id, session=own)
    purge_expired_states(session)
    state = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    session.add(OAuthState(state=state, user_id=user_id, created_at=now, expires_at=now + STATE_TTL))
    session.flush()
    return state


def consume_state(state: str) -> Optional[uuid.UUID]:
    """The user the state was issued to, or None for a blank, unknown, used or
    expired state. Single use: a found row is deleted, valid or expired. Runs
    in its own committed transaction."""
    if not state:
        return None
    with session_scope() as session:
        row = session.get(OAuthState, state)
        if row is None:
            return None
        user_id = row.user_id
        expires_at = row.expires_at
        session.delete(row)
    if expires_at.tzinfo is None:            # SQLite hands back naive datetimes
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None
    return user_id


# --------------------------------------------------------------------------- #
# The token store (gmail_tokens, one row per user)
# --------------------------------------------------------------------------- #
def get_connection(user_id: uuid.UUID, *, session: Optional[Session] = None) -> Optional[GmailConnection]:
    """The user's connection, or None when there is no row or its address is
    NULL or blank (the column is nullable; without an address nothing can be sent)."""
    if session is None:
        with session_scope() as own:
            return get_connection(user_id, session=own)
    row = session.get(GmailToken, user_id)
    if row is None or not row.refresh_token or not (row.google_email or "").strip():
        return None
    return GmailConnection(google_email=row.google_email, refresh_token=row.refresh_token)


def save_user_token(user_id: uuid.UUID, google_email: str, refresh_token: str, *,
                    session: Optional[Session] = None) -> None:
    """Store (or replace) the user's connection: one row per user."""
    if session is None:
        with session_scope() as own:
            return save_user_token(user_id, google_email, refresh_token, session=own)
    row = session.get(GmailToken, user_id)
    if row is None:
        session.add(GmailToken(user_id=user_id, google_email=google_email, refresh_token=refresh_token))
    else:
        row.google_email = google_email
        row.refresh_token = refresh_token
    session.flush()


def delete_connection(user_id: uuid.UUID, *, only_if_token: Optional[str] = None,
                      session: Optional[Session] = None) -> Optional[str]:
    """Delete the user's connection and return its refresh token, or None when
    no row matched. With `only_if_token`, only a row still holding that token is
    deleted: a connection made again since the token failed is kept."""
    if session is None:
        with session_scope() as own:
            return delete_connection(user_id, only_if_token=only_if_token, session=own)
    row = session.get(GmailToken, user_id)
    if row is None or (only_if_token is not None and row.refresh_token != only_if_token):
        return None
    token = row.refresh_token
    session.delete(row)
    session.flush()
    return token
