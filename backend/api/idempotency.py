"""Idempotency-Key replays for POST routes (F §1.6; slice 1).

A route that accepts the header reads it with `Depends(idempotency_key())` and
wraps its usecase call in run_idempotent(). The first request with a key runs
the call and stores the response; a repeat with the same key and the same body
gets the stored status and body back with `Idempotent-Replayed: true`; a repeat
with a different body is 422 `idempotency_mismatch`.

What is stored: 2xx responses and DomainError 4xx responses, except
RateLimited (its 429 is returned, the entry dropped, so the same key runs again
after Retry-After). Never a 5xx: a 5xx DomainError drops the entry, and any
other exception drops it and propagates (the app's handlers turn it into a 500).

The store is in memory, keyed by (user_id, church_id, method, route template,
key), with a 15-minute TTL and at most 10 000 entries. church_id is None for a
user-scoped route (POST /churches); a church-scoped route passes the resolved
church (5a-2's POST /services), so a key sent in two churches never replays
one church's answer in the other (F §1.6, church-scope amendment 2026-09-28).
That is enough for one uvicorn worker; if --workers ever exceeds 1, move it to
a Postgres table first (F §1.6).
A request waits on a per-key threading.Lock while an identical one is running,
so run_idempotent must only be called from sync `def` routes (they run in the
threadpool); calling it from an `async def` route would block the event loop.
"""
import hashlib
import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable, Optional

from fastapi import Header
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from api.errors import domain_error_response
from domain_errors import DomainError, InvalidInput, RateLimited

IDEMPOTENCY_HEADER = "Idempotency-Key"
REPLAYED_HEADER = "Idempotent-Replayed"
IDEMPOTENCY_TTL_SECONDS = 15 * 60
MAX_ENTRIES = 10_000

_Key = tuple[uuid.UUID, Optional[uuid.UUID], str, str, uuid.UUID]


def idempotency_key(required: bool = False) -> Callable[..., Optional[uuid.UUID]]:
    """A dependency that reads the Idempotency-Key header as a UUID.

    Absent → None (no idempotency), or 422 "Missing Idempotency-Key header."
    when `required` (5b's POST /bulletin-emails). Not a UUID → 422
    "Idempotency-Key must be a UUID.". Both are `invalid_request` without `fields`.
    """

    def dependency(
        idempotency_key: Optional[str] = Header(default=None, alias=IDEMPOTENCY_HEADER),
    ) -> Optional[uuid.UUID]:
        if idempotency_key is None:
            if required:
                raise InvalidInput("Missing Idempotency-Key header.")
            return None
        try:
            return uuid.UUID(idempotency_key.strip())
        except ValueError:
            raise InvalidInput("Idempotency-Key must be a UUID.") from None

    return dependency


@dataclass
class _Entry:
    """One key's slot. `lock` is held while the first request runs its call."""

    body_hash: str
    lock: threading.Lock = field(default_factory=threading.Lock)
    status: Optional[int] = None          # set once a response is stored
    body: bytes = b""
    expires_at: float = 0.0
    dropped: bool = False                  # removed from the store; waiters must look again


class IdempotencyStore:
    """In-memory idempotency entries (F §1.6): TTL, lazy expiry, bounded size."""

    def __init__(self, *, clock: Callable[[], float] = time.monotonic,
                 ttl: float = IDEMPOTENCY_TTL_SECONDS, max_entries: int = MAX_ENTRIES):
        self.clock = clock
        self.ttl = ttl
        self.max_entries = max_entries
        self._entries: dict[_Key, _Entry] = {}
        self._lock = threading.Lock()

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)

    def clear(self) -> None:
        with self._lock:
            for entry in self._entries.values():
                entry.dropped = True
            self._entries.clear()

    def claim(self, key: _Key, body_hash: str) -> _Entry:
        """The live entry for `key`, or a new one (expired entries are replaced)."""
        with self._lock:
            now = self.clock()
            entry = self._entries.get(key)
            if entry is not None and entry.status is not None and entry.expires_at <= now:
                self._remove(key)
                entry = None
            if entry is None:
                self._make_room(now)
                entry = _Entry(body_hash=body_hash)
                self._entries[key] = entry
            return entry

    def save(self, entry: _Entry, status: int, body: bytes) -> None:
        with self._lock:
            entry.status = status
            entry.body = body
            entry.expires_at = self.clock() + self.ttl

    def drop(self, key: _Key, entry: _Entry) -> None:
        with self._lock:
            if self._entries.get(key) is entry:
                self._remove(key)
            entry.dropped = True

    def _remove(self, key: _Key) -> None:
        self._entries.pop(key).dropped = True

    def _make_room(self, now: float) -> None:
        """Called under the lock before an insert: expired entries go first, then the oldest stored ones."""
        if len(self._entries) < self.max_entries:
            return
        for key in [k for k, e in self._entries.items() if e.status is not None and e.expires_at <= now]:
            self._remove(key)
        for key in [k for k, e in self._entries.items() if e.status is not None]:
            if len(self._entries) < self.max_entries:
                break
            self._remove(key)               # dicts keep insertion order: oldest first


store = IdempotencyStore()


def reset_idempotency_for_tests() -> None:
    """Forget every stored response in the process-wide store."""
    _process_store().clear()


def _process_store() -> IdempotencyStore:
    # run_idempotent's `store` keyword shadows the module attribute of the same name.
    return globals()["store"]


def _body_hash(payload: BaseModel) -> str:
    canonical = json.dumps(payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def run_idempotent(
    *,
    user_id: uuid.UUID,
    route: str,
    key: Optional[uuid.UUID],
    payload: BaseModel,
    status_code: int,
    call: Callable[[], BaseModel],
    method: str = "POST",
    church_id: Optional[uuid.UUID] = None,
    store: Optional[IdempotencyStore] = None,
) -> Response:
    """Run `call` once per (user, church, method, route, key) and replay its response.

    `route` is the route template (e.g. "/churches"), `payload` the parsed
    request body (its SHA-256 over sorted-key JSON is compared on a repeat),
    `status_code` the success status, `church_id` the resolved church of a
    church-scoped route (None: user-scoped). Blocks on a threading.Lock while an
    identical request is running: call it only from sync `def` routes.
    Slice 5b adds a `store_error` keyword (F §1.6).
    """
    if key is None:
        return _success(call(), status_code)
    target = store if store is not None else _process_store()
    scope = (user_id, church_id, method.upper(), route, key)
    body_hash = _body_hash(payload)
    while True:
        entry = target.claim(scope, body_hash)
        with entry.lock:
            if entry.dropped:                  # the first request failed while we waited
                continue
            if entry.body_hash != body_hash:
                raise InvalidInput("This request was already sent with different details.",
                                   code="idempotency_mismatch")
            if entry.status is not None:
                return Response(entry.body, status_code=entry.status, media_type="application/json",
                                headers={REPLAYED_HEADER: "true"})
            try:
                response = _success(call(), status_code)
            except DomainError as exc:
                response = domain_error_response(exc)
                if 400 <= exc.status < 500 and not isinstance(exc, RateLimited):
                    target.save(entry, response.status_code, bytes(response.body))
                else:
                    target.drop(scope, entry)
                return response
            except BaseException:
                target.drop(scope, entry)
                raise
            target.save(entry, response.status_code, bytes(response.body))
            return response


def _success(result: BaseModel, status_code: int) -> JSONResponse:
    return JSONResponse(result.model_dump(mode="json"), status_code=status_code)
