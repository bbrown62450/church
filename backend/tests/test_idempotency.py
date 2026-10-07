"""The Idempotency-Key store and run_idempotent (F §1.6; S Idempotency).

POST /things is a throwaway sync route on create_app(); the user id comes from
an X-Test-User header so these tests need no token or database.
"""
import threading
import time
import uuid
from typing import Optional

import pytest
from fastapi import APIRouter, Depends, Header
from fastapi.testclient import TestClient
from pydantic import BaseModel

from api import idempotency
from api.idempotency import (
    IDEMPOTENCY_TTL_SECONDS,
    MAX_ENTRIES,
    REPLAYED_HEADER,
    IdempotencyStore,
    idempotency_key,
    reset_idempotency_for_tests,
    run_idempotent,
)
from api.main import create_app
from domain_errors import Busy, Conflict, DomainError, RateLimited, UpstreamTimeout
from tests.conftest import FakeClock

USER_A = uuid.UUID(int=1)
USER_B = uuid.UUID(int=2)
KEY = "6f1c2a52-3a8e-4c3e-9d57-2f0b1f6f1a11"


class _In(BaseModel):
    name: str


class _Tags(BaseModel):
    tags: dict[str, int]


class _Out(BaseModel):
    id: int
    name: str


@pytest.fixture(autouse=True)
def _fresh_store():
    reset_idempotency_for_tests()
    yield
    reset_idempotency_for_tests()


def _client(outcome=None, *, required=False):
    """create_app() plus POST /things. The call records each name it sees in
    `calls`, runs `outcome(<call number>)` (which may raise), then returns
    {"id": <call number>, "name": …}. Returns (client, calls)."""
    calls = []
    app = create_app()
    router = APIRouter()

    @router.post("/things", status_code=201, response_model=_Out)
    def create_thing(
        payload: _In,
        key: Optional[uuid.UUID] = Depends(idempotency_key(required=required)),
        x_test_user: str = Header(),
    ):
        def call():
            calls.append(payload.name)
            if outcome is not None:
                outcome(len(calls))
            return _Out(id=len(calls), name=payload.name)

        return run_idempotent(user_id=uuid.UUID(x_test_user), route="/things", key=key,
                              payload=payload, status_code=201, call=call)

    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False), calls


def _post(client, name="Grace", *, key=KEY, user=USER_A):
    headers = {"X-Test-User": str(user)}
    if key is not None:
        headers["Idempotency-Key"] = key
    return client.post("/things", json={"name": name}, headers=headers)


def _direct(store, calls, **overrides):
    """run_idempotent outside HTTP, with a call that counts itself in `calls`."""

    def call():
        calls.append(1)
        return _Out(id=len(calls), name="Grace")

    kwargs = dict(user_id=USER_A, route="/things", key=uuid.UUID(KEY), payload=_In(name="Grace"),
                  status_code=201, call=call, store=store)
    kwargs.update(overrides)
    return run_idempotent(**kwargs)


def test_replay_returns_the_stored_status_and_body_with_replayed_header():
    client, calls = _client()
    first, again = _post(client), _post(client)
    assert (first.status_code, first.json()) == (201, {"id": 1, "name": "Grace"})
    assert REPLAYED_HEADER.lower() not in first.headers
    assert (again.status_code, again.json()) == (201, {"id": 1, "name": "Grace"})
    assert again.headers[REPLAYED_HEADER] == "true"
    assert calls == ["Grace"]


def test_a_4xx_domain_error_is_stored_and_replayed():
    def conflict(_n):
        raise Conflict("That name is taken.")

    client, calls = _client(conflict)
    first, again = _post(client), _post(client)
    assert first.status_code == again.status_code == 409
    assert again.json() == first.json()          # the stored body, its request_id included
    assert again.json()["error"]["code"] == "conflict"
    assert again.headers[REPLAYED_HEADER] == "true"
    assert len(calls) == 1


def test_a_5xx_is_not_stored_and_re_executes():
    def busy_once(n):
        if n == 1:
            raise Busy("The AI is busy. Try again in a moment.", code="ai_busy")

    client, calls = _client(busy_once)
    first = _post(client)
    assert (first.status_code, first.json()["error"]["code"]) == (503, "ai_busy")
    again = _post(client)
    assert (again.status_code, again.json()) == (201, {"id": 2, "name": "Grace"})
    assert REPLAYED_HEADER.lower() not in again.headers
    assert len(calls) == 2


