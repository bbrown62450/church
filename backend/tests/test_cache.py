"""cache.TTLCache: TTLs for values and CacheableFailures, LRU, single-flight
per key, uncached exceptions (F §2.7; S New modules "cache.py", Testing
"test_cache.py"; 2a clarification 36).

Threaded tests gate the loader on a threading.Event (never time.sleep), set
it in `finally`, and join their threads before returning."""
import threading
import traceback

import pytest

from cache import CacheableFailure, TTLCache
from tests.conftest import FakeClock


class Down(CacheableFailure):
    """A failure the cache stores for ttl_fail."""


class Boom(Exception):
    """An unexpected loader error: never stored."""


def _counting(result):
    """A loader returning `result` (or raising it, if it is an exception) and
    counting its calls in .calls."""
    def loader():
        loader.calls += 1
        if isinstance(result, BaseException):
            raise result
        return result
    loader.calls = 0
    return loader


def _run(results, name, cache, key, loader):
    """Thread body: store get_or_load's value, or the exception it raised."""
    try:
        results[name] = cache.get_or_load(key, loader)
    except BaseException as exc:   # the test asserts on it
        results[name] = exc


def test_ok_value_cached_until_ttl_ok():
    clock = FakeClock()
    cache = TTLCache(maxsize=4, ttl_ok=100, ttl_fail=10, clock=clock.now)
    first, second = _counting("v1"), _counting("v2")
    assert cache.get_or_load("k", first) == "v1"
    clock.advance(99.5)
    assert cache.get_or_load("k", second) == "v1"      # still fresh
    assert (first.calls, second.calls) == (1, 0)
    clock.advance(0.5)                                  # exactly ttl_ok after the store
    assert cache.get_or_load("k", second) == "v2"
    assert second.calls == 1


def test_none_and_empty_values_cached():
    cache = TTLCache(maxsize=4, ttl_ok=100, ttl_fail=10, clock=FakeClock().now)
    none_loader, empty_loader = _counting(None), _counting([])
    for _ in range(3):
        assert cache.get_or_load("none", none_loader) is None
        assert cache.get_or_load("empty", empty_loader) == []
    assert (none_loader.calls, empty_loader.calls) == (1, 1)


def test_cacheable_failure_cached_for_ttl_fail_and_reraised():
    clock = FakeClock()
    cache = TTLCache(maxsize=4, ttl_ok=100, ttl_fail=10, clock=clock.now)
    failure = Down("upstream 500")
    failing, fine = _counting(failure), _counting("ok")
    with pytest.raises(Down) as first:
        cache.get_or_load("k", failing)
    assert first.value is failure
    depths = []
    for _ in range(2):
        clock.advance(4)                                # 4 s, then 8 s: inside ttl_fail
        with pytest.raises(Down) as hit:
            cache.get_or_load("k", fine)
        assert hit.value is failure
        depths.append(len(traceback.extract_tb(hit.value.__traceback__)))
    assert depths[0] == depths[1]                       # a hit never grows the traceback
    assert (failing.calls, fine.calls) == (1, 0)
    clock.advance(2)                                    # 10 s: ttl_fail is over
    assert cache.get_or_load("k", fine) == "ok"
    assert fine.calls == 1

    # ttl_fail=0 (the bible-api part cache) never stores a failure.
    uncached = TTLCache(maxsize=4, ttl_ok=100, ttl_fail=0, clock=clock.now)
    for _ in range(2):
        with pytest.raises(Down):
            uncached.get_or_load("k", failing)
    assert failing.calls == 3


def test_other_exception_not_cached():
    cache = TTLCache(maxsize=4, ttl_ok=100, ttl_fail=10, clock=FakeClock().now)
    boom, fine = _counting(Boom("bug")), _counting("fine")
    with pytest.raises(Boom):
        cache.get_or_load("k", boom)
    assert cache.get_or_load("k", fine) == "fine"       # the next call loads again
    assert (boom.calls, fine.calls) == (1, 1)


