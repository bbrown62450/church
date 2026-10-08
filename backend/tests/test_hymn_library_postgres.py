"""POST /hymns and POST /hymnals on real Postgres (slice 6a-2; 6a spec,
Testing → Postgres): two members adding the same hymn at the same moment get
one hymn and one 409, and two admins adding PH1990 at once get 605 hymns, not
1210, because the duplicate check and the inserts run under the church-row
lock (usecases.hymn_library, through lock_and_read_actor). Adding PH1990 is
also timed: under 10 s (a guard, not a benchmark).

Skipped without TEST_DATABASE_URL; CI's backend-postgres job runs them. As in
test_contacts_postgres.py: the owner signs in through GET /me and the church
is made through repos.churches.create_church on pg_db's engine (the test
catalog is empty, so the church starts with no hymns).
"""
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import func, select

from db import session_scope
from db.models import Hymn
from repos import hymns as hymn_repo
from repos.churches import create_church
from tests.api_helpers import auth_headers, church_headers
from usecases import hymn_library

pytestmark = pytest.mark.postgres

OWNER = "owner@example.com"


@pytest.fixture
def pg_client(pg_db):
    from tests.api_helpers import make_api_client

    return make_api_client()


def _church(client, name="Grace") -> uuid.UUID:
    r = client.get("/me", headers=auth_headers(OWNER))
    assert r.status_code == 200, r.text
    return create_church(name=name, timezone="America/New_York", owner_user_id=uuid.UUID(r.json()["user"]["id"]))


@pytest.fixture
def church(pg_client) -> uuid.UUID:
    return _church(pg_client)


def _post_hymn(client, church, title, number):
    return client.post("/hymns", headers=church_headers(OWNER, church), json={"title": title, "number": number})


def _add_hymnal(client, church):
    return client.post("/hymnals", headers=church_headers(OWNER, church), json={"code": "PH1990"})


def _count(church, **where) -> int:
    with session_scope() as s:
        return s.execute(select(func.count()).select_from(Hymn).where(
            Hymn.church_id == church, *[getattr(Hymn, k) == v for k, v in where.items()])).scalar_one()


def test_a_second_add_of_one_hymn_waits_for_the_first_and_gets_a_409(pg_client, church, monkeypatch):
    inside, release = threading.Event(), threading.Event()
    real = hymn_repo.find_duplicate
    calls = []

    def held(*args, **kwargs):
        calls.append(args)
        if len(calls) == 1:
            inside.set()                   # the first add holds the church-row lock here
            assert release.wait(10), "the test never released the first add"
        return real(*args, **kwargs)

    monkeypatch.setattr(hymn_repo, "find_duplicate", held)
    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(_post_hymn, pg_client, church, "Be Thou My Vision", 339)
        assert inside.wait(10), "the first add never took the lock"
        second = pool.submit(_post_hymn, pg_client, church, "be thou my vision", 339)
        threading.Event().wait(1)          # time for the second add to finish if nothing held it
        assert not second.done(), "the second add did not wait for the church-row lock"
        release.set()
        responses = [first.result(10), second.result(10)]
    assert [r.status_code for r in responses] == [201, 409]
    assert responses[1].json()["error"]["message"] == "GG2013 already has #339 be thou my vision."
    assert _count(church, number=339) == 1


def test_two_adds_of_one_hymn_at_once_make_one_hymn_twenty_times(pg_client, church, monkeypatch):
    barrier = threading.Barrier(2)
    real = hymn_library.lock_and_read_actor

    def together(*args, **kwargs):
        barrier.wait(timeout=10)
        return real(*args, **kwargs)

    monkeypatch.setattr(hymn_library, "lock_and_read_actor", together)
    for round_ in range(20):
        title = f"Hymn {round_}"
        with ThreadPoolExecutor(2) as pool:
            responses = list(pool.map(lambda t: _post_hymn(pg_client, church, t, round_ + 1), [title, title.upper()]))
        assert sorted(r.status_code for r in responses) == [201, 409], f"round {round_}"
        assert _count(church, number=round_ + 1) == 1, f"round {round_}"


def test_two_adds_of_ph1990_at_once_make_605_hymns(pg_client, church, monkeypatch):
    barrier = threading.Barrier(2)
    real = hymn_library.lock_and_read_actor

    def together(*args, **kwargs):
        barrier.wait(timeout=10)
        return real(*args, **kwargs)

    monkeypatch.setattr(hymn_library, "lock_and_read_actor", together)
    with ThreadPoolExecutor(2) as pool:
        responses = list(pool.map(lambda _: _add_hymnal(pg_client, church), range(2)))
    assert [r.status_code for r in responses] == [200, 200]
    assert sorted(r.json()["inserted"] for r in responses) == [0, 605]
    assert _count(church, hymnal="PH1990") == 605


def test_adding_ph1990_takes_under_ten_seconds(pg_client, church):
    started = time.monotonic()
    r = _add_hymnal(pg_client, church)
    elapsed = time.monotonic() - started
    assert (r.status_code, r.json()["inserted"]) == (200, 605)
    assert elapsed < 10, f"POST /hymnals took {elapsed:.1f} s"
