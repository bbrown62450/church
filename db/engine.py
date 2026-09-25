"""SQLAlchemy engine + session plumbing.

One engine is cached per process (`_engine`). Both SQLite (local dev) and
Postgres (Supabase, prod) are driven from the same models, selected by
DATABASE_URL. Tests bypass the env var via reset_engine_for_tests(url).
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


def _make_engine(url: str) -> Engine:
    kwargs = {"pool_pre_ping": True, "future": True}
    if url.startswith("sqlite"):
        # Streamlit reruns across threads; SQLite needs this relaxed.
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        # Retire connections the Supabase pooler may have dropped.
        kwargs["pool_recycle"] = 1800
    return create_engine(url, **kwargs)


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
