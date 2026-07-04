#!/usr/bin/env python3
"""
Google OAuth2 "Sign in with your own Gmail" for per-user email sending.

Instead of one shared Gmail App Password, each user connects their own Google
account and grants the ``gmail.send`` scope, so worship emails are sent from
*their* mailbox. Refresh tokens are stored locally in
``data/gmail_tokens.json`` (gitignored) keyed by the user's email address.

This uses the standard OAuth 2.0 authorization-code flow via plain HTTPS
requests, so it adds no new dependencies (only ``requests``, already used
elsewhere in the project).

Setup (one-time, in your own Google account):
  1. Google Cloud Console -> create/select a project.
  2. APIs & Services -> Library -> enable the "Gmail API".
  3. APIs & Services -> OAuth consent screen -> External. Add the
     ``.../auth/gmail.send`` scope and add yourself (and anyone else) as a
     Test user (up to 100) so you can use it before Google verification.
  4. APIs & Services -> Credentials -> Create OAuth client ID ->
     "Web application". Add an Authorized redirect URI that exactly matches
     the app's URL (e.g. ``http://localhost:8501`` locally, or your
     Streamlit Cloud URL when hosted).
  5. Put the client ID/secret and redirect URI in ``.env`` (or Streamlit
     secrets):
        GOOGLE_CLIENT_ID=...
        GOOGLE_CLIENT_SECRET=...
        GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8501
"""

import base64
import json
import os
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional, Union
from urllib.parse import urlencode

import requests

# Scopes: identify the user (email) and let the app send mail as them.
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/gmail.send",
]

AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"
USERINFO_URI = "https://www.googleapis.com/oauth2/v2/userinfo"
GMAIL_SEND_URI = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
TOKENS_FILE = os.path.join(DATA_DIR, "gmail_tokens.json")

_TIMEOUT = 30


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
def _client_id() -> str:
    return os.getenv("GOOGLE_CLIENT_ID", "").strip()


def _client_secret() -> str:
    return os.getenv("GOOGLE_CLIENT_SECRET", "").strip()


def _redirect_uri() -> str:
    return os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "").strip()


def is_configured() -> bool:
    """True when the Google OAuth client is fully configured via env."""
    return bool(_client_id() and _client_secret() and _redirect_uri())


# --------------------------------------------------------------------------- #
# Token store (data/gmail_tokens.json)  ->  { email: {"refresh_token": "..."} }
# --------------------------------------------------------------------------- #
def _load_tokens() -> Dict[str, Dict[str, str]]:
    try:
        with open(TOKENS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, ValueError, OSError):
        return {}


def _save_tokens(tokens: Dict[str, Dict[str, str]]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(TOKENS_FILE, "w", encoding="utf-8") as f:
        json.dump(tokens, f, indent=2)


def list_connected() -> List[str]:
    """Emails that have a stored refresh token (i.e. connected accounts)."""
    return sorted(e for e, t in _load_tokens().items() if t.get("refresh_token"))


def is_connected(email: str) -> bool:
    return bool(_load_tokens().get(email, {}).get("refresh_token"))


def save_user_token(email: str, refresh_token: str) -> None:
    tokens = _load_tokens()
    tokens[email] = {"refresh_token": refresh_token}
    _save_tokens(tokens)


def disconnect(email: str) -> None:
    """Forget a user's stored Gmail credentials."""
    tokens = _load_tokens()
    if email in tokens:
        del tokens[email]
        _save_tokens(tokens)


# --------------------------------------------------------------------------- #
# OAuth flow
# --------------------------------------------------------------------------- #
def build_auth_url(state: str) -> str:
    """URL to send the user to Google's consent screen."""
    params = {
        "client_id": _client_id(),
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",       # request a refresh token
        "prompt": "consent",            # ensure a refresh token is returned
        "include_granted_scopes": "true",
        "state": state,
    }
    return f"{AUTH_URI}?{urlencode(params)}"


def exchange_code(code: str) -> Dict[str, Optional[str]]:
    """
    Exchange an authorization code for tokens, look up the user's email, and
    persist the refresh token. Returns {"email": ..., "refresh_token": ...}.
    Raises RuntimeError with a readable message on failure.
    """
    resp = requests.post(
        TOKEN_URI,
        data={
            "code": code,
            "client_id": _client_id(),
            "client_secret": _client_secret(),
            "redirect_uri": _redirect_uri(),
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

    email = _fetch_email(access_token)
    if not email:
        raise RuntimeError("Could not read your email address from Google.")

    if refresh_token:
        save_user_token(email, refresh_token)
    elif not is_connected(email):
        # No refresh token now and none stored before: Google only returns one
        # on first consent. prompt=consent should prevent this, but guard anyway.
        raise RuntimeError(
            "Google did not return a refresh token. Remove this app's access at "
            "https://myaccount.google.com/permissions and connect again."
        )
    return {"email": email, "refresh_token": refresh_token}


def _fetch_email(access_token: str) -> Optional[str]:
    resp = requests.get(
        USERINFO_URI,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=_TIMEOUT,
    )
    if not resp.ok:
        return None
    return resp.json().get("email")


def _access_token_for(email: str) -> str:
    """Get a fresh access token for a connected user via their refresh token."""
    refresh_token = _load_tokens().get(email, {}).get("refresh_token")
    if not refresh_token:
        raise RuntimeError(f"{email} is not connected. Connect the Gmail account first.")
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
            disconnect(email)
        raise RuntimeError(
            _google_error(resp)
            + " You may need to reconnect your Gmail account."
        )
    token = resp.json().get("access_token")
    if not token:
        raise RuntimeError("Google did not return a fresh access token.")
    return token


# --------------------------------------------------------------------------- #
# Sending
# --------------------------------------------------------------------------- #
def send_email(
    sender_email: str,
    to_email: Union[str, List[str]],
    subject: str,
    body_plain: str,
    *,
    attachment_bytes: Optional[bytes] = None,
    attachment_filename: Optional[str] = None,
) -> Optional[str]:
    """
    Send an email as ``sender_email`` via the Gmail API using that user's
    connected credentials. Returns None on success, or an error string.
    """
    if not is_configured():
        return (
            "Google sign-in isn't configured. Set GOOGLE_CLIENT_ID, "
            "GOOGLE_CLIENT_SECRET and GOOGLE_OAUTH_REDIRECT_URI."
        )

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
        access_token = _access_token_for(sender_email)
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