def test_rate_limited_is_returned_with_retry_after_not_stored_and_re_executes():
    def limited(_n):
        raise RateLimited("You've created 5 churches in the last 24 hours. Try again later.",
                          retry_after_seconds=90)

    client, calls = _client(limited)
    first, again = _post(client), _post(client)
    for r in (first, again):
        assert r.status_code == 429
        assert r.headers["retry-after"] == "90"
        assert r.json()["error"]["details"] == {"retry_after_seconds": 90}
        assert REPLAYED_HEADER.lower() not in r.headers
    assert len(calls) == 2
    assert len(idempotency.store) == 0


def test_a_different_body_is_idempotency_mismatch():
    client, calls = _client()
    assert _post(client, "Grace").status_code == 201
    r = _post(client, "Hope")
    assert r.status_code == 422
    error = r.json()["error"]
    assert (error["code"], error["message"]) == (
        "idempotency_mismatch", "This request was already sent with different details.")
    assert calls == ["Grace"]


def test_keys_are_scoped_per_user():
    client, calls = _client()
    a, b = _post(client, user=USER_A), _post(client, user=USER_B)
    assert (a.json()["id"], b.json()["id"]) == (1, 2)
    assert REPLAYED_HEADER.lower() not in b.headers
    assert len(calls) == 2


def test_keys_are_scoped_per_route_and_method():
    store, calls = IdempotencyStore(), []
    _direct(store, calls, route="/things")
    _direct(store, calls, route="/other")
    _direct(store, calls, route="/things", method="PUT")
    replay = _direct(store, calls, route="/things", method="post")    # methods compare upper-cased
    assert len(calls) == 3
    assert replay.headers[REPLAYED_HEADER] == "true"
    assert len(store) == 3


def test_keys_are_scoped_per_church():
    """F §1.6 church-scope amendment (2026-09-28): a church-scoped route passes its
    church, so the same user and key in another church runs the call again."""
    church_a, church_b = uuid.UUID(int=10), uuid.UUID(int=11)
    store, calls = IdempotencyStore(), []
    first = _direct(store, calls, church_id=church_a)
    other_church = _direct(store, calls, church_id=church_b)
    user_scoped = _direct(store, calls)                                # church_id None: POST /churches
    replay = _direct(store, calls, church_id=church_a)
    assert len(calls) == 3
    assert REPLAYED_HEADER.lower() not in first.headers
    assert REPLAYED_HEADER.lower() not in other_church.headers
    assert REPLAYED_HEADER.lower() not in user_scoped.headers
    assert replay.headers[REPLAYED_HEADER] == "true"
    assert len(store) == 3


