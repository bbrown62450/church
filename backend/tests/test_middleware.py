"""Request ids, CORS-safe 500s, middleware order, CORS lists and logging (ops slice, F §1.10, §2.5)."""
import asyncio
import logging
import re

import pytest
from fastapi import APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.testclient import TestClient

from api import settings as settings_mod
from api.deps import get_verifier
from api.errors import error_body
from api.logging_config import LOG_FORMAT, configure_logging
from api.main import create_app
from api.middleware import RequestIdMiddleware, UnhandledErrorMiddleware, UploadSizeMiddleware

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


def test_middleware_order_is_cors_then_request_id_then_unhandled_error_then_upload_size_then_gzip():
    # Starlette makes the last middleware added the outermost; user_middleware
    # lists them outermost first (F §2.5; slice 3 added GZip innermost; printed
    # bulletin PR 3a UploadSize inside UnhandledError, so its 422 has CORS headers).
    app = create_app()
    assert [m.cls for m in app.user_middleware] == [
        CORSMiddleware, RequestIdMiddleware, UnhandledErrorMiddleware, UploadSizeMiddleware, GZipMiddleware,
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


# --- Logging: request_id= on every line (F §2.5) --------------------------------

def test_a_log_line_from_a_sync_route_carries_the_request_id(caplog):
    app = create_app()
    router = APIRouter()

    @router.get("/hello")
    def hello():                      # a plain def: FastAPI runs it in the threadpool
        logging.getLogger("tests.hello").info("hello")
        return {"ok": True}

    app.include_router(router)
    with caplog.at_level(logging.INFO):
        r = TestClient(app).get("/hello")
    records = [rec for rec in caplog.records if rec.name == "tests.hello"]
    assert len(records) == 1
    assert records[0].request_id == r.headers["x-request-id"]


def test_a_log_line_outside_a_request_has_a_dash(caplog):
    with caplog.at_level(logging.INFO):
        logging.getLogger("tests.outside").info("no request here")
    assert [rec.request_id for rec in caplog.records if rec.name == "tests.outside"] == ["-"]


def test_configure_logging_installs_the_record_factory_once():
    configure_logging("INFO")
    factory = logging.getLogRecordFactory()
    configure_logging("INFO")
    assert logging.getLogRecordFactory() is factory


@pytest.mark.parametrize("value, level", [
    ("debug", logging.DEBUG), (" Warning ", logging.WARNING), ("ERROR", logging.ERROR),
])
def test_configure_logging_accepts_level_names(value, level):
    assert configure_logging(value) == level


def test_an_invalid_log_level_warns_and_uses_info(caplog):
    with caplog.at_level(logging.WARNING):
        assert configure_logging("verbose") == logging.INFO
    assert "LOG_LEVEL='verbose' is not a valid level; using INFO." in [
        rec.getMessage() for rec in caplog.records if rec.levelno == logging.WARNING]


def test_configure_logging_sets_up_a_root_logger_that_has_no_handlers():
    root = logging.getLogger()
    saved_handlers, saved_level = root.handlers[:], root.level
    root.handlers[:] = []                 # as under uvicorn: nothing has configured root
    try:
        assert configure_logging("WARNING") == logging.WARNING
        assert root.level == logging.WARNING
        assert len(root.handlers) == 1
        # A record built without the factory (makeLogRecord) still formats, with "-".
        record = logging.makeLogRecord({"name": "api.x", "levelname": "INFO", "msg": "hi"})
        assert root.handlers[0].format(record) == "api.x INFO request_id=- hi"
    finally:
        root.handlers[:] = saved_handlers
        root.setLevel(saved_level)


def test_the_log_format_names_the_request_id():
    assert LOG_FORMAT == "%(name)s %(levelname)s request_id=%(request_id)s %(message)s"


@pytest.mark.parametrize("env, expected", [(None, "INFO"), ("", "INFO"), (" debug ", "debug")],
                         ids=["unset", "blank", "set"])
def test_the_log_level_setting_comes_from_log_level(monkeypatch, env, expected):
    if env is None:
        monkeypatch.delenv("LOG_LEVEL", raising=False)
    else:
        monkeypatch.setenv("LOG_LEVEL", env)
    settings_mod.get_settings.cache_clear()
    try:
        assert settings_mod.get_settings().log_level == expected
    finally:
        settings_mod.get_settings.cache_clear()
