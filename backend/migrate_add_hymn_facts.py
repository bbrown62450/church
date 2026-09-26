#!/usr/bin/env python3
"""One-off migration: add `text_year` and `hymnal_count` to hymns and
hymn_catalog on an existing database.

Fresh databases get the columns from Base.metadata.create_all. Run this against
the deployed Postgres BEFORE merging code that maps these columns: the
Streamlit app and the API both select every mapped column and would fail
without them. Idempotent: it adds only the missing columns, so it is safe to
re-run and also works on SQLite (which lacks ADD COLUMN IF NOT EXISTS). It
first prints the database it is about to change, password hidden.

    python migrate_add_hymn_facts.py
"""
from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import inspect, text  # noqa: E402

from db import get_engine  # noqa: E402

TABLES = ("hymns", "hymn_catalog")
COLUMNS = {"text_year": "INTEGER", "hymnal_count": "INTEGER"}


def run(engine=None) -> list:
    """Add any missing columns. Returns the "table.column" names added."""
    engine = engine or get_engine()
    added = []
    with engine.begin() as conn:
        inspector = inspect(conn)
        for table in TABLES:
            existing = {c["name"] for c in inspector.get_columns(table)}
            for column, sql_type in COLUMNS.items():
                if column not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}"))
                    added.append(f"{table}.{column}")
    return added


def main() -> None:
    engine = get_engine()
    # Name the target first: a wrong DATABASE_URL (or a backend/.env picked up
    # when none is exported) prints the same "already present" as a correct run.
    print("Database:", engine.url.render_as_string(hide_password=True))
    added = run(engine)
    print("Added: " + ", ".join(added) if added else "OK — columns already present.")


if __name__ == "__main__":
    main()
