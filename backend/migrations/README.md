# Database migrations (Alembic)

Since slice 1a, Alembic owns the database schema. The API no longer creates
tables at startup (`db.init_db()` stays only for the frozen Streamlit app, the
CLIs and the test fixtures). On Railway, the API service runs
`alembic upgrade head` as its Pre-deploy Command, set in the Railway UI
(step 7; `backend/railway.toml` only records it), and in production
`GET /health/ready` answers 503 `db_unavailable` with `details.reason`
`schema_behind` while the database is behind the release, so such a release
fails its deploy health check.

## How it is wired

- `backend/alembic.ini`: `script_location = %(here)s/migrations` and
  `prepend_sys_path = %(here)s`, so Alembic finds its scripts from any working
  directory. Code builds its config only through
  `db.schema_check.alembic_config()`.
- `migrations/env.py`: the models are `db.models.Base.metadata`. The URL is
  the one a caller passed in (tests), else the **exported** `DATABASE_URL`.
  Alembic never reads `backend/.env`; with no exported `DATABASE_URL` it falls
  back to the local default `sqlite:///data/church.db` (relative to the
  current directory). Before anything else it prints
  `Database: dialect=… driver=… host=… database=…` to stderr, never with the
  username or password: read that line before trusting the rest. On Postgres
  every run starts with `SET LOCAL lock_timeout = '5s'` and
  `SET LOCAL statement_timeout = '60s'`, and all pending revisions run in one
  transaction, so any failure rolls every one of them back.
- Revisions live in `migrations/versions/`, one file per revision, named
  `NNNN_short_slug.py`. Head is `0009_memberships_one_owner`.

| Revision | What it does |
|---|---|
| `0001_baseline` | The 11 tables of `db/models.py`, including `text_year` and `hymnal_count` on `hymns` and `hymn_catalog`, and `ix_hymns_church_hymnal`. Runs only on fresh databases (CI, new local dev); production is stamped at it. |
| `0002_reconcile` | Guarded adds: `ix_hymns_church_hymnal` (`IF NOT EXISTS`) and the two hymn-facts columns on both hymn tables, only where missing. A no-op on fresh databases, and on production except creating the index if step 6 reports it missing; it fixes a stamped local database made before PR #4. |
| `0003_lockdown` | Postgres only: row-level security on every `public` table (after the precondition below), and the REVOKEs from `anon` and `authenticated`. Idempotent after the ops lockdown of 2026-09-25. |
| `0004_invites_reusable` | `invites.reusable` (NOT NULL, default false; existing code-only invites become reusable) and `invites.accepted_by` with the FK `fk_invites_accepted_by_users` (`ON DELETE SET NULL`). |
| `0005_services_extras` | Slice 5a-2: `services.custom_elements` (JSON) and `services.hymnal` (VARCHAR), both nullable with no default and no backfill, and the index `ix_services_church_date` on `services (church_id, service_date_iso)`. Before it reaches production: "Before 0005_services_extras" below. |
| `0006_services_bulletin` | Printed bulletin PR 2b: `services.bulletin` (JSON), nullable with no default and no backfill: the printed bulletin's weekly fields. Before it reaches production: "Before 0006_services_bulletin" below. |
| `0007_bulletin_images` | Printed bulletin PR 3a: the table `bulletin_images` (the cover pictures, stored as JPEG in `bytes`) with the index `ix_bulletin_images_church_created`, and on Postgres row-level security on it and, when Supabase's `anon` and `authenticated` roles exist, `REVOKE ALL` on it from both. No other table changes. Before it reaches production: "Before 0007_bulletin_images" below. |
| `0008_invites_integrity` | Slice 6b-1: an invite whose role is neither `member` nor `admin` becomes an `admin` invite and is revoked; then, unless two pending invites of one church share an email in any capitalization (it refuses, naming the churches: "Church integrity" below), the unique constraint `uq_invites_church_email` is replaced by the partial unique index `uq_invites_pending_email` on `(church_id, lower(email))` for pending email invites, and the check `ck_invites_role` (`member` or `admin`) is added. No column changes. Before it reaches production: "Before 0008_invites_integrity" below. |
| `0009_memberships_one_owner` | Slice 6b-2a: unless a church has more than one owner (it refuses, naming the churches: "Church integrity" below), the partial unique index `uq_memberships_one_owner` on `memberships (church_id)` `WHERE role = 'owner'`: the database refuses a second owner. No column or data changes. Before it reaches production: "Before 0009_memberships_one_owner" below. |

## Rules for a new revision

- It has a working `downgrade()`, and every new constraint and index is
  explicitly named.
- Until slice 7 the frozen Streamlit app shares this database, so changes are
  expand-only (F §3.4): a new column is nullable or declares a server default,
  and nothing the frozen app reads is renamed or dropped.
- `.venv/bin/python -m pytest -q backend/tests/test_migrations.py` (from the
  repo root) runs the upgrade and downgrade cycle and checks that the
  migrated schema matches the models.

## Local development

Run these from `backend/`. Alembic reads only an exported `DATABASE_URL`, so
export the one your local API uses (`backend/.env.example` has
`sqlite:///../data/app.db`). If your `backend/.env` points at Supabase, do not
run them: production is migrated only by Railway and by the runbook below.

```bash
cd backend
export DATABASE_URL=sqlite:///../data/app.db
../.venv/bin/alembic upgrade head
```

- A new local database: `upgrade head` creates every table.
- A database made by the old `create_all` (before slice 1a): stamp it at the
  baseline first, then upgrade:
  `../.venv/bin/alembic stamp 0001_baseline && ../.venv/bin/alembic upgrade head`.
  One made before PR #4 (no `text_year`/`hymnal_count`) gets those columns
  from `0002_reconcile`.
