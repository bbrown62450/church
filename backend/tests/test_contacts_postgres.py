"""POST /contacts on real Postgres (slice 5b-1; 6a spec, Testing → Postgres):
two admins adding the same address at the same moment get one contact and
one 409, because the duplicate check and the insert run under the church-row
lock (usecases.contacts, through lock_and_read_actor).

Skipped without TEST_DATABASE_URL; CI's backend-postgres job runs them. The
SQLite fixtures cannot be used here: the owner signs in through GET /me and
the church is made through repos.churches.create_church on pg_db's engine.

- The held lock: the first request's duplicate check (email_contacts.
  email_exists, which usecases.contacts calls through the module attribute
  after taking the lock) waits until the test lets it go; the second request
  must still be waiting a second later. Without the lock it would finish.
- The barrier (the 6a spec's test): both requests wait for each other just
  before the lock, 20 times over, each round with a new address in two cases.
A request that never reaches the wrapper makes the test fail after 10 s
instead of passing vacuously.
"""
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import func, select

import email_contacts
from db import session_scope
from db.models import Contact
from repos.churches import create_church
from tests.api_helpers import auth_headers, church_headers
from usecases import contacts

pytestmark = pytest.mark.postgres

OWNER = "owner@example.com"


@pytest.fixture
def pg_client(pg_db):
    from tests.api_helpers import make_api_client

    return make_api_client()


@pytest.fixture
def church(pg_client) -> uuid.UUID:
    r = pg_client.get("/me", headers=auth_headers(OWNER))
    assert r.status_code == 200, r.text
    return create_church(name="Grace", timezone="America/New_York", owner_user_id=uuid.UUID(r.json()["user"]["id"]))


def _post(client, church, email):
    return client.post("/contacts", headers=church_headers(OWNER, church), json={"email": email})


def _rows(church, address) -> int:
    with session_scope() as s:
        return s.execute(select(func.count()).select_from(Contact).where(
            Contact.church_id == church, func.lower(Contact.email) == address)).scalar_one()


def test_a_second_add_waits_for_the_first_and_gets_a_409(pg_client, church, monkeypatch):
    inside, release = threading.Event(), threading.Event()
    real = email_contacts.email_exists
    calls = []

    def held(*args, **kwargs):
        calls.append(args)
        if len(calls) == 1:
            inside.set()                   # the first add holds the church-row lock here
            assert release.wait(10), "the test never released the first add"
        return real(*args, **kwargs)

    monkeypatch.setattr(email_contacts, "email_exists", held)
    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(_post, pg_client, church, "mary@example.org")
        assert inside.wait(10), "the first add never took the lock"
        second = pool.submit(_post, pg_client, church, "MARY@example.org")
        threading.Event().wait(1)          # time for the second add to finish if nothing held it
        assert not second.done(), "the second add did not wait for the church-row lock"
        release.set()
        responses = [first.result(10), second.result(10)]
    assert [r.status_code for r in responses] == [201, 409]
    assert responses[1].json()["error"]["message"] == "That email is already in your contacts."
    assert _rows(church, "mary@example.org") == 1


def test_two_adds_of_one_address_at_once_make_one_contact_twenty_times(pg_client, church, monkeypatch):
    barrier = threading.Barrier(2)
    real = contacts.lock_and_read_actor

    def together(*args, **kwargs):
        barrier.wait(timeout=10)
        return real(*args, **kwargs)

    monkeypatch.setattr(contacts, "lock_and_read_actor", together)
    for round_ in range(20):
        address = f"mary{round_}@example.org"
        with ThreadPoolExecutor(2) as pool:
            responses = list(pool.map(lambda email: _post(pg_client, church, email), [address, address.upper()]))
        assert sorted(r.status_code for r in responses) == [201, 409], f"round {round_}"
        assert _rows(church, address) == 1, f"round {round_}"
