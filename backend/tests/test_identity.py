"""Identity (ops slice, F §2.4): repos.users.ensure_user, the race fix and fewer writes."""
import re
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import event, func, select, update

from db import session_scope
from db.models import User
from repos.users import LAST_SEEN_RESOLUTION, UserRow, ensure_user, get_user_by_email

NOW = datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)


def _utc(value):
    """SQLite hands back naive datetimes; they were written as UTC."""
    return value if value is None or value.tzinfo else value.replace(tzinfo=timezone.utc)


def _stored(email):
    with session_scope() as s:
        return s.execute(select(User).where(User.email == email)).scalar_one()


def _user_count():
    with session_scope() as s:
        return s.execute(select(func.count()).select_from(User)).scalar_one()


@contextmanager
def users_statements(engine):
    """Record every SQL statement on `engine`; yields counts of users INSERT/SELECT/UPDATE."""
    seen = []

    def _record(_conn, _cursor, statement, _params, _context, _executemany):
        seen.append(" ".join(statement.split()))

    counts = {}
    event.listen(engine, "before_cursor_execute", _record)
    try:
        yield counts
    finally:
        event.remove(engine, "before_cursor_execute", _record)
        counts["insert"] = sum(s.startswith("INSERT INTO users ") for s in seen)
        counts["update"] = sum(s.startswith("UPDATE users ") for s in seen)
        counts["select"] = sum(s.startswith("SELECT ") and bool(re.search(r"\bFROM users\b", s))
                               for s in seen)


# --- ensure_user ------------------------------------------------------------

def test_ensure_user_creates_a_normalized_user_stamped_now(tmp_db):
    row = ensure_user("  New.Person@Example.COM ", "New Person", "https://x/p.png", now=NOW)
    assert isinstance(row, UserRow)
    assert row.email == "new.person@example.com"
    assert (row.name, row.picture, row.last_login_at) == ("New Person", "https://x/p.png", NOW)
    user = _stored("new.person@example.com")
    assert user.id == row.id
    assert _utc(user.created_at) == NOW
    assert _utc(user.last_login_at) == NOW
    assert user.google_sub is None                     # the API path never passes it


def test_ensure_user_stores_google_sub_only_when_passed(tmp_db):
    with users_statements(tmp_db) as first:
        ensure_user("streamlit@example.com", google_sub="  google-sub-9 ")
    # The UPDATE writes google_sub, never the INSERT: ON CONFLICT (email) does not
    # cover users_google_sub_key, so concurrent first sign-ins would collide on it.
    assert (first["insert"], first["update"]) == (1, 1)
    assert _stored("streamlit@example.com").google_sub == "google-sub-9"
    ensure_user("streamlit@example.com")               # a later call without it keeps it
    assert _stored("streamlit@example.com").google_sub == "google-sub-9"


def test_ensure_user_is_idempotent_across_case(tmp_db):
    first = ensure_user("Pastor@Example.com", now=NOW)
    second = ensure_user("pastor@EXAMPLE.com", now=NOW)
    assert first.id == second.id
    assert _user_count() == 1


def test_ensure_user_updates_name_and_picture_only_when_truthy_and_different(tmp_db):
    ensure_user("pat@example.com", "Pat", "https://x/1.png", now=NOW)
    with users_statements(tmp_db) as same:
        row = ensure_user("pat@example.com", "Pat", "https://x/1.png", now=NOW)
    assert same["update"] == 0
    with users_statements(tmp_db) as changed:
        row = ensure_user("pat@example.com", "Pat Tor", "https://x/2.png", now=NOW)
    assert changed["update"] == 1                      # one UPDATE for both fields
    assert (row.name, row.picture) == ("Pat Tor", "https://x/2.png")
    user = _stored("pat@example.com")
    assert (user.name, user.picture) == ("Pat Tor", "https://x/2.png")


