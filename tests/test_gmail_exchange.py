import uuid

import pytest

import google_oauth


class _FakeResp:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self._payload = payload or {}
        self.text = ""

    def json(self):
        return self._payload


def test_scopes_unchanged():
    assert google_oauth.SCOPES == [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/gmail.send",
    ]


def test_exchange_code_rejects_email_mismatch(tmp_db, make_user, monkeypatch):
    uid = make_user(email="owner@example.com")
    monkeypatch.setattr(
        google_oauth.requests, "post",
        lambda *a, **k: _FakeResp(200, {"access_token": "at", "refresh_token": "rt"}),
    )
    # Google says the authorizing account is someone else -> must be rejected.
    monkeypatch.setattr(google_oauth, "_fetch_email", lambda token: "attacker@example.com")
    with pytest.raises(RuntimeError):
        google_oauth.exchange_code("auth-code", expected_user_id=uid)
    assert google_oauth.is_connected(uid) is False        # nothing saved on mismatch


def test_exchange_code_saves_on_match_case_insensitive(tmp_db, make_user, monkeypatch):
    uid = make_user(email="owner@example.com")
    monkeypatch.setattr(
        google_oauth.requests, "post",
        lambda *a, **k: _FakeResp(200, {"access_token": "at", "refresh_token": "rt"}),
    )
    monkeypatch.setattr(google_oauth, "_fetch_email", lambda token: "Owner@Example.com")
    result = google_oauth.exchange_code("auth-code", expected_user_id=uid)
    assert result["user_id"] == uid
    assert result["email"] == "Owner@Example.com"
    assert google_oauth.is_connected(uid) is True


def test_exchange_code_unknown_user_rejected(tmp_db, monkeypatch):
    monkeypatch.setattr(
        google_oauth.requests, "post",
        lambda *a, **k: _FakeResp(200, {"access_token": "at", "refresh_token": "rt"}),
    )
    with pytest.raises(RuntimeError):
        google_oauth.exchange_code("auth-code", expected_user_id=uuid.uuid4())


def test_send_email_refuses_when_user_not_connected(tmp_db, make_user, monkeypatch):
    uid = make_user(email="nogmail@example.com")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")
    monkeypatch.setenv("GOOGLE_OAUTH_REDIRECT_URI", "https://app.example/")
    err = google_oauth.send_email(uid, "to@example.com", "Subject", "Body")
    assert err is not None
    assert "connect" in err.lower()                        # no token -> cannot send
