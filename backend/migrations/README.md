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
  `NNNN_short_slug.py`. Head is `0005_services_extras`.

| Revision | What it does |
|---|---|
| `0001_baseline` | The 11 tables of `db/models.py`, including `text_year` and `hymnal_count` on `hymns` and `hymn_catalog`, and `ix_hymns_church_hymnal`. Runs only on fresh databases (CI, new local dev); production is stamped at it. |
| `0002_reconcile` | Guarded adds: `ix_hymns_church_hymnal` (`IF NOT EXISTS`) and the two hymn-facts columns on both hymn tables, only where missing. A no-op on fresh databases, and on production except creating the index if step 6 reports it missing; it fixes a stamped local database made before PR #4. |
| `0003_lockdown` | Postgres only: row-level security on every `public` table (after the precondition below), and the REVOKEs from `anon` and `authenticated`. Idempotent after the ops lockdown of 2026-09-25. |
| `0004_invites_reusable` | `invites.reusable` (NOT NULL, default false; existing code-only invites become reusable) and `invites.accepted_by` with the FK `fk_invites_accepted_by_users` (`ON DELETE SET NULL`). |
| `0005_services_extras` | Slice 5a-2: `services.custom_elements` (JSON) and `services.hymnal` (VARCHAR), both nullable with no default and no backfill, and the index `ix_services_church_date` on `services (church_id, service_date_iso)`. Before it reaches production: "Before 0005_services_extras" below. |

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
