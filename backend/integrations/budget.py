"""Process-wide upstream budgets (S "Upstream budgets"; F §2.7, §7.4; slice 2).

Every user shares the Railway IP (bible-api's per-IP limit) and the one ESV
key, so per-user buckets alone do not protect the upstreams. One token
bucket per rule, shared by every request in this process (backend/Procfile
runs a single uvicorn worker). scripture_fetcher calls try_acquire before
each uncached part; a part that finds no token is not sent and becomes
`unavailable`. Imports no FastAPI, Starlette or Streamlit.
"""
import threading
import time
from collections.abc import Callable
from typing import Literal

from token_bucket import TokenBucket

Upstream = Literal["bible_api", "esv"]

# (capacity, per_seconds) for each rule; an acquire needs a token from every rule.
BUDGETS: dict[str, tuple[tuple[int, float], ...]] = {
    "bible_api": ((15, 30.0),),                                   # bible-api.com, per IP
    "esv": ((60, 60.0), (1_000, 3_600.0), (5_000, 86_400.0)),     # Crossway, per key
}

_lock = threading.Lock()
_clock: Callable[[], float] = time.monotonic
_buckets: dict[str, tuple[TokenBucket, ...]] = {}


def try_acquire(upstream: Upstream) -> bool:
    """Take one token from every rule of `upstream` and return True, or take none and return False.

    Never waits. KeyError: an unknown upstream.
    """
    with _lock:
        buckets = _buckets.get(upstream)
        if buckets is None:
            buckets = _buckets[upstream] = tuple(
                TokenBucket(capacity, per_seconds, _clock) for capacity, per_seconds in BUDGETS[upstream]
            )
        if any(b.wait_for(1) > 0 for b in buckets):
            return False
        for b in buckets:
            b.try_take(1)
        return True


def set_clock_for_tests(clock: Callable[[], float]) -> None:
    """Tests: forget every budget (each starts full again) and run them on `clock`
    (a FakeClock's `now`), so a bucket made under one clock is never read under
    another."""
    global _clock
    with _lock:
        _clock = clock
        _buckets.clear()


def reset_for_tests() -> None:
    """Tests: forget every budget (each starts full again) and run them on time.monotonic."""
    set_clock_for_tests(time.monotonic)
