"""Invites integrity: member/admin roles only, one pending invite per email (slice 6b-1)

6b spec, "Data and migrations" (its 0006_invites_integrity; the owner's 6b
planning answers of 2026-10-09 number it 0008). Expand-only while nothing
else shares the database (F §3.4): no column changes.

Upgrade, in order:
1. Role repair: an invite whose role is neither member nor admin (only a
   direct database write could make one; it would have granted a second
   owner) becomes an admin invite and is revoked. Data only; the downgrade
   does not undo it. Online runs log how many rows it changed once step 2
   has passed (6b-1 build review 4), so a refused run never claims it.
2. Duplicate pre-check: if two pending invites (email set, not revoked, not
   accepted) of one church share an email in any capitalization, stop with
   the runbook message, naming the church ids and never an email. On
   Postgres it is a DO block (so the owner's SQL preview shows it); on
   SQLite a RuntimeError with the same words.
3. Drop the unique constraint uq_invites_church_email (church_id, email):
   it refused a re-invite after a revoke or an acceptance.
4. Create the unique index uq_invites_pending_email on
   (church_id, lower(email)) WHERE email IS NOT NULL AND NOT revoked AND
   accepted_at IS NULL: one pending invite per church and email.
5. Add the check constraint ck_invites_role: role IN ('member','admin').
   Every existing row passes it after step 1 (role is NOT NULL).

On Postgres env.py runs SET LOCAL lock_timeout = '5s' (and
statement_timeout '60s') first, and everything runs in one transaction, so
a refusal in step 2 rolls back step 1 too and the previous release keeps
serving. On SQLite steps 3 and 5 recreate the table (batch mode) and copy
its rows.

Downgrade: drop ck_invites_role and uq_invites_pending_email, then restore
uq_invites_church_email, unless two invites of one church share an exact
non-null email (re-inviting after a revoke makes such pairs legitimately):
then it refuses with a RuntimeError, and nothing changes.

Revision ID: 0008_invites_integrity
Revises: 0007_bulletin_images
Create Date: 2026-10-09
"""
import logging
import uuid

from alembic import context, op
import sqlalchemy as sa

revision = "0008_invites_integrity"
down_revision = "0007_bulletin_images"
branch_labels = None
depends_on = None

logger = logging.getLogger("alembic.runtime.migration")

PENDING = "email IS NOT NULL AND NOT revoked AND accepted_at IS NULL"
ROLES = "role IN ('member','admin')"
DUPLICATES_MESSAGE = (
    "0008_invites_integrity: {pairs} (church, email) pair(s) have more than one pending invite: {churches}. "
    "Follow \"Church integrity\" in backend/migrations/README.md, then redeploy."
)

# A lightweight table for the data step: never the ORM model, which keeps changing.
invites = sa.table(
    "invites",
    sa.column("role", sa.String()),
    sa.column("revoked", sa.Boolean()),
)

# The pending duplicates: one row per (church, lower(email)) with more than one pending invite.
DUPLICATES_SQL = """\
SELECT church_id FROM invites
           WHERE email IS NOT NULL AND NOT revoked AND accepted_at IS NULL
           GROUP BY church_id, lower(email) HAVING count(*) > 1"""

# Step 2 on Postgres: the same refusal inside the migration's transaction.
DUPLICATES_CHECK_PG = """\
DO $$
DECLARE
  pairs integer;
  church_ids text;
BEGIN
  SELECT count(*), string_agg(DISTINCT church_id::text, ', ')
    INTO pairs, church_ids
    FROM (""" + DUPLICATES_SQL + """) AS duplicates;
  IF pairs > 0 THEN
    RAISE EXCEPTION '0008_invites_integrity: % (church, email) pair(s) have more than one pending invite: %. Follow "Church integrity" in backend/migrations/README.md, then redeploy.', pairs, church_ids;
  END IF;
END $$"""


def upgrade() -> None:
    dialect = op.get_context().dialect.name
    repair = invites.update().where(invites.c.role.not_in(["member", "admin"])).values(
        role="admin", revoked=sa.true())
    repaired = None
    if context.is_offline_mode():
        op.execute(repair)
    else:
        repaired = op.get_bind().execute(repair).rowcount
    if dialect == "postgresql":
        op.execute(DUPLICATES_CHECK_PG)
    else:
        rows = op.get_bind().execute(sa.text(DUPLICATES_SQL)).all()
        if rows:
            churches = ", ".join(sorted({str(uuid.UUID(str(row[0]))) for row in rows}))   # SQLite keeps hex
            raise RuntimeError(DUPLICATES_MESSAGE.format(pairs=len(rows), churches=churches))
    if repaired is not None:   # logged once the check passed: a refusal rolls the repair back
        logger.info("0008_invites_integrity: %d invite(s) with another role made admin and revoked", repaired)
    with op.batch_alter_table("invites") as batch:
        batch.drop_constraint("uq_invites_church_email", type_="unique")
        batch.create_check_constraint("ck_invites_role", ROLES)
    op.create_index(
        "uq_invites_pending_email", "invites", ["church_id", sa.text("lower(email)")], unique=True,
        postgresql_where=sa.text(PENDING), sqlite_where=sa.text(PENDING))


def downgrade() -> None:
    pairs = op.get_bind().execute(sa.text(
        "SELECT church_id, email FROM invites WHERE email IS NOT NULL "
        "GROUP BY church_id, email HAVING count(*) > 1")).all()
    if pairs:   # checked before any change: SQLite runs DDL outside a transaction
        raise RuntimeError(
            f"Cannot restore uq_invites_church_email: {len(pairs)} (church, email) pairs have more than one "
            "invite. Delete the revoked or accepted duplicates first.")
    op.drop_index("uq_invites_pending_email", table_name="invites")
    with op.batch_alter_table("invites") as batch:
        batch.drop_constraint("ck_invites_role", type_="check")
        batch.create_unique_constraint("uq_invites_church_email", ["church_id", "email"])
