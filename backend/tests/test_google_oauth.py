"""google_oauth (slice 5b spec, Testing "test_google_oauth.py"; slice 5b-2):
the config, the consent URL, the single-use states and the token store; Task
3 adds the Google calls. It replaces test_oauth_state.py, test_gmail_exchange.py
and test_gmail_token_store.py: every assertion they made about code that is
kept is ported here; the Streamlit-only functions went with their tests."""
import json
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

import google_oauth
from db import session_scope
from db.models import GmailToken, OAuthState
from tests.fake_google import ACCESS_TOKEN, FRESH_ACCESS_TOKEN, REFRESH_TOKEN, FakeGoogle, gmail_error, google_error

CONFIG = google_oauth.GoogleOAuthConfig(
    client_id="client-123", client_secret="secret-456", redirect_uri="https://app.example.org/gmail/callback")


def test_scopes_unchanged():
    assert google_oauth.SCOPES == [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/gmail.send",
    ]
    assert google_oauth.GMAIL_SEND_SCOPE in google_oauth.SCOPES


def test_the_config_is_configured_only_with_all_three_values():
    assert CONFIG.configured
    for blank in ("client_id", "client_secret", "redirect_uri"):
        values = {"client_id": "a", "client_secret": "b", "redirect_uri": "https://c.example.org/gmail/callback"}
        values[blank] = ""
        assert not google_oauth.GoogleOAuthConfig(**values).configured, blank


