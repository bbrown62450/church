# Operations runbook

The single place for the Supabase lockdown record, backup key custody and the
restore drill, the Streamlit freeze record, platform limits and incident
response. Design: `docs/superpowers/specs/2026-09-25-slice-ops-cleanup-design.md`
("the ops spec").

- An entry marked `[owner: …]` is a value only the owner can see (a dashboard,
  a SQL result, a message sent). Replace the whole marker with the value and
  the date.
- Never paste a secret here: no database URL with its password, no API key,
  no access token, no `age` private key.
- The seven sections follow the ops spec (Testing → Manual checks):
  environments and variables, the Supabase lockdown record, backups,
  keep-alive, the Streamlit freeze, platform limits and incident response.

## Environments and variables

Names, and where each value comes from. Never the secret values themselves.

**Railway, the API service.** Service root `backend`; start command in
`backend/Procfile`; public URL https://church-production-74ca.up.railway.app;
deploy health check: `/health/ready` since slice 1a, and `alembic upgrade head`
as the pre-deploy command (`backend/migrations/README.md`), both set by hand
in Settings → Deploy (Healthcheck Path, Pre-deploy Command) since 2026-09-27.
Railway does not read `/backend/railway.toml` for this service (Config as Code
is deprecated and closed to services that never used it); the file only
records the two values. With the health check, a deployment whose process
never answers (for example the `APP_ENV` guard refusing to start) is not
promoted and the previous one keeps serving. Without it, or if a bad
deployment went Active anyway, roll back by hand: Deployments → the previous
deployment → Redeploy.

| Variable | Value | Since |
|---|---|---|
| `DATABASE_URL` | Supabase session-pooler URL (secret) | slice 0 |
| `SUPABASE_URL` | `https://tbecmwtitsoxzkrvxxxu.supabase.co` | slice 0 |
| `CORS_ORIGINS` | `https://worship-service-builder.vercel.app`, plus `http://localhost:3000` and the slice-0 preview origin `https://church-git-claude-react-fastapi-slice0-bbrown62450s-projects.vercel.app` (both kept by the owner, 2026-09-26): exact origins, comma-separated, no trailing slash | slice 0 |
| `APP_ENV` | `production`, set before ops-3 merged and confirmed in effect on the Active deployment (Railway stages variable edits until they are deployed). The API then refuses to start on anything but PostgreSQL, and logs an ERROR when `CORS_ORIGINS` lists only localhost. | ops-3 |
| `LOG_LEVEL` | optional: `DEBUG`, `INFO` (the default when unset), `WARNING` or `ERROR` | ops-3 |
| `DB_POOL_SIZE`, `DB_MAX_OVERFLOW` | `3` and `3` (see Platform limits) | ops-1; read since ops-2 |
| `ESV_API_KEY` | optional: enables the ESV translation (secret). The new app reads it from the environment (`scripture_fetcher._esv_key()`) until slice 7 moves it into `api/settings.py`; while it is unset, `GET /translations` returns `esv_available: false` and ESV is hidden. | ops-1; read by the new app since slice 2a |
| `OPENAI_API_KEY` | the new app's own OpenAI key (secret), separate from the Streamlit app's, with a monthly budget cap of $15 set in the OpenAI dashboard (owner, 2026-09-29). Read by `integrations/openai_client.py` since slice 3a. Without it, or without `OPENAI_MODEL`, hymn suggestions answer 503 `ai_not_configured` and the startup log says `AI: not configured (...)`. When the cap is reached, suggestions read "not set up" until the next month, with `ERROR AI: quota exhausted (insufficient_quota)` in the log and no retries. | slice 0; read since slice 3a |
| `OPENAI_MODEL` | required with the key; no default in code. A non-reasoning, inexpensive chat model that accepts `response_format` json_object and `max_completion_tokens` (slice 3a plan, "Model"). The startup log names it: `AI: configured (model=...)`. If OpenAI retires the model (possible at any time after a deploy), suggestions read "not set up" and each call logs `ERROR AI: model not available (OPENAI_MODEL=...)`: set a model the project offers and redeploy. | slice 3a |
| `OPENAI_TIMEOUT_SECONDS`, `OPENAI_MAX_RETRIES`, `OPENAI_MAX_CONCURRENCY`, `OPENAI_TEMPERATURE` | optional: defaults 30, 1 and 4, and no temperature sent | slice 3a |
| `OPENAI_REASONING_EFFORT` | optional; unset by default, and then nothing is sent. Set it (for example `minimal` or `low`) only for a reasoning (GPT-5-family) model, which otherwise can spend its answer budget on hidden reasoning and answer "had a problem". | slice 3a |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI` | carried over for a later slice (secrets) | slice 0 |

Checked against Railway → the API service → Variables (names only) and Settings → Deploy → Healthcheck Path:
2026-09-26: the names match this table (`DATABASE_URL` is a `postgresql://` Supabase pooler URL; `CORS_ORIGINS` as in the row above). `APP_ENV` = `production` added, deployed and Active, with no staged change pending; `/health` still answered `{"ok":true}` afterwards. Healthcheck Path `/health` (already set). The Actions variable `API_BASE_URL` is set, and the repository has no Actions secrets.

**Vercel, project `worship-service-builder`.** Root `frontend`; URL
https://worship-service-builder.vercel.app. `NEXT_PUBLIC_SUPABASE_URL` (the
Supabase URL above), `NEXT_PUBLIC_SUPABASE_ANON_KEY` (the publishable key,
public by design) and `NEXT_PUBLIC_API_URL`
(https://church-production-74ca.up.railway.app). The install command is the
default (no `--omit=dev`) and there is no `NPM_CONFIG_PRODUCTION`, because the
build needs the `shadcn` devDependency.

**GitHub Actions, repo `bbrown62450/church`.**

| Kind | Name | Used by | Since |
|---|---|---|---|
| Environment secret (environment `backup`, deployment branch `main` only) | `BACKUP_DATABASE_URL` | `db-backup` (see Backups) | ops-1 |
| Repository variable | `API_BASE_URL` = `https://church-production-74ca.up.railway.app` | `keepalive` (see Keep-alive) | ops-3 |

No repository secret is needed. Nothing reads a `DATABASE_URL` Actions secret
since ops-3; if one exists, delete it.

**Streamlit Community Cloud.**

| App | Source | Secrets (names only) |
|---|---|---|
| `liturgy-frozen`, https://liturgy-frozen.streamlit.app/ (production since the Freeze on 2026-09-26, the only Streamlit app) | repo `bbrown62450/church`, branch `streamlit-frozen`, main file `app.py`, Python 3.14. Created as the Freeze's temporary pre-flight app; the owner then kept production on it instead of moving it onto `liturgy-next` (see Streamlit apps). Merges to `main` do not reach it. Sharing: public. | the `[auth]` block (Google sign-in, `redirect_uri = https://liturgy-frozen.streamlit.app/oauth2callback`), `DATABASE_URL`, `OPENAI_API_KEY`, the `GOOGLE_*` gmail.send client with `GOOGLE_OAUTH_REDIRECT_URI = https://liturgy-frozen.streamlit.app/` (README → Local setup), and `DB_POOL_SIZE = "3"` and `DB_MAX_OVERFLOW = "3"` at the very top, above the first `[section]` line (below `[auth]` they would belong to that section and never reach the environment). They are `liturgy-next`'s Secrets with exactly the two redirect values changed. The owner keeps a copy in the password manager. |
| `liturgy-next`, https://liturgy-next.streamlit.app/ | production from 2026-09-26 until the Freeze that evening: branch `main`, main file `app.py`, Python 3.14.7 (its log; this table said 3.13). Deleted in the Freeze; no app holds the subdomain now (see Streamlit apps) | — |
| `liturgy`, `liturgy-stg` | deleted on 2026-09-26 (see Streamlit apps) | — |

**Supabase**, project `worship-staging` (ref `tbecmwtitsoxzkrvxxxu`, Nano
compute, Postgres 17.6): Data API off (see Supabase lockdown record); Auth
providers: Google only; `mailer_autoconfirm` off; session pooler Pool Size 15
(see Platform limits).

**Google OAuth client "Liturgy"** (Google Cloud Console → APIs & Services →
Credentials): since 2026-09-26 the Streamlit redirect URIs are
`https://liturgy-frozen.streamlit.app/oauth2callback` and the bare root
`https://liturgy-frozen.streamlit.app/`, the only `streamlit.app` URIs on the
client. Once an app is deleted, anyone may be able to claim its subdomain and
would then receive this client's authorization responses, for sign-in and for
the `gmail.send` flow. So a subdomain's URIs are registered only while one of
this project's apps holds it: the four URIs of the deleted `liturgy` and
`liturgy-stg` apps were removed before the Freeze, and the two of
`liturgy-next` after it was deleted in the Freeze (see Freeze record). No
other redirect URI is touched.

## Supabase lockdown record

Project `worship-staging`, ref `tbecmwtitsoxzkrvxxxu`. Procedure: the ops spec →
Data and migrations → Step 0. Done on 2026-09-25; the results are below. To
check again, connect with the session-pooler URL the apps use, but never put
the URL on a command line: shell history keeps it, and libpq quotes parts of a
malformed URL, password included, in its errors. From the repo root, in bash
or zsh, `.github/backup/pg_env.py` turns it into `PG*` variables:

```
IFS= read -rs BACKUP_URL        # paste the URL and press Return; nothing is shown
eval "$(python3 .github/backup/pg_env.py --exports <<<"$BACKUP_URL")"; unset BACKUP_URL
docker run --rm -it -e PGHOST -e PGPORT -e PGUSER -e PGPASSWORD -e PGDATABASE \
    -e PGSSLMODE=require postgres:17 psql
unset PGHOST PGPORT PGUSER PGPASSWORD PGDATABASE    # when finished
```

If `psql` is installed, plain `PGSSLMODE=require psql` can replace the
`docker run` line.

**1. Exposure before the lockdown.** For each of `users`, `gmail_tokens`,
`invites` and `memberships`:

```
curl -s "https://tbecmwtitsoxzkrvxxxu.supabase.co/rest/v1/<table>?select=*&limit=1" \
  -H "apikey: <anon key>" -H "Authorization: Bearer <anon key>"
```

Then again with `Authorization: Bearer <your own access token>` (the
`authenticated` role, which any Google user can get by signing in).

| Role | Result | Date |
|---|---|---|
| anon | Not run as an exposure test: the Data API was already off. REST and GraphQL requests with the anon key return HTTP 503 `PGRST002` and no rows. | 2026-09-25 |
| authenticated | Not run: with the Data API off, `/rest/v1` serves no table to any role. | 2026-09-25 |

Any rows returned mean an incident: complete "Incident response" below. None
were returned, so there was no incident.

**2. Can RLS be enabled safely?** Through the pooler URL:

```sql
select tablename, tableowner from pg_tables where schemaname = 'public' order by 1;
select current_user, rolbypassrls from pg_roles where rolname = current_user;
show server_version;
```

| Check | Result (2026-09-25) |
|---|---|
| Owner of every `public` table | `postgres` |
| `current_user`, `rolbypassrls` | `postgres`, `true` |
| `server_version` (its major also goes in "Platform limits") | `17.6` |
| RLS safe: `current_user` owns every table or has BYPASSRLS | Yes (both) |

**3. Lockdown applied.**

| Action | Result | Date |
|---|---|---|
| (a) Dashboard → Project Settings → Data API: off | Already off before Step 0; left off. REST and GraphQL requests with the anon key return HTTP 503 `PGRST002` and no data. | 2026-09-25 |
| (b) Enable RLS on every `public` table (the `DO` block below) | Applied | 2026-09-25 |
| (b) The two REVOKEs from `anon` and `authenticated`, and the two `ALTER DEFAULT PRIVILEGES` (below) | Applied | 2026-09-25 |

```sql
-- Defense in depth; slice 1's 0003_lockdown repeats this idempotently.
DO $$
DECLARE t text;
BEGIN
  FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
  END LOOP;
END $$;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON TABLES FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON SEQUENCES FROM anon, authenticated;
```

If step 2 said "no", skip the `DO` block: RLS with no policies would hide every
row from both apps. Apply (a) and the REVOKEs only; slice 1 decides between
transferring table ownership and adding policies (ops spec, Risks item 1).

**4. Confirmation.**

| Check | Result | Date |
|---|---|---|
| Step-1 curls with the anon key: no rows | HTTP 503 `PGRST002`, no rows | 2026-09-25 |
| Step-1 curls with your access token: no rows | Not run: the Data API is off for every role | 2026-09-25 |
| GraphQL introspection lists no app tables (no `usersCollection`) | HTTP 503 `PGRST002`, no data | 2026-09-25 |
| `/me` works on https://worship-service-builder.vercel.app | Yes: the Vercel app loads the owner's church | 2026-09-25 |
| https://liturgy-stg.streamlit.app loads the owner's church | Yes | 2026-09-25 |
| Incident response needed (step 1 returned rows)? | No: the Data API was already off | 2026-09-25 |

GraphQL check:

```
curl -s -X POST https://tbecmwtitsoxzkrvxxxu.supabase.co/graphql/v1 \
  -H "apikey: <anon key>" -H "Content-Type: application/json" \
  -d '{"query":"{ __schema { queryType { fields { name } } } }"}'
```

**Rollback:** `ALTER TABLE public.<t> DISABLE ROW LEVEL SECURITY` for each
table, and turn the Data API back on. The REVOKEs need no rollback, because no
app uses those roles.

### Alembic stamping record (slice 1a)

Slice 1a's production runbook (`backend/migrations/README.md` → Production
runbook, steps 0–10) and its manual check (`docs/manual-verification.md` →
Slice 1). Step 2 above said yes, so the choice step 3 left to slice 1
(transferring table ownership or adding policies) never arose, and slice 1a
needs neither: `postgres`, the role both apps connect as through the session
pooler, owns every `public` table and has BYPASSRLS. RLS with no policies
therefore stays deny-all for `anon` and `authenticated` and hides no row from
the apps. `0003_lockdown` checks that before it changes anything, repeated the
lockdown idempotently and also enabled RLS on `alembic_version`. If a table is
ever owned by another role, follow `backend/migrations/README.md` → RLS
precondition before any migration runs. Steps 7 and 8 went differently from
the runbook: Railway's Config as Code is closed to this service, so the
pre-deploy command and the health check path are set in the Railway UI.

