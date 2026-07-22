#!/usr/bin/env python3
"""Google OAuth2 "Sign in with your own Gmail" for per-user email sending.

Each user connects their own Google account and grants the ``gmail.send`` scope,
so worship emails are sent from *their* mailbox. Refresh tokens are stored in the
``gmail_tokens`` table keyed by the user's id (user-scoped, not church-scoped:
one connection works across every church the user belongs to).

Uses the standard OAuth 2.0 authorization-code flow via plain HTTPS requests.

Setup (one-time, in your own Google account):
  1. Google Cloud Console -> create/select a project.
  2. APIs & Services -> Library -> enable the "Gmail API".
  3. APIs & Services -> OAuth consent screen -> External. Add the
     ``.../auth/gmail.send`` scope and add each user as a Test user (up to 100)
     until the app is verified.
  4. APIs & Services -> Credentials -> Create OAuth client ID -> "Web
     application". Register the app's root URL as an Authorized redirect URI
     (e.g. ``http://localhost:8501`` locally, or the Streamlit Cloud URL). The
     st.login flow uses ``<app>/oauth2callback`` separately.
  5. Put the client ID/secret and redirect URI in ``.env`` / Streamlit secrets:
        GOOGLE_CLIENT_ID=...
        GOOGLE_CLIENT_SECRET=...
        GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8501
"""

import base64
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional, Union
from urllib.parse import urlencode

import requests

from db import session_scope
from db.models import GmailToken, OAuthState, User

# Scopes: identify the connecting Google account (email) and let the app send
# mail as them. openid/userinfo.email are kept ONLY so the callback can verify
# the connected Google account matches the logged-in user (Task 16).
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/gmail.send",
]

AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"
USERINFO_URI = "https://www.googleapis.com/oauth2/v2/userinfo"
GMAIL_SEND_URI = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"

_TIMEOUT = 30

# Marker appended to the manual gmail.send redirect (app root) so its ?code=
# is distinguishable from Streamlit's internal /oauth2callback (§1).
GMAIL_OAUTH_MARKER = "gmail_oauth"
# Short TTL for a single-use CSRF state.
STATE_TTL = timedelta(minutes=10)


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
def _client_id() -> str:
    return os.getenv("GOOGLE_CLIENT_ID", "").strip()


def _client_secret() -> str:
    return os.getenv("GOOGLE_CLIENT_SECRET", "").strip()


def _redirect_uri() -> str:
    return os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "").strip()


def _redirect_uri_with_marker() -> str:
    """The app-root redirect_uri plus the gmail_oauth marker query param."""
    base = _redirect_uri()
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}{GMAIL_OAUTH_MARKER}=1"


def _user_email(user_id: uuid.UUID) -> Optional[str]:
    """The stored (normalized) email for a user id, or None if unknown."""
    with session_scope() as session:
        user = session.get(User, user_id)
        return user.email if user else None


def is_configured() -> bool:
    """True when the Google OAuth client is fully configured via env."""
    return bool(_client_id() and _client_secret() and _redirect_uri())


# --------------------------------------------------------------------------- #
# Token store (gmail_tokens table, keyed by user_id — user-scoped, not church)
# --------------------------------------------------------------------------- #
def is_connected(user_id: uuid.UUID) -> bool:
    """True when the user has a stored Gmail refresh token."""
    with session_scope() as session:
        row = session.get(GmailToken, user_id)
        return bool(row and row.refresh_token)


def save_user_token(user_id: uuid.UUID, google_email: str, refresh_token: str) -> None:
    """Persist (or replace) a user's Gmail refresh token; one row per user."""
    with session_scope() as session:
        row = session.get(GmailToken, user_id)
        if row is None:
            session.add(
                GmailToken(
                    user_id=user_id,
                    google_email=google_email,
                    refresh_token=refresh_token,
                )
            )
        else:
            row.google_email = google_email
            row.refresh_token = refresh_token


