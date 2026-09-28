"""TTL cache with single-flight loading (F §2.7; S New modules "cache.py").

TTLCache(maxsize, ttl_ok, ttl_fail, clock) is thread-safe, evicts the least
recently used entry beyond `maxsize`, and loads through get_or_load(key,
loader):
- an ok hit returns the stored value (None and [] are values too);
- a failure hit re-raises the stored CacheableFailure;
- a miss is single-flight per key: one caller (the leader) runs the loader
  while later callers for the same key wait for it; other keys load in
  parallel. The leader's return value is stored for ttl_ok seconds. A
  CacheableFailure it raises is stored for ttl_fail seconds and re-raised.
  Any other exception is stored nowhere: it is re-raised to the leader and to
  every waiter of that flight, and the next call runs the loader again
  (S :888; 2a clarification 36).
A TTL of 0 stores nothing (the bible-api part cache uses ttl_fail=0).

An error is never stored as an empty success (F §2.7): a loader reports a
failure worth remembering by raising a CacheableFailure subclass
(vanderbilt_lectionary.SourceFailed, slice 2).

A loader must not call get_or_load for its own key (it would wait on itself).
clear() drops every stored entry; a load already in flight still stores its
result when it finishes. Modules that own a cache rebuild it as a new object
in their reset_for_tests (2a clarification 39).

Not api/identity_cache.py: that cache compares the incoming profile before it
decides to load, which get_or_load does not fit.

No FastAPI, no Streamlit (tests/test_no_streamlit_in_core.py).
"""
import threading
import time
from collections import OrderedDict
from typing import Callable, Generic, Hashable, TypeVar

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")

_MISSING = object()   # "no value": lets None and [] be stored as values


class CacheableFailure(Exception):
    """A loader failure to remember for the cache's ttl_fail (for example an
    upstream answering 500), so the upstream is not asked again at once."""


class _Flight:
    """One in-progress load of one key; waiters block on `done`."""

    __slots__ = ("done", "value", "error")

    def __init__(self) -> None:
        self.done = threading.Event()
        self.value: object = _MISSING
        self.error: BaseException | None = None


class TTLCache(Generic[K, V]):
    """Thread-safe LRU cache with separate TTLs for values and CacheableFailures."""

    def __init__(self, maxsize: int, ttl_ok: float, ttl_fail: float,
                 clock: Callable[[], float] = time.monotonic):
        if maxsize < 1:
            raise ValueError("maxsize must be >= 1")
        self._maxsize = maxsize
        self._ttl_ok = ttl_ok
        self._ttl_fail = ttl_fail
        self._clock = clock
        self._lock = threading.Lock()
        # key -> (expires_at, value, failure); failure is None for a stored value
        self._entries: "OrderedDict[K, tuple[float, object, CacheableFailure | None]]" = OrderedDict()
        self._flights: dict[K, _Flight] = {}

    def get_or_load(self, key: K, loader: Callable[[], V]) -> V:
        with self._lock:
            entry = self._entries.get(key)
            if entry is not None:
                expires_at, value, failure = entry
                if self._clock() < expires_at:
                    self._entries.move_to_end(key)
                    if failure is not None:
                        # A fresh traceback each time: re-raising the stored
                        # object would otherwise grow its traceback on every hit.
                        raise failure.with_traceback(None)
                    return value  # type: ignore[return-value]
                del self._entries[key]
            flight = self._flights.get(key)
            leader = flight is None
            if leader:
                flight = _Flight()
                self._flights[key] = flight

        if not leader:
            flight.done.wait()
            if flight.error is not None:
                raise flight.error
            return flight.value  # type: ignore[return-value]

        try:
            value = loader()
        except CacheableFailure as failure:
            self._settle(key, flight, error=failure, ttl=self._ttl_fail)
            raise
        except BaseException as exc:
            self._settle(key, flight, error=exc, ttl=0)
            raise
        self._settle(key, flight, value=value, ttl=self._ttl_ok)
        return value

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def _settle(self, key: K, flight: _Flight, *, value: object = _MISSING,
                error: BaseException | None = None, ttl: float) -> None:
        """Record the leader's outcome, store it when ttl > 0, end the flight."""
        flight.value = value
        flight.error = error
        with self._lock:
            try:
                if ttl > 0:
                    self._entries[key] = (self._clock() + ttl, value, error)
                    self._entries.move_to_end(key)
                    while len(self._entries) > self._maxsize:
                        self._entries.popitem(last=False)
            finally:
                # Always end the flight, or its waiters and every later
                # caller for this key would block forever.
                if self._flights.get(key) is flight:
                    del self._flights[key]
                flight.done.set()
