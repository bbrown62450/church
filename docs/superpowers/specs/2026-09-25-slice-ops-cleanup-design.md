# Slice ops — Ops cleanup (independent) — Design

**Status:** Draft  **Depends on:** Slice 0 (merged, live). No other slice. Needs the owner for the manual steps (Supabase dashboard, GitHub settings, Railway env, Streamlit Cloud, an `age` key pair).  **Size:** M. Inventory §5 sized the original list S; foundations §7.1 and §7.2 added the three deferred slice-0 backend fixes and the platform pieces.

**Date:** 2026-09-25
**Inputs (cited as):**
- Foundations: `docs/superpowers/specs/2026-09-25-migration-foundations-design.md` ("F §n"). Binding; this spec does not contradict it.
- Inventory: `docs/superpowers/specs/2026-09-25-streamlit-migration-inventory.md` ("inv §n"). Source of truth for current behavior.
- Slice 0 spec: `docs/superpowers/specs/2026-09-25-react-fastapi-migration-design.md`.
- Owner decision 7: freeze Streamlit now, with data-safety fixes only.

---

## Goal

Before any feature slice starts, make production safe, observable and stable, and freeze the Streamlit app:

1. **Close the data exposures.**
   - The Supabase Data API is locked down (F D1, §3.6).
   - Backups run daily, and each dump is encrypted before it leaves the runner (inv H5, F §7.4).
2. **Fix the three deferred slice-0 backend issues** (F §7.3):
   - 500s reach the browser with CORS headers;
   - concurrent first requests no longer 500;
   - authenticated requests stop writing `users` on every call.
3. **Give every later slice a platform to build on:**
   - request ids on every response the app produces;
   - startup guards and a pool size that fits the Supabase pooler;
   - a readiness endpoint;
   - the final CORS header lists;
   - `redirect_slashes=False`.
4. **Remove dead code and fix configuration drift** (inv H8, H10, H11, H12).
5. **Freeze Streamlit** on a `streamlit-frozen` branch at the same URL, so that `main` can change freely (F D2, §6.1).

Nothing in this slice changes a screen in the React app.

---

## Scope / Out of scope

### In scope

| # | Item | Source | Specified in |
|---|---|---|---|
| S1 | Supabase Data API lockdown (manual, day one) | F D1, §3.6 | Data and migrations → Lockdown |
| S2 | `backup.yml`: strip the `+driver` from the URL, match `pg_dump` to the server major version, encrypt with `age` before upload, then add the secret | inv H5, §4 "Secrets"; F §7.2 | Data and migrations → Backups |
| S3 | `GET /health/ready`; `keepalive.yml` curls it and holds no database secret | inv §2.2 last row, H4; F §7.2 | API; Backend changes |
| S4 | Delete `email_send.py`, `notion_archive.py`, `notion_usage.py`, `select_sunday_hymns.py`, `add_hymnary_links.py`, `fix_hymn_titles.py` | inv H8, H10, H11, §5 "Now" | Backend changes → Deleted |
| S5 | `backend/.env.example` gains `ESV_API_KEY`, `LOG_LEVEL`, `APP_ENV`, `DB_POOL_SIZE` (plus `DB_MAX_OVERFLOW`, which F §2.6 names alongside it) | inv H12, §5; F §7.2 | Backend changes → Config |
| S6 | Move `shadcn` to devDependencies | inv H12, §6; F §4.11 | Frontend changes |
| S7 | Streamlit freeze: branch, redeploy, delete `liturgy-stg`, header comment, keep-awake, policy | F §6.1; owner decision 7 | Data and migrations → Freeze |
| S8 | `db/upsert.py` + `repos.users.ensure_user` + identity cache | F §2.4, §7.3 | Backend changes → Identity |
| S9 | `RequestIdMiddleware`, `UnhandledErrorMiddleware`, middleware order, CORS header lists | F §1.10, §2.5 | Backend changes → Middleware |
| S10 | Startup: log the database target, the `APP_ENV` production guard, pool settings | F §2.6 items 1, 2, 6 | Backend changes → Startup |
| S11 | `FastAPI(redirect_slashes=False)` | F §1.1 | Backend changes → Middleware |
| S12 | Confirm that Railway's request limit exceeds 120 s, and record it | F §1.8 | Data and migrations → Step 0 |
| S13 | `request_id` in every error body. This is the part of F §1.5 that needs only the request id. | F §1.5 | API |
| S14 | Fold `repos.users.upsert_user` into `ensure_user` | F §2.4; inv §6 "Code to delete" | Backend changes → Identity |
| S15 | Ops runbook, README "Operations" section, and an "Ops slice" section in `docs/manual-verification.md` | F §5.5 | Testing → Manual checks |
| S16 | Streamlit data-safety fix: "Exclude hymns used in the last 12 weeks" never drops hymns already picked (inv D5, and the F6 "drops a loaded service's own hymns" case) | owner decision 7; inv D5 | Data and migrations → Freeze → Streamlit bug triage |

**Streamlit data-safety fixes during the freeze.** The foundations assign none to ops. This slice:
- triages every Streamlit bug in the inventory against the policy's definition (data loss, corruption, leakage, security) and records a disposition for each (Freeze → "Streamlit bug triage");
- fixes the one bug that meets the definition in the tester's normal flow and cannot reasonably be accepted (S16, inv D5). The fix ships in ops-1, while Streamlit still deploys from `main`, so the frozen branch inherits it;
- sets up the process for later fixes (Freeze, step 7);
- lists the ops backend changes that the frozen branch inherits and verifies each before the branch is cut (Freeze, "What the frozen app inherits").

### Out of scope: moved to named slices

