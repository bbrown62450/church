"""usecases.email (slice 5b spec, Testing "test_usecase_email.py"; slice 5b-2):
the Gmail connection (status, start, finish, disconnect) and (Task 12) the
bulletin email, against tests.fake_google. No network."""
import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from io import BytesIO
from urllib.parse import parse_qs, urlsplit
from zipfile import ZipFile

import httpx
import pytest
from sqlalchemy import event

import email_contacts
import google_oauth
from db import session_scope
from db.models import GmailToken, HymnUsage, OAuthState
from domain_errors import (Conflict, DomainError, InvalidInput, NotConfigured, NotFound, RateLimited, Rejected, UpstreamError,
                           UpstreamTimeout)
from repos.memberships import add_membership
from service_output import CustomElement
from tests.fake_google import REFRESH_TOKEN, FakeGoogle, gmail_error, google_error
from usecases import archive, documents, email
from usecases.liturgy import HymnRefData

CONFIG = google_oauth.GoogleOAuthConfig("client-123", "secret-456", "https://app.example.org/gmail/callback")
UNCONFIGURED = google_oauth.GoogleOAuthConfig("", "", "")
OWNER = "owner@example.com"


@pytest.fixture
def owner(tmp_db, make_user):
    return make_user(email=OWNER)


def _rows() -> list[tuple]:
    with session_scope() as s:
        return [(r.user_id, r.google_email, r.refresh_token) for r in s.query(GmailToken).all()]


def _finish(user, state=None, code="auth-code", config=CONFIG, email_=OWNER):
    state = google_oauth.create_state(user) if state is None else state
    return email.finish_gmail_connect(user, email_, code, state, config)


def _error(call):
    with pytest.raises(Exception) as failed:
        call()
    error = failed.value
    return type(error), error.code, error.message


def test_status_before_and_after_connecting(owner):
    assert email.gmail_status(owner, CONFIG) == email.GmailStatus(True, False, None)
    assert email.gmail_status(owner, UNCONFIGURED) == email.GmailStatus(False, False, None)
    google_oauth.save_user_token(owner, "Owner@Example.com", REFRESH_TOKEN)
    assert email.gmail_status(owner, CONFIG) == email.GmailStatus(True, True, "Owner@Example.com")


def test_start_returns_googles_url_with_a_state_stored_for_the_caller(owner):
    url = email.start_gmail_connect(owner, OWNER, CONFIG)
    query = {key: values[0] for key, values in parse_qs(urlsplit(url).query).items()}
    assert url.startswith("https://accounts.google.com/") and query["login_hint"] == OWNER
    assert google_oauth.consume_state(query["state"]) == owner
    assert _error(lambda: email.start_gmail_connect(owner, OWNER, UNCONFIGURED)) == (
        NotConfigured, "gmail_not_configured", "Per-user Gmail sending isn't configured on this deployment.")


def test_finish_stores_the_connection(owner):
    FakeGoogle(email="Owner@Example.com").install()
    assert _finish(owner) == email.GmailStatus(True, True, "Owner@Example.com")
    assert _rows() == [(owner, "Owner@Example.com", REFRESH_TOKEN)]


def test_a_state_that_is_another_users_used_expired_or_unknown_stores_nothing(owner, make_user):
    google = FakeGoogle().install()
    other = make_user(email="other@example.com")
    used = google_oauth.create_state(owner)
    google_oauth.consume_state(used)
    expired = google_oauth.create_state(owner)
    with session_scope() as s:
        s.get(OAuthState, expired).expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    invalid = (Rejected, "gmail_state_invalid",
               "This Gmail connection request expired or was already used. Try connecting again.")
    for state in (google_oauth.create_state(other), used, expired, "unknown", ""):
        assert _error(lambda: _finish(owner, state=state)) == invalid
    assert google.requests == [] and _rows() == []


def test_the_state_is_used_up_even_when_the_exchange_fails(owner):
    google = FakeGoogle().install()
    google.exchange = google_error(400, "invalid_grant")
    state = google_oauth.create_state(owner)
    assert _error(lambda: _finish(owner, state=state))[1] == "gmail_connect_failed"
    assert _error(lambda: _finish(owner, state=state))[1] == "gmail_state_invalid"


