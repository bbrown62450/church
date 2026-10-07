"""api.ratelimit and token_bucket (F §1.8; S "Rate-limit buckets", Testing; AC7, AC13; slice 2a).

Every test runs on the `limiter_clock` FakeClock (conftest.py), which never
moves unless a test advances it, so each wait below is exact.
"""
import time
import uuid

import pytest
from fastapi import Depends
from fastapi.dependencies.utils import get_dependant
from fastapi.testclient import TestClient

from api import ratelimit
from api import settings as settings_mod
from api.deps import get_current_user, get_verifier, require_church
from api.errors import ApiError
from api.main import create_app
from api.ratelimit import BUCKETS, MESSAGE, RateLimiter, Rule, consume, rate_limit
from api.security import TokenVerifier
from domain_errors import RateLimited
from tests.conftest import FakeClock
from tests.jwt_helpers import ISSUER, SIGNING_KEY, make_token
from token_bucket import TokenBucket


def _user() -> uuid.UUID:
    return uuid.uuid4()


def _rate_limited(bucket: str, **kwargs) -> RateLimited:
    with pytest.raises(RateLimited) as caught:
        consume(bucket, **kwargs)
    return caught.value


def test_buckets_match_f_1_8():
    assert BUCKETS == {
        "lectionary": (Rule("user", 120, 300),),
        "scripture": (Rule("user", 60, 300),),
        "church_create": (Rule("user", 3, 60),),
        "ai": (Rule("user", 40, 600), Rule("church", 400, 86_400)),
        "email": (Rule("user", 10, 3_600),),
        "picture": (Rule("user", 20, 3_600), Rule("church", 60, 86_400)),     # printed bulletin PR 3a
        "gmail_connect": (Rule("user", 10, 600),),                            # slice 5b-2
    }
    assert MESSAGE == "Too many requests. Try again in {n} seconds."


def test_refill_is_continuous(limiter_clock):
    user = _user()
    for _ in range(3):
        consume("church_create", user_id=user)
    assert _rate_limited("church_create", user_id=user).retry_after_seconds == 20
    limiter_clock.advance(10)                    # half a token back: 10 s still to wait
    assert _rate_limited("church_create", user_id=user).retry_after_seconds == 10
    limiter_clock.advance(10)                    # one whole token, 20 s after the 3rd create
    consume("church_create", user_id=user)
    assert _rate_limited("church_create", user_id=user).retry_after_seconds == 20


def test_per_user_isolation(limiter_clock):
    first, second = _user(), _user()
    for _ in range(3):
        consume("church_create", user_id=first)
    _rate_limited("church_create", user_id=first)
    for _ in range(3):
        consume("church_create", user_id=second)     # the first user's bucket is not the second's


def test_ai_church_rule_shared_across_users(limiter_clock):
    church, other_church = uuid.uuid4(), uuid.uuid4()
    for _ in range(10):                              # 10 users x 40 = the church's 400 per day
        user = _user()
        for _ in range(40):
            consume("ai", user_id=user, church_id=church)
    newcomer = _user()
    limited = _rate_limited("ai", user_id=newcomer, church_id=church)
    assert limited.retry_after_seconds == 216        # one church token: 86 400 s / 400
    consume("ai", user_id=newcomer, church_id=other_church)


def test_ai_without_church_id_is_value_error(limiter_clock):
    with pytest.raises(ValueError, match="church_id"):
        consume("ai", user_id=_user())


def test_exhausted_raises_rate_limited_with_ceiling(limiter_clock):
    user = _user()
    for _ in range(120):
        consume("lectionary", user_id=user)
    limited = _rate_limited("lectionary", user_id=user)
    assert not isinstance(limited, ApiError)
    assert (limited.status, limited.code) == (429, "rate_limited")
    assert limited.message == "Too many requests. Try again in 3 seconds."   # 2.5 s rounded up
    assert limited.retry_after_seconds == 3
    assert limited.details == {"retry_after_seconds": 3}
    limiter_clock.advance(1)                         # 1.5 s still to wait: rounded up to 2
    limited = _rate_limited("lectionary", user_id=user)
    assert (limited.message, limited.retry_after_seconds) == (
        "Too many requests. Try again in 2 seconds.", 2)
    limiter_clock.advance(1.5)
    consume("lectionary", user_id=user)


def test_cost_three_charges_three(limiter_clock):
    user = _user()
    consume("scripture", user_id=user, cost=3)
    for _ in range(57):                              # 60 - 3
        consume("scripture", user_id=user)
    assert _rate_limited("scripture", user_id=user).retry_after_seconds == 5
    limiter_clock.advance(15)                        # three tokens back: 5 s each
    consume("scripture", user_id=user, cost=3)


def test_failed_charge_takes_nothing_across_rules(limiter_clock):
    church = uuid.uuid4()
    spender = _user()
    for _ in range(40):
        consume("ai", user_id=spender, church_id=church)
    for _ in range(400):                             # each fails on the user rule...
        _rate_limited("ai", user_id=spender, church_id=church)
    other = _user()
    for _ in range(40):                              # ...and took no church token
        consume("ai", user_id=other, church_id=church)

    full_church = uuid.uuid4()
    for _ in range(10):
        user = _user()
        for _ in range(40):
            consume("ai", user_id=user, church_id=full_church)
    late = _user()
    for _ in range(40):                              # each fails on the church rule...
        _rate_limited("ai", user_id=late, church_id=full_church)
    for _ in range(40):                              # ...and took no user token
        consume("ai", user_id=late, church_id=uuid.uuid4())


