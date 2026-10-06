"""/gmail-connection over HTTP (slice 5b spec, API and Testing "test_api_gmail.py";
slice 5b-2): user-scoped (X-Church-Id ignored), the exact codes and messages,
and Google's own text never in a response. Google is tests.fake_google."""
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

import google_oauth
from api.deps import get_google_config
from db import session_scope
from db.models import OAuthState
from tests.api_helpers import auth_headers, make_api_client
from tests.fake_google import REFRESH_TOKEN, FakeGoogle, google_error

OWNER = "owner@example.com"
CONFIG = google_oauth.GoogleOAuthConfig("client-123", "secret-456", "https://app.example.org/gmail/callback")
DISCONNECTED = {"configured": True, "connected": False, "google_email": None}


@pytest.fixture
def config():
    return {"value": CONFIG}


@pytest.fixture
def client(tmp_db, config):
    client = make_api_client()
    client.app.dependency_overrides[get_google_config] = lambda: config["value"]
    return client


def _error(r) -> tuple:
    error = r.json()["error"]
    return r.status_code, error["code"], error["message"]


def _start(client, email=OWNER) -> str:
    r = client.post("/gmail-connection/auth-url", headers=auth_headers(email))
    assert r.status_code == 200, r.text
    return {key: values[0] for key, values in parse_qs(urlsplit(r.json()["auth_url"]).query).items()}["state"]


def test_connect_status_and_disconnect(client):
    google = FakeGoogle(email="Owner@Example.com").install()
    headers = {**auth_headers(OWNER), "X-Church-Id": "not-a-church"}           # ignored: user-scoped
    assert client.get("/gmail-connection", headers=headers).json() == DISCONNECTED
    r = client.post("/gmail-connection/auth-url", headers=headers)
    url = r.json()["auth_url"]
    query = {key: values[0] for key, values in parse_qs(urlsplit(url).query).items()}
    assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert (query["login_hint"], query["redirect_uri"]) == (OWNER, CONFIG.redirect_uri)
    r = client.post("/gmail-connection", headers=headers, json={"code": "auth-code", "state": query["state"]})
    connected = {"configured": True, "connected": True, "google_email": "Owner@Example.com"}
    assert (r.status_code, r.json()) == (200, connected)
    assert client.get("/gmail-connection", headers=headers).json() == connected
    r = client.delete("/gmail-connection", headers=headers)
    assert (r.status_code, r.json()) == (200, DISCONNECTED)
    assert google.form(google.requests[-1]) == {"token": REFRESH_TOKEN}
    assert client.get("/gmail-connection", headers=headers).json() == DISCONNECTED


def test_a_connection_is_the_users_own(client):
    FakeGoogle().install()
    state = _start(client)
    r = client.post("/gmail-connection", headers=auth_headers("other@example.com"),
                    json={"code": "auth-code", "state": state})
    assert _error(r) == (400, "gmail_state_invalid",
                         "This Gmail connection request expired or was already used. Try connecting again.")
    assert client.get("/gmail-connection", headers=auth_headers(OWNER)).json() == DISCONNECTED


@pytest.mark.parametrize("answer, expected", [
    (google_error(400, "invalid_grant"),
     (400, "gmail_connect_failed", "That Google approval has expired or was already used. Try connecting again.")),
    (google_error(401, "invalid_client"),
     (503, "gmail_not_configured", "Gmail sending isn't set up correctly on this deployment.")),
    (httpx.Response(200, json={"refresh_token": "r"}),
     (502, "upstream_error", "Google returned an incomplete response. Try connecting again.")),
    (httpx.Response(500, json={"error": "SECRET-GOOGLE-TEXT"}),
     (502, "upstream_error", "Couldn't reach Google. Try connecting again in a minute.")),
    (httpx.ReadTimeout("slow"),
     (504, "upstream_timeout", "Google took too long to respond. Try connecting again.")),
], ids=["invalid-grant", "client", "incomplete", "google-5xx", "timeout"])
def test_connect_errors_never_show_googles_text(client, answer, expected):
    google = FakeGoogle().install()
    google.exchange = answer
    r = client.post("/gmail-connection", headers=auth_headers(OWNER), json={"code": "auth-code", "state": _start(client)})
    assert _error(r) == expected
    assert "SECRET-GOOGLE-TEXT" not in r.text


def test_a_mismatched_account_is_named(client):
    FakeGoogle(email="someone.else@example.com").install()
    r = client.post("/gmail-connection", headers=auth_headers(OWNER), json={"code": "auth-code", "state": _start(client)})
    assert _error(r) == (400, "gmail_connect_failed", "That Google account doesn't match your signed-in email "
                                                      "(owner@example.com). Connect the Gmail account you're logged in with.")


def test_not_configured(client, config):
    config["value"] = google_oauth.GoogleOAuthConfig("", "", "")
    not_configured = (503, "gmail_not_configured", "Per-user Gmail sending isn't configured on this deployment.")
    assert client.get("/gmail-connection", headers=auth_headers(OWNER)).json() == {
        "configured": False, "connected": False, "google_email": None}
    assert _error(client.post("/gmail-connection/auth-url", headers=auth_headers(OWNER))) == not_configured
    r = client.post("/gmail-connection", headers=auth_headers(OWNER), json={"code": "c", "state": "s"})
    assert _error(r) == not_configured


def test_consent_urls_are_rate_limited_per_user(client):
    for _ in range(10):
        _start(client)
    r = client.post("/gmail-connection/auth-url", headers=auth_headers(OWNER))
    assert _error(r)[:2] == (429, "rate_limited") and int(r.headers["Retry-After"]) >= 1
    with session_scope() as s:
        assert s.query(OAuthState).count() == 10                      # the refused request stored no state
    assert _start(client, "other@example.com")                        # another user's bucket is their own


def test_the_body_is_checked(client):
    for body in ({"code": "c"}, {"code": "c", "state": "s", "extra": 1}, {"code": "c" * 2049, "state": "s"}):
        r = client.post("/gmail-connection", headers=auth_headers(OWNER), json=body)
        assert (r.status_code, r.json()["error"]["code"]) == (422, "invalid_request"), body


def test_every_gmail_route_needs_a_signed_in_user(client):
    for method, path in (("GET", "/gmail-connection"), ("POST", "/gmail-connection/auth-url"),
                         ("POST", "/gmail-connection"), ("DELETE", "/gmail-connection")):
        r = client.request(method, path, json={"code": "c", "state": "s"} if path == "/gmail-connection" else None)
        assert (r.status_code, r.json()["error"]["code"]) == (401, "unauthenticated"), (method, path)
