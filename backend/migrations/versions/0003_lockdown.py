"""Row-level security on every public table, and the anon/authenticated REVOKEs

Revision ID: 0003_lockdown
Revises: 0002_reconcile
Create Date: 2026-09-26

F §3.2 item 4, §3.6; slice 1 spec, "Revisions". Postgres only; a no-op on
SQLite. It repeats the ops lockdown of 2026-09-25 (docs/ops-runbook.md,
"Supabase lockdown record") idempotently and covers tables created after it
(alembic_version first of all).

LOCKDOWN_SQL is one DO block, run as the migrating (app) role:
1. Precondition: unless current_user has BYPASSRLS, it must own every public
   table. RLS with no policies hides every row from a role that neither owns
   the table nor bypasses RLS, and both apps connect as this role.
2. Every public table with RLS off: ENABLE ROW LEVEL SECURITY when
   current_user owns it (only the owner may), else refuse. Tables that already
   have RLS (the ops lockdown) are skipped.
3. When the Supabase roles anon and authenticated both exist (the statements
   name both; CI Postgres has neither): the REVOKEs and ALTER DEFAULT
   PRIVILEGES of the ops lockdown. Without FOR ROLE, ALTER DEFAULT PRIVILEGES
   applies to current_user, which is postgres in production: the same as the
   recorded ops SQL's FOR ROLE postgres.

A RAISE aborts env.py's single upgrade transaction. Postgres DDL is
transactional, so every revision of that run rolls back with it (0002 to 0004
in production), the pre-deploy command fails and the previous release keeps
serving. migrations/README.md, "RLS precondition", says what to do then.
"""
from alembic import op

revision = "0003_lockdown"
down_revision = "0002_reconcile"
branch_labels = None
depends_on = None

LOCKDOWN_SQL = """\
DO $$
DECLARE
  bypass boolean;
  not_owned text;
  t record;
BEGIN
  SELECT r.rolbypassrls INTO bypass FROM pg_roles r WHERE r.rolname = current_user;
  IF NOT coalesce(bypass, false) THEN
    SELECT string_agg(c.relname::text, ', ' ORDER BY c.relname) INTO not_owned
      FROM pg_class c
     WHERE c.relnamespace = 'public'::regnamespace
       AND c.relkind IN ('r', 'p')
       AND pg_get_userbyid(c.relowner) <> current_user;
    IF not_owned IS NOT NULL THEN
      RAISE EXCEPTION '0003_lockdown: role % has no BYPASSRLS and does not own: %. Enabling RLS would hide their rows from the app. See migrations/README.md "RLS precondition".', current_user, not_owned;
    END IF;
  END IF;

  FOR t IN
    SELECT c.relname::text AS tbl, pg_get_userbyid(c.relowner)::text AS tbl_owner
      FROM pg_class c
     WHERE c.relnamespace = 'public'::regnamespace
       AND c.relkind IN ('r', 'p')
       AND NOT c.relrowsecurity
     ORDER BY c.relname
  LOOP
    IF t.tbl_owner <> current_user THEN
      RAISE EXCEPTION '0003_lockdown: cannot enable RLS on % (owned by %, migrating as %). Only the owner of a table can enable RLS on it. See migrations/README.md "RLS precondition".', t.tbl, t.tbl_owner, current_user;
    END IF;
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t.tbl);
  END LOOP;

  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon')
     AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated;
    REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM anon, authenticated;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM anon, authenticated;
  END IF;
END $$"""

# Downgrade turns RLS off again on every public table the migrating role owns.
# The REVOKEs are deliberately NOT undone: granting anon and authenticated
# access again would reopen the Data API exposure the ops lockdown closed.
# Never downgrade production below 0003_lockdown (migrations/README.md).
UNLOCK_SQL = """\
DO $$
DECLARE
  t text;
BEGIN
  FOR t IN
    SELECT c.relname::text
      FROM pg_class c
     WHERE c.relnamespace = 'public'::regnamespace
       AND c.relkind IN ('r', 'p')
       AND c.relrowsecurity
       AND pg_get_userbyid(c.relowner) = current_user
     ORDER BY c.relname
  LOOP
    EXECUTE format('ALTER TABLE public.%I DISABLE ROW LEVEL SECURITY', t);
  END LOOP;
END $$"""


def _postgres() -> bool:
    return op.get_context().dialect.name == "postgresql"


def upgrade() -> None:
    if not _postgres():
        return      # SQLite (local dev, tests): no roles, no row-level security
    op.execute(LOCKDOWN_SQL)


def downgrade() -> None:
    if not _postgres():
        return
    op.execute(UNLOCK_SQL)
