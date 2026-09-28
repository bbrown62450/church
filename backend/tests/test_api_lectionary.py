"""GET /lectionary/readings over HTTP (S API, Status rules, Testing; AC1, AC2, AC7, AC9).

The merge, the caches and the status derivation are pinned in
test_usecase_lectionary.py. These tests pin the HTTP contract: the token,
the strict `date` parameter, the exact bodies, the `lectionary` bucket and
X-Church-Id being ignored. The two upstreams are a MockTransport put behind
integrations.http with set_http_for_tests (F §5: injection over mocking).
The autouse fixtures in conftest.py restore the real client, full buckets
and empty lectionary caches before every test.
"""
from collections.abc import Callable

import httpx
import pytest
from sqlalchemy import select

from api import ratelimit
from api import settings as settings_mod
from db import session_scope
from db.models import User
from domain_errors import RateLimited
from integrations import http
from tests import upstream_fixtures
from tests.api_helpers import auth_headers, make_api_client

EMAIL = "pastor@example.com"
ORIGIN = "https://church.example.app"
LECTIO_HOST = "lectio-api.org"
VANDERBILT_HOST = "lectionary.library.vanderbilt.edu"
UNREACHABLE = ("The lectionary couldn't be reached. "
               "Enter readings yourself, or try again in a few minutes.")
RANGE = "Enter a date between 1900 and 2199."

# S "Example": both sources answer; Vanderbilt alone has the Palms set, and the
# Passion set is in both (merged) and is the default.
PALM_SUNDAY = {
    "date": "2026-03-29",
    "status": "ok",
    "partial": False,
    "default_index": 1,
    "reading_sets": [
        {"name": "Liturgy of the Palms", "source": "vanderbilt",
         "scriptures": ["Psalm 118:1-2, 19-29", "Matthew 21:1-11"]},
        {"name": "Liturgy of the Passion", "source": "merged",
         "scriptures": ["Isaiah 50:4-9a", "Psalm 31:9-16", "Philippians 2:5-11",
                        "Matthew 26:14-27:66"]},
    ],
}


@pytest.fixture
def client(tmp_db):
    return make_api_client()


