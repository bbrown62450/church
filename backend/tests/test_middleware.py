"""Request ids, CORS-safe 500s, middleware order, CORS lists and logging (ops slice, F §1.10, §2.5)."""
import re

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

from api.deps import get_verifier
from api.errors import error_body
from api.main import create_app

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
