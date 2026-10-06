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

import base64
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional
from urllib.parse import urlencode

import httpx
from sqlalchemy import delete
from sqlalchemy.orm import Session

from db import session_scope
from db.models import GmailToken, OAuthState
from integrations import http

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
    client_secret: str = field(repr=False)
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
    in its own committed transaction. The row is read by the DELETE itself
    (RETURNING), so of two consumes racing for one state only the one whose
    delete removed the row gets the user (build review I1)."""
    if not state:
        return None
    with session_scope() as session:
        found = session.execute(
            delete(OAuthState).where(OAuthState.state == state)
            .returning(OAuthState.user_id, OAuthState.expires_at)
        ).first()
    if found is None:
        return None
    user_id, expires_at = found
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


# --------------------------------------------------------------------------- #
# The Google calls (Task 3)
# --------------------------------------------------------------------------- #
# F §1.8. httpx applies each value per phase, not to the whole call: 5 s to connect, then up to 15 s
# (a token, userinfo or refresh call), 30 s (the send) or 5 s (the revoke) for each wait on a write, a
# read or the pool. A slow but steady answer can therefore take longer than the number; the browser's own
# timeout (lib/api/timeouts.ts) is the overall deadline, and a send it stops waiting for is treated there
# as possibly sent.
TOKEN_TIMEOUT = httpx.Timeout(15.0, connect=5.0)
SEND_TIMEOUT = httpx.Timeout(30.0, connect=5.0)
REVOKE_TIMEOUT = httpx.Timeout(5.0, connect=5.0)

_CLIENT_ERRORS = {"invalid_client", "unauthorized_client", "redirect_uri_mismatch"}
_SCOPE_ERRORS = {"insufficientPermissions", "ACCESS_TOKEN_SCOPE_INSUFFICIENT"}
_LIMIT_ERRORS = {"rateLimitExceeded", "userRateLimitExceeded", "dailyLimitExceeded"}
# Gmail refuses the account itself (a Google account without Gmail, Gmail turned off by a Workspace admin).
_ACCOUNT_ERRORS = {"failedPrecondition", "FAILED_PRECONDITION"}
# A send that failed before its request was written cannot have reached Gmail.
_NOT_SENT = (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout, httpx.UnsupportedProtocol)


class GoogleErrorKind(str, Enum):
    INVALID_GRANT = "invalid_grant"                 # the code or the refresh token is no longer valid
    CLIENT_MISCONFIGURED = "client_misconfigured"   # our client id, secret or redirect URI
    INCOMPLETE_RESPONSE = "incomplete_response"     # no access token, an unreadable answer, or another token 400/401
    SCOPE_MISSING = "scope_missing"                 # consent given without "send email on your behalf"
    NO_EMAIL = "no_email"                           # userinfo had no address
    EMAIL_MISMATCH = "email_mismatch"               # a Google account other than the signed-in one
    INSUFFICIENT_SCOPE = "insufficient_scope"       # Gmail: the grant no longer allows sending
    SEND_LIMIT = "send_limit"                       # Gmail: a rate or daily limit
    ACCOUNT_REFUSED = "account_refused"             # Gmail: a 401 not about the scope, or a failed precondition
    SEND_REJECTED = "send_rejected"                 # Gmail: any other 4xx; nothing was sent
    UPSTREAM = "upstream"                           # a 5xx or a network error where nothing changed at Google
    TIMEOUT = "timeout"                             # no answer in time where nothing changed at Google
    SEND_UNCONFIRMED = "send_unconfirmed"           # the send was written but not confirmed: it may have gone out


class GoogleOAuthError(Exception):
    """A Google call failed in a way the caller maps to a message. `status` is
    Google's HTTP status (None for a network error); `google_error` is Google's
    error code (for example "invalid_client"), for the logs only: never shown."""

    def __init__(self, kind: GoogleErrorKind, *, status: Optional[int] = None,
                 google_error: Optional[str] = None):
        super().__init__(kind.value)
        self.kind = kind
        self.status = status
        self.google_error = google_error


@dataclass(frozen=True)
class GmailGrant:
    """What a successful code exchange gives: the Google address (as Google
    spells it), the refresh token (None when Google sent none) and the granted scopes."""

    google_email: str
    refresh_token: Optional[str]
    scopes: frozenset[str]


def _error_names(resp: httpx.Response) -> set[str]:
    """Google's error names in a response body: the OAuth "error" string, or the
    Gmail API's error status and each reason. Empty for a body that is not JSON."""
    try:
        body = resp.json()
    except ValueError:
        return set()
    if not isinstance(body, dict):
        return set()
    error = body.get("error")
    if isinstance(error, str):
        return {error}
    if not isinstance(error, dict):
        return set()
    names = {error["status"]} if isinstance(error.get("status"), str) else set()
    for item in [*(error.get("errors") or []), *(error.get("details") or [])]:
        if isinstance(item, dict) and isinstance(item.get("reason"), str):
            names.add(item["reason"])
    return names