def test_check_refuses_as_consume_would_and_takes_nothing(limiter_clock):
    """5b-2b build review M2: the email send peeks before building its files."""
    user = _user()
    for _ in range(3):
        ratelimit.check("church_create", user_id=user)             # a peek never charges
    for _ in range(3):
        consume("church_create", user_id=user)
    with pytest.raises(RateLimited) as caught:
        ratelimit.check("church_create", user_id=user)
    assert caught.value.retry_after_seconds == _rate_limited("church_create", user_id=user).retry_after_seconds == 20
    limiter_clock.advance(20)
    ratelimit.check("church_create", user_id=user)
    ratelimit.check("church_create", user_id=user)
    consume("church_create", user_id=user)                         # the one token is still there
    with pytest.raises(ValueError):
        ratelimit.check("ai", user_id=user)


def test_cost_below_one_or_above_capacity_is_value_error(limiter_clock):
    user = _user()
    for cost in (0, -1):
        with pytest.raises(ValueError, match="at least 1"):
            consume("church_create", user_id=user, cost=cost)
    with pytest.raises(ValueError, match="capacity"):
        consume("church_create", user_id=user, cost=4)
    with pytest.raises(ValueError, match="capacity"):
        consume("scripture", user_id=user, cost=61)
    for _ in range(3):                               # nothing was charged
        consume("church_create", user_id=user)
    with pytest.raises(ValueError):
        TokenBucket(3, 60, FakeClock().now).try_take(4)
    with pytest.raises(KeyError):
        consume("lectionry", user_id=user)


def test_idle_entries_pruned():
    clock = FakeClock()
    limiter = RateLimiter(clock.now)
    a, b, c, d = (_user() for _ in range(4))
    limiter.consume("church_create", user_id=a)                  # t=1000
    clock.advance(30)
    limiter.consume("church_create", user_id=b, cost=3)          # t=1030: no sweep yet
    assert len(limiter) == 2
    clock.advance(40)
    limiter.consume("church_create", user_id=c)                  # t=1070: sweep; a is full again
    assert len(limiter) == 2                                     # b (2 tokens) and c
    with pytest.raises(RateLimited) as caught:                   # b kept its state
        limiter.consume("church_create", user_id=b, cost=3)
    assert caught.value.retry_after_seconds == 20
    clock.advance(30)
    limiter.consume("church_create", user_id=d)                  # t=1100: 30 s since the sweep
    assert len(limiter) == 3                                     # b, c, d: no second sweep yet


def _app_with(dependency) -> TestClient:
    app = create_app()

    @app.get("/limited")
    def limited(_rl: None = Depends(dependency)) -> dict:
        return {"ok": True}

    app.dependency_overrides[get_verifier] = lambda: TokenVerifier(
        lambda _token: SIGNING_KEY.public_key(), issuer=ISSUER
    )
    return TestClient(app)


def test_dependency_429_has_retry_after_and_details(tmp_db, limiter_clock, monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://church.example.app")
    settings_mod.get_settings.cache_clear()
    try:
        client = _app_with(rate_limit("church_create"))
        headers = {"Authorization": f"Bearer {make_token(email='a@example.com')}",
                   "Origin": "https://church.example.app"}
        for _ in range(3):
            assert client.get("/limited", headers=headers).status_code == 200
        r = client.get("/limited", headers=headers)
        assert r.status_code == 429
        assert r.json() == {"error": {
            "code": "rate_limited",
            "message": "Too many requests. Try again in 20 seconds.",
            "request_id": r.headers["x-request-id"],
            "details": {"retry_after_seconds": 20},
        }}
        assert r.headers["retry-after"] == "20"
        assert r.headers["access-control-allow-origin"] == "https://church.example.app"
        limiter_clock.advance(20)
        assert client.get("/limited", headers=headers).status_code == 200
    finally:
        settings_mod.get_settings.cache_clear()


def _calls(dependency) -> set:
    found, stack = set(), list(get_dependant(path="/", call=dependency).dependencies)
    while stack:
        dep = stack.pop()
        found.add(dep.call)
        stack.extend(dep.dependencies)
    return found


def test_dependency_trees():
    for name in ("lectionary", "scripture", "church_create", "email"):
        calls = _calls(rate_limit(name))
        assert get_current_user in calls, name
        assert require_church not in calls, name     # user-scoped routes stay user-scoped
    assert {get_current_user, require_church} <= _calls(rate_limit("ai"))
    with pytest.raises(KeyError):
        rate_limit("lectionry")


def test_reset_and_set_clock():
    user = _user()
    clock = FakeClock()
    ratelimit.set_clock_for_tests(clock.now)
    assert ratelimit._limiter.clock == clock.now
    for _ in range(3):
        consume("church_create", user_id=user)
    _rate_limited("church_create", user_id=user)
    ratelimit.set_clock_for_tests(clock.now)             # empties the buckets
    for _ in range(3):
        consume("church_create", user_id=user)
    ratelimit.reset_for_tests()                          # empties them and restores the clock
    assert ratelimit._limiter.clock is time.monotonic
    for _ in range(3):
        consume("church_create", user_id=user)


def test_token_bucket_clamps_negative_elapsed():
    clock = FakeClock(start=5000.0)
    bucket = TokenBucket(3, 60, clock.now)
    assert bucket.try_take(2) == 0.0
    clock.value = 10.0                                   # a swapped clock: far behind
    assert bucket.wait_for(1) == 0.0                     # the one token left is still there
    assert bucket.try_take(1) == 0.0
    assert bucket.wait_for(1) == 20.0
    clock.advance(20)
    assert bucket.try_take(1) == 0.0