def test_the_consent_url_asks_for_offline_access_with_the_state_and_the_signed_in_account():
    url = google_oauth.build_auth_url(CONFIG, "state-token-123", login_hint="owner@example.com")
    parts = urlsplit(url)
    assert f"{parts.scheme}://{parts.netloc}{parts.path}" == google_oauth.AUTH_URI
    assert {key: values[0] for key, values in parse_qs(parts.query).items()} == {
        "client_id": "client-123",
        "redirect_uri": "https://app.example.org/gmail/callback",
        "response_type": "code",
        "scope": " ".join(google_oauth.SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": "state-token-123",
        "login_hint": "owner@example.com",
    }
    assert "gmail_oauth" not in url
    assert "login_hint" not in google_oauth.build_auth_url(CONFIG, "s")


def test_create_state_persists_a_row_bound_to_the_user_for_ten_minutes(tmp_db, make_user):
    uid = make_user(email="a@example.com")
    before = datetime.now(timezone.utc)
    state = google_oauth.create_state(uid)
    assert isinstance(state, str) and len(state) >= 20
    with session_scope() as s:
        row = s.get(OAuthState, state)
        assert row.user_id == uid
        expires_at = row.expires_at.replace(tzinfo=timezone.utc) if row.expires_at.tzinfo is None else row.expires_at
    assert before + timedelta(minutes=10) <= expires_at <= datetime.now(timezone.utc) + timedelta(minutes=10)


def test_create_state_purges_only_expired_states(tmp_db, make_user):
    me, other = make_user(email="a@example.com"), make_user(email="b@example.com")
    old = google_oauth.create_state(me)
    live = google_oauth.create_state(other)                 # another user's, still valid
    with session_scope() as s:
        s.get(OAuthState, old).expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    google_oauth.create_state(me)
    with session_scope() as s:
        assert s.get(OAuthState, old) is None
        assert s.get(OAuthState, live) is not None


def test_consume_state_is_single_use(tmp_db, make_user):
    uid = make_user(email="a@example.com")
    state = google_oauth.create_state(uid)
    assert google_oauth.consume_state(state) == uid
    assert google_oauth.consume_state(state) is None        # already consumed
    with session_scope() as s:
        assert s.get(OAuthState, state) is None


def test_two_consumes_racing_for_one_state_let_only_one_through(tmp_db, make_user, monkeypatch):
    """A second consume slips in while the first is inside its transaction: after the
    first reads the row, or just before it deletes it (build review I1). The user id
    must come back once, from whichever delete removed the row."""
    uid = make_user(email="a@example.com")
    state = google_oauth.create_state(uid)
    real_scope = google_oauth.session_scope
    second = []

    @contextmanager
    def racing_scope():
        with real_scope() as session:
            if getattr(racing_scope, "entered", False):
                yield session                                  # the second consume runs plainly
                return
            racing_scope.entered = True
            real_get, real_execute = session.get, session.execute

            def slip_in():
                if not second:
                    second.append(google_oauth.consume_state(state))

            def get(*args, **kwargs):
                row = real_get(*args, **kwargs)
                slip_in()
                return row

            def execute(statement, *args, **kwargs):
                if getattr(statement, "is_delete", False):      # not the SELECT inside session.get
                    slip_in()
                return real_execute(statement, *args, **kwargs)

            session.get, session.execute = get, execute
            yield session

    monkeypatch.setattr(google_oauth, "session_scope", racing_scope)
    first = google_oauth.consume_state(state)
    assert second, "the second consume never ran"
    assert [first, second[0]].count(uid) == 1, (first, second[0])
    assert None in (first, second[0])


def test_consume_unknown_or_empty_state_returns_none(tmp_db):
    assert google_oauth.consume_state("nope") is None
    assert google_oauth.consume_state("") is None


def test_consume_expired_state_returns_none_and_deletes(tmp_db, make_user):
    uid = make_user(email="a@example.com")
    state = google_oauth.create_state(uid)
    with session_scope() as s:
        s.get(OAuthState, state).expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    assert google_oauth.consume_state(state) is None
    with session_scope() as s:
        assert s.get(OAuthState, state) is None              # consumed even when expired


def test_save_user_token_keeps_one_row_per_user_and_replaces_it(tmp_db, make_user):
    uid = make_user(email="a@example.com")
    assert google_oauth.get_connection(uid) is None
    google_oauth.save_user_token(uid, "a@example.com", "refresh-1")
    google_oauth.save_user_token(uid, "A@Example.com", "refresh-2")
    with session_scope() as s:
        rows = s.query(GmailToken).filter(GmailToken.user_id == uid).all()
        assert [(r.google_email, r.refresh_token) for r in rows] == [("A@Example.com", "refresh-2")]
    assert google_oauth.get_connection(uid) == google_oauth.GmailConnection("A@Example.com", "refresh-2")


def test_a_row_without_an_address_is_not_a_connection(tmp_db, make_user):
    uid = make_user(email="a@example.com")
    with session_scope() as s:
        s.add(GmailToken(user_id=uid, google_email=None, refresh_token="refresh-1"))
    assert google_oauth.get_connection(uid) is None
    google_oauth.save_user_token(uid, "  ", "refresh-2")
    assert google_oauth.get_connection(uid) is None


def test_delete_connection_returns_the_token_and_only_if_token_keeps_a_newer_one(tmp_db, make_user):
    uid = make_user(email="a@example.com")
    assert google_oauth.delete_connection(uid) is None
    google_oauth.save_user_token(uid, "a@example.com", "refresh-old")
    google_oauth.save_user_token(uid, "a@example.com", "refresh-new")     # connected again meanwhile
    assert google_oauth.delete_connection(uid, only_if_token="refresh-old") is None
    assert google_oauth.get_connection(uid).refresh_token == "refresh-new"
    assert google_oauth.delete_connection(uid, only_if_token="refresh-new") == "refresh-new"
    assert google_oauth.get_connection(uid) is None
    google_oauth.save_user_token(uid, "a@example.com", "refresh-3")
    assert google_oauth.delete_connection(uid) == "refresh-3"


def test_the_store_joins_the_callers_session(tmp_db, make_user):
    uid = make_user(email="a@example.com")
    with session_scope() as s:
        state = google_oauth.create_state(uid, session=s)
        google_oauth.save_user_token(uid, "a@example.com", "refresh-1", session=s)
        assert google_oauth.get_connection(uid, session=s).refresh_token == "refresh-1"
        assert google_oauth.delete_connection(uid, session=s) == "refresh-1"
        assert s.get(OAuthState, state) is not None
    assert google_oauth.get_connection(uid) is None


def test_the_streamlit_functions_are_gone():
    for name in ("should_handle_gmail_callback", "send_email", "disconnect", "is_configured", "is_connected",
                 "_fetch_email", "_access_token_for", "_user_email", "_client_id", "_google_error"):
        assert not hasattr(google_oauth, name), name
    source = open(google_oauth.__file__, encoding="utf-8").read()
    assert "os.getenv" not in source and "import requests" not in source and "os.environ" not in source


# --- Task 3: the Google calls, against tests.fake_google (no network) -----------------------------

Kind = google_oauth.GoogleErrorKind


def _kind(call) -> google_oauth.GoogleErrorKind:
    with pytest.raises(google_oauth.GoogleOAuthError) as failed:
        call()
    return failed.value.kind


def _exchange(email="owner@example.com"):
    return google_oauth.exchange_code(CONFIG, "auth-code", expected_email=email)


def test_exchange_code_returns_the_grant_with_googles_spelling_and_stores_nothing(tmp_db):
    google = FakeGoogle(email="Owner@Example.com").install()
    grant = _exchange("owner@example.com")
    assert grant == google_oauth.GmailGrant("Owner@Example.com", REFRESH_TOKEN, frozenset(google_oauth.SCOPES))
    token_request, userinfo_request = google.requests
    assert google.form(token_request) == {"code": "auth-code", "client_id": "client-123", "client_secret": "secret-456",
                                          "redirect_uri": "https://app.example.org/gmail/callback",
                                          "grant_type": "authorization_code"}
    assert token_request.extensions["timeout"]["read"] == 15.0
    assert userinfo_request.headers["Authorization"] == f"Bearer {ACCESS_TOKEN}"
    assert userinfo_request.extensions["timeout"] == {"connect": 5.0, "read": 15.0, "write": 15.0, "pool": 15.0}
    with session_scope() as s:
        assert s.query(GmailToken).count() == 0


def test_exchange_code_without_a_refresh_token_or_a_scope_field(tmp_db):
    google = FakeGoogle().install()
    google.exchange = httpx.Response(200, json={"access_token": ACCESS_TOKEN})       # no scope: as requested
    assert _exchange() == google_oauth.GmailGrant("owner@example.com", None, frozenset(google_oauth.SCOPES))


@pytest.mark.parametrize("answer, kind", [
    (google_error(400, "invalid_grant"), Kind.INVALID_GRANT),
    (google_error(401, "invalid_client"), Kind.CLIENT_MISCONFIGURED),
    (google_error(400, "redirect_uri_mismatch"), Kind.CLIENT_MISCONFIGURED),
    (google_error(400, "invalid_request"), Kind.UPSTREAM),
    (httpx.Response(500, text="oops"), Kind.UPSTREAM),
    (httpx.ReadTimeout("slow"), Kind.TIMEOUT),
    (httpx.ConnectError("down"), Kind.UPSTREAM),
    (httpx.Response(200, json={"refresh_token": REFRESH_TOKEN}), Kind.INCOMPLETE_RESPONSE),
    (httpx.Response(200, text="not json"), Kind.INCOMPLETE_RESPONSE),
    (httpx.Response(200, json={"access_token": ACCESS_TOKEN, "scope": "openid email"}), Kind.SCOPE_MISSING),
    (httpx.Response(200, json={"access_token": ACCESS_TOKEN, "scope": ["openid"]}), Kind.INCOMPLETE_RESPONSE),
])
def test_exchange_code_failures(tmp_db, answer, kind):
    google = FakeGoogle().install()
    google.exchange = answer
    assert _kind(_exchange) == kind


@pytest.mark.parametrize("answer, kind", [
    (httpx.Response(401, json={"error": {"code": 401}}), Kind.NO_EMAIL),
    (httpx.Response(200, json={"verified_email": False}), Kind.NO_EMAIL),
    (httpx.Response(503, text="later"), Kind.UPSTREAM),
    (httpx.ReadTimeout("slow"), Kind.TIMEOUT),
])
def test_exchange_code_userinfo_failures(tmp_db, answer, kind):
    google = FakeGoogle().install()
    google.userinfo = answer
    assert _kind(_exchange) == kind


def test_exchange_code_refuses_another_google_account(tmp_db):
    FakeGoogle(email="attacker@example.com").install()
    assert _kind(_exchange) == Kind.EMAIL_MISMATCH


def test_exchange_code_opens_no_database_session(tmp_db, monkeypatch):
    FakeGoogle().install()
    monkeypatch.setattr(google_oauth, "session_scope", lambda: pytest.fail("exchange_code opened a session"))
    assert _exchange().google_email == "owner@example.com"


def test_refresh_access_token(tmp_db):
    google = FakeGoogle().install()
    assert google_oauth.refresh_access_token(CONFIG, REFRESH_TOKEN) == FRESH_ACCESS_TOKEN
    assert google.form(google.requests[0]) == {"client_id": "client-123", "client_secret": "secret-456",
                                               "refresh_token": REFRESH_TOKEN, "grant_type": "refresh_token"}
    for answer, kind in ((google_error(400, "invalid_grant"), Kind.INVALID_GRANT),
                         (google_error(401, "unauthorized_client"), Kind.CLIENT_MISCONFIGURED),
                         (httpx.Response(502), Kind.UPSTREAM),
                         (httpx.Response(200, json={}), Kind.INCOMPLETE_RESPONSE),
                         (httpx.ReadTimeout("slow"), Kind.TIMEOUT),
                         (httpx.ConnectTimeout("slow"), Kind.TIMEOUT)):
        google.refresh = answer
        assert _kind(lambda: google_oauth.refresh_access_token(CONFIG, REFRESH_TOKEN)) == kind, answer


def test_send_raw_message_posts_the_message_with_the_access_token():
    google = FakeGoogle().install()
    google_oauth.send_raw_message(FRESH_ACCESS_TOKEN, b"From: a@example.org\r\nTo: b@example.org\r\n\r\nHi\r\n")
    (request,) = google.requests
    assert request.headers["Authorization"] == f"Bearer {FRESH_ACCESS_TOKEN}"
    assert request.extensions["timeout"] == {"connect": 5.0, "read": 30.0, "write": 30.0, "pool": 30.0}
    assert google.sent()[0]["To"] == "b@example.org"


@pytest.mark.parametrize("answer, kind, status", [
    (gmail_error(403, "insufficientPermissions"), Kind.INSUFFICIENT_SCOPE, 403),
    (httpx.Response(403, json={"error": {"code": 403, "status": "PERMISSION_DENIED",
                                         "details": [{"reason": "ACCESS_TOKEN_SCOPE_INSUFFICIENT"}]}}),
     Kind.INSUFFICIENT_SCOPE, 403),
    (gmail_error(429, "rateLimitExceeded"), Kind.SEND_LIMIT, 429),
    (gmail_error(403, "dailyLimitExceeded"), Kind.SEND_LIMIT, 403),
    (gmail_error(400, "invalidArgument"), Kind.SEND_REJECTED, 400),
    (gmail_error(401, "authError"), Kind.ACCOUNT_REFUSED, 401),
    (gmail_error(400, "failedPrecondition", "FAILED_PRECONDITION"), Kind.ACCOUNT_REFUSED, 400),
    (httpx.ConnectError("down"), Kind.UPSTREAM, None),
    (httpx.ConnectTimeout("slow"), Kind.UPSTREAM, None),
    (httpx.PoolTimeout("busy"), Kind.UPSTREAM, None),
    (httpx.Response(503, text="later"), Kind.SEND_UNCONFIRMED, 503),
    (httpx.ReadTimeout("slow"), Kind.SEND_UNCONFIRMED, None),
    (httpx.WriteTimeout("slow"), Kind.SEND_UNCONFIRMED, None),
    (httpx.ReadError("reset"), Kind.SEND_UNCONFIRMED, None),
    (httpx.RemoteProtocolError("closed"), Kind.SEND_UNCONFIRMED, None),
])
def test_send_raw_message_failures(answer, kind, status):
    google = FakeGoogle().install()
    google.send = answer
    with pytest.raises(google_oauth.GoogleOAuthError) as failed:
        google_oauth.send_raw_message(FRESH_ACCESS_TOKEN, b"Subject: x\r\n\r\nx\r\n")
    assert (failed.value.kind, failed.value.status) == (kind, status)
    assert "SECRET-GOOGLE-TEXT" not in str(failed.value)
    if isinstance(answer, httpx.Response) and answer.headers["Content-Type"] == "application/json":
        error = json.loads(answer.content)["error"]
        reasons = [item["reason"] for item in error.get("errors", []) + error.get("details", [])]
        assert failed.value.google_error == reasons[0]                     # logged by the caller: a reason, never text


def test_revoke_token_is_best_effort():
    google = FakeGoogle().install()
    assert google_oauth.revoke_token(REFRESH_TOKEN) is True
    assert google.form(google.requests[0]) == {"token": REFRESH_TOKEN}
    assert google.requests[0].extensions["timeout"]["read"] == 5.0
    for answer in (httpx.Response(400, json={"error": "invalid_token"}), httpx.ReadTimeout("slow"),
                   httpx.ConnectError("down")):
        google.revoke = answer
        assert google_oauth.revoke_token(REFRESH_TOKEN) is False
