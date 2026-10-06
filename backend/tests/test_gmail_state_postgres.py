"""The Gmail connect's CSRF state on real Postgres (slice 5b-2; build review I1):
two consumes of one state at the same moment give the user id once.

Skipped without TEST_DATABASE_URL; CI's backend-postgres job runs it.

The first consume is held inside its transaction (after its delete, before
the commit; the old read-then-delete code was held after its read) while the
second runs in another thread and its own connection. With the delete as the
read, the second waits for the first's row lock and then finds nothing; the
old code let the second read the same row and both returned the user. A
consume that never reaches the hold makes the test fail after 10 s instead
of passing vacuously.
"""
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager

import pytest

import google_oauth
from db import session_scope
from db.models import OAuthState, User

pytestmark = pytest.mark.postgres


def _user() -> uuid.UUID:
    user_id = uuid.uuid4()
    with session_scope() as s:
        s.add(User(id=user_id, email="owner@example.com"))
    return user_id


def test_two_consumes_of_one_state_give_the_user_once(pg_db, monkeypatch):
    uid = _user()
    state = google_oauth.create_state(uid)
    real_scope = google_oauth.session_scope
    inside, release = threading.Event(), threading.Event()
    held = threading.Lock()
    first_taken = []

    def hold():
        inside.set()
        assert release.wait(10), "the test never released the first consume"

    @contextmanager
    def held_scope():
        with held:
            is_first = not first_taken
            first_taken.append(True)
        with real_scope() as session:
            if is_first:
                real_get, real_execute = session.get, session.execute

                def get(*args, **kwargs):
                    row = real_get(*args, **kwargs)
                    hold()
                    return row

                def execute(statement, *args, **kwargs):
                    result = real_execute(statement, *args, **kwargs)
                    if getattr(statement, "is_delete", False):
                        result = result.freeze()             # read before the hold, as the caller would
                        hold()
                        return result()
                    return result

                session.get, session.execute = get, execute
            yield session

    monkeypatch.setattr(google_oauth, "session_scope", held_scope)
    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(google_oauth.consume_state, state)
        assert inside.wait(10), "the first consume never reached the hold"
        second = pool.submit(google_oauth.consume_state, state)
        threading.Event().wait(1)          # time for the second consume to finish if nothing held it
        release.set()
        results = [first.result(10), second.result(10)]
    assert results.count(uid) == 1, results
    assert None in results
    with session_scope() as s:
        assert s.get(OAuthState, state) is None
