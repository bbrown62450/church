#!/usr/bin/env python3
"""One-off migration: add the `hymnal` column to hymns + hymn_catalog on an
existing (pre-hymnal-dimension) database.

Fresh databases get the column from Base.metadata.create_all, so this is only
needed for databases created before the hymnal feature (e.g. the deployed
Postgres). Idempotent and Postgres-oriented (ADD COLUMN IF NOT EXISTS).

    python migrate_add_hymnal.py
"""
from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import text  # noqa: E402
from db import get_engine  # noqa: E402


def run():
    engine = get_engine()
    with engine.begin() as conn:
        for table in ("hymns", "hymn_catalog"):
            conn.execute(text(
                f"ALTER TABLE {table} "
                "ADD COLUMN IF NOT EXISTS hymnal VARCHAR NOT NULL DEFAULT 'GG2013'"
            ))
    print("OK — 'hymnal' column ensured on hymns and hymn_catalog "
          "(existing rows backfilled to 'GG2013').")


if __name__ == "__main__":
    run()