@pytest.mark.parametrize("setup, expected", [
    (lambda g: setattr(g, "exchange", google_error(400, "invalid_grant")),
     (Rejected, "gmail_connect_failed", "That Google approval has expired or was already used. Try connecting again.")),
    (lambda g: setattr(g, "exchange", google_error(401, "invalid_client")),
     (NotConfigured, "gmail_not_configured", "Gmail sending isn't set up correctly on this deployment.")),
    (lambda g: setattr(g, "exchange", httpx.Response(200, json={"refresh_token": "r"})),
     (UpstreamError, "upstream_error", "Google returned an incomplete response. Try connecting again.")),
    (lambda g: setattr(g, "exchange", httpx.Response(200, json={"access_token": "a", "refresh_token": "r",
                                                                "scope": "openid email"})),
     (Rejected, "gmail_connect_failed",
      "Google didn't give permission to send email. Try again and allow “Send email on your behalf”.")),
    (lambda g: setattr(g, "userinfo", httpx.Response(200, json={})),
     (Rejected, "gmail_connect_failed", "Could not read your email address from Google.")),
    (lambda g: setattr(g, "userinfo", httpx.Response(200, json={"email": "someone.else@example.com"})),
     (Rejected, "gmail_connect_failed", "That Google account doesn't match your signed-in email "
                                        "(owner@example.com). Connect the Gmail account you're logged in with.")),
    (lambda g: setattr(g, "exchange", httpx.Response(503)),
     (UpstreamError, "upstream_error", "Couldn't reach Google. Try connecting again in a minute.")),
    (lambda g: setattr(g, "exchange", httpx.ReadTimeout("slow")),
     (UpstreamTimeout, "upstream_timeout", "Google took too long to respond. Try connecting again.")),
], ids=["invalid-grant", "client", "no-access-token", "scope", "no-email", "mismatch", "google-5xx", "timeout"])
def test_each_connect_failure_has_its_message_and_stores_nothing(owner, setup, expected):
    setup(FakeGoogle().install())
    assert _error(lambda: _finish(owner)) == expected
    assert _rows() == []


@pytest.mark.parametrize("error", ["invalid_request", "invalid_scope"])
def test_another_token_endpoint_refusal_asks_to_connect_again_and_logs_googles_code(owner, caplog, error):
    """Build review M4: Google answered, so not "Couldn't reach Google"; the log names Google's error code."""
    FakeGoogle().install().exchange = google_error(400, error)
    caplog.set_level(logging.INFO, logger="usecases.email")
    assert _error(lambda: _finish(owner)) == (
        UpstreamError, "upstream_error", "Google returned an incomplete response. Try connecting again.")
    assert f"outcome=incomplete_response google_error={error}" in caplog.text
    assert "SECRET-GOOGLE-TEXT" not in caplog.text
    assert _rows() == []


def test_a_blank_code_or_no_config_fails_before_google(owner):
    google = FakeGoogle().install()
    assert _error(lambda: _finish(owner, code="  ")) == (
        Rejected, "gmail_connect_failed", "That Google approval has expired or was already used. Try connecting again.")
    assert _error(lambda: _finish(owner, config=UNCONFIGURED))[1] == "gmail_not_configured"
    assert google.requests == []


def test_no_refresh_token_keeps_an_existing_connection_and_refuses_a_new_one(owner):
    google = FakeGoogle().install()
    google.exchange = httpx.Response(200, json={"access_token": "a"})
    assert _error(lambda: _finish(owner)) == (
        Rejected, "gmail_connect_failed", "Google did not return a refresh token. Remove this app's access at "
                                          "https://myaccount.google.com/permissions and connect again.")
    google_oauth.save_user_token(owner, OWNER, "refresh-kept")
    assert _finish(owner) == email.GmailStatus(True, True, OWNER)
    assert _rows() == [(owner, OWNER, "refresh-kept")]


def test_no_refresh_token_keeps_an_existing_connection_only_for_the_same_google_address(owner, caplog):
    """Build review M1: a stored connection for another Google address is not this
    grant's, so with no refresh token the connect is refused (the row is left as it was)."""
    google = FakeGoogle().install()
    google.exchange = httpx.Response(200, json={"access_token": "a"})
    google_oauth.save_user_token(owner, "old.account@example.com", "refresh-old")
    caplog.set_level(logging.INFO, logger="usecases.email")
    assert _error(lambda: _finish(owner)) == (
        Rejected, "gmail_connect_failed", "Google did not return a refresh token. Remove this app's access at "
                                          "https://myaccount.google.com/permissions and connect again.")
    assert _rows() == [(owner, "old.account@example.com", "refresh-old")]
    assert "outcome=no_refresh_token" in caplog.text
    google_oauth.save_user_token(owner, "Owner@Example.COM", "refresh-kept")       # the same address, ignoring case
    assert _finish(owner).connected is True
    assert _rows() == [(owner, "Owner@Example.COM", "refresh-kept")]


