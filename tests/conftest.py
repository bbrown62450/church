"""Shared pytest fixtures for the multi-church test suite.

Created once (Task 1); later tasks MODIFY this file, never re-create it.

Design note: db-layer imports live INSIDE each fixture body (deferred), not at
module top level. That keeps this conftest collectable before db/ exists, and
lets every later task's tests depend on a single canonical set of factories.
"""
import uuid

import pytest


@pytest.fixture
def tmp_db(tmp_path):
    """Fresh, isolated SQLite database for one test.

    Binds the engine DIRECTLY via reset_engine_for_tests (not os.environ),
    creates all tables via init_db, and enforces FK ON DELETE on SQLite so
    later cascade/tenancy tests behave like Postgres. Yields the Engine.
    """
    from sqlalchemy import event

    from db import reset_engine_for_tests, init_db

    url = f"sqlite:///{tmp_path / 'test.db'}"
    engine = reset_engine_for_tests(url)

    if engine.dialect.name == "sqlite":
        @event.listens_for(engine, "connect")
        def _enable_sqlite_fks(dbapi_conn, _rec):  # pragma: no cover - driver hook
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

    init_db()
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def make_user(tmp_db):
    """Factory: insert a users row, return its id (uuid.UUID)."""
    from db import session_scope
    from db.models import User

    def _make(email="person@example.com", *, name="Person",
              google_sub=None, picture=None):
        user_id = uuid.uuid4()
        with session_scope() as s:
            s.add(User(
                id=user_id,
                email=email.strip().lower(),
                name=name,
                google_sub=google_sub,
                picture=picture,
            ))
        return user_id

    return _make


@pytest.fixture
def make_church(tmp_db, make_user):
    """Factory: insert a churches row + owner membership; return church id (uuid.UUID).

    When owner_user_id is None, a fresh owner user is created. owner_user_id is a
    uuid.UUID user id (as returned by make_user).
    """
    from db import session_scope
    from db.models import Church, Membership

    def _make(name="First Church", timezone="America/New_York", owner_user_id=None):
        if owner_user_id is None:
            owner_user_id = make_user(email=f"owner-{uuid.uuid4().hex[:8]}@example.com")
        church_id = uuid.uuid4()
        with session_scope() as s:
            s.add(Church(id=church_id, name=name, timezone=timezone))
            s.flush()  # persist the church before its FK-referencing membership
            s.add(Membership(church_id=church_id, user_id=owner_user_id, role="owner"))
        return church_id

    return _make


@pytest.fixture
def seed_catalog(tmp_db):
    """Factory: insert n HymnCatalog rows with scripture_refs + theme populated.

    Returns the number of rows inserted.
    """
    from db import session_scope
    from db.models import HymnCatalog

    def _seed(n=3):
        with session_scope() as s:
            for i in range(1, n + 1):
                s.add(HymnCatalog(
                    title=f"Hymn {i}",
                    number=i,
                    scripture_refs=f"John {i}:1-{i + 2}",
                    theme="praise, grace",
                    hymnary_link=f"https://hymnary.org/hymn/{i}",
                    audio_url=None,
                ))
        return n

    return _seed
