# Slice 1a — Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship PR 1a of slice 1, the platform the onboarding flow (1b) builds on. Alembic takes over the schema (four revisions, a startup revision and RLS check, a readiness gate, Railway's pre-deploy `alembic upgrade head`, and a one-time production stamping runbook). The API error contract gains `fields`/`details`, a 29-code registry, domain errors, idempotency, route-guard and isolation tests and a committed OpenAPI snapshot. The frontend gets its foundations: a typed API client, TanStack Query, the `(signed-in)` and `(church)` layouts with a safe sign-out, the UI kit and a stub `/welcome`. Creating and joining a church ship in 1b.

**Architecture:** Below the API, `domain_errors.py`, `db/ids.py` and `db/schema_check.py` (Alembic config, drift diff, revision state, startup checks) import no FastAPI; `backend/alembic.ini` and `backend/migrations/` (`env.py` prefers an explicit URL attribute over `DATABASE_URL`, runs every revision in one transaction with Postgres lock and statement timeouts) hold revisions `0001_baseline` → `0004_invites_reusable`, and `api/errors.py` maps every `DomainError` and framework error to `{"error": {code, message, request_id, fields?, details?}}`. On the frontend, `lib/api/client.ts` is typed from `schema.d.ts`, generated from the committed `openapi.json`; a TanStack Query layer (`lib/queries/`, `useApi`, `authEvents`) and a module-level signing-out flag in `lib/auth.ts` feed the route groups `(signed-in)` (loads `/me`, owns the 401 sign-out) and `(church)` (resolves and confirms the active church, keyed remount, `no_church_access` fallback). Production is stamped at `0001_baseline` by the owner before the merge (Task 26) and upgraded to head by Railway's pre-deploy command on the merge deploy (Task 27).

**Tech Stack:** Python 3.11 (`.venv`), FastAPI 0.141.1, Pydantic 2.13.5, Starlette 1.7.0, SQLAlchemy 2.1.1, Alembic 1.20 (+ Mako), tzdata, psycopg2, pytest 9 (SQLite locally; a `postgres:17` service in CI); Next 16.3.6, React 19.2.8, TanStack Query v5 (`^5.101`), Vitest 3.2.7 (`unit` and `dom` projects, jsdom, Testing Library), openapi-typescript 7, `@base-ui/react` 1.8.0 with shadcn 4.21.0 (base-nova), sonner; GitHub Actions, Railway, Vercel, Supabase Postgres 17.6.

**Source documents:**
- Slice spec ("S"): `docs/superpowers/specs/2026-09-25-slice-1-onboarding-design.md` (the 1a scope; its file:line refs point at `50fda65` and are re-derived against `7978a5e` here).
- Foundations ("F §n"): `docs/superpowers/specs/2026-09-25-migration-foundations-design.md`.
- Inventory ("inv"): `docs/superpowers/specs/2026-09-25-streamlit-migration-inventory.md`.
- Previous plan and the ops handoffs 1a picks up: `docs/superpowers/plans/2026-09-25-ops-3-api-platform-freeze.md`; production facts in `docs/ops-runbook.md`.
- Facts checked for this plan (tree `7978a5e` unless noted):
  - `fastapi.routing.iter_route_contexts(app.routes)` yields `RouteContext`s; `ctx.dependant` includes router-level `include_router(dependencies=…)`, `ctx.route.dependant` does not (FastAPI 0.141.1).
  - F §1.5 lists 27 codes (29 with owner Q2); `test_migrate_hymn_facts.py` has 4 tests; `/me` churches are `order_by(Church.name)` (`repos/churches.py:51`).
  - `api/__init__.py` is empty and `api/startup.py` imports only `api.settings` and SQLAlchemy, so `migrations/env.py` may import `api.startup.describe_database` (it takes a SQLAlchemy `URL`, `api/startup.py:27`).
  - `api/main.py:5,17` calls `load_dotenv()` at import and `backend/.env` holds a `DATABASE_URL` line, so every pytest process that imports `api.main` has the owner's real `DATABASE_URL`; this drives env.py's URL rule. `backend/tests/` is a package (`from tests.x import …`).
  - No `psql`, `postgres`, `pg_dump` or `docker` on this machine: Postgres runs only in CI. Local Node is 26.4.0 (CI: 22).
  - `origin/main` is `560ebb3` (2026-09-27): the freeze records PRs #14 and #15 on top of `7978a5e` changed only `docs/ops-runbook.md`, `docs/manual-verification.md`, `keep-awake.yml` and URL constants in `test_ops_workflows.py`; the backend baseline stays `559 passed`, and the runbook's owner-marker count is 4.
  - Every task's code was run in a throwaway worktree by its writer, except where its task text says a step first runs in CI (Postgres) or needs the network (npm installs, `shadcn add`, `next build` fonts).

## Global Constraints

- Python: run from the repo root with `.venv/bin/python` (3.11.15); system `python3` is 3.9 with no deps. Every command in the plan uses `.venv/bin/python` / `.venv/bin/alembic` (or `../.venv/bin/…` from `backend/`), never bare `python`/`alembic`. T1 runs `.venv/bin/pip install -r requirements-dev.txt` (adds alembic + Mako, tzdata).
- Shell: cwd resets between commands; frontend commands run in a subshell `(cd frontend && …)`; no foreground `sleep`, no `timeout` binary on macOS; servers via `run_in_background` + Monitor.
- Branch `claude/slice-1-plan` (this worktree), from origin/main `7978a5e`; first commit = the plan (`docs/superpowers/plans/2026-09-26-slice-1a-platform.md`). `origin/main` has since moved to `560ebb3` (freeze records PRs #14 and #15: `docs/ops-runbook.md`, `docs/manual-verification.md`, `.github/workflows/keep-awake.yml` and URL constants in `test_ops_workflows.py`; still `559 passed`); Task 1 merges it right after the plan commit, so every later task works on that tree. Stage files by name (never `-A`/`.`); `.claude/` stays untracked. Merge only after ops-3 Tasks 13–15 (Streamlit Freeze) and the freeze records PRs are merged (met on `560ebb3`: #14 = A, #15 = B; Task 26 re-checks); then merge `origin/main` into the branch, rerun both suites; merge with `gh pr merge --merge`, on the owner's explicit yes, on a weekday when the tester is not using the app.
- Backend baseline `559 passed`. The plan adds **147 test items (142 pass locally, 5 skip)** and deletes 4 → **`697 passed, 5 skipped`** (cumulative after Tasks 1–16: 569, 591, 611, 626, 636, 643, 646, 648+3s, 652+3s, 663+3s, 668+4s, 675+4s, 687+4s, 689+5s, 690+5s, 692+5s; unchanged through Task 23; Task 24: 697+5s) (the 5 skips are `@pytest.mark.postgres` without `TEST_DATABASE_URL`). CI `backend-postgres`: `pytest -m postgres` → `5 passed`. If the baseline differs, stop and ask the owner.
- Frontend baseline: 3 files, `15 passed`; this plan ends at **`122 passed`** (`it.each` rows count individually; recounted from the tests written in Tasks 15–23: 15 → 18 → 34 → 66 → 87 → 89 → 99 → 103 → 107 → 122). Frontend check per task: `(cd frontend && npm test && npm run typecheck && npm run lint)`; T22, T23 and T25 add the build with CI's placeholder env: `(cd frontend && NEXT_PUBLIC_SUPABASE_URL=https://ci-placeholder.supabase.co NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build)` (route-group conflicts and `"use client"` + `metadata` errors only show in `next build`).
- Test commands: `.venv/bin/python -m pytest -q <file> 2>&1 | tail -3`; suite `.venv/bin/python -m pytest -q | tail -1`; `(cd frontend && npx vitest run <file>)`.
- Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; subject style "Area: plain words (F §x, S …)"; TDD (failing test first, quote the failure). PR body ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)` and "Tests: backend +142 (+5 Postgres-only), −4 (697 passed, 5 skipped); frontend 15 → 122".
- **Postgres is CI-only.** Nothing on this machine runs Postgres, so the five `@pytest.mark.postgres` tests, 0003's DO block, the RLS query and the CI alembic cycle skip locally. T8, T11 and T14 expect `skipped` locally plus their SQLite/offline-SQL assertions; for them "failing test first" means the offline/SQLite parts, and the Postgres parts first run at T14's draft-PR checkpoint (owner Q5). If CI Postgres fails there or at T25: fix in the owning task's files, re-review that task, push again.
- **Test databases are local only.** `backend/tests/pg_helpers.py::require_local_test_url(url)` accepts only a `postgres*` scheme on `localhost`/`127.0.0.1`/`::1` (same rule as `pg_smoke.py:30-34`); `pg_db` and T8's sandbox helper call it before connecting; the autouse `_no_network` fixture is the second guard. Every in-process Alembic call passes its URL explicitly (`alembic_config(url=…, configure_logger=False)`); nothing in tests relies on `DATABASE_URL` (see the `load_dotenv` note in the header).
- Pins/versions: `fastapi==0.141.*` (0.141.1), `pydantic==2.13.*` (2.13.5), `alembic>=1.20` (the line T1 installs; 1.13 predates SQLAlchemy 2.1 — if T1 resolves another version, use its `major.minor` as the floor and record it), `tzdata>=2026.4` (S Risk 7 "pinned to a recent release"); starlette 1.7.0, SQLAlchemy 2.1.1 (no new pin). Frontend: Vitest pinned `^3.2.7` (never 4/5), `@tanstack/react-query` v5 (`^5.101`), next 16.3.6, react 19.2.8, `@base-ui/react` 1.8.0, shadcn 4.21.0 (base-nova), Node 22 in CI. `@vitejs/plugin-react` `^5` (6.x targets Vite 8; Vitest 3.2.7 runs Vite 7.3.6 — confirm peers at install, UNVERIFIED), jsdom `^26` (conservative for Vitest 3; 29 needs Node ≥22.13).
- Postgres: `PG_MAJOR: "17"` (`backup.yml:26`); CI `image: postgres:17`; production `server_version` 17.6.
- CI `backend-postgres` (T14), env `DATABASE_URL` = `TEST_DATABASE_URL` = `postgresql://postgres:ci-throwaway@localhost:5432/postgres`; steps in order: `alembic upgrade head` → `alembic check` → `alembic downgrade base` → `alembic upgrade head` (each in `backend/`) → `python backend/tests/pg_smoke.py` → `python -m pytest -m postgres -q` (clarification 2: the smoke runs before the Postgres tests).
- Revisions (names fixed, files `NNNN_short_slug.py`): `0001_baseline`, `0002_reconcile`, `0003_lockdown`, `0004_invites_reusable`; head = `0004_invites_reusable`.
- `alembic.ini`: `script_location = %(here)s/migrations`, `prepend_sys_path = %(here)s`, plus the standard `[loggers]`/`[handlers]`/`[formatters]` sections (root WARN, `sqlalchemy` WARN, `alembic` INFO, console handler on stderr) so `fileConfig` never raises KeyError. Code builds `Config` only via `db.schema_check.alembic_config(*, url: str | None = None, configure_logger: bool = True)` from `Path(__file__).resolve().parents[1] / "alembic.ini"`; `url` → `cfg.attributes["url"]`, `configure_logger` → `cfg.attributes["configure_logger"]`.
- `env.py` (critique 1–4, 21):
  - Logging: `if config.config_file_name and config.attributes.get("configure_logger", True): fileConfig(config.config_file_name, disable_existing_loggers=False)`. In-process callers pass `configure_logger=False`, so caplog tests (`test_startup.py:53-58`, `:113-116`; `test_api_app`, `test_health_ready`, `test_middleware`) keep their loggers whatever the test order.
  - URL: `config.attributes["url"]` when set (tests, `pg_db`, T8 helpers), else `db.engine._database_url()` (CLI, Railway pre-deploy); always through `db.engine._normalize_url`. No `load_dotenv`.
  - `print(f"Database: {describe_database(make_url(url))}", file=sys.stderr)` — never stdout, so `--sql > upgrade.sql` stays pure SQL.
  - `target_metadata = db.models.Base.metadata`; `render_as_batch=True` on SQLite (autogenerate rendering only; hand-written ALTERs use `op.batch_alter_table`, T9); `compare_type=True`; `compare_server_default=False`; `include_object` from `db.schema_check`. No `MetaData(naming_convention=…)` (production has unnamed `users_email_key`, `users_google_sub_key`, `invites_code_key`, `*_fkey`, `*_pkey`).
  - Offline: `context.configure(url=url, literal_binds=True, dialect_opts={"paramstyle": "named"}, …)` (named paramstyle keeps 0003's `%` single).
  - Online: `create_engine(url, poolclass=NullPool)`; `with engine.connect() as connection: context.configure(connection=connection, …)`; `with context.begin_transaction():` on Postgres first `context.execute("SET LOCAL lock_timeout = '5s'")` and `context.execute("SET LOCAL statement_timeout = '60s'")`, then `context.run_migrations()`. **Never `connection.execute(...)` before `configure`**: SQLAlchemy 2.1 autobegins, Alembic then treats it as an external transaction, `begin_transaction()` is a no-op and closing the connection rolls back every migration while the command exits 0. Default single transaction (no `transaction_per_migration=True`), so a 0003 RAISE rolls back 0002–0004. Offline the same code emits `BEGIN;`, the two `SET` lines, the revisions, `COMMIT;`.
- `backend/scripts/*.py` insert `Path(__file__).resolve().parents[1]` into `sys.path` before importing `db`/`api` (run as `python scripts/x.py` from `backend/` or `python backend/scripts/x.py` from the root, `sys.path[0]` is `backend/scripts`); each has a subprocess test.
- `backend/railway.toml`: `[deploy]` `preDeployCommand = ["alembic upgrade head"]`, `healthcheckPath = "/health/ready"`; start command stays in `backend/Procfile`. Config-as-code path `/backend/railway.toml` (set by hand, T26).
- 0003 messages verbatim: `'0003_lockdown: role % has no BYPASSRLS and does not own: %. Enabling RLS would hide their rows from the app. See migrations/README.md "RLS precondition".'`; `'0003_lockdown: cannot enable RLS on % (owned by %, migrating as %). Only the owner of a table can enable RLS on it. See migrations/README.md "RLS precondition".'`. The DO block text is a module constant `LOCKDOWN_SQL` (T8's idempotence test re-runs it).
- 0004: `invites.reusable BOOLEAN NOT NULL DEFAULT false`; `invites.accepted_by UUID NULL` FK `fk_invites_accepted_by_users` → `users(id) ON DELETE SET NULL`; `UPDATE invites SET reusable = true WHERE email IS NULL` via `sa.table`. Upgrade and downgrade use `with op.batch_alter_table("invites") as b:` (plain ALTERs on Postgres, renders offline; SQLite needs batch for the FK). Model: `Column(Boolean, nullable=False, default=False, server_default=sa.false())`.
- Drift output (`schema_check.format_diff`): one line per entry, sorted: `add_table <t>`, `remove_table <t>`, `add_column <t>.<c>`, `remove_column <t>.<c>`, `add_index <name>`, `remove_index <name>`, `add_constraint <name>`, `remove_constraint <name>`, `add_fk <name>`, `remove_fk <name>`, `modify_nullable <t>.<c> <old> -> <new>`, `modify_type <t>.<c> <old> -> <new>`, `modify_default <t>.<c>`; nested `modify_*` lists flattened; unknown kinds `repr`. `schema_drift.py` prints `revision: <current> head: <head> state: <state>` then those lines; at production's expected state exactly `add_column invites.accepted_by`, `add_column invites.reusable`, `add_fk fk_invites_accepted_by_users` (+ `add_index ix_hymns_church_hymnal` only if missing). The README quotes the same strings.
- Startup log: WARNING `schema revision X != head Y` (fresh DB: `schema revision None != head 0004_invites_reusable`); in production `behind` at ERROR; check failures ERROR + state `unknown`; never blocks startup; RLS WARNING names every `public` table with `rowsecurity = false` (plan text: `Row-level security is off on: <t1>, <t2>`).
- Gate: `APP_ENV=production` + `behind` → 503 `db_unavailable` "The database schema is behind this release." `details: {"reason": "schema_behind", "current": X, "head": Y}`; `ahead`/`unknown`/unset → 200; outside production nothing changes; checked before `database_ready()`; route stays sync, no `try`, no sqlalchemy import (`test_health_ready.py:75,79-84`).
- Error body: `{"error": {"code", "message", "request_id", "fields"?, "details"?}}`; `fields`/`details` omitted when absent (`test_middleware.py` asserts the exact 500 body).
- `ERROR_CODES` (27 from F§1.5, **29** with owner Q2): 400 `invite_rejected`, `gmail_state_invalid`, `gmail_connect_failed`; 401 `unauthenticated`; 403 `forbidden`; 404 `not_found`; 409 `conflict`, `last_admin`, `owner_must_transfer`, `invite_exists`, `gmail_not_connected`; 422 `invalid_request`, `prompt_invalid`, `idempotency_mismatch`, `invalid_rubric`; 429 `rate_limited`; 500 `internal_error`; 502 `upstream_error`, `ai_upstream_error`, `gmail_send_failed`; 503 `auth_unavailable`, `ai_not_configured`, `ai_busy`, `gmail_not_configured`, `db_unavailable`; 504 `upstream_timeout`, `ai_timeout`. Plus, per owner Q2, `bad_request` 400 and `method_not_allowed` 405 = 29, with an F§1.5 amendment row in the same PR (Task 2); any other framework status maps to `bad_request` (4xx) or `internal_error` (5xx), so the fallback code `"error"` is gone (Task 3). Client-only: `network_error`, `timeout`, `aborted`, `unknown` (clarification 9).
- 422: `invalid_request` "The request was not valid."; `fields` = location minus leading `body`/`query`/`header`/`path`, joined by `.`; "Required." (`missing`), "Too long (max N characters)." (`string_too_long`, N = `ctx.max_length`), "Not a valid value." (anything else incl. `extra_forbidden`).
- Other exact server copy: 403 `forbidden` "You don't have access to this church." + `details: {"reason": "no_church_access"}` (also for a missing or malformed `X-Church-Id`); `require_admin` "Only church admins can do this." (no `details`); 503 `db_unavailable` "The database is not reachable."; 500 `internal_error` "Something went wrong."; 401 "Please sign in."; 503 `auth_unavailable` "Sign-in is temporarily unavailable. Try again shortly.".
- Idempotency: header `Idempotency-Key` (UUID); replay header `Idempotent-Replayed: true`; 422 `invalid_request` "Idempotency-Key must be a UUID."; required-and-absent 422 "Missing Idempotency-Key header."; 422 `idempotency_mismatch` "This request was already sent with different details."; key `(user_id, method, route template, key)`; TTL 15 min; lazy expiry; bounded to 10 000 entries; per-key `threading.Lock` (so `run_idempotent` is called only from sync `def` routes — it blocks); body hash SHA-256 of `payload.model_dump(mode="json")` JSON with `sort_keys=True`; stores 2xx + DomainError 4xx except `RateLimited`; never 5xx; non-DomainError → drop entry, re-raise.
- `RateLimited(message, *, retry_after_seconds)` → 429 `rate_limited`, `details.retry_after_seconds = n`, header `Retry-After: n`; the only 429 mechanism; no `ApiError` 429, no `ApiError.headers`.
- Headers: `X-Request-Id`, `X-Church-Id`, `If-Match`, `Retry-After`; CORS already allows/exposes these (`main.py:48-50`), unchanged.
- Frontend copy: timeout `ApiError(0, "timeout", "This is taking too long. Try again.")`; network `ApiError(0, "network_error", "Can't reach the server. Check your connection and try again.")` (unchanged); signing out `ApiError(0, "aborted", "Signing out.")`; a caller's own abort `ApiError(0, "aborted", "The request was cancelled.")` (Task 16, clarification 29); `ErrorState` "Can't reach the server." / "Something went wrong. (Ref: {first 8 chars of requestId})"; toast "You no longer have access to {name}."; `PendingButton` "Saving…"; stub `/welcome` card "No church yet" / "Creating or joining a church is coming in the next update.".
- Frontend constants: `timeoutMs` default 20 000; `POST /churches` 30 000 (`timeouts.ts`); storage keys `wsb:pendingInviteCode`, `wsb:postLoginPath` (sessionStorage), `activeChurchId` (localStorage, unchanged); QueryClient `staleTime: 30_000`, `gcTime: 5 * 60_000`, `refetchOnWindowFocus: true`, `retry: (n, e) => n < 1 && isRetryable(e)` (network_error/timeout/5xx only), mutations `retry: false`; button `size: { touch: "h-11 px-4" }`; every sign-out `supabase.auth.signOut({ scope: "local" })`.
- Sign-out (critique 8): a module-level signing-out flag in `lib/auth.ts` is set first by `useSignOut`. While set: `getAccessToken()` rejects with the `aborted` error; `handleAuthErrors` does nothing (one sign-out in flight); the `(signed-in)` layout renders the shell skeleton (unmounting the `(church)` subtree and its `ChurchProvider`) and passes `enabled: false` to `useMe`; `(church)` layout step 3 never stores. The flag is cleared only by a full page load (every sign-in returns through the Google OAuth redirect) or `resetSigningOutForTests()`.
- Layering: nothing under `backend/` imports `streamlit`; `domain_errors.py`, `db/*`, `usecases/*` import no `fastapi`/`starlette`; `db/` never imports `api/` (`migrations/env.py` is not `db/` and may import `api.startup`). `/health/ready` keeps its recorded F§2.2 exception (ApiError via `db_unavailable`). `PATCH /rubric`'s `ApiError(422, "invalid_rubric", …)` stays (6a converts it).
- Log hygiene: never log request bodies, tokens, invite codes, OAuth code/state, email bodies, AI prompts/outputs, or a query string (F§2.5).
- Next 16: read `frontend/node_modules/next/dist/docs/` guide before layout/route code (frontend/AGENTS.md); `"use client"` layouts export no `metadata`; do not use generated `LayoutProps`/`PageProps` helpers (CI runs `tsc` before `next build`).
- Base UI rules (F§4.9): generated components only (`npx shadcn@latest add …`, never `--overwrite`), hand edits limited to variants; no `asChild` (use `render`, `nativeButton={false}` for links); `DropdownMenuLabel` inside `DropdownMenuGroup`; radio choices via `DropdownMenuRadioGroup`; toasts stay on sonner.
- Secrets/outward actions: the agent never sees or types a secret (DATABASE_URL, keys, `.env`); pushing, opening/merging PRs, repo settings, branch protection, workflow dispatches, Railway/Supabase changes need the owner's explicit yes; owner reports secrets only as "present"/"missing".
- Owner laptop commands (T24 README, T26, T27): from `backend/` of a checkout of the 1a branch (this worktree has its own `.venv`): `../.venv/bin/pip install -r ../requirements-dev.txt`; owner exports `DATABASE_URL` in that shell; `../.venv/bin/alembic current|stamp|upgrade|check …`; `../.venv/bin/python scripts/schema_drift.py`; `unset DATABASE_URL` when done. No `psql`/`pg_dump` on the laptop: step 0 reruns go through the Supabase SQL editor; step 1's backup is a `backup.yml` run (`workflow_dispatch`, `backup.yml:14`).
- Owner-marker check: `grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l` = 20 at `7978a5e` and **4 at `560ebb3`** (the freeze records PRs filled the Freeze rows); 1a adds no `[owner` marker to the runbook, so every check compares with `origin/main`'s count (records go in T27's records PR).
- Unchanged and green: `test_ops_workflows.py` (except the stale comment at `:397`), `test_middleware.py`, `test_docs.py`, all repo tests, `streamlit_tests/`. Changing: `test_startup.py` (fixture `init_db_calls` → `schema_check_calls`, same test count), `test_ci_workflow.py` (one test replaced, three added), `test_foundation_setup.py` (gains 6: T1 2, T5 1, T7 2, T12 1), `test_identity.py` (gains 1, Postgres), `test_api_app.py`, `test_health_ready.py`, `test_models.py`, `test_no_streamlit_in_core.py` (gain tests); `test_migrate_hymn_facts.py` deleted. The 1a docs tests go in a new `test_slice1_docs.py`.
- **Not in 1a:** everything in the 1b list in §1; slice 2 `api/ratelimit.py`, `church_create` bucket, `backend/cache.py`, nav items, `/`→`/builder`; `require_owner` (6b); `apiFetchBlob` (5a); `store_error` hook (5b); Streamlit files (`app.py`, `ui_helpers.py`, `streamlit_tenancy.py`) untouched.
- **Production Streamlit (owner Q1):** https://liturgy-frozen.streamlit.app/ (branch `streamlit-frozen`, `app.py`, Python 3.14), on the shared database. Merges to `main` no longer reach it, so 1a's merge needs no Streamlit reboot; T27's smoke check runs on it. `liturgy-next` was deleted; the plan names it only as history (and in tests that assert its absence).
- **Owner answers Q2–Q5 as constraints:** 29 error codes and the F §1.5 amendment in the same PR (T2, T3); `npx shadcn@latest add combobox` in 1a, `TimezoneCombobox` and `lib/timezones.ts` in 1b, a hand-written `src/components/ui/combobox.tsx` over `@base-ui/react/combobox` only if the registry has no `combobox` (T20, recorded exception to F §4.9.1); at runbook step 7 the owner sets both Railway's Config-as-code path `/backend/railway.toml` and the UI Healthcheck Path `/health/ready` and records both (T24, T26); right after T14 the agent pushes and opens a **draft** PR titled "Draft: …" without asking again, and marks it ready only on the owner's yes (T14, T25).
- **Local Node is 26.4.0, CI's is 22.** Node ≥ 25 defines its own `localStorage`/`sessionStorage` globals that hide jsdom's under Vitest 3.2.7, so T15's `vitest.config.ts` runs the test forks with `poolOptions: { forks: { execArgv: ["--no-experimental-webstorage"] } }` at the root of `test` (Node 22 accepts the flag; the feature is already off there).
- **One DOM `afterEach`.** `src/test/setup-dom.ts` has a single `afterEach`: `cleanup()`, both storage clears, then T17's `resetStoredChurchIdForTests()` and T18's `resetSigningOutForTests()`. Vitest 3 runs `afterEach` hooks in reverse registration order, so a separate hook added below it would run before `cleanup()`.

## Owner decisions (2026-09-26)

Binding for this plan (outline §6).

- **Q1 Freeze timing: resolved by events.** The Streamlit Freeze was done on 2026-09-26. `streamlit-frozen` was cut from the ops-3 merge `7978a5e` and is branch-protected. The owner deleted `liturgy-next` and kept production on the pre-flight app https://liturgy-frozen.streamlit.app/ (branch `streamlit-frozen`, `app.py`, Python 3.14, Sharing public); no app holds `liturgy-next` and its Google redirect URIs are removed. Every reference to production Streamlit is liturgy-frozen. The freeze records PRs (A, B) must be on `main` before 1a merges (they are: #14 and #15, `560ebb3`); Task 26 checks the Freeze record in `origin/main:docs/ops-runbook.md` and that `keep-awake.yml` points at liturgy-frozen. Merges to `main` no longer reach Streamlit, so 1a needs no Streamlit reboot, and Task 27's smoke check (frozen code, shared database) proves the new columns and RLS do not break it.
- **Q2 Error codes: accepted.** `ERROR_CODES` gains `bad_request: 400` and `method_not_allowed: 405` (29 codes), with an F §1.5 amendment row in the same PR (Task 2); any other Starlette HTTP status maps to `bad_request` (4xx) or `internal_error` (5xx), so the fallback code `"error"` disappears (Task 3).
- **Q3 Combobox: accepted.** 1a runs `npx shadcn@latest add combobox` (Task 20); `TimezoneCombobox` and `lib/timezones.ts` are 1b. Only if the base-nova registry has no `combobox` is a hand-written thin wrapper over `@base-ui/react/combobox` in `src/components/ui/combobox.tsx` allowed, as a recorded exception to F §4.9.1.
- **Q4 Railway UI health check: accepted.** Runbook step 7 (Task 26) also sets Railway → Settings → Deploy → Healthcheck Path to `/health/ready` in the UI and records both the config-file path and the UI value.
- **Q5 Early draft PR: accepted.** Right after Task 14 the agent may push the branch and open a **draft** PR (title prefixed "Draft:") without asking again, so `backend-postgres` runs 0003, the RLS check and the Postgres tests early; the draft becomes the real PR at Task 25, and marking it ready for review still needs the owner's yes.
- **1b, for context only:** invite links will show a preview card and a **Join** tap (behavior change 4 approved); F §4.3 records it as an amendment to decision 6 in the 1b plan.

## Spec clarifications

1. File:line refs re-derived against `7978a5e` (invite checks `repos/invites.py:75-96`; `require_church` `deps.py:103-110`; README section `:142-191`; lifespan `main.py:23-33`; ops CI-major test `test_ops_workflows.py:396-400` (at `560ebb3`; `:394-398` at `7978a5e`)). Task 1 merges `origin/main` `560ebb3` (freeze records #14 and #15); of the refs a task edits by line number only `docs/ops-runbook.md:315-316` (now `:317-318`), the dated records `:148`/`:163` (now `:149`/`:164`) and `docs/manual-verification.md`'s last line (66 → 67) move, and Task 24 uses the `560ebb3` numbers.
2. `backend-postgres` already exists (ops-2): 1a extends it; env gains `TEST_DATABASE_URL` (same throwaway URL as `DATABASE_URL`); `pg_smoke.py` runs after the alembic cycle (so its `init_db()` is a no-op on existing tables) and **before** `python -m pytest -m postgres -q`, not last: it expects exactly 2 users (`pg_smoke.py:70`) and `pg_db` truncates only before each test, so a row left by the last Postgres test would fail it (Task 14).
3. `test_ci_workflow.py::test_ci_runs_the_postgres_smoke_on_a_throwaway_postgres_17` is replaced: S says only ops' `test_ops_workflows.py` checks the major. A new shape-only test (`^postgres:\d+$`) keeps that ops check from passing vacuously on an empty service list.
4. Removing `init_db` breaks `test_startup.py:28-33` (`init_db_calls`) and tests `:61,:69,:95`; they spy on `api.main.run_startup_checks` instead, keeping "guards run before anything touches the database". `:95` (localhost:1 Postgres engine) needs the spy so the revision check does not log an ERROR.
5. Guard walker uses `iter_route_contexts(app.routes)` and `ctx.dependant` (FastAPI 0.141 nests `_IncludedRouter`s; `ctx.route.dependant` misses router-level deps — verified). The `fastapi==0.141.*` pin makes this stable.
6. S "`GET /church` stays the only church-scoped route" is stale: `GET /rubric`, `PATCH /rubric` (PR #4) also get `assert_church_isolated` (F§1.2 rule 5).
7. `ERROR_CODES` includes `invalid_rubric` (F§1.5 amendment) though S names only `db_unavailable`. `test_error_registry.py` supersedes `test_foundation_setup.py::test_frontend_error_union_lists_db_unavailable_once_it_exists`, which stays (it passes).
8. 422 whole-body errors (loc `('body',)`, e.g. `test_api_rubric.py:72`): the empty key is dropped; `fields` omitted when empty. `path` is stripped too (F§1.1 malformed path ids).
9. Client: non-JSON/code-less error bodies → `internal_error` for status ≥ 500, else client code `unknown`; 204/empty 2xx → `undefined` (slice-0 carry-over). Replaces the old `"error"` fallback.
10. `run_idempotent` gains `method: str = "POST"` (F key includes method); `store_error` is 5b's additive keyword; sync routes only (per-key `threading.Lock`).
11. `alembic.ini` uses S's `%(here)s` form (F§3.1 text stale); runbook uses `schema_drift.py` before head, `alembic check` only at head (F§3.2 stale).
12. `TimezoneCombobox`, `timezones.ts` and `timezone-combobox.test.tsx` ship in 1b (S's 1a scope bullet and file map don't list them; its only consumer is 1b's create form); 1a only generates `combobox` (owner Q3).
13. `useStoredChurchId` store tests live in `src/lib/church-store.test.tsx` (dom project, `renderHook`, plus `renderToString` for the server snapshot, which `renderHook` never calls), not node `church.test.ts`.
14. `MeProvider`/`useMeContext` live in new `src/lib/me-context.tsx` (S names the context, not the file).
15. `vi.mock("next/navigation")` and `vi.mock("@/lib/supabase/client")` live in `src/test/setup-dom.ts` (setupFiles), exposing spies from `src/test/mocks.ts`, so real `lib/auth.ts` runs under test and `signOut({scope:"local"})` is asserted (verified in Tasks 15 and 18's trials: a setup file's `vi.mock` applies to modules the test files import, and the setup file and test files share one module instance). Node-project tests (`auth.test.ts`) declare their own `vi.mock`.
16. 1a's 401 path already calls `useSignOut({ keepPendingInvite: true, next: pathname })`; `/login` ignores `next` until 1b (AC14's return-to-path half is verified in 1b).
17. `lib/latest.ts` stays (F§4.11 lists it) although `app/page.tsx` is deleted.
18. `types.ts` in 1a exports `Church`, `Me` (+ `ErrorBody`); `InvitePreview`/`InviteAccepted` arrive with 1b's schemas.
19. Runbook step 7 also sets Railway's UI Healthcheck Path to `/health/ready` (owner Q4), and only `docs/ops-runbook.md:23-24, :317-318` (`:315-316` at `7978a5e`) are edited in place (dated records stay).
20. Manual-verification "## Slice 1" gets the 1a item (S item 1) now; 1b appends items 2–11.
21. `compare_type=True` on SQLite may report Uuid/JSON/DateTime(tz) false positives (UNVERIFIED); T5's `test_schema_diff_is_empty_for_a_create_all_database` is the detector; if it shows any, `schema_check` gets a type comparator that ignores dialect-equivalent types, recorded in T5. Task 5's trial saw none on Alembic 1.20.0 / SQLAlchemy 2.1.1.
22. Pins: S says `alembic>=1.13` and bare `tzdata`; the plan uses `alembic>=1.20` (tested line; 1.13 predates SQLAlchemy 2.1) and `tzdata>=2026.4` (S Risk 7).
23. env.py prefers `config.attributes["url"]` over `DATABASE_URL`, because `api.main`'s import-time `load_dotenv()` puts `backend/.env`'s real URL into every pytest process that imports the app.
24. env.py writes its `Database:` line to stderr, so `upgrade.sql` is pure SQL; the expected `upgrade.sql` also contains `BEGIN;`, the two `SET … timeout` lines and `COMMIT;`.
25. `schema_drift.py` refuses to run without an exported `DATABASE_URL` (exit 2, "DATABASE_URL is not set.") instead of falling back to local SQLite, prints `Database: …` to stderr, and prints drift lines sorted (S lists them without a meaningful order).
26. A missing or malformed `X-Church-Id` also returns 403 `no_church_access` (deps.py:107-109 treats it as no membership); intended and tested.
27. The sign-out flag (Global Constraints) is a design addition S does not name; it is what makes AC14's "clears … the stored church" hold while observers are still mounted. Slice 2 (first pushed in-app navigation) must either leave sign-out with `window.location.replace('/login')` or reset the flag when `/login` mounts; 1a has no push navigation, so Back always reloads.
28. `test_ops_workflows.py`'s stale comment is at `:397-398` after Task 1's merge of `560ebb3` (`:395-396` at `7978a5e`).
29. *(assembly)* A caller's own abort is `ApiError(0, "aborted", "The request was cancelled.")` (S gives no text); `timeoutMs` defaults to `timeoutFor(method, path)`, so 1b's `POST /churches` gets 30 s without passing it (Task 16).
30. *(assembly)* `pg_db` runs `alembic upgrade head` on every call (a no-op at head, and it also lifts a local Postgres left behind head), not only when `alembic_version` is absent (Task 6).
31. *(assembly)* `0003`'s `REVOKE`/`ALTER DEFAULT PRIVILEGES` statements sit inside its `DO` block, guarded on both `anon` and `authenticated` existing (the statements name both); the second refusal message completes S's "…" as `… (owned by %, migrating as %). Only the owner of a table can enable RLS on it. See migrations/README.md "RLS precondition".` (Task 8).
32. *(assembly)* Autogenerate on Alembic 1.20 / SQLite does detect a lost `ondelete`, but never a lost CHECK constraint; `test_baseline_keeps_on_delete_rules_and_check_constraints` (run at head) is what guards `ck_memberships_role` (Task 6).
33. *(assembly)* The outline's file list omitted `backend/usecases/__init__.py` (Task 2); with it and the F §1.5 amendment (Q2 = yes) the 1a diff has 133 paths plus T20's registry-dependency files.
34. *(assembly)* `/health/ready` declares no `responses=error_responses(503)` and `/health` has no `response_model` (F §1.3), so the OpenAPI snapshot documents `ErrorBody` only on `/me`, `/church` and `/rubric` (Task 13). Adding them later changes the snapshot on purpose.
35. *(owner decision 2026-09-27; deviation from F §3.1's text)* env.py sets the migration timeouts with `SET LOCAL lock_timeout = '5s'` and `SET LOCAL statement_timeout = '60s'`, not plain `SET`. F §3.1 only asks that "a migration never hangs"; a plain `SET` would outlive the migration transaction on the Supabase session pooler's shared server connection, which the API and the frozen Streamlit app reuse, so a later app connection could inherit the 5 s `lock_timeout`. `SET LOCAL` lasts until the migration transaction ends. It requires a transaction: every revision runs inside env.py's single transaction, so it always applies; a future revision that must run outside a transaction (e.g. `CREATE INDEX CONCURRENTLY` in an `autocommit_block`) would run without these limits and should set its own.

## File Structure

Sorted list of every path the 1a PR touches (`git diff --name-only --no-renames origin/main...HEAD`): **133 paths**: the outline's 131, plus the F §1.5 amendment (Q2 = yes), plus `backend/usecases/__init__.py`; and on top the registry-dependency files `shadcn add` creates in T20 (expected `frontend/src/components/ui/input-group.tsx` and `textarea.tsx`; T20's commit message records the real list on its `Generated:` line and T25 checks it). A = added, M = modified, D = deleted.

```
.github/workflows/ci.yml                                     M  backend-postgres: TEST_DATABASE_URL + alembic cycle + pytest -m postgres (T14); frontend gen:api diff (T15)
README.md                                                    M  hymn-facts step 1 (T7); ## Database local-dev Alembic notes (T24)
backend/alembic.ini                                          A  T5
backend/api/deps.py                                          M  require_church → forbidden(details={"reason": "no_church_access"}) (T3)
backend/api/errors.py                                        M  ApiError(details), forbidden(details), _body, DomainError handler, domain_error_response, 422 mapping, ErrorDetail/ErrorBody, error_responses (T3); db_unavailable(message, details) (T12)
backend/api/idempotency.py                                   A  T4
backend/api/main.py                                          M  - init_db; + run_startup_checks → app.state.schema_state (T11)
backend/api/routes/health.py                                 M  gate before database_ready() (T12)
backend/api/routes/me.py                                     M  responses=error_responses(...) (T3)
backend/api/routes/rubric.py                                 M  responses=error_responses(...) (T3)
backend/api/schemas.py                                       M  ChurchOut.role Literal, Page[T], ItemList[T], ErrorBody re-export (T3)
backend/backfill_hymn_facts.py                               M  :5 docstring → "Run after `alembic upgrade head`" (T7)
backend/db/ids.py                                            A  as_uuid (T2)
backend/db/models.py                                         M  Invite.reusable/accepted_by; docstring server-default rule (T9)
backend/db/schema_check.py                                   A  alembic_config, include_object, schema_diff (T5); RevisionState, revision_state, format_diff (T10); rls_disabled_tables, run_startup_checks (T11)
backend/domain_errors.py                                     A  T2
backend/migrate_add_hymn_facts.py                            D  T7
backend/migrate_add_hymnal.py                                D  T7
backend/migrations/README.md                                 A  production runbook steps 0–10, RLS precondition, PG major 17, local dev (T24)
backend/migrations/env.py                                    A  T5
backend/migrations/script.py.mako                            A  T5
backend/migrations/versions/0001_baseline.py                 A  T6
backend/migrations/versions/0002_reconcile.py                A  T7
backend/migrations/versions/0003_lockdown.py                 A  T8
backend/migrations/versions/0004_invites_reusable.py         A  T9
backend/railway.toml                                         A  T12
backend/requirements.txt                                     M  T1
backend/scripts/export_openapi.py                            A  T13
backend/scripts/schema_drift.py                              A  T10
backend/tests/api_helpers.py                                 A  T13
backend/tests/conftest.py                                    M  _no_network, pg_db (T1); pg_db upgrade wiring (T6)
backend/tests/pg_helpers.py                                  A  require_local_test_url (T1); throwaway_database (T8)
backend/tests/test_api_app.py                                M  T3, T11
backend/tests/test_ci_workflow.py                            M  T14, T15
backend/tests/test_domain_errors.py                          A  T2, T3
backend/tests/test_error_registry.py                         A  T16
backend/tests/test_foundation_setup.py                       M  T1, T5, T7, T12
backend/tests/test_health_ready.py                           M  T12
backend/tests/test_idempotency.py                            A  T4
backend/tests/test_identity.py                               M  T14
backend/tests/test_ids.py                                    A  T2
backend/tests/test_isolation.py                              A  T13
backend/tests/test_migrate_hymn_facts.py                     D  T7 (4 tests)
backend/tests/test_migrations.py                             A  T5–T9
backend/tests/test_models.py                                 M  T9
backend/tests/test_no_network.py                             A  T1
backend/tests/test_no_streamlit_in_core.py                   M  T2, T13
backend/tests/test_openapi_contract.py                       A  T13
backend/tests/test_ops_workflows.py                          M  stale comment :397 only (T14)
backend/tests/test_pg_helpers.py                             A  T1
backend/tests/test_route_guards.py                           A  T13
backend/tests/test_schema_check.py                           A  T5, T10
backend/tests/test_slice1_docs.py                            A  T24
backend/tests/test_startup.py                                M  T11
backend/usecases/__init__.py                                 A  T2
docs/manual-verification.md                                  M  + "## Slice 1" (1a item) after "## Ops slice" (T24)
docs/ops-runbook.md                                          M  :23-24 and :317-318 in place (T24); records in T27's separate PR
docs/superpowers/plans/2026-09-26-slice-1a-platform.md       A  the plan (first commit)
docs/superpowers/specs/2026-09-25-migration-foundations-design.md  M  F§1.5 amendment rows: bad_request, method_not_allowed (T2; owner Q2)
frontend/eslint.config.mjs                                   M  react/no-danger; globalIgnores schema.d.ts (T15)
frontend/package-lock.json                                   M  T15
frontend/package.json                                        M  deps; "gen:api" (T15)
frontend/src/app/(signed-in)/(church)/church-layout.test.tsx A  T23
frontend/src/app/(signed-in)/(church)/layout.tsx             A  T23
frontend/src/app/(signed-in)/(church)/page.tsx               A  T23
frontend/src/app/(signed-in)/layout.tsx                      A  T22
frontend/src/app/(signed-in)/signed-in-layout.test.tsx       A  T22
frontend/src/app/(signed-in)/welcome/page.tsx                A  T22
frontend/src/app/(signed-in)/welcome/welcome.test.tsx        A  T22
frontend/src/app/layout.tsx                                  M  <Providers> (T19)
frontend/src/app/page.tsx                                    D  T23
frontend/src/app/providers.tsx                               A  T19
frontend/src/components/app-header.tsx                       D  T23
frontend/src/components/app/account-menu.tsx                 A  T21
frontend/src/components/app/app-header.test.tsx              A  T21
frontend/src/components/app/app-header.tsx                   A  T21
frontend/src/components/app/church-switcher.tsx              A  T21
frontend/src/components/app/confirm-dialog.test.tsx          A  T20
frontend/src/components/app/confirm-dialog.tsx               A  T20
frontend/src/components/app/empty-state.test.tsx             A  T20
frontend/src/components/app/empty-state.tsx                  A  T20
frontend/src/components/app/error-state.test.tsx             A  T20
frontend/src/components/app/error-state.tsx                  A  T20
frontend/src/components/app/page-header.test.tsx             A  T20
frontend/src/components/app/page-header.tsx                  A  T20
frontend/src/components/app/pending-button.test.tsx          A  T20
frontend/src/components/app/pending-button.tsx               A  T20
frontend/src/components/ui/alert-dialog.tsx                  A  generated (T20)
frontend/src/components/ui/alert.tsx                         A  generated (T20)
frontend/src/components/ui/button.test.tsx                   A  T20
frontend/src/components/ui/button.tsx                        M  touch size (T20)
frontend/src/components/ui/combobox.tsx                      A  generated (T20; Q3)
frontend/src/components/ui/input.tsx                         A  generated (T20)
frontend/src/components/ui/label.tsx                         A  generated (T20)
frontend/src/components/ui/tabs.tsx                          A  generated (T20)
frontend/src/lib/api.test.ts                                 D  moved (T16)
frontend/src/lib/api.ts                                      D  moved (T16)
frontend/src/lib/api/client.test.ts                          A  T16
frontend/src/lib/api/client.ts                               A  T16
frontend/src/lib/api/errors.test.ts                          A  T16
frontend/src/lib/api/errors.ts                               A  T16
frontend/src/lib/api/openapi.json                            A  generated by export_openapi.py (T13)
frontend/src/lib/api/schema.d.ts                             A  generated by gen:api (T15)
frontend/src/lib/api/timeouts.ts                             A  T16
frontend/src/lib/api/types.ts                                A  T16
frontend/src/lib/auth.test.ts                                A  T18
frontend/src/lib/auth.ts                                     A  getAccessToken + signing-out flag (T18); useSignOut (T19)
frontend/src/lib/church-context.tsx                          A  T18
frontend/src/lib/church-store.test.tsx                       A  T17
frontend/src/lib/church.test.ts                              M  T17
frontend/src/lib/church.ts                                   M  T17
frontend/src/lib/me-context.tsx                              A  T19
frontend/src/lib/queries/auth-events.ts                      A  T18
frontend/src/lib/queries/church.ts                           A  T18
frontend/src/lib/queries/client.test.ts                      A  T18
frontend/src/lib/queries/client.ts                           A  T18
frontend/src/lib/queries/keys.test.ts                        A  T18
frontend/src/lib/queries/keys.ts                             A  T18
frontend/src/lib/queries/me.ts                               A  T18
frontend/src/lib/storage.test.ts                             A  T17
frontend/src/lib/storage.ts                                  A  T17
frontend/src/lib/urls.test.ts                                A  T17
frontend/src/lib/urls.ts                                     A  T17
frontend/src/lib/use-sign-out.test.tsx                       A  T19
frontend/src/test/fake-api.ts                                A  T15
frontend/src/test/fixtures/index.ts                          A  T15
frontend/src/test/lint-rules.test.ts                         A  T15
frontend/src/test/mocks.ts                                   A  T15
frontend/src/test/render.tsx                                 A  T19
frontend/src/test/setup-dom.test.tsx                         A  T15
frontend/src/test/setup-dom.ts                               A  T15; afterEach resets added in T17, T18
frontend/vitest.config.ts                                    M  unit + dom projects, plugin-react, --no-experimental-webstorage forks (T15)
pytest.ini                                                   M  markers = postgres: needs TEST_DATABASE_URL (T1)
```
Count check: 5 root/CI/docs files excluding the plan (`.github/workflows/ci.yml`, `README.md`, `docs/manual-verification.md`, `docs/ops-runbook.md`, `pytest.ini`) + the plan + the F §1.5 spec amendment + 53 `backend/` + 73 `frontend/` = 133. Unchanged on purpose: `app.py`, `ui_helpers.py`, `streamlit_tenancy.py`, `db/engine.py` (`init_db` stays), `db/health.py`, `api/middleware.py`, `api/startup.py`, `lib/supabase/proxy.ts`, `app/login/page.tsx`, `app/auth/callback/route.ts`, `lib/latest.ts`, `backend/Procfile`, `backend/tests/pg_smoke.py`, `.github/workflows/backup.yml`.

---

### Task 1: Preflight, dependencies, the `postgres` marker, the no-network and `pg_db` fixtures, the local-URL guard (F §5.1, §5.3; S Backend 1a)

Owner answer Q2 is recorded (Owner decisions above: 29 codes), so Task 2 can start right after this task. Nothing here needs Postgres: `pg_db` skips without `TEST_DATABASE_URL`, and its first user is Task 11.

**Files:**
- Modify: `backend/requirements.txt:1-14` (the runtime block; lines 15-17, the "migration only" block, are unchanged)
- Modify: `pytest.ini:1-3` (add `markers`)
- Modify: `backend/tests/conftest.py` (append after line 169: `_no_network`, `pg_db`; deferred imports, per the header rule at lines 3-7)
- Create: `backend/tests/pg_helpers.py`
- Test: `backend/tests/test_no_network.py` (new, 2 tests), `backend/tests/test_pg_helpers.py` (new, 6 tests), `backend/tests/test_foundation_setup.py:1` (import) and appended block (2 tests)

**Interfaces:**
- Consumes: `db.reset_engine_for_tests(url: str) -> Engine` (db/engine.py:97-107; normalizes `postgresql://` to psycopg2); `db.init_db()`; `ROOT` in `test_foundation_setup.py:7`.
- Produces:
  - `tests.pg_helpers.LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1")`;
  - `tests.pg_helpers.require_local_test_url(url: str) -> str`: returns `url` unchanged; raises `RuntimeError("TEST_DATABASE_URL must point at a local, throwaway Postgres.")` unless the scheme starts with `postgres` and the host is `localhost`, `127.0.0.1` or `::1` (same rule as `pg_smoke.py:30-34`, plus IPv6 loopback). Later users: `pg_db` (here), Task 8's `throwaway_database`.
  - autouse fixture `_no_network` (conftest): patches `socket.socket.connect` and `psycopg2.connect` (libpq opens its own C sockets, which the socket patch never sees); allows `localhost`, `127.0.0.1`, `::1` and every `AF_UNIX` address; anything else raises `RuntimeError("Tests must not open network connections: <host>")` before a packet is sent. Later users: every test; Tasks 6, 8, 11, 14 and 1b rely on it.
  - fixture `pg_db` (conftest) → `sqlalchemy.Engine`: skips with "TEST_DATABASE_URL is not set (the backend-postgres CI job sets it)" when the variable is unset or blank; `reset_engine_for_tests(require_local_test_url(url))`; creates missing tables with `init_db()` (the single line `    init_db()   # the tables, when a run starts from an empty database`, which Task 6 replaces with `command.upgrade(alembic_config(url=url, configure_logger=False), "head")`, run on every call: a no-op at head); then `TRUNCATE "<t1>", "<t2>", … RESTART IDENTITY CASCADE` of every table except `alembic_version`; disposes the engine after the test. Later users: Task 11 (`test_rls_check_names_tables_without_rls`), Task 14 (`test_concurrent_first_requests_on_postgres_both_succeed_with_one_id`), 1b.
  - `pytest.ini` marker `postgres: needs TEST_DATABASE_URL (runs in the backend-postgres CI job)`.
  - `backend/requirements.txt` lines `fastapi==0.141.*`, `pydantic==2.13.*`, `alembic>=1.20`, `tzdata>=2026.4` (floors from the versions Step 6 resolves).

- [ ] **Step 0: Commit this plan (the branch's first commit)**

Skip this step if `git log --oneline -1 -- docs/superpowers/plans/2026-09-26-slice-1a-platform.md` already prints `<sha> Plan: slice 1a platform (F, S slice 1; owner answers 2026-09-26)` (the controller may commit the plan before dispatching Task 1).

```bash
git status --short
git add docs/superpowers/plans/2026-09-26-slice-1a-platform.md
git commit -m "Plan: slice 1a platform (F, S slice 1; owner answers 2026-09-26)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
```

Expected: before the commit, `git status --short` lists only `?? .claude/` and `?? docs/superpowers/plans/2026-09-26-slice-1a-platform.md`; `.claude/` stays untracked. Afterwards the last line is `<sha> Plan: slice 1a platform …`. If the plan is already committed (`git log --oneline origin/main..HEAD` lists it), skip this step. (Numbered 0 so that the step numbers the rest of the plan cites stay valid.)

- [ ] **Step 1: Check the branch and the baseline**

```bash
git fetch origin
git status -sb | head -1
git log --oneline -1 origin/main
git diff --name-only 7978a5e origin/main
git log --oneline origin/main..HEAD
test -f backend/api/middleware.py && test -f backend/db/health.py \
  && grep -q '^from api.routes import health, me, rubric$' backend/api/main.py \
  && echo "ops-3 is on main"
test ! -d backend/migrations && ! grep -qi alembic backend/requirements.txt && echo "no Alembic yet"
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
git show origin/main:docs/ops-runbook.md | grep -n '\[owner' | grep -v 'An entry marked' | wc -l
.venv/bin/python -m pytest -q | tail -1
(cd frontend && npx vitest run 2>&1 | grep -E '^ +Tests ')
```

Expected, in order: `## claude/slice-1-plan...origin/main [ahead 1, behind 4]` (only the plan commit on this branch; `origin/main` gained the freeze records PRs #14 and #15 after `7978a5e`), or `[ahead 1]` if `origin/main` is still `7978a5e`; `560ebb3 Merge pull request #15 from bbrown62450/claude/ops-3-freeze-records-b` (or `7978a5e …`, or a later docs-only merge); the name-only diff prints exactly `.github/workflows/keep-awake.yml`, `backend/tests/test_ops_workflows.py`, `docs/manual-verification.md`, `docs/ops-runbook.md` (the freeze records: production Streamlit is liturgy-frozen; URL constants only, no test added or removed), or nothing when `origin/main` is `7978a5e`; exactly one line, this plan's commit; `ops-3 is on main`; `no Alembic yet`; `20` (this branch, still at `7978a5e`) and `4` (`origin/main` at `560ebb3`: the freeze records filled the Freeze rows); `559 passed`; `      Tests  15 passed (15)`.

If the branch line shows `behind`, merge `origin/main` now: `git merge origin/main -m "Merge origin/main (freeze records #14, #15) into claude/slice-1-plan" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"` (the branch holds only the plan, so no conflict), then rerun this step. After the merge expect `[ahead 2]`, two lines from `git log --oneline origin/main..HEAD` (the merge and the plan commit), the two marker counts equal (`4` at `560ebb3`), `559 passed` and `15 passed`. Every later task works on this merged tree (Task 24's `docs/` line numbers are those of `560ebb3`). If anything else differs (another path in the diff, a count other than 559 or 15, a merge conflict), stop and ask the owner.

- [ ] **Step 2: Write the failing tests**

In `backend/tests/test_foundation_setup.py`, replace line 1:

```python
import json
```

with:

```python
import configparser
import json
```

and append at the end of the file (after line 108):

```python


# --- slice 1a: Alembic, tzdata, exact minor pins and the postgres marker (S Backend 1a) ---

def test_backend_requirements_add_alembic_tzdata_and_exact_minor_pins():
    lines = {line.strip() for line in (ROOT / "backend" / "requirements.txt").read_text().splitlines()}
    assert {"alembic>=1.20", "tzdata>=2026.4", "fastapi==0.141.*", "pydantic==2.13.*"} <= lines
    assert "fastapi>=0.115" not in lines          # replaced by the exact minor pin


def test_pytest_ini_declares_the_postgres_marker():
    ini = configparser.ConfigParser()
    ini.read(ROOT / "pytest.ini")
    markers = [line.strip() for line in ini["pytest"]["markers"].splitlines() if line.strip()]
    assert markers == ["postgres: needs TEST_DATABASE_URL (runs in the backend-postgres CI job)"]
```

`test_backend_requirements_pin_runtime_and_migration_deps` (lines 10-18) stays as it is: the new requirements file keeps `SQLAlchemy>=2.0`, `psycopg2-binary`, `notion-client` and the "migration only" comment, and still names no `streamlit`.

Create `backend/tests/test_pg_helpers.py`:

```python
"""The local-URL guard every Postgres-only test goes through (F §5.1)."""
import pytest

from tests.pg_helpers import require_local_test_url


@pytest.mark.parametrize("url", [
    "postgresql://postgres:ci-throwaway@localhost:5432/postgres",
    "postgresql+psycopg2://postgres:pw@127.0.0.1:5432/postgres",
    "postgres://postgres:pw@[::1]:5432/postgres",
], ids=["localhost", "127.0.0.1", "ipv6-loopback"])
def test_local_test_url_guard_accepts_loopback_postgres(url):
    assert require_local_test_url(url) == url


@pytest.mark.parametrize("url", [
    "postgresql://u:p@aws-0.pooler.supabase.com:5432/postgres",
    "sqlite:///x.db",
    "",
], ids=["supabase-pooler", "sqlite", "empty"])
def test_local_test_url_guard_rejects_remote_or_non_postgres(url):
    with pytest.raises(RuntimeError, match="TEST_DATABASE_URL must point at a local, throwaway Postgres."):
        require_local_test_url(url)
```

Create `backend/tests/test_no_network.py`:

```python
"""The suite never reaches the network (F §5.3): conftest's autouse _no_network
fixture refuses any socket connect that is not to this machine."""
import socket

import pytest


def test_an_outbound_connect_raises():
    # 192.0.2.1 is TEST-NET-1 (RFC 5737): a numeric address, so no DNS lookup either.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)          # if the guard were ever missing: fail in 1 s, never hang
        with pytest.raises(RuntimeError, match="Tests must not open network connections: 192.0.2.1"):
            sock.connect(("192.0.2.1", 80))

    # libpq opens its own sockets: the guard checks psycopg2's host too.
    from sqlalchemy import create_engine
    engine = create_engine("postgresql+psycopg2://u:p@aws-0-us-east-1.pooler.supabase.com:5432/postgres")
    with pytest.raises(RuntimeError, match="Tests must not open network connections: aws-0-us-east-1.pooler.supabase.com"):
        engine.connect()


def test_a_localhost_connect_is_allowed():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        with socket.create_connection(server.getsockname(), timeout=5) as client:
            peer, _ = server.accept()
            with peer:
                client.sendall(b"ping")
                assert peer.recv(4) == b"ping"
```

- [ ] **Step 3: Run the tests to verify they fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_foundation_setup.py 2>&1 | tail -3
.venv/bin/python -m pytest -q backend/tests/test_pg_helpers.py 2>&1 | tail -3
.venv/bin/python -m pytest -q backend/tests/test_no_network.py -k localhost 2>&1 | tail -1
```

Expected: first `2 failed, 11 passed`: the requirements test fails with `AssertionError` ("Extra items in the left set: 'pydantic==2.13.*' 'fastapi==0.141.*' 'alembic>=1.20' …"), and the marker test with `KeyError: 'markers'`. Then a collection error `ModuleNotFoundError: No module named 'tests.pg_helpers'` and `1 error`. Then `1 passed, 1 deselected`: the localhost test passes before and after the fixture (it proves the guard will not block loopback). `test_an_outbound_connect_raises` is deliberately not run yet: without the fixture it would really send a connect attempt off this machine (and its `engine.connect()` would do a DNS lookup). It first runs in Step 7, where it must pass.

- [ ] **Step 4: Pin the backend requirements (`backend/requirements.txt`)**

Replace lines 1-14:

```
# --- Runtime ---
fastapi>=0.115
uvicorn[standard]>=0.30
PyJWT[crypto]>=2.8
SQLAlchemy>=2.0
psycopg2-binary>=2.9
python-dotenv>=1.0.0
beautifulsoup4>=4.12.0
requests>=2.31.0
httpx>=0.25.0
lxml>=4.9.0
playwright>=1.40.0
openai>=1.0.0
python-docx>=1.0.0
```

with:

```
# --- Runtime ---
# fastapi and pydantic are pinned to exact minors so the committed OpenAPI
# snapshot (frontend/src/lib/api/openapi.json) only changes on purpose.
fastapi==0.141.*
pydantic==2.13.*
uvicorn[standard]>=0.30
PyJWT[crypto]>=2.8
SQLAlchemy>=2.0
alembic>=1.20
psycopg2-binary>=2.9
python-dotenv>=1.0.0
# zoneinfo needs an IANA database; Railway's image may not ship one.
tzdata>=2026.4
beautifulsoup4>=4.12.0
requests>=2.31.0
httpx>=0.25.0
lxml>=4.9.0
playwright>=1.40.0
openai>=1.0.0
python-docx>=1.0.0
```

Lines 15-17 (blank line, the "migration only" comment, `notion-client>=2.2.1`) stay.

- [ ] **Step 5: Declare the marker (`pytest.ini`)**

Replace the whole file (3 lines):

```ini
[pytest]
pythonpath = . backend
testpaths = backend/tests streamlit_tests
```

with:

```ini
[pytest]
pythonpath = . backend
testpaths = backend/tests streamlit_tests
markers =
    postgres: needs TEST_DATABASE_URL (runs in the backend-postgres CI job)
```

- [ ] **Step 6: Install the new dependencies and record the versions**

This step needs the network (PyPI). The agent runs it:

```bash
.venv/bin/pip install -q -r requirements-dev.txt
.venv/bin/pip show alembic mako tzdata 2>/dev/null | grep -E '^(Name|Version):'
.venv/bin/python -c "import fastapi, pydantic, sqlalchemy; print(fastapi.__version__, pydantic.VERSION, sqlalchemy.__version__)"
```

Expected: the install ends without errors; `Name: alembic` / `Version: 1.20.x`, `Name: Mako` / `Version: 1.4.x`, `Name: tzdata` / `Version: 2026.4` (or newer); then `0.141.1 2.13.5 2.1.1` (the pins change nothing that is installed). If alembic resolves to another minor (for example 1.21), change `alembic>=1.20` to `alembic>=<that major.minor>` in both `backend/requirements.txt` and the test, and record it for Task 25's PR body; do the same for a tzdata newer than 2026.4 only if 2026.4 cannot be installed. If PyPI cannot be reached, stop and ask the owner (Tasks 2-4 do not need Alembic, but Task 5 does).

- [ ] **Step 7: Create `backend/tests/pg_helpers.py` and the two fixtures**

Create `backend/tests/pg_helpers.py`:

```python
"""Helpers for the Postgres-only tests (`@pytest.mark.postgres`; F §5.1).

Every Postgres URL a test uses passes require_local_test_url first, so a test
can never create roles, drop databases or TRUNCATE tables anywhere but a
local, throwaway Postgres (the same rule as pg_smoke.py).
"""
from urllib.parse import urlsplit

LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1")


def require_local_test_url(url: str) -> str:
    """Return `url` if it is a Postgres URL on this machine, else raise RuntimeError."""
    try:
        parts = urlsplit(url or "")
        host = parts.hostname
    except ValueError:              # e.g. an unbalanced "[" in the host
        parts, host = None, None
    if parts is None or not parts.scheme.startswith("postgres") or host not in LOCAL_HOSTS:
        raise RuntimeError("TEST_DATABASE_URL must point at a local, throwaway Postgres.")
    return url
```

Append to `backend/tests/conftest.py` (after line 169, the end of `_fresh_readiness_memo`):

```python


# --- slice 1: network-free tests and the Postgres test database (F §5.1, §5.3) ---

_LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1")


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """Refuse every socket connect, and every psycopg2 connect, that leaves
    this machine (F §5.3). It patches socket.socket.connect and
    psycopg2.connect: libpq opens its own C sockets, which the first patch
    never sees.

    Loopback addresses (the CI Postgres service, a test's own listening socket)
    and AF_UNIX paths stay allowed. Anything else raises RuntimeError before a
    packet is sent, so a test that forgot a fake fails loudly instead of
    calling Google, OpenAI or the production database."""
    import socket

    real_connect = socket.socket.connect

    def guarded_connect(sock, address):
        if sock.family != getattr(socket, "AF_UNIX", None):
            host = address[0] if isinstance(address, tuple) else address
            if host not in _LOCAL_HOSTS:
                raise RuntimeError(f"Tests must not open network connections: {host}")
        return real_connect(sock, address)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)

    # psycopg2 connects through libpq's own C sockets, which the patch above
    # never sees; check the host SQLAlchemy (or a test) passes to it instead.
    import psycopg2
    from psycopg2.extensions import parse_dsn

    real_pg_connect = psycopg2.connect

    def guarded_pg_connect(dsn=None, connection_factory=None, cursor_factory=None, **kwargs):
        params = {**(parse_dsn(dsn) if dsn else {}), **kwargs}
        host = params.get("host") or "localhost"      # no host: libpq uses the local socket
        if any(h not in _LOCAL_HOSTS for h in str(host).split(",")):
            raise RuntimeError(f"Tests must not open network connections: {host}")
        return real_pg_connect(dsn, connection_factory, cursor_factory, **kwargs)

    monkeypatch.setattr(psycopg2, "connect", guarded_pg_connect)
    yield


@pytest.fixture
def pg_db():
    """The CI Postgres test database, emptied for this test; yields its Engine.

    Skips unless TEST_DATABASE_URL is set (only the backend-postgres CI job
    sets it). The URL must be a local, throwaway Postgres
    (tests.pg_helpers.require_local_test_url). Every table except
    alembic_version is truncated before the test, so each test starts empty.
    """
    import os

    url = os.environ.get("TEST_DATABASE_URL", "").strip()
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set (the backend-postgres CI job sets it)")

    from sqlalchemy import inspect, text

    from db import init_db, reset_engine_for_tests
    from tests.pg_helpers import require_local_test_url

    engine = reset_engine_for_tests(require_local_test_url(url))
    init_db()   # the tables, when a run starts from an empty database
    tables = [name for name in inspect(engine).get_table_names() if name != "alembic_version"]
    if tables:
        quoted = ", ".join(f'"{name}"' for name in tables)
        with engine.begin() as conn:
            conn.execute(text(f"TRUNCATE {quoted} RESTART IDENTITY CASCADE"))
    try:
        yield engine
    finally:
        engine.dispose()
```

The guard is the second line of defence after `require_local_test_url`: even a test that bypassed the helper cannot reach a remote database. The whole suite already runs with it (no current test opens an outbound connection; checked on `7978a5e`). `pg_db` has no users yet; Task 6 swaps its `init_db()` line for `alembic upgrade head`.

- [ ] **Step 8: Run the tests and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_foundation_setup.py backend/tests/test_no_network.py backend/tests/test_pg_helpers.py
.venv/bin/python -m pytest -q | tail -1
```

Expected: `21 passed` (13 + 2 + 6), then `569 passed`.

- [ ] **Step 9: Commit**

```bash
git add backend/requirements.txt pytest.ini backend/tests/conftest.py backend/tests/pg_helpers.py \
        backend/tests/test_no_network.py backend/tests/test_pg_helpers.py \
        backend/tests/test_foundation_setup.py
git commit -m "Tests: no-network guard, pg_db fixture and postgres marker; pin fastapi/pydantic, add alembic and tzdata (F §5.1, §5.3, S Backend 1a)

The autouse _no_network fixture refuses any socket connect that leaves the
machine. pg_db binds TEST_DATABASE_URL (skipped without it), refuses any URL
that is not a local Postgres, and empties every table before each test.
fastapi and pydantic are pinned to exact minors for the OpenAPI snapshot.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: `domain_errors`, `db.ids.as_uuid` and the `usecases` package; `bad_request` and `method_not_allowed` join the registry (F §2.2 items 4-5, §1.5; owner Q2)

Owner answer Q2 (2026-09-26): `ERROR_CODES` holds the 27 F §1.5 codes plus `bad_request` (400) and `method_not_allowed` (405), which `api/errors.py` already returns for Starlette's 400 and 405 (`test_middleware.py:59` asserts the 405). That is **29 codes**, and F §1.5 is amended in this task (an index row in "Amendments from slice specs" and the two registry rows). Task 3 maps every other framework status to `bad_request` (4xx) or `internal_error` (5xx), so the handler's fallback code `"error"` disappears. This task adds no FastAPI code; the API mapping is Task 3.

**Files:**
- Create: `backend/domain_errors.py`, `backend/db/ids.py`, `backend/usecases/__init__.py`
- Modify: `docs/superpowers/specs/2026-09-25-migration-foundations-design.md:69` (insert an amendment-index row after it), `:194` (the 400 registry row), `:197` (insert a 405 row after the 404 row)
- Test: `backend/tests/test_domain_errors.py` (new; 15 tests here, Task 3 appends 8), `backend/tests/test_ids.py` (new, 6 tests), `backend/tests/test_no_streamlit_in_core.py` (append 1 test after line 15)

**Interfaces:**
- Consumes: nothing new (standard library only).
- Produces:
  - `domain_errors.ERROR_CODES: dict[str, int]`, exactly these 29 entries: 400 `bad_request`, `invite_rejected`, `gmail_state_invalid`, `gmail_connect_failed`; 401 `unauthenticated`; 403 `forbidden`; 404 `not_found`; 405 `method_not_allowed`; 409 `conflict`, `last_admin`, `owner_must_transfer`, `invite_exists`, `gmail_not_connected`; 422 `invalid_request`, `prompt_invalid`, `idempotency_mismatch`, `invalid_rubric`; 429 `rate_limited`; 500 `internal_error`; 502 `upstream_error`, `ai_upstream_error`, `gmail_send_failed`; 503 `auth_unavailable`, `ai_not_configured`, `ai_busy`, `gmail_not_configured`, `db_unavailable`; 504 `upstream_timeout`, `ai_timeout`. Later users: Task 3 (`api/errors.py`), Task 16 (`test_error_registry.py` reads the keys; the frontend `ServerErrorCode` union has the same 29).
  - `class domain_errors.DomainError(Exception)`: class attributes `status: ClassVar[int]` (500 on the base), `default_code: ClassVar[Optional[str]]` (None on the base); `__init__(self, message: str, *, code: Optional[str] = None, field: Optional[str] = None, details: Optional[dict[str, Any]] = None)`; instance attributes `message`, `code`, `field`, `details` (and `status` from the class). Raises `ValueError("<Class> needs a code: it has no default code.")` when neither `code` nor `default_code` is set, and `ValueError("<Class> is a <status>; code '<code>' is not registered with that status in ERROR_CODES.")` when `ERROR_CODES.get(code) != status`.
  - Subclasses (status, default code): `InvalidInput` (422, `invalid_request`), `NotFound` (404, `not_found`), `Forbidden` (403, `forbidden`), `Conflict` (409, `conflict`), `Rejected` (400, None), `NotConfigured` (503, None), `Busy` (503, None), `UpstreamError` (502, None), `UpstreamTimeout` (504, None).
  - `domain_errors.RateLimited(message: str, *, retry_after_seconds: float)`: 429, `rate_limited`; `retry_after_seconds` attribute = `max(1, ceil(n))` (an int); `details == {"retry_after_seconds": <that int>}`; `field` None. Later users: Task 3 (the handler adds `Retry-After`), Task 4 (never stored), 1b's church-create cap, slice 2's limiter.
  - `db.ids.as_uuid(value: object) -> uuid.UUID`: a `uuid.UUID` passes through; a `str` is parsed with `uuid.UUID(value)`; `None`, a malformed string, `""` or any other type raises `NotFound("Not found.")`. Later users: 1b repos and usecases.
  - `backend/usecases/__init__.py`: package marker whose docstring states the F §2.2 layer rules. Later users: 1b `usecases/onboarding.py`, Task 13's import test.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_domain_errors.py`:

```python
"""Domain errors, the F §1.5 code registry, and (Task 3) their API mapping."""
import subprocess
import sys
from pathlib import Path

import pytest

from domain_errors import (
    ERROR_CODES,
    Busy,
    Conflict,
    DomainError,
    Forbidden,
    InvalidInput,
    NotConfigured,
    NotFound,
    RateLimited,
    Rejected,
    UpstreamError,
    UpstreamTimeout,
)

BACKEND = Path(__file__).resolve().parents[1]

# --- the classes and the registry (F §2.2 item 4, §1.5) ---------------------------


@pytest.mark.parametrize("make, status, code", [
    (lambda: InvalidInput("Church name is required."), 422, "invalid_request"),
    (lambda: NotFound("Not found."), 404, "not_found"),
    (lambda: Forbidden("Only the owner can do that."), 403, "forbidden"),
    (lambda: Conflict("Someone else changed this."), 409, "conflict"),
    (lambda: RateLimited("Slow down.", retry_after_seconds=30), 429, "rate_limited"),
], ids=["InvalidInput", "NotFound", "Forbidden", "Conflict", "RateLimited"])
def test_each_domain_error_has_its_status_and_default_code(make, status, code):
    exc = make()
    assert isinstance(exc, DomainError)
    assert (exc.status, exc.code) == (status, code)
    assert exc.message == str(exc)


@pytest.mark.parametrize("cls, code, status", [
    (Rejected, "invite_rejected", 400),
    (NotConfigured, "ai_not_configured", 503),
    (Busy, "ai_busy", 503),
    (UpstreamError, "ai_upstream_error", 502),
    (UpstreamTimeout, "ai_timeout", 504),
])
def test_per_case_classes_require_a_code(cls, code, status):
    with pytest.raises(ValueError, match="needs a code"):
        cls("Something failed.")
    exc = cls("Something failed.", code=code)
    assert (exc.status, exc.code) == (status, code)


def test_a_code_must_be_registered_with_the_class_status():
    with pytest.raises(ValueError, match="not registered"):
        Rejected("No.", code="not_a_code")
    with pytest.raises(ValueError, match="not registered"):
        Conflict("No.", code="not_found")                  # a 404 code on a 409 class
    assert InvalidInput("Bad rubric.", code="invalid_rubric").status == 422
    assert Conflict("Last admin.", code="last_admin").code == "last_admin"


def test_rate_limited_always_sets_retry_after_seconds():
    exc = RateLimited("You've created 5 churches in the last 24 hours. Try again later.",
                      retry_after_seconds=30)
    assert exc.retry_after_seconds == 30
    assert exc.details == {"retry_after_seconds": 30}
    assert exc.field is None
    assert RateLimited("Slow down.", retry_after_seconds=2.2).retry_after_seconds == 3   # rounded up
    assert RateLimited("Slow down.", retry_after_seconds=0).details == {"retry_after_seconds": 1}


def test_error_codes_is_the_f_1_5_registry():
    assert ERROR_CODES == {
        "bad_request": 400, "invite_rejected": 400, "gmail_state_invalid": 400,
        "gmail_connect_failed": 400,
        "unauthenticated": 401,
        "forbidden": 403,
        "not_found": 404,
        "method_not_allowed": 405,
        "conflict": 409, "last_admin": 409, "owner_must_transfer": 409, "invite_exists": 409,
        "gmail_not_connected": 409,
        "invalid_request": 422, "prompt_invalid": 422, "idempotency_mismatch": 422,
        "invalid_rubric": 422,
        "rate_limited": 429,
        "internal_error": 500,
        "upstream_error": 502, "ai_upstream_error": 502, "gmail_send_failed": 502,
        "auth_unavailable": 503, "ai_not_configured": 503, "ai_busy": 503,
        "gmail_not_configured": 503, "db_unavailable": 503,
        "upstream_timeout": 504, "ai_timeout": 504,
    }
    assert len(ERROR_CODES) == 29


def test_db_unavailable_is_503():
    assert ERROR_CODES["db_unavailable"] == 503


def test_domain_errors_imports_no_fastapi():
    code = ("import sys, domain_errors; "
            "bad = sorted({m.split('.')[0] for m in sys.modules} & {'fastapi', 'starlette', 'streamlit'}); "
            "print(bad); sys.exit(1 if bad else 0)")
    result = subprocess.run([sys.executable, "-c", code], cwd=BACKEND, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
```

Create `backend/tests/test_ids.py`:

```python
"""db.ids.as_uuid: malformed ids are a 404, never a 500 (F §2.2 item 5)."""
import uuid

import pytest

from db.ids import as_uuid
from domain_errors import NotFound

ID = uuid.UUID("6f1c2a52-3a8e-4c3e-9d57-2f0b1f6f1a11")


@pytest.mark.parametrize("value", [ID, str(ID)], ids=["uuid", "string"])
def test_as_uuid_accepts_uuid_and_string(value):
    assert as_uuid(value) == ID


@pytest.mark.parametrize("value", [None, "nope", 123, ""], ids=["none", "malformed", "int", "empty"])
def test_as_uuid_raises_not_found_for_bad_input(value):
    with pytest.raises(NotFound) as caught:
        as_uuid(value)
    assert (caught.value.status, caught.value.code, caught.value.message) == (404, "not_found", "Not found.")
```

Append to `backend/tests/test_no_streamlit_in_core.py` (after line 15):

```python


def test_usecases_package_imports_no_fastapi_or_streamlit():
    # usecases, domain_errors and db.ids are below the API layer (F §2.2).
    code = ("import sys, usecases, domain_errors, db.ids; "
            "bad = sorted({m.split('.')[0] for m in sys.modules} & {'fastapi', 'starlette', 'streamlit'}); "
            "print(bad); sys.exit(1 if bad else 0)")
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=CODE_DIR, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_domain_errors.py 2>&1 | tail -3
.venv/bin/python -m pytest -q backend/tests/test_ids.py 2>&1 | tail -3
.venv/bin/python -m pytest -q backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -3
```

Expected: a collection error `ModuleNotFoundError: No module named 'domain_errors'` and `1 error`; then `ModuleNotFoundError: No module named 'db.ids'` and `1 error`; then `1 failed, 1 passed`: the new test's subprocess fails with `ModuleNotFoundError: No module named 'usecases'`.

- [ ] **Step 3: Create `backend/domain_errors.py`**

```python
"""Domain errors and the error-code registry (F §1.5, §2.2 item 4; slice 1).

Usecases, repos and domain modules raise these; one handler in api/errors.py
turns each into the uniform body {"error": {"code", "message", "request_id",
"fields"?, "details"?}} with the class's HTTP status. This module imports no
FastAPI, Starlette or Streamlit, so every layer can use it.

ERROR_CODES is the one registry of server error codes and their statuses. The
frontend mirrors it as the ApiErrorCode union in frontend/src/lib/api/errors.ts
(test_error_registry.py keeps the two in step).
"""
import math
from typing import Any, ClassVar, Optional

ERROR_CODES: dict[str, int] = {
    # 400: a well-formed request the domain refuses; bad_request for framework 4xx
    "bad_request": 400,
    "invite_rejected": 400,
    "gmail_state_invalid": 400,
    "gmail_connect_failed": 400,
    # 401
    "unauthenticated": 401,
    # 403: a require_church 403 carries details.reason = "no_church_access"
    "forbidden": 403,
    # 404
    "not_found": 404,
    # 405: a known path called with the wrong method (framework)
    "method_not_allowed": 405,
    # 409
    "conflict": 409,
    "last_admin": 409,
    "owner_must_transfer": 409,
    "invite_exists": 409,
    "gmail_not_connected": 409,
    # 422
    "invalid_request": 422,
    "prompt_invalid": 422,
    "idempotency_mismatch": 422,
    "invalid_rubric": 422,
    # 429: always RateLimited
    "rate_limited": 429,
    # 500
    "internal_error": 500,
    # 502
    "upstream_error": 502,
    "ai_upstream_error": 502,
    "gmail_send_failed": 502,
    # 503
    "auth_unavailable": 503,
    "ai_not_configured": 503,
    "ai_busy": 503,
    "gmail_not_configured": 503,
    "db_unavailable": 503,
    # 504
    "upstream_timeout": 504,
    "ai_timeout": 504,
}


class DomainError(Exception):
    """Base class: a failure the user can be told about, with a registered code.

    `field` names the input the message is about (it becomes `fields[field]` on
    a 422); `details` is an optional, code-specific object (F §1.5).
    """

    status: ClassVar[int] = 500
    default_code: ClassVar[Optional[str]] = None

    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        field: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message)
        code = code or self.default_code
        if code is None:
            raise ValueError(f"{type(self).__name__} needs a code: it has no default code.")
        if ERROR_CODES.get(code) != self.status:
            raise ValueError(
                f"{type(self).__name__} is a {self.status}; code {code!r} is not registered "
                f"with that status in ERROR_CODES."
            )
        self.message = message
        self.code = code
        self.field = field
        self.details = details


class InvalidInput(DomainError):
    status = 422
    default_code = "invalid_request"


class NotFound(DomainError):
    status = 404
    default_code = "not_found"


class Forbidden(DomainError):
    status = 403
    default_code = "forbidden"


class Conflict(DomainError):
    status = 409
    default_code = "conflict"


class Rejected(DomainError):
    status = 400


class NotConfigured(DomainError):
    status = 503


class Busy(DomainError):
    status = 503


class UpstreamError(DomainError):
    status = 502


class UpstreamTimeout(DomainError):
    status = 504


class RateLimited(DomainError):
    """The only 429 (F §1.5, §2.2): the limiter and the church-create cap raise it.

    It always carries details.retry_after_seconds (a whole number of seconds,
    at least 1); the API handler copies it into the Retry-After header, and
    run_idempotent never stores it.
    """

    status = 429
    default_code = "rate_limited"

    def __init__(self, message: str, *, retry_after_seconds: float):
        seconds = max(1, math.ceil(retry_after_seconds))
        super().__init__(message, details={"retry_after_seconds": seconds})
        self.retry_after_seconds = seconds
```

The constructor check makes a wrong code fail where it is raised (and in that module's tests), not as a confusing status in production. `ERROR_CODES` keeps F §1.5's order, grouped by status.

- [ ] **Step 4: Create `backend/db/ids.py`**

```python
"""One way to turn an untrusted id into a uuid.UUID (F §2.2 item 5; slice 1).

Every repo and usecase function that slice 1 creates or changes coerces its ids
with as_uuid(), so a malformed id is a 404 `not_found`, never a ValueError or
a SQLAlchemy StatementError (a 500).
"""
import uuid

from domain_errors import NotFound


def as_uuid(value: object) -> uuid.UUID:
    """`value` as a UUID; NotFound("Not found.") for None, malformed text or any other type."""
    if isinstance(value, uuid.UUID):
        return value
    if isinstance(value, str):
        try:
            return uuid.UUID(value)
        except ValueError:
            pass
    raise NotFound("Not found.")
```

`db/__init__.py` does not re-export it: callers import `from db.ids import as_uuid`. `db/` still imports nothing from `api/`.

- [ ] **Step 5: Create `backend/usecases/__init__.py`**

```python
"""Usecases: one function per user action (F §2.2; slice 1 creates the package).

Layer rules:
- A usecase takes church_id and user_id as uuid.UUID (coerced with
  db.ids.as_uuid by the caller or the usecase itself).
- It owns the transaction: `with session_scope() as s:` around every write
  that must be atomic, passing `session=s` to the repo functions it calls.
- It raises domain_errors.DomainError subclasses with the exact user-facing
  messages; routes never catch them (api/errors.py maps them).
- It never imports fastapi, starlette or streamlit
  (test_no_streamlit_in_core.py checks this).
"""
```

- [ ] **Step 6: Amend F §1.5 (`docs/superpowers/specs/2026-09-25-migration-foundations-design.md`)**

After line 69 (the row that starts `| §1.5 | *(2026-09-26)* New 422 code `invalid_rubric``), insert this row, so the index table gains one line directly above the `| §1.7 | *(2026-09-26)*` row:

```markdown
| §1.5 | *(2026-09-26, owner, slice 1a)* Two framework codes join the registry: `bad_request` (400) and `method_not_allowed` (405), which `api/errors.py` already returns for Starlette's 400 and 405. Any other framework HTTP error keeps its status and gets `bad_request` (4xx) or `internal_error` (5xx), so the old fallback code `error` is gone. `ERROR_CODES` has 29 codes. | 1 |
```

Replace line 194:

```markdown
| 400 | `invite_rejected`, `gmail_state_invalid`, `gmail_connect_failed` | Well-formed request that the domain refuses |
```

with:

```markdown
| 400 | `invite_rejected`, `gmail_state_invalid`, `gmail_connect_failed`; `bad_request` (*amendment 2026-09-26, slice 1a*: a 400 from the framework, and the code of any other framework 4xx that has no code of its own) | Well-formed request that the domain refuses |
```

After line 197 (`| 404 | `not_found` | Unknown id, or an id from another church |`), insert:

```markdown
| 405 | `method_not_allowed` (*amendment 2026-09-26, slice 1a*) | A known path called with a method it does not support (framework) |
```

Check:

```bash
grep -c 'method_not_allowed' docs/superpowers/specs/2026-09-25-migration-foundations-design.md
grep -c 'bad_request' docs/superpowers/specs/2026-09-25-migration-foundations-design.md
grep -c '^| §1.5 |' docs/superpowers/specs/2026-09-25-migration-foundations-design.md
```

Expected: `2`, `2`, `3` (the two existing §1.5 index rows plus the new one).

- [ ] **Step 7: Run the tests and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_domain_errors.py backend/tests/test_ids.py backend/tests/test_no_streamlit_in_core.py
.venv/bin/python -m pytest -q | tail -1
```

Expected: `23 passed` (15 + 6 + 2), then `591 passed`.

- [ ] **Step 8: Commit**

```bash
git add backend/domain_errors.py backend/db/ids.py backend/usecases/__init__.py \
        backend/tests/test_domain_errors.py backend/tests/test_ids.py \
        backend/tests/test_no_streamlit_in_core.py \
        docs/superpowers/specs/2026-09-25-migration-foundations-design.md
git commit -m "Add domain_errors (29-code registry), db.ids.as_uuid and the usecases package (F §2.2, §1.5; owner Q2)

DomainError and its subclasses carry the F §2.2 statuses and default codes
and refuse a code that ERROR_CODES does not register with their status.
RateLimited always sets details.retry_after_seconds. bad_request (400) and
method_not_allowed (405) join the registry; F §1.5 records the amendment.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Error body `fields`/`details`, the DomainError handler, the 422 mapping, `ErrorBody`, schemas and `no_church_access` (F §1.5, §1.3-1.4, §2.2; S Modules changed; owner Q2)

After this task every error body is `{"error": {"code", "message", "request_id", "fields"?, "details"?}}` with a code from `domain_errors.ERROR_CODES`. `fields` and `details` are left out when absent, so `test_middleware.py:103-113` (the exact 500 body) and `test_health_ready.py:65` (the exact 503 body) stay green unchanged. Framework HTTP errors follow owner answer Q2: 400 `bad_request`, 401, 403, 404, 405 `method_not_allowed` as today; any other status keeps its number and gets `bad_request` (4xx) or `internal_error` (5xx, message "Something went wrong.", never the framework's text). The fallback code `"error"` is gone. `PATCH /rubric`'s `ApiError(422, "invalid_rubric", …)` stays (slice 6a converts it). A missing or malformed `X-Church-Id` is also a `no_church_access` 403, because `validate_active_church` treats it as no membership (`tenancy.py:39-41`; clarification 26).

Every current route also declares `responses=error_responses(...)`. Declaring 422 replaces FastAPI's default `HTTPValidationError` (which is not our body) in the OpenAPI schema, so that model disappears from `/openapi.json`; Task 13 snapshots the result.

**Files:**
- Modify: `backend/api/errors.py` (whole file, 83 lines → the version below)
- Modify: `backend/api/deps.py:108-109` (`require_church`'s `raise`)
- Modify: `backend/api/schemas.py` (whole file, 35 lines: `ChurchOut.role` Literal, `Page[T]`, `ItemList[T]`, `ErrorBody` re-export)
- Modify: `backend/api/routes/me.py:3` (add an import after it), `:10` and `:18` (decorators only)
- Modify: `backend/api/routes/rubric.py:7` (import), `:20` and `:25` (decorators only)
- Test: `backend/tests/test_domain_errors.py:1-8` (imports) and appended API section (8 tests); `backend/tests/test_api_app.py:1-11` (imports) and appended section (12 tests)

**Interfaces:**
- Consumes: Task 2's `domain_errors.DomainError`, `RateLimited`, `InvalidInput`, `Conflict`, `NotFound`, `Rejected`, `ERROR_CODES`; `api.middleware.current_request_id() -> Optional[str]`; conftest fixtures `tmp_db`, `make_user`, `make_church`; `repos.memberships.add_membership(user_id, church_id, role)`; `tests.jwt_helpers.make_token`, `ISSUER`, `SIGNING_KEY`.
- Produces (all in `api.errors` unless noted):
  - `ApiError(status: int, code: str, message: str, *, details: Optional[dict[str, Any]] = None)` with attributes `status`, `code`, `message`, `details`; no `headers` (every 429 is a `RateLimited`).
  - `forbidden(message: str = "You don't have access to this church.", *, details: Optional[dict[str, Any]] = None) -> ApiError`; `unauthenticated()`, `auth_unavailable()` and `db_unavailable()` unchanged (Task 12 gives `db_unavailable` its parameters).
  - `_body(code: str, message: str, *, fields: Optional[dict[str, str]] = None, details: Optional[dict[str, Any]] = None) -> dict`; `error_body = _body` (the middleware's two positional arguments still work).
  - `validation_fields(errors: Sequence[dict]) -> dict[str, str]`: location minus a leading `body`/`query`/`header`/`path`, joined by `.`; "Required." (`missing`), "Too long (max N characters)." (`string_too_long`, N = `ctx.max_length`), "Not a valid value." (anything else, `extra_forbidden` included); an empty key (whole body) and `json_invalid` errors are dropped; the first error per key wins.
  - `domain_error_response(exc: DomainError) -> JSONResponse`: status `exc.status`; body `_body(exc.code, exc.message, fields={exc.field: exc.message} if exc.field else None, details=exc.details)`; header `Retry-After: <exc.retry_after_seconds>` for `RateLimited` only. Later users: Task 4 (`run_idempotent`), 1b.
  - `class ErrorDetail(BaseModel)`: `code: str`, `message: str`, `request_id: str`, `fields: Optional[dict[str, str]] = None`, `details: Optional[dict[str, Any]] = None`; `class ErrorBody(BaseModel)`: `error: ErrorDetail`.
  - `error_responses(*statuses: int) -> dict[int, dict[str, Any]]` = `{status: {"model": ErrorBody}}`. Later users: every new route (1b onward).
  - `install_error_handlers(app)` gains the `DomainError` handler (→ `domain_error_response`); the 422 handler adds `fields`; the HTTP handler maps codes per Q2.
  - `api.deps.require_church` raises `forbidden(details={"reason": "no_church_access"})`; `require_admin` unchanged (no `details`).
  - `api.schemas.ChurchOut.role: Literal["owner", "admin", "member"]`; `api.schemas.Page[T]` (`items: list[T]`, `total: int`, `limit: int`, `offset: int`); `api.schemas.ItemList[T]` (`items: list[T]`); `api.schemas.ErrorBody` (re-export). Later users: slices 3, 5a, 6a (`Page`, `ItemList`), Task 16 (`types.ts` reads `ChurchOut` from the generated schema).
  - Route decorators: `GET /me` `error_responses(401, 422, 503)`; `GET /church`, `GET /rubric`, `PATCH /rubric` `error_responses(401, 403, 422, 503)`.

- [ ] **Step 1: Write the failing tests**

In `backend/tests/test_domain_errors.py`, replace the import block (lines 1-8):

```python
"""Domain errors, the F §1.5 code registry, and (Task 3) their API mapping."""
import subprocess
import sys
from pathlib import Path

import pytest

from domain_errors import (
```

with:

```python
"""Domain errors, the F §1.5 code registry, and (Task 3) their API mapping."""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

from api.errors import ApiError, domain_error_response, error_body, forbidden
from api.main import create_app
from domain_errors import (
```

and append at the end of the file (after `test_domain_errors_imports_no_fastapi`, leaving two blank lines):

```python
# --- the API mapping (Task 3; F §1.5, §2.2) ---------------------------------------

HEX32 = re.compile(r"[0-9a-f]{32}")


def _raising(exc):
    """A client for create_app() plus GET /raise, which raises `exc`."""
    app = create_app()
    router = APIRouter()

    @router.get("/raise")
    def raise_it():
        raise exc

    app.include_router(router)
    return TestClient(app)


def test_handler_maps_a_domain_error_to_the_body():
    r = _raising(Conflict("Someone else changed this.")).get("/raise")
    assert r.status_code == 409
    assert r.json() == {"error": {
        "code": "conflict",
        "message": "Someone else changed this.",
        "request_id": r.headers["x-request-id"],
    }}


def test_field_becomes_fields():
    r = _raising(InvalidInput("Church name is required.", field="name")).get("/raise")
    assert r.status_code == 422
    error = r.json()["error"]
    assert (error["code"], error["message"]) == ("invalid_request", "Church name is required.")
    assert error["fields"] == {"name": "Church name is required."}
    assert "details" not in error


def test_details_pass_through():
    exc = Rejected("This invite has expired.", code="invite_rejected", details={"reason": "expired"})
    r = _raising(exc).get("/raise")
    assert r.status_code == 400
    error = r.json()["error"]
    assert (error["code"], error["details"]) == ("invite_rejected", {"reason": "expired"})
    assert "fields" not in error


def test_request_id_is_always_present():
    r = _raising(NotFound("Not found.")).get("/raise", headers={"X-Request-Id": "abcd-1234-efgh"})
    assert r.json()["error"]["request_id"] == "abcd-1234-efgh"
    outside = json.loads(domain_error_response(NotFound("Not found.")).body)   # no request running
    assert HEX32.fullmatch(outside["error"]["request_id"])


def test_rate_limited_is_a_429_with_retry_after_equal_to_details():
    r = _raising(RateLimited("Too many requests. Try again in 30 seconds.", retry_after_seconds=30)).get("/raise")
    assert r.status_code == 429
    error = r.json()["error"]
    assert error["code"] == "rate_limited"
    assert error["details"] == {"retry_after_seconds": 30}
    assert r.headers["retry-after"] == "30"


def test_api_error_carries_details():
    exc = ApiError(503, "db_unavailable", "The database schema is behind this release.",
                   details={"reason": "schema_behind"})
    r = _raising(exc).get("/raise")
    assert r.status_code == 503
    assert r.json()["error"]["details"] == {"reason": "schema_behind"}
    assert forbidden(details={"reason": "no_church_access"}).details == {"reason": "no_church_access"}
    assert forbidden().details is None


def test_body_omits_fields_and_details_when_absent():
    assert set(error_body("not_found", "Not found.")["error"]) == {"code", "message", "request_id"}
    assert set(error_body("not_found", "Not found.", fields={}, details={})["error"]) == {
        "code", "message", "request_id"}
    full = error_body("invalid_request", "The request was not valid.",
                      fields={"name": "Required."}, details={"k": 1})["error"]
    assert (full["fields"], full["details"]) == ({"name": "Required."}, {"k": 1})


def test_domain_error_response_matches_the_handler():
    exc = RateLimited("Slow down.", retry_after_seconds=7)
    via_handler = _raising(exc).get("/raise")
    direct = domain_error_response(exc)
    handler_body, direct_body = via_handler.json(), json.loads(direct.body)
    handler_body["error"].pop("request_id")
    direct_body["error"].pop("request_id")
    assert (direct.status_code, direct_body) == (via_handler.status_code, handler_body)
    assert direct.headers["retry-after"] == via_handler.headers["retry-after"] == "7"
```

In `backend/tests/test_api_app.py`, replace lines 1-11:

```python
import re
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter
from fastapi.testclient import TestClient

from api import settings as settings_mod
from api.main import create_app
from api.settings import _split_origins
```

with:

```python
import re
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

import pytest
from fastapi import APIRouter, Body
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from api import settings as settings_mod
from api.deps import get_verifier
from api.errors import validation_fields
from api.main import create_app
from api.schemas import ChurchOut, ItemList, Page
from api.security import TokenVerifier
from api.settings import _split_origins
from domain_errors import ERROR_CODES
from repos.memberships import add_membership
from tests.jwt_helpers import ISSUER, SIGNING_KEY, make_token
```

and append at the end of the file (after `test_api_does_not_import_streamlit`, leaving two blank lines):

```python
# --- slice 1a: 422 fields, 403 reasons, framework codes, OpenAPI error bodies (F §1.5; S) ---

class _Named(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(max_length=5)


def _app_with_validation_routes():
    """create_app() plus a model body, a free-form object body and a UUID path id."""
    app = create_app()
    router = APIRouter()

    @router.post("/named")
    def named(payload: _Named):
        return {"name": payload.name}

    @router.post("/object")
    def any_object(payload: dict[str, Any] = Body(...)):
        return payload

    @router.get("/items/{item_id}")
    def item(item_id: uuid.UUID):
        return {"id": str(item_id)}

    app.include_router(router)
    return app


@pytest.mark.parametrize("body, fields", [
    ({}, {"name": "Required."}),
    ({"name": "abcdef"}, {"name": "Too long (max 5 characters)."}),
    ({"name": "Grace", "colour": "red"}, {"colour": "Not a valid value."}),
], ids=["missing", "too-long", "extra"])
def test_validation_422_maps_fields(body, fields):
    r = TestClient(_app_with_validation_routes()).post("/named", json=body)
    assert r.status_code == 422
    assert r.json() == {"error": {
        "code": "invalid_request",
        "message": "The request was not valid.",
        "request_id": r.headers["x-request-id"],
        "fields": fields,
    }}


def test_a_whole_body_422_has_no_fields():
    client = TestClient(_app_with_validation_routes())
    not_an_object = client.post("/object", json=["x"])             # location ("body",)
    not_json = client.post("/object", content=b"{", headers={"Content-Type": "application/json"})
    for r in (not_an_object, not_json):
        assert r.status_code == 422
        error = r.json()["error"]
        assert (error["code"], error["message"]) == ("invalid_request", "The request was not valid.")
        assert "fields" not in error


def test_a_path_param_422_strips_path():
    r = TestClient(_app_with_validation_routes()).get("/items/nope")
    assert r.status_code == 422
    assert r.json()["error"]["fields"] == {"item_id": "Not a valid value."}
    # Every source prefix goes; the rest of the location is dotted (F §1.5).
    assert validation_fields([
        {"type": "missing", "loc": ("body", "hymns", "opening", "title")},
        {"type": "string_too_long", "loc": ("query", "q"), "ctx": {"max_length": 3}},
        {"type": "int_parsing", "loc": ("header", "x-count")},
        {"type": "int_parsing", "loc": ("body", "items", 0, "n")},
    ]) == {
        "hymns.opening.title": "Required.",
        "q": "Too long (max 3 characters).",
        "x-count": "Not a valid value.",
        "items.0.n": "Not a valid value.",
    }


@pytest.fixture
def auth_client(tmp_db):
    app = create_app()
    app.dependency_overrides[get_verifier] = lambda: TokenVerifier(
        lambda _token: SIGNING_KEY.public_key(), issuer=ISSUER
    )
    return TestClient(app)


def _auth(email):
    return {"Authorization": f"Bearer {make_token(email=email)}"}


def test_require_church_403_says_no_church_access(auth_client, make_user, make_church):
    make_church(name="Grace", owner_user_id=make_user(email="a@example.com"))
    other = make_church(name="Hope")
    r = auth_client.get("/church", headers={**_auth("a@example.com"), "X-Church-Id": str(other)})
    assert r.status_code == 403
    assert r.json() == {"error": {
        "code": "forbidden",
        "message": "You don't have access to this church.",
        "request_id": r.headers["x-request-id"],
        "details": {"reason": "no_church_access"},
    }}


def test_require_church_without_a_church_header_says_no_church_access(auth_client, make_user, make_church):
    make_church(name="Grace", owner_user_id=make_user(email="a@example.com"))
    missing = auth_client.get("/church", headers=_auth("a@example.com"))
    malformed = auth_client.get("/church", headers={**_auth("a@example.com"), "X-Church-Id": "not-a-uuid"})
    for r in (missing, malformed):
        assert r.status_code == 403
        assert r.json()["error"]["details"] == {"reason": "no_church_access"}


def test_require_admin_403_has_no_reason(auth_client, make_user, make_church):
    church = make_church(name="Grace")
    add_membership(make_user(email="member@example.com"), church, "member")
    r = auth_client.patch("/rubric", json={"prefer_familiar": False},
                          headers={**_auth("member@example.com"), "X-Church-Id": str(church)})
    assert r.status_code == 403
    error = r.json()["error"]
    assert (error["code"], error["message"]) == ("forbidden", "Only church admins can do this.")
    assert "details" not in error


def test_other_http_errors_use_registered_codes():
    app = create_app()
    router = APIRouter()

    @router.get("/status/{status}")
    def fail_with(status: int):
        raise StarletteHTTPException(status_code=status, detail="upstream said: secret" if status >= 500 else None)

    app.include_router(router)
    client = TestClient(app)
    cases = [("GET", "/status/400", 400, "bad_request"), ("POST", "/health", 405, "method_not_allowed"),
             ("GET", "/status/418", 418, "bad_request"), ("GET", "/status/502", 502, "internal_error")]
    for method, path, status, code in cases:
        r = client.request(method, path)
        assert (r.status_code, r.json()["error"]["code"]) == (status, code), path
        assert code in ERROR_CODES
    assert client.get("/status/418").json()["error"]["message"] == "I'm a Teapot"
    server = client.get("/status/502")
    assert server.json()["error"]["message"] == "Something went wrong."
    assert "secret" not in server.text


def test_routes_document_the_error_body():
    schema = create_app().openapi()
    expected = {
        ("/me", "get"): {"401", "422", "503"},
        ("/church", "get"): {"401", "403", "422", "503"},
        ("/rubric", "get"): {"401", "403", "422", "503"},
        ("/rubric", "patch"): {"401", "403", "422", "503"},
    }
    for (path, method), statuses in expected.items():
        responses = schema["paths"][path][method]["responses"]
        assert set(responses) - {"200"} == statuses, (path, method)
        for status in statuses:
            assert responses[status]["content"]["application/json"]["schema"] == {
                "$ref": "#/components/schemas/ErrorBody"}
    schemas = schema["components"]["schemas"]
    assert "HTTPValidationError" not in schemas            # FastAPI's default 422 shape is not ours
    assert set(schemas["ErrorDetail"]["required"]) == {"code", "message", "request_id"}


def test_church_out_role_is_a_literal():
    with pytest.raises(ValidationError):
        ChurchOut(id=uuid.uuid4(), name="Grace", role="pastor")
    role = create_app().openapi()["components"]["schemas"]["ChurchOut"]["properties"]["role"]
    assert role["enum"] == ["owner", "admin", "member"]


def test_page_and_item_list_shapes():
    church = ChurchOut(id=uuid.UUID(int=1), name="Grace", role="owner")
    page = Page[ChurchOut](items=[church], total=3, limit=1, offset=0)
    assert page.model_dump(mode="json") == {
        "items": [{"id": "00000000-0000-0000-0000-000000000001", "name": "Grace", "role": "owner"}],
        "total": 3, "limit": 1, "offset": 0,
    }
    assert ItemList[str](items=["a", "b"]).model_dump() == {"items": ["a", "b"]}
    with pytest.raises(ValidationError):
        Page[ChurchOut](items=[], total=0, limit=50)        # offset is required
```

The existing tests in both files are unchanged. `test_validation_error_uses_error_shape` (`/needs-int?n=abc`) now also gets `fields: {"n": "Not a valid value."}`; it reads only `code`.

- [ ] **Step 2: Run the tests to verify they fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_domain_errors.py 2>&1 | tail -3
.venv/bin/python -m pytest -q backend/tests/test_api_app.py 2>&1 | tail -3
```

Expected: a collection error `ImportError: cannot import name 'domain_error_response' from 'api.errors'` and `1 error`; then a collection error `ImportError: cannot import name 'validation_fields' from 'api.errors'` and `1 error`.

- [ ] **Step 3: Rewrite `backend/api/errors.py`**

Replace the whole file with:

```python
"""One error shape for every API failure (F §1.5):
{"error": {"code", "message", "request_id", "fields"?, "details"?}}.

Code below the API raises domain_errors.DomainError subclasses; one handler
here maps them. ApiError stays for API-layer failures only: authentication and
the /health/ready probe's db_unavailable (F §2.2). Every code comes from
domain_errors.ERROR_CODES.
"""
import logging
import uuid
from typing import Any, Optional, Sequence

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.middleware import current_request_id
from domain_errors import DomainError, RateLimited

logger = logging.getLogger(__name__)

# Framework (Starlette) HTTP errors. Any other status keeps its number and gets
# bad_request (4xx) or internal_error (5xx): every code is in ERROR_CODES.
_HTTP_CODES = {
    400: "bad_request",
    401: "unauthenticated",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
}

# Leading parts of a Pydantic error location that name where the value came from.
_LOCATION_PREFIXES = ("body", "query", "header", "path")


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, *,
                 details: Optional[dict[str, Any]] = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details


def unauthenticated(message: str = "Please sign in.") -> ApiError:
    return ApiError(401, "unauthenticated", message)


def forbidden(message: str = "You don't have access to this church.", *,
              details: Optional[dict[str, Any]] = None) -> ApiError:
    return ApiError(403, "forbidden", message, details=details)


def auth_unavailable() -> ApiError:
    return ApiError(503, "auth_unavailable", "Sign-in is temporarily unavailable. Try again shortly.")


def db_unavailable() -> ApiError:
    """503 from GET /health/ready only (F §1.5 registry; the recorded F §2.2 exception)."""
    return ApiError(503, "db_unavailable", "The database is not reachable.")


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str
    fields: Optional[dict[str, str]] = None
    details: Optional[dict[str, Any]] = None


class ErrorBody(BaseModel):
    """Every error response's body (F §1.5). `fields` and `details` are left out when absent."""

    error: ErrorDetail


def error_responses(*statuses: int) -> dict[int, dict[str, Any]]:
    """`responses=` for a route decorator: each status documents ErrorBody in OpenAPI."""
    return {status: {"model": ErrorBody} for status in statuses}


def _body(code: str, message: str, *, fields: Optional[dict[str, str]] = None,
          details: Optional[dict[str, Any]] = None) -> dict:
    """The uniform error body (F §1.5).

    `request_id` is the X-Request-Id of the request. The uuid4 fallback only
    fires outside RequestIdMiddleware, in the last-resort handler below.
    `fields` and `details` appear only when they are non-empty.
    """
    error: dict[str, Any] = {
        "code": code,
        "message": message,
        "request_id": current_request_id() or uuid.uuid4().hex,
    }
    if fields:
        error["fields"] = fields
    if details:
        error["details"] = details
    return {"error": error}


# Public name for UnhandledErrorMiddleware (api/middleware.py).
error_body = _body


def _field_message(error: dict) -> str:
    kind = error.get("type")
    if kind == "missing":
        return "Required."
    if kind == "string_too_long":
        return f"Too long (max {(error.get('ctx') or {}).get('max_length')} characters)."
    return "Not a valid value."


def validation_fields(errors: Sequence[dict]) -> dict[str, str]:
    """Pydantic errors as {"dotted.location": short message} (F §1.5).

    The leading body/query/header/path part is dropped, so
    ("body", "hymns", "opening", "title") becomes "hymns.opening.title". An
    error about the whole body (location ("body",)) or about unparseable JSON
    names no field and is left out. The first error for a location wins.
    """
    fields: dict[str, str] = {}
    for error in errors:
        if error.get("type") == "json_invalid":      # its location is a character offset
            continue
        location = [str(part) for part in error.get("loc", ())]
        if location and location[0] in _LOCATION_PREFIXES:
            location = location[1:]
        key = ".".join(location)
        if key and key not in fields:
            fields[key] = _field_message(error)
    return fields


def domain_error_response(exc: DomainError) -> JSONResponse:
    """The response for a DomainError: the app's handler, and run_idempotent (api/idempotency.py)."""
    fields = {exc.field: exc.message} if exc.field and exc.status == 422 else None
    headers = {"Retry-After": str(exc.retry_after_seconds)} if isinstance(exc, RateLimited) else None
    return JSONResponse(_body(exc.code, exc.message, fields=fields, details=exc.details),
                        status_code=exc.status, headers=headers)


def _http_code(status: int) -> str:
    if status in _HTTP_CODES:
        return _HTTP_CODES[status]
    return "internal_error" if status >= 500 else "bad_request"


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_request: Request, exc: ApiError):
        return JSONResponse(_body(exc.code, exc.message, details=exc.details), status_code=exc.status)

    @app.exception_handler(DomainError)
    async def _domain_error(_request: Request, exc: DomainError):
        return domain_error_response(exc)

    @app.exception_handler(RequestValidationError)
    async def _invalid(_request: Request, exc: RequestValidationError):
        return JSONResponse(
            _body("invalid_request", "The request was not valid.", fields=validation_fields(exc.errors())),
            status_code=422,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_request: Request, exc: StarletteHTTPException):
        if exc.status_code >= 500:
            message = "Something went wrong."          # never framework or upstream text
        else:
            message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return JSONResponse(_body(_http_code(exc.status_code), message), status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, _exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(_body("internal_error", "Something went wrong."), status_code=500)
```

`ApiError`, `unauthenticated`, `auth_unavailable`, `db_unavailable`, the `ApiError` handler and the last-resort `Exception` handler keep their behavior; `_HTTP_CODES` keeps its five entries (it is now complete per Q2 because `_http_code` covers every other status). `DomainError` needs its own handler: Starlette looks handlers up along the exception's MRO, so every subclass (`RateLimited` included) lands in `_domain_error`.

- [ ] **Step 4: Give `require_church`'s 403 its reason (`backend/api/deps.py`)**

Replace lines 108-109:

```python
    if validated is None:
        raise forbidden()
```

with:

```python
    if validated is None:   # not a member, or a missing or malformed X-Church-Id
        raise forbidden(details={"reason": "no_church_access"})
```

`require_admin` (lines 113-116) is unchanged: a role 403 carries no `reason`, so the client never falls back on it (F §1.5).

- [ ] **Step 5: Rewrite `backend/api/schemas.py`**

Replace the whole file with:

```python
"""Response models (also documented at /docs)."""
import uuid
from typing import Generic, Literal, Optional, TypeVar

from pydantic import BaseModel

from api.errors import ErrorBody  # noqa: F401  (re-exported: every error response's body, F §1.5)

T = TypeVar("T")


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None


class ChurchOut(BaseModel):
    id: uuid.UUID
    name: str
    role: Literal["owner", "admin", "member"]


class MeOut(BaseModel):
    user: UserOut
    churches: list[ChurchOut]


class Page(BaseModel, Generic[T]):
    """One page of a paginated list (F §1.4): the page's items and the full total."""

    items: list[T]
    total: int
    limit: int
    offset: int


class ItemList(BaseModel, Generic[T]):
    """An unpaginated list (F §1.3): always an object, never a bare array."""

    items: list[T]


class RubricModel(BaseModel):
    hymns: dict[str, list[str]]
    prayers: dict[str, list[str]]
    prefer_before_year: int
    prefer_familiar: bool


class RubricOut(BaseModel):
    rubric: RubricModel
    customized: list[str]
```

`ChurchOut.role` is safe to narrow: `memberships.role` has the check constraint `ck_memberships_role` (`role IN ('owner','admin','member')`, `db/models.py:70-72`), and `/me` and `/church` only return membership roles.

- [ ] **Step 6: Document the error body on the four routes**

In `backend/api/routes/me.py`, after line 3 (`from api.deps import ActiveChurch, CurrentUser, get_current_user, require_church`), add:

```python
from api.errors import error_responses
```

Replace line 10:

```python
@router.get("/me", response_model=MeOut)
```

with:

```python
@router.get("/me", response_model=MeOut, responses=error_responses(401, 422, 503))
```

and line 18:

```python
@router.get("/church", response_model=ChurchOut)
```

with:

```python
@router.get("/church", response_model=ChurchOut, responses=error_responses(401, 403, 422, 503))
```

In `backend/api/routes/rubric.py`, replace line 7:

```python
from api.errors import ApiError
```

with:

```python
from api.errors import ApiError, error_responses
```

line 20:

```python
@router.get("/rubric", response_model=RubricOut)
```

with:

```python
@router.get("/rubric", response_model=RubricOut, responses=error_responses(401, 403, 422, 503))
```

and line 25:

```python
@router.patch("/rubric", response_model=RubricOut)
```

with:

```python
@router.patch("/rubric", response_model=RubricOut, responses=error_responses(401, 403, 422, 503))
```

Nothing else in the routes changes.

- [ ] **Step 7: Run the tests and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_domain_errors.py backend/tests/test_api_app.py \
  backend/tests/test_middleware.py backend/tests/test_health_ready.py backend/tests/test_api_me.py \
  backend/tests/test_api_rubric.py 2>&1 | tail -1
.venv/bin/python -m pytest -q backend/tests/test_domain_errors.py backend/tests/test_api_app.py
.venv/bin/python -m pytest -q | tail -1
```

Expected: `112 passed` (the error-shape tests that already existed stay green); then `44 passed` (23 + 21); then `611 passed`.

- [ ] **Step 8: Commit**

```bash
git add backend/api/errors.py backend/api/deps.py backend/api/schemas.py \
        backend/api/routes/me.py backend/api/routes/rubric.py \
        backend/tests/test_domain_errors.py backend/tests/test_api_app.py
git commit -m "API: DomainError handler, 422 fields, details and no_church_access; ErrorBody in OpenAPI (F §1.5, §2.2; owner Q2)

DomainErrors map to the uniform body with their status; RateLimited adds
Retry-After. Pydantic 422s carry short per-field messages. require_church
403s carry details.reason = no_church_access. Framework errors other than
400/401/403/404/405 become bad_request or internal_error, so every code is
in ERROR_CODES. ChurchOut.role is a Literal; Page[T] and ItemList[T] added.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: The idempotency store and `run_idempotent` (F §1.6; S Idempotency)

No route uses it yet: 1b's `POST /churches` is the first. The tests drive it through a throwaway sync route on `create_app()` (so the Task 3 handlers shape every error) and through direct calls with their own `IdempotencyStore`. The store blocks on a per-key `threading.Lock`, so `run_idempotent` is for sync `def` routes only (FastAPI runs them in its threadpool); the module docstring says so.

**Files:**
- Create: `backend/api/idempotency.py`
- Test: `backend/tests/test_idempotency.py` (new, 15 tests)

**Interfaces:**
- Consumes: Task 3's `api.errors.domain_error_response(exc) -> JSONResponse`; Task 2's `domain_errors.DomainError`, `InvalidInput`, `RateLimited`, `Busy`, `Conflict`; `api.main.create_app()`; `tests.conftest.FakeClock` (`now()`, `advance(seconds)`).
- Produces (all in `api.idempotency`):
  - `IDEMPOTENCY_HEADER = "Idempotency-Key"`; `REPLAYED_HEADER = "Idempotent-Replayed"`; `IDEMPOTENCY_TTL_SECONDS = 15 * 60`; `MAX_ENTRIES = 10_000`.
  - `idempotency_key(required: bool = False) -> Callable[..., Optional[uuid.UUID]]`: a dependency factory reading the `Idempotency-Key` header. Absent → `None`, or when `required` raises `InvalidInput("Missing Idempotency-Key header.")`; not a UUID → `InvalidInput("Idempotency-Key must be a UUID.")` (both 422 `invalid_request`, no `fields`). Later users: 1b `POST /churches`, 5a, 5b (`required=True` on `POST /bulletin-emails`), 6b.
  - `class IdempotencyStore(*, clock: Callable[[], float] = time.monotonic, ttl: float = IDEMPOTENCY_TTL_SECONDS, max_entries: int = MAX_ENTRIES)` with attributes `clock`, `ttl`, `max_entries`; `__len__()`; `clear()`. Entries expire lazily (on the next claim of their key, or when room is needed); when full, expired entries go first, then the oldest stored ones (in-flight entries are never evicted).
  - `store: IdempotencyStore` (the process-wide instance); `reset_idempotency_for_tests() -> None` (clears it; 1b adds it to a conftest autouse fixture when a real route uses the store).
  - `run_idempotent(*, user_id: uuid.UUID, route: str, key: Optional[uuid.UUID], payload: BaseModel, status_code: int, call: Callable[[], BaseModel], method: str = "POST", store: Optional[IdempotencyStore] = None) -> Response`. Key = `(user_id, method.upper(), route, key)`; body hash = SHA-256 of `json.dumps(payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))`. `key=None` → just runs `call` (no idempotency). First request → runs `call`, returns `JSONResponse(result.model_dump(mode="json"), status_code=status_code)` and stores it; stores `DomainError` 4xx responses (built by `domain_error_response`) except `RateLimited`; drops the entry for `RateLimited`, any 5xx `DomainError` and any other exception (which propagates). Repeat with the same hash → stored status and body plus `Idempotent-Replayed: true`; with another hash → raises `InvalidInput("This request was already sent with different details.", code="idempotency_mismatch")`. A concurrent repeat waits on the entry's lock and then replays; if the first request's entry was dropped meanwhile, it runs the call itself. Slice 5b adds a `store_error` keyword (F §1.6).

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_idempotency.py`:

```python
"""The Idempotency-Key store and run_idempotent (F §1.6; S Idempotency).

POST /things is a throwaway sync route on create_app(); the user id comes from
an X-Test-User header so these tests need no token or database.
"""
import threading
import time
import uuid
from typing import Optional

import pytest
from fastapi import APIRouter, Depends, Header
from fastapi.testclient import TestClient
from pydantic import BaseModel

from api import idempotency
from api.idempotency import (
    IDEMPOTENCY_TTL_SECONDS,
    MAX_ENTRIES,
    REPLAYED_HEADER,
    IdempotencyStore,
    idempotency_key,
    reset_idempotency_for_tests,
    run_idempotent,
)
from api.main import create_app
from domain_errors import Busy, Conflict, DomainError, RateLimited
from tests.conftest import FakeClock

USER_A = uuid.UUID(int=1)
USER_B = uuid.UUID(int=2)
KEY = "6f1c2a52-3a8e-4c3e-9d57-2f0b1f6f1a11"


class _In(BaseModel):
    name: str


class _Tags(BaseModel):
    tags: dict[str, int]


class _Out(BaseModel):
    id: int
    name: str


@pytest.fixture(autouse=True)
def _fresh_store():
    reset_idempotency_for_tests()
    yield
    reset_idempotency_for_tests()


def _client(outcome=None, *, required=False):
    """create_app() plus POST /things. The call records each name it sees in
    `calls`, runs `outcome(<call number>)` (which may raise), then returns
    {"id": <call number>, "name": …}. Returns (client, calls)."""
    calls = []
    app = create_app()
    router = APIRouter()

    @router.post("/things", status_code=201, response_model=_Out)
    def create_thing(
        payload: _In,
        key: Optional[uuid.UUID] = Depends(idempotency_key(required=required)),
        x_test_user: str = Header(),
    ):
        def call():
            calls.append(payload.name)
            if outcome is not None:
                outcome(len(calls))
            return _Out(id=len(calls), name=payload.name)

        return run_idempotent(user_id=uuid.UUID(x_test_user), route="/things", key=key,
                              payload=payload, status_code=201, call=call)

    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False), calls


def _post(client, name="Grace", *, key=KEY, user=USER_A):
    headers = {"X-Test-User": str(user)}
    if key is not None:
        headers["Idempotency-Key"] = key
    return client.post("/things", json={"name": name}, headers=headers)


def _direct(store, calls, **overrides):
    """run_idempotent outside HTTP, with a call that counts itself in `calls`."""

    def call():
        calls.append(1)
        return _Out(id=len(calls), name="Grace")

    kwargs = dict(user_id=USER_A, route="/things", key=uuid.UUID(KEY), payload=_In(name="Grace"),
                  status_code=201, call=call, store=store)
    kwargs.update(overrides)
    return run_idempotent(**kwargs)


def test_replay_returns_the_stored_status_and_body_with_replayed_header():
    client, calls = _client()
    first, again = _post(client), _post(client)
    assert (first.status_code, first.json()) == (201, {"id": 1, "name": "Grace"})
    assert REPLAYED_HEADER.lower() not in first.headers
    assert (again.status_code, again.json()) == (201, {"id": 1, "name": "Grace"})
    assert again.headers[REPLAYED_HEADER] == "true"
    assert calls == ["Grace"]


def test_a_4xx_domain_error_is_stored_and_replayed():
    def conflict(_n):
        raise Conflict("That name is taken.")

    client, calls = _client(conflict)
    first, again = _post(client), _post(client)
    assert first.status_code == again.status_code == 409
    assert again.json() == first.json()          # the stored body, its request_id included
    assert again.json()["error"]["code"] == "conflict"
    assert again.headers[REPLAYED_HEADER] == "true"
    assert len(calls) == 1


def test_a_5xx_is_not_stored_and_re_executes():
    def busy_once(n):
        if n == 1:
            raise Busy("The AI is busy. Try again in a moment.", code="ai_busy")

    client, calls = _client(busy_once)
    first = _post(client)
    assert (first.status_code, first.json()["error"]["code"]) == (503, "ai_busy")
    again = _post(client)
    assert (again.status_code, again.json()) == (201, {"id": 2, "name": "Grace"})
    assert REPLAYED_HEADER.lower() not in again.headers
    assert len(calls) == 2


def test_rate_limited_is_returned_with_retry_after_not_stored_and_re_executes():
    def limited(_n):
        raise RateLimited("You've created 5 churches in the last 24 hours. Try again later.",
                          retry_after_seconds=90)

    client, calls = _client(limited)
    first, again = _post(client), _post(client)
    for r in (first, again):
        assert r.status_code == 429
        assert r.headers["retry-after"] == "90"
        assert r.json()["error"]["details"] == {"retry_after_seconds": 90}
        assert REPLAYED_HEADER.lower() not in r.headers
    assert len(calls) == 2
    assert len(idempotency.store) == 0


def test_a_different_body_is_idempotency_mismatch():
    client, calls = _client()
    assert _post(client, "Grace").status_code == 201
    r = _post(client, "Hope")
    assert r.status_code == 422
    error = r.json()["error"]
    assert (error["code"], error["message"]) == (
        "idempotency_mismatch", "This request was already sent with different details.")
    assert calls == ["Grace"]


def test_keys_are_scoped_per_user():
    client, calls = _client()
    a, b = _post(client, user=USER_A), _post(client, user=USER_B)
    assert (a.json()["id"], b.json()["id"]) == (1, 2)
    assert REPLAYED_HEADER.lower() not in b.headers
    assert len(calls) == 2


def test_keys_are_scoped_per_route_and_method():
    store, calls = IdempotencyStore(), []
    _direct(store, calls, route="/things")
    _direct(store, calls, route="/other")
    _direct(store, calls, route="/things", method="PUT")
    replay = _direct(store, calls, route="/things", method="post")    # methods compare upper-cased
    assert len(calls) == 3
    assert replay.headers[REPLAYED_HEADER] == "true"
    assert len(store) == 3


def test_concurrent_same_key_requests_run_the_call_once():
    store, calls, responses = IdempotencyStore(), [], []
    barrier = threading.Barrier(2)

    def slow_call():
        calls.append(1)
        time.sleep(0.2)          # long enough that an unlocked second request would run it too
        return _Out(id=len(calls), name="Grace")

    def request():
        barrier.wait(timeout=5)
        responses.append(_direct(store, calls, call=slow_call))

    threads = [threading.Thread(target=request) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    assert len(calls) == 1
    assert sorted(r.headers.get(REPLAYED_HEADER, "") for r in responses) == ["", "true"]
    assert responses[0].body == responses[1].body


def test_entries_expire_after_15_minutes():
    assert IDEMPOTENCY_TTL_SECONDS == 15 * 60
    clock = FakeClock()
    store, calls = IdempotencyStore(clock=clock.now), []
    _direct(store, calls)
    clock.advance(IDEMPOTENCY_TTL_SECONDS - 1)
    assert _direct(store, calls).headers[REPLAYED_HEADER] == "true"
    clock.advance(1)
    assert REPLAYED_HEADER not in _direct(store, calls).headers
    assert len(calls) == 2


def test_malformed_key_is_422_with_exact_message():
    client, calls = _client()
    r = _post(client, key="not-a-uuid")
    assert r.status_code == 422
    assert r.json() == {"error": {
        "code": "invalid_request",
        "message": "Idempotency-Key must be a UUID.",
        "request_id": r.headers["x-request-id"],
    }}
    assert calls == []


def test_required_key_missing_is_422():
    client, calls = _client(required=True)
    r = _post(client, key=None)
    assert r.status_code == 422
    error = r.json()["error"]
    assert (error["code"], error["message"]) == ("invalid_request", "Missing Idempotency-Key header.")
    assert calls == []
    assert _post(client).status_code == 201          # with a key it runs


def test_no_key_means_no_idempotency():
    client, calls = _client()
    a, b = _post(client, key=None), _post(client, key=None)
    assert (a.json()["id"], b.json()["id"]) == (1, 2)
    assert REPLAYED_HEADER.lower() not in b.headers
    assert len(idempotency.store) == 0


def test_store_is_bounded_to_10000_entries():
    assert MAX_ENTRIES == 10_000
    assert IdempotencyStore().max_entries == MAX_ENTRIES
    store, calls = IdempotencyStore(max_entries=3), []
    keys = [uuid.uuid4() for _ in range(4)]
    for key in keys:
        _direct(store, calls, key=key)
    assert len(store) == 3
    assert _direct(store, calls, key=keys[3]).headers[REPLAYED_HEADER] == "true"   # newest kept
    assert REPLAYED_HEADER not in _direct(store, calls, key=keys[0]).headers       # oldest evicted
    assert len(calls) == 5
    assert len(store) == 3


def test_non_domain_exception_drops_the_entry_and_is_a_500():
    def boom_once(n):
        if n == 1:
            raise RuntimeError("database went away")

    client, calls = _client(boom_once)
    first = _post(client)
    assert (first.status_code, first.json()["error"]["code"]) == (500, "internal_error")
    assert "database went away" not in first.text
    assert len(idempotency.store) == 0
    again = _post(client)
    assert (again.status_code, again.json()) == (201, {"id": 2, "name": "Grace"})


def test_body_hash_ignores_key_order():
    store, calls = IdempotencyStore(), []
    _direct(store, calls, payload=_Tags(tags={"a": 1, "b": 2}))
    again = _direct(store, calls, payload=_Tags(tags={"b": 2, "a": 1}))
    assert again.headers[REPLAYED_HEADER] == "true"
    assert len(calls) == 1
    with pytest.raises(DomainError) as caught:
        _direct(store, calls, payload=_Tags(tags={"a": 1, "b": 3}))
    assert caught.value.code == "idempotency_mismatch"
```

A replayed error body keeps the first response's `request_id` (it is the stored body, F §1.6 "the stored status and body"); the replay's `X-Request-Id` header is its own.

- [ ] **Step 2: Run the tests to verify they fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_idempotency.py 2>&1 | tail -3
```

Expected: a collection error `ModuleNotFoundError: No module named 'api.idempotency'` and `1 error`.

- [ ] **Step 3: Create `backend/api/idempotency.py`**

```python
"""Idempotency-Key replays for POST routes (F §1.6; slice 1).

A route that accepts the header reads it with `Depends(idempotency_key())` and
wraps its usecase call in run_idempotent(). The first request with a key runs
the call and stores the response; a repeat with the same key and the same body
gets the stored status and body back with `Idempotent-Replayed: true`; a repeat
with a different body is 422 `idempotency_mismatch`.

What is stored: 2xx responses and DomainError 4xx responses, except
RateLimited (its 429 is returned, the entry dropped, so the same key runs again
after Retry-After). Never a 5xx: a 5xx DomainError drops the entry, and any
other exception drops it and propagates (the app's handlers turn it into a 500).

The store is in memory, keyed by (user_id, method, route template, key), with a
15-minute TTL and at most 10 000 entries. That is enough for one uvicorn
worker; if --workers ever exceeds 1, move it to a Postgres table first (F §1.6).
A request waits on a per-key threading.Lock while an identical one is running,
so run_idempotent must only be called from sync `def` routes (they run in the
threadpool); calling it from an `async def` route would block the event loop.
"""
import hashlib
import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable, Optional

from fastapi import Header
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from api.errors import domain_error_response
from domain_errors import DomainError, InvalidInput, RateLimited

IDEMPOTENCY_HEADER = "Idempotency-Key"
REPLAYED_HEADER = "Idempotent-Replayed"
IDEMPOTENCY_TTL_SECONDS = 15 * 60
MAX_ENTRIES = 10_000

_Key = tuple[uuid.UUID, str, str, uuid.UUID]


def idempotency_key(required: bool = False) -> Callable[..., Optional[uuid.UUID]]:
    """A dependency that reads the Idempotency-Key header as a UUID.

    Absent → None (no idempotency), or 422 "Missing Idempotency-Key header."
    when `required` (5b's POST /bulletin-emails). Not a UUID → 422
    "Idempotency-Key must be a UUID.". Both are `invalid_request` without `fields`.
    """

    def dependency(
        idempotency_key: Optional[str] = Header(default=None, alias=IDEMPOTENCY_HEADER),
    ) -> Optional[uuid.UUID]:
        if idempotency_key is None:
            if required:
                raise InvalidInput("Missing Idempotency-Key header.")
            return None
        try:
            return uuid.UUID(idempotency_key.strip())
        except ValueError:
            raise InvalidInput("Idempotency-Key must be a UUID.") from None

    return dependency


@dataclass
class _Entry:
    """One key's slot. `lock` is held while the first request runs its call."""

    body_hash: str
    lock: threading.Lock = field(default_factory=threading.Lock)
    status: Optional[int] = None          # set once a response is stored
    body: bytes = b""
    expires_at: float = 0.0
    dropped: bool = False                  # removed from the store; waiters must look again


class IdempotencyStore:
    """In-memory idempotency entries (F §1.6): TTL, lazy expiry, bounded size."""

    def __init__(self, *, clock: Callable[[], float] = time.monotonic,
                 ttl: float = IDEMPOTENCY_TTL_SECONDS, max_entries: int = MAX_ENTRIES):
        self.clock = clock
        self.ttl = ttl
        self.max_entries = max_entries
        self._entries: dict[_Key, _Entry] = {}
        self._lock = threading.Lock()

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)

    def clear(self) -> None:
        with self._lock:
            for entry in self._entries.values():
                entry.dropped = True
            self._entries.clear()

    def claim(self, key: _Key, body_hash: str) -> _Entry:
        """The live entry for `key`, or a new one (expired entries are replaced)."""
        with self._lock:
            now = self.clock()
            entry = self._entries.get(key)
            if entry is not None and entry.status is not None and entry.expires_at <= now:
                self._remove(key)
                entry = None
            if entry is None:
                self._make_room(now)
                entry = _Entry(body_hash=body_hash)
                self._entries[key] = entry
            return entry

    def save(self, entry: _Entry, status: int, body: bytes) -> None:
        with self._lock:
            entry.status = status
            entry.body = body
            entry.expires_at = self.clock() + self.ttl

    def drop(self, key: _Key, entry: _Entry) -> None:
        with self._lock:
            if self._entries.get(key) is entry:
                self._remove(key)
            entry.dropped = True

    def _remove(self, key: _Key) -> None:
        self._entries.pop(key).dropped = True

    def _make_room(self, now: float) -> None:
        """Called under the lock before an insert: expired entries go first, then the oldest stored ones."""
        if len(self._entries) < self.max_entries:
            return
        for key in [k for k, e in self._entries.items() if e.status is not None and e.expires_at <= now]:
            self._remove(key)
        for key in [k for k, e in self._entries.items() if e.status is not None]:
            if len(self._entries) < self.max_entries:
                break
            self._remove(key)               # dicts keep insertion order: oldest first


store = IdempotencyStore()


def reset_idempotency_for_tests() -> None:
    """Forget every stored response in the process-wide store."""
    _process_store().clear()


def _process_store() -> IdempotencyStore:
    # run_idempotent's `store` keyword shadows the module attribute of the same name.
    return globals()["store"]


def _body_hash(payload: BaseModel) -> str:
    canonical = json.dumps(payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def run_idempotent(
    *,
    user_id: uuid.UUID,
    route: str,
    key: Optional[uuid.UUID],
    payload: BaseModel,
    status_code: int,
    call: Callable[[], BaseModel],
    method: str = "POST",
    store: Optional[IdempotencyStore] = None,
) -> Response:
    """Run `call` once per (user, method, route, key) and replay its response.

    `route` is the route template (e.g. "/churches"), `payload` the parsed
    request body (its SHA-256 over sorted-key JSON is compared on a repeat),
    `status_code` the success status. Blocks on a threading.Lock while an
    identical request is running: call it only from sync `def` routes.
    Slice 5b adds a `store_error` keyword (F §1.6).
    """
    if key is None:
        return _success(call(), status_code)
    target = store if store is not None else _process_store()
    scope = (user_id, method.upper(), route, key)
    body_hash = _body_hash(payload)
    while True:
        entry = target.claim(scope, body_hash)
        with entry.lock:
            if entry.dropped:                  # the first request failed while we waited
                continue
            if entry.body_hash != body_hash:
                raise InvalidInput("This request was already sent with different details.",
                                   code="idempotency_mismatch")
            if entry.status is not None:
                return Response(entry.body, status_code=entry.status, media_type="application/json",
                                headers={REPLAYED_HEADER: "true"})
            try:
                response = _success(call(), status_code)
            except DomainError as exc:
                response = domain_error_response(exc)
                if 400 <= exc.status < 500 and not isinstance(exc, RateLimited):
                    target.save(entry, response.status_code, bytes(response.body))
                else:
                    target.drop(scope, entry)
                return response
            except BaseException:
                target.drop(scope, entry)
                raise
            target.save(entry, response.status_code, bytes(response.body))
            return response


def _success(result: BaseModel, status_code: int) -> JSONResponse:
    return JSONResponse(result.model_dump(mode="json"), status_code=status_code)
```

Why the `dropped` flag: a waiter holds a reference to the entry it claimed. If the first request fails (5xx, `RateLimited` or an exception), the entry leaves the dict and is marked dropped; the waiter then loops, claims a fresh entry and runs the call itself, instead of storing into an entry nobody can find. The body-hash check comes after that, so a waiter with a different body gets `idempotency_mismatch` only against an entry that is still live.

- [ ] **Step 4: Run the tests, the concurrency test ten times, and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_idempotency.py
for i in 1 2 3 4 5 6 7 8 9 10; do .venv/bin/python -m pytest -q backend/tests/test_idempotency.py -k concurrent 2>&1 | tail -1; done | grep -c "1 passed"
.venv/bin/python -m pytest -q | tail -1
```

Expected: `15 passed`; then `10`; then `626 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/api/idempotency.py backend/tests/test_idempotency.py
git commit -m "API: in-memory Idempotency-Key store and run_idempotent (F §1.6)

Keyed by (user, method, route template, key) with a 15-minute TTL and at most
10 000 entries. Stores 2xx and DomainError 4xx responses, never RateLimited or
a 5xx; a replay carries Idempotent-Replayed: true, a different body is 422
idempotency_mismatch, and a concurrent repeat waits on a per-key lock (sync
routes only).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Alembic configuration, `env.py` and `db/schema_check.py` part 1 (F §3.1, §3.3; S Alembic setup; clarifications 11, 21, 23, 24)

Alembic arrives without any revision: `alembic.ini` with `%(here)s` paths and the standard logging sections, the `env.py` described in Global Constraints (URL rule, stderr `Database:` line, logging switch, one transaction with the Postgres timeouts inside it), the revision template, and the first half of `db/schema_check.py`. `command.current` runs `env.py` online on a database without any revision (checked on Alembic 1.20.0: it works with an empty or even a missing `migrations/versions/`), so the `env.py` tests run before Task 6 adds `0001_baseline`. Clarification 21 is settled here: on Alembic 1.20.0 and SQLAlchemy 2.1.1, `schema_diff` on a `create_all` SQLite database is `[]` (no `Uuid`/`JSON`/`DateTime(timezone=True)` false positives), so `schema_check` needs no custom type comparator.

**Files:**
- Create: `backend/alembic.ini`, `backend/migrations/env.py`, `backend/migrations/script.py.mako`, `backend/db/schema_check.py` (first part: `ALEMBIC_INI`, `alembic_config`, `include_object`, `schema_diff`)
- Test: `backend/tests/test_schema_check.py` (new, 5 tests), `backend/tests/test_migrations.py` (new, 4 tests), `backend/tests/test_foundation_setup.py` (append 1 test after Task 1's additions)

**Interfaces:**
- Consumes: `alembic` 1.20 (installed by Task 1); `db.engine.Base`, `db.engine._database_url() -> str`, `db.engine._normalize_url(url: str) -> str`; `db.models` (registers the 11 tables); `api.startup.describe_database(url: sqlalchemy.engine.URL) -> str` (`api/startup.py:27`; `api/__init__.py` is empty and `api.startup` imports only `api.settings` and SQLAlchemy); fixture `tmp_db` (`conftest.py:27-53`); Task 1's autouse `_no_network`.
- Produces:
  - `db.schema_check.ALEMBIC_INI: Path` = `Path(__file__).resolve().parents[1] / "alembic.ini"`;
  - `db.schema_check.alembic_config(*, url: str | None = None, configure_logger: bool = True) -> alembic.config.Config` (`url` → `cfg.attributes["url"]` only when given; `cfg.attributes["configure_logger"]` always set). Later users: Task 6 (`pg_db`), Tasks 6-10 tests, Task 10 (`schema_drift.py`), Task 11 (`run_startup_checks`, head via `ScriptDirectory.from_config(alembic_config(configure_logger=False))`);
  - `db.schema_check.include_object(obj, name, type_, reflected, compare_to) -> bool` (False only for a reflected table the models do not declare). Later users: `env.py`, `schema_diff`;
  - `db.schema_check.schema_diff(conn: sqlalchemy.engine.Connection) -> list` (`compare_metadata` with `compare_type=True`, `compare_server_default=False`, `include_object`; does not run `env.py`). Later users: Tasks 6-10, `schema_drift.py`;
  - `backend/migrations/env.py` behavior exactly as Global Constraints; module names used by later tasks: none (Alembic loads it);
  - test helpers in `backend/tests/test_migrations.py`: `_alembic(url: str, *args, **kw)` (runs `getattr(alembic.command, args[0])(alembic_config(url=url, configure_logger=False), *args[1:], **kw)`; never reads `DATABASE_URL`) and fixture `sqlite_url(tmp_path) -> str`. Later users: Tasks 6-9.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_schema_check.py`:

```python
"""db.schema_check: the Alembic config, include_object and schema_diff (F §3.1, §2.6)."""
import subprocess
import sys
from pathlib import Path

from alembic.script import ScriptDirectory
from sqlalchemy import Column, Integer, MetaData, Table

from db.engine import Base
from db.schema_check import ALEMBIC_INI, alembic_config, include_object, schema_diff

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"


def test_alembic_config_finds_the_scripts_from_the_repo_root(monkeypatch):
    monkeypatch.chdir(ROOT)
    script = ScriptDirectory.from_config(alembic_config(configure_logger=False))
    assert Path(script.dir).resolve() == (BACKEND / "migrations").resolve()
    assert (Path(script.dir) / "env.py").is_file()


def test_alembic_config_finds_the_scripts_from_backend():
    code = ("from alembic.script import ScriptDirectory; from db.schema_check import alembic_config; "
            "print(ScriptDirectory.from_config(alembic_config(configure_logger=False)).dir)")
    result = subprocess.run([sys.executable, "-c", code], cwd=BACKEND, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert Path(result.stdout.strip()).resolve() == (BACKEND / "migrations").resolve()


def test_alembic_config_sets_the_url_and_logger_attributes():
    assert ALEMBIC_INI == BACKEND.resolve() / "alembic.ini"
    cfg = alembic_config(url="sqlite:///x.db", configure_logger=False)
    assert cfg.config_file_name == str(ALEMBIC_INI)
    assert cfg.attributes == {"url": "sqlite:///x.db", "configure_logger": False}
    assert alembic_config().attributes == {"configure_logger": True}


def test_include_object_skips_reflected_tables_not_in_the_models(tmp_db):
    users = Base.metadata.tables["users"]
    assert include_object(None, "alembic_version", "table", True, None) is False
    assert include_object(users, "users", "table", True, users) is True
    assert include_object(users, "users", "table", False, None) is True      # missing: reported
    assert include_object(None, "ix_legacy", "index", True, None) is True
    Table("legacy_notes", MetaData(), Column("id", Integer, primary_key=True)).create(tmp_db)
    Base.metadata.tables["contacts"].drop(tmp_db)
    with tmp_db.connect() as conn:
        diff = schema_diff(conn)
    assert sorted((entry[0], entry[1].name) for entry in diff) == [
        ("add_index", "ix_contacts_church_id"), ("add_table", "contacts")]


def test_schema_diff_is_empty_for_a_create_all_database(tmp_db):
    with tmp_db.connect() as conn:
        assert schema_diff(conn) == []
```

Create `backend/tests/test_migrations.py`:

```python
"""Alembic migrations: env.py, the revisions, offline SQL (F §3.1-§3.3; slice 1 spec)."""
import logging.config

import pytest
from alembic import command

from db.schema_check import ALEMBIC_INI, alembic_config


def _alembic(url: str, *args, **kw):
    """Run one Alembic command in-process on `url`; never reads DATABASE_URL, never touches logging."""
    return getattr(command, args[0])(alembic_config(url=url, configure_logger=False), *args[1:], **kw)


@pytest.fixture
def sqlite_url(tmp_path):
    return f"sqlite:///{tmp_path / 'migrations.db'}"


# --- env.py -------------------------------------------------------------------

@pytest.mark.parametrize("configure_logger", [True, False])
def test_env_py_configures_logging_only_when_asked(monkeypatch, sqlite_url, configure_logger):
    calls = []
    monkeypatch.setattr(logging.config, "fileConfig", lambda *a, **kw: calls.append((a, kw)))
    command.current(alembic_config(url=sqlite_url, configure_logger=configure_logger))
    expected = [((str(ALEMBIC_INI),), {"disable_existing_loggers": False})] if configure_logger else []
    assert calls == expected


def test_env_py_uses_the_configured_url_not_database_url(monkeypatch, capsys, sqlite_url, tmp_path):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@pooler.invalid:5432/postgres")
    _alembic(sqlite_url, "current")
    err = capsys.readouterr().err
    assert "Database: dialect=sqlite" in err
    assert "pooler.invalid" not in err
    assert (tmp_path / "migrations.db").exists()


def test_env_py_prints_the_database_line_to_stderr_only(capsys, sqlite_url, tmp_path):
    _alembic(sqlite_url, "current")
    out, err = capsys.readouterr()
    assert f"Database: dialect=sqlite driver=pysqlite host=- database={tmp_path / 'migrations.db'}\n" in err
    assert "Database:" not in out
```

Append to the end of `backend/tests/test_foundation_setup.py` (after Task 1's tests; it uses the module-level `configparser` import Task 1 added):

```python


# --- slice 1a: Alembic (F §3.1; slice 1 spec, "Alembic setup") ---

def test_alembic_ini_uses_here_paths_and_has_logging_sections():
    ini = configparser.RawConfigParser()
    assert ini.read(ROOT / "backend" / "alembic.ini", encoding="utf-8")
    assert ini.get("alembic", "script_location") == "%(here)s/migrations"
    assert ini.get("alembic", "prepend_sys_path") == "%(here)s"
    assert ini.get("alembic", "path_separator") == "os"
    assert not ini.has_option("alembic", "sqlalchemy.url")    # env.py owns the URL
    for section in ("loggers", "handlers", "formatters", "logger_root", "logger_sqlalchemy",
                    "logger_alembic", "handler_console", "formatter_generic"):
        assert ini.has_section(section), section
    assert ini.get("handler_console", "args") == "(sys.stderr,)"
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_schema_check.py 2>&1 | tail -3
.venv/bin/python -m pytest -q backend/tests/test_migrations.py 2>&1 | tail -3
.venv/bin/python -m pytest -q backend/tests/test_foundation_setup.py 2>&1 | tail -3
```

Expected: the first two each stop with a collection error, `ModuleNotFoundError: No module named 'db.schema_check'`, and `1 error`. The third: `1 failed, 13 passed` (11 at `7978a5e` + Task 1's 2); `test_alembic_ini_uses_here_paths_and_has_logging_sections` fails with `AssertionError: assert []` (`read()` found no `backend/alembic.ini`).

- [ ] **Step 3: Create `backend/alembic.ini`**

`path_separator = os` is the Alembic 1.16+ setting; without it Alembic warns that it falls back to splitting `prepend_sys_path` on spaces, commas and colons. The formatter's single `%` is correct: `logging.config.fileConfig` reads `format` raw, and Alembic only interpolates the `[alembic]` values it reads (hence `%%(rev)s` there).

```ini
# Alembic configuration (F §3.1; slice 1 spec, "Alembic setup").
#
# %(here)s is this file's directory (backend/), so the scripts are found from
# backend/ (Railway's pre-deploy command, the CLI) and from the repo root
# (pytest). Code builds its Config with db.schema_check.alembic_config(), from
# this file's absolute path. There is no sqlalchemy.url: migrations/env.py
# takes the URL from the caller or from DATABASE_URL.

[alembic]
script_location = %(here)s/migrations
prepend_sys_path = %(here)s
path_separator = os
# New revision files are named after their id, e.g. 0005_short_slug.py:
#   alembic revision -m "..." --rev-id 0005_short_slug
file_template = %%(rev)s

# Logging for the alembic command line. In-process callers (tests, the API's
# startup check) pass configure_logger=False, so env.py leaves the app's
# logging alone.
[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARNING
handlers = console
qualname =

[logger_sqlalchemy]
level = WARNING
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 4: Create `backend/migrations/script.py.mako`** (the template `alembic revision` renders; hand-written revisions follow the same layout)

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 5: Create `backend/db/schema_check.py`** (Tasks 10 and 11 append to it)

```python
"""Schema checks shared by migrations/env.py, the API's startup check, the
drift script and the tests (F §3.1, §2.6; slice 1 spec, "Modules added").

- alembic_config: the Alembic Config, built from alembic.ini's absolute
  path (never the working directory). `url` reaches env.py through
  cfg.attributes["url"]; configure_logger=False keeps env.py from
  reconfiguring logging (every in-process caller passes it).
- include_object: autogenerate never looks at reflected tables that the
  models do not declare (alembic_version, anything else in the schema), so
  it never proposes dropping them.
- schema_diff: compare_metadata between a live connection and the models,
  with the same options env.py uses. It does not run env.py.

Imports no FastAPI and nothing from api/ (layering, F §2.2).
"""
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy.engine import Connection

from db.engine import Base

ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"


def alembic_config(*, url: str | None = None, configure_logger: bool = True) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    if url is not None:
        cfg.attributes["url"] = url
    cfg.attributes["configure_logger"] = configure_logger
    return cfg


def include_object(obj, name, type_, reflected, compare_to) -> bool:
    """False only for a table that exists in the database but not in the models."""
    return not (type_ == "table" and reflected and compare_to is None)


def schema_diff(conn: Connection) -> list:
    """Differences between the database behind `conn` and the models ([] = none)."""
    from db import models  # noqa: F401  (registers every table on Base.metadata)

    context = MigrationContext.configure(conn, opts={
        "compare_type": True,
        "compare_server_default": False,
        "include_object": include_object,
    })
    return compare_metadata(context, Base.metadata)
```

- [ ] **Step 6: Create `backend/migrations/env.py`**

```python
"""Alembic environment (F §3.1; slice 1 spec, "Alembic setup").

URL: config.attributes["url"] when the caller set one (tests, the pg_db
fixture), else DATABASE_URL through db.engine._database_url() (the alembic
command line, Railway's pre-deploy command); always through
db.engine._normalize_url. No load_dotenv: a laptop run exports DATABASE_URL.

The "Database: ..." line goes to stderr, so `alembic upgrade ... --sql >
upgrade.sql` stays pure SQL. Logging comes from alembic.ini only when
config.attributes["configure_logger"] is not False.

Everything runs in ONE transaction (the default; no transaction_per_migration),
so a RAISE in 0003_lockdown rolls back 0002 to 0004 as well. On Postgres the
two timeouts run first, through context.execute inside that transaction.
Never call connection.execute() before context.configure(): SQLAlchemy 2.1
autobegins, Alembic then treats the transaction as external and does not
commit it, and closing the connection rolls every migration back while the
command still exits 0. Offline (--sql) the same code prints BEGIN;, the two
SET lines, the revisions and COMMIT;.
"""
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from api.startup import describe_database
from db.engine import _database_url, _normalize_url
from db.models import Base
from db.schema_check import include_object

config = context.config

if config.config_file_name and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata

POSTGRES_TIMEOUTS = ("SET LOCAL lock_timeout = '5s'", "SET LOCAL statement_timeout = '60s'")


def _configure_options(dialect_name: str) -> dict:
    return {
        "target_metadata": target_metadata,
        "include_object": include_object,
        "compare_type": True,
        "compare_server_default": False,
        # Batch mode affects autogenerate rendering only; hand-written ALTERs
        # on SQLite use op.batch_alter_table themselves (0004).
        "render_as_batch": dialect_name == "sqlite",
    }


def _run_in_one_transaction(dialect_name: str) -> None:
    with context.begin_transaction():
        if dialect_name == "postgresql":
            for statement in POSTGRES_TIMEOUTS:
                context.execute(statement)
        context.run_migrations()


def run_migrations_offline(url: str) -> None:
    dialect_name = make_url(url).get_backend_name()
    context.configure(
        url=url,
        literal_binds=True,
        # Named paramstyle: a literal % (0003's RAISE text) is not doubled.
        dialect_opts={"paramstyle": "named"},
        **_configure_options(dialect_name),
    )
    _run_in_one_transaction(dialect_name)


def run_migrations_online(url: str) -> None:
    engine = create_engine(url, poolclass=NullPool)
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, **_configure_options(connection.dialect.name))
            _run_in_one_transaction(connection.dialect.name)
    finally:
        engine.dispose()


database_url = _normalize_url(config.attributes.get("url") or _database_url())
print(f"Database: {describe_database(make_url(database_url))}", file=sys.stderr)

if context.is_offline_mode():
    run_migrations_offline(database_url)
else:
    run_migrations_online(database_url)
```

Do not create `backend/migrations/versions/` yet: git does not track an empty directory, and Alembic runs without it (Task 6 creates it with `0001_baseline.py`).

- [ ] **Step 7: Run the tests and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_schema_check.py backend/tests/test_migrations.py backend/tests/test_foundation_setup.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
```

Expected: `23 passed` (5 + 4 + 14), then `636 passed`.

If `test_schema_diff_is_empty_for_a_create_all_database` fails with `modify_type` entries (it did not on Alembic 1.20.0 / SQLAlchemy 2.1.1; clarification 21), stop and report the entries: the fix is a `compare_type` callable in `schema_check` and `env.py`, recorded as a clarification, not a change to the models.

Caplog check (critique 3): `backend/tests/test_startup.py` runs after `test_migrations.py` and `test_schema_check.py` in the suite; it stays green because every in-process Alembic call passes `configure_logger=False`, and the one test that asks for logging replaces `logging.config.fileConfig` with a spy.

- [ ] **Step 8: Commit**

```bash
git add backend/alembic.ini backend/migrations/env.py backend/migrations/script.py.mako \
        backend/db/schema_check.py backend/tests/test_schema_check.py \
        backend/tests/test_migrations.py backend/tests/test_foundation_setup.py
git commit -m "Alembic: alembic.ini with %(here)s paths, env.py and schema_check (F §3.1, S Alembic setup)

env.py takes the URL from the caller (cfg.attributes[\"url\"]) or DATABASE_URL,
prints the Database: line to stderr so --sql output stays pure SQL, configures
logging only when asked, and runs every revision in one transaction with the
Postgres lock and statement timeouts inside it. schema_check builds the Config
from alembic.ini's absolute path and diffs a live database against the models.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: `0001_baseline` (F §3.2 item 1; S Revisions; AC1, AC18)

The first revision: the 11 tables of `db/models.py`, written out by hand. It includes `text_year`/`hymnal_count` on `hymns` and `hymn_catalog` and `ix_hymns_church_hymnal` (the 2026-09-26 amendments), plus every named constraint and index. Unique, primary-key and foreign-key constraints stay unnamed, so a fresh database gets the names production already has (`users_email_key`, `invites_code_key`, `*_pkey`, `*_fkey`). Fresh databases (CI, new local dev) run it. Production is stamped at it (T26). `pg_db` now builds its database with Alembic instead of `init_db()`.

Checked on Alembic 1.20.0 / SQLAlchemy 2.1.1 with Task 5's files applied:
- the revision's offline Postgres DDL is statement-for-statement identical to `create_all`'s (Step 4 re-proves it: 19 statements, 11 tables + 8 indexes);
- `upgrade head`, `check`, `downgrade base` and `upgrade head` all run on SQLite;
- autogenerate on SQLite does report a lost `ON DELETE`, but never a lost `CHECK` (mutation run: removing `ck_memberships_role` from the revision fails only `test_baseline_keeps_on_delete_rules_and_check_constraints`);
- a stand-in `0004` that rebuilds `invites` with `op.batch_alter_table` (Task 9's shape) keeps all 7 tests green, including the ON DELETE/CHECK test at head and `downgrade base`.

**Files:**
- Create: `backend/migrations/versions/0001_baseline.py` (git tracks `backend/migrations/versions/` from here on)
- Modify: `backend/tests/conftest.py` (inside Task 1's `pg_db`: one docstring paragraph; the deferred imports and the `init_db()` line)
- Test: `backend/tests/test_migrations.py` (replace Task 5's import block; append the `0001_baseline` section, 7 tests)

**Interfaces:**
- Consumes: `db.schema_check.ALEMBIC_INI`, `alembic_config(*, url: str | None = None, configure_logger: bool = True) -> Config`, `schema_diff(conn: Connection) -> list` (Task 5); `test_migrations.py`'s `_alembic(url: str, *args, **kw)` and fixture `sqlite_url` (Task 5); `migrations/env.py` (Task 5): URL from `cfg.attributes["url"]`, `Database: …` on stderr, one transaction with `SET LOCAL lock_timeout = '5s'` / `SET LOCAL statement_timeout = '60s'` first on Postgres, named paramstyle offline; `db.engine.Base`, `db.models`; fixture `pg_db` and `tests.pg_helpers.require_local_test_url(url: str) -> str` (Task 1); `db.reset_engine_for_tests(url: str) -> Engine`.
- Produces:
  - revision `0001_baseline` (`down_revision = None`) in `backend/migrations/versions/0001_baseline.py`: head until Task 7, whose `0002_reconcile` sets `down_revision = "0001_baseline"`. Files are named after their revision id (`NNNN_short_slug.py`), and `test_every_revision_defines_downgrade` enforces this for Tasks 7-9;
  - in `backend/tests/test_migrations.py`: `BASELINE_TABLES: set[str]` (the 11 table names), `_script() -> alembic.script.ScriptDirectory`, `_connection(url: str)` (context manager yielding a `Connection` on its own `NullPool` engine, disposed on exit), and module imports `io`, `contextmanager`, `Path`, `ScriptDirectory`, `CheckConstraint`, `Integer`, `create_engine`, `inspect`, `NullPool`, `Base`, `schema_diff`. Later users: Tasks 7-9 (their sections append to this file);
  - `pg_db` runs `command.upgrade(alembic_config(url=url, configure_logger=False), "head")` before truncating, every time (a no-op at head), so its database always has 0003's RLS and 0004's columns. Later users: Task 11 (`test_rls_check_names_tables_without_rls`), Task 14 (`test_concurrent_first_requests_on_postgres_both_succeed_with_one_id`).

- [ ] **Step 1: Write the failing tests**

In `backend/tests/test_migrations.py`, replace Task 5's import block:

```python
import logging.config

import pytest
from alembic import command

from db.schema_check import ALEMBIC_INI, alembic_config
```

with:

```python
import io
import logging.config
from contextlib import contextmanager
from pathlib import Path

import pytest
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import CheckConstraint, Integer, create_engine, inspect
from sqlalchemy.pool import NullPool

from db import models  # noqa: F401  (registers every table on Base.metadata)
from db.engine import Base
from db.schema_check import ALEMBIC_INI, alembic_config, schema_diff
```

Then append to the end of the file (after `test_env_py_prints_the_database_line_to_stderr_only`):

```python


# --- 0001_baseline (Task 6) ------------------------------------------------------

BASELINE_TABLES = {
    "users", "churches", "memberships", "invites", "hymn_catalog", "hymns",
    "services", "hymn_usage", "contacts", "gmail_tokens", "oauth_states",
}


def _script() -> ScriptDirectory:
    return ScriptDirectory.from_config(alembic_config(configure_logger=False))


@contextmanager
def _connection(url: str):
    """A short-lived connection of its own (NullPool), closed and disposed on exit."""
    engine = create_engine(url, poolclass=NullPool)
    try:
        with engine.connect() as conn:
            yield conn
    finally:
        engine.dispose()


def test_upgrade_head_on_empty_sqlite_matches_the_models(sqlite_url):
    _alembic(sqlite_url, "upgrade", "head")
    with _connection(sqlite_url) as conn:
        assert schema_diff(conn) == []
    _alembic(sqlite_url, "check")   # AC1: raises AutogenerateDiffsDetected on any difference


def test_downgrade_base_then_upgrade_head(sqlite_url):
    _alembic(sqlite_url, "upgrade", "head")
    _alembic(sqlite_url, "downgrade", "base")
    with _connection(sqlite_url) as conn:
        assert inspect(conn).get_table_names() == ["alembic_version"]
        assert conn.exec_driver_sql("SELECT count(*) FROM alembic_version").scalar() == 0
    _alembic(sqlite_url, "upgrade", "head")
    with _connection(sqlite_url) as conn:
        assert schema_diff(conn) == []
        versions = conn.exec_driver_sql("SELECT version_num FROM alembic_version").scalars().all()
    assert versions == [_script().get_current_head()]


def test_every_revision_defines_downgrade():
    revisions = list(_script().walk_revisions())
    assert revisions
    for rev in revisions:
        assert callable(getattr(rev.module, "downgrade", None)), rev.revision
        assert Path(rev.path).name == f"{rev.revision}.py"   # NNNN_short_slug.py, id = file name


def test_there_is_a_single_head():
    script = _script()
    assert len(script.get_heads()) == 1
    assert script.get_bases() == ["0001_baseline"]
    assert not [rev.revision for rev in script.walk_revisions()
                if rev.is_branch_point or rev.is_merge_point]


def test_baseline_creates_the_eleven_tables_with_hymn_facts_columns(sqlite_url):
    _alembic(sqlite_url, "upgrade", "0001_baseline")
    with _connection(sqlite_url) as conn:
        insp = inspect(conn)
        assert set(insp.get_table_names()) == BASELINE_TABLES | {"alembic_version"}
        for table in ("hymns", "hymn_catalog"):
            columns = {column["name"]: column for column in insp.get_columns(table)}
            for name in ("text_year", "hymnal_count"):
                assert isinstance(columns[name]["type"], Integer), (table, name)
                assert columns[name]["nullable"] is True, (table, name)
        assert {ix["name"]: ix["column_names"] for ix in insp.get_indexes("hymns")} == {
            "ix_hymns_church_id": ["church_id"],
            "ix_hymns_church_hymnal": ["church_id", "hymnal"],
            "ix_hymns_church_number": ["church_id", "number"],
        }


def _on_delete_rules_in_the_models() -> dict:
    return {
        (table.name, tuple(fk.column_keys), fk.referred_table.name): (fk.ondelete or "").upper() or None
        for table in Base.metadata.sorted_tables
        for fk in table.foreign_key_constraints
    }


def _check_constraints_in_the_models() -> dict:
    return {
        table.name: sorted((c.name, str(c.sqltext)) for c in table.constraints
                           if isinstance(c, CheckConstraint))
        for table in Base.metadata.sorted_tables
    }


def test_baseline_keeps_on_delete_rules_and_check_constraints(sqlite_url):
    """ON DELETE rules and CHECK constraints equal the models' after `upgrade head`.

    Autogenerate never compares CHECK constraints, and whether it compares ON
    DELETE depends on the Alembic version and the dialect, so schema_diff alone
    cannot be trusted with either. Runs at head, so it keeps holding when a later
    revision rebuilds a table (0004's batch mode on SQLite)."""
    _alembic(sqlite_url, "upgrade", "head")
    expected_rules = _on_delete_rules_in_the_models()
    expected_checks = _check_constraints_in_the_models()
    assert expected_rules[("memberships", ("church_id",), "churches")] == "CASCADE"
    assert expected_rules[("services", ("created_by",), "users")] == "SET NULL"
    assert expected_checks["memberships"] == [("ck_memberships_role", "role IN ('owner','admin','member')")]
    with _connection(sqlite_url) as conn:
        insp = inspect(conn)
        rules = {
            (table, tuple(fk["constrained_columns"]), fk["referred_table"]):
                (fk["options"].get("ondelete") or "").upper() or None
            for table in Base.metadata.tables
            for fk in insp.get_foreign_keys(table)
        }
        checks = {
            table: sorted((c["name"], c["sqltext"]) for c in insp.get_check_constraints(table))
            for table in Base.metadata.tables
        }
    assert rules == expected_rules
    assert checks == expected_checks


def test_offline_sql_wraps_timeouts_in_one_transaction(capsys):
    """`upgrade --sql` on Postgres opens no connection (port 1 has no server)."""
    cfg = alembic_config(url="postgresql://u:p@localhost:1/x", configure_logger=False)
    cfg.output_buffer = buffer = io.StringIO()
    command.upgrade(cfg, "head", sql=True)
    sql = buffer.getvalue()
    lines = [line for line in sql.splitlines() if line.strip() and not line.startswith("--")]
    assert lines[:3] == ["BEGIN;", "SET LOCAL lock_timeout = '5s';", "SET LOCAL statement_timeout = '60s';"]
    assert lines[-1] == "COMMIT;"
    assert sql.count("BEGIN;") == 1
    assert sql.count("COMMIT;") == 1
    assert "CREATE TABLE users (" in sql
    assert "Database:" not in sql
    assert "Database: dialect=postgresql driver=psycopg2 host=localhost database=x" in capsys.readouterr().err
```

`test_baseline_creates_the_eleven_tables_with_hymn_facts_columns` pins the revision itself (`upgrade 0001_baseline`), so it still holds after Tasks 7-9. The other SQLite tests run at head, so they keep checking the whole chain against the models as revisions land. `test_offline_sql_wraps_timeouts_in_one_transaction` needs no server: offline mode only builds the psycopg2 dialect (installed), and port 1 is never dialled.

- [ ] **Step 2: Run the tests to verify they fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_migrations.py 2>&1 | tail -3
```

Expected: `7 failed, 4 passed` (Task 5's four env.py tests pass). There is no `backend/migrations/versions/` yet, so:
- `test_upgrade_head_on_empty_sqlite_matches_the_models` and `test_downgrade_base_then_upgrade_head` fail with `AssertionError: assert [('add_table'...` and "Left contains 19 more items" (upgrade head is a no-op, so the 11 tables and 8 indexes are missing);
- `test_every_revision_defines_downgrade` fails with `assert []`;
- `test_there_is_a_single_head` fails with `assert 0 == 1`;
- `test_baseline_creates_the_eleven_tables_with_hymn_facts_columns` fails with `alembic.util.exc.CommandError: Can't locate revision identified by '0001_baseline'`;
- `test_baseline_keeps_on_delete_rules_and_check_constraints` fails with `sqlalchemy.exc.NoSuchTableError: users`;
- `test_offline_sql_wraps_timeouts_in_one_transaction` fails with `assert 'CREATE TABLE users (' in "BEGIN;\n\nSET LOCAL lock_timeout = '5s';\n\nSET LOCAL statement_timeout = '60s';\n\nCOMMIT;\n\n"`. Task 5's env.py already wraps even an empty run in one transaction.

- [ ] **Step 3: Create `backend/migrations/versions/0001_baseline.py`**

Constraint order inside each `create_table` follows `create_all`'s, so Step 4's DDL comparison is exact. Indexes are plain `op.create_index` calls: batch mode is only needed for ALTERs on SQLite.

```python
"""Baseline: the 11 tables of db/models.py as of slice 1a.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-09-26

Runs only on fresh databases (CI, new local dev). Production is stamped at
this revision, not migrated (backend/migrations/README.md, step 4).

Written out by hand, never imported from db.models, so later model changes
cannot change what this revision creates. It reproduces the models exactly:
- unique, primary-key and foreign-key constraints stay unnamed, as
  create_all made them in production (users_email_key, invites_code_key,
  *_pkey, *_fkey on Postgres); no naming convention;
- the named constraints and indexes keep their model names;
- ON DELETE CASCADE for church content and memberships, SET NULL for the
  created_by authorship columns;
- the nullable INTEGER text_year and hymnal_count columns on hymns and
  hymn_catalog, and ix_hymns_church_hymnal (0002_reconcile adds these to an
  older database that lacks them);
- no server defaults (the models use Python-side defaults). Production's
  DEFAULT 'GG2013' on hymnal (from the deleted migrate_add_hymnal.py) stays
  where it is; env.py compares no server defaults.
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("google_sub", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("picture", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("google_sub"),
    )
    op.create_table(
        "churches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("timezone", sa.String(), nullable=False),
        sa.Column("settings", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "memberships",
        sa.Column("church_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role IN ('owner','admin','member')", name="ck_memberships_role"),
        sa.ForeignKeyConstraint(["church_id"], ["churches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("church_id", "user_id"),
    )
    op.create_index("ix_memberships_user_id", "memberships", ["user_id"])
    op.create_table(
        "invites",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("church_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("church_id", "email", name="uq_invites_church_email"),
        sa.ForeignKeyConstraint(["church_id"], ["churches.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("code"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_invites_church_id", "invites", ["church_id"])
    op.create_table(
        "hymn_catalog",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("hymnal", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("number", sa.Integer(), nullable=True),
        sa.Column("scripture_refs", sa.Text(), nullable=True),
        sa.Column("theme", sa.Text(), nullable=True),
        sa.Column("hymnary_link", sa.Text(), nullable=True),
        sa.Column("audio_url", sa.Text(), nullable=True),
        sa.Column("text_year", sa.Integer(), nullable=True),
        sa.Column("hymnal_count", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "hymns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("church_id", sa.Uuid(), nullable=False),
        sa.Column("hymnal", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("number", sa.Integer(), nullable=True),
        sa.Column("scripture_refs", sa.Text(), nullable=True),
        sa.Column("theme", sa.Text(), nullable=True),
        sa.Column("hymnary_link", sa.Text(), nullable=True),
        sa.Column("audio_url", sa.Text(), nullable=True),
        sa.Column("text_year", sa.Integer(), nullable=True),
        sa.Column("hymnal_count", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["church_id"], ["churches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hymns_church_id", "hymns", ["church_id"])
    op.create_index("ix_hymns_church_hymnal", "hymns", ["church_id", "hymnal"])
    op.create_index("ix_hymns_church_number", "hymns", ["church_id", "number"])
    op.create_table(
        "services",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("church_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("service_date_iso", sa.String(), nullable=True),
        sa.Column("service_date_display", sa.String(), nullable=True),
        sa.Column("occasion", sa.String(), nullable=True),
        sa.Column("scriptures", sa.JSON(), nullable=True),
        sa.Column("hymns", sa.JSON(), nullable=True),
        sa.Column("liturgy", sa.JSON(), nullable=True),
        sa.Column("sermon_title", sa.String(), nullable=True),
        sa.Column("selected_ot_ref", sa.String(), nullable=True),
        sa.Column("selected_nt_ref", sa.String(), nullable=True),
        sa.Column("include_communion", sa.Boolean(), nullable=False),
        sa.Column("saved_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["church_id"], ["churches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_services_church_saved_at", "services", ["church_id", "saved_at"])
    op.create_table(
        "hymn_usage",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("church_id", sa.Uuid(), nullable=False),
        sa.Column("date_iso", sa.String(), nullable=True),
        sa.Column("hymn_number", sa.Integer(), nullable=True),
        sa.Column("hymn_title", sa.String(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "church_id", "date_iso", "hymn_number", "hymn_title", name="uq_hymn_usage_dedupe"
        ),
        sa.ForeignKeyConstraint(["church_id"], ["churches.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_hymn_usage_church_date", "hymn_usage", ["church_id", "date_iso"])
    op.create_table(
        "contacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("church_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["church_id"], ["churches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_contacts_church_id", "contacts", ["church_id"])
    op.create_table(
        "gmail_tokens",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=False),
        sa.Column("google_email", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "oauth_states",
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("state"),
    )


def downgrade() -> None:
    # Reverse creation order; dropping a table drops its indexes with it.
    for table in ("oauth_states", "gmail_tokens", "contacts", "hymn_usage", "services",
                  "hymns", "hymn_catalog", "invites", "memberships", "churches", "users"):
        op.drop_table(table)
```

- [ ] **Step 4: Run the tests, prove the Postgres DDL, smoke the command line**

```bash
.venv/bin/python -m pytest -q backend/tests/test_migrations.py backend/tests/test_schema_check.py 2>&1 | tail -1
```

Expected: `16 passed` (11 + 5).

One-off proof (not a test: after Task 9 the models' `invites` differs from `0001_baseline` on purpose) that the revision's Postgres DDL is exactly `create_all`'s. It renders offline, so no server is needed:

```bash
(cd backend && ../.venv/bin/python - <<'EOF'
import io
import re

from alembic import command
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

from db import models  # noqa: F401
from db.engine import Base
from db.schema_check import alembic_config

cfg = alembic_config(url="postgresql://u:p@localhost:1/x", configure_logger=False)
cfg.output_buffer = buf = io.StringIO()
command.upgrade(cfg, "0001_baseline", sql=True)
norm = lambda s: " ".join(s.split())
revision = {norm(s) for s in re.findall(r"^(CREATE (?:TABLE|INDEX) .*?);$", buf.getvalue(), re.S | re.M)
            if "alembic_version" not in s}
pg = postgresql.dialect()
models_ddl = {norm(str(CreateTable(t).compile(dialect=pg))) for t in Base.metadata.sorted_tables}
models_ddl |= {norm(str(CreateIndex(ix).compile(dialect=pg)))
               for t in Base.metadata.sorted_tables for ix in t.indexes}
print("statements:", len(revision), len(models_ddl))
print("only in the models:", sorted(models_ddl - revision))
print("only in 0001:", sorted(revision - models_ddl))
EOF
)
```

Expected: `Database: dialect=postgresql driver=psycopg2 host=localhost database=x` (stderr), then `statements: 19 19`, `only in the models: []`, `only in 0001: []`. Any other line means the revision differs from the models. Fix the revision, never the models, and rerun Steps 2-4.

Command-line smoke, on a throwaway SQLite file (`DATABASE_URL` is exported inside the subshell only; env.py never calls `load_dotenv`):

```bash
D=$(mktemp -d) && (cd backend && export DATABASE_URL="sqlite:///$D/t6.db" && ../.venv/bin/alembic upgrade head && ../.venv/bin/alembic current && ../.venv/bin/alembic check && ../.venv/bin/alembic downgrade base && ../.venv/bin/alembic history); rm -rf "$D"
```

Expected, on stdout: `0001_baseline (head)`, `No new upgrade operations detected.`, `<base> -> 0001_baseline (head), Baseline: the 11 tables of db/models.py as of slice 1a.`. On stderr: a `Database: dialect=sqlite driver=pysqlite host=- database=…/t6.db` line before each of `upgrade`, `current`, `check` and `downgrade` (not `history`, which does not run env.py), `Running upgrade  -> 0001_baseline, Baseline: …` and `Running downgrade 0001_baseline -> , Baseline: …`.

- [ ] **Step 5: Build `pg_db`'s database with Alembic**

In `backend/tests/conftest.py`, inside `pg_db` (Task 1), replace the docstring paragraph:

```python
    Skips unless TEST_DATABASE_URL is set (only the backend-postgres CI job
    sets it). The URL must be a local, throwaway Postgres
    (tests.pg_helpers.require_local_test_url). Every table except
    alembic_version is truncated before the test, so each test starts empty.
```

with:

```python
    Skips unless TEST_DATABASE_URL is set (only the backend-postgres CI job
    sets it). The URL must be a local, throwaway Postgres
    (tests.pg_helpers.require_local_test_url). The database is migrated to
    head with Alembic (so 0003_lockdown's RLS is on), then every table except
    alembic_version is truncated, so each test starts empty.
```

and replace:

```python
    from sqlalchemy import inspect, text

    from db import init_db, reset_engine_for_tests
    from tests.pg_helpers import require_local_test_url

    engine = reset_engine_for_tests(require_local_test_url(url))
    init_db()   # the tables, when a run starts from an empty database
```

with:

```python
    from alembic import command
    from sqlalchemy import inspect, text

    from db import reset_engine_for_tests
    from db.schema_check import alembic_config
    from tests.pg_helpers import require_local_test_url

    engine = reset_engine_for_tests(require_local_test_url(url))
    # Built the way every database is now built: Alembic to head (a no-op
    # when CI's alembic cycle already got there). A local Postgres whose
    # tables came from init_db() needs `alembic stamp head` once (tables made
    # before slice 1a: `alembic stamp 0001_baseline`, then this upgrade).
    command.upgrade(alembic_config(url=url, configure_logger=False), "head")
```

The rest of `pg_db` (the truncate, `yield`, `dispose`) stays. `init_db` is no longer imported here. It stays in `db` for Streamlit, the CLIs, `tmp_db` and `pg_smoke.py`. The upgrade runs every time rather than only when `alembic_version` is missing, so a local Postgres left behind head also reaches head; at head it only opens a connection and reads `alembic_version`. `pg_db` has no local run (no Postgres on this machine). Its first run is Task 14's draft-PR checkpoint, where CI's alembic cycle has already reached head.

- [ ] **Step 6: Run the suite**

```bash
.venv/bin/python -m pytest -q | tail -1
```

Expected: `643 passed` (636 + 7).

- [ ] **Step 7: Commit**

```bash
git add backend/migrations/versions/0001_baseline.py backend/tests/test_migrations.py backend/tests/conftest.py
git commit -m "Alembic: 0001_baseline creates the 11 tables exactly as the models (F §3.2, S Revisions)

Written by hand: unnamed unique, primary-key and foreign-key constraints (the
names production already has), the named constraints and indexes including
ix_hymns_church_hymnal, and text_year/hymnal_count on hymns and hymn_catalog.
Its Postgres DDL is identical to create_all's. Tests cover upgrade, check,
downgrade base, a single linear head, ON DELETE rules and CHECK constraints
(which autogenerate cannot be trusted with), and the offline SQL's single
transaction with the Postgres timeouts. pg_db now migrates with Alembic.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: `0002_reconcile`; delete the one-off schema scripts; README hymn-facts step (F §3.2 item 3; S "Revisions", amendment 2026-09-26; AC18)

`0002_reconcile` holds only guarded adds, so it changes nothing on production (stamped at `0001_baseline`, T26) and nothing on a fresh database (0001 created everything). What it fixes: a local database made by the old `create_all` and stamped at `0001_baseline` that lacks `ix_hymns_church_hymnal` (which `migrate_add_hymnal.py` never created) or PR #4's `text_year`/`hymnal_count`. On Postgres the column adds are `ALTER TABLE … ADD COLUMN IF NOT EXISTS …`, which also renders in the runbook's offline `--sql` review (step 5). On SQLite, which has no `IF NOT EXISTS` for columns, an inspector check decides, the pattern of `migrate_add_hymn_facts.py:32-39`. Its downgrade is a no-op on purpose (S: every object is also 0001's, and 0001's downgrade drops it). With 0002 in place the two one-off schema scripts and their test are deleted, and README step 1 and the backfill docstring point at Alembic. `backfill_hymn_facts.py` and `hymnary_facts.py` stay: they fill data, not schema.

On Postgres both statements lock their table even when they change nothing. T5's `SET LOCAL lock_timeout = '5s'` bounds that wait, and a timeout rolls the whole upgrade back (one transaction), so a busy table fails the pre-deploy step instead of stalling it.

Checked on Alembic 1.20.0, SQLAlchemy 2.1.1 and SQLite 3.53.1, with T5's `env.py` and a baseline standing in for T6's: all five new tests fail without `0002_reconcile.py` for the reasons in Step 2 and pass with it. `alembic upgrade head`, `check`, `downgrade base`, `upgrade head`, `check` runs clean. Offline, `0001_baseline:head` on Postgres renders exactly the lines quoted in Step 3.

**Files:**
- Create: `backend/migrations/versions/0002_reconcile.py`
- Delete: `backend/migrate_add_hymnal.py`, `backend/migrate_add_hymn_facts.py`, `backend/tests/test_migrate_hymn_facts.py` (4 tests)
- Modify: `README.md:155-160` (step 1 of "### Service rubric: hymn year and familiarity"), `backend/backfill_hymn_facts.py:5` (docstring)
- Test: `backend/tests/test_migrations.py` (append the Task 7 block at the end, after T6's tests: 5 tests), `backend/tests/test_foundation_setup.py` (append 2 tests after T5's `test_alembic_ini_uses_here_paths_and_has_logging_sections`)

**Interfaces:**
- Consumes:
  - T5: `db.schema_check.alembic_config(*, url: str | None = None, configure_logger: bool = True) -> alembic.config.Config`, `db.schema_check.schema_diff(conn: Connection) -> list`; in `test_migrations.py`, `_alembic(url: str, *args, **kw)`, fixture `sqlite_url(tmp_path) -> str` and the top-level imports `from alembic import command`, `from db.schema_check import ALEMBIC_INI, alembic_config`; `env.py` offline mode (named paramstyle, `BEGIN;`, the two `SET … timeout` lines, `COMMIT;`, the `Database:` line on stderr, never in the SQL).
  - T6: revision `0001_baseline` (`revision = "0001_baseline"`, `down_revision = None`), which creates the 11 tables including `ix_hymns_church_hymnal` on `hymns (church_id, hymnal)` and nullable INTEGER `text_year`/`hymnal_count` on `hymns` and `hymn_catalog`, and whose downgrade drops them. T6's `test_downgrade_base_then_upgrade_head`, `test_every_revision_defines_downgrade`, `test_there_is_a_single_head`, `test_upgrade_head_on_empty_sqlite_matches_the_models` and `test_offline_sql_wraps_timeouts_in_one_transaction` now run through 0002 as well and must stay green unchanged.
  - T1: autouse `_no_network` (the offline test never connects).
- Produces:
  - Revision `0002_reconcile` (`down_revision = "0001_baseline"`), head until T8. Later users: T8 (`0003_lockdown.down_revision = "0002_reconcile"`; its idempotence test upgrades to `0002_reconcile`), T10 (revision ids), T24 (README step 5 quotes the rendered lines below), T26 (runbook step 5), T27 (the deploy log line `Running upgrade 0001_baseline -> 0002_reconcile`).
  - Offline SQL for `0001_baseline:head` on Postgres, in this order: `-- Running upgrade 0001_baseline -> 0002_reconcile`, `CREATE INDEX IF NOT EXISTS ix_hymns_church_hymnal ON hymns (church_id, hymnal);`, `ALTER TABLE hymns ADD COLUMN IF NOT EXISTS text_year INTEGER;`, `ALTER TABLE hymns ADD COLUMN IF NOT EXISTS hymnal_count INTEGER;`, `ALTER TABLE hymn_catalog ADD COLUMN IF NOT EXISTS text_year INTEGER;`, `ALTER TABLE hymn_catalog ADD COLUMN IF NOT EXISTS hymnal_count INTEGER;`, `UPDATE alembic_version SET version_num='0002_reconcile' WHERE alembic_version.version_num = '0001_baseline';`.
  - Module constants in the revision file: `HYMN_FACT_TABLES = ("hymns", "hymn_catalog")`, `HYMN_FACT_COLUMNS = ("text_year", "hymnal_count")` (nothing imports them).
  - Module-level names in `test_migrations.py` that later appends (T8, T9) must not reuse: `RECONCILE_TABLES`, `RECONCILE_COLUMNS`, `_execute_on(url: str, *statements: str) -> None`, `_legacy_database(url: str, *, without_hymn_facts: bool = False, without_hymnal_index: bool = False) -> None`, `_tables_snapshot(url: str) -> dict`, `_snapshot_columns(snapshot: dict, table: str) -> set[str]`, `_models_diff(url: str) -> list`.

- [ ] **Step 1: Write the failing tests**

Append to the end of `backend/tests/test_migrations.py` (after T6's tests). The block brings its own imports and uses only names T5 and T6 do not define, so their tests are undisturbed. The legacy databases are built with Alembic (`upgrade 0001_baseline`, then drop what an older database lacked, then drop `alembic_version`), not with `Base.metadata.create_all`: from T9 on the models also have 0004's `invites` columns, and a `create_all` database stamped at `0001_baseline` would make 0004 add them a second time.

```python


# --- Task 7: 0002_reconcile (F §3.2 item 3; S amendment 2026-09-26; AC18) ------
import io

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import NullPool

from db.schema_check import schema_diff

RECONCILE_TABLES = ("hymns", "hymn_catalog")
RECONCILE_COLUMNS = ("text_year", "hymnal_count")


def _execute_on(url: str, *statements: str) -> None:
    engine = create_engine(url, poolclass=NullPool)
    try:
        with engine.begin() as conn:
            for statement in statements:
                conn.execute(text(statement))
    finally:
        engine.dispose()


def _legacy_database(url: str, *, without_hymn_facts: bool = False,
                     without_hymnal_index: bool = False) -> None:
    """A database the old create_all made (no alembic_version table): the 0001
    schema, minus what an older one lacked (PR #4's columns, or the index
    migrate_add_hymnal.py never created)."""
    _alembic(url, "upgrade", "0001_baseline")
    statements = ["DROP TABLE alembic_version"]
    if without_hymnal_index:
        statements.append("DROP INDEX ix_hymns_church_hymnal")
    if without_hymn_facts:
        statements += [f"ALTER TABLE {table} DROP COLUMN {column}"
                       for table in RECONCILE_TABLES for column in RECONCILE_COLUMNS]
    _execute_on(url, *statements)


def _tables_snapshot(url: str) -> dict:
    """{table: (sorted (column, type, nullable), sorted (index, columns))}."""
    engine = create_engine(url, poolclass=NullPool)
    try:
        with engine.connect() as conn:
            insp = inspect(conn)
            return {
                table: (
                    sorted((c["name"], str(c["type"]), c["nullable"]) for c in insp.get_columns(table)),
                    sorted((i["name"], tuple(i["column_names"])) for i in insp.get_indexes(table)),
                )
                for table in insp.get_table_names()
            }
    finally:
        engine.dispose()


def _snapshot_columns(snapshot: dict, table: str) -> set[str]:
    return {name for name, _type, _nullable in snapshot[table][0]}


def _models_diff(url: str) -> list:
    engine = create_engine(url, poolclass=NullPool)
    try:
        with engine.connect() as conn:
            return schema_diff(conn)
    finally:
        engine.dispose()


def test_a_pre_pr4_database_stamped_at_baseline_gains_hymn_facts(sqlite_url):
    _legacy_database(sqlite_url, without_hymn_facts=True)
    before = _tables_snapshot(sqlite_url)
    for table in RECONCILE_TABLES:
        assert not set(RECONCILE_COLUMNS) & _snapshot_columns(before, table)

    _alembic(sqlite_url, "stamp", "0001_baseline")
    _alembic(sqlite_url, "upgrade", "head")

    after = _tables_snapshot(sqlite_url)
    for table in RECONCILE_TABLES:
        columns = {name: (type_, nullable) for name, type_, nullable in after[table][0]}
        assert columns["text_year"] == ("INTEGER", True)
        assert columns["hymnal_count"] == ("INTEGER", True)
    assert _models_diff(sqlite_url) == []


def test_upgrade_head_twice_changes_nothing(sqlite_url):
    _legacy_database(sqlite_url, without_hymn_facts=True, without_hymnal_index=True)
    _alembic(sqlite_url, "stamp", "0001_baseline")
    _alembic(sqlite_url, "upgrade", "head")
    first = _tables_snapshot(sqlite_url)

    _alembic(sqlite_url, "upgrade", "head")              # already at head: nothing runs
    assert _tables_snapshot(sqlite_url) == first

    # 0002 itself a second time, as on production, which already has everything.
    _alembic(sqlite_url, "stamp", "0001_baseline")
    _alembic(sqlite_url, "upgrade", "0002_reconcile")
    assert _tables_snapshot(sqlite_url) == first


def test_on_a_fresh_database_0002_adds_nothing(sqlite_url):
    _alembic(sqlite_url, "upgrade", "0001_baseline")
    baseline = _tables_snapshot(sqlite_url)
    for table in RECONCILE_TABLES:                       # 0001 already made them
        assert set(RECONCILE_COLUMNS) <= _snapshot_columns(baseline, table)
    assert ("ix_hymns_church_hymnal", ("church_id", "hymnal")) in baseline["hymns"][1]

    _alembic(sqlite_url, "upgrade", "0002_reconcile")

    assert _tables_snapshot(sqlite_url) == baseline


def test_a_stamped_database_missing_the_hymnal_index_gets_it(sqlite_url):
    _legacy_database(sqlite_url, without_hymnal_index=True)
    assert "ix_hymns_church_hymnal" not in {name for name, _cols in _tables_snapshot(sqlite_url)["hymns"][1]}

    _alembic(sqlite_url, "stamp", "0001_baseline")
    _alembic(sqlite_url, "upgrade", "head")

    assert ("ix_hymns_church_hymnal", ("church_id", "hymnal")) in _tables_snapshot(sqlite_url)["hymns"][1]
    assert _models_diff(sqlite_url) == []


def test_offline_sql_from_baseline_renders_guarded_adds_and_no_create_table():
    # Runbook step 5: `alembic upgrade 0001_baseline:head --sql`. Offline mode
    # never connects (port 1 on localhost would refuse anyway).
    cfg = alembic_config(url="postgresql://u:p@localhost:1/x", configure_logger=False)
    cfg.output_buffer = buffer = io.StringIO()
    command.upgrade(cfg, "0001_baseline:head", sql=True)
    sql = buffer.getvalue()

    assert "CREATE TABLE" not in sql
    assert "CREATE INDEX IF NOT EXISTS ix_hymns_church_hymnal ON hymns (church_id, hymnal);" in sql
    for table in RECONCILE_TABLES:
        for column in RECONCILE_COLUMNS:
            assert f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} INTEGER;" in sql
    assert sql.count("ADD COLUMN IF NOT EXISTS") == 4
    assert ("UPDATE alembic_version SET version_num='0002_reconcile' "
            "WHERE alembic_version.version_num = '0001_baseline';") in sql
```

Why the assertions hold at later heads: 0003 is a no-op on SQLite (T8) and renders a `DO` block and `REVOKE`s offline; 0004 (T9) adds its `invites` columns with plain `ADD COLUMN` (no `IF NOT EXISTS`, no `CREATE TABLE`), so the count of 4 and "no `CREATE TABLE`" stay true, and `_models_diff` stays `[]` at head.

Append to the end of `backend/tests/test_foundation_setup.py` (after T5's `test_alembic_ini_uses_here_paths_and_has_logging_sections`; T12 appends after these):

```python


# --- slice 1a: the one-off schema scripts give way to Alembic (F §3.2; S amendment 2026-09-26) ---

def test_one_off_schema_scripts_are_deleted():
    backend = ROOT / "backend"
    for gone in ("migrate_add_hymnal.py", "migrate_add_hymn_facts.py", "tests/test_migrate_hymn_facts.py"):
        assert not (backend / gone).exists(), gone
    # The data backfill stays as an ops CLI (data, not schema) and now points at Alembic.
    backfill = (backend / "backfill_hymn_facts.py").read_text(encoding="utf-8")
    assert "Run after `alembic upgrade head`" in backfill
    assert "migrate_add_hymn_facts" not in backfill
    assert (backend / "hymnary_facts.py").is_file()


def test_readme_says_hymn_facts_columns_come_from_alembic():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    section = readme.split("### Service rubric: hymn year and familiarity", 1)[1].split("\n## ", 1)[0]
    assert "1. The columns come from the Alembic migrations (`alembic upgrade head`)." in section
    assert "backfill_hymn_facts.py --dry-run" in section            # steps 2 and 3 unchanged
    assert "migrate_add_hymn_facts" not in readme
    assert "migrate_add_hymnal" not in readme
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_migrations.py 2>&1 | tail -3
.venv/bin/python -m pytest -q backend/tests/test_foundation_setup.py 2>&1 | tail -3
```

Expected: `5 failed, 11 passed` (T5's 4 and T6's 7 pass). With head still at `0001_baseline`: `test_a_pre_pr4_database_stamped_at_baseline_gains_hymn_facts` fails with `KeyError: 'text_year'` (the upgrade adds nothing); `test_upgrade_head_twice_changes_nothing` and `test_on_a_fresh_database_0002_adds_nothing` fail with `alembic.util.exc.CommandError: Can't locate revision identified by '0002_reconcile'`; `test_a_stamped_database_missing_the_hymnal_index_gets_it` fails with `AssertionError: assert ('ix_hymns_church_hymnal', ('church_id', 'hymnal')) in [('ix_hymns_church_id', ('church_id',)), ('ix_hymns_church_number', ('church_id', 'number'))]`; the offline test fails on the `CREATE INDEX IF NOT EXISTS` assertion (the rendered SQL is only `BEGIN;`, the two `SET` lines and `COMMIT;`).

Then `2 failed, 14 passed`: `test_one_off_schema_scripts_are_deleted` fails with `AssertionError: migrate_add_hymnal.py`, and `test_readme_says_hymn_facts_columns_come_from_alembic` fails on the step-1 sentence.

- [ ] **Step 3: Create `backend/migrations/versions/0002_reconcile.py`**

`op.get_context().dialect.name` works online and offline (the dialect comes from the URL). Offline, `op.get_bind()` is SQLAlchemy's `MockConnection`, which the inspector cannot read, so SQLite in `--sql` mode stops with a clear message instead (only the Postgres `--sql` render is a supported path: runbook step 5).

```python
"""Reconcile an existing database with the 0001 baseline (F §3.2 item 3).

Only guarded, idempotent adds, so this is a no-op on production (stamped at
0001_baseline) and on a fresh database (0001 created everything):

- ix_hymns_church_hymnal, which migrate_add_hymnal.py never created;
- text_year and hymnal_count (INTEGER, nullable) on hymns and hymn_catalog,
  only where missing (amendment 2026-09-26). This fixes a local database made
  by create_all before PR #4 and then stamped at 0001_baseline. On Postgres it
  is ADD COLUMN IF NOT EXISTS, which also renders in offline --sql mode; SQLite
  has no IF NOT EXISTS for columns, so there an inspector check decides.

Replaces migrate_add_hymnal.py and migrate_add_hymn_facts.py (deleted).

Revision ID: 0002_reconcile
Revises: 0001_baseline
Create Date: 2026-09-26
"""
from alembic import context, op
import sqlalchemy as sa

revision = "0002_reconcile"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None

HYMN_FACT_TABLES = ("hymns", "hymn_catalog")
HYMN_FACT_COLUMNS = ("text_year", "hymnal_count")


def upgrade() -> None:
    op.create_index("ix_hymns_church_hymnal", "hymns", ["church_id", "hymnal"], if_not_exists=True)

    if op.get_context().dialect.name == "postgresql":
        for table in HYMN_FACT_TABLES:
            for column in HYMN_FACT_COLUMNS:
                op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} INTEGER")
        return

    if context.is_offline_mode():
        raise RuntimeError(
            "0002_reconcile: offline --sql needs Postgres; on SQLite the column "
            "check reads the database (there is no ADD COLUMN IF NOT EXISTS).")
    inspector = sa.inspect(op.get_bind())
    for table in HYMN_FACT_TABLES:
        existing = {c["name"] for c in inspector.get_columns(table)}
        for column in HYMN_FACT_COLUMNS:
            if column not in existing:
                op.add_column(table, sa.Column(column, sa.Integer(), nullable=True))


def downgrade() -> None:
    # No-op on purpose. Every object above is also declared by 0001_baseline:
    # on a fresh database 0001 created them and 0001's downgrade drops them,
    # so dropping them here would break 0001's own drop_index / drop_table and
    # the `downgrade base` cycle. Only a drift fix that is not part of the 0001
    # model schema would get a guarded drop_...(if_exists=True) here (none).
    pass
```

The offline render of `alembic upgrade 0001_baseline:head --sql` on Postgres at this task (T8 and T9 add their statements before `COMMIT;`):

```sql
BEGIN;

SET LOCAL lock_timeout = '5s';

SET LOCAL statement_timeout = '60s';

-- Running upgrade 0001_baseline -> 0002_reconcile

CREATE INDEX IF NOT EXISTS ix_hymns_church_hymnal ON hymns (church_id, hymnal);

ALTER TABLE hymns ADD COLUMN IF NOT EXISTS text_year INTEGER;

ALTER TABLE hymns ADD COLUMN IF NOT EXISTS hymnal_count INTEGER;

ALTER TABLE hymn_catalog ADD COLUMN IF NOT EXISTS text_year INTEGER;

ALTER TABLE hymn_catalog ADD COLUMN IF NOT EXISTS hymnal_count INTEGER;

UPDATE alembic_version SET version_num='0002_reconcile' WHERE alembic_version.version_num = '0001_baseline';

COMMIT;
```

- [ ] **Step 4: Delete the one-off schema scripts and their test**

```bash
git rm backend/migrate_add_hymnal.py backend/migrate_add_hymn_facts.py backend/tests/test_migrate_hymn_facts.py
```

Expected: three `rm '…'` lines. `backfill_hymn_facts.py` and `hymnary_facts.py` stay (S "Deleted": the backfill is an ops CLI that fills data, not schema).

- [ ] **Step 5: Point README step 1 and the backfill docstring at Alembic**

In `README.md` (section "### Service rubric: hymn year and familiarity"), replace lines 155-160:

````markdown
1. **Before merging** code that maps these columns, add them to the deployed
   database. Both apps select every mapped column and would fail without them:

   ```bash
   (cd backend && ../.venv/bin/python migrate_add_hymn_facts.py)
   ```
````

with this single line (the blank line before step 2 stays; steps 2 and 3 and the rest of the section are unchanged, per S "Deleted"):

```markdown
1. The columns come from the Alembic migrations (`alembic upgrade head`).
```

In `backend/backfill_hymn_facts.py`, replace line 5:

```python
corrections survive. Run AFTER migrate_add_hymn_facts.py, and again after
```

with:

```python
corrections survive. Run after `alembic upgrade head`, and again after
```

Then confirm nothing still points at the deleted scripts. The dated plans and specs keep their history, and the only other hits are this task's own mentions (0002's docstring, the new tests), so those paths are excluded:

```bash
git grep -n 'migrate_add_hymn' -- ':!docs/superpowers' ':!backend/migrations' ':!backend/tests'; echo "exit $?"
```

Expected: no matches, then `exit 1`.

- [ ] **Step 6: Run the tests and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_migrations.py backend/tests/test_foundation_setup.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
```

Expected: `32 passed` (`test_migrations.py` 16 = T5's 4 + T6's 7 + these 5; `test_foundation_setup.py` 16 = 14 + these 2), then `646 passed` (643 + 7 − 4: `test_migrate_hymn_facts.py`'s 4 tests are gone). T6's `test_downgrade_base_then_upgrade_head` now runs through 0002's no-op downgrade, which proves it leaves `ix_hymns_church_hymnal` for 0001 to drop (S "Tests", `test_migrations.py`), and T6's `command.check` at head still reports nothing.

If `test_a_pre_pr4_database_stamped_at_baseline_gains_hymn_facts` errors inside `_legacy_database` with `sqlite3.OperationalError` near `DROP`, the SQLite library is older than 3.35 (no `DROP COLUMN`); check `.venv/bin/python -c "import sqlite3; print(sqlite3.sqlite_version)"` (3.53.1 here; CI's `ubuntu-latest` Python 3.11 ships a newer one than 3.35) and stop and report it rather than changing the test.

- [ ] **Step 7: Commit**

```bash
git add backend/migrations/versions/0002_reconcile.py backend/backfill_hymn_facts.py README.md \
        backend/tests/test_migrations.py backend/tests/test_foundation_setup.py
git commit -m "Migrations: 0002_reconcile replaces the one-off schema scripts (F §3.2, S amendment 2026-09-26)

0002 adds ix_hymns_church_hymnal and PR #4's text_year/hymnal_count on hymns
and hymn_catalog only where missing: ADD COLUMN IF NOT EXISTS on Postgres
(renders in --sql), an inspector check on SQLite. It is a no-op on production
and on fresh databases, and its downgrade is a no-op because 0001 owns those
objects. migrate_add_hymnal.py, migrate_add_hymn_facts.py and its test are
deleted; README step 1 and the backfill docstring now point at
'alembic upgrade head'.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

The three deletions are already staged by Step 4's `git rm`, so the commit includes them. Check with `git show --stat HEAD`: 8 files, of which 3 are deleted.

---

### Task 8: `0003_lockdown`, the throwaway-database helper and the Postgres refusal tests (F §3.2 item 4, §3.6; S Revisions; AC1)

`0003_lockdown` makes the ops lockdown of 2026-09-25 part of the migration history: one `DO` block, run as the migrating (app) role, that checks the RLS precondition, enables row-level security on every `public` table that still has it off (`alembic_version` included), and repeats the ops REVOKEs when the Supabase roles exist. It is a no-op on SQLite. A `RAISE` aborts env.py's single transaction (Task 5), so nothing half-applies. Nothing on this machine runs Postgres (Global Constraints), so here "failing test first" covers the two SQLite/offline tests; the three `@pytest.mark.postgres` tests skip locally and first run in CI at Task 14's draft-PR checkpoint (owner Q5). If one fails there, fix it in this task's files and re-review this task.

The sandbox follows critique 11: since Postgres 15 only a database's owner has CREATE on its `public` schema, so the migrating role owns a fresh database (a role that merely had CONNECT would fail in 0001 with "permission denied for schema public", not in 0003). `CREATE DATABASE` cannot run in a transaction, so the admin engine is `AUTOCOMMIT`; roles are cluster-wide, so teardown drops the database `WITH (FORCE)` first and then the roles.

**Files:**
- Create: `backend/migrations/versions/0003_lockdown.py`
- Modify: `backend/tests/pg_helpers.py` (Task 1's file: replace lines 1-9, the docstring, the import and `LOCAL_HOSTS`; append `ThrowawayDb`, `throwaway_database` and `supabase_roles` after `require_local_test_url`)
- Test: `backend/tests/test_migrations.py` (append after Task 7's tests: 2 local tests, 3 `@pytest.mark.postgres` tests)

**Interfaces:**
- Consumes: `tests.pg_helpers.require_local_test_url(url: str) -> str` and the `postgres` marker in `pytest.ini` (Task 1); `db.schema_check.alembic_config(*, url=None, configure_logger=True)`, the `_alembic(url, *args, **kw)` helper, the `sqlite_url` fixture and the `pytest`/`command`/`alembic_config` imports at the top of `test_migrations.py`, and env.py's single transaction and named paramstyle (Task 5); revision `0001_baseline` with the 11 model tables (Task 6); revision `0002_reconcile` (Task 7); `db.engine.Base`, `db.engine._normalize_url(url: str) -> str` (`db/engine.py:33-42`); `db.models` (registers the 11 tables).
- Produces:
  - revision `0003_lockdown` (`down_revision = "0002_reconcile"`); Task 9's `0004_invites_reusable` sets `down_revision = "0003_lockdown"`;
  - module constants `LOCKDOWN_SQL: str` (the upgrade's `DO` block, without a trailing `;`) and `UNLOCK_SQL: str` (the downgrade's `DO` block); tests reach them through `ScriptDirectory.from_config(alembic_config(configure_logger=False)).get_revision("0003_lockdown").module` (the file name starts with a digit);
  - the two refusal messages, verbatim (the second completes the spec's "…"; Task 24's README quotes both):
    - `0003_lockdown: role % has no BYPASSRLS and does not own: %. Enabling RLS would hide their rows from the app. See migrations/README.md "RLS precondition".`
    - `0003_lockdown: cannot enable RLS on % (owned by %, migrating as %). Only the owner of a table can enable RLS on it. See migrations/README.md "RLS precondition".`
  - `tests.pg_helpers.ThrowawayDb` (frozen dataclass): `name: str`, `role: str`, `role_url: str`, `admin_db_url: str`, `other_role: str` (the outline's four fields plus `other_role`, the NOLOGIN `wsb_o_<hex>` owner for tables the migrating role must not own);
  - `tests.pg_helpers.throwaway_database(admin_url: str, *, role_bypassrls: bool = False) -> ContextManager[ThrowawayDb]`;
  - `tests.pg_helpers.supabase_roles(admin_url: str) -> ContextManager[None]` (creates NOLOGIN `anon` and `authenticated` when missing, drops only those it created);
  - test-file names (Task 9 appends after them and must not reuse them): `LOCKDOWN_REFUSAL`, `LOCKDOWN_CANNOT_ENABLE`, `SUPABASE_REVOKES`, `_lockdown_module`, `_lockdown_offline_sql`, `_pg_engine`, `_rls_flags`, `_create_foreign_owned_table`, fixture `pg_admin_url`.

- [ ] **Step 1: Add the sandbox helpers to `backend/tests/pg_helpers.py`**

These are test infrastructure with no tests of their own: the three Postgres tests of Step 2 are their tests, and they run in CI.

Replace lines 1-9 (Task 1's docstring, import and constant):

```python
"""Helpers for the Postgres-only tests (`@pytest.mark.postgres`; F §5.1).

Every Postgres URL a test uses passes require_local_test_url first, so a test
can never create roles, drop databases or TRUNCATE tables anywhere but a
local, throwaway Postgres (the same rule as pg_smoke.py).
"""
from urllib.parse import urlsplit

LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1")
```

with:

```python
"""Helpers for the Postgres-only tests (`@pytest.mark.postgres`; F §5.1).

Every Postgres URL a test uses passes require_local_test_url first, so a test
can never create roles, drop databases or TRUNCATE tables anywhere but a
local, throwaway Postgres (the same rule as pg_smoke.py).

throwaway_database and supabase_roles (Task 8) create cluster-wide roles and
a whole database on that local Postgres, and drop them again on the way out.
"""
import secrets
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator
from urllib.parse import urlsplit

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.pool import NullPool

from db.engine import _normalize_url

LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1")
```

Then append at the end of the file (after `require_local_test_url`, which is unchanged):

```python


@dataclass(frozen=True)
class ThrowawayDb:
    name: str           # the database, wsb_lockdown_<hex>
    role: str           # LOGIN role wsb_t_<hex>: owns the database, runs the migrations
    role_url: str       # the database, connected as `role`
    admin_db_url: str   # the database, connected as the admin (superuser) role
    other_role: str     # NOLOGIN role wsb_o_<hex>: owns tables `role` must not own


def _admin_engine(admin_url: str) -> Engine:
    # CREATE DATABASE and DROP DATABASE cannot run inside a transaction.
    return create_engine(_normalize_url(admin_url), isolation_level="AUTOCOMMIT", poolclass=NullPool)


@contextmanager
def throwaway_database(admin_url: str, *, role_bypassrls: bool = False) -> Iterator[ThrowawayDb]:
    """A new database owned by a new LOGIN role, both dropped on exit.

    `admin_url` is TEST_DATABASE_URL (CI's superuser, which may grant
    BYPASSRLS). The role owns the database, so it has CREATE on its `public`
    schema (since Postgres 15 only the database owner has it) and 0001 runs
    as it; it is not a superuser, so 0003's ownership rules apply to it.
    """
    admin_url = require_local_test_url(admin_url)
    suffix = secrets.token_hex(4)
    name, role, other_role = f"wsb_lockdown_{suffix}", f"wsb_t_{suffix}", f"wsb_o_{suffix}"
    password = secrets.token_hex(16)
    rls = "BYPASSRLS" if role_bypassrls else "NOBYPASSRLS"
    base = make_url(admin_url)
    admin = _admin_engine(admin_url)
    try:
        with admin.connect() as conn:
            conn.exec_driver_sql(f"CREATE ROLE {role} LOGIN {rls} PASSWORD '{password}'")
            conn.exec_driver_sql(f"CREATE ROLE {other_role} NOLOGIN")
            conn.exec_driver_sql(f"CREATE DATABASE {name} OWNER {role}")
        yield ThrowawayDb(
            name=name,
            role=role,
            role_url=base.set(username=role, password=password, database=name)
                         .render_as_string(hide_password=False),
            admin_db_url=base.set(database=name).render_as_string(hide_password=False),
            other_role=other_role,
        )
    finally:
        with admin.connect() as conn:
            conn.exec_driver_sql(f"DROP DATABASE IF EXISTS {name} WITH (FORCE)")
            conn.exec_driver_sql(f"DROP ROLE IF EXISTS {role}")
            conn.exec_driver_sql(f"DROP ROLE IF EXISTS {other_role}")
        admin.dispose()


@contextmanager
def supabase_roles(admin_url: str) -> Iterator[None]:
    """Make sure the NOLOGIN roles anon and authenticated exist, as on Supabase.

    Drops on exit only the ones it created. Enter it BEFORE throwaway_database,
    so the database (and every grant to these roles inside it) is gone before
    the roles are dropped.
    """
    admin = _admin_engine(require_local_test_url(admin_url))
    created = []
    try:
        with admin.connect() as conn:
            for name in ("anon", "authenticated"):
                exists = conn.execute(
                    text("SELECT 1 FROM pg_roles WHERE rolname = :name"), {"name": name}).first()
                if exists is None:
                    conn.exec_driver_sql(f"CREATE ROLE {name} NOLOGIN")
                    created.append(name)
        yield
    finally:
        with admin.connect() as conn:
            for name in created:
                conn.exec_driver_sql(f"DROP ROLE IF EXISTS {name}")
        admin.dispose()
```

Run Task 1's guard tests, which import the module:

```bash
.venv/bin/python -m pytest -q backend/tests/test_pg_helpers.py 2>&1 | tail -1
```

Expected: `6 passed`.

- [ ] **Step 2: Write the failing tests**

Append to the end of `backend/tests/test_migrations.py` (after Task 7's tests). The imports sit under the section comment with `# noqa: E402`, as in `backend/tests/pg_smoke.py`, so this block does not depend on the exact import lines Tasks 5-7 put at the top of the file:

```python


# --- 0003_lockdown (Task 8; F §3.2 item 4, §3.6) --------------------------------

import io  # noqa: E402
import os  # noqa: E402

from alembic.script import ScriptDirectory  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.exc import DBAPIError  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

from db.engine import Base, _normalize_url  # noqa: E402
from db import models  # noqa: E402,F401  (registers every table on Base.metadata)
from tests.pg_helpers import require_local_test_url, supabase_roles, throwaway_database  # noqa: E402

LOCKDOWN_REFUSAL = (
    "0003_lockdown: role {role} has no BYPASSRLS and does not own: {tables}. Enabling RLS would "
    'hide their rows from the app. See migrations/README.md "RLS precondition".'
)
LOCKDOWN_CANNOT_ENABLE = (
    "0003_lockdown: cannot enable RLS on {table} (owned by {owner}, migrating as {role}). "
    'Only the owner of a table can enable RLS on it. See migrations/README.md "RLS precondition".'
)
SUPABASE_REVOKES = (
    "REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated;",
    "REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated;",
    "ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM anon, authenticated;",
    "ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM anon, authenticated;",
)


def _lockdown_module():
    """The 0003 revision module, loaded by Alembic (its file name starts with a digit)."""
    script = ScriptDirectory.from_config(alembic_config(configure_logger=False))
    return script.get_revision("0003_lockdown").module


def _lockdown_offline_sql() -> str:
    """`alembic upgrade 0002_reconcile:0003_lockdown --sql` for Postgres; never connects."""
    cfg = alembic_config(url="postgresql://u:p@localhost:1/x", configure_logger=False)
    cfg.output_buffer = io.StringIO()
    command.upgrade(cfg, "0002_reconcile:0003_lockdown", sql=True)
    return cfg.output_buffer.getvalue()


def _pg_engine(url: str):
    return create_engine(_normalize_url(url), poolclass=NullPool)


def _rls_flags(engine) -> dict[str, bool]:
    """relrowsecurity of every table in `public`, by name."""
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT c.relname, c.relrowsecurity FROM pg_class c "
            "WHERE c.relnamespace = 'public'::regnamespace AND c.relkind IN ('r', 'p')"))
        return {name: flag for name, flag in rows}


def _create_foreign_owned_table(admin, owner: str) -> None:
    """As the admin: public.foreign_owned in the sandbox, owned by another role, RLS off."""
    with admin.begin() as conn:
        conn.execute(text("CREATE TABLE public.foreign_owned (id integer PRIMARY KEY)"))
        conn.execute(text(f"ALTER TABLE public.foreign_owned OWNER TO {owner}"))


@pytest.fixture
def pg_admin_url():
    url = os.environ.get("TEST_DATABASE_URL", "").strip()
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set (the backend-postgres CI job sets it)")
    return require_local_test_url(url)


def test_0003_is_a_no_op_on_sqlite(sqlite_url):
    _alembic(sqlite_url, "upgrade", "0002_reconcile")
    engine = create_engine(sqlite_url)
    try:
        snapshot = "SELECT type, name, tbl_name, sql FROM sqlite_master ORDER BY type, name"
        with engine.connect() as conn:
            before = conn.execute(text(snapshot)).all()
        _alembic(sqlite_url, "upgrade", "0003_lockdown")
        with engine.connect() as conn:
            assert conn.execute(text(snapshot)).all() == before
            assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0003_lockdown"
        _alembic(sqlite_url, "downgrade", "0002_reconcile")
        with engine.connect() as conn:
            assert conn.execute(text(snapshot)).all() == before
            assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0002_reconcile"
    finally:
        engine.dispose()


def test_offline_sql_for_0003_has_the_do_block_and_revokes():
    sql = _lockdown_offline_sql()
    lockdown = _lockdown_module().LOCKDOWN_SQL
    assert lockdown + ";" in sql                    # the module constant, verbatim
    assert sql.count("DO $$") == 1
    # Named paramstyle (env.py): RAISE placeholders and format() stay single %.
    assert "%%" not in sql
    assert LOCKDOWN_REFUSAL.format(role="%", tables="%") in sql
    assert LOCKDOWN_CANNOT_ENABLE.format(table="%", owner="%", role="%") in sql
    assert "EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t.tbl);" in sql
    for statement in SUPABASE_REVOKES:
        assert statement in sql
    assert "UPDATE alembic_version SET version_num='0003_lockdown' " \
           "WHERE alembic_version.version_num = '0002_reconcile';" in sql
    assert "CREATE TABLE" not in sql
    assert "DISABLE ROW LEVEL SECURITY" not in sql  # the downgrade's block is not in an upgrade


@pytest.mark.postgres
def test_0003_refuses_without_bypassrls_or_ownership_and_rolls_back(pg_admin_url):
    with throwaway_database(pg_admin_url) as sandbox:
        admin = _pg_engine(sandbox.admin_db_url)
        try:
            _create_foreign_owned_table(admin, sandbox.other_role)
            with pytest.raises(DBAPIError) as excinfo:
                _alembic(sandbox.role_url, "upgrade", "head")
            assert excinfo.value.orig.diag.message_primary == LOCKDOWN_REFUSAL.format(
                role=sandbox.role, tables="foreign_owned")
            # One transaction (env.py): 0001 and 0002 rolled back with 0003, so no
            # model table and no alembic_version exist, and RLS is still off.
            assert _rls_flags(admin) == {"foreign_owned": False}
        finally:
            admin.dispose()


@pytest.mark.postgres
def test_0003_refuses_a_bypassrls_role_that_does_not_own_a_table(pg_admin_url):
    with throwaway_database(pg_admin_url, role_bypassrls=True) as sandbox:
        admin = _pg_engine(sandbox.admin_db_url)
        try:
            _create_foreign_owned_table(admin, sandbox.other_role)
            with pytest.raises(DBAPIError) as excinfo:
                _alembic(sandbox.role_url, "upgrade", "head")
            assert excinfo.value.orig.diag.message_primary == LOCKDOWN_CANNOT_ENABLE.format(
                table="foreign_owned", owner=sandbox.other_role, role=sandbox.role)
            # The loop had already enabled RLS on alembic_version, churches and
            # contacts (alphabetical order); the rollback undid that too.
            assert _rls_flags(admin) == {"foreign_owned": False}
        finally:
            admin.dispose()


@pytest.mark.postgres
def test_0003_is_idempotent_after_the_manual_lockdown(pg_admin_url):
    with supabase_roles(pg_admin_url), throwaway_database(pg_admin_url, role_bypassrls=True) as sandbox:
        _alembic(sandbox.role_url, "upgrade", "0002_reconcile")
        owner = _pg_engine(sandbox.role_url)
        admin = _pg_engine(sandbox.admin_db_url)
        try:
            with owner.begin() as conn:
                # The ops lockdown of 2026-09-25 enabled RLS by hand; here on three tables.
                for table in ("churches", "invites", "users"):
                    conn.execute(text(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY"))
                # What Supabase's defaults give anon and authenticated before the REVOKEs.
                conn.execute(text("GRANT SELECT ON ALL TABLES IN SCHEMA public TO anon, authenticated"))

            _alembic(sandbox.role_url, "upgrade", "head")
            after_upgrade = _rls_flags(admin)
            assert after_upgrade == {name: True for name in [*Base.metadata.tables, "alembic_version"]}
            with admin.connect() as conn:
                for grantee in ("anon", "authenticated"):
                    assert conn.execute(text(
                        "SELECT has_table_privilege(:grantee, 'public.users', 'SELECT')"),
                        {"grantee": grantee}).scalar_one() is False

            with owner.begin() as conn:            # the DO block again: no error, no change
                conn.execute(text(_lockdown_module().LOCKDOWN_SQL))
            assert _rls_flags(admin) == after_upgrade
        finally:
            owner.dispose()
            admin.dispose()
```

Why each test: `test_0003_is_a_no_op_on_sqlite` proves 0003 and its downgrade change nothing but the revision on SQLite (`sqlite_master` compared whole). `test_offline_sql_for_0003_has_the_do_block_and_revokes` proves the module constant reaches `--sql` output verbatim with single `%` (the runbook's `upgrade.sql`, step 5). The refusal test is AC1's "refuses, with its precondition message and without partial changes": `_rls_flags(admin) == {"foreign_owned": False}` says at once that no model table and no `alembic_version` survived (0001 and 0002 rolled back with 0003, which is env.py's single transaction) and that the foreign table's RLS flag did not change. The second refusal test reaches the "cannot enable RLS on" branch, which a BYPASSRLS role that does not own a table hits after the loop has already enabled RLS on `alembic_version`, `churches` and `contacts`. The idempotence test is production's shape: a BYPASSRLS owner, the Supabase roles present with table grants, RLS already on for some tables; it also exercises the REVOKE branch, which CI's plain Postgres never reaches otherwise.

- [ ] **Step 3: Run the tests to verify they fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_migrations.py 2>&1 | grep -E '^E +alembic.util.exc.CommandError' | sort | uniq -c
.venv/bin/python -m pytest -q backend/tests/test_migrations.py 2>&1 | tail -1
```

Expected: one line, the count `2` (padded by `uniq -c`) then `E           alembic.util.exc.CommandError: Can't locate revision identified by '0003_lockdown'` (the SQLite test's `upgrade 0003_lockdown` and the offline test's `0002_reconcile:0003_lockdown` range), then `2 failed, 16 passed, 3 skipped` (Task 5's 4, Task 6's 7 and Task 7's 5 tests pass; the three Postgres tests skip without `TEST_DATABASE_URL`).

- [ ] **Step 4: Create `backend/migrations/versions/0003_lockdown.py`**

```python
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
```

Notes for the reviewer:
- `op.execute(str)` wraps the SQL in `text()`. On psycopg2 (online) SQLAlchemy doubles every `%` and psycopg2 undoes it; offline, env.py's named paramstyle leaves `%` single (Task 5). The SQL has no `:word` sequence (`::regnamespace` and `::text` are not bind parameters), checked with `text(LOCKDOWN_SQL).compile(dialect=postgresql.psycopg2.dialect())`: no binds, and the compiled string with `%%` undone equals the constant.
- The precondition and the loop read `pg_class` (`relkind IN ('r', 'p')`: tables and partitioned tables, as `pg_tables` lists them), so they see `alembic_version`, which Alembic creates inside the same transaction.
- `RAISE` checks at compile time that the `%` placeholders match the arguments (2 and 3 here).
- The REVOKEs are static statements inside the `DO` block (they cannot be conditional outside one), so `upgrade.sql` shows them inside the block, not after it; PL/pgSQL prepares a statement only when it runs, so on CI Postgres, with no `anon` role, they are never parsed against missing roles. The guard asks for both `anon` and `authenticated` (the spec says "if role `anon` exists"), because the statements name both and would fail if only one existed.
- The downgrade only turns RLS off on tables the migrating role owns (only an owner may) and deliberately restores no grant. CI's `alembic downgrade base` (Task 14) runs it as the superuser that owns every table.
- In production the app role `postgres` owns every table and has BYPASSRLS (docs/ops-runbook.md:132-137), so the precondition passes, the loop finds only `alembic_version` (created by the stamp in runbook step 4) with RLS off, and the REVOKEs repeat what ops applied.

- [ ] **Step 5: Run the tests, the offline render and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_migrations.py backend/tests/test_pg_helpers.py -rs 2>&1 | tail -5
.venv/bin/python -m pytest -q -m postgres backend/tests/test_migrations.py 2>&1 | tail -1
(cd backend && DATABASE_URL=postgresql://u:p@localhost:1/x ../.venv/bin/alembic upgrade 0002_reconcile:0003_lockdown --sql 2>/dev/null) | grep -E '^(BEGIN|SET|DO|END|COMMIT|UPDATE alembic_version)'
(cd backend && DATABASE_URL=postgresql://u:p@localhost:1/x ../.venv/bin/alembic upgrade 0002_reconcile:0003_lockdown --sql 2>/dev/null) | grep -c '%%'
.venv/bin/python -m pytest -q | tail -1
```

Expected:
- three `SKIPPED [1] backend/tests/test_migrations.py:<line>: TEST_DATABASE_URL is not set (the backend-postgres CI job sets it)` lines, then `24 passed, 3 skipped` (18 in `test_migrations.py` + 6 in `test_pg_helpers.py`);
- `3 skipped, 18 deselected`;
- the offline render (the `DATABASE_URL` is a dummy that is never connected to; the CLI's `Database:` and INFO lines go to stderr), exactly these eight lines (the second `BEGIN` is the `DO` block's own):

  ```
  BEGIN;
  SET LOCAL lock_timeout = '5s';
  SET LOCAL statement_timeout = '60s';
  DO $$
  BEGIN
  END $$;
  UPDATE alembic_version SET version_num='0003_lockdown' WHERE alembic_version.version_num = '0002_reconcile';
  COMMIT;
  ```

  then `0` (no doubled `%` anywhere);
- the suite: `648 passed, 3 skipped` (Task 7 left `646 passed`). Tasks 6 and 7's tests that span several revisions now also run 0003 and stay green: `test_every_revision_defines_downgrade` and `test_there_is_a_single_head` see it (head is `0003_lockdown` until Task 9), the SQLite up/down cycles pass through its no-op, and the offline renders from base or `0001_baseline` gain the `DO` block, which contains no `CREATE TABLE`, `CREATE INDEX` or `ADD COLUMN`.

The three skips are expected until Task 14: there the `backend-postgres` job runs `pytest -m postgres` and must report `5 passed`, three of them these. A failure there is fixed in `0003_lockdown.py`, `pg_helpers.py` or this test block, and this task is re-reviewed before Task 15.

- [ ] **Step 6: Commit**

```bash
git add backend/migrations/versions/0003_lockdown.py backend/tests/pg_helpers.py backend/tests/test_migrations.py
git commit -m "Alembic: 0003_lockdown enables RLS as the app role and refuses rather than half-applying (F §3.2, §3.6, S Revisions)

One DO block: unless the migrating role has BYPASSRLS it must own every
public table; every public table with RLS off is enabled when the role owns
it, else the upgrade stops; the ops REVOKEs run when anon and authenticated
exist. A RAISE rolls back the whole upgrade (one transaction). No-op on
SQLite. Postgres tests run each case in a throwaway database owned by a
throwaway role (CI only).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: `0004_invites_reusable` and the `Invite` model (F §3.2 item 5, §3.4; S Revisions, `db/models.py`)

The last 1a revision and the one model change of the PR. `invites` gains `reusable BOOLEAN NOT NULL DEFAULT false` and `accepted_by UUID NULL` with the named FK `fk_invites_accepted_by_users` → `users(id) ON DELETE SET NULL`; the data step marks every existing code-only invite (`email IS NULL`) reusable, so pre-existing Streamlit invites keep their 7-day multi-use meaning. The server default is what keeps frozen Streamlit working (its ORM does not map the new columns, so its INSERTs name only the old ones), and the models docstring now says so (S "`db/models.py`"; F §3.4). Both directions run inside `op.batch_alter_table("invites")` (Global Constraints): on Postgres and offline that is plain `ALTER TABLE`; on SQLite, which cannot add or drop a foreign key with `ALTER`, the batch recreates `invites` and copies its rows (`render_as_batch=True` in `env.py` only affects autogenerate, critique 25). The data step uses a lightweight `sa.table`, so `sa.true()` renders `true` on Postgres and `1` on SQLite. No repository or route reads the new columns in 1a (1b's accept and 6b's create do); `repos.invites.create_invite` keeps working unchanged because the ORM now sends the Python default `False`.

Checked on Alembic 1.20.0 / SQLAlchemy 2.1.1 against Task 5's `env.py` with 0001–0003 stand-ins: `upgrade head` → `schema_diff` `[]` and `alembic check` "No new upgrade operations detected."; `downgrade base` → `upgrade head` → `[]`; at `0003_lockdown` the diff is exactly `add_column`, `add_column`, `add_fk` (what Task 10 pins); the SQLite recreate keeps every other column type, the unnamed FKs with their `ON DELETE` rules, both unique constraints, the index and the rows; the whole suite stayed green with the model change (`streamlit_tests/` included).

**Files:**
- Create: `backend/migrations/versions/0004_invites_reusable.py`
- Modify: `backend/db/models.py:1-10` (module docstring; `import sqlalchemy as sa`), `backend/db/models.py:90-91` (two columns after `accepted_at` in `class Invite`)
- Test: `backend/tests/test_migrations.py` (append the Task 9 block after Task 8's tests: 3 tests), `backend/tests/test_models.py` (append 1 test)

**Interfaces:**
- Consumes: Task 5's `_alembic(url: str, *args, **kw)` and fixture `sqlite_url(tmp_path) -> str` (in `test_migrations.py`), `db.schema_check.alembic_config`, `env.py` (URL from `cfg.attributes["url"]`, one transaction, `Database:` line on stderr); Task 6's `0001_baseline` (the `invites` table exactly as `db/models.py` at `7978a5e`: unnamed PK, unnamed `UNIQUE (code)`, unnamed FKs `church_id` → `churches.id` `ON DELETE CASCADE` and `created_by` → `users.id` `ON DELETE SET NULL`, `uq_invites_church_email`, `ix_invites_church_id`); Task 7's `0002_reconcile`; Task 8's `0003_lockdown` (no-op on SQLite; `down_revision` of this revision); conftest fixtures `tmp_db`, `make_user(email=…, *, name=…, google_sub=…, picture=…) -> uuid.UUID`, `make_church(name=…, timezone=…, owner_user_id=None) -> uuid.UUID` (`tmp_db` turns SQLite foreign keys on).
- Produces:
  - revision `0004_invites_reusable` (`down_revision = "0003_lockdown"`; the single head); module constant `FK_ACCEPTED_BY = "fk_invites_accepted_by_users"`. Later users: Task 10 (head name; the three drift lines at `0001_baseline`), Task 11 (`schema revision None != head 0004_invites_reusable`), Task 24 (README, expected `upgrade.sql`), Tasks 26–27 (owner runbook), and every later revision's `down_revision` (F §3.5 chain rule).
  - `db.models.Invite.reusable = Column(Boolean, nullable=False, default=False, server_default=sa.false())`; `db.models.Invite.accepted_by = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL", name="fk_invites_accepted_by_users"))`. Later users: 1b (`repos.invites.claim`, `_to_dict`, accept rule 4), 6b (`create_invite(..., reusable=)`).

- [ ] **Step 1: Write the failing tests**

Append to the end of `backend/tests/test_migrations.py` (after Task 8's tests). The block brings its own imports and uses only names no earlier task defines (`T9_NOW`, `_legacy_invites`, `_t9_users`, `_t9_churches`, `_seed_owner_and_church`, `_insert_legacy_invite`, `_invites_shape`); it uses Task 5's `_alembic` and `sqlite_url`, so every Alembic call passes its URL explicitly. The seed rows go through typed `sa.table` INSERTs that name only the pre-0004 columns, which is the exact shape of frozen Streamlit's ORM INSERT and binds UUIDs and datetimes correctly on either dialect.

```python


# --- Task 9: 0004_invites_reusable (F §3.2 item 5, §3.4) -----------------------
import uuid
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa
from sqlalchemy.pool import NullPool

T9_NOW = datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc)

# The invites columns before 0004, i.e. everything frozen Streamlit's ORM maps:
# its INSERTs name exactly these columns and never reusable or accepted_by.
_legacy_invites = sa.table(
    "invites",
    sa.column("id", sa.Uuid()),
    sa.column("church_id", sa.Uuid()),
    sa.column("code", sa.String()),
    sa.column("email", sa.String()),
    sa.column("role", sa.String()),
    sa.column("created_by", sa.Uuid()),
    sa.column("created_at", sa.DateTime(timezone=True)),
    sa.column("expires_at", sa.DateTime(timezone=True)),
    sa.column("revoked", sa.Boolean()),
    sa.column("accepted_at", sa.DateTime(timezone=True)),
)
_t9_users = sa.table(
    "users",
    sa.column("id", sa.Uuid()),
    sa.column("email", sa.String()),
    sa.column("created_at", sa.DateTime(timezone=True)),
)
_t9_churches = sa.table(
    "churches",
    sa.column("id", sa.Uuid()),
    sa.column("name", sa.String()),
    sa.column("timezone", sa.String()),
    sa.column("settings", sa.JSON()),
    sa.column("created_at", sa.DateTime(timezone=True)),
)


def _seed_owner_and_church(conn) -> tuple[uuid.UUID, uuid.UUID]:
    user_id, church_id = uuid.uuid4(), uuid.uuid4()
    conn.execute(_t9_users.insert().values(id=user_id, email="owner@example.com", created_at=T9_NOW))
    conn.execute(_t9_churches.insert().values(
        id=church_id, name="Grace Church", timezone="America/New_York", settings={}, created_at=T9_NOW))
    return user_id, church_id


def _insert_legacy_invite(conn, church_id, user_id, *, code, email=None, accepted_at=None) -> None:
    """An INSERT shaped like frozen Streamlit's: no reusable, no accepted_by."""
    conn.execute(_legacy_invites.insert().values(
        id=uuid.uuid4(), church_id=church_id, code=code, email=email, role="member",
        created_by=user_id, created_at=T9_NOW, expires_at=T9_NOW + timedelta(days=7),
        revoked=False, accepted_at=accepted_at))


def _invites_shape(conn) -> dict:
    """Everything a table recreate could lose: columns, keys, constraints, indexes."""
    insp = sa.inspect(conn)
    return {
        "columns": [(c["name"], str(c["type"]), c["nullable"]) for c in insp.get_columns("invites")],
        "pk": insp.get_pk_constraint("invites")["constrained_columns"],
        "fks": sorted(
            (fk["name"] or "", tuple(fk["constrained_columns"]), fk["referred_table"],
             tuple(fk["referred_columns"]), fk["options"].get("ondelete"))
            for fk in insp.get_foreign_keys("invites")),
        "uniques": sorted((u["name"] or "", tuple(u["column_names"]))
                          for u in insp.get_unique_constraints("invites")),
        "indexes": sorted((i["name"], tuple(i["column_names"]), bool(i["unique"]))
                          for i in insp.get_indexes("invites")),
    }


def test_0004_marks_only_code_only_invites_reusable(sqlite_url):
    _alembic(sqlite_url, "upgrade", "0003_lockdown")
    engine = sa.create_engine(sqlite_url, poolclass=NullPool)
    try:
        with engine.begin() as conn:
            user_id, church_id = _seed_owner_and_church(conn)
            _insert_legacy_invite(conn, church_id, user_id, code="CODEONLY")
            _insert_legacy_invite(conn, church_id, user_id, code="PENDING", email="new@example.com")
            _insert_legacy_invite(conn, church_id, user_id, code="USED", email="old@example.com",
                                  accepted_at=T9_NOW)
        _alembic(sqlite_url, "upgrade", "head")
        with engine.connect() as conn:
            rows = conn.execute(sa.text(
                "SELECT code, reusable, accepted_by FROM invites ORDER BY code")).all()
    finally:
        engine.dispose()
    assert [(code, bool(reusable), accepted_by) for code, reusable, accepted_by in rows] == [
        ("CODEONLY", True, None),
        ("PENDING", False, None),
        ("USED", False, None),
    ]


def test_0004_downgrade_drops_the_columns_and_fk(sqlite_url):
    _alembic(sqlite_url, "upgrade", "0003_lockdown")
    engine = sa.create_engine(sqlite_url, poolclass=NullPool)
    try:
        with engine.connect() as conn:
            before = _invites_shape(conn)
        _alembic(sqlite_url, "upgrade", "head")
        with engine.begin() as conn:
            user_id, church_id = _seed_owner_and_church(conn)
            _insert_legacy_invite(conn, church_id, user_id, code="KEEP")
            at_head = _invites_shape(conn)
        _alembic(sqlite_url, "downgrade", "0003_lockdown")
        with engine.connect() as conn:
            after = _invites_shape(conn)
            codes = conn.execute(sa.text("SELECT code FROM invites")).scalars().all()
            version = conn.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one()
    finally:
        engine.dispose()
    assert at_head["columns"] == before["columns"] + [
        ("reusable", "BOOLEAN", False), ("accepted_by", "CHAR(32)", True)]
    assert at_head["fks"] == sorted(before["fks"] + [
        ("fk_invites_accepted_by_users", ("accepted_by",), "users", ("id",), "SET NULL")])
    assert after == before          # the recreate kept every other column, key and index
    assert codes == ["KEEP"]        # and the rows
    assert version == "0003_lockdown"


def test_an_insert_without_reusable_gets_false(sqlite_url):
    _alembic(sqlite_url, "upgrade", "head")
    engine = sa.create_engine(sqlite_url, poolclass=NullPool)
    try:
        with engine.begin() as conn:
            user_id, church_id = _seed_owner_and_church(conn)
            _insert_legacy_invite(conn, church_id, user_id, code="STREAMLIT")
        with engine.connect() as conn:
            reusable, accepted_by = conn.execute(sa.text(
                "SELECT reusable, accepted_by FROM invites WHERE code = 'STREAMLIT'")).one()
    finally:
        engine.dispose()
    assert (bool(reusable), accepted_by) == (False, None)
```

Append to the end of `backend/tests/test_models.py` (its top already imports `uuid`; the other imports are deferred inside the test, as the file's other tests do):

```python


def test_invite_reusable_and_accepted_by_columns(tmp_db, make_user, make_church):
    """Slice 1 (F §3.2 item 5, §3.4): reusable has a server default for frozen Streamlit's inserts."""
    from datetime import datetime, timedelta, timezone

    from sqlalchemy.dialects import postgresql
    from sqlalchemy.schema import CreateTable

    from db import session_scope
    from db.models import Invite, User

    ddl = str(CreateTable(Invite.__table__).compile(dialect=postgresql.dialect()))
    assert "reusable BOOLEAN DEFAULT false NOT NULL" in ddl
    assert "accepted_by UUID," in ddl
    assert ("CONSTRAINT fk_invites_accepted_by_users FOREIGN KEY(accepted_by) "
            "REFERENCES users (id) ON DELETE SET NULL") in ddl

    owner_id = make_user("owner@example.com")
    joiner_id = make_user("joiner@example.com")
    church_id = make_church(owner_user_id=owner_id)
    invite_id = uuid.uuid4()
    with session_scope() as s:
        s.add(Invite(id=invite_id, church_id=church_id, code="ABC123", created_by=owner_id,
                     expires_at=datetime.now(timezone.utc) + timedelta(days=7)))
    with session_scope() as s:
        invite = s.get(Invite, invite_id)
        assert (invite.reusable, invite.accepted_by) == (False, None)
        invite.accepted_by = joiner_id

    with session_scope() as s:
        assert s.get(Invite, invite_id).accepted_by == joiner_id
        s.delete(s.get(User, joiner_id))
    with session_scope() as s:            # tmp_db enforces SQLite foreign keys
        assert s.get(Invite, invite_id).accepted_by is None
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_migrations.py backend/tests/test_models.py 2>&1 | tail -3
```

Expected summary line: `4 failed, 21 passed, 3 skipped` (`test_migrations.py` after Task 8 = 21 items, 18 passed + 3 Postgres skips, plus these 3; `test_models.py` 3 + 1). Head is still `0003_lockdown` and the model has no new columns, so:
- `test_0004_marks_only_code_only_invites_reusable` and `test_an_insert_without_reusable_gets_false` fail with `sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such column: reusable`;
- `test_0004_downgrade_drops_the_columns_and_fk` fails its first assertion: `Right contains 2 more items, first extra item: ('reusable', 'BOOLEAN', False)`;
- `test_invite_reusable_and_accepted_by_columns` fails with `AssertionError: assert 'reusable BOOLEAN DEFAULT false NOT NULL' in '\nCREATE TABLE invites (…`.

- [ ] **Step 3: Amend `backend/db/models.py`**

Replace lines 1-10 (the module docstring and the two stdlib imports):

```python
"""ORM models — one relational schema serving SQLite (dev) and Postgres (prod).

Portability rules (both backends): generic types only (Uuid, JSON), Python-side
defaults only (uuid4, utcnow) — never server defaults. Church content cascades
to the CHURCH; authorship FKs (created_by) SET NULL so history survives a
departing author.
"""
import uuid
from datetime import datetime, timezone

```

with:

```python
"""ORM models — one relational schema serving SQLite (dev) and Postgres (prod).

Portability rules (both backends): generic types only (Uuid, JSON), Python-side
defaults (uuid4, utcnow) rather than server defaults. One exception: a NOT NULL
column added while the frozen Streamlit app still shares the database (until
slice 7) also declares a server default, because Streamlit's ORM does not map
the column and its inserts must still succeed (F §3.4; Invite.reusable,
revision 0004_invites_reusable). A new nullable column needs none. Church
content cascades to the CHURCH; authorship FKs (created_by) SET NULL so history
survives a departing author.
"""
import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
```

(the existing `from sqlalchemy import (` block follows unchanged; `sa` is used only for `sa.false()`, as S spells it.)

In `class Invite`, replace:

```python
    revoked = Column(Boolean, nullable=False, default=False)
    accepted_at = Column(DateTime(timezone=True))

    __table_args__ = (
        # NULL emails are distinct on both SQLite and Postgres, so many
```

with:

```python
    revoked = Column(Boolean, nullable=False, default=False)
    accepted_at = Column(DateTime(timezone=True))
    # Revision 0004_invites_reusable. reusable: several people may join with
    # the code until it expires or is revoked (6b sets it); frozen Streamlit's
    # inserts get the server default false. accepted_by: who consumed a
    # single-use invite (1b's accept stamps it with accepted_at).
    reusable = Column(Boolean, nullable=False, default=False, server_default=sa.false())
    accepted_by = Column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL", name="fk_invites_accepted_by_users")
    )

    __table_args__ = (
        # NULL emails are distinct on both SQLite and Postgres, so many
```

- [ ] **Step 4: Create `backend/migrations/versions/0004_invites_reusable.py`**

```python
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
```

- [ ] **Step 5: Run the tests and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_migrations.py backend/tests/test_models.py backend/tests/test_schema_check.py 2>&1 | tail -1
.venv/bin/python -m pytest -q backend/tests/test_invites_repo.py backend/tests/test_churches_repo.py streamlit_tests/test_onboarding.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
```

Expected: `30 passed, 3 skipped` (`test_migrations.py` 21 passed + 3 skipped, `test_models.py` 4, `test_schema_check.py` 5). Task 6's `test_upgrade_head_on_empty_sqlite_matches_the_models` and `test_downgrade_base_then_upgrade_head` now run through 0004 against the changed models and stay green (`schema_diff` `[]`, `alembic check` clean); Task 7's offline test from `0001_baseline` still finds no `CREATE TABLE` (on Postgres the batch emits `ALTER TABLE`, and 0004's plain `ADD COLUMN` lines are not the four `ADD COLUMN IF NOT EXISTS` it counts). The second command (the existing invite and onboarding tests, unchanged; their tables come from `init_db()` with the changed models, and `repos.invites.create_invite` now sends `reusable = False` from the Python default): `16 passed`, as at `7978a5e`. Then the suite: `652 passed, 3 skipped`.

Task 7's `test_offline_sql_from_baseline_renders_guarded_adds_and_no_create_table` stays green: it counts `ADD COLUMN IF NOT EXISTS` (4, `test_migrations.py` as written in Task 7), and 0004's two plain `ADD COLUMN` lines are not counted.

- [ ] **Step 6: Check the offline SQL that runbook step 5 will show for 0004** (read-only; no database, the URL is a dummy that is never connected)

```bash
(cd backend && ../.venv/bin/python -c "from alembic import command; from db.schema_check import alembic_config; command.upgrade(alembic_config(url='postgresql://u:p@localhost:1/x', configure_logger=False), '0003_lockdown:head', sql=True)")
```

Expected: stderr `Database: dialect=postgresql driver=psycopg2 host=localhost database=x`; stdout, blank lines between statements omitted here:

```sql
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';
-- Running upgrade 0003_lockdown -> 0004_invites_reusable
ALTER TABLE invites ADD COLUMN reusable BOOLEAN DEFAULT false NOT NULL;
ALTER TABLE invites ADD COLUMN accepted_by UUID;
ALTER TABLE invites ADD CONSTRAINT fk_invites_accepted_by_users FOREIGN KEY(accepted_by) REFERENCES users (id) ON DELETE SET NULL;
UPDATE invites SET reusable=true WHERE invites.email IS NULL;
UPDATE alembic_version SET version_num='0004_invites_reusable' WHERE alembic_version.version_num = '0003_lockdown';
COMMIT;
```

Any `CREATE TABLE` or `_alembic_tmp_invites` in that output means the batch recreated the table on Postgres: stop and report it. The downgrade renders the reverse (`'0004_invites_reusable:0003_lockdown'` with `command.downgrade`): `ALTER TABLE invites DROP CONSTRAINT fk_invites_accepted_by_users;`, `ALTER TABLE invites DROP COLUMN accepted_by;`, `ALTER TABLE invites DROP COLUMN reusable;`, then the `alembic_version` update.

- [ ] **Step 7: Commit**

```bash
git add backend/migrations/versions/0004_invites_reusable.py backend/db/models.py \
        backend/tests/test_migrations.py backend/tests/test_models.py
git commit -m "Migrations: 0004_invites_reusable and Invite.reusable/accepted_by (F §3.2, S Revisions)

invites gains reusable (NOT NULL, server default false, so frozen Streamlit's
inserts keep working) and accepted_by with the FK fk_invites_accepted_by_users
(ON DELETE SET NULL). Existing code-only invites become reusable; email-bound
ones stay single-use. Both directions use batch_alter_table: plain ALTERs on
Postgres and offline, a table recreate on SQLite. The models docstring records
the server-default rule for columns added while Streamlit runs (F §3.4).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: `revision_state`, `format_diff` and `scripts/schema_drift.py` (F §2.6 item 3; S `db/schema_check.py`, `scripts/schema_drift.py`, runbook step 6)

`alembic check` refuses a database that is not at head ("Target database is not up to date."), and production will sit at `0001_baseline` between the stamp and the merge. The drift script answers the runbook's step 6 question there: which differences remain between that database and this release's models. Its output lines are pinned here, and T24's README and T26 quote exactly these strings (clarification 25: sorted, stderr for `Database:`, exit 2 without an exported `DATABASE_URL`). `revision_state` is also what T11's startup check and T12's readiness gate read.

**Files:**
- Modify: `backend/db/schema_check.py` (T5's module: add imports to its import block; append `RevisionState`, `revision_state`, `_name`, `_type`, `_entry_lines`, `format_diff` at the end of the file)
- Create: `backend/scripts/schema_drift.py` (no `backend/scripts/__init__.py`: the directory holds scripts, not a package)
- Test: `backend/tests/test_schema_check.py` (T5's file; append the Task 10 block at the end)

**Interfaces:**
- Consumes: `db.schema_check.alembic_config(*, url: str | None = None, configure_logger: bool = True) -> alembic.config.Config`, `db.schema_check.schema_diff(conn: Connection) -> list` (T5; `schema_diff` does not run `env.py`); revisions `0001_baseline` … `0004_invites_reusable` (T6–T9; head `0004_invites_reusable`; at `0001_baseline` on SQLite the only differences from the models are T9's two `invites` columns and its FK, because T6's 0001 already creates `ix_hymns_church_hymnal`); `migrations/env.py` reads `config.attributes["url"]` before `DATABASE_URL` and prints `Database: …` to stderr (T5); `api.startup.describe_database(url: sqlalchemy.engine.URL) -> str`; `db.engine._normalize_url(url: str) -> str`.
- Produces:
  - `db.schema_check.RevisionState` — `@dataclass(frozen=True)` with `current: str | None`, `head: str | None`, `state: Literal["current", "behind", "ahead", "unknown"]` (positional order `current, head, state`). Later users: T11 (`run_startup_checks`, `app.state.schema_state`), T12 (the gate), `test_startup.py`'s spy (T11).
  - `db.schema_check.revision_state(conn: Connection) -> RevisionState` — head from `ScriptDirectory.from_config(alembic_config(configure_logger=False))` (never runs `env.py`, so it logs nothing and prints nothing); `current` from `MigrationContext.configure(conn).get_current_revision()`; `"current"` when equal, `"behind"` when `current` is `None` or a revision this release's scripts know, `"ahead"` when the scripts do not know it (a rolled-back release). It never returns `"unknown"`; only T11's wrapper does, when the check itself fails.
  - `db.schema_check.format_diff(diff: list) -> list[str]` — one line per `compare_metadata` entry, nested `modify_*` lists flattened, the result sorted: `add_table <t>`, `remove_table <t>`, `add_column <t>.<c>`, `remove_column <t>.<c>`, `add_index <name>`, `remove_index <name>`, `add_constraint <name>`, `remove_constraint <name>`, `add_fk <name>`, `remove_fk <name>`, `modify_nullable <t>.<c> <old> -> <new>`, `modify_type <t>.<c> <old> -> <new>`, `modify_default <t>.<c>`; any other entry is its `repr`. An unnamed index or constraint prints as `<table>(<col>,<col>)`.
  - `backend/scripts/schema_drift.py::main(argv: list[str] | None = None) -> int` — requires an exported `DATABASE_URL` (else stderr `DATABASE_URL is not set.`, return 2); stderr `Database: <describe_database>`; stdout `revision: <current> head: <head> state: <state>` then the `format_diff` lines; returns 0 when the diff is empty, 1 otherwise. Read-only (a `NullPool` engine, one connection, no DDL, no writes). Later users: T24 (README step 6), T26 step 4 (owner, laptop).

- [ ] **Step 1: Write the failing tests**

Append to the end of `backend/tests/test_schema_check.py` (T5 created it). The block brings its own imports and uses names T5's part does not (`EXPECTED_HEAD`, `BACKEND_DIR`, `_sqlite_file_url`, `_upgrade_to`, …), so it does not disturb T5's tests. Every Alembic call passes its URL explicitly (Global Constraints: nothing in tests relies on `DATABASE_URL`).

```python


# --- Task 10: revision_state, format_diff and scripts/schema_drift.py ---------
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from db.schema_check import (
    RevisionState,
    alembic_config,
    format_diff,
    revision_state,
    schema_diff,
)

EXPECTED_HEAD = "0004_invites_reusable"
# What a stamped production at 0001_baseline lacks (runbook step 6, sorted).
BASELINE_DRIFT = [
    "add_column invites.accepted_by",
    "add_column invites.reusable",
    "add_fk fk_invites_accepted_by_users",
]
BACKEND_DIR = Path(__file__).resolve().parents[1]
SCHEMA_DRIFT = BACKEND_DIR / "scripts" / "schema_drift.py"


def _sqlite_file_url(tmp_path, name="drift.db"):
    return f"sqlite:///{tmp_path / name}"


def _upgrade_to(url, revision):
    """In-process `alembic upgrade`, with the URL passed explicitly (never DATABASE_URL)."""
    command.upgrade(alembic_config(url=url, configure_logger=False), revision)


def _state_of(url):
    engine = create_engine(url, poolclass=NullPool)
    try:
        with engine.connect() as conn:
            return revision_state(conn)
    finally:
        engine.dispose()


def _load_schema_drift():
    """backend/scripts is not a package: load the script by path, as `python scripts/…` does."""
    spec = importlib.util.spec_from_file_location("schema_drift_under_test", SCHEMA_DRIFT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_head_is_0004_invites_reusable():
    script = ScriptDirectory.from_config(alembic_config(configure_logger=False))
    assert script.get_current_head() == EXPECTED_HEAD


def test_revision_state_on_an_empty_database_is_behind(tmp_path):
    assert _state_of(_sqlite_file_url(tmp_path)) == RevisionState(None, EXPECTED_HEAD, "behind")


def test_revision_state_at_head_is_current(tmp_path):
    url = _sqlite_file_url(tmp_path)
    _upgrade_to(url, "head")
    assert _state_of(url) == RevisionState(EXPECTED_HEAD, EXPECTED_HEAD, "current")


def test_revision_state_at_baseline_is_behind(tmp_path):
    url = _sqlite_file_url(tmp_path)
    _upgrade_to(url, "0001_baseline")
    assert _state_of(url) == RevisionState("0001_baseline", EXPECTED_HEAD, "behind")


def test_an_unknown_revision_is_ahead(tmp_path):
    """A database migrated by a newer release that was then rolled back."""
    url = _sqlite_file_url(tmp_path)
    _upgrade_to(url, "head")
    engine = create_engine(url, poolclass=NullPool)
    try:
        with engine.begin() as conn:
            conn.execute(text("UPDATE alembic_version SET version_num = '0005_from_the_future'"))
    finally:
        engine.dispose()
    assert _state_of(url) == RevisionState("0005_from_the_future", EXPECTED_HEAD, "ahead")


def test_schema_diff_at_baseline_lists_exactly_the_0004_changes(tmp_path):
    """0001_baseline stands in for production after `alembic stamp 0001_baseline`."""
    url = _sqlite_file_url(tmp_path)
    _upgrade_to(url, "0001_baseline")
    engine = create_engine(url, poolclass=NullPool)
    try:
        with engine.connect() as conn:
            assert format_diff(schema_diff(conn)) == BASELINE_DRIFT
    finally:
        engine.dispose()


def test_format_diff_renders_each_entry_kind():
    md = sa.MetaData()
    users = sa.Table("users", md, sa.Column("id", sa.Integer, primary_key=True))
    things = sa.Table(
        "things", md,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer),
        sa.Column("label", sa.String(20)),
    )
    fk = sa.ForeignKeyConstraint(["user_id"], [users.c.id], name="fk_things_user")
    things.append_constraint(fk)
    unique = sa.UniqueConstraint(things.c.label, name="uq_things_label")
    things.append_constraint(unique)
    index = sa.Index("ix_things_label", things.c.label)
    diff = [
        ("add_table", things),
        ("remove_table", users),
        ("add_column", None, "things", things.c.label),
        ("remove_column", None, "things", sa.Column("old", sa.Integer)),
        ("add_index", index),
        ("remove_index", sa.Index("ix_gone", things.c.user_id)),
        ("add_constraint", unique),
        ("remove_constraint", sa.UniqueConstraint(things.c.user_id, name="uq_gone")),
        ("add_fk", fk),
        ("remove_fk", sa.ForeignKeyConstraint(["user_id"], [users.c.id], name="fk_gone")),
        [                                              # compare_metadata nests modify_* entries
            ("modify_nullable", None, "things", "label", {}, True, False),
            ("modify_type", None, "things", "label", {}, sa.String(10), sa.String(20)),
            ("modify_default", None, "things", "label", {}, None, "x"),
        ],
        ("add_table_comment", things),                 # a kind format_diff does not know
    ]
    assert format_diff(diff) == sorted([
        "add_table things",
        "remove_table users",
        "add_column things.label",
        "remove_column things.old",
        "add_index ix_things_label",
        "remove_index ix_gone",
        "add_constraint uq_things_label",
        "remove_constraint uq_gone",
        "add_fk fk_things_user",
        "remove_fk fk_gone",
        "modify_nullable things.label True -> False",
        "modify_type things.label VARCHAR(10) -> VARCHAR(20)",
        "modify_default things.label",
        repr(("add_table_comment", things)),
    ])


def test_schema_drift_exits_1_at_baseline_and_prints_the_diff(tmp_path, monkeypatch, capsys):
    url = _sqlite_file_url(tmp_path)
    _upgrade_to(url, "0001_baseline")
    capsys.readouterr()                                   # drop env.py's own Database: line
    monkeypatch.setenv("DATABASE_URL", url)
    assert _load_schema_drift().main([]) == 1
    out, err = capsys.readouterr()
    assert out.splitlines() == [
        f"revision: 0001_baseline head: {EXPECTED_HEAD} state: behind",
        *BASELINE_DRIFT,
    ]
    assert err.startswith("Database: dialect=sqlite driver=pysqlite host=- database=")


def test_schema_drift_exits_0_at_head(tmp_path, monkeypatch, capsys):
    url = _sqlite_file_url(tmp_path)
    _upgrade_to(url, "head")
    capsys.readouterr()
    monkeypatch.setenv("DATABASE_URL", url)
    assert _load_schema_drift().main([]) == 0
    out, _err = capsys.readouterr()
    assert out.splitlines() == [f"revision: {EXPECTED_HEAD} head: {EXPECTED_HEAD} state: current"]


def test_schema_drift_refuses_without_database_url(monkeypatch, capsys):
    """Never falls back to the local SQLite default: the owner must export the URL."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert _load_schema_drift().main([]) == 2
    out, err = capsys.readouterr()
    assert (out, err) == ("", "DATABASE_URL is not set.\n")


def test_schema_drift_script_runs_from_backend(tmp_path):
    """Runbook step 6 runs `python scripts/schema_drift.py` from backend/, where
    sys.path[0] is backend/scripts; the script must still import db and api."""
    url = _sqlite_file_url(tmp_path)
    _upgrade_to(url, "head")
    env = {**os.environ, "DATABASE_URL": url}
    result = subprocess.run([sys.executable, "scripts/schema_drift.py"], cwd=BACKEND_DIR, env=env,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"revision: {EXPECTED_HEAD} head: {EXPECTED_HEAD} state: current\n"
    assert "Database: dialect=sqlite" in result.stderr
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_schema_check.py 2>&1 | tail -3`
Expected: a collection error `ImportError: cannot import name 'RevisionState' from 'db.schema_check'` and `1 error` (the whole file, T5's five tests included, fails to collect until Step 3).

- [ ] **Step 3: Add `revision_state` and `format_diff` to `backend/db/schema_check.py`**

First, the module's import block. T5 already imports `MigrationContext` (`from alembic.migration import MigrationContext`) and `Connection` (`from sqlalchemy.engine import Connection`); add the four lines it lacks: insert `from dataclasses import dataclass` above T5's `from pathlib import Path` and `from typing import Literal` below it; add the two `alembic` imports right after `from alembic.migration import MigrationContext` (the block stays sorted stdlib → third-party, alphabetically within each group):

```python
from dataclasses import dataclass
from typing import Literal

from alembic.script import ScriptDirectory
from alembic.util import CommandError
```

Then append at the end of the file:

```python


@dataclass(frozen=True)
class RevisionState:
    """Where a database stands against this release's migration scripts.

    state: "current" (at head), "behind" (no alembic_version row, or a revision
    these scripts know that is not head), "ahead" (a revision these scripts do
    not know: a newer release ran, then was rolled back) or "unknown" (the
    check itself failed; only run_startup_checks returns it).
    """
    current: str | None
    head: str | None
    state: Literal["current", "behind", "ahead", "unknown"]


def revision_state(conn: Connection) -> RevisionState:
    """Compare the database's alembic_version with this release's head.

    Reads the scripts through ScriptDirectory, so env.py never runs here (no
    logging reconfiguration, no Database: line). Raises what the database
    raises; callers that must not fail wrap it (run_startup_checks).
    """
    script = ScriptDirectory.from_config(alembic_config(configure_logger=False))
    head = script.get_current_head()
    current = MigrationContext.configure(conn).get_current_revision()
    if current == head:
        return RevisionState(current, head, "current")
    if current is None:
        return RevisionState(current, head, "behind")
    try:
        script.get_revision(current)
    except CommandError:                               # not one of this release's revisions
        return RevisionState(current, head, "ahead")
    return RevisionState(current, head, "behind")


def _name(obj) -> str:
    """An index's or constraint's name; `<table>(<cols>)` when it has none."""
    if isinstance(obj.name, str) and obj.name:
        return obj.name
    table = getattr(obj, "table", None)
    columns = ",".join(column.name for column in getattr(obj, "columns", ()))
    return f"{table.name if table is not None else '?'}({columns})"


def _type(value) -> str:
    try:
        return str(value)
    except Exception:  # noqa: BLE001 - a type that only compiles on its own dialect
        return repr(value)


def _entry_lines(entry) -> list[str]:
    if isinstance(entry, list):                        # compare_metadata nests modify_* entries
        return [line for item in entry for line in _entry_lines(item)]
    kind = entry[0] if isinstance(entry, tuple) and entry else None
    if kind in ("add_table", "remove_table"):
        return [f"{kind} {entry[1].name}"]
    if kind in ("add_column", "remove_column"):        # (kind, schema, table, Column)
        return [f"{kind} {entry[2]}.{entry[3].name}"]
    if kind in ("add_index", "remove_index", "add_constraint", "remove_constraint",
                "add_fk", "remove_fk"):
        return [f"{kind} {_name(entry[1])}"]
    if kind == "modify_nullable":                      # (kind, schema, table, column, kw, old, new)
        return [f"modify_nullable {entry[2]}.{entry[3]} {entry[5]} -> {entry[6]}"]
    if kind == "modify_type":
        return [f"modify_type {entry[2]}.{entry[3]} {_type(entry[5])} -> {_type(entry[6])}"]
    if kind == "modify_default":
        return [f"modify_default {entry[2]}.{entry[3]}"]
    return [repr(entry)]


def format_diff(diff: list) -> list[str]:
    """schema_diff() as sorted text lines, one per difference (runbook step 6)."""
    return sorted(line for entry in diff for line in _entry_lines(entry))
```

`modify_default` prints no values on purpose: a default can be long or carry data, and step 6 only needs to know that one differs.

- [ ] **Step 4: Create `backend/scripts/schema_drift.py`**

```python
"""Compare the database at DATABASE_URL with this release's models (runbook step 6).

Run from backend/ with DATABASE_URL exported in the same shell:

    ../.venv/bin/python scripts/schema_drift.py

Prints `revision: <current> head: <head> state: <state>`, then one line per
difference between the database and db/models.py (db.schema_check.format_diff),
sorted. Exit status: 0 when there is no difference, 1 when there is one, 2 when
DATABASE_URL is not set. Unlike `alembic check`, it also works on a database
that is not at head (production stamped at 0001_baseline). It only reads: no
DDL, no writes. The `Database:` line goes to stderr and never shows the
username or password.
"""
import argparse
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))   # run as a file, sys.path[0] is backend/scripts

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

from api.startup import describe_database  # noqa: E402
from db.engine import _normalize_url  # noqa: E402
from db.schema_check import format_diff, revision_state, schema_diff  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args(argv)
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        return 2
    engine = create_engine(_normalize_url(url), poolclass=NullPool)
    print(f"Database: {describe_database(engine.url)}", file=sys.stderr)
    try:
        with engine.connect() as conn:
            state = revision_state(conn)
            diff = schema_diff(conn)
    finally:
        engine.dispose()
    print(f"revision: {state.current} head: {state.head} state: {state.state}")
    for line in format_diff(diff):
        print(line)
    return 1 if diff else 0


if __name__ == "__main__":
    sys.exit(main())
```

The script never calls `load_dotenv()`: a laptop run must name its database by exporting `DATABASE_URL` in that shell (Global Constraints, owner laptop commands), never by whatever `backend/.env` holds. `api.startup` imports only `api.settings` and SQLAlchemy, so the script pulls in no FastAPI app.

- [ ] **Step 5: Run the tests, the script by hand, and the suite**

Run:
```bash
.venv/bin/python -m pytest -q backend/tests/test_schema_check.py 2>&1 | tail -3
(env -u DATABASE_URL .venv/bin/python backend/scripts/schema_drift.py; echo "exit $?")
.venv/bin/python -m pytest -q | tail -1
```
Expected: `16 passed` (T5's 5 + these 11); then `DATABASE_URL is not set.` and `exit 2` (the script also imports cleanly when started from the repo root); then `663 passed, 3 skipped`.

- [ ] **Step 6: Commit**

```bash
git add backend/db/schema_check.py backend/scripts/schema_drift.py backend/tests/test_schema_check.py
git commit -m "Schema: revision_state, format_diff and scripts/schema_drift.py (F §2.6 item 3, S runbook step 6)

revision_state compares alembic_version with this release's head (current,
behind, ahead) without running env.py. schema_drift.py prints the revision
line and one sorted line per difference from the models, exits 0/1, and
refuses to run without an exported DATABASE_URL (exit 2), so the owner's
runbook step 6 can compare its output with the README word for word.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: Lifespan without `create_all`; revision and RLS startup checks (F §2.6 items 3–4, §3.3; S Modules changed → `api/main.py`; AC3)

Alembic owns the schema from here on, so the API lifespan stops calling `init_db()` (`db.init_db` itself stays: Streamlit, the CLIs, `conftest.tmp_db` and `pg_smoke.py` still use it). In its place the lifespan runs `run_startup_checks`: it logs how the database's revision compares with head (WARNING; ERROR for `behind` in production), stores the result on `app.state.schema_state` for T12's gate, and on Postgres names every `public` table without row-level security. Neither check ever blocks startup. `test_startup.py` spied on `api.main.init_db` to prove "the guards run before anything touches the database"; its spy moves to `api.main.run_startup_checks`, the first code that now touches the database (clarification 4). The spy also keeps `test_production_warns_when_cors_allows_only_localhost` from connecting to its `localhost:1` engine, which would log an ERROR. The Postgres half of the RLS check only runs in CI (Global Constraints: Postgres is CI-only); it first executes at T14's draft-PR checkpoint.

**Files:**
- Modify: `backend/api/main.py:15` (imports), `:23-33` (lifespan: parameter `app`, `init_db()` → `run_startup_checks`)
- Modify: `backend/db/schema_check.py` (add three imports and a module logger; append `rls_disabled_tables`, `run_startup_checks`, `_check_revision`, `_check_rls`)
- Test: `backend/tests/test_api_app.py` (append the Task 11 block after T3's tests), `backend/tests/test_startup.py:10-11` (import), `:28-33` (fixture `init_db_calls` → `schema_check_calls`), `:61-74` and `:95-110` (the three tests that used it)

**Interfaces:**
- Consumes: `RevisionState`, `revision_state(conn)` (T10); `alembic_config` (T5, through `revision_state`); fixtures `tmp_db`, `pg_db` (T1: skips without `TEST_DATABASE_URL`; binds the engine; the database is at head); `pytest.mark.postgres` (T1); `api.settings.Settings.is_production`; `db.reset_engine_for_tests(url) -> Engine`.
- Produces:
  - `db.schema_check.rls_disabled_tables(conn: Connection) -> list[str]` — `public` tables with `rowsecurity = false`, sorted (Postgres only; `pg_tables` does not exist on SQLite).
  - `db.schema_check.run_startup_checks(engine: Engine, *, is_production: bool) -> RevisionState` — never raises. Revision check: WARNING `schema revision <current> != head <head>` when the state is not `current`, at ERROR instead when `is_production` and the state is `behind`; a failure logs ERROR `Schema revision check failed: <ExceptionClass>` (class name only: driver messages can carry host names) and returns `RevisionState(None, None, "unknown")`. RLS check, on Postgres only: WARNING `Row-level security is off on: <t1>, <t2>`; a failure logs ERROR `Row-level security check failed: <ExceptionClass>`. Logger `db.schema_check`. Never runs `env.py`.
  - `api.main` imports `run_startup_checks` by name, so tests monkeypatch `api.main.run_startup_checks`; the lifespan sets `app.state.schema_state: RevisionState`. Later users: T12 (`/health/ready` gate reads `app.state.schema_state`), T25 (local smoke expects the WARNING on an un-migrated file and none at head).

- [ ] **Step 1: Write the failing tests (`test_api_app.py`)**

Append to the end of `backend/tests/test_api_app.py` (after T3's block). `TestClient`, `create_app` and `settings_mod` are already imported at the top of the file.

```python


# --- Task 11: no create_all in the lifespan; revision and RLS startup checks ---
import logging
import uuid

import pytest
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import text

import db.schema_check
from db.schema_check import RevisionState, rls_disabled_tables, run_startup_checks

SCHEMA_HEAD = "0004_invites_reusable"
BEHIND_WARNING = f"schema revision None != head {SCHEMA_HEAD}"


@pytest.fixture
def fresh_sqlite(tmp_path, monkeypatch):
    """A development app on an empty SQLite file: no tables and no alembic_version."""
    from db import reset_engine_for_tests

    monkeypatch.setenv("APP_ENV", "development")
    settings_mod.get_settings.cache_clear()
    engine = reset_engine_for_tests(f"sqlite:///{tmp_path / 'fresh.db'}")
    yield engine
    engine.dispose()
    settings_mod.get_settings.cache_clear()


def _schema_check_records(caplog):
    return [(r.levelno, r.getMessage()) for r in caplog.records if r.name == "db.schema_check"]


def test_lifespan_creates_no_tables(fresh_sqlite):
    with TestClient(create_app()):
        pass
    assert sa_inspect(fresh_sqlite).get_table_names() == []


def test_startup_warns_on_a_revision_mismatch_without_errors(fresh_sqlite, caplog):
    """The WARNING names head 0004, so the check found the scripts; no ERROR means it did not fail."""
    app = create_app()
    with caplog.at_level(logging.INFO):
        with TestClient(app):
            pass
    assert _schema_check_records(caplog) == [(logging.WARNING, BEHIND_WARNING)]
    assert [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR] == []
    assert app.state.schema_state == RevisionState(None, SCHEMA_HEAD, "behind")


def test_rls_check_is_skipped_on_sqlite(fresh_sqlite, monkeypatch):
    calls = []
    monkeypatch.setattr(db.schema_check, "rls_disabled_tables", lambda conn: calls.append(conn) or [])
    with TestClient(create_app()):
        pass
    assert calls == []


def test_production_logs_behind_at_error(fresh_sqlite, caplog):
    """In production a behind schema is an ERROR (and /health/ready's gate turns it into a 503)."""
    with caplog.at_level(logging.INFO):
        state = run_startup_checks(fresh_sqlite, is_production=True)
    assert state == RevisionState(None, SCHEMA_HEAD, "behind")
    assert _schema_check_records(caplog) == [(logging.ERROR, BEHIND_WARNING)]


def test_a_failing_schema_check_logs_error_and_starts(fresh_sqlite, monkeypatch, caplog):
    def broken(_conn):
        raise RuntimeError("password=s3cret host=db.internal")

    monkeypatch.setattr(db.schema_check, "revision_state", broken)
    app = create_app()
    with caplog.at_level(logging.INFO):
        with TestClient(app) as client:
            assert client.get("/health").status_code == 200
    errors = [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR]
    assert errors == ["Schema revision check failed: RuntimeError"]    # the class only
    assert "s3cret" not in caplog.text
    assert app.state.schema_state == RevisionState(None, None, "unknown")


@pytest.mark.postgres
def test_rls_check_names_tables_without_rls(pg_db, caplog):
    """After the CI alembic cycle 0003 has enabled RLS on every public table, so
    the test adds its own table without RLS and drops it again."""
    probe = f"wsb_rls_probe_{uuid.uuid4().hex[:8]}"
    with pg_db.begin() as conn:
        conn.execute(text(f"CREATE TABLE public.{probe} (id integer PRIMARY KEY)"))
    try:
        with pg_db.connect() as conn:
            assert rls_disabled_tables(conn) == [probe]
        with caplog.at_level(logging.INFO):
            state = run_startup_checks(pg_db, is_production=False)
        assert state == RevisionState(SCHEMA_HEAD, SCHEMA_HEAD, "current")
        assert _schema_check_records(caplog) == [
            (logging.WARNING, f"Row-level security is off on: {probe}")]
    finally:
        with pg_db.begin() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS public.{probe}"))
```

`fresh_sqlite` sets `APP_ENV=development` itself, so a developer's `backend/.env` (loaded by `api.main`'s `load_dotenv()`) cannot turn these into production starts. The Postgres test creates its probe table in the database `pg_db` bound; the fixture truncates only rows, never RLS flags, so every model table still has RLS from 0003.

- [ ] **Step 2: Move `test_startup.py`'s spy to the schema check**

In `backend/tests/test_startup.py`, replace:

```python
from api.startup import check_app_env, describe_database
from db.engine import _make_engine
```

with:

```python
from api.startup import check_app_env, describe_database
from db.engine import _make_engine
from db.schema_check import RevisionState
```

Replace the fixture:

```python
@pytest.fixture
def init_db_calls(monkeypatch):
    """Replace api.main.init_db with a spy; the list records each call."""
    calls = []
    monkeypatch.setattr(api.main, "init_db", lambda: calls.append("init_db"))
    return calls
```

with:

```python
@pytest.fixture
def schema_check_calls(monkeypatch):
    """Replace api.main.run_startup_checks with a spy: the first code that touches
    the database (slice 1). The list records each call's is_production."""
    calls = []

    def spy(_engine, *, is_production):
        calls.append(is_production)
        return RevisionState("0004_invites_reusable", "0004_invites_reusable", "current")

    monkeypatch.setattr(api.main, "run_startup_checks", spy)
    return calls
```

Replace:

```python
def test_production_refuses_sqlite_before_init_db(api_env, tmp_db, init_db_calls):
    api_env.setenv("APP_ENV", "production")
    with pytest.raises(RuntimeError) as exc:
        _start(api.main.create_app())
    assert str(exc.value) == SQLITE_REFUSED
    assert init_db_calls == []


def test_an_invalid_app_env_refuses_to_start(api_env, tmp_db, init_db_calls):
    api_env.setenv("APP_ENV", "staging")
    with pytest.raises(RuntimeError) as exc:
        _start(api.main.create_app())
    assert str(exc.value) == "APP_ENV must be 'development' or 'production' (got 'staging')."
    assert init_db_calls == []
```

with:

```python
def test_production_refuses_sqlite_before_the_schema_check(api_env, tmp_db, schema_check_calls):
    api_env.setenv("APP_ENV", "production")
    with pytest.raises(RuntimeError) as exc:
        _start(api.main.create_app())
    assert str(exc.value) == SQLITE_REFUSED
    assert schema_check_calls == []


def test_an_invalid_app_env_refuses_to_start(api_env, tmp_db, schema_check_calls):
    api_env.setenv("APP_ENV", "staging")
    with pytest.raises(RuntimeError) as exc:
        _start(api.main.create_app())
    assert str(exc.value) == "APP_ENV must be 'development' or 'production' (got 'staging')."
    assert schema_check_calls == []
```

In `test_production_warns_when_cors_allows_only_localhost`, replace the signature line:

```python
def test_production_warns_when_cors_allows_only_localhost(api_env, monkeypatch, caplog, init_db_calls,
                                                          origins, logs_error):
```

with:

```python
def test_production_warns_when_cors_allows_only_localhost(api_env, monkeypatch, caplog, schema_check_calls,
                                                          origins, logs_error):
```

and its last line:

```python
    assert init_db_calls == ["init_db"]
```

with:

```python
    assert schema_check_calls == [True]
```

`test_startup_logs_the_database_target` and `test_development_on_sqlite_starts_without_errors` stay as they are and now run the real check on `tmp_db` (create_all tables, no `alembic_version`): it logs a WARNING, never an ERROR, and no second `Database:` line, because `revision_state` never runs `env.py`. The file keeps its 14 tests.

- [ ] **Step 3: Run the tests to verify they fail**

Run:
```bash
.venv/bin/python -m pytest -q backend/tests/test_api_app.py 2>&1 | tail -3
.venv/bin/python -m pytest -q backend/tests/test_startup.py 2>&1 | tail -3
```
Expected: first a collection error `ImportError: cannot import name 'rls_disabled_tables' from 'db.schema_check'` and `1 error`; then `8 passed, 6 errors`: the six tests that use `schema_check_calls` error in setup with `AttributeError: <module 'api.main' …> has no attribute 'run_startup_checks'`.

- [ ] **Step 4: Add the startup checks to `backend/db/schema_check.py`**

Add to the module's import block (T5 and T10 already import `Connection` from `sqlalchemy.engine`; extend that line to `from sqlalchemy.engine import Connection, Engine`):

```python
import logging

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine
```

Directly below the import block, add:

```python
logger = logging.getLogger(__name__)
```

Append at the end of the file:

```python


def rls_disabled_tables(conn: Connection) -> list[str]:
    """`public` tables with row-level security off, sorted (Postgres only)."""
    rows = conn.execute(text(
        "SELECT tablename FROM pg_tables "
        "WHERE schemaname = 'public' AND NOT rowsecurity ORDER BY tablename"))
    return [row[0] for row in rows]


def run_startup_checks(engine: Engine, *, is_production: bool) -> RevisionState:
    """The API lifespan's schema checks (F §2.6 items 3-4). Logs; never raises.

    Revision: WARNING `schema revision X != head Y` when the database is not at
    head (ERROR when it is behind in production, where /health/ready then
    answers 503). RLS, on Postgres only: WARNING naming every public table with
    row-level security off. A check that fails logs an ERROR with the exception
    class only and startup goes on; the revision state is then "unknown".
    """
    state = _check_revision(engine, is_production=is_production)
    if engine.dialect.name == "postgresql":
        _check_rls(engine)
    return state


def _check_revision(engine: Engine, *, is_production: bool) -> RevisionState:
    try:
        with engine.connect() as conn:
            if conn.dialect.name == "postgresql":
                # Same bound as the ops probe (db/health.py): a lock on
                # alembic_version must not stall startup.
                conn.exec_driver_sql("SET LOCAL statement_timeout = '5s'")
            state = revision_state(conn)
    except Exception as exc:  # noqa: BLE001 - a failed check never blocks startup
        logger.error("Schema revision check failed: %s", type(exc).__name__)
        return RevisionState(None, None, "unknown")
    if state.state != "current":
        level = logging.ERROR if is_production and state.state == "behind" else logging.WARNING
        logger.log(level, "schema revision %s != head %s", state.current, state.head)
    return state


def _check_rls(engine: Engine) -> None:
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SET LOCAL statement_timeout = '5s'")
            tables = rls_disabled_tables(conn)
    except Exception as exc:  # noqa: BLE001 - a failed check never blocks startup
        logger.error("Row-level security check failed: %s", type(exc).__name__)
        return
    if tables:
        logger.warning("Row-level security is off on: %s", ", ".join(tables))
```

`db/` still imports no `fastapi`/`starlette` and nothing from `api/` (Global Constraints). Both checks bound their SQL with `SET LOCAL statement_timeout = '5s'` on Postgres, like the ops probe (`db/health.py:53`); `SET LOCAL` runs in the transaction SQLAlchemy autobegins, which the `with engine.connect()` exit rolls back. An `ahead` state is a WARNING even in production: expand-only migrations keep an older release working, so a Railway rollback is not an error.

- [ ] **Step 5: Replace `init_db()` in the lifespan (`backend/api/main.py`)**

Replace line 15:

```python
from db import get_engine, init_db
```

with:

```python
from db import get_engine
from db.schema_check import run_startup_checks
```

Replace the lifespan (lines 23-33):

```python
@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    check_app_env(settings.app_env)
    engine = get_engine()                                   # creating the engine opens no connection
    logger.info("Database: %s", describe_database(engine.url))
    enforce_production_guards(settings, engine)             # before anything touches the database
    init_db()   # create_all: no-op on existing tables, creates them for local SQLite; removed in slice 1
    if not settings.supabase_url:
        logger.warning("SUPABASE_URL is not set; every authenticated request will return 503.")
    yield
```

with:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    check_app_env(settings.app_env)
    engine = get_engine()                                   # creating the engine opens no connection
    logger.info("Database: %s", describe_database(engine.url))
    enforce_production_guards(settings, engine)             # before anything touches the database
    # Alembic owns the schema (F §3.3): no create_all here. Logs, never raises;
    # /health/ready reads the state (Task 12's gate).
    app.state.schema_state = run_startup_checks(engine, is_production=settings.is_production)
    if not settings.supabase_url:
        logger.warning("SUPABASE_URL is not set; every authenticated request will return 503.")
    yield
```

A fresh local SQLite database now has no tables until `cd backend && ../.venv/bin/alembic upgrade head` (T24 documents it in README "## Database"); every test that needs tables already uses `tmp_db`, which still calls `init_db()`.

- [ ] **Step 6: Run the tests and the suite**

Run:
```bash
.venv/bin/python -m pytest -q backend/tests/test_api_app.py backend/tests/test_startup.py 2>&1 | tail -3
.venv/bin/python -m pytest -q | tail -1
```
Expected: `40 passed, 1 skipped` (`test_api_app.py` 26 = 21 after T3 + 5, `test_startup.py` 14; the skip is `test_rls_check_names_tables_without_rls` without `TEST_DATABASE_URL`); then `668 passed, 4 skipped`.

- [ ] **Step 7: Commit**

```bash
git add backend/api/main.py backend/db/schema_check.py \
        backend/tests/test_api_app.py backend/tests/test_startup.py
git commit -m "API startup: no create_all; revision and RLS checks log and set app.state.schema_state (F §2.6 items 3-4, §3.3)

The lifespan no longer creates tables: Alembic owns the schema. After the
production guards it runs db.schema_check.run_startup_checks, which logs
'schema revision X != head Y' (ERROR when behind in production), names every
public table without row-level security on Postgres, never raises, and
returns the state /health/ready's gate will read. test_startup's spy moves
from init_db to run_startup_checks.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 12: Readiness gate on a schema behind head, `db_unavailable` parameters, `backend/railway.toml` (F §2.6 item 5, §3.3 as amended; S `routes/health.py`, `railway.toml`; AC3)

In production, a release that starts on a schema behind its head must not go live: `/health/ready` answers 503 `db_unavailable` with `details.reason = "schema_behind"`, so Railway's deploy health check (moved to `/health/ready` by `railway.toml`, and in the UI by T26, owner Q4) fails the deploy and the previous release keeps serving; if Railway ever ignores the file, keepalive's daily curl of `/health/ready` turns red. The gate reads the state the lifespan fixed at startup (T11) and runs **before** ops' memoized `SELECT 1`, so a remembered good probe can never hide it. `ahead` (a rolled-back release on an expand-only schema) and `unknown` (the check itself failed; its ERROR is in the log) stay 200, and outside production nothing changes. The route stays a sync `def` with no `try` and no SQLAlchemy import (`test_health_ready.py:75`, `:79-84`), and it stays the recorded F §2.2 exception that raises `ApiError` through `db_unavailable`.

**Files:**
- Modify: `backend/api/routes/health.py` (whole file, 36 lines: docstring, `Request` and `get_settings` imports, the gate in `ready`)
- Modify: `backend/api/errors.py` — `db_unavailable` (`:43-45` at `7978a5e`; T3's edits above it shift the line numbers, so find it by its text)
- Create: `backend/railway.toml`
- Test: `backend/tests/test_health_ready.py` (append the Task 12 block), `backend/tests/test_foundation_setup.py` (append one test)

**Interfaces:**
- Consumes: `RevisionState` (T10); `app.state.schema_state` set by the lifespan (T11) — absent whenever a test builds `TestClient(create_app())` without `with`, so the gate treats a missing state as "not behind"; `ApiError(status, code, message, *, details: Optional[dict[str, Any]] = None)` and `_body(..., details=...)` omitting `details` when it is `None` (T3); `api.settings.get_settings().is_production`; fixture `probes` (`test_health_ready.py:24-38`, counts `db.health._probe` calls).
- Produces:
  - `api.errors.db_unavailable(message: str = "The database is not reachable.", *, details: Optional[dict[str, Any]] = None) -> ApiError` (503 `db_unavailable`; the existing no-argument call keeps its body, without `details`).
  - `GET /health/ready`: `ready(request: Request) -> ReadyOut`; with `APP_ENV=production` and `app.state.schema_state.state == "behind"` → 503 `{"error": {"code": "db_unavailable", "message": "The database schema is behind this release.", "request_id": …, "details": {"reason": "schema_behind", "current": <current>, "head": <head>}}}`.
  - `backend/railway.toml`: `[deploy] preDeployCommand = ["alembic upgrade head"]`, `healthcheckPath = "/health/ready"`; read by Railway only when the service's Config-as-code path is `/backend/railway.toml` (set by the owner in Task 26 Step 15, runbook step 7). Later users: T24 (README steps 7–8), T26, T27.

- [ ] **Step 1: Write the failing tests**

Append to the end of `backend/tests/test_health_ready.py` (`pytest`, `TestClient`, `create_app` and the `probes` fixture are already in the file):

```python


# --- Task 12: the production schema gate (slice 1a, F §2.6 item 5) -----------

from api import settings as settings_mod
from db.schema_check import RevisionState

SCHEMA_HEAD = "0004_invites_reusable"


@pytest.fixture
def app_env(monkeypatch):
    """Set APP_ENV for this test; get_settings() re-reads it."""
    def set_app_env(value):
        monkeypatch.setenv("APP_ENV", value)
        settings_mod.get_settings.cache_clear()

    yield set_app_env
    settings_mod.get_settings.cache_clear()


def _app_with_state(state):
    """An app whose lifespan left `state` (None: the lifespan never ran)."""
    app = create_app()
    if state is not None:
        app.state.schema_state = state
    return app


def test_gate_503_when_production_and_behind(app_env, probes):
    app_env("production")
    app = _app_with_state(RevisionState("0001_baseline", SCHEMA_HEAD, "behind"))
    r = TestClient(app).get("/health/ready")
    assert r.status_code == 503
    assert r.json() == {"error": {
        "code": "db_unavailable",
        "message": "The database schema is behind this release.",
        "request_id": r.headers["x-request-id"],
        "details": {"reason": "schema_behind", "current": "0001_baseline", "head": SCHEMA_HEAD},
    }}
    assert probes.calls == 0                      # the gate answers before the probe


@pytest.mark.parametrize("state", [
    RevisionState("0005_from_a_newer_release", SCHEMA_HEAD, "ahead"),
    RevisionState(None, None, "unknown"),
    None,
], ids=["ahead", "unknown", "unset"])
def test_gate_passes_ahead_unknown_and_unset(app_env, probes, state):
    app_env("production")
    r = TestClient(_app_with_state(state)).get("/health/ready")
    assert r.status_code == 200
    assert r.json() == {"ok": True, "db": "ok"}


def test_gate_does_nothing_outside_production(app_env, probes):
    app_env("development")
    app = _app_with_state(RevisionState(None, SCHEMA_HEAD, "behind"))
    r = TestClient(app).get("/health/ready")
    assert r.status_code == 200
    assert r.json() == {"ok": True, "db": "ok"}


def test_gate_runs_before_the_memoized_probe(app_env, probes):
    """A remembered good probe never hides a schema that is behind."""
    app_env("production")
    app = _app_with_state(RevisionState(SCHEMA_HEAD, SCHEMA_HEAD, "current"))
    client = TestClient(app)
    assert client.get("/health/ready").status_code == 200
    assert probes.calls == 1                      # the memo now holds a success for 10 s
    app.state.schema_state = RevisionState("0003_lockdown", SCHEMA_HEAD, "behind")
    r = client.get("/health/ready")
    assert r.status_code == 503
    assert r.json()["error"]["details"]["reason"] == "schema_behind"
    assert probes.calls == 1
```

Append to the end of `backend/tests/test_foundation_setup.py`:

```python


# --- slice 1a: Railway config-as-code (S backend/railway.toml, F §3.3) --------

def test_railway_toml_runs_migrations_and_checks_readiness():
    import tomllib

    config = tomllib.loads((ROOT / "backend" / "railway.toml").read_text(encoding="utf-8"))
    # Exactly these two settings: the start command stays in backend/Procfile.
    assert config == {"deploy": {
        "preDeployCommand": ["alembic upgrade head"],
        "healthcheckPath": "/health/ready",
    }}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_health_ready.py backend/tests/test_foundation_setup.py 2>&1 | tail -5`
Expected: `3 failed, 30 passed`. `test_gate_503_when_production_and_behind` and `test_gate_runs_before_the_memoized_probe` fail with `assert 200 == 503` (no gate yet); `test_railway_toml_runs_migrations_and_checks_readiness` fails with `FileNotFoundError` for `backend/railway.toml`. The three `test_gate_passes_ahead_unknown_and_unset` cases and `test_gate_does_nothing_outside_production` pass as soon as they are written: they pin the cases the gate must leave alone, and they would fail on a gate that checked `state != "current"` or ignored `APP_ENV`.

- [ ] **Step 3: Give `db_unavailable` a message and details (`backend/api/errors.py`)**

Replace:

```python
def db_unavailable() -> ApiError:
    """503 from GET /health/ready only (F §1.5 registry; the recorded F §2.2 exception)."""
    return ApiError(503, "db_unavailable", "The database is not reachable.")
```

with:

```python
def db_unavailable(message: str = "The database is not reachable.", *,
                   details: Optional[dict[str, Any]] = None) -> ApiError:
    """503 from GET /health/ready only (F §1.5 registry; the recorded F §2.2 exception).

    The schema gate passes its own message and
    details={"reason": "schema_behind", "current": ..., "head": ...}.
    """
    return ApiError(503, "db_unavailable", message, details=details)
```

- [ ] **Step 4: Add the gate (`backend/api/routes/health.py`)**

Replace the whole file with:

```python
"""Infrastructure probes: GET /health (liveness) and GET /health/ready (readiness).

Recorded exception to F §2.2 items 1 and 4 (ops spec, API): these are probes,
not domain operations, so there is no usecase and no DomainError. The route
calls one db-layer function, db.health.database_ready(), which holds the SQL,
the try/except and the memo, and raises ApiError through db_unavailable().
Slice 1's production schema gate comes first: it reads the revision state the
lifespan stored on app.state (db.schema_check.run_startup_checks), so the
probe's memo can never hide a schema that is behind this release.
"""
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel

from api.errors import db_unavailable
from api.settings import get_settings
from db.health import database_ready

router = APIRouter()


class ReadyOut(BaseModel):
    ok: bool
    db: Literal["ok"]


@router.get("/health")
def health() -> dict:
    """Liveness: never touches the database. Railway's deploy health check is /health/ready (railway.toml)."""
    return {"ok": True}


@router.get("/health/ready", response_model=ReadyOut)
def ready(request: Request) -> ReadyOut:
    """Readiness (Railway's deploy health check and keepalive.yml): 503 db_unavailable
    when, in production, the schema is behind this release, or when the database
    is not reachable. `ahead`, `unknown` and an unset state (no lifespan) pass."""
    state = getattr(request.app.state, "schema_state", None)
    if get_settings().is_production and state is not None and state.state == "behind":
        raise db_unavailable(
            "The database schema is behind this release.",
            details={"reason": "schema_behind", "current": state.current, "head": state.head},
        )
    if not database_ready():
        raise db_unavailable()
    return ReadyOut(ok=True, db="ok")
```

- [ ] **Step 5: Create `backend/railway.toml`**

```toml
# Railway config-as-code for the API service (slice 1a, F §3.3).
# Railway reads this file only when the service's Settings → Config-as-code
# path is /backend/railway.toml: it does not look under the service's root
# directory (backend/migrations/README.md, step 7). The start command stays in
# backend/Procfile.
[deploy]
preDeployCommand = ["alembic upgrade head"]
healthcheckPath = "/health/ready"
```

The pre-deploy command runs in the service's root directory (`backend/`), where `alembic.ini` lives; `env.py` reads Railway's `DATABASE_URL` there (T5).

- [ ] **Step 6: Run the tests and the suite**

Run:
```bash
.venv/bin/python -m pytest -q backend/tests/test_health_ready.py backend/tests/test_foundation_setup.py 2>&1 | tail -3
.venv/bin/python -m pytest -q | tail -1
```
Expected: `33 passed` (`test_health_ready.py` 16 = 10 + 6, `test_foundation_setup.py` 17 = 16 after T7 + 1), then `675 passed, 4 skipped`. `test_ready_is_503_db_unavailable_when_the_database_is_unreachable` still sees the exact ops body without a `details` key, and `test_the_route_module_holds_no_sql_and_no_try` still passes (the gate is a plain `if`).

- [ ] **Step 7: Commit**

```bash
git add backend/api/routes/health.py backend/api/errors.py backend/railway.toml \
        backend/tests/test_health_ready.py backend/tests/test_foundation_setup.py
git commit -m "Readiness: 503 schema_behind in production before the probe; railway.toml (F §2.6 item 5, §3.3)

/health/ready answers 503 db_unavailable 'The database schema is behind this
release.' with details {reason: schema_behind, current, head} when APP_ENV is
production and the startup check found the schema behind head; ahead,
unknown and an unset state pass. railway.toml runs 'alembic upgrade head' as
the pre-deploy command and makes /health/ready the deploy health check once
the service's Config-as-code path points at it.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 13: Route guards, the isolation helper, the OpenAPI export and contract, no Streamlit behind `api.main` (F §1.2 rules 4–5, §1.11, §2.2 item 6; S test_route_guards, api_helpers, export_openapi; AC4, AC5, AC16)

Four guards that every later slice leans on. (1) `test_route_guards.py` lists every `(method, path)` the app serves with every dependency FastAPI runs for it and fails on any route outside `PUBLIC`/`USER_SCOPED` without `require_church` in its tree. FastAPI 0.141 keeps included routers nested (`app.routes` holds `_IncludedRouter`s with no path), so the walk uses `fastapi.routing.iter_route_contexts(app.routes)` and reads `ctx.dependant` — unlike `ctx.route.dependant` it includes `include_router(dependencies=…)` (clarification 5; checked on 0.141.1: a walker on `ctx.route.dependant` fails `test_the_walker_sees_router_level_dependencies`). Two self-tests build apps with a deliberately unguarded route and a router-level guard, so the walker can never pass vacuously. (2) `tests/api_helpers.py` gives every church-scoped route its cross-church isolation test; on main today that is `GET /church`, `GET /rubric` and `PATCH /rubric` (clarification 6: S's "`GET /church` stays the only church-scoped route" is stale since PR #4). None of them names a resource id, so they exercise the 403 half and the control; `resource_path_b` is for 1b onward. (3) `backend/scripts/export_openapi.py` writes `frontend/src/lib/api/openapi.json`; `test_openapi_contract.py` fails while the committed text differs from the live schema and prints the command. The tests never write the committed file (they compare text or write to `tmp_path`, critique 7). (4) `test_no_streamlit_in_core.py` imports `api.main`, every module in `api/routes` and builds the app in a subprocess (F §2.2 item 6; `test_api_app.py:109` stays, it checks the bare import).

The committed snapshot is taken after T3 (every API route (`/me`, `/church`, `/rubric` GET and PATCH) declares `responses=error_responses(...)` and the two probes declare none (clarification 34), so FastAPI's `HTTPValidationError` is gone and `ErrorBody`/`ErrorDetail` appear) and T12 (the `ready(request: Request)` signature adds no parameter to the schema). No later 1a task changes a route, so this snapshot is the one T15's `gen:api` reads. Nothing in this task touches the frontend's code: `frontend/src/lib/api/` starts as a directory next to the existing `frontend/src/lib/api.ts` (T16 moves the client into it); `@/lib/api` still resolves to `api.ts`, and ESLint and `tsc` do not read `.json` files.

**Files:**
- Create: `backend/tests/test_route_guards.py`
- Create: `backend/tests/api_helpers.py`
- Create: `backend/tests/test_isolation.py`
- Create: `backend/scripts/export_openapi.py` (no `backend/scripts/__init__.py`, as in T10: the directory holds scripts, not a package)
- Create: `backend/tests/test_openapi_contract.py`
- Create: `frontend/src/lib/api/openapi.json` (generated by the script in Step 5; never edited by hand)
- Modify: `backend/tests/test_no_streamlit_in_core.py` (append after T2's `test_usecases_package_imports_no_fastapi_or_streamlit`, the end of the file)

**Interfaces:**
- Consumes: `api.main.create_app() -> FastAPI`; `api.deps.get_current_user`, `require_church`, `require_admin`, `get_verifier`; `api.security.TokenVerifier(key_resolver, issuer=...)`; `tests.jwt_helpers.make_token(*, email=...)`, `ISSUER`, `SIGNING_KEY`; conftest fixtures `tmp_db`, `make_user(email=...) -> uuid.UUID`, `make_church(name=..., owner_user_id=...) -> uuid.UUID`; T3's `require_church` 403 body `{"code": "forbidden", "message": "You don't have access to this church.", "details": {"reason": "no_church_access"}}` (plus `request_id`) and `error_responses(...)` on all four API routes; `service_rubric.default_rubric()`; `fastapi.routing.iter_route_contexts` (FastAPI 0.141.1, pinned `==0.141.*` by T1).
- Produces:
  - `tests/test_route_guards.py`: `PUBLIC = {("GET", "/health"), ("GET", "/health/ready"), ("GET", "/openapi.json"), ("GET", "/docs"), ("GET", "/docs/oauth2-redirect"), ("GET", "/redoc")}`; `USER_SCOPED = {("GET", "/me")}` (1b adds `("POST", "/churches")`, `("POST", "/invites/preview")`, `("POST", "/invites/accept")` in the same PR as the routes); `route_dependencies(app: FastAPI) -> dict[tuple[str, str], set[Callable[..., Any]]]` (HEAD ignored; a route with no methods is `"ANY"`; a plain Starlette route has no dependencies); `unguarded_routes(app: FastAPI) -> list[tuple[str, str]]` (sorted).
  - `tests/api_helpers.py`: `auth_headers(email: str) -> dict[str, str]`; `church_headers(email: str, church_id: uuid.UUID) -> dict[str, str]`; `make_api_client() -> TestClient` (addition to the outline: a fresh `create_app()` whose verifier trusts `tests.jwt_helpers.SIGNING_KEY`; lifespan not run); `NO_CHURCH_ACCESS: dict` (the 403 error minus `request_id`); `@dataclass(frozen=True) IsolationWorld(church_a: uuid.UUID, church_b: uuid.UUID, a: str = "a@example.com", b: str = "b@example.com", outsider: str = "o@example.com")`; fixture `isolation_world(tmp_db, make_user, make_church) -> IsolationWorld` (a@ owns church A, b@ owns church B, the outsider is a user in neither; test modules import the fixture by name); `assert_church_isolated(client: TestClient, method: str, path: str, *, world: IsolationWorld, json: Any = None, resource_path_b: str | None = None) -> None` — (1) outsider and a@ with `X-Church-Id = B` → 403 with exactly `NO_CHURCH_ACCESS`; (2) with `resource_path_b`, a@ with `X-Church-Id = A` → 404 `not_found`; (3) control, last: a@ with `X-Church-Id = A` on `path` → not 401/403/404. Later users: 1b, 2, 3, 5a, 6a, 6b, reviewer.
  - `backend/scripts/export_openapi.py`: `DEFAULT_OUT = <repo>/frontend/src/lib/api/openapi.json`; `render_openapi() -> str` (`json.dumps(create_app().openapi(), sort_keys=True, indent=2) + "\n"`); `write_openapi(path: Path) -> None` (creates parent dirs); `main(argv: list[str] | None = None) -> int` with `--out PATH` (default `DEFAULT_OUT`), prints `Wrote <path>`, returns 0. Later users: T15 (`gen:api` reads the file), T25 (`export_openapi.py && git diff --exit-code frontend/src/lib/api/openapi.json`), every slice that changes the API.
  - `frontend/src/lib/api/openapi.json`: paths `/church`, `/health`, `/health/ready`, `/me`, `/rubric`; schemas `ChurchOut`, `ErrorBody`, `ErrorDetail`, `MeOut`, `ReadyOut`, `RubricModel`, `RubricOut`, `UserOut`. Later user: T15 (`schema.d.ts`), T16 (`types.ts`).

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_route_guards.py`:

```python
"""Every API route declares who may call it (F §1.2 rule 4; S test_route_guards).

The walker lists every (method, path) the app serves with the full set of
dependencies FastAPI will run for it, and flags a route unless:
- it is in PUBLIC (the probes and FastAPI's built-in docs), or
- it is in USER_SCOPED and depends on get_current_user (and never on
  require_church: user-scoped routes ignore X-Church-Id), or
- require_church is somewhere in its dependency tree (require_admin depends
  on it, so admin routes pass too).

FastAPI 0.141 keeps included routers nested (app.routes holds
`_IncludedRouter`s with no path), so the walk goes through
fastapi.routing.iter_route_contexts, and reads `ctx.dependant`, which, unlike
`ctx.route.dependant`, includes the dependencies given to include_router(...)
(checked on 0.141.1; the fastapi==0.141.* pin keeps it stable).

Every slice that adds a user-scoped route adds it to USER_SCOPED in the same PR
(1b: POST /churches, POST /invites/preview, POST /invites/accept).
"""
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, FastAPI
from fastapi.routing import iter_route_contexts

from api.deps import get_current_user, require_admin, require_church
from api.main import create_app

PUBLIC = {
    ("GET", "/health"),
    ("GET", "/health/ready"),
    ("GET", "/openapi.json"),
    ("GET", "/docs"),
    ("GET", "/docs/oauth2-redirect"),
    ("GET", "/redoc"),
}
USER_SCOPED = {
    ("GET", "/me"),
}
CHURCH_SCOPED_TODAY = {("GET", "/church"), ("GET", "/rubric"), ("PATCH", "/rubric")}


def _calls(dependant: Any) -> set[Callable[..., Any]]:
    """Every callable in a dependency tree (sub-dependencies included)."""
    found: set[Callable[..., Any]] = set()
    stack = list(dependant.dependencies) if dependant is not None else []
    while stack:
        dep = stack.pop()
        if dep.call is not None:
            found.add(dep.call)
        stack.extend(dep.dependencies)
    return found


def route_dependencies(app: FastAPI) -> dict[tuple[str, str], set[Callable[..., Any]]]:
    """(method, path) -> every dependency FastAPI runs for it. HEAD is ignored
    (Starlette adds it to GET routes); a route with no methods (a mount) is "ANY"."""
    routes: dict[tuple[str, str], set[Callable[..., Any]]] = {}
    for ctx in iter_route_contexts(app.routes):
        calls = _calls(getattr(ctx, "dependant", None))   # None: a plain Starlette route
        for method in sorted(set(ctx.methods or {"ANY"}) - {"HEAD"}):
            routes.setdefault((method, ctx.path), set()).update(calls)
    return routes


def unguarded_routes(app: FastAPI) -> list[tuple[str, str]]:
    """The routes outside PUBLIC and USER_SCOPED with no require_church in their tree."""
    return sorted(
        route for route, calls in route_dependencies(app).items()
        if route not in PUBLIC and route not in USER_SCOPED and require_church not in calls
    )


def test_every_non_public_route_requires_a_church():
    routes = route_dependencies(create_app())
    assert CHURCH_SCOPED_TODAY <= routes.keys()   # the walker really sees the included routers
    assert unguarded_routes(create_app()) == []


def test_user_scoped_routes_require_a_user():
    routes = route_dependencies(create_app())
    for route in sorted(USER_SCOPED):
        assert get_current_user in routes[route], f"{route} does not depend on get_current_user"
        assert require_church not in routes[route], f"{route} is user-scoped but reads X-Church-Id"


def test_allowlists_name_real_routes():
    """A renamed or removed route must leave the allowlists too, or they hide nothing."""
    served = set(route_dependencies(create_app()))
    assert PUBLIC - served == set()
    assert USER_SCOPED - served == set()
    assert PUBLIC.isdisjoint(USER_SCOPED)


def _church_scoped_ok(church=Depends(require_church)) -> dict:
    return {}


def test_the_walker_flags_an_unguarded_route():
    app = create_app()

    @app.get("/unguarded")
    def unguarded() -> dict:
        return {}

    nested = APIRouter()

    @nested.post("/user-only")
    def user_only(user=Depends(get_current_user)) -> dict:
        return {}

    nested.add_api_route("/guarded", _church_scoped_ok, methods=["GET"])
    app.include_router(nested, prefix="/nested")

    assert unguarded_routes(app) == [("GET", "/unguarded"), ("POST", "/nested/user-only")]


def test_the_walker_sees_router_level_dependencies():
    app = create_app()
    on_include = APIRouter()
    on_include.add_api_route("/include-level", lambda: {}, methods=["DELETE"])
    app.include_router(on_include, dependencies=[Depends(require_church)])

    on_router = APIRouter(dependencies=[Depends(require_admin)])
    on_router.add_api_route("/router-level", lambda: {}, methods=["PUT"])
    app.include_router(on_router)

    routes = route_dependencies(app)
    assert require_church in routes[("DELETE", "/include-level")]
    assert require_church in routes[("PUT", "/router-level")]   # through require_admin
    assert unguarded_routes(app) == []
```

Create `backend/tests/test_isolation.py`:

```python
"""Cross-church isolation for every church-scoped route (F §1.2 rule 5).

Each church-scoped route gets one test here (or in its own slice's test file)
through tests.api_helpers.assert_church_isolated. The routes on main today
(GET /church, GET /rubric, PATCH /rubric) name no resource id, so only the 403
half and the control apply; routes with ids pass resource_path_b.
"""
import pytest

from service_rubric import default_rubric
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    assert_church_isolated,
    church_headers,
    isolation_world,
    make_api_client,
)


@pytest.fixture
def client(tmp_db):
    return make_api_client()


def test_get_church_is_isolated(client, isolation_world):
    assert_church_isolated(client, "GET", "/church", world=isolation_world)


def test_get_rubric_is_isolated(client, isolation_world):
    assert_church_isolated(client, "GET", "/rubric", world=isolation_world)


def test_patch_rubric_is_isolated(client, isolation_world):
    assert_church_isolated(client, "PATCH", "/rubric", world=isolation_world,
                           json={"prefer_familiar": False})
    # The denied PATCHes changed nothing in church B; the control changed church A.
    b = client.get("/rubric", headers=church_headers(isolation_world.b, isolation_world.church_b))
    assert b.json() == {"rubric": default_rubric(), "customized": []}
    a = client.get("/rubric", headers=church_headers(isolation_world.a, isolation_world.church_a))
    assert a.json()["customized"] == ["prefer_familiar"]
```

Create `backend/tests/test_openapi_contract.py`:

```python
"""The committed OpenAPI snapshot matches the live API (F §1.11; S test_openapi_contract).

frontend/src/lib/api/openapi.json feeds `npm run gen:api` (schema.d.ts), so a
backend change that alters the API must regenerate it in the same PR. These
tests never write the committed file: they compare text, or write to tmp_path.
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "backend" / "scripts" / "export_openapi.py"
COMMITTED = REPO_ROOT / "frontend" / "src" / "lib" / "api" / "openapi.json"
REGENERATE = ".venv/bin/python backend/scripts/export_openapi.py"


def _load_export_openapi():
    """backend/scripts is not a package: load the script by path, as `python backend/scripts/…` does."""
    spec = importlib.util.spec_from_file_location("export_openapi_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_committed_openapi_matches_the_live_schema():
    live = _load_export_openapi().render_openapi()
    committed = COMMITTED.read_text(encoding="utf-8") if COMMITTED.exists() else ""
    assert committed == live, (
        f"{COMMITTED.relative_to(REPO_ROOT)} is stale. From the repo root run:\n"
        f"    {REGENERATE}\n"
        f"then `npm run gen:api` in frontend/, and commit both files."
    )


def test_write_openapi_writes_sorted_json_with_trailing_newline(tmp_path):
    module = _load_export_openapi()
    out = tmp_path / "nested" / "openapi.json"
    module.write_openapi(out)
    text = out.read_text(encoding="utf-8")
    assert text.endswith("}\n") and not text.endswith("\n\n")
    schema = json.loads(text)
    assert text == json.dumps(schema, sort_keys=True, indent=2) + "\n"
    assert schema["info"]["title"] == "Worship Service Builder API"
    assert {"/health", "/health/ready", "/me", "/church", "/rubric"} <= schema["paths"].keys()
    # T3's error_responses(...): every route documents the one error body.
    assert "ErrorBody" in schema["components"]["schemas"]
    assert "HTTPValidationError" not in schema["components"]["schemas"]


def test_export_script_runs_from_the_repo_root(tmp_path):
    """The regenerate command in the failure message works as printed:
    `python backend/scripts/export_openapi.py` puts backend/scripts on
    sys.path[0], and the script must still import api."""
    out = tmp_path / "openapi.json"
    result = subprocess.run([sys.executable, "backend/scripts/export_openapi.py", "--out", str(out)],
                            cwd=REPO_ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"Wrote {out}\n"
    assert out.read_text(encoding="utf-8") == _load_export_openapi().render_openapi()
```

Append to the end of `backend/tests/test_no_streamlit_in_core.py` (after T2's `test_usecases_package_imports_no_fastapi_or_streamlit`; `subprocess`, `sys` and `CODE_DIR` = `backend/` are already defined at the top of the file):

```python


# Imports every module in api/routes, builds the app, and fails if a routes
# module's router is not mounted (so "every router" stays true as slices add
# routers) or if anything on that path imported streamlit (F §2.2 item 6).
_EVERY_ROUTER = """
import importlib, pkgutil, sys
import api.main, api.routes
from fastapi.routing import iter_route_contexts
modules = [importlib.import_module(f"api.routes.{m.name}")
           for m in pkgutil.iter_modules(api.routes.__path__)]
served = {ctx.endpoint for ctx in iter_route_contexts(api.main.create_app().routes)}
unmounted = [m.__name__ for m in modules
             if not any(route.endpoint in served for route in m.router.routes)]
print("modules:", sorted(m.__name__ for m in modules))
print("unmounted:", unmounted)
print("streamlit imported:", "streamlit" in sys.modules)
sys.exit(1 if unmounted or "streamlit" in sys.modules or not modules else 0)
"""


def test_api_main_with_every_router_does_not_import_streamlit():
    result = subprocess.run(
        [sys.executable, "-c", _EVERY_ROUTER], cwd=CODE_DIR, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "unmounted: []" in result.stdout
    assert "'api.routes.me'" in result.stdout and "'api.routes.rubric'" in result.stdout
```

- [ ] **Step 2: Run the tests to verify they fail**

Run (one file at a time: a collection error in one file would interrupt the others):
```bash
.venv/bin/python -m pytest -q backend/tests/test_isolation.py 2>&1 | tail -3
.venv/bin/python -m pytest -q backend/tests/test_openapi_contract.py 2>&1 | tail -3
.venv/bin/python -m pytest -q backend/tests/test_route_guards.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1
```
Expected:
- `E   ModuleNotFoundError: No module named 'tests.api_helpers'` and `1 error` (collection).
- `3 failed`: `test_committed_openapi_matches_the_live_schema` and `test_write_openapi_writes_sorted_json_with_trailing_newline` with `FileNotFoundError: [Errno 2] No such file or directory: '…/backend/scripts/export_openapi.py'`; `test_export_script_runs_from_the_repo_root` with `can't open file '…/backend/scripts/export_openapi.py'` in the assertion message.
- `8 passed`. These two files check code that already exists: the guard walker lives in the test file, every current route is guarded (T3), and nothing behind `api.main` imports Streamlit. The self-tests `test_the_walker_flags_an_unguarded_route` and `test_the_walker_sees_router_level_dependencies` are what prove the walker can fail. See it fail on a real route once:

```bash
sed -i '' 's/def church(active: ActiveChurch = Depends(require_church))/def church(active: ActiveChurch = Depends(get_current_user))/' backend/api/routes/me.py
.venv/bin/python -m pytest -q backend/tests/test_route_guards.py 2>&1 | grep -m1 'AssertionError'; .venv/bin/python -m pytest -q backend/tests/test_route_guards.py 2>&1 | tail -1
git checkout -- backend/api/routes/me.py
git status --short backend/api/routes/me.py
```
Expected: `E       AssertionError: assert [('GET', '/church')] == []`, then `3 failed, 2 passed` (the two self-tests build on `create_app()`, so they see the unguarded `/church` too); `git checkout` restores T3's committed file and `git status` prints nothing for it. (`sed -i ''` is the macOS form.)

- [ ] **Step 3: Create `backend/tests/api_helpers.py`**

```python
"""Shared helpers for API tests: signed-in headers, a test client, and the
cross-church isolation check every church-scoped route gets (F §1.2 rule 5;
S tests/api_helpers.py).

Use from a test module:

    from tests.api_helpers import assert_church_isolated, isolation_world  # noqa: F401 (fixture)

`isolation_world` is a pytest fixture: importing it into the test module is
what makes pytest find it (only the root conftest may declare pytest_plugins).
"""
import uuid
from dataclasses import dataclass
from typing import Any, Optional

import pytest
from fastapi.testclient import TestClient

from tests.jwt_helpers import ISSUER, SIGNING_KEY, make_token

# require_church's 403 body without its request_id (F §1.2, S "no_church_access").
NO_CHURCH_ACCESS = {
    "code": "forbidden",
    "message": "You don't have access to this church.",
    "details": {"reason": "no_church_access"},
}


def auth_headers(email: str) -> dict[str, str]:
    """A signed-in Google user with this email (token from tests.jwt_helpers)."""
    return {"Authorization": f"Bearer {make_token(email=email)}"}


def church_headers(email: str, church_id: uuid.UUID) -> dict[str, str]:
    """auth_headers plus X-Church-Id: the caller acting in that church."""
    return {**auth_headers(email), "X-Church-Id": str(church_id)}


def make_api_client() -> TestClient:
    """A TestClient on a fresh app whose token verifier trusts tests.jwt_helpers'
    signing key. Built without `with`, so the lifespan does not run. Call it
    after `tmp_db` (the routes use the engine that fixture binds)."""
    from api.deps import get_verifier
    from api.main import create_app
    from api.security import TokenVerifier

    app = create_app()
    app.dependency_overrides[get_verifier] = lambda: TokenVerifier(
        lambda _token: SIGNING_KEY.public_key(), issuer=ISSUER
    )
    return TestClient(app)


@dataclass(frozen=True)
class IsolationWorld:
    """Church A (a@ owns it), church B (b@ owns it) and an outsider who
    belongs to neither."""
    church_a: uuid.UUID
    church_b: uuid.UUID
    a: str = "a@example.com"
    b: str = "b@example.com"
    outsider: str = "o@example.com"


@pytest.fixture
def isolation_world(tmp_db, make_user, make_church) -> IsolationWorld:
    a, b, outsider = "a@example.com", "b@example.com", "o@example.com"
    church_a = make_church(name="Church A", owner_user_id=make_user(email=a))
    church_b = make_church(name="Church B", owner_user_id=make_user(email=b))
    make_user(email=outsider)                     # signed up, member of neither church
    return IsolationWorld(church_a=church_a, church_b=church_b, a=a, b=b, outsider=outsider)


def _error_without_request_id(response) -> dict:
    error = dict(response.json()["error"])
    error.pop("request_id")
    return error


def assert_church_isolated(
    client: TestClient,
    method: str,
    path: str,
    *,
    world: IsolationWorld,
    json: Any = None,
    resource_path_b: Optional[str] = None,
) -> None:
    """Nobody reaches church B through `method path` without belonging to it.

    1. The outsider and a@, each sending X-Church-Id = B, get 403 `forbidden`
       "You don't have access to this church." with details.reason
       `no_church_access`.
    2. When `resource_path_b` is given (a path naming one of church B's
       resources), a@ acting in church A gets 404 `not_found` there: an id
       from another church is never a 403 (F §1.2 rule 2).
    3. Control: a@ acting in church A on `path` gets neither 401, 403 nor 404,
       so the denials above come from the church check and not from a broken
       request. It runs last, so a route that changes church A (PATCH, DELETE)
       does so only after the checks.
    """
    for email in (world.outsider, world.a):
        r = client.request(method, path, headers=church_headers(email, world.church_b), json=json)
        assert r.status_code == 403, f"{method} {path} as {email} in church B: {r.status_code} {r.text}"
        assert _error_without_request_id(r) == NO_CHURCH_ACCESS

    if resource_path_b is not None:
        r = client.request(method, resource_path_b,
                           headers=church_headers(world.a, world.church_a), json=json)
        assert r.status_code == 404, (
            f"{method} {resource_path_b} as {world.a} in church A: {r.status_code} {r.text}"
        )
        assert r.json()["error"]["code"] == "not_found"

    r = client.request(method, path, headers=church_headers(world.a, world.church_a), json=json)
    assert r.status_code not in (401, 403, 404), (
        f"control: {method} {path} as {world.a} in church A: {r.status_code} {r.text}"
    )
```

Run: `.venv/bin/python -m pytest -q backend/tests/test_isolation.py 2>&1 | tail -1`
Expected: `3 passed`. Each test sends 3 requests (outsider in B, a@ in B, control a@ in A); the PATCH test's control changes church A's rubric (`customized == ["prefer_familiar"]`) and church B's stays the default.

- [ ] **Step 4: Create `backend/scripts/export_openapi.py`**

```python
"""Write the API's OpenAPI schema to frontend/src/lib/api/openapi.json (F §1.11).

Run from the repo root after any change to a route, a request or response
model, or an error declaration:

    .venv/bin/python backend/scripts/export_openapi.py

then run `npm run gen:api` in frontend/ and commit both files. The output is
create_app().openapi() as JSON with sorted keys, two-space indents and a
trailing newline, so the committed file changes only when the API does.
backend/tests/test_openapi_contract.py fails while the committed file differs
from the live schema. `--out PATH` writes somewhere else (the tests use it).
"""
import argparse
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))   # run as a file, sys.path[0] is backend/scripts

from api.main import create_app  # noqa: E402

DEFAULT_OUT = BACKEND.parent / "frontend" / "src" / "lib" / "api" / "openapi.json"


def render_openapi() -> str:
    """The live schema as the committed file's text."""
    return json.dumps(create_app().openapi(), sort_keys=True, indent=2) + "\n"


def write_openapi(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_openapi(), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help="where to write the schema (default: %(default)s)")
    args = parser.parse_args(argv)
    write_openapi(args.out)
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Run: `.venv/bin/python -m pytest -q backend/tests/test_openapi_contract.py 2>&1 | grep -A2 '^E .*is stale' | head -3; .venv/bin/python -m pytest -q backend/tests/test_openapi_contract.py 2>&1 | tail -1`
Expected: the failure message `AssertionError: frontend/src/lib/api/openapi.json is stale. From the repo root run:` followed by `.venv/bin/python backend/scripts/export_openapi.py` and `then \`npm run gen:api\` in frontend/, and commit both files.` (the snapshot does not exist yet, and `gen:api` arrives in T15); then `1 failed, 2 passed`.

- [ ] **Step 5: Generate the committed snapshot**

Run from the repo root:
```bash
.venv/bin/python backend/scripts/export_openapi.py
.venv/bin/python -c "
import json
s = json.load(open('frontend/src/lib/api/openapi.json'))
print(s['openapi'], s['info'])
print(sorted(s['components']['schemas']))
for path, ops in sorted(s['paths'].items()):
    for method, op in ops.items():
        print(method.upper(), path, sorted(op['responses']))
"
git add frontend/src/lib/api/openapi.json
```
Expected:
```text
Wrote /Users/beaubrown/Desktop/projects/church/.claude/worktrees/duplicate-wire-activity-review-6370f5/frontend/src/lib/api/openapi.json
3.1.0 {'title': 'Worship Service Builder API', 'version': '0.1.0'}
['ChurchOut', 'ErrorBody', 'ErrorDetail', 'MeOut', 'ReadyOut', 'RubricModel', 'RubricOut', 'UserOut']
GET /church ['200', '401', '403', '422', '503']
GET /health ['200']
GET /health/ready ['200']
GET /me ['200', '401', '422', '503']
GET /rubric ['200', '401', '403', '422', '503']
PATCH /rubric ['200', '401', '403', '422', '503']
```
(the `Wrote` line shows this checkout's absolute path). The file is about 640 lines of sorted JSON ending in one newline. `HTTPValidationError` and `ValidationError` must not appear in the schema list: if they do, T3's `error_responses(...)` is missing from a route — fix the route in T3's files, not the snapshot. Staging it now lets Step 6 prove that running the suite never rewrites it.

- [ ] **Step 6: Run the tests, the suite and the frontend checks**

Run:
```bash
.venv/bin/python -m pytest -q backend/tests/test_route_guards.py backend/tests/test_isolation.py \
  backend/tests/test_openapi_contract.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
git diff --exit-code frontend/src/lib/api/openapi.json && echo "snapshot untouched"
(cd frontend && npm test 2>&1 | grep 'Tests ' && npm run typecheck >/dev/null && npm run lint >/dev/null && echo "typecheck and lint clean")
```
Expected: `14 passed` (route guards 5, isolation 3, contract 3, no-Streamlit 3 = the original test, T2's and this task's); then `687 passed, 4 skipped` (675 after T12 + 12; the skips are the Postgres-only tests without `TEST_DATABASE_URL`); then `snapshot untouched`; then `Tests  15 passed (15)` and `typecheck and lint clean` (the frontend still has 15 tests; the new `src/lib/api/` directory sits next to `src/lib/api.ts` until T16 moves the client into it).

- [ ] **Step 7: Commit**

```bash
git add backend/tests/test_route_guards.py backend/tests/api_helpers.py backend/tests/test_isolation.py \
        backend/scripts/export_openapi.py backend/tests/test_openapi_contract.py \
        backend/tests/test_no_streamlit_in_core.py frontend/src/lib/api/openapi.json
git commit -m "Guards: route-guard walker, cross-church isolation helper, OpenAPI snapshot and contract (F §1.2, §1.11, §2.2 item 6)

test_route_guards walks iter_route_contexts(app.routes) with ctx.dependant
(which includes include_router dependencies) and fails on any route outside
PUBLIC and USER_SCOPED without require_church; two self-tests prove it can
fail. tests/api_helpers.py adds auth_headers, church_headers,
make_api_client, isolation_world and assert_church_isolated, used on
GET /church, GET /rubric and PATCH /rubric. scripts/export_openapi.py writes
frontend/src/lib/api/openapi.json (sorted keys, trailing newline);
test_openapi_contract fails while the snapshot is stale and prints the
command. test_no_streamlit_in_core imports api.main with every router.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 14: Postgres re-run of the concurrent first-request test; the Alembic cycle in CI's `backend-postgres`; the early draft-PR checkpoint (F §5.4, §7.3; ops handoff; AC1, AC4; owner Q5)

Nothing on this machine runs Postgres, so five things have only been checked on SQLite or as offline SQL so far: `0003_lockdown`'s DO block (Task 8's three tests), the RLS startup check (Task 11's test), the whole Alembic chain on a real server, and the ops-2 concurrent first-request race on the real `INSERT … ON CONFLICT (email)` path (this task's test). This task extends the existing ops-2 `backend-postgres` job (`ci.yml:19-44`): it gains `TEST_DATABASE_URL` (the same throwaway container URL as `DATABASE_URL`) and, after installing the dependencies, runs `alembic upgrade head` → `alembic check` → `alembic downgrade base` → `alembic upgrade head` in `backend/`, then the ops-2 smoke, then `python -m pytest -m postgres -q` from the repo root. Then the agent pushes the branch and opens a **draft** PR (owner Q5: authorized, no need to ask again; the title starts "Draft:"), so the job runs before the frontend work starts (Tasks 15–23). The agent never marks the PR ready: that happens at Task 25, on the owner's yes.

**Order change from the outline (recorded):** `pg_smoke.py` runs **before** the Postgres tests, not as the last step. `pg_smoke.py:70` expects exactly 2 rows in `users`, and `pg_db` empties the tables only *before* each test, so the row this task's test leaves behind (`first@example.com`) would fail the smoke with a count of 3. After the second `alembic upgrade head` the tables are empty, the smoke's `init_db()` is still a no-op on existing tables (clarification 2's reason for running it after the cycle), and `pg_db` truncates the smoke's two users before each test. `pg_smoke.py` itself stays unchanged.

`test_ci_workflow.py::test_ci_runs_the_postgres_smoke_on_a_throwaway_postgres_17` is replaced (clarification 3): only `test_ops_workflows.py` checks the Postgres major. Its replacement set pins the step order, the two URLs, and the image *shape* `postgres:<N>`, so the ops major check (which passes on an empty list) always reads a real image. The stale comment at `test_ops_workflows.py:397` (clarification 28) is corrected; no test there changes.

**Files:**
- Modify: `.github/workflows/ci.yml:19-44` (the whole `backend-postgres` job: comment, `TEST_DATABASE_URL`, six named steps)
- Modify: `backend/tests/test_identity.py:198-210` (the `client` fixture uses Task 13's `tests.api_helpers.make_api_client()`), `:227-244` (the race body moves into `_first_requests_at_once()`; the SQLite test keeps its name and assertions); append the Postgres block after the last line (`:358`)
- Modify: `backend/tests/test_ci_workflow.py` (whole file, 28 lines → 76: module constants, `_ci()`, one test kept, one replaced by three)
- Modify: `backend/tests/test_ops_workflows.py:397-398` (comment only)
- No application code changes.

**Interfaces:**
- Consumes: fixture `pg_db` (Task 1; Task 6's wiring runs `alembic upgrade head` on every call, a no-op at head — in CI the cycle has already reached head, so it only truncates); `tests.pg_helpers.require_local_test_url(url: str) -> str` (Task 1); the `postgres` marker in `pytest.ini` (Task 1); `backend/alembic.ini` and `migrations/env.py` (Task 5: the CLI takes the URL from the exported `DATABASE_URL` and prints `Database: dialect=… driver=… host=… database=…` to stderr); revisions `0001_baseline` … `0004_invites_reusable` (Tasks 6–9); the other four `@pytest.mark.postgres` tests: `test_migrations.py::test_0003_refuses_without_bypassrls_or_ownership_and_rolls_back`, `::test_0003_refuses_a_bypassrls_role_that_does_not_own_a_table`, `::test_0003_is_idempotent_after_the_manual_lockdown` (Task 8), `test_api_app.py::test_rls_check_names_tables_without_rls` (Task 11); `repos.users.ensure_user` and the monkeypatch target `api.deps.ensure_user` (ops-2); `tests.api_helpers.make_api_client() -> TestClient` (Task 13).
- Produces:
  - CI job `backend-postgres`: env `DATABASE_URL` = `TEST_DATABASE_URL` = `postgresql://postgres:ci-throwaway@localhost:5432/postgres`; its last six `run` steps, in order: `alembic upgrade head`, `alembic check`, `alembic downgrade base`, `alembic upgrade head` (each with `working-directory: backend`), `python backend/tests/pg_smoke.py`, `python -m pytest -m postgres -q`. Later users: Task 24 (README "Tests" paragraph), Task 25 (expects `backend-postgres` green with `5 passed`).
  - `tests/test_identity.py`: `_first_requests_at_once(client, monkeypatch, email="first@example.com") -> list[httpx.Response]`; fixture `pg_client(pg_db) -> TestClient`; test `test_concurrent_first_requests_on_postgres_both_succeed_with_one_id`.
  - `tests/test_ci_workflow.py`: `CI_YML: pathlib.Path`, `THROWAWAY_URL: str`, `POSTGRES_JOB_RUNS: list[str]`, `_ci() -> dict` (Task 15 appends `test_ci_frontend_regenerates_api_types_and_fails_on_diff` to this file and may reuse `CI_YML` and `_ci()`).
  - The draft PR on `claude/slice-1-plan` (its number and URL recorded in Step 12). Later user: Task 25 (updates its title and body, and runs `gh pr ready` only on the owner's yes).

- [ ] **Step 1: Write the failing tests**

Replace the whole of `backend/tests/test_ci_workflow.py` (28 lines) with:

```python
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
CI_YML = ROOT / ".github" / "workflows" / "ci.yml"
# The backend-postgres service container: throwaway, local to the runner, never a real database.
THROWAWAY_URL = "postgresql://postgres:ci-throwaway@localhost:5432/postgres"
# Slice 1a (S Backend 1a, F §5.4): the Alembic cycle on the empty container, then
# ops-2's smoke on the fresh head schema (its user count assumes empty tables),
# then the @pytest.mark.postgres tests (pg_db empties the tables before each).
POSTGRES_JOB_RUNS = [
    "alembic upgrade head",
    "alembic check",
    "alembic downgrade base",
    "alembic upgrade head",
    "python backend/tests/pg_smoke.py",
    "python -m pytest -m postgres -q",
]


def _ci():
    import yaml

    return yaml.safe_load(CI_YML.read_text(encoding="utf-8"))


def test_ci_runs_backend_tests_and_frontend_checks_on_prs():
    text = CI_YML.read_text(encoding="utf-8")
    assert "pull_request" in text
    assert "python -m pytest" in text
    for script in ("npm run lint", "npm run typecheck", "npm test", "npm run build"):
        assert script in text


def test_ci_postgres_job_runs_the_alembic_cycle_then_postgres_tests():
    """Upgrade an empty database to head, check the models match, downgrade every
    revision, upgrade again, then the ops-2 smoke and the Postgres-only tests.
    The alembic steps run in backend/ (alembic.ini's home); the rest from the
    repo root. The Postgres major is checked only by test_ops_workflows (ops spec)."""
    steps = _ci()["jobs"]["backend-postgres"]["steps"]
    runs = [step.get("run", "") for step in steps]
    assert runs[-len(POSTGRES_JOB_RUNS):] == POSTGRES_JOB_RUNS     # in this order, last, nothing between
    assert runs.index("pip install -r requirements-dev.txt") < runs.index("alembic upgrade head")
    for step in steps:
        if step.get("run", "").startswith("alembic "):
            assert step.get("working-directory") == "backend", step
        elif step.get("run", "").startswith("python "):
            assert "working-directory" not in step, step
    assert (ROOT / "backend" / "alembic.ini").is_file()
    assert (ROOT / "backend" / "tests" / "pg_smoke.py").is_file()


def test_ci_postgres_job_points_both_urls_at_the_throwaway_container():
    import yaml

    from tests.pg_helpers import require_local_test_url

    ci = _ci()
    job = ci["jobs"]["backend-postgres"]
    assert job["env"]["DATABASE_URL"] == THROWAWAY_URL
    assert job["env"]["TEST_DATABASE_URL"] == THROWAWAY_URL
    assert require_local_test_url(job["env"]["TEST_DATABASE_URL"]) == THROWAWAY_URL
    service = job["services"]["postgres"]
    assert f":{service['env']['POSTGRES_PASSWORD']}@localhost:5432/" in THROWAWAY_URL
    assert service["ports"] == ["5432:5432"]
    assert "secrets." not in yaml.safe_dump(job)                   # the job never reads a real database
    assert "TEST_DATABASE_URL" not in (ci["jobs"]["backend"].get("env") or {})   # there they skip


def test_ci_postgres_service_image_is_a_bare_postgres_major():
    """test_ops_workflows.test_ci_postgres_service_matches_pg_major is the only check
    of the CI Postgres major, and it passes on an empty list. Pinning the one
    service to the bare postgres:<N> shape keeps that check reading a real image."""
    services = _ci()["jobs"]["backend-postgres"]["services"]
    assert list(services) == ["postgres"]
    assert re.fullmatch(r"postgres:\d+", services["postgres"]["image"]), services["postgres"]["image"]
```

In `backend/tests/test_identity.py`, replace the `client` fixture (`:198-210`):

```python
@pytest.fixture
def client(tmp_db):
    from fastapi.testclient import TestClient

    from api.deps import get_verifier
    from api.main import create_app
    from api.security import TokenVerifier
    from tests.jwt_helpers import ISSUER, SIGNING_KEY

    app = create_app()
    app.dependency_overrides[get_verifier] = lambda: TokenVerifier(
        lambda _token: SIGNING_KEY.public_key(), issuer=ISSUER)
    return TestClient(app)
```

with:

```python
@pytest.fixture
def client(tmp_db):
    from tests.api_helpers import make_api_client

    return make_api_client()
```

Then replace `test_concurrent_first_requests_both_succeed_with_one_id` (`:227-244`):

```python
def test_concurrent_first_requests_both_succeed_with_one_id(client, monkeypatch):
    """F §7.3: StrictMode's double /me for a new email. A barrier makes both
    requests miss the cache and enter ensure_user together."""
    import api.deps

    barrier = threading.Barrier(2)

    def together(*args, **kwargs):
        barrier.wait(timeout=10)
        return ensure_user(*args, **kwargs)

    monkeypatch.setattr(api.deps, "ensure_user", together)
    headers = _auth(email="first@example.com")
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: client.get("/me", headers=headers), range(2)))
    assert [r.status_code for r in responses] == [200, 200]
    assert responses[0].json()["user"]["id"] == responses[1].json()["user"]["id"]
    assert _user_count() == 1
```

with:

```python
def _first_requests_at_once(client, monkeypatch, email="first@example.com"):
    """Two concurrent GET /me for a new email; returns both responses. A barrier
    makes both requests miss the cache and enter ensure_user together."""
    import api.deps

    barrier = threading.Barrier(2)

    def together(*args, **kwargs):
        barrier.wait(timeout=10)
        return ensure_user(*args, **kwargs)

    monkeypatch.setattr(api.deps, "ensure_user", together)
    headers = _auth(email=email)
    with ThreadPoolExecutor(max_workers=2) as pool:
        return list(pool.map(lambda _: client.get("/me", headers=headers), range(2)))


def test_concurrent_first_requests_both_succeed_with_one_id(client, monkeypatch):
    """F §7.3: StrictMode's double /me for a new email."""
    responses = _first_requests_at_once(client, monkeypatch)
    assert [r.status_code for r in responses] == [200, 200]
    assert responses[0].json()["user"]["id"] == responses[1].json()["user"]["id"]
    assert _user_count() == 1
```

Append to the end of `backend/tests/test_identity.py` (after `:358`, the last line of `test_the_token_is_verified_even_when_the_identity_is_cached`):

```python


# --- the same race on real Postgres (slice 1a; ops handoff, F §7.3) ------------

@pytest.fixture
def pg_client(pg_db):
    from tests.api_helpers import make_api_client

    return make_api_client()


@pytest.mark.postgres
def test_concurrent_first_requests_on_postgres_both_succeed_with_one_id(pg_client, monkeypatch):
    """SQLite serializes writers, so only on Postgres do the two
    INSERT ... ON CONFLICT (email) statements really overlap: the second waits
    for the first to commit, inserts nothing and reads the committed row.
    Runs in CI's backend-postgres job; skipped without TEST_DATABASE_URL."""
    responses = _first_requests_at_once(pg_client, monkeypatch)
    assert [r.status_code for r in responses] == [200, 200]
    assert responses[0].json()["user"]["id"] == responses[1].json()["user"]["id"]
    assert _user_count() == 1
```

`_user_count()` (`:28-30`) reads through `session_scope()`, which uses the engine `pg_db` bound with `reset_engine_for_tests`, so it counts the Postgres rows. `TestClient(app)` without `with` does not run the lifespan, so no startup check touches the database. The autouse `_fresh_identity_cache` fixture guarantees both requests miss the cache.

- [ ] **Step 2: Run the tests to verify they fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_ci_workflow.py backend/tests/test_identity.py -rs 2>&1 | tail -6
```

Expected: `2 failed, 29 passed, 1 skipped`. `test_ci_postgres_job_runs_the_alembic_cycle_then_postgres_tests` fails with `AssertionError: assert ['', '', 'pip.../pg_smoke.py'] == ['alembic upg... postgres -q']` (the job has only checkout, setup-python, pip and the smoke); `test_ci_postgres_job_points_both_urls_at_the_throwaway_container` fails with `KeyError: 'TEST_DATABASE_URL'`. `test_ci_postgres_service_image_is_a_bare_postgres_major` passes as written: it pins the shape the ops-2 job already has. The skip line reads `SKIPPED [1] backend/tests/test_identity.py:378: TEST_DATABASE_URL is not set (the backend-postgres CI job sets it)`; the 27 SQLite identity tests pass after the refactor (the Postgres half of this test first runs at the checkpoint, Global Constraints "Postgres is CI-only").

- [ ] **Step 3: Extend the `backend-postgres` job (`.github/workflows/ci.yml`)**

Replace lines 19-44 (the whole `backend-postgres` job):

```yaml
  backend-postgres:
    # ON CONFLICT (email), the 3 + 3 pool and concurrent first sign-ins on real
    # Postgres, in a throwaway container (major matches PG_MAJOR in backup.yml).
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:17
        env:
          POSTGRES_PASSWORD: ci-throwaway
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U postgres"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 20
    env:
      DATABASE_URL: postgresql://postgres:ci-throwaway@localhost:5432/postgres
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
      - run: pip install -r requirements-dev.txt
      - run: python backend/tests/pg_smoke.py
```

with:

```yaml
  backend-postgres:
    # Real Postgres in a throwaway container (major matches PG_MAJOR in backup.yml):
    # the Alembic cycle on an empty database (slice 1a), the ops-2 smoke (ON CONFLICT
    # (email), the 3 + 3 pool, concurrent first sign-ins), then the
    # @pytest.mark.postgres tests. pg_smoke runs before the tests because its user
    # count assumes empty tables; pg_db empties them before each test anyway.
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:17
        env:
          POSTGRES_PASSWORD: ci-throwaway
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U postgres"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 20
    env:
      DATABASE_URL: postgresql://postgres:ci-throwaway@localhost:5432/postgres
      TEST_DATABASE_URL: postgresql://postgres:ci-throwaway@localhost:5432/postgres
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
      - run: pip install -r requirements-dev.txt
      - name: Migrate the empty database to head
        working-directory: backend
        run: alembic upgrade head
      - name: The models match the migrated schema
        working-directory: backend
        run: alembic check
      - name: Every revision downgrades
        working-directory: backend
        run: alembic downgrade base
      - name: Migrate to head again
        working-directory: backend
        run: alembic upgrade head
      - name: Identity smoke (ops-2)
        run: python backend/tests/pg_smoke.py
      - name: Postgres-only tests
        run: python -m pytest -m postgres -q
```

`pip install -r requirements-dev.txt` puts the `alembic` command on the runner's PATH (`requirements-dev.txt` → `requirements.txt` → `backend/requirements.txt`, which gained `alembic>=1.20` in Task 1). In `backend/`, `alembic` finds `alembic.ini`, whose `prepend_sys_path = %(here)s` lets `env.py` import `db`; with no `url` attribute set, `env.py` uses the exported `DATABASE_URL` (Task 5). The `backend` and `frontend` jobs are unchanged; the `backend` job has no `TEST_DATABASE_URL`, so the five Postgres tests skip there.

- [ ] **Step 4: Correct the stale comment (`backend/tests/test_ops_workflows.py:397-398`)**

Replace:

```python
def test_ci_postgres_service_matches_pg_major():
    # Inert until slice 1 declares a postgres:<N> service container in ci.yml.
    # This is the only check of the CI Postgres major (ops spec, slice 1 row).
```

with:

```python
def test_ci_postgres_service_matches_pg_major():
    # ci.yml's backend-postgres job declares the postgres:<N> service (ops-2), and
    # test_ci_workflow.test_ci_postgres_service_image_is_a_bare_postgres_major keeps
    # it in that shape, so this check never passes on an empty list.
    # This is the only check of the CI Postgres major (ops spec, slice 1 row).
```

The test body (`:399-400`) is unchanged.

- [ ] **Step 5: Run the tests and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_ci_workflow.py backend/tests/test_identity.py backend/tests/test_ops_workflows.py 2>&1 | tail -1
.venv/bin/python -m pytest -q -m postgres 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
```

Expected: `111 passed, 1 skipped` (`test_ci_workflow.py` 4, `test_identity.py` 27 + the skip, `test_ops_workflows.py` 80); then `5 skipped, 689 deselected` (exactly five tests carry the `postgres` marker: Task 8's three, Task 11's one and this task's one); then `689 passed, 5 skipped` (Task 13 left `687 passed, 4 skipped`; +2 passed, +1 skipped). If the marker count is not 5, stop: a Postgres test is missing its marker or a task added an unplanned one.

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/ci.yml backend/tests/test_ci_workflow.py backend/tests/test_identity.py \
        backend/tests/test_ops_workflows.py
git commit -m "CI: Alembic cycle and Postgres-only tests in backend-postgres; concurrent first /me on Postgres (F §5.4, §7.3; S Backend 1a)

backend-postgres now upgrades the empty container to head, runs alembic
check, downgrades to base and upgrades again, then runs the ops-2 smoke and
pytest -m postgres with TEST_DATABASE_URL pointing at the same throwaway
container. The smoke runs before the tests because its user count assumes
empty tables. test_identity re-runs the concurrent first-request race on
Postgres. test_ci_workflow no longer asserts the major (only
test_ops_workflows does) but pins the service image to postgres:<N>, so that
check cannot pass on an empty list.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 7: Check the branch before the first push (agent)**

The owner authorized this push and the draft PR in advance (the plan's **Owner decisions**, Q5); do not ask again. Everything else outward (marking the PR ready, merging, repo settings) still needs the owner's yes.

```bash
git status --short
git fetch origin
git rev-list --count HEAD..origin/main
git log --oneline origin/main..HEAD
git diff --name-only origin/main...HEAD | grep -E '(^|/)\.env' ; echo "env files: $?"
gh auth status 2>&1 | grep -E "Logged in|not logged"
gh pr list -R bbrown62450/church --head claude/slice-1-plan --state open --json number,isDraft,url
```

Expected, in order: `?? .claude/`; the fetch prints nothing or only updated refs; `0`; the plan commit, Task 1's merge of `origin/main` (there whenever Task 1 Step 1 found the branch behind, as it is once `560ebb3` is on `origin/main`) and the commits of Tasks 1–14; no other merge commit; `env files: 1` (grep found nothing: no `.env` file is on the branch); `Logged in to github.com account …`; `[]`.
- If the count is not `0` (the freeze-records PRs merged meanwhile): `git merge origin/main -m "Merge origin/main into claude/slice-1-plan (Task 14)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`, then `.venv/bin/python -m pytest -q | tail -1` → `689 passed, 5 skipped`, and continue. On a merge conflict, stop and tell the owner.
- If `gh` is not logged in: stop and ask the owner to run `gh auth login` in their own terminal (the agent never handles a token).
- If an open PR already exists for the branch: do not open another; use its number in Steps 9–12, and tell the owner if it is not a draft (do not convert it).

- [ ] **Step 8: Push the branch (agent, authorized by Q5)**

```bash
git push -u origin claude/slice-1-plan
```

Expected: `* [new branch]      claude/slice-1-plan -> claude/slice-1-plan` and `branch 'claude/slice-1-plan' set up to track 'origin/claude/slice-1-plan'.` If the push is rejected, stop and tell the owner; never force-push.

- [ ] **Step 9: Open the draft PR (agent, authorized by Q5)**

```bash
gh pr create -R bbrown62450/church --draft --base main --head claude/slice-1-plan \
  --title "Draft: Slice 1a platform: Alembic, error contract, idempotency, route guards (CI Postgres checkpoint)" \
  --body-file - <<'EOF'
Draft for the CI Postgres checkpoint (owner answer Q5 in the slice 1a plan). Not ready for review and not for merging: Tasks 15–24 (frontend foundations and docs) are still to come on this branch, and Task 25 turns this into the real PR.

Plan: docs/superpowers/plans/2026-09-26-slice-1a-platform.md. Spec: docs/superpowers/specs/2026-09-25-slice-1-onboarding-design.md (1a).

On the branch so far (Tasks 1–14):
- Test guards: autouse no-network fixture, `postgres` marker, `pg_db` on a local-only `TEST_DATABASE_URL`; pins fastapi 0.141.*, pydantic 2.13.*, alembic, tzdata.
- `domain_errors.py` (DomainError family, `ERROR_CODES` with 29 codes), `db/ids.py::as_uuid`, `usecases/` package.
- Error body `fields`/`details`, DomainError handler, 422 field mapping, `ErrorBody`, `no_church_access` reason; `Page[T]`, `ItemList[T]`.
- `api/idempotency.py` (Idempotency-Key store, 15-minute replay).
- Alembic: `alembic.ini`, `migrations/env.py`, `0001_baseline`, `0002_reconcile`, `0003_lockdown`, `0004_invites_reusable` (+ `Invite.reusable`/`accepted_by`); the one-off schema scripts deleted.
- `db/schema_check.py` + `scripts/schema_drift.py`; the lifespan no longer calls `create_all`; startup revision and RLS checks; `/health/ready` 503 `schema_behind` in production; `backend/railway.toml` (inert until the Config-as-code path is set in Task 26).
- Route-guard, isolation and OpenAPI contract tests; `frontend/src/lib/api/openapi.json`.
- CI `backend-postgres`: alembic upgrade → check → downgrade base → upgrade, the ops-2 smoke, then `pytest -m postgres` (the first run of 0003, the RLS check and the five Postgres-only tests).

Tests so far: backend +134 (+5 Postgres-only), −4 (689 passed, 5 skipped); frontend unchanged (15 passed).

Before merge: Task 26; after merge: Task 27. Production Streamlit (https://liturgy-frozen.streamlit.app/) runs from `streamlit-frozen` and is not deployed by this PR.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
gh pr view claude/slice-1-plan -R bbrown62450/church --json number,url,isDraft,title
```

Expected: the create command prints `https://github.com/bbrown62450/church/pull/<N>`; the view prints `"isDraft":true` and the title starting `Draft: Slice 1a platform`. Keep `<N>` for the next steps.

- [ ] **Step 10: Watch the checks (agent)**

Run with the Bash tool's `run_in_background: true` (the watch can outlast the 10-minute foreground limit; the tool re-invokes the agent when it exits):

```bash
gh pr checks <N> -R bbrown62450/church --watch --interval 30
```

Expected when it exits: every check `pass`: `backend` (the SQLite suite, `689 passed, 5 skipped`), `backend-postgres`, `frontend` (no frontend file changed since `560ebb3` apart from Task 13's generated `openapi.json`, which no frontend check reads yet), and the Vercel preview deployment. Exit code 0. Any `fail` goes to Step 11.

- [ ] **Step 11: Read the `backend-postgres` log and compare (agent)**

```bash
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch claude/slice-1-plan --commit "$(git rev-parse HEAD)" --limit 1 --json databaseId --jq '.[0].databaseId'); echo "run $RUN"
gh run view "$RUN" -R bbrown62450/church --json jobs --jq '.jobs[] | "\(.name): \(.conclusion)"'
gh run view "$RUN" -R bbrown62450/church --json jobs --jq '.jobs[] | select(.name == "backend-postgres") | .steps[] | "\(.name): \(.conclusion)"'
JOB=$(gh run view "$RUN" -R bbrown62450/church --json jobs --jq '.jobs[] | select(.name == "backend-postgres") | .databaseId'); gh run view -R bbrown62450/church --job "$JOB" --log | grep -E "Database: |Running (upgrade|downgrade)|No new upgrade operations detected|pg_smoke|Racer Two|[0-9]+ (passed|failed|errors?)( |,)"
```

(Shell variables do not carry between commands, so each line that needs `$RUN` or `$JOB` sets it itself; if the first line prints `run ` with no id, the run has not been listed yet: run it again.)

Expected:
- jobs: `backend: success`, `backend-postgres: success`, `frontend: success`;
- steps: every step `success`, including `Migrate the empty database to head`, `The models match the migrated schema`, `Every revision downgrades`, `Migrate to head again`, `Identity smoke (ops-2)`, `Postgres-only tests`;
- log lines, in this order: `Database: dialect=postgresql driver=psycopg2 host=localhost database=postgres` before each of the four alembic commands; `Running upgrade  -> 0001_baseline`, `Running upgrade 0001_baseline -> 0002_reconcile`, `Running upgrade 0002_reconcile -> 0003_lockdown`, `Running upgrade 0003_lockdown -> 0004_invites_reusable` (each followed by the revision's message); `No new upgrade operations detected.`; `Running downgrade 0004_invites_reusable -> 0003_lockdown`, `Running downgrade 0003_lockdown -> 0002_reconcile`, `Running downgrade 0002_reconcile -> 0001_baseline`, `Running downgrade 0001_baseline -> `; the four upgrades again; `postgresql 3 [] 1 1 2 google-sub-tabs Racer Two True` and `pg_smoke: OK`; `5 passed, 689 deselected in …s`.

The `5 passed` covers `test_migrations.py`'s three `0003` tests (the first execution of 0003's DO block, both RAISE branches and the single-transaction rollback), `test_api_app.py::test_rls_check_names_tables_without_rls` and this task's `test_identity.py::test_concurrent_first_requests_on_postgres_both_succeed_with_one_id`.

- [ ] **Step 12: Fix any failure in its owning task, then report (agent)**

If everything in Steps 10–11 matched, go to the report below. Otherwise read the failing step's log:

```bash
gh run view <run-id> -R bbrown62450/church --log-failed | tail -80
```

and fix it in the task that owns it:

| Failing step or test | Owning task (files) |
|---|---|
| `Migrate the empty database to head` / `Migrate to head again` | the revision in the last `Running upgrade` line: Task 6 (`0001_baseline.py`), Task 7 (`0002_reconcile.py`), Task 8 (`0003_lockdown.py`), Task 9 (`0004_invites_reusable.py`); no `Running` line at all: Task 5 (`alembic.ini`, `migrations/env.py`) |
| `The models match the migrated schema` (`New upgrade operations detected: …`) | Task 6 (0001 vs `db/models.py`), Task 9 (0004 vs the `Invite` model), or Task 5 (`include_object`, `compare_type` in `env.py`) for dialect-only type differences |
| `Every revision downgrades` | the revision in the last `Running downgrade` line (Tasks 6–9) |
| `Identity smoke (ops-2)` | this task (step order in `ci.yml`), or the revision that changed `users` (Task 6) |
| `test_migrations.py::test_0003_*` | Task 8 (`0003_lockdown.py`, `tests/pg_helpers.py::throwaway_database`) |
| `test_api_app.py::test_rls_check_names_tables_without_rls` | Task 11 (`db/schema_check.py`) |
| `test_identity.py::test_concurrent_first_requests_on_postgres_*` | this task, or `pg_db` (Task 1 fixture, Task 6 wiring) on a setup error |
| a `pg_db` setup error in any Postgres test | Task 1 (`conftest.py::pg_db`) or Task 6 (its upgrade wiring) |
| `backend` job | the task that owns the failing test file (the plan's **File Structure** names the task for each path) |
| `frontend` job or the Vercel preview | nothing in Tasks 1–14 touches `frontend/` except the generated `openapi.json` (Task 13): report the failure to the owner before changing anything |

For each fix: reproduce it locally first where SQLite or offline SQL can show it (for example `.venv/bin/python -m pytest -q backend/tests/test_migrations.py`, or, for the offline Postgres render, `(cd backend && DATABASE_URL=postgresql://u:p@localhost:1/x ../.venv/bin/alembic upgrade head --sql > /dev/null)`, which never connects); change only the owning task's files; run `.venv/bin/python -m pytest -q | tail -1` → `689 passed, 5 skipped`; commit with the subject `Fix: <what> (Task <n>, CI Postgres checkpoint)` and the `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` trailer; have that task re-reviewed (its plan section against the fix's diff) before Task 15; `git push` (never `--force`); repeat Steps 10–11. An infrastructure failure with no test output (the service container never became healthy, `pip install` timed out) gets one `gh run rerun <run-id> -R bbrown62450/church --failed` before it counts as a failure.

Report to the owner in one line, then start Task 15: "Draft PR #<N> (<url>): backend-postgres green: Alembic cycle, `alembic check` clean, `pg_smoke: OK`, `5 passed`." Do not run `gh pr ready`; the PR stays a draft until Task 25 and the owner's yes.

Expected counts after this task: backend `689 passed, 5 skipped` locally (CI `backend-postgres`: `5 passed, 689 deselected`); frontend unchanged at `15 passed`.

---

### Task 15: Frontend tooling: dependencies, Vitest `unit` + `dom` projects, DOM setup, fake API, `react/no-danger`, `gen:api` + CI step (F §5.2, §4.9 item 8, §1.11, §5.4; S Dependencies 1a; AC4, AC15)

The frontend gets the test platform every later task uses. `npm test` runs two Vitest projects: `unit` (Node, `*.test.ts`, as today) and `dom` (jsdom + Testing Library, `*.test.tsx`). `src/test/setup-dom.ts` adds the jest-dom matchers, the jsdom shims Base UI needs (F §4.9 item 8), and the two module mocks of clarification 15 (`next/navigation`, `@/lib/supabase/client`) backed by the spies in `src/test/mocks.ts`, so the real `lib/auth.ts` (T18) runs under test. `src/test/fake-api.ts` stubs `fetch` per test, records requests and fails the test on any unhandled request, even when the UI swallowed the error. ESLint gains `react/no-danger` at error, proved by a test that lints a probe through the ESLint API. `npm run gen:api` turns T13's committed `openapi.json` into `src/lib/api/schema.d.ts`, and CI's `frontend` job regenerates it and fails on `git diff`.

Verified on this machine before writing (Vitest 3.2.7, Node 26, offline): the two-project config with `extends: true` and `--project` filtering; `vi.mock` calls in a `setupFiles` module apply to the test files' imports, and the factory's `await import("./mocks")` is the same module instance as a test's `@/test/mocks` import (clarification 15 is now **verified**); `installFakeApi` from inside a test and from `beforeEach`, delayed async handlers, `AbortController` and `AbortSignal.timeout` rejections, 204 with no body, an unhandled request failing its test through `onTestFinished`, `fetch` restored after the test; the ESLint-API test fails on the current config and passes with the rule (about 1 s); `schema.d.ts` under `globalIgnores` is not linted; `tsc` and `eslint` are clean on every new file except the imports of packages that are not installed yet. **Not verified here:** the new packages themselves (jsdom, Testing Library, jest-dom, user-event, `@vitejs/plugin-react`, openapi-typescript are not in the offline npm cache), so `setup-dom.test.tsx` has never run under jsdom and Step 1 needs the network.

**Files:**
- Modify: `frontend/package.json` (dependencies via `npm install`; the `gen:api` script by hand), `frontend/package-lock.json` (by `npm install`)
- Modify: `frontend/vitest.config.ts` (whole file, 7 lines → two projects + `@vitejs/plugin-react` + the fork flag `--no-experimental-webstorage`)
- Modify: `frontend/eslint.config.mjs` (whole file: a rules object with `"react/no-danger": "error"`; `src/lib/api/schema.d.ts` added to `globalIgnores`)
- Modify: `.github/workflows/ci.yml` (`frontend` job only: one step between `npm run typecheck` and `npm test`; T14's `backend-postgres` edits are untouched)
- Create: `frontend/src/test/mocks.ts`, `frontend/src/test/setup-dom.ts`, `frontend/src/test/fake-api.ts`, `frontend/src/test/fixtures/index.ts`
- Create (generated): `frontend/src/lib/api/schema.d.ts` (by `npm run gen:api` from T13's `frontend/src/lib/api/openapi.json`)
- Test: `frontend/src/test/setup-dom.test.tsx` (new, `dom`), `frontend/src/test/lint-rules.test.ts` (new, `unit`), `backend/tests/test_ci_workflow.py` (append one test after T14's)

**Interfaces:**
- Consumes: `frontend/src/lib/api/openapi.json` (T13, committed; `test_openapi_contract.py` keeps it equal to the live app); its `ChurchOut.role` enum and `ErrorBody`/`ErrorDetail` schemas (T3); `Church`, `Me` types from `@/lib/church` (current `src/lib/church.ts:1-6`; T17 turns them into re-exports of `@/lib/api/types`, which keeps these imports working); `ROOT`, `CI_YML` and `_ci()` defined at the top of `backend/tests/test_ci_workflow.py` (Task 14); T14's state of that file (4 tests) and of `ci.yml` (`backend-postgres` rewritten, `frontend` job unchanged).
- Produces:
  - `package.json` script `"gen:api": "openapi-typescript src/lib/api/openapi.json -o src/lib/api/schema.d.ts"`; dependency `@tanstack/react-query` `^5.101`; devDependencies `jsdom` `^26`, `@testing-library/react` `^16.3`, `@testing-library/dom` `^10.4`, `@testing-library/user-event` `^14.6`, `@testing-library/jest-dom` `^6.6`, `@vitejs/plugin-react` `^5`, `openapi-typescript` `^7` (Vitest stays `^3.2.7`).
  - Vitest projects `unit` (node, `src/**/*.test.ts`) and `dom` (jsdom, `src/**/*.test.tsx`, `setupFiles: ["src/test/setup-dom.ts"]`), root `plugins: [react()]`; root `test.poolOptions.forks.execArgv: ["--no-experimental-webstorage"]`; run one with `npx vitest run --project unit|dom`.
  - `src/test/setup-dom.ts`: `@testing-library/jest-dom/vitest`; `vi.mock("next/navigation")` → `{ useRouter: () => testRouter, usePathname: () => testPathname(), useSearchParams: () => testSearchParams() }` (other exports are not mocked; Vitest names any missing one in its error); `vi.mock("@/lib/supabase/client")` → `{ createClient: () => ({ auth: supabaseAuth }) }`; shims (only where jsdom lacks them) `PointerEvent`, `ResizeObserver`, `matchMedia` (`matches: false`), `Element.prototype.scrollIntoView`, `hasPointerCapture` (false), `setPointerCapture`, `releasePointerCapture`, `getAnimations = () => []`; `beforeEach(resetTestMocks)`; `afterEach`: `cleanup()`, `localStorage.clear()`, `sessionStorage.clear()`. T17 and T18 append `resetStoredChurchIdForTests();` / `resetSigningOutForTests();` (plus imports) as the last statements of this `afterEach` block, never as separate hooks: Vitest 3 runs `afterEach` hooks in reverse registration order, so a hook added below would run before `cleanup()`.
  - `src/test/mocks.ts`: `TEST_ACCESS_TOKEN = "test-access-token"`; `testRouter: { replace: Mock; push: Mock; refresh: Mock; back: Mock }` (one stable object); `supabaseAuth: { getSession: Mock; signOut: Mock }`; `setTestPath(path: string): void` (path may carry a query, e.g. `"/welcome?tab=join"`); `testPathname(): string`; `testSearchParams(): URLSearchParams` (the same object until the next `setTestPath`); `resetTestMocks(): void` (spies reset; path `/`; `getSession` resolves `{ data: { session: { access_token: TEST_ACCESS_TOKEN } }, error: null }`; `signOut` resolves `{ error: null }`). Node-project tests that import these spies (T18 `auth.test.ts`, which declares its own `vi.mock`) call `resetTestMocks()` in their own `beforeEach`, because `setup-dom.ts` does not run in `unit`.
  - `src/test/fake-api.ts`: `type RecordedRequest = { method: string; path: string; headers: Record<string, string>; body: unknown }` (`path` = pathname + query; header keys stored lower-case, lookups ignore case, so `req.headers["X-Church-Id"]` and `toMatchObject({ headers: { "X-Church-Id": id } })` both work; a JSON string body is parsed); `type FakeResponse = { status: number; body?: unknown; headers?: Record<string, string> }`; `type FakeHandler = unknown | ((req: RecordedRequest) => FakeResponse | Promise<FakeResponse> | unknown)`; `type FakeApi = { requests: RecordedRequest[]; set(route: string, handler: FakeHandler): void }`; `FAKE_REQUEST_ID = "4f9a2c1e8b7d4e6fa0c3b5d7e9f1a2b4"` (so "(Ref: 4f9a2c1e)"); `fakeError(status: number, code: string, message: string, extra?: { details?: Record<string, unknown>; fields?: Record<string, string>; request_id?: string }): FakeResponse` (body `{ error: { code, message, request_id, fields?, details? } }`, header `X-Request-Id`); `installFakeApi(handlers: Record<string, FakeHandler>): FakeApi`. Rules: route keys are `"METHOD /path"`, matched on path + query first, then the path alone; a non-function handler is a 200 JSON body; a function may return a body or a `FakeResponse`, synchronously or after an `await` (delayed responses, T23); a `FakeResponse` is recognized as a plain object with a numeric `status` and no keys besides `status`/`body`/`headers`; `body: undefined` or status 204/205/304 sends no body; requests are recorded when `fetch` is called (before any delay); an aborted `signal` rejects with `signal.reason` (as `fetch` does); an unhandled request rejects with `TypeError("installFakeApi: no handler for GET /x")` and the test fails when it finishes; the stub is removed when the test finishes (`vi.unstubAllGlobals()`). Call it inside a test or a `beforeEach`.
  - `src/test/fixtures/index.ts`: `CHURCH_IDS = { grace: "11111111-1111-4111-8111-111111111111", hope: "22222222-2222-4222-8222-222222222222", trinity: "33333333-3333-4333-8333-333333333333" }`; `USER_ID = "99999999-9999-4999-8999-999999999999"`; `church(overrides?: Partial<Church>): Church` (default `{ id: CHURCH_IDS.grace, name: "Grace", role: "admin" }`); `me(overrides?: Partial<Me>): Me` (default user `{ id: USER_ID, email: "pat@example.com", name: "Pat Pastor", picture: null }`, `churches: [church()]`; overrides replace top-level fields).
  - `src/lib/api/schema.d.ts` (generated; exports `paths`, `components`, `operations`; `components["schemas"]["ChurchOut"]`, `["MeOut"]`, `["ErrorBody"]`). Later users: T16 `types.ts`; CI; T25.
  - CI `frontend` step `npm run gen:api && git diff --exit-code src/lib/api/schema.d.ts` after `npm run typecheck`, before `npm test`.
  - Environment note for T16/T18–T23: in the `dom` project `AbortController`, `AbortSignal`, `DOMException` and `window === globalThis` come from jsdom, while `fetch`, `Request`, `Response` and `Headers` stay Node's (Vitest copies them in because jsdom lacks them). Every DOM test must stub `fetch` (via `installFakeApi` or a `fetchImpl`): the real Node `fetch` rejects a jsdom `AbortSignal`.

- [ ] **Step 1: Install the dependencies (needs the network)**

These packages are not in this machine's offline npm cache, so this is the one step that needs the network. Run from the repo root:

```bash
(cd frontend && npm install @tanstack/react-query@^5.101 \
  && npm install --save-dev jsdom@^26 @testing-library/react@^16.3 @testing-library/dom@^10.4 \
       @testing-library/user-event@^14.6 @testing-library/jest-dom@^6.6 \
       @vitejs/plugin-react@^5 openapi-typescript@^7)
```

Expected: both commands end with `added N packages` and print no `ERESOLVE` and no `peer dependency` conflict. Never pass `--force` or `--legacy-peer-deps`. If the network is unavailable, stop and tell the owner (no fallback: nothing below runs without these packages). If npm reports a peer conflict for `@vitejs/plugin-react` (6.x targets Vite 8; this project runs Vitest 3.2.7 on Vite 7.3.6), stop and report the exact message; dropping the plugin (Vite's esbuild already compiles JSX from `tsconfig.json`'s `"jsx": "react-jsx"`) is an owner decision because F §5.2 names the plugin.

Then check the majors and the single Vite:

```bash
(cd frontend && node -e '
const fs = require("fs");
const pkg = JSON.parse(fs.readFileSync("package.json", "utf8"));
const want = [
  ["dependencies", "@tanstack/react-query", 5], ["devDependencies", "jsdom", 26],
  ["devDependencies", "@testing-library/react", 16], ["devDependencies", "@testing-library/dom", 10],
  ["devDependencies", "@testing-library/user-event", 14], ["devDependencies", "@testing-library/jest-dom", 6],
  ["devDependencies", "@vitejs/plugin-react", 5], ["devDependencies", "openapi-typescript", 7],
  ["devDependencies", "vitest", 3],
];
let ok = true;
for (const [section, name, major] of want) {
  const installed = JSON.parse(fs.readFileSync(`node_modules/${name}/package.json`, "utf8")).version;
  const good = Boolean(pkg[section][name]) && Number(installed.split(".")[0]) === major;
  ok = ok && good;
  console.log(`${good ? "ok " : "BAD"} ${section} ${name} ${pkg[section][name]} -> ${installed}`);
}
process.exit(ok ? 0 : 1);')
(cd frontend && npm ls vite vitest @vitejs/plugin-react)
(cd frontend && npx vitest run | tail -4)
git status --short
```

Expected: nine `ok` lines and exit 0; `npm ls` shows `vitest@3.2.7` and one `vite@7.3.6` (other occurrences `deduped`), with no `invalid` or `UNMET PEER`; Vitest still `Tests  15 passed (15)` with the old config; `git status --short` shows ` M frontend/package-lock.json`, ` M frontend/package.json` and `?? .claude/` only. Note the resolved versions for the commit body.

- [ ] **Step 2: Write the failing tests**

Create `frontend/src/test/setup-dom.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { describe, expect, it } from "vitest";
import { createClient } from "@/lib/supabase/client";
import { setTestPath, supabaseAuth, TEST_ACCESS_TOKEN, testRouter } from "@/test/mocks";

// The two tests run in order: the first dirties the DOM, storage and spies; the
// second proves setup-dom.ts reset all of them (F §5.2).
describe("the dom project setup (setup-dom.ts)", () => {
  it("renders with jest-dom matchers and the shared navigation and Supabase mocks", async () => {
    render(<button type="button">Save</button>);
    expect(screen.getByRole("button", { name: "Save" })).toBeInTheDocument();

    expect(useRouter()).toBe(testRouter);
    setTestPath("/welcome?tab=join");
    expect(usePathname()).toBe("/welcome");
    expect(useSearchParams().get("tab")).toBe("join");

    expect(createClient().auth).toBe(supabaseAuth);
    const { data } = await createClient().auth.getSession();
    expect(data.session?.access_token).toBe(TEST_ACCESS_TOKEN);

    testRouter.replace("/login");
    window.localStorage.setItem("activeChurchId", "stale");
    window.sessionStorage.setItem("wsb:pendingInviteCode", "stale");
  });

  it("has the Base UI jsdom shims and starts each test clean", () => {
    expect(document.body).toBeEmptyDOMElement();
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
    expect(testRouter.replace).not.toHaveBeenCalled();
    expect(usePathname()).toBe("/");

    expect(new PointerEvent("pointerdown", { pointerId: 7 }).pointerId).toBe(7);
    const observer = new ResizeObserver(() => {});
    expect(() => {
      observer.observe(document.body);
      observer.disconnect();
    }).not.toThrow();
    expect(window.matchMedia("(min-width: 640px)").matches).toBe(false);

    const element = document.createElement("div");
    expect(() => element.scrollIntoView()).not.toThrow();
    expect(element.hasPointerCapture(1)).toBe(false);
    expect(() => element.releasePointerCapture(1)).not.toThrow();
    expect(element.getAnimations()).toEqual([]);
  });
});
```

Create `frontend/src/test/lint-rules.test.ts`:

```ts
import path from "node:path";
import { fileURLToPath } from "node:url";
import { ESLint } from "eslint";
import { expect, it } from "vitest";

// frontend/, so ESLint loads the project's eslint.config.mjs.
const FRONTEND_ROOT = fileURLToPath(new URL("../..", import.meta.url));

const PROBE = `export function Probe({ html }: { html: string }) {
  return <div dangerouslySetInnerHTML={{ __html: html }} />;
}
`;

it("reports dangerouslySetInnerHTML as a react/no-danger error (F §4.9)", async () => {
  const eslint = new ESLint({ cwd: FRONTEND_ROOT });
  const [result] = await eslint.lintText(PROBE, {
    // Never written to disk; the path only selects the config for a .tsx file under src/.
    filePath: path.join(FRONTEND_ROOT, "src", "components", "lint-probe.tsx"),
  });
  const noDanger = result.messages.filter((message) => message.ruleId === "react/no-danger");
  expect(noDanger).toHaveLength(1);
  expect(noDanger[0].severity).toBe(2);
}, 30_000);
```

Append to the end of `backend/tests/test_ci_workflow.py` (after T14's tests; `ROOT`, `CI_YML` and `_ci()` are defined at the top of the file (Task 14)):

```python


# --- slice 1a (Task 15): the frontend job regenerates the API types (F §5.4, §1.11) ---

def test_ci_frontend_regenerates_api_types_and_fails_on_diff():
    """CI rebuilds schema.d.ts from the committed OpenAPI snapshot and fails when
    the committed types differ; test_openapi_contract.py keeps the snapshot equal
    to the live app, so the frontend types can never drift from the API."""
    import json

    ci = _ci()
    job = ci["jobs"]["frontend"]
    assert job["defaults"]["run"]["working-directory"] == "frontend"
    runs = [step.get("run", "") for step in job["steps"]]
    regenerate = "npm run gen:api && git diff --exit-code src/lib/api/schema.d.ts"
    assert regenerate in runs
    assert runs.index("npm run typecheck") < runs.index(regenerate) < runs.index("npm test")

    frontend = ROOT / "frontend"
    package = json.loads((frontend / "package.json").read_text(encoding="utf-8"))
    assert package["scripts"]["gen:api"] == (
        "openapi-typescript src/lib/api/openapi.json -o src/lib/api/schema.d.ts"
    )
    assert "openapi-typescript" in package["devDependencies"]
    assert (frontend / "src" / "lib" / "api" / "openapi.json").is_file()
    assert (frontend / "src" / "lib" / "api" / "schema.d.ts").is_file()
```

- [ ] **Step 3: Run the tests to verify they fail**

Run:

```bash
(cd frontend && npx vitest run src/test/setup-dom.test.tsx 2>&1 | tail -6)
(cd frontend && npx vitest run src/test/lint-rules.test.ts 2>&1 | grep -E "✓|×|→|Tests")
.venv/bin/python -m pytest -q backend/tests/test_ci_workflow.py 2>&1 | tail -3
```

Expected:
- `No test files found, exiting with code 1`, with `filter: src/test/setup-dom.test.tsx` and `include: src/**/*.test.ts` (the current config has no `.tsx` project);
- `× reports dangerouslySetInnerHTML as a react/no-danger error (F §4.9)` with `→ expected [] to have a length of 1 but got +0`, then `Tests  1 failed (1)`;
- `FAILED backend/tests/test_ci_workflow.py::test_ci_frontend_regenerates_api_types_and_fails_on_diff - AssertionError` (on `assert regenerate in runs`), then `1 failed, 4 passed`.

- [ ] **Step 4: Replace `frontend/vitest.config.ts`**

Whole file (was 7 lines: one Node environment, `src/**/*.test.ts`):

```ts
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// F §5.2: `npm test` runs both projects. Node for pure modules (*.test.ts);
// jsdom + Testing Library for components and layouts (*.test.tsx).
export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  test: {
    // Node >= 25 defines its own localStorage/sessionStorage globals, which hide
    // jsdom's in the dom project (window.localStorage is undefined). CI's Node 22
    // accepts the flag; the feature is already off there.
    poolOptions: { forks: { execArgv: ["--no-experimental-webstorage"] } },
    projects: [
      {
        extends: true,
        test: { name: "unit", environment: "node", include: ["src/**/*.test.ts"] },
      },
      {
        extends: true,
        test: {
          name: "dom",
          environment: "jsdom",
          include: ["src/**/*.test.tsx"],
          setupFiles: ["src/test/setup-dom.ts"],
        },
      },
    ],
  },
});
```

The `poolOptions` line comes from Tasks 17 and 19's trials on this machine (Node 26.4.0, Vitest 3.2.7): without it every DOM test fails in `setup-dom.ts`'s `afterEach` with `TypeError: Cannot read properties of undefined (reading 'clear')` and the log shows `ExperimentalWarning: localStorage is not available because --localstorage-file was not provided.` It must sit at the root of `test`: a per-project `poolOptions` does not typecheck and had no effect.

- [ ] **Step 5: Create the DOM setup and its spies**

Create `frontend/src/test/mocks.ts`:

```ts
/**
 * Spies behind the module mocks that `setup-dom.ts` installs for every DOM test
 * (clarification 15): `next/navigation` and `@/lib/supabase/client`. The real
 * `lib/auth.ts` therefore runs under test, and tests assert on these spies.
 * `resetTestMocks()` runs before each DOM test (setup-dom.ts).
 */
import { vi } from "vitest";

/** The access token the default `getSession` spy hands out. */
export const TEST_ACCESS_TOKEN = "test-access-token";

/** What `useRouter()` returns in DOM tests (one stable object, like Next's). */
export const testRouter = {
  replace: vi.fn(),
  push: vi.fn(),
  refresh: vi.fn(),
  back: vi.fn(),
};

/** `createClient().auth` in DOM tests. */
export const supabaseAuth = {
  getSession: vi.fn(),
  signOut: vi.fn(),
};

let pathname = "/";
let searchParams = new URLSearchParams();

/** Sets what `usePathname()` and `useSearchParams()` return, e.g. "/welcome?tab=join". */
export function setTestPath(path: string): void {
  const url = new URL(path, "http://localhost");
  pathname = url.pathname;
  searchParams = url.searchParams;
}

/** `usePathname()` in DOM tests. */
export function testPathname(): string {
  return pathname;
}

/** `useSearchParams()` in DOM tests: the same object until the next `setTestPath`. */
export function testSearchParams(): URLSearchParams {
  return searchParams;
}

/** Back to defaults: path "/", a signed-in session, a successful local sign-out. */
export function resetTestMocks(): void {
  for (const spy of Object.values(testRouter)) spy.mockReset();
  setTestPath("/");
  supabaseAuth.getSession.mockReset();
  supabaseAuth.getSession.mockResolvedValue({
    data: { session: { access_token: TEST_ACCESS_TOKEN } },
    error: null,
  });
  supabaseAuth.signOut.mockReset();
  supabaseAuth.signOut.mockResolvedValue({ error: null });
}
```

Create `frontend/src/test/setup-dom.ts`:

```ts
/**
 * Setup for the `dom` Vitest project (jsdom; F §5.2, §4.9 item 8).
 *
 * - jest-dom matchers (`toBeInTheDocument`, …) with their types.
 * - Base UI's jsdom gaps: PointerEvent, ResizeObserver, matchMedia,
 *   scrollIntoView, pointer capture and getAnimations.
 * - Module mocks for every DOM test (clarification 15): `next/navigation` and
 *   `@/lib/supabase/client`, backed by the spies in `./mocks`, so the real
 *   `lib/auth.ts` runs under test.
 * - Before each test the spies go back to their defaults; after each test the
 *   rendered tree is unmounted and both storages are cleared.
 */
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, beforeEach, vi } from "vitest";
import { resetTestMocks } from "./mocks";

vi.mock("next/navigation", async () => {
  const mocks = await import("./mocks");
  return {
    useRouter: () => mocks.testRouter,
    usePathname: () => mocks.testPathname(),
    useSearchParams: () => mocks.testSearchParams(),
  };
});

vi.mock("@/lib/supabase/client", async () => {
  const mocks = await import("./mocks");
  return { createClient: () => ({ auth: mocks.supabaseAuth }) };
});

// --- jsdom shims (only where jsdom lacks the API) ---------------------------------

if (typeof window.PointerEvent !== "function") {
  class PointerEventShim extends MouseEvent {
    readonly pointerId: number;
    readonly pointerType: string;
    readonly isPrimary: boolean;
    readonly width: number;
    readonly height: number;
    readonly pressure: number;

    constructor(type: string, init: PointerEventInit = {}) {
      super(type, init);
      this.pointerId = init.pointerId ?? 1;
      this.pointerType = init.pointerType ?? "mouse";
      this.isPrimary = init.isPrimary ?? true;
      this.width = init.width ?? 1;
      this.height = init.height ?? 1;
      this.pressure = init.pressure ?? 0;
    }
  }
  window.PointerEvent = PointerEventShim as unknown as typeof PointerEvent;
}

if (typeof window.ResizeObserver !== "function") {
  class ResizeObserverShim {
    observe(): void {}
    unobserve(): void {}
    disconnect(): void {}
  }
  window.ResizeObserver = ResizeObserverShim as unknown as typeof ResizeObserver;
}

if (typeof window.matchMedia !== "function") {
  window.matchMedia = (query: string): MediaQueryList =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }) as MediaQueryList;
}

Element.prototype.scrollIntoView ??= function scrollIntoView() {};
Element.prototype.hasPointerCapture ??= () => false;
Element.prototype.setPointerCapture ??= () => {};
Element.prototype.releasePointerCapture ??= () => {};
Element.prototype.getAnimations ??= () => [];

// --- per-test reset -----------------------------------------------------------------

beforeEach(() => {
  resetTestMocks();
});

afterEach(() => {
  cleanup();
  window.localStorage.clear();
  window.sessionStorage.clear();
});
```

The mock factories import `./mocks` inside the factory (`await import`), because `vi.mock` is hoisted above the file's imports; Vitest gives the setup file and the test file one module instance, so a test's `import { testRouter } from "@/test/mocks"` is the very object `useRouter()` returns.

- [ ] **Step 6: Create the fake API and the fixtures**

Create `frontend/src/test/fake-api.ts`:

```ts
/**
 * A fake API server for tests (F §5.2): `installFakeApi({ "GET /me": me(), ... })`
 * stubs global `fetch` for the current test.
 *
 * - Routes are "METHOD /path". A request matches its exact path with the query
 *   string first, then the path without it.
 * - A handler is either a response body (sent as 200 JSON) or a function of the
 *   recorded request that returns a body or a `FakeResponse`, possibly after an
 *   `await` (a delayed response). A `FakeResponse` is a plain object with a numeric
 *   `status` and no keys other than `status`, `body` and `headers`; build error
 *   responses with `fakeError`.
 * - Every request is recorded (at call time, before any delay) with lower-case
 *   header names; header lookups on a recorded request ignore case.
 * - An aborted `signal` rejects the call with the signal's reason, as `fetch` does.
 * - A request with no handler rejects, and fails the test when it finishes, even
 *   if the UI swallowed the error. The stub is removed when the test finishes.
 */
import { onTestFinished, vi } from "vitest";

export type RecordedRequest = {
  method: string;
  path: string;
  headers: Record<string, string>;
  body: unknown;
};

export type FakeResponse = {
  status: number;
  body?: unknown;
  headers?: Record<string, string>;
};

/** A body (sent as 200 JSON), or a function returning a body or a `FakeResponse`. */
export type FakeHandler =
  | unknown
  | ((req: RecordedRequest) => FakeResponse | Promise<FakeResponse> | unknown);

export type FakeApi = {
  /** Every request so far, in call order. */
  requests: RecordedRequest[];
  /** Adds or replaces the handler for a route, e.g. `api.set("GET /me", fakeError(...))`. */
  set(route: string, handler: FakeHandler): void;
};

/** The `request_id` `fakeError` uses unless told otherwise (a uuid4 hex, like the API's). */
export const FAKE_REQUEST_ID = "4f9a2c1e8b7d4e6fa0c3b5d7e9f1a2b4";

/** An error response in the API's error body shape (F §1.4), with its `X-Request-Id` header. */
export function fakeError(
  status: number,
  code: string,
  message: string,
  extra: { details?: Record<string, unknown>; fields?: Record<string, string>; request_id?: string } = {},
): FakeResponse {
  const { request_id = FAKE_REQUEST_ID, fields, details } = extra;
  const error: Record<string, unknown> = { code, message, request_id };
  if (fields) error.fields = fields;
  if (details) error.details = details;
  return { status, body: { error }, headers: { "X-Request-Id": request_id } };
}

const RESPONSE_KEYS = new Set(["status", "body", "headers"]);

function isFakeResponse(value: unknown): value is FakeResponse {
  if (typeof value !== "object" || value === null || Array.isArray(value)) return false;
  const keys = Object.keys(value);
  return (
    keys.includes("status") &&
    typeof (value as { status: unknown }).status === "number" &&
    keys.every((key) => RESPONSE_KEYS.has(key))
  );
}

function caseInsensitive(headers: Record<string, string>): Record<string, string> {
  return new Proxy(headers, {
    get: (target, prop) =>
      typeof prop === "string" ? target[prop.toLowerCase()] : Reflect.get(target, prop),
    has: (target, prop) =>
      typeof prop === "string" ? prop.toLowerCase() in target : Reflect.has(target, prop),
    getOwnPropertyDescriptor: (target, prop) =>
      Reflect.getOwnPropertyDescriptor(target, typeof prop === "string" ? prop.toLowerCase() : prop),
  });
}

function record(input: RequestInfo | URL, init: RequestInit | undefined): RecordedRequest {
  const request = input instanceof Request ? input : undefined;
  const url = new URL(request ? request.url : String(input), "http://localhost");
  const headers: Record<string, string> = {};
  new Headers(init?.headers ?? request?.headers).forEach((value, name) => {
    headers[name] = value;
  });
  let body: unknown = init?.body ?? undefined;
  if (typeof body === "string") {
    try {
      body = JSON.parse(body);
    } catch {
      // Not JSON: keep the raw string.
    }
  }
  return {
    method: (init?.method ?? request?.method ?? "GET").toUpperCase(),
    path: url.pathname + url.search,
    headers: caseInsensitive(headers),
    body,
  };
}

function toResponse(result: unknown): Response {
  const { status, body, headers = {} } = isFakeResponse(result) ? result : { status: 200, body: result };
  const empty = body === undefined || status === 204 || status === 205 || status === 304;
  return new Response(empty ? null : JSON.stringify(body), {
    status,
    headers: empty ? headers : { "Content-Type": "application/json", ...headers },
  });
}

function abortReason(signal: AbortSignal): unknown {
  return signal.reason ?? new DOMException("This operation was aborted", "AbortError");
}

export function installFakeApi(handlers: Record<string, FakeHandler>): FakeApi {
  const routes = new Map<string, FakeHandler>(Object.entries(handlers));
  const requests: RecordedRequest[] = [];
  const unhandled: string[] = [];

  async function fakeFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
    const req = record(input, init);
    requests.push(req);
    const signal = init?.signal ?? (input instanceof Request ? input.signal : undefined);
    if (signal?.aborted) throw abortReason(signal);

    const pathOnly = req.path.split("?")[0];
    const route = [`${req.method} ${req.path}`, `${req.method} ${pathOnly}`].find((key) => routes.has(key));
    if (route === undefined) {
      unhandled.push(`${req.method} ${req.path}`);
      throw new TypeError(`installFakeApi: no handler for ${req.method} ${req.path}`);
    }
    const handler = routes.get(route);
    const pending = Promise.resolve(typeof handler === "function" ? handler(req) : handler);
    if (!signal) return toResponse(await pending);
    return new Promise<Response>((resolve, reject) => {
      const onAbort = () => reject(abortReason(signal));
      signal.addEventListener("abort", onAbort, { once: true });
      pending.then(
        (result) => {
          signal.removeEventListener("abort", onAbort);
          if (signal.aborted) reject(abortReason(signal));
          else resolve(toResponse(result));
        },
        (error: unknown) => {
          signal.removeEventListener("abort", onAbort);
          reject(error);
        },
      );
    });
  }

  vi.stubGlobal("fetch", vi.fn(fakeFetch));
  onTestFinished(() => {
    vi.unstubAllGlobals();
    if (unhandled.length > 0) {
      throw new Error(`installFakeApi: requests without a handler: ${unhandled.join(", ")}`);
    }
  });

  return {
    requests,
    set(route, handler) {
      routes.set(route, handler);
    },
  };
}
```

Create `frontend/src/test/fixtures/index.ts`:

```ts
/**
 * Builders for API payloads in tests. Each call returns a fresh object;
 * `overrides` replace top-level fields (pass a whole `user` to change it).
 */
import type { Church, Me } from "@/lib/church";

/** Ids that read well in failure output (valid UUIDs, like the API's). */
export const CHURCH_IDS = {
  grace: "11111111-1111-4111-8111-111111111111",
  hope: "22222222-2222-4222-8222-222222222222",
  trinity: "33333333-3333-4333-8333-333333333333",
} as const;

export const USER_ID = "99999999-9999-4999-8999-999999999999";

/** Grace (admin) unless overridden. */
export function church(overrides: Partial<Church> = {}): Church {
  return { id: CHURCH_IDS.grace, name: "Grace", role: "admin", ...overrides };
}

/** Pat Pastor, a member of Grace only, unless overridden. */
export function me(overrides: Partial<Me> = {}): Me {
  return {
    user: { id: USER_ID, email: "pat@example.com", name: "Pat Pastor", picture: null },
    churches: [church()],
    ...overrides,
  };
}
```

- [ ] **Step 7: Enforce `react/no-danger`; ignore the generated types**

Replace `frontend/eslint.config.mjs` (whole file, 18 lines → 26):

```js
import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    rules: {
      // F §4.9: never render raw HTML; user and AI text is rendered as text.
      "react/no-danger": "error",
    },
  },
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // Generated by `npm run gen:api` (openapi-typescript); CI fails if it drifts.
    "src/lib/api/schema.d.ts",
  ]),
]);

export default eslintConfig;
```

The `react` plugin is already registered by `eslint-config-next`, so the rule needs no plugin entry.

- [ ] **Step 8: Add `gen:api` and generate `schema.d.ts`**

In `frontend/package.json`, replace the end of the `scripts` block:

```json
    "typecheck": "tsc --noEmit",
    "test": "vitest run"
  },
```

with:

```json
    "typecheck": "tsc --noEmit",
    "test": "vitest run",
    "gen:api": "openapi-typescript src/lib/api/openapi.json -o src/lib/api/schema.d.ts"
  },
```

Then generate the types and check them:

```bash
(cd frontend && npm run gen:api)
head -4 frontend/src/lib/api/schema.d.ts
grep -c 'ChurchOut: {\|MeOut: {\|ErrorBody: {' frontend/src/lib/api/schema.d.ts
grep -A8 'ChurchOut: {' frontend/src/lib/api/schema.d.ts | grep 'role'
(cd frontend && shasum src/lib/api/schema.d.ts && npm run gen:api > /dev/null && shasum src/lib/api/schema.d.ts)
```

Expected: openapi-typescript prints its version and a `src/lib/api/openapi.json → src/lib/api/schema.d.ts` line (lint warnings from its bundled Redocly check are fine; an error is not — stop and report it); the file starts with

```
/**
 * This file was auto-generated by openapi-typescript.
 * Do not make direct changes to the file.
 */
```

the `grep -c` prints `3` (one line each for the three schemas); the role line is `role: "owner" | "admin" | "member";` (T3's `Literal`); the two `shasum` lines are identical (the output is deterministic, which the CI diff relies on). Never edit this file by hand: regenerate it after `backend/scripts/export_openapi.py` changes `openapi.json`.

- [ ] **Step 9: Add the CI step**

In `.github/workflows/ci.yml`, `frontend` job, replace:

```yaml
      - run: npm run lint
      - run: npm run typecheck
      - run: npm test
```

with:

```yaml
      - run: npm run lint
      - run: npm run typecheck
      - name: API types match the OpenAPI snapshot (F §5.4)
        run: npm run gen:api && git diff --exit-code src/lib/api/schema.d.ts
      - run: npm test
```

The job's `working-directory: frontend` makes both the script and the git pathspec resolve inside `frontend/`.

- [ ] **Step 10: Run the tests, types, lint and the backend suite**

Run:

```bash
(cd frontend && npx vitest run src/test 2>&1 | tail -5)
(cd frontend && npm test 2>&1 | tail -5 && npm run typecheck && npm run lint)
.venv/bin/python -m pytest -q backend/tests/test_ci_workflow.py 2>&1 | tail -3
.venv/bin/python -m pytest -q | tail -1
git status --short
```

Expected:
- `src/test`: `Test Files  2 passed (2)`, `Tests  3 passed (3)` (`|dom| src/test/setup-dom.test.tsx (2 tests)`, `|unit| src/test/lint-rules.test.ts (1 test)`);
- `npm test`: `Test Files  5 passed (5)`, `Tests  18 passed (18)` (15 → 18: the existing `api`, `church` and `latest` files run in `|unit|`); `typecheck` and `lint` exit 0 with no output beyond the script banners;
- `5 passed`, then **`690 passed, 5 skipped`** (689 after T14, + 1);
- `git status --short`: ` M .github/workflows/ci.yml`, ` M backend/tests/test_ci_workflow.py`, ` M frontend/eslint.config.mjs`, ` M frontend/package-lock.json`, ` M frontend/package.json`, ` M frontend/vitest.config.ts`, `?? .claude/`, `?? frontend/src/lib/api/schema.d.ts`, `?? frontend/src/test/` — nothing else.

If `setup-dom.test.tsx` fails under jsdom (the one part never run on this machine): a missing shim shows as a `TypeError` naming the API (add it to `setup-dom.ts` with the same only-if-missing guard); a jest-dom matcher type error means `@testing-library/jest-dom/vitest` did not load (check Step 1's install). Fix within this task's files and rerun.

- [ ] **Step 11: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vitest.config.ts \
        frontend/eslint.config.mjs frontend/src/lib/api/schema.d.ts \
        frontend/src/test/mocks.ts frontend/src/test/setup-dom.ts frontend/src/test/fake-api.ts \
        frontend/src/test/fixtures/index.ts frontend/src/test/setup-dom.test.tsx \
        frontend/src/test/lint-rules.test.ts \
        .github/workflows/ci.yml backend/tests/test_ci_workflow.py
git commit -m "Frontend: Vitest unit + dom projects, fake API, react/no-danger, gen:api in CI (F §5.2, §4.9, §1.11, §5.4)

npm test now runs two projects: unit (node, *.test.ts) and dom (jsdom and
Testing Library, *.test.tsx). setup-dom.ts adds jest-dom, the Base UI jsdom
shims and the next/navigation and Supabase client mocks behind the spies in
src/test/mocks.ts. installFakeApi stubs fetch per test, records requests and
fails the test on any request without a handler. ESLint enforces
react/no-danger. gen:api builds src/lib/api/schema.d.ts from the committed
OpenAPI snapshot, and CI fails when the committed types drift.

Adds @tanstack/react-query 5; jsdom 26, Testing Library (react 16, dom 10,
user-event 14, jest-dom 6), @vitejs/plugin-react 5 and openapi-typescript 7
as dev dependencies; Vitest stays 3.2.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 16: API client, error union, timeouts, types; `test_error_registry.py` (F §4.5, §1.5, §1.8; ops handoff; AC5)

`src/lib/api.ts` moves to `src/lib/api/client.ts` (F §4.11) and becomes the amended client of F §4.5: `method`, `json`, `idempotencyKey`, `ifMatch`, `timeoutMs` and `signal`, with `ApiError` carrying `fields`, `requestId`, `retryAfterSeconds` and `details`. `requestId` is the body's `request_id`, else the `X-Request-Id` response header (ops handoff; CORS already exposes it, `backend/api/main.py:48-50`). A non-JSON or code-less error body gets `internal_error` at 500 and above and the client code `unknown` below (clarification 9), so the slice-0 fallback code `"error"` disappears on this side too; a 204 or empty 2xx body returns `undefined` (slice-0 carry-over). `errors.ts` holds the `ApiErrorCode` union: the **29** server codes of Task 2's `ERROR_CODES` (owner Q2) plus the client codes, and `backend/tests/test_error_registry.py` checks the two in both directions. Creating `errors.ts` also switches on ops' `test_foundation_setup.py::test_frontend_error_union_lists_db_unavailable_once_it_exists`, which was inert until this file existed; it passes because the union lists `db_unavailable`.

Copy decisions the spec leaves open (recorded here, used by later tasks): a caller's abort is `ApiError(0, "aborted", "The request was cancelled.")` (Task 18's sign-out rejection uses its own message, "Signing out."); `timeoutMs` defaults to `timeoutFor(method, path)`, so 1b's `POST /churches` gets its 30 s without passing anything; `Retry-After` is read from the header and falls back to `details.retry_after_seconds`; `describeError` of anything that is not an `ApiError` is "Something went wrong." (a render bug's `TypeError` text never reaches the page).

The timeout and the caller's signal share one `AbortController`, combined by hand: F §4.5 rules out `AbortSignal.any` (older iOS Safari). The body is read before the timer is cleared, so a response whose body stalls also times out.

`types.ts` has no consumer until Task 17 (`lib/church.ts` re-exports `Church` and `Me` from it); `npm run typecheck` still checks it against Task 15's generated `schema.d.ts`.

**Files:**
- Move: `frontend/src/lib/api.ts` → `frontend/src/lib/api/client.ts` (then the whole file is replaced, Step 6)
- Move: `frontend/src/lib/api.test.ts` → `frontend/src/lib/api/client.test.ts` (import line in Step 1; whole file replaced in Step 2)
- Modify: `frontend/src/app/page.tsx:10` (import path only; the file is deleted in Task 23)
- Create: `frontend/src/lib/api/errors.ts`, `frontend/src/lib/api/timeouts.ts`, `frontend/src/lib/api/types.ts`
- Test: `frontend/src/lib/api/client.test.ts` (8 kept, 10 new), `frontend/src/lib/api/errors.test.ts` (6, new), `backend/tests/test_error_registry.py` (2, new)

**Interfaces:**
- Consumes: Task 2's `domain_errors.ERROR_CODES: dict[str, int]` (29 keys); Task 15's generated `frontend/src/lib/api/schema.d.ts` (`export interface components { schemas: { ChurchOut; MeOut; ErrorBody; … } }`, from Task 13's `openapi.json`; `ErrorBody` is there because Task 3's `error_responses(...)` documents it on every route, and `ChurchOut.role` is Task 3's `Literal`); Task 15's Vitest `unit` project (node environment, `src/**/*.test.ts`), which runs both new frontend test files without the DOM setup.
- Produces:
  - `frontend/src/lib/api/client.ts`:
    - `export type ApiOptions = { token: string; churchId?: string | null; method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE"; json?: unknown; idempotencyKey?: string; ifMatch?: string; timeoutMs?: number; signal?: AbortSignal; init?: RequestInit; baseUrl?: string; fetchImpl?: typeof fetch }`.
    - `export async function apiFetch<T>(path: string, opts: ApiOptions): Promise<T>`: headers `Authorization: Bearer <token>`, `X-Church-Id` (when `churchId`), `Idempotency-Key`, `If-Match`, `Content-Type: application/json` (when `json` is given; body `JSON.stringify(json)`); `method` = `opts.method ?? init.method ?? "GET"`; timeout `opts.timeoutMs ?? timeoutFor(method, path)`; caller signal `opts.signal ?? init.signal`; 204 or empty body → `undefined as T`. Errors: timeout → `ApiError(0, "timeout", "This is taking too long. Try again.")`; caller abort → `ApiError(0, "aborted", "The request was cancelled.")`; transport failure → `ApiError(0, "network_error", "Can't reach the server. Check your connection and try again.")`; non-2xx → `ApiError(res.status, error.code ?? (status >= 500 ? "internal_error" : "unknown"), error.message ?? "Something went wrong.", { fields, requestId, retryAfterSeconds, details })`.
    - `export type ApiErrorExtra = { fields?: Record<string, string>; requestId?: string; retryAfterSeconds?: number; details?: Record<string, unknown> }`.
    - `export class ApiError extends Error { status: number; code: ApiErrorCode; fields?: Record<string, string>; requestId?: string; retryAfterSeconds?: number; details?: Record<string, unknown>; constructor(status: number, code: ApiErrorCode, message: string, extra: ApiErrorExtra = {}) }`, `name === "ApiError"`. Later users: Task 18 (`getAccessToken` throws `new ApiError(401, "unauthenticated", "Please sign in.")` and `new ApiError(0, "aborted", "Signing out.")`; `isRetryable`), Tasks 20-23, 1b.
  - `frontend/src/lib/api/errors.ts`: `export type ServerErrorCode` (the 29 literals, one per line, grouped by status as in `ERROR_CODES`); `export type ClientErrorCode = "network_error" | "timeout" | "aborted" | "unknown"`; `export type ApiErrorCode = ServerErrorCode | ClientErrorCode`; `export type InviteRejectReason = "unknown" | "revoked" | "expired" | "used" | "church_unavailable" | "email_mismatch"`; `export function isNoChurchAccess(e: unknown): boolean` (`e instanceof ApiError && e.code === "forbidden" && e.details?.reason === "no_church_access"`); `export function describeError(e: unknown): string` (`network_error` → "Can't reach the server."; status ≥ 500 → "Something went wrong. (Ref: <first 8 chars of requestId>)", or "Something went wrong." without a `requestId`; any other `ApiError` → its `message`, so `timeout` → "This is taking too long. Try again."; not an `ApiError` → "Something went wrong."); re-exports `ApiError`. Later users: Task 18 (`handleAuthErrors`), Task 20 (`ErrorState`), Task 23, 1b (`InviteRejectReason`).
  - `frontend/src/lib/api/timeouts.ts`: `export const DEFAULT_TIMEOUT_MS = 20_000`; `export function timeoutFor(method: string, path: string): number` (`"POST /churches"` → `30_000`, keyed on the upper-cased method and the path without its query string; else `DEFAULT_TIMEOUT_MS`).
  - `frontend/src/lib/api/types.ts`: `export type Church = components["schemas"]["ChurchOut"]`, `export type Me = components["schemas"]["MeOut"]`, `export type ErrorBody = components["schemas"]["ErrorBody"]`. Later users: Task 17 (`lib/church.ts` re-exports `Church`, `Me`).
  - `backend/tests/test_error_registry.py`: `test_frontend_union_lists_every_error_code`, `test_frontend_union_has_no_unregistered_server_codes`.

- [ ] **Step 1: Move the client and its test**

```bash
git mv frontend/src/lib/api.ts frontend/src/lib/api/client.ts
git mv frontend/src/lib/api.test.ts frontend/src/lib/api/client.test.ts
```

`frontend/src/lib/api/` already exists (Task 13's `openapi.json`, Task 15's `schema.d.ts`). In `frontend/src/lib/api/client.test.ts`, replace line 3:

```ts
import { apiFetch } from "./api";
```

with:

```ts
import { apiFetch } from "./client";
```

In `frontend/src/app/page.tsx`, replace line 10:

```ts
import { ApiError, apiFetch } from "@/lib/api";
```

with:

```ts
import { ApiError, apiFetch } from "@/lib/api/client";
```

Run:
```bash
(cd frontend && npx vitest run src/lib/api/client.test.ts 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck)
grep -rn 'from "@/lib/api"\|from "./api"' frontend/src
```
Expected: `Test Files  1 passed (1)` and `Tests  8 passed (8)` (the move changes no behavior); `tsc --noEmit` reports no errors; the `grep` prints nothing (exit 1): `page.tsx` was the only importer of `@/lib/api`.

- [ ] **Step 2: Write the failing tests**

Replace the whole of `frontend/src/lib/api/client.test.ts` with the version below. The first eight tests are the slice-0 ones, unchanged except one expectation: a non-JSON 502 is now `internal_error`, not `"error"` (clarification 9). Ten tests are new; `hangingFetch` never answers and rejects like the real `fetch` when its signal aborts, so the timeout and abort tests need no network.

```ts
import { afterEach, describe, expect, it, vi } from "vitest";

import { apiFetch } from "./client";

function jsonFetch(status: number, body: unknown, headers: Record<string, string> = {}) {
  return vi.fn<typeof fetch>(
    async () =>
      new Response(JSON.stringify(body), {
        status,
        headers: { "Content-Type": "application/json", ...headers },
      }),
  );
}

/** A fetch that never answers; it rejects like the real one when its signal aborts. */
function hangingFetch() {
  return vi.fn<typeof fetch>(
    (_url, init) =>
      new Promise<Response>((_resolve, reject) => {
        init?.signal?.addEventListener("abort", () =>
          reject(new DOMException("The operation was aborted.", "AbortError")),
        );
      }),
  );
}

afterEach(() => {
  vi.useRealTimers();
});

describe("apiFetch", () => {
  it("strips a trailing slash from baseUrl before joining the path", async () => {
    const f = jsonFetch(200, { ok: true });
    await apiFetch("/church", { token: "t", baseUrl: "https://api.test/", fetchImpl: f });
    const [url] = f.mock.calls[0];
    expect(url).toBe("https://api.test/church");
  });

  it("strips multiple trailing slashes from baseUrl", async () => {
    const f = jsonFetch(200, { ok: true });
    await apiFetch("/church", { token: "t", baseUrl: "https://api.test///", fetchImpl: f });
    const [url] = f.mock.calls[0];
    expect(url).toBe("https://api.test/church");
  });

  it("sends the bearer token and church id", async () => {
    const f = jsonFetch(200, { ok: true });
    await apiFetch("/church", { token: "t0k", churchId: "c-1", baseUrl: "https://api.test", fetchImpl: f });
    const [url, init] = f.mock.calls[0];
    expect(url).toBe("https://api.test/church");
    const headers = new Headers(init?.headers);
    expect(headers.get("Authorization")).toBe("Bearer t0k");
    expect(headers.get("X-Church-Id")).toBe("c-1");
  });

  it("omits X-Church-Id when no church is selected", async () => {
    const f = jsonFetch(200, {});
    await apiFetch("/me", { token: "t", baseUrl: "", fetchImpl: f });
    const headers = new Headers(f.mock.calls[0][1]?.headers);
    expect(headers.has("X-Church-Id")).toBe(false);
  });

  it("returns the parsed JSON body on success", async () => {
    const f = jsonFetch(200, { ok: true });
    await expect(apiFetch("/health", { token: "t", baseUrl: "", fetchImpl: f })).resolves.toEqual({ ok: true });
  });

  it("throws ApiError with the server's code and message", async () => {
    const f = jsonFetch(403, { error: { code: "forbidden", message: "No access" } });
    await expect(apiFetch("/church", { token: "t", baseUrl: "", fetchImpl: f })).rejects.toMatchObject({
      name: "ApiError",
      status: 403,
      code: "forbidden",
      message: "No access",
    });
  });

  it("uses a generic error when the body isn't JSON", async () => {
    const f = vi.fn<typeof fetch>(async () => new Response("Bad gateway", { status: 502 }));
    await expect(apiFetch("/me", { token: "t", baseUrl: "", fetchImpl: f })).rejects.toMatchObject({
      status: 502,
      code: "internal_error",
      message: "Something went wrong.",
    });
  });

  it("maps network failures to status 0", async () => {
    const f = vi.fn<typeof fetch>(async () => {
      throw new TypeError("fetch failed");
    });
    await expect(apiFetch("/me", { token: "t", baseUrl: "", fetchImpl: f })).rejects.toMatchObject({
      status: 0,
      code: "network_error",
    });
  });

  it("sends a JSON body with the method and Content-Type", async () => {
    const f = jsonFetch(201, { id: "c-1", name: "Grace", role: "owner" });
    await apiFetch("/churches", {
      token: "t",
      baseUrl: "",
      method: "POST",
      json: { name: "Grace", timezone: "America/Chicago" },
      fetchImpl: f,
    });
    const [, init] = f.mock.calls[0];
    expect(init?.method).toBe("POST");
    expect(new Headers(init?.headers).get("Content-Type")).toBe("application/json");
    expect(JSON.parse(String(init?.body))).toEqual({ name: "Grace", timezone: "America/Chicago" });
  });

  it("sends the Idempotency-Key header when given", async () => {
    const f = jsonFetch(201, {});
    const key = "0b0e7a4e-3f7c-4f55-9a55-8d7f0f6b2c11";
    await apiFetch("/churches", { token: "t", baseUrl: "", method: "POST", json: {}, idempotencyKey: key, fetchImpl: f });
    const headers = new Headers(f.mock.calls[0][1]?.headers);
    expect(headers.get("Idempotency-Key")).toBe(key);
    expect(headers.has("If-Match")).toBe(false);
  });

  it("sends the If-Match header when given", async () => {
    const f = jsonFetch(200, {});
    await apiFetch("/rubric", { token: "t", churchId: "c-1", baseUrl: "", method: "PATCH", json: {}, ifMatch: '"v3"', fetchImpl: f });
    const headers = new Headers(f.mock.calls[0][1]?.headers);
    expect(headers.get("If-Match")).toBe('"v3"');
    expect(headers.has("Idempotency-Key")).toBe(false);
  });

  it("times out after 20 s by default and 30 s for POST /churches", async () => {
    vi.useFakeTimers();
    const timeout = { status: 0, code: "timeout", message: "This is taking too long. Try again." };

    const get = hangingFetch();
    const me = apiFetch("/me", { token: "t", baseUrl: "", fetchImpl: get });
    const meFailed = expect(me).rejects.toMatchObject(timeout);
    await vi.advanceTimersByTimeAsync(19_999);
    expect(get.mock.calls[0][1]?.signal?.aborted).toBe(false);
    await vi.advanceTimersByTimeAsync(1);
    await meFailed;

    const post = hangingFetch();
    const create = apiFetch("/churches", { token: "t", baseUrl: "", method: "POST", json: {}, fetchImpl: post });
    const createFailed = expect(create).rejects.toMatchObject(timeout);
    await vi.advanceTimersByTimeAsync(29_999);
    expect(post.mock.calls[0][1]?.signal?.aborted).toBe(false);
    await vi.advanceTimersByTimeAsync(1);
    await createFailed;
  });

  it("maps the caller's abort to aborted", async () => {
    const f = hangingFetch();
    const controller = new AbortController();
    const pending = apiFetch("/me", { token: "t", baseUrl: "", fetchImpl: f, signal: controller.signal });
    controller.abort();
    await expect(pending).rejects.toMatchObject({ status: 0, code: "aborted", message: "The request was cancelled." });
  });

  it("parses fields, details and request_id from the error body", async () => {
    const invalid = jsonFetch(
      422,
      {
        error: {
          code: "invalid_request",
          message: "The request was not valid.",
          request_id: "req-body-1",
          fields: { name: "Required." },
        },
      },
      { "X-Request-Id": "req-header-1" },
    );
    await expect(apiFetch("/churches", { token: "t", baseUrl: "", fetchImpl: invalid })).rejects.toMatchObject({
      status: 422,
      code: "invalid_request",
      requestId: "req-body-1",
      fields: { name: "Required." },
    });

    const lost = jsonFetch(403, {
      error: {
        code: "forbidden",
        message: "You don't have access to this church.",
        request_id: "req-body-2",
        details: { reason: "no_church_access" },
      },
    });
    await expect(apiFetch("/church", { token: "t", baseUrl: "", fetchImpl: lost })).rejects.toMatchObject({
      status: 403,
      code: "forbidden",
      details: { reason: "no_church_access" },
      requestId: "req-body-2",
    });
  });

  it("takes requestId from X-Request-Id when the body has none", async () => {
    const f = jsonFetch(404, { error: { code: "not_found", message: "Not found." } }, { "X-Request-Id": "abcdef0123456789" });
    await expect(apiFetch("/church", { token: "t", baseUrl: "", fetchImpl: f })).rejects.toMatchObject({
      status: 404,
      code: "not_found",
      requestId: "abcdef0123456789",
    });
  });

  it("gives a code-less body internal_error at 5xx and unknown below, with the header's requestId", async () => {
    const proxy = vi.fn<typeof fetch>(
      async () => new Response("<html>Bad gateway</html>", { status: 502, headers: { "X-Request-Id": "req-proxy-1" } }),
    );
    await expect(apiFetch("/me", { token: "t", baseUrl: "", fetchImpl: proxy })).rejects.toMatchObject({
      status: 502,
      code: "internal_error",
      message: "Something went wrong.",
      requestId: "req-proxy-1",
    });

    const codeless = jsonFetch(400, { detail: "Bad request" });
    await expect(apiFetch("/me", { token: "t", baseUrl: "", fetchImpl: codeless })).rejects.toMatchObject({
      status: 400,
      code: "unknown",
      message: "Something went wrong.",
    });
  });

  it("parses Retry-After into retryAfterSeconds, falling back to details", async () => {
    const body = {
      error: {
        code: "rate_limited",
        message: "Slow down.",
        request_id: "req-429",
        details: { retry_after_seconds: 42 },
      },
    };
    const withHeader = jsonFetch(429, body, { "Retry-After": "42" });
    await expect(apiFetch("/churches", { token: "t", baseUrl: "", fetchImpl: withHeader })).rejects.toMatchObject({
      status: 429,
      code: "rate_limited",
      retryAfterSeconds: 42,
      details: { retry_after_seconds: 42 },
    });

    const withoutHeader = jsonFetch(429, { error: { ...body.error, details: { retry_after_seconds: 7 } } });
    await expect(apiFetch("/churches", { token: "t", baseUrl: "", fetchImpl: withoutHeader })).rejects.toMatchObject({
      retryAfterSeconds: 7,
    });
  });

  it("returns undefined for 204 and for an empty 2xx body", async () => {
    const noContent = vi.fn<typeof fetch>(async () => new Response(null, { status: 204 }));
    await expect(apiFetch("/invites/x", { token: "t", baseUrl: "", method: "DELETE", fetchImpl: noContent })).resolves.toBeUndefined();

    const empty = vi.fn<typeof fetch>(async () => new Response("", { status: 200 }));
    await expect(apiFetch("/me", { token: "t", baseUrl: "", fetchImpl: empty })).resolves.toBeUndefined();
  });
});
```

Create `frontend/src/lib/api/errors.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import { ApiError } from "./client";
import { describeError, isNoChurchAccess } from "./errors";

describe("isNoChurchAccess", () => {
  it("is true for a require_church 403", () => {
    const lost = new ApiError(403, "forbidden", "You don't have access to this church.", {
      details: { reason: "no_church_access" },
    });
    expect(isNoChurchAccess(lost)).toBe(true);
  });

  it("is false for a role 403, another code or a non-ApiError", () => {
    expect(isNoChurchAccess(new ApiError(403, "forbidden", "Only church admins can do this."))).toBe(false);
    expect(
      isNoChurchAccess(new ApiError(404, "not_found", "Not found.", { details: { reason: "no_church_access" } })),
    ).toBe(false);
    expect(isNoChurchAccess(new Error("forbidden"))).toBe(false);
    expect(isNoChurchAccess({ code: "forbidden", details: { reason: "no_church_access" } })).toBe(false);
  });
});

describe("describeError", () => {
  it("says the server can't be reached for a network error", () => {
    const e = new ApiError(0, "network_error", "Can't reach the server. Check your connection and try again.");
    expect(describeError(e)).toBe("Can't reach the server.");
  });

  it("uses the timeout's own message", () => {
    expect(describeError(new ApiError(0, "timeout", "This is taking too long. Try again."))).toBe(
      "This is taking too long. Try again.",
    );
  });

  it("hides a 5xx message behind a reference from the request id", () => {
    const withRef = new ApiError(500, "internal_error", "Something went wrong.", { requestId: "0123456789abcdef" });
    expect(describeError(withRef)).toBe("Something went wrong. (Ref: 01234567)");
    const noRef = new ApiError(503, "db_unavailable", "The database is not reachable.");
    expect(describeError(noRef)).toBe("Something went wrong.");
  });

  it("shows a 4xx server message, and a generic one for anything else", () => {
    expect(describeError(new ApiError(409, "conflict", "Someone else changed this."))).toBe("Someone else changed this.");
    expect(describeError(new TypeError("x is undefined"))).toBe("Something went wrong.");
    expect(describeError("boom")).toBe("Something went wrong.");
  });
});
```

Create `backend/tests/test_error_registry.py`:

```python
"""The frontend error-code union mirrors domain_errors.ERROR_CODES (S Testing; ops handoff).

frontend/src/lib/api/errors.ts is read as text. Its ServerErrorCode union must
list exactly the registry's codes, and the client-only codes must never shadow
a server code, so a code added on one side fails CI until the other side has it.
"""
import re
from pathlib import Path

from domain_errors import ERROR_CODES

ERRORS_TS = Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "api" / "errors.ts"


def _union(name: str) -> list[str]:
    """The string literals of `export type <name> = ...;` in errors.ts, in order."""
    text = ERRORS_TS.read_text(encoding="utf-8")
    match = re.search(rf"export type {name} =(.*?);", text, re.DOTALL)
    assert match, f"errors.ts has no `export type {name} = ...;`"
    return re.findall(r'"([^"]*)"', match.group(1))


def test_frontend_union_lists_every_error_code():
    server = _union("ServerErrorCode")
    assert sorted(set(ERROR_CODES) - set(server)) == []
    assert "db_unavailable" in server   # the ops handoff code


def test_frontend_union_has_no_unregistered_server_codes():
    server = _union("ServerErrorCode")
    client = _union("ClientErrorCode")
    assert sorted(set(server) - set(ERROR_CODES)) == []
    assert len(server) == len(set(server)), "a code is listed twice"
    assert client == ["network_error", "timeout", "aborted", "unknown"]
    assert set(client).isdisjoint(ERROR_CODES)
    # ApiErrorCode is exactly ServerErrorCode | ClientErrorCode: no stray literal.
    assert _union("ApiErrorCode") == []
```

The registry test reads `errors.ts` as text (S Testing: "every key of `domain_errors.ERROR_CODES` appears as a string literal in the `ApiErrorCode` union"). It checks both directions, so a code added only in `ERROR_CODES` or only in the union fails CI, and it pins the four client codes so they can never shadow a server code.

- [ ] **Step 3: Run the tests to verify they fail**

Run:
```bash
.venv/bin/python -m pytest -q backend/tests/test_error_registry.py 2>&1 | tail -3
(cd frontend && npx vitest run src/lib/api 2>&1 | grep -E "Test Files|Tests |Cannot find module")
```
Expected: `2 failed`, both with `FileNotFoundError: [Errno 2] No such file or directory: '…/frontend/src/lib/api/errors.ts'`. Then `Error: Cannot find module './errors' imported from '…/src/lib/api/errors.test.ts'`, `Test Files  2 failed (2)` and `Tests  11 failed | 7 passed (18)`: the kept non-JSON test fails on `code: "error"` vs `"internal_error"`; the JSON-body, `Idempotency-Key` and `If-Match` tests see no method or header (`expected undefined to be 'POST'`, `expected null to be …`); the timeout test sees no signal (`expected undefined to be false`); the abort test fails with `Error: Test timed out in 5000ms` (the old client passes no signal, so the hanging fetch never settles); the error-body, `X-Request-Id`, code-less-body and `Retry-After` tests fail on `toMatchObject` (no `requestId`, `fields`, `details` or `retryAfterSeconds`; code `"error"`); the 204 test fails with `SyntaxError: Unexpected end of JSON input`.

- [ ] **Step 4: Create `frontend/src/lib/api/timeouts.ts`**

```ts
/** Request timeouts (F §1.8, §4.5). apiFetch uses timeoutFor unless the caller passes timeoutMs. */
export const DEFAULT_TIMEOUT_MS = 20_000;

/** Endpoints slower than the default, keyed "METHOD /path" (path without the query string). */
const ENDPOINT_TIMEOUTS: Record<string, number> = {
  // Creating a church copies the whole hymn catalog into it (slice 1b).
  "POST /churches": 30_000,
};

export function timeoutFor(method: string, path: string): number {
  const key = `${method.toUpperCase()} ${path.split("?")[0]}`;
  return ENDPOINT_TIMEOUTS[key] ?? DEFAULT_TIMEOUT_MS;
}
```

- [ ] **Step 5: Create `frontend/src/lib/api/errors.ts`**

The union keeps `ERROR_CODES`' order and grouping. The comments inside it carry no quotes and no semicolons, because `test_error_registry.py` reads the text from `export type ServerErrorCode =` to the first `;`.

```ts
import { ApiError } from "./client";

// Re-exported so a caller can import the class next to the helpers below.
export { ApiError };

/**
 * Server error codes: exactly the keys of backend `domain_errors.ERROR_CODES`
 * (F §1.5, 29 codes, grouped by status). backend/tests/test_error_registry.py
 * reads this union as text and fails when the two differ, so keep one quoted
 * code per line and no quotes or semicolons in the comments inside it.
 */
export type ServerErrorCode =
  // 400
  | "bad_request"
  | "invite_rejected"
  | "gmail_state_invalid"
  | "gmail_connect_failed"
  // 401
  | "unauthenticated"
  // 403
  | "forbidden"
  // 404
  | "not_found"
  // 405
  | "method_not_allowed"
  // 409
  | "conflict"
  | "last_admin"
  | "owner_must_transfer"
  | "invite_exists"
  | "gmail_not_connected"
  // 422
  | "invalid_request"
  | "prompt_invalid"
  | "idempotency_mismatch"
  | "invalid_rubric"
  // 429
  | "rate_limited"
  // 500
  | "internal_error"
  // 502
  | "upstream_error"
  | "ai_upstream_error"
  | "gmail_send_failed"
  // 503
  | "auth_unavailable"
  | "ai_not_configured"
  | "ai_busy"
  | "gmail_not_configured"
  | "db_unavailable"
  // 504
  | "upstream_timeout"
  | "ai_timeout";

/**
 * Codes only the client produces: network_error, timeout and aborted (status 0),
 * and unknown for an error body without a code below 500 (500 and up get
 * internal_error).
 */
export type ClientErrorCode = "network_error" | "timeout" | "aborted" | "unknown";

export type ApiErrorCode = ServerErrorCode | ClientErrorCode;

/** `details.reason` of a 400 `invite_rejected` (backend `InviteRejectReason`, slice 1b). */
export type InviteRejectReason =
  | "unknown"
  | "revoked"
  | "expired"
  | "used"
  | "church_unavailable"
  | "email_mismatch";

/** A `require_church` 403: the user is not (or no longer) a member of the church sent in X-Church-Id. */
export function isNoChurchAccess(e: unknown): boolean {
  return e instanceof ApiError && e.code === "forbidden" && e.details?.reason === "no_church_access";
}

/** The sentence an error state shows for any thrown value. */
export function describeError(e: unknown): string {
  if (!(e instanceof ApiError)) return "Something went wrong.";
  if (e.code === "network_error") return "Can't reach the server.";
  if (e.status >= 500) {
    return e.requestId ? `Something went wrong. (Ref: ${e.requestId.slice(0, 8)})` : "Something went wrong.";
  }
  return e.message;
}
```

`errors.ts` imports the `ApiError` class from `client.ts`, and `client.ts` imports only the `ApiErrorCode` type from `errors.ts` (`import type`, erased at build), so there is no runtime import cycle.

- [ ] **Step 6: Replace `frontend/src/lib/api/client.ts`**

Replace the whole file (the moved slice-0 client, 57 lines) with:

```ts
import type { ApiErrorCode } from "./errors";
import { timeoutFor } from "./timeouts";

export type ApiErrorExtra = {
  fields?: Record<string, string>;
  requestId?: string;
  retryAfterSeconds?: number;
  details?: Record<string, unknown>;
};

/** A failed API call: the server's error body (F §1.5), or a client code with status 0. */
export class ApiError extends Error {
  status: number;
  code: ApiErrorCode;
  fields?: Record<string, string>;
  requestId?: string;
  retryAfterSeconds?: number;
  details?: Record<string, unknown>;

  constructor(status: number, code: ApiErrorCode, message: string, extra: ApiErrorExtra = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.fields = extra.fields;
    this.requestId = extra.requestId;
    this.retryAfterSeconds = extra.retryAfterSeconds;
    this.details = extra.details;
  }
}

export type ApiOptions = {
  token: string;
  churchId?: string | null;
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  /** Sent as JSON.stringify(json) with Content-Type: application/json. */
  json?: unknown;
  idempotencyKey?: string;
  ifMatch?: string;
  /** Default: timeoutFor(method, path) from ./timeouts (20 s; POST /churches 30 s). */
  timeoutMs?: number;
  signal?: AbortSignal;
  init?: RequestInit;
  baseUrl?: string;
  fetchImpl?: typeof fetch;
};

const GENERIC_MESSAGE = "Something went wrong.";
const NETWORK_MESSAGE = "Can't reach the server. Check your connection and try again.";
const TIMEOUT_MESSAGE = "This is taking too long. Try again.";
const ABORTED_MESSAGE = "The request was cancelled.";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function retryAfterSeconds(res: Response, details: Record<string, unknown> | undefined): number | undefined {
  const header = res.headers.get("Retry-After");
  if (header !== null && /^\d+$/.test(header.trim())) return Number(header.trim());
  const fromBody = details?.retry_after_seconds;
  return typeof fromBody === "number" ? fromBody : undefined;
}

/** The ApiError for a non-2xx response whose body has been read as text. */
function errorFromResponse(res: Response, text: string): ApiError {
  let error: Record<string, unknown> = {};
  try {
    const parsed: unknown = JSON.parse(text);
    if (isRecord(parsed) && isRecord(parsed.error)) error = parsed.error;
  } catch {
    // Non-JSON error body (e.g. a proxy's HTML page); keep the generic message.
  }
  const code =
    typeof error.code === "string"
      ? (error.code as ApiErrorCode)
      : res.status >= 500
        ? "internal_error"
        : "unknown";
  const message = typeof error.message === "string" ? error.message : GENERIC_MESSAGE;
  const details = isRecord(error.details) ? error.details : undefined;
  return new ApiError(res.status, code, message, {
    fields: isRecord(error.fields) ? (error.fields as Record<string, string>) : undefined,
    requestId: typeof error.request_id === "string" ? error.request_id : (res.headers.get("X-Request-Id") ?? undefined),
    retryAfterSeconds: retryAfterSeconds(res, details),
    details,
  });
}

/** Call the FastAPI backend. The server re-checks the church on every request. */
export async function apiFetch<T>(path: string, opts: ApiOptions): Promise<T> {
  const {
    token,
    churchId,
    json,
    idempotencyKey,
    ifMatch,
    init,
    baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "",
    fetchImpl = fetch,
  } = opts;
  const method = opts.method ?? init?.method ?? "GET";
  const timeoutMs = opts.timeoutMs ?? timeoutFor(method, path);
  const callerSignal = opts.signal ?? init?.signal ?? undefined;

  const headers = new Headers(init?.headers);
  headers.set("Authorization", `Bearer ${token}`);
  if (churchId) headers.set("X-Church-Id", churchId);
  if (idempotencyKey) headers.set("Idempotency-Key", idempotencyKey);
  if (ifMatch) headers.set("If-Match", ifMatch);
  let body = init?.body;
  if (json !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(json);
  }

  // One controller serves the timeout and the caller's signal, combined by hand:
  // older iOS Safari has no AbortSignal.any (F §4.5).
  const controller = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);
  const onCallerAbort = () => controller.abort();
  if (callerSignal?.aborted) controller.abort();
  else callerSignal?.addEventListener("abort", onCallerAbort);

  const normalizedBaseUrl = baseUrl.replace(/\/+$/, "");

  let res: Response;
  let text: string;
  try {
    res = await fetchImpl(`${normalizedBaseUrl}${path}`, {
      ...init,
      method,
      headers,
      body,
      signal: controller.signal,
    });
    // Read the body before the timer stops: a stalled body also times out.
    text = res.status === 204 ? "" : await res.text();
  } catch {
    if (timedOut) throw new ApiError(0, "timeout", TIMEOUT_MESSAGE);
    if (controller.signal.aborted) throw new ApiError(0, "aborted", ABORTED_MESSAGE);
    throw new ApiError(0, "network_error", NETWORK_MESSAGE);
  } finally {
    clearTimeout(timer);
    callerSignal?.removeEventListener("abort", onCallerAbort);
  }

  if (res.ok) {
    if (!text) return undefined as T;
    try {
      return JSON.parse(text) as T;
    } catch {
      // A proxy or captive portal answering 200 with HTML: still an ApiError.
      throw new ApiError(res.status, "internal_error", GENERIC_MESSAGE, {
        requestId: res.headers.get("X-Request-Id") ?? undefined,
      });
    }
  }
  throw errorFromResponse(res, text);
}
```

- [ ] **Step 7: Create `frontend/src/lib/api/types.ts`**

```ts
/**
 * App-facing names for the generated API types (F §1.11). schema.d.ts is
 * generated from openapi.json by `npm run gen:api`; never edit it by hand.
 */
import type { components } from "./schema";

export type Church = components["schemas"]["ChurchOut"];
export type Me = components["schemas"]["MeOut"];
export type ErrorBody = components["schemas"]["ErrorBody"];
```

`./schema` resolves to Task 15's generated `schema.d.ts` (`moduleResolution: "bundler"`); `import type` keeps it out of the bundle.

- [ ] **Step 8: Run the tests, the frontend check and the backend suite**

Run:
```bash
(cd frontend && npx vitest run src/lib/api 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests " && npm run typecheck && npm run lint)
.venv/bin/python -m pytest -q backend/tests/test_error_registry.py backend/tests/test_foundation_setup.py 2>&1 | tail -3
.venv/bin/python -m pytest -q | tail -1
git status --short
```
Expected: `Test Files  2 passed (2)` and `Tests  24 passed (24)` (18 + 6); then `Test Files  6 passed (6)` and `Tests  34 passed (34)` (18 after Task 15 + 16), `tsc --noEmit` and `eslint` report no errors; then `19 passed` (2 + `test_foundation_setup.py`'s 17 after Task 12, including `test_frontend_error_union_lists_db_unavailable_once_it_exists`, now reading the real `errors.ts`); then `692 passed, 5 skipped`. `git status --short` lists exactly (plus `?? .claude/`):

```
 M frontend/src/app/page.tsx
RM frontend/src/lib/api.test.ts -> frontend/src/lib/api/client.test.ts
RM frontend/src/lib/api.ts -> frontend/src/lib/api/client.ts
?? backend/tests/test_error_registry.py
?? frontend/src/lib/api/errors.test.ts
?? frontend/src/lib/api/errors.ts
?? frontend/src/lib/api/timeouts.ts
?? frontend/src/lib/api/types.ts
```

If `typecheck` reports `Property 'ErrorBody' does not exist` (or `ChurchOut`/`MeOut`), the generated schema is stale: rerun `.venv/bin/python backend/scripts/export_openapi.py && (cd frontend && npm run gen:api)`, and check that Task 3's `error_responses` decorators are on the routes; never hand-edit `schema.d.ts`.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/lib/api/client.ts frontend/src/lib/api/client.test.ts \
        frontend/src/lib/api/errors.ts frontend/src/lib/api/errors.test.ts \
        frontend/src/lib/api/timeouts.ts frontend/src/lib/api/types.ts \
        frontend/src/app/page.tsx backend/tests/test_error_registry.py
git status --short
git commit -m "Frontend: API client in lib/api with the error union, timeouts and generated types (F §4.5, §1.5, §1.8)

apiFetch moves to src/lib/api/client.ts and gains method, json,
idempotencyKey, ifMatch, timeoutMs (20 s by default, 30 s for POST
/churches) and signal, combined by hand with the timeout. ApiError carries
fields, requestId (the body's request_id, else the X-Request-Id header),
retryAfterSeconds and details. Client codes are network_error, timeout,
aborted and unknown; a code-less 5xx body is internal_error, and a 204 or
empty body returns undefined. errors.ts mirrors the 29 codes of
domain_errors.ERROR_CODES, and test_error_registry.py checks both directions.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

The `git status --short` before the commit prints exactly (plus `?? .claude/`); once the contents differ, the index shows each move as a delete and an add:

```
A  backend/tests/test_error_registry.py
M  frontend/src/app/page.tsx
D  frontend/src/lib/api.test.ts
D  frontend/src/lib/api.ts
A  frontend/src/lib/api/client.test.ts
A  frontend/src/lib/api/client.ts
A  frontend/src/lib/api/errors.test.ts
A  frontend/src/lib/api/errors.ts
A  frontend/src/lib/api/timeouts.ts
A  frontend/src/lib/api/types.ts
```

Tests after this task: backend `692 passed, 5 skipped`; frontend `34 passed`.

---

### Task 17: `storage.ts`, `urls.ts`, `church.ts` store (F §4.3, §4.2; S Storage and URL helpers, Layouts step 1)

Three small `src/lib` modules that the layouts (Tasks 19, 21, 23) and 1b build on. `storage.ts` wraps both browser storages in try/catch and does nothing on the server (F §4.3), and owns the key names: `wsb:pendingInviteCode`, `wsb:postLoginPath` (session) and `activeChurchId` (local, the slice-0 name, so nobody loses their remembered church). `urls.ts` holds four pure helpers whose first callers come later (`safeInternalPath` and `extractInviteCode` in 1b, `safeHttpsUrl` in slice 3, `buildInviteUrl` in 6b); they ship now because S lists them in 1a and they are only unit-tested code. `church.ts` stops declaring its own `Church`/`Me` and re-exports Task 16's generated types, reads and writes through `storage.ts`, gains `excluded` ids in `pickActiveChurch` and `roleLabel`, and gets S's hydration-safe `useStoredChurchId` (S Layouts step 1): a `useSyncExternalStore` over a module-level value that is read from `localStorage` on first client use, updated by `storeChurchId` (which notifies this tab only), and `undefined` in the server/hydration snapshot. That value changes only inside plain functions (`getSnapshot`, `storeChurchId`, the test reset), never in a component body, as react-hooks v7's `purity`/`refs` rules require.

Decisions the spec leaves open (recorded here, used by later tasks):
- `pickActiveChurch`'s fallback sorts the remaining churches by name (`localeCompare`) instead of trusting `/me`'s order (`repos/churches.py:51` already orders by name), so any fixture order gives "first by name".
- `extractInviteCode` of a link that carries no `code` returns `""` (1b's blank-code check then applies), not the whole link.
- `safeInternalPath` also rejects percent-encoded `..` segments (`%2e%2e`, which browsers resolve like `..`) and C1 control characters (U+0080–U+009F) besides S's list; it returns the input unchanged when accepted.
- `safeHttpsUrl` returns the normalized `URL.href` (so `https://Example.com` comes back as `https://example.com/`).
- `storeChurchId("")` forgets the church, like `null`.

Test layout (clarification 13): `storage.test.ts`, `urls.test.ts` and `church.test.ts` run in the `unit` project (node, no `window`; the storage and `buildInviteUrl` tests stub `window` with `vi.stubGlobal`); the store tests live in `church-store.test.tsx` in the `dom` project with `renderHook`, and the server-snapshot case uses `renderToString` from `react-dom/server`, because `renderHook` never calls `getServerSnapshot`. `setup-dom.ts`'s `afterEach` block gains a `resetStoredChurchIdForTests()` call after `cleanup()` and the storage clears (Task 15's contract), since the module-level value otherwise leaks into the next test of the same file.

Verified on this machine before writing (throwaway worktree; Vitest 3.2.7, Node 26.4.0; jsdom 29.1.1 and `@testing-library/react` 16.3.2 extracted from the offline npm cache; a stand-in `types.ts` with the generated shape of `ChurchOut`/`MeOut`; a setup file with Task 15's `afterEach` plus this task's reset): every file below as written, `Tests  47 passed (47)` (15 slice-0 + the 32 here), `tsc --noEmit` and `eslint` clean, and the red-phase messages quoted in Step 3. **Found while verifying:** on Node ≥ 25 (this machine has 26.4.0; CI has 22) Node's own Web Storage global hides jsdom's, so in the `dom` project `window.localStorage` is `undefined` and every DOM test fails in Task 15's `afterEach` (`TypeError: Cannot read properties of undefined (reading 'clear')`). Running the test forks with `--no-experimental-webstorage` fixes it (verified); Task 15's `vitest.config.ts` now carries that flag, and Step 1 checks it.

**Files:**
- Create: `frontend/src/lib/storage.ts`, `frontend/src/lib/urls.ts`
- Modify: `frontend/src/lib/church.ts` (whole file, 30 lines, replaced in Step 6), `frontend/src/test/setup-dom.ts` (one import after Task 15's `vitest` import; one statement at the end of Task 15's `afterEach` block)
- Test: `frontend/src/lib/storage.test.ts` (4, new), `frontend/src/lib/urls.test.ts` (21, new), `frontend/src/lib/church.test.ts` (whole file: 4 kept + 2 new), `frontend/src/lib/church-store.test.tsx` (5, new, `dom` project)

**Interfaces:**
- Consumes: Task 16's `frontend/src/lib/api/types.ts` (`export type Church = components["schemas"]["ChurchOut"]` = `{ id: string; name: string; role: "owner" | "admin" | "member" }`, the role union coming from Task 3's `Literal`; `export type Me = components["schemas"]["MeOut"]`); Task 15's Vitest projects (`unit`: node, `src/**/*.test.ts`; `dom`: jsdom, `src/**/*.test.tsx`, `setupFiles: ["src/test/setup-dom.ts"]`) and its `setup-dom.ts` (imports `import { afterEach, beforeEach, vi } from "vitest";` then `import { resetTestMocks } from "./mocks";`; ends with `afterEach(() => { cleanup(); window.localStorage.clear(); window.sessionStorage.clear(); });`); `@testing-library/react` (`renderHook`, `act`) from Task 15; `react-dom/server` (`renderToString`, react-dom 19.2.8, already installed). Current importers of `@/lib/church`, which keep compiling unchanged: `src/app/page.tsx:11-17` (`type Church`, `type Me`, `pickActiveChurch`, `readStoredChurchId`, `storeChurchId`) and `src/components/app-header.tsx:20` (`type Church`, `type Me`); both are deleted in Task 23.
- Produces:
  - `frontend/src/lib/storage.ts`: `export const SESSION_KEYS = { pendingInviteCode: "wsb:pendingInviteCode", postLoginPath: "wsb:postLoginPath" } as const`; `export const ACTIVE_CHURCH_KEY = "activeChurchId"`; `export function readSession(key: string): string | null`; `export function writeSession(key: string, value: string): void`; `export function removeSession(key: string): void`; `export function readLocal(key: string): string | null`; `export function writeLocal(key: string, value: string): void`; `export function removeLocal(key: string): void` (every call try/catch; on the server a read returns `null` and a write or remove does nothing). Later users: Task 19 (`useSignOut` removes `SESSION_KEYS.pendingInviteCode` unless `keepPendingInvite`, and `SESSION_KEYS.postLoginPath`), 1b (`/join`, `post-login.ts`, `/welcome`), 5b.
  - `frontend/src/lib/urls.ts`: `export function safeInternalPath(raw: unknown): string | null`; `export function extractInviteCode(input: string): string`; `export function buildInviteUrl(code: string, origin: string = window.location.origin): string` (`${origin}/join?code=${encodeURIComponent(code)}`); `export function safeHttpsUrl(raw: unknown): string | null`. Later users: Task 19 (`useSignOut`'s `next` goes through `safeInternalPath`), 1b, 3, 5b, 6b.
  - `frontend/src/lib/church.ts`: `export type { Church, Me } from "@/lib/api/types"`; `export function pickActiveChurch(churches: Church[], storedId: string | null | undefined, excluded: ReadonlySet<string> = new Set()): Church | null`; `export function roleLabel(role: Church["role"]): "Owner" | "Admin" | "Member"`; `export function readStoredChurchId(): string | null`; `export function storeChurchId(id: string | null): void` (writes `activeChurchId`, updates the module value, notifies this tab's subscribers); `export function useStoredChurchId(): string | null | undefined` (`useSyncExternalStore(subscribe, getSnapshot, () => undefined)`); `export function resetStoredChurchIdForTests(): void`. Later users: Task 19 (`storeChurchId(null)`), Task 21 (`roleLabel`, `Church`, `Me`), Task 22 (`Me`), Task 23 (`useStoredChurchId`, `pickActiveChurch` with `excluded`, `storeChurchId`), 1b (`useMembershipChanged` → `storeChurchId`).
  - `frontend/src/test/setup-dom.ts`: its `afterEach` block calls `resetStoredChurchIdForTests()` after `cleanup()` and the storage clears (Task 18 appends `resetSigningOutForTests();` to the same block).

- [ ] **Step 1: Check the `dom` project runs on this machine's Node**

```bash
node --version
(cd frontend && npx vitest run --project dom 2>&1 | grep -E "Test Files|Tests |reading 'clear'")
```

Expected: `Test Files  1 passed (1)` and `Tests  2 passed (2)` (Task 15's `setup-dom.test.tsx`). If instead every test fails with `TypeError: Cannot read properties of undefined (reading 'clear')` at `src/test/setup-dom.ts` (Node ≥ 25: Node's own `localStorage` global hides jsdom's), Task 15's `vitest.config.ts` has lost its `poolOptions: { forks: { execArgv: ["--no-experimental-webstorage"] } },` line under `test:`: stop, restore it in Task 15's file (re-review Task 15) and rerun this step. This task never edits `vitest.config.ts`.

- [ ] **Step 2: Write the failing tests**

Create `frontend/src/lib/storage.test.ts`:

```ts
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ACTIVE_CHURCH_KEY,
  SESSION_KEYS,
  readLocal,
  readSession,
  removeLocal,
  removeSession,
  writeLocal,
  writeSession,
} from "./storage";

function memoryStorage(): Storage {
  const data = new Map<string, string>();
  return {
    get length() {
      return data.size;
    },
    clear: () => data.clear(),
    getItem: (key) => data.get(key) ?? null,
    key: (index) => [...data.keys()][index] ?? null,
    removeItem: (key) => {
      data.delete(key);
    },
    setItem: (key, value) => {
      data.set(key, String(value));
    },
  };
}

function throwingStorage(): Storage {
  const fail = () => {
    throw new Error("QuotaExceededError");
  };
  return { length: 0, clear: fail, getItem: fail, key: fail, removeItem: fail, setItem: fail };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("storage", () => {
  it("round-trips session and local values in their own areas", () => {
    vi.stubGlobal("window", { sessionStorage: memoryStorage(), localStorage: memoryStorage() });
    expect(SESSION_KEYS).toEqual({
      pendingInviteCode: "wsb:pendingInviteCode",
      postLoginPath: "wsb:postLoginPath",
    });
    expect(ACTIVE_CHURCH_KEY).toBe("activeChurchId");

    writeSession(SESSION_KEYS.pendingInviteCode, "XYZ");
    writeLocal(ACTIVE_CHURCH_KEY, "church-1");

    expect(readSession(SESSION_KEYS.pendingInviteCode)).toBe("XYZ");
    expect(readLocal(ACTIVE_CHURCH_KEY)).toBe("church-1");
    expect(readLocal(SESSION_KEYS.pendingInviteCode)).toBeNull();
    expect(readSession(ACTIVE_CHURCH_KEY)).toBeNull();
  });

  it("removes a value from one area only", () => {
    vi.stubGlobal("window", { sessionStorage: memoryStorage(), localStorage: memoryStorage() });
    writeSession("k", "session");
    writeLocal("k", "local");

    removeSession("k");
    expect(readSession("k")).toBeNull();
    expect(readLocal("k")).toBe("local");

    removeLocal("k");
    expect(readLocal("k")).toBeNull();
  });

  it("returns null and never throws when storage is blocked or full", () => {
    vi.stubGlobal("window", {
      get sessionStorage(): Storage {
        throw new Error("SecurityError");
      },
      localStorage: throwingStorage(),
    });

    expect(readSession("k")).toBeNull();
    expect(() => writeSession("k", "v")).not.toThrow();
    expect(() => removeSession("k")).not.toThrow();
    expect(readLocal("k")).toBeNull();
    expect(() => writeLocal("k", "v")).not.toThrow();
    expect(() => removeLocal("k")).not.toThrow();
  });

  it("does nothing on the server, where there is no window", () => {
    expect(typeof window).toBe("undefined");

    expect(readSession("k")).toBeNull();
    expect(readLocal("k")).toBeNull();
    expect(() => writeSession("k", "v")).not.toThrow();
    expect(() => writeLocal("k", "v")).not.toThrow();
    expect(() => removeSession("k")).not.toThrow();
    expect(() => removeLocal("k")).not.toThrow();
  });
});
```

Create `frontend/src/lib/urls.test.ts` (S's cases: 3 accepted paths; 9 rejection rows, one per rule, each row holding S's example plus the variants the rule also covers; 5 `extractInviteCode` cases; the `buildInviteUrl` round trip; 3 `safeHttpsUrl` cases = 21):

```ts
import { afterEach, describe, expect, it, vi } from "vitest";

import { buildInviteUrl, extractInviteCode, safeHttpsUrl, safeInternalPath } from "./urls";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("safeInternalPath", () => {
  it.each(["/join", "/builder/hymns", "/settings/people"])("accepts %s", (path) => {
    expect(safeInternalPath(path)).toBe(path);
  });

  it.each<[string, unknown[]]>([
    ["a protocol-relative URL", ["//evil.com", "/join//evil.com"]],
    ["a backslash, whitespace or control character", ["/\\evil.com", "/join x", "/join\t", "/join\u0000"]],
    ["an absolute URL", ["https://evil.com", "http://localhost/join"]],
    ["a scheme", ["javascript:alert(1)", "data:text/html,x"]],
    ["a first segment outside the allow-list", ["/joinx", "/", "/login", "/auth/callback"]],
    ["a query or fragment", ["/join?code=x", "/welcome#create"]],
    ["a `..` segment", ["/settings/../x", "/settings/%2e%2E/x"]],
    ["an empty or non-string value", ["", null, undefined, 42]],
    ["a path over 512 characters", ["/join/" + "a".repeat(594)]],
  ])("rejects %s", (_rule, inputs) => {
    for (const input of inputs) {
      expect(safeInternalPath(input), String(input)).toBeNull();
    }
  });
});

describe("extractInviteCode", () => {
  it("returns a raw code unchanged", () => {
    expect(extractInviteCode("Abc123_-xyz")).toBe("Abc123_-xyz");
  });

  it("reads the code from a full invite link", () => {
    expect(extractInviteCode("https://wsb.example/join?code=Abc123")).toBe("Abc123");
    expect(extractInviteCode("https://wsb.example/join?ref=mail&code=Abc123#top")).toBe("Abc123");
    expect(extractInviteCode("https://wsb.example/join")).toBe("");
  });

  it("reads the code from a link pasted without its scheme", () => {
    expect(extractInviteCode("wsb.example/join?code=Abc123")).toBe("Abc123");
  });

  it("decodes an encoded code", () => {
    expect(extractInviteCode("https://wsb.example/join?code=a%2Bb%2Fc")).toBe("a+b/c");
    expect(extractInviteCode("wsb.example/join?code=a%2Bb%2Fc")).toBe("a+b/c");
  });

  it("trims surrounding whitespace", () => {
    expect(extractInviteCode("  Abc123 \n")).toBe("Abc123");
    expect(extractInviteCode("\thttps://wsb.example/join?code=Abc123  ")).toBe("Abc123");
  });
});

describe("buildInviteUrl", () => {
  it("builds a link that extractInviteCode reads back", () => {
    const url = buildInviteUrl("a b/c+d?", "https://wsb.example");
    expect(url).toBe("https://wsb.example/join?code=a%20b%2Fc%2Bd%3F");
    expect(extractInviteCode(url)).toBe("a b/c+d?");

    vi.stubGlobal("window", { location: { origin: "https://app.example" } });
    expect(buildInviteUrl("Abc123")).toBe("https://app.example/join?code=Abc123");
  });
});

describe("safeHttpsUrl", () => {
  it("accepts an https URL", () => {
    expect(safeHttpsUrl("https://example.com/a?b=1")).toBe("https://example.com/a?b=1");
  });

  it("rejects other schemes", () => {
    for (const raw of ["http://example.com", "javascript:alert(1)", "data:text/html,x", "mailto:a@b.c"]) {
      expect(safeHttpsUrl(raw), raw).toBeNull();
    }
  });

  it("rejects values that are not absolute URLs", () => {
    for (const raw of ["", "example.com", "/join", null, 42]) {
      expect(safeHttpsUrl(raw), String(raw)).toBeNull();
    }
  });
});
```

Replace the whole of `frontend/src/lib/church.test.ts` (the four `pickActiveChurch` tests are kept word for word; two are added):

```ts
import { describe, expect, it } from "vitest";

import { type Church, pickActiveChurch, roleLabel } from "./church";

const churches: Church[] = [
  { id: "a", name: "Alpha", role: "owner" },
  { id: "b", name: "Beta", role: "member" },
];

describe("pickActiveChurch", () => {
  it("keeps the remembered church while the user still belongs to it", () => {
    expect(pickActiveChurch(churches, "b")?.id).toBe("b");
  });

  it("falls back to the first church when the remembered one is gone", () => {
    expect(pickActiveChurch(churches, "zzz")?.id).toBe("a");
  });

  it("falls back to the first church when nothing is remembered", () => {
    expect(pickActiveChurch(churches, null)?.id).toBe("a");
  });

  it("returns null when the user has no churches", () => {
    expect(pickActiveChurch([], "a")).toBeNull();
  });

  it("skips excluded churches and falls back to the first remaining one by name", () => {
    const three: Church[] = [
      { id: "g", name: "Grace", role: "admin" },
      { id: "b", name: "Beta", role: "member" },
      { id: "a", name: "Alpha", role: "owner" },
    ];
    expect(pickActiveChurch(three, "a", new Set(["a"]))?.id).toBe("b");
    expect(pickActiveChurch(three, "g", new Set(["a"]))?.id).toBe("g");
    expect(pickActiveChurch(three, undefined)?.id).toBe("a");
    expect(pickActiveChurch(three, "a", new Set(["a", "b", "g"]))).toBeNull();
  });
});

describe("roleLabel", () => {
  it("names each role for people", () => {
    expect((["owner", "admin", "member"] as const).map(roleLabel)).toEqual(["Owner", "Admin", "Member"]);
  });
});
```

Create `frontend/src/lib/church-store.test.tsx` (`dom` project):

```tsx
import { act, renderHook } from "@testing-library/react";
import { renderToString } from "react-dom/server";
import { beforeEach, describe, expect, it } from "vitest";

import { resetStoredChurchIdForTests, storeChurchId, useStoredChurchId } from "./church";

function Probe() {
  const id = useStoredChurchId();
  return <span>{id === undefined ? "not-read" : String(id)}</span>;
}

// setup-dom.ts already does both after each test; doing them first as well keeps this
// file independent of hook order.
beforeEach(() => {
  window.localStorage.clear();
  resetStoredChurchIdForTests();
});

describe("useStoredChurchId", () => {
  it("is undefined in the server snapshot even when an id is stored", () => {
    window.localStorage.setItem("activeChurchId", "a");
    renderHook(() => useStoredChurchId()); // the client cache now holds "a"

    expect(renderToString(<Probe />)).toBe("<span>not-read</span>");
  });

  it("returns the stored id on the client, or null when nothing is stored", () => {
    const empty = renderHook(() => useStoredChurchId());
    expect(empty.result.current).toBeNull();
    empty.unmount();

    window.localStorage.setItem("activeChurchId", "a");
    resetStoredChurchIdForTests();
    const stored = renderHook(() => useStoredChurchId());
    expect(stored.result.current).toBe("a");
  });

  it("follows storeChurchId in the same tab", () => {
    const { result } = renderHook(() => useStoredChurchId());
    expect(result.current).toBeNull();

    act(() => storeChurchId("b"));
    expect(result.current).toBe("b");
    expect(window.localStorage.getItem("activeChurchId")).toBe("b");

    act(() => storeChurchId(null));
    expect(result.current).toBeNull();
    expect(window.localStorage.getItem("activeChurchId")).toBeNull();
  });

  it("ignores a storage event from another tab", () => {
    window.localStorage.setItem("activeChurchId", "a");
    const { result, rerender } = renderHook(() => useStoredChurchId());
    expect(result.current).toBe("a");

    act(() => {
      window.localStorage.setItem("activeChurchId", "b");
      window.dispatchEvent(
        new StorageEvent("storage", { key: "activeChurchId", oldValue: "a", newValue: "b" }),
      );
    });
    rerender();
    expect(result.current).toBe("a");
  });

  it("re-reads localStorage after resetStoredChurchIdForTests", () => {
    act(() => storeChurchId("a"));
    window.localStorage.setItem("activeChurchId", "b"); // written behind the cache's back

    expect(renderHook(() => useStoredChurchId()).result.current).toBe("a");
    resetStoredChurchIdForTests();
    expect(renderHook(() => useStoredChurchId()).result.current).toBe("b");
  });
});
```

- [ ] **Step 3: Run the tests to verify they fail**

```bash
(cd frontend && npx vitest run src/lib/storage.test.ts src/lib/urls.test.ts src/lib/church.test.ts src/lib/church-store.test.tsx 2>&1 | grep -E "Test Files|Tests |Cannot find module|is not a function|expected 'a' to be 'b'" | sort | uniq -c)
```

Expected, among the counted lines:
- `Error: Cannot find module './storage' imported from '…/frontend/src/lib/storage.test.ts'` and `Error: Cannot find module './urls' imported from '…/frontend/src/lib/urls.test.ts'` (both files fail before collecting any test);
- `AssertionError: expected 'a' to be 'b' // Object.is equality` (the old `pickActiveChurch` ignores `excluded`);
- `TypeError: undefined is not a function` (`roleLabel` is not exported yet);
- `TypeError: (0 , __vi_import_…__.resetStoredChurchIdForTests) is not a function` (the import alias varies), and the same message 5 times on `→` lines (the `beforeEach` of each store test);
- `Test Files  4 failed (4)` and `Tests  7 failed | 4 passed (11)` (the four kept `pickActiveChurch` tests pass).

- [ ] **Step 4: Create `frontend/src/lib/storage.ts`**

```ts
/**
 * Browser storage behind try/catch (F §4.3). Storage can be missing (server render),
 * blocked (privacy settings throw on access) or full (quota errors on write); in every
 * case a read returns null and a write or remove does nothing, so callers never guard.
 */

/** Session keys use the `wsb:` prefix; sign-out removes them (S Flow D). */
export const SESSION_KEYS = {
  pendingInviteCode: "wsb:pendingInviteCode",
  postLoginPath: "wsb:postLoginPath",
} as const;

/** The remembered church (localStorage). Name kept from slice 0 so nobody loses their choice. */
export const ACTIVE_CHURCH_KEY = "activeChurchId";

type Area = "sessionStorage" | "localStorage";

function read(area: Area, key: string): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window[area].getItem(key);
  } catch {
    return null;
  }
}

function write(area: Area, key: string, value: string): void {
  if (typeof window === "undefined") return;
  try {
    window[area].setItem(key, value);
  } catch {
    // Blocked or full: the value just isn't remembered.
  }
}

function remove(area: Area, key: string): void {
  if (typeof window === "undefined") return;
  try {
    window[area].removeItem(key);
  } catch {
    // Blocked: there is nothing stored to remove.
  }
}

export function readSession(key: string): string | null {
  return read("sessionStorage", key);
}

export function writeSession(key: string, value: string): void {
  write("sessionStorage", key, value);
}

export function removeSession(key: string): void {
  remove("sessionStorage", key);
}

export function readLocal(key: string): string | null {
  return read("localStorage", key);
}

export function writeLocal(key: string, value: string): void {
  write("localStorage", key, value);
}

export function removeLocal(key: string): void {
  remove("localStorage", key);
}
```

- [ ] **Step 5: Create `frontend/src/lib/urls.ts`**

```ts
/**
 * URL helpers (S "Storage and URL helpers"; F §4.3). Pure functions: anything that came
 * from a query string, a paste or the server goes through one of these before the app
 * navigates to it or renders it as a link.
 */

const MAX_INTERNAL_PATH_LENGTH = 512;

/** First path segments a post-login `next` may return to (F §4.3). */
const INTERNAL_PATH_ROOTS = new Set(["join", "builder", "services", "settings", "welcome"]);

function hasUnsafeCharacter(path: string): boolean {
  for (const ch of path) {
    const code = ch.codePointAt(0) ?? 0;
    if (code <= 0x1f || (code >= 0x7f && code <= 0x9f)) return true;
  }
  return /[\s\\?#]/.test(path);
}

/** `..`, including percent-encoded dots, which browsers also resolve. */
function isParentSegment(segment: string): boolean {
  return segment.replace(/%2e/gi, ".") === "..";
}

/**
 * `raw` if it is a same-site path the app may navigate to after sign-in, else null.
 * At most 512 characters; exactly one leading `/`; no `//`, `\`, whitespace, control
 * characters, `?`, `#` or `..` segment; first segment one of join, builder, services,
 * settings, welcome, matched whole (so `/joinx` is rejected).
 */
export function safeInternalPath(raw: unknown): string | null {
  if (typeof raw !== "string") return null;
  if (raw.length === 0 || raw.length > MAX_INTERNAL_PATH_LENGTH) return null;
  if (!raw.startsWith("/") || raw.includes("//")) return null;
  if (hasUnsafeCharacter(raw)) return null;
  const segments = raw.slice(1).split("/");
  if (segments.some(isParentSegment)) return null;
  if (!INTERNAL_PATH_ROOTS.has(segments[0])) return null;
  return raw;
}

function decodeParam(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

/**
 * The invite code in whatever the user pasted: a raw code, a full invite link, or a link
 * without its scheme (`example.com/join?code=…`). A link that carries no `code` gives "".
 */
export function extractInviteCode(input: string): string {
  const trimmed = input.trim();
  try {
    return (new URL(trimmed).searchParams.get("code") ?? "").trim();
  } catch {
    // Not an absolute URL: a raw code, or a link pasted without its scheme.
  }
  const match = /[?&]code=([^&#\s]*)/.exec(trimmed);
  return match ? decodeParam(match[1]).trim() : trimmed;
}

/** The shareable invite link for `code` (6b's Copy link button). */
export function buildInviteUrl(code: string, origin: string = window.location.origin): string {
  return `${origin}/join?code=${encodeURIComponent(code)}`;
}

/** The normalized URL when `raw` is an absolute `https:` URL, else null (slice 3 links). */
export function safeHttpsUrl(raw: unknown): string | null {
  if (typeof raw !== "string") return null;
  try {
    const url = new URL(raw);
    return url.protocol === "https:" ? url.href : null;
  } catch {
    return null;
  }
}
```

- [ ] **Step 6: Replace `frontend/src/lib/church.ts`**

Replace the whole file (30 lines: its own `Church`/`Me` types, a private `ACTIVE_CHURCH_KEY`, `pickActiveChurch(churches, storedId)`, and `readStoredChurchId`/`storeChurchId` with inline try/catch) with:

```ts
import { useSyncExternalStore } from "react";

import type { Church } from "@/lib/api/types";
import { ACTIVE_CHURCH_KEY, readLocal, removeLocal, writeLocal } from "@/lib/storage";

export type { Church, Me } from "@/lib/api/types";

/**
 * The remembered church if the user still belongs to it and it is not excluded, else
 * their first church by name; null when none is left. `excluded` holds churches the
 * user has just lost access to (the `(church)` layout's 403 fallback, F §4.2 step 2).
 */
export function pickActiveChurch(
  churches: Church[],
  storedId: string | null | undefined,
  excluded: ReadonlySet<string> = new Set(),
): Church | null {
  const available = churches.filter((c) => !excluded.has(c.id));
  const stored = available.find((c) => c.id === storedId);
  if (stored) return stored;
  return [...available].sort((a, b) => a.name.localeCompare(b.name))[0] ?? null;
}

const ROLE_LABELS = {
  owner: "Owner",
  admin: "Admin",
  member: "Member",
} as const satisfies Record<Church["role"], string>;

/** How a membership role reads in the UI (account menu, switcher). */
export function roleLabel(role: Church["role"]): "Owner" | "Admin" | "Member" {
  return ROLE_LABELS[role];
}

export function readStoredChurchId(): string | null {
  return readLocal(ACTIVE_CHURCH_KEY);
}

// The stored church as this tab sees it. `undefined` = not read from localStorage yet.
// It changes only inside getSnapshot, storeChurchId and the test reset, never during a
// component render (react-hooks v7 rules).
let storedChurchId: string | null | undefined;
const listeners = new Set<() => void>();

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function getSnapshot(): string | null {
  if (storedChurchId === undefined) storedChurchId = readStoredChurchId();
  return storedChurchId;
}

function getServerSnapshot(): undefined {
  return undefined;
}

/**
 * Remembers the active church (null forgets it) and tells this tab's `useStoredChurchId`
 * readers. Other tabs are not told: they keep their church until they reload.
 */
export function storeChurchId(id: string | null): void {
  if (id) writeLocal(ACTIVE_CHURCH_KEY, id);
  else removeLocal(ACTIVE_CHURCH_KEY);
  storedChurchId = id || null;
  for (const listener of listeners) listener();
}

/**
 * The stored church id: `undefined` on the server and during hydration ("not read yet",
 * so the layout shows its skeleton), then the id or null. It follows `storeChurchId` in
 * this tab and ignores `storage` events from other tabs (S Layouts step 1).
 */
export function useStoredChurchId(): string | null | undefined {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}

/** Forget the cached id so the next read goes back to localStorage (test isolation). */
export function resetStoredChurchIdForTests(): void {
  storedChurchId = undefined;
}
```

`app/page.tsx` still calls `pickActiveChurch(result.churches, readStoredChurchId())` and `storeChurchId(…)`, and `components/app-header.tsx` imports `Church`/`Me`; the new signatures accept those calls unchanged (both files are deleted in Task 23). The generated `Me["user"]` has `name?: string | null` and `picture?: string | null` (FastAPI marks fields with defaults as optional); both files already handle a missing name and picture (`user.name ?? user.email`, `user.picture && …`), so `tsc` stays clean.

- [ ] **Step 7: Reset the store after each DOM test in `frontend/src/test/setup-dom.ts`**

In `frontend/src/test/setup-dom.ts` (Task 15), replace:

```ts
import { afterEach, beforeEach, vi } from "vitest";
import { resetTestMocks } from "./mocks";
```

with:

```ts
import { afterEach, beforeEach, vi } from "vitest";
import { resetStoredChurchIdForTests } from "@/lib/church";
import { resetTestMocks } from "./mocks";
```

and replace the file's last block:

```ts
afterEach(() => {
  cleanup();
  window.localStorage.clear();
  window.sessionStorage.clear();
});
```

with:

```ts
afterEach(() => {
  cleanup();
  window.localStorage.clear();
  window.sessionStorage.clear();
  resetStoredChurchIdForTests();
});
```

`lib/church.ts` caches the stored church id at module level; without this reset a value read in one test would leak into the next test in the same file. Vitest runs the setup file and the test file against one module instance (Task 15), so this reset clears the same cache the tests and layouts read. It goes inside the existing block, after `cleanup()`, not in a new `afterEach`: Vitest 3 runs `afterEach` hooks in reverse registration order, so a hook added below would run before `cleanup()`. Task 18 appends its reset to this exact block.

- [ ] **Step 8: Run the tests, the frontend check and the backend suite**

```bash
(cd frontend && npx vitest run src/lib/storage.test.ts src/lib/urls.test.ts src/lib/church.test.ts src/lib/church-store.test.tsx 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests " && npm run typecheck && npm run lint)
.venv/bin/python -m pytest -q | tail -1
git status --short
```

Expected: `Test Files  4 passed (4)` and `Tests  36 passed (36)` (4 + 21 + 6 + 5); then `Test Files  9 passed (9)` and `Tests  66 passed (66)` (34 after Task 16 + 32), `tsc --noEmit` and `eslint` report no errors; then `692 passed, 5 skipped` (no backend change); `git status --short` lists exactly (plus `?? .claude/`):

```
 M frontend/src/lib/church.test.ts
 M frontend/src/lib/church.ts
 M frontend/src/test/setup-dom.ts
?? frontend/src/lib/church-store.test.tsx
?? frontend/src/lib/storage.test.ts
?? frontend/src/lib/storage.ts
?? frontend/src/lib/urls.test.ts
?? frontend/src/lib/urls.ts
```

If `typecheck` reports `Property 'role' …` or `Type 'string' is not assignable to type '"owner" | "admin" | "member"'` in `church.ts`, the generated `ChurchOut.role` is still `string`: Task 3's `Literal` did not reach `openapi.json`; rerun `.venv/bin/python backend/scripts/export_openapi.py && (cd frontend && npm run gen:api)` and never hand-edit `schema.d.ts`. If the five store tests fail with `window.localStorage` undefined, Step 1's check was skipped.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/lib/storage.ts frontend/src/lib/storage.test.ts \
        frontend/src/lib/urls.ts frontend/src/lib/urls.test.ts \
        frontend/src/lib/church.ts frontend/src/lib/church.test.ts \
        frontend/src/lib/church-store.test.tsx frontend/src/test/setup-dom.ts
git status --short
git commit -m "Frontend: storage and URL helpers; hydration-safe stored church (F §4.3, §4.2; S Storage and URL helpers, Layouts step 1)

storage.ts wraps session and local storage in try/catch, does nothing on
the server and names the keys (wsb:pendingInviteCode, wsb:postLoginPath,
activeChurchId). urls.ts adds safeInternalPath, extractInviteCode,
buildInviteUrl and safeHttpsUrl. church.ts re-exports the generated Church
and Me types, skips excluded churches and falls back to the first by name,
labels roles, and adds useStoredChurchId: undefined on the server and during
hydration, then the stored id, following storeChurchId in this tab only.
setup-dom.ts resets the stored id after each DOM test.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

The `git status --short` before the commit prints exactly (plus `?? .claude/`):

```
A  frontend/src/lib/church-store.test.tsx
M  frontend/src/lib/church.test.ts
M  frontend/src/lib/church.ts
A  frontend/src/lib/storage.test.ts
A  frontend/src/lib/storage.ts
A  frontend/src/lib/urls.test.ts
A  frontend/src/lib/urls.ts
M  frontend/src/test/setup-dom.ts
```

Tests after this task: backend `692 passed, 5 skipped`; frontend `66 passed`.

---

### Task 18: Query layer, `useApi`, auth token + signing-out flag, `ChurchProvider` (F §4.4, §4.2, §4.5; S API client and query layer; AC14 1a part)

This task builds the client-side plumbing every later screen uses; nothing renders it yet (Task 19 adds `Providers`, Tasks 22–23 the layouts). `queries/client.ts` makes the `QueryClient` of F §4.4 (`staleTime: 30_000`, `gcTime: 5 * 60_000`, `refetchOnWindowFocus: true`, one retry for `network_error`/`timeout`/5xx only, mutations `retry: false`) whose query and mutation caches send every error through `handleAuthErrors`: a 401 emits `authEvents.signOutRequired()`, a 403 with `details.reason = "no_church_access"` emits `authEvents.churchAccessLost(churchId)` with the id from the query key (`["church", id, …]`) or the mutation's `meta.churchId`, and a role 403 emits nothing. `useApi()` returns the bound clients of F §4.5; each call fetches the token through `getAccessToken()`.

The signing-out flag (Global Constraints "Sign-out", clarification 27) lives in `lib/auth.ts` as module state with a `useSyncExternalStore` hook. While it is set, `getAccessToken()` rejects with `ApiError(0, "aborted", "Signing out.")` (it checks the flag before and again after `getSession()`, so a request whose token read straddles the Log out click never reaches `fetch`), and `handleAuthErrors` does nothing, so only one sign-out is ever in flight. Task 19's `useSignOut` sets it first; only a full page load clears it (every sign-in returns through the Google OAuth redirect).

Decisions the outline leaves open, recorded here:
- `useApi().church` is a function that **throws synchronously when called** outside `ChurchProvider` (`useApi()` itself never throws), because `useMe` runs `useApi().user` in the `(signed-in)` layout, above any `ChurchProvider`. The `(church)` layout confirms its candidate above the provider it renders, so `useChurchProfile` sends its id through `useApi().forChurch(id)`.
- Query functions pass TanStack's `signal` to `apiFetch`, so unmounting the last observer (a church switch remounts the `(church)` subtree, sign-out unmounts it) cancels the request. TanStack treats that as a cancel and does not call the caches' `onError` (query-core 5.101.1 `query.js`: `removeObserver` and `cancelQueries` cancel with `revert: true`, and a reverted `CancelledError` returns or rethrows before the `onError` call); `isRetryable` is `false` for `aborted` in any case.
- `useChurchProfile(undefined)` uses `skipToken` (no request; key `["church", "", "profile"]`).
- `keys.hymns`/`keys.services` take `params: object`, so later slices can pass an `interface`-typed params object (an interface is not assignable to `Record<string, unknown>`).
- All three test files are `.ts`, so they run in Task 15's node `unit` project without `setup-dom.ts`; each declares its own `vi.mock("@/lib/supabase/client")` (clarification 15). The `handleAuthErrors` tests go through a real `makeQueryClient()` (`fetchQuery`, `getMutationCache().build(…).execute()`), so they test the cache wiring and the retry default (a 401/403 is not retried, so no test waits) as well as the function.
- The flag's reset for DOM tests goes **inside** `setup-dom.ts`'s existing `afterEach` block, after `cleanup()`, not in a new `afterEach`: Vitest 3 runs `afterEach` hooks in reverse registration order (`sequence.hooks` defaults to `"stack"`, `vitest/dist/chunks/coverage.*.js`), so an `afterEach` appended to the file would run **before** `cleanup()` and re-render still-mounted `useSigningOut()` subscribers outside `act`. Checked in a scratch worktree: a setup file's `afterEach` that calls `resetSigningOutForTests` resets the same module instance the test file imported, and the setup file's `vi.mock("@/lib/supabase/client")` applies to `lib/auth.ts` imported by the test file.

`@tanstack/react-query` (`^5.101`, resolved 5.101.1) is installed by Task 15. Checked against 5.101.1 in a scratch worktree: `QueryCacheConfig.onError(error, query)`, `MutationCacheConfig.onError(error, variables, onMutateResult, mutation, context)`, `Mutation#meta`, and the `isServer`/`skipToken` exports; the three test files give `21 passed`, and `tsc --noEmit` and `eslint` are clean on these files.

**Files:**
- Create: `frontend/src/lib/auth.ts` (Task 19 adds `useSignOut` to it)
- Create: `frontend/src/lib/church-context.tsx`
- Create: `frontend/src/lib/queries/auth-events.ts`, `frontend/src/lib/queries/keys.ts`, `frontend/src/lib/queries/client.ts`, `frontend/src/lib/queries/me.ts`, `frontend/src/lib/queries/church.ts`
- Modify: `frontend/src/test/setup-dom.ts` (one import; one statement at the end of the `afterEach` block that calls `cleanup()`)
- Test: `frontend/src/lib/queries/client.test.ts` (16, new), `frontend/src/lib/queries/keys.test.ts` (2, new), `frontend/src/lib/auth.test.ts` (3, new)

**Interfaces:**
- Consumes:
  - Task 15: dependency `@tanstack/react-query` `^5.101`; Vitest project `unit` (node, `src/**/*.test.ts`); `frontend/src/test/setup-dom.ts` with `vi.mock("@/lib/supabase/client", …)` and an `afterEach(() => { cleanup(); window.localStorage.clear(); window.sessionStorage.clear(); … })` block (Task 17 adds `resetStoredChurchIdForTests();` to that block).
  - Task 16: `ApiError` (`status: number; code: ApiErrorCode; details?: Record<string, unknown>`; constructor `(status, code, message, extra?: ApiErrorExtra)`), `apiFetch<T>(path: string, opts: ApiOptions): Promise<T>`, `type ApiOptions` from `@/lib/api/client`; `type ApiErrorCode`, `isNoChurchAccess(e: unknown): boolean` from `@/lib/api/errors`; `type Church`, `type Me` from `@/lib/api/types`.
  - Existing: `createClient()` from `@/lib/supabase/client` (`frontend/src/lib/supabase/client.ts`, unchanged).
- Produces:
  - `frontend/src/lib/auth.ts`: `getAccessToken(): Promise<string>` (rejects `new ApiError(401, "unauthenticated", "Please sign in.")` with no session; rejects `new ApiError(0, "aborted", "Signing out.")` while signing out, checked before and after `getSession()`); `beginSignOut(): void` (idempotent; notifies subscribers); `isSigningOut(): boolean`; `useSigningOut(): boolean` (`useSyncExternalStore`, server snapshot `false`); `resetSigningOutForTests(): void`. Later users: Task 19 (`useSignOut` calls `beginSignOut()` first), Task 22 (`useSigningOut`, `isSigningOut`), Task 23 (`isSigningOut`), `setup-dom.ts`.
  - `frontend/src/lib/queries/auth-events.ts`: `export const authEvents: { signOutRequired(): void; churchAccessLost(churchId: string): void; onSignOutRequired(cb: () => void): () => void; onChurchAccessLost(cb: (churchId: string) => void): () => void }` (listeners run synchronously; each `on…` returns its unsubscribe). Later users: Task 22 (`onSignOutRequired`), Task 23 (`onChurchAccessLost`).
  - `frontend/src/lib/queries/keys.ts`: `export const keys` with `me() → ["me"]`, `translations() → ["ref", "translations"]`, `liturgyConfig() → ["ref", "liturgy-config"]`, `lectionary(dateIso: string) → ["lectionary", dateIso]`, `passage(translation: string, ref: string) → ["passage", translation, ref]`, `gmailConnection() → ["gmail-connection"]`, `church(id) → ["church", id]`, `churchProfile(id) → ["church", id, "profile"]`, `hymns(id, params: object) → ["church", id, "hymns", params]`, `hymnals(id) → [..., "hymnals"]`, `hymnalSources(id) → [..., "hymnal-sources"]`, `services(id, params: object) → [..., "services", params]`, `service(id, serviceId: string) → [..., "service", serviceId]`, `contacts(id)`, `members(id)`, `invites(id)`, `liturgyPrompts(id) → [..., "liturgy-prompts"]`, `rubric(id)`, `prayerLibrary(id) → [..., "prayer-library"]` (all `as const`; church keys start `["church", id]`). Later users: Tasks 19, 23, 1b, slices 2–6.
  - `frontend/src/lib/queries/client.ts`: `isRetryable(e: unknown): boolean`; `handleAuthErrors(error: unknown, source: Query<unknown, unknown, unknown> | Mutation<unknown, unknown, unknown>): void`; `makeQueryClient(overrides?: DefaultOptions): QueryClient`; `getQueryClient(): QueryClient` (new per server render, one per browser tab); `useChurchMutation<TData = unknown, TError = ApiError, TVariables = void, TOnMutateResult = unknown>(options: UseMutationOptions<TData, TError, TVariables, TOnMutateResult>): UseMutationResult<TData, TError, TVariables, TOnMutateResult>` (sets `meta.churchId` from `useChurch()`); `type ApiCall = <T>(path: string, opts?: Omit<ApiOptions, "token" | "churchId">) => Promise<T>`; `type Api = { user: ApiCall; church: ApiCall; forChurch(churchId: string): ApiCall }`; `useApi(): Api` (memoized per active church id; `church` throws `Error("useApi().church needs a ChurchProvider; use useApi().user or forChurch(id).")` when called outside `ChurchProvider`). Later users: Task 19 (`getQueryClient` in `Providers`, `makeQueryClient({ queries: { retry: false } })` in `renderWithProviders`), Task 23 (`useApi().church` test), 1b (`useApi().user` for `/churches` and `/invites/*`), slice 2+ (`useChurchMutation`, `useApi().church`).
  - `frontend/src/lib/queries/me.ts`: `useMe(opts?: { enabled?: boolean }): UseQueryResult<Me, ApiError>` (`GET /me` via `api.user`, key `keys.me()`). Later user: Task 22.
  - `frontend/src/lib/queries/church.ts`: `useChurchProfile(id: string | undefined, opts?: { enabled?: boolean }): UseQueryResult<Church, ApiError>` (`GET /church` via `api.forChurch(id)`, key `keys.churchProfile(id)`; `skipToken` while `id` is undefined). Later user: Task 23.
  - `frontend/src/lib/church-context.tsx`: `ChurchProvider({ value: Church; children: ReactNode })`, `useChurch(): Church` (throws `Error("useChurch() must be used inside ChurchProvider.")` outside), `useOptionalChurch(): Church | null`. Later users: Task 19 (`renderWithProviders({ church })`), Task 23, slice 2+.

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/lib/auth.test.ts`:

```ts
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/client";

import { beginSignOut, getAccessToken, resetSigningOutForTests } from "./auth";

// Node project: no setup-dom.ts here, so this file mocks the Supabase client itself.
const { getSession } = vi.hoisted(() => ({ getSession: vi.fn() }));
vi.mock("@/lib/supabase/client", () => ({ createClient: () => ({ auth: { getSession } }) }));

function session(accessToken: string | null) {
  return { data: { session: accessToken ? { access_token: accessToken } : null }, error: null };
}

afterEach(() => {
  resetSigningOutForTests();
  getSession.mockReset();
});

describe("getAccessToken", () => {
  it("returns the session's access token", async () => {
    getSession.mockResolvedValue(session("tok-1"));
    await expect(getAccessToken()).resolves.toBe("tok-1");
  });

  it("throws 401 unauthenticated when there is no session", async () => {
    getSession.mockResolvedValue(session(null));
    const error = await getAccessToken().catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 401, code: "unauthenticated", message: "Please sign in." });
  });

  it("rejects with aborted while signing out, even when the sign-out starts during getSession", async () => {
    getSession.mockResolvedValue(session("tok-1"));
    beginSignOut();
    await expect(getAccessToken()).rejects.toMatchObject({ status: 0, code: "aborted", message: "Signing out." });
    expect(getSession).not.toHaveBeenCalled();

    resetSigningOutForTests();
    getSession.mockImplementation(async () => {
      beginSignOut();
      return session("tok-1");
    });
    await expect(getAccessToken()).rejects.toMatchObject({ status: 0, code: "aborted" });
  });
});
```

Create `frontend/src/lib/queries/client.test.ts`:

```ts
import type { QueryClient, QueryKey } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/client";
import type { ApiErrorCode } from "@/lib/api/errors";
import { beginSignOut, resetSigningOutForTests } from "@/lib/auth";

import { authEvents } from "./auth-events";
import { isRetryable, makeQueryClient } from "./client";
import { keys } from "./keys";

// Node project: no setup-dom.ts here. lib/auth imports the Supabase client, which these tests never call.
vi.mock("@/lib/supabase/client", () => ({
  createClient: () => {
    throw new Error("queries/client.test.ts must not reach Supabase");
  },
}));

const noChurchAccess = () =>
  new ApiError(403, "forbidden", "You don't have access to this church.", {
    details: { reason: "no_church_access" },
  });

describe("isRetryable", () => {
  it.each<[number, ApiErrorCode]>([
    [0, "network_error"],
    [0, "timeout"],
    [500, "internal_error"],
    [502, "upstream_error"],
    [503, "db_unavailable"],
  ])("retries %i %s", (status, code) => {
    expect(isRetryable(new ApiError(status, code, "x"))).toBe(true);
  });

  it.each<[number, ApiErrorCode]>([
    [0, "aborted"],
    [400, "bad_request"],
    [401, "unauthenticated"],
    [403, "forbidden"],
    [422, "invalid_request"],
    [429, "rate_limited"],
  ])("never retries %i %s", (status, code) => {
    expect(isRetryable(new ApiError(status, code, "x"))).toBe(false);
  });
});

describe("handleAuthErrors (through makeQueryClient's caches)", () => {
  let client: QueryClient;
  let events: string[];
  let unsubscribe: Array<() => void>;

  beforeEach(() => {
    client = makeQueryClient();
    events = [];
    unsubscribe = [
      authEvents.onSignOutRequired(() => events.push("signOutRequired")),
      authEvents.onChurchAccessLost((id) => events.push(`churchAccessLost:${id}`)),
    ];
  });

  afterEach(() => {
    for (const off of unsubscribe) off();
    client.clear();
    resetSigningOutForTests();
  });

  async function failQuery(queryKey: QueryKey, error: ApiError): Promise<void> {
    await expect(client.fetchQuery({ queryKey, queryFn: () => Promise.reject(error) })).rejects.toBe(error);
  }

  async function failMutation(meta: Record<string, unknown> | undefined, error: ApiError): Promise<void> {
    const mutation = client.getMutationCache().build(client, { mutationFn: () => Promise.reject(error), meta });
    await expect(mutation.execute(undefined)).rejects.toBe(error);
  }

  it("asks for sign-out on a 401 from any query", async () => {
    await failQuery(keys.me(), new ApiError(401, "unauthenticated", "Please sign in."));
    expect(events).toEqual(["signOutRequired"]);
  });

  it("reports no_church_access with the church id from the query key", async () => {
    await failQuery(keys.churchProfile("c-1"), noChurchAccess());
    expect(events).toEqual(["churchAccessLost:c-1"]);
  });

  it("reports no_church_access with the church id from the mutation's meta", async () => {
    await failMutation({ churchId: "c-2" }, noChurchAccess());
    expect(events).toEqual(["churchAccessLost:c-2"]);
  });

  it("emits nothing for a role 403", async () => {
    const roleError = new ApiError(403, "forbidden", "Only church admins can do this.");
    await failQuery(keys.churchProfile("c-1"), roleError);
    await failMutation({ churchId: "c-1" }, roleError);
    expect(events).toEqual([]);
  });

  it("emits nothing while signing out", async () => {
    beginSignOut();
    await failQuery(keys.me(), new ApiError(401, "unauthenticated", "Please sign in."));
    await failQuery(keys.churchProfile("c-1"), noChurchAccess());
    await failMutation({ churchId: "c-1" }, noChurchAccess());
    expect(events).toEqual([]);
  });
});
```

Create `frontend/src/lib/queries/keys.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import { keys } from "./keys";

describe("keys", () => {
  it("builds the user-level and reference keys of F §4.4", () => {
    expect(keys.me()).toEqual(["me"]);
    expect(keys.translations()).toEqual(["ref", "translations"]);
    expect(keys.liturgyConfig()).toEqual(["ref", "liturgy-config"]);
    expect(keys.lectionary("2026-10-04")).toEqual(["lectionary", "2026-10-04"]);
    expect(keys.passage("NRSVUE", "John 3:16")).toEqual(["passage", "NRSVUE", "John 3:16"]);
    expect(keys.gmailConnection()).toEqual(["gmail-connection"]);
  });

  it("starts every church-scoped key with ['church', id]", () => {
    const id = "c-1";
    const churchKeys: ReadonlyArray<readonly unknown[]> = [
      keys.church(id),
      keys.churchProfile(id),
      keys.hymns(id, { q: "grace" }),
      keys.hymnals(id),
      keys.hymnalSources(id),
      keys.services(id, { page: 1 }),
      keys.service(id, "s-9"),
      keys.contacts(id),
      keys.members(id),
      keys.invites(id),
      keys.liturgyPrompts(id),
      keys.rubric(id),
      keys.prayerLibrary(id),
    ];
    expect(churchKeys.map((key) => key.slice(0, 2))).toEqual(churchKeys.map(() => ["church", id]));
    expect(churchKeys.map((key) => key.slice(2))).toEqual([
      [],
      ["profile"],
      ["hymns", { q: "grace" }],
      ["hymnals"],
      ["hymnal-sources"],
      ["services", { page: 1 }],
      ["service", "s-9"],
      ["contacts"],
      ["members"],
      ["invites"],
      ["liturgy-prompts"],
      ["rubric"],
      ["prayer-library"],
    ]);
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:
```bash
(cd frontend && npx vitest run src/lib/auth.test.ts src/lib/queries 2>&1 | grep -E "^ FAIL|^Error: Cannot find module|Test Files|Tests ")
```
Expected: three `FAIL` lines, with `Error: Cannot find module './auth' imported from '…/src/lib/auth.test.ts'`, `Error: Cannot find module '@/lib/auth' imported from '…/src/lib/queries/client.test.ts'.` and `Error: Cannot find module './keys' imported from '…/src/lib/queries/keys.test.ts'`; then `Test Files  3 failed (3)` and `Tests  no tests`.

- [ ] **Step 3: Create `frontend/src/lib/auth.ts`**

```ts
/**
 * The browser session for API calls, and the signing-out flag (F §4.5, §4.2).
 *
 * The flag is module state: set once by `beginSignOut()` (Task 19's `useSignOut`
 * calls it first) and cleared only by a full page load, since every sign-in
 * comes back through the Google OAuth redirect. While it is set, no new API
 * request starts (`getAccessToken` rejects with `aborted`), `handleAuthErrors`
 * stays quiet, and the `(signed-in)` layout shows its skeleton, so nothing
 * refetches or re-stores a church during sign-out.
 */
import { useSyncExternalStore } from "react";

import { ApiError } from "@/lib/api/client";
import { createClient } from "@/lib/supabase/client";

let signingOut = false;
const listeners = new Set<() => void>();

function notify(): void {
  for (const listener of [...listeners]) listener();
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function signingOutError(): ApiError {
  return new ApiError(0, "aborted", "Signing out.");
}

/** True from `beginSignOut()` until the next full page load. */
export function isSigningOut(): boolean {
  return signingOut;
}

/** Marks this tab as signing out. Idempotent. */
export function beginSignOut(): void {
  if (signingOut) return;
  signingOut = true;
  notify();
}

/** `isSigningOut()` for rendering; the server snapshot is `false`. */
export function useSigningOut(): boolean {
  return useSyncExternalStore(subscribe, isSigningOut, () => false);
}

/** Tests only: clears the flag (setup-dom.ts runs it after every DOM test). */
export function resetSigningOutForTests(): void {
  signingOut = false;
  notify();
}

/**
 * The Supabase access token for the API's `Authorization` header.
 * Rejects with `ApiError(401, "unauthenticated")` when there is no session and
 * with `ApiError(0, "aborted")` while signing out, including a sign-out that
 * starts while the session is being read.
 */
export async function getAccessToken(): Promise<string> {
  if (signingOut) throw signingOutError();
  const { data } = await createClient().auth.getSession();
  if (signingOut) throw signingOutError();
  const token = data.session?.access_token;
  if (!token) throw new ApiError(401, "unauthenticated", "Please sign in.");
  return token;
}
```

- [ ] **Step 4: Create `frontend/src/lib/queries/auth-events.ts` and `frontend/src/lib/queries/keys.ts`**

`frontend/src/lib/queries/auth-events.ts`:

```ts
/**
 * Auth events (F §4.4, §4.2): `handleAuthErrors` in ./client emits them from the
 * query and mutation caches; the layouts subscribe. `(signed-in)` signs out on
 * `signOutRequired` (Task 22); `(church)` falls back to the next church on
 * `churchAccessLost` (Task 23). Listeners run synchronously, in subscription order.
 */
type SignOutListener = () => void;
type ChurchAccessLostListener = (churchId: string) => void;

const signOutListeners = new Set<SignOutListener>();
const churchAccessLostListeners = new Set<ChurchAccessLostListener>();

export const authEvents = {
  /** An API call answered 401: the session is gone or was rejected. */
  signOutRequired(): void {
    for (const listener of [...signOutListeners]) listener();
  },

  /** A church-scoped call answered 403 with `details.reason = "no_church_access"`. */
  churchAccessLost(churchId: string): void {
    for (const listener of [...churchAccessLostListeners]) listener(churchId);
  },

  /** Returns the unsubscribe function (an effect's cleanup). */
  onSignOutRequired(listener: SignOutListener): () => void {
    signOutListeners.add(listener);
    return () => {
      signOutListeners.delete(listener);
    };
  },

  /** Returns the unsubscribe function (an effect's cleanup). */
  onChurchAccessLost(listener: ChurchAccessLostListener): () => void {
    churchAccessLostListeners.add(listener);
    return () => {
      churchAccessLostListeners.delete(listener);
    };
  },
};
```

`frontend/src/lib/queries/keys.ts`:

```ts
/**
 * The query key factory (F §4.4). Every church-scoped key starts with
 * ["church", churchId], so a church switch can cancel and remove all of one
 * church's queries with the prefix `keys.church(oldId)`, and `handleAuthErrors`
 * reads the church id from the key's second element. Later slices only add entries.
 */
export const keys = {
  me: () => ["me"] as const,
  translations: () => ["ref", "translations"] as const,
  liturgyConfig: () => ["ref", "liturgy-config"] as const,
  lectionary: (dateIso: string) => ["lectionary", dateIso] as const,
  passage: (translation: string, ref: string) => ["passage", translation, ref] as const,
  gmailConnection: () => ["gmail-connection"] as const,

  /** Prefix of every key below: cancel or remove a whole church with it. */
  church: (id: string) => ["church", id] as const,
  churchProfile: (id: string) => ["church", id, "profile"] as const,
  hymns: (id: string, params: object) => ["church", id, "hymns", params] as const,
  hymnals: (id: string) => ["church", id, "hymnals"] as const,
  hymnalSources: (id: string) => ["church", id, "hymnal-sources"] as const,
  services: (id: string, params: object) => ["church", id, "services", params] as const,
  service: (id: string, serviceId: string) => ["church", id, "service", serviceId] as const,
  contacts: (id: string) => ["church", id, "contacts"] as const,
  members: (id: string) => ["church", id, "members"] as const,
  invites: (id: string) => ["church", id, "invites"] as const,
  liturgyPrompts: (id: string) => ["church", id, "liturgy-prompts"] as const,
  rubric: (id: string) => ["church", id, "rubric"] as const,
  prayerLibrary: (id: string) => ["church", id, "prayer-library"] as const,
};
```

- [ ] **Step 5: Create `frontend/src/lib/church-context.tsx`**

React 19 renders a context object directly as its provider (`<ChurchContext value={…}>`).

```tsx
/**
 * The confirmed church for everything under the `(church)` layout (F §4.2).
 * The layout provides the `GET /church` result; `useApi().church` reads its id
 * for `X-Church-Id`.
 */
import { createContext, useContext, type ReactNode } from "react";

import type { Church } from "@/lib/api/types";

const ChurchContext = createContext<Church | null>(null);

export function ChurchProvider({ value, children }: { value: Church; children: ReactNode }) {
  return <ChurchContext value={value}>{children}</ChurchContext>;
}

/** The active church. Throws outside `ChurchProvider` (a church-scoped component rendered in the wrong place). */
export function useChurch(): Church {
  const church = useContext(ChurchContext);
  if (!church) throw new Error("useChurch() must be used inside ChurchProvider.");
  return church;
}

/** The active church, or null outside `ChurchProvider` (for code that also runs above it, like `useApi`). */
export function useOptionalChurch(): Church | null {
  return useContext(ChurchContext);
}
```

- [ ] **Step 6: Create `frontend/src/lib/queries/client.ts`**

```ts
/**
 * TanStack Query setup (F §4.4) and the bound API clients (F §4.5).
 * Pages and components never call `apiFetch` directly: hooks in
 * `src/lib/queries/<area>.ts` use `useApi()`.
 */
import {
  isServer,
  MutationCache,
  QueryCache,
  QueryClient,
  useMutation,
  type DefaultOptions,
  type Mutation,
  type Query,
  type UseMutationOptions,
  type UseMutationResult,
} from "@tanstack/react-query";
import { useMemo } from "react";

import { ApiError, apiFetch, type ApiOptions } from "@/lib/api/client";
import { isNoChurchAccess } from "@/lib/api/errors";
import { getAccessToken, isSigningOut } from "@/lib/auth";
import { useChurch, useOptionalChurch } from "@/lib/church-context";

import { authEvents } from "./auth-events";

/**
 * Worth one automatic retry: the request may never have reached the server
 * (`network_error`, `timeout`) or the server failed (5xx). Never a 4xx, and
 * never `aborted` (the caller or a sign-out cancelled it).
 */
export function isRetryable(e: unknown): boolean {
  if (!(e instanceof ApiError)) return false;
  return e.code === "network_error" || e.code === "timeout" || e.status >= 500;
}

type AnyQuery = Query<unknown, unknown, unknown>;
type AnyMutation = Mutation<unknown, unknown, unknown>;

/** The church a failed query or mutation was for: key ["church", id, …] or `meta.churchId`. */
function churchIdOf(source: AnyQuery | AnyMutation): string | null {
  if ("queryKey" in source) {
    const [scope, id] = source.queryKey;
    return scope === "church" && typeof id === "string" ? id : null;
  }
  const id = source.meta?.churchId;
  return typeof id === "string" ? id : null;
}

/**
 * The caches' `onError` (F §4.4): a 401 asks the `(signed-in)` layout to sign
 * out; a 403 `no_church_access` tells the `(church)` layout which church was
 * lost. A role 403 (no `reason`) emits nothing. While signing out it does
 * nothing, so one sign-out is ever in flight.
 */
export function handleAuthErrors(error: unknown, source: AnyQuery | AnyMutation): void {
  if (isSigningOut()) return;
  if (error instanceof ApiError && error.status === 401) {
    authEvents.signOutRequired();
    return;
  }
  if (isNoChurchAccess(error)) {
    const churchId = churchIdOf(source);
    if (churchId) authEvents.churchAccessLost(churchId);
  }
}

/** A client with the F §4.4 defaults; `overrides` replace single defaults (tests pass `{ queries: { retry: false } }`). */
export function makeQueryClient(overrides: DefaultOptions = {}): QueryClient {
  return new QueryClient({
    queryCache: new QueryCache({ onError: handleAuthErrors }),
    mutationCache: new MutationCache({
      onError: (error, _variables, _onMutateResult, mutation) => handleAuthErrors(error, mutation),
    }),
    defaultOptions: {
      ...overrides,
      queries: {
        staleTime: 30_000,
        gcTime: 5 * 60_000,
        refetchOnWindowFocus: true,
        retry: (failureCount, error) => failureCount < 1 && isRetryable(error),
        ...overrides.queries,
      },
      mutations: { retry: false, ...overrides.mutations },
    },
  });
}

let browserQueryClient: QueryClient | undefined;

/** A new client per server render; one client for the life of the browser tab (Next "TanStack Query" guide). */
export function getQueryClient(): QueryClient {
  if (isServer) return makeQueryClient();
  browserQueryClient ??= makeQueryClient();
  return browserQueryClient;
}

/**
 * `useMutation` for a church-scoped call: sets `meta.churchId` to the active
 * church, so `handleAuthErrors` can report a `no_church_access` 403 for it.
 * Use it inside `ChurchProvider` only (it calls `useChurch()`).
 */
export function useChurchMutation<TData = unknown, TError = ApiError, TVariables = void, TOnMutateResult = unknown>(
  options: UseMutationOptions<TData, TError, TVariables, TOnMutateResult>,
): UseMutationResult<TData, TError, TVariables, TOnMutateResult> {
  const church = useChurch();
  return useMutation({ ...options, meta: { ...options.meta, churchId: church.id } });
}

/** `apiFetch` with the token (and, for church calls, `X-Church-Id`) filled in. */
export type ApiCall = <T>(path: string, opts?: Omit<ApiOptions, "token" | "churchId">) => Promise<T>;

export type Api = {
  /** User-scoped routes (`/me`, 1b's `/churches`, `/invites/*`): no church header. */
  user: ApiCall;
  /** Church-scoped routes: `X-Church-Id` from `ChurchProvider`. Throws when called outside it. */
  church: ApiCall;
  /** A church-scoped call for a church that is not (yet) provided: the `(church)` layout's `GET /church`. */
  forChurch(churchId: string): ApiCall;
};

function boundCall(churchId: string | null): ApiCall {
  return async <T>(path: string, opts: Omit<ApiOptions, "token" | "churchId"> = {}) =>
    apiFetch<T>(path, { ...opts, token: await getAccessToken(), churchId });
}

const churchOutsideProvider: ApiCall = () => {
  throw new Error("useApi().church needs a ChurchProvider; use useApi().user or forChurch(id).");
};

/** The bound API clients (F §4.5). Stable while the active church stays the same. */
export function useApi(): Api {
  const churchId = useOptionalChurch()?.id ?? null;
  return useMemo(
    () => ({
      user: boundCall(null),
      church: churchId ? boundCall(churchId) : churchOutsideProvider,
      forChurch: (id: string) => boundCall(id),
    }),
    [churchId],
  );
}
```

- [ ] **Step 7: Create `frontend/src/lib/queries/me.ts` and `frontend/src/lib/queries/church.ts`**

`frontend/src/lib/queries/me.ts`:

```ts
import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import type { ApiError } from "@/lib/api/client";
import type { Me } from "@/lib/api/types";

import { useApi } from "./client";
import { keys } from "./keys";

/** `GET /me` (user-scoped): the user and their churches, sorted by name. The `(signed-in)` layout passes `enabled: false` while signing out. */
export function useMe(opts: { enabled?: boolean } = {}): UseQueryResult<Me, ApiError> {
  const api = useApi();
  return useQuery<Me, ApiError>({
    queryKey: keys.me(),
    queryFn: ({ signal }) => api.user<Me>("/me", { signal }),
    enabled: opts.enabled ?? true,
  });
}
```

`frontend/src/lib/queries/church.ts`:

```ts
import { skipToken, useQuery, type UseQueryResult } from "@tanstack/react-query";

import type { ApiError } from "@/lib/api/client";
import type { Church } from "@/lib/api/types";

import { useApi } from "./client";
import { keys } from "./keys";

/**
 * `GET /church` for `id` (key ["church", id, "profile"]): the server confirms
 * the membership. The `(church)` layout calls it above `ChurchProvider`, so it
 * sends the id through `forChurch`. No request while `id` is undefined or
 * `enabled` is false.
 */
export function useChurchProfile(
  id: string | undefined,
  opts: { enabled?: boolean } = {},
): UseQueryResult<Church, ApiError> {
  const api = useApi();
  return useQuery<Church, ApiError>({
    queryKey: keys.churchProfile(id ?? ""),
    queryFn: id ? ({ signal }) => api.forChurch(id)<Church>("/church", { signal }) : skipToken,
    enabled: opts.enabled ?? true,
  });
}
```

- [ ] **Step 8: Reset the flag after every DOM test in `frontend/src/test/setup-dom.ts`**

Add this import to the file's import block (after the last `import` line; Task 17 added `import { resetStoredChurchIdForTests } from "@/lib/church";` there):

```ts
import { resetSigningOutForTests } from "@/lib/auth";
```

Then add `resetSigningOutForTests();` as the **last statement of the existing `afterEach` block that calls `cleanup()`** (do not add a separate `afterEach`: Vitest runs `afterEach` hooks in reverse registration order, so a new hook at the end of the file would run before `cleanup()`). After Tasks 15 and 17 the block reads as below; replace it with the version under it:

```ts
afterEach(() => {
  cleanup();
  window.localStorage.clear();
  window.sessionStorage.clear();
  resetStoredChurchIdForTests();
});
```

```ts
afterEach(() => {
  cleanup();
  window.localStorage.clear();
  window.sessionStorage.clear();
  resetStoredChurchIdForTests();
  // Task 18: the signing-out flag is module state; clear it after the tree is unmounted.
  resetSigningOutForTests();
});
```

If Task 15's or Task 17's lines in that block differ in wording or order, keep them as they are and only append the two lines above as the block's last statements. The static import is safe: `vi.mock("@/lib/supabase/client", …)` in the same file is hoisted above every import, so `lib/auth.ts` loads the mocked client.

- [ ] **Step 9: Run the tests, the whole frontend suite, types and lint**

Run:
```bash
(cd frontend && npx vitest run src/lib/auth.test.ts src/lib/queries 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests " && npm run typecheck && npm run lint)
git status --short
```
Expected: `Test Files  3 passed (3)` and `Tests  21 passed (21)` (16 + 2 + 3); then `Test Files  12 passed (12)` and `Tests  87 passed (87)` (66 after Task 17 + 21), `tsc --noEmit` and `eslint` report no errors. The backend is untouched: `692 passed, 5 skipped` (Task 16's total). `git status --short` lists exactly (plus `?? .claude/`):

```
 M frontend/src/test/setup-dom.ts
?? frontend/src/lib/auth.test.ts
?? frontend/src/lib/auth.ts
?? frontend/src/lib/church-context.tsx
?? frontend/src/lib/queries/
```

If the whole suite's DOM tests now fail with `Cannot find module '@/lib/auth' imported from '…/src/test/setup-dom.ts'`, Step 3's file is missing or misnamed. If `tsc` reports `Module '"@tanstack/react-query"' has no exported member …`, check `(cd frontend && npm ls @tanstack/react-query)` shows `5.101.x` (Task 15); do not change these files to fit another major.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/lib/auth.ts frontend/src/lib/auth.test.ts \
        frontend/src/lib/church-context.tsx \
        frontend/src/lib/queries/auth-events.ts frontend/src/lib/queries/keys.ts \
        frontend/src/lib/queries/client.ts frontend/src/lib/queries/me.ts \
        frontend/src/lib/queries/church.ts \
        frontend/src/lib/queries/client.test.ts frontend/src/lib/queries/keys.test.ts \
        frontend/src/test/setup-dom.ts
git status --short
git commit -m "Frontend: query client, keys, auth events, useApi and the signing-out flag (F §4.4, §4.5, §4.2)

makeQueryClient applies the F §4.4 defaults (30 s stale, 5 min gc, one
retry for network_error/timeout/5xx only, no mutation retries) and routes
every query and mutation error through handleAuthErrors: a 401 emits
signOutRequired, a 403 no_church_access emits churchAccessLost with the church
id from the query key or the mutation's meta.churchId, and a role 403
emits nothing. useApi() binds apiFetch to getAccessToken(); its church
client reads ChurchProvider and throws outside it. The signing-out flag in
lib/auth.ts makes getAccessToken reject with aborted and silences
handleAuthErrors until the next page load, so one sign-out is in flight and
nothing refetches during it. useMe and useChurchProfile are the first hooks.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

The `git status --short` before the commit prints exactly (plus `?? .claude/`):

```
A  frontend/src/lib/auth.test.ts
A  frontend/src/lib/auth.ts
A  frontend/src/lib/church-context.tsx
A  frontend/src/lib/queries/auth-events.ts
A  frontend/src/lib/queries/church.ts
A  frontend/src/lib/queries/client.test.ts
A  frontend/src/lib/queries/client.ts
A  frontend/src/lib/queries/keys.test.ts
A  frontend/src/lib/queries/keys.ts
A  frontend/src/lib/queries/me.ts
M  frontend/src/test/setup-dom.ts
```

Tests after this task: backend `692 passed, 5 skipped` (unchanged); frontend `87 passed`.

---

### Task 19: `useSignOut`, `MeContext`, providers, `renderWithProviders` (F §4.4, §4.2; S Layouts; AC14 1a part)

This task finishes the client plumbing the layouts (Tasks 22-23) stand on. `useSignOut()` in `src/lib/auth.ts` implements S Flow D "Log out" and "Session expired": it raises Task 18's signing-out flag **first** (clarification 27, critique 8), then cancels and clears every query, forgets the stored church, removes `wsb:postLoginPath` and (unless asked to keep it) `wsb:pendingInviteCode`, ends this browser's Supabase session with `scope: "local"` and replaces the route with `/login`, or `/login?next=<path>` when `safeInternalPath` accepts `next` (clarification 16: 1a's 401 path already passes `next`; `/login` ignores it until 1b). It needs no `ChurchProvider`, so the `/welcome` stub's header can sign out (notes C14). The root layout stays a Server Component and wraps `children` in a new client `Providers` (a `QueryClientProvider` fed by Task 18's `getQueryClient()`, the pattern of Next's bundled "TanStack Query" guide); the `Toaster` stays where it is. `MeProvider`/`useMeContext()` (new `src/lib/me-context.tsx`, clarification 14) hold `/me` for the `(signed-in)` subtree. `renderWithProviders` (F §5.2) renders a DOM test inside the same providers with a fresh `retry: false` client; the `next/navigation` and Supabase mocks already come from Task 15's `setup-dom.ts` (clarification 15), so the real `lib/auth.ts` runs under test and the test asserts `signOut({ scope: "local" })` on Task 15's spy.

Choices recorded here: the returned sign-out function never rejects (supabase-js 2.117 reports a failed `/logout` call as `{ error }` **after** removing the local session, `GoTrueClient._signOut`; anything it throws is swallowed and `/login` still follows), and it does not check the flag itself (de-duplication lives in its callers: `handleAuthErrors` and Task 22's `onSignOutRequired` subscriber do nothing while `isSigningOut()`). `renderWithProviders` renders **no** `<Toaster />`: a test that asserts toast text (Tasks 22-23) renders `<Toaster />` next to its `ui`, so there is only ever one.

Verified before writing (offline, throwaway worktree, Vitest 3.2.7 on Node 26.4.0): `@tanstack/react-query` 5.101.1, `@testing-library/react` 16.3.2, `@testing-library/dom` 10.4.1 and jsdom 29.1.1 from the npm cache, Task 15's `mocks.ts`/`setup-dom.ts`/fixtures as written in its plan, and the Task 17/18 modules as their writers drafted them. `user-event` and `jest-dom` are not in the offline cache: the click went through a `fireEvent` stand-in, and these tests use no jest-dom matcher. Results: both tests pass; the first fails (`expected false to be true`) if `beginSignOut()` moves after `queryClient.clear()`, the second if the call drops `{ scope: "local" }`; `tsc --noEmit` and `eslint` are clean on every file below; Task 18's node-project `auth.test.ts` still passes although `auth.ts` now also imports `next/navigation` and `@tanstack/react-query`. One environment fact from that run: on Node ≥ 25 Node's own experimental `localStorage` global shadows jsdom's under Vitest 3.2.7, so `window.localStorage` is `undefined` in every DOM test (`ExperimentalWarning: localStorage is not available because --localstorage-file was not provided.`); root-level `test.poolOptions.forks.execArgv: ["--no-experimental-webstorage"]` in `vitest.config.ts` fixes it (checked, and `tsc` accepts it; CI's Node 22 is unaffected). That belongs to Task 15's config; Step 2 below says what to do if it is missing.

**Files:**
- Modify: `frontend/src/lib/auth.ts` (Task 18's file: its import block is replaced; `SignOutOptions` and `useSignOut` are appended at the end)
- Modify: `frontend/src/app/layout.tsx:4-5` (one import added) and `:23` (`{children}` → `<Providers>{children}</Providers>`)
- Create: `frontend/src/lib/me-context.tsx`, `frontend/src/app/providers.tsx`, `frontend/src/test/render.tsx`
- Test: `frontend/src/lib/use-sign-out.test.tsx` (new, `dom` project, 2 tests)

**Interfaces:**
- Consumes:
  - Task 18 `@/lib/auth`: `beginSignOut(): void`, `isSigningOut(): boolean` (and the module's existing imports `useSyncExternalStore`, `ApiError`, `createClient`); `@/lib/queries/client`: `makeQueryClient(overrides?: DefaultOptions): QueryClient` (installs `handleAuthErrors` on both caches), `getQueryClient(): QueryClient`; `@/lib/queries/keys`: `keys.me()`, `keys.churchProfile(id)`; `@/lib/church-context`: `ChurchProvider({ value: Church, children })`.
  - Task 17: `@/lib/church`: `storeChurchId(id: string | null): void` (writes `activeChurchId` and notifies `useStoredChurchId`), `readStoredChurchId(): string | null`; `@/lib/storage`: `SESSION_KEYS = { pendingInviteCode: "wsb:pendingInviteCode", postLoginPath: "wsb:postLoginPath" }`, `readSession`, `writeSession`, `removeSession`; `@/lib/urls`: `safeInternalPath(raw: unknown): string | null`.
  - Task 16: `@/lib/api/types`: `Church`, `Me`.
  - Task 15: `@/test/mocks`: `testRouter.replace: Mock`, `supabaseAuth.signOut: Mock` (resolves `{ error: null }` by default), `setTestPath(path: string): void`; `setup-dom.ts` (mocks `next/navigation` and `@/lib/supabase/client`, resets spies and path before each test, clears both storages after it; Tasks 17-18 add `resetStoredChurchIdForTests` / `resetSigningOutForTests`); `@/test/fixtures`: `me(overrides?)`, `church(overrides?)`; devDependencies `@testing-library/react`, `@testing-library/user-event`, `@tanstack/react-query`.
- Produces:
  - `frontend/src/lib/auth.ts`: `export type SignOutOptions = { keepPendingInvite?: boolean; next?: string }`; `export function useSignOut(): (opts?: SignOutOptions) => Promise<void>` (a stable `useCallback`; order: `beginSignOut()` → `await queryClient.cancelQueries()` → `queryClient.clear()` → `storeChurchId(null)` → `removeSession("wsb:postLoginPath")` → `removeSession("wsb:pendingInviteCode")` unless `keepPendingInvite` → `await createClient().auth.signOut({ scope: "local" })` (errors swallowed) → `router.replace("/login")` or `router.replace("/login?next=" + encodeURIComponent(safe))` with `safe = safeInternalPath(next)`; never rejects). Later users: Task 21 (`AccountMenu`'s "Log out" via `AppHeader onSignOut`), Task 22 (`(signed-in)` layout: `onSignOutRequired` → `signOut({ keepPendingInvite: true, next: pathname })`, `/welcome` stub's Log out), Task 23 (`(church)` layout's header), 1b ("Use a different Google account").
  - `frontend/src/lib/me-context.tsx` (`"use client"`): `export function MeProvider({ value, children }: { value: Me; children: ReactNode })`; `export function useMeContext(): Me` (throws `Error("useMeContext() must be used inside <MeProvider>.")` outside). Later users: Task 22 (provider), Task 23 (`me.churches`, `me.user`), slice 2 (`user.id` draft key).
  - `frontend/src/app/providers.tsx` (`"use client"`): `export function Providers({ children }: { children: ReactNode })` → `<QueryClientProvider client={getQueryClient()}>`. Rendered once, by the root layout.
  - `frontend/src/test/render.tsx`: `export type UserEvent = ReturnType<typeof userEvent.setup>`; `export type RenderWithProvidersOptions = { me?: Me; church?: Church; path?: string; queryClient?: QueryClient }`; `export function renderWithProviders(ui: ReactElement, opts?: RenderWithProvidersOptions): RenderResult & { user: UserEvent; queryClient: QueryClient }` (wrapper order `QueryClientProvider` → `MeProvider` when `me` → `ChurchProvider` when `church`; default client `makeQueryClient({ queries: { retry: false } })`, so `handleAuthErrors` runs in tests; `path` calls `setTestPath(path)`, otherwise the path stays as `setup-dom.ts` or the test set it; `user = userEvent.setup()`; no `<Toaster />`). Later users: Tasks 20-23 and every later DOM test.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/lib/use-sign-out.test.tsx`:

```tsx
import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { isSigningOut, type SignOutOptions, useSignOut } from "@/lib/auth";
import { readStoredChurchId, storeChurchId } from "@/lib/church";
import { useMeContext } from "@/lib/me-context";
import { keys } from "@/lib/queries/keys";
import { readSession, SESSION_KEYS, writeSession } from "@/lib/storage";
import { church, me } from "@/test/fixtures";
import { supabaseAuth, testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

/** Stands in for the account menu's "Log out": reads `/me` from `MeProvider`, signs out with `options`. */
function LogOut({ options }: { options?: SignOutOptions }) {
  const { user } = useMeContext();
  const signOut = useSignOut();
  return (
    <button type="button" onClick={() => void signOut(options)}>
      Log out {user.email}
    </button>
  );
}

/** What a signed-in tab holds: a stored church, a pending invite and a post-login path. */
function seedSignedInTab(): void {
  storeChurchId(church().id);
  writeSession(SESSION_KEYS.pendingInviteCode, "INVITE-CODE");
  writeSession(SESSION_KEYS.postLoginPath, JSON.stringify({ path: "/welcome", at: 0 }));
}

describe("useSignOut", () => {
  it("raises the flag first, clears the cache, stored church and wsb: keys, signs out locally, then goes to /login", async () => {
    seedSignedInTab();
    const pat = me();
    const { user, queryClient } = renderWithProviders(<LogOut />, { me: pat });
    queryClient.setQueryData(keys.me(), pat);
    queryClient.setQueryData(keys.churchProfile(church().id), church());
    const clear = queryClient.clear.bind(queryClient);
    let signingOutWhenCleared: boolean | undefined;
    vi.spyOn(queryClient, "clear").mockImplementation(() => {
      signingOutWhenCleared = isSigningOut();
      clear();
    });

    await user.click(screen.getByRole("button", { name: `Log out ${pat.user.email}` }));

    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/login"));
    expect(signingOutWhenCleared).toBe(true);
    expect(queryClient.getQueryCache().getAll()).toEqual([]);
    expect(readStoredChurchId()).toBeNull();
    expect(readSession(SESSION_KEYS.pendingInviteCode)).toBeNull();
    expect(readSession(SESSION_KEYS.postLoginPath)).toBeNull();
    expect(supabaseAuth.signOut).toHaveBeenCalledTimes(1);
    expect(supabaseAuth.signOut).toHaveBeenCalledWith({ scope: "local" });
    expect(supabaseAuth.signOut.mock.invocationCallOrder[0]).toBeLessThan(
      testRouter.replace.mock.invocationCallOrder[0],
    );
    expect(testRouter.replace).toHaveBeenCalledTimes(1);
  });

  it("keeps the pending invite and returns to an allow-listed path when asked (the 401 path)", async () => {
    seedSignedInTab();
    const pat = me();
    const { user } = renderWithProviders(
      <LogOut options={{ keepPendingInvite: true, next: "/welcome" }} />,
      { me: pat, path: "/welcome" },
    );

    await user.click(screen.getByRole("button", { name: `Log out ${pat.user.email}` }));

    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/login?next=%2Fwelcome"));
    expect(readSession(SESSION_KEYS.pendingInviteCode)).toBe("INVITE-CODE");
    expect(readSession(SESSION_KEYS.postLoginPath)).toBeNull();
    expect(readStoredChurchId()).toBeNull();
    expect(supabaseAuth.signOut).toHaveBeenCalledWith({ scope: "local" });
    expect(isSigningOut()).toBe(true);
  });
});
```

The probe component stands in for the account menu (Task 21) and reads `/me` through `useMeContext()`, so the test also proves `renderWithProviders` wires `MeProvider`. The `clear` spy records the flag at the moment the cache is emptied: that is the ordering critique 8 asks for, which a check after the fact cannot see.

- [ ] **Step 2: Run it to verify it fails**

Run: `(cd frontend && npx vitest run src/lib/use-sign-out.test.tsx)`
Expected: FAIL before any test runs — `FAIL  |dom| src/lib/use-sign-out.test.tsx [ src/lib/use-sign-out.test.tsx ]`, `Error: Failed to resolve import "@/lib/me-context" from "src/lib/use-sign-out.test.tsx". Does the file exist?` (`Plugin: vite:import-analysis`), `Test Files  1 failed (1)`, `Tests  no tests`. (`@/test/render` is missing too, and `useSignOut` is not exported yet; Vite reports the first unresolved import.)

If instead it fails inside `setup-dom.ts` with `TypeError: Cannot read properties of undefined (reading 'clear')` at `window.localStorage.clear()` and the log shows `ExperimentalWarning: localStorage is not available because --localstorage-file was not provided.`, the Node on this machine (≥ 25) shadows jsdom's storage: Task 15's `vitest.config.ts` needs `poolOptions: { forks: { execArgv: ["--no-experimental-webstorage"] } }` at the root of `test` (next to `projects`). Stop and report it; fix it in Task 15's file (re-review Task 15), not here.

- [ ] **Step 3: Create `frontend/src/lib/me-context.tsx`**

```tsx
"use client";

/**
 * The signed-in user's `/me` for everything under the `(signed-in)` layout
 * (S Layouts): `useMeContext().user.id` keys slice 2's drafts and
 * `.churches` feeds the church switcher and draft pruning.
 */
import { createContext, useContext, type ReactNode } from "react";

import type { Me } from "@/lib/api/types";

const MeContext = createContext<Me | null>(null);

export function MeProvider({ value, children }: { value: Me; children: ReactNode }) {
  return <MeContext value={value}>{children}</MeContext>;
}

/** The current `/me`. Throws outside `MeProvider` (a layout bug, not a user error). */
export function useMeContext(): Me {
  const me = useContext(MeContext);
  if (!me) throw new Error("useMeContext() must be used inside <MeProvider>.");
  return me;
}
```

`<MeContext value={value}>` is React 19's context-as-provider (react 19.2.8); `useMeContext()` throws rather than returning `null`, because every consumer sits under the `(signed-in)` layout, which renders `MeProvider` only once `/me` has loaded.

- [ ] **Step 4: Create `frontend/src/test/render.tsx`**

```tsx
/**
 * `renderWithProviders` (F §5.2): renders `ui` the way the app does, inside a
 * `QueryClientProvider` (a fresh client per call, `retry: false`, with the app's
 * `handleAuthErrors`), a `MeProvider` when `me` is given and a `ChurchProvider`
 * when `church` is given. `path` sets what the mocked `usePathname()` returns
 * (`setup-dom.ts` resets it to "/" before each test).
 *
 * It renders no `<Toaster />`: a test that asserts toast text renders one
 * next to `ui`. Requests go through the real `apiFetch`, so stub `fetch` with
 * `installFakeApi` in the test.
 */
import { QueryClientProvider, type QueryClient } from "@tanstack/react-query";
import { render, type RenderResult } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement, ReactNode } from "react";

import type { Church, Me } from "@/lib/api/types";
import { ChurchProvider } from "@/lib/church-context";
import { MeProvider } from "@/lib/me-context";
import { makeQueryClient } from "@/lib/queries/client";

import { setTestPath } from "./mocks";

export type UserEvent = ReturnType<typeof userEvent.setup>;

export type RenderWithProvidersOptions = {
  me?: Me;
  church?: Church;
  path?: string;
  queryClient?: QueryClient;
};

export function renderWithProviders(
  ui: ReactElement,
  { me, church, path, queryClient = makeQueryClient({ queries: { retry: false } }) }: RenderWithProvidersOptions = {},
): RenderResult & { user: UserEvent; queryClient: QueryClient } {
  if (path !== undefined) setTestPath(path);

  function Wrapper({ children }: { children: ReactNode }) {
    let tree = children;
    if (church) tree = <ChurchProvider value={church}>{tree}</ChurchProvider>;
    if (me) tree = <MeProvider value={me}>{tree}</MeProvider>;
    return <QueryClientProvider client={queryClient}>{tree}</QueryClientProvider>;
  }

  const user = userEvent.setup();
  // Object.assign, not a spread: with `wrapper` tsc picks RTL's generic `render` overload,
  // and a spread of that result loses the bound queries' types (getByRole & co.).
  return Object.assign(render(ui, { wrapper: Wrapper }), { user, queryClient });
}
```

- [ ] **Step 5: Add `useSignOut` to `frontend/src/lib/auth.ts`**

Replace Task 18's import block:

```ts
import { useSyncExternalStore } from "react";

import { ApiError } from "@/lib/api/client";
import { createClient } from "@/lib/supabase/client";
```

with:

```ts
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useCallback, useSyncExternalStore } from "react";

import { ApiError } from "@/lib/api/client";
import { storeChurchId } from "@/lib/church";
import { removeSession, SESSION_KEYS } from "@/lib/storage";
import { createClient } from "@/lib/supabase/client";
import { safeInternalPath } from "@/lib/urls";
```

(If Task 18's block differs, keep its lines and add the six new names: `useQueryClient`, `useRouter`, `useCallback`, `storeChurchId`, `removeSession` + `SESSION_KEYS`, `safeInternalPath`.) Nothing in `@/lib/church`, `@/lib/storage` or `@/lib/urls` imports `@/lib/auth`, and `useQueryClient` comes from the library, not `@/lib/queries/client` (which imports `@/lib/auth`), so no import cycle appears. Then append at the end of the file, after `getAccessToken`:

```ts
export type SignOutOptions = {
  /** Keep `wsb:pendingInviteCode` (the automatic 401 path), so an invite survives the new sign-in. */
  keepPendingInvite?: boolean;
  /** Where to return after sign-in; used only when `safeInternalPath` accepts it. */
  next?: string;
};

/**
 * Flow D sign-out (S "Log out" and "Session expired"; F §4.2). The signing-out
 * flag goes up first, so while the cache is torn down nothing refetches, no 401
 * starts a second sign-out and no layout re-stores a church (clarification 27).
 * Then: cancel and clear every query, forget the stored church and the `wsb:`
 * session keys (the pending invite only when not asked to keep it), end this
 * browser's Supabase session (`scope: "local"`, never the global default) and
 * go to `/login`, with `?next=` when `next` is an allow-listed path. Needs no
 * `ChurchProvider`, so the `/welcome` header can use it.
 */
export function useSignOut(): (opts?: SignOutOptions) => Promise<void> {
  const queryClient = useQueryClient();
  const router = useRouter();
  return useCallback(
    async ({ keepPendingInvite = false, next }: SignOutOptions = {}) => {
      beginSignOut();
      await queryClient.cancelQueries();
      queryClient.clear();
      storeChurchId(null);
      removeSession(SESSION_KEYS.postLoginPath);
      if (!keepPendingInvite) removeSession(SESSION_KEYS.pendingInviteCode);
      try {
        await createClient().auth.signOut({ scope: "local" });
      } catch {
        // supabase-js reports failures as `{ error }` after removing the local
        // session; a throw here is unexpected, and /login is still the right place.
      }
      const back = next === undefined ? null : safeInternalPath(next);
      router.replace(back ? `/login?next=${encodeURIComponent(back)}` : "/login");
    },
    [queryClient, router],
  );
}
```

- [ ] **Step 6: Run the test**

Run: `(cd frontend && npx vitest run src/lib/use-sign-out.test.tsx)`
Expected: `✓ |dom| src/lib/use-sign-out.test.tsx (2 tests)`, `Test Files  1 passed (1)`, `Tests  2 passed (2)`.

- [ ] **Step 7: Create `frontend/src/app/providers.tsx` and wrap the root layout**

Create `frontend/src/app/providers.tsx`:

```tsx
"use client";

import { QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

import { getQueryClient } from "@/lib/queries/client";

/**
 * Client-side providers for the whole app (F §4.4): one QueryClient for the
 * life of the browser tab, a new one per server render (Next's "TanStack
 * Query" guide). The root layout stays a Server Component and renders this.
 */
export function Providers({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={getQueryClient()}>{children}</QueryClientProvider>;
}
```

In `frontend/src/app/layout.tsx`, replace lines 4-5:

```tsx
import { Toaster } from "@/components/ui/sonner";
import "./globals.css";
```

with:

```tsx
import { Toaster } from "@/components/ui/sonner";
import "./globals.css";
import { Providers } from "./providers";
```

and replace line 23:

```tsx
        {children}
```

with:

```tsx
        <Providers>{children}</Providers>
```

The layout keeps `metadata`, `viewport` and `<Toaster richColors />` (a sibling of `Providers`, as S's file map says) and stays a Server Component. The whole file afterwards:

```tsx
import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import { Toaster } from "@/components/ui/sonner";
import "./globals.css";
import { Providers } from "./providers";

const geistSans = Geist({ variable: "--font-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Worship Service Builder",
  description: "Plan Sunday worship services with your church.",
};

export const viewport: Viewport = { width: "device-width", initialScale: 1 };

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body className="antialiased">
        <Providers>{children}</Providers>
        <Toaster richColors />
      </body>
    </html>
  );
}
```

`src/app/page.tsx` (deleted in Task 23) keeps working: it now merely has a `QueryClientProvider` above it.

- [ ] **Step 8: Run the frontend check and the build**

Run: `(cd frontend && npm test && npm run typecheck && npm run lint)`
Expected: `Test Files  13 passed (13)` and `Tests  89 passed (89)` (87 after Task 18 + 2; the `dom` project now runs `setup-dom.test.tsx`, `church-store.test.tsx` and `use-sign-out.test.tsx`); `tsc --noEmit` and `eslint` print nothing beyond the script banners.

The root layout changed, so build once with CI's placeholder env (Global Constraints; `next/font/google` fetches Geist, so this needs the network, as in CI):

Run: `(cd frontend && NEXT_PUBLIC_SUPABASE_URL=https://ci-placeholder.supabase.co NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build)`
Expected: `✓ Compiled successfully`, no `"use client"`/`metadata` error, exit 0; the route table lists `/`, `/_not-found`, `/auth/callback` and `/login` (unchanged). Backend untouched: `692 passed, 5 skipped` stands (not rerun).

`git status --short` lists exactly (plus `?? .claude/`):

```
 M frontend/src/app/layout.tsx
 M frontend/src/lib/auth.ts
?? frontend/src/app/providers.tsx
?? frontend/src/lib/me-context.tsx
?? frontend/src/lib/use-sign-out.test.tsx
?? frontend/src/test/render.tsx
```

- [ ] **Step 9: Commit**

```bash
git add frontend/src/lib/auth.ts frontend/src/lib/me-context.tsx frontend/src/app/providers.tsx \
        frontend/src/app/layout.tsx frontend/src/test/render.tsx frontend/src/lib/use-sign-out.test.tsx
git commit -m "Frontend: useSignOut, MeContext, app Providers and renderWithProviders (F §4.2, §4.4, §5.2; S Flow D)

useSignOut raises the signing-out flag first, then cancels and clears every
query, forgets the stored church and the wsb: session keys (keeping a pending
invite when asked), signs out with scope local and replaces the route with
/login (?next= only for an allow-listed path). The root layout wraps its
children in Providers (one QueryClient per browser tab, a new one per server
render). MeProvider/useMeContext hold /me for the signed-in subtree;
renderWithProviders renders DOM tests inside the same providers with a fresh
retry-free client.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Tests after this task: backend `692 passed, 5 skipped` (unchanged); frontend `89 passed` (13 files).

---

### Task 20: UI kit, generated components, `touch` size (F §4.8, §4.9; AC15)

The F §4.8 kit arrives in `src/components/app/`: `EmptyState`, `ErrorState`, `PendingButton`, `ConfirmDialog` and `PageHeader`. The base-nova components that 1a and 1b need are generated with `npx shadcn@latest add input label tabs alert alert-dialog combobox` (S tooling; owner Q3). `button.tsx` gains the `touch` size. After this task, that variant is the only hand edit to a generated file (F §4.9 item 1).

`shadcn add` downloads the registry from `ui.shadcn.com`, so Steps 2–3 need the network. Nothing else in this task does. The generated files cannot be known before the command runs. The tests therefore use only the exports every shadcn version of these files has (`Alert`, `AlertTitle`, `AlertDescription`; `AlertDialog`, `AlertDialogContent`, `AlertDialogHeader`, `AlertDialogFooter`, `AlertDialogTitle`, `AlertDialogDescription`, `AlertDialogCancel`). `npm run typecheck` in Step 4 is what proves those exports exist.

These decisions are recorded here and used by later tasks:
- **`ConfirmDialog`'s confirm button is a `PendingButton`, not `AlertDialogAction`.** In some registry versions `AlertDialogAction` is a `Close` and shuts the dialog on click. The dialog must stay open while the mutation is pending, and the caller closes it (`onOpenChange(false)`) when the mutation succeeds. **Cancel** is the generated `AlertDialogCancel`, a Base UI `Close`, so it calls `onOpenChange(false)`. `onOpenChange` receives only the boolean: Base UI's second `eventDetails` argument is dropped.
- **`ErrorState`** shows `describeError(error)` inside a destructive `Alert` (`role="alert"`). With `title`, the title is the `AlertTitle` and the sentence is the `AlertDescription`. Without it, the sentence is the `AlertTitle`. **Retry** is an outline `touch` button outside the alert and calls `onRetry()` with no arguments, so a TanStack `refetch` never receives the click event as its options. The text in the alert is exactly the sentence, which Tasks 22 and 23 match ("Can't reach the server." / "Something went wrong. (Ref: xxxxxxxx)").
- **`PendingButton`** keeps the `Button` props. While `pending` it is disabled, sets `aria-busy="true"`, and shows a spinning `Loader2Icon` (`data-icon="inline-start"`, `aria-hidden`) followed by `pendingLabel` (default "Saving…", with the Unicode ellipsis). The page around it stays usable (F §4.8).
- **`touch` size** = `"h-11 gap-1.5 px-4 has-data-[icon=inline-end]:pr-3.5 has-data-[icon=inline-start]:pl-3.5"`. This is S's `h-11 px-4` plus `default`'s gap. The icon-side padding keeps `default`'s rule of 0.5 less than `px` (`px-2.5` → `pl-2`), so `px-4` → `pl-3.5`. Copying `pl-2` verbatim would leave a lopsided 8 px / 16 px button.
- `EmptyState`'s title is an `h2` and `PageHeader`'s title is the page's `h1`. Neither file has `"use client"`, so both work in server components. `ConfirmDialog` has `"use client"`: it passes an inline callback to a client component.

Tried in a throwaway worktree. The environment was Vitest 3.2.7, jsdom 29.1.1 and `@testing-library/react` 16.3.2 from the npm cache, `@base-ui/react` 1.8.0, `fireEvent` (user-event and jest-dom are not in the cache), and a stand-in `alert-dialog.tsx`/`alert.tsx` written from the base-nova registry shape. Results:
- The popup renders in a portal with `role="alertdialog"`, `aria-labelledby` (title) and `aria-describedby` (description).
- Clicking the confirm button calls `onConfirm` and leaves the dialog open.
- **Cancel** calls `onOpenChange` exactly once with `false`, and with `getAnimations = () => []` the popup unmounts.
- A pending Base UI `Button` gets the native `disabled` attribute, and clicking it does not call `onClick`.
- `type="submit"` overrides Base UI's default `type="button"`.
- `tsc --noEmit` and `eslint` pass on all five components and the Combobox fallback in Step 3.
- The fallback opens with ArrowDown and filters on input.

Base UI never sets `pointer-events: none` on `body` (checked with a grep of `esm/`), so user-event's pointer check passes on popups. The user-event runs of these tests themselves are UNVERIFIED locally: that package first installs in Task 15.

**Files:**
- Generate (Steps 2–3, `npx shadcn@latest add`): `frontend/src/components/ui/input.tsx`, `frontend/src/components/ui/label.tsx`, `frontend/src/components/ui/tabs.tsx`, `frontend/src/components/ui/alert.tsx`, `frontend/src/components/ui/alert-dialog.tsx`, `frontend/src/components/ui/combobox.tsx`. Registry dependencies of these items are also created. The expected ones are `frontend/src/components/ui/input-group.tsx` and `frontend/src/components/ui/textarea.tsx` (base-nova's Combobox is built on InputGroup; UNVERIFIED offline). Step 4 records the real list, and the commit message carries it for Task 25's file-list check (§3: 131 paths + 1 for Q2 + these).
- Modify: `frontend/src/components/ui/button.tsx:26` (a `touch` entry after `lg`; nothing else)
- Create: `frontend/src/components/app/empty-state.tsx`, `frontend/src/components/app/error-state.tsx`, `frontend/src/components/app/pending-button.tsx`, `frontend/src/components/app/confirm-dialog.tsx`, `frontend/src/components/app/page-header.tsx`
- Test: `frontend/src/components/ui/button.test.tsx` (1), `frontend/src/components/app/error-state.test.tsx` (3), `frontend/src/components/app/pending-button.test.tsx` (2), `frontend/src/components/app/confirm-dialog.test.tsx` (2), `frontend/src/components/app/empty-state.test.tsx` (1), `frontend/src/components/app/page-header.test.tsx` (1). All six are new, 10 tests in total.

**Interfaces:**
- Consumes:
  - Task 15's Vitest `dom` project (jsdom, `src/**/*.test.tsx`, setupFiles `src/test/setup-dom.ts`). It provides the `@testing-library/jest-dom/vitest` matchers, `cleanup` after each test, and the shims `PointerEvent`, `ResizeObserver`, `matchMedia`, `scrollIntoView`, `hasPointerCapture`/`releasePointerCapture` and `getAnimations = () => []`.
  - Task 15's dev dependencies `@testing-library/react` and `@testing-library/user-event`.
  - Task 16's `ApiError` (`@/lib/api/client`: `new ApiError(status, code, message, { requestId? })`) and `describeError(e: unknown): string` (`@/lib/api/errors`).
  - Existing `Button`/`buttonVariants` (`src/components/ui/button.tsx`), `cn` (`@/lib/utils`) and `lucide-react` icons (`Loader2Icon`, `CircleAlertIcon`, `LucideIcon`).
- Produces:
  - `Button` `size="touch"` (`src/components/ui/button.tsx`). Later users: Tasks 21–23 and 1b (S "primary actions full-width `size="touch"`").
  - Generated components, each exporting its registry names: `Input`, `Label`, `Tabs`/`TabsList`/`TabsTrigger`/`TabsContent`, `Alert`/`AlertTitle`/`AlertDescription`, the `AlertDialog*` family, and the `Combobox*` family. Later users: 1b (`/welcome` tabs and forms, `TimezoneCombobox`), Task 20's own kit.
  - `src/components/app/empty-state.tsx`: `export type EmptyStateProps = { icon?: LucideIcon; title: string; description: string; action?: ReactNode }`; `export function EmptyState(props: EmptyStateProps): JSX.Element` (icon `aria-hidden`, title `h2`, one-sentence `p`, action below).
  - `src/components/app/error-state.tsx`: `export type ErrorStateProps = { error: unknown; onRetry: () => void; title?: string }`; `export function ErrorState(props: ErrorStateProps): JSX.Element`. Later users: Task 22 (full-page `/me` error), Task 23 (`GET /church` error, role 403), 1b (invite preview).
  - `src/components/app/pending-button.tsx`: `export type PendingButtonProps = ComponentProps<typeof Button> & { pending: boolean; pendingLabel?: string }`; `export function PendingButton(props: PendingButtonProps): JSX.Element` (default `pendingLabel` "Saving…"). Later users: 1b ("Creating church…", "Joining…"), 5a+, and `ConfirmDialog`.
  - `src/components/app/confirm-dialog.tsx`: `export type ConfirmDialogProps = { open: boolean; onOpenChange(open: boolean): void; title: string; description?: string; confirmLabel: string; onConfirm(): void; pending?: boolean; destructive?: boolean }`; `export function ConfirmDialog(props: ConfirmDialogProps): JSX.Element`. Later users: 6a+ (destructive actions).
  - `src/components/app/page-header.tsx`: `export type PageHeaderProps = { title: string; description?: string; actions?: ReactNode }`; `export function PageHeader(props: PageHeaderProps): JSX.Element` (title `h1`). Later users: slice 2+ pages.

- [ ] **Step 1: Preflight**

Run:
```bash
git status --short
ls frontend/src/components/ui
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```
Expected:
- `git status --short` prints only `?? .claude/`.
- `ls` prints the seven names `avatar.tsx`, `button.tsx`, `card.tsx`, `dropdown-menu.tsx`, `select.tsx`, `skeleton.tsx`, `sonner.tsx`, one per line.
- The test run prints `Test Files  13 passed (13)` and `Tests  89 passed (89)`, the count after Task 19.

If the count differs, stop and reconcile with Tasks 15–19 before continuing.

- [ ] **Step 2: Generate input, label, tabs, alert and alert-dialog (network)**

Run from the repo root:
```bash
(cd frontend && npx shadcn@latest add input label tabs alert alert-dialog < /dev/null)
```
`< /dev/null` means no prompt can wait for input.
- `alert-dialog` depends on `button`, and the local `button.tsx` differs from the registry copy (it imports `cn` from `"cn"`). So shadcn either asks "The file button.tsx already exists. Would you like to overwrite?", where the default and the closed-stdin answer are both No, or lists `button.tsx` under "Skipped … (files might be identical, use --overwrite to overwrite)".
- Never pass `--overwrite` or `--force` (F §4.9 item 1).
- The CLI skips npm dependencies that `package.json` already lists (`@base-ui/react` is there), so nothing should be installed.

Expected: the CLI ends by listing the files it created: `alert-dialog.tsx`, `alert.tsx`, `input.tsx`, `label.tsx`, `tabs.tsx` under `src/components/ui`.

Three failure cases:
- **The CLI exits before writing anything** (an aborted prompt): this becomes an **OWNER** step, as in the network case below: the owner runs `cd frontend && npx shadcn@latest add input label tabs alert alert-dialog && git status --short`, answers **No** to every overwrite question, and pastes the `git status --short` output back.
- **The network is unavailable** (`ENOTFOUND`, `fetch failed`, npm `ETIMEDOUT`): this becomes an **OWNER** step. Ask the owner to run the command below in a terminal. It is the same `add` command without `< /dev/null`, plus a `git status`:
  ```bash
  cd frontend && npx shadcn@latest add input label tabs alert alert-dialog && git status --short
  ```
  The owner answers **No** to any overwrite question and pastes the `git status --short` output back.
- **The owner's run also fails:** stop this task.

- [ ] **Step 3: Generate combobox (network; owner Q3 fallback)**

Run:
```bash
(cd frontend && npx shadcn@latest add combobox < /dev/null)
```
Expected: the CLI lists `combobox.tsx` as created, plus any registry dependencies it needed. The expected ones are `input-group.tsx` and `textarea.tsx`, and `button.tsx`/`input.tsx` are skipped or answered No. Network failures are handled exactly as in Step 2.

**Only if** the registry answers that the item does not exist (a message like `The item at https://ui.shadcn.com/r/styles/base-nova/combobox.json was not found.` or `Component combobox not found`), use the owner's Q3 fallback: an accepted, recorded exception to F §4.9 item 1. Create `frontend/src/components/ui/combobox.tsx` with exactly the code below. Do not hand-write it for any other failure.

```tsx
"use client"

// Hand-written thin wrapper over @base-ui/react/combobox: the recorded
// exception to F §4.9.1 that the owner accepted (slice 1a plan, Q3) because
// `npx shadcn@latest add combobox` had no base-nova entry. Replace it with the
// generated component once the registry has one.
import * as React from "react"
import { Combobox as ComboboxPrimitive } from "@base-ui/react/combobox"
import { CheckIcon, ChevronDownIcon } from "lucide-react"

import { cn } from "@/lib/utils"

const Combobox = ComboboxPrimitive.Root

function ComboboxInput({ className, ...props }: ComboboxPrimitive.Input.Props) {
  return (
    <ComboboxPrimitive.Input
      data-slot="combobox-input"
      className={cn(
        "h-8 w-full min-w-0 rounded-lg border border-input bg-transparent px-2.5 py-1 text-base transition-colors outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 md:text-sm dark:bg-input/30",
        className
      )}
      {...props}
    />
  )
}

function ComboboxTrigger({ className, children, ...props }: ComboboxPrimitive.Trigger.Props) {
  return (
    <ComboboxPrimitive.Trigger
      data-slot="combobox-trigger"
      className={cn("flex size-8 items-center justify-center text-muted-foreground", className)}
      {...props}
    >
      {children ?? <ChevronDownIcon className="size-4" />}
    </ComboboxPrimitive.Trigger>
  )
}

function ComboboxContent({
  className,
  side = "bottom",
  sideOffset = 4,
  align = "start",
  ...props
}: ComboboxPrimitive.Popup.Props &
  Pick<ComboboxPrimitive.Positioner.Props, "side" | "sideOffset" | "align">) {
  return (
    <ComboboxPrimitive.Portal>
      <ComboboxPrimitive.Positioner side={side} sideOffset={sideOffset} align={align} className="isolate z-50">
        <ComboboxPrimitive.Popup
          data-slot="combobox-content"
          className={cn(
            "max-h-(--available-height) w-(--anchor-width) min-w-36 overflow-y-auto rounded-lg bg-popover p-1 text-popover-foreground shadow-md ring-1 ring-foreground/10",
            className
          )}
          {...props}
        />
      </ComboboxPrimitive.Positioner>
    </ComboboxPrimitive.Portal>
  )
}

function ComboboxList({ className, ...props }: ComboboxPrimitive.List.Props) {
  return <ComboboxPrimitive.List data-slot="combobox-list" className={cn("outline-none", className)} {...props} />
}

function ComboboxItem({ className, children, ...props }: ComboboxPrimitive.Item.Props) {
  return (
    <ComboboxPrimitive.Item
      data-slot="combobox-item"
      className={cn(
        "relative flex w-full cursor-default items-center gap-2 rounded-md py-1.5 pr-8 pl-2 text-sm outline-none select-none data-disabled:pointer-events-none data-disabled:opacity-50 data-highlighted:bg-accent data-highlighted:text-accent-foreground",
        className
      )}
      {...props}
    >
      {children}
      <ComboboxPrimitive.ItemIndicator className="pointer-events-none absolute right-2 flex size-4 items-center justify-center">
        <CheckIcon className="size-4" />
      </ComboboxPrimitive.ItemIndicator>
    </ComboboxPrimitive.Item>
  )
}

function ComboboxEmpty({ className, ...props }: ComboboxPrimitive.Empty.Props) {
  return (
    <ComboboxPrimitive.Empty
      data-slot="combobox-empty"
      className={cn("px-2 py-1.5 text-sm text-muted-foreground empty:hidden", className)}
      {...props}
    />
  )
}

function ComboboxStatus({ className, ...props }: ComboboxPrimitive.Status.Props) {
  return (
    <ComboboxPrimitive.Status
      data-slot="combobox-status"
      className={cn("px-2 py-1.5 text-xs text-muted-foreground empty:hidden", className)}
      {...props}
    />
  )
}

export {
  Combobox,
  ComboboxContent,
  ComboboxEmpty,
  ComboboxInput,
  ComboboxItem,
  ComboboxList,
  ComboboxStatus,
  ComboboxTrigger,
}
```

This wrapper typechecked and linted clean against `@base-ui/react` 1.8.0. It opened (ArrowDown) and filtered (typing) in jsdom. Base UI's Combobox supports `limit`, which 1b's `TimezoneCombobox` uses for its 50-match cap. The fallback adds no test, because 1b's `timezone-combobox.test.tsx` exercises it, so the counts below hold in both cases.

- [ ] **Step 4: Check and record what was generated**

Run:
```bash
git status --short
git diff --stat
grep -n "md:text-sm" frontend/src/components/ui/input.tsx
grep -c -E "^function (Alert|AlertTitle|AlertDescription)\b" frontend/src/components/ui/alert.tsx
grep -c -E "^function (AlertDialog|AlertDialogContent|AlertDialogHeader|AlertDialogFooter|AlertDialogTitle|AlertDialogDescription|AlertDialogCancel)\b" frontend/src/components/ui/alert-dialog.tsx
(cd frontend && npm run typecheck && npm run lint)
```
Expected:

`git status --short` prints exactly:
```
?? .claude/
?? frontend/src/components/ui/alert-dialog.tsx
?? frontend/src/components/ui/alert.tsx
?? frontend/src/components/ui/combobox.tsx
?? frontend/src/components/ui/input-group.tsx
?? frontend/src/components/ui/input.tsx
?? frontend/src/components/ui/label.tsx
?? frontend/src/components/ui/tabs.tsx
?? frontend/src/components/ui/textarea.tsx
```
The `input-group.tsx` and `textarea.tsx` lines are the expected registry dependencies of `combobox` (UNVERIFIED offline). Whatever `??` lines under `frontend/src/components/ui/` actually appear are the record: write them down for Step 9.

The remaining checks:
- `git diff --stat` prints nothing: no tracked file changed.
- The first `grep` prints one line from `input.tsx` whose class list has `text-base` and `md:text-sm` (F §4.8: iOS does not zoom on focus).
- The two counts are `3` and `7`: every name the kit imports exists as a function.
- `tsc --noEmit` and `eslint` report no errors.

If a tracked file changed:
- `frontend/src/components/ui/*.tsx` (for example `button.tsx`): restore it with `git checkout -- <path>`. That is the same as answering No, and the new files keep importing the local `Button`.
- `frontend/package.json` or `frontend/package-lock.json`: run `git checkout -- frontend/package.json frontend/package-lock.json && (cd frontend && npm ci)`. `@base-ui/react` stays at the Global Constraints' 1.8.0.
- `frontend/src/app/globals.css` or `frontend/components.json`: stop and show the owner `git diff` of that file. Neither is expected to change, because none of these items carries CSS variables or config.

If `typecheck`, `lint` or a count fails on a generated file, stop and report the exact error to the owner. Generated files get no hand edits besides variants (F §4.9 item 1).

- [ ] **Step 5: Write the failing tests**

Create `frontend/src/components/ui/button.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Button } from "./button";

describe("Button", () => {
  it("has a 44 px touch size for primary actions on phones (F §4.8)", () => {
    render(<Button size="touch">Create church</Button>);
    const button = screen.getByRole("button", { name: "Create church" });
    expect(button).toHaveClass("h-11", "px-4");
    expect(button).not.toHaveClass("h-8");
  });
});
```

Create `frontend/src/components/app/pending-button.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { PendingButton } from "./pending-button";

describe("PendingButton", () => {
  it("is disabled and says Saving… while pending", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    const { rerender } = render(
      <PendingButton pending onClick={onClick}>
        Save changes
      </PendingButton>,
    );

    const button = screen.getByRole("button", { name: "Saving…" });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
    expect(screen.queryByText("Save changes")).not.toBeInTheDocument();
    await user.click(button);
    expect(onClick).not.toHaveBeenCalled();

    rerender(
      <PendingButton pending pendingLabel="Creating church…">
        Create church
      </PendingButton>,
    );
    expect(screen.getByRole("button", { name: "Creating church…" })).toBeDisabled();
  });

  it("shows its label and passes Button props through when not pending", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(
      <PendingButton pending={false} type="submit" size="touch" onClick={onClick}>
        Save changes
      </PendingButton>,
    );

    const button = screen.getByRole("button", { name: "Save changes" });
    expect(button).toBeEnabled();
    expect(button).not.toHaveAttribute("aria-busy");
    expect(button).toHaveAttribute("type", "submit");
    expect(button).toHaveClass("h-11");
    await user.click(button);
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});
```

Create `frontend/src/components/app/error-state.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/client";

import { ErrorState } from "./error-state";

describe("ErrorState", () => {
  it("shows the title and the server message, and Retry calls onRetry", async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();
    render(
      <ErrorState
        title="Couldn't load the church"
        error={new ApiError(409, "conflict", "Someone else changed this.")}
        onRetry={onRetry}
      />,
    );

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Couldn't load the church");
    expect(alert).toHaveTextContent("Someone else changed this.");
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
    expect(onRetry).toHaveBeenCalledWith();
  });

  it("says Can't reach the server. for a network error", () => {
    render(
      <ErrorState
        error={new ApiError(0, "network_error", "Can't reach the server. Check your connection and try again.")}
        onRetry={() => {}}
      />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(/^Can't reach the server\.$/);
    expect(screen.getByRole("button", { name: "Retry" })).toBeEnabled();
  });

  it("shows Something went wrong. with the first 8 characters of the request id for a 5xx", () => {
    render(
      <ErrorState
        error={new ApiError(502, "upstream_error", "Bad gateway", { requestId: "0123456789abcdef" })}
        onRetry={() => {}}
      />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(/^Something went wrong\. \(Ref: 01234567\)$/);
  });
});
```

Create `frontend/src/components/app/confirm-dialog.test.tsx`:
```tsx
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { ConfirmDialog } from "./confirm-dialog";

describe("ConfirmDialog", () => {
  it("names the action on the confirm button and calls onConfirm", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    const onOpenChange = vi.fn();
    const props = {
      open: true,
      onOpenChange,
      title: "Delete this service?",
      description: "Sunday, October 5. This can't be undone.",
      confirmLabel: "Delete service",
      onConfirm,
      destructive: true,
    };
    const { rerender } = render(<ConfirmDialog {...props} />);

    const dialog = await screen.findByRole("alertdialog", { name: "Delete this service?" });
    expect(dialog).toHaveAccessibleDescription("Sunday, October 5. This can't be undone.");
    await user.click(within(dialog).getByRole("button", { name: "Delete service" }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onOpenChange).not.toHaveBeenCalled();
    expect(screen.getByRole("alertdialog")).toBeInTheDocument();

    rerender(<ConfirmDialog {...props} pending />);
    expect(within(screen.getByRole("alertdialog")).getByRole("button", { name: "Saving…" })).toBeDisabled();
  });

  it("Cancel closes the dialog without confirming", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    const openChanges: boolean[] = [];
    function Harness() {
      const [open, setOpen] = useState(true);
      return (
        <ConfirmDialog
          open={open}
          onOpenChange={(next) => {
            openChanges.push(next);
            setOpen(next);
          }}
          title="Remove Ann from Grace Church?"
          confirmLabel="Remove member"
          onConfirm={onConfirm}
          destructive
        />
      );
    }
    render(<Harness />);

    const dialog = await screen.findByRole("alertdialog", { name: "Remove Ann from Grace Church?" });
    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument());
    expect(openChanges).toEqual([false]);
    expect(onConfirm).not.toHaveBeenCalled();
  });
});
```

Create `frontend/src/components/app/empty-state.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import { InboxIcon } from "lucide-react";
import { describe, expect, it } from "vitest";

import { Button } from "@/components/ui/button";

import { EmptyState } from "./empty-state";

describe("EmptyState", () => {
  it("shows the icon, a one-line title, one sentence and the primary action", () => {
    const { container } = render(
      <EmptyState
        icon={InboxIcon}
        title="No services yet"
        description="Plan your first service to see it here."
        action={<Button size="touch">Plan a service</Button>}
      />,
    );

    expect(screen.getByRole("heading", { level: 2, name: "No services yet" })).toBeInTheDocument();
    expect(screen.getByText("Plan your first service to see it here.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Plan a service" })).toBeInTheDocument();
    expect(container.querySelector("svg[aria-hidden='true']")).not.toBeNull();
  });
});
```

Create `frontend/src/components/app/page-header.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Button } from "@/components/ui/button";

import { PageHeader } from "./page-header";

describe("PageHeader", () => {
  it("renders the title as the page h1 with its description and actions", () => {
    const { rerender } = render(
      <PageHeader
        title="Services"
        description="Everything planned for Grace Church."
        actions={<Button>New service</Button>}
      />,
    );

    expect(screen.getByRole("heading", { level: 1, name: "Services" })).toBeInTheDocument();
    expect(screen.getByText("Everything planned for Grace Church.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "New service" })).toBeInTheDocument();

    rerender(<PageHeader title="Home" />);
    expect(screen.getByRole("heading", { level: 1, name: "Home" })).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 6: Run the tests to see them fail**

Run:
```bash
(cd frontend && npx vitest run src/components 2>&1 | grep -E "FAIL|Failed to resolve import|toHaveClass|Test Files|Tests ")
```
Expected:
- Each of the five `src/components/app/*.test.tsx` files fails with `Error: Failed to resolve import "./<name>" from "src/components/app/<name>.test.tsx". Does the file exist?`, where `<name>` is `confirm-dialog`, `empty-state`, `error-state`, `page-header` or `pending-button`.
- `src/components/ui/button.test.tsx > Button > has a 44 px touch size …` fails on `expect(element).toHaveClass("h-11 px-4")`: the received classes have neither class, because `cva` adds no size classes for an unknown `size`.
- Totals: `Test Files  6 failed (6)`, `Tests  1 failed (1)`. Files that fail to import collect no tests.

- [ ] **Step 7: Add the `touch` size to `button.tsx`**

In `frontend/src/components/ui/button.tsx`, replace:
```tsx
        lg: "h-9 gap-1.5 px-2.5 has-data-[icon=inline-end]:pr-2 has-data-[icon=inline-start]:pl-2",
        icon: "size-8",
```
with:
```tsx
        lg: "h-9 gap-1.5 px-2.5 has-data-[icon=inline-end]:pr-2 has-data-[icon=inline-start]:pl-2",
        touch:
          "h-11 gap-1.5 px-4 has-data-[icon=inline-end]:pr-3.5 has-data-[icon=inline-start]:pl-3.5",
        icon: "size-8",
```
Nothing else in the file changes, and this is the task's only edit to a generated file (F §4.9 item 1).

- [ ] **Step 8: Create the five kit components**

Create `frontend/src/components/app/pending-button.tsx`:
```tsx
import { Loader2Icon } from "lucide-react";
import type { ComponentProps } from "react";

import { Button } from "@/components/ui/button";

export type PendingButtonProps = ComponentProps<typeof Button> & {
  /** True while the mutation is in flight: the button is disabled and shows pendingLabel. */
  pending: boolean;
  pendingLabel?: string;
};

/** F §4.8 "Mutation in flight": disabled, label changes to "Saving…"; the rest of the page stays usable. */
export function PendingButton({
  pending,
  pendingLabel = "Saving…",
  disabled,
  children,
  ...props
}: PendingButtonProps) {
  return (
    <Button {...props} disabled={pending || disabled} aria-busy={pending || undefined}>
      {pending ? (
        <>
          <Loader2Icon data-icon="inline-start" className="animate-spin" aria-hidden="true" />
          {pendingLabel}
        </>
      ) : (
        children
      )}
    </Button>
  );
}
```

Create `frontend/src/components/app/error-state.tsx`:
```tsx
import { CircleAlertIcon } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { describeError } from "@/lib/api/errors";

export type ErrorStateProps = {
  /** The failed query's error; describeError picks the sentence (F §4.8, ops handoff Ref). */
  error: unknown;
  /** Usually the query's refetch; called with no arguments. */
  onRetry: () => void;
  /** Optional heading above the sentence. */
  title?: string;
};

/** F §4.8 "Query failed": the message inline with a Retry button. An error is never shown as empty. */
export function ErrorState({ error, onRetry, title }: ErrorStateProps) {
  const message = describeError(error);
  return (
    <div data-slot="error-state" className="flex flex-col items-start gap-3">
      <Alert variant="destructive">
        <CircleAlertIcon aria-hidden="true" />
        {title ? (
          <>
            <AlertTitle>{title}</AlertTitle>
            <AlertDescription>{message}</AlertDescription>
          </>
        ) : (
          <AlertTitle>{message}</AlertTitle>
        )}
      </Alert>
      <Button variant="outline" size="touch" onClick={() => onRetry()}>
        Retry
      </Button>
    </div>
  );
}
```

Create `frontend/src/components/app/confirm-dialog.tsx`:
```tsx
"use client";

import { PendingButton } from "@/components/app/pending-button";
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

export type ConfirmDialogProps = {
  open: boolean;
  onOpenChange(open: boolean): void;
  title: string;
  description?: string;
  /** Names the action ("Delete service"), never "OK" (F §4.8). */
  confirmLabel: string;
  onConfirm(): void;
  /** While true the confirm button is a disabled "Saving…"; the caller closes the dialog on success. */
  pending?: boolean;
  destructive?: boolean;
};

/**
 * F §4.8 "Destructive or lossy action": a Base UI AlertDialog, controlled with
 * open/onOpenChange (F §4.9 item 6). Confirm is a PendingButton rather than
 * AlertDialogAction so the dialog stays open while the mutation runs.
 */
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel,
  onConfirm,
  pending = false,
  destructive = false,
}: ConfirmDialogProps) {
  return (
    <AlertDialog open={open} onOpenChange={(next) => onOpenChange(next)}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          {description ? <AlertDialogDescription>{description}</AlertDialogDescription> : null}
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <PendingButton
            pending={pending}
            variant={destructive ? "destructive" : "default"}
            onClick={() => onConfirm()}
          >
            {confirmLabel}
          </PendingButton>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
```

Create `frontend/src/components/app/empty-state.tsx`:
```tsx
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

export type EmptyStateProps = {
  icon?: LucideIcon;
  /** One line. */
  title: string;
  /** One sentence. */
  description: string;
  /** The primary action, usually a size="touch" Button. */
  action?: ReactNode;
};

/** F §4.8 "Empty collection": icon, one-line title, one sentence, a primary action. */
export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div
      data-slot="empty-state"
      className="flex flex-col items-center gap-2 rounded-lg border border-dashed px-4 py-10 text-center"
    >
      {Icon ? <Icon className="size-8 text-muted-foreground" aria-hidden="true" /> : null}
      <h2 className="text-base font-medium">{title}</h2>
      <p className="max-w-sm text-sm text-muted-foreground">{description}</p>
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}
```

Create `frontend/src/components/app/page-header.tsx`:
```tsx
import type { ReactNode } from "react";

export type PageHeaderProps = {
  title: string;
  description?: string;
  actions?: ReactNode;
};

/** The page's h1, an optional one-line description and the page actions (stacked on phones). */
export function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <div data-slot="page-header" className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0">
        <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
        {description ? <p className="mt-1 text-sm text-muted-foreground">{description}</p> : null}
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap gap-2">{actions}</div> : null}
    </div>
  );
}
```

- [ ] **Step 9: Run the tests and the frontend check**

Run:
```bash
(cd frontend && npx vitest run src/components 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests " && npm run typecheck && npm run lint)
git diff --stat
git status --short
```
Expected:
- The first run prints `Test Files  6 passed (6)` and `Tests  10 passed (10)`.
- The full check prints `Test Files  19 passed (19)` and `Tests  99 passed (99)` (89 + 10), and `tsc --noEmit` and `eslint` report no errors.
- `git diff --stat` prints only `frontend/src/components/ui/button.tsx | 2 ++` (`1 file changed, 2 insertions(+)`).
- `git status --short` prints ` M frontend/src/components/ui/button.tsx`, the Step 4 `??` lines, and the eleven new `frontend/src/components/app/*.tsx` and `frontend/src/components/ui/button.test.tsx` files. Git may collapse the new directory to `?? frontend/src/components/app/`.

If only the `ConfirmDialog` tests fail, look at the generated `alert-dialog.tsx`. Its `AlertDialogCancel` must be a Base UI `Close`, and `AlertDialogContent` must render the portal and popup. Do not edit the generated file; report its exports and the failure to the owner instead.

- [ ] **Step 10: Commit**

Stage the Step 4 list by name. The command below is for the expected list; if Step 4 recorded a different set of `??` files under `frontend/src/components/ui/`, stage exactly that set instead of the eight generated paths shown.
```bash
git add frontend/src/components/ui/button.tsx frontend/src/components/ui/button.test.tsx \
        frontend/src/components/ui/alert-dialog.tsx frontend/src/components/ui/alert.tsx \
        frontend/src/components/ui/combobox.tsx frontend/src/components/ui/input-group.tsx \
        frontend/src/components/ui/input.tsx frontend/src/components/ui/label.tsx \
        frontend/src/components/ui/tabs.tsx frontend/src/components/ui/textarea.tsx \
        frontend/src/components/app/confirm-dialog.tsx frontend/src/components/app/confirm-dialog.test.tsx \
        frontend/src/components/app/empty-state.tsx frontend/src/components/app/empty-state.test.tsx \
        frontend/src/components/app/error-state.tsx frontend/src/components/app/error-state.test.tsx \
        frontend/src/components/app/page-header.tsx frontend/src/components/app/page-header.test.tsx \
        frontend/src/components/app/pending-button.tsx frontend/src/components/app/pending-button.test.tsx
git status --short
git commit -m "Frontend: UI kit, generated Base UI components and the touch button size (F §4.8, §4.9)

npx shadcn@latest add input label tabs alert alert-dialog combobox
generates the base-nova components 1a and 1b use, without overwriting
any existing file. Button gains size touch (h-11 px-4) for primary
actions on phones. components/app adds EmptyState, ErrorState
(describeError and Retry), PendingButton (disabled, Saving…),
ConfirmDialog (AlertDialog whose confirm button names the action and
stays open while pending) and PageHeader.

Generated: alert-dialog.tsx alert.tsx combobox.tsx input-group.tsx input.tsx label.tsx tabs.tsx textarea.tsx

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
The `Generated:` line lists exactly the `??` files that Step 4 recorded under `frontend/src/components/ui/`. With the Step 3 fallback, it reads `combobox.tsx hand-written (owner Q3 exception to F §4.9.1)` instead of naming `combobox.tsx` as generated. Task 25 reads this line (`git log --grep "UI kit" --format=%B`) to adjust §3's expected path list. With the expected set, §3 gains `frontend/src/components/ui/input-group.tsx` and `frontend/src/components/ui/textarea.tsx`.

Expected `git status --short` before the commit (plus `?? .claude/`):
```
A  frontend/src/components/app/confirm-dialog.test.tsx
A  frontend/src/components/app/confirm-dialog.tsx
A  frontend/src/components/app/empty-state.test.tsx
A  frontend/src/components/app/empty-state.tsx
A  frontend/src/components/app/error-state.test.tsx
A  frontend/src/components/app/error-state.tsx
A  frontend/src/components/app/page-header.test.tsx
A  frontend/src/components/app/page-header.tsx
A  frontend/src/components/app/pending-button.test.tsx
A  frontend/src/components/app/pending-button.tsx
A  frontend/src/components/ui/alert-dialog.tsx
A  frontend/src/components/ui/alert.tsx
A  frontend/src/components/ui/button.test.tsx
M  frontend/src/components/ui/button.tsx
A  frontend/src/components/ui/combobox.tsx
A  frontend/src/components/ui/input-group.tsx
A  frontend/src/components/ui/input.tsx
A  frontend/src/components/ui/label.tsx
A  frontend/src/components/ui/tabs.tsx
A  frontend/src/components/ui/textarea.tsx
```

Tests after this task: backend `692 passed, 5 skipped` (unchanged since Task 16); frontend `99 passed` (19 files).

---

### Task 21: `AppHeader`, `ChurchSwitcher`, `AccountMenu` (F §4.2, §4.9 item 4; S A5, A6; AC12 1a part)

The header moves to `src/components/app/` (F §4.11) and splits into three presentational components. None of them reads a context or a query: the `(church)` layout (Task 23) passes the user, `me.churches`, the church being confirmed or confirmed, a select callback and the sign-out callback, and the stub `/welcome` (Task 22) passes only the user and the sign-out callback. That is why `useSignOut` never needs `useChurch()` (notes C14) and why these tests use plain `render`, not `renderWithProviders`.

- **`ChurchSwitcher`** (S A5, Flow C; F §4.9 item 4): a `DropdownMenu` whose content is a `DropdownMenuGroup` labelled **"Your churches"** holding a `DropdownMenuRadioGroup` with one `DropdownMenuRadioItem` per church. Values are church **ids**, never names (the Streamlit selectbox keyed by name is inv A5's bug), and each row shows the role in muted text (`roleLabel`), so two churches with the same name are told apart and each is selectable. It is shown whenever the header has at least one church (not Streamlit's ≥2). Radio items pass `closeOnClick` (Base UI's `Menu.RadioItem` defaults to `false`), so choosing a church closes the menu; choosing the church that is already active does not call `onSelect` (Base UI fires `onValueChange` only on a change). The trigger's accessible name is `Active church: {name}` (or "Choose a church" when `activeId` matches none), and its visible text is the church name. 1b adds a separator and **"Join or create a church…"** → `/welcome` below the group; 1a has no such item.
- **`AccountMenu`** (S A6): the Avatar trigger (`aria-label="Account menu"`) keeps slice 0's avatar and initial; its `DropdownMenuGroup > DropdownMenuLabel` shows the name (or the email when there is no name), the email and, when a role is given, `Role: {roleLabel(role)}` (slice 0 printed the raw `role`); then a separator and **"Log out"**. F §4.2's "Settings" item arrives with the Settings slice, not here. The item calls `onSignOut()` with no arguments, so the click event never reaches Task 19's `useSignOut(opts)`.
- **`AppHeader`**: the switcher when both `churches` (non-empty) and `onSelectChurch` are given, otherwise the app name **"Worship Service Builder"** on the left (S Flow A step 2: "app name on the left, account menu … on the right"); the account menu always, so every signed-in screen can log out (S A6, change 20). The role shown is `active?.role`.
- Both triggers are 44 px tall for touch (F §4.8): the switcher uses Task 20's `buttonVariants({ variant: "ghost", size: "touch" })`, the avatar trigger is `size-11` around the `size-9` avatar. The header's vertical padding drops from `py-3` to `py-2` to keep its height close to slice 0's.

The old `src/components/app-header.tsx` (a Base UI `Select`, `onSelectChurch(church: Church)`) stays untouched: `src/app/page.tsx` still imports it, and Task 23 deletes both in one commit. `src/components/ui/select.tsx` stays (generated; unused after Task 23).

Verified before writing (throwaway worktree, jsdom 29.1.1, `@testing-library/react` 16.3.2, Base UI 1.8.0, the Task 15 shims): the four tests below pass, and they fail with the unresolved import before the components exist; `tsc --noEmit` and `eslint` are clean on the three components. `@testing-library/user-event` and `@testing-library/jest-dom` were not in the offline npm cache, so there the clicks were driven by `fireEvent` (pointerdown, mousedown, pointerup, mouseup, click), which is the sequence `user.click` dispatches; the menus opened, the radio items reported `aria-checked`, and `closeOnClick` closed the menu after a choice.

**Files:**
- Create: `frontend/src/components/app/church-switcher.tsx`
- Create: `frontend/src/components/app/account-menu.tsx`
- Create: `frontend/src/components/app/app-header.tsx`
- Test: `frontend/src/components/app/app-header.test.tsx` (4 tests, new; Vitest `dom` project)
- Unchanged on purpose: `frontend/src/components/app-header.tsx`, `frontend/src/app/page.tsx` (both deleted in Task 23), `frontend/src/components/ui/dropdown-menu.tsx`, `frontend/src/components/ui/avatar.tsx` (generated; no hand edits, F §4.9)

**Interfaces:**
- Consumes:
  - Task 15: the Vitest `dom` project (jsdom, `src/**/*.test.tsx`, setupFiles `src/test/setup-dom.ts` with `@testing-library/jest-dom/vitest`, `cleanup` after each test and the Base UI shims `PointerEvent`, `ResizeObserver`, `matchMedia`, `scrollIntoView`, `hasPointerCapture`/`releasePointerCapture`, `getAnimations = () => []`); the dev dependencies `@testing-library/react` and `@testing-library/user-event`.
  - Task 17: `@/lib/church` exports `type Church` (= `components["schemas"]["ChurchOut"]`, `role: "owner" | "admin" | "member"` from Task 3's `Literal`), `type Me` (= `components["schemas"]["MeOut"]`, so `Me["user"]` is `{ id: string; email: string; name?: string | null; picture?: string | null }`) and `roleLabel(role: Church["role"]): "Owner" | "Admin" | "Member"`.
  - Task 20: `buttonVariants` from `@/components/ui/button` with `size: "touch"` (`h-11 px-4` plus the default size's gap and icon classes).
  - Existing: `@/components/ui/dropdown-menu` (`DropdownMenu`, `DropdownMenuTrigger`, `DropdownMenuContent` (props `align`, `className`), `DropdownMenuGroup`, `DropdownMenuLabel`, `DropdownMenuRadioGroup`, `DropdownMenuRadioItem`, `DropdownMenuItem`, `DropdownMenuSeparator`; radio parts at `:181-221`); `@/components/ui/avatar` (`Avatar`, `AvatarImage`, `AvatarFallback`); `cn` from `@/lib/utils` (re-exports the `cn` package: class merging with Tailwind conflict resolution, so `w-auto min-w-56` replaces the content's `w-(--anchor-width) min-w-32`); `ChevronsUpDownIcon` from `lucide-react`.
- Produces:
  - `frontend/src/components/app/church-switcher.tsx`: `export function ChurchSwitcher({ churches, activeId, onSelect }: { churches: Church[]; activeId: string | null; onSelect: (id: string) => void }): JSX.Element`. Trigger: a `<button>` named `Active church: {name}` (or `Choose a church`); menu: `role="menu"` containing a `role="group"` named "Your churches" and one `role="menuitemradio"` per church named `{name} {roleLabel}` (e.g. "Grace Admin"), `aria-checked="true"` on `activeId`. Later users: `AppHeader`; 1b adds the "Join or create a church…" item after the group.
  - `frontend/src/components/app/account-menu.tsx`: `export function AccountMenu({ user, role, onSignOut }: { user: Me["user"]; role?: Church["role"]; onSignOut: () => void }): JSX.Element`. Trigger `<button aria-label="Account menu">`; menu: group label with name, email and `Role: {Owner|Admin|Member}` (when `role`), separator, `role="menuitem"` "Log out" → `onSignOut()`.
  - `frontend/src/components/app/app-header.tsx`: `export function AppHeader({ user, churches, active, onSelectChurch, onSignOut }: { user: Me["user"]; churches?: Church[]; active?: Church | null; onSelectChurch?: (id: string) => void; onSignOut: () => void }): JSX.Element`. Switcher only when `churches` is non-empty and `onSelectChurch` is given (else the text "Worship Service Builder"); the switcher's `activeId` is `active?.id ?? null`, and the account menu's role is `active?.role`. Later users: Task 22 (stub `/welcome`: `<AppHeader user={me.user} onSignOut={() => void signOut()} />`), Task 23 (`(church)` layout: `<AppHeader user={me.user} churches={me.churches} active={…} onSelectChurch={…} onSignOut={…} />`, where `active` is the candidate while `GET /church` confirms it and the confirmed profile afterwards; the candidate always comes from `me.churches`, so the trigger finds its name there), 1b's `/welcome` (no switcher).

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/components/app/app-header.test.tsx`:

```tsx
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AppHeader } from "@/components/app/app-header";
import type { Church, Me } from "@/lib/church";

const pat: Me["user"] = { id: "u-1", email: "pat@example.com", name: "Pat Doe", picture: null };
// Two churches with the same name: only the id (and the role shown) tells them apart.
const graceAdmin: Church = { id: "c-admin", name: "Grace", role: "admin" };
const graceMember: Church = { id: "c-member", name: "Grace", role: "member" };

describe("AppHeader", () => {
  it("lists same-name churches by id with their roles, and either one can be chosen", async () => {
    const onSelectChurch = vi.fn();
    const header = (active: Church) => (
      <AppHeader
        user={pat}
        churches={[graceAdmin, graceMember]}
        active={active}
        onSelectChurch={onSelectChurch}
        onSignOut={vi.fn()}
      />
    );
    const { rerender } = render(header(graceAdmin));
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Active church: Grace" }));
    const menu = await screen.findByRole("menu");
    expect(within(menu).getByRole("group", { name: "Your churches" })).toBeInTheDocument();
    expect(within(menu).getByRole("menuitemradio", { name: "Grace Admin" })).toHaveAttribute("aria-checked", "true");
    expect(within(menu).getByRole("menuitemradio", { name: "Grace Member" })).toHaveAttribute("aria-checked", "false");
    await user.click(within(menu).getByRole("menuitemradio", { name: "Grace Member" }));
    expect(onSelectChurch).toHaveBeenLastCalledWith("c-member");

    // The layout stores the new id and re-renders with it as the active church.
    rerender(header(graceMember));
    await user.click(screen.getByRole("button", { name: "Active church: Grace" }));
    expect(await screen.findByRole("menuitemradio", { name: "Grace Member" })).toHaveAttribute("aria-checked", "true");
    await user.click(screen.getByRole("menuitemradio", { name: "Grace Admin" }));
    expect(onSelectChurch).toHaveBeenLastCalledWith("c-admin");
    expect(onSelectChurch).toHaveBeenCalledTimes(2);
  });

  it("shows the user's name, email and role label in the account menu", async () => {
    render(
      <AppHeader
        user={pat}
        churches={[graceAdmin]}
        active={graceAdmin}
        onSelectChurch={vi.fn()}
        onSignOut={vi.fn()}
      />,
    );
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Account menu" }));
    const menu = await screen.findByRole("menu");
    expect(within(menu).getByText("Pat Doe")).toBeInTheDocument();
    expect(within(menu).getByText("pat@example.com")).toBeInTheDocument();
    expect(within(menu).getByText("Role: Admin")).toBeInTheDocument();
  });

  it("calls onSignOut from Log out", async () => {
    const onSignOut = vi.fn();
    render(
      <AppHeader
        user={pat}
        churches={[graceAdmin]}
        active={graceAdmin}
        onSelectChurch={vi.fn()}
        onSignOut={onSignOut}
      />,
    );
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Account menu" }));
    await user.click(await screen.findByRole("menuitem", { name: "Log out" }));
    expect(onSignOut).toHaveBeenCalledTimes(1);
  });

  it("shows the app name and no switcher without churches, and still offers Log out", async () => {
    const onSignOut = vi.fn();
    render(<AppHeader user={pat} onSignOut={onSignOut} />);
    const user = userEvent.setup();

    expect(screen.getByText("Worship Service Builder")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /church/i })).toBeNull();
    await user.click(screen.getByRole("button", { name: "Account menu" }));
    const menu = await screen.findByRole("menu");
    expect(within(menu).queryByText(/^Role:/)).toBeNull();
    await user.click(within(menu).getByRole("menuitem", { name: "Log out" }));
    expect(onSignOut).toHaveBeenCalledTimes(1);
  });
});
```

The first test is the "keyed by id" check: with name-keyed values both rows would share one value, both would report `aria-checked="true"`, and choosing "Grace Member" would pass "Grace" instead of `c-member`.

- [ ] **Step 2: Run the tests to verify they fail**

Run:
```bash
(cd frontend && npx vitest run src/components/app/app-header.test.tsx 2>&1 | grep -E "Error|Test Files|Tests ")
```
Expected: FAIL — `Error: Failed to resolve import "@/components/app/app-header" from "src/components/app/app-header.test.tsx". Does the file exist?`, `Test Files  1 failed (1)`, `Tests  no tests`.

- [ ] **Step 3: Create `frontend/src/components/app/church-switcher.tsx`**

```tsx
"use client";

import { ChevronsUpDownIcon } from "lucide-react";

import { buttonVariants } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { roleLabel, type Church } from "@/lib/church";
import { cn } from "@/lib/utils";

type Props = {
  churches: Church[];
  activeId: string | null;
  onSelect: (id: string) => void;
};

/**
 * The header's church menu (S Flow C, F §4.9 item 4): a radio list keyed and
 * selected by id, each row showing the role so same-name churches differ.
 * Slice 1b adds a separator and "Join or create a church…" below the group.
 */
export function ChurchSwitcher({ churches, activeId, onSelect }: Props) {
  const active = churches.find((c) => c.id === activeId) ?? null;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label={active ? `Active church: ${active.name}` : "Choose a church"}
        className={cn(
          buttonVariants({ variant: "ghost", size: "touch" }),
          "max-w-full justify-start px-2 font-semibold",
        )}
      >
        <span className="min-w-0 truncate">{active?.name ?? "Choose a church"}</span>
        <ChevronsUpDownIcon aria-hidden className="text-muted-foreground" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-auto min-w-56">
        <DropdownMenuGroup>
          <DropdownMenuLabel>Your churches</DropdownMenuLabel>
          <DropdownMenuRadioGroup
            value={activeId}
            onValueChange={(id: string) => onSelect(id)}
          >
            {churches.map((c) => (
              <DropdownMenuRadioItem key={c.id} value={c.id} label={c.name} closeOnClick>
                <span className="min-w-0 flex-1 truncate">{c.name}</span>{" "}
                <span className="text-xs text-muted-foreground">{roleLabel(c.role)}</span>
              </DropdownMenuRadioItem>
            ))}
          </DropdownMenuRadioGroup>
        </DropdownMenuGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

`label={c.name}` makes keyboard type-ahead match the name, not "Grace Admin". The literal `{" "}` puts a space into the accessible name ("Grace Admin", not "GraceAdmin"); inside the flex row it takes no space. `onValueChange` is wrapped so Base UI's second argument (event details) never reaches `onSelect`.

- [ ] **Step 4: Create `frontend/src/components/app/account-menu.tsx`**

```tsx
"use client";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { roleLabel, type Church, type Me } from "@/lib/church";

type Props = {
  user: Me["user"];
  role?: Church["role"];
  onSignOut: () => void;
};

/** Avatar menu: who is signed in, their role in the active church, and Log out (S A6). */
export function AccountMenu({ user, role, onSignOut }: Props) {
  const displayName = user.name ?? user.email;
  const initial = displayName.slice(0, 1).toUpperCase();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label="Account menu"
        className="flex size-11 shrink-0 items-center justify-center rounded-full outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <Avatar className="size-9">
          {user.picture && <AvatarImage src={user.picture} alt="" />}
          <AvatarFallback>{initial}</AvatarFallback>
        </Avatar>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-auto min-w-56">
        <DropdownMenuGroup>
          <DropdownMenuLabel className="font-normal">
            <div className="text-sm font-medium text-foreground">{displayName}</div>
            <div className="text-xs text-muted-foreground">{user.email}</div>
            {role && <div className="text-xs text-muted-foreground">{`Role: ${roleLabel(role)}`}</div>}
          </DropdownMenuLabel>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => onSignOut()}>Log out</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

- [ ] **Step 5: Create `frontend/src/components/app/app-header.tsx`**

```tsx
"use client";

import { AccountMenu } from "@/components/app/account-menu";
import { ChurchSwitcher } from "@/components/app/church-switcher";
import type { Church, Me } from "@/lib/church";

type Props = {
  user: Me["user"];
  churches?: Church[];
  active?: Church | null;
  onSelectChurch?: (id: string) => void;
  onSignOut: () => void;
};

/**
 * The signed-in header (F §4.2). With `churches` and `onSelectChurch` it shows
 * the church switcher; without them (the `/welcome` stub) it shows the app name.
 * The account menu is always there, so every signed-in screen can log out (S A6).
 */
export function AppHeader({ user, churches, active = null, onSelectChurch, onSignOut }: Props) {
  const showSwitcher = churches !== undefined && churches.length > 0 && onSelectChurch !== undefined;

  return (
    <header className="sticky top-0 z-10 border-b bg-background/95 backdrop-blur">
      <div className="mx-auto flex max-w-3xl items-center gap-3 px-4 py-2">
        <div className="min-w-0 flex-1">
          {showSwitcher ? (
            <ChurchSwitcher churches={churches} activeId={active?.id ?? null} onSelect={onSelectChurch} />
          ) : (
            <span className="font-semibold">Worship Service Builder</span>
          )}
        </div>
        <AccountMenu user={user} role={active?.role} onSignOut={onSignOut} />
      </div>
    </header>
  );
}
```

TypeScript narrows `churches` and `onSelectChurch` through the `const showSwitcher` condition (aliased-condition narrowing), so no non-null assertions are needed.

- [ ] **Step 6: Run the tests, the frontend check and the backend suite**

Run:
```bash
(cd frontend && npx vitest run src/components/app/app-header.test.tsx 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests " && npm run typecheck && npm run lint)
.venv/bin/python -m pytest -q | tail -1
git status --short
```
Expected: `Test Files  1 passed (1)` and `Tests  4 passed (4)`; then `Test Files  20 passed (20)` and `Tests  103 passed (103)` (99 after Task 20 + 4), `tsc --noEmit` and `eslint` report no errors; then `692 passed, 5 skipped` (no backend change since Task 16). `git status --short` lists exactly (plus `?? .claude/`):

```
?? frontend/src/components/app/account-menu.tsx
?? frontend/src/components/app/app-header.test.tsx
?? frontend/src/components/app/app-header.tsx
?? frontend/src/components/app/church-switcher.tsx
```

If a `findByRole("menu")` times out, the menu never opened: check that `src/test/setup-dom.ts` (Task 15) defines the `PointerEvent` shim and `Element.prototype.getAnimations = () => []`, and that the test file is in the `dom` project (`.test.tsx`), not the node `unit` project. If `typecheck` reports `Type '"touch"' is not assignable`, Task 20's `touch` size is missing from `button.tsx`; add it there (Task 20's step), not here.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/app/church-switcher.tsx frontend/src/components/app/account-menu.tsx \
        frontend/src/components/app/app-header.tsx frontend/src/components/app/app-header.test.tsx
git status --short
git commit -m "Frontend: AppHeader with a church menu keyed by id and an account menu (F §4.2, §4.9 item 4; S A5, A6)

The header moves to components/app and splits into ChurchSwitcher and
AccountMenu. The switcher is a DropdownMenu with a \"Your churches\" radio
group keyed by church id, each row showing the role, so same-name churches
stay distinct; it shows with one church or more. The account menu shows the
name, email and role label, and Log out. Without churches the header shows
the app name, for the /welcome stub. The old components/app-header.tsx goes
with src/app/page.tsx in Task 23.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

The `git status --short` before the commit prints exactly (plus `?? .claude/`):

```
A  frontend/src/components/app/account-menu.tsx
A  frontend/src/components/app/app-header.test.tsx
A  frontend/src/components/app/app-header.tsx
A  frontend/src/components/app/church-switcher.tsx
```

Tests after this task: backend `692 passed, 5 skipped`; frontend `103 passed`.

---

### Task 22: `(signed-in)` layout, stub `/welcome` (F §4.1, §4.2, §4.4; S Layouts, stub; AC12 last sentence, AC14 1a part)

The `(signed-in)` route group gets its layout (F §4.1 folder layout; S "Layouts (1a)"): it loads `/me` with Task 18's `useMe`, shows the shell skeleton until it arrives, shows a full-page `ErrorState` with **Retry** when the first load fails with anything but a 401, and hands `/me` to every page below it through Task 19's `MeProvider` (`useMeContext()`; slice 2 uses it for the draft key and pruning). It is also the one subscriber to `authEvents.onSignOutRequired`: a 401 anywhere (Task 18's `handleAuthErrors` emits the event) becomes one local sign-out that keeps a pending invite and passes the current path as `next` (S Flow D "Session expired"; 1b's `/login` reads it, clarification 16). While the signing-out flag of `lib/auth.ts` is set (Global Constraints "Sign-out"; critique 8), the layout renders the skeleton and disables `/me`, which unmounts the `(church)` subtree (Task 23) and its `ChurchProvider`, so nothing refetches the cleared cache or stores a church again during the sign-out.

`/welcome` is the 1a stub (S file map): `AppHeader` without the switcher (Task 21's no-switcher mode) plus the slice-0 card "No church yet" / "Creating or joining a church is coming in the next update." (moved from `src/app/page.tsx:104-111`), so the `(church)` layout's zero-church redirect (Task 23) never lands on a 404 between the 1a and 1b merges (AC12 last sentence), and a zero-church user can log out (S behavior change 20, inv A6). Slice 1b replaces the page with the Join / Create tabs.

Decisions recorded here (the spec leaves them open):
- **A failed background refetch keeps the loaded shell.** The layout renders the children whenever `/me` data exists, and shows `ErrorState` only when there is no data yet. `refetchOnWindowFocus: true` (Task 18) would otherwise swap a working page, with its unsaved form state, for a full-page error after one network blip.
- **A 401 renders the skeleton, never `ErrorState`.** `handleAuthErrors` has already started the sign-out; showing "Please sign in." with a Retry button for the few milliseconds before the flag flips would flash.
- **The skeleton is `role="status"` with `aria-label="Loading"`**, so tests find it by role and name. It stays private to `layout.tsx`: a Next layout file exports only its default component and route config.
- **`/welcome` has no `metadata`.** A `"use client"` page cannot export it (`generate-metadata.md:110`), and a server wrapper would add a file to §3's list for a page that 1b replaces. The root title "Worship Service Builder" applies.
- **`/welcome` shows the stub card to every signed-in user.** In 1a nothing links there except Task 23's zero-church redirect (the switcher's "Join or create a church…" item is 1b), so a user with churches only sees it by typing the URL.

The `/welcome` test renders the page **inside the real layout** with a zero-church `/me`, not through `renderWithProviders`' `me` option. It then checks the composition Task 23's redirect relies on (layout → `MeProvider` → stub → header → Log out) and that Log out triggers no further `/me` request.

**Files:**
- Create: `frontend/src/app/(signed-in)/layout.tsx`
- Create: `frontend/src/app/(signed-in)/welcome/page.tsx`
- Test: `frontend/src/app/(signed-in)/signed-in-layout.test.tsx` (3, new), `frontend/src/app/(signed-in)/welcome/welcome.test.tsx` (1, new)

Every shell command that names one of these paths **quotes it**: zsh treats unquoted `(signed-in)` as glob grouping and fails with `no matches found`. The Vitest filter `signed-in` matches both test files (and no other file at this point) without parentheses.

**Interfaces:**
- Consumes:
  - Task 15: `installFakeApi(handlers: Record<string, FakeHandler>): FakeApi` (routes `"METHOD /path"`; a non-function handler is a 200 JSON body; `api.set(route, handler)`; `api.requests: RecordedRequest[]` with case-insensitive `headers`), `fakeError(status, code, message, extra?)` (default `request_id` `FAKE_REQUEST_ID = "4f9a2c1e8b7d4e6fa0c3b5d7e9f1a2b4"`, so "(Ref: 4f9a2c1e)") from `@/test/fake-api`; `me(overrides?: Partial<Me>): Me` (default user email `pat@example.com`, churches `[Grace]`) from `@/test/fixtures`; `testRouter.replace: Mock`, `supabaseAuth.signOut: Mock`, `TEST_ACCESS_TOKEN = "test-access-token"` from `@/test/mocks`. `setup-dom.ts` runs `resetTestMocks()` before each DOM test (path `/`, `getSession` resolves a session with `TEST_ACCESS_TOKEN`, `signOut` resolves `{ error: null }`) and clears both storages after each; Tasks 17 and 18 add `resetStoredChurchIdForTests()` and `resetSigningOutForTests()` to its `afterEach`.
  - Task 16: `ApiError` (class with `status: number`) from `@/lib/api/client`; `describeError` (used inside `ErrorState`: status ≥ 500 → "Something went wrong. (Ref: <first 8 chars of requestId>)").
  - Task 18: `useMe(opts?: { enabled?: boolean }): UseQueryResult<Me, ApiError>` from `@/lib/queries/me`; `authEvents.onSignOutRequired(cb: () => void): () => void` from `@/lib/queries/auth-events` (the `authEvents` object that S and Task 18's `handleAuthErrors` call `authEvents.signOutRequired()` on); `useSigningOut(): boolean` and `isSigningOut(): boolean` from `@/lib/auth`; the `QueryCache` / `MutationCache` `onError: handleAuthErrors` inside `makeQueryClient` (401 → `authEvents.signOutRequired()`; no-op while signing out).
  - Task 19: `useSignOut(): (opts?: { keepPendingInvite?: boolean; next?: string }) => Promise<void>` from `@/lib/auth` (`beginSignOut()` first, then `cancelQueries` + `clear()`, `storeChurchId(null)`, `wsb:` keys removed unless `keepPendingInvite`, `await signOut({ scope: "local" })`, then `router.replace("/login")` or `router.replace("/login?next=" + encodeURIComponent(safeInternalPath(next)))`); `MeProvider({ value: Me; children })` and `useMeContext(): Me` from `@/lib/me-context`; `renderWithProviders(ui, opts?: { me?; church?; path?: string; queryClient? }): RenderResult & { user: UserEvent; queryClient: QueryClient }` from `@/test/render` (fresh `makeQueryClient({ queries: { retry: false } })`; `path` sets what `usePathname()` returns).
  - Task 20: `ErrorState({ error: unknown; onRetry: () => void; title?: string })` from `@/components/app/error-state` (message from `describeError`, a **Retry** button).
  - Task 21: `AppHeader({ user: Me["user"]; churches?: Church[]; active?: Church | null; onSelectChurch?: (id: string) => void; onSignOut: () => void })` from `@/components/app/app-header` (no switcher without `churches`/`onSelectChurch`; account-menu trigger `aria-label="Account menu"`; menu item "Log out" calls `onSignOut`).
  - Existing: `Skeleton` (`src/components/ui/skeleton.tsx`), `Card`, `CardHeader`, `CardTitle`, `CardDescription` (`src/components/ui/card.tsx`).
- Produces:
  - `frontend/src/app/(signed-in)/layout.tsx`: `export default function SignedInLayout({ children }: { children: ReactNode })`. Contract for Task 23 and later slices: every page under `(signed-in)` may call `useMeContext()`; the `(church)` subtree is unmounted while `isSigningOut()`; this layout is the only `authEvents.onSignOutRequired` subscriber (Task 23 subscribes to `onChurchAccessLost` only); the shell skeleton is `role="status"` named "Loading". Slice 1b adds the post-login redirect effect here.
  - `frontend/src/app/(signed-in)/welcome/page.tsx`: `export default function WelcomePage()` at `/welcome` (Task 23's `router.replace("/welcome")` target; 1b replaces it).

- [ ] **Step 1: Read the Next 16 guides this task depends on**

`frontend/AGENTS.md` requires reading the bundled docs before writing route code. Read:

```bash
sed -n 1,60p frontend/node_modules/next/dist/docs/01-app/03-api-reference/03-file-conventions/route-groups.md
sed -n 230,280p frontend/node_modules/next/dist/docs/01-app/03-api-reference/03-file-conventions/layout.md
sed -n 100,125p frontend/node_modules/next/dist/docs/01-app/03-api-reference/04-functions/generate-metadata.md
sed -n 170,190p frontend/node_modules/next/dist/docs/01-app/01-getting-started/05-server-and-client-components.md
sed -n 350,380p frontend/node_modules/next/dist/docs/01-app/01-getting-started/05-server-and-client-components.md
```

The rules this task follows, as the docs state them:
- `route-groups.md:31`: "Routes in different groups should not resolve to the same URL path." `/welcome` is new, and `src/app/page.tsx` (`/`) stays outside the group until Task 23 deletes it in the commit that adds `(signed-in)/(church)/page.tsx`, so this task creates no conflict.
- `layout.md:240-242`: layouts do not re-render on navigation, so read the pathname with `usePathname` inside a Client Component. The layout is `"use client"` and calls `usePathname()` for `next`.
- `generate-metadata.md:110`: `metadata` exports are "only supported in Server Components". Neither new file exports `metadata`.
- `05-server-and-client-components.md:354-356`: React context is not supported in Server Components; a Client Component provides it. `MeProvider` is rendered by the `"use client"` layout.
- Do not use the generated `LayoutProps` / `PageProps` helpers (Global Constraints: CI runs `tsc` before `next build`, when `.next/types` does not exist yet). Type `children` by hand.

- [ ] **Step 2: Write the failing tests**

Create `frontend/src/app/(signed-in)/signed-in-layout.test.tsx`:

```tsx
import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useMeContext } from "@/lib/me-context";
import { fakeError, installFakeApi } from "@/test/fake-api";
import { me } from "@/test/fixtures";
import { supabaseAuth, TEST_ACCESS_TOKEN, testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

import SignedInLayout from "./layout";

/** Stands in for a page under the layout: it reads MeContext. */
function WhoAmI() {
  const current = useMeContext();
  return <p>{current.user.email}</p>;
}

function renderLayout(path = "/") {
  return renderWithProviders(
    <SignedInLayout>
      <WhoAmI />
    </SignedInLayout>,
    { path },
  );
}

describe("(signed-in) layout", () => {
  it("shows the shell skeleton until /me loads, then gives the children MeContext", async () => {
    const api = installFakeApi({ "GET /me": me() });
    renderLayout();

    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
    expect(screen.queryByText("pat@example.com")).not.toBeInTheDocument();

    expect(await screen.findByText("pat@example.com")).toBeInTheDocument();
    expect(screen.queryByRole("status", { name: "Loading" })).not.toBeInTheDocument();
    expect(api.requests).toHaveLength(1);
    expect(api.requests[0]).toMatchObject({ method: "GET", path: "/me" });
    expect(api.requests[0].headers["Authorization"]).toBe(`Bearer ${TEST_ACCESS_TOKEN}`);
  });

  it("shows a full-page ErrorState on a 5xx from /me, and Retry refetches it", async () => {
    const api = installFakeApi({
      "GET /me": fakeError(500, "internal_error", "Something went wrong."),
    });
    const { user } = renderLayout();

    expect(await screen.findByText("Something went wrong. (Ref: 4f9a2c1e)")).toBeInTheDocument();
    expect(screen.queryByText("pat@example.com")).not.toBeInTheDocument();
    expect(api.requests).toHaveLength(1);

    api.set("GET /me", me());
    await user.click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByText("pat@example.com")).toBeInTheDocument();
    expect(api.requests.filter((r) => r.path === "/me")).toHaveLength(2);
    expect(supabaseAuth.signOut).not.toHaveBeenCalled();
  });

  it("signs out locally on a 401 from /me, keeping a pending invite and the current path", async () => {
    window.sessionStorage.setItem("wsb:pendingInviteCode", "code-123");
    const api = installFakeApi({
      "GET /me": fakeError(401, "unauthenticated", "Please sign in."),
    });
    renderLayout("/welcome");

    await waitFor(() =>
      expect(testRouter.replace).toHaveBeenCalledWith("/login?next=%2Fwelcome"),
    );
    expect(testRouter.replace).toHaveBeenCalledTimes(1);
    expect(supabaseAuth.signOut).toHaveBeenCalledTimes(1);
    expect(supabaseAuth.signOut).toHaveBeenCalledWith({ scope: "local" });
    expect(window.sessionStorage.getItem("wsb:pendingInviteCode")).toBe("code-123");
    expect(api.requests).toHaveLength(1);
    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument();
  });
});
```

Create `frontend/src/app/(signed-in)/welcome/welcome.test.tsx`:

```tsx
import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { installFakeApi } from "@/test/fake-api";
import { me } from "@/test/fixtures";
import { supabaseAuth, testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

import SignedInLayout from "../layout";
import WelcomePage from "./page";

describe("/welcome stub (slice 1a)", () => {
  it("shows the No church yet card under the header, and Log out signs out locally", async () => {
    const api = installFakeApi({ "GET /me": me({ churches: [] }) });
    const { user } = renderWithProviders(
      <SignedInLayout>
        <WelcomePage />
      </SignedInLayout>,
      { path: "/welcome" },
    );

    expect(await screen.findByText("No church yet")).toBeInTheDocument();
    expect(
      screen.getByText("Creating or joining a church is coming in the next update."),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Account menu" }));
    await user.click(await screen.findByRole("menuitem", { name: "Log out" }));

    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/login"));
    expect(supabaseAuth.signOut).toHaveBeenCalledTimes(1);
    expect(supabaseAuth.signOut).toHaveBeenCalledWith({ scope: "local" });
    expect(api.requests.filter((r) => r.path === "/me")).toHaveLength(1);
    expect(screen.queryByText("No church yet")).not.toBeInTheDocument();
  });
});
```

What each test pins:
- Test 1: skeleton first, children only after `/me`, one `GET /me` carrying the bearer token, `useMeContext()` returns the loaded `Me` (S Layouts; F §4.2 "while loading → shell skeleton").
- Test 2: a 5xx with no data yet is a full-page `ErrorState` with the reference id (S "Loading, empty and error states"), children stay unmounted, and **Retry** refetches `/me` (F §4.8 "Query failed"). `renderWithProviders` sets `retry: false`, so exactly one request precedes the click.
- Test 3: AC14's 1a part for the 401 path: one local sign-out (`scope: "local"`), `wsb:pendingInviteCode` kept, `/login?next=%2Fwelcome` (Task 19 passes `next` through `safeInternalPath`; `/welcome` is on the allow-list), no refetch of `/me`, and the skeleton instead of an `ErrorState`.
- Test 4: S Testing "`/welcome` stub (1a): renders the 'No church yet' card and the account menu's Log out"; explicit Log out goes to plain `/login`, and the layout issues no `/me` request after the click (the signing-out flag disables the query).

- [ ] **Step 3: Run the tests to verify they fail**

Run:
```bash
(cd frontend && npx vitest run signed-in 2>&1 | grep -E "Failed to resolve import|Test Files|Tests ")
```
Expected: both files fail to load, because neither module exists yet:
```
Error: Failed to resolve import "./layout" from "src/app/(signed-in)/signed-in-layout.test.tsx". Does the file exist?
Error: Failed to resolve import "../layout" from "src/app/(signed-in)/welcome/welcome.test.tsx". Does the file exist?
 Test Files  2 failed (2)
      Tests  no tests
```

- [ ] **Step 4: Create `frontend/src/app/(signed-in)/layout.tsx`**

```tsx
"use client";

/**
 * Layout for every signed-in route (F §4.1, §4.2; S "Layouts (1a)").
 *
 * - Loads `/me` and shows the shell skeleton until it arrives.
 * - A first load that fails with anything but a 401 shows a full-page
 *   `ErrorState` with Retry. Once `/me` has loaded, a failed background refetch
 *   keeps the loaded shell: a network blip on window focus never replaces a
 *   working page.
 * - A 401 anywhere reaches `handleAuthErrors`, which emits
 *   `authEvents.signOutRequired()`. This layout, the event's only subscriber,
 *   answers with one local sign-out that keeps a pending invite and passes the
 *   current path as `next` (S Flow D "Session expired").
 * - While a sign-out runs (the signing-out flag in `lib/auth.ts`) it renders the
 *   skeleton and disables `/me`. That unmounts the `(church)` subtree and its
 *   `ChurchProvider`, so nothing refetches the cleared cache or stores a church
 *   again before `router.replace("/login")`.
 * - Pages below it read `/me` with `useMeContext()`.
 *
 * Slice 1b adds the post-login redirect here. A `"use client"` layout cannot
 * export `metadata`; the root layout's title applies.
 */
import { useEffect, type ReactNode } from "react";
import { usePathname } from "next/navigation";

import { ErrorState } from "@/components/app/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api/client";
import { isSigningOut, useSignOut, useSigningOut } from "@/lib/auth";
import { MeProvider } from "@/lib/me-context";
import { authEvents } from "@/lib/queries/auth-events";
import { useMe } from "@/lib/queries/me";

export default function SignedInLayout({ children }: { children: ReactNode }) {
  const signingOut = useSigningOut();
  const me = useMe({ enabled: !signingOut });
  const signOut = useSignOut();
  const pathname = usePathname();

  useEffect(
    () =>
      authEvents.onSignOutRequired(() => {
        if (isSigningOut()) return;
        void signOut({ keepPendingInvite: true, next: pathname });
      }),
    [signOut, pathname],
  );

  if (signingOut) return <ShellSkeleton />;
  if (me.data) return <MeProvider value={me.data}>{children}</MeProvider>;
  if (me.isError && !isUnauthenticated(me.error)) {
    return (
      <main className="mx-auto flex min-h-dvh max-w-md flex-col justify-center p-4">
        <ErrorState error={me.error} onRetry={() => void me.refetch()} />
      </main>
    );
  }
  return <ShellSkeleton />;
}

/** A 401 is already handled: `handleAuthErrors` has started the sign-out. */
function isUnauthenticated(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401;
}

/** The shell's shape while `/me` loads or a sign-out runs: a header bar and two cards. */
function ShellSkeleton() {
  return (
    <div role="status" aria-label="Loading" className="min-h-dvh">
      <div className="border-b">
        <div className="mx-auto flex max-w-3xl items-center gap-3 px-4 py-3">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="ml-auto size-9 rounded-full" />
        </div>
      </div>
      <div className="mx-auto grid max-w-3xl gap-4 p-4">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    </div>
  );
}
```

Notes for the implementer:
- `signingOut` is checked before `me.data`: `queryClient.clear()` in `useSignOut` drops the data anyway, and the flag must win even for the render in which the cache still holds it.
- The effect only subscribes (its body returns the unsubscribe function), so it satisfies react-hooks v7's `set-state-in-effect`; nothing reads a ref during render. If `useSignOut()` returns a new function on each render, the effect resubscribes on each render, which is harmless: `onSignOutRequired` is synchronous and a second concurrent 401 is dropped by the `isSigningOut()` check (Task 19 calls `beginSignOut()` before its first `await`).
- `next: pathname` is the path only, never the query (S Flow D; F §4.2). `useSignOut` runs it through `safeInternalPath`, so `/` gives plain `/login`.

- [ ] **Step 5: Create `frontend/src/app/(signed-in)/welcome/page.tsx`**

```tsx
"use client";

/**
 * Stub `/welcome` (slice 1a; S file map). It is the zero-church landing, so the
 * `(church)` layout's redirect never lands on a 404 between the 1a and 1b
 * merges. The header has no church switcher (there is no church to switch to)
 * but keeps the account menu, so a user with no church can still log out (S
 * behavior change 20). Slice 1b replaces this page with the Join and Create tabs.
 */
import { AppHeader } from "@/components/app/app-header";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useSignOut } from "@/lib/auth";
import { useMeContext } from "@/lib/me-context";

export default function WelcomePage() {
  const me = useMeContext();
  const signOut = useSignOut();

  return (
    <div className="min-h-dvh">
      <AppHeader user={me.user} onSignOut={() => void signOut()} />
      <main className="mx-auto grid max-w-3xl gap-4 p-4">
        <Card>
          <CardHeader>
            <CardTitle>No church yet</CardTitle>
            <CardDescription>
              Creating or joining a church is coming in the next update.
            </CardDescription>
          </CardHeader>
        </Card>
      </main>
    </div>
  );
}
```

Explicit Log out passes no options: it clears `wsb:` keys including a pending invite and goes to plain `/login` (S Flow D "Log out"). The card copy is the slice-0 text from `src/app/page.tsx:104-111` verbatim; that file keeps its copy until Task 23 deletes it.

- [ ] **Step 6: Run the tests to verify they pass**

Run:
```bash
(cd frontend && npx vitest run signed-in 2>&1 | grep -E "Test Files|Tests ")
```
Expected: `Test Files  2 passed (2)` and `Tests  4 passed (4)`.

If test 4 cannot find the "Log out" menu item, open the menu exactly as Task 21's `app-header.test.tsx` does (same `user.click` on the "Account menu" trigger, then `findByRole("menuitem", …)`); do not change `AppHeader` in this task. If test 3 sees `/login` instead of `/login?next=%2Fwelcome`, check that `renderWithProviders`' `path` option reaches `usePathname()` (Task 19 calls `setTestPath(path)`); do not move the expectation.

- [ ] **Step 7: Run the frontend check, the build and the backend suite**

Run:
```bash
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests " && npm run typecheck && npm run lint)
(cd frontend && NEXT_PUBLIC_SUPABASE_URL=https://ci-placeholder.supabase.co NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build 2>&1 | tail -20)
.venv/bin/python -m pytest -q | tail -1
git status --short
```
Expected:
- `Test Files  22 passed (22)` and `Tests  107 passed (107)` (103 after Task 21 + 4; files: 20 after Task 21 + 2). `tsc --noEmit` and `eslint` report no errors.
- The build ends with the route table, which lists `/welcome` as a static route (`○`) next to `/`, `/login` and `/auth/callback`, with no "conflicting paths" error and no "You are attempting to export "metadata" from a component marked with "use client"" error. The build downloads the Geist fonts (`next/font/google`, `src/app/layout.tsx:2`); if it fails with `Failed to fetch font`, the machine is offline: rerun with network, it is not a code problem. `.next/`, `next-env.d.ts` and `*.tsbuildinfo` are git-ignored (`frontend/.gitignore:17,41-42`).
- Backend `692 passed, 5 skipped` (unchanged since Task 16).
- `git status --short` prints exactly (plus `?? .claude/`):
```
?? frontend/src/app/(signed-in)/
```
Git prints the new directory as one untracked entry and does not quote parentheses in its output (checked with git on this machine).

- [ ] **Step 8: Commit**

```bash
git add "frontend/src/app/(signed-in)/layout.tsx" \
        "frontend/src/app/(signed-in)/signed-in-layout.test.tsx" \
        "frontend/src/app/(signed-in)/welcome/page.tsx" \
        "frontend/src/app/(signed-in)/welcome/welcome.test.tsx"
git status --short
git commit -m "Frontend: (signed-in) layout with MeContext and the stub /welcome (F §4.1, §4.2; S Layouts; AC12, AC14)

The (signed-in) layout loads /me with useMe, shows the shell skeleton until
it arrives, shows a full-page ErrorState with Retry when the first load
fails with anything but a 401, and provides /me through MeProvider. It is
the one subscriber to authEvents.onSignOutRequired: a 401 becomes one local
sign-out that keeps a pending invite and passes the current path as next.
While the signing-out flag is set it renders the skeleton and disables /me,
so the church subtree unmounts and nothing refetches or re-stores a church
during sign-out. A failed background refetch keeps the loaded shell.

/welcome is the 1a stub: AppHeader without the switcher plus the slice-0
\"No church yet\" card, so a zero-church user never lands on a 404 between
the two slice 1 merges and can log out.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

The `git status --short` before the commit prints exactly (plus `?? .claude/`):
```
A  frontend/src/app/(signed-in)/layout.tsx
A  frontend/src/app/(signed-in)/signed-in-layout.test.tsx
A  frontend/src/app/(signed-in)/welcome/page.tsx
A  frontend/src/app/(signed-in)/welcome/welcome.test.tsx
```

Tests after this task: backend `692 passed, 5 skipped`; frontend `107 passed` (22 files).

---

### Task 23: `(church)` layout, keyed remount, 403 fallback, home; delete `src/app/page.tsx` (F §4.2, §4.4; S Flow D, Layouts 1–7; AC12, AC13, AC14 1a part)

The last piece of the 1a shell. `src/app/(signed-in)/(church)/layout.tsx` resolves the active church exactly as S "Layouts (1a)" steps 1–7 say: nothing is picked until `useStoredChurchId()` has read `activeChurchId` (Task 17), the candidate is the stored church if it is still in `/me` and not excluded, else the first by name, and `GET /church` confirms it while the header already shows the candidate's name. The children render under `ChurchProvider` inside `<Fragment key={church.id}>`, so a switch remounts every church page. A `no_church_access` 403 from any church query (Task 18's `authEvents.churchAccessLost`) toasts "You no longer have access to {name}.", excludes that church and refetches `/me`; a role 403, a 5xx or a network error shows `ErrorState` with **Retry** instead and never falls back. The slice-0 home cards move to `(church)/page.tsx` and read `useChurch()`. `src/app/page.tsx` and the old `src/components/app-header.tsx` are deleted in the same commit: a second `page.tsx` resolving to `/` is a build error (Next route groups), and the old header has no other user.

Decisions this task pins (S leaves them open):
- **Old queries are removed in the effect that runs after the render that stopped showing the old church**, not in a cleanup keyed on the stored id. A ref, read and written only inside that effect, holds the church last shown. Reason: in development Next runs React StrictMode, whose simulated unmount would run a cleanup and remove the *shown* church's live queries. The outcome S asks for is unchanged: the old church's `["church", oldId]` queries are cancelled and removed once its pages are unmounted, so no mounted observer can rebuild them with the old `X-Church-Id`.
- **The body keeps its skeleton (no `ErrorState`) for errors another handler owns**: `no_church_access` (step 5 moves to the next church), 401 and `aborted` (the `(signed-in)` layout signs out and unmounts this subtree). Everything else from `GET /church` shows `ErrorState`.
- The lost-access handler acts once per subscription (a second event for the same church before the re-render adds no second toast or refetch).
- The confirmed id is stored only when it is the candidate's, differs from the stored id, and `isSigningOut()` is false (critique 8: the sign-out race).

The tests render the real `(signed-in)` layout (Task 22) around the `(church)` layout, because the `/me` refetch, the skeleton while signing out and the 401 subscription live there; a `renderWithProviders({ me })` MeProvider would have no `/me` observer to refetch. Toasts are asserted with `vi.spyOn(toast, "error")` (sonner's `toast.error` is a writable property, checked), so the test does not depend on a mounted `<Toaster>`.

Verified before writing (offline, in a throwaway worktree, with TanStack Query 5.101.1 and Testing Library 16.3.2 types extracted from the npm cache and stand-ins with the outline's signatures for Tasks 17–22): `layout.tsx` and `page.tsx` pass `tsc --noEmit` and `eslint` with the react-hooks v7 rules at error (a probe proved `set-state-in-effect` and `refs` fire on this file's patterns when misused); `church-layout.test.tsx` passes `eslint` and `tsc` except for the jest-dom matcher types that Task 15's `setup-dom.ts` import provides. **Not run here:** the DOM tests themselves (jsdom, user-event and jest-dom are not in the offline cache) and `next build` (it fetches the Geist fonts). Both first run in Step 6.

**Files:**
- Create: `frontend/src/app/(signed-in)/(church)/layout.tsx`, `frontend/src/app/(signed-in)/(church)/page.tsx`
- Delete: `frontend/src/app/page.tsx` (144 lines; its session, church and header logic now lives in Tasks 18–23), `frontend/src/components/app-header.tsx` (87 lines; replaced by Task 21's `components/app/app-header.tsx`)
- Test: `frontend/src/app/(signed-in)/(church)/church-layout.test.tsx` (new, `dom` project, 15 tests)
- Unchanged on purpose: `frontend/src/lib/latest.ts` + `latest.test.ts` (clarification 17), `frontend/src/components/ui/select.tsx` (generated; unused after this task, harmless).

**Interfaces:**
- Consumes:
  - Task 15: `installFakeApi(handlers): FakeApi`, `fakeError(status, code, message, extra?)`, types `FakeApi`, `RecordedRequest` (`@/test/fake-api`; route keys `"GET /me"`, `"GET /church"`, a non-function `FakeResponse` handler is sent as that response, async handlers delay, requests recorded at call time with case-insensitive header lookup, unhandled requests fail the test, `api.set(route, handler)`); `CHURCH_IDS`, `church(overrides?)` (default Grace, admin), `me(overrides?)` (`@/test/fixtures`); `testRouter`, `supabaseAuth` (`@/test/mocks`); `setup-dom.ts` (mocks of `next/navigation` and `@/lib/supabase/client`, `beforeEach(resetTestMocks)` with path `/`, `afterEach` cleanup + both storages cleared); `FAKE_REQUEST_ID = "4f9a2c1e8b7d4e6fa0c3b5d7e9f1a2b4"` (hence "(Ref: 4f9a2c1e)").
  - Task 16: `ApiError` (`@/lib/api/client`: `status`, `code`), `isNoChurchAccess(e)` (`@/lib/api/errors`); `describeError` through `ErrorState` (403 → the message; 5xx → "Something went wrong. (Ref: xxxxxxxx)").
  - Task 17: `pickActiveChurch(churches, storedId, excluded?)`, `storeChurchId(id: string | null)` (writes `localStorage` and notifies this tab), `useStoredChurchId(): string | null | undefined`, type `Church` (`@/lib/church`); `ACTIVE_CHURCH_KEY`, `SESSION_KEYS` (`@/lib/storage`); `setup-dom.ts`'s `afterEach` calling `resetStoredChurchIdForTests()`.
  - Task 18: `useChurchProfile(id: string | undefined, opts?: { enabled?: boolean }): UseQueryResult<Church, ApiError>` (`@/lib/queries/church`, key `keys.churchProfile(id)`); `keys.me()`, `keys.church(id)` (`["church", id]`), `keys.churchProfile(id)` (`["church", id, "profile"]`) (`@/lib/queries/keys`); `authEvents.onChurchAccessLost(cb: (churchId: string) => void): () => void` (`@/lib/queries/auth-events`); `isSigningOut(): boolean` (`@/lib/auth`); `makeQueryClient(overrides?)` (its `QueryCache`/`MutationCache` call `handleAuthErrors` whatever the overrides) and `useApi()` (`@/lib/queries/client`); `ChurchProvider({ value, children })`, `useChurch()` (`@/lib/church-context`); `setup-dom.ts`'s `afterEach` calling `resetSigningOutForTests()`.
  - Task 19: `useSignOut(): (opts?) => Promise<void>` (`@/lib/auth`), `useMeContext(): Me` (`@/lib/me-context`), `renderWithProviders(ui, opts?: { me?; church?; path?; queryClient? })` → `RenderResult & { user; queryClient }` (`@/test/render`; wraps in `MeProvider`/`ChurchProvider` only when `me`/`church` are given, and uses `opts.queryClient` when given).
  - Task 20: `ErrorState({ error, onRetry, title? })` (`@/components/app/error-state`; shows `describeError(error)` and a **Retry** button).
  - Task 21: `AppHeader({ user, churches?, active?, onSelectChurch?, onSignOut })` (`@/components/app/app-header`). The tests assume its DOM as Task 21 describes it: one `<header>` (role `banner`) that shows `active.name`; the account-menu trigger `aria-label="Account menu"` whose menu has a `menuitem` "Log out"; the church switcher as the header's only other button, whose menu lists each church as a `menuitemradio` whose name contains the church name.
  - Task 22: the default export of `frontend/src/app/(signed-in)/layout.tsx` (`useMe({ enabled: !signingOut })`, skeleton while loading or signing out, `MeProvider`, `authEvents.onSignOutRequired` → `signOut({ keepPendingInvite: true, next: pathname })`).
- Produces:
  - `frontend/src/app/(signed-in)/(church)/layout.tsx`: `export default function ChurchLayout({ children }: { children: ReactNode })` (the only export; Next rejects unknown exports from layout files). Behavior per S Layouts steps 1–7 and the decisions above.
  - `frontend/src/app/(signed-in)/(church)/page.tsx`: `export default function HomePage()` at `/` (two cards; "Readings, hymns, and liturgy for {church.name} are coming soon. Until then, keep using the current app." and "Church profile, members, and invites are coming later.").
  - Route `/` is now served by the `(signed-in)` → `(church)` layouts. Later users: slice 2 pages under `(church)` (`useChurch()`, church queries keyed `["church", id, …]`); 1b's `useMembershipChanged` (stores the new id and refetches `/me` before `router.replace("/")`, which step 3 never overwrites).

- [ ] **Step 1: Read the Next 16 guides this task depends on**

`frontend/AGENTS.md` requires it before route code. Read:

```bash
sed -n 1,60p frontend/node_modules/next/dist/docs/01-app/03-api-reference/03-file-conventions/route-groups.md
sed -n 1,80p frontend/node_modules/next/dist/docs/01-app/03-api-reference/03-file-conventions/layout.md
```

Expected, and relied on below: route groups are left out of the URL, so `(signed-in)/(church)/page.tsx` is `/`; "Routes in different groups should not resolve to the same URL path" (route-groups.md "Caveats"), so the old `src/app/page.tsx` goes in the same commit; a `"use client"` layout exports no `metadata` (the root layout keeps the title); a layout receives `children` and reads the path only through `usePathname` in a client component. Do not use the generated `LayoutProps`/`PageProps` helpers (CI runs `tsc` before `next build`, when `.next/types` does not exist).

- [ ] **Step 2: Write the failing test**

Create `frontend/src/app/(signed-in)/(church)/church-layout.test.tsx`:

```tsx
/**
 * The `(church)` layout inside the real `(signed-in)` layout, against the fake
 * API (S Flow D, Layouts steps 1-7, Testing "(church) layout"; AC12, AC13, the
 * 1a part of AC14; F §5.2 error-state test).
 *
 * `ChurchProbe` stands in for a church page: it shows `useChurch().name` and
 * keeps local state, so a remount is visible as its counter going back to 0.
 */
import { useState, type ReactElement, type ReactNode } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, screen, waitFor, within } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from "vitest";

import type { Church } from "@/lib/church";
import { useChurch } from "@/lib/church-context";
import { makeQueryClient, useApi } from "@/lib/queries/client";
import { keys } from "@/lib/queries/keys";
import { ACTIVE_CHURCH_KEY, SESSION_KEYS } from "@/lib/storage";
import { type FakeApi, type RecordedRequest, fakeError, installFakeApi } from "@/test/fake-api";
import { CHURCH_IDS, church, me } from "@/test/fixtures";
import { supabaseAuth, testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

import SignedInLayout from "../layout";
import ChurchLayout from "./layout";
import HomePage from "./page";

const GRACE = church();
const HOPE = church({ id: CHURCH_IDS.hope, name: "Hope", role: "member" });

/** `require_church`'s 403 for a church the user no longer belongs to. */
const NO_ACCESS = fakeError(403, "forbidden", "You don't have access to this church.", {
  details: { reason: "no_church_access" },
});

function ChurchProbe() {
  const active = useChurch();
  const [clicks, setClicks] = useState(0);
  return (
    <div>
      <p>Showing {active.name}</p>
      <button type="button" onClick={() => setClicks((n) => n + 1)}>
        Clicked {clicks}
      </button>
    </div>
  );
}

function renderShell(
  page: ReactElement = <ChurchProbe />,
  options: Parameters<typeof renderWithProviders>[1] = {},
) {
  return renderWithProviders(
    <SignedInLayout>
      <ChurchLayout>{page}</ChurchLayout>
    </SignedInLayout>,
    options,
  );
}

/** `GET /church` as the API answers it: the church named by `X-Church-Id`, else 403. */
function churchById(...churches: Church[]) {
  return (req: RecordedRequest) =>
    churches.find((c) => c.id === req.headers["X-Church-Id"]) ?? NO_ACCESS;
}

/** The same answer, 20 ms later. */
function slowly(answer: (req: RecordedRequest) => unknown) {
  return async (req: RecordedRequest) => {
    await new Promise((resolve) => setTimeout(resolve, 20));
    return answer(req);
  };
}

/** A promise the test resolves by hand. */
function gate(): { wait: Promise<void>; open: () => void } {
  let open = () => {};
  const wait = new Promise<void>((resolve) => {
    open = resolve;
  });
  return { wait, open };
}

/** The `X-Church-Id` of every `GET /church`, in order. */
function churchRequests(api: FakeApi): string[] {
  return api.requests
    .filter((req) => req.method === "GET" && req.path === "/church")
    .map((req) => req.headers["X-Church-Id"]);
}

function meRequests(api: FakeApi): RecordedRequest[] {
  return api.requests.filter((req) => req.method === "GET" && req.path === "/me");
}

function header(): HTMLElement {
  return screen.getByRole("banner");
}

/** The header's church switcher: its one button besides the account menu. */
function switcherTrigger(): HTMLElement {
  const account = screen.getByRole("button", { name: "Account menu" });
  const trigger = within(header())
    .getAllByRole("button")
    .find((button) => button !== account);
  if (!trigger) throw new Error("The header has no church switcher.");
  return trigger;
}

describe("(church) layout", () => {
  let toastError: MockInstance<typeof toast.error>;

  beforeEach(() => {
    toastError = vi.spyOn(toast, "error").mockImplementation(() => 0);
  });

  afterEach(() => {
    toastError.mockRestore();
  });

  it("confirms the stored church when the user still belongs to it", async () => {
    window.localStorage.setItem(ACTIVE_CHURCH_KEY, HOPE.id);
    const api = installFakeApi({
      "GET /me": me({ churches: [GRACE, HOPE] }),
      "GET /church": churchById(GRACE, HOPE),
    });

    renderShell();

    expect(await screen.findByText("Showing Hope")).toBeInTheDocument();
    expect(header()).toHaveTextContent("Hope");
    expect(churchRequests(api)).toEqual([HOPE.id]);
    expect(window.localStorage.getItem(ACTIVE_CHURCH_KEY)).toBe(HOPE.id);
  });

  it("falls back to the first church by name when the stored id is stale, and stores it", async () => {
    window.localStorage.setItem(ACTIVE_CHURCH_KEY, CHURCH_IDS.trinity);
    const api = installFakeApi({
      "GET /me": me({ churches: [GRACE, HOPE] }),
      "GET /church": churchById(GRACE, HOPE),
    });

    renderShell();

    expect(await screen.findByText("Showing Grace")).toBeInTheDocument();
    await waitFor(() => expect(window.localStorage.getItem(ACTIVE_CHURCH_KEY)).toBe(GRACE.id));
    expect(churchRequests(api)).toEqual([GRACE.id]);
  });

  it("never asks for or shows a cached church other than the stored one", async () => {
    window.localStorage.setItem(ACTIVE_CHURCH_KEY, HOPE.id);
    const queryClient = makeQueryClient({ queries: { retry: false } });
    queryClient.setQueryData(keys.churchProfile(GRACE.id), GRACE);
    const hopeAnswer = gate();
    const api = installFakeApi({
      "GET /me": me({ churches: [GRACE, HOPE] }),
      "GET /church": async (req: RecordedRequest) => {
        await hopeAnswer.wait;
        return churchById(GRACE, HOPE)(req);
      },
    });

    renderShell(<ChurchProbe />, { queryClient });

    // While Hope is being confirmed, the header shows Hope (the candidate), never Grace.
    await waitFor(() => expect(churchRequests(api)).toEqual([HOPE.id]));
    expect(header()).toHaveTextContent("Hope");
    expect(header()).not.toHaveTextContent("Grace");
    expect(screen.queryByText("Showing Grace")).not.toBeInTheDocument();

    await act(async () => hopeAnswer.open());

    expect(await screen.findByText("Showing Hope")).toBeInTheDocument();
    expect(header()).not.toHaveTextContent("Grace");
    expect(churchRequests(api)).toEqual([HOPE.id]);
    expect(window.localStorage.getItem(ACTIVE_CHURCH_KEY)).toBe(HOPE.id);
  });

  it("on 403 no_church_access says so, refetches /me and confirms the next church", async () => {
    const api = installFakeApi({
      "GET /me": me({ churches: [GRACE, HOPE] }),
      "GET /church": churchById(HOPE),
    });

    renderShell();

    expect(await screen.findByText("Showing Hope")).toBeInTheDocument();
    expect(toastError).toHaveBeenCalledTimes(1);
    expect(toastError).toHaveBeenCalledWith("You no longer have access to Grace.");
    await waitFor(() => expect(meRequests(api)).toHaveLength(2));
    expect(churchRequests(api)).toEqual([GRACE.id, HOPE.id]);
    await waitFor(() => expect(window.localStorage.getItem(ACTIVE_CHURCH_KEY)).toBe(HOPE.id));
  });

  it("on refocus, a /me that no longer lists the shown church says so and confirms the next one", async () => {
    let meCalls = 0;
    const api = installFakeApi({
      "GET /me": () => {
        meCalls += 1;
        return meCalls === 1 ? me({ churches: [GRACE, HOPE] }) : me({ churches: [HOPE] });
      },
      "GET /church": churchById(GRACE, HOPE),
    });
    const { queryClient } = renderShell();
    expect(await screen.findByText("Showing Grace")).toBeInTheDocument();

    await act(async () => {
      await queryClient.invalidateQueries({ queryKey: keys.me() });
    });

    expect(await screen.findByText("Showing Hope")).toBeInTheDocument();
    expect(toastError).toHaveBeenCalledTimes(1);
    expect(toastError).toHaveBeenCalledWith("You no longer have access to Grace.");
    expect(churchRequests(api)).toEqual([GRACE.id, HOPE.id]);
    await waitFor(() => expect(window.localStorage.getItem(ACTIVE_CHURCH_KEY)).toBe(HOPE.id));
  });

  it("goes to /welcome when the last church is lost", async () => {
    let meCalls = 0;
    const api = installFakeApi({
      "GET /me": () => {
        meCalls += 1;
        return meCalls === 1 ? me({ churches: [GRACE] }) : me({ churches: [] });
      },
      "GET /church": NO_ACCESS,
    });

    renderShell();

    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/welcome"));
    expect(toastError).toHaveBeenCalledWith("You no longer have access to Grace.");
    await waitFor(() => expect(meRequests(api)).toHaveLength(2));
    expect(churchRequests(api)).toEqual([GRACE.id]);
  });

  it("sends a user with no church to /welcome without asking for a church", async () => {
    const api = installFakeApi({ "GET /me": me({ churches: [] }) });

    renderShell();

    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/welcome"));
    expect(churchRequests(api)).toEqual([]);
  });

  it("switching remounts the page and removes the old church's queries", async () => {
    const api = installFakeApi({
      "GET /me": me({ churches: [GRACE, HOPE] }),
      "GET /church": churchById(GRACE, HOPE),
    });
    const { user, queryClient } = renderShell();
    expect(await screen.findByText("Showing Grace")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Clicked 0" }));
    expect(screen.getByRole("button", { name: "Clicked 1" })).toBeInTheDocument();

    await user.click(switcherTrigger());
    await user.click(await screen.findByRole("menuitemradio", { name: /Hope/ }));

    expect(await screen.findByText("Showing Hope")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Clicked 0" })).toBeInTheDocument();
    expect(window.localStorage.getItem(ACTIVE_CHURCH_KEY)).toBe(HOPE.id);
    await waitFor(() =>
      expect(queryClient.getQueryCache().findAll({ queryKey: keys.church(GRACE.id) })).toHaveLength(0),
    );
    expect(queryClient.getQueryData(keys.churchProfile(HOPE.id))).toEqual(HOPE);
    expect(churchRequests(api)).toEqual([GRACE.id, HOPE.id]);
  });

  it("a role 403 shows the error state and does not fall back", async () => {
    const api = installFakeApi({
      "GET /me": me({ churches: [GRACE, HOPE] }),
      "GET /church": fakeError(403, "forbidden", "Only church admins can do this."),
    });

    renderShell();

    expect(await screen.findByText("Only church admins can do this.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
    expect(header()).toHaveTextContent("Grace");
    expect(toastError).not.toHaveBeenCalled();
    expect(meRequests(api)).toHaveLength(1);
    expect(churchRequests(api)).toEqual([GRACE.id]);
  });

  it("GET /church 500 shows the error state with its reference, and Retry refetches", async () => {
    const api = installFakeApi({
      "GET /me": me(),
      "GET /church": fakeError(500, "internal_error", "Something went wrong."),
    });
    const { user } = renderShell();

    expect(await screen.findByText("Something went wrong. (Ref: 4f9a2c1e)")).toBeInTheDocument();

    api.set("GET /church", GRACE);
    await user.click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByText("Showing Grace")).toBeInTheDocument();
    expect(churchRequests(api)).toEqual([GRACE.id, GRACE.id]);
  });

  it("Log out clears the cache, the stored church and the wsb: keys, and signs out locally", async () => {
    window.sessionStorage.setItem(SESSION_KEYS.pendingInviteCode, "invite-code-1");
    window.sessionStorage.setItem(SESSION_KEYS.postLoginPath, "/builder");
    installFakeApi({ "GET /me": me(), "GET /church": GRACE });
    const { user, queryClient } = renderShell();
    expect(await screen.findByText("Showing Grace")).toBeInTheDocument();
    await waitFor(() => expect(window.localStorage.getItem(ACTIVE_CHURCH_KEY)).toBe(GRACE.id));

    await user.click(screen.getByRole("button", { name: "Account menu" }));
    await user.click(await screen.findByRole("menuitem", { name: "Log out" }));

    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/login"));
    expect(supabaseAuth.signOut).toHaveBeenCalledWith({ scope: "local" });
    expect(window.localStorage.getItem(ACTIVE_CHURCH_KEY)).toBeNull();
    expect(window.sessionStorage.getItem(SESSION_KEYS.pendingInviteCode)).toBeNull();
    expect(window.sessionStorage.getItem(SESSION_KEYS.postLoginPath)).toBeNull();
    expect(queryClient.getQueryData(keys.me())).toBeUndefined();
    expect(queryClient.getQueryData(keys.churchProfile(GRACE.id))).toBeUndefined();
  });

  it("signing out sends no request and stores no church, even with slow answers in flight", async () => {
    const api = installFakeApi({
      "GET /me": slowly(() => me({ churches: [GRACE, HOPE] })),
      "GET /church": slowly(churchById(GRACE, HOPE)),
    });
    const { user } = renderShell();
    expect(await screen.findByText("Showing Grace")).toBeInTheDocument();
    await waitFor(() => expect(window.localStorage.getItem(ACTIVE_CHURCH_KEY)).toBe(GRACE.id));
    await user.click(screen.getByRole("button", { name: "Account menu" }));
    const logOut = await screen.findByRole("menuitem", { name: "Log out" });
    const sent = api.requests.length;

    await user.click(logOut);
    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/login"));
    // Longer than a slow answer: a refetch started by the sign-out would have landed by now.
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 60));
    });

    expect(api.requests.slice(sent)).toEqual([]);
    expect(supabaseAuth.signOut).toHaveBeenCalledTimes(1);
    expect(window.localStorage.getItem(ACTIVE_CHURCH_KEY)).toBeNull();
  });

  it("a 401 from a church query signs out locally and keeps the pending invite", async () => {
    window.localStorage.setItem(ACTIVE_CHURCH_KEY, GRACE.id);
    window.sessionStorage.setItem(SESSION_KEYS.pendingInviteCode, "invite-code-1");
    installFakeApi({
      "GET /me": me(),
      "GET /church": fakeError(401, "unauthenticated", "Please sign in."),
    });

    renderShell();

    await waitFor(() =>
      expect(testRouter.replace).toHaveBeenCalledWith(expect.stringMatching(/^\/login/)),
    );
    expect(supabaseAuth.signOut).toHaveBeenCalledTimes(1);
    expect(supabaseAuth.signOut).toHaveBeenCalledWith({ scope: "local" });
    expect(window.localStorage.getItem(ACTIVE_CHURCH_KEY)).toBeNull();
    expect(window.sessionStorage.getItem(SESSION_KEYS.pendingInviteCode)).toBe("invite-code-1");
  });

  it("the home page shows the confirmed church from useChurch()", async () => {
    installFakeApi({ "GET /me": me(), "GET /church": GRACE });

    renderShell(<HomePage />);

    expect(
      await screen.findByText(
        "Readings, hymns, and liturgy for Grace are coming soon. Until then, keep using the current app.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Church profile, members, and invites are coming later.")).toBeInTheDocument();
  });

  it("useApi().church refuses to run outside ChurchProvider", async () => {
    const api = installFakeApi({});
    const queryClient = makeQueryClient({ queries: { retry: false } });
    function Wrapper({ children }: { children: ReactNode }) {
      return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
    }
    const { result } = renderHook(() => useApi(), { wrapper: Wrapper });

    await expect(Promise.resolve().then(() => result.current.church("/church"))).rejects.toThrow();
    expect(api.requests).toEqual([]);
  });
});
```

- [ ] **Step 3: Run the test to verify it fails**

Run:
```bash
(cd frontend && npx vitest run church-layout 2>&1 | tail -15)
```
Expected: FAIL before any test runs: `Error: Failed to resolve import "./layout" from "src/app/(signed-in)/(church)/church-layout.test.tsx". Does the file exist?` (Vite may name `"./page"` first; both are created below), then `Test Files  1 failed (1)` and `Tests  no tests`.

- [ ] **Step 4: Create `frontend/src/app/(signed-in)/(church)/layout.tsx`**

```tsx
"use client";

/**
 * The church-scoped shell: every page that works on one church lives under it
 * (S Layouts steps 1-7, Flow D; F §4.2, §4.4).
 *
 * 1. `useStoredChurchId()` is `undefined` until the client has read
 *    `activeChurchId`, so the server render and the hydration pass show the
 *    shell skeleton and no church is picked before the stored one is known.
 * 2. The candidate is the stored church when it is still in `/me` and not
 *    excluded, else the first by name. No candidate → `/welcome`.
 * 3. `GET /church` confirms the candidate while the header shows its name. The
 *    confirmed id is stored only when it is the candidate's and differs from
 *    the stored id (the fallback pick), and never while signing out.
 * 4. The children render under `ChurchProvider`, keyed by the church id, so a
 *    switch remounts the whole subtree.
 * 5. `churchAccessLost` for the candidate (`no_church_access` from any church
 *    query): toast, exclude it, refetch `/me`, which picks the next church.
 *    A `/me` refetch that no longer lists the shown church (it can answer
 *    before the 403 on refocus) toasts the same message once.
 * 6. A switch stores the new id. Once the old church is no longer shown, its
 *    `["church", oldId]` queries are cancelled and removed.
 */
import { Fragment, useEffect, useRef, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { AppHeader } from "@/components/app/app-header";
import { ErrorState } from "@/components/app/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api/client";
import { isNoChurchAccess } from "@/lib/api/errors";
import { isSigningOut, useSignOut } from "@/lib/auth";
import { type Church, pickActiveChurch, storeChurchId, useStoredChurchId } from "@/lib/church";
import { ChurchProvider } from "@/lib/church-context";
import { useMeContext } from "@/lib/me-context";
import { authEvents } from "@/lib/queries/auth-events";
import { useChurchProfile } from "@/lib/queries/church";
import { keys } from "@/lib/queries/keys";

export default function ChurchLayout({ children }: { children: ReactNode }) {
  const me = useMeContext();
  const router = useRouter();
  const queryClient = useQueryClient();
  const signOut = useSignOut();
  const activeId = useStoredChurchId();
  const [excluded, setExcluded] = useState<ReadonlySet<string>>(() => new Set());

  // Step 2: nothing is picked until the stored id has been read.
  const candidate = activeId === undefined ? null : pickActiveChurch(me.churches, activeId, excluded);
  const candidateId = candidate?.id ?? null;
  const candidateName = candidate?.name ?? "";
  const noChurch = activeId !== undefined && candidate === null;

  // Step 3: only the candidate's own profile confirms it; cached data for any
  // other church never does.
  const profile = useChurchProfile(candidate?.id, { enabled: candidate !== null });
  const confirmed: Church | null =
    candidate !== null && profile.data?.id === candidate.id ? profile.data : null;
  const confirmedId = confirmed?.id ?? null;

  useEffect(() => {
    if (noChurch) router.replace("/welcome");
  }, [noChurch, router]);

  useEffect(() => {
    if (confirmedId !== null && confirmedId !== activeId && !isSigningOut()) {
      storeChurchId(confirmedId);
    }
  }, [confirmedId, activeId]);

  // Step 5: one toast and one /me refetch per lost church.
  useEffect(() => {
    if (candidateId === null) return;
    let handled = false;
    return authEvents.onChurchAccessLost((lostId) => {
      if (lostId !== candidateId || handled) return;
      handled = true;
      toast.error(`You no longer have access to ${candidateName}.`);
      setExcluded((previous) => new Set(previous).add(lostId));
      void queryClient.invalidateQueries({ queryKey: keys.me() });
    });
  }, [candidateId, candidateName, queryClient]);

  // The church last shown ({id, name}); read and written only inside effects.
  const shownRef = useRef<{ id: string; name: string } | null>(null);
  const confirmedName = confirmed?.name ?? "";

  // Step 5, second path: a /me refetch that no longer lists the church being
  // shown is lost access too. On refocus /me can answer before GET /church's
  // 403, and step 6 then cancels that request, so no churchAccessLost event
  // would come. Declared before step 6, so it still sees the church last shown.
  useEffect(() => {
    const shown = shownRef.current;
    if (shown === null || isSigningOut()) return;
    if (!me.churches.some((c) => c.id === shown.id)) {
      toast.error(`You no longer have access to ${shown.name}.`);
    }
  }, [me.churches]);

  // Step 6: runs after the render that stopped showing the old church, so no
  // mounted observer can rebuild its queries. The ref keeps StrictMode's
  // repeated effect from removing the shown church.
  useEffect(() => {
    const previous = shownRef.current;
    shownRef.current = confirmedId === null ? null : { id: confirmedId, name: confirmedName };
    if (previous === null || previous.id === confirmedId) return;
    const queryKey = keys.church(previous.id);
    void queryClient.cancelQueries({ queryKey });
    queryClient.removeQueries({ queryKey });
  }, [confirmedId, confirmedName, queryClient]);

  if (candidate === null) return <ShellSkeleton />;

  let body: ReactNode;
  if (confirmed !== null) {
    // Step 4.
    body = (
      <ChurchProvider value={confirmed}>
        <Fragment key={confirmed.id}>{children}</Fragment>
      </ChurchProvider>
    );
  } else if (profile.isError && !isHandledElsewhere(profile.error)) {
    body = (
      <main className="mx-auto max-w-3xl p-4">
        <ErrorState error={profile.error} onRetry={() => void profile.refetch()} />
      </main>
    );
  } else {
    body = <BodySkeleton />;
  }

  return (
    <div className="min-h-dvh">
      <AppHeader
        user={me.user}
        churches={me.churches.filter((church) => !excluded.has(church.id))}
        active={confirmed ?? candidate}
        onSelectChurch={(id) => storeChurchId(id)}
        onSignOut={() => void signOut()}
      />
      {body}
    </div>
  );
}

/**
 * Errors another handler owns, so the body keeps its skeleton: lost access
 * (step 5 picks the next church) and 401 or a sign-out in progress (the
 * `(signed-in)` layout signs out and unmounts this subtree).
 */
function isHandledElsewhere(error: unknown): boolean {
  return (
    isNoChurchAccess(error) ||
    (error instanceof ApiError && (error.status === 401 || error.code === "aborted"))
  );
}

function ShellSkeleton() {
  return (
    <div className="min-h-dvh">
      <div className="border-b">
        <div className="mx-auto flex max-w-3xl items-center gap-3 px-4 py-3">
          <Skeleton className="h-8 flex-1" />
          <Skeleton className="size-8 rounded-full" />
        </div>
      </div>
      <BodySkeleton />
    </div>
  );
}

function BodySkeleton() {
  return (
    <main className="mx-auto grid max-w-3xl gap-4 p-4" aria-busy="true">
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-24 w-full" />
    </main>
  );
}
```

Notes for the reviewer: every hook runs on every render (the early `return <ShellSkeleton />` comes after the last hook); the only `setState` call (`setExcluded`) runs inside the `authEvents` callback, never synchronously in an effect body (`react-hooks/set-state-in-effect`); `shownRef` is read and written only inside effects (`react-hooks/refs`); `isSigningOut()` is called only inside an effect. `onSelectChurch` just stores the id: `useStoredChurchId()` re-renders the layout with the new candidate, the old pages unmount (body skeleton, header showing the new name), and step 6 removes the old church's queries.

- [ ] **Step 5: Move the home page under `(church)` and delete the old page and header**

Create `frontend/src/app/(signed-in)/(church)/page.tsx`:

```tsx
"use client";

import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useChurch } from "@/lib/church-context";

/** Home (`/`): the slice-0 placeholder cards for the confirmed church (slice 2 makes `/` a redirect to `/builder`). */
export default function HomePage() {
  const church = useChurch();

  return (
    <main className="mx-auto grid max-w-3xl gap-4 p-4">
      <Card>
        <CardHeader>
          <CardTitle>Service Builder</CardTitle>
          <CardDescription>
            Readings, hymns, and liturgy for {church.name} are coming soon. Until then, keep
            using the current app.
          </CardDescription>
        </CardHeader>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Settings</CardTitle>
          <CardDescription>Church profile, members, and invites are coming later.</CardDescription>
        </CardHeader>
      </Card>
    </main>
  );
}
```

Then delete the old home page (its `/` would collide with the new one) and the old header (its only importer was that page):

```bash
git rm -q frontend/src/app/page.tsx frontend/src/components/app-header.tsx
git grep -n "@/components/app-header" -- frontend/src; echo "exit $?"
```
Expected: no matches and `exit 1` (Task 21's header is imported as `@/components/app/app-header`, which the grep does not match because of the `/app/` segment).

- [ ] **Step 6: Run the tests, the frontend check, the build and the backend suite**

Run:
```bash
(cd frontend && npx vitest run church-layout 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests " && npm run typecheck && npm run lint)
(cd frontend && NEXT_PUBLIC_SUPABASE_URL=https://ci-placeholder.supabase.co NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build 2>&1 | tail -20)
.venv/bin/python -m pytest -q | tail -1
git status --short
```
Expected:
- `Test Files  1 passed (1)` and `Tests  15 passed (15)`.
- `Test Files  23 passed (23)` and `Tests  122 passed (122)` (107 after Task 22 + 15; 22 files after Task 22 + this one); `tsc --noEmit` and `eslint` print no errors or warnings.
- The build ends with the route list, which shows `/` (now `(signed-in)/(church)/page.tsx`), `/welcome`, `/login` and `/auth/callback`, and no `You cannot have two parallel pages that resolve to the same path` error (that error means `src/app/page.tsx` is still there).
- `692 passed, 5 skipped` (unchanged since Task 16; no backend test reads the deleted files).
- `git status --short` lists exactly (plus `?? .claude/`):

```
D  frontend/src/app/page.tsx
D  frontend/src/components/app-header.tsx
?? frontend/src/app/(signed-in)/(church)/
```

(The new directory is wholly untracked, so `git status` collapses it to one line; `git status --short -uall` lists its three files.)

If a test fails, check the consumed interfaces before changing this layout:
- `findByRole("menuitemradio", { name: /Hope/ })` or the `Account menu` / `Log out` lookups fail → compare with Task 21's `app-header.test.tsx`, which uses the same roles; adjust only the lookup helpers `switcherTrigger()` / `header()` in this test to match Task 21's DOM, never the layout.
- `/me` is requested only once in the lost-access tests → Task 22's layout must observe `keys.me()` through `useMe` (so `invalidateQueries` refetches it).
- A request appears after Log out, or `signOut` is called twice → Task 18's flag (`getAccessToken` rejects with `aborted`, `handleAuthErrors` ignores everything while signing out) or Task 22's skeleton-while-signing-out is missing; fix it in that task's files and re-review that task.
- `toastError` is never called in the lost-access tests → Task 18's `handleAuthErrors` must read the church id from the query key `["church", id, "profile"]`.

- [ ] **Step 7: Commit**

```bash
git add "frontend/src/app/(signed-in)/(church)/layout.tsx" \
        "frontend/src/app/(signed-in)/(church)/page.tsx" \
        "frontend/src/app/(signed-in)/(church)/church-layout.test.tsx"
git status --short
git commit -m "Frontend: (church) layout resolves, confirms and switches the church; home moves under it (F §4.2, §4.4; S Flow D, Layouts)

The (church) layout picks the stored church when it is still in /me and
not excluded, else the first by name, and confirms it with GET /church
while the header shows its name. Nothing is picked before the stored id
has been read, so no other church is requested or shown first, and cached
data for another church can never overwrite the stored choice. Pages
render under ChurchProvider keyed by the church id, so a switch remounts
them; the old church's queries are cancelled and removed once its pages
are gone. A no_church_access 403 from any church query toasts \"You no
longer have access to {name}.\", excludes the church and refetches /me;
none left goes to /welcome. A role 403, 5xx or network error shows
ErrorState with Retry and never falls back. Nothing is stored while
signing out.

src/app/page.tsx and components/app-header.tsx are deleted: / is now
(signed-in)/(church)/page.tsx, and the header lives in components/app.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git status --short
```
Expected: the first `git status --short` shows five staged paths (`D  frontend/src/app/page.tsx`, `D  frontend/src/components/app-header.tsx` and `A ` for the three new files); after the commit only `?? .claude/` remains.

---

### Task 24: Docs: the Alembic production runbook, the deploy health check, local-dev migrations and the "Slice 1" manual checks (S Production runbook, Local dev, Manual checks item 1; F §3.3, §5.5)

The spec puts the production runbook in `backend/migrations/README.md` (so the seven `##` sections of `docs/ops-runbook.md` stay as `test_ops_workflows.py::test_runbook_has_the_seven_sections_in_order` pins them). In `docs/ops-runbook.md` only the two "slice 1 moves it" sentences change, in place (`:23-24`, `:317-318`; line numbers of `560ebb3`, which Task 1 merged); the dated records (`:40-41`, the lockdown SQL comment at `:149`, the instruction at `:164`) are history and stay (clarification 19); slice 1a's own results go in Task 27's records PR. The runbook is written for this machine (clarifications 22-25): the owner runs `../.venv/bin/alembic` and `../.venv/bin/python` from `backend/` of this worktree, exports `DATABASE_URL` with `read -s` (Alembic never reads `backend/.env`), reruns step 0 in the Supabase SQL Editor (no `psql`, `pg_dump` or Docker on the laptop), and takes step 1's backup as a `db-backup` run. Production Streamlit is https://liturgy-frozen.streamlit.app/ (owner answer Q1); the new text never names `liturgy-next`. The README's `**Deploying:**` Railway bullet and "Run locally" paragraph are also corrected (they would otherwise still say health check `/health` and imply the API creates its tables).

**Files:**
- Create: `backend/migrations/README.md`, `backend/tests/test_slice1_docs.py`
- Modify: `docs/ops-runbook.md:23-24` (Environments and variables → the Railway paragraph) and `:317-318` (Keep-alive → the `GET /health` sentence; `:315-316` at `7978a5e`), in place, no new heading
- Modify: `README.md:29-31` ("Run locally": the tables come from Alembic), `README.md:35` (`**Deploying:**` → the Railway bullet), `README.md:119` (after "Store `DATABASE_URL` in Streamlit secrets …", a new `### Schema migrations (Alembic)` inside `## Database`)
- Modify: `docs/manual-verification.md` (append `## Slice 1` after line 67, the last line of `## Ops slice` and of the file at `560ebb3`)

**Interfaces:**
- Consumes (quoted verbatim in the docs; defined by the earlier tasks): revision ids `0001_baseline`, `0002_reconcile`, `0003_lockdown`, `0004_invites_reusable` (Tasks 6-9); env.py's stderr line `Database: dialect=… driver=… host=… database=…`, the `SET LOCAL lock_timeout = '5s'` / `SET LOCAL statement_timeout = '60s'` pair and the single transaction (Task 5); the 0003 refusal messages (Task 8, Global Constraints); `scripts/schema_drift.py` stdout `revision: <current> head: <head> state: <state>` + sorted `format_diff` lines, exit 0/1/2 and `DATABASE_URL is not set.` (Task 10); the startup lines `schema revision <current> != head <head>` and `Row-level security is off on: …` (Task 11); the 503 `db_unavailable` gate with `"reason": "schema_behind"` and `backend/railway.toml`'s `preDeployCommand = ["alembic upgrade head"]` / `healthcheckPath = "/health/ready"` (Task 12); `require_local_test_url`'s message `TEST_DATABASE_URL must point at a local, throwaway Postgres.` (Task 1); the CI `backend-postgres` cycle (Task 14); `ROOT`-relative paths as in `test_ops_workflows.py`.
- Produces: `backend/migrations/README.md` with the sections `## How it is wired`, `## Rules for a new revision`, `## Local development`, `## Tests`, `## Production runbook (slice 1a)` (`### Step 0: RLS precondition` … `### Step 10: Streamlit smoke check`), `## RLS precondition`, `## Postgres major`, `## Reverting`. Later users: Task 25 (the reference `upgrade.sql` hash), Task 26 (steps 0-7), Task 27 (steps 8-10 and the records PR); slice 1b appends manual items 2-11 under `## Slice 1`.
- Produces: `backend/tests/test_slice1_docs.py` (5 tests).

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_slice1_docs.py`:

```python
"""Slice 1a docs: the Alembic production runbook in backend/migrations/README.md,
the ops-runbook health-check lines, the README's Alembic notes and the manual
"Slice 1" checks (slice 1 spec → Production runbook, Local dev, Manual checks
item 1; F §3.3, §5.5).

Text is compared whitespace-collapsed (`_flat`), so rewrapping a paragraph
never breaks a test; fenced output blocks are compared exactly.
"""
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]   # repo root
MIGRATIONS_README = ROOT / "backend" / "migrations" / "README.md"
RUNBOOK = ROOT / "docs" / "ops-runbook.md"
README = ROOT / "README.md"
MANUAL_VERIFICATION = ROOT / "docs" / "manual-verification.md"
BACKUP_YML = ROOT / ".github" / "workflows" / "backup.yml"

RUNBOOK_STEPS = (
    "### Step 0: RLS precondition",
    "### Step 1: Backup",
    "### Step 2: Server version",
    "### Step 3: Nothing is stamped yet",
    "### Step 4: Stamp the baseline",
    "### Step 5: Read the SQL the upgrade will run",
    "### Step 6: Drift check",
    "### Step 7: Railway settings, immediately before merging",
    "### Step 8: Merge and watch the deploy",
    "### Step 9: Confirm head",
    "### Step 10: Streamlit smoke check",
)
OWNER_COMMANDS = (
    "../.venv/bin/pip install -r ../requirements-dev.txt",
    "IFS= read -rs DATABASE_URL && export DATABASE_URL",
    "../.venv/bin/alembic current",
    "../.venv/bin/alembic stamp 0001_baseline",
    "../.venv/bin/alembic upgrade 0001_baseline:head --sql > upgrade.sql",
    "../.venv/bin/python scripts/schema_drift.py",
    "../.venv/bin/alembic check",
    "../.venv/bin/alembic upgrade head",
    "unset DATABASE_URL",
)
# schema_drift.py's stdout on production right after stamping (sorted lines;
# db.schema_check.format_diff). "add_index ix_hymns_church_hymnal" follows only
# if production lacks that index.
DRIFT_AT_BASELINE = (
    "revision: 0001_baseline head: 0004_invites_reusable state: behind\n"
    "add_column invites.accepted_by\n"
    "add_column invites.reusable\n"
    "add_fk fk_invites_accepted_by_users\n"
)
DRIFT_AT_HEAD = "revision: 0004_invites_reusable head: 0004_invites_reusable state: current\n"
LOCKDOWN_REFUSAL = (
    "0003_lockdown: role % has no BYPASSRLS and does not own: %. Enabling RLS would hide "
    'their rows from the app. See migrations/README.md "RLS precondition".'
)


def _read(path):
    return path.read_text(encoding="utf-8")


def _flat(text):
    """The text with every run of whitespace collapsed to one space."""
    return " ".join(text.split())


def _section(text, heading):
    """The body of `heading` up to the next heading of the same level."""
    level = heading.split(" ", 1)[0]
    return text.split(f"\n{heading}\n", 1)[1].split(f"\n{level} ", 1)[0]


def test_migrations_readme_has_the_production_runbook_steps():
    text = _read(MIGRATIONS_README)
    runbook = _section(text, "## Production runbook (slice 1a)")
    assert re.findall(r"^### Step \d+: .+$", runbook, re.MULTILINE) == list(RUNBOOK_STEPS)
    for command in OWNER_COMMANDS:
        assert command in runbook, command
    assert DRIFT_AT_BASELINE in runbook
    assert DRIFT_AT_HEAD in runbook
    flat = _flat(runbook)
    for needle in (
        "add_index ix_hymns_church_hymnal",
        "`/backend/railway.toml`",
        "Healthcheck Path",
        "`/health/ready`",
        '"reason": "schema_behind"',
        "No new upgrade operations detected.",
        "0004_invites_reusable (head)",
        "Target database is not up to date.",
        "BEGIN;",
        "SET LOCAL lock_timeout = '5s';",
        "SET LOCAL statement_timeout = '60s';",
        "COMMIT;",
        "gh workflow run db-backup --ref main",
        "https://liturgy-frozen.streamlit.app/",
        "Create invite",
        "relation",
        "already exists",
    ):
        assert needle in flat, needle
    assert "liturgy-next" not in text


def test_migrations_readme_records_the_rls_precondition_and_pg_major():
    text = _read(MIGRATIONS_README)
    section = _flat(_section(text, "## RLS precondition"))
    for needle in (
        "select tablename, tableowner from pg_tables where schemaname = 'public' order by 1;",
        "select current_user, rolbypassrls from pg_roles where rolname = current_user;",
        "owner of every `public` table: `postgres`",
        "`current_user`, `rolbypassrls`: `postgres`, `true`",
        "2026-09-25",
        "ALTER TABLE public.<t> OWNER TO <app role>;",
        "CREATE POLICY app_all ON public.<t> TO <app role> USING (true) WITH CHECK (true);",
        LOCKDOWN_REFUSAL,
    ):
        assert needle in section, needle
    reverting = _flat(_section(text, "## Reverting"))
    for needle in ("Never downgrade production below `0003_lockdown`",
                   "../.venv/bin/alembic downgrade 0003_lockdown",
                   "Config-as-code"):
        assert needle in reverting, needle
    majors = re.findall(r"^Server major recorded for slice 1a: (\d+) ", text, re.MULTILINE)
    pg_major = str(yaml.safe_load(_read(BACKUP_YML))["jobs"]["dump"]["env"]["PG_MAJOR"])
    assert majors == [pg_major]


def test_ops_runbook_health_check_lines_name_health_ready():
    text = _read(RUNBOOK)
    environments = _flat(_section(text, "## Environments and variables"))
    for needle in ("`/backend/railway.toml`", "Healthcheck Path", "`/health/ready`",
                   "alembic upgrade head", "backend/migrations/README.md"):
        assert needle in environments, needle
    keep_alive = _flat(_section(text, "## Keep-alive"))
    for needle in ("deploy health check", "`schema_behind`", "backend/migrations/README.md"):
        assert needle in keep_alive, needle
    flat = _flat(text)
    for stale in ("(slice 1 moves it to `/health/ready`)",
                  "slice 1 moves the deploy check to `/health/ready`"):
        assert stale not in flat, stale
    # Dated records are history: slice 1a edits none of them in place.
    for record in (
        "Checked against Railway → the API service → Variables (names only) and "
        "Settings → Deploy → Healthcheck Path:",
        "Healthcheck Path `/health` (already set).",
        "-- Defense in depth; slice 1's 0003_lockdown repeats this idempotently.",
        "slice 1 decides between transferring table ownership and adding policies",
    ):
        assert record in flat, record


def test_manual_verification_has_the_slice_1_section():
    text = _read(MANUAL_VERIFICATION)
    assert re.findall(r"^## .+$", text, re.MULTILINE)[-2:] == ["## Ops slice", "## Slice 1"]
    section = _flat(_section(text, "## Slice 1"))
    for needle in (
        "https://worship-service-builder.vercel.app",
        "375 px",
        "step 0",
        "`/backend/railway.toml`",
        "pre-deploy",
        "alembic upgrade head",
        "`/health/ready`",
        "0004_invites_reusable (head)",
        "No new upgrade operations detected.",
        "`/welcome`",
        "No church yet",
        "not a 404",
        "Log out",
        "https://liturgy-frozen.streamlit.app",
        "Create invite",
    ):
        assert needle in section, needle
    assert "liturgy-next" not in section
    assert section.count("- [ ] ") == 3
    assert "- [x]" not in section


def test_readme_documents_alembic_for_local_dev():
    text = _read(README)
    database = _flat(_section(text, "## Database"))
    for needle in (
        "../.venv/bin/alembic upgrade head",
        "../.venv/bin/alembic stamp 0001_baseline && ../.venv/bin/alembic upgrade head",
        "sqlite:///../data/app.db",
        "TEST_DATABASE_URL",
        "pytest -m postgres",
        "backend/migrations/README.md",
        "backend/railway.toml",
    ):
        assert needle in database, needle
    deploying = _flat(text.split("**Deploying:**", 1)[1].split("\n## ", 1)[0])
    for needle in ("`/backend/railway.toml`", "`/health/ready`", "alembic upgrade head"):
        assert needle in deploying, needle
    assert "health check `/health`)" not in deploying
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_slice1_docs.py 2>&1 | tail -3
```

Expected: `5 failed`. The two `test_migrations_readme_*` tests fail with `FileNotFoundError: … backend/migrations/README.md`; `test_ops_runbook_health_check_lines_name_health_ready` with `AssertionError: `/backend/railway.toml``; `test_manual_verification_has_the_slice_1_section` with `assert ['## Slice 0 ...## Ops slice'] == ['## Ops slice', '## Slice 1']`; `test_readme_documents_alembic_for_local_dev` with `AssertionError: ../.venv/bin/alembic upgrade head`.

- [ ] **Step 3: Create `backend/migrations/README.md`**

````markdown
# Database migrations (Alembic)

Since slice 1a, Alembic owns the database schema. The API no longer creates
tables at startup (`db.init_db()` stays only for the frozen Streamlit app, the
CLIs and the test fixtures). On Railway, `backend/railway.toml` runs
`alembic upgrade head` as the pre-deploy command, and in production
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
  `NNNN_short_slug.py`. Head is `0004_invites_reusable`.

| Revision | What it does |
|---|---|
| `0001_baseline` | The 11 tables of `db/models.py`, including `text_year` and `hymnal_count` on `hymns` and `hymn_catalog`, and `ix_hymns_church_hymnal`. Runs only on fresh databases (CI, new local dev); production is stamped at it. |
| `0002_reconcile` | Guarded adds: `ix_hymns_church_hymnal` (`IF NOT EXISTS`) and the two hymn-facts columns on both hymn tables, only where missing. A no-op on production and on fresh databases; it fixes a stamped local database made before PR #4. |
| `0003_lockdown` | Postgres only: row-level security on every `public` table (after the precondition below), and the REVOKEs from `anon` and `authenticated`. Idempotent after the ops lockdown of 2026-09-25. |
| `0004_invites_reusable` | `invites.reusable` (NOT NULL, default false; existing code-only invites become reusable) and `invites.accepted_by` with the FK `fk_invites_accepted_by_users` (`ON DELETE SET NULL`). |

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
  `hymnal_count` on `hymns` and `hymn_catalog`), no-ops on production;
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

Railway → the project → the API service → Settings:

1. Config-as-code → Railway config file: `/backend/railway.toml`. Railway
   reads this path from the repository root, not from the service's root
   directory (`backend`). Save.
2. Deploy → Healthcheck Path: `/health/ready` (it was `/health`). Save.

`backend/railway.toml` sets `preDeployCommand = ["alembic upgrade head"]` and
`healthcheckPath = "/health/ready"`; the start command stays in
`backend/Procfile`. The UI Healthcheck Path is the safety net if Railway ever
ignores the file. Set both immediately before merging, so the merge deploy is
the first to read them. The release serving now is not affected: it has had
`/health/ready` since ops-3.

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
- There is no pre-deploy step at all: Railway did not read
  `/backend/railway.toml`. The new release then starts on a database still at
  `0001_baseline`: its startup logs `schema revision 0001_baseline != head
  0004_invites_reusable` at ERROR, and `/health/ready` answers 503
  `db_unavailable` with `"reason": "schema_behind"`, so the UI Healthcheck
  Path of step 7 fails the deploy. If that health check did not apply either,
  the release is live on a schema behind head (harmless in 1a, which serves
  no route that reads the new `invites` columns). Either way, at once: the
  laptop setup, `../.venv/bin/alembic upgrade head` (the same three
  `Running upgrade` lines), `unset DATABASE_URL`; fix step 7 and redeploy.

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
  ops lockdown. To back out `0004` alone, while no deployed code reads its
  columns: the laptop setup, then
  `../.venv/bin/alembic downgrade 0003_lockdown`, then `unset DATABASE_URL`.
- To revert the 1a release: first clear Railway → the API service →
  Settings → Config-as-code (after a revert `/backend/railway.toml` no longer
  exists, and what Railway does with a path to a missing file is unverified).
  Keep the UI Healthcheck Path `/health/ready`: the code before 1a has served
  that route since ops-3. Then revert the merge commit on `main` through a PR
  (the owner's yes). The schema stays at `0004_invites_reusable`; every 1a
  change is expand-only, so the older code runs on it.
````

- [ ] **Step 4: Edit `docs/ops-runbook.md` in place (two sentences)**

Lines 23-24 (Environments and variables → **Railway, the API service.**). Replace

```markdown
deploy health check: Settings → Deploy → Healthcheck Path `/health` (slice 1
moves it to `/health/ready`). With it, a deployment whose process never answers
```

with

```markdown
deploy health check: `/health/ready` since slice 1a, set in
`backend/railway.toml` (Settings → Config-as-code path `/backend/railway.toml`)
and in Settings → Deploy → Healthcheck Path. The same file runs
`alembic upgrade head` as the pre-deploy command
(`backend/migrations/README.md`). With it, a deployment whose process never answers
```

The next line, `(for example the `APP_ENV` guard refusing to start) is not promoted and the`, is unchanged context. The dated line 41 (`2026-09-26: the names match this table … Healthcheck Path `/health` (already set). …`) stays as it is.

Lines 317-318 (Keep-alive, the paragraph about `GET /health/ready`). Replace

```markdown
`GET /health` stays the dependency-free liveness probe and Railway's deploy
health check; slice 1 moves the deploy check to `/health/ready`.
```

with

```markdown
`GET /health` stays the dependency-free liveness probe. Since slice 1a
`/health/ready` is also Railway's deploy health check, and in production it
answers 503 `db_unavailable` with `details.reason` `schema_behind` while the
database schema is behind the release (`backend/migrations/README.md`).
```

Nothing else in the runbook changes: no new `##` or `###` heading and no `[owner` marker.

- [ ] **Step 5: Edit `README.md` (three places)**

Lines 29-31 ("Run locally"). Replace

```markdown
Copy `backend/.env.example` → `backend/.env` and `frontend/.env.example` →
`frontend/.env.local` first. Tests: `.venv/bin/python -m pytest -q` (backend and
Streamlit) and `cd frontend && npm test`.
```

with

```markdown
Copy `backend/.env.example` → `backend/.env` and `frontend/.env.example` →
`frontend/.env.local` first. The API does not create tables: create or update
the local database with
`(cd backend && DATABASE_URL=sqlite:///../data/app.db ../.venv/bin/alembic upgrade head)`
the first time and after pulling a new migration (a `data/app.db` made before
slice 1a needs `../.venv/bin/alembic stamp 0001_baseline` once first, with the
same `DATABASE_URL`; see Database → Schema migrations). Tests: `.venv/bin/python -m pytest -q` (backend and
Streamlit) and `cd frontend && npm test`.
```

Line 35 (`**Deploying:**`). Replace

```markdown
- **Railway** (service root `backend`, health check `/health`): env
```

with

```markdown
- **Railway** (service root `backend`; Config-as-code path
  `/backend/railway.toml`, which runs `alembic upgrade head` before each
  deploy and sets the deploy health check `/health/ready`): env
```

Line 119 (`## Database`). After the line `Store `DATABASE_URL` in Streamlit secrets (App → Settings → Secrets).` and before the blank line that precedes `## One-time migration (Notion + legacy contacts → database)`, insert (with one blank line before it):

````markdown
### Schema migrations (Alembic)

Since slice 1a the schema comes from Alembic (`backend/alembic.ini`,
`backend/migrations/`), and the API no longer creates tables at startup: it
logs the WARNING `schema revision <current> != head <head>` when the database
is not at the latest revision. Alembic reads only an exported `DATABASE_URL`,
never `backend/.env`. For a local database, from `backend/`:

```bash
cd backend
export DATABASE_URL=sqlite:///../data/app.db
../.venv/bin/alembic upgrade head
```

A local database made by the old `create_all` (before slice 1a) needs stamping first:
`../.venv/bin/alembic stamp 0001_baseline && ../.venv/bin/alembic upgrade head`.
Tests build their SQLite databases themselves. The Postgres-only tests run
with `TEST_DATABASE_URL` set to a local, throwaway Postgres
(`TEST_DATABASE_URL=postgresql://postgres:<password>@localhost:5432/postgres .venv/bin/python -m pytest -m postgres -q`
from the repo root) and skip without it. Production is migrated by Railway's
pre-deploy command (`backend/railway.toml`); the one-time stamping runbook and
the details are in `backend/migrations/README.md`.
````

- [ ] **Step 6: Append `## Slice 1` to `docs/manual-verification.md`**

After line 67 (the `keep-awake` item, the last line of `## Ops slice` and of the file), append one blank line and then:

```markdown
## Slice 1

Run on the production URLs: https://worship-service-builder.vercel.app (at
375 px in Chrome device mode, iPhone SE, and on desktop),
https://church-production-74ca.up.railway.app, and
https://liturgy-frozen.streamlit.app, the production Streamlit app. Record
each result, with its date, in `docs/ops-runbook.md` → Supabase lockdown
record → "Alembic stamping record (slice 1a)". The items marked "(after 1a)"
come from `backend/migrations/README.md` → Production runbook; slice 1b
appends its own items here.

- [ ] (after 1a) Runbook step 0 (RLS precondition) rerun and recorded; Railway's Config-as-code path is `/backend/railway.toml` and its Healthcheck Path is `/health/ready`; the merge deploy's log shows the **pre-deploy** `alembic upgrade head` (`0001_baseline -> 0002_reconcile`, `-> 0003_lockdown`, `-> 0004_invites_reusable`) and a passing `/health/ready` health check; `alembic current` shows `0004_invites_reusable (head)` and `alembic check` prints `No new upgrade operations detected.` (outputs pasted in the 1a PR).
- [ ] (after 1a) A new Google account signing in right after the 1a merge lands on the stub `/welcome` ("No church yet"), not a 404, and **Log out** returns it to `/login`; at 375 px and on desktop.
- [ ] (after 1a) Streamlit smoke check on https://liturgy-frozen.streamlit.app (F §6.3): sign in, the church and hymnal load, a saved service loads, Settings opens; Settings → Invites → **Create invite** works (the frozen app's insert gets `reusable = false`), then revoke that invite.
```

The boxes stay unchecked: this is a reusable checklist (results go in the runbook). Slice 1b appends manual items 2-11 below these (clarification 20).

- [ ] **Step 7: Run the tests, the docs guards and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_slice1_docs.py backend/tests/test_ops_workflows.py backend/tests/test_docs.py backend/tests/test_foundation_setup.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
grep -c 'liturgy-next' backend/migrations/README.md
git diff --stat
```

Expected: all pass (the new 5, plus the unchanged runbook, README and manual-verification guards: `test_runbook_has_the_seven_sections_in_order`, `test_runbook_keep_alive_section_names_the_variable_and_the_endpoint`, `test_manual_verification_has_the_ops_slice_checklist`, `test_readme_keep_alive_paragraph_describes_the_readiness_curl`, `test_readme_documents_multiuser_ops`, `test_manual_verification_checklist_exists`); then `697 passed, 5 skipped`; `4`, the same as `git show origin/main:docs/ops-runbook.md | grep -n '\[owner' | grep -v 'An entry marked' | wc -l` (1a adds no owner marker; `20` was the count at `7978a5e`); `0`; and `git diff --stat` lists exactly 3 files (`README.md`, `docs/manual-verification.md`, `docs/ops-runbook.md`); the 2 new files are still untracked. The frontend is untouched in this task (still `122 passed`).

- [ ] **Step 8: Commit**

```bash
git add backend/migrations/README.md backend/tests/test_slice1_docs.py \
        docs/ops-runbook.md README.md docs/manual-verification.md
git commit -m "Docs: Alembic production runbook, /health/ready deploy check, local-dev migrations, Slice 1 checks (S runbook, Local dev, Manual checks 1; F §3.3, §5.5)

backend/migrations/README.md holds runbook steps 0-10 for this machine
(../.venv/bin/alembic from backend/, DATABASE_URL read with read -s, step 0
in the SQL Editor, step 1 as a db-backup run), the RLS precondition with the
2026-09-25 answer (postgres owns every table and has BYPASSRLS), the Postgres
major, and the revert path. The ops runbook's two 'slice 1 moves it'
sentences now name /health/ready and railway.toml; dated records are
unchanged. Production Streamlit is liturgy-frozen.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 25: Full verification, local smoke, the reference `upgrade.sql`, and the slice 1a pull request (owner's yes before the push)

The whole branch is checked in one place before anyone reviews it: both suites, the frontend build (route-group conflicts and `"use client"` + `metadata` errors only show in `next build`), the two generated files, the acceptance greps, the exact list of changed paths, a real Alembic + uvicorn run on SQLite, and the offline `upgrade.sql` that the owner compares in Task 26 (runbook step 5, `backend/migrations/README.md`, Task 24). Then, on the owner's yes, the agent pushes the Tasks 15–24 commits to the draft PR that Task 14 opened, turns it into the real PR and marks it ready for review once CI is green. Merging is not part of this task (Task 27, its own yes).

`origin/main` may have moved since the branch was cut: on 2026-09-27 it is at `560ebb3` (freeze records PRs #14 and #15: `docs/ops-runbook.md`, `docs/manual-verification.md`, constants in `backend/tests/test_ops_workflows.py`, `keep-awake.yml`; no test added or removed, so every total below still holds). Step 1 merges it if the branch is behind.

Below, `<scratch>` is the absolute path of the session's scratchpad directory (any empty temp directory will do); write it out literally in each command. `<N>` is the draft PR's number from Task 14, Step 9.

**Files:** none changed (the plan is already the branch's first commit). A CI failure is fixed in the owning task's files (Step 14), never here.

**Interfaces:**
- Consumes: everything from Tasks 1–24, in particular: `backend/alembic.ini` + `migrations/env.py` (Task 5: the URL from the exported `DATABASE_URL`, `Database: dialect=… driver=… host=… database=…` on stderr, `BEGIN;` + the two `SET … timeout` lines + `COMMIT;` offline); revisions `0001_baseline` → `0002_reconcile` → `0003_lockdown` → `0004_invites_reusable` (Tasks 6–9); `backend/scripts/schema_drift.py` (Task 10: `revision: <current> head: <head> state: <state>`, exit 0 at head); the startup WARNING `schema revision None != head 0004_invites_reusable` from logger `db.schema_check` (Task 11); `backend/scripts/export_openapi.py` (Task 13: prints `Wrote <path>`); `npm run gen:api` (Task 15); CI step names `Migrate the empty database to head`, `The models match the migrated schema`, `Every revision downgrades`, `Migrate to head again`, `Identity smoke (ops-2)`, `Postgres-only tests` (Task 14) and `API types match the OpenAPI snapshot (F §5.4)` (Task 15); draft PR `<N>` on `claude/slice-1-plan` (Task 14, Step 9); the runbook step 5 checks in `backend/migrations/README.md` (Task 24).
- Produces:
  - PR `<N>` (`claude/slice-1-plan` → `main`), titled `Slice 1a platform: Alembic migrations, error contract, idempotency, route guards, frontend foundations`, not a draft, CI green on the branch head. Later users: Task 26 (reads the reference hash from its body, adds the runbook outputs), Task 27 (merges it).
  - The reference offline render `<scratch>/slice1a-upgrade-reference.sql` of `alembic upgrade 0001_baseline:head --sql`, and its SHA-256 in the PR body line `Reference upgrade.sql (runbook step 5, rendered offline from <short sha>): SHA-256 <64 hex>`. Later user: Task 26 (the owner's `shasum -a 256 upgrade.sql` must print the same hash; any change to a revision after this task means re-rendering it, Step 14).

- [ ] **Step 1: Bring the branch up to date with `origin/main` (agent)**

```bash
git status --short
git fetch origin
git rev-list --count HEAD..origin/main
git log --oneline -1 origin/main
```

Expected, in order: `?? .claude/`; the fetch prints nothing or only updated refs; `0`; `560ebb3 Merge pull request #15 from bbrown62450/claude/ops-3-freeze-records-b` (or a later merge the owner made).
- If the count is not `0`: `git merge origin/main -m "Merge origin/main into claude/slice-1-plan (Task 25)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`. On a conflict (most likely in `docs/ops-runbook.md`, `docs/manual-verification.md` or `backend/tests/test_ops_workflows.py`), run `git merge --abort`, stop and tell the owner which files conflict: the dated records on `main` must not be edited by a merge resolution the owner has not seen. Without a conflict, continue: Steps 2–4 rerun both suites on the merged tree.
- If `git status --short` shows anything besides `?? .claude/`, stop: commit it in its owning task or ask the owner.

- [ ] **Step 2: Run the backend suite and the Postgres marker count**

```bash
.venv/bin/python -m pytest -q | tail -1
.venv/bin/python -m pytest -q -m postgres | tail -1
```

Expected: `697 passed, 5 skipped in …s` (baseline 559, +142, −4; the five skips are the `@pytest.mark.postgres` tests without `TEST_DATABASE_URL`); then `5 skipped, 697 deselected in …s` (exactly five tests carry the marker: Task 8's three, Task 11's one, Task 14's one). Any other number: stop and find the task whose count drifted (each task's last run step states its cumulative total).

- [ ] **Step 3: Run the frontend tests, types and lint**

```bash
(cd frontend && npm test && npm run typecheck && npm run lint)
```

Expected: Vitest's summary ` Test Files  23 passed (23)` and `      Tests  122 passed (122)` (the two projects together: `unit` and `dom`; 23 files = the unchanged `latest.test.ts` and `church.test.ts` plus the 21 new test files of Tasks 15–23; 15 → 122); `tsc --noEmit` prints nothing; `eslint` prints nothing. The command exits 0.

- [ ] **Step 4: Build the frontend with CI's placeholder environment**

```bash
(cd frontend && NEXT_PUBLIC_SUPABASE_URL=https://ci-placeholder.supabase.co NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build)
(cd frontend && node -e 'const m = require("./.next/app-path-routes-manifest.json"); console.log(Object.values(m).sort().join(" "))')
```

Expected: the build prints `✓ Compiled successfully`, runs `tsc`, generates the static pages and ends with its route table, with no `Error:` line (in particular no "You cannot have two parallel pages that resolve to the same path" and no "You are attempting to export "metadata" from a component marked with "use client""); then exactly:

```
/ /_global-error /_not-found /auth/callback /favicon.ico /login /welcome
```

(`/` now comes from `(signed-in)/(church)/page.tsx` and `/welcome` from `(signed-in)/welcome/page.tsx`; `src/app/page.tsx` is gone.) The build downloads the Geist fonts through `next/font/google`; if it fails only with `Failed to fetch` for a font (no network), say so in the Step 9 message and rely on CI's `frontend` job, which runs the same build (Step 13 checks it).

- [ ] **Step 5: Check that the generated files match the code**

```bash
.venv/bin/python backend/scripts/export_openapi.py && git diff --exit-code --stat frontend/src/lib/api/openapi.json; echo "openapi diff exit $?"
(cd frontend && npm run gen:api) && git diff --exit-code --stat frontend/src/lib/api/schema.d.ts; echo "schema diff exit $?"
git status --short
```

Expected: `Wrote /Users/…/frontend/src/lib/api/openapi.json` and `openapi diff exit 0`; openapi-typescript's `🚀 src/lib/api/openapi.json → src/lib/api/schema.d.ts` line and `schema diff exit 0`; then only `?? .claude/`. A non-zero exit means an API change was committed without regenerating: rerun the same command, commit both generated files in the task that changed the API (Step 14's rule), and start again at Step 2.

- [ ] **Step 6: Run the acceptance checks**

```bash
(cd backend && ../.venv/bin/python -c "import sys, api.main, api.idempotency, domain_errors, usecases, db.schema_check; print(sorted(m for m in sys.modules if m.split('.')[0] == 'streamlit'))")
grep -rnE '^\s*(from|import) (fastapi|starlette|streamlit)' backend/domain_errors.py backend/db backend/usecases; echo "grep exit $?"
grep -rnE '^\s*(from|import) api(\.|\s|$)' backend/db; echo "grep exit $?"
ls backend/migrate_add_hymnal.py backend/migrate_add_hymn_facts.py backend/tests/test_migrate_hymn_facts.py 2>&1 | grep -c "No such file"
(cd backend && ../.venv/bin/alembic heads)
(cd backend && ../.venv/bin/alembic history) | grep -oE '^.* -> [0-9a-z_]+( \(head\))?'
git diff origin/main...HEAD -- backend/migrations/README.md README.md docs/manual-verification.md docs/ops-runbook.md | grep '^+' | grep -v '^+++' | grep -c 'liturgy-next'
for r in origin/main HEAD; do git show "$r:docs/ops-runbook.md" | grep -n '\[owner' | grep -v 'An entry marked' | wc -l; done
git diff --name-only origin/main...HEAD | grep -E '(^|/)\.env' ; echo "env files: $?"
```

Expected, in order:
- `[]` (the API, the idempotency store, the domain errors, the usecases package and the schema checks pull in no Streamlit; AC16 first half);
- no output and `grep exit 1` (`domain_errors.py`, `db/` and `usecases/` import no FastAPI, Starlette or Streamlit; F §2.2);
- no output and `grep exit 1` (`db/` never imports `api/`; `migrations/env.py` is outside `db/`);
- `3` (the one-off schema scripts and their test are gone; AC18);
- `0004_invites_reusable (head)` (a single head; `heads` does not run `env.py`, so there is no `Database:` line);
- exactly these four lines:
  ```
  0003_lockdown -> 0004_invites_reusable (head)
  0002_reconcile -> 0003_lockdown
  0001_baseline -> 0002_reconcile
  <base> -> 0001_baseline
  ```
- `0` (no added line in the user-facing docs names `liturgy-next`; production Streamlit is https://liturgy-frozen.streamlit.app/, owner answer Q1);
- the same number twice (`4` at `560ebb3`): 1a adds no `[owner` marker to the runbook; its records go in Task 27's records PR;
- `env files: 1` (grep found nothing: no `.env` file is on the branch).

- [ ] **Step 7: Check the exact list of changed paths**

```bash
LC_ALL=C sort > "<scratch>/slice1a-expected-paths.txt" <<'EOF'
.github/workflows/ci.yml
README.md
backend/alembic.ini
backend/api/deps.py
backend/api/errors.py
backend/api/idempotency.py
backend/api/main.py
backend/api/routes/health.py
backend/api/routes/me.py
backend/api/routes/rubric.py
backend/api/schemas.py
backend/backfill_hymn_facts.py
backend/db/ids.py
backend/db/models.py
backend/db/schema_check.py
backend/domain_errors.py
backend/migrate_add_hymn_facts.py
backend/migrate_add_hymnal.py
backend/migrations/README.md
backend/migrations/env.py
backend/migrations/script.py.mako
backend/migrations/versions/0001_baseline.py
backend/migrations/versions/0002_reconcile.py
backend/migrations/versions/0003_lockdown.py
backend/migrations/versions/0004_invites_reusable.py
backend/railway.toml
backend/requirements.txt
backend/scripts/export_openapi.py
backend/scripts/schema_drift.py
backend/tests/api_helpers.py
backend/tests/conftest.py
backend/tests/pg_helpers.py
backend/tests/test_api_app.py
backend/tests/test_ci_workflow.py
backend/tests/test_domain_errors.py
backend/tests/test_error_registry.py
backend/tests/test_foundation_setup.py
backend/tests/test_health_ready.py
backend/tests/test_idempotency.py
backend/tests/test_identity.py
backend/tests/test_ids.py
backend/tests/test_isolation.py
backend/tests/test_migrate_hymn_facts.py
backend/tests/test_migrations.py
backend/tests/test_models.py
backend/tests/test_no_network.py
backend/tests/test_no_streamlit_in_core.py
backend/tests/test_openapi_contract.py
backend/tests/test_ops_workflows.py
backend/tests/test_pg_helpers.py
backend/tests/test_route_guards.py
backend/tests/test_schema_check.py
backend/tests/test_slice1_docs.py
backend/tests/test_startup.py
backend/usecases/__init__.py
docs/manual-verification.md
docs/ops-runbook.md
docs/superpowers/plans/2026-09-26-slice-1a-platform.md
docs/superpowers/specs/2026-09-25-migration-foundations-design.md
frontend/eslint.config.mjs
frontend/package-lock.json
frontend/package.json
frontend/src/app/(signed-in)/(church)/church-layout.test.tsx
frontend/src/app/(signed-in)/(church)/layout.tsx
frontend/src/app/(signed-in)/(church)/page.tsx
frontend/src/app/(signed-in)/layout.tsx
frontend/src/app/(signed-in)/signed-in-layout.test.tsx
frontend/src/app/(signed-in)/welcome/page.tsx
frontend/src/app/(signed-in)/welcome/welcome.test.tsx
frontend/src/app/layout.tsx
frontend/src/app/page.tsx
frontend/src/app/providers.tsx
frontend/src/components/app-header.tsx
frontend/src/components/app/account-menu.tsx
frontend/src/components/app/app-header.test.tsx
frontend/src/components/app/app-header.tsx
frontend/src/components/app/church-switcher.tsx
frontend/src/components/app/confirm-dialog.test.tsx
frontend/src/components/app/confirm-dialog.tsx
frontend/src/components/app/empty-state.test.tsx
frontend/src/components/app/empty-state.tsx
frontend/src/components/app/error-state.test.tsx
frontend/src/components/app/error-state.tsx
frontend/src/components/app/page-header.test.tsx
frontend/src/components/app/page-header.tsx
frontend/src/components/app/pending-button.test.tsx
frontend/src/components/app/pending-button.tsx
frontend/src/components/ui/alert-dialog.tsx
frontend/src/components/ui/alert.tsx
frontend/src/components/ui/button.test.tsx
frontend/src/components/ui/button.tsx
frontend/src/components/ui/combobox.tsx
frontend/src/components/ui/input.tsx
frontend/src/components/ui/label.tsx
frontend/src/components/ui/tabs.tsx
frontend/src/lib/api.test.ts
frontend/src/lib/api.ts
frontend/src/lib/api/client.test.ts
frontend/src/lib/api/client.ts
frontend/src/lib/api/errors.test.ts
frontend/src/lib/api/errors.ts
frontend/src/lib/api/openapi.json
frontend/src/lib/api/schema.d.ts
frontend/src/lib/api/timeouts.ts
frontend/src/lib/api/types.ts
frontend/src/lib/auth.test.ts
frontend/src/lib/auth.ts
frontend/src/lib/church-context.tsx
frontend/src/lib/church-store.test.tsx
frontend/src/lib/church.test.ts
frontend/src/lib/church.ts
frontend/src/lib/me-context.tsx
frontend/src/lib/queries/auth-events.ts
frontend/src/lib/queries/church.ts
frontend/src/lib/queries/client.test.ts
frontend/src/lib/queries/client.ts
frontend/src/lib/queries/keys.test.ts
frontend/src/lib/queries/keys.ts
frontend/src/lib/queries/me.ts
frontend/src/lib/storage.test.ts
frontend/src/lib/storage.ts
frontend/src/lib/urls.test.ts
frontend/src/lib/urls.ts
frontend/src/lib/use-sign-out.test.tsx
frontend/src/test/fake-api.ts
frontend/src/test/fixtures/index.ts
frontend/src/test/lint-rules.test.ts
frontend/src/test/mocks.ts
frontend/src/test/render.tsx
frontend/src/test/setup-dom.test.tsx
frontend/src/test/setup-dom.ts
frontend/vitest.config.ts
pytest.ini
EOF
git diff --name-only --no-renames origin/main...HEAD | LC_ALL=C sort > "<scratch>/slice1a-actual-paths.txt"
wc -l < "<scratch>/slice1a-expected-paths.txt"
wc -l < "<scratch>/slice1a-actual-paths.txt"
LC_ALL=C comm -3 "<scratch>/slice1a-expected-paths.txt" "<scratch>/slice1a-actual-paths.txt"
```

Expected: `133`; `133` plus the number of registry-dependency files Task 20 recorded (its `npx shadcn@latest add` may create files beyond the six named components; Task 20 names them in its commit message); and `comm` prints nothing, or only tab-indented lines (in the diff, not in the list) under `frontend/src/components/ui/` or `frontend/src/hooks/` that Task 20 recorded. Check each such line with `git log --format='%h %s' origin/main..HEAD -- '<that path>'`: it must print only Task 20's commit. The 133 are this plan's File Structure list: the outline's 131, the F §1.5 amendment (owner answer Q2) and `backend/usecases/__init__.py` (Task 2). Any other line (a path missing from the diff, or an unexpected path such as `app.py`, `ui_helpers.py`, `streamlit_tenancy.py`, `backend/db/engine.py`, `backend/api/startup.py`, `backend/Procfile`, `backend/tests/pg_smoke.py`, `frontend/src/lib/latest.ts` or a workflow other than `ci.yml`): stop and find the task that touched it.

- [ ] **Step 8: Render the reference `upgrade.sql` and run the local smoke**

First the offline SQL the owner will render in runbook step 5 (Task 26). Offline mode never connects, so the made-up URL only selects the PostgreSQL dialect and the psycopg2 driver (the same ones `db.engine._normalize_url` gives the production URL); the URL never appears in the SQL:

```bash
(cd backend && DATABASE_URL=postgresql://u:p@localhost:1/x ../.venv/bin/alembic upgrade 0001_baseline:head --sql > "<scratch>/slice1a-upgrade-reference.sql" 2> "<scratch>/slice1a-upgrade-reference.err")
grep 'Database:' "<scratch>/slice1a-upgrade-reference.err"
F="<scratch>/slice1a-upgrade-reference.sql"; head -1 "$F"; grep -c "SET LOCAL lock_timeout = '5s'" "$F"; grep -c "SET LOCAL statement_timeout = '60s'" "$F"; grep -c 'CREATE TABLE' "$F"; grep -c 'ADD COLUMN IF NOT EXISTS' "$F"; grep -c 'CREATE INDEX IF NOT EXISTS ix_hymns_church_hymnal' "$F"; grep -c '0003_lockdown: role % has no BYPASSRLS and does not own: %' "$F"; grep -c '%%' "$F"; grep -c 'fk_invites_accepted_by_users' "$F"; grep -c 'UPDATE alembic_version' "$F"; grep -c 'Database:' "$F"; grep -v '^$' "$F" | tail -1; shasum -a 256 "$F"
```

Expected: `Database: dialect=postgresql driver=psycopg2 host=localhost database=x`; then `BEGIN;`, `1`, `1`, `0`, `4`, `1`, `1`, `0`, `1`, `3`, `0`, `COMMIT;` (the same checks as runbook step 5, plus the 0002 index, 0003's first RAISE text with single `%` (named paramstyle) and 0004's FK); then `<64 hex>  <scratch>/slice1a-upgrade-reference.sql`. Keep the 64 hex characters: Step 10 puts them in the PR body. (`grep -c` exits 1 when it counts `0`; that is expected here.)

Then Alembic on a real SQLite file, the way the owner and Railway run it (the CLI reads the exported `DATABASE_URL`; `load_dotenv()` in `api.main` never overrides a variable set on the command line, and `env.py` does not read `backend/.env` at all):

```bash
rm -f "<scratch>/slice1a-smoke.db" "<scratch>/slice1a-fresh.db"
(cd backend && DATABASE_URL="sqlite:///<scratch>/slice1a-smoke.db" ../.venv/bin/alembic upgrade head 2>&1 | grep -oE '^Database: .*|Running upgrade .* -> [0-9a-z_]+')
(cd backend && DATABASE_URL="sqlite:///<scratch>/slice1a-smoke.db" ../.venv/bin/alembic current 2>/dev/null)
(cd backend && DATABASE_URL="sqlite:///<scratch>/slice1a-smoke.db" ../.venv/bin/alembic check 2>/dev/null)
(cd backend && DATABASE_URL="sqlite:///<scratch>/slice1a-smoke.db" ../.venv/bin/python scripts/schema_drift.py 2>/dev/null; echo "exit $?")
```

Expected, exactly (`<scratch>` expanded):

```
Database: dialect=sqlite driver=pysqlite host=- database=<scratch>/slice1a-smoke.db
Running upgrade  -> 0001_baseline
Running upgrade 0001_baseline -> 0002_reconcile
Running upgrade 0002_reconcile -> 0003_lockdown
Running upgrade 0003_lockdown -> 0004_invites_reusable
0004_invites_reusable (head)
No new upgrade operations detected.
revision: 0004_invites_reusable head: 0004_invites_reusable state: current
exit 0
```

Now the API on the migrated file. The agent's shell blocks a foreground `sleep` and keeps no `&` jobs between commands, so start the server with the Bash tool's `run_in_background: true`:

```bash
DATABASE_URL="sqlite:///<scratch>/slice1a-smoke.db" APP_ENV=development \
  .venv/bin/python -m uvicorn --app-dir backend api.main:app --port 8765 > "<scratch>/slice1a-uvicorn.log" 2>&1
```

Wait for it with a Monitor until-loop whose condition is `curl -sf localhost:8765/health >/dev/null` (up within a few seconds; if the Monitor times out, read `<scratch>/slice1a-uvicorn.log`). Then, as one foreground command:

```bash
curl -s localhost:8765/health/ready; echo
curl -s localhost:8765/nope; echo
curl -s -X POST localhost:8765/health; echo
grep -E 'Database:|schema revision|Row-level security|Traceback' "<scratch>/slice1a-uvicorn.log"
```

Expected:

```
{"ok":true,"db":"ok"}
{"error":{"code":"not_found","message":"Not Found","request_id":"<32 hex>"}}
{"error":{"code":"method_not_allowed","message":"Method Not Allowed","request_id":"<32 hex>"}}
api.main INFO request_id=- Database: dialect=sqlite driver=pysqlite host=- database=<scratch>/slice1a-smoke.db
```

(no `fields`/`details` keys when absent; no `schema revision` line, because the database is at head; no RLS line, because the RLS check runs on Postgres only). Stop the server: stop the background task (TaskStop), or `pkill -f 'api.main:app --port 8765'`.

Then the same server on a file nothing has migrated (AC3: the lifespan creates no tables and warns). Start it again with `run_in_background: true`:

```bash
DATABASE_URL="sqlite:///<scratch>/slice1a-fresh.db" APP_ENV=development \
  .venv/bin/python -m uvicorn --app-dir backend api.main:app --port 8765 > "<scratch>/slice1a-uvicorn-fresh.log" 2>&1
```

Wait with the same Monitor condition, then:

```bash
curl -s localhost:8765/health/ready; echo
grep -E 'schema revision|ERROR' "<scratch>/slice1a-uvicorn-fresh.log"
.venv/bin/python -c "import sqlite3; print(sqlite3.connect('<scratch>/slice1a-fresh.db').execute(\"select count(*) from sqlite_master where type = 'table'\").fetchone()[0])"
```

Expected:

```
{"ok":true,"db":"ok"}
db.schema_check WARNING request_id=- schema revision None != head 0004_invites_reusable
0
```

(`/health/ready` stays 200 outside production: the `schema_behind` gate is production-only and is covered by Task 12's tests, because `APP_ENV=production` refuses SQLite at startup. No `ERROR` line.) Stop the server as before.

- [ ] **Step 9 (agent → OWNER): Ask for the go-ahead to push and to mark the PR ready**

Pushing the branch again, rewriting the PR and marking it ready for review are outward-facing; Task 14's authorization (owner answer Q5) covered only the draft checkpoint. Count the new commits and find the PR:

```bash
git rev-list --count origin/claude/slice-1-plan..HEAD
gh pr list -R bbrown62450/church --head claude/slice-1-plan --state open --json number,isDraft,url
```

Expected: a positive count (the commits of Tasks 15–24, plus any merge from Step 1); one PR with `"isDraft":true` (Task 14). If the list is `[]` (Task 14's checkpoint did not open one), Step 10 creates the PR instead of editing it.

Send the owner exactly this message, with `<count>` and `<N>` replaced by the values above, and wait for a clear yes:

> Slice 1a is verified locally: backend 697 passed, 5 skipped; frontend 122 passed; typecheck, lint and build clean; OpenAPI and API types in sync; changed paths as planned; Alembic upgrade/check and the API smoke OK on SQLite. May I (1) push `claude/slice-1-plan` (<count> new commits), (2) retitle draft PR #<N> to "Slice 1a platform: Alembic migrations, error contract, idempotency, route guards, frontend foundations" and replace its body, and (3) mark it ready for review once CI is green? Merging stays with you (Tasks 26 and 27).

Do only what the owner approves. A yes to (1) and (2) without (3) leaves the PR a draft after Step 13.

- [ ] **Step 10 (agent, on the owner's yes): Push, and update or open the PR**

```bash
git push origin claude/slice-1-plan
```

Expected: `<old sha>..<new sha>  claude/slice-1-plan -> claude/slice-1-plan`. If the push is rejected, stop and tell the owner; never force-push.

Write the body (quoted heredoc, so the backticks stay literal), then the `sed` below replaces its `@REF_COMMIT@` and `@REF_SHA@` markers with the commit and the reference hash:

```bash
cat > "<scratch>/slice1a-pr-body.md" <<'EOF'
PR 1a of slice 1: the platform. Spec: docs/superpowers/specs/2026-09-25-slice-1-onboarding-design.md (1a). Plan: docs/superpowers/plans/2026-09-26-slice-1a-platform.md. No onboarding flow yet: creating and joining a church ship in 1b.

Backend
- Test guards: autouse no-network fixture, `postgres` marker, `pg_db` on a local-only `TEST_DATABASE_URL`; pins fastapi 0.141.*, pydantic 2.13.*, alembic>=1.20, tzdata>=2026.4 (F §5.1).
- `domain_errors.py` (DomainError family, `RateLimited`, `ERROR_CODES` with 29 codes: F §1.5 plus `bad_request` and `method_not_allowed`, with the F §1.5 amendment row), `db/ids.py::as_uuid`, the `usecases/` package (F §2.2, §1.5).
- Error body gains `fields` (Pydantic 422 mapping) and `details`; DomainError handler; 429 with `Retry-After`; `require_church` 403 carries `details.reason = "no_church_access"`; `ErrorBody` documented on every route; `Page[T]`, `ItemList[T]`, `ChurchOut.role` literal (F §1.3-1.5).
- `api/idempotency.py`: Idempotency-Key store, 15-minute replay, `idempotency_mismatch` (F §1.6).
- Alembic: `alembic.ini`, `migrations/env.py` (stderr `Database:` line, lock and statement timeouts, one transaction), `0001_baseline`, `0002_reconcile`, `0003_lockdown` (RLS; refuses a role without BYPASSRLS or ownership), `0004_invites_reusable` (+ `Invite.reusable`, `Invite.accepted_by`); `migrate_add_hymnal.py`, `migrate_add_hymn_facts.py` and their test deleted (F §3).
- `db/schema_check.py` + `scripts/schema_drift.py`; the API lifespan no longer runs `create_all`; startup revision and RLS checks; `/health/ready` 503 `db_unavailable` with `details.reason = "schema_behind"` in production; `backend/railway.toml` (pre-deploy `alembic upgrade head`, health check `/health/ready`; inert until the Config-as-code path is set in Task 26) (F §2.6).
- Route-guard walker, cross-church isolation tests (`GET /church`, `GET`/`PATCH /rubric`), OpenAPI export + contract test (`frontend/src/lib/api/openapi.json`), no-Streamlit import test (F §1.2, §1.11, §2.2).
- CI `backend-postgres`: alembic upgrade → check → downgrade base → upgrade, the ops-2 smoke, then `pytest -m postgres` (0003's refusals and idempotence, the RLS check, concurrent first sign-ins) (F §5.4).

Frontend
- Vitest `unit` + `dom` projects, Testing Library, a fake API, `react/no-danger`, `gen:api` (`schema.d.ts` from the committed `openapi.json`; CI fails on drift) (F §5.2, §1.11).
- `lib/api/{client,errors,timeouts,types}.ts`: timeouts, `requestId`, the full error union, kept equal to `ERROR_CODES` by `test_error_registry.py` (F §4.5).
- TanStack Query layer (`useApi`, `keys`, `useMe`, `useChurchProfile`, auth events); `lib/{auth,storage,urls,church,church-context,me-context}`; sign-out is local-scope and clears the query cache, the stored church and the `wsb:` keys, with no refetch or re-store while signing out (F §4.2-4.4).
- UI kit (`EmptyState`, `ErrorState`, `PendingButton`, `ConfirmDialog`, `PageHeader`; generated `input`, `label`, `tabs`, `alert`, `alert-dialog`, `combobox`; button `touch` size); `AppHeader`, `ChurchSwitcher`, `AccountMenu` (F §4.8, §4.9).
- Route groups: `(signed-in)` layout (`MeContext`, 401 → local sign-out), stub `/welcome` ("No church yet"), `(church)` layout (active-church resolution, keyed remount on switch, 403 `no_church_access` fallback with a toast); `src/app/page.tsx` and `components/app-header.tsx` removed (F §4.1-4.4).

Docs: `backend/migrations/README.md` (production runbook steps 0-10, RLS precondition, local development), README Alembic notes, the `docs/ops-runbook.md` health-check lines, manual checks "Slice 1".

Tests: backend +142 (+5 Postgres-only), −4 (697 passed, 5 skipped); frontend 15 → 122

Reference upgrade.sql (runbook step 5, rendered offline from @REF_COMMIT@): SHA-256 @REF_SHA@

Before merge: Task 26 (rerun the RLS precondition queries, backup run, server version, stamp `0001_baseline`, read `upgrade.sql` and compare its SHA-256 with the line above, drift check, branch protection on `backend`, `backend-postgres` and `frontend`, Railway Config-as-code path `/backend/railway.toml` and Healthcheck Path `/health/ready`). After merge: Task 27 (pre-deploy `alembic upgrade head` in the deploy log, `alembic current` and `alembic check`, Streamlit smoke on https://liturgy-frozen.streamlit.app/, manual check 1, records PR). Production Streamlit runs from `streamlit-frozen` and is not deployed by this PR.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
SHA=$(shasum -a 256 "<scratch>/slice1a-upgrade-reference.sql" | cut -c1-64); COMMIT=$(git rev-parse --short HEAD); sed -i '' -e "s/@REF_SHA@/$SHA/" -e "s/@REF_COMMIT@/$COMMIT/" "<scratch>/slice1a-pr-body.md"; grep -c '@REF_' "<scratch>/slice1a-pr-body.md"; grep -n 'SHA-256' "<scratch>/slice1a-pr-body.md"
```

Expected: `0` (both markers replaced), then `…:Reference upgrade.sql (runbook step 5, rendered offline from <short sha>): SHA-256 <the 64 hex from Step 8>`.

If PR `<N>` exists (the usual case):

```bash
gh pr edit <N> -R bbrown62450/church \
  --title "Slice 1a platform: Alembic migrations, error contract, idempotency, route guards, frontend foundations" \
  --body-file "<scratch>/slice1a-pr-body.md"
gh pr view <N> -R bbrown62450/church --json title,isDraft,headRefOid --jq '"\(.title) | draft=\(.isDraft) | \(.headRefOid)"'
```

Expected: the edit prints the PR URL; the view prints `Slice 1a platform: Alembic migrations, error contract, idempotency, route guards, frontend foundations | draft=true | <the sha of git rev-parse HEAD>`.

If Step 9 found no PR, open it instead (not as a draft: it is ready once CI is green, which Step 13 checks before telling the owner):

```bash
gh pr create -R bbrown62450/church --base main --head claude/slice-1-plan \
  --title "Slice 1a platform: Alembic migrations, error contract, idempotency, route guards, frontend foundations" \
  --body-file "<scratch>/slice1a-pr-body.md"
```

Expected: `https://github.com/bbrown62450/church/pull/<N>`; use this `<N>` from here on.

- [ ] **Step 11: Watch the checks (agent)**

Run with the Bash tool's `run_in_background: true` (the watch can outlast the 10-minute foreground limit; the tool re-invokes the agent when it exits):

```bash
gh pr checks <N> -R bbrown62450/church --watch --interval 30
```

Expected when it exits: every check `pass`: `backend`, `backend-postgres`, `frontend`, and the Vercel preview deployment; exit code 0. If it exits at once with the previous head's results (the new run has not registered yet), run it again. Any `fail` goes to Step 14.

- [ ] **Step 12: Read the CI logs and compare (agent)**

```bash
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch claude/slice-1-plan --commit "$(git rev-parse HEAD)" --limit 1 --json databaseId --jq '.[0].databaseId'); echo "run $RUN"
gh run view "$RUN" -R bbrown62450/church --json jobs --jq '.jobs[] | "\(.name): \(.conclusion)"'
gh run view "$RUN" -R bbrown62450/church --json jobs --jq '.jobs[] | select(.name == "backend-postgres" or .name == "frontend") | .name as $j | .steps[] | "\($j) / \(.name): \(.conclusion)"'
JOB=$(gh run view "$RUN" -R bbrown62450/church --json jobs --jq '.jobs[] | select(.name == "backend") | .databaseId'); gh run view -R bbrown62450/church --job "$JOB" --log | grep -E "[0-9]+ passed"
JOB=$(gh run view "$RUN" -R bbrown62450/church --json jobs --jq '.jobs[] | select(.name == "backend-postgres") | .databaseId'); gh run view -R bbrown62450/church --job "$JOB" --log | grep -E "Running (upgrade|downgrade)|No new upgrade operations detected|pg_smoke: OK|[0-9]+ (passed|failed|errors?)( |,)"
JOB=$(gh run view "$RUN" -R bbrown62450/church --json jobs --jq '.jobs[] | select(.name == "frontend") | .databaseId'); gh run view -R bbrown62450/church --job "$JOB" --log | grep -E "Test Files +[0-9]+ passed|Tests +[0-9]+ passed|Compiled successfully"
```

(Shell variables do not carry between commands, so each line that needs `$RUN` or `$JOB` sets it itself; if the first line prints `run ` with no id, run it again.)

Expected:
- jobs: `backend: success`, `backend-postgres: success`, `frontend: success`;
- steps: every step `success`, including `backend-postgres / Migrate the empty database to head`, `… / The models match the migrated schema`, `… / Every revision downgrades`, `… / Migrate to head again`, `… / Identity smoke (ops-2)`, `… / Postgres-only tests`, and `frontend / API types match the OpenAPI snapshot (F §5.4)`;
- backend: `697 passed, 5 skipped in …s`;
- backend-postgres, in this order: the four `Running upgrade` lines (`  -> 0001_baseline` … `0003_lockdown -> 0004_invites_reusable`), `No new upgrade operations detected.`, the four `Running downgrade` lines (`0004_invites_reusable -> 0003_lockdown` … `0001_baseline -> `), the four upgrades again, `pg_smoke: OK`, `5 passed, 697 deselected in …s`;
- frontend: `Test Files  23 passed (23)`, `Tests  122 passed (122)`, `✓ Compiled successfully`.

- [ ] **Step 13 (agent, on the owner's yes to item 3): Mark the PR ready, and report**

Only when Steps 11–12 matched:

```bash
gh pr ready <N> -R bbrown62450/church
gh pr view <N> -R bbrown62450/church --json isDraft,state,url --jq '"draft=\(.isDraft) \(.state) \(.url)"'
```

Expected: `✓ Pull request bbrown62450/church#<N> is marked as "ready for review"`, then `draft=false OPEN https://github.com/bbrown62450/church/pull/<N>`. (CI does not rerun: `ci.yml`'s `pull_request` trigger uses the default activity types, which do not include `ready_for_review`.)

Report to the owner in one message: "PR #<N> (<url>) is ready for review: CI green (backend 697 passed, 5 skipped; backend-postgres Alembic cycle, `alembic check` clean, `pg_smoke: OK`, 5 passed; frontend 122 passed, build OK; Vercel preview OK). Reference `upgrade.sql` SHA-256: <64 hex> (also in the PR body). Next: Task 26, your runbook steps 0–7 before merging." If the owner did not approve item 3, say the PR stays a draft and ask again when they want it.

- [ ] **Step 14: Fix any failure in its owning task (agent)**

If Steps 2–8 or 11–12 did not match, read the failure (`gh run view <run-id> -R bbrown62450/church --log-failed | tail -80` for CI) and fix it in the task that owns it:

| Failing check or test | Owning task (files) |
|---|---|
| an Alembic step in `backend-postgres`, a `test_migrations.py` test, `alembic check` in Step 8 | Task 5 (`alembic.ini`, `migrations/env.py`, `db/schema_check.py` part 1), Tasks 6–9 (the revision in the last `Running upgrade`/`downgrade` line; `0004` also `db/models.py`) |
| `schema_drift.py`, `test_schema_check.py` | Task 10 |
| startup log lines, `test_startup.py`, `test_api_app.py::test_rls_check_names_tables_without_rls` | Task 11 |
| `/health/ready`, `railway.toml` | Task 12 |
| route guards, isolation, `openapi.json` drift, `export_openapi.py` | Task 13 (regenerate with `.venv/bin/python backend/scripts/export_openapi.py`, then `(cd frontend && npm run gen:api)`, and commit both) |
| `Identity smoke (ops-2)`, `test_identity.py` Postgres test, the CI step order | Task 14 |
| error bodies, `domain_errors.py`, `test_error_registry.py` | Tasks 2, 3, 16 |
| `schema.d.ts` drift, Vitest projects, `lint-rules.test.ts`, `setup-dom.test.tsx` | Task 15 |
| `lib/api/*` | Task 16 |
| `storage`, `urls`, `church` store | Task 17 |
| `lib/queries/*`, `auth.ts` token and flag, `church-context.tsx` | Task 18 |
| `useSignOut`, `me-context.tsx`, `providers.tsx`, `render.tsx` | Task 19 |
| `components/app/*` UI kit, `components/ui/*` | Task 20 |
| `AppHeader`, `ChurchSwitcher`, `AccountMenu` | Task 21 |
| `(signed-in)` layout, `/welcome`, a build error in those files | Task 22 |
| `(church)` layout and page, a route-group build error | Task 23 |
| `test_slice1_docs.py`, a docs guard in `test_ops_workflows.py` or `test_docs.py` | Task 24 |
| the Vercel preview only | report the preview's build log to the owner before changing anything |

For each fix: reproduce it locally first where SQLite, offline SQL, Vitest or the build can show it; change only the owning task's files; rerun Steps 2–5 (`697 passed, 5 skipped`; `122 passed`; clean types, lint, build and generated files); commit with the subject `Fix: <what> (Task <n>, slice 1a final verification)` and the trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, staging files by name; have that task re-reviewed (its plan section against the fix's diff); `git push origin claude/slice-1-plan` (covered by the owner's yes to item 1; never `--force`); repeat Steps 11–12. If the fix touched a file under `backend/migrations/` or `backend/db/models.py`, rerun Step 8's offline render, update the PR body's `Reference upgrade.sql` line with the new hash (`gh pr edit <N> -R bbrown62450/church --body-file …` after rerunning Step 10's `sed` on a fresh copy of the body) and tell the owner the new hash. An infrastructure failure with no test output (a service container that never became healthy, a timed-out `npm ci` or `pip install`) gets one `gh run rerun <run-id> -R bbrown62450/church --failed` before it counts as a failure.

Expected counts after this task: backend `697 passed, 5 skipped` locally (CI `backend-postgres`: `5 passed, 697 deselected`); frontend `122 passed` in 23 files. No commit unless Step 14 needed a fix.

---

### Task 26 (OWNER + agent, before merge): the Freeze gate, the RLS precondition, backup, stamping, `upgrade.sql`, drift, branch protection, the Railway config path (S runbook steps 0–7; F §5.4; AC2, AC4, AC18)

The spec's gate for PR 1a is the production runbook in `backend/migrations/README.md` (Task 24): the owner runs steps 0–7 from a laptop **before** the merge, step 7 immediately before it. This task walks through them in small pieces: the agent checks each answer against the expected output, and nothing is merged here (Task 27, Step 1, on its own yes). Order matters: the Freeze gate first (owner answer Q1: production Streamlit is https://liturgy-frozen.streamlit.app/, on `streamlit-frozen`, and the freeze records PRs #14 and #15 must be on `main`); the RLS precondition before anything is written; the backup before the stamp; the stamp (the only production write in this task: it creates and fills the new `alembic_version` table, which neither running app reads) before `upgrade.sql` and the drift check; and the Railway settings last, so the merge deploy is the first to read `/backend/railway.toml`. Runbook step 0 was answered on 2026-09-25 (`docs/ops-runbook.md` → Supabase lockdown record, step 2: every `public` table owned by `postgres`, `rolbypassrls` true); the owner reruns the two queries anyway (outline §1 row 15, README step 0) and the rerun is recorded.

The agent never sees or types a secret: the owner exports `DATABASE_URL` in their own terminal with `read -s`, reports outputs only (the `Database:` line carries no username or password), and says "present"/"missing" for anything secret. Dispatching the backup workflow, pushing, commenting on the PR and changing branch protection are outward-facing: each needs the owner's explicit yes, asked for at that step. If the merge is abandoned after the stamp, the stamp is harmless: leave it (no code on `main` reads `alembic_version`), and the runbook restarts at step 3 (which then shows `0001_baseline`).

Below, `<N>` is PR 1a's number (Task 14, Step 9; Task 25), `<scratch>` the absolute path of the session's scratchpad directory (written out literally in each command), `<checkout>` the path Step 2 prints, and `<date>` the day the owner did the step.

**Files:**
- None in the usual case. The results go in `<scratch>/slice1a-t26-results.md` (never committed), which Step 14 posts as a PR comment and Task 27, Step 10 turns into the runbook's `### Alembic stamping record (slice 1a)`.
- Only if Step 1 finds `origin/main` moved since Task 25: a merge commit (and, only on the known conflict, `docs/manual-verification.md` resolved as given there).
- Only if Step 10 finds an expand-safe drift line beyond the expected ones (Step 11): Modify `backend/migrations/versions/0002_reconcile.py` (`upgrade()`), Test `backend/tests/test_migrations.py` (append; for a missing column also the count in `test_offline_sql_from_baseline_renders_guarded_adds_and_no_create_table`), Modify `backend/migrations/README.md` (step 5's expected count, column case only).

**Interfaces:**
- Consumes:
  - PR `<N>` on `claude/slice-1-plan`, ready for review, CI green, with the body line `Reference upgrade.sql (runbook step 5, rendered offline from <short sha>): SHA-256 <64 hex>` (Task 25, Steps 8 and 10).
  - `backend/migrations/README.md` → `## Production runbook (slice 1a)`: the laptop setup (`../.venv/bin/pip install -r ../requirements-dev.txt`, `IFS= read -rs DATABASE_URL && export DATABASE_URL`, `unset DATABASE_URL`) and `### Step 0` … `### Step 7`, their expected outputs and stop conditions (Task 24).
  - `migrations/env.py`: `Database: dialect=… driver=… host=… database=…` on stderr, `BEGIN;` + `SET LOCAL lock_timeout = '5s';` + `SET LOCAL statement_timeout = '60s';` + `COMMIT;` offline, the exported `DATABASE_URL` only (Task 5); revisions `0001_baseline` → `0002_reconcile` → `0003_lockdown` → `0004_invites_reusable` (Tasks 6–9).
  - `backend/scripts/schema_drift.py`: stdout `revision: <current> head: <head> state: <state>` plus sorted `format_diff` lines; exit 0 (no diff), 1 (diff), 2 (`DATABASE_URL is not set.`) (Task 10).
  - `backend/railway.toml` (`preDeployCommand = ["alembic upgrade head"]`, `healthcheckPath = "/health/ready"`) (Task 12); the CI jobs `backend`, `backend-postgres`, `frontend` (`.github/workflows/ci.yml`, Tasks 14–15).
  - Step 11 only: in `backend/tests/test_migrations.py`, `_alembic(url, *args, **kw)` and fixture `sqlite_url` (Task 5), `_execute_on`, `_legacy_database`, `_tables_snapshot`, `_snapshot_columns`, `_models_diff` (Task 7); `0002_reconcile.upgrade()` as Task 7 wrote it.
- Produces:
  - Production: `alembic_version` = `0001_baseline`; branch protection on `main` requiring `backend`, `backend-postgres`, `frontend`; Railway → the API service: Config-as-code path `/backend/railway.toml`, Healthcheck Path `/health/ready`.
  - `<scratch>/slice1a-t26-results.md`: dated results of runbook steps 0–7 and the branch protection line. Later user: Task 27 (Step 10's records PR; Step 3 compares the deploy log with this task's Step 10 drift result).
  - One comment on PR `<N>` with the steps 0–6 results (S step 9: outputs in the PR).

- [ ] **Step 1 (agent): The PR, the Freeze gate, and `origin/main` in the branch**

```bash
git status --short
git fetch origin
git log -1 --format='%h %s' origin/main
git show origin/main:docs/ops-runbook.md | sed -n '/^### Freeze record$/,/^### Freeze policy$/p' | grep -c '\[owner'
git show origin/main:docs/ops-runbook.md | sed -n '/^### Freeze record$/,/^### Freeze policy$/p' | grep -c 'PR #14 merged'
git show origin/main:.github/workflows/keep-awake.yml | grep -c 'APP_URLS: "https://liturgy-frozen.streamlit.app/"'
git merge-base --is-ancestor origin/main HEAD; echo "main in branch: exit $?"
git rev-list --count origin/claude/slice-1-plan..HEAD
git rev-parse HEAD
gh pr list -R bbrown62450/church --head claude/slice-1-plan --state open --json number,isDraft,headRefOid,url
```

Expected, in order: `?? .claude/`; the fetch prints nothing or only updated refs; `560ebb3 Merge pull request #15 from bbrown62450/claude/ops-3-freeze-records-b` (or a later merge); `0` (every Freeze record row filled: records PR A, #14); `1` (the last row, records PR B, #15: the frozen app pulled nothing after #14 merged); `1` (`keep-awake` visits liturgy-frozen); `main in branch: exit 0` (Task 14 or Task 25 merged it); `0` (nothing unpushed); a 40-character sha; one PR with `"isDraft":false` and `headRefOid` equal to that sha.

- Any of the three Freeze checks differs: stop and tell the owner. PR 1a migrates the database the frozen app shares; it merges only after the Freeze and both records PRs (owner answer Q1).
- The PR is still a draft or its head differs: finish Task 25 first.
- `main in branch: exit 1` (someone merged to `main` after Task 25): merge it, without committing yet:

```bash
git merge --no-commit origin/main; git diff --name-only --diff-filter=U
```

  - No file listed: go to the commit below.
  - Exactly `docs/manual-verification.md` listed (the one conflict verified on 2026-09-27: `main`'s edits of the last `## Ops slice` lines touch the line after which Task 24 appends `## Slice 1`): take `main`'s file and re-append this branch's `## Slice 1` section, so no dated line of `main` changes:

```bash
git show origin/main:docs/manual-verification.md > docs/manual-verification.md
printf '\n' >> docs/manual-verification.md
git show HEAD:docs/manual-verification.md | sed -n '/^## Slice 1$/,$p' >> docs/manual-verification.md
git diff origin/main -- docs/manual-verification.md | grep '^[-+]' | grep -v '^+++\|^---' | grep -c '^-'
grep -c '^<<<<<<<\|^=======\|^>>>>>>>' docs/manual-verification.md
git add docs/manual-verification.md
```

    Expected: `0` (only added lines against `main`), `0` (no conflict markers).
  - Any other file listed: `git merge --abort`, stop, and tell the owner which files conflict (a dated record on `main` must not change in a resolution the owner has not seen).

  Then commit, rerun both suites, and ask before pushing:

```bash
git commit -m "Merge origin/main into claude/slice-1-plan before the slice 1a runbook (Task 26)" -m "Brings in main's changes since Task 25; no slice 1a file changes meaning." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
.venv/bin/python -m pytest -q | tail -1
(cd frontend && npm test 2>&1 | grep -E '^ +Tests ' ; npm run typecheck >/dev/null && npm run lint >/dev/null && echo "types+lint ok")
git diff --stat HEAD~1 HEAD -- backend/migrations backend/db/models.py | tail -1
```

  Expected: `697 passed, 5 skipped`; `Tests  122 passed (122)` and `types+lint ok`; the stat line prints nothing (no revision or model changed; if one did, Step 2's hash will differ and Step 2 says what to do). A different count: stop and find the cause before anything else. Ask the owner: "`main` moved after Task 25 (<the new `git log -1 origin/main` line>). I merged it into `claude/slice-1-plan` (<clean, or: the known `docs/manual-verification.md` conflict, resolved by keeping main's text and re-appending `## Slice 1`>); both suites pass. May I push it to PR #<N>?" On the yes: `git push origin claude/slice-1-plan` (never `--force`), then `gh pr checks <N> -R bbrown62450/church --watch --interval 30` → every check `pass` (`backend`, `backend-postgres`, `frontend`, the Vercel preview). A failure goes to its owning task (Task 25, Step 14's table).

- [ ] **Step 2 (agent): The checkout the owner will use, and the reference hash at this head**

The owner runs the laptop steps in this very checkout, because its `.venv` has Alembic (Task 1) and its code is the PR head. From here until Step 13, the agent does not switch branches, commit or edit files in it (Step 11 is the only exception, and it says when).

```bash
git rev-parse --show-toplevel
git rev-parse --short HEAD
ls .venv/bin/alembic .venv/bin/python
(cd backend && DATABASE_URL=postgresql://u:p@localhost:1/x ../.venv/bin/alembic upgrade 0001_baseline:head --sql 2>/dev/null) | shasum -a 256
gh pr view <N> -R bbrown62450/church --json body --jq '.body' | grep 'Reference upgrade.sql'
```

Expected: the absolute path of the checkout (this is `<checkout>`); the short sha; both files listed; `<64 hex>  -`; and the PR body line with the **same** 64 hex characters (offline mode never connects: the made-up URL only picks the PostgreSQL dialect and psycopg2, as `db.engine._normalize_url` does for the production URL, and it never appears in the SQL). If the two hashes differ, a revision changed after Task 25: follow Task 25, Step 14's last paragraph (re-render, update the PR body's `Reference upgrade.sql` line) before Step 7.

Start `<scratch>/slice1a-t26-results.md` with exactly these two lines (the values filled in):

```markdown
Slice 1a production runbook before merge (plan Task 26; `backend/migrations/README.md` → Production runbook), PR head `<short sha>`.

- Freeze gate, <today>: `origin/main` at `<git log -1 --format=%h origin/main>`; Freeze record complete (records PRs #14 and #15); `keep-awake` visits https://liturgy-frozen.streamlit.app/.
```

Tell the owner: "Task 26 starts: the runbook in `backend/migrations/README.md`, steps 0–7. Your laptop commands run in `<checkout>/backend`. First, three read-only queries in the Supabase SQL Editor (Step 3 below)."

- [ ] **Step 3 (OWNER): Supabase SQL Editor: runbook steps 0 and 2 (read-only)**

Supabase → project `worship-staging` → SQL Editor → New query. Paste and run **one query at a time** (the editor shows only the last statement's result). The editor runs as `postgres`, the role the pooler URL signs in as.

```sql
select tablename, tableowner from pg_tables where schemaname = 'public' order by 1;
```

```sql
select current_user, rolbypassrls from pg_roles where rolname = current_user;
```

```sql
select tablename from pg_tables where schemaname = 'public' and not rowsecurity order by 1;
```

```sql
SHOW server_version;
```

Tell the agent the date and, for each query: (1) the number of rows, and every `tableowner` that is not `postgres` (with its table), and any table name not in this list of 11: `churches`, `contacts`, `gmail_tokens`, `hymn_catalog`, `hymn_usage`, `hymns`, `invites`, `memberships`, `oauth_states`, `services`, `users`; (2) the one row; (3) the rows, or "no rows"; (4) the version. Nothing here is secret.

Expected: (1) 11 rows (those tables; the order depends on the collation), every owner `postgres`, and no `alembic_version` yet; (2) `postgres | true`; (3) no rows (the ops lockdown of 2026-09-25 enabled RLS on every table); (4) `17.6`, or another `17.x`.

- [ ] **Step 4 (agent): Decide step 0 and check the major**

```bash
grep -c 'PG_MAJOR: "17"' .github/workflows/backup.yml
grep -c 'image: postgres:17' .github/workflows/ci.yml
grep -n '^Server major recorded for slice 1a: ' backend/migrations/README.md
```

Expected: `1`; `1`; `…:Server major recorded for slice 1a: 17 (`server_version` 17.6 on 2026-09-25, …`.

- (1) and (2) as expected: the first branch of step 0 holds (the app role `postgres` owns every table and has BYPASSRLS), so `0003_lockdown`'s precondition will pass and RLS without policies hides no row from either app. Proceed.
- (1) shows a table not owned by `postgres`, or (2) shows `false`: **stop before stamping**. Tell the owner to follow `backend/migrations/README.md` → "RLS precondition" (the preferred fix is `ALTER TABLE public.<t> OWNER TO postgres;` run by the table's current owner, recorded with the before/after output), and to repeat Step 3 afterwards. The merge waits.
- (1) lists a table beyond the 11 but owned by `postgres`: proceed, and name it in the results (0003 enables RLS on it too; the drift check ignores tables the models do not declare).
- (3) lists tables: proceed (0003 enables RLS on them at the deploy); name them in the results.
- (4) is not `17.x`: stop. `docs/ops-runbook.md` → Platform limits says how `PG_MAJOR`, the CI image and the README line change together, in a separate PR first.

Append to the results file:

```markdown
- Step 0 (RLS precondition), <date>: `pg_tables` <n> rows, every `tableowner` `postgres`<; extra tables: …>; `current_user`, `rolbypassrls`: `postgres`, `true` → first branch, proceed (no ownership transfer, no policy). Tables without RLS before the stamp: <none | names>.
- Step 2 (server version), <date>: `server_version` `<17.x>` = `PG_MAJOR` 17 (`backup.yml`) = CI `postgres:17`.
```

- [ ] **Step 5 (OWNER, or the agent on the owner's yes): Runbook step 1, the backup**

Either Actions → **db-backup** → Run workflow → branch `main` → Run workflow; or say yes and the agent runs (it starts a workflow that reads the `backup` environment's secret):

```bash
gh workflow run db-backup --ref main -R bbrown62450/church
```

- [ ] **Step 6 (agent): Check the backup run**

```bash
gh run list -R bbrown62450/church --workflow db-backup --limit 1 --json databaseId,createdAt,event,status
```

The new run takes a few seconds to appear: if the listed run is older than the dispatch or its `event` is `schedule`, run the line again (no `sleep`). Then, with its `databaseId`:

```bash
gh run watch <run-id> --exit-status -R bbrown62450/church
gh api repos/bbrown62450/church/actions/runs/<run-id>/artifacts --jq '.artifacts[] | "\(.name) \(.size_in_bytes) expired=\(.expired)"'
gh run view <run-id> --log -R bbrown62450/church | grep -ciE 'postgres(ql)?://|pooler\.supabase\.com'
```

Expected: `"event":"workflow_dispatch"`; the watch ends with the run completing successfully (exit 0); `db-backup <bytes> expired=false` with more than 1024 bytes (the first run, on 2026-09-26, made 225,686); `0` (the log shows no URL or pooler host). The job also checked the server major against `PG_MAJOR` (a mismatch fails it). A failed run: stop, read `gh run view <run-id> --log-failed -R bbrown62450/church | tail -40`, and fix the backup before any stamp (`docs/ops-runbook.md` → Backups). Append:

```markdown
- Step 1 (backup), <date>: https://github.com/bbrown62450/church/actions/runs/<run-id>: green, artifact `db-backup` (<bytes> bytes, encrypted), expires <date + 30 days>; the log shows no URL or pooler host.
```

- [ ] **Step 7 (OWNER, laptop): Runbook steps 3–5: nothing stamped, stamp the baseline, read `upgrade.sql`**

In a **new** terminal (this shell only; the agent never sees the URL):

```bash
cd <checkout>/backend
../.venv/bin/pip install -r ../requirements-dev.txt
IFS= read -rs DATABASE_URL && export DATABASE_URL
```

At the `read` line paste the Supabase session-pooler URL (Railway → the API service → Variables → `DATABASE_URL`) and press Return; nothing is shown. Then run these one at a time, reading each output:

```bash
../.venv/bin/alembic current
```

Expected (stderr): `Database: dialect=postgresql driver=psycopg2 host=aws-….pooler.supabase.com database=postgres`, `INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.`, `INFO  [alembic.runtime.migration] Will assume transactional DDL.`, and **no revision line**. If the `Database:` line says `dialect=sqlite`, the variable is not exported: stop and repeat the `read` line. If a revision is printed, the database was stamped before: stop and tell the agent.

```bash
../.venv/bin/alembic stamp 0001_baseline
../.venv/bin/alembic current
```

Expected: the `Database:` and `INFO` lines, then `INFO  [alembic.runtime.migration] Running stamp_revision  -> 0001_baseline`; then `0001_baseline`.

```bash
../.venv/bin/alembic upgrade 0001_baseline:head --sql > upgrade.sql
```

Expected on the screen: only the stderr lines (the `Database:` line, `INFO` lines including three `Running upgrade …` lines); the SQL is in the file. Open `upgrade.sql` and read it: `BEGIN;`, the two `SET … timeout` lines, 0002's `CREATE INDEX IF NOT EXISTS ix_hymns_church_hymnal …` and four `ADD COLUMN IF NOT EXISTS`, 0003's `DO $$ … $$` block with the `REVOKE`s and `ALTER DEFAULT PRIVILEGES`, 0004's two `invites` columns, the FK `fk_invites_accepted_by_users` and the `UPDATE`, an `UPDATE alembic_version …` after each revision, `COMMIT;` last (README step 5 lists them in order). Then:

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

Keep the terminal open (the variable stays exported for Step 9). Tell the agent the date and, as text: the `Database:` line, the output of each `alembic` command, and the seven check lines. Nothing here is secret (the `Database:` line never contains the username or password).

- [ ] **Step 8 (agent): Compare steps 3–5 with the expected output**

Expected from the owner: the first `current` without a revision; `Running stamp_revision  -> 0001_baseline`; the second `current` = `0001_baseline`; the checks `BEGIN;`, `0`, `4`, `3`, `0`, `COMMIT;`; and the SHA-256 equal to Step 2's 64 hex characters (same commit, same SQL: the reference was rendered without a database). Any difference: stop, and ask the owner to rerun the `--sql` line and paste `upgrade.sql` itself (it holds no secret), then compare it with `(cd backend && DATABASE_URL=postgresql://u:p@localhost:1/x ../.venv/bin/alembic upgrade 0001_baseline:head --sql 2>/dev/null) > <scratch>/slice1a-upgrade-reference.sql` using `diff`. Append:

```markdown
- Steps 3–4 (stamp), <date>: `alembic current` before: no revision (`Database: dialect=postgresql driver=psycopg2 host=<pooler host> database=postgres`); `alembic stamp 0001_baseline`: `Running stamp_revision  -> 0001_baseline`; `alembic current` after: `0001_baseline`.
- Step 5 (`upgrade.sql`), <date>: read by the owner; checks `BEGIN;`, `0` CREATE TABLE, `4` ADD COLUMN IF NOT EXISTS, `3` UPDATE alembic_version, `0` Database:, `COMMIT;`; SHA-256 `<64 hex>`, equal to the reference rendered offline from `<short sha>`.
```

- [ ] **Step 9 (OWNER, laptop): Runbook step 6, the drift check**

In the same terminal:

```bash
../.venv/bin/python scripts/schema_drift.py; echo "exit $?"
unset DATABASE_URL
```

Close the terminal. Tell the agent the date and the output, exactly as printed (stdout and the `exit` line).

Expected:

```
revision: 0001_baseline head: 0004_invites_reusable state: behind
add_column invites.accepted_by
add_column invites.reusable
add_fk fk_invites_accepted_by_users
exit 1
```

plus `add_index ix_hymns_church_hymnal` after the `add_fk` line only if production lacks that index (0002 adds it). `exit 1` only means "differences found". (`alembic check` cannot run here: it refuses with `Target database is not up to date.`)

- [ ] **Step 10 (agent): Classify the drift output**

- Exactly the expected lines (with or without `add_index ix_hymns_church_hymnal`): proceed to Step 12. Record whether the index line appeared (Task 27: 0002 then creates it at the deploy; otherwise 0002 is a no-op on production).
- `text_year` or `hymnal_count` appears: stop. Production has had them since PR #4, so this is not the database PR #4 migrated: ask the owner to check which URL they pasted before anything else (AC18). The merge waits.
- `DATABASE_URL is not set.` and `exit 2`: the variable was not exported in that shell; the owner repeats Step 7's setup lines (not the stamp) and Step 9.
- Another `add_index <name>` line, or an `add_column <table>.<column>` line whose model column is nullable (`grep -n '<column>' backend/db/models.py` shows `nullable=True`, or no `nullable=` on a non-key column): expand-safe (F §3.4). Tell the owner what it is and go to Step 11.
- Anything else (`modify_type`, `modify_nullable`, `add_column` of a NOT NULL column, `add_table`, `remove_*`, `add_constraint`, `add_fk` other than `fk_invites_accepted_by_users`): **the merge is blocked** (S step 6, Risk 2). Tell the owner the lines and resolve each with them before going on; the stamp stays.

Append:

```markdown
- Step 6 (drift), <date>: `schema_drift.py` printed exactly: <the lines, in a fenced block>; `exit 1`. <`ix_hymns_church_hymnal` present in production (0002 is a no-op) | missing (0002 creates it at the deploy)>.
```

- [ ] **Step 11 (agent, only if Step 10 found an expand-safe extra line): Add it to `0002_reconcile`, then the owner repeats Steps 7–9 without the stamp**

Tell the owner first ("the agent now commits in `<checkout>`; do not run laptop commands until it says so"). For each extra line, write the test first. Tokens in angle brackets come from the drift line and `backend/db/models.py`: for `add_index <name>`, `grep -n '"<name>"' backend/db/models.py` shows `Index("<name>", "<col1>", "<col2>")` in the `__table_args__` of the class whose `__tablename__` is `<table>` (`unique=True` there means unique below too); for `add_column <table>.<column>`, the Postgres type is

```bash
PYTHONPATH=backend .venv/bin/python -c "from sqlalchemy.dialects import postgresql; from db.models import Base; print(Base.metadata.tables['<table>'].c['<column>'].type.compile(dialect=postgresql.dialect()))"
```

Append to the end of `backend/tests/test_migrations.py` (index case):

```python


def test_a_stamped_database_missing_<name>_gets_it(sqlite_url):
    # Production lacked <name> at runbook step 6 on <date> (plan Task 26).
    _legacy_database(sqlite_url)
    _execute_on(sqlite_url, "DROP INDEX <name>")
    assert "<name>" not in {name for name, _cols in _tables_snapshot(sqlite_url)["<table>"][1]}

    _alembic(sqlite_url, "stamp", "0001_baseline")
    _alembic(sqlite_url, "upgrade", "head")

    assert ("<name>", ("<col1>", "<col2>")) in _tables_snapshot(sqlite_url)["<table>"][1]
    assert _models_diff(sqlite_url) == []
```

or (column case; if `<column>` is in one of the model's indexes, add `_execute_on(sqlite_url, "DROP INDEX <that index>")` before the `DROP COLUMN`, and expect that index's `add_index` line in Step 9 too):

```python


def test_a_stamped_database_missing_<table>_<column>_gets_it(sqlite_url):
    # Production lacked <table>.<column> at runbook step 6 on <date> (plan Task 26).
    _legacy_database(sqlite_url)
    _execute_on(sqlite_url, "ALTER TABLE <table> DROP COLUMN <column>")
    assert "<column>" not in _snapshot_columns(_tables_snapshot(sqlite_url), "<table>")

    _alembic(sqlite_url, "stamp", "0001_baseline")
    _alembic(sqlite_url, "upgrade", "head")

    assert "<column>" in _snapshot_columns(_tables_snapshot(sqlite_url), "<table>")
    assert _models_diff(sqlite_url) == []
```

```bash
.venv/bin/python -m pytest -q backend/tests/test_migrations.py 2>&1 | tail -3
```

Expected: `1 failed` per new test, with `AssertionError` on the `in _tables_snapshot(...)` (index) or `in _snapshot_columns(...)` (column) line: 0002 does not add it yet.

Then edit `backend/migrations/versions/0002_reconcile.py`. Index case: replace

```python
def upgrade() -> None:
    op.create_index("ix_hymns_church_hymnal", "hymns", ["church_id", "hymnal"], if_not_exists=True)
```

with

```python
def upgrade() -> None:
    op.create_index("ix_hymns_church_hymnal", "hymns", ["church_id", "hymnal"], if_not_exists=True)
    # Production lacked it at runbook step 6 on <date> (plan Task 26).
    op.create_index("<name>", "<table>", ["<col1>", "<col2>"], if_not_exists=True)
```

(add `unique=True,` before `if_not_exists=True` for a unique model index). Column case: replace

```python
                op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} INTEGER")
        return
```

with

```python
                op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} INTEGER")
        # Production lacked it at runbook step 6 on <date> (plan Task 26).
        op.execute("ALTER TABLE <table> ADD COLUMN IF NOT EXISTS <column> <Postgres type>")
        return
```

and replace

```python
            if column not in existing:
                op.add_column(table, sa.Column(column, sa.Integer(), nullable=True))
```

with

```python
            if column not in existing:
                op.add_column(table, sa.Column(column, sa.Integer(), nullable=True))
    if "<column>" not in {c["name"] for c in inspector.get_columns("<table>")}:
        op.add_column("<table>", sa.Column("<column>", <the model column's type expression, as written in db/models.py>, nullable=True))
```

The downgrade stays a no-op (the object is part of 0001's schema; Task 7's comment explains why). Column case only, two counts move from 4 to 5: in `backend/tests/test_migrations.py`, replace `    assert sql.count("ADD COLUMN IF NOT EXISTS") == 4` with `    assert sql.count("ADD COLUMN IF NOT EXISTS") == 5`; in `backend/migrations/README.md` step 5, replace ``Expected: `BEGIN;`, `0`, `4`, `3`, `0`, `COMMIT;`, and the SHA-256`` with ``Expected: `BEGIN;`, `0`, `5`, `3`, `0`, `COMMIT;`, and the SHA-256`` and ``and four `ALTER TABLE … ADD COLUMN IF NOT EXISTS …` statements`` with ``and five `ALTER TABLE … ADD COLUMN IF NOT EXISTS …` statements (the fifth: `<table>.<column>`, found missing on <date>)``.

```bash
.venv/bin/python -m pytest -q backend/tests/test_migrations.py backend/tests/test_schema_check.py backend/tests/test_slice1_docs.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
(cd backend && DATABASE_URL=postgresql://u:p@localhost:1/x ../.venv/bin/alembic upgrade 0001_baseline:head --sql 2>/dev/null) | grep -c 'IF NOT EXISTS <name or column>'
git add backend/migrations/versions/0002_reconcile.py backend/tests/test_migrations.py
git commit -m "Migrations: 0002 adds <name, or table.column> where missing (production drift, runbook step 6; S Risk 2)" -m "Found by schema_drift.py on production after the stamp on <date>. Guarded with IF NOT EXISTS, a no-op on fresh databases (0001 creates it); the downgrade stays a no-op." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: all pass; `698 passed, 5 skipped` for one extra line (`697` + one per extra line); `1`; the commit. In the column case also `git add backend/migrations/README.md` before the commit. Then re-render the reference and update the PR (Task 25, Step 14's last paragraph: new hash in the body's `Reference upgrade.sql` line), ask the owner's yes to push, `git push origin claude/slice-1-plan`, and wait for `gh pr checks <N> -R bbrown62450/church --watch --interval 30` → all `pass` (the `backend-postgres` Alembic cycle runs the new 0002 on Postgres). Then tell the owner to repeat Step 7 **without** `alembic stamp` (its first `current` now prints `0001_baseline`; the new hash is the one in the PR body) and Step 9 (the drift output keeps the extra line: 0002 adds it at the deploy, and Step 10 now expects it).

- [ ] **Step 12 (OWNER, or the agent on the owner's yes): Branch protection on `main` requires all three CI jobs (F §5.4, AC4)**

First the agent reads what `main` has now (read-only):

```bash
gh api repos/bbrown62450/church/branches/main/protection --jq '"checks=\(.required_status_checks.contexts // [] | sort | join(",")) strict=\(.required_status_checks.strict) pr=\(.required_pull_request_reviews != null) admins=\(.enforce_admins.enabled)"'
gh api repos/bbrown62450/church/rules/branches/main --jq '[.[].type] | sort | join(",")'
```

It answers either with a `checks=…` line (a classic rule exists) or `Branch not protected (HTTP 404)`; the second line prints the ruleset rule types on `main`, or an empty line.

GitHub → `bbrown62450/church` → Settings → Branches:
- If a classic rule for `main` exists: Edit it. Otherwise: Add classic branch protection rule, Branch name pattern `main`.
- Tick "Require status checks to pass before merging"; search for and select `backend`, `backend-postgres` and `frontend` (the `ci` workflow's jobs; all three run on every pull request).
- Recommended: also tick "Require branches to be up to date before merging". Two open PRs that each add a revision after `0004_invites_reusable` would otherwise both pass CI and merge into two Alembic heads, and the next pre-deploy `alembic upgrade head` would fail; with it, the second PR must merge `main` first, and `test_migrations.py`'s single-head test catches it. Leave it unticked if you prefer: say so.
- A new rule: also tick "Require a pull request before merging" and **untick "Require approvals"** (you are the only reviewer). Leave "Do not allow bypassing the above settings" unticked on `main`, so a broken CI runner can never lock you out of an urgent revert (a normal `gh pr merge` still refuses while a required check is failing or pending). An existing rule: change nothing else.
- Save changes / Create.

If the second command printed rule types (a ruleset covers `main`): add the three checks in that ruleset instead (Settings → Rules → Rulesets → the ruleset → Require status checks to pass → Add checks), and tell the agent.

Alternatively, only when the first command answered `Branch not protected`, the agent runs this on your explicit yes (it changes repository settings; `strict` follows your answer above):

```bash
gh api -X PUT repos/bbrown62450/church/branches/main/protection --input - <<'JSON'
{
  "required_status_checks": {"strict": true, "contexts": ["backend", "backend-postgres", "frontend"]},
  "enforce_admins": false,
  "required_pull_request_reviews": {"required_approving_review_count": 0},
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
```

If the owner left "Require branches to be up to date" unticked, send the same JSON with `"strict": false`.

Tell the agent the date, and whether you ticked "up to date".

- [ ] **Step 13 (agent): Verify the protection (read-only)**

```bash
gh api repos/bbrown62450/church/branches/main/protection --jq '"checks=\(.required_status_checks.contexts // [] | sort | join(",")) strict=\(.required_status_checks.strict) pr=\(.required_pull_request_reviews != null) admins=\(.enforce_admins.enabled)"'
gh pr checks <N> -R bbrown62450/church --required
```

Expected: `checks=backend,backend-postgres,frontend strict=true pr=true admins=false` for a new rule (`strict=false` if the owner left "up to date" unticked; an edited existing rule keeps its own `pr=`/`admins=`); then three rows, `backend`, `backend-postgres` and `frontend`, each `pass`. If the PR shows a required check as `pending` or `expected` forever, a name does not match the job: the owner reselects it from the search list. Under a ruleset, the first command answers `Branch not protected (HTTP 404)` and `gh pr checks … --required` is the check. Append:

```markdown
- Branch protection on `main`, <date>: required checks `backend`, `backend-postgres`, `frontend` (<classic rule | ruleset>; up to date required: <yes|no>); `gh pr checks <N> --required` lists all three, passing.
```

- [ ] **Step 14 (agent, on the owner's yes): Post the pre-merge results on the PR**

```bash
cat <scratch>/slice1a-t26-results.md
grep -ciE 'postgres(ql)?://|password|pooler\.supabase\.com:[0-9]' <scratch>/slice1a-t26-results.md
```

Expected: the lines appended in Steps 2–13; `0` (no URL, password or pooler host:port; the bare host name in the `Database:` line is not a secret, and the ops runbook already names it). Show the file to the owner and ask: "May I post these results as a comment on PR #<N> (S step 9: the step 5 and step 6 outputs go in the PR)?" On the yes:

```bash
gh pr comment <N> -R bbrown62450/church --body-file <scratch>/slice1a-t26-results.md
```

Expected: `https://github.com/bbrown62450/church/pull/<N>#issuecomment-<id>`.

- [ ] **Step 15 (OWNER, immediately before the merge): Runbook step 7, the Railway settings**

Do this only when you are about to merge (Task 27, Step 1: a weekday, when the tester is not using the app), so the merge deploy is the first to read the file. Railway → the project → the API service → Settings:

1. Config-as-code → Railway config file → `/backend/railway.toml` → Save. Railway reads the path from the repository root, not from the service's root directory (`backend`).
2. Deploy → Healthcheck Path → `/health/ready` (it was `/health`) → Save.
3. If Railway shows its staged-changes banner (as it did for the ops-3 variables), click **Deploy** and watch Deployments. That redeploys the release serving now (the pre-1a commit on `main`, which has no `backend/railway.toml` yet). Either outcome is safe: (a) the deployment becomes Active (its health check `/health/ready` passes: that route exists since ops-3), or (b) it fails, for example because the config file is not found, and the previous deployment keeps serving. Note which one, with any message: it also answers what Railway does with a path to a missing file, which `backend/migrations/README.md` → Reverting leaves unverified. Any other failure: stop and tell the agent before merging.

Trigger no other deployment before the merge. Tell the agent the date and time, both values as Railway now shows them, and whether a staged Deploy ran and its outcome ((a) or (b), with the message).

- [ ] **Step 16 (agent): Last checks, then hand over to Task 27**

These are public, read-only requests:

```bash
curl -s https://church-production-74ca.up.railway.app/health/ready; echo
curl -s https://church-production-74ca.up.railway.app/health; echo
gh pr view <N> -R bbrown62450/church --json isDraft,mergeable,mergeStateStatus,headRefOid --jq '"draft=\(.isDraft) \(.mergeable) \(.mergeStateStatus) \(.headRefOid)"'
git rev-parse HEAD
```

Expected: `{"ok":true,"db":"ok"}` (the pre-1a release answers the new health check path); `{"ok":true}`; `draft=false MERGEABLE CLEAN <sha>` with `<sha>` equal to `git rev-parse HEAD` (`BEHIND` instead of `CLEAN` means `main` moved and "up to date" is required: repeat Step 1, then Step 2; Steps 7–10 need repeating only if a revision changed, which Step 2's hash shows. `UNSTABLE` means a check that is not required, such as the Vercel preview, is not green: look at it with `gh pr checks <N> -R bbrown62450/church` before merging). If `/health/ready` fails, the Step 15 redeploy went wrong: Railway → Deployments → the previous deployment → ⋮ → Redeploy, and stop. Append to the results file (not posted; Task 27 records it):

```markdown
- Step 7 (Railway), <date time>: Config-as-code path `/backend/railway.toml`; Healthcheck Path `/health/ready` (was `/health`); staged Deploy of the pre-1a release: <not needed | (a) Active | (b) failed: <message>>; `/health/ready` → `{"ok":true,"db":"ok"}` afterwards.
```

Tell the owner: "Runbook steps 0–7 are done (results posted on PR #<N>; the Railway line is kept for the records PR). Production is stamped at `0001_baseline`, and Railway will run `alembic upgrade head` before the merge deploy. Next is Task 27, Step 1: may I merge PR #<N> now (`gh pr merge --merge`)?"

Expected counts after this task: backend `697 passed, 5 skipped` locally (plus one test per Step 11 fix, if any; CI `backend-postgres`: `5 passed`), frontend `122 passed`. No commit in the usual case (a merge commit only if Step 1 needed one; a `Migrations: 0002 …` commit only if Step 11 ran).

---

### Task 27: Merge and after (OWNER + agent): merge, deploy checks, `alembic check`, Streamlit smoke, manual check 1, records (S runbook steps 8–10; AC2, AC3, AC17)

The spec's runbook ends at the merge: step 8 (the merge deploy runs `alembic upgrade head` as Railway's pre-deploy command and passes the `/health/ready` health check), step 9 (`alembic current` at head, `alembic check` clean now that it is valid) and step 10 (the Streamlit smoke check, with an invite created in Streamlit). This task merges PR 1a straight after Task 26, Step 15 saved the Railway settings (the spec: "immediately before merging, so the merge deploy is the first to read it"), watches that deploy, runs the after-merge checks on the production URLs, and records everything in one docs-only records PR, as ops-3 did (plan conventions: dated records live in `docs/ops-runbook.md`; `docs/manual-verification.md` stays a reusable checklist with unchecked boxes). Production Streamlit is https://liturgy-frozen.streamlit.app/ on branch `streamlit-frozen` (owner answer Q1): the merge does not reach it and it needs no reboot, but it shares the database, so its smoke check is the proof that the new columns, RLS and `alembic_version` do not break it (F §6.3).

Below, `<N>` is PR 1a's number (Task 25), `<scratch>` the absolute path of the session's scratchpad directory (write both out literally in each command), and every `gh` command names the repository with `-R bbrown62450/church`. Pushing, commenting on or merging a PR, running a workflow and every Railway, Supabase or GitHub settings change need the owner's explicit yes, asked for each one; the agent never sees a database URL or any other secret, and nothing below is recorded with a database URL, password, database host name or invite code.

**Files:**
- Merge (Steps 1–2): no file changes; PR `<N>` (`claude/slice-1-plan` → `main`) merges with a merge commit.
- Create (not committed): `<scratch>/slice1a-steps-8-9.md` (the PR comment, Step 5)
- Modify (records PR, Step 9, branch `claude/slice-1a-records` from `origin/main` after the merge): `docs/ops-runbook.md` → `## Supabase lockdown record` (append `### Alembic stamping record (slice 1a)` after the `**Rollback:**` paragraph, right before `## Backups`; about line 190 of `origin/main` after the merge) and `### Backup run record` (append one table row)
- Revert path only (Step R): a branch `claude/revert-slice-1a` from `origin/main` holding `git revert -m 1` of the merge commit (every path of Task 25's list)

**Interfaces:**
- Consumes: PR `<N>` (Task 25: ready for review, CI green, body line `Reference upgrade.sql (runbook step 5, rendered offline from <short sha>): SHA-256 <64 hex>`) with Task 26's comment of the runbook step 0–7 outputs, and the same results in `<scratch>/slice1a-t26-results.md` (Task 26); Task 26's owner reports (step 0 query results, the `db-backup` run URL, `server_version`, steps 3–6 outputs, required checks `backend`/`backend-postgres`/`frontend` on `main`, Railway Config-as-code path `/backend/railway.toml` and Healthcheck Path `/health/ready` with the time they were saved); `backend/migrations/README.md` → `### Step 8: Merge and watch the deploy`, `### Step 9: Confirm head`, `### Step 10: Streamlit smoke check`, `## Reverting`, and the record heading it names, "Alembic stamping record (slice 1a)" (Task 24); `docs/manual-verification.md` → `## Slice 1`, its three "(after 1a)" items (Task 24); `backend/railway.toml` `preDeployCommand = ["alembic upgrade head"]`, `healthcheckPath = "/health/ready"` (Task 12); the 503 `db_unavailable` gate with `details.reason` `schema_behind` (Task 12); the startup lines `schema revision <current> != head <head>` and `Row-level security is off on: <tables>` (logger `db.schema_check`, Task 11); env.py's stderr line `Database: dialect=… driver=… host=… database=…` (Task 5); `scripts/schema_drift.py`'s stdout `revision: <current> head: <head> state: <state>` and exit 0/1/2 (Task 10); revision ids `0001_baseline` … `0004_invites_reusable` (Tasks 6–9); the stub `/welcome` card "No church yet" / "Creating or joining a church is coming in the next update." (Task 22); `AccountMenu`'s "Account menu" button and "Log out" item (Task 21).
- Produces: the 1a merge commit on `main`: the Railway API at `0004_invites_reusable (head)`, the Vercel frontend with the `(signed-in)` layouts; a comment on PR `<N>` with runbook steps 8–9; records PR `claude/slice-1a-records` with `### Alembic stamping record (slice 1a)` (the slice 1 RLS decision the lockdown record left open: no ownership transfer and no policies) and a `### Backup run record` row. Later users: slice 1b (starts from this `main`; appends manual items 2–11 under `## Slice 1`).

- [ ] **Step 1 (agent): Pre-merge gate**

Run this in the same sitting as Task 26, Step 15 (the Railway settings are saved "immediately before merging"; if the owner saved them on another day, or anything merged into `main` since, ask them to confirm both values are still set before going on).

```bash
git fetch origin
gh pr view <N> -R bbrown62450/church --json state,isDraft,mergeable,mergeStateStatus,baseRefName,headRefOid --jq '[.state, .isDraft, .mergeable, .mergeStateStatus, .baseRefName, .headRefOid] | @tsv'
git rev-parse origin/claude/slice-1-plan
git log --oneline origin/claude/slice-1-plan..origin/main | wc -l
gh pr checks <N> -R bbrown62450/church
gh api repos/bbrown62450/church/branches/main/protection/required_status_checks --jq '.contexts | sort | join(",")'
gh pr view <N> -R bbrown62450/church --json body --jq .body | grep 'Reference upgrade.sql'
gh run list -R bbrown62450/church --workflow db-backup --limit 1 --json conclusion,createdAt,event --jq '.[0] | "\(.conclusion) \(.createdAt) \(.event)"'
date '+%A %H:%M %Z'
```

Expected: `OPEN	false	MERGEABLE	CLEAN	main	<sha>`, and the next line prints the same `<sha>`; `0` (the branch already contains `main`); every check `pass` (`backend`, `backend-postgres`, `frontend`, the Vercel preview); `backend,backend-postgres,frontend`; the reference line; `success <today's date>…` (the daily 08:37 UTC run, or a dispatch: Task 26's backup protects the stamp, but the schema changes at this merge); a Monday to Friday. If the latest green `db-backup` run is not from today, ask the owner's yes for `gh workflow run db-backup --ref main -R bbrown62450/church` and wait for it to go green before the merge. Then, with the `<short sha>` from the reference line:

```bash
git diff --quiet <short sha> origin/claude/slice-1-plan -- backend/migrations/env.py backend/migrations/versions backend/db/models.py; echo "exit $?"
```

Expected: `exit 0` (neither `env.py`, a revision nor a model changed after the SQL the owner read in runbook step 5, so the deploy runs exactly that SQL; the README beside them may change without mattering). If `gh api …/required_status_checks` answered 404 or 403 instead of the three names, ask the owner to confirm in GitHub → Settings → Branches → the `main` rule that `backend`, `backend-postgres` and `frontend` are required. Also confirm, from Task 26's reports, all eight: step 0 rerun (every `public` table owned by `postgres`; `postgres`, `true`); a green `db-backup` run URL; `server_version` 17.x; `alembic current` showed `0001_baseline` after the stamp; the owner's `upgrade.sql` checks and SHA-256 matched the reference; the drift output was exactly the three expected lines (plus `add_index ix_hymns_church_hymnal` only if production lacked it) with exit 1; branch protection set; the two Railway values saved.

If `main` moved (a count other than `0`): `git merge origin/main -m "Merge origin/main into claude/slice-1-plan (Task 27)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"` on the branch, rerun both suites (`.venv/bin/python -m pytest -q | tail -1` → `697 passed, 5 skipped`; `(cd frontend && npm test)` → `122 passed`), push on the owner's yes and wait for green checks. If `mergeStateStatus` is `BLOCKED`, a required check is not green: fix it in the owning task's files (Task 25, Step 14); never merge with `--admin`. If any Task 26 item is missing, stop: that step comes first.

Then ask the owner, in one message: "PR #<N> is green and Task 26 is complete (Railway settings saved at <time>). May I merge it now with a merge commit? Please confirm it is a weekday and the tester is not using either app for the next 15 minutes (the upgrade briefly locks each table), and close any open Supabase SQL Editor tab."

- [ ] **Step 2 (agent, on the owner's yes): Merge**

```bash
gh pr merge <N> --merge -R bbrown62450/church
gh pr view <N> -R bbrown62450/church --json state,mergedAt,mergeCommit --jq '[.state, .mergedAt, .mergeCommit.oid] | @tsv'
```

Expected: `MERGED	<UTC time>	<merge sha>`. Use a merge commit (`--merge`), not squash. Note the merge time and sha in the session ledger. Then tell the owner: "Merged at <time> (<short merge sha>). Railway and Vercel are deploying it now: please do Step 3."

- [ ] **Step 3 (OWNER): Watch the merge deploy (runbook step 8)**

Railway → the project → the API service → Deployments → the deployment for the merge commit (its message starts `Merge pull request #<N>`) → its logs. Railway shows the pre-deploy command's output in the deployment's logs, before the app's startup lines (which tab is unverified: look in Deploy Logs first, then Build Logs). Alembic writes to stderr, so Railway may colour these lines red; that alone is not an error. Check, in order:

1. The **pre-deploy** step ran `alembic upgrade head`: a `Database: dialect=postgresql driver=psycopg2 host=… database=postgres` line (the pooler host), `INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.`, `INFO  [alembic.runtime.migration] Will assume transactional DDL.`, then exactly three `INFO  [alembic.runtime.migration] Running upgrade …` lines: `0001_baseline -> 0002_reconcile, …`, `0002_reconcile -> 0003_lockdown, …` and `0003_lockdown -> 0004_invites_reusable, …`.
2. The health check used `/health/ready` and succeeded, and the deployment is **Active**.
3. The app's startup lines include `api.main INFO request_id=- Database: dialect=postgresql driver=psycopg2 host=… database=postgres`, and no line contains `schema revision`, `Row-level security`, `Traceback` or `ERROR`.

Then Vercel → the `worship-service-builder` project → Deployments: the Production deployment for the merge commit is **Ready**.

Tell the agent: the date; the pre-deploy lines from `Context impl` to the last `Running upgrade` line (copy them as shown, but replace the host after `host=` with `…`); the health-check lines; "no schema/RLS/error lines" (or the lines you saw); Vercel Ready or not.

If something went wrong (the previous release keeps serving in every case except the last):
- `0003_lockdown: role … has no BYPASSRLS …` or `0003_lockdown: cannot enable RLS on …`: the whole upgrade rolled back, the database is still at `0001_baseline`. Stop and go back to runbook step 0 (`backend/migrations/README.md` → RLS precondition) with the agent.
- `relation "…" already exists`: the stamp of runbook step 4 is missing. Run runbook steps 3–7 (Task 26, Steps 7–10 and 15), then Deployments → the failed deployment → ⋮ → Redeploy.
- `canceling statement due to lock timeout`: something held a table lock for more than 5 s (an open SQL Editor transaction, a busy Streamlit session). Close it, wait until nobody uses the apps, then ⋮ → Redeploy.
- The pre-deploy succeeded but the health check failed: the database is at `0004_invites_reusable` and the pre-1a release keeps serving on it (every 1a schema change is expand-only). Send the agent the startup lines; the fix goes in a PR, or Step R.
- **No pre-deploy step at all:** Railway did not read `/backend/railway.toml`. The new release started on a database still at `0001_baseline`: its startup logs `schema revision 0001_baseline != head 0004_invites_reusable` at ERROR and `/health/ready` answers 503 `db_unavailable` with `"reason": "schema_behind"`, so the UI Healthcheck Path should have failed the deploy; if the deployment went Active anyway, the release is live on a schema behind head (harmless in 1a, which serves no route that reads the new `invites` columns). Either way, at once: the laptop setup of `backend/migrations/README.md` (`cd <the checkout>/backend`, then `IFS= read -rs DATABASE_URL && export DATABASE_URL`, pasting Railway's `DATABASE_URL`), `../.venv/bin/alembic upgrade head` (the same three `Running upgrade` lines), `unset DATABASE_URL`; then fix Settings → Config-as-code → Railway config file (`/backend/railway.toml`) and ⋮ → Redeploy; the redeploy's pre-deploy must then print no `Running upgrade` line.

- [ ] **Step 4 (agent): CI on `main` and the public endpoints**

```bash
gh run list --workflow ci --branch main --limit 3 -R bbrown62450/church --json databaseId,headSha,status,conclusion --jq '.[] | select(.headSha == "<merge sha>") | [.databaseId, .status, .conclusion] | @tsv'
```

The push run can take a few seconds to appear: if nothing prints, run the line again (no `sleep`). Then, with its `databaseId`:

```bash
gh run watch <run-id> --exit-status -R bbrown62450/church
API=https://church-production-74ca.up.railway.app
curl -s "$API/health"; echo
curl -s "$API/health/ready"; echo
curl -s "$API/me"; echo
```

Expected: the run completes successfully (`backend`, `backend-postgres`, `frontend`); `{"ok":true}`; `{"ok":true,"db":"ok"}` (a 503 body with `"reason":"schema_behind"` instead means the release is behind head: Step 3's last failure bullet); `{"error":{"code":"unauthenticated","message":"Please sign in.","request_id":"<32 hex>"}}`, with no `fields` or `details` keys. These are public, read-only requests.

- [ ] **Step 5 (OWNER, laptop): Confirm head (runbook step 9)**

In a new terminal, the laptop setup (`backend/migrations/README.md` → Production runbook → Laptop setup):

```bash
cd <the checkout>/backend
IFS= read -rs DATABASE_URL && export DATABASE_URL
../.venv/bin/alembic current
../.venv/bin/alembic check
../.venv/bin/python scripts/schema_drift.py; echo "exit $?"
unset DATABASE_URL
```

At the `read` line paste Railway's `DATABASE_URL` (nothing is shown) and press Return. Every command first prints `Database: dialect=postgresql driver=psycopg2 host=… database=postgres` on stderr (if it says `dialect=sqlite`, the variable is not exported: redo the setup). Expected, after Alembic's `INFO` lines: `0004_invites_reusable (head)`; `No new upgrade operations detected.`; then exactly

```
revision: 0004_invites_reusable head: 0004_invites_reusable state: current
exit 0
```

Close the terminal. Tell the agent the date and those outputs (without the `Database:` lines).

If `alembic check` prints `New upgrade operations detected: …` (and the drift script the same lines with exit 1), stop and send the agent the lines: production differs from the models in a way runbook step 6 did not show. `/health/ready` is unaffected (the revision is at head). An expand-safe difference gets a new revision in a follow-up PR; a type or nullability difference is resolved with the owner before slice 1b starts.

- [ ] **Step 6 (agent, on the owner's yes): Post the runbook step 8–9 outputs on PR `<N>`**

Write `<scratch>/slice1a-steps-8-9.md` from the owner's Step 3 and Step 5 reports (Task 26's comment already holds steps 0–7):

````markdown
Runbook steps 8–9 (`backend/migrations/README.md`), <date>

**Step 8, the merge deploy** (Railway → API → Deployments → <short merge sha>): pre-deploy `alembic upgrade head`

```
<the owner's pre-deploy lines, from "Context impl PostgresqlImpl." to "Running upgrade 0003_lockdown -> 0004_invites_reusable, …">
```

Health check: <the owner's health-check lines>; deployment Active. Startup: no `schema revision` or `Row-level security` line. Vercel production deployment: Ready.

**Step 9, head confirmed:**

```
$ alembic current
0004_invites_reusable (head)
$ alembic check
No new upgrade operations detected.
$ python scripts/schema_drift.py; echo "exit $?"
revision: 0004_invites_reusable head: 0004_invites_reusable state: current
exit 0
```

CI on the merge commit: green. `GET /health/ready` → `{"ok":true,"db":"ok"}`.
````

Replace every `<…>` with the real values, then check the file:

```bash
sed -E -i '' 's/host=[^ ]+/host=…/g' "<scratch>/slice1a-steps-8-9.md"
grep -c '<' "<scratch>/slice1a-steps-8-9.md"
grep -Eic 'postgres(ql)?://|password|pooler\.supabase\.com' "<scratch>/slice1a-steps-8-9.md"
gh pr comment <N> -R bbrown62450/church --body-file "<scratch>/slice1a-steps-8-9.md"
```

Expected: `0` and `0` before posting (run `gh pr comment` only then); `gh` prints the comment's URL. If the owner prefers to paste the outputs into the PR themselves, skip `gh pr comment`.

- [ ] **Step 7 (OWNER): Streamlit smoke check on the frozen app (runbook step 10)**

On https://liturgy-frozen.streamlit.app/, the production Streamlit app (F §6.3): sign in; the church and hymnal load; a saved service loads; Settings opens. Then Settings → Invites → **Create invite** with "Bind to email" empty and role `member`: the success message shows `Invite code: …` (never paste the code anywhere). Click **Revoke** next to that invite. Then Supabase → SQL Editor, one query at a time:

```sql
select reusable, accepted_by, revoked from invites order by created_at desc limit 1;
select tablename from pg_tables where schemaname = 'public' and not rowsecurity;
```

Expected: `false`, `NULL`, `true` (the frozen app's insert got the new column's server default); then no rows (RLS is on for every `public` table, `alembic_version` included). Last, Streamlit Cloud → `liturgy-frozen` → Manage app → logs: after the merge time from Step 2 there is no `Pulling code changes from Github` / `Updated app!` line and no restart, and ⋮ → Settings still shows branch `streamlit-frozen`.

Tell the agent the date and the result of each check. If the invite insert or any page fails, stop and send the agent the error text (never a code or a URL with a secret): the fix is Step R first, then, only if the `invites` columns themselves are the cause, `../.venv/bin/alembic downgrade 0003_lockdown` from the laptop setup (`backend/migrations/README.md` → Reverting; never below `0003_lockdown`).

- [ ] **Step 8 (agent, on the owner's yes): Run keepalive by hand**

```bash
gh workflow run keepalive --ref main -R bbrown62450/church
gh run list --workflow keepalive --limit 1 -R bbrown62450/church --json databaseId,createdAt,status
```

If the listed run was created before the dispatch, run the `gh run list` line again (no `sleep`). Then, with its `databaseId`:

```bash
gh run watch <run-id> --exit-status -R bbrown62450/church
gh run view <run-id> --log -R bbrown62450/church | grep -c '{"ok":true,"db":"ok"}'
```

Expected: the run completes successfully; `1`. Note the run URL (`https://github.com/bbrown62450/church/actions/runs/<run-id>`) and the date.

- [ ] **Step 9 (OWNER): Manual check 1 on the production frontend**

On https://worship-service-builder.vercel.app, at 375 px (Chrome → DevTools → device mode, iPhone SE) and again on desktop:

1. Your own account: sign in; home shows your church; the church switcher lists your churches (switch once if you have two: the page reloads its content for that church); **Account menu** shows your name, email and `Role: Owner` (or `Admin`/`Member`); **Log out** returns to `/login`.
2. A Google account that belongs to no church (for example a second personal account; signing in creates its user row, which is harmless): sign in; you land on `/welcome` with the card **No church yet** / "Creating or joining a church is coming in the next update." (not a 404, and no church switcher); **Account menu** → **Log out** returns to `/login`.

Tell the agent the date and the result of each, at 375 px and on desktop. A 404, a blank page or an error card: send the agent a screenshot and the "(Ref: …)" code if one shows; the fix is a PR (or Step R if the app is unusable).

- [ ] **Step 10 (agent): Records PR: the stamping record**

```bash
git fetch origin
git switch -c claude/slice-1a-records origin/main
git show origin/main:docs/ops-runbook.md | grep '\[owner' | grep -vc 'An entry marked'
```

Note that last number (the owner markers before this edit). In `docs/ops-runbook.md`:

1. `### Backup run record`: append one row to its table (after the `2026-09-26 (first manual run after ops-1)` row):

```markdown
| <date of Task 26's backup> (slice 1a runbook step 1, before stamping) | <the db-backup run URL> | Green. Artifact `db-backup` (`<backup-….dump.age name>`). |
```

2. `## Supabase lockdown record`: after the `**Rollback:**` paragraph (its last line is `app uses those roles.`) and before `## Backups`, insert one blank line and:

```markdown
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
precondition before any migration runs.

| Step | Result | Date |
|---|---|---|
| 0. RLS precondition rerun in the SQL Editor (step 2's two queries above) | <n> `public` tables, every one owned by `postgres`; `current_user`, `rolbypassrls`: `postgres`, `true`. Proceed. | <date> |
| 1. Backup | `db-backup` run, green (see Backup run record) | <date> |
| 2. `SHOW server_version;` | `<version>`; major 17 = `PG_MAJOR` and the CI image `postgres:17` | <date> |
| 3. `alembic current` before stamping | No revision; the `Database:` line named the session pooler | <date> |
| 4. `alembic stamp 0001_baseline` | `alembic current` then showed `0001_baseline` | <date> |
| 5. `alembic upgrade 0001_baseline:head --sql` | `BEGIN;` first, `COMMIT;` last; 0 `CREATE TABLE`, 4 `ADD COLUMN IF NOT EXISTS`, 3 `UPDATE alembic_version`, no `Database:` line; SHA-256 equal to PR #<N>'s reference render | <date> |
| 6. `scripts/schema_drift.py` | `revision: 0001_baseline head: 0004_invites_reusable state: behind`, then `add_column invites.accepted_by`, `add_column invites.reusable`, `add_fk fk_invites_accepted_by_users`<, and `add_index ix_hymns_church_hymnal` if it printed>; exit 1; no `text_year` or `hymnal_count` | <date> |
| Branch protection on `main` | Required checks `backend`, `backend-postgres`, `frontend` | <date> |
| 7. Railway → the API service → Settings, immediately before merging | Config-as-code → Railway config file `/backend/railway.toml`; Deploy → Healthcheck Path `/health/ready` (was `/health`) | <date> |
| 8. Merge and deploy | PR #<N> merged <UTC time>, merge commit `<short sha>`. The pre-deploy `alembic upgrade head` ran `0001_baseline -> 0002_reconcile`, `0002_reconcile -> 0003_lockdown`, `0003_lockdown -> 0004_invites_reusable`; the `/health/ready` health check passed; no `schema revision` or `Row-level security` line at startup; Vercel production Ready; CI on the merge commit green; `/health/ready` → `{"ok":true,"db":"ok"}` | <date> |
| 9. `alembic current`, `alembic check`, `scripts/schema_drift.py` | `0004_invites_reusable (head)`; `No new upgrade operations detected.`; `revision: 0004_invites_reusable head: 0004_invites_reusable state: current`, exit 0 (outputs on PR #<N>) | <date> |
| 10. Streamlit smoke on https://liturgy-frozen.streamlit.app/ | Sign-in, church, hymnal, a saved service and Settings OK; an invite created (`reusable` `false`, `accepted_by` `NULL`) and revoked; no `public` table without RLS; no code pull in its logs after the merge, branch still `streamlit-frozen` | <date> |
| Keepalive run by hand | <run URL>: green, `{"ok":true,"db":"ok"}` | <date> |
| Manual check 1 (at 375 px and on desktop) | Owner's account: home, switcher, role in the account menu, Log out. An account in no church: the stub `/welcome` ("No church yet"), not a 404; Log out. | <date> |
```

Replace every `<…>` with the owner's values (Task 26's, from `<scratch>/slice1a-t26-results.md`, and Steps 3–9). A step that went differently records what happened (for example "no pre-deploy step; upgraded from the laptop, config path fixed, redeployed") instead of the expected text. Then:

```bash
sed -n '/^### Alembic stamping record (slice 1a)$/,/^## Backups$/p' docs/ops-runbook.md | grep -c '<'
sed -n '/^### Backup run record$/,/^## Keep-alive$/p' docs/ops-runbook.md | grep -c '^| 20'
grep '\[owner' docs/ops-runbook.md | grep -vc 'An entry marked'
grep -Eic 'postgres(ql)?://|password=|PGPASSWORD|pooler\.supabase\.com|liturgy-next' <(sed -n '/^### Alembic stamping record (slice 1a)$/,/^## Backups$/p' docs/ops-runbook.md)
git diff --stat origin/main
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_slice1_docs.py backend/tests/test_docs.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
```

Expected: `0` (no `<…>` left); `2`; the same number as before the edit (1a adds no `[owner` marker); `0`; `docs/ops-runbook.md | …` and `1 file changed`; all passed (among them `test_runbook_has_the_seven_sections_in_order`, which the new `###` does not touch, and Task 24's `test_ops_runbook_health_check_lines_name_health_ready`, whose dated lines are unchanged); `697 passed, 5 skipped`. No new test: dated records are not pinned by tests (as in ops-3's records PRs).

```bash
git add docs/ops-runbook.md
git commit -m "Runbook: Alembic stamping record (slice 1a): production at 0004_invites_reusable, RLS without policies

Records slice 1a's production runbook steps 0-10 and manual check 1: postgres
owns every public table and has BYPASSRLS, so 0003_lockdown enabled RLS with
no policies (the choice the lockdown record left to slice 1 never arose);
stamped 0001_baseline; drift as expected; Railway reads /backend/railway.toml
(pre-deploy alembic upgrade head, health check /health/ready); alembic check
clean at head; the frozen Streamlit app on liturgy-frozen still works.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 11 (agent, on the owner's yes): Push, open and merge the records PR**

```bash
git push -u origin claude/slice-1a-records
gh pr create -R bbrown62450/church --base main --head claude/slice-1a-records \
  --title "Runbook: slice 1a stamping and deploy record" \
  --body "Records slice 1a's production runbook (backend/migrations/README.md, steps 0-10) and its manual check in docs/ops-runbook.md: the RLS precondition held (postgres owns every public table and has BYPASSRLS), so 0003_lockdown enabled RLS without policies; backup run; server version; stamped 0001_baseline; drift as expected; branch protection on backend, backend-postgres and frontend; Railway's Config-as-code path /backend/railway.toml and Healthcheck Path /health/ready; the merge deploy's pre-deploy upgrade to 0004_invites_reusable; alembic check clean; the Streamlit smoke check on liturgy-frozen; the stub /welcome for an account in no church. Docs only.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
gh pr checks claude/slice-1a-records -R bbrown62450/church --watch
```

Expected: the PR URL; `backend`, `backend-postgres`, `frontend` and the Vercel preview pass. Merge on the owner's explicit yes:

```bash
gh pr merge claude/slice-1a-records --merge -R bbrown62450/church
```

This merge redeploys the API: its pre-deploy `alembic upgrade head` is now a no-op (the `Database:` line and the two `INFO` lines, no `Running upgrade` line) and the `/health/ready` health check passes. The owner may glance at that deployment's logs; anything else there goes back to Step 3's list. Then report to the owner: "Slice 1a is live and recorded: production at `0004_invites_reusable (head)`, `alembic check` clean, Streamlit on liturgy-frozen unaffected, `/welcome` stub checked. Slice 1b can start from `main`."

- [ ] **Step R (only if the 1a release must come out): Revert**

Use this only when the release cannot serve and a fix PR would take too long (Steps 3, 7 or 9 say when). The schema stays at `0004_invites_reusable`: every 1a change is expand-only, so the code before 1a runs on it.

1. OWNER, first: Railway → the API service → Settings → Config-as-code → Railway config file: clear the field and save (after the revert `/backend/railway.toml` no longer exists, and what Railway does with a path to a missing file is unverified). Keep Deploy → Healthcheck Path `/health/ready`: the code before 1a has served that route since ops-3. Tell the agent when it is saved.
2. Agent, on the owner's yes (every command that leaves this machine):

```bash
git fetch origin
git switch -c claude/revert-slice-1a origin/main
git revert -m 1 --no-commit <merge sha>
git commit -m "Revert slice 1a (PR #<N>): back to the pre-1a release; the schema stays at 0004_invites_reusable

The 1a merge deploy <what failed>. Every 1a schema change is expand-only, so
the pre-1a code runs on the migrated database; Railway's Config-as-code path
was cleared first (backend/migrations/README.md -> Reverting).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
.venv/bin/python -m pytest -q | tail -1
(cd frontend && npm ci --prefer-offline && npm test)
git push -u origin claude/revert-slice-1a
gh pr create -R bbrown62450/church --base main --head claude/revert-slice-1a \
  --title "Revert slice 1a" \
  --body "Reverts the slice 1a merge (PR #<N>) because <what failed>. The database stays at 0004_invites_reusable (expand-only, so the pre-1a code runs on it); Railway's Config-as-code path was cleared first and the Healthcheck Path stays /health/ready. Never downgrade production below 0003_lockdown.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
gh pr checks claude/revert-slice-1a -R bbrown62450/church --watch
```

Replace `<merge sha>`, `<N>` and `<what failed>` first. Expected: `559 passed` (the pre-1a suite); Vitest `15 passed` (if `npm ci --prefer-offline` cannot install without the network, skip the local frontend run and rely on CI's `frontend` job); the PR URL; every check passes. Merge on the owner's explicit yes (`gh pr merge claude/revert-slice-1a --merge -R bbrown62450/church`); the OWNER then checks that deployment: no pre-deploy step, the `/health/ready` health check passed, Active, and https://worship-service-builder.vercel.app signs in and shows the church as before 1a. Only if the `invites` columns themselves broke the frozen Streamlit app (Step 7), the owner then runs `../.venv/bin/alembic downgrade 0003_lockdown` in the laptop setup and `unset DATABASE_URL`. Record the revert, and the downgrade if one ran, as rows of the stamping record in Step 10's records PR.

Expected counts after this task: backend `697 passed, 5 skipped` on `main` (CI `backend-postgres`: `5 passed, 697 deselected`); frontend `122 passed`. The records PR adds no test.

---

## Spec coverage

Every 1a item of S (and the gaps this plan found) mapped to its task. Status is as of `7978a5e`: DONE = already on `main`, PARTIAL, NEW.

| # | S 1a item | Status | Task |
|---|---|---|---|
| 1 | `backend/alembic.ini` (`%(here)s` paths) + `migrations/env.py` (+ `script.py.mako`) | NEW | T5 |
| 2 | `0001_baseline` (11 tables + `text_year`/`hymnal_count` on `hymns`, `hymn_catalog`; `ix_hymns_church_hymnal`) | NEW | T6 |
| 3 | `0002_reconcile` (guarded index + guarded hymn-facts columns; no-op downgrade for 0001 objects) | NEW | T7 |
| 4 | `0003_lockdown` (DO block, precondition RAISE, REVOKEs; downgrade disables RLS only) | NEW | T8 |
| 5 | `0004_invites_reusable` + `Invite.reusable`/`accepted_by` model + models docstring amendment | NEW | T9 |
| 6 | Every revision has working `downgrade()`; single head; new constraints named | NEW | T6–T9 (tests in `test_migrations.py`) |
| 7 | `db/schema_check.py` (`alembic_config`, `include_object`, `schema_diff`) | NEW | T5 |
| 8 | `db/schema_check.py` (`revision_state`, `RevisionState`, `format_diff`) + `scripts/schema_drift.py` | NEW | T10 |
| 9 | Startup revision check (WARNING / ERROR in prod) + `app.state.schema_state` | NEW | T11 |
| 10 | Startup RLS check (Postgres only) | NEW | T11 |
| 11 | Remove `init_db()` from API lifespan (`main.py:15,30`); keep `db.init_db` (Streamlit, CLIs, conftest, pg_smoke use it) | NEW | T11 |
| 12 | Readiness gate `schema_behind` in `routes/health.py:31-36` | NEW | T12 |
| 13 | `backend/railway.toml` | NEW | T12 |
| 14 | Delete `migrate_add_hymnal.py`, `migrate_add_hymn_facts.py`, `tests/test_migrate_hymn_facts.py`; README step 1 (`README.md:155-160`); `backfill_hymn_facts.py:5` docstring | NEW | T7 |
| 15 | Production runbook in `backend/migrations/README.md` (steps 0–10, local dev) | NEW (step 0 answered by `docs/ops-runbook.md:128-138` (at `560ebb3`): owner `postgres`, `rolbypassrls` true; step 2 by "Platform limits": 17.6) | T24 (write), T26/T27 (run) |
| 16 | `backend/domain_errors.py` (DomainError + 9 subclasses + `RateLimited`, `ERROR_CODES` incl. `db_unavailable`, `invalid_rubric`) | NEW | T2 (after owner Q2) |
| 17 | `db/ids.py::as_uuid` | NEW | T2 |
| 18 | `backend/usecases/__init__.py` | NEW | T2 |
| 19 | Error body `fields`/`details`; `request_id` always | PARTIAL (`request_id` DONE, errors.py:57) | T3 |
| 20 | Pydantic 422 field mapping | NEW | T3 |
| 21 | `ApiError(details=)`; DomainError handler; `domain_error_response`; `ErrorBody`; `error_responses` | NEW | T3 |
| 22 | `db_unavailable` 503 in both registries | PARTIAL (helper DONE errors.py:43-45, takes no arguments; registry NEW) | T2 (backend), T16 (frontend union), T12 (message/details params) |
| 23 | `require_church` 403 `details.reason = "no_church_access"` (deps.py:103-110, incl. a missing/malformed header); `require_admin` no reason (already) | NEW / DONE | T3 |
| 24 | `schemas.py`: `ChurchOut.role: Literal`, `Page[T]`, `ItemList[T]`, `ErrorBody` re-export | NEW | T3 |
| 25 | `api/idempotency.py` (`idempotency_key`, `IdempotencyStore`, `run_idempotent`) | NEW | T4 |
| 26 | `requirements.txt`: `alembic`, `tzdata`, `fastapi==0.141.*`, `pydantic==2.13.*` | NEW | T1 (floors raised, clarification 22) |
| 27 | `pytest.ini` `postgres` marker | NEW | T1 |
| 28 | Autouse no-network fixture + proving test | NEW | T1 |
| 29 | `pg_db` fixture (`TEST_DATABASE_URL`) | NEW | T1 (+ local-URL guard); upgrade wiring T6 |
| 30 | `test_route_guards.py` (+ deliberately-unguarded self-test) | NEW | T13 |
| 31 | `tests/api_helpers.py` (`auth_headers`, `church_headers`, `isolation_world`, `assert_church_isolated`) on `GET /church` | NEW | T13 (also `GET/PATCH /rubric`, clarification 6) |
| 32 | `scripts/export_openapi.py` + committed `frontend/src/lib/api/openapi.json` + `test_openapi_contract.py` | NEW | T13 |
| 33 | `test_no_streamlit_in_core.py` extended (`api.main`; `usecases.onboarding` is 1b) | PARTIAL (`test_api_app.py:109` covers `api.main`) | T2 (usecases pkg), T13 (api.main) |
| 34 | `test_migrations.py` (SQLite cycle, downgrade defs, 0004 data step, `--sql` render, pre-PR-#4 amendment, Postgres 0003 refusal + idempotence) | NEW | T5–T9 |
| 35 | `test_schema_check.py` | NEW | T5, T10 |
| 36 | `test_domain_errors.py` | NEW | T2, T3 |
| 37 | `test_idempotency.py` | NEW | T4 |
| 38 | `test_api_app.py` extended (422 fields, reasons, lifespan/no tables, WARNING, RLS skip, gate) | NEW | T3, T11 |
| 39 | `test_error_registry.py` | NEW | T16 |
| 40 | `test_foundation_setup.py` asserts (requirements, `railway.toml`, `alembic.ini %(here)s`) | PARTIAL (file exists) | T1, T5, T7, T12 |
| 41 | `test_ci_workflow.py` (postgres job alembic steps + `pytest -m postgres`; frontend `gen:api` diff; no major check) | PARTIAL (exists; `:14-28` asserts `postgres:17` + pg_smoke) | T14, T15 |
| 42 | CI `backend-postgres` job (alembic cycle, `pytest -m postgres`) | PARTIAL (job exists, pg_smoke only, `ci.yml:19-44`) | T14 |
| 43 | CI image `postgres:<PG_MAJOR>` check | DONE (`test_ops_workflows.py:396-400`, live 17=17) | T14 fixes the stale comment at `:397` and adds a non-vacuous image-shape test (critique 12) |
| 44 | CI frontend `npm run gen:api && git diff --exit-code src/lib/api/schema.d.ts` | NEW | T15 |
| 45 | Postgres re-run of ops concurrent first-request test (`test_identity.py:227-243`) | NEW | T14 |
| 46 | Frontend deps (TanStack Query v5; jsdom, RTL react/dom/user-event/jest-dom, plugin-react, openapi-typescript) + `gen:api` script | NEW | T15 |
| 47 | Vitest `unit` + `dom` projects; `src/test/setup-dom.ts` | NEW | T15 |
| 48 | `installFakeApi` (`src/test/fake-api.ts`), `src/test/fixtures/` | NEW | T15 |
| 49 | `renderWithProviders` (`src/test/render.tsx`) | NEW | T19 |
| 50 | `eslint.config.mjs` `"react/no-danger": "error"` | NEW | T15 |
| 51 | API client moved `lib/api.ts` → `lib/api/client.ts` + new opts + `ApiError` fields + `requestId` header fallback | NEW | T16 |
| 52 | `lib/api/{errors,timeouts,types}.ts`, `schema.d.ts` | NEW | T15 (`schema.d.ts`), T16 |
| 53 | `useApi()` (S: in `queries/client.ts`); QueryClient; `keys`; `authEvents`; `useMe`; `useChurchProfile` | NEW | T18 |
| 54 | `lib/auth.ts` (`getAccessToken`, `useSignOut`, `scope: "local"`) | NEW (page.tsx:34 uses global scope) | T18 (`getAccessToken` + signing-out flag), T19 (`useSignOut`) |
| 55 | `lib/storage.ts`, `lib/urls.ts` | NEW | T17 |
| 56 | `lib/church.ts`: `pickActiveChurch(+excluded)`, `roleLabel`, `useStoredChurchId`, `storeChurchId` notify, `resetStoredChurchIdForTests`, types re-exported | PARTIAL | T17 |
| 57 | `lib/church-context.tsx` (`ChurchProvider`, `useChurch`) | NEW | T18 (`useApi().church` reads it) |
| 58 | `app/providers.tsx` + root `<Providers>` | NEW | T19 |
| 59 | UI kit `components/app/{empty-state,error-state,pending-button,confirm-dialog,page-header}.tsx`; shadcn `input label tabs alert alert-dialog combobox`; button `touch` | NEW | T20 |
| 60 | `AppHeader` (moved to `components/app/`), `ChurchSwitcher` (DropdownMenu+RadioGroup, **no** "Join or create" item — 1b), `AccountMenu` | PARTIAL (old `components/app-header.tsx` uses `Select`) | T21 |
| 61 | `(signed-in)/layout.tsx` + `MeContext`; stub `/welcome` | NEW | T19 (`MeContext`), T22 |
| 62 | `(church)/layout.tsx` (resolution, keyed remount, 403 fallback, switch cleanup), `(church)/page.tsx`; delete `src/app/page.tsx` | NEW | T23 |
| 63 | `queryClient.clear()` + `storeChurchId(null)` + `wsb:` keys on sign-out, with no refetch or re-store during sign-out (critique 8) | NEW | T18 (flag), T19 (hook), T22 (layout), T23 (integration + race test) |
| 64 | Manual check 1 (after 1a) in `docs/manual-verification.md` "## Slice 1" | NEW | T24 (write), T27 (run) |
| 65 | Ops-runbook "slice 1 moves it" lines | NEW: edit in place only `docs/ops-runbook.md:23-24` and `:317-318` (line numbers at `560ebb3`). `:40-41` (dated 2026-09-26 check record), `:149` (comment inside the recorded lockdown SQL) and `:164` (the lockdown record's instructions) are history and stay; slice 1's RLS decision goes in T27's new `###` record | T24, T27 |
| 66 | Branch protection on all three jobs (F§5.4; AC4 "all three jobs are required") | missing from S | T26 |
| 67 | AC1–AC5, AC13, AC15, AC18; 1a parts of AC12, AC14, AC16, AC17 | — | see tasks; AC6–11 are 1b |
| 68 | Risks 2 (drift), 5 (RLS), 6 (Railway path), 11 (ops ordering: DONE) | — | T26/T27; risk 11 moot |

Acceptance criteria:

| Acceptance criterion | Task(s) |
|---|---|
| AC1 | T5–T9, T14 |
| AC2 | T26, T27 |
| AC3 | T11, T12, T27 |
| AC4 | T13, T14, T15, T26 |
| AC5 | T2, T3, T4, T16 (major check DONE) |
| AC12 (1a) | T21, T22, T23 |
| AC13 | T23 |
| AC14 (1a) | T18, T19, T22, T23 (return-to-path in 1b) |
| AC15 | T15, T20 |
| AC16 (first half) | T13 (+`test_api_app.py:109`) |
| AC17 (1a) | T27 |
| AC18 | T6, T7, T26 |
| AC6–AC11 | 1b |

Not in 1a (S "In scope 1b" and the items S marks 1b): `POST /churches`, `/invites/preview`, `/invites/accept`, `usecases/onboarding.py`, `timezones.py`, bulk seed, public `as_utc`, `repos` changes, USER_SCOPED additions, `/welcome` tabs, `/join`, `/login?next`, proxy `next` + `/join` public, switcher "Join or create a church…", `lib/idempotency.ts`, `post-login.ts`, `timezones.ts`, `TimezoneCombobox` (clarification 12), `queries/{onboarding,membership}.ts`, `streamlit_tests/test_onboarding.py` removal.