def test_disconnect_deletes_then_revokes_and_a_failed_revoke_still_disconnects(owner, caplog):
    google = FakeGoogle().install()
    google_oauth.save_user_token(owner, OWNER, REFRESH_TOKEN)
    assert email.disconnect_gmail(owner, CONFIG) == email.GmailStatus(True, False, None)
    assert _rows() == [] and [google.form(r) for r in google.requests] == [{"token": REFRESH_TOKEN}]
    google_oauth.save_user_token(owner, OWNER, "refresh-2")
    google.revoke = httpx.ConnectError("down")
    with caplog.at_level(logging.WARNING):
        assert email.disconnect_gmail(owner, CONFIG).connected is False
    assert _rows() == []
    assert [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING] == [
        f"gmail.disconnect user_id={owner} outcome=revoke_failed"]
    assert email.disconnect_gmail(owner, CONFIG).connected is False         # nothing stored: no revoke
    assert len(google.requests) == 2


def test_the_logs_never_carry_a_code_state_token_or_address(owner, caplog):
    google = FakeGoogle().install()
    state = google_oauth.create_state(owner)
    with caplog.at_level(logging.DEBUG):
        _finish(owner, state=state)
        google.exchange = google_error(401, "invalid_client")
        with pytest.raises(NotConfigured):
            _finish(owner)
        email.disconnect_gmail(owner, CONFIG)
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert "google_error=invalid_client" in text
    for secret in ("auth-code", state, REFRESH_TOKEN, OWNER, "secret-456", "SECRET-GOOGLE-TEXT"):
        assert secret not in text


# --- Task 12: emailing the bulletin ----------------------------------------------------------------

SUNDAY = date(2026, 10, 4)
FIXED_DOCX = documents.DocumentResult(b"FIXED-DOCX", "worship_October_04_2026.docx")
FIXED_PDF = documents.DocumentResult(b"%PDF-FIXED", "printed_bulletin_October_04_2026.pdf")
SECRET_MESSAGE = "A private note for the organist."


@pytest.fixture
def world(owner, make_user, make_church, monkeypatch):
    """Grace with a member who sends (connected), two contacts, Google faked and
    the files fixed (python-docx output is not byte-reproducible)."""
    member = make_user(email="member@example.com")
    church = make_church(name="Grace", owner_user_id=owner)
    add_membership(member, church, "member")
    mary = email_contacts.add_contact(church, name="Mary", email="mary@example.org")["id"]
    office = email_contacts.add_contact(church, name="", email=" Office@Example.ORG ")["id"]
    google_oauth.save_user_token(member, "member@example.com", REFRESH_TOKEN)
    built = []
    monkeypatch.setattr(documents, "build_document", lambda *args: built.append(("docx", args)) or FIXED_DOCX)
    monkeypatch.setattr(documents, "build_printed",
                        lambda *args, charge: built.append(("pdf", args)) or charge(2) or FIXED_PDF)
    return {"church": church, "member": member, "mary": mary, "office": office, "built": built,
            "google": FakeGoogle(email="member@example.com").install(), "charged": [], "scripture": []}


def _send(world, contact_ids=(), extra=(), message=None, attachments=("docx",), config=CONFIG,
          data=None, user=None):
    return email.send_bulletin_email(
        world["church"], user or world["member"], data or archive.ServiceInput(service_date=SUNDAY),
        contact_ids=[uuid.UUID(c) if isinstance(c, str) else c for c in contact_ids], additional_emails=list(extra),
        message=message, attachments=list(attachments), translation="nrsvue", config=config,
        charge=lambda: world["charged"].append(1), charge_scripture=lambda parts: world["scripture"].append(parts))


