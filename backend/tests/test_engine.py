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


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("postgresql://u:p@h:5432/db", "postgresql+psycopg2://u:p@h:5432/db"),
        ("postgres://u:p@h:5432/db", "postgresql+psycopg2://u:p@h:5432/db"),
        ("postgresql+psycopg2://u:p@h/db", "postgresql+psycopg2://u:p@h/db"),
        ("sqlite:///data/app.db", "sqlite:///data/app.db"),
    ],
)
def test_postgres_urls_pin_the_installed_psycopg2_driver(raw, expected):
    """SQLAlchemy 2.1 made psycopg (v3) the default for bare postgresql:// URLs;
    we install psycopg2, so bare URLs must be pinned to it."""
    from db.engine import _normalize_url

    assert _normalize_url(raw) == expected


def test_bare_postgres_url_builds_a_psycopg2_engine():
    from db.engine import _make_engine

    engine = _make_engine("postgresql://u:p@localhost:5432/db")  # no connection is opened
    try:
        assert engine.dialect.driver == "psycopg2"
    finally:
        engine.dispose()


# --- Postgres pool and connect timeout (ops slice, F §2.6 item 6) -------------
# The Supabase session pooler's Pool Size is 15 (Nano), so the defaults are
# 3 + 3: 2 x (3 + 3) + 2 = 14 <= 15 (docs/ops-runbook.md -> Platform limits).

PG_URL = "postgresql://u:p@h/db"


@pytest.fixture
def pool_env(monkeypatch):
    """No DB_POOL_SIZE / DB_MAX_OVERFLOW from the developer's shell; tests set them."""
    monkeypatch.delenv("DB_POOL_SIZE", raising=False)
    monkeypatch.delenv("DB_MAX_OVERFLOW", raising=False)
    return monkeypatch


def test_postgres_engine_kwargs_default_to_the_pooler_budget(pool_env):
    from db.engine import _engine_kwargs

    kwargs = _engine_kwargs(PG_URL)
    assert kwargs["pool_size"] == 3
    assert kwargs["max_overflow"] == 3
    assert kwargs["pool_recycle"] == 1800
    assert kwargs["pool_pre_ping"] is True
    assert kwargs["connect_args"] == {"connect_timeout": 10}


def test_pool_settings_come_from_the_environment(pool_env):
    from db.engine import _engine_kwargs

    pool_env.setenv("DB_POOL_SIZE", "2")
    pool_env.setenv("DB_MAX_OVERFLOW", "0")
    kwargs = _engine_kwargs(PG_URL)
    assert (kwargs["pool_size"], kwargs["max_overflow"]) == (2, 0)


def test_blank_pool_settings_use_the_defaults(pool_env):
    from db.engine import _engine_kwargs

    pool_env.setenv("DB_POOL_SIZE", "")
    pool_env.setenv("DB_MAX_OVERFLOW", "  ")
    kwargs = _engine_kwargs(PG_URL)
    assert (kwargs["pool_size"], kwargs["max_overflow"]) == (3, 3)


@pytest.mark.parametrize("name, value, message", [
    ("DB_POOL_SIZE", "abc", "DB_POOL_SIZE must be an integer >= 1 (got 'abc')."),
    ("DB_POOL_SIZE", "0", "DB_POOL_SIZE must be an integer >= 1 (got '0')."),
    ("DB_MAX_OVERFLOW", "-1", "DB_MAX_OVERFLOW must be an integer >= 0 (got '-1')."),
    ("DB_MAX_OVERFLOW", "2.5", "DB_MAX_OVERFLOW must be an integer >= 0 (got '2.5')."),
])
def test_invalid_pool_settings_raise_at_engine_creation(pool_env, name, value, message):
    from db.engine import _make_engine

    pool_env.setenv(name, value)
    with pytest.raises(ValueError) as exc:
        _make_engine(PG_URL)
    assert str(exc.value) == message


def test_sqlite_engine_kwargs_have_no_pool_size(pool_env):
    from db.engine import _engine_kwargs

    pool_env.setenv("DB_POOL_SIZE", "abc")          # ignored: SQLite never reads it
    kwargs = _engine_kwargs("sqlite:///data/app.db")
    assert "pool_size" not in kwargs and "max_overflow" not in kwargs
    assert kwargs["connect_args"] == {"check_same_thread": False}
    assert kwargs["pool_pre_ping"] is True


def test_postgres_engine_uses_the_pool_size_without_connecting(pool_env):
    from db.engine import _make_engine

    engine = _make_engine("postgresql://u:p@localhost:5432/db")   # no connection is opened
    try:
        assert engine.pool.size() == 3
    finally:
        engine.dispose()
