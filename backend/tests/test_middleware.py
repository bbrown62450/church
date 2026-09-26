"""Request ids, CORS-safe 500s, middleware order, CORS lists and logging (ops slice, F §1.10, §2.5)."""
import asyncio
import logging
import re

import pytest
from fastapi import APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from api import settings as settings_mod
from api.deps import get_verifier
from api.errors import error_body
from api.main import create_app
from api.middleware import RequestIdMiddleware, UnhandledErrorMiddleware

HEX32 = re.compile(r"[0-9a-f]{32}")


def _app_with_test_routes():
    """create_app() plus a route that needs an int, for a 422."""
    app = create_app()
    router = APIRouter()

    @router.get("/needs-int")
    def needs_int(n: int):
        return {"n": n}

    app.include_router(router)
    app.dependency_overrides[get_verifier] = lambda: None   # /me fails on the missing token first
    return app


# --- RequestIdMiddleware ------------------------------------------------------

def test_every_response_gets_a_generated_request_id():
    r = TestClient(create_app()).get("/health")
    assert r.status_code == 200
    assert HEX32.fullmatch(r.headers["x-request-id"])


@pytest.mark.parametrize("inbound", ["abcd-1234-efgh", "abcd1234", "A" * 64],
                         ids=["dashed", "8-chars", "64-chars"])
def test_a_valid_inbound_request_id_is_echoed(inbound):
    r = TestClient(create_app()).get("/health", headers={"X-Request-Id": inbound})
    assert r.headers["x-request-id"] == inbound


@pytest.mark.parametrize("inbound", ["bad id!", "abc-123", "a" * 65],
                         ids=["bad-characters", "7-chars", "65-chars"])
def test_an_invalid_inbound_request_id_is_replaced(inbound):
    r = TestClient(create_app()).get("/health", headers={"X-Request-Id": inbound})
    assert HEX32.fullmatch(r.headers["x-request-id"])


@pytest.mark.parametrize("method, path, status, code", [
    ("GET", "/nope", 404, "not_found"),
    ("POST", "/health", 405, "method_not_allowed"),
    ("GET", "/me", 401, "unauthenticated"),
    ("GET", "/needs-int?n=abc", 422, "invalid_request"),
], ids=["404", "405", "401", "422"])
def test_every_error_body_carries_the_request_id_from_the_header(method, path, status, code):
    r = TestClient(_app_with_test_routes()).request(method, path)
    assert r.status_code == status
    error = r.json()["error"]
    assert error["code"] == code
    assert error["request_id"] == r.headers["x-request-id"]


def test_an_error_body_built_outside_a_request_still_has_a_request_id():
    # Only the last-resort handler (outside RequestIdMiddleware) builds one here.
    body = error_body("internal_error", "Something went wrong.")
    assert HEX32.fullmatch(body["error"]["request_id"])


# --- UnhandledErrorMiddleware: CORS-safe 500s (F §2.5, §7.3) --------------------

ALLOWED_ORIGIN = "https://church.example.app"


@pytest.fixture
def cors_origin(monkeypatch):
    """CORS_ORIGINS is exactly ALLOWED_ORIGIN for apps created in this test."""
    monkeypatch.setenv("CORS_ORIGINS", ALLOWED_ORIGIN)
    settings_mod.get_settings.cache_clear()
    yield ALLOWED_ORIGIN
    settings_mod.get_settings.cache_clear()


def _app_that_raises():
    app = create_app()
    router = APIRouter()

    @router.get("/boom")
    def boom():
        raise RuntimeError("secret detail")

    app.include_router(router)
    return app


def test_a_500_carries_cors_headers_and_the_request_id(cors_origin):
    client = TestClient(_app_that_raises(), raise_server_exceptions=False)
    r = client.get("/boom", headers={"Origin": cors_origin})
    assert r.status_code == 500
    assert r.json() == {"error": {
        "code": "internal_error",
        "message": "Something went wrong.",
        "request_id": r.headers["x-request-id"],
    }}
    assert r.headers["access-control-allow-origin"] == cors_origin
    assert "secret detail" not in r.text


def test_a_500_for_another_origin_has_no_cors_header(cors_origin):
    client = TestClient(_app_that_raises(), raise_server_exceptions=False)
    r = client.get("/boom", headers={"Origin": "https://evil.example"})
    assert r.status_code == 500
    assert "access-control-allow-origin" not in r.headers
    assert r.json()["error"]["request_id"] == r.headers["x-request-id"]


def test_an_unhandled_error_is_logged_with_the_path_but_not_the_query(caplog):
    client = TestClient(_app_that_raises(), raise_server_exceptions=False)
    with caplog.at_level(logging.ERROR):
        r = client.get("/boom?code=do-not-log-me")
    assert r.status_code == 500
    records = [rec for rec in caplog.records if rec.name == "api.middleware"]
    assert [rec.getMessage() for rec in records] == ["Unhandled error on GET /boom"]
    assert records[0].exc_info is not None                  # the stack trace is logged
    assert "do-not-log-me" not in caplog.text


def test_an_error_after_the_response_started_is_reraised_without_a_second_start():
    sent = []

    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        raise RuntimeError("mid-stream")

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    scope = {"type": "http", "method": "GET", "path": "/stream", "headers": []}
    with pytest.raises(RuntimeError, match="mid-stream"):
        asyncio.run(UnhandledErrorMiddleware(app)(scope, receive, send))
    assert [m["type"] for m in sent] == ["http.response.start"]


def test_middleware_order_is_cors_then_request_id_then_unhandled_error():
    # Starlette makes the last middleware added the outermost; user_middleware
    # lists them outermost first (F §2.5; slice 3 appends GZip innermost).
    app = create_app()
    assert [m.cls for m in app.user_middleware] == [
        CORSMiddleware, RequestIdMiddleware, UnhandledErrorMiddleware,
    ]


# --- CORS header lists (F §1.10) and no trailing-slash redirect (F §1.1) --------

ALLOWED_REQUEST_HEADERS = ("authorization", "content-type", "x-church-id",
                           "idempotency-key", "if-match", "x-request-id")


def _header_list(value):
    return {item.strip().lower() for item in value.split(",")}


def test_preflight_allows_the_six_request_headers_for_ten_minutes(cors_origin):
    r = TestClient(create_app()).options("/me", headers={
        "Origin": cors_origin,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": ", ".join(ALLOWED_REQUEST_HEADERS),
    })
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == cors_origin
    assert set(ALLOWED_REQUEST_HEADERS) <= _header_list(r.headers["access-control-allow-headers"])
    assert r.headers["access-control-max-age"] == "600"
    assert "access-control-allow-credentials" not in r.headers    # bearer tokens, not cookies
    # CORSMiddleware answers preflights itself, outside RequestIdMiddleware (accepted, F §2.5).
    assert "x-request-id" not in r.headers


def test_responses_expose_request_id_content_disposition_and_retry_after(cors_origin):
    r = TestClient(create_app()).get("/health", headers={"Origin": cors_origin})
    assert r.status_code == 200
    assert {"x-request-id", "content-disposition", "retry-after"} <= _header_list(
        r.headers["access-control-expose-headers"])


@pytest.mark.parametrize("path", ["/health/", "/me/"])
def test_a_trailing_slash_is_a_404_not_a_redirect(path):
    r = TestClient(create_app()).get(path, follow_redirects=False)
    assert r.status_code == 404
    assert "location" not in r.headers
    assert r.json()["error"]["code"] == "not_found"
    assert r.json()["error"]["request_id"] == r.headers["x-request-id"]