def test_a_member_emails_the_bulletin_with_both_files_in_bcc(world):
    count = _send(world, [world["office"], world["mary"]], [" organist@example.org", "MARY@example.org"],
                  "  See you Sunday.  ", ("pdf", "docx"))
    assert count == 3
    (sent,) = world["google"].sent()
    assert (sent["From"], sent["To"]) == ("member@example.com", "member@example.com")
    assert sent["Bcc"] == "Office@example.org, mary@example.org, organist@example.org"
    assert sent["Subject"] == "Worship service for October 4, 2026"
    assert sent.get_body(preferencelist=("plain",)).get_content() == "See you Sunday.\n"
    assert [(p.get_filename(), p.get_content()) for p in sent.iter_attachments()] == [
        ("worship_October_04_2026.docx", b"FIXED-DOCX"), ("printed_bulletin_October_04_2026.pdf", b"%PDF-FIXED")]
    data = archive.ServiceInput(service_date=SUNDAY)
    assert world["built"] == [("docx", (world["church"], data, "bulletin")),
                              ("pdf", (world["church"], data, "pdf", "nrsvue"))]
    assert (world["charged"], world["scripture"]) == ([1], [2])
    refresh = world["google"].calls(google_oauth.TOKEN_URI, "refresh_token")
    assert world["google"].form(refresh[0])["refresh_token"] == REFRESH_TOKEN


def test_the_stored_sender_is_normalized_and_left_out_of_bcc(world):
    """5b-2b build review M3: a stored address with spaces and capitals is sent as normalize_address gives it."""
    google_oauth.save_user_token(world["member"], " Member@Example.COM ", REFRESH_TOKEN)
    assert _send(world, [world["mary"], world["office"]], ["member@EXAMPLE.com"]) == 3
    (sent,) = world["google"].sent()
    assert (sent["From"], sent["To"]) == ("Member@example.com", "Member@example.com")
    assert sent["Bcc"] == "mary@example.org, Office@example.org"


def test_a_malformed_stored_sender_is_not_connected_and_nothing_is_sent(world):
    """5b-2b build review M3."""
    google_oauth.save_user_token(world["member"], "member@example.com, other@example.org", REFRESH_TOKEN)
    with pytest.raises(Conflict) as failed:
        _send(world, [world["mary"]])
    assert (failed.value.code, failed.value.message) == ("gmail_not_connected", "Connect your Gmail first, then try again.")
    assert world["google"].requests == [] and world["built"] == [] and world["charged"] == []


def test_one_recipient_is_in_to_and_the_default_message_fills_a_blank_one(world):
    assert _send(world, [world["mary"]], message="   ") == 1
    (sent,) = world["google"].sent()
    assert (sent["To"], sent["Bcc"]) == ("mary@example.org", None)
    assert sent.get_body(preferencelist=("plain",)).get_content() == "Hi! Here's the worship bulletin for this Sunday.\n"
    assert [p.get_filename() for p in sent.iter_attachments()] == ["worship_October_04_2026.docx"]
    assert world["scripture"] == []                                     # no PDF: no readings fetched


@pytest.mark.parametrize("call, expected", [
    (lambda w: _send(w), (InvalidInput, "invalid_request",
                          "Please select at least one recipient or enter an email address.", "recipients")),
    (lambda w: _send(w, extra=[f"p{i}@example.org" for i in range(51)] + ["P0@example.org"] * 9),
     (InvalidInput, "invalid_request", "You can email at most 50 people at once.", "recipients")),
    (lambda w: _send(w, extra=["mary@example.org", "not an address, really, it is far too long to show"]),
     (InvalidInput, "invalid_request", "“not an address, really, it is far too long to show” isn't a valid email "
                                       "address.", "additional_emails")),
    (lambda w: _send(w, [uuid.uuid4()]),
     (NotFound, "not_found", "One of the selected contacts no longer exists. Refresh the list and try again.", None)),
    (lambda w: _send(w, [w["mary"]], attachments=()),
     (InvalidInput, "invalid_request", "Choose at least one attachment.", "attachments")),
], ids=["none", "51-after-dedupe", "bad-extra", "unknown-contact", "no-attachment"])
def test_recipient_and_attachment_errors_come_first_and_send_nothing(world, call, expected):
    with pytest.raises(DomainError) as failed:
        call(world)
    assert (type(failed.value), failed.value.code, failed.value.message, failed.value.field) == expected
    assert world["google"].requests == [] and world["built"] == [] and world["charged"] == []


def test_an_extra_address_is_shown_cut_to_60_characters(world):
    with pytest.raises(InvalidInput) as failed:
        _send(world, extra=["x" * 70])
    assert failed.value.message == f"“{'x' * 60}” isn't a valid email address."


