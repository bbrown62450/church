"""GET /translations over HTTP (S API row 2, Testing `test_api_translations.py`; AC6).

User-scoped reference data: a token is required, X-Church-Id is ignored, and
"esv" is offered, last, only while ESV_API_KEY is set (the configuration
exception: scripture_fetcher reads the key from the environment until slice 7).
"""
import pytest

from tests.api_helpers import auth_headers, make_api_client

EMAIL = "pastor@example.com"
PUBLIC_DOMAIN = [
    {"id": "web", "label": "World English Bible (WEB)"},
    {"id": "kjv", "label": "King James Version (KJV)"},
    {"id": "asv", "label": "American Standard Version (ASV)"},
    {"id": "ylt", "label": "Young's Literal Translation (YLT)"},
    {"id": "dra", "label": "Douay-Rheims 1899 (DRA)"},
    {"id": "darby", "label": "Darby Bible"},
    {"id": "bbe", "label": "Bible in Basic English (BBE)"},
    {"id": "oeb-us", "label": "Open English Bible, US (OEB)"},
    {"id": "webbe", "label": "World English Bible, British (WEBBE)"},
]
ESV = {"id": "esv", "label": "English Standard Version (ESV)"}


@pytest.fixture
def client(tmp_db):
    return make_api_client()


def test_requires_token_401(client):
    r = client.get("/translations")
    assert r.status_code == 401
    error = r.json()["error"]
    assert (error["code"], error["message"]) == ("unauthenticated", "Please sign in.")


def test_without_esv_key(client, monkeypatch):
    monkeypatch.delenv("ESV_API_KEY", raising=False)
    # X-Church-Id is ignored: a malformed one is neither checked nor a 403.
    r = client.get("/translations", headers={**auth_headers(EMAIL), "X-Church-Id": "not-a-uuid"})
    assert r.status_code == 200, r.text
    assert r.json() == {"default": "web", "esv_available": False, "items": PUBLIC_DOMAIN}


def test_with_esv_key_esv_last(client, monkeypatch):
    monkeypatch.setenv("ESV_API_KEY", "test-key")
    r = client.get("/translations", headers=auth_headers(EMAIL))
    assert r.status_code == 200, r.text
    assert r.json() == {"default": "web", "esv_available": True, "items": [*PUBLIC_DOMAIN, ESV]}
    assert "test-key" not in r.text                         # the key never leaves the backend
