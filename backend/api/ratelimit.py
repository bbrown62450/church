"""Per-user and per-church rate limits (F §1.8; S "Rate-limit buckets"; slice 2).

In-memory token buckets keyed by (bucket, rule index, scope id), in this one
process: backend/Procfile runs a single uvicorn worker. Refill is continuous
(backend/token_bucket.py).

- consume(bucket, *, user_id, church_id=None, cost=1) charges every rule of
  the bucket all-or-nothing. When a rule is short it charges nothing and
  raises domain_errors.RateLimited, never ApiError (F §1.5, §2.2). The
  DomainError handler adds Retry-After and details.retry_after_seconds, and
  run_idempotent never stores it, so a limiter 429 is never replayed.
- check(...) takes the same arguments and raises as consume would, but
  charges nothing (slice 5b-2b: the bulletin email peeks before it builds
  its files and charges only right before Google).
- rate_limit(name) is the FastAPI dependency that calls consume(name,
  cost=1). It depends on get_current_user, plus require_church when the
  bucket has a church rule (only `ai`), so user-scoped routes stay free of
  require_church (test_route_guards). The church id comes from the resolved
  ActiveChurch, never the raw header. Routes whose cost depends on the
  request (/scripture/passages) call consume themselves after validation.
- reset_for_tests() and set_clock_for_tests(clock): backend/tests/conftest.py.

This is the one API-layer module of the slice 2 platform: it may import
FastAPI (the dependency); consume itself needs none of it.
"""
import math
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from fastapi import Depends

from api.deps import ActiveChurch, CurrentUser, get_current_user, require_church
from domain_errors import RateLimited
from token_bucket import TokenBucket


@dataclass(frozen=True)
class Rule:
    """One limit of a bucket: `capacity` tokens per `per_seconds`, per user or per church."""

    scope: Literal["user", "church"]
    capacity: int
    per_seconds: float


# F §1.8 plus S's `lectionary` addition. Wired in 2a: lectionary, scripture,
# church_create. ai: slices 3 and 4, PR #7, PR #8. email: slice 5b. picture:
# printed bulletin PR 3a (POST /bulletin-images). gmail_connect: slice 5b-2
# (POST /gmail-connection/auth-url; a new consent URL and state per request).
BUCKETS: dict[str, tuple[Rule, ...]] = {
    "lectionary": (Rule("user", 120, 300),),
    "scripture": (Rule("user", 60, 300),),
    "church_create": (Rule("user", 3, 60),),
    "ai": (Rule("user", 40, 600), Rule("church", 400, 86_400)),
    "email": (Rule("user", 10, 3_600),),
    "picture": (Rule("user", 20, 3_600), Rule("church", 60, 86_400)),
    "gmail_connect": (Rule("user", 10, 600),),
}

MESSAGE = "Too many requests. Try again in {n} seconds."

# At most one sweep of idle (full) buckets per this many seconds of the clock.
PRUNE_EVERY_SECONDS = 60.0