def test_another_churchs_contact_is_not_found(world, make_church):
    other = make_church(name="Other", owner_user_id=world["member"])
    theirs = email_contacts.add_contact(other, name="Theirs", email="theirs@example.org")["id"]
    with pytest.raises(NotFound) as failed:
        _send(world, [world["mary"], theirs])
    assert failed.value.details == {"field": "contact_ids"}
    assert world["google"].requests == []


def test_a_saved_contact_the_rule_refuses_is_named_with_the_hint(world):
    two = email_contacts.add_contact(world["church"], name="", email="a@example.org, b@example.org")["id"]
    named = email_contacts.add_contact(world["church"], name="Two at once", email="c@example.org; d@example.org")["id"]
    for contact, label in ((two, "a@example.org, b@example.org"), (named, "Two at once")):
        with pytest.raises(InvalidInput) as failed:
            _send(world, [contact])
        assert (failed.value.field, failed.value.message) == (
            "contact_ids", f"The saved contact “{label}” has an invalid email address. "
                           "An admin can fix it in Settings → Contacts.")
    assert email.MALFORMED_CONTACT_HINT == "An admin can fix it in Settings → Contacts."


def test_not_configured_and_not_connected_come_after_the_recipients(world, make_user):
    with pytest.raises(InvalidInput):
        _send(world, config=UNCONFIGURED)                         # no recipients: that is said first
    with pytest.raises(NotConfigured) as failed:
        _send(world, [world["mary"]], config=UNCONFIGURED)
    assert failed.value.code == "gmail_not_configured"
    stranger = make_user(email="nogmail@example.com")
    no_address = make_user(email="noaddress@example.com")
    with session_scope() as s:
        s.add(GmailToken(user_id=no_address, google_email=None, refresh_token="r"))     # counts as not connected
    for user in (stranger, no_address):
        with pytest.raises(Conflict) as failed:
            _send(world, [world["mary"]], user=user)
        assert (failed.value.code, failed.value.message) == ("gmail_not_connected",
                                                             "Connect your Gmail first, then try again.")
    assert world["google"].requests == [] and world["charged"] == []


def test_the_services_own_errors_propagate_and_nothing_is_charged_or_sent(world, monkeypatch):
    monkeypatch.undo()                                             # the real build_document again
    hymn = archive.ServiceInput(service_date=SUNDAY, hymns={"response": HymnRefData(uuid.uuid4(), "Gone", 1, None)})
    with pytest.raises(NotFound) as failed:
        _send(world, [world["mary"]], data=hymn)
    assert (failed.value.message, failed.value.details) == (
        "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step.",
        {"field": "hymns.response.hymn_id"})
    label = archive.ServiceInput(service_date=SUNDAY, custom_elements=(CustomElement("  ", "Text", "sermon"),))
    with pytest.raises(InvalidInput) as failed:
        _send(world, [world["mary"]], data=label)
    assert failed.value.field == "custom_elements.0.label"
    assert world["google"].requests == [] and world["charged"] == []


def test_a_real_bulletin_copy_is_the_same_document_as_the_download(world, monkeypatch):
    monkeypatch.undo()
    data = archive.ServiceInput(service_date=SUNDAY, occasion="World Communion Sunday", sermon_title="Living Water")
    _send(world, [world["mary"]], data=data, attachments=("docx", "pdf"))
    files = {p.get_filename(): p.get_content() for p in world["google"].sent()[0].iter_attachments()}
    direct = documents.build_document(world["church"], data, "bulletin").content
    with ZipFile(BytesIO(files["worship_October_04_2026.docx"])) as sent, ZipFile(BytesIO(direct)) as built:
        assert sent.read("word/document.xml") == built.read("word/document.xml")
    assert files["printed_bulletin_October_04_2026.pdf"].startswith(b"%PDF")
    with session_scope() as s:
        assert s.query(HymnUsage).count() == 0                     # emailing records no hymn use


def _connected(world) -> bool:
    return google_oauth.get_connection(world["member"]) is not None


