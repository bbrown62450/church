#!/usr/bin/env python3
"""Keep the (free-tier Supabase) database warm.

The free Supabase project pauses after ~7 days idle, so the first visitor each
week would otherwise hit a cold/paused database. A scheduled `SELECT 1` (see
.github/workflows/keepalive.yml) keeps it awake. Standalone: imports no app
modules, so CI needs only SQLAlchemy + a Postgres driver.
"""

import os
import sys

from sqlalchemy import create_engine, text


def ping(database_url: str) -> bool:
    """Open a short-lived connection and run SELECT 1. Returns True on success."""
    if not database_url:
        return False
    try:
        engine = create_engine(database_url, pool_pre_ping=True)
        try:
            with engine.connect() as conn:
                value = conn.execute(text("SELECT 1")).scalar()
            return value == 1
        finally:
            engine.dispose()
    except Exception:
        return False


def main() -> int:
    url = os.getenv("DATABASE_URL", "")
    ok = ping(url)
    print("keepalive: OK" if ok else "keepalive: FAILED",
          file=sys.stdout if ok else sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
