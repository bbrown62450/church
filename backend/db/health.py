"""Database readiness probe behind GET /health/ready (ops slice S3).

database_ready() answers "can this process reach the database right now?" with
one `SELECT 1` through the process engine, so it exercises the real pool. The
route is public, so the answer is memoized and single-flight: however many
requests arrive, at most one probe (one pooled connection) runs at a time, and
a result is reused for READY_OK_TTL seconds after a success or READY_FAIL_TTL
after a failure. A caller that waits on the lock waits for at most one probe.
connect_timeout (10 s, db/engine.py) and statement_timeout (5 s) bound most
of that probe, but not all of it: checkout can wait pool_timeout (30 s) for a
free pooled connection, and pool_pre_ping has no timeout of its own. A slow
database can therefore hold threadpool workers; slice 2's rate limiter caps
that exposure.

The SQL and the try/except live here, not in the route (the recorded
exception to F §2.2 in the ops spec's API section). No FastAPI import.
"""
import logging
import threading
import time
from typing import Callable, Optional

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from db.engine import get_engine

logger = logging.getLogger(__name__)

READY_OK_TTL = 10.0     # seconds a success is reused
READY_FAIL_TTL = 5.0    # seconds a failure is reused

_lock = threading.Lock()
_last: Optional[tuple[bool, float]] = None          # (ok, expires_at)


def database_ready(*, clock: Callable[[], float] = time.monotonic) -> bool:
    """True when the database answered `SELECT 1` recently (memoized, single-flight)."""
    global _last
    with _lock:                                  # single-flight: one probe, so at most one pooled connection
        if _last is not None and clock() < _last[1]:
            return _last[0]
        ok = _probe()
        _last = (ok, clock() + (READY_OK_TTL if ok else READY_FAIL_TTL))
        return ok


def _probe() -> bool:
    try:
        with get_engine().connect() as conn:
            if conn.dialect.name == "postgresql":
                # Inside the transaction SQLAlchemy has begun, so LOCAL applies.
                conn.exec_driver_sql("SET LOCAL statement_timeout = '5s'")
            conn.execute(text("SELECT 1")).scalar_one()
        return True
    except SQLAlchemyError as exc:
        # The class name only: driver messages can contain host names.
        logger.warning("Readiness check failed: %s", type(exc).__name__)
        return False


def reset_readiness_for_tests() -> None:
    """Forget the memoized result (backend/tests/conftest.py, before each test)."""
    global _last
    with _lock:
        _last = None