def disconnect(user_id: uuid.UUID) -> None:
    """Forget a user's stored Gmail credentials."""
    with session_scope() as session:
        row = session.get(GmailToken, user_id)
        if row is not None:
            session.delete(row)


# --------------------------------------------------------------------------- #
# OAuth flow
# --------------------------------------------------------------------------- #
def build_auth_url(state: str) -> str:
    """URL to send the user to Google's consent screen for the gmail.send grant.

    The redirect target is the app root plus the gmail_oauth marker so the return
    trip is distinguishable from Streamlit's internal /oauth2callback handler and
    is only processed by should_handle_gmail_callback().
    """
    params = {
        "client_id": _client_id(),
        "redirect_uri": _redirect_uri_with_marker(),
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",       # request a refresh token
        "prompt": "consent",            # ensure a refresh token is returned
        "state": state,
    }
    return f"{AUTH_URI}?{urlencode(params)}"


def create_state(user_id: uuid.UUID) -> str:
    """Create a single-use CSRF state bound to the user; return the opaque token."""
    state = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    with session_scope() as session:
        session.add(
            OAuthState(
                state=state,
                user_id=user_id,
                created_at=now,
                expires_at=now + STATE_TTL,
            )
        )
    return state


def consume_state(state: str) -> Optional[uuid.UUID]:
    """Validate and consume a CSRF state; return the bound user_id on success.

    Single-use: the row is deleted whenever found (valid *or* expired). Returns
    None for missing / expired / already-used states — never raises, and a
    missing state is never treated as a pass (§4).
    """
    if not state:
        return None
    with session_scope() as session:
        row = session.get(OAuthState, state)
        if row is None:
            return None
        user_id = row.user_id
        expires_at = row.expires_at
        session.delete(row)  # consumed regardless of validity
    if expires_at is None:
        return None
    if expires_at.tzinfo is None:            # SQLite may hand back naive datetimes
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None
    return user_id


def should_handle_gmail_callback(query_params, is_logged_in: bool) -> bool:
    """Whether a ?code= belongs to the manual gmail.send flow (vs. st.login).

    Pure/testable. True only when the gmail marker is present, an auth code is
    present, and a login session already exists — keeping Streamlit's internal
    handler from grabbing the manual code and enforcing "never exchange a token
    before authentication" (§4).
    """
    if not is_logged_in or not query_params:
        return False
    has_marker = str(query_params.get(GMAIL_OAUTH_MARKER, "")) in ("1", "true", "True")
    has_code = bool(query_params.get("code"))
    return has_marker and has_code


def exchange_code(code: str, expected_user_id: uuid.UUID) -> dict:
    """Exchange an authorization code for tokens and store them for the signed-in
    user only.

    Security (§4): the refresh token is saved *only if* the Google account that
    authorized equals the signed-in user's email. A mismatch raises RuntimeError
    and stores nothing, so a user can never connect (or later send as) an account
    that isn't theirs. Returns {"user_id": UUID, "email": str, "refresh_token": str|None}.
    """
    expected_email = _user_email(expected_user_id)
    if not expected_email:
        raise RuntimeError("Sign in before connecting a Gmail account.")

    resp = requests.post(
        TOKEN_URI,
        data={
            "code": code,
            "client_id": _client_id(),
            "client_secret": _client_secret(),
            "redirect_uri": _redirect_uri_with_marker(),
            "grant_type": "authorization_code",
        },
        timeout=_TIMEOUT,
    )
    if not resp.ok:
        raise RuntimeError(_google_error(resp))
    payload = resp.json()
    access_token = payload.get("access_token")
    refresh_token = payload.get("refresh_token")
    if not access_token:
        raise RuntimeError("Google did not return an access token.")

    google_email = _fetch_email(access_token)
    if not google_email:
        raise RuntimeError("Could not read your email address from Google.")

    if google_email.strip().lower() != expected_email.strip().lower():
        raise RuntimeError(
            "That Google account doesn't match your signed-in email. "
            "Connect the Gmail account you're logged in with."
        )

    if refresh_token:
        save_user_token(expected_user_id, google_email, refresh_token)
    elif not is_connected(expected_user_id):
        raise RuntimeError(
            "Google did not return a refresh token. Remove this app's access at "
            "https://myaccount.google.com/permissions and connect again."
        )
    return {
        "user_id": expected_user_id,
        "email": google_email,
        "refresh_token": refresh_token,
    }