@pytest.mark.parametrize("falsy", [None, "", "   "])
def test_a_falsy_name_or_picture_never_blanks_the_stored_one(tmp_db, falsy):
    ensure_user("pat@example.com", "Pat", "https://x/1.png", now=NOW)
    row = ensure_user("pat@example.com", falsy, falsy, now=NOW)
    assert (row.name, row.picture) == ("Pat", "https://x/1.png")
    user = _stored("pat@example.com")
    assert (user.name, user.picture) == ("Pat", "https://x/1.png")


def test_last_login_at_is_written_at_most_hourly(tmp_db):
    assert LAST_SEEN_RESOLUTION == timedelta(hours=1)
    ensure_user("pat@example.com", now=NOW)
    with users_statements(tmp_db) as within_the_hour:
        row = ensure_user("pat@example.com", now=NOW + timedelta(minutes=59))
    assert within_the_hour["update"] == 0
    assert row.last_login_at == NOW
    with users_statements(tmp_db) as after_the_hour:
        row = ensure_user("pat@example.com", now=NOW + timedelta(minutes=61))
    assert after_the_hour["update"] == 1
    assert row.last_login_at == NOW + timedelta(minutes=61)
    assert _utc(_stored("pat@example.com").last_login_at) == NOW + timedelta(minutes=61)


def test_a_naive_stored_last_login_at_is_read_as_utc(tmp_db):
    ensure_user("pat@example.com", now=NOW)
    with session_scope() as s:                         # what SQLite (or an old row) holds: no tzinfo
        s.execute(update(User).where(User.email == "pat@example.com")
                  .values(last_login_at=datetime(2026, 9, 25, 11, 30)))
    with users_statements(tmp_db) as thirty_minutes:
        ensure_user("pat@example.com", now=NOW)        # 11:30 UTC is 30 min before NOW
    assert thirty_minutes["update"] == 0
    with users_statements(tmp_db) as sixty_one_minutes:
        ensure_user("pat@example.com", now=NOW + timedelta(minutes=31))
    assert sixty_one_minutes["update"] == 1


@pytest.mark.parametrize("email", ["", "   ", None])
def test_ensure_user_requires_an_email(tmp_db, email):
    with pytest.raises(ValueError, match="email is required"):
        ensure_user(email)
    assert _user_count() == 0


def test_ensure_user_joins_the_callers_transaction(tmp_db):
    with pytest.raises(RuntimeError):
        with session_scope() as s:
            row = ensure_user("tx@example.com", "Tx", session=s)
            assert s.execute(select(User.id).where(User.email == "tx@example.com")).scalar_one() == row.id
            raise RuntimeError("roll back the outer scope")
    assert get_user_by_email("tx@example.com") is None


def test_concurrent_first_calls_create_one_row(tmp_db):
    """F §7.3: the first-request duplicate-email race. Eight threads released
    together all get the same id, and exactly one row exists. (Slice 1 adds a
    @pytest.mark.postgres copy.)"""
    workers = 8
    barrier = threading.Barrier(workers)
    ids, errors = [], []

    def call():
        try:
            barrier.wait(timeout=10)
            ids.append(ensure_user("race@example.com", "Racer").id)
        except Exception as exc:  # noqa: BLE001 - any failure fails the test below
            errors.append(repr(exc))

    threads = [threading.Thread(target=call) for _ in range(workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert errors == []
    assert len(ids) == workers and len(set(ids)) == 1
    assert _user_count() == 1


# --- auth.upsert_from_claims (Streamlit and migrate_to_db.py) -----------------

def test_upsert_from_claims_delegates_to_ensure_user(tmp_db, monkeypatch):
    import auth

    calls = []

    def spy(email, name=None, picture=None, **kwargs):
        calls.append(((email, name, picture), kwargs))
        return ensure_user(email, name, picture, **kwargs)

    monkeypatch.setattr(auth, "ensure_user", spy)
    user_id = auth.upsert_from_claims(
        {"email": " Pastor@Example.com", "sub": "google-sub-1", "name": "Pat Tor", "picture": "http://x/p.png"}
    )
    assert calls == [(("pastor@example.com", "Pat Tor", "http://x/p.png"), {"google_sub": "google-sub-1"})]
    assert _stored("pastor@example.com").id == user_id