def _upstream(answer: Callable[[httpx.Request], httpx.Response]) -> list[httpx.Request]:
    """Put a fake Lectio and Vanderbilt behind integrations.http: `answer`
    builds each response. Returns the list every outbound request lands in."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host in (LECTIO_HOST, VANDERBILT_HOST), request.url.host
        seen.append(request)
        return answer(request)

    http.set_http_for_tests(httpx.Client(transport=httpx.MockTransport(handler)))
    return seen


def _not_found(request: httpx.Request) -> httpx.Response:
    """Neither source has anything for the date: a definitive none (S Status rules)."""
    if request.url.host == LECTIO_HOST:
        return httpx.Response(404, json={"error": "No readings found"})
    return httpx.Response(404, text="<html><body>Not Found</body></html>",
                          headers={"Content-Type": "text/html"})


def _server_error(request: httpx.Request) -> httpx.Response:
    return httpx.Response(500, text="Internal Server Error")


def _timeout(request: httpx.Request) -> httpx.Response:
    raise httpx.ReadTimeout("The read operation timed out", request=request)


def _recorded(request: httpx.Request) -> httpx.Response:
    """The recorded fixtures (T1): Lectio by its `date` parameter, Vanderbilt
    by the year in its path (/calendar/2025-26/)."""
    if request.url.host == LECTIO_HOST:
        recorded = upstream_fixtures.load("lectio", request.url.params["date"])
    else:
        recorded = upstream_fixtures.load("vanderbilt", request.url.path.split("/")[2])
    return httpx.Response(recorded.status, content=recorded.body,
                          headers={"Content-Type": recorded.content_type})


def _readings(client, day: str, headers: dict[str, str]):
    return client.get("/lectionary/readings", params={"date": day}, headers=headers)


def _user_id(email: str = EMAIL):
    with session_scope() as s:
        return s.execute(select(User.id).where(User.email == email)).scalar_one()


def test_requires_token_401(client):
    seen = _upstream(_not_found)
    r = client.get("/lectionary/readings", params={"date": "2026-03-29"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthenticated"
    assert seen == []


def test_palm_sunday_200_shape(client):
    """AC1 and S's example, end to end over the recorded fixtures. If the
    recording differs from S's example, the expected value is the recorded
    result and T12 corrects S (2a clarification 41)."""
    _upstream(_recorded)
    r = _readings(client, "2026-03-29", auth_headers(EMAIL))
    assert r.status_code == 200, r.text
    assert r.json() == PALM_SUNDAY


def test_church_header_ignored_zero_church_user_200(client, make_church):
    seen = _upstream(_not_found)
    someone_elses = make_church(name="Someone Else's")
    headers = {**auth_headers(EMAIL), "X-Church-Id": str(someone_elses)}
    r = _readings(client, "2026-09-29", headers)
    assert r.status_code == 200, r.text
    assert r.json() == {"date": "2026-09-29", "status": "no_readings", "partial": False,
                        "reading_sets": [], "default_index": None}
    assert {request.url.host for request in seen} == {LECTIO_HOST, VANDERBILT_HOST}
    assert client.get("/me", headers=auth_headers(EMAIL)).json()["churches"] == []


def test_bad_date_422_fields_date(client, limiter_clock):
    seen = _upstream(_not_found)
    headers = auth_headers(EMAIL)
    for bad in ("2026-3-29", "0", "2026-03-29T00:00:00", "2026-02-30"):
        r = _readings(client, bad, headers)
        assert r.status_code == 422, bad
        assert r.json()["error"]["code"] == "invalid_request", bad
        assert r.json()["error"]["message"] == "The request was not valid.", bad
        assert r.json()["error"]["fields"] == {"date": "Not a valid value."}, bad
    missing = client.get("/lectionary/readings", headers=headers)
    assert missing.status_code == 422
    assert missing.json()["error"]["fields"] == {"date": "Required."}
    assert seen == []
    # The bucket's dependency runs before FastAPI validates the query, so each
    # of the five 422s spent a token: exactly 115 of 120 are left (2a clarification 38).
    ratelimit.consume("lectionary", user_id=_user_id(), cost=115)
    with pytest.raises(RateLimited):
        ratelimit.consume("lectionary", user_id=_user_id())


def test_out_of_range_422_exact_message(client):
    seen = _upstream(_not_found)
    headers = auth_headers(EMAIL)
    for outside in ("1899-12-31", "2200-01-01", "0001-01-01"):
        r = _readings(client, outside, headers)
        assert r.status_code == 422, outside
        assert r.json() == {"error": {
            "code": "invalid_request",
            "message": RANGE,
            "request_id": r.headers["x-request-id"],
            "fields": {"date": RANGE},
        }}, outside
    assert seen == []                                   # no lookup runs
    for edge in ("1900-01-01", "2199-12-31"):
        r = _readings(client, edge, headers)
        assert r.status_code == 200, (edge, r.text)
        assert r.json()["date"] == edge


def test_502_exact_message(client):
    seen = _upstream(_server_error)
    r = _readings(client, "2026-10-04", auth_headers(EMAIL))
    assert r.status_code == 502
    assert r.json() == {"error": {
        "code": "upstream_error",
        "message": UNREACHABLE,
        "request_id": r.headers["x-request-id"],
    }}
    assert {request.url.host for request in seen} == {LECTIO_HOST, VANDERBILT_HOST}


def test_504_exact_message(client):
    seen = _upstream(_timeout)
    r = _readings(client, "2026-10-04", auth_headers(EMAIL))
    assert r.status_code == 504
    assert r.json() == {"error": {
        "code": "upstream_timeout",
        "message": UNREACHABLE,
        "request_id": r.headers["x-request-id"],
    }}
    assert {request.url.host for request in seen} == {LECTIO_HOST, VANDERBILT_HOST}


def test_121st_call_429_with_headers_and_cors(tmp_db, limiter_clock, monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", ORIGIN)
    settings_mod.get_settings.cache_clear()
    try:
        client = make_api_client()
        seen = _upstream(_not_found)
        headers = {**auth_headers(EMAIL), "Origin": ORIGIN}
        for n in range(120):                    # limiter_clock never moves: no token comes back
            r = _readings(client, "2026-09-29", headers)
            assert r.status_code == 200, (n, r.text)
        assert len(seen) == 2                   # the first call filled both caches; the rest were hits
        r = _readings(client, "2026-09-29", headers)
        assert r.status_code == 429
        assert r.json() == {"error": {
            "code": "rate_limited",
            "message": "Too many requests. Try again in 3 seconds.",
            "request_id": r.headers["x-request-id"],
            "details": {"retry_after_seconds": 3},
        }}
        assert r.headers["retry-after"] == "3"  # one token per 2.5 s, rounded up
        assert r.headers["access-control-allow-origin"] == ORIGIN
        assert len(seen) == 2                   # the 429 never reached the usecase
        limiter_clock.advance(2.5)
        assert _readings(client, "2026-09-29", headers).status_code == 200
    finally:
        settings_mod.get_settings.cache_clear()


def test_date_echoed_never_normalized(client):
    """Ascension Thursday is looked up as itself, not as the Sunday before
    (2026-05-10), and none of its sets is named for a Sunday (S Behavior changes row 3)."""
    seen = _upstream(_recorded)
    r = _readings(client, "2026-05-14", auth_headers(EMAIL))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["date"] == "2026-05-14"
    assert body["status"] == "ok"
    assert body["reading_sets"]
    assert not any("Sunday" in s["name"] for s in body["reading_sets"])
    assert [request.url.params["date"] for request in seen
            if request.url.host == LECTIO_HOST] == ["2026-05-14"]