class RateLimiter:
    """Token buckets keyed by (bucket, rule index, scope id), behind one lock."""

    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self.clock = clock
        self._lock = threading.Lock()
        self._buckets: dict[tuple[str, int, uuid.UUID], TokenBucket] = {}
        self._last_prune = clock()

    def __len__(self) -> int:
        """How many buckets are held (pruning drops full ones)."""
        with self._lock:
            return len(self._buckets)

    def consume(self, bucket: str, *, user_id: uuid.UUID,
                church_id: uuid.UUID | None = None, cost: int = 1) -> None:
        self._charge(bucket, user_id, church_id, cost, take=True)

    def check(self, bucket: str, *, user_id: uuid.UUID,
              church_id: uuid.UUID | None = None, cost: int = 1) -> None:
        """Raise RateLimited when consume would; take nothing either way."""
        self._charge(bucket, user_id, church_id, cost, take=False)

    def _charge(self, bucket: str, user_id: uuid.UUID, church_id: uuid.UUID | None, cost: int, *,
                take: bool) -> None:
        rules = BUCKETS[bucket]                          # KeyError: no such bucket
        if cost < 1:
            raise ValueError("cost must be at least 1")
        keys: list[tuple[tuple[str, int, uuid.UUID], Rule]] = []
        for index, rule in enumerate(rules):
            scope_id = user_id if rule.scope == "user" else church_id
            if scope_id is None:
                raise ValueError(f"the {bucket!r} bucket has a church rule: pass church_id")
            if cost > rule.capacity:
                raise ValueError(f"cost {cost} exceeds the {bucket!r} capacity {rule.capacity}")
            keys.append(((bucket, index, scope_id), rule))
        with self._lock:
            self._prune_if_due()
            held = [self._bucket(key, rule) for key, rule in keys]
            wait = max(b.wait_for(cost) for b in held)
            if wait > 0:
                n = max(1, math.ceil(wait))              # once: message and header agree
                raise RateLimited(MESSAGE.format(n=n), retry_after_seconds=n)
            if take:
                for b in held:
                    b.try_take(cost)

    def _bucket(self, key: tuple[str, int, uuid.UUID], rule: Rule) -> TokenBucket:
        found = self._buckets.get(key)
        if found is None:
            found = self._buckets[key] = TokenBucket(rule.capacity, rule.per_seconds, self.clock)
        return found

    def _prune_if_due(self) -> None:
        now = self.clock()
        if now - self._last_prune < PRUNE_EVERY_SECONDS:
            return
        self._last_prune = now
        for key in [key for key, b in self._buckets.items() if b.is_full()]:
            del self._buckets[key]


# Read as a module attribute on every call, so the test hooks can swap it.
_limiter = RateLimiter()


def consume(bucket: str, *, user_id: uuid.UUID,
            church_id: uuid.UUID | None = None, cost: int = 1) -> None:
    """Charge `cost` tokens to every rule of `bucket`, or raise RateLimited and charge nothing.

    KeyError: an unknown bucket. ValueError: a church rule without
    church_id, cost < 1, or cost above a rule's capacity.
    """
    _limiter.consume(bucket, user_id=user_id, church_id=church_id, cost=cost)


def check(bucket: str, *, user_id: uuid.UUID,
          church_id: uuid.UUID | None = None, cost: int = 1) -> None:
    """Raise RateLimited when `consume` with the same arguments would, and charge nothing.

    For a request that does costly work before the charge (the bulletin email
    builds its files, then charges right before Google): a caller at the limit
    is refused before that work. The same errors as `consume`.
    """
    _limiter.check(bucket, user_id=user_id, church_id=church_id, cost=cost)


def rate_limit(name: str) -> Callable[..., None]:
    """A dependency that charges one token of `name` to the caller (and church).

    Raises KeyError now for an unknown name, so a misspelled bucket fails when
    the route module is imported, not on every request.
    """
    rules = BUCKETS[name]
    if any(rule.scope == "church" for rule in rules):
        def church_rate_limit(
            user: CurrentUser = Depends(get_current_user),
            church: ActiveChurch = Depends(require_church),
        ) -> None:
            consume(name, user_id=user.id, church_id=church.id)

        return church_rate_limit

    def user_rate_limit(user: CurrentUser = Depends(get_current_user)) -> None:
        consume(name, user_id=user.id)

    return user_rate_limit


def set_clock_for_tests(clock: Callable[[], float]) -> None:
    """Tests: a new limiter on `clock` (a FakeClock's `now`) that holds no buckets,
    so every caller starts full. A bucket made under one clock is never read
    under another."""
    global _limiter
    _limiter = RateLimiter(clock)


def reset_for_tests() -> None:
    """Tests: a new limiter on time.monotonic that holds no buckets."""
    set_clock_for_tests(time.monotonic)