def _failure(resp: httpx.Response, phase: str) -> GoogleOAuthError:
    """The error for a non-2xx answer. `phase` is "token", "userinfo",
    "refresh" or "send" (5b spec, the one classification helper)."""
    names = _error_names(resp)
    named = next(iter(sorted(names, key=lambda name: (name.isupper(), name))), None)   # a reason before a STATUS
    status = resp.status_code
    if phase == "send":
        if status == 403 and names & _SCOPE_ERRORS:
            return GoogleOAuthError(GoogleErrorKind.INSUFFICIENT_SCOPE, status=status, google_error=named)
        if status == 429 or (status == 403 and names & _LIMIT_ERRORS):
            return GoogleOAuthError(GoogleErrorKind.SEND_LIMIT, status=status, google_error=named)
        if status == 401 or (status == 400 and names & _ACCOUNT_ERRORS):
            return GoogleOAuthError(GoogleErrorKind.ACCOUNT_REFUSED, status=status, google_error=named)
        if status >= 500:
            return GoogleOAuthError(GoogleErrorKind.SEND_UNCONFIRMED, status=status, google_error=named)
        return GoogleOAuthError(GoogleErrorKind.SEND_REJECTED, status=status, google_error=named)
    if phase in ("token", "refresh") and status in (400, 401):
        if "invalid_grant" in names:
            return GoogleOAuthError(GoogleErrorKind.INVALID_GRANT, status=status, google_error="invalid_grant")
        client = names & _CLIENT_ERRORS
        if client:
            return GoogleOAuthError(GoogleErrorKind.CLIENT_MISCONFIGURED, status=status,
                                    google_error=sorted(client)[0])
        # Google answered and refused the request (invalid_request, invalid_scope, or a 400 or 401
        # with no readable error): not "couldn't reach Google" but "try connecting again" (build review M4).
        return GoogleOAuthError(GoogleErrorKind.INCOMPLETE_RESPONSE, status=status, google_error=named)
    if phase == "userinfo" and status < 500:
        return GoogleOAuthError(GoogleErrorKind.NO_EMAIL, status=status, google_error=named)
    return GoogleOAuthError(GoogleErrorKind.UPSTREAM, status=status, google_error=named)


def _transport_failure(exc: httpx.HTTPError, phase: str) -> GoogleOAuthError:
    """The error for a request that got no answer. A send that was written may
    have gone out (SEND_UNCONFIRMED); any other call changed nothing at Google."""
    if phase == "send":
        return GoogleOAuthError(GoogleErrorKind.UPSTREAM if isinstance(exc, _NOT_SENT)
                                else GoogleErrorKind.SEND_UNCONFIRMED)
    return GoogleOAuthError(GoogleErrorKind.TIMEOUT if isinstance(exc, httpx.TimeoutException)
                            else GoogleErrorKind.UPSTREAM)


def _json(resp: httpx.Response) -> dict[str, Any]:
    try:
        body = resp.json()
    except ValueError:
        raise GoogleOAuthError(GoogleErrorKind.INCOMPLETE_RESPONSE, status=resp.status_code) from None
    if not isinstance(body, dict):
        raise GoogleOAuthError(GoogleErrorKind.INCOMPLETE_RESPONSE, status=resp.status_code)
    return body


def _token_request(form: dict[str, str], phase: str) -> dict[str, Any]:
    try:
        resp = http.post(TOKEN_URI, data=form, timeout=TOKEN_TIMEOUT)
    except httpx.HTTPError as exc:
        raise _transport_failure(exc, phase) from None
    if not resp.is_success:
        raise _failure(resp, phase)
    return _json(resp)


def _access_token(payload: dict[str, Any]) -> str:
    token = payload.get("access_token")
    if not isinstance(token, str) or not token:
        raise GoogleOAuthError(GoogleErrorKind.INCOMPLETE_RESPONSE)
    return token


