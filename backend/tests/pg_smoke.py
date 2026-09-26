"""Postgres smoke test for the ops-2 identity code (run by CI's backend-postgres job).

ON CONFLICT (email), the 3 + 3 pool and the Streamlit multi-tab race only exist
on Postgres (SQLite serializes writers), so the SQLite suite cannot exercise
them. Run from the repo root against a THROWAWAY database:

    DATABASE_URL=postgresql://postgres:<pw>@localhost:5432/postgres \
        python backend/tests/pg_smoke.py

It refuses to run against anything but a local Postgres, so it can never touch
production. Not collected by pytest (the file name does not start with test_).
"""
import sys
import threading
from urllib.parse import urlsplit

sys.path[:0] = [".", "backend"]

import os  # noqa: E402

from sqlalchemy import func, select  # noqa: E402

from db import get_engine, init_db, session_scope  # noqa: E402
from db.models import User  # noqa: E402
from repos.users import ensure_user  # noqa: E402

RACERS = 8


def _require_local_postgres() -> None:
    url = os.environ.get("DATABASE_URL", "")
    parts = urlsplit(url)
    if not parts.scheme.startswith("postgres") or parts.hostname not in ("localhost", "127.0.0.1"):
        sys.exit("pg_smoke: DATABASE_URL must point at a local, throwaway Postgres.")


def race(email, **kwargs):
    """RACERS concurrent first calls for one new email: (distinct ids, errors)."""
    barrier = threading.Barrier(RACERS)
    ids, errors = [], []

    def call():
        try:
            barrier.wait(timeout=10)
            ids.append(ensure_user(email, "Racer", **kwargs).id)
        except Exception as exc:  # noqa: BLE001
            errors.append(repr(exc))

    threads = [threading.Thread(target=call) for _ in range(RACERS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return set(ids), errors


def main() -> int:
    _require_local_postgres()
    init_db()
    api_ids, api_errors = race("race@example.com")                              # API path: no google_sub
    st_ids, st_errors = race("tabs@example.com", google_sub="google-sub-tabs")  # Streamlit, several tabs
    row = ensure_user("RACE@example.com", "Racer Two")
    with session_scope() as s:
        count = s.execute(select(func.count()).select_from(User)).scalar_one()
        sub = s.execute(select(User.google_sub).where(User.email == "tabs@example.com")).scalar_one()
    engine = get_engine()
    result = (engine.dialect.name, engine.pool.size(), api_errors + st_errors, len(api_ids), len(st_ids),
              count, sub, row.name, row.id in api_ids)
    print(*result)
    expected = ("postgresql", 3, [], 1, 1, 2, "google-sub-tabs", "Racer Two", True)
    if result != expected:
        print(f"pg_smoke: FAILED, expected {expected}", file=sys.stderr)
        return 1
    print("pg_smoke: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
