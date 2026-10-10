"""Check every church for the problems slice 6b's rules forbid (read-only).

Run from backend/ with DATABASE_URL exported in the same shell (the laptop
setup of backend/migrations/README.md, "Production runbook"):

    ../.venv/bin/python scripts/check_integrity.py

Prints one line per problem found by repos.integrity.find_violations: its
kind, the church id and a count (or the invite id), never an email, a name or
an invite code; or "OK: no integrity violations." Exit status: 0 when there
is none, 1 when there is one, 2 when DATABASE_URL is not set. It only reads.
The `Database:` line goes to stderr and never shows the username or
password. backend/migrations/README.md, "Church integrity", says what to do
with each kind.
"""
import argparse
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))   # run as a file, sys.path[0] is backend/scripts

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

from api.startup import describe_database  # noqa: E402
from db.engine import _normalize_url  # noqa: E402
from repos.integrity import find_violations  # noqa: E402

OK = "OK: no integrity violations."


def format_violation(v: dict) -> str:
    """One line: the kind, then church=<id> and the kind's count or invite id."""
    extra = {"owner_count": lambda: f" owners={v['owners']}",
             "no_admin": lambda: "",
             "invite_role": lambda: f" invite={v['invite_id']}",
             "pending_duplicate": lambda: f" invites={v['invites']}"}[v["kind"]]()
    return f"{v['kind']} church={v['church_id']}{extra}"


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args(argv)
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        return 2
    engine = create_engine(_normalize_url(url), poolclass=NullPool)
    print(f"Database: {describe_database(engine.url)}", file=sys.stderr)
    try:
        with Session(engine) as session:
            violations = find_violations(session=session)
    finally:
        engine.dispose()
    for v in violations:
        print(format_violation(v))
    if not violations:
        print(OK)
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