def _fetch_email(access_token: str) -> Optional[str]:
    resp = requests.get(
        USERINFO_URI,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=_TIMEOUT,
    )
    if not resp.ok:
        return None
    return resp.json().get("email")


def _access_token_for(user_id: uuid.UUID) -> str:
    """Get a fresh access token for a connected user via their refresh token."""
    with session_scope() as session:
        row = session.get(GmailToken, user_id)
        refresh_token = row.refresh_token if row else None
    if not refresh_token:
        raise RuntimeError("This account is not connected. Connect Gmail first.")
    resp = requests.post(
        TOKEN_URI,
        data={
            "client_id": _client_id(),
            "client_secret": _client_secret(),
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=_TIMEOUT,
    )
    if not resp.ok:
        # A revoked or expired grant lands here; drop it so the UI re-prompts.
        if resp.status_code in (400, 401):
            disconnect(user_id)
        raise RuntimeError(
            _google_error(resp) + " You may need to reconnect your Gmail account."
        )
    token = resp.json().get("access_token")
    if not token:
        raise RuntimeError("Google did not return a fresh access token.")
    return token


# --------------------------------------------------------------------------- #
# Sending
# --------------------------------------------------------------------------- #
def send_email(
    user_id: uuid.UUID,
    to_email: Union[str, List[str]],
    subject: str,
    body_plain: str,
    *,
    attachment_bytes: Optional[bytes] = None,
    attachment_filename: Optional[str] = None,
) -> Optional[str]:
    """
    Send an email as the user's connected Gmail via the Gmail API. Returns None
    on success, or an error string.

    The sender ("From") is taken solely from the user's stored GmailToken row —
    never from a caller-supplied address — so nobody can send as an account they
    have not connected (fixes the §4 sender-spoofing bug).
    """
    if not is_configured():
        return (
            "Google sign-in isn't configured. Set GOOGLE_CLIENT_ID, "
            "GOOGLE_CLIENT_SECRET and GOOGLE_OAUTH_REDIRECT_URI."
        )

    with session_scope() as session:
        row = session.get(GmailToken, user_id)
        sender_email = row.google_email if row else None
        has_token = bool(row and row.refresh_token)
    if not has_token or not sender_email:
        return "Your account isn't connected to Gmail. Connect your Gmail first."

    if isinstance(to_email, list):
        recipients = [e.strip() for e in to_email if (e or "").strip()]
    else:
        recipients = [e.strip() for e in (to_email or "").split(",") if e.strip()]
    if not recipients:
        return "Recipient email is required."

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.attach(MIMEText(body_plain, "plain"))

    if attachment_bytes and attachment_filename:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment_bytes)
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition", "attachment", filename=attachment_filename
        )
        msg.attach(part)

    try:
        access_token = _access_token_for(user_id)
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        resp = requests.post(
            GMAIL_SEND_URI,
            headers={"Authorization": f"Bearer {access_token}"},
            json={"raw": raw},
            timeout=_TIMEOUT,
        )
        if not resp.ok:
            return _google_error(resp)
        return None
    except Exception as e:  # noqa: BLE001 - surface any failure to the UI
        return str(e)


def _google_error(resp: "requests.Response") -> str:
    """Extract a human-readable message from a Google error response."""
    try:
        data = resp.json()
    except ValueError:
        return f"Google API error {resp.status_code}: {resp.text[:300]}"
    err = data.get("error")
    if isinstance(err, dict):
        msg = err.get("message") or err.get("status") or ""
    else:
        msg = data.get("error_description") or err or ""
    return f"Google API error {resp.status_code}: {msg}".strip()
