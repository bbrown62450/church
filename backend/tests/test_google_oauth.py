"""google_oauth (slice 5b spec, Testing "test_google_oauth.py"; slice 5b-2):
the config, the consent URL, the single-use states and the token store; Task
3 adds the Google calls. It replaces test_oauth_state.py, test_gmail_exchange.py
and test_gmail_token_store.py: every assertion they made about code that is
kept is ported here; the Streamlit-only functions went with their tests."""
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

import pytest

import google_oauth
from db import session_scope
from db.models import GmailToken, OAuthState

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
