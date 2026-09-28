"""A continuous-refill token bucket (S "Rate-limit buckets", "Upstream budgets"; slice 2).

Pure arithmetic on an injected clock. api/ratelimit.py (per-user and
per-church buckets) and integrations/budget.py (process-wide upstream
budgets) both build on it. It holds no lock: each owner takes its own lock
around wait_for and try_take, so a check across several buckets is
all-or-nothing. Imports no FastAPI, Starlette or Streamlit.
"""
from collections.abc import Callable


class TokenBucket:
    """`capacity` tokens, refilled continuously at capacity per `per_seconds`.

    A new bucket is full. Elapsed time is clamped at 0, so a clock that moves
    backwards (a test that swaps clocks) never removes tokens. Rates are
    applied as capacity / per_seconds and waits as missing * per_seconds /
    capacity, so whole-number limits give whole-number waits (3 per 60 s:
    exactly 20 s for one token).
    """

    def __init__(self, capacity: float, per_seconds: float, clock: Callable[[], float]):
        if capacity <= 0 or per_seconds <= 0:
            raise ValueError("capacity and per_seconds must be positive")
        self.capacity = float(capacity)
        self.per_seconds = float(per_seconds)
        self._clock = clock
        self._tokens = self.capacity
        self._last = clock()

    def _refill(self) -> None:
        now = self._clock()
        elapsed = max(0.0, now - self._last)
        self._tokens = min(self.capacity, self._tokens + elapsed * self.capacity / self.per_seconds)
        self._last = now

    def _check(self, n: float) -> None:
        if n <= 0 or n > self.capacity:
            raise ValueError(f"n must be between 0 (exclusive) and the capacity {self.capacity:g}")

    def wait_for(self, n: float = 1) -> float:
        """0.0 when n tokens are available now, else the seconds until they are. Takes none."""
        self._check(n)
        self._refill()
        missing = n - self._tokens
        return 0.0 if missing <= 0 else missing * self.per_seconds / self.capacity

    def try_take(self, n: float = 1) -> float:
        """Take n tokens and return 0.0, or take nothing and return the wait (wait_for)."""
        wait = self.wait_for(n)
        if wait == 0.0:
            self._tokens -= n
        return wait

    def is_full(self) -> bool:
        """True when the bucket has refilled to capacity (the limiter prunes these)."""
        self._refill()
        return self._tokens >= self.capacity