def _granted_scopes(payload: dict[str, Any]) -> frozenset[str]:
    """The granted scopes. No `scope` (or a blank one) means exactly the
    requested ones (RFC 6749 §5.1); one without gmail.send is SCOPE_MISSING."""
    scope = payload.get("scope")
    if scope is None or scope == "":
        return frozenset(SCOPES)
    if not isinstance(scope, str):
        raise GoogleOAuthError(GoogleErrorKind.INCOMPLETE_RESPONSE)
    granted = frozenset(scope.split())
    if GMAIL_SEND_SCOPE not in granted:
        raise GoogleOAuthError(GoogleErrorKind.SCOPE_MISSING)
    return granted


def _fetch_userinfo_email(access_token: str) -> str:
    try:
        resp = http.get(USERINFO_URI, headers={"Authorization": f"Bearer {access_token}"},
                        read_timeout=TOKEN_TIMEOUT.read)
    except httpx.HTTPError as exc:
        raise _transport_failure(exc, "userinfo") from None
    if not resp.is_success:
        raise _failure(resp, "userinfo")
    try:
        email = resp.json().get("email")
    except (ValueError, AttributeError):
        email = None
    if not isinstance(email, str) or not email.strip():
        raise GoogleOAuthError(GoogleErrorKind.NO_EMAIL)
    return email.strip()


def exchange_code(config: GoogleOAuthConfig, code: str, *, expected_email: str) -> GmailGrant:
    """Exchange the consent screen's code (15 s), check the granted scopes, read
    the Google address (15 s) and compare it, ignoring case, with the signed-in
    user's. Stores nothing (the caller does, in its own transaction). A grant
    refused for its scopes or its address is revoked at Google first, best effort."""
    payload = _token_request({
        "code": code,
        "client_id": config.client_id,
        "client_secret": config.client_secret,
        "redirect_uri": config.redirect_uri,
        "grant_type": "authorization_code",
    }, "token")
    access_token = _access_token(payload)
    refresh = payload.get("refresh_token")
    refresh_token = refresh if isinstance(refresh, str) and refresh else None
    try:
        scopes = _granted_scopes(payload)
        google_email = _fetch_userinfo_email(access_token)
        if google_email.lower() != expected_email.strip().lower():
            raise GoogleOAuthError(GoogleErrorKind.EMAIL_MISMATCH)
    except GoogleOAuthError as error:
        if error.kind in (GoogleErrorKind.SCOPE_MISSING, GoogleErrorKind.EMAIL_MISMATCH):
            # A grant we refuse is not left behind at Google (build review M2): best effort,
            # the refresh token when there is one (it revokes the whole grant), else the access token.
            revoke_token(refresh_token or access_token)
        raise
    return GmailGrant(google_email=google_email, refresh_token=refresh_token, scopes=scopes)


def refresh_access_token(config: GoogleOAuthConfig, refresh_token: str) -> str:
    """A fresh access token for the stored refresh token (15 s)."""
    payload = _token_request({
        "client_id": config.client_id,
        "client_secret": config.client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }, "refresh")
    return _access_token(payload)


def send_raw_message(access_token: str, raw: bytes) -> None:
    """Send one MIME message (its bytes) through the Gmail API's JSON endpoint
    (SEND_TIMEOUT, per phase; the caller keeps the message small enough for it).
    A failure before the request was written is UPSTREAM (nothing was sent); no
    answer after it, or a Gmail 5xx, is SEND_UNCONFIRMED (it may have been sent)."""
    body = {"raw": base64.urlsafe_b64encode(raw).decode("ascii")}
    try:
        resp = http.post(GMAIL_SEND_URI, json=body, headers={"Authorization": f"Bearer {access_token}"},
                         timeout=SEND_TIMEOUT)
    except httpx.HTTPError as exc:
        raise _transport_failure(exc, "send") from None
    if not resp.is_success:
        raise _failure(resp, "send")


def revoke_token(token: str) -> bool:
    """Ask Google to revoke the grant (5 s), best effort: True when Google said
    yes, False on any failure. Never raises."""
    try:
        resp = http.post(REVOKE_URI, data={"token": token}, timeout=REVOKE_TIMEOUT)
    except httpx.HTTPError:
        return False
    return resp.is_success
