"""Compare the database at DATABASE_URL with this release's models (runbook step 6).

Run from backend/ with DATABASE_URL exported in the same shell:

    ../.venv/bin/python scripts/schema_drift.py

Prints `revision: <current> head: <head> state: <state>`, then one line per
difference between the database and db/models.py (db.schema_check.format_diff),
sorted. Exit status: 0 when there is no difference, 1 when there is one, 2 when
DATABASE_URL is not set. Unlike `alembic check`, it also works on a database
that is not at head (production stamped at 0001_baseline). It only reads: no
DDL, no writes. The `Database:` line goes to stderr and never shows the
username or password.
"""
import argparse
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))   # run as a file, sys.path[0] is backend/scripts

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

from api.startup import describe_database  # noqa: E402
from db.engine import _normalize_url  # noqa: E402
from db.schema_check import format_diff, revision_state, schema_diff  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args(argv)
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        return 2
    engine = create_engine(_normalize_url(url), poolclass=NullPool)
    print(f"Database: {describe_database(engine.url)}", file=sys.stderr)
    try:
        with engine.connect() as conn:
            state = revision_state(conn)
            diff = schema_diff(conn)
    finally:
        engine.dispose()
    print(f"revision: {state.current} head: {state.head} state: {state.state}")
    for line in format_diff(diff):
        print(line)
    return 1 if diff else 0


if __name__ == "__main__":
    sys.exit(main())
