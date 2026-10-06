"""usecases.email (slice 5b spec, Testing "test_usecase_email.py"; slice 5b-2):
the Gmail connection (status, start, finish, disconnect) against
tests.fake_google; Task 12 adds the bulletin send. No network."""
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

import google_oauth
from db import session_scope
from db.models import GmailToken, OAuthState
from domain_errors import NotConfigured, Rejected, UpstreamError, UpstreamTimeout
from tests.fake_google import REFRESH_TOKEN, FakeGoogle, google_error
from usecases import email

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
