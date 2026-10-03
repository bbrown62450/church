"""Services: the printed bulletin's weekly fields (printed bulletin spec, "Data model"; PR 2b)

Expand-only (F §3.4): one nullable JSON column, no backfill, no server
default, no index. Existing rows keep NULL, which the API reads as an empty
bulletin (nothing filled in).
- services.bulletin JSON NULL: what the service's printed bulletin prints
  each week: the prelude and postlude, this week's people and part leaders,
  the announcements and any pasted reading text (service_bulletin.py).
  A new column rather than a key inside services.liturgy, which holds only
  the eight liturgy sections and which every reader filters to them.

On Postgres env.py runs SET LOCAL lock_timeout = '5s' (and statement_timeout
'60s') first, so a lock held elsewhere fails the deploy after 5 s instead of
queueing every query behind it; the previous release keeps serving. Adding a
nullable column without a default changes only the catalog. Both directions
use op.batch_alter_table, as 0004 and 0005 do: plain ALTER TABLE on Postgres
and in --sql, a table copy on SQLite when the column is dropped.

Revision ID: 0006_services_bulletin
Revises: 0005_services_extras
Create Date: 2026-10-03
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_services_bulletin"
down_revision = "0005_services_extras"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("services") as batch:
        batch.add_column(sa.Column("bulletin", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("services") as batch:
        batch.drop_column("bulletin")