| Item | Slice | Why / interface assumed |
|---|---|---|
| Alembic, `0001`–`0004`, and `0003_lockdown`, which codifies S1 | 1 | `0003_lockdown` must be idempotent against a production that ops already locked by hand. `ENABLE ROW LEVEL SECURITY` and `REVOKE` are both idempotent. |
| Removing `init_db()` / `create_all` from the lifespan (F §2.6 item 5) | 1 | Until Alembic exists, `create_all` is the only way a fresh local SQLite database gets its tables. Slice 1 removes it together with the Alembic setup. |
| Revision and RLS startup checks (F §2.6 items 3–4) | 1 | Both need Alembic, or the lockdown migration, to exist. |
| Error-body `fields` and `details`, `domain_errors.py`, the Pydantic 422 mapping | 1 | Ops adds only `request_id`. The body stays a superset of slice 0 (F §1.5). |
| Frontend `ApiError.requestId` and the "Something went wrong. (Ref: …)" text | 1 | Assumes ops's server contract: `error.request_id` is always present, and the header `X-Request-Id` is exposed to the browser by CORS. |
| Railway's deploy health check on `/health/ready` (`backend/railway.toml`), and the production readiness gate that returns 503 `db_unavailable` with `details.reason = "schema_behind"` when the schema is behind head | 1 | F §3.3 as amended. Ops builds `/health/ready` (database reachability only) and leaves the Railway health check where it is; `/health` stays the dependency-free liveness probe before and after slice 1. The gate is checked before ops' memoized probe, so the memo never hides it. |
| `test_route_guards.py` and its `PUBLIC` allowlist | 1 | The allowlist must contain `/health` and `/health/ready` (F §1.2). |
| Postgres CI job, and a Postgres re-run of the identity race test | 1 | The CI service container uses the major version that ops records as `PG_MAJOR` in `backup.yml` (see Data and migrations). Ops already enforces this: `test_ops_workflows.py` fails as soon as `ci.yml` declares a `postgres:<major>` image that differs from `PG_MAJOR`. That is the only check of the CI Postgres major; slice 1's `test_ci_workflow.py` does not repeat it. |
| No-network autouse fixture | 1 | F §7.2 |
| `integrations/http.py`, `backend/cache.py` (`TTLCache` with `get_or_load`, `CacheableFailure`, single-flight) and `backend/tests/test_cache.py`, rate limiter | 2 | F §2.1 and §7.2 assign `cache.py` to slice 2, and slice 2's spec creates it. **Ops creates neither `cache.py` nor `test_cache.py`.** The identity cache is a private, success-only class in `api/identity_cache.py` (see Identity) and does not depend on `cache.py`. |
| `OPENAI_MODEL` default in `.env.example` | 3 | F §2.8. Ops leaves the existing `OPENAI_MODEL=gpt-3.5-turbo` line alone. |
| The Streamlit switchover banner on `streamlit-frozen` | 5b (parity gate) | F §6.3 phase C |
| `migrate_to_db.py`, `notion_hymns.py`, `fill_from_hymnary.py`, their tests, and the `playwright` and `notion-client` requirements | 7 | They wait for the `hymn_catalog` export (inv §6 "Data", F §6.4). |
| `migrate_add_hymnal.py` | 1 | F §3.2 |
| `db/engine.py` default URL (`sqlite:///data/church.db`, which differs from the docs' `data/app.db`) | 7 | inv §3 row "backend/db/engine.py:24". Only the stale comment is fixed here, because ops edits that function anyway. |
| README and manual-verification rewrite, root `.env.example` deletion, deleting `keep-awake.yml` and the `liturgy` app, rotating secrets, an off-GitHub pinger | 7 | inv §6; F §6.3 phase E |
| Gmail refresh-token encryption | 7 | F §6.4 (the frozen Streamlit app reads the tokens as plaintext) |

### Inventory §H disposition (every row)

| Row | Fate in this slice |
|---|---|
| H1 `migrate_to_db.py` | Untouched; deleted in 7. Its `upsert_from_claims` call keeps working because the wrapper keeps its signature. |
| H2 `migrate_add_hymnal.py` | Untouched; deleted in 1. |
| H3 `import_hymnal.py` | Untouched. It stays a CLI; the admin API comes in 6a. |
| H4 `keepalive.py` + `keepalive.yml` | The workflow now curls `/health/ready`. **`backend/keepalive.py` and its `ping` tests are deleted.** The inventory's "KEEP" assumed the workflow ran the script, and after this slice nothing does. |
| H5 `backup.yml` | Rewritten (S2). |
| H6 `ci.yml` | Unchanged. PRs into `streamlit-frozen` run it, because it triggers on every `pull_request`. |
| H7 `keep-awake.yml` | Pings only `https://liturgy.streamlit.app/`. Deleted in 7. |
| H8 `notion_archive.py`, `notion_usage.py` | Deleted. |
| H9 `notion_hymns.py` | Untouched; deleted in 7. It is still imported by `migrate_to_db.py`, `fill_from_hymnary.py` and `worship_service.py:20-21`. |
| H10 `add_hymnary_links.py`, `fix_hymn_titles.py`, `select_sunday_hymns.py` | Deleted. |
| H10 `fill_from_hymnary.py` | Untouched; deleted in 7. |
| H11 `email_send.py` | Deleted. |
| H12 config, env, deps, docs | `backend/.env.example` (S5); `shadcn` (S6); the `db/engine.py:43` comment. Everything else moves to 7 (table above). |

Zero-importer check, done for this spec with a grep over `*.py`, `*.yml`, `*.ini`, `*.toml`, `*.txt` and `*.json`, excluding `.venv` and `docs/`:
- none of the six modules is imported anywhere;
- three of them (`add_hymnary_links.py`, `fix_hymn_titles.py`, `select_sunday_hymns.py`) import `notion_hymns` and `hymn_utils` themselves; both of those stay;
- no test references any of the six.

### Delivery plan (order)

Commits follow TDD (test first) and end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

| Step | Kind | Contents | Gate before the next step |
|---|---|---|---|
| 0 | Owner, manual, day one | Generate the `age` key pair first (an incident dump needs it). Send the tester the D5 workaround message (User experience). Data API lockdown and its checks, plus Incident response if step 1 returns rows. Record the Postgres server version, the pooler pool size, the table owner and BYPASSRLS. Look up and record Railway's request limit. | The anonymous curl returns no rows. `/me` and Streamlit both work. |
| ops-1 | PR | The Streamlit D5 fix (S16; its own first commit, and it may merge as a separate PR if the rest of ops-1 is delayed); encrypted `backup.yml`, `.github/backup/age-recipients.txt`, `.github/backup/normalize-pg-url.sh`; delete the six modules; `backend/.env.example`; `shadcn` to devDependencies; runbook sections for backups, the lockdown record, the Streamlit bug triage and "Platform limits" (with the `Postgres server major` line); README "Backups" paragraph; tests. | Merged. The owner runs the D5 manual check on the live app, runs the recovery query, and sends the tester the "fixed" message. The owner adds the `BACKUP_DATABASE_URL` secret, runs the workflow by hand, and completes the restore drill. |
| ops-2 | PR | The database layer that Streamlit also uses: `db/upsert.py`, `ensure_user`, the `upsert_from_claims` wrapper, removal of `upsert_user`, `api/identity_cache.py` and the identity cache in `api/deps.py`, pool and connect-timeout settings, comment fixes; tests. | Merged. For at least one day the tester uses Streamlit (still deployed from `main`) and nothing regresses. |
| ops-3 | PR | API platform: middleware, `request_id` in error bodies, CORS lists, `redirect_slashes=False`, logging, startup guards, settings, `db/health.py` and `/health/ready`; `keepalive.yml` rewrite; delete `keepalive.py`; `test_keepalive.py` becomes `test_ops_workflows.py`; `app.py` FROZEN header; `keep-awake.yml` production-only; README, manual-verification and runbook updates. | Before merging, set `APP_ENV=production` on Railway. After merging: set the Actions variable `API_BASE_URL` and run keepalive. |
| Freeze | Owner (plus agent for git) | Cut `streamlit-frozen` from the **ops-3 merge commit**, protect it, redeploy Streamlit, delete `liturgy-stg`, remove its redirect URIs, run the smoke checks. | Acceptance criteria 20–22 pass. |

Why this order:
- The D5 fix goes first because it stops silent loss of the tester's hymn picks, and Streamlit still deploys from `main`, so merging it puts it live at once. The frozen branch inherits it.
- ops-2 changes code the live Streamlit app runs: `auth.upsert_from_claims` on every rerun, and the engine pool. It merges while Streamlit still deploys from `main`, so any regression shows up before the freeze locks it in.
- The ops-3 merge commit is "the ops-slice merge commit" of F §6.1, step 1.

---

## User experience

This slice adds no screens and changes nothing visible in the React app. The sections below cover the people who do notice something.

**Tester (Streamlit user)**
- Same URL, `https://liturgy.streamlit.app/`, and same behavior.
- One short outage while the app is redeployed from the frozen branch. Schedule it on a weekday the tester has agreed to, never Saturday or Sunday.
- Message before the redeploy (the owner sends it; exact copy):
  > Heads-up: on {weekday, date} between {start} and {end} I'm moving the planning app to a new setup. The address stays https://liturgy.streamlit.app. It may be unavailable for up to 15 minutes. Please don't start a new service during that window — anything you've already saved is safe.
- Message after:
  > All done — the app is back at the same address. Please sign in once and let me know if anything looks different.
- Sent **only if** Step 0 finds the Data API was exposing `gmail_tokens` (exact copy):
  > As a precaution, please go to https://myaccount.google.com/permissions, remove access for Worship Service Builder, then open the app and click "Connect your Gmail" again. This replaces the Gmail permission the app stores for you.
- D5 workaround, sent on day one (Step 0) and in force until the fix is live (exact copy):
  > Quick tip until I tell you it's fixed: keep "Exclude hymns used in the last 12 weeks" unticked whenever you load a saved service, click "Prepare bulletin copy" or "Prepare pastor's copy", or save. You can tick it while you choose hymns, but untick it before those steps. Otherwise the app can silently clear your hymn choices and save the service without hymns.
- Sent after ops-1 is live and the D5 manual check passes (exact copy):
  > The hymn problem is fixed: "Exclude hymns used in the last 12 weeks" no longer clears hymns you've already picked, so you can leave it ticked. If a service you saved recently shows no hymns, tell me its date and I'll tell you which hymns you had picked.

**Browser (React app on Vercel)**
- Every API response the app produces now carries an `X-Request-Id` header, and the browser can read it. CORS preflight (`OPTIONS`) responses are the exception: `CORSMiddleware` answers them before `RequestIdMiddleware` runs (F §2.5 order).
- Every error body now carries `request_id`.
- Unexpected server errors now arrive as a readable 500 with CORS headers instead of a network error.
- The slice-0 page still shows its existing messages:
  - `ApiError` message "Something went wrong." for a 500;
  - "Can't reach the server. Check your connection and try again." only for real network failures.
- The "(Ref: …)" suffix comes in slice 1.

**Owner (operations)**
- GitHub Actions:
  - `db-backup` runs daily at 08:37 UTC. Its artifact is `backup-<UTC timestamp>.dump.age`, and only the owner's `age` key can open it.
  - `keepalive` runs daily at 09:17 UTC. It is green when `/health/ready` returns 200.
  - `keep-awake` pings one app.
- Railway logs:
  - one startup line naming the database target without credentials;
  - an ERROR line when `CORS_ORIGINS` is localhost-only in production;
  - every application log line carries `request_id=`.
- `docs/ops-runbook.md` is the single place for the lockdown record, key custody, the restore drill, the freeze record and platform limits.

**Exact server messages added by this slice**

| Where | Copy |
|---|---|
| `GET /health/ready`, 503 | `{"error": {"code": "db_unavailable", "message": "The database is not reachable.", "request_id": "…"}}` |
| Any 500 (unchanged text) | `{"error": {"code": "internal_error", "message": "Something went wrong.", "request_id": "…"}}` |
| Startup, invalid `APP_ENV` (raises) | `APP_ENV must be 'development' or 'production' (got '{value}').` |
| Startup, production on a non-Postgres URL (raises) | `APP_ENV=production requires a PostgreSQL DATABASE_URL; refusing to start.` |
| Startup, production with localhost-only CORS (log ERROR) | `CORS_ORIGINS allows only localhost origins in production; browsers on the real site will be blocked.` |
| Startup (log INFO) | `Database: dialect=postgresql driver=psycopg2 host=aws-0-<region>.pooler.supabase.com database=postgres` |
| Invalid `LOG_LEVEL` (log WARNING, continue at INFO) | `LOG_LEVEL='{value}' is not a valid level; using INFO.` |
| Invalid `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` (raises at engine creation) | `DB_POOL_SIZE must be an integer >= 1 (got '{value}').` / `DB_MAX_OVERFLOW must be an integer >= 0 (got '{value}').` |
| `backup.yml`, missing secret | `::error::BACKUP_DATABASE_URL secret is not set` |
| `backup.yml`, missing key | `::error::.github/backup/age-recipients.txt has no age recipient` |
| `backup.yml`, version mismatch | `::error::Postgres server major is {N} but PG_MAJOR is {M}; update PG_MAJOR in backup.yml` |
| `keepalive.yml`, missing variable | `::error::Set the API_BASE_URL repository variable (Settings → Secrets and variables → Actions → Variables)` |

There are no empty or loading states: nothing in the UI changes.

---

## API

Conventions follow F §1: kebab-case, no trailing slash, uniform error body, `response_model` on every route, and blocking I/O in plain `def` routes.

| Method | Path | Guard | Request | Response | Errors |
|---|---|---|---|---|---|
| GET | `/health/ready` | public | none. `Authorization` and `X-Church-Id` are ignored. | 200 `ReadyOut` `{"ok": true, "db": "ok"}`. The result is memoized: at most one probe runs at a time, and a result is reused for 10 s (ok) or 5 s (failed). | 503 `db_unavailable` "The database is not reachable."; 500 `internal_error`. Slice 1 adds the production-only schema-behind gate, which is checked before the memoized probe: 503 `db_unavailable` "The database schema is behind this release." with `details: {"reason": "schema_behind", "current": X, "head": Y}` (F §1.5, §3.3). |
| GET | `/health` | public | unchanged | 200 `{"ok": true}`, unchanged. It is the dependency-free liveness probe and never touches the database. Ops leaves Railway's deploy health check where it is; slice 1 moves it to `/health/ready` (`backend/railway.toml` `healthcheckPath = "/health/ready"`, F §3.3 as amended), and `/health` stays the liveness probe after that. | — |
| GET | `/me` | user | unchanged | unchanged | 401 `unauthenticated`; 503 `auth_unavailable`. The first-request race no longer produces a 500 (F §7.3). |
| GET | `/church` | church | unchanged | unchanged | 401; 403 `forbidden`; 503. Tenancy is still re-checked on every request and never cached. |

**Changes that apply to every route (additive, F §1.11):**
1. **Response header `X-Request-Id`** on every response produced inside the app, including 404s, 405s, 422s and the 500s of `UnhandledErrorMiddleware`.
   - If the request carries an `X-Request-Id` that matches `^[A-Za-z0-9-]{8,64}$`, that value is echoed.
   - Otherwise the server generates `uuid4().hex`.
   - Not covered: CORS preflights (`OPTIONS` with `Access-Control-Request-Method`, allowed or rejected), which `CORSMiddleware` answers itself from outside `RequestIdMiddleware`, and the last-resort 500 from Starlette's `ServerErrorMiddleware`, which only occurs if a middleware itself fails. Both follow from the F §2.5 order and are accepted.
2. **Every error body includes `request_id`,** the same value as the header:
   `{"error": {"code", "message", "request_id"}}`. `fields` and `details` arrive in slice 1.
3. **Unexpected exceptions** return 500 `internal_error` from inside CORS. An allowed `Origin` therefore gets `access-control-allow-origin` on the 500 (F §2.5).
4. **A trailing slash is no longer redirected** (`redirect_slashes=False`). `GET /me/` returns 404 `not_found` instead of a 307. The slice-0 frontend never sends one (it calls `/me` and `/church`; `frontend/src/app/page.tsx:53,77`).
5. **CORS** (F §1.10):
   - `allow_headers` = `Authorization, Content-Type, X-Church-Id, Idempotency-Key, If-Match, X-Request-Id`;
   - `expose_headers` = `Content-Disposition, Retry-After, X-Request-Id`;
   - `max_age=600`;
   - `allow_credentials` stays off.

**Error code registry addition:** `db_unavailable` (503), an addition to the F §1.5 table. Ops does all of the backend part:
- `api/errors.py` gains the helper `db_unavailable()`. Until slice 1 adds `domain_errors.py`, `api/errors.py` is the whole backend registry, and `db_unavailable` stays there afterwards (see the exception below), so `domain_errors.py` never needs it.
- `frontend/src/lib/api/errors.ts` does not exist yet; slice 1 creates it (F §4.11). So that the union stays complete without relying on slice 1 remembering, `test_foundation_setup.py` asserts that once that file exists it contains `"db_unavailable"`. The check is inert until slice 1 and fails slice 1's CI if the code is missing. The UI never calls `/health/ready`.
- Slice 1 reuses the same code for its readiness gate rather than adding a `schema_behind` code: a release whose schema is behind head gets 503 `db_unavailable` with `details.reason = "schema_behind"`, which F §1.5's registry documents. Ops adds no `details`.

**Recorded exception to F §2.2 items 1 and 4.** `/health` and `/health/ready` are infrastructure probes, not domain operations. They have no usecase and raise no `DomainError`.
- `/health/ready` calls one db-layer function, `db.health.database_ready()`, which holds the SQL, the `try/except` and the memo. The route itself contains neither SQL nor `try/except`.
- It raises `ApiError` through `db_unavailable()`, although F §2.2 item 4 keeps `ApiError` for authentication failures.
- This stays as is after slice 1. Slice 1 adds its schema-behind gate to this route (it reads `app.state.schema_state`, fixed at startup, before calling `database_ready()`), but does not move it behind a usecase; its `test_route_guards.py` lists both paths as `PUBLIC`.

`ReadyOut` lives at the top of `api/routes/health.py`, because only that module uses it (F §1.3): `ok: bool`, `db: Literal["ok"]`.

---

## Backend changes

### Modules added

| Module | Contents |
|---|---|
| `backend/api/identity_cache.py` | `CachedIdentity` and `IdentityCache`: a private, thread-safe, success-only LRU map with a TTL, used only by `get_current_user`. Not a general cache: `backend/cache.py` belongs to slice 2. |
| `backend/db/upsert.py` | `insert_ignore(table, *, dialect_name=None) -> Insert` |
| `backend/db/health.py` | `database_ready() -> bool`: the memoized, single-flight `SELECT 1` probe behind `/health/ready`; `reset_readiness_for_tests()` |
| `backend/api/middleware.py` | `REQUEST_ID_HEADER`, `current_request_id()`, `RequestIdMiddleware`, `UnhandledErrorMiddleware` (both pure ASGI) |
| `backend/api/logging_config.py` | `configure_logging(level)` and the record factory that adds `request_id` |
| `backend/api/startup.py` | `describe_database(url)`, `check_app_env(value)`, `enforce_production_guards(settings, engine)` |
| `.github/backup/age-recipients.txt` | The owner's `age` public key or keys |
| `.github/backup/normalize-pg-url.sh` | Reads a URL on stdin and writes a libpq-compatible URL on stdout |
| `docs/ops-runbook.md` | See Testing → Manual checks |

**`backend/api/identity_cache.py`**

```python
@dataclass(frozen=True)
class CachedIdentity:
    user_id: uuid.UUID; name: str | None; picture: str | None   # as stored after the last ensure_user

class IdentityCache:
    def __init__(self, maxsize: int = 1024, ttl: float = 300.0,
                 *, clock: Callable[[], float] = time.monotonic): ...
    def get(self, email: str) -> CachedIdentity | None   # None when absent or expired; expired entries are dropped
    def put(self, email: str, identity: CachedIdentity) -> None
    def clear(self) -> None
    def __len__(self) -> int
```

- One `threading.Lock` guards an `OrderedDict`.
- `get` marks the key as recently used. `put` evicts the least recently used entry when the size exceeds `maxsize`.
- The clock is injectable, for tests (see Testing → `identity_clock`).
- **Success-only by construction.** The only value ever stored is the result of an `ensure_user` call that returned. There is no failure entry and no `ok` flag: if `ensure_user` raises, nothing is cached and the error propagates. A database error can therefore never be remembered as an identity (F §2.7).
- **Why not `cache.TTLCache`.** F §2.1 and §7.2 assign `backend/cache.py` and its tests to slice 2, whose spec defines it around `get_or_load` and `CacheableFailure`. That interface does not fit a lookup that must compare the incoming profile before deciding to load. F §2.4's `TTLCache(maxsize=1024, ttl=300 s)` is this class with those parameters. Slice 2 creates `cache.py` and `test_cache.py` as its spec says; nothing in ops conflicts with them.

**`backend/db/upsert.py`**

```python
def insert_ignore(table: Table | type, *, dialect_name: str | None = None) -> Insert:
    """Dialect insert() that supports .on_conflict_do_nothing(); postgresql or sqlite only."""
```

- This is the one-argument form F §2.4 names, and the one slices 1 and 5a call: `insert_ignore(Membership)` and `insert_ignore(HymnUsage.__table__)`.
- `table` is a `Table` or a mapped class.
- The dialect comes from `get_engine().dialect.name`, the process engine that `SessionLocal` is bound to, including after `reset_engine_for_tests`.
- `dialect_name` overrides it, only so tests can compile the Postgres form without connecting.
- Picks `sqlalchemy.dialects.postgresql.insert` or `sqlalchemy.dialects.sqlite.insert`. Raises `NotImplementedError` for any other dialect.
- Later reuse:
  - slice 1: the double-accept of an invite into `memberships`;
  - slice 5a: usage recording.

### Identity (F §2.4): the race fix and fewer writes

**`repos/users.py` changes:**

```python
@dataclass(frozen=True)
class UserRow:
    id: uuid.UUID; email: str; name: str | None; picture: str | None; last_login_at: datetime | None

LAST_SEEN_RESOLUTION = timedelta(hours=1)

def ensure_user(email: str, name: str | None = None, picture: str | None = None, *,
                google_sub: str | None = None, now: datetime | None = None,
                session: Session | None = None) -> UserRow
```

The algorithm runs in one transaction: the caller's `session`, or its own `session_scope()` when `session` is None (F §2.2.3).
1. Normalize the email with `strip().lower()`. If it is empty, raise `ValueError("email is required")`.
2. Normalize name, picture and google_sub: strip, and turn an empty string into None. `now` defaults to `datetime.now(timezone.utc)`.
3. Insert, ignoring a duplicate email:
   `insert_ignore(User.__table__).values(id=uuid4(), email, google_sub, name, picture, created_at=now, last_login_at=now).on_conflict_do_nothing(index_elements=["email"])`.
4. Select the row: `SELECT id, email, name, picture, google_sub, last_login_at FROM users WHERE email = :email`.
5. Collect updates:
   - `name` when the incoming value is truthy and differs from the stored one; `picture` the same way;
   - `google_sub` the same way (the Streamlit path only; the API never passes it);
   - `last_login_at = now` when the stored value is NULL, or when it is older than `now - LAST_SEEN_RESOLUTION`. Naive stored datetimes (SQLite) are read as UTC.
6. If anything was collected, run one `UPDATE users SET … WHERE id = :id`. Return the `UserRow` with the values as they now stand.

Notes:
- A `google_sub` UNIQUE conflict for a *new* email still raises `IntegrityError`, exactly as today. Only the Streamlit path can reach it, because the conflict target is `email`.
- `upsert_user` is deleted. Its only callers were tests (inv A2). The tests move to `ensure_user`, and the "overwrite when not None" rule becomes "overwrite when truthy".
- `get_user` and `get_user_by_email` stay. They are never exposed through the API (inv I).

**`auth.upsert_from_claims`** (`backend/auth.py:23-60`) becomes a thin wrapper. Its signature and error text stay the same, for Streamlit (`streamlit_auth.py:28`) and `migrate_to_db.py:130`:

```python
def upsert_from_claims(claims: dict) -> uuid.UUID:
    email = _normalize_email(claims.get("email"))
    if not email:
        raise ValueError("OIDC claims are missing an email address.")
    return ensure_user(email, claims.get("name"), claims.get("picture"),
                       google_sub=claims.get("sub")).id
```

**`api/deps.get_current_user`** (`backend/api/deps.py:55-76`):

```python
_identity_cache = IdentityCache(maxsize=1024, ttl=300)

def clear_identity_cache() -> None: ...
```

`get_current_user` reads the module attribute `_identity_cache` on every call (never binds it as a default argument or a closure), so a test can replace it with an `IdentityCache` on a fake clock.

Flow:
1. Parse the bearer token and call `verifier.verify` (**every request, never cached**). The slice-0 401 and 503 mapping is unchanged.
2. `profile = claims_to_profile(claims)`. Normalize the email; if it is empty, return 401 "Please sign in."
3. Take the incoming name and picture, stripped, with an empty string turned into None.
4. On a cache hit where each incoming value is falsy or equal to the cached value, use the cached `user_id`. **No database work.**
5. Otherwise call `row = ensure_user(email, name, picture)` (never `google_sub`, per `security.py:104-122`). Only after it returns, `put` `CachedIdentity(row.id, row.name, row.picture)`. If it raises, nothing is cached.
6. Return `CurrentUser(id, email, name=profile["name"], picture=profile["picture"])`. This is the same shape as slice 0.

Properties:
- Each user causes at most one identity SELECT per 5 minutes and one users write per hour.
- Concurrent first requests all succeed: each runs `ensure_user`, `ON CONFLICT DO NOTHING` absorbs the duplicate insert, and every caller gets the same id.
- `require_church` still calls `validate_active_church` on every request (`backend/tenancy.py:33-54`), which is a security invariant. Removing a membership or soft-deleting a church takes effect on the very next request, even when the identity is cached.
- Test isolation: an autouse fixture in `backend/tests/conftest.py` calls `clear_identity_cache()` before each test, because every test gets a new SQLite file while reusing the same emails.

**`db/models.py:42`**: comment `last_login_at` as "last seen, to the hour (see repos.users.LAST_SEEN_RESOLUTION)". The column is unchanged, and nothing reads it (grep).

### Middleware, errors and logging (F §1.10, §2.5)

**`RequestIdMiddleware`** (pure ASGI; any scope type other than `http` passes through unchanged):
1. Read the inbound `x-request-id`. Keep it if it matches `^[A-Za-z0-9-]{8,64}$`; otherwise use `uuid.uuid4().hex`.
2. Set the `_request_id` contextvar. anyio copies the context into the threadpool, so sync `def` routes see it too.
3. Wrap `send` so that `http.response.start` gains `X-Request-Id`.
4. Reset the contextvar in `finally`.

**`UnhandledErrorMiddleware`** (pure ASGI, not `BaseHTTPMiddleware`):

```python
async def __call__(self, scope, receive, send):
    if scope["type"] != "http":
        return await self.app(scope, receive, send)
    started = False
    async def send_wrapper(message):
        nonlocal started
        if message["type"] == "http.response.start":
            started = True
        await send(message)
    try:
        await self.app(scope, receive, send_wrapper)
    except Exception:
        logger.exception("Unhandled error on %s %s", scope["method"], scope["path"])  # path only, never the query
        if started:
            raise
        await _send_json(send, 500, error_body("internal_error", "Something went wrong."))
```

- After it sends the 500 it does **not** re-raise, because the error is already logged and a second response must never start.
- The exception text never reaches the client (F §1.5 "never leak").

**Order in `create_app()`** (`backend/api/main.py:34-46`). The last middleware added is the outermost:

```python
app = FastAPI(title="Worship Service Builder API", lifespan=lifespan, redirect_slashes=False)
app.add_middleware(UnhandledErrorMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins),
                   allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
                   allow_headers=["Authorization", "Content-Type", "X-Church-Id",
                                  "Idempotency-Key", "If-Match", "X-Request-Id"],
                   expose_headers=["Content-Disposition", "Retry-After", "X-Request-Id"],
                   max_age=600)
install_error_handlers(app)
```

The resulting stack, outside in: Starlette `ServerErrorMiddleware` → CORS → RequestId → UnhandledError → `ExceptionMiddleware` → router. The `ApiError`, `RequestValidationError` and `HTTPException` handlers still run in `ExceptionMiddleware`. The existing `@app.exception_handler(Exception)` (`errors.py:59-62`) stays as a last resort for failures inside middleware.

**`api/errors.py`:**
- `_body(code, message)` keeps its name, because slice 1 extends it with `fields` and `details`. It adds `"request_id": current_request_id() or uuid4().hex`; the fallback only fires outside `RequestIdMiddleware`, in the last-resort handler.
- `UnhandledErrorMiddleware` uses the public alias `error_body = _body`.
- Add `db_unavailable() -> ApiError(503, "db_unavailable", "The database is not reachable.")`. This is the recorded F §2.2 exception in the API section.
- `ApiError` keeps its signature. Slice 1 adds the `DomainError` mapping on top.

**`api/logging_config.py`:** `configure_logging(level: str)` does three things.
1. It maps the level name. An unknown name falls back to INFO and logs the WARNING in the copy table.
2. It installs, once and idempotently, a `logging.setLogRecordFactory` wrapper that sets `record.request_id = current_request_id() or "-"`. This is the "logging filter" of F §2.5, built as a record factory so that every handler, including pytest's `caplog`, sees the attribute.
3. If the root logger has no handlers, it calls `basicConfig` with the format `%(name)s %(levelname)s request_id=%(request_id)s %(message)s`.

`api/main.py:17-21` calls `configure_logging(get_settings().log_level)` in place of the inline `basicConfig`. Logging rules follow F §2.5: never log bodies, tokens, codes, OAuth values, email bodies, or AI prompts and outputs.

### Settings and startup (F §2.6 items 1, 2, 6)

**`api/settings.py`:** `Settings` gains two fields, and `get_settings` reads them from the environment:
- `app_env: str`, from `APP_ENV`, stripped and lower-cased, default `"development"`;
- `log_level: str`, from `LOG_LEVEL`, default `"INFO"`.

Add the property `is_production`. Validation happens in the lifespan, not in `get_settings`, so that importing `api.main` never raises.

**`api/startup.py`:**
- `describe_database(url: sqlalchemy.engine.URL) -> str` returns `f"dialect={url.get_backend_name()} driver={url.get_driver_name()} host={url.host or '-'} database={url.database or '-'}"`. It never includes the username or password. The function is pure.
- `check_app_env(value) -> str` returns `"development"` or `"production"`, and raises `RuntimeError` with the copy above for anything else.
- `enforce_production_guards(settings, engine) -> None` applies only in production:
  - if `engine.dialect.name != "postgresql"`, it raises `RuntimeError` with the copy above;
  - if every origin's host is `localhost`, `127.0.0.1` or `[::1]`, it logs an ERROR with the copy above.

**Lifespan** (replaces `api/main.py:24-31`):

```python
settings = get_settings()
check_app_env(settings.app_env)
engine = get_engine()                                   # creating the engine opens no connection
logger.info("Database: %s", describe_database(engine.url))
enforce_production_guards(settings, engine)             # before anything touches the database
init_db()                                               # removed in slice 1 (Alembic)
if not settings.supabase_url: logger.warning(...)      # unchanged slice-0 text
yield
```

- A failure here makes uvicorn exit with "Application startup failed".
- On Railway the new deploy then fails its health check, and the previous release keeps serving.

**Engine and pool** (`db/engine.py:39-48`): `_make_engine(url)` now calls a pure helper, `_engine_kwargs(url) -> dict`, so tests can inspect it.
- **All databases:** `pool_pre_ping=True`, `future=True` (unchanged).
- **SQLite:** `connect_args={"check_same_thread": False}`. The comment at `engine.py:43` changes to "FastAPI runs sync routes in a threadpool; SQLite needs this relaxed." It no longer cites Streamlit reruns (inv §3).
- **Postgres:**
  - `pool_size = _int_env("DB_POOL_SIZE", 5, minimum=1)`;
  - `max_overflow = _int_env("DB_MAX_OVERFLOW", 5, minimum=0)`;
  - `pool_recycle=1800`;
  - `connect_args={"connect_timeout": 10}`.

  `_int_env` treats a blank value as the default and raises `ValueError` with the copy above for anything else invalid.
- `connect_timeout=10` is a small addition to F §2.6. Without it, libpq waits for the operating system's TCP timeout (minutes) when the pooler is unreachable. That would tie up a threadpool worker and make `/health/ready` hang instead of returning 503.
- The engine is also used by the frozen Streamlit app. See Data and migrations → "What the frozen app inherits".

### Readiness endpoint and keep-alive

**`db/health.py`** (no FastAPI import; the SQL and the `try/except` live here, not in the route):

```python
READY_OK_TTL = 10.0     # seconds a success is reused
READY_FAIL_TTL = 5.0    # seconds a failure is reused

_lock = threading.Lock()
_last: tuple[bool, float] | None = None          # (ok, expires_at)

def database_ready(*, clock: Callable[[], float] = time.monotonic) -> bool:
    global _last
    with _lock:                                  # single-flight: one probe, so at most one pooled connection
        if _last is not None and clock() < _last[1]:
            return _last[0]
        ok = _probe()
        _last = (ok, clock() + (READY_OK_TTL if ok else READY_FAIL_TTL))
        return ok

def _probe() -> bool:
    try:
        with get_engine().connect() as conn:
            if conn.dialect.name == "postgresql":
                conn.exec_driver_sql("SET LOCAL statement_timeout = '5s'")
            conn.execute(text("SELECT 1")).scalar_one()
        return True
    except SQLAlchemyError as exc:
        logger.warning("Readiness check failed: %s", type(exc).__name__)   # class name only: messages can contain hosts
        return False

def reset_readiness_for_tests() -> None: ...     # sets _last = None
```

**`api/routes/health.py`:**

```python
@router.get("/health/ready", response_model=ReadyOut)
def ready() -> ReadyOut:
    if not database_ready():
        raise db_unavailable()
    return ReadyOut(ok=True, db="ok")
```

- It is a plain `def`, so it runs in the threadpool. The probe uses the process engine, so it exercises the real pool.
- It does no logging on success.
- **Flood protection.** The endpoint is public, so the memo and the lock bound what it can cost: however many requests arrive, at most one pooled connection is used for readiness at a time, and a new probe starts at most every 10 s after a success or 5 s after a failure. Authenticated routes keep the rest of the pool. Waiting callers block for at most one probe, which `connect_timeout` (10 s) and `statement_timeout` (5 s) bound; if the pool is exhausted the probe waits for SQLAlchemy's `pool_timeout` (30 s) and reports 503, which is then the correct answer. While a probe is in flight, a flood can still hold threadpool workers waiting on the lock; that is the exposure every public endpoint has until the slice 2 rate limiter, and it no longer touches the database pool.
- **Keep-alive still reaches the database.** The daily keepalive gets a cached result only if another probe ran in the previous 10 s, and that probe already touched the database. No authentication and no rate limiter are needed (the limiter arrives in slice 2).
- An autouse fixture in `backend/tests/conftest.py` calls `reset_readiness_for_tests()` before each test.

**`.github/workflows/keepalive.yml`** (rewritten). No secrets. The Railway URL is not secret, because it is already in the public frontend bundle as `NEXT_PUBLIC_API_URL`.

```yaml
name: keepalive
on:
  schedule:
    - cron: "17 9 * * *"   # daily; Supabase Free pauses after ~7 idle days
  workflow_dispatch: {}
permissions: {}
jobs:
  ping:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - name: Check API readiness (keeps the Supabase database awake)
        env:
          API_BASE_URL: ${{ vars.API_BASE_URL }}
        run: |
          test -n "$API_BASE_URL" || { echo "::error::Set the API_BASE_URL repository variable (Settings → Secrets and variables → Actions → Variables)"; exit 1; }
          curl --fail-with-body --silent --show-error --max-time 30 \
               --retry 3 --retry-delay 20 --retry-all-errors \
               "${API_BASE_URL%/}/health/ready"
```

`backend/keepalive.py` is deleted, and `backend/tests/test_keepalive.py` is replaced by `test_ops_workflows.py` (Testing).

### Modules deleted

- `backend/email_send.py`, `backend/notion_archive.py`, `backend/notion_usage.py`, `backend/select_sunday_hymns.py`, `backend/add_hymnary_links.py`, `backend/fix_hymn_titles.py` (ops-1)
- `backend/keepalive.py` and `backend/tests/test_keepalive.py` (ops-3; its workflow assertions move to `test_ops_workflows.py`)
- `repos.users.upsert_user` (ops-2)

### Config

`backend/.env.example` gains these lines, after `CORS_ORIGINS`:

```
# development (default) or production (Railway). Production refuses to start on
# SQLite and logs an error when CORS_ORIGINS lists only localhost.
APP_ENV=development

# API log level: DEBUG, INFO (default), WARNING, ERROR.
LOG_LEVEL=INFO

# Postgres connection pool per API process (defaults 5 and 5). Both apps share
# the Supabase session pooler, so keep the totals small.
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=5

# Optional. Enables the ESV translation; the key stays on the backend.
ESV_API_KEY=
```

- The existing `OPENAI_MODEL=gpt-3.5-turbo` line stays until slice 3.
- The root `.env.example` (Streamlit) is not touched; slice 7 deletes it.

Railway env, set by the owner and recorded in the runbook:
- `APP_ENV=production` (before merging ops-3);
- `LOG_LEVEL=INFO` (optional).

### Streamlit coupling and layering

- Nothing under `backend/` imports streamlit.
  - `test_api_app.py::test_api_does_not_import_streamlit` and `test_no_streamlit_in_core.py` keep passing.
  - The new modules (`api/identity_cache`, `db/upsert`, `db/health`, `api/middleware`, `api/logging_config`, `api/startup`) import no Streamlit. `db/health` imports no FastAPI either.
- The D5 fix (S16) touches only the root Streamlit files `app.py` and `ui_helpers.py`. It imports the existing `hymn_usage.is_hymn_recently_used` and changes nothing under `backend/`.
- `auth.py` keeps its Streamlit-facing wrapper. Its docstring still mentions `streamlit_auth.py`, which is fine until slice 7 (inv §0 item 10).
- `db/` does not import `api/`. Pool settings are read from the environment inside `db/engine.py`, the same way `DATABASE_URL` already is. The engine is shared by the API, Streamlit and the CLIs.

### Data access and tenancy notes

- No church-scoped route is added.
- `require_church` is unchanged and uncached. Its per-request `validate_active_church` gets a regression test with a warm identity cache (Testing).
- `/health/ready` touches no table.

---

## Data and migrations

### Schema

- There are no schema changes, no Alembic (it arrives in slice 1) and no data migration.
- The only change in the database is the manual Data API lockdown below, which slice 1's `0003_lockdown` later codifies.
- F §3.4's expand-only rules are not engaged.

### Step 0: Data API lockdown (manual, day one; F §3.6)

The owner runs these steps and records the results, with dates, in `docs/ops-runbook.md` → "Supabase lockdown record". Local tools: `docker run --rm -it postgres:17 psql "<url>"` works if `psql` isn't installed. Use the same session-pooler URL the apps use.

1. **Verify the exposure,** before changing anything. Repeat the request for `users`, `gmail_tokens`, `invites` and `memberships`:
   ```
   curl -s "https://<ref>.supabase.co/rest/v1/users?select=email&limit=1" \
     -H "apikey: <anon key>" -H "Authorization: Bearer <anon key>"
   ```
   Also run it with `Authorization: Bearer <your own access token>`, which is the `authenticated` role: any Google user can obtain one by signing in. Get the token from your own browser session.
   - **Any rows returned mean an incident:** follow Incident response below after step 4.
2. **Check that RLS won't block the apps.** Through the pooler URL, run:
   ```sql
   select tablename, tableowner from pg_tables where schemaname = 'public' order by 1;
   select current_user, rolbypassrls from pg_roles where rolname = current_user;
   show server_version;
   ```
   - It is safe to enable RLS with no policies only if `current_user` owns every table or has `rolbypassrls = true`. Record both results, plus `server_version`, which sets `PG_MAJOR` below.
   - Record the major in the runbook → "Platform limits" as exactly one line of the form `- Postgres server major: 17`. `test_ops_workflows.py` parses that line and checks it against `PG_MAJOR` in `backup.yml`.
   - Also record the session pooler's "Pool Size" from Dashboard → Database → Connection pooling. Risks, item 2 uses it.
3. **Lock down:**
   - **(a)** Dashboard → Project Settings → Data API: turn the Data API **off**, since neither app uses PostgREST (`frontend/src` calls only `supabase.auth.*`; grep finds no `.from(` or `.rpc(`). If the toggle isn't available, remove `public` from "Exposed schemas" instead.
   - **(b)** In the SQL editor, run:
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
     **If step 2 failed** (the tables aren't owned by the app role and it has no BYPASSRLS), skip the `DO` block. Enabling RLS would hide every row from both apps. Apply (a) and the REVOKEs only, and record the issue for slice 1 (see Risks, item 1).
4. **Confirm:**
   - the step-1 curls, with both tokens, now fail with no rows;
   - the GraphQL introspection `curl -s -X POST https://<ref>.supabase.co/graphql/v1 -H "apikey: <anon key>" -H "Content-Type: application/json" -d '{"query":"{ __schema { queryType { fields { name } } } }"}'` lists no app tables (for example no `usersCollection`);
   - `/me` works on `https://worship-service-builder.vercel.app`;
   - Streamlit loads the tester's church.

   **Rollback:** `ALTER TABLE public.<t> DISABLE ROW LEVEL SECURITY` for each table, and turn the Data API back on. The REVOKEs need no rollback, because no app uses those roles.

**Incident response** (only if step 1 returned rows). Do this the same day: Supabase Free keeps logs for a short time. Steps 1–3 come before any repair.
1. **Preserve evidence.** No backup exists yet on day one, so take an encrypted dump before changing any row. It never exists in plaintext:
   ```
   docker run --rm postgres:17 pg_dump "<pooler URL, libpq form: postgresql://…, no +psycopg2>" \
       --schema=public --format=custom \
     | age --encrypt -r <your age1… public key> > incident-$(date -u +%Y%m%dT%H%M%SZ).dump.age
   ```
   Use an image tag at least as new as the server major. Keep the file offline next to the key, not in the repo or in GitHub. It is also the reference for any repair below.
2. **Review the API logs.** Dashboard → Logs → API: list the `/rest/v1` and `/graphql/v1` requests you didn't make, **especially `POST`, `PATCH` and `DELETE`**, and note their dates, methods, paths and IPs in the runbook.
3. **Check for tampering** in every table the default grants let a caller write, not only the obvious ones. Compare with the people and data you know:
   - **`users`: every row.** Compare `email`, `google_sub`, `name` and `created_at` with the known users. Identity is matched by email only (inv A2): `ensure_user` selects the row by email, and tenancy then uses that row's id. So an `UPDATE users SET email = 'attacker@…'` on the owner's row gives the next Google sign-in with that address the owner's memberships, without touching `memberships`. Also look for rows created for people you don't know.
   - `memberships` (unexpected rows or roles) and `invites` (unexpected rows, especially with the admin or owner role).
   - `contacts`: unexpected recipients. Bulletins are emailed to them.
   - `churches`: `name`, `settings` (liturgy prompts, translation) and `deleted_at`.
   - `services`, `hymns`, `hymn_usage` and `hymn_catalog`: rows or edits you don't recognize (`services.saved_at` shows recent writes).
   - `gmail_tokens`: recently changed rows.
   - **Purge `oauth_states`** (`DELETE FROM oauth_states;`). A state is valid for only 10 minutes (inv F8), so the only cost is that a Gmail connect in progress must be restarted.
4. **Repair** anything found in step 3 from the forensic dump or the known values: a changed `users.email` first, before anyone signs in again; then memberships, contacts and settings. Note each repair in the runbook.
5. Revoke every active invite in Streamlit Settings → Invites, and reissue any still needed. Invite codes are bearer secrets, and some may carry the admin role.
6. Send the tester the Gmail message in User experience. Removing the app's access at Google revokes the old refresh token.
7. **Record the incident** in the runbook: the log review; the users/contacts audit (rows checked, differences found, repairs made); the other tables checked; the `oauth_states` purge; the invite revocation; and the forensic dump's file name and where it is kept.

**Railway request limit (S12):**
- Find Railway's documented maximum HTTP request duration for the service's proxy.
- Record the value, the source URL and the date in the runbook → "Platform limits".
- If the limit is below 120 s, stop and raise it with the slice 3 and 4 authors, because F §1.8's client timeouts reach 90 s.
- Do not add a test endpoint that sleeps (F §1.8).

### Backups (S2): encrypted `pg_dump` before any secret exists

**Key setup (owner, once):**
1. Run `brew install age`, then `age-keygen -o ~/wsb-backup-key.txt`.
2. Store the whole file in the owner's password manager, plus one offline copy. Then delete the file from disk.
3. Optionally generate a second recovery key, kept apart from the first. Every public key listed is a recipient that can decrypt.
4. Give the `age1…` public line or lines to the PR.
5. The private key never goes to GitHub, Railway, the repo or chat.

**`.github/backup/age-recipients.txt`:**
- `#` comments, plus one or more lines matching `^age1[02-9ac-hj-np-z]{58}$`;
- committed in ops-1;
- a test enforces the format, so a placeholder cannot merge.

**`.github/backup/normalize-pg-url.sh`** (bash, `set -euo pipefail`):
- reads one URL on stdin and writes it on stdout after `sed -E 's#^postgres(ql)?(\+[A-Za-z0-9_]+)?://#postgresql://#'`;
- this strips the SQLAlchemy `+psycopg2` driver (inv H5), which `pg_dump` rejects;
- it never echoes to stderr;
- the workflow and the test both run it as `bash .github/backup/normalize-pg-url.sh`, so its file mode doesn't matter. A missing executable bit therefore can't pass the tests and then fail on the first real run.

**`.github/workflows/backup.yml`** (rewritten):

```yaml
name: db-backup
on:
  schedule:
    - cron: "37 8 * * *"   # daily at 08:37 UTC
  workflow_dispatch: {}
permissions:
  contents: read
concurrency:
  group: db-backup
  cancel-in-progress: false
jobs:
  dump:
    runs-on: ubuntu-24.04
    timeout-minutes: 20
    env:
      PG_MAJOR: "17"          # MUST equal the Supabase server major recorded in step 0; the job checks it
    steps:
      - uses: actions/checkout@v4
      - name: Check prerequisites
        env:
          BACKUP_DATABASE_URL: ${{ secrets.BACKUP_DATABASE_URL }}
        run: |
          test -n "$BACKUP_DATABASE_URL" || { echo "::error::BACKUP_DATABASE_URL secret is not set"; exit 1; }
          grep -Eq '^age1[02-9ac-hj-np-z]{58}$' .github/backup/age-recipients.txt \
            || { echo "::error::.github/backup/age-recipients.txt has no age recipient"; exit 1; }
      - name: Install PostgreSQL client and age
        run: |
          sudo apt-get update
          sudo apt-get install -y postgresql-common age
          sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -y
          sudo apt-get install -y "postgresql-client-${PG_MAJOR}"
      - name: Dump, compress and encrypt (plaintext never touches disk)
        env:
          BACKUP_DATABASE_URL: ${{ secrets.BACKUP_DATABASE_URL }}
        run: |
          set -euo pipefail
          url=$(printf '%s' "$BACKUP_DATABASE_URL" | bash .github/backup/normalize-pg-url.sh)
          echo "::add-mask::$url"
          bin="/usr/lib/postgresql/${PG_MAJOR}/bin"
          server=$("$bin/psql" "$url" -Atc 'show server_version_num')
          major=$(( server / 10000 ))
          [ "$major" = "$PG_MAJOR" ] || { echo "::error::Postgres server major is $major but PG_MAJOR is $PG_MAJOR; update PG_MAJOR in backup.yml"; exit 1; }
          ts=$(date -u +%Y%m%dT%H%M%SZ)
          "$bin/pg_dump" "$url" --schema=public --no-owner --no-privileges --format=custom \
            | age --encrypt --recipients-file .github/backup/age-recipients.txt --output "backup-$ts.dump.age"
          test "$(stat -c %s "backup-$ts.dump.age")" -gt 1024
      - uses: actions/upload-artifact@v4
        with:
          name: db-backup
          path: backup-*.dump.age
          retention-days: 30
          if-no-files-found: error
          compression-level: 0
```

Decisions:

| Decision | Why |
|---|---|
| **Secret name `BACKUP_DATABASE_URL`**, not `DATABASE_URL` | After ops, only the backup job holds database credentials (keepalive no longer does). The name documents that. Use the **session pooler** URL: the direct host is IPv6-only on Free, and GitHub runners are IPv4. The value is the same `postgres` pooler URL the apps use, because a separate least-privilege role would need BYPASSRLS once RLS is on (pg_dump refuses to run under row security). |
| **`--schema=public`** | All app data, and `alembic_version` from slice 1, lives in `public`. Supabase-managed schemas such as `auth` and `storage` are excluded: they can fail to dump as `postgres`, and the app does not need them. Users simply sign in again with Google and are matched by email. |
| **`--format=custom`** | Already compressed, and it allows a selective `pg_restore`. |
| **`age` on a pipe with `pipefail`** | No plaintext file ever exists on the runner. A `pg_dump` failure fails the job. |
| **Artifacts stay 30 days** | In a public repo any signed-in GitHub user can download them. They are encrypted, so that is acceptable (inv §4 "Critical"). |

**Order (the gate in F §7.2):**
1. ops-1 merges with the encrypted workflow and the real recipients.
2. Only then does the owner add the `BACKUP_DATABASE_URL` secret (repo Settings → Secrets and variables → Actions).
3. Run the workflow by hand (`workflow_dispatch`).
4. Run the restore drill.

Until step 2 the scheduled run fails at "Check prerequisites", which is intended.

**Restore drill** (runbook; once in this slice, then quarterly):

```
gh run download <run-id> -n db-backup                       # or download from the Actions UI
age --decrypt -i <key file from the password manager> -o backup.dump backup-*.dump.age
docker run --rm -d --name wsb-restore -e POSTGRES_PASSWORD=restore postgres:17
until docker exec wsb-restore pg_isready -h 127.0.0.1 -U postgres; do sleep 1; done
docker exec -i wsb-restore pg_restore -h 127.0.0.1 -U postgres -d postgres --no-owner --no-privileges < backup.dump
docker exec wsb-restore psql -h 127.0.0.1 -U postgres -Atc "select 'users', count(*) from users union all select 'churches', count(*) from churches union all select 'services', count(*) from services union all select 'hymns', count(*) from hymns"
docker stop wsb-restore && rm backup.dump                    # the plaintext dump holds Gmail refresh tokens
```

- **Why the wait uses TCP.** The official image first runs a temporary, socket-only server for initdb and then restarts. A socket connection can reach that temporary server and be cut off in the middle of the restore. `pg_isready -h 127.0.0.1` succeeds only once the final server listens on TCP, and the image trusts `127.0.0.1` connections, so no password is needed.
- Expected: at most the harmless "schema "public" already exists" error, and every table restored.
- Compare the counts with the same query run on production in the SQL editor. Rows written between the dump and the check are the only allowed difference.

### Streamlit freeze (S7; F §6.1)

1. **Before the freeze:**
   - ops-3 is merged and CI is green.
   - Run the Streamlit smoke check on the live app, which is still deployed from `main`: sign in, load the church, load an archived service, open Settings. Also confirm the sidebar shows no "Church" selectbox, which the A7 triage row relies on.
   - Record in the runbook the app's Python version and the package versions from its current build log (Streamlit Cloud → Manage app → logs).
2. **Cut the branch** from the ops-3 merge commit:
   ```
   git fetch origin && git push origin <ops-3-merge-sha>:refs/heads/streamlit-frozen
   ```
3. **Protect `streamlit-frozen`** (GitHub → Settings → Branches):
   - require a pull request;
   - require the `backend` status check;
   - block force pushes and deletion.
4. **Redeploy the `liturgy` app** during the agreed window, after sending the tester the "before" message.
   - If the app settings allow changing the branch, set it to `streamlit-frozen` and reboot.
   - Otherwise:
     1. copy the app's Secrets into the password manager;
     2. note the custom subdomain `liturgy` and the Python version;
     3. delete the app;
     4. create a new app from repo `bbrown62450/church`, branch `streamlit-frozen`, main file `app.py`, with the same Python version and the pasted secrets;
     5. set the custom subdomain back to `liturgy`.

   The URL is unchanged, so the Google redirect URIs don't change.
5. **Delete `liturgy-stg`,** and remove its two redirect URIs from the Google OAuth client: `https://liturgy-stg.streamlit.app/oauth2callback` and the bare root `https://liturgy-stg.streamlit.app/`. The production URIs stay.
6. **Verify the freeze:**
   - the smoke check passes on `https://liturgy.streamlit.app/`;
   - the app's settings show branch `streamlit-frozen`;
   - after the next merge to `main`, the app's logs show no new build.

   Then send the tester the "after" message.
7. **Policy** (runbook → "Streamlit freeze"):
   - Only data-safety fixes (data loss, corruption, leakage, security) go into `streamlit-frozen`, as PRs into that branch, and CI runs on them. The one planned exception is the 5b banner.
   - A fix that also concerns backend code on `main` is fixed on `main` separately, with its own tests.
   - Streamlit code on `main` is not maintained (F §2.3.7).
   - If a Streamlit Cloud reboot breaks the frozen app because a dependency released a new version, the fix is to pin the versions recorded in step 1 in the frozen branch's `requirements.txt`. That counts as a data-safety fix, because it restores the tester's access to their data.
8. **Contingency** (F §6.1.6): if the redeploy is impossible,
   - revert the FROZEN header in `app.py`;
   - keep `app.py` working against `main`;
   - add an `AppTest` smoke test;
   - record this in the runbook.

**What the frozen app inherits from ops.** It is cut after ops-2 and ops-3, so it includes:
- `ensure_user`, through `upsert_from_claims`:
  - Streamlit still writes `google_sub` when Google supplies one;
  - it now writes `last_login_at` at most hourly;
  - it no longer races on insert;
  - per rerun, it runs an `INSERT … ON CONFLICT DO NOTHING` plus a SELECT, instead of a SELECT plus an unconditional UPDATE.
- **Pool 5+5 and `connect_timeout=10`** instead of SQLAlchemy's default 5+10 with no timeout. Before ops each process can hold 15 pooler sessions, so the API plus `liturgy` can hold 30, and 45 while `liturgy-stg` still runs against the same database. After the freeze the worst case is 2 × (5+5) = 20. Risks, item 2 compares this with the pooler's size.
- **The D5 fix** (S16, ops-1).
- **The deleted dead modules,** which it never imported.

The `streamlit_tests/` suite, the D5 manual check and the step-1 smoke check cover the first three before the branch is cut.

**Streamlit bug triage** (recorded in the runbook → "Streamlit freeze"). Every Streamlit bug in the inventory was checked against the policy's definition: data loss, corruption, leakage, security. "Stored data" means rows in the database; losing text typed but not yet saved is a usability bug, not a data-safety one.

| Inventory | Bug | Meets the definition? | Disposition |
|---|---|---|---|
| D5, and F6 "drops a loaded service's own hymns" | With "Exclude hymns used in the last 12 weeks" ticked, Prepare records the picks and reruns; the picks are now "recent", `safe_hymn_selectbox` resets them to '', and the next Prepare or Save stores no hymns. Loading a recent archived service with the box ticked drops its hymns, and "Save changes" then overwrites the archived hymns. | **Yes: silent loss of stored data in the normal Prepare → Save flow** | **Fixed in ops-1** (below). Until the fix is live, the tester gets the D5 workaround message on day one. |
| A7 | A Word file prepared for church A can be downloaded or emailed while church B is active, to church B's contacts. | Leakage, in principle | **Accepted.** The tester belongs to one church, and Streamlit offers no way to join or create a second one (onboarding runs only at zero churches, inv A5), so the switcher never renders (the pre-freeze smoke check confirms there is no "Church" selectbox in the sidebar). React keys the draft and documents by church (slice 2, 5a). |
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
| inv §4 | The Data API exposed the tables; backups were unencrypted. | Security | **Fixed in ops** (Step 0, S2), outside the Streamlit code. |
| inv §4 | Gmail refresh tokens are stored in plaintext. | Security | **Deferred to slice 7** (F §6.4), because the frozen app reads them. The lockdown and the encrypted backups remove the exposure paths. |

**The D5 fix (S16, ops-1).** It is minimal and changes nothing else:
- `ui_helpers.py` gains a pure helper:
  ```python
  def hymn_options_excluding_recent(title_to_info: dict, recent_used: set, keep: set[str]) -> list[str]:
      """Sorted title keys without recently used hymns, but never without a key in `keep`
      (the hymns already picked in the three slots)."""
  ```
- `app.py:735-746`: when the box is ticked, `keep = {st.session_state.get(s, "") for s in ("opening", "response", "closing")} - {""}`, and `titles_sorted = hymn_options_excluding_recent(title_to_info, recent_used, keep)`. The caption still reports `len(title_to_info) - len(titles_sorted)`, so a kept pick is not counted as excluded. Recent hymns that are not picked stay hidden.
- Why this covers every path:
  - after Prepare, the picks are recent but in `keep`, so they stay among the options and `safe_hymn_selectbox` no longer resets them;
  - loading an archived service writes its hymns into the three slot keys (`app.py:401-404`) before this block runs;
  - an AI-applied pick is stored and followed by `st.rerun()` (`app.py:817`), so it is in `keep` on the next run.
- **Recovery (owner, after the fix is live).** Find archived services saved without hymns:
  ```sql
  select church_id, service_date_iso, occasion, saved_at from services
  where case when hymns is null or jsonb_typeof(hymns::jsonb) <> 'array' then true
             else jsonb_array_length(hymns::jsonb) = 0 end
  order by service_date_iso desc;
  ```
  For each row, `select hymn_number, hymn_title from hymn_usage where church_id = '<id>' and date_iso = '<service_date_iso>'` lists the hymns picked when it was prepared. Ask the tester whether the service really had no hymns. If it had hymns, the tester loads it, picks them again and clicks "Save changes".

**`main` after the freeze** (in ops-3):
- `app.py` starts with the comment `# FROZEN — production runs from branch streamlit-frozen; deleted in slice 7.`
- `keep-awake.yml` sets `APP_URLS: "https://liturgy.streamlit.app/"`, dropping `https://liturgy-stg.streamlit.app/` (currently `keep-awake.yml:24`).

---

## Frontend changes

- **`frontend/package.json`:** move `"shadcn": "^4.21.0"` from `dependencies` to `devDependencies` with `npm install --save-dev shadcn@^4.21.0`, and commit the regenerated `package-lock.json`.
  - `src/app/globals.css:3` imports `shadcn/tailwind.css`. That import is resolved at build time, and Vercel installs devDependencies for the build.
  - Check that the Vercel project has no custom install command using `--omit=dev` and no `NPM_CONFIG_PRODUCTION`.
- **No code changes:**
  - `src/lib/api.ts` already reads only `error.code` and `error.message`, so the new `request_id` field and header are ignored until slice 1.
  - No routes, components, draft store or query cache are touched.
- **Handoff to slice 1:** `ApiError` gains `requestId` from `error.request_id`, falling back to the `X-Request-Id` header, and the UI kit shows "Something went wrong. (Ref: {first 8 chars})" (F §2.5, §4.8).

---

## Behavior changes vs Streamlit (and vs slice 0)

| # | Change | Who notices | Kind |
|---|---|---|---|
| 1 | `users.last_login_at` is written at most once an hour per user, by both the API and the frozen Streamlit app. It now means "last seen, to the hour". Nothing reads it. | nobody | intentional (F §2.4) |
| 2 | Concurrent first requests for a new email all succeed. Before, the second one got a 500 (inv A2). | React in StrictMode dev; a first sign-in with parallel calls | bug fix |
| 3 | Authenticated API requests stop writing to `users` on every call: at most one identity read per 5 minutes per user. | nobody (fewer writes and pool checkouts) | intentional |
| 4 | Unexpected 500s carry CORS headers, so the browser sees a 500 instead of a network error. | the React UI (the correct message appears) | bug fix (F §7.3) |
| 5 | Every response the app produces has `X-Request-Id` (CORS preflights excepted), and every error body has `request_id`. Log lines carry `request_id=`. | owner, when debugging | additive |
| 6 | A trailing slash returns 404 instead of a 307 redirect. | nobody (no caller uses one) | intentional (F §1.1) |
| 7 | CORS allows `Idempotency-Key`, `If-Match` and `X-Request-Id`, and exposes `Content-Disposition`, `Retry-After` and `X-Request-Id`. | later slices | additive |
| 8 | With `APP_ENV=production`, the API refuses to start on SQLite, rather than silently using an ephemeral file on Railway. An invalid `APP_ENV` or pool setting also stops startup. | owner (deploy fails and the old release keeps serving) | intentional |
| 9 | The Postgres pool is 5+5 with a 10 s connect timeout, instead of 5+10 with no timeout, in both apps. | nobody | intentional |
| 10 | New `GET /health/ready`. | keepalive | additive |
| 11 | Keepalive goes through the API; no database secret is stored in GitHub for it. `keepalive.py` is deleted. | owner | intentional |
| 12 | Backups are encrypted, in custom format, cover `public` only, and use the secret `BACKUP_DATABASE_URL`. The old workflow never ran successfully, because the secret was never added. | owner | intentional, security fix |
| 13 | The Supabase Data API is off; the `anon` and `authenticated` roles have no table grants, and RLS is on. No app feature used the Data API. | nobody (closes a possible exposure) | security fix |
| 14 | Production Streamlit runs from `streamlit-frozen`. Merges to `main` no longer redeploy it. `liturgy-stg` no longer exists. | tester (one short outage), owner | intentional (owner decision 7) |
| 15 | Six dead modules and `repos.users.upsert_user` are removed. | nobody | cleanup |
| 16 | `upsert_user`'s "overwrite when not None" rule is gone; the only surviving rule is "overwrite when truthy". | nobody (it had only test callers) | intentional |
| 17 | Streamlit: with "Exclude hymns used in the last 12 weeks" ticked, hymns already picked in the three slots stay selectable, so Prepare, Save and loading a recent service no longer clear them. Recent hymns that are not picked stay hidden. | tester | data-safety fix (inv D5; owner decision 7) |
| 18 | `/health/ready` reuses its last result for up to 10 s (ok) or 5 s (failed), and runs one probe at a time. | nobody | intentional |

---

## Testing

The backend is tested with pytest from the repo root (`.venv/bin/python -m pytest -q`). Tests are written first in each PR.

### Backend

**`backend/tests/conftest.py`** (modified):
- ops-2: an autouse fixture calls `api.deps.clear_identity_cache()` before each test.
- ops-2: a `FakeClock` helper (`now()` returns the current value; `advance(seconds)`), and an `identity_clock` fixture that does `monkeypatch.setattr(api.deps, "_identity_cache", IdentityCache(maxsize=1024, ttl=300, clock=clock.now))` and returns `clock`. This works because `get_current_user` reads `api.deps._identity_cache` on every call.
- ops-3: an autouse fixture calls `db.health.reset_readiness_for_tests()` before each test.

Ops adds no `backend/tests/test_cache.py`; slice 2 creates it with `cache.py`.

**`backend/tests/test_identity_cache.py`** (new, ops-2)
- `get` returns the stored `CachedIdentity` before the TTL and `None` after it (fake clock); an expired entry is removed, so `len` drops.
- The least recently used entry is evicted at `maxsize + 1`; a `get` refreshes recency.
- `clear` empties it.
- 8 threads × 1 000 mixed `put`/`get` calls raise nothing, and `len <= maxsize`.
- Success-only: with `api.deps.ensure_user` monkeypatched to raise `OperationalError` and `TestClient(app, raise_server_exceptions=False)`, `/me` returns 500 and the cache stays empty (`len == 0`); the next `/me`, with `ensure_user` restored, runs it and returns 200.

**`backend/tests/test_upsert.py`** (new, ops-2)
- On a `tmp_db`, `insert_ignore(User.__table__)` with `.on_conflict_do_nothing(index_elements=["email"])` inserts once, and a second execute leaves one row. `insert_ignore(User)`, with the mapped class, behaves the same.
- `insert_ignore(User.__table__, dialect_name="mysql")` raises `NotImplementedError`.
- With `dialect_name="postgresql"`, the statement compiles to `ON CONFLICT (email) DO NOTHING`, checked by compiling with the Postgres dialect without connecting.

**`backend/tests/test_identity.py`** (new, ops-2)

`ensure_user`:
- creates a user with a normalized email, `created_at == last_login_at == now`, and google_sub only when it is passed;
- is idempotent across case differences (one row) and updates name and picture only when they are truthy and different;
- a falsy name never blanks a stored one;
- with `now` = the stored `last_login_at` + 59 min: no UPDATE. With + 61 min: `last_login_at` is updated. Count statements with a `before_cursor_execute` listener;
- a naive stored `last_login_at` (SQLite) is treated as UTC;
- an empty email raises `ValueError`;
- `session=` makes it join the caller's transaction: a rollback of the outer scope leaves no row.

Race:
- 8 threads released together by a `threading.Barrier` call `ensure_user("race@example.com")` on one SQLite file. All return the same id, and `count(*) == 1`.
- Slice 1 adds a `@pytest.mark.postgres` copy.

Wrapper:
- `auth.upsert_from_claims` delegates to `ensure_user`, and the existing `test_auth.py` passes unchanged, including the google_sub assertion.

API identity:
- **Ten sequential `/me`** calls with one token cause exactly one `INSERT INTO users`, zero `UPDATE users` and one `SELECT … FROM users` (F acceptance criterion 3).
- **Two concurrent `/me`** calls for a new email (ThreadPoolExecutor) both return 200 with the same `user.id`.
- **TTL** (uses `identity_clock`): after `/me`, `identity_clock.advance(301)`. The next `/me` runs one users SELECT and no UPDATE. With `advance(299)` instead, it runs no users statement.
- **Profile change:** a token whose `user_metadata.full_name` changed causes exactly one UPDATE, even on a cache hit.
- **No cross-user leak:** tokens for A then B return different ids.
- **Tenancy is not cached:**
  - warm the cache with `/church` → 200;
  - delete the membership → the next `/church` returns 403;
  - soft-delete a second church the user belongs to → 403;
  - an `X-Church-Id` for another church → 403, with the church name absent from the body.

  The same guarantees as `test_api_me.py:97-113`, now with a warm cache.
- **Token verification still runs on a cache hit:** an expired or other-provider token returns 401 even when the email is cached.

**`backend/tests/test_users_repo.py`** (ported, ops-2): the `upsert_user` tests become `ensure_user` tests with the same assertions (lower-casing, google_sub stored, idempotent update, empty email rejected). The `get_user` and `get_user_by_email` tests keep their assertions, but their setup changes from `upsert_user(email=…)` to `ensure_user(…).id`, because `upsert_user` no longer exists (`test_users_repo.py:3, 25`). The import line drops `upsert_user`.

**`backend/tests/test_engine.py`** (extended, ops-2)
- `_engine_kwargs("postgresql://u:p@h/db")` returns `pool_size == 5`, `max_overflow == 5`, `pool_recycle == 1800`, `pool_pre_ping is True`, `connect_args == {"connect_timeout": 10}`.
- `DB_POOL_SIZE=2`, `DB_MAX_OVERFLOW=0` are honored.
- `DB_POOL_SIZE=abc` and `DB_POOL_SIZE=0` raise `ValueError` with the exact copy. A blank value gives the default.
- For SQLite: no pool size keys, and `check_same_thread` is False.
- `_make_engine("postgresql://…").pool.size() == 5`, with no connection opened.

**`backend/tests/test_middleware.py`** (new, ops-3)
- `GET /health` has `X-Request-Id` matching `^[0-9a-f]{32}$`.
- An inbound `X-Request-Id: abcd-1234-efgh` is echoed. Inbound `bad id!`, `short` (7 characters) and a 65-character id are each replaced.
- Unknown route (404), `/me` without a token (401), and a 422 from the `needs-int` route: each body has `error.request_id` equal to the header.
- **CORS on 500 (F acceptance criterion 2):**
  - `TestClient(app, raise_server_exceptions=False)` with a route that raises `RuntimeError("secret detail")`, `CORS_ORIGINS=https://church.example.app` and `Origin: https://church.example.app`;
  - expect status 500, body `{"error": {"code": "internal_error", "message": "Something went wrong.", "request_id": <header>}}`, `access-control-allow-origin == "https://church.example.app"`, `x-request-id` present, and `"secret detail"` absent from the body;
  - with `Origin: https://evil.example`: still 500, with no `access-control-allow-origin`.
- **Response already started:** a pure-ASGI unit test with a fake app that sends `http.response.start` and then raises. `UnhandledErrorMiddleware` re-raises and never calls `send` with a second start.
- **Request id in logs:** a sync `def` route (threadpool) logs "hello". The `caplog` record's `request_id` equals the response header. A log outside any request has `request_id == "-"`.
- `configure_logging` called twice doesn't nest record factories. `LOG_LEVEL=verbose` logs the WARNING copy and uses INFO.
- `GET /health/` returns 404 `not_found` with no `location` header.
- **CORS preflight** with `Access-Control-Request-Headers: authorization, content-type, x-church-id, idempotency-key, if-match, x-request-id` → 200. `access-control-allow-headers` lists all six, and `access-control-max-age: 600`. A simple GET's `access-control-expose-headers` includes `x-request-id`, `content-disposition` and `retry-after`.
- **Middleware order:** walk `app.user_middleware` and assert the order is CORS, RequestId, UnhandledError, outermost first.

**`backend/tests/test_api_app.py`** (modified, ops-3): `test_unhandled_exception_is_a_generic_500` asserts `code`, `message`, a 32-hex `request_id` equal to the header, and no "secret detail". Every other test stays.

**`backend/tests/test_startup.py`** (new, ops-3)
- `describe_database(make_url("postgresql+psycopg2://alice:s3cret@aws-0-x.pooler.supabase.com:5432/postgres"))` returns `"dialect=postgresql driver=psycopg2 host=aws-0-x.pooler.supabase.com database=postgres"`. Neither `alice` nor `s3cret` appears.
- On a `tmp_db`, lifespan logs `Database: dialect=sqlite driver=pysqlite`.
- **Production guard (F acceptance criterion 4):**
  - with `APP_ENV=production` and a SQLite `tmp_db`, `with TestClient(create_app())` raises `RuntimeError` with the exact copy;
  - a monkeypatched `api.main.init_db` spy is **not** called.
- `APP_ENV=staging` raises with the exact copy. `APP_ENV=" Production "` is accepted.
- With `APP_ENV=production`, `CORS_ORIGINS=http://localhost:3000`, and the engine replaced by `_make_engine("postgresql://u:p@localhost:1/db")` with `init_db` stubbed so nothing connects: an ERROR record with the exact copy. With `https://worship-service-builder.vercel.app`: no such record.
- With `APP_ENV=development` and SQLite: startup succeeds, with no ERROR.
- The existing SUPABASE_URL warning test keeps passing.

**`backend/tests/test_health_ready.py`** (new, ops-3)
- On a `tmp_db`: 200 `{"ok": true, "db": "ok"}` with no auth; also with a junk `Authorization` and `X-Church-Id`.
- With `db.health.get_engine` monkeypatched to `_make_engine("sqlite:////nonexistent-dir/x.db")`: 503, body code `db_unavailable`, message "The database is not reachable.", a `request_id`, and a WARNING log naming only the exception class.
- The route is a sync `def`: `inspect.iscoroutinefunction` is False.
- **Memo** (`database_ready(clock=fake)`, with `_probe` replaced by a counting stub):
  - two calls 9 s apart → one probe; a call at 11 s → a second probe;
  - a failing probe is reused for 5 s and retried at 6 s;
  - 16 threads released together by a `threading.Barrier`, with a stub that sleeps 0.2 s → exactly one probe, and every thread gets its result.
- The route module contains no SQL: `api/routes/health.py` does not import `sqlalchemy`.

**`backend/tests/test_ops_workflows.py`** (new, replaces `test_keepalive.py`; built in ops-1, extended in ops-3)

`backup.yml`:
- contains `schedule:`, `workflow_dispatch`, `contents: read`, `secrets.BACKUP_DATABASE_URL`, `pipefail`, `bash .github/backup/normalize-pg-url.sh`, `--recipients-file .github/backup/age-recipients.txt`, `postgresql-client-${PG_MAJOR}`, `--schema=public`, `--format=custom`, `.dump.age`, `retention-days: 30`;
- does **not** contain `secrets.DATABASE_URL`, `.sql.gz`, ` -f "backup`, or `+psycopg2`.

`PG_MAJOR` (ops-1):
- read `PG_MAJOR` from `backup.yml` (parsed as YAML: `jobs.dump.env.PG_MAJOR`) and the `- Postgres server major: <N>` line from `docs/ops-runbook.md`; both exist and are equal;
- if `.github/workflows/ci.yml` declares any `postgres:<N>` image (slice 1's service container), `<N>` equals `PG_MAJOR`. Until slice 1 adds that job the check finds no image and passes. It is the only check of the CI Postgres major: slice 1's `test_ci_workflow.py` deliberately does not assert it.

`normalize-pg-url.sh` (run as `bash .github/backup/normalize-pg-url.sh`, exactly as the workflow runs it; stdin to stdout):
- `postgresql+psycopg2://u:p@h:5432/db` → `postgresql://u:p@h:5432/db`;
- `postgres://u:p@h/db` → `postgresql://u:p@h/db`;
- `postgresql://u:p@h/db` is unchanged;
- stderr is empty.

`age-recipients.txt`:
- exists, has at least one recipient line, and every non-blank, non-`#` line matches the recipient regex;
- no file under `.github/` or `docs/` contains `AGE-SECRET-KEY-`.

`keepalive.yml`:
- contains `schedule:`, `cron:`, `/health/ready`, `vars.API_BASE_URL`, `--fail`;
- contains no `secrets.` and no `python keepalive.py`.

`keep-awake.yml` (ops-3): contains `https://liturgy.streamlit.app/` and not `liturgy-stg`.

**`backend/tests/test_foundation_setup.py`** (extended, ops-1; the last item in ops-3)
- `backend/.env.example` contains `APP_ENV=`, `LOG_LEVEL=`, `DB_POOL_SIZE=`, `DB_MAX_OVERFLOW=`, `ESV_API_KEY=`.
- `frontend/package.json`, parsed as JSON: `shadcn` is in `devDependencies` and not in `dependencies`.
- None of the six deleted modules exists under `backend/`.
- If `frontend/src/lib/api/errors.ts` exists, it contains `"db_unavailable"`. The file does not exist until slice 1, so the check is inert until then.

**`streamlit_tests/test_app_helpers.py`** (extended, ops-1; the D5 fix, written first)
- `hymn_options_excluding_recent`: with three hymns A, B, C where A and B are recent and A is in `keep`, the result is `["a", "c"]` (sorted keys); with an empty `keep` it is `["c"]`; a non-recent hymn is always present.
- A key in `keep` that is not in `title_to_info` (a renamed or deleted hymn) is not added.
- **Regression for the D5 flow:** on a `tmp_db` with `make_church` (both already re-exported by `streamlit_tests/conftest.py`), record usage for the three picks with `hymn_usage.record_usage` for today's date, compute `recent_used` with `get_recently_used_identifiers`, then build the options with the picks in `keep`. `coerce_selectbox_value(pick, [""] + options)` returns each pick unchanged. Without the picks in `keep` it returns `""`, which is the bug.
- These tests cover a Streamlit-only fix and are not ported. Slice 6b's port ledger records them as "DROPPED: Streamlit-only fix; intent covered by slice 3 test that exclusion never clears a pick (hymns-step DOM test, AC 12)".

**Unchanged and must stay green:**
- `test_auth.py`, `test_api_me.py`, `test_api_security.py`, `test_docs.py` (the README still mentions keep-alive), `test_ci_workflow.py`, `test_no_streamlit_in_core.py`;
- all of `streamlit_tests/`. If an ops change breaks one, port it per F §2.3.7.

**Cross-church isolation and role checks:** this slice adds no church-scoped or role-guarded route. The regression tests under "Tenancy is not cached" prove that the identity cache cannot weaken `require_church`.

### Frontend

- No new tests; no behavior changes.
- CI's `npm ci`, lint, typecheck, `npm test` and `npm run build` must pass with `shadcn` as a devDependency.
- The Vercel preview build of the ops-1 PR and the production deploy after merge must succeed.

### Manual checks

These are appended to `docs/manual-verification.md` as "## Ops slice" (F §5.5). Run at 375 px (Chrome device mode, iPhone SE) and on desktop, where the app is involved.
- [ ] Step 0 recorded in `docs/ops-runbook.md`: exposure curls before and after (anon and authenticated), GraphQL introspection, table owners and BYPASSRLS, `server_version` and the `- Postgres server major:` line, pooler pool size, Railway request limit with its source. If step 1 returned rows: the incident record, including the users/contacts audit and where the forensic dump is kept.
- [ ] D5 workaround message sent to the tester on day one.
- [ ] D5 fix, after ops-1 is live (Streamlit still deploys from `main`). Do it in a throwaway church so no usage rows land in the tester's church: sign in with a second Google account that has no church, create "Ops test", and delete it afterwards in Settings → Danger zone. Tick "Exclude hymns used in the last 12 weeks", pick three hymns, click "Prepare bulletin copy": the three picks are still selected. Click "Prepare pastor's copy": both Word files list the three hymns. Save, load the service again with the box still ticked: its three hymns are in the slots. Then run the recovery query, record the result in the runbook, and send the tester the "fixed" message.
- [ ] `https://worship-service-builder.vercel.app`, after the lockdown and after each ops merge: sign in, the church shows in the switcher, switch church if you have two, log out.
- [ ] `db-backup` run by hand: green, with an artifact `backup-*.dump.age`; the log shows no URL or password. The restore drill's counts match production.
- [ ] `https://<railway-domain>/health/ready` → `{"ok":true,"db":"ok"}`. The `keepalive` run by hand is green.
- [ ] Railway deploy log after ops-3: `Database: dialect=postgresql driver=psycopg2 host=…pooler.supabase.com database=postgres`, with no username or password, and no CORS ERROR line.
- [ ] Browser devtools on the Vercel app: `/me` has an `x-request-id` response header, readable from JS (exposed).
- [ ] `curl -i https://<railway-domain>/me/` → 404 JSON with `request_id`, not a 307.
- [ ] Streamlit before the freeze and after the redeploy: sign in, load the church, load an archived service, open Settings. The app settings show branch `streamlit-frozen`. After the next merge to `main`, no new Streamlit build.
- [ ] `liturgy-stg` is gone; its two redirect URIs are removed from the Google OAuth client; `keep-awake` is green with one URL.

`docs/ops-runbook.md` (new) has these sections:
1. Environments and variables: Railway, Vercel, GitHub secrets and variables, Streamlit Cloud.
2. Supabase lockdown record.
3. Backups: key custody, schedule, restore drill, how to rotate the `age` key.
4. Keep-alive.
5. Streamlit freeze: record, policy, the bug triage table, the D5 recovery query's result, recorded Python and package versions.
6. Platform limits: Railway request limit; Postgres version, with the exact line `- Postgres server major: <N>` that `test_ops_workflows.py` reads; pooler pool size and the pool values set in each app (Risks, item 2).
7. Incident response: the procedure (Step 0), and the incident record if step 1 returned rows: log review, users/contacts audit, other tables checked, repairs, `oauth_states` purge, invite revocation, and the forensic dump's file name and location.

**README → Operations** changes:
- "Keep-alive" now describes the `/health/ready` curl and the `API_BASE_URL` variable, and needs no secret.
- "Backups" describes encrypted artifacts, `BACKUP_DATABASE_URL`, and the runbook's key custody and restore drill.
- The rest of the README waits for slice 7.

---

## Acceptance criteria

1. **Lockdown.** The anonymous and the authenticated `/rest/v1` curls for `users`, `gmail_tokens`, `invites` and `memberships` return no rows, and the GraphQL introspection lists no app tables. The results, with dates, are in the runbook. If step 1 returned rows, the incident record is complete, including the users/contacts audit. *(deployed)*
2. **Apps unaffected.** After the lockdown, `/me` works on the Vercel URL and Streamlit loads the tester's church. *(deployed)*
3. **Backups are encrypted and restorable.**
   - `backup.yml` matches the spec, and `test_ops_workflows.py` passes, including `PG_MAJOR` equal to the runbook's recorded server major.
   - A manual run produces `backup-*.dump.age`, and the log shows no URL or password.
   - The restore drill restores every table, with counts matching production.
   - `BACKUP_DATABASE_URL` was added only after the encrypted workflow merged.

   *(test + deployed)*
4. **Readiness.** `GET /health/ready` returns 200 `{"ok": true, "db": "ok"}` with no auth, and 503 `db_unavailable` with `request_id` when the database is unreachable. Results are memoized (10 s ok, 5 s failed) and concurrent calls run one probe. The route holds no SQL. *(test + deployed)*
5. **Keep-alive.** `keepalive.yml` references no secret, curls `${API_BASE_URL}/health/ready`, and a manual run is green. `backend/keepalive.py` no longer exists. *(test + deployed)*
6. **Dead code.** The six modules no longer exist; the whole-word search `grep -rnwE '(email_send|notion_archive|notion_usage|select_sunday_hymns|add_hymnary_links|fix_hymn_titles)' --include='*.py' backend app.py streamlit_* ui_helpers.py` finds nothing; `pytest -q` passes. Whole-word matching matters: `migrate_to_db.py`, kept until slice 7, defines `fetch_notion_archive_pages` and `fetch_notion_usage_pages` (lines 486, 492, 540, 542), which a substring search would report. *(CI)*
7. **Config.** `backend/.env.example` lists `APP_ENV`, `LOG_LEVEL`, `DB_POOL_SIZE`, `DB_MAX_OVERFLOW` and `ESV_API_KEY`. *(test)*
8. **shadcn.** `shadcn` is a devDependency only. The CI frontend job passes, the Vercel production deploy succeeds, and sign-in works at 375 px. *(CI + deployed)*
9. **CORS-safe 500s.** A route that raises returns 500 with the uniform body including `request_id`, plus `X-Request-Id` and `access-control-allow-origin` for an allowed origin, and never the exception text (F acceptance criterion 2). *(test)*
10. **Request ids.** Every response produced inside the app has `X-Request-Id`, including 404, 401, 422 and the `UnhandledErrorMiddleware` 500. CORS preflights, which `CORSMiddleware` answers from outside `RequestIdMiddleware`, and the last-resort `ServerErrorMiddleware` 500 are excluded. A valid inbound id is echoed and an invalid one replaced. Every error body's `request_id` equals the header. A log record from a sync route carries the same id. *(test)*
11. **Routing and CORS.** `GET /health/` → 404 `not_found` with no redirect. The CORS preflight allows the six headers with `max-age` 600, and responses expose `X-Request-Id`, `Content-Disposition` and `Retry-After`. *(test)*
12. **Identity race.** Two concurrent first `/me` calls for a new email both return 200 with the same user id. Eight concurrent `ensure_user` calls create one row (F acceptance criterion 3, first half). *(test)*
13. **Fewer identity writes.** Ten sequential authenticated requests cause at most one `users` write and exactly one `users` SELECT. After the 5-minute TTL, one SELECT and no UPDATE. `last_login_at` is updated only when it is more than an hour old (F acceptance criterion 3, second half). *(test)*
14. **Tenancy not cached.** With a warm identity cache, removing a membership or soft-deleting the church makes the next `/church` return 403. *(test)*
15. **Streamlit identity parity.** `test_auth.py` passes unchanged (google_sub is still written from Streamlit claims), and `upsert_user` is gone with its tests ported. *(test)*
16. **Startup.**
    - Startup logs `dialect`, `driver`, `host` and `database`, with no credentials.
    - `APP_ENV=production` with SQLite refuses to start before `init_db` runs.
    - An invalid `APP_ENV` refuses to start.
    - Localhost-only CORS in production logs the ERROR (F acceptance criterion 4).

    *(test)*
17. **Pool.** The Postgres engine uses pool 5+5, `pool_recycle` 1800, pre-ping and `connect_timeout` 10, overridable by `DB_POOL_SIZE` and `DB_MAX_OVERFLOW`; invalid values raise with the exact copy. *(test)*
18. **Railway.** `APP_ENV=production` is set, and the deploy log shows the Postgres pooler host with no credentials and no CORS ERROR. *(deployed)*
19. **Railway limit.** Railway's request limit is recorded in the runbook with its source and date, and it is at least 120 s. If it is lower, slices 3 and 4 have been told before this criterion is signed off. *(doc)*
20. **Branch.** `streamlit-frozen` exists at the ops-3 merge commit and is protected: PR required, `backend` check required, no force push, no deletion. *(deployed)*
21. **Frozen app.** The `liturgy` app serves from `streamlit-frozen` at `https://liturgy.streamlit.app/`, and the smoke check passes. A later merge to `main` does not redeploy it. *(deployed)*
22. **Staging gone.** `liturgy-stg` is deleted, and its two Google redirect URIs are removed. `keep-awake.yml` pings only production, and its next run is green. `app.py` on `main` carries the FROZEN header. *(deployed + test)*
23. **Docs.** `docs/ops-runbook.md` has the seven sections, filled in. The README Operations section is updated. `docs/manual-verification.md` has an "Ops slice" section, and every box is checked on the production URLs. *(review)*
24. **CI.** The whole backend suite (`backend/tests` and `streamlit_tests`) and the frontend checks are green on the final ops PR. *(CI)*
25. **Streamlit D5 fix.** With "Exclude hymns used in the last 12 weeks" ticked, hymns already picked survive Prepare, Save and loading a recent service: `test_app_helpers.py` covers the helper and the regression, and the D5 manual check passes on the live app before the branch is cut. The triage table is in the runbook, the tester got the workaround message on day one and the "fixed" message afterwards, and the recovery query's result is recorded. *(test + deployed)*
26. **No cache overlap with slice 2.** Ops creates no `backend/cache.py` and no `backend/tests/test_cache.py`. The identity cache lives in `api/identity_cache.py`, stores only successful `ensure_user` results, and a TTL test drives it through the `identity_clock` fixture. *(test + review)*

---

## Risks and open questions

1. **Open until Step 0 runs: can RLS be enabled safely?**
   - If the pooler role neither owns the tables nor has BYPASSRLS, enabling RLS with no policies would hide every row from both apps.
   - In that case ops applies only the Data API switch-off and the REVOKEs, which already close the exposure, and slice 1 must decide on its own: transfer table ownership to the app role, or add permissive policies for it.
   - Slice 1's `0003_lockdown` must read the recorded result, not assume it.
2. **Open until Step 0 runs: the pooler's session limit.**
   - **Budget.** Before ops each process can hold SQLAlchemy's default 5+10 = 15 sessions: 30 for the API plus `liturgy`, and 45 while `liturgy-stg` still runs against the same database. After ops-2 and the freeze, each app holds at most `DB_POOL_SIZE + DB_MAX_OVERFLOW` = 10, so 20. `/health/ready` checks out from the API's pool, so it adds nothing beyond it (and the memo keeps it to one connection). Outside the pools, allow 2 more: the backup job holds one session at a time (the `psql` version check, then `pg_dump`, which uses one connection without `-j`), and the owner's SQL editor or `psql` holds one. Real use by one tester is 2–4.
   - **Trigger:** the recorded pooler pool size is less than 2 × (`DB_POOL_SIZE` + `DB_MAX_OVERFLOW`) + 2, which is 22 with the defaults.
   - **Action if it fires:** set `DB_POOL_SIZE=3` and `DB_MAX_OVERFLOW=2` in **both** apps before ops-2 merges (the code reads them from ops-2 on, and setting them earlier is harmless). That needs 2 × 5 + 2 = 12.
     - API: Railway service variables.
     - Streamlit: top-level keys `DB_POOL_SIZE = "3"` and `DB_MAX_OVERFLOW = "2"` in the `liturgy` app's Secrets. Streamlit Cloud exposes top-level secrets as environment variables, so no code change is needed, and the frozen branch reads them through `db/engine.py`.
     - If the pool size is below 12, use `DB_POOL_SIZE=2` and `DB_MAX_OVERFLOW=1` (needs 8).
     - Record the values in the runbook → "Platform limits".
3. **Open, owner: is 30 days of daily encrypted artifacts enough retention?**
   - The default, if unanswered, is yes until slice 7. GitHub artifacts cannot be kept longer than 90 days, and anything longer-term means copying artifacts to storage the owner controls.
   - This does not block the slice.
4. **Streamlit Cloud redeploy.** If the branch can't be changed in place, the app must be deleted and recreated.
   - Two risks: the `liturgy` subdomain may not be reclaimable right away, and the tester's session cookie resets.
   - Mitigation: the scheduled window, the tester messages, and the recorded secrets. The fallback is F §6.1.6 (contingency, step 8).
5. **Dependency drift on the frozen app.** A reboot reinstalls unpinned requirements. Mitigation: record the versions at freeze time, and pin on breakage as a data-safety fix (freeze policy, step 7).
6. **Key custody.** If every `age` private key is lost, every backup is unreadable. Mitigation: the password manager plus an offline copy, an optional second recipient, and the restore drill every quarter.
7. **GitHub disables scheduled workflows** in public repos after 60 days without activity. Commits during the migration prevent it; slice 7 decides on an off-GitHub pinger (inv §6).
8. **Incident scope.** If Step 0 finds exposed data, the incident steps (forensic dump, log review, the users/contacts and wider tampering audit, repairs, `oauth_states` purge, invite revocation, Gmail reconnect) come before everything else in this slice and may add work beyond size M.
