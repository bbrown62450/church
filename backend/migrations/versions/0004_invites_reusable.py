"""Invites: reusable flag and accepted_by (F §3.2 item 5, §3.4; slice 1 spec, "Revisions")

Expand-only, safe while the frozen Streamlit app shares the database (F §3.4):
- invites.reusable BOOLEAN NOT NULL DEFAULT false. The server default is what
  lets frozen Streamlit, whose ORM does not map the column, keep inserting
  invites (they get false: single-use in the new app, F §6.2).
- invites.accepted_by UUID NULL, FK fk_invites_accepted_by_users -> users(id)
  ON DELETE SET NULL (who consumed a single-use invite; 1b's accept stamps it).
- Data step: every existing code-only invite (email IS NULL) becomes reusable,
  so it keeps the 7-day multi-use meaning it had in Streamlit; email-bound
  invites stay single-use.

Both directions run inside op.batch_alter_table("invites"): on Postgres (and
offline --sql) that is plain ALTER TABLE statements; SQLite cannot add or drop
a foreign key with ALTER, so there the batch recreates the table and copies
its rows.

Revision ID: 0004_invites_reusable
Revises: 0003_lockdown
Create Date: 2026-09-26
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_invites_reusable"
down_revision = "0003_lockdown"
branch_labels = None
depends_on = None

FK_ACCEPTED_BY = "fk_invites_accepted_by_users"

# A lightweight table for the data step: never the ORM model, which keeps
# changing after this revision is written. sa.true() renders `true` on
# Postgres and `1` on SQLite.
invites = sa.table(
    "invites",
    sa.column("email", sa.String()),
    sa.column("reusable", sa.Boolean()),
)


def upgrade() -> None:
    with op.batch_alter_table("invites") as batch:
        batch.add_column(sa.Column("reusable", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("accepted_by", sa.Uuid(), nullable=True))
        batch.create_foreign_key(FK_ACCEPTED_BY, "users", ["accepted_by"], ["id"], ondelete="SET NULL")
    op.execute(invites.update().where(invites.c.email.is_(None)).values(reusable=sa.true()))


def downgrade() -> None:
    with op.batch_alter_table("invites") as batch:
        batch.drop_constraint(FK_ACCEPTED_BY, type_="foreignkey")
        batch.drop_column("accepted_by")
        batch.drop_column("reusable")
