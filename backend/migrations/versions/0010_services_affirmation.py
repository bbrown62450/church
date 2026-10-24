"""Services: the Affirmation of Faith (affirmation spec, "Data shape")

Expand-only (F §3.4): one nullable JSON column, no backfill, no server
default, no index. Existing rows keep NULL, which the API reads as the
Apostles' Creed, included: every service saved before this change prints
exactly as before.
- services.affirmation JSON NULL: {include, choice, text} (affirmation.py).
  A new column rather than a key inside services.liturgy, which holds only
  the eight liturgy sections (0006's reason too); the frozen Streamlit app
  never reads it.

On Postgres env.py runs SET LOCAL lock_timeout = '5s' (and statement_timeout
'60s') first; adding a nullable column without a default changes only the
catalog. Both directions use op.batch_alter_table, as 0004 to 0006 do.

Revision ID: 0010_services_affirmation
Revises: 0009_memberships_one_owner
Create Date: 2026-10-24
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_services_affirmation"
down_revision = "0009_memberships_one_owner"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("services") as batch:
        batch.add_column(sa.Column("affirmation", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("services") as batch:
        batch.drop_column("affirmation")
