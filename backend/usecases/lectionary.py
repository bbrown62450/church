"""Readings for one date from the two lectionary sources (S `usecases/lectionary.py`).

Lectio (keyed by the date) and Vanderbilt (keyed by the liturgical-year file)
load in parallel on one module-level pool, each through its own TTLCache: a
success, including a definitive 404, is kept 24 h; a SourceFailed 5 min;
anything else is a bug and is not kept (cache.py). Both sources share one
20 s deadline (clarification 31). Any date is looked up as itself: no
normalization and no nearest row (spec decision 8). No database access.
"""
from __future__ import annotations

import dataclasses
import logging
import time
from concurrent.futures import Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from datetime import date
from typing import Callable, Literal, Optional, TypeVar

from cache import TTLCache
from domain_errors import InvalidInput, UpstreamError, UpstreamTimeout
from vanderbilt_lectionary import (
    LectioDay,
    ReadingSet,
    SourceFailed,
    VRow,
    fits_draft_limits,
    liturgical_year_for,
    load_lectio,
    load_vanderbilt_year,
    merge,
    vanderbilt_sets_on,
)

logger = logging.getLogger(__name__)

LECTIONARY_UNREACHABLE = (
    "The lectionary couldn't be reached. Enter readings yourself, "
    "or try again in a few minutes."
)
DATE_OUT_OF_RANGE = "Enter a date between 1900 and 2199."
MIN_YEAR = 1900
MAX_YEAR = 2199

DEADLINE_SECONDS = 20.0       # read at call time, so tests can monkeypatch it
OK_TTL_SECONDS = 86_400.0     # 24 h
FAIL_TTL_SECONDS = 300.0      # 5 min
MAX_WORKERS = 4

T = TypeVar("T")


def _new_pool() -> ThreadPoolExecutor:
    return ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="lectionary")


def _new_lectio_cache(clock: Callable[[], float]) -> TTLCache[date, Optional[LectioDay]]:
    return TTLCache(maxsize=512, ttl_ok=OK_TTL_SECONDS, ttl_fail=FAIL_TTL_SECONDS, clock=clock)


def _new_vanderbilt_cache(clock: Callable[[], float]) -> TTLCache[str, list[VRow]]:
    return TTLCache(maxsize=8, ttl_ok=OK_TTL_SECONDS, ttl_fail=FAIL_TTL_SECONDS, clock=clock)


_POOL = _new_pool()
_LECTIO = _new_lectio_cache(time.monotonic)
_VANDERBILT = _new_vanderbilt_cache(time.monotonic)


@dataclass(frozen=True)
class LectionaryResult:
    date: date                                   # the requested date, never normalized
    status: Literal["ok", "no_readings"]
    partial: bool                                # sets found, but one source failed
    reading_sets: list[ReadingSet]               # [] when status == "no_readings"
    default_index: Optional[int]                 # None iff reading_sets == []


@dataclass(frozen=True)
class _Outcome:
    value: object                                # what the cache returned; None on failure
    failure: Optional[SourceFailed]
    cached: bool                                 # True when this request ran no loader


def _load(cache: TTLCache, key: object, loader: Callable[[], T]) -> _Outcome:
    """Run in a pool worker. Only SourceFailed becomes an outcome; any other
    exception is re-raised by Future.result() in the request thread (a 500)."""
    ran = False

    def run() -> T:
        nonlocal ran
        ran = True
        return loader()

    try:
        value = cache.get_or_load(key, run)
    except SourceFailed as e:
        return _Outcome(value=None, failure=e, cached=not ran)
    return _Outcome(value=value, failure=None, cached=not ran)


def _outcome(future: Future) -> _Outcome:
    """The source's outcome, or a timeout failure for this request only when
    the source is unfinished at the deadline. The running loader carries on
    and caches its own outcome (clarification 31)."""
    if future.done():
        return future.result()
    return _Outcome(value=None, failure=SourceFailed(timeout=True), cached=False)


def readings_for_date(d: date) -> LectionaryResult:
    """The reading sets for exactly `d` (S Status rules).

    Raises InvalidInput for a year outside 1900–2199, UpstreamTimeout when no
    set was found and every failed source timed out, and UpstreamError when
    no set was found and a source failed otherwise."""
    if not MIN_YEAR <= d.year <= MAX_YEAR:
        raise InvalidInput(DATE_OUT_OF_RANGE, field="date")
    started = time.monotonic()
    year = liturgical_year_for(d)
    lectio_future = _POOL.submit(_load, _LECTIO, d, lambda: load_lectio(d))
    vanderbilt_future = _POOL.submit(_load, _VANDERBILT, year, lambda: load_vanderbilt_year(year))
    wait((lectio_future, vanderbilt_future), timeout=DEADLINE_SECONDS)
    lectio = _outcome(lectio_future)
    vanderbilt = _outcome(vanderbilt_future)

    day: Optional[LectioDay] = lectio.value  # type: ignore[assignment]
    groups = tuple(g for g in day.groups if fits_draft_limits(g)) if day is not None else ()
    fitting_day = dataclasses.replace(day, groups=groups) if groups else None
    on_date = vanderbilt_sets_on(vanderbilt.value or [], d)  # type: ignore[arg-type]
    v_sets = [s for s in on_date if fits_draft_limits(s)]
    sets, default_index = merge(fitting_day, v_sets, d)
    failures = [o.failure for o in (lectio, vanderbilt) if o.failure is not None]

    logger.info(
        "lectionary_lookup date=%s lectio=%s vanderbilt=%s lectio_cached=%s "
        "vanderbilt_cached=%s sets=%d duration_ms=%d",
        d.isoformat(),
        "failed" if lectio.failure else ("ok" if day is not None else "none"),
        "failed" if vanderbilt.failure else ("ok" if on_date else "none"),
        lectio.cached,
        vanderbilt.cached,
        len(sets),
        round((time.monotonic() - started) * 1000),
    )

    if sets:
        return LectionaryResult(d, "ok", bool(failures), sets, default_index)
    if failures:
        if all(f.timeout for f in failures):
            raise UpstreamTimeout(LECTIONARY_UNREACHABLE, code="upstream_timeout")
        raise UpstreamError(LECTIONARY_UNREACHABLE, code="upstream_error")
    return LectionaryResult(d, "no_readings", False, [], None)


def reset_for_tests(clock: Callable[[], float] = time.monotonic) -> None:
    """Join the pool, then start over with a new pool and new, empty caches on
    `clock` (clarification 39). Queued work is cancelled; a running worker is
    waited for, so no straggler from an earlier test holds a worker or writes
    into this test's caches."""
    global _POOL, _LECTIO, _VANDERBILT
    _POOL.shutdown(wait=True, cancel_futures=True)
    _POOL = _new_pool()
    _LECTIO = _new_lectio_cache(clock)
    _VANDERBILT = _new_vanderbilt_cache(clock)