@pytest.mark.parametrize("where, answer, expected", [
    ("refresh", google_error(400, "invalid_grant"),
     (UpstreamError, "gmail_send_failed", email.EXPIRED, {"disconnected": True, "send_uncertain": False}, False)),
    ("refresh", google_error(401, "unauthorized_client"),
     (NotConfigured, "gmail_not_configured", "Gmail sending isn't set up correctly on this deployment.", None, True)),
    ("refresh", httpx.Response(503),
     (UpstreamError, "gmail_send_failed", email.GMAIL_UNREACHABLE, {"disconnected": False, "send_uncertain": False},
      True)),
    ("refresh", httpx.Response(200, json={}),
     (UpstreamError, "gmail_send_failed", email.GMAIL_UNREACHABLE, {"disconnected": False, "send_uncertain": False},
      True)),
    ("refresh", httpx.ReadTimeout("slow"),
     (UpstreamTimeout, "upstream_timeout", email.GOOGLE_SLOW_NOTHING_SENT, None, True)),
    ("send", gmail_error(403, "insufficientPermissions"),
     (UpstreamError, "gmail_send_failed", email.NO_SEND_PERMISSION, {"disconnected": True, "send_uncertain": False},
      False)),
    ("send", gmail_error(429, "rateLimitExceeded"),
     (UpstreamError, "gmail_send_failed", email.SEND_LIMIT, {"disconnected": False, "send_uncertain": False}, True)),
    ("send", gmail_error(400, "invalidArgument"),
     (UpstreamError, "gmail_send_failed", email.SEND_REJECTED, {"disconnected": False, "send_uncertain": False}, True)),
    ("send", httpx.ConnectError("down"),
     (UpstreamError, "gmail_send_failed", email.GMAIL_UNREACHABLE, {"disconnected": False, "send_uncertain": False},
      True)),
    ("send", httpx.Response(503),
     (UpstreamError, "gmail_send_failed", email.MAYBE_SENT_PROBLEM, {"disconnected": False, "send_uncertain": True},
      True)),
    ("send", httpx.ReadTimeout("slow"),
     (UpstreamTimeout, "upstream_timeout", email.MAYBE_SENT_UNCONFIRMED, {"send_uncertain": True}, True)),
], ids=["refresh-invalid-grant", "refresh-client", "refresh-5xx", "refresh-no-token", "refresh-timeout",
        "send-scope", "send-limit", "send-4xx", "send-connect", "send-5xx", "send-read-timeout"])
def test_google_failures_map_to_their_message_and_keep_or_forget_the_connection(world, where, answer, expected):
    setattr(world["google"], where, answer)
    with pytest.raises(DomainError) as failed:
        _send(world, [world["mary"]])
    error = failed.value
    assert (type(error), error.code, error.message, error.details, _connected(world)) == expected
    assert world["charged"] == [1]


def test_gmail_refusing_the_account_has_its_own_message_and_its_reason_is_logged(world, caplog):
    assert email.ACCOUNT_REFUSED == ("Gmail won't send from this Google account. Nothing was sent. "
                                     "Check that you can send email in Gmail with it, then try again.")
    for answer, status, reason in ((gmail_error(401, "authError"), 401, "authError"),
                                   (gmail_error(400, "failedPrecondition", "FAILED_PRECONDITION"), 400,
                                    "failedPrecondition")):
        world["google"].send = answer
        with caplog.at_level(logging.INFO), pytest.raises(UpstreamError) as failed:
            _send(world, [world["mary"]])
        assert (failed.value.code, failed.value.message, failed.value.details) == (
            "gmail_send_failed", email.ACCOUNT_REFUSED, {"disconnected": False, "send_uncertain": False})
        assert f"outcome=account_refused status={status} google_error={reason}" in caplog.text
    assert _connected(world) and "SECRET-GOOGLE-TEXT" not in caplog.text


def test_a_message_too_large_for_gmail_is_refused_before_the_limit_and_google(world, monkeypatch):
    assert email.MAX_RAW_BYTES == 3_500_000
    monkeypatch.setattr(email, "MAX_RAW_BYTES", 100)
    with pytest.raises(InvalidInput) as failed:
        _send(world, [world["mary"]], attachments=("docx", "pdf"))
    assert (failed.value.field, failed.value.message) == (
        "attachments", "The attachments are too large to email. Try sending only the bulletin copy.")
    assert world["google"].requests == [] and world["charged"] == []


def test_a_connection_made_again_meanwhile_is_kept(world):
    def reconnect_then_refuse(_request):
        google_oauth.save_user_token(world["member"], "member@example.com", "refresh-new")   # in either app
        return google_error(400, "invalid_grant")

    world["google"].refresh = reconnect_then_refuse
    with pytest.raises(UpstreamError) as failed:
        _send(world, [world["mary"]])
    assert (failed.value.message, failed.value.details) == (
        "Your Gmail connection changed while sending. Nothing was sent. Try again.",
        {"disconnected": False, "send_uncertain": False})
    assert google_oauth.get_connection(world["member"]).refresh_token == "refresh-new"