- A database made by `init_db()` after slice 1a (local Streamlit,
  `import_hymnal.py`) already has head's tables but no revision:
  `../.venv/bin/alembic stamp head`. (`upgrade head` fails with "table users
  already exists", and the baseline stamp above stops in `0004`.)
- `../.venv/bin/alembic current` shows `0004_invites_reusable (head)` when you
  are up to date. If you forget, the API logs the WARNING
  `schema revision <current> != head 0004_invites_reusable` at startup (for a
  database with no revision: `schema revision None != head 0004_invites_reusable`).

## Tests

- SQLite test databases are built with `create_all` in the fixtures;
  `backend/tests/test_migrations.py` runs the revisions on temporary SQLite
  files and never reads `DATABASE_URL`.
- The Postgres-only tests (`@pytest.mark.postgres`: `0003_lockdown`'s refusals
  and idempotence, the RLS startup check, concurrent first requests) skip
  unless `TEST_DATABASE_URL` points at a local, throwaway Postgres (host
  `localhost`, `127.0.0.1` or `::1`; anything else is refused with
  `TEST_DATABASE_URL must point at a local, throwaway Postgres.`). They create
  and drop databases and roles there. From the repo root:
  `TEST_DATABASE_URL=postgresql://postgres:<password>@localhost:5432/postgres .venv/bin/python -m pytest -m postgres -q`.
- CI's `backend-postgres` job runs them on a throwaway `postgres:17`
  container, after `alembic upgrade head`, `alembic check`,
  `alembic downgrade base` and `alembic upgrade head`.

## Production runbook (slice 1a)

The owner runs steps 0–7 **before PR 1a merges** (step 7 immediately before),
and steps 8–10 at and after the merge. Record each result with its date in
`docs/ops-runbook.md` → Supabase lockdown record → "Alembic stamping record
(slice 1a)", never a URL or a password. Paste the outputs of steps 5, 6 and 9
and the deploy-log lines of step 8 into the 1a PR.

**Laptop setup** (steps 3–6, 9 and the failure paths): a checkout of the 1a
branch that has its own `.venv` (Python 3.11). There is no `psql`, `pg_dump`
or Docker on the laptop, and none is needed. In a new terminal:

```bash
cd <the checkout>/backend
../.venv/bin/pip install -r ../requirements-dev.txt
IFS= read -rs DATABASE_URL && export DATABASE_URL
```

At the `read` line, paste the Supabase session-pooler URL, the value of
Railway's `DATABASE_URL` (Railway → the API service → Variables), and press
Return. Nothing is shown, and the URL stays out of the shell history. Every
command below then first prints, on stderr,
`Database: dialect=postgresql driver=psycopg2 host=aws-….pooler.supabase.com database=postgres`.
If it says `dialect=sqlite`, `DATABASE_URL` is not exported: stop and repeat
the setup. When you are done, run `unset DATABASE_URL` and close the terminal.

### Step 0: RLS precondition

Answered on 2026-09-25 (see "RLS precondition" below): the app role
`postgres` owns every `public` table and has BYPASSRLS, so proceed. Before
stamping, rerun the two queries in Supabase → SQL Editor, one query at a time
(the editor shows only the last statement's result). The editor runs as
`postgres`, the role the pooler URL signs in as.

```sql
select tablename, tableowner from pg_tables where schemaname = 'public' order by 1;
select current_user, rolbypassrls from pg_roles where rolname = current_user;
```

Proceed only if the owner of every table is still `postgres` and
`rolbypassrls` is still `true`; otherwise stop and follow "RLS precondition".

### Step 1: Backup

Actions → db-backup → Run workflow (branch `main`), or
`gh workflow run db-backup --ref main`. It must finish green with an
artifact `db-backup` (`backup-<UTC timestamp>.dump.age`). This is the spec's
`pg_dump` backup: the job checks the server major against `PG_MAJOR`, dumps
the `public` schema with a matching `pg_dump` and encrypts it with `age`
before anything touches disk (`docs/ops-runbook.md` → Backups). Record the
run URL.

### Step 2: Server version

SQL Editor: `SHOW server_version;` The major must equal `PG_MAJOR` in
`.github/workflows/backup.yml` and the CI image `postgres:<major>` (see
"Postgres major" below). If it differs, stop: `docs/ops-runbook.md` →
Platform limits says how to change them together.

### Step 3: Nothing is stamped yet

```bash
../.venv/bin/alembic current
```

Expected: the `Database:` line (pooler host), Alembic's two `INFO` lines
(`Context impl PostgresqlImpl.`, `Will assume transactional DDL.`) and **no
revision**. If it prints a revision, the database was already stamped: stop
and read the stamping record before doing anything else.

### Step 4: Stamp the baseline

```bash
../.venv/bin/alembic stamp 0001_baseline
../.venv/bin/alembic current
```

Expected: `Running stamp_revision  -> 0001_baseline`, then `0001_baseline`.
Stamping only creates and fills the `alembic_version` table; no other table
changes, and neither running app reads that table.

### Step 5: Read the SQL the upgrade will run

```bash
../.venv/bin/alembic upgrade 0001_baseline:head --sql > upgrade.sql
```

Offline mode never connects, so it cannot know the database's revision:
without the explicit start revision it would render from base, with every
`CREATE TABLE` of 0001 and the `alembic_version` DDL. Open `upgrade.sql` and
read it. Expect, in order:

- `BEGIN;`, then `SET LOCAL lock_timeout = '5s';` and `SET LOCAL statement_timeout = '60s';`;
- 0002: `CREATE INDEX IF NOT EXISTS ix_hymns_church_hymnal …` and four
  `ALTER TABLE … ADD COLUMN IF NOT EXISTS …` statements (`text_year` and
  `hymnal_count` on `hymns` and `hymn_catalog`), no-ops on production except
  creating the index if step 6 reports it missing;
- 0003: one `DO $$ … $$` block holding the precondition check, `ENABLE ROW
  LEVEL SECURITY` for each table still without it and, when the roles `anon`
  and `authenticated` exist, the `REVOKE ALL ON ALL TABLES …` /
  `… ON ALL SEQUENCES …` and `ALTER DEFAULT PRIVILEGES …` statements;
- 0004: the `invites.reusable` and `invites.accepted_by` columns, the FK
  `fk_invites_accepted_by_users`, and the `UPDATE` that marks invites with no
  email reusable;
- after each revision an `UPDATE alembic_version …` line, and `COMMIT;` last.

Then:

```bash
head -1 upgrade.sql
grep -c 'CREATE TABLE' upgrade.sql
grep -c 'ADD COLUMN IF NOT EXISTS' upgrade.sql
grep -c 'UPDATE alembic_version' upgrade.sql
grep -c 'Database:' upgrade.sql
grep -v '^$' upgrade.sql | tail -1
shasum -a 256 upgrade.sql
rm upgrade.sql
```

Expected: `BEGIN;`, `0`, `4`, `3`, `0`, `COMMIT;`, and the SHA-256 the agent
rendered from the same commit without a database (plan Task 25). Anything
else: stop and show the agent the file.

### Step 6: Drift check

```bash
../.venv/bin/python scripts/schema_drift.py; echo "exit $?"
```

`alembic check` cannot be used yet: it refuses with
`Target database is not up to date.` because the database is at
`0001_baseline` and head is `0004_invites_reusable`. The script compares the
live schema with the models instead. Expected stdout, exactly:

```
revision: 0001_baseline head: 0004_invites_reusable state: behind
add_column invites.accepted_by
add_column invites.reusable
add_fk fk_invites_accepted_by_users
exit 1
```

with one more line, `add_index ix_hymns_church_hymnal`, after the `add_fk`
line only if production lacks that index (`0002` adds it). Exit 1 only means
"differences found", which is expected here.

- `text_year` or `hymnal_count` in the output: they are already in
  production (PR #4), so this is not the database PR #4 migrated. Stop and
  check `DATABASE_URL` with the owner before merging.
- Any other line: if it is expand-safe (F §3.4; for example a missing index
  or a missing nullable column), the agent adds it to `0002_reconcile` with an
  `IF NOT EXISTS` guard and you repeat from step 5 (step 4 stays done).
  Anything else (a type or nullability difference, an extra table or column)
  blocks the merge until it is resolved with the owner.
- `DATABASE_URL is not set.` and exit 2: the variable is not exported; redo
  the laptop setup.

Then `unset DATABASE_URL`.

### Step 7: Railway settings, immediately before merging

Railway → the project → the API service → Settings → Deploy:

1. Pre-deploy Command: `alembic upgrade head`. Save.
2. Healthcheck Path: `/health/ready` (it was `/health`). Save.

Both live in the Railway UI. Railway does not read `/backend/railway.toml`
for this service: it has deprecated Config as Code, and since 2026-08-28
services that have never used it cannot opt in (on 2026-09-27 the
Config-as-code path was entered and never took). The file keeps the same two
values as a record; change it and the UI together. The start command stays
in `backend/Procfile`. Set both immediately before merging, so the merge
deploy is the first to use them. The release serving now is not affected: it
has had `/health/ready` since ops-3. Railway stages both edits. Its
staged-changes banner's Deploy redeploys the release serving now, and that
deploy's pre-deploy step fails (the release has no Alembic) while the
previous deployment keeps serving. This order has not been tried: on
2026-09-27 the Healthcheck Path was deployed before the merge (the pre-1a
release went Active), and the Pre-deploy Command was set after the failed
merge deploy, then the merge deployment was redeployed (step 8).

### Step 8: Merge and watch the deploy

Merge PR 1a (plan Task 27: a weekday, when the tester is not using the app).
Railway → the API service → Deployments → the merge commit's deployment →
its logs:

- the **pre-deploy** step ran `alembic upgrade head`: after its `Database:`
  line, `Running upgrade 0001_baseline -> 0002_reconcile`,
  `Running upgrade 0002_reconcile -> 0003_lockdown` and
  `Running upgrade 0003_lockdown -> 0004_invites_reusable`;
- the `/health/ready` health check passed and the deployment is Active;
- the app's startup lines contain no `schema revision` line and no
  `Row-level security is off on:` line.

If it goes wrong (in every case below, the previous release keeps serving
unless the last bullet says otherwise):

- The pre-deploy output shows `0003_lockdown: role … has no BYPASSRLS …` or
  `0003_lockdown: cannot enable RLS on …`: the whole upgrade rolled back and
  the database is still at `0001_baseline`. Go back to step 0.
- It shows `relation "…" already exists`: step 4 was skipped. Run steps 3–7,
  then Deployments → the failed deployment → ⋮ → Redeploy.
- It shows `canceling statement due to lock timeout`: something held a lock
  for more than 5 s (for example an open transaction in the SQL Editor).
  Close it and redeploy.
- There is no pre-deploy step at all: the Pre-deploy Command of step 7 is not
  set. The new release then starts on a database still at `0001_baseline`:
  its startup logs `schema revision 0001_baseline != head
  0004_invites_reusable` at ERROR, and `/health/ready` answers 503
  `db_unavailable` with `"reason": "schema_behind"`, so the Healthcheck Path
  of step 7 fails the deploy, the previous release keeps serving and the
  database is untouched. This is exactly what happened on 2026-09-27, when
  step 7 relied on the Config-as-code path that never took. Set the
  Pre-deploy Command (step 7), then Deployments → the merge deployment → ⋮ →
  Redeploy: its pre-deploy step runs the upgrade. If that health check did
  not apply either, the release is live on a schema behind head (harmless in
  1a, which serves no route that reads the new `invites` columns): at once,
  the laptop setup, `../.venv/bin/alembic upgrade head` (the same three
  `Running upgrade` lines), `unset DATABASE_URL`; then fix step 7 and
  redeploy.

### Step 9: Confirm head

The laptop setup, then:

```bash
../.venv/bin/alembic current
../.venv/bin/alembic check
../.venv/bin/python scripts/schema_drift.py; echo "exit $?"
unset DATABASE_URL
```

Expected: `0004_invites_reusable (head)`; `No new upgrade operations detected.`;
and

```
revision: 0004_invites_reusable head: 0004_invites_reusable state: current
exit 0
```

Paste these, the step 5 checks, the step 6 output and the step 8 deploy-log
lines into the 1a PR.

### Step 10: Streamlit smoke check

On https://liturgy-frozen.streamlit.app/, the production Streamlit app (frozen
on `streamlit-frozen`; merges to `main` no longer reach it, so it needs no
reboot). It shares this database, so this proves the new columns, RLS and
`alembic_version` do not break it (F §6.3): sign in; the church and hymnal
load; a saved service loads; Settings opens. Then Settings → Invites →
**Create invite** with no email and role member: the success message shows a
code (never paste it anywhere). **Revoke** it. In the SQL Editor:

```sql
select reusable, accepted_by, revoked from invites order by created_at desc limit 1;
```

Expected: `false`, `NULL`, `true`. The frozen app's insert got the new
column's server default.

## RLS precondition

`0003_lockdown` enables row-level security on every `public` table without
adding policies. With RLS on and no policy, a role sees no rows unless it owns
the table or has BYPASSRLS, and both apps connect as the pooler URL's role. So
before changing anything, `0003` checks that `current_user` has BYPASSRLS or
owns every `public` table, and otherwise refuses with:

```
0003_lockdown: role % has no BYPASSRLS and does not own: %. Enabling RLS would hide their rows from the app. See migrations/README.md "RLS precondition".
```

(`%` is the role, then the tables). A table it cannot alter stops it with
`0003_lockdown: cannot enable RLS on % (owned by %, migrating as %) …`. Either
refusal rolls back the whole upgrade: Postgres DDL is transactional.

The two queries, through the pooler role (step 0):

```sql
select tablename, tableowner from pg_tables where schemaname = 'public' order by 1;
select current_user, rolbypassrls from pg_roles where rolname = current_user;
```

Recorded on 2026-09-25 (`docs/ops-runbook.md` → Supabase lockdown record,
step 2): owner of every `public` table: `postgres`; `current_user`,
`rolbypassrls`: `postgres`, `true`. Both conditions hold, so no ownership
transfer and no policy is needed. The ops lockdown already enabled RLS on
every table; `0003` repeats it idempotently and newly enables it on
`alembic_version`, which step 4 creates.

If a rerun ever shows neither condition, stop before stamping. Neither fix can
live in `0003`: `ENABLE ROW LEVEL SECURITY` and `CREATE POLICY` both require
table ownership, and the migration runs as the app role. The owner runs one
fix by hand in the SQL Editor as the current owner of each such table, and
records it (date, SQL, the before and after query output) in the lockdown
record:

- preferred: `ALTER TABLE public.<t> OWNER TO <app role>;` for each table the
  app role does not own (RLS with no policies then stays deny-all for `anon`
  and `authenticated`, with no policy to maintain);
- only if ownership cannot be transferred:
  `CREATE POLICY app_all ON public.<t> TO <app role> USING (true) WITH CHECK (true);`
  then `ALTER TABLE public.<t> ENABLE ROW LEVEL SECURITY;`. A PR must then
  widen `0003`'s precondition to accept a table that already has RLS enabled
  and an `app_all` policy for `current_user`, with a test on CI Postgres,
  before stamping.

Rerun both queries; continue only when the first condition holds (or the
alternative is in place and `0003` amended).

## Postgres major

Server major recorded for slice 1a: 17 (`server_version` 17.6 on 2026-09-25,
`docs/ops-runbook.md` → Platform limits). It equals `PG_MAJOR` in
`.github/workflows/backup.yml` and CI's `postgres:17` service image;
`backend/tests/test_ops_workflows.py` fails if those two differ, and
`backend/tests/test_slice1_docs.py` if this line differs from `PG_MAJOR`.

## Reverting

- Never downgrade production below `0003_lockdown`: that would disable the
  ops lockdown. Back out `0004` only together with reverting the 1a release
  (next item), once the revert is deployed and no deployed code reads its
  columns: the laptop setup, then
  `../.venv/bin/alembic downgrade 0003_lockdown`, then `unset DATABASE_URL`.
  With 1a still deployed, the next deploy's pre-deploy command would re-apply
  `0004`, and any restart would see the schema behind head, so production
  `/health/ready` would return 503.
- To revert the 1a release: first clear Railway → the API service →
  Settings → Deploy → Pre-deploy Command (the code before 1a has no Alembic,
  so `alembic upgrade head` would fail its pre-deploy step and the revert
  would never go live). Keep the Healthcheck Path `/health/ready`: the code
  before 1a has served that route since ops-3. Then revert the merge commit
  on `main` through a PR (the owner's yes). The schema stays at
  `0004_invites_reusable`; every 1a change is expand-only, so the older code
  runs on it.

## Before 0005_services_extras (slice 5a-2)

Railway's Pre-deploy Command (`alembic upgrade head`) applies
`0005_services_extras` when the slice 5a-2 PR merges. First, as the owner
decided on 2026-10-01: a backup, read-only counts of the saved services, and
a look at the SQL. No Streamlit check (Streamlit is retired). Nothing here
changes data. The agent guides the owner one step at a time and records the
results in `docs/ops-runbook.md` → "Slice 5a-2 record", never with an email
address, a church id or a database URL.

### Step 1: Backup

Actions → db-backup → Run workflow (branch `main`), or
`gh workflow run db-backup --ref main`. It must finish green with an
artifact `db-backup`. Record the run URL.

### Step 2: Count the saved services (read-only)

Supabase → the project → SQL Editor → New query. Paste this and Run:

```sql
-- Read-only: what the archive holds before 0005. Changes nothing.
SELECT (SELECT version_num FROM alembic_version) AS version,
       count(*) AS services,
       count(*) FILTER (WHERE coalesce(substr(service_date_iso, 1, 10), '')
                              !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$') AS undated,
       count(*) FILTER (WHERE CASE WHEN json_typeof(hymns::json) = 'array'
                                   THEN json_array_length(hymns::json) = 0
                                        OR EXISTS (SELECT 1 FROM json_array_elements(hymns::json) AS e
                                                   WHERE json_typeof(e) <> 'object' OR e ->> 'slot' IS NULL)
                                   ELSE true END) AS old_style_hymn_lists
FROM services;
```

One row. Expected before the merge: `version` is `0004_invites_reusable`
(anything else: stop); `services` is the number of saved services in all
churches; `undated` is how many have no readable date (the list shows them
last); it counts unreadable date patterns only (no `YYYY-MM-DD` at the
start), so an impossible date such as `2026-02-30` is not in it, although
the app reads it as undated. `old_style_hymn_lists` normally equals
`services`, because every service so far was saved by Streamlit, whose hymn
lists have no slots (they are read by position); a smaller number is not a
stop: tell the agent, who records it.

### Step 3: Read the SQL the upgrade will run

The agent renders it from the PR's code without connecting to any database
(from `backend/`):

```bash
DATABASE_URL=postgresql://preview@localhost:1/preview ../.venv/bin/alembic upgrade 0004_invites_reusable:0005_services_extras --sql 2>/dev/null | grep -v -e '^--' -e '^$'
```

Expected, exactly (`backend/tests/test_migrations.py` pins it):

```
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';
ALTER TABLE services ADD COLUMN custom_elements JSON;
ALTER TABLE services ADD COLUMN hymnal VARCHAR;
CREATE INDEX ix_services_church_date ON services (church_id, service_date_iso);
UPDATE alembic_version SET version_num='0005_services_extras' WHERE alembic_version.version_num = '0004_invites_reusable';
COMMIT;
```

Two new empty columns and one index, in one transaction: no row is copied,
changed or deleted. If another connection holds a lock on `services` for
more than 5 s, the deploy fails and the previous release keeps serving; run
the deploy again.

### Step 4: After the deploy (read-only)

SQL Editor:

```sql
-- Read-only: is 0005 applied? Changes nothing.
SELECT (SELECT version_num FROM alembic_version) AS version,
       (SELECT count(*) FROM information_schema.columns
         WHERE table_schema = 'public' AND table_name = 'services'
           AND column_name IN ('custom_elements', 'hymnal')) AS new_columns,
       (SELECT count(*) FROM pg_indexes
         WHERE schemaname = 'public' AND indexname = 'ix_services_church_date') AS new_index;
```

Expected: `0005_services_extras`, `2`, `1`. Then step 2's query again: the
same `services`, `undated` and `old_style_hymn_lists` (no row changed; the
app cannot save a service until 5a-3).

### Reverting 5a-2

The schema stays at `0005_services_extras`: its columns are nullable and the
code before 5a-2 ignores them. Revert the merge commit, then restore
`backend/migrations/versions/0005_services_extras.py` and the two `Service`
columns and the index in `backend/db/models.py` from the merge commit in the
same PR, so Railway's `alembic upgrade head` still finds the database at
head and `alembic check` stays clean. Never `alembic downgrade` production
for this.

## Before 0006_services_bulletin (printed bulletin PR 2b-1)

Railway's Pre-deploy Command (`alembic upgrade head`) applies
`0006_services_bulletin` when the printed bulletin PR 2b-1 (the server's
half of PR 2b; the Bulletin step, PR 2b-2, merges after it is live) merges.
First, as
the owner decided on 2026-10-02 (PR 2 planning answer 8, the same routine as
0005): a backup, read-only counts of the saved services, and a look at the
SQL; after the deploy, one read-only check. One step at a time. Nothing here
changes data. The agent guides the owner and records the results in
`docs/ops-runbook.md` → "Printed bulletin PR 2b-1 record", never with an email
address, a church id or a database URL.

### Step 1: Backup

Actions → db-backup → Run workflow (branch `main`), or
`gh workflow run db-backup --ref main`. It must finish green with an
artifact `db-backup`. Record the run URL.

### Step 2: Count the saved services (read-only)

Supabase → the project → SQL Editor → New query. Paste this and Run:

```sql
-- Read-only: what the archive holds before 0006. Changes nothing.
SELECT (SELECT version_num FROM alembic_version) AS version,
       count(*) AS services,
       count(DISTINCT church_id) AS churches
FROM services;
```

One row. Expected before the merge: `version` is `0005_services_extras`
(anything else: stop); `services` is the number of saved services in all
churches and `churches` the number of churches that saved at least one.

### Step 3: Read the SQL the upgrade will run

The agent renders it from the PR's code without connecting to any database
(from `backend/`):

```bash
DATABASE_URL=postgresql://preview@localhost:1/preview ../.venv/bin/alembic upgrade 0005_services_extras:0006_services_bulletin --sql 2>/dev/null | grep -v -e '^--' -e '^$'
```

Expected, exactly (`backend/tests/test_migrations.py` pins it):

```
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';
ALTER TABLE services ADD COLUMN bulletin JSON;
UPDATE alembic_version SET version_num='0006_services_bulletin' WHERE alembic_version.version_num = '0005_services_extras';
COMMIT;
```

One new empty column, in one transaction: no row is copied, changed or
deleted. If another connection holds a lock on `services` for more than
5 s, the deploy fails and the previous release keeps serving; run the
deploy again.

### Step 4: After the deploy (read-only)

SQL Editor:

```sql
-- Read-only: is 0006 applied? Changes nothing.
SELECT (SELECT version_num FROM alembic_version) AS version,
       (SELECT count(*) FROM information_schema.columns
         WHERE table_schema = 'public' AND table_name = 'services'
           AND column_name = 'bulletin') AS new_column,
       (SELECT count(*) FROM services WHERE bulletin IS NOT NULL) AS with_bulletin;
```

Expected: `0006_services_bulletin`, `1`, and `with_bulletin` `0` (no page
sends a bulletin until PR 2b-2's Bulletin step; from then on every save
stores one). Then step 2's query again: the same `services` and
`churches` (or more, by the services saved since the deploy; never fewer).

### Reverting PR 2b-2 or PR 2b-1

PR 2b-2 (the Bulletin step) changes no schema: revert it first, as the
plan's Step R says. Revert PR 2b-1 only after PR 2b-2 is reverted and live
(the Bulletin step sends `bulletin`, which the API before 2b-1 refuses).
For PR 2b-1 the schema stays at `0006_services_bulletin`: the column is nullable and the
code before 2b-1 ignores it. Revert the merge commit, then restore
`backend/migrations/versions/0006_services_bulletin.py` and the `Service`
column in `backend/db/models.py` from the merge commit in the same PR, so
Railway's `alembic upgrade head` still finds the database at head and
`alembic check` stays clean. Never `alembic downgrade` production for this:
the weekly fields saved since the merge stay in the column, unread, and come
back when 2b-1 does.

## Before 0007_bulletin_images (printed bulletin PR 3a)

Railway's Pre-deploy Command (`alembic upgrade head`) applies
`0007_bulletin_images` when printed bulletin PR 3a (the server's half of
PR 3, the cover picture; the upload on the Bulletin step, PR 3b, merges
after it is live) merges. First, as the owner decided on 2026-10-03 (PR 3
planning answer 10, the same routine as 0006): a backup, read-only counts,
and a look at the SQL; after the deploy, one read-only check. One step at a
time. Nothing here changes data. The agent guides the owner and records the
results in `docs/ops-runbook.md` → "Printed bulletin PR 3a record", never
with an email address, a church id or a database URL.

### Step 1: Backup

Actions → db-backup → Run workflow (branch `main`), or
`gh workflow run db-backup --ref main`. It must finish green with an
artifact `db-backup`. Record the run URL and the artifact's size.

### Step 2: Count the saved services and the database's size (read-only)

Supabase → the project → SQL Editor → New query. Paste this and Run:

```sql
-- Read-only: the database before 0007. Changes nothing.
SELECT (SELECT version_num FROM alembic_version) AS version,
       (SELECT count(*) FROM services) AS services,
       (SELECT count(*) FROM services WHERE bulletin IS NOT NULL) AS with_bulletin,
       pg_size_pretty(pg_database_size(current_database())) AS database_size;
```

One row. Expected before the merge: `version` is `0006_services_bulletin`
(anything else: stop); `services` the saved services in all churches,
`with_bulletin` those saved with the Bulletin step's fields, and
`database_size` the whole database today (the free plan holds 500 MB; a
stored picture takes at most 0.6 MB, a phone photo usually 0.2-0.5 MB, and
the app stops taking pictures when all churches' together reach 150 MB:
"Checking the cover pictures' storage" below).

### Step 3: Read the SQL the upgrade will run

The agent renders it from the PR's code without connecting to any database
(from `backend/`):

```bash
DATABASE_URL=postgresql://preview@localhost:1/preview ../.venv/bin/alembic upgrade 0006_services_bulletin:0007_bulletin_images --sql 2>/dev/null | grep -v -e '^--' -e '^$' | sed 's/ *$//'
```

Expected, exactly (`backend/tests/test_migrations.py` pins it):

```
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';
CREATE TABLE bulletin_images (
    id UUID NOT NULL,
    church_id UUID NOT NULL,
    content_type VARCHAR NOT NULL,
    bytes BYTEA NOT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    created_by UUID,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(church_id) REFERENCES churches (id) ON DELETE CASCADE,
    FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL
);
CREATE INDEX ix_bulletin_images_church_created ON bulletin_images (church_id, created_at);
ALTER TABLE bulletin_images ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon')
     AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    REVOKE ALL ON bulletin_images FROM anon, authenticated;
  END IF;
END $$;
UPDATE alembic_version SET version_num='0007_bulletin_images' WHERE alembic_version.version_num = '0006_services_bulletin';
COMMIT;
```

One new, empty table for the cover pictures, its index, row-level security
and no grant to Supabase's `anon` and `authenticated` roles (so Supabase's
own web API shows none of its rows; the `DO` block does that only where both
roles exist, as `0003_lockdown` does), in one transaction: no existing row
is copied, changed or deleted. If another
connection holds a lock on `churches` or `users` for more than 5 s, the
deploy fails and the previous release keeps serving; run the deploy again.

### Step 4: After the deploy (read-only)

SQL Editor:

```sql
-- Read-only: is 0007 applied, and closed to Supabase's web API? Changes nothing.
-- Before 0007 is applied it still runs: 0006_services_bulletin, NULL, 0, NULL.
SELECT (SELECT version_num FROM alembic_version) AS version,
       (SELECT relrowsecurity FROM pg_class WHERE oid = to_regclass('public.bulletin_images')) AS row_security,
       (SELECT count(*) FROM information_schema.role_table_grants
         WHERE table_schema = 'public' AND table_name = 'bulletin_images'
           AND grantee IN ('anon', 'authenticated')) AS open_grants,
       (SELECT (xpath('/row/n/text()', query_to_xml('SELECT count(*) AS n FROM public.bulletin_images',
                                                     false, true, '')))[1]::text::int
         WHERE to_regclass('public.bulletin_images') IS NOT NULL) AS pictures;
```

Expected: `0007_bulletin_images`, `true`, `0` and `0` (no page uploads a
picture until PR 3b). `0006_services_bulletin` with two empty (NULL) values
means the deploy has not applied 0007 yet: wait a minute and run it again. Then step 2's query again: the same `services` and
`with_bulletin` (or more, by the services saved since the deploy; never
fewer) and about the same `database_size`.

### Checking the cover pictures' storage (any time, read-only)

Any Google account can create a church, so the app limits what pictures can
take (plan review of 2026-10-03): a stored picture is at most 0.6 MB; a
church keeps at most 160 (past that its oldest picture no saved service uses
makes room, and when all 160 are in saved services the upload says so); and
when all churches' pictures together reach 150 MB, every upload is refused
with "The app has no room for more pictures right now. Please tell the
app's administrator." and Railway's log has a
`bulletin_images.storage_full` warning. A picture no saved service uses
goes 60 days after its upload, on any church's next upload. To see where
things stand (SQL Editor):

```sql
-- Read-only: the cover pictures' storage. Changes nothing.
SELECT count(*) AS pictures,
       count(DISTINCT church_id) AS churches,
       pg_size_pretty(coalesce(sum(octet_length(bytes)), 0)) AS pictures_size,
       coalesce((SELECT max(n) FROM (SELECT count(*) AS n FROM bulletin_images GROUP BY church_id) AS c), 0)
         AS most_in_one_church,
       pg_size_pretty(pg_database_size(current_database())) AS database_size
  FROM bulletin_images;
```

`pictures_size` near 150 MB (or `most_in_one_church` at 160 for a church
that is not yours) is the time to look closer: the oldest unused pictures go
on their own after 60 days; a church made only to fill the storage can be
removed with the agent's help (its pictures go with it).

### Reverting PR 3b or PR 3a

PR 3b (the upload on the Bulletin step) changes no schema: revert it first,
as the plan's Step R says. Revert PR 3a only after PR 3b is reverted and
live (PR 3b's pages send `cover_image_id` and upload pictures, which the API
before 3a refuses). For PR 3a the schema stays at `0007_bulletin_images`:
the table is new and the code before 3a ignores it. Revert the merge
commit, then restore `backend/migrations/versions/0007_bulletin_images.py`
and the `BulletinImage` model in `backend/db/models.py` from the merge
commit in the same PR, so Railway's `alembic upgrade head` still finds the
database at head and `alembic check` stays clean. Never `alembic downgrade`
production for this: the pictures uploaded since the merge stay in the
table, unread, and come back when 3a does.

## Before 0008_invites_integrity (slice 6b-1)

Railway's Pre-deploy Command (`alembic upgrade head`) applies
`0008_invites_integrity` when slice 6b-1 (the server side of People:
members, invites, ownership, leave and delete) merges. First, as the owner
decided on 2026-10-09 (6b planning answer 1, the same routine as 0007): a
backup, one read-only query that counts the invites and checks the
churches' owners, and a look at the SQL; after the deploy, one read-only
check. One step at a time. Nothing here changes data. The agent guides the
owner and records the results in `docs/ops-runbook.md` → "Slice 6b-1
record", never with an email address, a church id or a database URL.

### Step 1: Backup

Actions → db-backup → Run workflow (branch `main`), or
`gh workflow run db-backup --ref main`. It must finish green with an
artifact `db-backup`. Record the run URL and the artifact's size.

### Step 2: Count the invites and check the churches (read-only)

Supabase → the project → SQL Editor → New query. Paste this and Run:

```sql
-- Read-only: the invites and the churches' owners before 0008. Changes nothing.
SELECT (SELECT version_num FROM alembic_version) AS version,
       (SELECT count(*) FROM invites) AS invites,
       (SELECT count(*) FROM invites
         WHERE email IS NOT NULL AND NOT revoked AND accepted_at IS NULL) AS pending_email_invites,
       (SELECT count(*) FROM (SELECT 1 FROM invites
                               WHERE email IS NOT NULL AND NOT revoked AND accepted_at IS NULL
                               GROUP BY church_id, lower(email) HAVING count(*) > 1) AS d)
         AS duplicate_pending_pairs,
       (SELECT count(*) FROM invites WHERE role NOT IN ('member', 'admin')) AS other_role_invites,
       (SELECT count(*) FROM invites WHERE email <> lower(trim(email))) AS unnormalized_email_invites,
       (SELECT count(*) FROM pg_constraint WHERE conname = 'uq_invites_church_email') AS old_constraint,
       (SELECT count(*) FROM churches WHERE deleted_at IS NULL) AS churches,
       (SELECT count(*) FROM churches c
         WHERE c.deleted_at IS NULL
           AND (SELECT count(*) FROM memberships m
                 WHERE m.church_id = c.id AND m.role = 'owner') <> 1) AS churches_without_one_owner,
       (SELECT count(*) FROM churches c
         WHERE c.deleted_at IS NULL
           AND NOT EXISTS (SELECT 1 FROM memberships m
                            WHERE m.church_id = c.id AND m.role IN ('owner', 'admin')))
         AS churches_without_admin;
```

One row. Expected before the merge:

- `version` is `0007_bulletin_images` (anything else: stop);
- `invites` all invites ever made; `pending_email_invites` those bound to an
  email that are neither revoked nor used, expired ones included (the
  upgrade's "one waiting invite per church and email" rule counts an
  expired one too, until the app revokes it);
- `duplicate_pending_pairs` is `0`. Anything else: stop. The upgrade would
  refuse (safely: the previous release keeps serving); follow "Church
  integrity" step 2 below with the agent first;
- `other_role_invites` is normally `0`; any number is fine (the upgrade
  makes those invites admin invites and revokes them): record it;
- `unnormalized_email_invites` is `0` (the app has always stored an
  invite's email trimmed and lower-cased). It does not block this upgrade,
  and such an invite still works (accept and removal compare emails trimmed
  and lower-cased), but the upgrade's duplicate check and the new index
  compare `lower(email)` without trimming, so one with spaces around its
  email is not seen as the same email as a clean one. Any other number:
  record it and tell the agent, who checks with you whether one of them is
  pending beside another pending invite of the same church for the same
  email once trimmed; if so, after a fresh backup, "Church integrity" step
  2's `UPDATE` with `lower(trim(email))` in its `PARTITION BY` keeps the
  newest, before the merge;
- `old_constraint` is `1` (the constraint the upgrade replaces; `0`: stop
  and tell the agent);
- `churches` the churches in use; `churches_without_one_owner` and
  `churches_without_admin` are normally `0`. They do not block this
  upgrade, but a church with no owner cannot transfer ownership or be
  deleted in the new app: tell the agent, who records it, and repair it
  together ("Church integrity" steps 3 and 4) before slice 6b-2 merges.
  That is a gate: 6b-2's revision only refuses a second owner, so it
  would not notice a church with none.

This is the same check as `backend/scripts/check_integrity.py` ("Church
integrity" below), as one query for the SQL Editor.

### Step 3: Read the SQL the upgrade will run

The agent renders it from the PR's code without connecting to any database
(from `backend/`):

```bash
DATABASE_URL=postgresql://preview@localhost:1/preview ../.venv/bin/alembic upgrade 0007_bulletin_images:0008_invites_integrity --sql 2>/dev/null | grep -v -e '^--' -e '^$' | sed 's/ *$//'
```

Expected, exactly (`backend/tests/test_migrations.py` pins it):

```
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';
UPDATE invites SET role='admin', revoked=true WHERE (invites.role NOT IN ('member', 'admin'));
DO $$
DECLARE
  pairs integer;
  church_ids text;
BEGIN
  SELECT count(*), string_agg(DISTINCT church_id::text, ', ')
    INTO pairs, church_ids
    FROM (SELECT church_id FROM invites
           WHERE email IS NOT NULL AND NOT revoked AND accepted_at IS NULL
           GROUP BY church_id, lower(email) HAVING count(*) > 1) AS duplicates;
  IF pairs > 0 THEN
    RAISE EXCEPTION '0008_invites_integrity: % (church, email) pair(s) have more than one pending invite: %. Follow "Church integrity" in backend/migrations/README.md, then redeploy.', pairs, church_ids;
  END IF;
END $$;
ALTER TABLE invites DROP CONSTRAINT uq_invites_church_email;
ALTER TABLE invites ADD CONSTRAINT ck_invites_role CHECK (role IN ('member','admin'));
CREATE UNIQUE INDEX uq_invites_pending_email ON invites (church_id, lower(email)) WHERE email IS NOT NULL AND NOT revoked AND accepted_at IS NULL;
UPDATE alembic_version SET version_num='0008_invites_integrity' WHERE alembic_version.version_num = '0007_bulletin_images';
COMMIT;
```

In one transaction: invites with a role other than member or admin (only a
direct database write could make one) become admin invites and are revoked;
the check stops everything if two waiting invites of one church share an
email; the old rule (one invite per church and email, ever) is replaced by
one waiting invite per church and email, in any capitalization; and an
invite's role must be member or admin from now on. No row is deleted and
no column changes. If another connection holds a lock on `invites` for
more than 5 s, the deploy fails and the previous release keeps serving;
run the deploy again.

### Step 4: After the deploy (read-only)

SQL Editor:

```sql
-- Read-only: is 0008 applied? Changes nothing.
-- Before 0008 is applied it still runs: 0007_bulletin_images, 0, 0, 1.
SELECT (SELECT version_num FROM alembic_version) AS version,
       (SELECT count(*) FROM pg_indexes
         WHERE schemaname = 'public' AND indexname = 'uq_invites_pending_email') AS pending_email_index,
       (SELECT count(*) FROM pg_constraint WHERE conname = 'ck_invites_role') AS role_check,
       (SELECT count(*) FROM pg_constraint WHERE conname = 'uq_invites_church_email') AS old_constraint;
```

Expected: `0008_invites_integrity`, `1`, `1`, `0`. `0007_bulletin_images`,
`0`, `0`, `1` means the deploy has not applied 0008 yet: wait a minute and
run it again. Then step 2's query again: the same counts as before (or more
`invites` and `pending_email_invites`, by the invites made since the
deploy), except `other_role_invites` `0` and `old_constraint` `0`.

### Reverting 6b-1

The schema stays at `0008_invites_integrity`: the code before 6b-1 creates
no invites (only `POST /invites/accept` and `/preview` read them), so it
runs on it unchanged. Revert the merge commit, then, in the same PR, restore
from the merge commit every file of 6b-1's first commit ("Migration
0008_invites_integrity: …"), not only the revision: the `Invite` model,
`pytest.ini`'s two filters, this README, the test helper and the tests that
know the head or store an old invite role. Then Railway's `alembic upgrade
head` still finds the database at head, `alembic check` stays clean, and
the backend suite passes (restoring only the revision, the model and
`pytest.ini` leaves 15 tests failing). From the repo root:

```bash
git checkout <merge sha> -- backend/migrations/versions/0008_invites_integrity.py backend/db/models.py pytest.ini backend/migrations/README.md backend/tests/invite_helpers.py backend/tests/test_migrations.py backend/tests/test_schema_check.py backend/tests/test_api_app.py backend/tests/test_services_postgres.py backend/tests/test_api_invites.py backend/tests/test_usecase_onboarding.py
```

Run the backend suite before the revert's PR opens; it must pass. Never
`alembic downgrade` production for this.

## Before 0009_memberships_one_owner (slice 6b-2a)

Railway's Pre-deploy Command (`alembic upgrade head`) applies
`0009_memberships_one_owner` when slice 6b-2a (Settings → People: invite
links, the member list, roles and removal) merges. First, as the owner
decided on 2026-10-10 (6b-2 planning answer 1, the same routine as 0008): a
backup, one read-only query that counts the churches' owners, and a look at
the SQL; after the deploy, one read-only check. One step at a time. Nothing
here changes data. The agent guides the owner and records the results in
`docs/ops-runbook.md` → "Slice 6b-2a record", never with an email address,
a church id or a database URL.

### Step 1: Backup

Actions → db-backup → Run workflow (branch `main`), or
`gh workflow run db-backup --ref main`. It must finish green with an
artifact `db-backup`. Record the run URL and the artifact's size.

### Step 2: Count the churches' owners (read-only)

Supabase → the project → SQL Editor → New query. Paste this and Run (it
only reads):

```sql
-- Read-only: the churches' owners before 0009. Changes nothing.
SELECT (SELECT version_num FROM alembic_version) AS version,
       (SELECT count(*) FROM churches WHERE deleted_at IS NULL) AS churches,
       (SELECT count(*) FROM churches WHERE deleted_at IS NOT NULL) AS deleted_churches,
       (SELECT count(*) FROM memberships) AS memberships,
       (SELECT count(*) FROM memberships WHERE role = 'owner') AS owners,
       (SELECT count(*) FROM (SELECT 1 FROM memberships WHERE role = 'owner'
                               GROUP BY church_id HAVING count(*) > 1) AS d)
         AS churches_with_two_owners,
       (SELECT count(*) FROM churches c
         WHERE c.deleted_at IS NULL
           AND (SELECT count(*) FROM memberships m
                 WHERE m.church_id = c.id AND m.role = 'owner') <> 1) AS churches_without_one_owner,
       (SELECT count(*) FROM churches c
         WHERE c.deleted_at IS NULL
           AND NOT EXISTS (SELECT 1 FROM memberships m
                            WHERE m.church_id = c.id AND m.role IN ('owner', 'admin')))
         AS churches_without_admin,
       (SELECT count(*) FROM pg_indexes
         WHERE schemaname = 'public' AND indexname = 'uq_memberships_one_owner') AS one_owner_index;
```

One row. Expected before the merge:

- `version` is `0008_invites_integrity` (anything else: stop);
- `churches` the churches in use and `deleted_churches` the deleted ones;
  `memberships` every person in every church; `owners` the owner rows
  (normally one per church, deleted churches included);
- `churches_with_two_owners` is `0`. It counts deleted churches too,
  because the new index covers every row. Anything else: stop. The
  upgrade would refuse (safely: the previous release keeps serving);
  agree with the church who keeps ownership and follow "Church integrity"
  step 3 below with the agent first;
- `churches_without_one_owner` and `churches_without_admin` are `0` (the
  gate from slice 6b-1: the index only refuses a second owner, so it
  would not notice a church with none). Anything else: stop and repair
  it with the agent ("Church integrity" step 4) before the merge;
- `one_owner_index` is `0` (the index does not exist yet).

### Step 3: Read the SQL the upgrade will run

**Read only. Do not run this.** It is the SQL Railway runs when the PR
merges, shown here so the owner can read it; pasting it into the SQL
Editor would change the database. The agent renders it from the PR's code
without connecting to any database (from `backend/`):

```bash
DATABASE_URL=postgresql://preview@localhost:1/preview ../.venv/bin/alembic upgrade 0008_invites_integrity:0009_memberships_one_owner --sql 2>/dev/null | grep -v -e '^--' -e '^$' | sed 's/ *$//'
```

Expected, exactly and in full (`backend/tests/test_migrations.py` pins it;
when the agent shows it in the chat it is the whole block, never shortened):

```
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';
DO $$
DECLARE
  hits integer;
  church_ids text;
BEGIN
  SELECT count(*), string_agg(church_id::text, ', ' ORDER BY church_id::text)
    INTO hits, church_ids
    FROM (SELECT church_id FROM memberships
           WHERE role = 'owner'
           GROUP BY church_id HAVING count(*) > 1) AS owners;
  IF hits > 0 THEN
    RAISE EXCEPTION '0009_memberships_one_owner: % church(es) have more than one owner: %. Follow "Church integrity" in backend/migrations/README.md, then redeploy.', hits, church_ids;
  END IF;
END $$;
CREATE UNIQUE INDEX uq_memberships_one_owner ON memberships (church_id) WHERE role = 'owner';
UPDATE alembic_version SET version_num='0009_memberships_one_owner' WHERE alembic_version.version_num = '0008_invites_integrity';
COMMIT;
```

In one transaction: a check that stops everything if any church has more
than one owner (your count was 0); then the new rule that a church can have
at most one owner; note the new version; finish. No row is changed or
deleted and no column changes. If another connection holds a lock on
`memberships` for more than 5 s, the deploy fails and the previous release
keeps serving; run the deploy again.

### Step 4: After the deploy (read-only)

SQL Editor (it only reads):

```sql
-- Read-only: is 0009 applied? Changes nothing.
-- Before 0009 is applied it still runs: 0008_invites_integrity, 0.
SELECT (SELECT version_num FROM alembic_version) AS version,
       (SELECT count(*) FROM pg_indexes
         WHERE schemaname = 'public' AND indexname = 'uq_memberships_one_owner') AS one_owner_index;
```

Expected: `0009_memberships_one_owner`, `1`. `0008_invites_integrity`, `0`
means the deploy has not applied 0009 yet: wait a minute and run it again.
Then step 2's query again: the same counts as before, except `version`
`0009_memberships_one_owner` and `one_owner_index` `1` (or more
`memberships` and `churches`, by the people and churches added since).

### Reverting 6b-2a

The schema stays at `0009_memberships_one_owner`: the code before 6b-2a
never makes a second owner (slice 6b-1's transfer demotes the owner before
it promotes the new one), so it runs on it unchanged. Revert the merge
commit, then, in the same PR, restore from the merge commit every file of
6b-2a's first commit ("Migration 0009_memberships_one_owner: …"), not only
the revision: the `Membership` model, this README and the tests that know
the head or the index, and keep the frozen app's transfer test deleted
(it promotes before it demotes, which the index refuses). Then Railway's
`alembic upgrade head` still finds the database at head, `alembic check`
stays clean, and the backend suite passes. From the repo root:

```bash
git checkout <merge sha> -- backend/migrations/versions/0009_memberships_one_owner.py backend/db/models.py backend/migrations/README.md backend/tests/test_migrations.py backend/tests/test_schema_check.py backend/tests/test_api_app.py backend/tests/test_services_postgres.py backend/tests/test_integrity.py
git rm -q -f streamlit_tests/test_settings_members_invites.py
```

Run the backend suite before the revert's PR opens; it must pass. Never
`alembic downgrade` production for this.

## Church integrity (slice 6b)

Every church should have exactly one owner and at least one owner or
admin, every invite should grant member or admin, and no two waiting
invites of one church should share an email. The new app keeps all of this
(slice 6b), but rows written before it, or by hand, may not.

1. **When to check:** before merging slice 6b-1 and slice 6b-2, and after
   each of their deploys. Either run "Before 0008_invites_integrity" step 2's
   query in the SQL Editor (read-only), or, from a laptop with the
   production `DATABASE_URL` (the laptop setup of "Production runbook"
   above), `../.venv/bin/python scripts/check_integrity.py` from `backend/`
   (read-only). The script prints one line per problem (its kind, the church
   id, a count) and `OK: no integrity violations.` when there is none; it
   exits 1 when it found any. Record the result (never a church id) in the
   PR or the slice's record. Before slice 6b-2 merges, every church must
   have exactly one owner (steps 3 and 4): its revision only refuses a
   second owner.
2. **Duplicate pending email invites** (`duplicate_pending_pairs` above,
   `pending_duplicate` in the script; `0008` refuses to run over them): after
   a fresh backup, keep the newest pending invite per church and email, and
   revoke the rest. In the SQL Editor:
   ```sql
   UPDATE invites SET revoked = true
   WHERE id IN (
     SELECT id FROM (
       SELECT id, row_number() OVER (
         PARTITION BY church_id, lower(email) ORDER BY created_at DESC, id DESC) AS rn
       FROM invites
       WHERE email IS NOT NULL AND NOT revoked AND accepted_at IS NULL
     ) ranked WHERE rn > 1
   );
   ```
   The people those invites were for can still use the newest one.
3. **More than one owner** in a church (`owner_count` with a count above 1;
   `0009_memberships_one_owner` refuses to run over it):
   agree with the church who keeps ownership, then, after a fresh backup,
   make the others admins. The statements in steps 3 and 4 hold
   placeholders in quotes (`'<church id>'`, `'<user id of the owner who
   stays>'`, `'<user id of the new owner>'`), which the SQL Editor never
   tries to fill in and which fail, changing nothing, if run as they are.
   The agent writes the statement out with the real ids in the chat only,
   for the owner to paste; the real ids never go into a committed file,
   the PR or the record.
   `UPDATE memberships SET role = 'admin' WHERE church_id = '<church id>' AND role = 'owner' AND user_id <> '<user id of the owner who stays>';`
4. **No owner** (`owner_count` 0): pick an existing admin with the church,
   then, after a fresh backup (the agent fills in the ids in the chat, as
   in step 3):
   `UPDATE memberships SET role = 'owner' WHERE church_id = '<church id>' AND user_id = '<user id of the new owner>';`
   If the church has no admin either (`no_admin`), pick any member.
5. **Invites with another role** (`invite_role`): `0008` repairs them; after
   it, the database refuses new ones.
6. Check again until it shows none of these, then merge. Railway's
   pre-deploy runs `alembic upgrade head`.
7. After the deploy, check once more.
