from datetime import datetime, timedelta, timezone

import pytest

import google_oauth
from db import session_scope
from db.models import OAuthState


def test_create_state_persists_row(tmp_db, make_user):
    uid = make_user(email="a@example.com")
    state = google_oauth.create_state(uid)
    assert isinstance(state, str) and len(state) >= 20
    with session_scope() as s:
        row = s.get(OAuthState, state)
        assert row is not None
        assert row.user_id == uid


def test_consume_state_is_single_use(tmp_db, make_user):
    uid = make_user(email="a@example.com")
    state = google_oauth.create_state(uid)
    assert google_oauth.consume_state(state) == uid
    assert google_oauth.consume_state(state) is None      # already consumed
    with session_scope() as s:
        assert s.get(OAuthState, state) is None            # row deleted


def test_consume_unknown_or_empty_state_returns_none(tmp_db):
    assert google_oauth.consume_state("nope") is None
    assert google_oauth.consume_state("") is None


def test_consume_expired_state_returns_none_and_deletes(tmp_db, make_user):
    uid = make_user(email="a@example.com")
    state = google_oauth.create_state(uid)
    with session_scope() as s:
        s.get(OAuthState, state).expires_at = (
            datetime.now(timezone.utc) - timedelta(minutes=1)
        )
    assert google_oauth.consume_state(state) is None
    with session_scope() as s:
        assert s.get(OAuthState, state) is None            # consumed even if expired


@pytest.mark.parametrize(
    "params,is_logged_in,expected",
    [
        ({"code": "abc", "state": "s1"}, True, True),
        ({"code": "abc"}, True, False),                      # no state -> not ours
        ({"state": "s1"}, True, False),                      # no code
        ({"code": "abc", "state": "s1"}, False, False),      # not logged in
        ({}, True, False),
    ],
)
def test_should_handle_gmail_callback(params, is_logged_in, expected):
    assert google_oauth.should_handle_gmail_callback(params, is_logged_in) is expected


def test_build_auth_url_uses_bare_root_and_state(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")
    monkeypatch.setenv("GOOGLE_OAUTH_REDIRECT_URI", "https://app.example/")
    url = google_oauth.build_auth_url("state-token-123")
    # Bare app-root redirect (exactly what gets registered in the Google console) —
    # no query-string marker that would break Google's exact-match rule.
    assert "redirect_uri=https%3A%2F%2Fapp.example%2F&" in url
    assert "gmail_oauth" not in url
    assert "state=state-token-123" in url
