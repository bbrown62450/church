"""Gmail and the bulletin email (slice 5b spec, "usecases/email.py"; slice 5b-2).

The Gmail connection is the user's own (user-scoped, `gmail_tokens`), so it
works in every church they belong to:
- gmail_status: configured, connected, and the Google address;
- start_gmail_connect: a new single-use state and Google's consent URL, with
  the signed-in address as the login hint;
- finish_gmail_connect: the state is checked (and used up) first, then the
  code is exchanged with no database session open, then the refresh token is
  stored. Every Google failure becomes one of the messages below; Google's
  own text is never shown (F §1.5);
- disconnect_gmail: the row is deleted, then the grant revoked at Google,
  best effort (a failed revoke is logged and ignored).

Task 12 adds send_bulletin_email. Logs carry user ids and outcomes, never a
code, a state, a token or an address (F §2.5). No FastAPI, Starlette or
Streamlit here.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Optional

import google_oauth
from db import session_scope
from domain_errors import DomainError, NotConfigured, Rejected, UpstreamError, UpstreamTimeout
from google_oauth import GoogleErrorKind, GoogleOAuthConfig, GoogleOAuthError

logger = logging.getLogger(__name__)

NOT_CONFIGURED = "Per-user Gmail sending isn't configured on this deployment."
MISCONFIGURED = "Gmail sending isn't set up correctly on this deployment."
STATE_INVALID = "This Gmail connection request expired or was already used. Try connecting again."
CODE_INVALID = "That Google approval has expired or was already used. Try connecting again."
INCOMPLETE = "Google returned an incomplete response. Try connecting again."
SCOPE_MISSING = "Google didn't give permission to send email. Try again and allow “Send email on your behalf”."
NO_EMAIL = "Could not read your email address from Google."
MISMATCH = ("That Google account doesn't match your signed-in email ({email}). "
            "Connect the Gmail account you're logged in with.")
NO_REFRESH_TOKEN = ("Google did not return a refresh token. Remove this app's access at "
                    "https://myaccount.google.com/permissions and connect again.")
GOOGLE_UNREACHABLE = "Couldn't reach Google. Try connecting again in a minute."
GOOGLE_SLOW = "Google took too long to respond. Try connecting again."


@dataclass(frozen=True)
class GmailStatus:
    configured: bool
    connected: bool
    google_email: Optional[str]


def not_configured() -> NotConfigured:
    return NotConfigured(NOT_CONFIGURED, code="gmail_not_configured")


def misconfigured(event: str, error: GoogleOAuthError) -> NotConfigured:
    """Our client id, secret or redirect URI is wrong: an ERROR in the log (Google's error code only)."""
    logger.error("%s outcome=client_misconfigured google_error=%s", event, error.google_error)
    return NotConfigured(MISCONFIGURED, code="gmail_not_configured")


def gmail_status(user_id: uuid.UUID, config: GoogleOAuthConfig) -> GmailStatus:
    """GET /gmail-connection."""
    connection = google_oauth.get_connection(user_id)
    return GmailStatus(configured=config.configured, connected=connection is not None,
                       google_email=connection.google_email if connection else None)


def start_gmail_connect(user_id: uuid.UUID, user_email: str, config: GoogleOAuthConfig) -> str:
    """POST /gmail-connection/auth-url: Google's consent URL with a new state."""
    if not config.configured:
        raise not_configured()
    state = google_oauth.create_state(user_id)
    return google_oauth.build_auth_url(config, state, login_hint=user_email)


def _connect_error(error: GoogleOAuthError, user_email: str) -> DomainError:
    kind = error.kind
    if kind == GoogleErrorKind.CLIENT_MISCONFIGURED:
        return misconfigured("gmail.connect", error)
    if kind == GoogleErrorKind.INVALID_GRANT:
        return Rejected(CODE_INVALID, code="gmail_connect_failed")
    if kind == GoogleErrorKind.SCOPE_MISSING:
        return Rejected(SCOPE_MISSING, code="gmail_connect_failed")
    if kind == GoogleErrorKind.NO_EMAIL:
        return Rejected(NO_EMAIL, code="gmail_connect_failed")
    if kind == GoogleErrorKind.EMAIL_MISMATCH:
        return Rejected(MISMATCH.format(email=user_email), code="gmail_connect_failed")
    if kind == GoogleErrorKind.INCOMPLETE_RESPONSE:
        return UpstreamError(INCOMPLETE, code="upstream_error")
    if kind == GoogleErrorKind.TIMEOUT:
        return UpstreamTimeout(GOOGLE_SLOW, code="upstream_timeout")
    return UpstreamError(GOOGLE_UNREACHABLE, code="upstream_error")


def finish_gmail_connect(user_id: uuid.UUID, user_email: str, code: str, state: str,
                         config: GoogleOAuthConfig) -> GmailStatus:
    """POST /gmail-connection: the order of the 5b spec's error table; nothing
    is stored unless every check passes. `user_email` is the verified address
    of the signed-in user (the token's), never a database lookup."""
    if not config.configured:
        raise not_configured()
    if google_oauth.consume_state(state) != user_id:               # CSRF first, in its own transaction
        logger.info("gmail.connect user_id=%s outcome=state_invalid", user_id)
        raise Rejected(STATE_INVALID, code="gmail_state_invalid")
    if not code.strip():
        raise Rejected(CODE_INVALID, code="gmail_connect_failed")
    try:
        grant = google_oauth.exchange_code(config, code, expected_email=user_email)   # no session open
    except GoogleOAuthError as error:
        logger.info("gmail.connect user_id=%s outcome=%s", user_id, error.kind.value)
        raise _connect_error(error, user_email) from None
    with session_scope() as s:
        if grant.refresh_token:
            google_oauth.save_user_token(user_id, grant.google_email, grant.refresh_token, session=s)
        elif google_oauth.get_connection(user_id, session=s) is None:
            logger.info("gmail.connect user_id=%s outcome=no_refresh_token", user_id)
            raise Rejected(NO_REFRESH_TOKEN, code="gmail_connect_failed")
    logger.info("gmail.connect user_id=%s outcome=connected", user_id)
    return gmail_status(user_id, config)


def disconnect_gmail(user_id: uuid.UUID, config: GoogleOAuthConfig) -> GmailStatus:
    """DELETE /gmail-connection: forget the connection, then revoke it at Google
    (best effort, outside the transaction)."""
    removed = google_oauth.delete_connection(user_id)
    if removed is not None and not google_oauth.revoke_token(removed):
        logger.warning("gmail.disconnect user_id=%s outcome=revoke_failed", user_id)
    logger.info("gmail.disconnect user_id=%s outcome=%s", user_id, "disconnected" if removed else "not_connected")
    return GmailStatus(configured=config.configured, connected=False, google_email=None)
