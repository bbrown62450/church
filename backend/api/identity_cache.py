"""Process-local identity cache in front of repos.users.ensure_user (F §2.4).

Used only by api.deps.get_current_user. Keyed by normalized email; holds the
user id plus the name and picture as stored after the last ensure_user, so an
unchanged profile needs no database work for up to `ttl` seconds.

Success-only by construction: the only value ever stored is the result of an
ensure_user call that returned. There is no failure entry, so a database error
can never be remembered as an identity (F §2.7).

Deliberately not backend/cache.py: slice 2 owns that module (TTLCache with
get_or_load and CacheableFailure), whose interface does not fit a lookup that
must compare the incoming profile before deciding to load.
"""
import threading
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class CachedIdentity:
    user_id: uuid.UUID
    name: Optional[str]      # as stored after the last ensure_user
    picture: Optional[str]


class IdentityCache:
    """Thread-safe LRU map with a TTL. One lock guards an OrderedDict."""

    def __init__(self, maxsize: int = 1024, ttl: float = 300.0,
                 *, clock: Callable[[], float] = time.monotonic):
        if maxsize < 1:
            raise ValueError("maxsize must be >= 1")
        self._maxsize = maxsize
        self._ttl = ttl
        self._clock = clock
        self._lock = threading.Lock()
        self._entries: "OrderedDict[str, tuple[float, CachedIdentity]]" = OrderedDict()

    def get(self, email: str) -> Optional[CachedIdentity]:
        """The cached identity, or None when absent or expired (expired entries are dropped)."""
        with self._lock:
            entry = self._entries.get(email)
            if entry is None:
                return None
            expires_at, identity = entry
            if self._clock() >= expires_at:
                del self._entries[email]
                return None
            self._entries.move_to_end(email)
            return identity

    def put(self, email: str, identity: CachedIdentity) -> None:
        with self._lock:
            self._entries[email] = (self._clock() + self._ttl, identity)
            self._entries.move_to_end(email)
            while len(self._entries) > self._maxsize:
                self._entries.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)
