"""One owner per church: the partial unique index uq_memberships_one_owner (slice 6b-2a)

6b spec, "Data and migrations" (its memberships_one_owner; the owner's 6b-2
planning answers of 2026-10-10 number it 0009 and ship it with the People
page). Expand-only (F §3.4): no column changes, no data changes.

Upgrade, in order:
1. Owner pre-check: if any church (soft-deleted ones too: the index covers
   every row) has more than one owner, stop with the runbook message, naming
   the church ids. Which owner stays is a person's decision, so there is no
   automatic repair. On Postgres it is a DO block (so the owner's SQL preview
   shows it and it runs in the upgrade's one transaction); on SQLite a
   RuntimeError with the same words.
2. Create the unique index uq_memberships_one_owner on
   memberships (church_id) WHERE role = 'owner': the database refuses a
   second owner. The API keeps exactly one (only a transfer moves ownership,
   demote first, then promote; usecases/church_admin.py).

On Postgres env.py runs SET LOCAL lock_timeout = '5s' (and
statement_timeout '60s') first, and everything runs in one transaction, so
a refusal changes nothing and the previous release keeps serving.

Downgrade: drop uq_memberships_one_owner. Nothing else changes.

Revision ID: 0009_memberships_one_owner
Revises: 0008_invites_integrity
Create Date: 2026-10-10
"""
import uuid

from alembic import op
import sqlalchemy as sa

revision = "0009_memberships_one_owner"
down_revision = "0008_invites_integrity"
branch_labels = None
depends_on = None

ONE_OWNER = "role = 'owner'"
OWNERS_MESSAGE = (
    "0009_memberships_one_owner: {churches} church(es) have more than one owner: {ids}. "
    "Follow \"Church integrity\" in backend/migrations/README.md, then redeploy."
)

# The churches with more than one owner, one row each.
EXTRA_OWNERS_SQL = """\
SELECT church_id FROM memberships
           WHERE role = 'owner'
           GROUP BY church_id HAVING count(*) > 1"""

# Step 1 on Postgres: the same refusal inside the migration's transaction.
EXTRA_OWNERS_CHECK_PG = """\
DO $$
DECLARE
  hits integer;
  church_ids text;
BEGIN
  SELECT count(*), string_agg(church_id::text, ', ' ORDER BY church_id::text)
    INTO hits, church_ids
    FROM (""" + EXTRA_OWNERS_SQL + """) AS owners;
  IF hits > 0 THEN
    RAISE EXCEPTION '0009_memberships_one_owner: % church(es) have more than one owner: %. Follow "Church integrity" in backend/migrations/README.md, then redeploy.', hits, church_ids;
  END IF;
END $$"""


def upgrade() -> None:
    if op.get_context().dialect.name == "postgresql":
        op.execute(EXTRA_OWNERS_CHECK_PG)
    else:
        rows = op.get_bind().execute(sa.text(EXTRA_OWNERS_SQL)).all()
        if rows:
            ids = ", ".join(sorted(str(uuid.UUID(str(row[0]))) for row in rows))   # SQLite keeps hex
            raise RuntimeError(OWNERS_MESSAGE.format(churches=len(rows), ids=ids))
    op.create_index(
        "uq_memberships_one_owner", "memberships", ["church_id"], unique=True,
        postgresql_where=sa.text(ONE_OWNER), sqlite_where=sa.text(ONE_OWNER))


def downgrade() -> None:
    op.drop_index("uq_memberships_one_owner", table_name="memberships")