| Step | Result | Date |
|---|---|---|
| 0. RLS precondition rerun in the SQL Editor (step 2's two queries above) | 11 `public` tables, every one owned by `postgres`; `current_user`, `rolbypassrls`: `postgres`, `true`. Proceed (no ownership transfer, no policy). No table without RLS before the stamp. | 2026-09-27 |
| 1. Backup | `db-backup` run, green (see Backup run record) | 2026-09-27 |
| 2. `SHOW server_version;` | `17.6`; major 17 = `PG_MAJOR` and the CI image `postgres:17` | 2026-09-27 |
| 3. `alembic current` before stamping | No revision; the `Database:` line named the session pooler | 2026-09-27 |
| 4. `alembic stamp 0001_baseline` | `Running stamp_revision  -> 0001_baseline`; `alembic current` then showed `0001_baseline` | 2026-09-27 |
| 5. `alembic upgrade 0001_baseline:head --sql` | Read by the owner. `BEGIN;` first, `COMMIT;` last; 0 `CREATE TABLE`, 4 `ADD COLUMN IF NOT EXISTS`, 3 `UPDATE alembic_version`, no `Database:` line; SHA-256 `1988eb3de35d7e0eb651c4c5a8d5c71ff6e0314ff301f91eb2e29ec2f0e0582f`, equal to the reference rendered offline from PR #16's head `2376b6a` | 2026-09-27 |
| 6. `scripts/schema_drift.py` | `revision: 0001_baseline head: 0004_invites_reusable state: behind`, then `add_column invites.accepted_by`, `add_column invites.reusable`, `add_fk fk_invites_accepted_by_users` and `add_index ix_hymns_church_hymnal` (the index was missing in production; `0002_reconcile` creates it at the deploy); exit 1; no `text_year` or `hymnal_count` | 2026-09-27 |
| Branch protection on `main` | Required checks `backend`, `backend-postgres`, `frontend` (classic rule, set by the agent on the owner's yes; branches must be up to date; a PR is required, with 0 approvals; admins not enforced); `gh pr checks 16 --required` listed all three, passing | 2026-09-27 |
| 7. Railway → the API service → Settings, immediately before merging | Deploy → Healthcheck Path `/health/ready` (was `/health`), set in the UI. The Config-as-code path `/backend/railway.toml` was entered and confirmed by the owner, but it never took: Railway has deprecated Config as Code, and since 2026-08-28 "services that have never used Config as Code cannot opt in". So Railway never read the file's pre-deploy command; the owner set Deploy → Pre-deploy Command `alembic upgrade head` in the UI after the first merge deploy (step 8). A staged deploy of the pre-1a release went Active, and `/health/ready` → `{"ok":true,"db":"ok"}` afterwards. | 2026-09-27 |
| 8. Merge and deploy | PR #16 merged 2026-09-28T00:34:57Z (2026-09-27 20:34 EDT), merge commit `7ea7f55`. First merge deploy (20:35 EDT): no pre-deploy step; startup logged `schema revision 0001_baseline != head 0004_invites_reusable` at ERROR and `Row-level security is off on: alembic_version` at WARNING; the `/health/ready` health check failed (14 attempts, HTTP 503), so Railway kept the previous release serving; the database stayed at `0001_baseline`, with nothing applied. Fix: Settings → Deploy → Pre-deploy Command `alembic upgrade head`, set in the UI; then Redeploy of the merge deployment: Active. The new release serves (`ErrorBody` in `/openapi.json`); `/health/ready` → `{"ok":true,"db":"ok"}`, `/health` → `{"ok":true}`, `/me` signed out → 401 `unauthenticated` with `request_id`; Vercel production Ready; CI on the merge commit green (run 36362737497: `backend`, `backend-postgres`, `frontend`). The redeploy's `Running upgrade` lines were not recorded; step 9 (`alembic current` at `0004_invites_reusable (head)`) shows the upgrade ran. | 2026-09-27 |
| 9. `alembic current`, `alembic check`, `scripts/schema_drift.py` | `0004_invites_reusable (head)`; `No new upgrade operations detected.`; `revision: 0004_invites_reusable head: 0004_invites_reusable state: current`, exit 0 (run from the owner's laptop) | 2026-09-27 |
| 10. Streamlit smoke on https://liturgy-frozen.streamlit.app/ | Sign-in, church and hymnal, a saved service and Settings OK; Settings → Invites → Create invite (no email, member) and Revoke worked; the latest invite's `reusable`, `accepted_by`, `revoked`: `false`, `NULL`, `true` (the frozen app's insert got the new server default); no `public` table without RLS (`alembic_version` included); no code pull in its logs after the 20:34 EDT merge, branch still `streamlit-frozen` | 2026-09-27 |
| Keepalive run by hand | https://github.com/bbrown62450/church/actions/runs/36363728870: green, `{"ok":true,"db":"ok"}` from the 1a release | 2026-09-27 |
| Manual check 1 (at 375 px and on desktop) | Owner's account, on desktop and at 375 px (iPhone SE): sign-in, home shows the church, the church menu lists the churches with the role, the account menu shows name, email and `Role: Owner`, Log out returns to `/login`: all OK. The check with an account in no church (the stub `/welcome`) was skipped by the owner. | 2026-09-27 |

### Slice 1b record

Slice 1b (onboarding: create a church, join by invite) merged as PR #18
with no database change, so production stays at `0004_invites_reusable`
(head). The manual checks are `docs/manual-verification.md` → Slice 1,
items 2–11. They were run on the production app with the owner's own
Google account (A) only, on desktop and at 375 px (iPhone SE); B and C were
not used. No invite was created: invites can only be made in
liturgy-frozen today, and the owner chose not to use it, so the invite-link
checks (2, 3, 4, 8 and the desktop pass of 2–3) are deferred to slice 6b,
when the new app gets its invite UI. Joining is covered by the automated
tests, including the Postgres race tests. No invite code, email address or
database URL is recorded here.

| Step | Result | Date |
|---|---|---|
| Merge and deploy | PR #18 merged 2026-09-28T17:21:43Z (13:21 EDT), merge commit `ef56f59`. No migration, so production stays at `0004_invites_reusable` (head). The Railway deployment for `ef56f59` succeeded (GitHub deployment status), and the new API was live about 105 s after the merge; `/health/ready` → `{"ok":true,"db":"ok"}`. The pre-deploy and startup log lines were not recorded. Vercel Production deployment for `ef56f59`: success | 2026-09-28 |
| CI and public endpoints | CI on the merge commit `ef56f59` (main): success. Final CI run on the PR head `c2f733d` (run 36457255146): green; `backend` 798 passed, 9 skipped; `backend-postgres` 9 passed, 798 deselected; `frontend` 221 passed in 34 files; build OK. After the deploy: `/health/ready` → `{"ok":true,"db":"ok"}`; signed out, `POST /churches` → 401; `/openapi.json` lists `/invites/preview` | 2026-09-28 |
| Seed timing (S Risk 3) | CI Postgres (`backend-postgres`, run 36457255146): `hymn seed: 700 rows in 88 ms` (budget 3 s). Production church create (Railway deploy logs): `church_created … hymns_seeded=853 duration_ms=1086` and `POST /churches` 201 Created. Under the 5 s production threshold: no change. The DevTools timing and the `hymn_catalog` count comparison were not recorded | 2026-09-28 |
| Account chooser (S Risk 8) | Not yet verified. It is observed in check 4 (an email-bound invite opened by the wrong account), which is deferred to slice 6b | 2026-09-28 |
| Invite-link checks 2, 3, 4, 8 and the desktop pass of 2–3 | Deferred to slice 6b by the owner's choice: invites can only be made in liturgy-frozen today and the owner chose not to use it; the new app has no invite UI until slice 6b. Joining is covered by the automated tests, including the Postgres race tests | 2026-09-28 |
| 5. Create a church (owner's account, desktop) | Run as A, not as a new account with no church. Create tab: copy, helper and hymnal note OK; the default time zone shown was America/Indianapolis (the computer's zone). "1b Invite Test" → "Creating church…" → home with it active and the toast "Created 1b Invite Test. You're the owner."; the church switcher lists it as Owner, beside First Presbyterian Church | 2026-09-28 |
| 6. Double tap and blank name (375 px, Slow 4G) | As A at 375 px (iPhone SE): blank name → "Church name is required.", focus in the field, no `churches` request sent; double tap on Slow 4G → exactly one "1b Double Tap Test" church | 2026-09-28 |
| 7. Switcher "Join or create a church…" (desktop) | A on desktop: switcher → "Join or create a church…" → `/welcome` with the heading "Join or create a church", the "Signed in as" line, "← Back to First Presbyterian Church" and the tabs Join a church (selected) and Create a church; the back link and browser Back OK. After check 5, both churches listed and switching both ways OK. The 375 px part as C (a third church, Member and Owner) was not run: only A was used and no church was joined | 2026-09-28 |
| 9. Log out, other device | Not run (owner). The landing of an account with no church was not run either | 2026-09-28 |
| 10. Mobile layout (375 px) | At 375 px (iPhone SE): no sideways scroll and everything fits on `/welcome` (both tabs), `/join` with no code (the "This invite link is incomplete." card with Go to home), and home's church switcher and account menu. The other `/join` cards need an invite and were not checked (see the deferred row). The 16 px input size and 44 px tap targets were not measured by hand; the automated tests cover them. The desktop pass of check 10 and the F §5.5 regression pass (Log out, sign in again) were not recorded; switching church both ways was OK (check 7 row) | 2026-09-28 |
| 11. Streamlit smoke on liturgy-frozen (AC17) | Not run: skipped by the owner. Slice 1b changes no schema, and merges never reach liturgy-frozen | 2026-09-28 |
| Test churches left in production | Two, owned by A: "1b Invite Test" and "1b Double Tap Test" | 2026-09-28 |
| Follow-ups | Slice 6b: run checks 2, 3, 4 and 8, the desktop pass of 2–3 and the S Risk 8 chooser observation once the new app has its invite UI. Seed timing: none (under 5 s) | 2026-09-28 |

### Slice 2a record

Slice 2a (the readings backend: `GET /lectionary/readings`, `POST /scripture/passages`,
`GET /translations` and the new `GET /church` fields) merged as PR #20 with no
database change, so production stays at `0004_invites_reusable` (head). No page in
the new app calls the new routes until 2b and 2c, so the live checks were API calls
from the production site's DevTools with the owner's own account. All 25 upstream
test fixtures were hand-built, because the build session's network policy blocked
lectio-api.org, lectionary.library.vanderbilt.edu and bible-api.com; the live calls
below are the first check against the real sites. No token, key, email address or
church id is recorded here.

| Step | Result | Date |
|---|---|---|
| Merge and deploy | PR #20 merged 2026-09-28 about 21:22 UTC (17:22 EDT), merge commit `8cf0793`. No migration. Railway: the deployment for `8cf0793` Active (owner); `/health/ready` → ok (owner, browser). The pre-deploy and startup log lines were not read. CI on `main` for `8cf0793` (run 36485572541): success | 2026-09-28 |
| CI on the PR head `16dae79` | Run 36485313947: `backend` 971 passed, 9 skipped; `backend-postgres` green (Alembic cycle, pg_smoke, Postgres-only tests); `frontend` green (lint, typecheck, API types match, 221 tests, build); Vercel preview Ready | 2026-09-28 |
| ESV on Railway | `ESV_API_KEY` was not set. The owner added it and deployed; `/health/ready` → ok after. ESV is now offered by `/translations` | 2026-09-28 |
| `GET /church` new fields (AC6) | `timezone` America/New_York, `timezone_valid` true, `bible_translation` null, `effective_translation` web, `effective_translation_label` World English Bible (WEB). The `/me` items check was not recorded | 2026-09-28 |
| `/translations` | 200, default web, `esv_available` true, items web, kjv, asv, ylt, dra, darby, bbe, oeb-us, webbe, esv | 2026-09-28 |
| `/lectionary/readings` (AC1, AC2, AC9) | 2026-10-04: ok, not partial, "Nineteenth Sunday after Pentecost" (merged), ending Matthew 21:33-46; the cold lookup took 5.4 s. 2026-11-01: ok, "All Saints Day" (Vanderbilt) and "Twenty-Third Sunday after Pentecost" (merged, ending Matthew 23:1-12), default the second (owner Q2). 2026-03-29: exactly the test's Palm Sunday answer ("Liturgy of the Palms", "Liturgy of the Passion"). Warm lookups about 0.4 s. `date=2026-3-29` → 422 "Not a valid value." Both sources answered on every date, so Vanderbilt's real Content-Type is accepted and the hand-built fixtures matched the real data on these dates | 2026-09-28 |
| `/scripture/passages` (AC5) | John 3:16 in WEB: 200, ok, "For God so loved the world…". In ESV: 200, ok, with the "(ESV)" credit | 2026-09-28 |
| API log lines (`lectionary_lookup`) | Not read: the answers above show both sources ok | 2026-09-28 |
| Streamlit smoke on liturgy-frozen | Not run: skipped by the owner for now. Slice 2a changes no schema, and merges never reach liturgy-frozen | 2026-09-28 |
| Follow-ups | Run the liturgy-frozen smoke when convenient. Slice 2b: the frontend foundation (builder shell, draft store, `/` → `/builder`); 2c: the Date & readings step UI, where the Saturday vigil question (spec open question 2) is asked | 2026-09-28 |

### Slice 2b record

Slice 2b (the frontend foundation: the Service Builder shell, the draft saved on
this device, date and scripture-reference helpers, `/` → `/builder`) merged as
PR #22 with no backend or database change, so production stays at
`0004_invites_reusable` (head). Every step, Date & readings included, shows the
"Available soon" card until 2c (owner answer Q1). Per owner answer Q4 the checks
are the automated tests plus a short look by the owner on phone and desktop.

| Step | Result | Date |
|---|---|---|
| Merge and deploy | PR #22 merged 2026-09-29 about 01:56 UTC (21:56 EDT on 2026-09-28), merge commit `c021a7f`. CI on `main` for `c021a7f` (run 36510209152): success. Vercel deployed; the owner's look below ran on production | 2026-09-29 |
| CI on the PR head `b12e463` | Run 36510043116: `backend`, `backend-postgres` and `frontend` green; frontend 299 tests in 49 files (221 in 34 before), also green locally with the clock moved +8 and +400 days; backend unchanged at 971 passed, 9 skipped | 2026-09-29 |
| Phone look | `/` opens Service Builder at "Step 1 of 4 · Date & readings" with the "Available soon" card, the "Builder" row under the header and Back/Next at the bottom. Summary opens as a bottom sheet with Sunday, October 4, 2026, "Available soon" blocks and "Draft saved on this device · Not in archive". Next: Hymns moves to step 2; Back has its outline. Owner: looks good | 2026-09-29 |
| Desktop look | Summary in the right column, the four named steps in the step bar, "Builder" in the header. New service on an untouched draft resets at once and opens Date & readings. Owner: looks good | 2026-09-29 |
| Follow-ups | 2c: the Date & readings step; add `"readings"` to `SHIPPED_STEPS`; count a user-picked date as unsaved and ask the owner about card toggles and overrides; auto-fill readings only in the visible tab; the Saturday vigil question. 5a: the owner question about the Readings-available banner on an archived service. Still open from 2a: the liturgy-frozen smoke | 2026-09-29 |

### Slice 2c record

Slice 2c (the Date & readings step: lectionary lookup and automatic fill, the
set switcher, Occasion and Scripture readings, passage text by translation and
the bulletin OT and NT picks) merged as PR #24 with no backend or database
change, so production stays at `0004_invites_reusable` (head). Hymns, Liturgy
and Review still show "Available soon". Per owner answer Q3 the checks are the
automated tests plus the owner's guided six-step phone check and a desktop look,
on production with live lectionary and Bible text. They cover
`docs/manual-verification.md` "## Slice 2" checks 1, 2, 3, 4, 8, 9, 12 and 14 in
part; checks 5, 6, 7, 10, 11 and 13 were not run.

| Step | Result | Date |
|---|---|---|
| Merge and deploy | PR #24 merged 2026-09-29 about 14:23 UTC (10:23 EDT), merge commit `d660cb1`. CI on `main` for `d660cb1` (run 36582341516): success. Vercel deployed; the checks below ran on production | 2026-09-29 |
| CI on the PR head `c676a9b` | Run 36581969543: `backend`, `backend-postgres` and `frontend` green; frontend 356 tests in 55 files (299 in 49 before), also green locally with the clock moved +8 and +400 days; backend unchanged at 971 passed, 9 skipped | 2026-09-29 |
| 1. Next Sunday | Opens on Date & readings dated Sunday, October 4, 2026, "Nineteenth Sunday after Pentecost" with four readings ending Matthew 21:33-46; the step shows Complete. Owner: looks good | 2026-09-29 |
| 2. A day with no readings | Tuesday, October 6, 2026: "No lectionary readings for …" with Enter readings, the note that the readings are from October 4 with Clear readings; Clear empties the fields. Owner: looks good | 2026-09-29 |
| 3. Two sets | Palm Sunday, March 21, 2027: two cards with the Passion set selected; tapping Palms switches the readings. Owner: looks good | 2026-09-29 |
| 4. Your own reading | A typed line changes the caption to "Edited from the lectionary (…)"; on October 11 "Readings for … are available." appears, Use them asks "Replace your readings?", Keep mine keeps the lines. Owner: looks good | 2026-09-29 |
| 5. Bible text | After New service, Show text on Isaiah 5:1-7 loads; switching to King James and ESV changes the text, ESV ending "(ESV)". Owner: looks good | 2026-09-29 |
| 6. Bulletin readings | Automatic Isaiah 5:1-7 and Philippians 3:4b-14; picking Psalm 80:7-15 then Use automatic restores it; New service with only a translation change starts over without asking and keeps the translation. Owner: looks good | 2026-09-29 |
| Desktop look | The summary column shows the date, occasion and readings with OT and NT marks; no sideways scroll. Owner: looks good | 2026-09-29 |
| Follow-ups | Slices 3 and 4: whether card toggles, hymnal overrides and hymn alternatives count as unsaved work (owner question). 5a: the Readings-available banner on an archived service (owner question). A date changed away from a rate-limited date and back asks again before Retry-After. Still open: manual checks 5, 6, 7, 10, 11 and 13, including the liturgy-frozen smoke | 2026-09-29 |

### Slice 3a record

Slice 3a (the Hymns step backend: `GET /hymnals`, `GET /hymns`,
`POST /hymns/scripture-matches`, `POST /hymns/suggestions`, the new OpenAI
client and two new `GET /church` fields) merged as PR #26 with no database
change, so production stays at `0004_invites_reusable` (head). No page calls the
new routes until 3b; the Hymns step still shows "Available soon". The live checks
were the owner's, from the Railway logs and a signed-in Console snippet.

| Step | Result | Date |
|---|---|---|
| Merge and deploy | PR #26 merged 2026-09-29 about 18:43 UTC (14:43 EDT), merge commit `1a1441e`. Deploy Logs: pre-deploy with no `Running upgrade` line; health check 200; first startup line `AI: not configured (OPENAI_API_KEY missing)`, as expected before the key was set; no Traceback or ERROR | 2026-09-29 |
| CI on `main` | Runs 36614060751 and 36614088233 for `1a1441e`: success. On the PR head `67e3046`: backend 1106 passed, 11 skipped; backend-postgres 11 passed; frontend 356 in 55 files | 2026-09-29 |
| Scripture sample | The owner's read-only export of `hymn_catalog` (400 rows spread across the catalog) replaced the synthetic sample before the PR was marked ready: 2 798 of 2 798 segments parsed (100 %). `hymn_usage.date_iso`: 90 rows, all 10 characters (`YYYY-MM-DD`) | 2026-09-29 |
| OpenAI | A separate project and key for this app, set on Railway by the owner (never shared in chat); monthly budget cap $15. The project's allowed-models list held only `gpt-3.5-turbo`, `gpt-4-turbo` and `text-embedding-3-small`; the owner added `gpt-4.1-mini`, the plan's recommendation. `OPENAI_REASONING_EFFORT` not set | 2026-09-29 |
| Model variable | A stale `OPENAI_MODEL=gpt-3.5-turbo` from the old app was already on Railway, so the first deploy after the key logged `AI: configured (model=gpt-3.5-turbo)`. The owner edited it; the next deploy logged `AI: configured (model=gpt-4.1-mini)` with no part of the key shown | 2026-09-29 |
| Console check | `/church` 200 (default none, effective GG2013); `/hymnals` 200: GG2013, 853 hymns, 795 with scripture references; `/hymns` 200 in 1411 ms, total 853, 244 newer than preferred, `content-encoding: gzip`; scripture matches for October 4, 2026 200 in 1027 ms, 25 matched, none unparsed; one suggestion 200 in 3940 ms with 5 hymns per slot, three distinct top picks, all from the model, NT text fetched for Matthew 21:33-46 | 2026-09-29 |
| Streamlit smoke | Not run (optional; merges never reach liturgy-frozen) | 2026-09-29 |
| Follow-ups | 3b: the Hymns step UI, and whether hymnal changes and hymn alternatives count as unsaved work (owner question). The Console check found no recent use within 12 weeks of October 4 (`recent=0`) although 90 uses are logged: check in 3b whether they are older or belong to another church. The suggestion's response slot included two Palm Sunday hymns on the Nineteenth Sunday after Pentecost: if off-season picks recur in 3b, add church-year guidance to the prompt. Research whether Hymnary.org can supply first lines for title matching (owner answer Q2). Known risk: one member's burst of 40 suggestions can briefly hold most worker threads before `ai_busy` | 2026-09-29 |

## Backups

- **Workflow:** `.github/workflows/backup.yml` (`db-backup`). Daily at 08:37 UTC,
  and by hand from `main`: Actions → db-backup → Run workflow (branch `main`),
  or `gh workflow run db-backup --ref main`.
- **What it does:** checks the server's Postgres major against `PG_MAJOR`,
  dumps the `public` schema with `pg_dump --format=custom --no-owner
  --no-privileges`, pipes it through `age` to every key in
  `.github/backup/age-recipients.txt`, and uploads
  `backup-<UTC timestamp>.dump.age` as the artifact `db-backup`, kept 30 days.
  No plaintext dump touches the runner's disk. Supabase-managed schemas
  (`auth`, `storage`) are not included; users sign in again with Google and are
  matched by email.
- **Secret:** `BACKUP_DATABASE_URL`, an **environment secret** of the GitHub
  Environment `backup` (repo Settings → Environments → `backup`), whose
  deployment-branch rule admits only `main`, so a workflow on any other branch
  cannot read it. There is no repository secret of that name. The value is
  the Supabase **session pooler** URL the apps use. The direct host is
  IPv6-only on Free and GitHub runners are IPv4. The SQLAlchemy form
  (`postgresql+psycopg2://…`) is fine: `.github/backup/pg_env.py` reads the
  URL as the app does, masks each part in the log (password, user, host,
  whole URL), and hands the parts to `psql` and `pg_dump` as `PG*` variables,
  so the URL never reaches a command line. The secret is added only after the
  encrypted workflow is on `main`; until then every run fails at "Check
  prerequisites", which is intended. Scheduled runs use `main`; a manual run
  from any other branch is refused by the environment.
- **Artifacts** are encrypted, so it is acceptable that anyone signed in to
  GitHub can download them from this public repo.

### Key custody

1. Created once with `brew install age`, then `age-keygen -o ~/wsb-backup-key.txt`.
2. The whole key file is stored in the owner's password manager, plus one
   offline copy; then the file is deleted from disk.
3. The private key never goes to GitHub, Railway, the repo or chat. Only the
   `age1…` public line is committed, in `.github/backup/age-recipients.txt`.
4. Every public key in that file can decrypt every new backup. An optional
   second recovery key, stored apart from the first, protects against losing
   the first.

| Key | Where the private key is kept | Created |
|---|---|---|
| `age1zl8f90cg` | [owner: password-manager entry name; offline copy: yes/no] | 2026-09-26 |

### Rotating the key

1. Generate and store the new key as in "Key custody".
2. PR: add its `age1…` line to `.github/backup/age-recipients.txt` next to the
   old one. After merging, run db-backup by hand and decrypt that artifact
   with the new key (the download and `age --decrypt` lines of the restore
   drill).
3. PR: remove the old line. Keep the old private key for 30 more days, until
   the last artifact encrypted to it has expired, then destroy every copy.
4. If a private key is exposed: remove its line at once, delete the existing
   `db-backup` artifacts (Actions → db-backup → each run → Artifacts), and run
   db-backup by hand so a fresh backup exists under the remaining keys.

### Restore drill (once in the ops slice, then quarterly)

```
cd "$(mktemp -d)"                                            # a fresh, empty folder
gh run download <run-id> -R bbrown62450/church -n db-backup  # or download from the Actions UI
ls backup-*.dump.age                                         # exactly one file: use its full name below
# Save the whole key file from the password manager as ~/wsb-backup-key.txt, then:
age --decrypt -i ~/wsb-backup-key.txt -o backup.dump backup-<timestamp>.dump.age
docker run --rm -d --name wsb-restore -e POSTGRES_PASSWORD=restore postgres:17
until docker exec wsb-restore pg_isready -h 127.0.0.1 -U postgres; do sleep 1; done
docker exec -i wsb-restore pg_restore -h 127.0.0.1 -U postgres -d postgres --no-owner --no-privileges < backup.dump
docker exec wsb-restore psql -h 127.0.0.1 -U postgres -Atc "select 'users', count(*) from users union all select 'churches', count(*) from churches union all select 'services', count(*) from services union all select 'hymns', count(*) from hymns"
docker stop wsb-restore
rm -f backup.dump ~/wsb-backup-key.txt backup-*.dump.age     # the plaintext dump holds Gmail refresh tokens; the key never stays on disk
```

If you stop early (for example Ctrl-C during the `pg_isready` wait), still run
the cleanup `rm …` line and `docker stop wsb-restore`, so no plaintext dump or
key file is left on disk.

- Use an image tag at least as new as the server major (`PG_MAJOR`).
- The wait uses TCP (`-h 127.0.0.1`) because the image first runs a temporary,
  socket-only server for initdb and then restarts; a socket connection can hit
  that temporary server and be cut off in the middle of the restore.
- Expected: at most the harmless `schema "public" already exists` error, and
  every table restored.
- Run the same count query on production (Supabase SQL editor) and compare.
  Rows written between the dump and the check are the only allowed difference.

| Date | Run | Artifact | Counts: restored / production (users, churches, services, hymns) | Result |
|---|---|---|---|---|
| [owner] | [owner: run URL] | [owner: backup-….dump.age] | [owner] | [owner] |

### Backup run record

| Date | Run | Result |
|---|---|---|
| 2026-09-26 (first manual run after ops-1) | https://github.com/bbrown62450/church/actions/runs/36261197972 | Green. Artifact `db-backup` (225,686 bytes, encrypted), expires 2026-10-26. A scan of the public log found no database host, user, URL, `PGPASSWORD` or private-key text; 4 values were masked as `***`. |
| 2026-09-27 (slice 1a runbook step 1, before stamping) | https://github.com/bbrown62450/church/actions/runs/36362040801 | Green. Artifact `db-backup` (225,690 bytes, encrypted), expires 2026-10-28. The log shows no URL or pooler host. |

## Keep-alive

Supabase Free pauses a project after about 7 days without activity, and
Streamlit Community Cloud hibernates an app after 12 hours without traffic.
Two scheduled workflows keep both awake:

- **`keepalive`** (`.github/workflows/keepalive.yml`): daily at 09:17 UTC, and
  by hand (Actions → keepalive → Run workflow, or `gh workflow run keepalive`).
  It curls `${API_BASE_URL}/health/ready` (up to 4 tries, 20 s apart) and is
  green when that returns 200 `{"ok":true,"db":"ok"}`. The API answers with a
  `SELECT 1` through its own connection pool, so the database sees real
  activity. The job holds no database credentials and no token permissions.
- **`keep-awake`** (`.github/workflows/keep-awake.yml`): every 6 hours it opens
  https://liturgy-frozen.streamlit.app/, the production Streamlit app since the
  Freeze on 2026-09-26 (it opened https://liturgy-next.streamlit.app/ before),
  in headless Chromium (a plain HTTP ping does not count as traffic). Deleted
  in slice 7.

**Variable.** `API_BASE_URL` = `https://church-production-74ca.up.railway.app`,
under repo Settings → Secrets and variables → Actions → **Variables** (not
Secrets). It is not a secret: the frontend bundle already carries the same URL
as `NEXT_PUBLIC_API_URL`. Without it the job fails with
`::error::Set the API_BASE_URL repository variable (Settings → Secrets and variables → Actions → Variables)`.

**`GET /health/ready`** is public and reads no table. It memoizes its answer
(10 s after a success, 5 s after a failure) and runs at most one probe at a
time, so however many requests arrive it holds at most one pooled
connection. 503 `db_unavailable` means the API cannot reach the database, and
the Railway logs then show `Readiness check failed: <exception class>`.
An error that is not a database error instead gives a 500 `internal_error`
and the log line `Unhandled error on GET /health/ready`.
`GET /health` stays the dependency-free liveness probe. Since slice 1a
`/health/ready` is also Railway's deploy health check, and in production it
answers 503 `db_unavailable` with `details.reason` `schema_behind` while the
database schema is behind the release (`backend/migrations/README.md`).

**If `keepalive` is red:**
1. `curl -i https://church-production-74ca.up.railway.app/health`. If that
   fails too, the API is down: Railway → the API service → Deployments.
2. If `/health` is 200 and `/health/ready` is 503: Supabase Dashboard → is the
   project paused? Restore it. Otherwise read the Railway logs for
   `Readiness check failed:`.
   If `/health/ready` is 500 instead, look for
   `Unhandled error on GET /health/ready`.
3. If the log shows `::error::Set the API_BASE_URL repository variable …`,
   set the variable as above.
4. GitHub disables scheduled workflows in a public repository after 60 days
   without activity (ops spec, Risks item 7): re-enable it under Actions →
   keepalive. Slice 7 adds an external uptime monitor.

| Date | Run | Result |
|---|---|---|
| 2026-09-26 (first manual run after ops-3) | https://github.com/bbrown62450/church/actions/runs/36282260699 | Green; the log shows `{"ok":true,"db":"ok"}`. |

## Streamlit freeze

### Streamlit apps

The ops spec names `liturgy` as production and deletes `liturgy-stg`. The
owner corrected this on 2026-09-25: it is the other way round.

| App | URL | Status |
|---|---|---|
| `liturgy-frozen` | https://liturgy-frozen.streamlit.app/ | **Production** since the Freeze on 2026-09-26. Repo `bbrown62450/church`, branch `streamlit-frozen`, main file `app.py`, Python 3.14, Sharing public. The owner created it on 2026-09-26 as the Freeze's temporary pre-flight app and then kept production on it, running its pre-flight build, instead of moving it onto `liturgy-next` (see the note below and the Freeze record). Merges to `main` do not reach it. Its Secrets are `liturgy-next`'s with `[auth] redirect_uri = https://liturgy-frozen.streamlit.app/oauth2callback` and `GOOGLE_OAUTH_REDIRECT_URI = https://liturgy-frozen.streamlit.app/`, both registered on the Google OAuth client "Liturgy"; the owner keeps a copy in the password manager. The pre-flight smoke check passed without the Gmail connect and test send, so the `gmail.send` flow has not been checked on this address. `keep-awake` keeps it awake. |
| `liturgy-next` | https://liturgy-next.streamlit.app/ | **Deleted 2026-09-26** in the Freeze window. Production from 2026-09-26 until the Freeze that evening: it deployed from repo `bbrown62450/church`, branch `main`, main file `app.py`, Python 3.14.7 (its log; this runbook had said 3.13). `liturgy-stg`, which ran from the old branch `claude/multi-user-app-support-edd5eb`, was deleted that day during Task 9a. Streamlit Community Cloud allows only one app per repository + branch + main file, and `liturgy-next` (created earlier as a side-by-side test) already held `main`/`app.py`. So the owner kept `liturgy-next` as the production address instead of recreating `liturgy-stg`, and checked sign-in, church and hymnal, saved services and a Gmail test send on it. No app holds its subdomain now. Its two Google redirect URIs (`https://liturgy-next.streamlit.app/oauth2callback` and the bare root `https://liturgy-next.streamlit.app/`) were removed from the OAuth client after it was deleted (see the Freeze record). |
| `liturgy` | https://liturgy.streamlit.app/ | **Deleted 2026-09-26** (it was unused; its Google sign-in failed with `StreamlitAuthError` from its secrets config). The URL now returns 404. Its two Google redirect URIs (`https://liturgy.streamlit.app/oauth2callback` and the bare root `https://liturgy.streamlit.app/`) were removed from the OAuth client on 2026-09-26 (see the Freeze record). |

**2026-09-26: production stays on `liturgy-frozen`.** The Freeze planned to
delete `liturgy-next` and move the checked pre-flight app onto its subdomain
(plan Task 14, path A, which was available). The owner deleted `liturgy-next`
and then decided to keep production on `liturgy-frozen` permanently instead of
renaming it. What that means:

- The production address changed to https://liturgy-frozen.streamlit.app/.
  The tester has to be told (Freeze record); the old address has no app.
- No app holds the `liturgy-next` subdomain, so anyone may be able to claim
  it. Its two redirect URIs were removed from the Google OAuth client for that
  reason; add them back only once an app of this project holds that
  subdomain again.
- `keep-awake` and `PRODUCTION_STREAMLIT_URL` in
  `backend/tests/test_ops_workflows.py` point at `liturgy-frozen` (records
  PR A).
- Renaming the app to `liturgy-next` later would repeat the move: the
  subdomain has to be free, the tester's address changes again, the Secrets'
  two redirect values change back, the `liturgy-next` URIs are registered
  only once the app holds that subdomain (and the `liturgy-frozen` ones
  removed once no app holds it), and `keep-awake` and the test follow.

### Streamlit bug triage

Every Streamlit bug in the inventory, checked against the freeze policy's
definition of a data-safety fix: data loss, corruption, leakage or security.
"Stored data" means rows in the database; losing text typed but not yet saved
is a usability bug, not a data-safety one.

| Inventory | Bug | Meets the definition? | Disposition |
|---|---|---|---|
| D5, and F6 "drops a loaded service's own hymns" | With "Exclude hymns used in the last 12 weeks" ticked, Prepare records the picks and reruns; the picks are now "recent", `safe_hymn_selectbox` resets them to '', and the next Prepare or Save stores no hymns. Loading a recent archived service with the box ticked drops its hymns, and "Save changes" then overwrites the archived hymns. | **Yes: silent loss of stored data in the normal Prepare → Save flow** | **Fixed in ops-1** (below). Until the fix is live, the tester relies on the D5 workaround message; the date it was sent is in the D5 record below. |
| A7 | A Word file prepared for church A can be downloaded or emailed while church B is active, to church B's contacts. | Leakage, in principle | **Accepted.** The tester belongs to one church, and Streamlit offers no way to join or create a second one (onboarding runs only at zero churches, inv A5), so the switcher never renders (the pre-freeze smoke check on 2026-09-26 confirmed there is no "Church" selectbox in the sidebar). React keys the draft and documents by church (slice 2, 5a). |
| E6 | Raw provider error text, or the "[Configure OPENAI_API_KEY…]" placeholder, becomes the liturgy text and can be saved or printed. | Corruption, in principle | **Accepted.** The Preview shows the text before Prepare or Save, so it is never saved silently, and Streamlit blocks Generate entirely when no key is set (inv E6). The new app shows such stored text as ordinary text and never writes error text itself (F §6.2). |
| E4 | Generate replaces the liturgy wholesale, so an unticked section of a loaded service disappears, and "Save changes" then overwrites it. | Loss, but visible | **Accepted.** The section is visibly missing from the Preview before Save, and the loaded text is still in its "Your text" box, so ticking the section and generating again restores it verbatim (inv E2). |
| D6 | With no Opening hymn, the Response hymn is stored first and reloads into the Opening slot. | Corruption of the slot order, visible | **Accepted.** It happens only when Opening is left empty, and the shifted slot is visible in the pickers before the next Save. The new app always writes three positional entries (F §6.2). |
| F6 | A hymn renamed or deleted in Settings is silently dropped when a service that used it is loaded; the next Save stores it without that hymn. | Loss, rare and visible | **Accepted.** It needs a hymn rename or delete, and the empty slot is visible before Save. |
| F7 | Last write wins; any member can overwrite any service. | Loss under concurrent edits | **Accepted.** One person uses the app. `If-Match` arrives in 5a. |
| F10 | All recipients go in one visible To header. | Contacts see each other's addresses | **Accepted.** This is the behavior the tester already relies on, and the recipients are the church's own contacts. 5b moves them to BCC (owner decision 9). |
| D3, D7, E6, F9 | Member-editable hymn titles and links rendered as unescaped markdown; configuration details and raw exception text shown to members. | Security, low | **Accepted.** Only signed-in members of the tester's own church can write hymns or see these messages. The React UI escapes and uses fixed messages (F §1.5, §4.8). |
| G7, G8, B1 | Admins can grant owner; the role is not validated on invites; code-only invites can be reused. | Security | **Accepted** by F §6.2, because the owner is the tester. 6b fixes them. |
| F4 | Usage is recorded on Prepare and never removed; the check-then-insert can race. | Stale data, not loss | **Accepted** by F §6.2. 5a replaces usage per date on save. |
| B2, G2 | Timezones are free text. | No | Not data-safety. Slices 1, 2 and 6a validate them. |
| C1, C4 | No readings, or a reading-set switch, overwrites the occasion and scriptures typed but not yet saved. | No (nothing stored is touched) | Not data-safety. |
| G5 | On Postgres, hymns with no number beyond the first 50 can't be seen or deleted in Settings. | No (nothing is lost) | Not data-safety. 6a replaces the page. |
| inv §4 | The Data API exposed the tables; backups were unencrypted. | Security | **Fixed in ops** (Step 0, S2), outside the Streamlit code. Step 0 (2026-09-25) found the Data API already off, and added RLS and the REVOKEs. |
| inv §4 | Gmail refresh tokens are stored in plaintext. | Security | **Deferred to slice 7** (F §6.4), because the frozen app reads them. The lockdown and the encrypted backups remove the exposure paths. |

### D5 fix and recovery record

ops-1 adds `ui_helpers.hymn_options_excluding_recent`, which `app.py` uses when
"Exclude hymns used in the last 12 weeks" is ticked: hymns already picked in the
three slots stay selectable, so Prepare, Save and loading a recent service no
longer clear them. Recent hymns that are not picked stay hidden.

| Event | Date |
|---|---|
| D5 workaround message sent to the tester | Not sent (owner decision, 2026-09-26): the fix goes live right after the ops-1 merge, when production Streamlit moves to `main` (Task 9a; production became `liturgy-next` instead), so the window is short. |
| ops-1 build live on https://liturgy-next.streamlit.app/ | 2026-09-26 (liturgy-next deployed from `main`, which includes the D5 fix; the owner verified sign-in, church and hymnal, saved services and a Gmail test send) |
| D5 manual check passed on https://liturgy-frozen.streamlit.app/ (planned on `liturgy-next`, then on the pre-flight app `liturgy-frozen`) | Not run: skipped by the owner on 2026-09-26, on neither app; still open in `docs/manual-verification.md` |
| "Fixed" message sent to the tester | [owner] |

**Recovery queries** (Supabase SQL editor, after the fix is live).

1. Archived services saved without hymns:

```sql
select church_id, service_date_iso, occasion, saved_at from services
where case when hymns is null or jsonb_typeof(hymns::jsonb) <> 'array' then true
           else jsonb_array_length(hymns::jsonb) = 0 end
order by service_date_iso desc;
```

2. Services that lost some of their hymns. Loading an older archived service
   with the box ticked clears only the slots whose hymn is recent, so "Save
   changes" can store one or two hymns. `hymn_usage` keeps what was recorded
   when the service was prepared, so a service that stores fewer hymns than
   its usage rows (at most 3) is a candidate. It also lists query 1's rows
   that have usage, and a service whose picks were changed between two
   Prepares can show up without having lost anything, so ask before re-saving.

```sql
select s.church_id, s.service_date_iso, s.occasion, s.saved_at,
       case when jsonb_typeof(s.hymns::jsonb) = 'array' then jsonb_array_length(s.hymns::jsonb) else 0 end as stored,
       count(u.id) as used
from services s
left join hymn_usage u on u.church_id = s.church_id and u.date_iso = s.service_date_iso
group by s.id
having least(count(u.id), 3) >
       case when jsonb_typeof(s.hymns::jsonb) = 'array' then jsonb_array_length(s.hymns::jsonb) else 0 end
order by s.service_date_iso desc;
```

For each row of either query, this lists the hymns picked when the service was prepared:

```sql
select hymn_number, hymn_title from hymn_usage
where church_id = '<church_id>' and date_iso = '<service_date_iso>';
```

Ask the tester whether the service really had no hymns, or only the ones it
stores. If hymns are missing, the tester loads it, picks them again and clicks
"Save changes".

Result: [owner: "no rows" for both queries, or per row: the query, the date, the hymns `hymn_usage` lists, the tester's answer, and whether the service was re-saved]

### What the frozen app inherits from ops-2

`liturgy-next`, the production Streamlit app until the Freeze, deployed from
`main` (branch `main`, main file `app.py`; see "Streamlit apps"), so ops-2
went live on it when it merged, before the freeze locked it in (ops spec,
Delivery plan). `streamlit-frozen`, which `liturgy-frozen` runs, includes it:

- Sign-in runs `auth.upsert_from_claims`, now a thin wrapper over
  `repos.users.ensure_user`. Per rerun it runs an
  `INSERT … ON CONFLICT (email) DO NOTHING` plus a SELECT, instead of a
  SELECT plus an unconditional UPDATE. It still writes `google_sub` when
  Google supplies one (by an UPDATE, never the INSERT), writes
  `last_login_at` at most hourly, and no longer races on a first sign-in.
- The Postgres pool is 3 + 3 with `connect_timeout=10`, instead of
  SQLAlchemy's default 5 + 10 with no timeout (see Platform limits).

| ops-2 gate (ops spec, Delivery plan) | Result | Date |
|---|---|---|
| Pre-check: `liturgy-next`'s Settings shows branch `main` and main file `app.py`; if not, stop and do not merge | Yes: branch `main`, main file `app.py` | 2026-09-26 |
| Production `users` has a unique constraint or non-partial unique index on exactly `(email)`, the `ON CONFLICT` target | Yes: `users_email_key`, `CREATE UNIQUE INDEX users_email_key ON public.users USING btree (email)`, no `WHERE` (from `pg_indexes`) | 2026-09-26 |
| `DB_POOL_SIZE` and `DB_MAX_OVERFLOW` are both present and `3` on Railway (API) and as top-level keys in `liturgy-next`'s Secrets | Yes: both `3` in Railway's API Variables, and both `3` above `[auth]` in `liturgy-next`'s Secrets | 2026-09-26 |
| API deploy of the ops-2 merge live; sign-in on https://worship-service-builder.vercel.app works | Yes: Railway's Active deployment is `57beda0` (the ops-2 merge); a fresh Google sign-in shows First Presbyterian Church and the Service Builder card | 2026-09-26 |
| New `liturgy-next` build after the merge; smoke check passed on https://liturgy-next.streamlit.app/ | Yes: rebooted after the merge; fresh Google sign-in, church and hymnal, and one saved service (readings and hymns) all worked | 2026-09-26 |
| The tester used `liturgy-next` for at least one day and nothing regressed | **Waived by the owner**: ops-3 goes ahead without a tester day. Rows above all passed, including a fresh sign-in on both apps on the ops-2 build. A regression the tester reports later is handled as an incident (Incident response). | 2026-09-26 |

### What the frozen app inherits from ops-3

Nothing that the Streamlit app runs. ops-3 changes the FastAPI app
(`backend/api/`, which Streamlit never imports), adds `backend/db/health.py`
(imported only by the API), deletes the old keep-alive script (never
imported), edits a docstring in `backend/db/engine.py`, changes workflows and
docs, and adds the FROZEN comment at the top of `app.py`. So
`streamlit-frozen`, cut from the ops-3 merge commit, runs what `liturgy-next`
already ran from `main` after ops-2:

- the service rubric (PR #4): it reads `churches.settings.rubric` and maps
  `text_year` and `hymnal_count` (F §6.2, amendment 2026-09-26);
- the D5 fix (ops-1; see "D5 fix and recovery record");
- `ensure_user` through `upsert_from_claims`, and the 3 + 3 pool with
  `connect_timeout=10` (ops-2; see the gate table above);
- without the six dead modules (ops-1), which it never imported.

It never gets the prayer library (PR #7) or the new season wording (PR #8):
both are new-app only (F §6.2). `streamlit_tests/` passed on the ops-3 PR, and
the pre-freeze smoke check below ran on the ops-3 build.

### Freeze record

The ops spec's Freeze steps for the one production app, `liturgy-next` (see
Streamlit apps; `liturgy` and `liturgy-stg` were deleted on 2026-09-26, so
there was no second app to delete). Streamlit Community Cloud cannot change an
app's branch, and a deleted app's subdomain may not be free again right away.
So the Freeze first built and checked an app from `streamlit-frozen` on the
temporary subdomain `liturgy-frozen` while `liturgy-next` kept serving; the
plan was then to delete `liturgy-next` in the window and move the checked app
onto that subdomain with the same Secrets. On 2026-09-26, a Saturday evening
(US Eastern), the owner deleted `liturgy-next` and kept production on
`liturgy-frozen` instead (see the note under Streamlit apps). A row whose step
did not happen as planned says what happened instead.

| Step | Result | Date |
|---|---|---|
| Google OAuth client "Liturgy": the four redirect URIs of the deleted `liturgy` and `liturgy-stg` apps removed before the Freeze (a deleted app's subdomain may be claimable by anyone, who would then receive this client's authorization responses); the two `liturgy-next` URIs kept; sign-in on https://liturgy-next.streamlit.app/ checked afterwards. If declined: the accepted risk, and AC 22 is not met | Removed; a fresh sign-in on liturgy-next worked afterwards | 2026-09-26 |
| Pre-freeze smoke check on https://liturgy-next.streamlit.app/ after the ops-3 merge and a reboot: sign in, the church and hymnal load, a saved service loads, Settings opens, and the sidebar has no "Church" selectbox. Noted: Python, subdomain, Sharing, other non-default settings; the pool keys sit at the top of the Secrets | Passed: `liturgy-next` rebooted after the ops-3 merge; sign-in, the church and hymnal, a saved service and Settings worked, and the sidebar had no "Church" selectbox. Noted: Python 3.14.7 (the log: `Using Python 3.14.7 environment at /home/adminuser/venv`; this runbook had said 3.13), subdomain `liturgy-next`, Sharing public, no other non-default setting. The reboot reused the installed environment, so the log had no `name==version` lines and no pre-freeze package list was recorded. The pool keys: at the top of the Secrets, as confirmed earlier that evening (ops-2 gate table) | 2026-09-26 |
| Tester "before" message sent, with the window (about 5 minutes) | Not sent (owner decision). The owner chose a Saturday-evening window instead of the plan's weekday window | 2026-09-26 |
| `streamlit-frozen` created at the ops-3 merge commit (`main` was still at that commit) | `7978a5ebf8efb2db1234d3d4e00c0b04e30457f3` (`7978a5e`, the merge of PR #13; CI's push run for it: success), pushed as the new branch; `main` had not moved | 2026-09-26 |
| `streamlit-frozen` protected: pull request required with 0 approvals, `backend` check required, no bypassing (admins included), no force pushes, no deletion | Classic branch protection rule. Verified: `checks=backend pr=true approvals=0 admins=true force_push=false deletion=false` | 2026-09-26 |
| Pre-flight: temporary app `liturgy-frozen` from `streamlit-frozen` / `app.py`, Python 3.13, Sharing as `liturgy-next`; its two redirect URIs added; build finished; installed versions compared (see Recorded Python and package versions); smoke check passed, including Gmail connect and a test send; custom subdomain editable in Settings (or the reclaim test result) | Created from repo `bbrown62450/church`, branch `streamlit-frozen`, main file `app.py`, Python 3.14 (`liturgy-next` ran 3.14.7, not 3.13; see the pre-freeze row), with the temporary Secrets (`liturgy-next`'s with only the two redirect values changed); Sharing public, the default for a public repository, not separately checked. Its two redirect URIs added to the client "Liturgy". The build finished with no traceback; its log shows Python 3.14. Versions not compared: neither package list was recorded (see Recorded Python and package versions). Smoke check passed: sign-in, the church and hymnal, a saved service, Settings. **Skipped by the owner:** the Gmail connect and test send, and the D5 manual check (which the owner had chosen to run on this app instead of on `liturgy-next`). The custom subdomain was editable in Settings → General, so path A was available and no reclaim test was needed | 2026-09-26 |
| In the window: `liturgy-next` Secrets matched the password-manager copy; `liturgy-next` deleted; the checked app moved to the subdomain `liturgy-next` with those Secrets pasted unchanged (or: recreated there from `streamlit-frozen`) | `liturgy-next` deleted. The checked app was **not** moved: the owner decided to keep production on `liturgy-frozen` permanently instead of renaming it to `liturgy-next`, with its Secrets unchanged (the owner keeps that copy in the password manager). A comparison of `liturgy-next`'s Secrets with the password-manager copy is not recorded. Minutes of downtime not recorded: `liturgy-frozen` kept running, but the address the tester used, https://liturgy-next.streamlit.app/, has had no app since the delete, and the tester was told the new one that evening (the tester row below) | 2026-09-26 |
| Post-freeze smoke check on https://liturgy-next.streamlit.app/ passed, including Gmail connect and a test send; ⋮ → Settings shows branch `streamlit-frozen`, main file `app.py`, Python 3.13 and the noted Sharing | Not done as planned: nothing moved onto `liturgy-next`. Production runs `liturgy-frozen`'s pre-flight build unchanged, whose smoke check passed (pre-flight row, without the Gmail connect and test send); no separate post-freeze check is recorded. The app was created with branch `streamlit-frozen`, main file `app.py`, Python 3.14, and has Sharing public; the last row re-reads its branch setting | 2026-09-26 |
| Temporary subdomain retired: no app holds `liturgy-frozen`, and its two redirect URIs are removed from the Google OAuth client | Not done: `liturgy-frozen` serves production, so it keeps its subdomain and its two redirect URIs. Instead `liturgy-next`'s two (`https://liturgy-next.streamlit.app/oauth2callback` and `https://liturgy-next.streamlit.app/`) were removed from the client "Liturgy": no app holds that subdomain any more, and whoever claimed it would receive the client's authorization responses. The client now lists only the two `liturgy-frozen` URIs among `streamlit.app` addresses | 2026-09-26 |
| `keep-awake` run by hand after records PR A merged (it points `keep-awake` at `liturgy-frozen`): green, one URL (https://liturgy-frozen.streamlit.app/) | https://github.com/bbrown62450/church/actions/runs/36316839015: green; the log shows `visited https://liturgy-frozen.streamlit.app/` | 2026-09-27 |
| Tester told the new address, https://liturgy-frozen.streamlit.app/ (instead of the plan's "after" message, which said the address stayed the same) | Sent by the owner: a message with the new address, asking the tester to update their bookmark and sign in once | 2026-09-26 |
| After the next merge to `main` (records PR A): `liturgy-frozen`'s logs show no code pull (`Pulling code changes from Github`, `Updated app!`) after the merge time, and ⋮ → Settings still shows branch `streamlit-frozen` | PR #14 merged 2026-09-27 11:46 UTC (`3c01e82`); no code pull (`Pulling code changes from Github`, `Updated app!`) in `liturgy-frozen`'s logs after it; ⋮ → Settings still shows `streamlit-frozen`; the app loads | 2026-09-27 |

### Freeze policy

- Only data-safety fixes (data loss, corruption, leakage, security) go into
  `streamlit-frozen`, as pull requests into that branch; CI runs on them. The
  one planned exception is the slice 5b switchover banner. No new features
  (owner decision).
- A fix that also concerns backend code on `main` is fixed on `main`
  separately, with its own tests.
- Streamlit code on `main` is not maintained (F §2.3.7); the FROZEN comment
  at the top of `app.py` on `main` says so.
- A running Streamlit app hot-pulls new commits but can keep stale imported
  modules. After a fix merges into `streamlit-frozen`, reboot the app
  (Manage app → Reboot) and run the smoke check.
- If a Streamlit Cloud reboot breaks the frozen app because a dependency
  released a new version, pin the versions recorded below (none were recorded
  at the Freeze on 2026-09-26; see Recorded Python and package versions) in
  the frozen branch's `requirements.txt`. That counts as a data-safety fix: it
  restores the tester's access to their data.
- Merges to `main` no longer reach the production app, `liturgy-frozen` (no
  code pull in its logs). `keep-awake` (on `main`) still keeps it awake.

### Recorded Python and package versions

What production runs from `streamlit-frozen`: the installed versions from the
build of the app that serves production after the Freeze, `liturgy-frozen`'s
pre-flight build of 2026-09-26 (a later reboot replaces it). Streamlit Cloud
→ the app → Manage app → logs, the dependency-install lines. The app's Python
setting is 3.14. These would be the versions to pin if a later reboot breaks
the app (Freeze policy).

- Python: 3.14 (the `liturgy-frozen` build log, 2026-09-26; the patch version
  was not recorded). Before the Freeze `liturgy-next` ran 3.14.7 (its log after
  the ops-3 reboot: `Using Python 3.14.7 environment at /home/adminuser/venv`),
  not the 3.13 this runbook had said.
- Compared with `liturgy-next`'s last build from `main` before the Freeze: not
  possible, because neither list was recorded (next line).
- Packages: not recorded. The pre-freeze reboot of `liturgy-next` reused its
  installed environment, so its log had no `name==version` lines, and the
  `liturgy-frozen` build's list was not copied from its log (2026-09-26). So
  there is no recorded list to pin if a later reboot breaks the app.

### Contingency

If the production app, `liturgy-frozen`, cannot run from `streamlit-frozen`
(F §6.1 item 6):
1. The production app is redeployed from branch `main` with the same
   subdomain, Secrets and Sharing. Streamlit Cloud cannot change an app's
   branch, so, as the Freeze planned for `liturgy-next`, an app from `main` is
   built and checked on a temporary subdomain first, with its own two redirect
   values in its Secrets and its own two redirect URIs on the Google OAuth
   client "Liturgy". Then the current `liturgy-frozen` app is deleted, the
   checked app is moved onto `liturgy-frozen` with `liturgy-frozen`'s Secrets
   pasted unchanged, and the temporary subdomain's two URIs are removed (see
   Freeze record). It then runs `main` as before the Freeze. Leave
   `streamlit-frozen` in place as a record.
2. Remove the FROZEN comment from `app.py` on `main`.
3. From then on every PR keeps `app.py` working against `main`: no signature
   change to a function `app.py` calls without a compatible wrapper (the
   slice specs name their shims for this case), and
   `streamlit_tests/test_app_smoke.py` (an `AppTest` run of `app.py` signed
   out) stays green. That test renders only the signed-out page; the
   functions called after sign-in are covered only by item 5's smoke check,
   an accepted limit.
4. Streamlit still gets no new features. It keeps the old season wording:
   slice 4's `generate_liturgy` wrapper keeps the old season sentences
   through a frozen copy of the old constant
   (`liturgy_prompts.LEGACY_SYSTEM_PROMPT`), and Streamlit's Settings page
   shows that copy as the "Overall voice" default and compares saves with it
   (`liturgy_prompts.legacy_default_prompts()`), so an admin's edit there
   never stores the new wording as an override. It never reads
   `prayer_library` (F §6.2, amendment 2026-09-26).
5. After every merge to `main`, Reboot the production app (Manage app → Reboot):
   the running app hot-pulls the commit but can keep stale imported modules.
   Then run the smoke check: sign in, the church and hymnal load, a saved
   service loads, Settings opens.
6. Record the decision and the date here.

## Platform limits

- Railway public networking: a request is closed after 5 minutes with no data
  transferred, and can run up to 15 minutes while data keeps flowing
  (https://docs.railway.com/networking/public-networking/specs-and-limits,
  checked 2026-09-25). F §1.8 needs at least 120 s: OK. Never add a test
  endpoint that sleeps.
- Postgres server major: 17
- Postgres `server_version`: 17.6 (2026-09-25)
- The `Postgres server major` line is read by
  `backend/tests/test_ops_workflows.py`, which fails unless it equals
  `PG_MAJOR` in `.github/workflows/backup.yml`. Change both together; the
  backup job also refuses to run when the server major differs.
- Supabase session pooler (Supavisor) Pool Size: 15 (Nano compute; max client
  connections 200), 2026-09-25 (Dashboard → Database → Connection pooling).
- Budget (ops spec, Risks item 2): 2 × (`DB_POOL_SIZE` + `DB_MAX_OVERFLOW`) + 2
  must not exceed the Pool Size; the 2 is the backup job's one session plus
  the owner's SQL editor. The spec's 5 + 5 needs 22 > 15, so the trigger
  fired. The values are `DB_POOL_SIZE=3` and `DB_MAX_OVERFLOW=3`:
  2 × (3 + 3) + 2 = 14 ≤ 15. `backend/.env.example` says the same.
- Since ops-2, `backend/db/engine.py` reads `DB_POOL_SIZE` and
  `DB_MAX_OVERFLOW` whenever it creates a Postgres engine, with code defaults
  3 and 3 (`DEFAULT_POOL_SIZE`, `DEFAULT_MAX_OVERFLOW`), plus `pool_pre_ping`,
  `pool_recycle=1800` and `connect_timeout=10`. The API, `liturgy-frozen` and
  the CLIs that use `db.get_engine()`, `init_db()` or `session_scope()` share
  that engine setup, and so does the API's `GET /health/ready` probe (ops-3),
  which holds at most one of the API's pooled connections at a time. The old
  keep-alive script, which built its own engine, is gone.
  `backend/tests/test_ops_workflows.py`
  fails if the code defaults stop fitting the Pool Size line above or stop
  matching `backend/.env.example`. An invalid value stops the process when
  the engine is created, with `DB_POOL_SIZE must be an integer >= 1 (got '…').`
  or `DB_MAX_OVERFLOW must be an integer >= 0 (got '…').`
- The two apps in the budget are the API (Railway) and `liturgy-frozen`, the
  only Streamlit app since the Freeze on 2026-09-26 (`liturgy-stg` and
  `liturgy` were deleted that day before it, `liturgy-next` in it). Real use
  by one tester is 2–4 sessions.
- Values set: `DB_POOL_SIZE=3` and `DB_MAX_OVERFLOW=3` as Railway service
  variables (API), and as top-level keys `DB_POOL_SIZE = "3"` and
  `DB_MAX_OVERFLOW = "3"` in the production Streamlit Secrets, at the very top
  above the first `[section]` line (a key below `[auth]` belongs to that
  section, and Streamlit does not export it to the environment). Set in
  `liturgy-stg`'s Secrets on 2026-09-26, before that app was deleted the same
  day; present at the top of `liturgy-next`'s that day (ops-2 gate table), and
  carried unchanged into `liturgy-frozen`'s, which differ from them only in the
  two redirect values (Freeze record).
- GitHub Actions artifacts: `db-backup` keeps 30 days (GitHub's maximum is 90).

## Incident response

Only if Step 0, step 1 returned rows. Do it the same day (Supabase Free keeps
logs for a short time). Steps 1–3 come before any repair.

1. **Preserve evidence.** Take an encrypted dump before changing any row; it
   never exists in plaintext. First load the pooler URL into `PG*` variables
   (the `read` and `eval` lines in "Supabase lockdown record"), then:
   ```
   docker run --rm -e PGHOST -e PGPORT -e PGUSER -e PGPASSWORD -e PGDATABASE \
       -e PGSSLMODE=require postgres:17 pg_dump --schema=public --format=custom \
     | age --encrypt -r <your age1… public key> > incident-$(date -u +%Y%m%dT%H%M%SZ).dump.age
   unset PGHOST PGPORT PGUSER PGPASSWORD PGDATABASE
   ```
   Use an image tag at least as new as the server major. Keep the file
   offline next to the key, not in the repo or in GitHub.
2. **Review the API logs.** Dashboard → Logs → API: list the `/rest/v1` and
   `/graphql/v1` requests you didn't make, especially `POST`, `PATCH` and
   `DELETE`, with dates, methods, paths and IPs.
3. **Check for tampering** in every table the default grants let a caller
   write:
   - `users`, every row: compare `email`, `google_sub`, `name` and
     `created_at` with the known users. Identity is matched by email, so a
     changed `users.email` on the owner's row hands the owner's memberships to
     whoever signs in with that address. Look for rows created for people you
     don't know.
   - `memberships` (unexpected rows or roles) and `invites` (unexpected rows,
     especially with the admin or owner role).
   - `contacts`: unexpected recipients (bulletins are emailed to them).
   - `churches`: `name`, `settings` and `deleted_at`.
   - `services`, `hymns`, `hymn_usage`, `hymn_catalog`: rows or edits you
     don't recognize (`services.saved_at` shows recent writes).
   - `gmail_tokens`: recently changed rows.
   - Purge `oauth_states`: `DELETE FROM oauth_states;` (a state is valid for
     10 minutes, so the only cost is restarting a Gmail connect in progress).
4. **Repair** from the forensic dump or the known values: a changed
   `users.email` first, before anyone signs in again; then memberships,
   contacts and settings; then restart the API service on Railway (clears
   the per-process identity cache, which can otherwise map an email to a
   user id for up to 5 minutes).
5. Revoke every active invite in Streamlit Settings → Invites and reissue
   those still needed (invite codes are bearer secrets).
6. Send the tester the Gmail message (ops spec, User experience): remove the
   app's access at https://myaccount.google.com/permissions, then "Connect
   your Gmail" again.
7. Record everything below.

### Incident record

None: the Data API was already off (2026-09-25). REST and GraphQL requests
with the anon key returned HTTP 503 `PGRST002` and no rows, so the owner
recorded no incident and no incident steps were needed.

### Accepted risk: database password shared in a chat session

On 2026-09-25 the Supabase database password (the `postgres.<ref>` pooler user) was pasted into an AI coding-assistant chat while configuring Railway. On 2026-09-26 the owner decided not to rotate it. If it is rotated later, update it in: Supabase (Project Settings → Database → Reset database password; avoid `@ # / ?` to skip URL-encoding), Railway `DATABASE_URL`, the `liturgy-frozen` Streamlit Secrets `DATABASE_URL` (the production app since the Freeze), and the `backup` environment secret `BACKUP_DATABASE_URL`; then run the backup by hand and check `/me` and liturgy-frozen.
