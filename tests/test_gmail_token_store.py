import uuid

import pytest

import google_oauth
from db import session_scope
from db.models import GmailToken


class _FakeResp:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self._payload = payload or {}
        self.text = ""

    def json(self):
        return self._payload


def test_save_and_is_connected(tmp_db, make_user):
    uid = make_user(email="a@example.com")
    assert google_oauth.is_connected(uid) is False
    google_oauth.save_user_token(uid, "a@example.com", "refresh-abc")
    assert google_oauth.is_connected(uid) is True
    with session_scope() as s:
        row = s.get(GmailToken, uid)
        assert row.refresh_token == "refresh-abc"
        assert row.google_email == "a@example.com"


def test_save_replaces_single_row(tmp_db, make_user):
    uid = make_user(email="a@example.com")
    google_oauth.save_user_token(uid, "a@example.com", "refresh-1")
    google_oauth.save_user_token(uid, "a@example.com", "refresh-2")
    with session_scope() as s:
        rows = s.query(GmailToken).filter(GmailToken.user_id == uid).all()
        assert len(rows) == 1
        assert rows[0].refresh_token == "refresh-2"


def test_disconnect(tmp_db, make_user):
    uid = make_user(email="a@example.com")
    google_oauth.save_user_token(uid, "a@example.com", "refresh-abc")
    google_oauth.disconnect(uid)
    assert google_oauth.is_connected(uid) is False


def test_access_token_for_unconnected_raises(tmp_db, make_user):
    uid = make_user(email="a@example.com")
    with pytest.raises(RuntimeError):
        google_oauth._access_token_for(uid)


def test_access_token_for_returns_fresh_token(tmp_db, make_user, monkeypatch):
    uid = make_user(email="a@example.com")
    google_oauth.save_user_token(uid, "a@example.com", "refresh-abc")
    monkeypatch.setattr(
        google_oauth.requests, "post",
        lambda *a, **k: _FakeResp(200, {"access_token": "fresh-xyz"}),
    )
    assert google_oauth._access_token_for(uid) == "fresh-xyz"


def test_access_token_for_revoked_grant_disconnects(tmp_db, make_user, monkeypatch):
    uid = make_user(email="a@example.com")
    google_oauth.save_user_token(uid, "a@example.com", "refresh-abc")
    monkeypatch.setattr(
        google_oauth.requests, "post",
        lambda *a, **k: _FakeResp(400, {"error": "invalid_grant"}),
    )
    with pytest.raises(RuntimeError):
        google_oauth._access_token_for(uid)
    assert google_oauth.is_connected(uid) is False   # revoked grant is dropped