def test_lru_evicts_least_recent():
    with pytest.raises(ValueError):
        TTLCache(maxsize=0, ttl_ok=100, ttl_fail=10)
    cache = TTLCache(maxsize=2, ttl_ok=100, ttl_fail=10, clock=FakeClock().now)
    cache.get_or_load("a", _counting("A"))
    cache.get_or_load("b", _counting("B"))
    cache.get_or_load("a", _counting("unused"))         # a hit makes "a" most recent
    cache.get_or_load("c", _counting("C"))              # evicts "b"
    kept, evicted = _counting("A2"), _counting("B2")
    assert cache.get_or_load("a", kept) == "A"
    assert cache.get_or_load("b", evicted) == "B2"
    assert (kept.calls, evicted.calls) == (0, 1)


def test_single_flight_one_loader_per_key():
    cache = TTLCache(maxsize=4, ttl_ok=100, ttl_fail=10, clock=FakeClock().now)
    started, release = threading.Event(), threading.Event()

    def slow():
        slow.calls += 1
        started.set()
        release.wait(5)
        return "v"
    slow.calls = 0
    second = _counting("second loader")
    results = {}
    leader = threading.Thread(target=_run, args=(results, "leader", cache, "k", slow))
    waiter = threading.Thread(target=_run, args=(results, "waiter", cache, "k", second))
    try:
        leader.start()
        assert started.wait(5)
        waiter.start()
        waiter.join(0.2)
        assert waiter.is_alive()                        # waiting on the leader's flight
    finally:
        release.set()
        leader.join(5)
        waiter.join(5)
    assert results == {"leader": "v", "waiter": "v"}
    assert (slow.calls, second.calls) == (1, 0)


def test_different_keys_load_concurrently():
    cache = TTLCache(maxsize=4, ttl_ok=100, ttl_fail=10, clock=FakeClock().now)
    started, release = threading.Event(), threading.Event()

    def slow():
        started.set()
        release.wait(5)
        return "A"
    results = {}
    a = threading.Thread(target=_run, args=(results, "a", cache, "a", slow))
    b = threading.Thread(target=_run, args=(results, "b", cache, "b", _counting("B")))
    try:
        a.start()
        assert started.wait(5)
        b.start()
        b.join(5)
        assert not b.is_alive()                         # "b" did not wait for "a"
        assert results == {"b": "B"}
    finally:
        release.set()
        a.join(5)
        b.join(5)
    assert results == {"a": "A", "b": "B"}


def test_uncached_exception_shared_by_waiters_then_retried():
    cache = TTLCache(maxsize=4, ttl_ok=100, ttl_fail=10, clock=FakeClock().now)
    started, release = threading.Event(), threading.Event()

    def slow():
        slow.calls += 1
        started.set()
        release.wait(5)
        raise Boom("bug")
    slow.calls = 0
    second = _counting("second loader")
    results = {}
    leader = threading.Thread(target=_run, args=(results, "leader", cache, "k", slow))
    waiter = threading.Thread(target=_run, args=(results, "waiter", cache, "k", second))
    try:
        leader.start()
        assert started.wait(5)
        waiter.start()
        waiter.join(0.2)
        assert waiter.is_alive()                        # waiting on the leader's flight
    finally:
        release.set()
        leader.join(5)
        waiter.join(5)
    assert isinstance(results["leader"], Boom)
    assert results["waiter"] is results["leader"]       # the leader's exception, shared
    assert (slow.calls, second.calls) == (1, 0)
    third = _counting("third")
    assert cache.get_or_load("k", third) == "third"     # nothing was stored
    assert third.calls == 1


def test_clear():
    cache = TTLCache(maxsize=4, ttl_ok=100, ttl_fail=10, clock=FakeClock().now)
    cache.get_or_load("a", _counting("A"))
    with pytest.raises(Down):
        cache.get_or_load("b", _counting(Down("down")))
    cache.clear()
    again_a, again_b = _counting("A2"), _counting("B2")
    assert cache.get_or_load("a", again_a) == "A2"
    assert cache.get_or_load("b", again_b) == "B2"
    assert (again_a.calls, again_b.calls) == (1, 1)
