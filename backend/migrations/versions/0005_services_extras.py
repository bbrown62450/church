"""Services: custom elements, hymnal and the date index (F §3.5; slice 5a spec, "Data and migrations"; slice 5a-2)

Expand-only (F §3.4): two nullable columns and one index. No backfill, no
server default, no NOT NULL; existing rows keep NULL, which the API reads as
no custom elements ([]) and no hymnal (null).
- services.custom_elements JSON NULL: the custom elements a saved service
  prints, [{label, text, insert_after}].
- services.hymnal VARCHAR NULL: the hymnal the service's hymns came from.
- ix_services_church_date on services (church_id, service_date_iso): for
  the archive list's order (newest service date first, per church); the
  hymn-use rebuild uses its church_id prefix (its LIKE on the date is not
  index-assisted under a non-C collation).

On Postgres env.py runs SET LOCAL lock_timeout = '5s' (and statement_timeout
'60s') first, so a lock held elsewhere fails the deploy after 5 s instead of
queueing every query behind it; the previous release keeps serving. Adding a
nullable column without a default changes only the catalog; the plain
CREATE INDEX blocks writes to services (not reads) while it builds, a moment
on a table this size. Both directions use op.batch_alter_table, as 0004 does:
plain ALTER TABLE on Postgres and in --sql, a table copy on SQLite when a
column is dropped.

Revision ID: 0005_services_extras
Revises: 0004_invites_reusable
Create Date: 2026-10-02
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_services_extras"
down_revision = "0004_invites_reusable"
branch_labels = None
depends_on = None

INDEX = "ix_services_church_date"


def upgrade() -> None:
    with op.batch_alter_table("services") as batch:
        batch.add_column(sa.Column("custom_elements", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("hymnal", sa.String(), nullable=True))
    op.create_index(INDEX, "services", ["church_id", "service_date_iso"])


def downgrade() -> None:
    op.drop_index(INDEX, table_name="services")
    with op.batch_alter_table("services") as batch:
        batch.drop_column("hymnal")
        batch.drop_column("custom_elements")
