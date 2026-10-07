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

send_bulletin_email (Task 12) emails the bulletin from the caller's Gmail,
in the 5b spec's order (§Errors, "POST /bulletin-emails"): the recipients
(the church's contacts by id, the other addresses, each through
email_addresses.normalize_address, then de-duplicated: 1 to 50), the
attachments (at least one), the connection, the files built from the posted
service (5a's bulletin copy, the printed bulletin's PDF) and the message's
size (MAX_RAW_BYTES), the `email` rate limit (`charge`; peeked with
`check_charge` before the files are built), and only then Google: the token refresh and the send, with
no database session open. A refused grant forgets the connection only if it
still holds the token that failed. A send that may have gone out is a 502 or
504 with details.send_uncertain, which the route keeps for a retry with the
same key. Nothing is recorded (hymn use is recorded on Save).

Logs carry ids, counts, outcomes and Google's error reason (a name such as
failedPrecondition), never a code, a state, a token, an address, the
subject, the message or Google's text (F §2.5). No FastAPI, Starlette or
Streamlit here.
"""
from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal, Optional

import email_contacts
import google_oauth
import printed_bulletin
import service_output
from bulletin_email import Attachment, compose_bulletin_email
from db import session_scope
from domain_errors import (Conflict, DomainError, InvalidInput, NotConfigured, NotFound, Rejected, UpstreamError,
                           UpstreamTimeout)
from email_addresses import InvalidAddress, dedupe_addresses, normalize_address
from google_oauth import GmailConnection, GoogleErrorKind, GoogleOAuthConfig, GoogleOAuthError
from usecases import archive, documents

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


def _same_address(connection: Optional[google_oauth.GmailConnection], google_email: str) -> bool:
    return connection is not None and connection.google_email.strip().lower() == google_email.strip().lower()


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
        # Google's error code (for example "invalid_request") only, never its text (F §2.5).
        logger.info("gmail.connect user_id=%s outcome=%s google_error=%s", user_id, error.kind.value,
                    error.google_error)
        raise _connect_error(error, user_email) from None
    with session_scope() as s:
        if grant.refresh_token:
            google_oauth.save_user_token(user_id, grant.google_email, grant.refresh_token, session=s)
        elif not _same_address(google_oauth.get_connection(user_id, session=s), grant.google_email):
            # No refresh token: only a stored connection for this same Google address can stand
            # in for it (build review M1); another address's token is not this grant's.
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


# --- emailing the bulletin (Task 12) ---------------------------------------------------------------

MAX_RECIPIENTS = 50
MALFORMED_CONTACT_HINT = "An admin can fix it in Settings → Contacts."
CONTACT_GONE = "One of the selected contacts no longer exists. Refresh the list and try again."
MALFORMED_CONTACT = "The saved contact “{label}” has an invalid email address. " + MALFORMED_CONTACT_HINT
BAD_ADDRESS = "“{value}” isn't a valid email address."
NO_RECIPIENTS = "Please select at least one recipient or enter an email address."
TOO_MANY = f"You can email at most {MAX_RECIPIENTS} people at once."
NO_ATTACHMENT = "Choose at least one attachment."
NOT_CONNECTED = "Connect your Gmail first, then try again."
EXPIRED = "Your Gmail connection has expired or was removed. Reconnect Gmail and try again."
NO_SEND_PERMISSION = "Your Gmail connection no longer allows sending. Reconnect Gmail and try again."
CHANGED = "Your Gmail connection changed while sending. Nothing was sent. Try again."
GMAIL_UNREACHABLE = "Couldn't reach Gmail. Nothing was sent. Try again in a minute."
GOOGLE_SLOW_NOTHING_SENT = "Google took too long to respond. Nothing was sent. Try again."
SEND_LIMIT = "Gmail's sending limit has been reached. Nothing was sent. Try again later."
SEND_REJECTED = "Gmail couldn't send this message. Nothing was sent. Check the email addresses and try again."
ACCOUNT_REFUSED = ("Gmail won't send from this Google account. Nothing was sent. "
                   "Check that you can send email in Gmail with it, then try again.")
TOO_LARGE = "The attachments are too large to email. Try sending only the bulletin copy."
# The Gmail API's JSON endpoint takes the message base64url-encoded inside the request (a third larger),
# and Google's upload guide puts simple requests at 5 MB at most
# (https://developers.google.com/workspace/gmail/api/guides/uploads). A message over 3.5 MB (about
# 4.7 MB once encoded) is refused here, before the email limit is charged and before Google is called.
# The bulletin copy is tens of KB and the printed PDF about a megabyte at most.
MAX_RAW_BYTES = 3_500_000
MAYBE_SENT_PROBLEM = ("Gmail reported a problem, so the email may already have been sent. "
                      "Check your Gmail Sent folder before sending again.")
MAYBE_SENT_UNCONFIRMED = ("Gmail didn't confirm the email, so it may already have been sent. "
                          "Check your Gmail Sent folder before sending again.")

AttachmentKind = Literal["docx", "pdf"]


def _send_failed(message: str, *, disconnected: bool = False, uncertain: bool = False) -> UpstreamError:
    return UpstreamError(message, code="gmail_send_failed",
                         details={"disconnected": disconnected, "send_uncertain": uncertain})


def _recipients(church_id: uuid.UUID, contact_ids: Sequence[uuid.UUID],
                additional_emails: Sequence[str], session) -> list[str]:
    """Step 5: the contacts' addresses in the order asked, then the others, each
    checked, without repeats (any case). 404 for a contact the church does not
    have; 422 naming the contact or the address; 422 for none or too many."""
    contacts = email_contacts.get_contacts_by_ids(church_id, contact_ids, session=session)
    if len(contacts) != len(set(contact_ids)):
        raise NotFound(CONTACT_GONE, details={"field": "contact_ids"})
    addresses = []
    for contact in contacts:
        try:
            addresses.append(normalize_address(contact["email"]))
        except InvalidAddress:
            label = (contact["name"] or "").strip() or contact["email"].strip()
            raise InvalidInput(MALFORMED_CONTACT.format(label=label), field="contact_ids") from None
    for value in additional_emails:
        try:
            addresses.append(normalize_address(value))
        except InvalidAddress:
            raise InvalidInput(BAD_ADDRESS.format(value=value.strip()[:60]), field="additional_emails") from None
    recipients = dedupe_addresses(addresses)
    if not recipients:
        raise InvalidInput(NO_RECIPIENTS, field="recipients")
    if len(recipients) > MAX_RECIPIENTS:
        raise InvalidInput(TOO_MANY, field="recipients")
    return recipients


def _attachments(church_id: uuid.UUID, data: archive.ServiceInput, kinds: Sequence[AttachmentKind],
                 translation: Optional[str], charge_scripture: Callable[[int], None]) -> list[Attachment]:
    """Step 7: each file built from the posted service, as the downloads build it."""
    files = []
    if "docx" in kinds:
        doc = documents.build_document(church_id, data, "bulletin")
        files.append(Attachment(doc.content, doc.filename, service_output.DOCX_MIME))
    if "pdf" in kinds:
        pdf = documents.build_printed(church_id, data, "pdf", translation, charge=charge_scripture)
        files.append(Attachment(pdf.content, pdf.filename, printed_bulletin.PDF_MIME))
    return files


def _refused_grant(user_id: uuid.UUID, connection: GmailConnection, message: str) -> UpstreamError:
    """Google says the grant is gone: forget it, unless it was replaced meanwhile."""
    removed = google_oauth.delete_connection(user_id, only_if_token=connection.refresh_token)
    if removed is None:
        return _send_failed(CHANGED)
    return _send_failed(message, disconnected=True)


def _refresh_error(error: GoogleOAuthError, user_id: uuid.UUID, connection: GmailConnection) -> DomainError:
    if error.kind == GoogleErrorKind.INVALID_GRANT:
        return _refused_grant(user_id, connection, EXPIRED)
    if error.kind == GoogleErrorKind.CLIENT_MISCONFIGURED:
        return misconfigured("bulletin_email.refresh", error)
    if error.kind == GoogleErrorKind.TIMEOUT:
        return UpstreamTimeout(GOOGLE_SLOW_NOTHING_SENT, code="upstream_timeout")
    return _send_failed(GMAIL_UNREACHABLE)


def _send_error(error: GoogleOAuthError, user_id: uuid.UUID, connection: GmailConnection) -> DomainError:
    kind = error.kind
    if kind == GoogleErrorKind.INSUFFICIENT_SCOPE:
        return _refused_grant(user_id, connection, NO_SEND_PERMISSION)
    if kind == GoogleErrorKind.SEND_LIMIT:
        return _send_failed(SEND_LIMIT)
    if kind == GoogleErrorKind.ACCOUNT_REFUSED:
        return _send_failed(ACCOUNT_REFUSED)
    if kind == GoogleErrorKind.SEND_REJECTED:
        return _send_failed(SEND_REJECTED)
    if kind == GoogleErrorKind.SEND_UNCONFIRMED and error.status is not None:
        return _send_failed(MAYBE_SENT_PROBLEM, uncertain=True)
    if kind == GoogleErrorKind.SEND_UNCONFIRMED:
        return UpstreamTimeout(MAYBE_SENT_UNCONFIRMED, code="upstream_timeout", details={"send_uncertain": True})
    return _send_failed(GMAIL_UNREACHABLE)


def send_bulletin_email(church_id: uuid.UUID, user_id: uuid.UUID, data: archive.ServiceInput, *,
                        contact_ids: Sequence[uuid.UUID], additional_emails: Sequence[str], message: Optional[str],
                        attachments: Sequence[AttachmentKind], translation: Optional[str],
                        config: GoogleOAuthConfig, charge: Callable[[], None] = lambda: None,
                        charge_scripture: Callable[[int], None] = lambda parts: None,
                        check_charge: Callable[[], None] = lambda: None) -> int:
    """POST /bulletin-emails: the number of people emailed. `charge` is the
    `email` bucket (called once, right before Google); `check_charge` peeks at
    it without charging, before the files are built, so a caller at the limit
    neither waits for the PDF nor pays its readings; `charge_scripture` the
    printed bulletin's readings fetch (POST /documents/printed's)."""
    started = time.monotonic()
    kinds = [kind for kind in ("docx", "pdf") if kind in attachments]
    with session_scope() as s:                                  # steps 5-6, closed before step 7
        recipients = _recipients(church_id, contact_ids, additional_emails, s)
        if not kinds:
            raise InvalidInput(NO_ATTACHMENT, field="attachments")
        connection = google_oauth.get_connection(user_id, session=s)
    if not config.configured:
        raise not_configured()
    if connection is None:
        raise Conflict(NOT_CONNECTED, code="gmail_not_connected")
    check_charge()                                              # at the limit: refused before any file is built
    files = _attachments(church_id, data, kinds, translation, charge_scripture)
    raw = compose_bulletin_email(sender=connection.google_email, recipients=recipients,
                                 service_date=data.service_date, message=message, attachments=files).as_bytes()
    if len(raw) > MAX_RAW_BYTES:
        logger.info("bulletin_email.too_large church_id=%s user_id=%s bytes=%d", church_id, user_id, len(raw))
        raise InvalidInput(TOO_LARGE, field="attachments")
    charge()                                                    # step 8: the only 429 here
    try:
        access_token = google_oauth.refresh_access_token(config, connection.refresh_token)
    except GoogleOAuthError as error:
        logger.info("bulletin_email.refresh church_id=%s user_id=%s outcome=%s", church_id, user_id, error.kind.value)
        raise _refresh_error(error, user_id, connection) from None
    try:
        google_oauth.send_raw_message(access_token, raw)
    except GoogleOAuthError as error:
        logger.info("bulletin_email.send church_id=%s user_id=%s outcome=%s status=%s google_error=%s", church_id,
                    user_id, error.kind.value, error.status, error.google_error)
        raise _send_error(error, user_id, connection) from None
    logger.info("bulletin_email.sent church_id=%s user_id=%s recipients=%d bcc=%s attachments=%s bytes=%d ms=%d",
                church_id, user_id, len(recipients), len(recipients) > 1, ",".join(kinds), len(raw),
                round((time.monotonic() - started) * 1000))
    return len(recipients)
