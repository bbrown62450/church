"""SQLAlchemy engine + session plumbing.

One engine is cached per process (`_engine`). Both SQLite (local dev) and
Postgres (Supabase, prod) are driven from the same models, selected by
DATABASE_URL. Tests bypass the env var via reset_engine_for_tests(url).

The Postgres pool is read from DB_POOL_SIZE / DB_MAX_OVERFLOW (defaults 3 and
3) when the engine is created. The API, the Streamlit app and the CLIs that
call get_engine() or session_scope() use this engine, and they share the
Supabase session pooler (docs/ops-runbook.md → Platform limits). keepalive.py
builds its own engine and does not get these settings.
"""
import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

# Cached engine (module global). Rebound by get_engine / reset_engine_for_tests.
_engine = None

# Bound lazily; reconfigured whenever the engine changes.
SessionLocal = sessionmaker(autoflush=False, expire_on_commit=False)


def _database_url() -> str:
    return os.environ.get("DATABASE_URL", "sqlite:///data/church.db")


def _normalize_url(url: str) -> str:
    """Pin bare Postgres URLs to psycopg2, the driver we install.

    SQLAlchemy 2.1 made psycopg (v3) the default for ``postgresql://``, and
    Supabase hands out bare ``postgresql://`` connection strings.
    """
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg2://" + url[len(prefix):]
    return url


# Postgres pool per process. The Supabase session pooler's Pool Size is 15
# (Nano), shared by the API and the Streamlit app: 2 x (3 + 3) + 2 = 14 <= 15.
# backend/tests/test_ops_workflows.py checks these against docs/ops-runbook.md.
DEFAULT_POOL_SIZE = 3
DEFAULT_MAX_OVERFLOW = 3


def _int_env(name: str, default: int, *, minimum: int) -> int:
    """An integer setting from the environment; blank or unset means `default`."""
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        value = None
    if value is None or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum} (got '{raw}').")
    return value


def _engine_kwargs(url: str) -> dict:
    """create_engine() keyword arguments for `url`; opens no connection, so tests inspect it."""
    kwargs = {"pool_pre_ping": True, "future": True}
    if url.startswith("sqlite"):
        # FastAPI runs sync routes in a threadpool; SQLite needs this relaxed.
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs["pool_size"] = _int_env("DB_POOL_SIZE", DEFAULT_POOL_SIZE, minimum=1)
        kwargs["max_overflow"] = _int_env("DB_MAX_OVERFLOW", DEFAULT_MAX_OVERFLOW, minimum=0)
        # Retire connections the Supabase pooler may have dropped.
        kwargs["pool_recycle"] = 1800
        # Without it libpq waits for the OS TCP timeout (minutes) when the
        # pooler is unreachable, tying up a threadpool worker.
        kwargs["connect_args"] = {"connect_timeout": 10}
    return kwargs


def _make_engine(url: str) -> Engine:
    url = _normalize_url(url)
    return create_engine(url, **_engine_kwargs(url))


def get_engine() -> Engine:
    """Return the process-wide engine, creating it (from DATABASE_URL) once."""
    global _engine
    if _engine is None:
        _engine = _make_engine(_database_url())
        SessionLocal.configure(bind=_engine)
    return _engine


def reset_engine_for_tests(url: str) -> Engine:
    """Dispose any existing engine and bind a fresh one directly from `url`.

    Does NOT touch os.environ — the url is used verbatim. Returns the Engine.
    """
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = _make_engine(url)
    SessionLocal.configure(bind=_engine)
    return _engine


def init_db() -> None:
    """Create all tables. Imports models so every table is registered on Base."""
    from db import models  # noqa: F401  (registers all mappers on Base.metadata)
    Base.metadata.create_all(bind=get_engine())


@contextmanager
def session_scope():
    """Transactional scope: commit on success, rollback on error, always close."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# Canonical alias — some call sites read better as `with get_session() as s:`.
get_session = session_scope
