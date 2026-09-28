"""Reconcile an existing database with the 0001 baseline (F §3.2 item 3).

Only guarded, idempotent adds, so this is a no-op on a fresh database (0001
created everything) and on production (stamped at 0001_baseline) except
creating the index if runbook step 6 reports it missing:

- ix_hymns_church_hymnal, which migrate_add_hymnal.py never created;
- text_year and hymnal_count (INTEGER, nullable) on hymns and hymn_catalog,
  only where missing (amendment 2026-09-26). This fixes a local database made
  by create_all before PR #4 and then stamped at 0001_baseline. On Postgres it
  is ADD COLUMN IF NOT EXISTS, which also renders in offline --sql mode; SQLite
  has no IF NOT EXISTS for columns, so there an inspector check decides.

Replaces migrate_add_hymnal.py and migrate_add_hymn_facts.py (deleted).

Revision ID: 0002_reconcile
Revises: 0001_baseline
Create Date: 2026-09-26
"""
from alembic import context, op
import sqlalchemy as sa

revision = "0002_reconcile"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None

HYMN_FACT_TABLES = ("hymns", "hymn_catalog")
HYMN_FACT_COLUMNS = ("text_year", "hymnal_count")


def upgrade() -> None:
    op.create_index("ix_hymns_church_hymnal", "hymns", ["church_id", "hymnal"], if_not_exists=True)

    if op.get_context().dialect.name == "postgresql":
        for table in HYMN_FACT_TABLES:
            for column in HYMN_FACT_COLUMNS:
                op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} INTEGER")
        return

    if context.is_offline_mode():
        raise RuntimeError(
            "0002_reconcile: offline --sql needs Postgres; on SQLite the column "
            "check reads the database (there is no ADD COLUMN IF NOT EXISTS).")
    inspector = sa.inspect(op.get_bind())
    for table in HYMN_FACT_TABLES:
        existing = {c["name"] for c in inspector.get_columns(table)}
        for column in HYMN_FACT_COLUMNS:
            if column not in existing:
                op.add_column(table, sa.Column(column, sa.Integer(), nullable=True))


def downgrade() -> None:
    # No-op on purpose. Every object above is also declared by 0001_baseline:
    # on a fresh database 0001 created them and 0001's downgrade drops them,
    # so dropping them here would break 0001's own drop_index / drop_table and
    # the `downgrade base` cycle. Only a drift fix that is not part of the 0001
    # model schema would get a guarded drop_...(if_exists=True) here (none).
    pass