@pytest.mark.parametrize("answer", [google_error(400, "invalid_grant"),
                                    gmail_error(403, "insufficientPermissions", "PERMISSION_DENIED")])
def test_a_connection_removed_meanwhile_offers_reconnect(world, answer):
    """5b-2b build review M4: a Disconnect during the send leaves no row; that is "removed", not "changed"."""
    def disconnect_then_refuse(_request):
        google_oauth.delete_connection(world["member"])
        return answer

    if answer.status_code == 400:
        world["google"].refresh = disconnect_then_refuse
    else:
        world["google"].send = disconnect_then_refuse
    with pytest.raises(UpstreamError) as failed:
        _send(world, [world["mary"]])
    assert (failed.value.code, failed.value.message, failed.value.details) == (
        "gmail_send_failed", email.EXPIRED, {"disconnected": True, "send_uncertain": False})
    assert google_oauth.get_connection(world["member"]) is None


def test_the_rate_limit_is_charged_once_after_the_files_and_before_google(world):
    order = []
    world["google"].refresh = lambda request: order.append("refresh") or httpx.Response(200, json={"access_token": "a"})
    email.send_bulletin_email(world["church"], world["member"], archive.ServiceInput(service_date=SUNDAY),
                              contact_ids=[uuid.UUID(world["mary"])], additional_emails=[], message=None,
                              attachments=["docx"], translation=None, config=CONFIG,
                              charge=lambda: order.append(("charge", len(world["built"]))))
    assert order == [("charge", 1), "refresh"]


def test_a_caller_at_the_rate_limit_is_refused_before_the_files_are_built(world):
    """5b-2b build review M2: no PDF, no readings charge, nothing sent; the limit is peeked, not charged."""
    def at_limit():
        raise RateLimited("Too many requests. Try again in 60 seconds.", retry_after_seconds=60)
    with pytest.raises(RateLimited):
        email.send_bulletin_email(world["church"], world["member"], archive.ServiceInput(service_date=SUNDAY),
                                  contact_ids=[uuid.UUID(world["mary"])], additional_emails=[], message=None,
                                  attachments=["docx", "pdf"], translation=None, config=CONFIG,
                                  charge=lambda: world["charged"].append(1),
                                  charge_scripture=lambda parts: world["scripture"].append(parts),
                                  check_charge=at_limit)
    assert (world["built"], world["scripture"], world["charged"], world["google"].requests) == ([], [], [], [])
    order = []
    _send(world, [world["mary"]])
    email.send_bulletin_email(world["church"], world["member"], archive.ServiceInput(service_date=SUNDAY),
                              contact_ids=[uuid.UUID(world["mary"])], additional_emails=[], message=None,
                              attachments=["docx"], translation=None, config=CONFIG,
                              charge=lambda: order.append("charge"),
                              check_charge=lambda: order.append(("check", len(world["built"]))))
    assert order == [("check", 1), "charge"]                     # checked before this send's file, charged after


def test_no_pooled_connection_is_held_while_google_is_called(world, tmp_db):
    out = []
    event.listen(tmp_db.pool, "checkout", lambda *a: out.append(1))
    event.listen(tmp_db.pool, "checkin", lambda *a: out.pop())

    def check(answer):
        def handler(_request):
            assert out == [], "a database connection was checked out during a Google call"
            return answer
        return handler

    world["google"].refresh = check(httpx.Response(200, json={"access_token": "a"}))
    world["google"].send = check(httpx.Response(200, json={"id": "m"}))
    assert _send(world, [world["mary"]]) == 1


def test_the_logs_carry_no_address_subject_message_or_token(world, caplog):
    with caplog.at_level(logging.DEBUG):
        _send(world, [world["mary"]], ["organist@example.org"], SECRET_MESSAGE)
        world["google"].send = httpx.Response(503)
        with pytest.raises(UpstreamError):
            _send(world, [world["office"]], message=SECRET_MESSAGE)
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert f"bulletin_email.sent church_id={world['church']} user_id={world['member']} recipients=2 bcc=True" in text
    for secret in ("mary@example.org", "organist@example.org", "ffice@example", "member@example.com",
                   "Worship service", SECRET_MESSAGE, REFRESH_TOKEN, "access-token"):
        assert secret not in text, secret