def test_concurrent_same_key_requests_run_the_call_once():
    store, calls, responses = IdempotencyStore(), [], []
    barrier = threading.Barrier(2)

    def slow_call():
        calls.append(1)
        time.sleep(0.2)          # long enough that an unlocked second request would run it too
        return _Out(id=len(calls), name="Grace")

    def request():
        barrier.wait(timeout=5)
        responses.append(_direct(store, calls, call=slow_call))

    threads = [threading.Thread(target=request) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    assert len(calls) == 1
    assert sorted(r.headers.get(REPLAYED_HEADER, "") for r in responses) == ["", "true"]
    assert responses[0].body == responses[1].body


def test_entries_expire_after_15_minutes():
    assert IDEMPOTENCY_TTL_SECONDS == 15 * 60
    clock = FakeClock()
    store, calls = IdempotencyStore(clock=clock.now), []
    _direct(store, calls)
    clock.advance(IDEMPOTENCY_TTL_SECONDS - 1)
    assert _direct(store, calls).headers[REPLAYED_HEADER] == "true"
    clock.advance(1)
    assert REPLAYED_HEADER not in _direct(store, calls).headers
    assert len(calls) == 2


def test_malformed_key_is_422_with_exact_message():
    client, calls = _client()
    r = _post(client, key="not-a-uuid")
    assert r.status_code == 422
    assert r.json() == {"error": {
        "code": "invalid_request",
        "message": "Idempotency-Key must be a UUID.",
        "request_id": r.headers["x-request-id"],
    }}
    assert calls == []


def test_required_key_missing_is_422():
    client, calls = _client(required=True)
    r = _post(client, key=None)
    assert r.status_code == 422
    error = r.json()["error"]
    assert (error["code"], error["message"]) == ("invalid_request", "Missing Idempotency-Key header.")
    assert calls == []
    assert _post(client).status_code == 201          # with a key it runs


def test_no_key_means_no_idempotency():
    client, calls = _client()
    a, b = _post(client, key=None), _post(client, key=None)
    assert (a.json()["id"], b.json()["id"]) == (1, 2)
    assert REPLAYED_HEADER.lower() not in b.headers
    assert len(idempotency.store) == 0


def test_store_is_bounded_to_10000_entries():
    assert MAX_ENTRIES == 10_000
    assert IdempotencyStore().max_entries == MAX_ENTRIES
    store, calls = IdempotencyStore(max_entries=3), []
    keys = [uuid.uuid4() for _ in range(4)]
    for key in keys:
        _direct(store, calls, key=key)
    assert len(store) == 3
    assert _direct(store, calls, key=keys[3]).headers[REPLAYED_HEADER] == "true"   # newest kept
    assert REPLAYED_HEADER not in _direct(store, calls, key=keys[0]).headers       # oldest evicted
    assert len(calls) == 5
    assert len(store) == 3


def test_non_domain_exception_drops_the_entry_and_is_a_500():
    def boom_once(n):
        if n == 1:
            raise RuntimeError("database went away")

    client, calls = _client(boom_once)
    first = _post(client)
    assert (first.status_code, first.json()["error"]["code"]) == (500, "internal_error")
    assert "database went away" not in first.text
    assert len(idempotency.store) == 0
    again = _post(client)
    assert (again.status_code, again.json()) == (201, {"id": 2, "name": "Grace"})


def test_body_hash_ignores_key_order():
    store, calls = IdempotencyStore(), []
    _direct(store, calls, payload=_Tags(tags={"a": 1, "b": 2}))
    again = _direct(store, calls, payload=_Tags(tags={"b": 2, "a": 1}))
    assert again.headers[REPLAYED_HEADER] == "true"
    assert len(calls) == 1
    with pytest.raises(DomainError) as caught:
        _direct(store, calls, payload=_Tags(tags={"a": 1, "b": 3}))
    assert caught.value.code == "idempotency_mismatch"


# --- slice 5b-2: store_error (an uncertain send's 5xx is kept for the retry) ----------------------

def _uncertain(_n):
    raise UpstreamTimeout("Gmail didn't confirm the email.", code="upstream_timeout",
                          details={"send_uncertain": True})


def _kept(error: DomainError) -> bool:
    return bool((error.details or {}).get("send_uncertain"))


def test_store_error_keeps_a_5xx_it_accepts_and_replays_it():
    store, calls = IdempotencyStore(), []
    first = _direct(store, calls, call=lambda: _uncertain(calls.append(1)), store_error=_kept)
    again = _direct(store, calls, call=lambda: _uncertain(calls.append(1)), store_error=_kept)
    assert first.status_code == again.status_code == 504
    assert bytes(again.body) == bytes(first.body) and again.headers[REPLAYED_HEADER] == "true"
    assert len(calls) == 1


def test_store_error_saying_no_or_left_out_keeps_slice_1s_rule():
    for store_error in (None, lambda error: False):
        store, calls = IdempotencyStore(), []
        for _ in range(2):
            r = _direct(store, calls, call=lambda: _uncertain(calls.append(1)), store_error=store_error)
            assert r.status_code == 504 and REPLAYED_HEADER.lower() not in r.headers
        assert len(calls) == 2 and len(store) == 0


def test_store_error_never_keeps_a_rate_limit():
    store, calls = IdempotencyStore(), []

    def limited():
        calls.append(1)
        raise RateLimited("Too many requests. Try again in 5 seconds.", retry_after_seconds=5)

    for _ in range(2):
        assert _direct(store, calls, call=limited, store_error=lambda error: True).status_code == 429
    assert len(calls) == 2 and len(store) == 0
