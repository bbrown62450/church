import pytest
from sqlalchemy import Engine, text


def test_public_imports_are_reexported():
    # `from db import ...` must expose the whole surface (Task 3 imports Base from here).
    from db import (  # noqa: F401
        Base, get_engine, SessionLocal, session_scope,
        get_session, init_db, reset_engine_for_tests,
    )


def test_get_session_is_session_scope_alias():
    from db import get_session, session_scope
    assert get_session is session_scope


def test_reset_engine_returns_engine_and_binds_directly(tmp_path):
    from db import reset_engine_for_tests, SessionLocal
    url = f"sqlite:///{tmp_path / 'e.db'}"
    engine = reset_engine_for_tests(url)
    assert isinstance(engine, Engine)
    # SessionLocal is rebound to the engine reset_engine_for_tests created.
    assert SessionLocal().get_bind() is engine


def test_session_scope_commits_on_success(tmp_path):
    from db import reset_engine_for_tests, session_scope
    reset_engine_for_tests(f"sqlite:///{tmp_path / 'c.db'}")
    with session_scope() as s:
        s.execute(text("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)"))
        s.execute(text("INSERT INTO t (v) VALUES ('a')"))
    with session_scope() as s:  # a NEW session must see the committed row
        row = s.execute(text("SELECT v FROM t")).fetchone()
    assert row[0] == "a"


def test_session_scope_rolls_back_on_exception(tmp_path):
    from db import reset_engine_for_tests, session_scope
    reset_engine_for_tests(f"sqlite:///{tmp_path / 'r.db'}")
    with session_scope() as s:
        s.execute(text("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)"))
    with pytest.raises(RuntimeError):
        with session_scope() as s:
            s.execute(text("INSERT INTO t (v) VALUES ('b')"))
            raise RuntimeError("boom")
    with session_scope() as s:
        count = s.execute(text("SELECT COUNT(*) FROM t")).fetchone()
    assert count[0] == 0
