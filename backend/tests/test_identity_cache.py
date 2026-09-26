"""api.identity_cache: the private, success-only identity cache (ops slice, F §2.4)."""
import threading
import uuid

from api.identity_cache import CachedIdentity, IdentityCache
from tests.conftest import FakeClock


def _identity(name="Pat"):
    return CachedIdentity(user_id=uuid.uuid4(), name=name, picture=None)


def test_get_returns_the_identity_before_the_ttl_and_none_after():
    clock = FakeClock()
    cache = IdentityCache(maxsize=10, ttl=300, clock=clock.now)
    pat = _identity()
    cache.put("pat@example.com", pat)
    clock.advance(299)
    assert cache.get("pat@example.com") == pat
    clock.advance(2)                                     # 301 s after the put
    assert cache.get("pat@example.com") is None
    assert len(cache) == 0                               # the expired entry was dropped
    assert cache.get("nobody@example.com") is None


def test_the_least_recently_used_entry_is_evicted():
    cache = IdentityCache(maxsize=2, ttl=300)
    cache.put("a@example.com", _identity("A"))
    cache.put("b@example.com", _identity("B"))
    cache.put("c@example.com", _identity("C"))           # maxsize + 1
    assert len(cache) == 2
    assert cache.get("a@example.com") is None
    assert cache.get("b@example.com").name == "B"
    assert cache.get("c@example.com").name == "C"


def test_get_refreshes_recency():
    cache = IdentityCache(maxsize=2, ttl=300)
    cache.put("a@example.com", _identity("A"))
    cache.put("b@example.com", _identity("B"))
    assert cache.get("a@example.com").name == "A"        # a is now the most recent
    cache.put("c@example.com", _identity("C"))
    assert cache.get("b@example.com") is None
    assert cache.get("a@example.com").name == "A"


def test_clear_empties_the_cache():
    cache = IdentityCache()
    cache.put("a@example.com", _identity())
    cache.put("b@example.com", _identity())
    cache.clear()
    assert len(cache) == 0
    assert cache.get("a@example.com") is None


def test_concurrent_puts_and_gets_are_safe():
    cache = IdentityCache(maxsize=64, ttl=300)
    errors = []

    def work(worker):
        try:
            for i in range(1000):
                email = f"user{(worker * 7 + i) % 100}@example.com"
                if i % 2:
                    cache.put(email, _identity())
                else:
                    cache.get(email)
        except Exception as exc:  # noqa: BLE001 - any failure fails the test below
            errors.append(repr(exc))

    threads = [threading.Thread(target=work, args=(n,)) for n in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    assert len(cache) <= 64
