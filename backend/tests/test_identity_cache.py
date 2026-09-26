"""api.identity_cache: the private, success-only identity cache (ops slice, F §2.4)."""
import sys
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
    """Without the lock, a get() can read an entry that another thread's put()
    then evicts, and move_to_end/del raises KeyError. At the default 5 ms switch
    interval threads rarely interleave inside one call, so this test forces
    switches every microsecond and starts all threads together; with the lock
    patched out it then fails most runs."""
    cache = IdentityCache(maxsize=64, ttl=300)
    errors = []
    start = threading.Barrier(8)

    def work(worker):
        try:
            start.wait()
            for i in range(1000):
                email = f"user{(worker * 7 + i) % 100}@example.com"
                if i % 2:
                    cache.put(email, _identity())
                else:
                    cache.get(email)
        except Exception as exc:  # noqa: BLE001 - any failure fails the test below
            errors.append(repr(exc))

    threads = [threading.Thread(target=work, args=(n,)) for n in range(8)]
    old_interval = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)
    try:
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    finally:
        sys.setswitchinterval(old_interval)
    assert errors == []
    assert len(cache) == 64      # all 100 emails were put, so the cache is exactly full


def test_a_failed_ensure_user_is_never_cached(tmp_db, monkeypatch):
    """Success-only: a database error propagates as a 500 and caches nothing;
    the next request runs ensure_user again."""
    from fastapi.testclient import TestClient
    from sqlalchemy.exc import OperationalError

    import api.deps
    from api.deps import get_verifier
    from api.main import create_app
    from api.security import TokenVerifier
    from repos.users import ensure_user
    from tests.jwt_helpers import ISSUER, SIGNING_KEY, make_token

    app = create_app()
    app.dependency_overrides[get_verifier] = lambda: TokenVerifier(
        lambda _token: SIGNING_KEY.public_key(), issuer=ISSUER)
    client = TestClient(app, raise_server_exceptions=False)
    headers = {"Authorization": f"Bearer {make_token(email='pastor@example.com')}"}

    def database_down(*_args, **_kwargs):
        raise OperationalError("INSERT INTO users ...", {}, Exception("server closed the connection"))

    monkeypatch.setattr(api.deps, "ensure_user", database_down)
    r = client.get("/me", headers=headers)
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "internal_error"
    assert len(api.deps._identity_cache) == 0

    calls = []

    def recovered(*args, **kwargs):
        calls.append(args)
        return ensure_user(*args, **kwargs)

    monkeypatch.setattr(api.deps, "ensure_user", recovered)
    r = client.get("/me", headers=headers)
    assert r.status_code == 200
    assert len(calls) == 1
    assert len(api.deps._identity_cache) == 1
