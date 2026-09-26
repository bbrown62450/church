# Ops-3: API Platform, Readiness, Keep-alive and the Streamlit Freeze — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship PR ops-3 of the ops slice, then the Freeze. ops-3 adds request ids on every response, CORS-safe 500s, the final CORS lists, `redirect_slashes=False`, logging with `request_id=`, the `APP_ENV` startup guards and `GET /health/ready`. `keepalive.yml` then curls `/health/ready` and holds no database secret, and `app.py` on `main` gets its FROZEN header. The Freeze then serves the production Streamlit app `liturgy-next` (https://liturgy-next.streamlit.app) from a protected `streamlit-frozen` branch: the new app is built and checked on a temporary subdomain while `liturgy-next` keeps serving, and a short window then moves it onto the `liturgy-next` subdomain.

**Architecture:** Two pure-ASGI middlewares in `backend/api/middleware.py` sit inside `CORSMiddleware`, in this order: CORS → `RequestIdMiddleware` → `UnhandledErrorMiddleware`. So every response the app produces carries `X-Request-Id`, and an unexpected exception becomes the uniform 500 body with CORS headers instead of a network error. A contextvar holds the request id. Error bodies read it (`api/errors._body`), and so does a log-record factory (`api/logging_config`) that stamps `request_id` on every record. `api/startup.py` holds the pure startup checks the lifespan runs before `init_db()`. `db/health.py` holds the memoized, single-flight `SELECT 1` probe; the public route `/health/ready` only calls it. Workflows, docs and the runbook are guarded by pytest tests in `backend/tests/test_ops_workflows.py`. The Freeze is owner work in Streamlit Community Cloud (it cannot change an app's branch, so an app from `streamlit-frozen` is pre-flighted on a temporary subdomain, then `liturgy-next` is deleted and the checked app takes over its subdomain and Secrets) plus two git commands, recorded in `docs/ops-runbook.md`.

**Tech Stack:** Python 3.11, FastAPI 0.141.1 / Starlette 1.7.0 (pure ASGI middleware, `CORSMiddleware`, `TestClient`), anyio 4.15 (copies the context into the threadpool), SQLAlchemy 2.1.1, psycopg2, pytest 9, PyYAML 6 (test only), Streamlit 1.64 (`AppTest`, Task 16 only), GitHub Actions (`curl`), Railway, Vercel (unchanged), Streamlit Community Cloud (Python 3.13), Google Cloud OAuth client "Liturgy".

**Spec:** `docs/superpowers/specs/2026-09-25-slice-ops-cleanup-design.md` ("the ops spec"). Foundations: `docs/superpowers/specs/2026-09-25-migration-foundations-design.md` ("F": §1.1, §1.5, §1.10, §2.5, §2.6 items 1–2, §3.3, §5.5, §6.1, §6.2 with its 2026-09-26 amendment, §7.2, §7.3). Inventory: `docs/superpowers/specs/2026-09-25-streamlit-migration-inventory.md` ("inv"). Already on `main` (57beda0): PR #4 (service rubric: `api/routes/rubric.py`, `service_rubric.py`, `hymn_ranking.py`, `hymnary_facts.py`, `text_year`/`hymnal_count`), ops-1 (#5), #6 (keep-awake and runbook → `liturgy-next`), the design-only PRs #7–#11, and ops-2 (#12: `db/upsert.py`, `ensure_user`, `api/identity_cache.py` wired into `api/deps.get_current_user`, the 3 + 3 pool with `connect_timeout=10`, the `backend-postgres` CI job, `keep-awake.yml` visiting only `liturgy-next`). The ops-1 and ops-2 plans are `docs/superpowers/plans/2026-09-25-ops-1-backups-cleanup-d5.md` and `docs/superpowers/plans/2026-09-25-ops-2-identity-db.md`.

## Global Constraints

- Run every command from the repo root with `.venv/bin/python` (Python 3.11). The system `python3` is 3.9 and has no deps. If `.venv` is missing: `/Users/beaubrown/.local/bin/python3.11 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt`.
- The agent's shell blocks a foreground `sleep`, and shell state (variables, `&` jobs) does not carry between commands. Start a server with the Bash tool's `run_in_background`, wait with a Monitor until-loop, and follow a workflow run with `gh run list` then `gh run watch <id>` (Tasks 10, 12, 14).
- Branch `claude/ops-3`, created from `origin/main` at 57beda0 ("Merge pull request #12 from bbrown62450/claude/ops-2") and checked out in this worktree. Its first commit is this plan. Never switch branches for Tasks 1–11. Stage files by name, never `git add -A` or `git add .`: the untracked `.claude/` directory must stay uncommitted.
- Backend test command: `.venv/bin/python -m pytest -q` (pytest.ini: `pythonpath = . backend`, `testpaths = backend/tests streamlit_tests`). Baseline on `claude/ops-3`: `489 passed` (2026-09-26). This plan adds 75 tests and deletes the 5 in `test_keepalive.py`, for `559 passed` (Task 16, only if needed, adds 1 more). If the baseline differs, stop and ask the owner.
- Frontend: untouched. CI's `frontend` job (`npm ci`, lint, typecheck, `npm test`, build) and the `backend-postgres` job (`backend/tests/pg_smoke.py` on a `postgres:17` service) must stay green.
- Every commit message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Commits follow TDD: test first, watch it fail, then code.
- Layering: nothing under `backend/` imports `streamlit`. `backend/db/health.py` imports neither FastAPI nor Starlette. `db/` never imports `api/`. `api/routes/health.py` holds no SQL and no `try` (the recorded exception to F §2.2 items 1 and 4: `/health` and `/health/ready` have no usecase and raise `ApiError`).
- No schema change, no Alembic, no data migration (slice 1). `init_db()` stays in the lifespan (slice 1 removes it).
- Middleware order in `create_app()` (the last added is the outermost): `add_middleware(UnhandledErrorMiddleware)`, then `RequestIdMiddleware`, then `CORSMiddleware`. The resulting stack, outside in: Starlette `ServerErrorMiddleware` → CORS → RequestId → UnhandledError → `ExceptionMiddleware` → router. The existing `@app.exception_handler(Exception)` stays as the last resort. The routers stay `health`, `me` and `rubric`, in that order.
- CORS (F §1.10), verbatim: `allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"]`, `allow_headers=["Authorization", "Content-Type", "X-Church-Id", "Idempotency-Key", "If-Match", "X-Request-Id"]`, `expose_headers=["Content-Disposition", "Retry-After", "X-Request-Id"]`, `max_age=600`, `allow_credentials` off.
- Request id: the inbound `X-Request-Id` is echoed if it matches `^[A-Za-z0-9-]{8,64}$`, else the server uses `uuid.uuid4().hex`. Every error body is `{"error": {"code", "message", "request_id"}}`, with `request_id` equal to the header (`fields` and `details` arrive in slice 1).
- Readiness: `GET /health/ready` is public; 200 `{"ok": true, "db": "ok"}`; 503 `db_unavailable` "The database is not reachable."; memoized 10 s after a success and 5 s after a failure; one probe at a time; `SET LOCAL statement_timeout = '5s'` on Postgres. `GET /health` stays the dependency-free liveness probe and Railway's deploy health check (slice 1 moves the deploy check).
- Exact copy (ops spec, "Exact server messages"):
  - `/health/ready` 503: `{"error": {"code": "db_unavailable", "message": "The database is not reachable.", "request_id": "…"}}`
  - any 500: `{"error": {"code": "internal_error", "message": "Something went wrong.", "request_id": "…"}}`
  - `APP_ENV must be 'development' or 'production' (got '{value}').` (raises)
  - `APP_ENV=production requires a PostgreSQL DATABASE_URL; refusing to start.` (raises)
  - `CORS_ORIGINS allows only localhost origins in production; browsers on the real site will be blocked.` (log ERROR)
  - `Database: dialect=postgresql driver=psycopg2 host=aws-0-<region>.pooler.supabase.com database=postgres` (log INFO)
  - `LOG_LEVEL='{value}' is not a valid level; using INFO.` (log WARNING)
  - `::error::Set the API_BASE_URL repository variable (Settings → Secrets and variables → Actions → Variables)` (`keepalive.yml`)
- Log lines never contain request bodies, tokens, invite codes, OAuth codes or state, email bodies, AI prompts or outputs, or a query string (F §2.5).
- **Production Streamlit (facts of 2026-09-26; they override the ops spec).** The one Streamlit app is `liturgy-next`, https://liturgy-next.streamlit.app, on Streamlit Community Cloud: repo `bbrown62450/church`, branch `main`, main file `app.py`, Python 3.13. Its Secrets carry `[auth] redirect_uri = https://liturgy-next.streamlit.app/oauth2callback` and `GOOGLE_OAUTH_REDIRECT_URI = https://liturgy-next.streamlit.app/`, both registered on the Google OAuth client "Liturgy". The owner and the tester use it. `liturgy` and `liturgy-stg` were **deleted on 2026-09-26** (both URLs return 404). Their four Google redirect URIs must be removed before the Freeze (Task 11): a deleted app's subdomain can probably be claimed by anyone, who would then receive the authorization responses Google sends for the "Liturgy" client (sign-in and the `gmail.send` flow). If the owner declines, it is an accepted risk recorded in the runbook, and AC 22 is not met. `keep-awake.yml` on `main` already visits only https://liturgy-next.streamlit.app/. Wherever the ops spec says "redeploy `liturgy`", "delete `liturgy-stg`" or "keep-awake pings only `https://liturgy.streamlit.app/`", read `liturgy-next` and "already done".
- **Streamlit Community Cloud rules.** One app per repo + branch + main file. An existing app's repo, branch or main file cannot be changed: changing the branch means deleting the app and redeploying it with the same subdomain (`liturgy-next`) and re-entering its Secrets, which the owner keeps in the password manager. A deleted app's subdomain may not be free again right away (ops spec, Risks item 4), and nothing proves when it is, so the Freeze builds and checks the new app on a temporary subdomain first and keeps it as the fallback address (Task 14). A running app hot-pulls new commits and can keep stale imported modules (an `ImportError` happened on the old `liturgy` app), so after any code change reaches a running app, reboot it (Manage app → Reboot).
- **Owner decisions.** No new features in Streamlit, only data-safety fixes. The database password was not rotated (accepted risk, recorded in the runbook); ops-3 does not touch it. Backups are live (environment `backup`, secret `BACKUP_DATABASE_URL`, first run green on 2026-09-26). Railway has `DB_POOL_SIZE=3` and `DB_MAX_OVERFLOW=3`; `APP_ENV` is **not** set on Railway yet (Task 11 sets it before merge). The Supabase pooler Pool Size is 15: 2 × (3 + 3) + 2 = 14 ≤ 15, for the API and `liturgy-next`. ops-3 changes no pool value.
- **Step 0 is done.** ops-1 wrote the results into `docs/ops-runbook.md`; never ask the owner to redo them. The Data API was already off (REST and GraphQL with the anon key return 503 `PGRST002`, no rows), so there was no incident. The server is 17.6 (`- Postgres server major: 17`). Railway's request limit (5 minutes idle, 15 minutes while data flows) is recorded with its source.
- **Open owner markers from ops-1 and ops-2.** On 2026-09-26 the runbook has 11 `[owner` lines that are not ops-3's: the `age` key's password-manager entry, the restore drill, three D5 rows (manual check, "fixed" message, recovery result) and the six ops-2 gate rows. ops-3's code work does not wait for them. The six ops-2 gate rows must be filled before ops-3 merges (the ops spec's gate after ops-2; Task 11), and the D5 manual check must have passed before `streamlit-frozen` is cut (Task 13). ops-3's own markers are checked with this section-scoped command, which reads only the sections ops-3 adds (call it "the ops-3 marker check"):

  ```bash
  awk '/^## Environments and variables$|^## Keep-alive$|^### What the frozen app inherits from ops-3$/{on=1} /^## Supabase lockdown record$|^## Streamlit freeze$|^## Platform limits$/{on=0} on && /\[owner/{print FNR": "$0}' docs/ops-runbook.md
  ```
- Production URLs: API https://church-production-74ca.up.railway.app; frontend https://worship-service-builder.vercel.app; Streamlit https://liturgy-next.streamlit.app; Supabase project `worship-staging`, ref `tbecmwtitsoxzkrvxxxu`; repo `bbrown62450/church`.
- The agent never sees or types a secret (database URLs, keys, tokens, Streamlit Secrets, the contents of `backend/.env`). Opening a PR, merging, pushing a branch other than the PR branch, setting repository variables or protection, triggering workflows and messaging the tester are outward-facing: get the owner's explicit yes first.
- These tests stay unchanged and green: `test_auth.py`, `test_api_me.py`, `test_api_rubric.py`, `test_api_security.py`, `test_docs.py`, `test_ci_workflow.py`, `test_no_streamlit_in_core.py`, `test_engine.py`, the ops-2 identity tests (`test_identity.py`, `test_identity_cache.py`, `test_upsert.py`, `test_users_repo.py`), `backend/tests/pg_smoke.py`, and all of `streamlit_tests/`. `test_api_app.py` changes exactly one test (Tasks 1–2). `test_keepalive.py` is deleted (Task 7).
- **Not in ops-3** (other PRs and slices; do not touch): `backup.yml`, `.github/backup/`, `backend/.env.example` (ops-1 already documents `APP_ENV`, `LOG_LEVEL`, `DB_POOL_SIZE`, `DB_MAX_OVERFLOW` and `ESV_API_KEY`); `keep-awake.yml` (already visits only `liturgy-next`, PR #6/#12); `db/upsert.py`, `ensure_user`, `api/deps.py`, the identity cache, the pool code and `ci.yml` (ops-2); the rubric code (PR #4); the prayer library and the service reviewer (PRs #7–#11, new app only, never Streamlit); Alembic, `railway.toml`, the Railway health check move, the schema-behind gate, `domain_errors.py`, `fields`/`details`, `test_route_guards.py`, the frontend `ApiError.requestId` and "(Ref: …)" text, `frontend/src/lib/api/errors.ts` itself (slice 1); `backend/cache.py` and `backend/tests/test_cache.py` (slice 2, never create them); `liturgy_prompts.LEGACY_SYSTEM_PROMPT` and `legacy_default_prompts()` (slice 4, and only under the Freeze contingency); `OPENAI_MODEL` (slice 3); the switchover banner (5b); the root `.env.example`, deleting `keep-awake.yml`, the README rewrite (slice 7).

## Spec clarifications (recorded, not deviations of intent)

1. **`liturgy-next` in code.** `keep-awake.yml` already lists exactly `https://liturgy-next.streamlit.app/` on `main`, so ops-3 does not edit it. The spec's keep-awake test ("contains `https://liturgy.streamlit.app/` and not `liturgy-stg`") is kept as a guard with the facts swapped in: the one URL is `https://liturgy-next.streamlit.app/`, and neither `https://liturgy.streamlit.app` nor `https://liturgy-stg.streamlit.app` appears. It passes when written (Task 8). The spec's Freeze step 5 (delete the second app) was done on 2026-09-26; only removing the deleted apps' redirect URIs is left, and it is mandatory and comes first (clarification 21). Slice 7's "verify ops" row names `liturgy`; slice 7 adapts it, as that row itself allows.
2. **`test_api_app.py::test_unhandled_exception_is_a_generic_500` changes in two steps.** Task 1 adds `request_id` to every error body. The last-resort 500 then carries a fallback id but no header yet, so Task 1 asserts a 32-hex `request_id`. Task 2 puts `UnhandledErrorMiddleware` inside `RequestIdMiddleware` and tightens the test to the spec's final form: `request_id` equals the `X-Request-Id` header, and the body has exactly `code`, `message` and `request_id`.
3. **Request-id boundaries.** The spec lists the invalid inbound id "`short` (7 characters)", but `short` has 5. The test uses the 7-character `abc-123`, plus `bad id!` and a 65-character id. The valid cases include both edges: 8 characters and 64 characters.
4. **405 in the error-body test.** The spec's API section names 404s, 405s and 422s. The body test covers 404, 405, 401 and 422.
5. **`configure_logging(level) -> int`** returns the level it used, so "uses INFO" is testable. The handler it installs formats with `defaults={"request_id": "-"}`, so a record built without the factory (`logging.makeLogRecord`) never breaks a log line. `basicConfig` receives that handler rather than a bare `format=`.
6. **Blank settings mean the default.** A blank `APP_ENV` means `development`, and a blank `LOG_LEVEL` means `INFO`, as ops-2's `_int_env` treats a blank pool size. `check_app_env` receives the normalized value, so the error shows it (`got 'staging'`).
7. **Where the FROZEN header goes.** `app.py` line 1 is the shebang `#!/usr/bin/env python3`. The FROZEN comment becomes line 2, the first comment after the shebang, and the test reads it there.
8. **Readiness-reset fixture.** The spec's autouse fixture resets the memo only when `db.health` is already imported, the same pattern as ops-2's `_fresh_identity_cache`. A stale result can only exist then.
9. **The `errors.ts` check** (`test_foundation_setup.py`) accepts `"db_unavailable"` or `'db_unavailable'`, and a parametrized self-test shows it bites. It passes as soon as it is written, because the file arrives in slice 1. `test_foundation_setup.py` gains `import pytest` for the self-test.
10. **What moves out of `test_keepalive.py`.** Its workflow assertions move to `test_ops_workflows.py`. `test_backup_workflow_present` is ported as `test_backup_workflow_runs_pg_dump_on_a_schedule`. The three `ping` tests go with `keepalive.py`, and `test_health_ready.py`'s 200 and 503 tests cover the same ground through the API.
11. **Docs get tests.** The README keep-alive paragraph, the runbook's seven sections, its Keep-alive and Environments sections, the freeze subsections, the Contingency wording and the manual-verification "Ops slice" checklist are asserted in `test_ops_workflows.py`, so each docs change has a failing test first. `test_docs.py` stays unchanged.
12. **Checklist boxes stay unchecked.** `docs/manual-verification.md` is a reusable checklist, as slice 0 left its own section. Results, with dates, go into `docs/ops-runbook.md`. So AC 23's "every box is checked" means performed and recorded.
13. **Two freeze-records PRs.** The spec's "after the next merge to `main`, the app's logs show no new build" needs a merge after the redeploy. Records PR A (Task 15) is that merge. Records PR B records the check that PR A's merge triggered. A docs-only commit does not show as a fresh build: a tracked branch's new commit shows in the logs as a code pull (`Pulling code changes from Github`, then `Updated app!`), so the check looks for those lines and re-reads the app's branch setting.
14. **Stale mentions of the keep-alive script.** The ops-2 docstring in `db/engine.py` (lines 10–11, closed by line 12's `"""`) and ops-2's pool bullet in the runbook's "Platform limits" mention `keepalive.py`, which ops-3 deletes. Both are reworded (Task 7), and a test keeps the runbook from mentioning it again. The "Values set" bullet next to the pool bullet still says the pool keys live in `liturgy-stg`'s Secrets "(not `liturgy`, which is being deleted)"; Task 7 rewords it to what is true at the ops-3 merge, and Task 15 fills in the Freeze facts.
15. **Contingency code.** The spec's contingency (Freeze step 8) asks for an `AppTest` smoke test. Task 16 gives it in full, checked against this branch on 2026-09-26 (it passed in 0.7 s, and the suite was then `560 passed`). It is used only if Task 14 falls back to `main`. It renders only the signed-out page: the functions F §6.1 item 6 keeps compatible run after sign-in, so under the contingency the signed-in pages rely on the manual smoke check after every merge to `main` (runbook → Contingency), an accepted limit recorded there.
16. **The old `DATABASE_URL` Actions secret.** After ops-3 only `db-backup` holds database credentials (ops spec, Backups → Decisions). Inventory H4 says the keepalive secret was never added. If a `DATABASE_URL` repository secret does exist, the owner deletes it in Task 11, Step 3, because nothing reads it once ops-3 is live.
17. **The Freeze deploys first, then swaps, for one app.** Streamlit Cloud cannot switch `liturgy-next` to another branch, so the ops spec's "otherwise" path is the only path, but deleting production first and hoping the subdomain comes back (Risks item 4) would leave the tester with no URL if it does not; a rollback from `main` needs the same subdomain and would fail the same way. So (Task 14): a few hours before the window, while `liturgy-next` keeps serving, the owner deploys `streamlit-frozen` / `app.py` (Python 3.13) as a temporary app on `liturgy-frozen` (a different branch, so the one-app rule allows it), with the `liturgy-next` Secrets except that the two redirect values point at `liturgy-frozen`, registers that subdomain's two redirect URIs, and runs the full smoke check there. That build's installed versions are compared with the pre-freeze list, and a failing pre-flight stops the Freeze before production is touched (a dependency pin goes into `streamlit-frozen` as a data-safety fix). In the window: delete `liturgy-next`, move the checked app to the subdomain `liturgy-next` (the spec's step 4.5 sets the subdomain after creation) and paste the `liturgy-next` Secrets unchanged. If Settings cannot change the subdomain, a reclaim test during the pre-flight decides whether delete-and-recreate is safe. If `liturgy-next` stays refused, the checked app keeps serving on `liturgy-frozen`, the tester gets that URL and `keep-awake` follows it (Fallback). Three apps share the pooler only during the pre-flight (worst case 3 × (3 + 3) + 2 = 20 > 15, never reached by two people), so the overlap is kept to a few hours. The tester is told about a window of about 5 minutes.
18. **Contingency wording (F §6.1 item 6 and the §6.2 amendment of 2026-09-26, PR #11).** If Streamlit keeps running from `main`, it still gets no new features: it keeps the old season wording (slice 4's `generate_liturgy` wrapper keeps the old sentences through `liturgy_prompts.LEGACY_SYSTEM_PROMPT`, and Streamlit's Settings page shows and compares with `liturgy_prompts.legacy_default_prompts()`), and it never reads `prayer_library`. The runbook's Contingency subsection says so (Task 9) and a test pins it. ops-3 writes no prompt code: those names arrive in slice 4, and only under the contingency.
19. **Reboot after merges that reach `liturgy-next`.** Until the Freeze, `liturgy-next` deploys from `main`, so the ops-3 merge reaches it (a comment line in `app.py`, a docstring in `db/engine.py`, a deleted module it never imported). The owner reboots it right after the merge and runs the short smoke check at once, because a reboot reinstalls the unpinned requirements (Task 11, Step 6); the full pre-freeze smoke check runs on that rebooted build (Task 13). No other PR merges to `main` between the ops-3 merge and the end of Task 14, so `liturgy-next` runs exactly the commit `streamlit-frozen` is cut from.
20. **`API_BASE_URL` is set before the merge.** The spec says "After merging: set the Actions variable `API_BASE_URL`". The rewritten `keepalive.yml` fails at its `::error::` line on every scheduled run (daily 09:17 UTC) until the variable exists, and the old workflow never reads it, so the owner sets it before merging (Task 11, Step 3); the manual keepalive run stays after the merge (Task 12).
21. **The deleted apps' redirect URIs are removed first, and it is mandatory.** The spec's Freeze step 5 removes `liturgy-stg`'s URIs with that app. Both deleted subdomains can probably be claimed by anyone, who would then receive Google's authorization responses for the "Liturgy" client under a consent screen the tester trusts, so the owner removes all four in Task 11, before the Freeze and independent of it, and checks sign-in on `liturgy-next`. If the owner declines, the Freeze record says so as an accepted risk and AC 22 is not claimed. The temporary `liturgy-frozen` URIs of the pre-flight follow the same rule: registered only after the app holds the subdomain, removed as soon as it no longer does.
22. **Railway's deploy health check is confirmed, not assumed.** The spec's "the previous release keeps serving" when the `APP_ENV` guard refuses to start holds only if the API service has Healthcheck Path `/health`; the repo has no `railway.toml` yet (slice 1). The owner checks the setting in Task 11 and records it, and Task 12 names the manual rollback (Deployments → the previous deployment → Redeploy). Railway also stages variable edits until they are deployed, so the owner confirms `APP_ENV` is in effect on the Active deployment (Tasks 11 and 12): no log line or public response shows it.

## File Map

```
backend/api/middleware.py            NEW: REQUEST_ID_HEADER, current_request_id(), RequestIdMiddleware, UnhandledErrorMiddleware
backend/api/logging_config.py        NEW: LOG_FORMAT, configure_logging(level) -> int (record factory adds request_id)
backend/api/startup.py               NEW: describe_database(url), check_app_env(value), enforce_production_guards(settings, engine)
backend/db/health.py                 NEW: READY_OK_TTL, READY_FAIL_TTL, database_ready(*, clock), _probe(), reset_readiness_for_tests()
backend/api/errors.py                request_id in _body; error_body alias; db_unavailable()
backend/api/main.py                  configure_logging; lifespan guards and Database log; redirect_slashes=False; middleware order; CORS lists (routers health, me, rubric unchanged)
backend/api/settings.py              Settings.app_env, Settings.log_level, Settings.is_production
backend/api/routes/health.py         ReadyOut; GET /health/ready
backend/db/engine.py                 module docstring lines 10-11 (line 12 closes it): the readiness probe, not the keep-alive script
backend/keepalive.py                 DELETED
backend/tests/test_keepalive.py      DELETED (5 tests)
backend/tests/test_middleware.py     NEW (33 tests)
backend/tests/test_startup.py        NEW (14 tests)
backend/tests/test_health_ready.py   NEW (10 tests)
backend/tests/test_api_app.py        test_unhandled_exception_is_a_generic_500 asserts request_id == header (still 9 tests)
backend/tests/test_foundation_setup.py  + errors.ts "db_unavailable" check and its self-test (7 -> 11 tests)
backend/tests/test_ops_workflows.py  + keepalive, keep-awake guard, FROZEN header, README, runbook, contingency, manual checks (66 -> 80 tests)
backend/tests/conftest.py            + autouse readiness-memo reset
.github/workflows/keepalive.yml      REWRITTEN: curl ${API_BASE_URL}/health/ready, permissions {}, no secret
app.py                               line 2: FROZEN header
README.md                            "Keep-alive (required)" paragraph (lines 194-199)
docs/ops-runbook.md                  + Environments and variables, Keep-alive, freeze subsections; intro bullet; Platform limits pool and "Values set" bullets
docs/manual-verification.md          + "## Ops slice"
```

Unchanged on purpose: `.github/workflows/keep-awake.yml` (already `liturgy-next` only), `backend/.env.example`, `.github/workflows/ci.yml`, `backend/api/deps.py`, `backend/api/identity_cache.py`, every Streamlit file except `app.py`'s comment line.

---

### Task 1: Request ids on every response and in every error body (S9, S13)

**Files:**
- Create: `backend/api/middleware.py`
- Modify: `backend/api/errors.py:1-9` (docstring and imports), `backend/api/errors.py:40-41` (`_body`)
- Modify: `backend/api/main.py:10` (add an import after it), `backend/api/main.py:36-37` (add the middleware)
- Test: `backend/tests/test_middleware.py` (new), `backend/tests/test_api_app.py:1-3` (imports) and `:50-53` (the end of the 500 test)

**Interfaces:**
- Consumes: `api.main.create_app() -> FastAPI`; `api.deps.get_verifier` (overridden so `/me` fails on the missing token first, before the identity cache or the database); `api.errors._body(code, message) -> dict`.
- Produces:
  - `api.middleware.REQUEST_ID_HEADER = "X-Request-Id"`;
  - `api.middleware.current_request_id() -> Optional[str]` (None outside a request);
  - `api.middleware.RequestIdMiddleware(app)`, pure ASGI;
  - `api.errors._body(code, message)` returns `{"error": {"code", "message", "request_id"}}`;
  - `api.errors.error_body`, a public alias of `_body` (Task 2 uses it);
  - in `test_middleware.py`: `HEX32` (compiled `[0-9a-f]{32}`) and `_app_with_test_routes()`.

- [ ] **Step 1: Check the branch and the baseline**

```bash
git status -sb | head -1
git log --oneline -1 origin/main
git log --oneline origin/main..HEAD
test -f docs/superpowers/specs/2026-09-25-slice-ops-cleanup-design.md \
  && test -f backend/tests/test_ops_workflows.py \
  && grep -q '^DEFAULT_POOL_SIZE = 3$' backend/db/engine.py \
  && grep -q '^def ensure_user' backend/repos/users.py \
  && test -f backend/api/identity_cache.py \
  && grep -q '^from api.routes import health, me, rubric$' backend/api/main.py \
  && echo "ops-1, ops-2 and the rubric are on main"
grep -c '^### What the frozen app inherits from ops-2' docs/ops-runbook.md
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
.venv/bin/python -m pytest -q | tail -1
```

Expected: `## claude/ops-3...origin/main [ahead 1]`; `57beda0 Merge pull request #12 from bbrown62450/claude/ops-2`; exactly one line, this plan's commit `Plan: refresh ops-3 for current main (ops-2, rubric, liturgy-next freeze)`; `ops-1, ops-2 and the rubric are on main`; `1`; `11` (the ops-1 and ops-2 owner markers listed in Global Constraints; a smaller number only means the owner filled some); `489 passed`. If the branch line shows `behind`, or any other check differs, stop and ask the owner.

- [ ] **Step 2: Write the failing tests**

Create `backend/tests/test_middleware.py`:

```python
"""Request ids, CORS-safe 500s, middleware order, CORS lists and logging (ops slice, F §1.10, §2.5)."""
import re

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

from api.deps import get_verifier
from api.errors import error_body
from api.main import create_app

HEX32 = re.compile(r"[0-9a-f]{32}")


def _app_with_test_routes():
    """create_app() plus a route that needs an int, for a 422."""
    app = create_app()
    router = APIRouter()

    @router.get("/needs-int")
    def needs_int(n: int):
        return {"n": n}

    app.include_router(router)
    app.dependency_overrides[get_verifier] = lambda: None   # /me fails on the missing token first
    return app


# --- RequestIdMiddleware ------------------------------------------------------

def test_every_response_gets_a_generated_request_id():
    r = TestClient(create_app()).get("/health")
    assert r.status_code == 200
    assert HEX32.fullmatch(r.headers["x-request-id"])


@pytest.mark.parametrize("inbound", ["abcd-1234-efgh", "abcd1234", "A" * 64],
                         ids=["dashed", "8-chars", "64-chars"])
def test_a_valid_inbound_request_id_is_echoed(inbound):
    r = TestClient(create_app()).get("/health", headers={"X-Request-Id": inbound})
    assert r.headers["x-request-id"] == inbound


@pytest.mark.parametrize("inbound", ["bad id!", "abc-123", "a" * 65],
                         ids=["bad-characters", "7-chars", "65-chars"])
def test_an_invalid_inbound_request_id_is_replaced(inbound):
    r = TestClient(create_app()).get("/health", headers={"X-Request-Id": inbound})
    assert HEX32.fullmatch(r.headers["x-request-id"])


@pytest.mark.parametrize("method, path, status, code", [
    ("GET", "/nope", 404, "not_found"),
    ("POST", "/health", 405, "method_not_allowed"),
    ("GET", "/me", 401, "unauthenticated"),
    ("GET", "/needs-int?n=abc", 422, "invalid_request"),
], ids=["404", "405", "401", "422"])
def test_every_error_body_carries_the_request_id_from_the_header(method, path, status, code):
    r = TestClient(_app_with_test_routes()).request(method, path)
    assert r.status_code == status
    error = r.json()["error"]
    assert error["code"] == code
    assert error["request_id"] == r.headers["x-request-id"]


def test_an_error_body_built_outside_a_request_still_has_a_request_id():
    # Only the last-resort handler (outside RequestIdMiddleware) builds one here.
    body = error_body("internal_error", "Something went wrong.")
    assert HEX32.fullmatch(body["error"]["request_id"])
```

In `backend/tests/test_api_app.py`, replace lines 1-3:

```python
import subprocess
import sys
from pathlib import Path
```

with:

```python
import re
import subprocess
import sys
from pathlib import Path
```

and replace the body of `test_unhandled_exception_is_a_generic_500` from its `r = …` line to the end (lines 50-53):

```python
    r = TestClient(app, raise_server_exceptions=False).get("/boom")
    assert r.status_code == 500
    assert r.json() == {"error": {"code": "internal_error", "message": "Something went wrong."}}
    assert "secret detail" not in r.text
```

with:

```python
    r = TestClient(app, raise_server_exceptions=False).get("/boom")
    assert r.status_code == 500
    error = r.json()["error"]
    assert (error["code"], error["message"]) == ("internal_error", "Something went wrong.")
    assert re.fullmatch(r"[0-9a-f]{32}", error["request_id"])
    assert "secret detail" not in r.text
```

- [ ] **Step 3: Run the tests to verify they fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_middleware.py 2>&1 | tail -3
.venv/bin/python -m pytest -q backend/tests/test_api_app.py 2>&1 | tail -3
```

Expected: first, a collection error `ImportError: cannot import name 'error_body' from 'api.errors'` and `1 error`. Then `1 failed, 8 passed`: `test_unhandled_exception_is_a_generic_500` fails with `KeyError: 'request_id'`.

- [ ] **Step 4: Create `backend/api/middleware.py`**

```python
"""Request ids and CORS-safe 500s: pure ASGI middleware (F §2.5; ops slice).

RequestIdMiddleware gives every HTTP request an id: the inbound X-Request-Id
when it matches ^[A-Za-z0-9-]{8,64}$, else a new uuid4 hex. The id lives in a
contextvar while the request runs (anyio copies the context into the
threadpool, so sync routes and dependencies see it too), and every response
started inside the middleware carries it as X-Request-Id. Error bodies and log
lines read it through current_request_id().

Pure ASGI, not BaseHTTPMiddleware: nothing here buffers or re-wraps a response.
"""
import re
import uuid
from contextvars import ContextVar
from typing import Optional

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_ID_HEADER = "X-Request-Id"

_VALID_REQUEST_ID = re.compile(r"[A-Za-z0-9-]{8,64}")
_request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def current_request_id() -> Optional[str]:
    """The id of the request being handled; None outside RequestIdMiddleware."""
    return _request_id.get()


def _inbound_request_id(scope: Scope) -> Optional[str]:
    """The caller's X-Request-Id if it is well formed, else None."""
    for name, value in scope.get("headers", []):
        if name == b"x-request-id":
            candidate = value.decode("latin-1")
            return candidate if _VALID_REQUEST_ID.fullmatch(candidate) else None
    return None


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = _inbound_request_id(scope) or uuid.uuid4().hex
        token = _request_id.set(request_id)

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                message.setdefault("headers", [])
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            _request_id.reset(token)
```

`fullmatch` rather than `^…$`, because `$` also matches before a trailing newline.

- [ ] **Step 5: Put `request_id` in every error body (`backend/api/errors.py`)**

Replace lines 1-9:

```python
"""One error shape for every API failure: {"error": {"code", "message"}}."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)
```

with:

```python
"""One error shape for every API failure: {"error": {"code", "message", "request_id"}}."""
import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.middleware import current_request_id

logger = logging.getLogger(__name__)
```

Replace `_body` (originally lines 40-41):

```python
def _body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}
```

with:

```python
def _body(code: str, message: str) -> dict:
    """The uniform error body (F §1.5); slice 1 adds `fields` and `details`.

    `request_id` is the X-Request-Id of the request. The uuid4 fallback only
    fires outside RequestIdMiddleware, in the last-resort handler below.
    """
    return {"error": {
        "code": code,
        "message": message,
        "request_id": current_request_id() or uuid.uuid4().hex,
    }}


# Public name for UnhandledErrorMiddleware (api/middleware.py).
error_body = _body
```

`_body` keeps its name, because slice 1 extends it with `fields` and `details`. `ApiError`, `unauthenticated`, `forbidden`, `auth_unavailable` and the four handlers in `install_error_handlers` are unchanged. The rubric route's `ApiError(422, "invalid_rubric", …)` gets the `request_id` like every other error (`test_api_rubric.py` reads only `code` and `message`).

- [ ] **Step 6: Add the middleware in `backend/api/main.py`**

After line 10 (`from api.errors import install_error_handlers`), add:

```python
from api.middleware import RequestIdMiddleware
```

Replace the two lines that were lines 36-37 before that import was added:

```python
    app = FastAPI(title="Worship Service Builder API", lifespan=lifespan)
    app.add_middleware(
```

with:

```python
    app = FastAPI(title="Worship Service Builder API", lifespan=lifespan)
    app.add_middleware(RequestIdMiddleware)   # added before CORS, so CORS stays the outermost
    app.add_middleware(
```

- [ ] **Step 7: Run the tests and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_middleware.py backend/tests/test_api_app.py
.venv/bin/python -m pytest -q | tail -1
```

Expected: `21 passed` (12 + 9), then `501 passed`.

- [ ] **Step 8: Commit**

```bash
git add backend/api/middleware.py backend/api/errors.py backend/api/main.py \
        backend/tests/test_middleware.py backend/tests/test_api_app.py
git commit -m "API: X-Request-Id on every response and request_id in every error body (F §2.5, §1.5)

RequestIdMiddleware (pure ASGI) echoes a well-formed inbound X-Request-Id or
generates a uuid4 hex, keeps it in a contextvar for the request, and sets the
response header. Error bodies carry the same id.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: CORS-safe 500s: `UnhandledErrorMiddleware` and the middleware order (S9, F §7.3)

**Files:**
- Modify: `backend/api/middleware.py` (docstring, imports, append the class)
- Modify: `backend/api/main.py` (the import line and the `RequestIdMiddleware` line from Task 1)
- Test: `backend/tests/test_middleware.py` (imports; append), `backend/tests/test_api_app.py` (the 500 test)

**Interfaces:**
- Consumes: `api.errors.error_body(code, message) -> dict` (Task 1), imported lazily; `RequestIdMiddleware` (Task 1).
- Produces:
  - `api.middleware.UnhandledErrorMiddleware(app)`, pure ASGI. It logs through logger `api.middleware` with the message `Unhandled error on {method} {path}`, never the query string;
  - `create_app()` adds UnhandledError, then RequestId, then CORS, so `app.user_middleware` lists them outermost first as CORS, RequestId, UnhandledError;
  - in `test_middleware.py`: `ALLOWED_ORIGIN = "https://church.example.app"`, the fixture `cors_origin` (sets `CORS_ORIGINS`, clears the settings cache) and `_app_that_raises()` (route `/boom` raises `RuntimeError("secret detail")`). Task 3 reuses `cors_origin`.

- [ ] **Step 1: Write the failing tests**

In `backend/tests/test_middleware.py`, replace the import block:

```python
import re

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

from api.deps import get_verifier
from api.errors import error_body
from api.main import create_app
```

with:

```python
import asyncio
import logging
import re

import pytest
from fastapi import APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from api import settings as settings_mod
from api.deps import get_verifier
from api.errors import error_body
from api.main import create_app
from api.middleware import RequestIdMiddleware, UnhandledErrorMiddleware
```

Append to `backend/tests/test_middleware.py`:

```python


# --- UnhandledErrorMiddleware: CORS-safe 500s (F §2.5, §7.3) --------------------

ALLOWED_ORIGIN = "https://church.example.app"


@pytest.fixture
def cors_origin(monkeypatch):
    """CORS_ORIGINS is exactly ALLOWED_ORIGIN for apps created in this test."""
    monkeypatch.setenv("CORS_ORIGINS", ALLOWED_ORIGIN)
    settings_mod.get_settings.cache_clear()
    yield ALLOWED_ORIGIN
    settings_mod.get_settings.cache_clear()


def _app_that_raises():
    app = create_app()
    router = APIRouter()

    @router.get("/boom")
    def boom():
        raise RuntimeError("secret detail")

    app.include_router(router)
    return app


def test_a_500_carries_cors_headers_and_the_request_id(cors_origin):
    client = TestClient(_app_that_raises(), raise_server_exceptions=False)
    r = client.get("/boom", headers={"Origin": cors_origin})
    assert r.status_code == 500
    assert r.json() == {"error": {
        "code": "internal_error",
        "message": "Something went wrong.",
        "request_id": r.headers["x-request-id"],
    }}
    assert r.headers["access-control-allow-origin"] == cors_origin
    assert "secret detail" not in r.text


def test_a_500_for_another_origin_has_no_cors_header(cors_origin):
    client = TestClient(_app_that_raises(), raise_server_exceptions=False)
    r = client.get("/boom", headers={"Origin": "https://evil.example"})
    assert r.status_code == 500
    assert "access-control-allow-origin" not in r.headers
    assert r.json()["error"]["request_id"] == r.headers["x-request-id"]


def test_an_unhandled_error_is_logged_with_the_path_but_not_the_query(caplog):
    client = TestClient(_app_that_raises(), raise_server_exceptions=False)
    with caplog.at_level(logging.ERROR):
        r = client.get("/boom?code=do-not-log-me")
    assert r.status_code == 500
    records = [rec for rec in caplog.records if rec.name == "api.middleware"]
    assert [rec.getMessage() for rec in records] == ["Unhandled error on GET /boom"]
    assert records[0].exc_info is not None                  # the stack trace is logged
    assert "do-not-log-me" not in caplog.text


def test_an_error_after_the_response_started_is_reraised_without_a_second_start():
    sent = []

    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        raise RuntimeError("mid-stream")

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    scope = {"type": "http", "method": "GET", "path": "/stream", "headers": []}
    with pytest.raises(RuntimeError, match="mid-stream"):
        asyncio.run(UnhandledErrorMiddleware(app)(scope, receive, send))
    assert [m["type"] for m in sent] == ["http.response.start"]


def test_middleware_order_is_cors_then_request_id_then_unhandled_error():
    # Starlette makes the last middleware added the outermost; user_middleware
    # lists them outermost first (F §2.5; slice 3 appends GZip innermost).
    app = create_app()
    assert [m.cls for m in app.user_middleware] == [
        CORSMiddleware, RequestIdMiddleware, UnhandledErrorMiddleware,
    ]
```

In `backend/tests/test_api_app.py`, in `test_unhandled_exception_is_a_generic_500`, replace:

```python
    error = r.json()["error"]
    assert (error["code"], error["message"]) == ("internal_error", "Something went wrong.")
    assert re.fullmatch(r"[0-9a-f]{32}", error["request_id"])
    assert "secret detail" not in r.text
```

with:

```python
    error = r.json()["error"]
    assert set(error) == {"code", "message", "request_id"}
    assert (error["code"], error["message"]) == ("internal_error", "Something went wrong.")
    assert re.fullmatch(r"[0-9a-f]{32}", error["request_id"])
    assert error["request_id"] == r.headers["x-request-id"]
    assert "secret detail" not in r.text
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_middleware.py 2>&1 | tail -3
.venv/bin/python -m pytest -q backend/tests/test_api_app.py 2>&1 | tail -3
```

Expected: a collection error `ImportError: cannot import name 'UnhandledErrorMiddleware' from 'api.middleware'` and `1 error`. Then `1 failed, 8 passed`: `test_unhandled_exception_is_a_generic_500` fails with `KeyError: 'x-request-id'`. The last-resort handler answers from outside `RequestIdMiddleware`, so its 500 has no header: that is the slice-0 bug (F §7.3).

- [ ] **Step 3: Add `UnhandledErrorMiddleware` to `backend/api/middleware.py`**

Replace the end of the module docstring and the imports:

```python
Pure ASGI, not BaseHTTPMiddleware: nothing here buffers or re-wraps a response.
"""
import re
import uuid
from contextvars import ContextVar
from typing import Optional

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_ID_HEADER = "X-Request-Id"
```

with:

```python
UnhandledErrorMiddleware turns an unexpected exception into the uniform 500
body from inside CORSMiddleware and RequestIdMiddleware, so the browser gets a
readable 500 with CORS headers and X-Request-Id instead of a network error.

Pure ASGI, not BaseHTTPMiddleware: nothing here buffers or re-wraps a response.
"""
import logging
import re
import uuid
from contextvars import ContextVar
from typing import Optional

from starlette.datastructures import MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-Id"
```

Append to the end of `backend/api/middleware.py`:

```python


class UnhandledErrorMiddleware:
    """Log an unexpected exception and answer 500 `internal_error`.

    If the response has already started, a second one must never start: the
    error is logged and re-raised. Otherwise it is logged, the 500 is sent and
    nothing is re-raised. The exception text never reaches the client.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = False

        async def send_wrapper(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            # The path only, never the query string: it can carry codes or tokens.
            logger.exception("Unhandled error on %s %s", scope["method"], scope["path"])
            if started:
                raise
            from api.errors import error_body   # deferred: api.errors imports this module

            response = JSONResponse(error_body("internal_error", "Something went wrong."), status_code=500)
            await response(scope, receive, send)
```

The 500 is sent through this middleware's own `send`, the one `RequestIdMiddleware` wrapped, so it gets `X-Request-Id` and, from the outer `CORSMiddleware`, `access-control-allow-origin`. The request id in the log line comes from the record factory (Task 4).

- [ ] **Step 4: Put it inside `RequestIdMiddleware` in `backend/api/main.py`**

Replace the import added in Task 1:

```python
from api.middleware import RequestIdMiddleware
```

with:

```python
from api.middleware import RequestIdMiddleware, UnhandledErrorMiddleware
```

Replace the line added in Task 1:

```python
    app.add_middleware(RequestIdMiddleware)   # added before CORS, so CORS stays the outermost
```

with:

```python
    # The last middleware added is the outermost: CORS → RequestId → UnhandledError
    # (F §2.5), so CORS decorates the 500s that UnhandledError produces.
    app.add_middleware(UnhandledErrorMiddleware)
    app.add_middleware(RequestIdMiddleware)
```

- [ ] **Step 5: Run the tests and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_middleware.py backend/tests/test_api_app.py
.venv/bin/python -m pytest -q backend/tests/test_identity_cache.py
.venv/bin/python -m pytest -q backend/tests/test_api_me.py backend/tests/test_api_rubric.py
.venv/bin/python -m pytest -q | tail -1
```

Expected: `26 passed` (17 + 9); `6 passed` (ops-2's `test_a_failed_ensure_user_is_never_cached` still gets its 500 `internal_error`, now from `UnhandledErrorMiddleware`, and still caches nothing); `25 passed` (`/me`, `/church` and `/rubric` unchanged); `506 passed`.

- [ ] **Step 6: Commit**

```bash
git add backend/api/middleware.py backend/api/main.py backend/tests/test_middleware.py backend/tests/test_api_app.py
git commit -m "API: unexpected 500s reach the browser with CORS headers and a request id (F §2.5, §7.3)

UnhandledErrorMiddleware (pure ASGI) sits inside CORS and RequestId. It logs
the method and path (never the query), answers the uniform 500 body if the
response has not started, and re-raises if it has.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Final CORS header lists and no trailing-slash redirect (S9, S11)

**Files:**
- Modify: `backend/api/main.py` (the `FastAPI(...)` line and the `CORSMiddleware` block in `create_app`)
- Test: `backend/tests/test_middleware.py` (append)

**Interfaces:**
- Consumes: the `cors_origin` fixture (Task 2).
- Produces: `create_app()` builds `FastAPI(..., redirect_slashes=False)` with the F §1.10 CORS lists. Test helpers `ALLOWED_REQUEST_HEADERS` and `_header_list(value) -> set[str]`.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_middleware.py`:

```python


# --- CORS header lists (F §1.10) and no trailing-slash redirect (F §1.1) --------

ALLOWED_REQUEST_HEADERS = ("authorization", "content-type", "x-church-id",
                           "idempotency-key", "if-match", "x-request-id")


def _header_list(value):
    return {item.strip().lower() for item in value.split(",")}


def test_preflight_allows_the_six_request_headers_for_ten_minutes(cors_origin):
    r = TestClient(create_app()).options("/me", headers={
        "Origin": cors_origin,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": ", ".join(ALLOWED_REQUEST_HEADERS),
    })
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == cors_origin
    assert set(ALLOWED_REQUEST_HEADERS) <= _header_list(r.headers["access-control-allow-headers"])
    assert r.headers["access-control-max-age"] == "600"
    assert "access-control-allow-credentials" not in r.headers    # bearer tokens, not cookies
    # CORSMiddleware answers preflights itself, outside RequestIdMiddleware (accepted, F §2.5).
    assert "x-request-id" not in r.headers


def test_responses_expose_request_id_content_disposition_and_retry_after(cors_origin):
    r = TestClient(create_app()).get("/health", headers={"Origin": cors_origin})
    assert r.status_code == 200
    assert {"x-request-id", "content-disposition", "retry-after"} <= _header_list(
        r.headers["access-control-expose-headers"])


@pytest.mark.parametrize("path", ["/health/", "/me/"])
def test_a_trailing_slash_is_a_404_not_a_redirect(path):
    r = TestClient(create_app()).get(path, follow_redirects=False)
    assert r.status_code == 404
    assert "location" not in r.headers
    assert r.json()["error"]["code"] == "not_found"
    assert r.json()["error"]["request_id"] == r.headers["x-request-id"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_middleware.py 2>&1 | tail -6`

Expected: `4 failed, 17 passed`. The preflight fails with `assert 400 == 200`, because today's CORS rejects the new request headers. The expose test fails with `KeyError: 'access-control-expose-headers'`. Both trailing-slash cases fail with `assert 307 == 404`.

- [ ] **Step 3: Set the lists and `redirect_slashes=False` in `backend/api/main.py`**

In `create_app`, replace:

```python
    app = FastAPI(title="Worship Service Builder API", lifespan=lifespan)
```

with:

```python
    # No trailing-slash redirects: a cross-origin 307 drops Authorization (F §1.1).
    app = FastAPI(title="Worship Service Builder API", lifespan=lifespan, redirect_slashes=False)
```

and replace the `CORSMiddleware` block:

```python
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Church-Id"],
    )
```

with:

```python
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Church-Id",
                       "Idempotency-Key", "If-Match", "X-Request-Id"],
        expose_headers=["Content-Disposition", "Retry-After", "X-Request-Id"],
        max_age=600,
    )
```

`allow_credentials` stays at its default (off): the API uses bearer tokens, not cookies. The frontend calls only `/me` and `/church`, never with a trailing slash (`frontend/src/app/page.tsx:53` and `:77`), and nothing calls `/rubric` from a browser yet, so nothing depends on the old 307.

- [ ] **Step 4: Run the tests and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_middleware.py backend/tests/test_api_app.py
.venv/bin/python -m pytest -q | tail -1
```

Expected: `30 passed` (21 + 9), then `510 passed`. `test_api_app.py::test_cors_allows_only_configured_origins` still passes.

- [ ] **Step 5: Commit**

```bash
git add backend/api/main.py backend/tests/test_middleware.py
git commit -m "API: final CORS lists and no trailing-slash redirects (F §1.10, §1.1)

CORS allows Idempotency-Key, If-Match and X-Request-Id, exposes
Content-Disposition, Retry-After and X-Request-Id, and caches preflights for
600 s. GET /me/ is now a 404, not a 307 that would drop Authorization.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Logging with `request_id=` on every line, and `LOG_LEVEL` (S9 logging, S10 settings)

**Files:**
- Create: `backend/api/logging_config.py`
- Modify: `backend/api/settings.py:7-10` (the `Settings` fields), `backend/api/settings.py:25-30` (`get_settings`)
- Modify: `backend/api/main.py:2-4` (imports), the `api.errors` import line (add one after it), `backend/api/main.py:15-21` of the original file (logging setup)
- Test: `backend/tests/test_middleware.py` (imports; append)

**Interfaces:**
- Consumes: `api.middleware.current_request_id()` (Task 1).
- Produces:
  - `api.logging_config.LOG_FORMAT = "%(name)s %(levelname)s request_id=%(request_id)s %(message)s"`;
  - `api.logging_config.configure_logging(level: str) -> int`. It installs the request-id record factory once, configures an unconfigured root logger, and returns the level used (INFO for an unknown name, with the WARNING);
  - `Settings.log_level: str = "INFO"`, which `get_settings()` reads from `LOG_LEVEL` (stripped; blank means `"INFO"`);
  - `api.main` calls `configure_logging(get_settings().log_level)` right after `load_dotenv()`.

- [ ] **Step 1: Write the failing tests**

In `backend/tests/test_middleware.py`, replace:

```python
from api.errors import error_body
from api.main import create_app
from api.middleware import RequestIdMiddleware, UnhandledErrorMiddleware
```

with:

```python
from api.errors import error_body
from api.logging_config import LOG_FORMAT, configure_logging
from api.main import create_app
from api.middleware import RequestIdMiddleware, UnhandledErrorMiddleware
```

Append to `backend/tests/test_middleware.py`:

```python


# --- Logging: request_id= on every line (F §2.5) --------------------------------

def test_a_log_line_from_a_sync_route_carries_the_request_id(caplog):
    app = create_app()
    router = APIRouter()

    @router.get("/hello")
    def hello():                      # a plain def: FastAPI runs it in the threadpool
        logging.getLogger("tests.hello").info("hello")
        return {"ok": True}

    app.include_router(router)
    with caplog.at_level(logging.INFO):
        r = TestClient(app).get("/hello")
    records = [rec for rec in caplog.records if rec.name == "tests.hello"]
    assert len(records) == 1
    assert records[0].request_id == r.headers["x-request-id"]


def test_a_log_line_outside_a_request_has_a_dash(caplog):
    with caplog.at_level(logging.INFO):
        logging.getLogger("tests.outside").info("no request here")
    assert [rec.request_id for rec in caplog.records if rec.name == "tests.outside"] == ["-"]


def test_configure_logging_installs_the_record_factory_once():
    configure_logging("INFO")
    factory = logging.getLogRecordFactory()
    configure_logging("INFO")
    assert logging.getLogRecordFactory() is factory


@pytest.mark.parametrize("value, level", [
    ("debug", logging.DEBUG), (" Warning ", logging.WARNING), ("ERROR", logging.ERROR),
])
def test_configure_logging_accepts_level_names(value, level):
    assert configure_logging(value) == level


def test_an_invalid_log_level_warns_and_uses_info(caplog):
    with caplog.at_level(logging.WARNING):
        assert configure_logging("verbose") == logging.INFO
    assert "LOG_LEVEL='verbose' is not a valid level; using INFO." in [
        rec.getMessage() for rec in caplog.records if rec.levelno == logging.WARNING]


def test_configure_logging_sets_up_a_root_logger_that_has_no_handlers():
    root = logging.getLogger()
    saved_handlers, saved_level = root.handlers[:], root.level
    root.handlers[:] = []                 # as under uvicorn: nothing has configured root
    try:
        assert configure_logging("WARNING") == logging.WARNING
        assert root.level == logging.WARNING
        assert len(root.handlers) == 1
        # A record built without the factory (makeLogRecord) still formats, with "-".
        record = logging.makeLogRecord({"name": "api.x", "levelname": "INFO", "msg": "hi"})
        assert root.handlers[0].format(record) == "api.x INFO request_id=- hi"
    finally:
        root.handlers[:] = saved_handlers
        root.setLevel(saved_level)


def test_the_log_format_names_the_request_id():
    assert LOG_FORMAT == "%(name)s %(levelname)s request_id=%(request_id)s %(message)s"


@pytest.mark.parametrize("env, expected", [(None, "INFO"), ("", "INFO"), (" debug ", "debug")],
                         ids=["unset", "blank", "set"])
def test_the_log_level_setting_comes_from_log_level(monkeypatch, env, expected):
    if env is None:
        monkeypatch.delenv("LOG_LEVEL", raising=False)
    else:
        monkeypatch.setenv("LOG_LEVEL", env)
    settings_mod.get_settings.cache_clear()
    try:
        assert settings_mod.get_settings().log_level == expected
    finally:
        settings_mod.get_settings.cache_clear()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_middleware.py 2>&1 | tail -3`
Expected: collection error `ModuleNotFoundError: No module named 'api.logging_config'`, `1 error`.

- [ ] **Step 3: Create `backend/api/logging_config.py`**

```python
"""API logging: every line carries request_id= (F §2.5; ops slice).

configure_logging(level) does three things:
1. maps the level name (DEBUG, INFO, WARNING, ERROR, CRITICAL; any case); an
   unknown name falls back to INFO with a WARNING;
2. installs, once, a log-record factory that sets record.request_id to the id
   of the request being handled, or "-" outside a request. A factory rather
   than a handler filter, so every handler (pytest's caplog too) sees it;
3. if nothing has configured the root logger yet (as under uvicorn), gives it
   one stream handler with LOG_FORMAT at that level.

Never log request bodies, tokens, invite codes, OAuth codes or state, email
bodies, or AI prompts and outputs (F §2.5).
"""
import logging

from api.middleware import current_request_id

LOG_FORMAT = "%(name)s %(levelname)s request_id=%(request_id)s %(message)s"

_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

logger = logging.getLogger(__name__)


def configure_logging(level: str) -> int:
    """Set up API logging at `level` (a name such as "INFO"); returns the level used."""
    resolved = _LEVELS.get((level or "").strip().upper())
    _install_request_id_factory()
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler()
        # `defaults` covers records built without the factory (logging.makeLogRecord).
        handler.setFormatter(logging.Formatter(LOG_FORMAT, defaults={"request_id": "-"}))
        logging.basicConfig(level=resolved or logging.INFO, handlers=[handler])
    if resolved is None:
        logger.warning("LOG_LEVEL='%s' is not a valid level; using INFO.", level)
        return logging.INFO
    return resolved


def _install_request_id_factory() -> None:
    """Wrap the current log-record factory once; calling again is a no-op."""
    previous = logging.getLogRecordFactory()
    if getattr(previous, "adds_request_id", False):
        return

    def factory(*args, **kwargs):
        record = previous(*args, **kwargs)
        record.request_id = current_request_id() or "-"
        return record

    factory.adds_request_id = True
    logging.setLogRecordFactory(factory)
```

- [ ] **Step 4: Add `log_level` to `backend/api/settings.py`**

Replace lines 7-10:

```python
@dataclass(frozen=True)
class Settings:
    supabase_url: str
    cors_origins: tuple[str, ...]
```

with:

```python
@dataclass(frozen=True)
class Settings:
    supabase_url: str
    cors_origins: tuple[str, ...]
    log_level: str = "INFO"                # LOG_LEVEL; api.logging_config validates it
```

Replace `get_settings` (lines 25-30):

```python
@lru_cache
def get_settings() -> Settings:
    return Settings(
        supabase_url=os.environ.get("SUPABASE_URL", "").strip().rstrip("/"),
        cors_origins=_split_origins(os.environ.get("CORS_ORIGINS", "http://localhost:3000")),
    )
```

with:

```python
@lru_cache
def get_settings() -> Settings:
    return Settings(
        supabase_url=os.environ.get("SUPABASE_URL", "").strip().rstrip("/"),
        cors_origins=_split_origins(os.environ.get("CORS_ORIGINS", "http://localhost:3000")),
        log_level=os.environ.get("LOG_LEVEL", "").strip() or "INFO",
    )
```

Validation stays out of `get_settings`, so importing `api.main` never raises. The `jwks_url` and `token_issuer` properties are unchanged.

- [ ] **Step 5: Call it from `backend/api/main.py`**

Replace lines 2-4:

```python
import logging
import os
from contextlib import asynccontextmanager
```

with:

```python
import logging
from contextlib import asynccontextmanager
```

After `from api.errors import install_error_handlers`, add:

```python
from api.logging_config import configure_logging
```

Replace the logging setup (originally lines 15-21):

```python
load_dotenv()

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(name)s %(levelname)s %(message)s",
    )
```

with:

```python
load_dotenv()
configure_logging(get_settings().log_level)
```

`import logging` stays: the lifespan uses it. Task 5 also adds a module logger.

- [ ] **Step 6: Run the tests and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_middleware.py
.venv/bin/python -m pytest -q | tail -1
```

Expected: `33 passed`, then `522 passed`.

- [ ] **Step 7: Commit**

```bash
git add backend/api/logging_config.py backend/api/settings.py backend/api/main.py backend/tests/test_middleware.py
git commit -m "API logging: request_id= on every line; LOG_LEVEL validated (F §2.5)

A log-record factory, installed once, stamps the current request id (or '-')
on every record, so every handler sees it. An unconfigured root logger gets
'name level request_id=… message'. An unknown LOG_LEVEL logs a WARNING and
uses INFO.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Startup: database target log, `APP_ENV` and the production guards (S10)

**Files:**
- Create: `backend/api/startup.py`
- Modify: `backend/api/settings.py` (add `app_env` and `is_production`)
- Modify: `backend/api/main.py` (imports; module logger; lifespan)
- Test: `backend/tests/test_startup.py` (new)

**Interfaces:**
- Consumes: `api.settings.Settings`, `get_settings()` (Task 4); `db.get_engine() -> Engine`; `db.init_db()`; `db.engine._make_engine(url) -> Engine` (ops-2; it applies the pool and `connect_timeout` settings but opens no connection); fixture `tmp_db`.
- Produces:
  - `Settings.app_env: str = "development"`, which `get_settings()` reads from `APP_ENV` (stripped and lower-cased; blank means `"development"`);
  - `Settings.is_production -> bool`;
  - `api.startup.APP_ENVS = ("development", "production")`;
  - `api.startup.describe_database(url: sqlalchemy.engine.URL) -> str`, pure, never with the username or password;
  - `api.startup.check_app_env(value: str) -> str`, which raises `RuntimeError` with the exact copy;
  - `api.startup.enforce_production_guards(settings: Settings, engine: Engine) -> None`: in production it raises for a non-PostgreSQL engine, and logs an ERROR (logger `api.startup`) when every origin is loopback;
  - `api.main` has module globals `get_engine` and `init_db`, looked up by the lifespan at call time (tests monkeypatch them), and `logger = logging.getLogger("api.main")`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_startup.py`:

```python
"""Startup: database target log, APP_ENV and the production guards (ops slice, F §2.6 items 1-2)."""
import logging

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url

import api.main
from api import settings as settings_mod
from api.startup import check_app_env, describe_database
from db.engine import _make_engine

SQLITE_REFUSED = "APP_ENV=production requires a PostgreSQL DATABASE_URL; refusing to start."
LOCALHOST_CORS = ("CORS_ORIGINS allows only localhost origins in production; "
                  "browsers on the real site will be blocked.")


@pytest.fixture
def api_env(monkeypatch):
    """No APP_ENV / CORS_ORIGINS from the developer's shell; get_settings() re-reads the env."""
    for name in ("APP_ENV", "CORS_ORIGINS"):
        monkeypatch.delenv(name, raising=False)
    settings_mod.get_settings.cache_clear()
    yield monkeypatch
    settings_mod.get_settings.cache_clear()


@pytest.fixture
def init_db_calls(monkeypatch):
    """Replace api.main.init_db with a spy; the list records each call."""
    calls = []
    monkeypatch.setattr(api.main, "init_db", lambda: calls.append("init_db"))
    return calls


def _start(app):
    with TestClient(app):
        pass


def test_describe_database_names_the_target_without_credentials():
    url = make_url("postgresql+psycopg2://alice:s3cret@aws-0-x.pooler.supabase.com:5432/postgres")
    text = describe_database(url)
    assert text == "dialect=postgresql driver=psycopg2 host=aws-0-x.pooler.supabase.com database=postgres"
    assert "alice" not in text and "s3cret" not in text


def test_describe_database_for_a_sqlite_file():
    assert describe_database(make_url("sqlite:///data/app.db")) == (
        "dialect=sqlite driver=pysqlite host=- database=data/app.db")


def test_startup_logs_the_database_target(api_env, tmp_db, caplog):
    with caplog.at_level(logging.INFO):
        _start(api.main.create_app())
    lines = [r.getMessage() for r in caplog.records if r.getMessage().startswith("Database: ")]
    assert len(lines) == 1
    assert lines[0].startswith("Database: dialect=sqlite driver=pysqlite host=- database=")


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


@pytest.mark.parametrize("env, expected", [
    (None, "development"), ("", "development"), (" Production ", "production"), ("DEVELOPMENT", "development"),
], ids=["unset", "blank", "padded-production", "upper-development"])
def test_app_env_is_normalized(api_env, env, expected):
    if env is not None:
        api_env.setenv("APP_ENV", env)
    settings = settings_mod.get_settings()
    assert settings.app_env == expected
    assert check_app_env(settings.app_env) == expected
    assert settings.is_production is (expected == "production")


@pytest.mark.parametrize("origins, logs_error", [
    ("http://localhost:3000", True),
    ("http://localhost:3000,http://127.0.0.1:3000,http://[::1]:3000", True),
    ("https://worship-service-builder.vercel.app", False),
    ("http://localhost:3000,https://worship-service-builder.vercel.app", False),
], ids=["localhost", "all-loopback-forms", "vercel", "mixed"])
def test_production_warns_when_cors_allows_only_localhost(api_env, monkeypatch, caplog, init_db_calls,
                                                          origins, logs_error):
    api_env.setenv("APP_ENV", "production")
    api_env.setenv("CORS_ORIGINS", origins)
    engine = _make_engine("postgresql://u:p@localhost:1/db")      # creating it opens no connection
    monkeypatch.setattr(api.main, "get_engine", lambda: engine)
    try:
        with caplog.at_level(logging.INFO):
            _start(api.main.create_app())
    finally:
        engine.dispose()
    messages = [r.getMessage() for r in caplog.records]
    assert "Database: dialect=postgresql driver=psycopg2 host=localhost database=db" in messages
    errors = [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR]
    assert errors == ([LOCALHOST_CORS] if logs_error else [])
    assert init_db_calls == ["init_db"]


def test_development_on_sqlite_starts_without_errors(api_env, tmp_db, caplog):
    with caplog.at_level(logging.INFO):
        _start(api.main.create_app())
    assert [r for r in caplog.records if r.levelno >= logging.ERROR] == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_startup.py 2>&1 | tail -3`
Expected: collection error `ModuleNotFoundError: No module named 'api.startup'`, `1 error`.

- [ ] **Step 3: Create `backend/api/startup.py`**

```python
"""Startup checks the API lifespan runs before anything touches the database
(F §2.6 items 1 and 2; ops slice).

- describe_database: the database target for the startup log line, never
  with the username or password.
- check_app_env: APP_ENV must be "development" or "production".
- enforce_production_guards: in production, refuse to start on anything but
  PostgreSQL (a missing DATABASE_URL would otherwise mean an ephemeral SQLite
  file on Railway), and log an ERROR when CORS_ORIGINS lists only localhost.

A RuntimeError here makes uvicorn exit with "Application startup failed"; on
Railway the new deploy then fails and the previous release keeps serving.
"""
import logging
from urllib.parse import urlsplit

from sqlalchemy.engine import URL, Engine

from api.settings import Settings

logger = logging.getLogger(__name__)

APP_ENVS = ("development", "production")
_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}   # urlsplit drops the brackets of [::1]


def describe_database(url: URL) -> str:
    return (f"dialect={url.get_backend_name()} driver={url.get_driver_name()} "
            f"host={url.host or '-'} database={url.database or '-'}")


def check_app_env(value: str) -> str:
    """Return "development" or "production"; raise RuntimeError for anything else."""
    if value not in APP_ENVS:
        raise RuntimeError(f"APP_ENV must be 'development' or 'production' (got '{value}').")
    return value


def enforce_production_guards(settings: Settings, engine: Engine) -> None:
    if not settings.is_production:
        return
    if engine.dialect.name != "postgresql":
        raise RuntimeError("APP_ENV=production requires a PostgreSQL DATABASE_URL; refusing to start.")
    if all(urlsplit(origin).hostname in _LOOPBACK_HOSTS for origin in settings.cors_origins):
        logger.error("CORS_ORIGINS allows only localhost origins in production; "
                     "browsers on the real site will be blocked.")
```

An empty `CORS_ORIGINS` also counts as "only localhost" (`all([])` is true), and that is right: no browser origin would be allowed.

- [ ] **Step 4: Add `app_env` and `is_production` to `backend/api/settings.py`**

Replace (from Task 4):

```python
    log_level: str = "INFO"                # LOG_LEVEL; api.logging_config validates it
```

with:

```python
    app_env: str = "development"           # APP_ENV; api.startup.check_app_env validates it
    log_level: str = "INFO"                # LOG_LEVEL; api.logging_config validates it

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"
```

and replace:

```python
        log_level=os.environ.get("LOG_LEVEL", "").strip() or "INFO",
```

with:

```python
        app_env=os.environ.get("APP_ENV", "").strip().lower() or "development",
        log_level=os.environ.get("LOG_LEVEL", "").strip() or "INFO",
```

- [ ] **Step 5: Rewrite the lifespan in `backend/api/main.py`**

After this step the whole file reads as below. Compared with Task 4, three things change: the imports of `api.startup` and `get_engine`, the module `logger`, and the lifespan, which replaces lines 24-31 of the original file. The `rubric` router (PR #4) stays exactly where it was.

```python
"""FastAPI entry point. Run from backend/: uvicorn api.main:app --reload"""
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.errors import install_error_handlers
from api.logging_config import configure_logging
from api.middleware import RequestIdMiddleware, UnhandledErrorMiddleware
from api.routes import health, me, rubric
from api.settings import get_settings
from api.startup import check_app_env, describe_database, enforce_production_guards
from db import get_engine, init_db

load_dotenv()
configure_logging(get_settings().log_level)

logger = logging.getLogger(__name__)


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


def create_app() -> FastAPI:
    settings = get_settings()
    # No trailing-slash redirects: a cross-origin 307 drops Authorization (F §1.1).
    app = FastAPI(title="Worship Service Builder API", lifespan=lifespan, redirect_slashes=False)
    # The last middleware added is the outermost: CORS → RequestId → UnhandledError
    # (F §2.5), so CORS decorates the 500s that UnhandledError produces.
    app.add_middleware(UnhandledErrorMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Church-Id",
                       "Idempotency-Key", "If-Match", "X-Request-Id"],
        expose_headers=["Content-Disposition", "Retry-After", "X-Request-Id"],
        max_age=600,
    )
    install_error_handlers(app)
    app.include_router(health.router)
    app.include_router(me.router)
    app.include_router(rubric.router)
    return app


app = create_app()
```

The SUPABASE_URL warning text is unchanged (`test_api_app.py::test_lifespan_warns_when_supabase_url_unset`). `db` already exports `get_engine` (`backend/db/__init__.py`).

- [ ] **Step 6: Run the tests, the suite and a real uvicorn start**

```bash
.venv/bin/python -m pytest -q backend/tests/test_startup.py backend/tests/test_api_app.py
.venv/bin/python -m pytest -q | tail -1
(cd backend && DATABASE_URL="sqlite:///$(mktemp -d)/guard.db" APP_ENV=production \
  ../.venv/bin/python -m uvicorn api.main:app --port 8765 2>&1 | tail -3)
```

Expected: `23 passed` (14 + 9), then `536 passed`. uvicorn exits by itself, and the last three lines are `RuntimeError: APP_ENV=production requires a PostgreSQL DATABASE_URL; refusing to start.`, a blank line, and `ERROR:    Application startup failed. Exiting.` (`load_dotenv()` reads `backend/.env` but never overrides the two variables set on the command line.)

- [ ] **Step 7: Commit**

```bash
git add backend/api/startup.py backend/api/settings.py backend/api/main.py backend/tests/test_startup.py
git commit -m "API startup: log the database target, APP_ENV guards (F §2.6 items 1-2)

The lifespan logs 'Database: dialect=… driver=… host=… database=…' without
credentials. With APP_ENV=production it refuses to start on a non-PostgreSQL
DATABASE_URL, before init_db, and logs an ERROR when CORS_ORIGINS is
localhost-only. An invalid APP_ENV refuses to start.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Readiness: `db/health.py` and `GET /health/ready` (S3)

**Files:**
- Create: `backend/db/health.py`
- Modify: `backend/api/routes/health.py:1-8` (full rewrite)
- Modify: `backend/api/errors.py` (add `db_unavailable()` after `auth_unavailable()`)
- Modify: `backend/tests/conftest.py` (append an autouse fixture at the end, after ops-2's `_fresh_identity_cache`, lines 141-154)
- Test: `backend/tests/test_health_ready.py` (new); `backend/tests/test_foundation_setup.py` (imports; append)

**Interfaces:**
- Consumes: `db.engine.get_engine()`; `db.engine._make_engine(url)`; `tests.conftest.FakeClock(start=1000.0)` with `now()` and `advance(seconds)` (ops-2); `api.errors.ApiError`; fixture `tmp_db`.
- Produces:
  - `db.health.READY_OK_TTL = 10.0`, `db.health.READY_FAIL_TTL = 5.0`;
  - `db.health.database_ready(*, clock: Callable[[], float] = time.monotonic) -> bool`, memoized and single-flight;
  - `db.health._probe() -> bool`, which tests replace;
  - `db.health.reset_readiness_for_tests() -> None`;
  - `api.errors.db_unavailable() -> ApiError(503, "db_unavailable", "The database is not reachable.")`;
  - `api.routes.health.ReadyOut` (`ok: bool`, `db: Literal["ok"]`) and `ready()`, a sync `def`;
  - conftest's autouse `_fresh_readiness_memo`;
  - in `test_foundation_setup.py`: `FRONTEND_ERROR_UNION` and `_missing_error_codes(path, codes=("db_unavailable",)) -> list[str]`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_health_ready.py`:

```python
"""GET /health/ready and db.health.database_ready (ops slice S3, F §1.5, §7.2)."""
import ast
import inspect
import logging
import pathlib
import subprocess
import sys
import threading
import time

import pytest
from fastapi.testclient import TestClient

import db.health
from api.main import create_app
from api.routes import health as health_routes
from db.engine import _make_engine
from db.health import READY_FAIL_TTL, READY_OK_TTL, database_ready
from tests.conftest import FakeClock

BACKEND = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture
def probes(monkeypatch):
    """Replace the real probe with a counting stub; set `probes.result` to choose its answer."""
    class Probe:
        def __init__(self):
            self.calls = 0
            self.result = True

        def __call__(self):
            self.calls += 1
            return self.result

    stub = Probe()
    monkeypatch.setattr(db.health, "_probe", stub)
    return stub


# --- The route ---------------------------------------------------------------

def test_ready_is_200_without_auth(tmp_db):
    r = TestClient(create_app()).get("/health/ready")
    assert r.status_code == 200
    assert r.json() == {"ok": True, "db": "ok"}


def test_ready_ignores_authorization_and_church_headers(tmp_db):
    r = TestClient(create_app()).get("/health/ready", headers={
        "Authorization": "Bearer junk", "X-Church-Id": "not-a-church"})
    assert r.status_code == 200
    assert r.json() == {"ok": True, "db": "ok"}


def test_ready_is_503_db_unavailable_when_the_database_is_unreachable(monkeypatch, caplog):
    unreachable = _make_engine("sqlite:////nonexistent-dir/x.db")   # opening it fails
    monkeypatch.setattr(db.health, "get_engine", lambda: unreachable)
    try:
        with caplog.at_level(logging.WARNING):
            r = TestClient(create_app()).get("/health/ready")
    finally:
        unreachable.dispose()
    assert r.status_code == 503
    assert r.json() == {"error": {
        "code": "db_unavailable",
        "message": "The database is not reachable.",
        "request_id": r.headers["x-request-id"],
    }}
    warnings = [rec.getMessage() for rec in caplog.records if rec.name == "db.health"]
    assert warnings == ["Readiness check failed: OperationalError"]   # the class only, never the message
    assert "nonexistent" not in caplog.text


def test_the_ready_route_is_a_sync_def():
    assert not inspect.iscoroutinefunction(health_routes.ready)


def test_the_route_module_holds_no_sql_and_no_try():
    tree = ast.parse(inspect.getsource(health_routes))
    imported = [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names]
    imported += [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    assert [name for name in imported if name.startswith("sqlalchemy")] == []
    assert [node for node in ast.walk(tree) if isinstance(node, ast.Try)] == []


def test_db_health_imports_no_fastapi():
    code = "import sys, db.health; sys.exit(1 if 'fastapi' in sys.modules or 'starlette' in sys.modules else 0)"
    result = subprocess.run([sys.executable, "-c", code], cwd=BACKEND, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr or "db.health imported fastapi or starlette"


# --- The memo: at most one probe at a time, results reused 10 s / 5 s ---------

def test_the_ttls_are_10_seconds_ok_and_5_seconds_failed():
    assert (READY_OK_TTL, READY_FAIL_TTL) == (10.0, 5.0)


def test_a_success_is_reused_for_10_seconds(probes):
    clock = FakeClock()
    assert database_ready(clock=clock.now) is True
    clock.advance(9)
    assert database_ready(clock=clock.now) is True
    assert probes.calls == 1
    clock.advance(2)                                   # 11 s after the first probe
    assert database_ready(clock=clock.now) is True
    assert probes.calls == 2


def test_a_failure_is_reused_for_5_seconds(probes):
    clock = FakeClock()
    probes.result = False
    assert database_ready(clock=clock.now) is False
    clock.advance(4)
    assert database_ready(clock=clock.now) is False
    assert probes.calls == 1
    clock.advance(2)                                   # 6 s after the failed probe
    probes.result = True
    assert database_ready(clock=clock.now) is True
    assert probes.calls == 2


def test_concurrent_callers_share_one_probe(monkeypatch):
    calls = []

    def slow_probe():
        calls.append(1)
        time.sleep(0.2)
        return True

    monkeypatch.setattr(db.health, "_probe", slow_probe)
    barrier = threading.Barrier(16)
    results = []

    def call():
        barrier.wait(timeout=10)
        results.append(database_ready())

    threads = [threading.Thread(target=call) for _ in range(16)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(calls) == 1
    assert results == [True] * 16
```

In `backend/tests/test_foundation_setup.py`, replace the first three lines (ops-1):

```python
import json
import re
from pathlib import Path
```

with:

```python
import json
import re
from pathlib import Path

import pytest
```

Append to `backend/tests/test_foundation_setup.py`:

```python


# --- ops slice (ops-3): the frontend error union gets db_unavailable (slice 1) ---

FRONTEND_ERROR_UNION = ROOT / "frontend" / "src" / "lib" / "api" / "errors.ts"


def _missing_error_codes(path, codes=("db_unavailable",)):
    """Codes the frontend error union lacks; [] while the file does not exist.

    Slice 1 creates src/lib/api/errors.ts (F §4.11). Until then this check is
    inert; from then on it fails slice 1's CI if the union lacks a code that
    ops added to the backend."""
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    return [code for code in codes if not re.search(rf"""["']{code}["']""", text)]


def test_frontend_error_union_lists_db_unavailable_once_it_exists():
    assert _missing_error_codes(FRONTEND_ERROR_UNION) == []


@pytest.mark.parametrize("content, missing", [
    (None, []),
    ('export type ErrorCode = "not_found" | "internal_error";\n', ["db_unavailable"]),
    ('export type ErrorCode = "not_found" | "db_unavailable";\n', []),
], ids=["no-file-yet", "code-missing", "code-present"])
def test_missing_error_codes_reads_the_union(tmp_path, content, missing):
    path = tmp_path / "errors.ts"
    if content is not None:
        path.write_text(content, encoding="utf-8")
    assert _missing_error_codes(path) == missing
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_health_ready.py 2>&1 | tail -3
.venv/bin/python -m pytest -q backend/tests/test_foundation_setup.py | tail -1
```

Expected: a collection error `ModuleNotFoundError: No module named 'db.health'` and `1 error`. Then `11 passed`: the `errors.ts` check passes as soon as it is written, because the file only arrives in slice 1 (clarification 9). Its `code-missing` case shows that it will bite.

- [ ] **Step 3: Create `backend/db/health.py`**

```python
"""Database readiness probe behind GET /health/ready (ops slice S3).

database_ready() answers "can this process reach the database right now?" with
one `SELECT 1` through the process engine, so it exercises the real pool. The
route is public, so the answer is memoized and single-flight: however many
requests arrive, at most one probe (one pooled connection) runs at a time, and
a result is reused for READY_OK_TTL seconds after a success or READY_FAIL_TTL
after a failure. A caller that waits on the lock waits for at most one probe,
which connect_timeout (10 s, db/engine.py) and statement_timeout (5 s) bound.

The SQL and the try/except live here, not in the route (the recorded
exception to F §2.2 in the ops spec's API section). No FastAPI import.
"""
import logging
import threading
import time
from typing import Callable, Optional

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from db.engine import get_engine

logger = logging.getLogger(__name__)

READY_OK_TTL = 10.0     # seconds a success is reused
READY_FAIL_TTL = 5.0    # seconds a failure is reused

_lock = threading.Lock()
_last: Optional[tuple[bool, float]] = None          # (ok, expires_at)


def database_ready(*, clock: Callable[[], float] = time.monotonic) -> bool:
    """True when the database answered `SELECT 1` recently (memoized, single-flight)."""
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
                # Inside the transaction SQLAlchemy has begun, so LOCAL applies.
                conn.exec_driver_sql("SET LOCAL statement_timeout = '5s'")
            conn.execute(text("SELECT 1")).scalar_one()
        return True
    except SQLAlchemyError as exc:
        # The class name only: driver messages can contain host names.
        logger.warning("Readiness check failed: %s", type(exc).__name__)
        return False


def reset_readiness_for_tests() -> None:
    """Forget the memoized result (backend/tests/conftest.py, before each test)."""
    global _last
    with _lock:
        _last = None
```

When the pool is exhausted, the probe waits for SQLAlchemy's `pool_timeout` (30 s) and then reports 503, which is the correct answer. While a probe is in flight, a flood can still hold threadpool workers waiting on the lock: every public endpoint has that exposure until slice 2's rate limiter, and it no longer touches the database pool.

- [ ] **Step 4: Add `db_unavailable()` to `backend/api/errors.py`**

After `auth_unavailable()` (it ends with `return ApiError(503, "auth_unavailable", "Sign-in is temporarily unavailable. Try again shortly.")`), add:

```python


def db_unavailable() -> ApiError:
    """503 from GET /health/ready only (F §1.5 registry; the recorded F §2.2 exception)."""
    return ApiError(503, "db_unavailable", "The database is not reachable.")
```

Until slice 1 adds `domain_errors.py`, `api/errors.py` is the whole backend registry. `db_unavailable` stays here afterwards; slice 1 reuses it for the schema-behind gate, with `details.reason`.

- [ ] **Step 5: Rewrite `backend/api/routes/health.py`**

Replace the whole file (8 lines) with:

```python
"""Infrastructure probes: GET /health (liveness) and GET /health/ready (readiness).

Recorded exception to F §2.2 items 1 and 4 (ops spec, API): these are probes,
not domain operations, so there is no usecase and no DomainError. The route
calls one db-layer function, db.health.database_ready(), which holds the SQL,
the try/except and the memo, and raises ApiError through db_unavailable().
Slice 1 adds its production schema-behind gate here, before the probe.
"""
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from api.errors import db_unavailable
from db.health import database_ready

router = APIRouter()


class ReadyOut(BaseModel):
    ok: bool
    db: Literal["ok"]


@router.get("/health")
def health() -> dict:
    """Liveness: never touches the database (Railway's deploy health check until slice 1)."""
    return {"ok": True}


@router.get("/health/ready", response_model=ReadyOut)
def ready() -> ReadyOut:
    """Readiness: 503 db_unavailable when the database is not reachable (keepalive.yml)."""
    if not database_ready():
        raise db_unavailable()
    return ReadyOut(ok=True, db="ok")
```

`ReadyOut` lives here because only this module uses it (F §1.3). `ready` is a plain `def`, so it runs in the threadpool, and it logs nothing on success.

- [ ] **Step 6: Reset the memo before each test (`backend/tests/conftest.py`)**

Append to the end of `backend/tests/conftest.py`:

```python


@pytest.fixture(autouse=True)
def _fresh_readiness_memo():
    """/health/ready memoizes its probe for up to 10 s (db.health); a result
    from an earlier test must never answer for this one (ops slice).

    Resets only when db.health is already imported: a stale result can exist
    only then (the deferred-import rule at the top of this file)."""
    import sys

    health = sys.modules.get("db.health")
    if health is not None:
        health.reset_readiness_for_tests()
    yield
```

- [ ] **Step 7: Run the tests, the concurrency test repeatedly, and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_health_ready.py backend/tests/test_foundation_setup.py
for i in $(seq 1 10); do .venv/bin/python -m pytest -q -p no:cacheprovider \
  backend/tests/test_health_ready.py -k concurrent | tail -1; done | grep -c "1 passed"
.venv/bin/python -m pytest -q | tail -1
```

Expected: `21 passed` (10 + 11); `10` (no flaky run); `550 passed`.

- [ ] **Step 8: Commit**

```bash
git add backend/db/health.py backend/api/routes/health.py backend/api/errors.py \
        backend/tests/conftest.py backend/tests/test_health_ready.py backend/tests/test_foundation_setup.py
git commit -m "Add GET /health/ready: memoized, single-flight SELECT 1 (ops S3, F §1.5)

db.health.database_ready() holds the SQL, the try/except and the memo (10 s
after a success, 5 s after a failure, one probe at a time). The public route
returns {\"ok\": true, \"db\": \"ok\"} or 503 db_unavailable. A guard makes
slice 1's frontend error union include db_unavailable.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: `keepalive.yml` curls `/health/ready`; delete `keepalive.py` (S3, inv H4)

**Files:**
- Modify: `.github/workflows/keepalive.yml:1-21` (full rewrite)
- Delete: `backend/keepalive.py`, `backend/tests/test_keepalive.py`
- Modify: `README.md:194-199` ("Keep-alive (required)")
- Modify: `docs/ops-runbook.md` (a new `## Keep-alive` section directly above `## Streamlit freeze`; three lines of the ops-2 pool bullet and the "Values set" bullet in `## Platform limits`)
- Modify: `backend/db/engine.py:10-12` (the last two lines of the module docstring; line 12's closing `"""` is unchanged context)
- Test: `backend/tests/test_ops_workflows.py` (append)

**Interfaces:**
- Consumes: from `test_ops_workflows.py` (ops-1): `ROOT`, `_read(path)`, `BACKUP_YML`, `RUNBOOK`, `README`, and the module import `yaml`.
- Produces: `KEEPALIVE_YML`, `KEEPALIVE_MUST_CONTAIN` and `KEEPALIVE_MUST_NOT_CONTAIN` in `test_ops_workflows.py`; the workflow reads the repository variable `API_BASE_URL` (the owner sets it before the merge, Task 11, Step 3; clarification 20); the runbook section `## Keep-alive`, with a run-record row filled in Task 15.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_ops_workflows.py`:

```python


# --- keepalive.yml: curls /health/ready and holds no secret (ops-3) -------------

KEEPALIVE_YML = ROOT / ".github" / "workflows" / "keepalive.yml"
KEEPALIVE_MUST_CONTAIN = (
    "schedule:",
    "cron:",
    "/health/ready",
    "vars.API_BASE_URL",
    "--fail",
    # Exact copy from the ops spec's "Exact server messages" table.
    "::error::Set the API_BASE_URL repository variable (Settings → Secrets and variables → Actions → Variables)",
)
KEEPALIVE_MUST_NOT_CONTAIN = ("secrets.", "python keepalive.py")


def test_keepalive_workflow_curls_readiness():
    text = _read(KEEPALIVE_YML)
    assert [needle for needle in KEEPALIVE_MUST_CONTAIN if needle not in text] == []


def test_keepalive_workflow_holds_no_secret():
    text = _read(KEEPALIVE_YML)
    assert [needle for needle in KEEPALIVE_MUST_NOT_CONTAIN if needle in text] == []


def test_keepalive_workflow_needs_no_token_permissions_and_no_checkout():
    workflow = yaml.safe_load(_read(KEEPALIVE_YML))
    assert workflow["permissions"] == {}
    assert [step["uses"] for step in workflow["jobs"]["ping"]["steps"] if "uses" in step] == []


def test_the_keepalive_script_and_its_tests_are_gone():
    left = [rel for rel in ("backend/keepalive.py", "backend/tests/test_keepalive.py") if (ROOT / rel).exists()]
    assert left == []


def test_backup_workflow_runs_pg_dump_on_a_schedule():
    # Ported from the deleted test_keepalive.py::test_backup_workflow_present.
    text = _read(BACKUP_YML)
    assert "pg_dump" in text
    assert "schedule:" in text


def test_readme_keep_alive_paragraph_describes_the_readiness_curl():
    section = _read(README).split("### Keep-alive (required)", 1)[1].split("\n### ", 1)[0]
    for needle in ("/health/ready", "API_BASE_URL", "docs/ops-runbook.md"):
        assert needle in section, needle
    for stale in ("keepalive.py", "DATABASE_URL"):
        assert stale not in section, stale


def test_runbook_keep_alive_section_names_the_variable_and_the_endpoint():
    text = _read(RUNBOOK)
    section = text.split("\n## Keep-alive\n", 1)[1].split("\n## ", 1)[0]
    for needle in ("API_BASE_URL", "/health/ready", "keepalive.yml", "keep-awake.yml"):
        assert needle in section, needle
    assert "keepalive.py" not in text        # the script is gone; nothing may point at it
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py 2>&1 | tail -8`

Expected: `6 failed, 67 passed`. The two workflow-text tests fail on the old workflow (`'/health/ready'` missing; `'secrets.'` present). The permissions test fails with `KeyError: 'permissions'`. The files test lists both files. The README test fails with `AssertionError: /health/ready` (today's paragraph already names `docs/ops-runbook.md`). The runbook test fails with `IndexError: list index out of range`, because there is no `## Keep-alive` section yet. The ported backup test passes.

- [ ] **Step 3: Rewrite `.github/workflows/keepalive.yml`**

Replace the whole file with:

```yaml
# Keeps the Supabase Free database from pausing (it pauses after ~7 idle days)
# by asking the API whether it is ready: GET /health/ready runs SELECT 1
# through the API's own connection pool (ops slice, S3). The job holds no
# database credentials and no token permissions. It needs only the repository
# variable API_BASE_URL, the Railway URL, which is not secret: the frontend
# bundle already carries it as NEXT_PUBLIC_API_URL. docs/ops-runbook.md → Keep-alive.
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

Four tries of at most 30 s plus three 20 s waits is 180 s, inside `timeout-minutes: 5`. `${API_BASE_URL%/}` drops one trailing slash, so a variable pasted with one still works. Without the variable a run fails at the `::error::` line, which is intended; the owner sets it before the merge (Task 11, Step 3), so no scheduled run on `main` meets that case.

- [ ] **Step 4: Delete the script and its tests**

```bash
git rm backend/keepalive.py backend/tests/test_keepalive.py
grep -rnE '(import|from) keepalive' --include='*.py' backend app.py streamlit_* ui_helpers.py; echo "grep exit $?"
```

Expected: `rm 'backend/keepalive.py'`, `rm 'backend/tests/test_keepalive.py'`, then no grep output and `grep exit 1`: nothing else imported it (before the `git rm`, the only hit was `test_keepalive.py` itself).

- [ ] **Step 5: Rewrite the README "Keep-alive (required)" paragraph**

`README.md:194-199` reads:

```markdown
### Keep-alive (required)

The free Supabase project pauses after ~7 days idle. `.github/workflows/keepalive.yml`
runs `keepalive.py` (a `SELECT 1` against `DATABASE_URL`) daily so the first
visitor each week never hits a paused/cold database. Do not add a
`DATABASE_URL` repository secret; see docs/ops-runbook.md → Backups.
```

Replace it with:

```markdown
### Keep-alive (required)

The free Supabase project pauses after ~7 days idle. `.github/workflows/keepalive.yml`
runs daily at 09:17 UTC and curls the API's `GET /health/ready`, which runs a
`SELECT 1` through the API's own connection pool, so the first visitor each
week never hits a paused database. The job holds no database credentials: it
needs only the Actions **variable** `API_BASE_URL` (the Railway URL, already
public in the frontend bundle). Details, and what to do when it is red:
`docs/ops-runbook.md` → Keep-alive.
```

The "Backups (required)" paragraph below it (ops-1) and the rest of the README stay unchanged (slice 7). The runbook's Environments section (Task 9) keeps the old "no `DATABASE_URL` repository secret" advice.

- [ ] **Step 6: Add the runbook's Keep-alive section and fix the pool and "Values set" bullets**

In `docs/ops-runbook.md`, insert this section directly above the line `## Streamlit freeze`, so it follows `## Backups` and its `### Backup run record`:

````markdown
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
  https://liturgy-next.streamlit.app/, the production Streamlit app, in
  headless Chromium (a plain HTTP ping does not count as traffic). Deleted in
  slice 7.

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
`GET /health` stays the dependency-free liveness probe and Railway's deploy
health check; slice 1 moves the deploy check to `/health/ready`.

**If `keepalive` is red:**
1. `curl -i https://church-production-74ca.up.railway.app/health`. If that
   fails too, the API is down: Railway → the API service → Deployments.
2. If `/health` is 200 and `/health/ready` is 503: Supabase Dashboard → is the
   project paused? Restore it. Otherwise read the Railway logs for
   `Readiness check failed:`.
3. If the log shows `::error::Set the API_BASE_URL repository variable …`,
   set the variable as above.
4. GitHub disables scheduled workflows in a public repository after 60 days
   without activity (ops spec, Risks item 7): re-enable it under Actions →
   keepalive. Slice 7 adds an external uptime monitor.

| Date | Run | Result |
|---|---|---|
| [owner: first manual run after ops-3] | [owner: run URL] | [owner: green; the log shows `{"ok":true,"db":"ok"}`] |

````

(The outer four-backtick fence is only for this plan; paste the content between the fences.)

In `## Platform limits`, ops-2's pool bullet ("Since ops-2, `backend/db/engine.py` reads …") contains these three lines:

```markdown
  that engine setup. `backend/keepalive.py` builds its own engine without
  these settings (ops-3 replaces it); its one short scheduled session fits in
  the spare connection (14 of 15). `backend/tests/test_ops_workflows.py`
```

Replace them with:

```markdown
  that engine setup, and so does the API's `GET /health/ready` probe (ops-3),
  which holds at most one of the API's pooled connections at a time. The old
  keep-alive script, which built its own engine, is gone.
  `backend/tests/test_ops_workflows.py`
```

The rest of that bullet ("fails if the code defaults stop fitting …") is unchanged.

Two bullets further down, the "Values set" bullet (ops-2) reads:

```markdown
- Values set: `DB_POOL_SIZE=3` and `DB_MAX_OVERFLOW=3` as Railway service
  variables (API), and as top-level keys `DB_POOL_SIZE = "3"` and
  `DB_MAX_OVERFLOW = "3"` in the `liturgy-stg` app's Streamlit Secrets (not
  `liturgy`, which is being deleted): 2026-09-26 (Railway API service and `liturgy-stg` Secrets)
```

It contradicts the bullet above it (both apps are gone). Replace those four lines with what is true when ops-3 merges (Task 15 replaces it again with the Freeze facts):

```markdown
- Values set: `DB_POOL_SIZE=3` and `DB_MAX_OVERFLOW=3` as Railway service
  variables (API), and as top-level keys `DB_POOL_SIZE = "3"` and
  `DB_MAX_OVERFLOW = "3"` in the production Streamlit Secrets, at the very top
  above the first `[section]` line (a key below `[auth]` belongs to that
  section, and Streamlit does not export it to the environment). Set in
  `liturgy-stg`'s Secrets on 2026-09-26, before that app was deleted the same
  day; for `liturgy-next`'s see the ops-2 gate table and the Freeze record.
```

- [ ] **Step 7: Fix the `db/engine.py` docstring**

The module docstring (ops-2) ends with (lines 10-12):

```python
Supabase session pooler (docs/ops-runbook.md → Platform limits). keepalive.py
builds its own engine and does not get these settings.
"""
```

Replace those three lines with:

```python
Supabase session pooler (docs/ops-runbook.md → Platform limits). The API's
readiness probe (db/health.py) uses this engine too.
"""
```

- [ ] **Step 8: Run the tests, a stale-reference check and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_docs.py
grep -rnI --exclude-dir=__pycache__ 'keepalive\.py' backend .github README.md docs/ops-runbook.md docs/manual-verification.md \
  | grep -v '^backend/tests/test_ops_workflows.py'; echo "grep exit $?"
.venv/bin/python -m pytest -q | tail -1
```

Expected: `76 passed` (73 + 3); no grep output and `grep exit 1`; `552 passed` (7 added, 5 deleted).

- [ ] **Step 9: Commit**

```bash
git add .github/workflows/keepalive.yml README.md docs/ops-runbook.md backend/db/engine.py \
        backend/tests/test_ops_workflows.py
git commit -m "keepalive: curl the API's /health/ready; delete keepalive.py (ops S3, inv H4)

The workflow needs only the repository variable API_BASE_URL and holds no
database secret or token permission. keepalive.py and test_keepalive.py are
gone; their workflow assertions live in test_ops_workflows.py. README and the
runbook's new Keep-alive section describe the curl and what to do when it is
red. The runbook's pool and "Values set" bullets no longer name the script or
the deleted liturgy-stg app as current.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

(`git rm` in Step 4 already staged the two deletions.)

---

### Task 8: Freeze on `main`: the FROZEN header, and a keep-awake guard (S7)

`keep-awake.yml` already visits only https://liturgy-next.streamlit.app/ on `main` (PR #6/#12), so this task does not edit it. It adds the spec's keep-awake test as a guard (it passes when written) and the FROZEN header (test first).

**Files:**
- Modify: `app.py:1` (insert line 2)
- Test: `backend/tests/test_ops_workflows.py` (append)

**Interfaces:**
- Consumes: `ROOT`, `_read(path)`, `yaml` from `test_ops_workflows.py`.
- Produces: `KEEP_AWAKE_YML`, `PRODUCTION_STREAMLIT_URL = "https://liturgy-next.streamlit.app/"`, `DELETED_STREAMLIT_URLS`, `FROZEN_HEADER` (Task 16 reuses `FROZEN_HEADER`).

- [ ] **Step 1: Write the tests**

Append to `backend/tests/test_ops_workflows.py`:

```python


# --- Streamlit freeze on main: keep-awake and the FROZEN header (ops-3) --------

KEEP_AWAKE_YML = ROOT / ".github" / "workflows" / "keep-awake.yml"
PRODUCTION_STREAMLIT_URL = "https://liturgy-next.streamlit.app/"   # the one Streamlit app since 2026-09-26
DELETED_STREAMLIT_URLS = ("https://liturgy.streamlit.app", "https://liturgy-stg.streamlit.app")
FROZEN_HEADER = "# FROZEN — production runs from branch streamlit-frozen; deleted in slice 7."


def test_keep_awake_pings_only_the_production_streamlit_app():
    text = _read(KEEP_AWAKE_YML)
    steps = yaml.safe_load(text)["jobs"]["visit"]["steps"]
    urls = [url for step in steps for url in step.get("env", {}).get("APP_URLS", "").split()]
    assert urls == [PRODUCTION_STREAMLIT_URL]
    assert [url for url in DELETED_STREAMLIT_URLS if url in text] == []


def test_app_py_carries_the_frozen_header():
    lines = _read(ROOT / "app.py").splitlines()
    first = lines[1] if lines[0].startswith("#!") else lines[0]   # the line after the shebang
    assert first == FROZEN_HEADER
```

Neither deleted URL is a substring of `https://liturgy-next.streamlit.app/` (a `-` follows `liturgy` there, then `next`), so the second assertion cannot trip on the production URL.

- [ ] **Step 2: Run the tests: the header test fails, the keep-awake guard passes**

Run: `.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py 2>&1 | tail -3`

Expected: `1 failed, 74 passed`. `test_app_py_carries_the_frozen_header` fails with `assert '"""' == '# FROZEN — production runs from branch streamlit-frozen; deleted in slice 7.'`. `test_keep_awake_pings_only_the_production_streamlit_app` passes: it guards what `main` already has (clarification 1).

- [ ] **Step 3: Add the FROZEN header to `app.py`**

`app.py` starts:

```python
#!/usr/bin/env python3
"""
Streamlit UI: worship service planner with hymn suggestions by scripture,
```

Insert one line after line 1, so it starts:

```python
#!/usr/bin/env python3
# FROZEN — production runs from branch streamlit-frozen; deleted in slice 7.
"""
Streamlit UI: worship service planner with hymn suggestions by scripture,
```

The docstring stays the module's first statement. Nothing else in `app.py` changes. ops-3's only change to a file the Streamlit app runs is this comment line. It states the target, not the state at merge time: from the ops-3 merge until the Freeze (Tasks 13–14) `liturgy-next` still deploys from `main`, so for those days the comment is ahead of the facts. `streamlit-frozen`, cut from the ops-3 merge commit, carries it too, and it is true there from the Freeze on. If the Freeze falls back to `main`, Task 16 removes it.

- [ ] **Step 4: Run the tests and the suite**

```bash
.venv/bin/python -m py_compile app.py && echo compiled
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py
.venv/bin/python -m pytest -q | tail -1
```

Expected: `compiled`, `75 passed`, `554 passed`.

- [ ] **Step 5: Commit**

```bash
git add app.py backend/tests/test_ops_workflows.py
git commit -m "Streamlit freeze on main: FROZEN header in app.py; keep-awake guard (F §6.1)

keep-awake already visits only liturgy-next, the production Streamlit app; a
test now keeps it that way and keeps the deleted liturgy and liturgy-stg URLs
out. The header states the target: liturgy-next moves to streamlit-frozen in
the Freeze, after this merges.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Runbook sections and the "Ops slice" manual checks (S15)

**Files:**
- Modify: `docs/ops-runbook.md` (the intro bullet about ops-3, lines 13-15; a new `## Environments and variables` directly above `## Supabase lockdown record`; five new `###` subsections directly above `## Platform limits`)
- Modify: `docs/manual-verification.md` (append `## Ops slice` after line 45)
- Test: `backend/tests/test_ops_workflows.py` (append)

**Interfaces:**
- Consumes: `ROOT`, `_read(path)`, `RUNBOOK`, `re` from `test_ops_workflows.py`.
- Produces: `RUNBOOK_SECTIONS` (the seven `##` headings in order), `FREEZE_SUBSECTIONS`, `MANUAL_VERIFICATION` and `_section(text, heading) -> str`. ops-3's `[owner: …]` markers are 17 lines: one in "Environments and variables" and the first "Freeze record" row (both filled in Task 11), one Keep-alive run row (Task 7), the other eleven "Freeze record" rows and three version lines (Tasks 13–15).

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_ops_workflows.py`:

```python


# --- Runbook sections, freeze record, manual checks (ops-3) --------------------

RUNBOOK_SECTIONS = (
    "## Environments and variables",
    "## Supabase lockdown record",
    "## Backups",
    "## Keep-alive",
    "## Streamlit freeze",
    "## Platform limits",
    "## Incident response",
)
FREEZE_SUBSECTIONS = (
    "### Streamlit apps",
    "### What the frozen app inherits from ops-3",
    "### Freeze record",
    "### Freeze policy",
    "### Recorded Python and package versions",
    "### Contingency",
)
MANUAL_VERIFICATION = ROOT / "docs" / "manual-verification.md"


def _section(text, heading):
    """The body of `heading` up to the next heading of the same level."""
    level = heading.split(" ", 1)[0]
    return text.split(f"\n{heading}\n", 1)[1].split(f"\n{level} ", 1)[0]


def test_runbook_has_the_seven_sections_in_order():
    assert re.findall(r"^## .+$", _read(RUNBOOK), re.MULTILINE) == list(RUNBOOK_SECTIONS)


def test_runbook_streamlit_freeze_has_the_record_policy_and_versions():
    section = _section(_read(RUNBOOK), "## Streamlit freeze")
    headings = re.findall(r"^### .+$", section, re.MULTILINE)
    assert [h for h in FREEZE_SUBSECTIONS if h not in headings] == []


def test_runbook_environments_name_every_ops_setting():
    section = _section(_read(RUNBOOK), "## Environments and variables")
    for name in ("APP_ENV", "LOG_LEVEL", "DB_POOL_SIZE", "DB_MAX_OVERFLOW", "CORS_ORIGINS",
                 "API_BASE_URL", "BACKUP_DATABASE_URL", "NEXT_PUBLIC_API_URL", "streamlit-frozen",
                 "https://liturgy-next.streamlit.app/"):
        assert name in section, name


def test_runbook_contingency_keeps_the_old_season_wording_and_no_prayer_library():
    # F §6.1 item 6 and §6.2 (amendment 2026-09-26): if Streamlit stays on main,
    # it gets no new features.
    section = _section(_section(_read(RUNBOOK), "## Streamlit freeze"), "### Contingency")
    for needle in ("LEGACY_SYSTEM_PROMPT", "legacy_default_prompts()", "prayer_library",
                   "streamlit_tests/test_app_smoke.py", "Reboot"):
        assert needle in section, needle


def test_manual_verification_has_the_ops_slice_checklist():
    section = _section(_read(MANUAL_VERIFICATION), "## Ops slice")
    for needle in ("/health/ready", "x-request-id", "/me/", "streamlit-frozen", "keep-awake",
                   "https://liturgy-next.streamlit.app", "db-backup", "375 px"):
        assert needle in section, needle
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py 2>&1 | tail -7`

Expected: `5 failed, 75 passed`. The order test fails `At index 0 diff: '## Supabase lockdown record' != '## Environments and variables'`. The freeze test lists the five missing subsections, starting with `'### What the frozen app inherits from ops-3'`. The environments, contingency and manual-verification tests fail with `IndexError: list index out of range`.

- [ ] **Step 3: Replace the runbook's ops-3 intro bullet**

In `docs/ops-runbook.md`, replace (lines 13-15, ops-1):

```markdown
- ops-3 adds "Environments and variables" at the top and "Keep-alive" after
  "Backups", and adds the freeze record, the policy and the recorded versions
  to "Streamlit freeze".
```

with:

```markdown
- The seven sections follow the ops spec (Testing → Manual checks):
  environments and variables, the Supabase lockdown record, backups,
  keep-alive, the Streamlit freeze, platform limits and incident response.
```

- [ ] **Step 4: Add "Environments and variables"**

Insert directly above the line `## Supabase lockdown record`:

````markdown
## Environments and variables

Names, and where each value comes from. Never the secret values themselves.

**Railway, the API service.** Service root `backend`; start command in
`backend/Procfile`; public URL https://church-production-74ca.up.railway.app;
deploy health check: Settings → Deploy → Healthcheck Path `/health` (slice 1
moves it to `/health/ready`). With it, a deployment whose process never answers
(for example the `APP_ENV` guard refusing to start) is not promoted and the
previous one keeps serving. Without it, or if a bad deployment went Active
anyway, roll back by hand: Deployments → the previous deployment → Redeploy.

| Variable | Value | Since |
|---|---|---|
| `DATABASE_URL` | Supabase session-pooler URL (secret) | slice 0 |
| `SUPABASE_URL` | `https://tbecmwtitsoxzkrvxxxu.supabase.co` | slice 0 |
| `CORS_ORIGINS` | `https://worship-service-builder.vercel.app`: exact origins, comma-separated, no trailing slash | slice 0 |
| `APP_ENV` | `production`, set before ops-3 merged and confirmed in effect on the Active deployment (Railway stages variable edits until they are deployed). The API then refuses to start on anything but PostgreSQL, and logs an ERROR when `CORS_ORIGINS` lists only localhost. | ops-3 |
| `LOG_LEVEL` | optional: `DEBUG`, `INFO` (the default when unset), `WARNING` or `ERROR` | ops-3 |
| `DB_POOL_SIZE`, `DB_MAX_OVERFLOW` | `3` and `3` (see Platform limits) | ops-1; read since ops-2 |
| `ESV_API_KEY` | optional: enables the ESV translation (secret) | ops-1 |
| `OPENAI_API_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI` | carried over for later slices (secrets) | slice 0 |

Checked against Railway → the API service → Variables (names only) and Settings → Deploy → Healthcheck Path:
[owner: date, any variable that differs from this table, and the Healthcheck Path]

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
| `liturgy-next`, https://liturgy-next.streamlit.app/ (production, the only Streamlit app) | repo `bbrown62450/church`, main file `app.py`, Python 3.13; branch `main` until the Freeze, then `streamlit-frozen`. Streamlit Cloud cannot change an app's branch, so the Freeze moves an app built and checked from `streamlit-frozen` onto this subdomain (see Freeze record). Sharing: as noted before the Freeze. | the `[auth]` block (Google sign-in, `redirect_uri = https://liturgy-next.streamlit.app/oauth2callback`), `DATABASE_URL`, `OPENAI_API_KEY`, the `GOOGLE_*` gmail.send client with `GOOGLE_OAUTH_REDIRECT_URI = https://liturgy-next.streamlit.app/` (README → Local setup), and `DB_POOL_SIZE = "3"` and `DB_MAX_OVERFLOW = "3"` at the very top, above the first `[section]` line (below `[auth]` they would belong to that section and never reach the environment). The owner keeps a copy in the password manager. |
| `liturgy-frozen`, https://liturgy-frozen.streamlit.app/ (temporary) | branch `streamlit-frozen`, main file `app.py`, Python 3.13; exists only from the Freeze pre-flight until the window, unless the Fallback serves production there (see Freeze record) | the `liturgy-next` Secrets with exactly two values changed: `redirect_uri` and `GOOGLE_OAUTH_REDIRECT_URI` point at `https://liturgy-frozen.streamlit.app/oauth2callback` and `https://liturgy-frozen.streamlit.app/`. A separate password-manager entry. |
| `liturgy`, `liturgy-stg` | deleted on 2026-09-26 (see Streamlit apps) | — |

**Supabase**, project `worship-staging` (ref `tbecmwtitsoxzkrvxxxu`, Nano
compute, Postgres 17.6): Data API off (see Supabase lockdown record); Auth
providers: Google only; `mailer_autoconfirm` off; session pooler Pool Size 15
(see Platform limits).

**Google OAuth client "Liturgy"** (Google Cloud Console → APIs & Services →
Credentials): the Streamlit redirect URIs are
`https://liturgy-next.streamlit.app/oauth2callback` and the bare root
`https://liturgy-next.streamlit.app/`. The four URIs of the deleted `liturgy`
and `liturgy-stg` apps are removed before the Freeze (see Freeze record): once
an app is deleted, anyone may be able to claim its subdomain and would then
receive this client's authorization responses, for sign-in and for the
`gmail.send` flow. For the same reason the temporary `liturgy-frozen` URIs are
registered only while that app holds its subdomain. No other redirect URI is
touched.

````

(Paste the content between the four-backtick fences.)

- [ ] **Step 5: Add the freeze subsections**

Insert directly above the line `## Platform limits`, so they follow ops-2's `### What the frozen app inherits from ops-2` and its gate table. The existing `### Streamlit apps`, `### Streamlit bug triage` and `### D5 fix and recovery record` stay as they are.

````markdown
### What the frozen app inherits from ops-3

Nothing that the Streamlit app runs. ops-3 changes the FastAPI app
(`backend/api/`, which Streamlit never imports), adds `backend/db/health.py`
(imported only by the API), deletes the old keep-alive script (never
imported), edits a docstring in `backend/db/engine.py`, changes workflows and
docs, and adds the FROZEN comment at the top of `app.py`. So
`streamlit-frozen`, cut from the ops-3 merge commit, runs what `liturgy-next`
already runs from `main` after ops-2:

- the service rubric (PR #4): it reads `churches.settings.rubric` and maps
  `text_year` and `hymnal_count` (F §6.2, amendment 2026-09-26);
- the D5 fix (ops-1; see "D5 fix and recovery record");
- `ensure_user` through `upsert_from_claims`, and the 3 + 3 pool with
  `connect_timeout=10` (ops-2; see the gate table above);
- without the six dead modules (ops-1), which it never imported.

It never gets the prayer library (PR #7) or the new season wording (PR #8):
both are new-app only (F §6.2). `streamlit_tests/` passed on the ops-3 PR, and
the pre-freeze smoke check below runs on the ops-3 build.

### Freeze record

The ops spec's Freeze steps for the one production app, `liturgy-next` (see
Streamlit apps; `liturgy` and `liturgy-stg` were deleted on 2026-09-26, so
there is no second app to delete). Streamlit Community Cloud cannot change an
app's branch, and a deleted app's subdomain may not be free again right away.
So the Freeze first builds and checks an app from `streamlit-frozen` on the
temporary subdomain `liturgy-frozen` while `liturgy-next` keeps serving; in
the window it deletes `liturgy-next` and moves the checked app onto that
subdomain with the same Secrets. A row that did not happen says
`not done: rolled back to main` or `not done: Fallback (production on liturgy-frozen)`.

| Step | Result | Date |
|---|---|---|
| Google OAuth client "Liturgy": the four redirect URIs of the deleted `liturgy` and `liturgy-stg` apps removed before the Freeze (a deleted app's subdomain may be claimable by anyone, who would then receive this client's authorization responses); the two `liturgy-next` URIs kept; sign-in on https://liturgy-next.streamlit.app/ checked afterwards. If declined: the accepted risk, and AC 22 is not met | [owner] | [owner] |
| Pre-freeze smoke check on https://liturgy-next.streamlit.app/ after the ops-3 merge and a reboot: sign in, the church and hymnal load, a saved service loads, Settings opens, and the sidebar has no "Church" selectbox. Noted: Python, subdomain, Sharing, other non-default settings; the pool keys sit at the top of the Secrets | [owner] | [owner] |
| Tester "before" message sent, with the window (about 5 minutes) | [owner: window] | [owner] |
| `streamlit-frozen` created at the ops-3 merge commit (`main` was still at that commit) | [owner: commit sha] | [owner] |
| `streamlit-frozen` protected: pull request required with 0 approvals, `backend` check required, no bypassing (admins included), no force pushes, no deletion | [owner] | [owner] |
| Pre-flight: temporary app `liturgy-frozen` from `streamlit-frozen` / `app.py`, Python 3.13, Sharing as `liturgy-next`; its two redirect URIs added; build finished; installed versions compared (see Recorded Python and package versions); smoke check passed, including Gmail connect and a test send; custom subdomain editable in Settings (or the reclaim test result) | [owner] | [owner] |
| In the window: `liturgy-next` Secrets matched the password-manager copy; `liturgy-next` deleted; the checked app moved to the subdomain `liturgy-next` with those Secrets pasted unchanged (or: recreated there from `streamlit-frozen`) | [owner: which way, minutes of downtime] | [owner] |
| Post-freeze smoke check on https://liturgy-next.streamlit.app/ passed, including Gmail connect and a test send; ⋮ → Settings shows branch `streamlit-frozen`, main file `app.py`, Python 3.13 and the noted Sharing | [owner] | [owner] |
| Temporary subdomain retired: no app holds `liturgy-frozen`, and its two redirect URIs are removed from the Google OAuth client | [owner] | [owner] |
| `keep-awake` run by hand: green, one URL (https://liturgy-next.streamlit.app/) | [owner: run URL] | [owner] |
| Tester "after" message sent | [owner] | [owner] |
| After the next merge to `main` (records PR A): `liturgy-next`'s logs show no code pull (`Pulling code changes from Github`, `Updated app!`) after the merge time, and ⋮ → Settings still shows branch `streamlit-frozen` | [owner: the merge, and what the logs showed] | [owner] |

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
  released a new version, pin the versions recorded below in the frozen
  branch's `requirements.txt`. That counts as a data-safety fix: it restores
  the tester's access to their data.
- Merges to `main` no longer reach `liturgy-next` (no code pull in its logs).
  `keep-awake` (on `main`) still keeps it awake.

### Recorded Python and package versions

What production runs from `streamlit-frozen`: the installed versions from the
build of the app that serves the production address after the Freeze (the
pre-flight app's build when it was moved onto `liturgy-next`, or the build of
the app recreated in the window; a later reboot replaces it). Streamlit Cloud
→ the app → Manage app → logs, the dependency-install lines. The app's Python
setting is 3.13. These are the versions to pin if a later reboot breaks the
app (Freeze policy).

- Python: [owner: the exact version from that build log]
- Compared with `liturgy-next`'s last build from `main` before the Freeze: [owner: same, or each name==version that differs]
- Packages:

```
[owner: paste the installed name==version lines from that build log]
```

### Contingency

If `liturgy-next` cannot run from `streamlit-frozen` (F §6.1 item 6):
1. `liturgy-next` was already redeployed from branch `main`, with the same
   subdomain and Secrets (the Freeze's rollback), so it runs `main` as before
   the Freeze. Leave `streamlit-frozen` in place as a record.
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
5. After every merge to `main`, Reboot `liturgy-next` (Manage app → Reboot):
   the running app hot-pulls the commit but can keep stale imported modules.
   Then run the smoke check: sign in, the church and hymnal load, a saved
   service loads, Settings opens.
6. Record the decision and the date here.

````

(Paste the content between the four-backtick fences; the inner three-backtick block belongs in the runbook.)

- [ ] **Step 6: Append the "Ops slice" checklist to `docs/manual-verification.md`**

Append after line 45 (the last Slice 0 item):

```markdown

## Ops slice

Run on the production URLs: https://worship-service-builder.vercel.app (at
375 px in Chrome device mode, iPhone SE, and on desktop),
https://church-production-74ca.up.railway.app, and
https://liturgy-next.streamlit.app, the production Streamlit app (the only
one since `liturgy` and `liturgy-stg` were deleted on 2026-09-26). Record each
result, with its date, in `docs/ops-runbook.md`.

- [ ] Step 0 recorded in `docs/ops-runbook.md` (done on 2026-09-25; confirm the records are there, do not redo the checks): the exposure checks (the Data API was already off: REST and GraphQL with the anon key return 503 `PGRST002` and no rows, so no incident), GraphQL introspection, table owners and BYPASSRLS, `server_version` 17.6 and the `- Postgres server major: 17` line, the pooler Pool Size 15 with 2 × (3 + 3) + 2 = 14 ≤ 15, and Railway's request limit with its source. If a later exposure check ever returns rows: the incident record, including the users/contacts audit and where the forensic dump is kept.
- [ ] D5 workaround message: sent to the tester on day one, or the owner's decision not to send it recorded (as on 2026-09-26).
- [ ] D5 fix, live on `liturgy-next` since the ops-1 merge, in a throwaway church: sign in with a second Google account that has no church and create "Ops test". Tick "Exclude hymns used in the last 12 weeks", pick three hymns, generate the liturgy, click "Prepare bulletin copy": the three picks are still selected. Click "Prepare pastor's copy": both Word files list the three hymns. Save, then load the service again with the box still ticked: its three hymns are in the slots. Delete "Ops test" in Settings → Danger zone. Then run the recovery queries, record the result, and send the tester the "fixed" message.
- [ ] https://worship-service-builder.vercel.app, after the lockdown and after each ops merge: sign in, the church shows in the switcher, switch church if you have two, log out.
- [ ] `db-backup` run by hand: green, with an artifact `backup-*.dump.age`; the log shows no URL or password. The restore drill's counts match production.
- [ ] `https://church-production-74ca.up.railway.app/health/ready` → `{"ok":true,"db":"ok"}`. The `keepalive` run by hand is green.
- [ ] Railway deploy log after ops-3: `Database: dialect=postgresql driver=psycopg2 host=…pooler.supabase.com database=postgres`, with no username or password, and no `CORS_ORIGINS allows only localhost` ERROR line.
- [ ] Browser devtools on the Vercel app: the `/me` response has an `x-request-id` header, and it is readable from JS: in the console, `fetch("https://church-production-74ca.up.railway.app/health").then(r => r.headers.get("x-request-id"))` resolves to an id, not `null`.
- [ ] `curl -i https://church-production-74ca.up.railway.app/me/` → 404 JSON with `request_id`, and no `location` header (not a 307).
- [ ] `liturgy-next` after the ops-3 merge (rebooted), the temporary pre-flight app `liturgy-frozen` from `streamlit-frozen`, and `liturgy-next` again after the Freeze: sign in, the church and hymnal load, load a saved service, open Settings; on the pre-flight app and after the Freeze also connect Gmail and send a test email to yourself. After the Freeze the app's settings show branch `streamlit-frozen` and the Sharing noted before it. After the next merge to `main`, the app's logs show no code pull (`Pulling code changes from Github`, `Updated app!`) and its settings still show `streamlit-frozen`.
- [ ] `keep-awake` is green with one URL, https://liturgy-next.streamlit.app/. The Google OAuth client "Liturgy" lists only the two `liturgy-next` redirect URIs: the deleted `liturgy` and `liturgy-stg` apps' four were removed before the Freeze, and the temporary `liturgy-frozen` two after it.
```

The boxes stay unchecked: this is a reusable checklist, as slice 0 left its own section, and results go into the runbook (clarification 12).

- [ ] **Step 7: Run the tests and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_docs.py
grep -n '^## ' docs/ops-runbook.md
awk '/^## Environments and variables$|^## Keep-alive$|^### What the frozen app inherits from ops-3$/{on=1} /^## Supabase lockdown record$|^## Streamlit freeze$|^## Platform limits$/{on=0} on && /\[owner/{print FNR": "$0}' docs/ops-runbook.md | wc -l
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
.venv/bin/python -m pytest -q | tail -1
```

Expected: `83 passed` (80 + 3); the seven `##` headings in the order of `RUNBOOK_SECTIONS`; `17` (ops-3's markers: the Railway check line, the Keep-alive run row, 12 Freeze record rows and the three version lines); `28` (those 17 plus the 11 ops-1/ops-2 markers from Task 1, Step 1, or fewer if the owner has filled some); `559 passed`.

- [ ] **Step 8: Commit**

```bash
git add docs/ops-runbook.md docs/manual-verification.md backend/tests/test_ops_workflows.py
git commit -m "Runbook: environments, freeze record, policy and contingency; 'Ops slice' checks (S15)

The runbook now has the spec's seven sections. The Freeze moves liturgy-next
to streamlit-frozen after a pre-flight; the contingency keeps the old
season wording and no prayer library (F §6.1 item 6, §6.2). The freeze
record, the recorded versions and the Railway check are [owner: …] markers,
filled before merge and after the Freeze.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Full verification, local smoke and the ops-3 pull request

**Files:** none changed (this plan is already the branch's first commit)

**Interfaces:**
- Consumes: everything from Tasks 1–9.
- Produces: an open PR `claude/ops-3` → `main` with green CI.

- [ ] **Step 1: Run the whole suite and the acceptance checks**

```bash
.venv/bin/python -m pytest -q | tail -1
ls backend/keepalive.py backend/tests/test_keepalive.py backend/cache.py backend/tests/test_cache.py 2>&1 | grep -c "No such file"
(cd backend && ../.venv/bin/python -c "import sys, api.main, db.health; print(sorted(m for m in sys.modules if m.split('.')[0] == 'streamlit'))")
grep -nE '^(from|import) ' backend/db/health.py backend/db/engine.py | grep -E 'api|fastapi|starlette|streamlit'; echo "grep exit $?"
git diff --name-only origin/main...HEAD
git status --short
grep -n '^- Postgres server major: 17$\|docs.railway.com/networking/public-networking/specs-and-limits' docs/ops-runbook.md | wc -l
```

Expected, in order:
- `559 passed`;
- `4` (the keep-alive script and its tests are gone; slice 2's cache files were never created);
- `[]` (the API and the readiness module pull in no Streamlit);
- no output and `grep exit 1` (`db/` imports no `api/`, FastAPI, Starlette or Streamlit);
- exactly these 24 paths, and nothing else (no ops-1 or ops-2 file, no frontend file, no other workflow, not `keep-awake.yml`, `backend/.env.example`, `backend/api/deps.py` or `backend/api/identity_cache.py`):

  ```
  .github/workflows/keepalive.yml
  README.md
  app.py
  backend/api/errors.py
  backend/api/logging_config.py
  backend/api/main.py
  backend/api/middleware.py
  backend/api/routes/health.py
  backend/api/settings.py
  backend/api/startup.py
  backend/db/engine.py
  backend/db/health.py
  backend/keepalive.py
  backend/tests/conftest.py
  backend/tests/test_api_app.py
  backend/tests/test_foundation_setup.py
  backend/tests/test_health_ready.py
  backend/tests/test_keepalive.py
  backend/tests/test_middleware.py
  backend/tests/test_ops_workflows.py
  backend/tests/test_startup.py
  docs/manual-verification.md
  docs/ops-runbook.md
  docs/superpowers/plans/2026-09-25-ops-3-api-platform-freeze.md
  ```
- only `?? .claude/` (nothing else modified or untracked);
- `2` (ops-1's Step 0 records: the Postgres major line and Railway's request limit, AC 19).

- [ ] **Step 2: Check what the frozen branch will inherit**

```bash
git diff --stat origin/main...HEAD -- app.py ui_helpers.py streamlit_auth.py streamlit_tenancy.py \
  streamlit_views streamlit_tests requirements.txt backend/requirements.txt
git diff origin/main...HEAD -- app.py | grep '^[+-][^+-]'
git diff origin/main...HEAD -- backend/db/engine.py | grep -c '^[+-][^+-]'
grep -rnE '^\s*(from|import) (api(\.|\s)|db\.health)' app.py ui_helpers.py streamlit_auth.py streamlit_tenancy.py streamlit_views; echo "grep exit $?"
```

Expected:
- ` app.py | 1 +` and `1 file changed, 1 insertion(+)`;
- `+# FROZEN — production runs from branch streamlit-frozen; deleted in slice 7.`;
- `4` (two docstring lines out, two in);
- no output and `grep exit 1`.

So the Streamlit app's behavior on `streamlit-frozen` is exactly what `liturgy-next` runs from `main` after ops-2, as the runbook's "What the frozen app inherits from ops-3" says.

- [ ] **Step 3: Local smoke test with a real uvicorn**

The agent's shell blocks a foreground `sleep` and does not keep `&` jobs or variables between commands (Global Constraints). Below, `<scratch>` is the absolute path of the session's scratchpad directory (any empty temp directory will do); write it out literally in each command.

Start the server with the Bash tool's `run_in_background: true`:

```bash
DATABASE_URL="sqlite:///<scratch>/ops3-smoke.db" APP_ENV=development CORS_ORIGINS=https://worship-service-builder.vercel.app \
  .venv/bin/python -m uvicorn --app-dir backend api.main:app --port 8765 > "<scratch>/ops3-uvicorn.log" 2>&1
```

Wait for it with a Monitor until-loop whose condition is `curl -sf localhost:8765/health >/dev/null` (it is up within a few seconds; if the Monitor times out, read `<scratch>/ops3-uvicorn.log`). Then run, as one foreground command:

```bash
curl -s localhost:8765/health/ready; echo
curl -si localhost:8765/me/ | tr -d '\r' | grep -iE '^HTTP|^x-request-id|^location|^\{'
curl -si localhost:8765/health -H 'X-Request-Id: smoke-test-0001' | tr -d '\r' | grep -i '^x-request-id'
curl -si -X OPTIONS localhost:8765/me -H 'Origin: https://worship-service-builder.vercel.app' \
  -H 'Access-Control-Request-Method: GET' \
  -H 'Access-Control-Request-Headers: authorization, x-church-id, idempotency-key, if-match, x-request-id' \
  | tr -d '\r' | grep -iE '^HTTP|^access-control-(allow-headers|max-age|allow-origin)'
curl -si localhost:8765/health -H 'Origin: https://worship-service-builder.vercel.app' \
  | tr -d '\r' | grep -i '^access-control-expose-headers'
grep 'Database:' "<scratch>/ops3-uvicorn.log"
```

Then stop the server: stop the background task (TaskStop), or `pkill -f 'api.main:app --port 8765'`. `load_dotenv()` reads `backend/.env` but never overrides the three variables set on the command line. Expected (checked in a scratch clone of this branch on 2026-09-26):

```
{"ok":true,"db":"ok"}
HTTP/1.1 404 Not Found
x-request-id: <32 hex>
{"error":{"code":"not_found","message":"Not Found","request_id":"<the same 32 hex>"}}
x-request-id: smoke-test-0001
HTTP/1.1 200 OK
access-control-max-age: 600
access-control-allow-headers: Accept, Accept-Language, Authorization, Content-Language, Content-Type, Idempotency-Key, If-Match, X-Church-Id, X-Request-Id
access-control-allow-origin: https://worship-service-builder.vercel.app
access-control-expose-headers: Content-Disposition, Retry-After, X-Request-Id
api.main INFO request_id=- Database: dialect=sqlite driver=pysqlite host=- database=<scratch>/ops3-smoke.db
```

There is no `location` line for `/me/`.

- [ ] **Step 4: Check ops-3's runbook markers**

```bash
awk '/^## Environments and variables$|^## Keep-alive$|^### What the frozen app inherits from ops-3$/{on=1} /^## Supabase lockdown record$|^## Streamlit freeze$|^## Platform limits$/{on=0} on && /\[owner/{print FNR": "$0}' docs/ops-runbook.md | wc -l
```

Expected: `17` (the Railway check line, the Keep-alive run row, 12 Freeze record rows, and the three version lines).

- [ ] **Step 5: Push and open the PR (get the owner's go-ahead first)**

```bash
git push -u origin claude/ops-3
gh pr create --base main --head claude/ops-3 \
  --title "ops-3: request ids, CORS-safe 500s, startup guards, /health/ready, keepalive, freeze on main" \
  --body "PR ops-3 of the ops slice (docs/superpowers/specs/2026-09-25-slice-ops-cleanup-design.md; plan docs/superpowers/plans/2026-09-25-ops-3-api-platform-freeze.md).

- RequestIdMiddleware and UnhandledErrorMiddleware (pure ASGI), order CORS → RequestId → UnhandledError: X-Request-Id on every response the app produces, request_id in every error body, unexpected 500s arrive with CORS headers (S9, S13, F §7.3). /me, /church and /rubric are unchanged apart from request_id.
- Final CORS lists (Idempotency-Key, If-Match, X-Request-Id; exposes Content-Disposition, Retry-After, X-Request-Id; max-age 600) and redirect_slashes=False (S11).
- Logging: request_id= on every line; LOG_LEVEL validated. Startup: 'Database: dialect=… driver=… host=… database=…' without credentials; APP_ENV=production refuses a non-PostgreSQL DATABASE_URL before init_db and logs an ERROR for localhost-only CORS (S10).
- GET /health/ready: memoized (10 s ok / 5 s failed), single-flight SELECT 1 in db/health.py; 503 db_unavailable (S3).
- keepalive.yml curls \${API_BASE_URL}/health/ready with no secret; backend/keepalive.py and test_keepalive.py deleted (inv H4).
- app.py FROZEN header; keep-awake.yml already visits only https://liturgy-next.streamlit.app/ and a test now guards it.
- README keep-alive, runbook (environments, keep-alive, freeze record, policy and contingency for liturgy-next), 'Ops slice' manual checks.
- Tests: +75, -5 (559 total).

Before merge (plan Task 11): the ops-2 gate rows are recorded; the owner sets APP_ENV=production on Railway, confirms the /health deploy health check, sets the API_BASE_URL Actions variable and removes the deleted liturgy and liturgy-stg apps' Google redirect URIs. After merge: reboot liturgy-next with a smoke check, and run keepalive (Tasks 11-12); no other merge to main until the Freeze (Tasks 13-15) is done.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
gh pr checks --watch
```

Expected: the `backend`, `backend-postgres` and `frontend` checks pass, and the Vercel preview deployment reports success (the frontend is unchanged).

---

### Task 11 (OWNER, before merge): the ops-2 gate, Railway settings, `API_BASE_URL`, the old redirect URIs, merge

The ops spec's gates: ops-2's ("for at least one day the tester uses Streamlit, still deployed from `main`, and nothing regresses") comes before ops-3, and `APP_ENV=production` is set on Railway **before** merging ops-3. The code on Railway before the merge ignores `APP_ENV`, so setting it early is harmless. Once ops-3 is live, the guard needs it. Two more owner steps happen here because neither depends on the merge: the `API_BASE_URL` variable (clarification 20) and the removal of the deleted apps' redirect URIs (clarification 21).

**Files:**
- Modify (by the agent, from the owner's answers): `docs/ops-runbook.md` → Environments and variables, the `[owner: …]` "Checked against Railway" line; Streamlit freeze → Freeze record, the first row (the old redirect URIs); and, if still open, the six rows of the ops-2 gate table under "What the frozen app inherits from ops-2"

- [ ] **Step 1 (agent): Is the ops-2 gate recorded?**

```bash
git fetch origin
git show origin/main:docs/ops-runbook.md | sed -n '/^| ops-2 gate/,/^$/p' | grep -c '\[owner'
```

Expected: `0`. If it prints more (it printed `6` on 2026-09-26), ask the owner for the six results (the pre-check that `liturgy-next` showed branch `main` and `app.py`; the unique constraint on `users(email)`; the pool keys on Railway and as top-level keys in `liturgy-next`'s Secrets, "present" or "missing" only, where top-level means at the very top of the Secrets, above the first `[section]` line: a key below `[auth]` belongs to that section and Streamlit never exports it to the environment; the API deploy and Vercel sign-in; the `liturgy-next` build and smoke check; the days the tester used `liturgy-next` and what they reported). Record them in Step 5's commit. Do not merge ops-3 while a row is open or the tester has reported a regression.

- [ ] **Step 2 (OWNER): Railway: the deploy health check, and the variables**

Railway → the project → the API service:
1. Settings → Deploy → Healthcheck Path: it must be `/health`; if it is empty, set it to `/health` and save. Without it Railway can promote a new deployment as soon as its container starts, so a deployment that then refuses to start (the `APP_ENV` guard, or any other startup failure) would take the API down instead of leaving the previous release serving (clarification 22).
2. Variables: add `APP_ENV` = `production`. Optionally add `LOG_LEVEL` = `INFO` (unset means `INFO` too).
3. Check, by name and without copying any secret value, that these are present:
   - `DATABASE_URL` starts with `postgresql` (or `postgres`) and points at the Supabase **pooler**. It must not be empty or `sqlite:…`: once ops-3 is live, that would stop the new deploy with `APP_ENV=production requires a PostgreSQL DATABASE_URL; refusing to start.`, and (with item 1's health check) the previous release would keep serving;
   - `CORS_ORIGINS` contains `https://worship-service-builder.vercel.app`, not only `localhost`;
   - `DB_POOL_SIZE` = `3` and `DB_MAX_OVERFLOW` = `3`;
   - `SUPABASE_URL`, and the carried-over `OPENAI_API_KEY` and `GOOGLE_*` variables.
4. Railway stages variable edits until they are deployed: apply them (the staged-changes banner → Deploy) and wait until the new deployment is Active. Then confirm `APP_ENV` = `production` is in effect: the Variables tab lists it with no staged change pending, and the Active deployment's details show it. Nothing else can show it: before ops-3 no code reads `APP_ENV`, and after ops-3 the guards log nothing when all is well.

Then tell the agent the date, the Healthcheck Path, and any variable name that differs from the runbook's Railway table.

- [ ] **Step 3 (OWNER): The Actions variable `API_BASE_URL`**

Set it now, before the merge: the old `keepalive.yml` never reads it, and the rewritten one fails every day at 09:17 UTC until it exists (clarification 20).

GitHub → `bbrown62450/church` → Settings → Secrets and variables → Actions → **Variables** tab → New repository variable:
- Name: `API_BASE_URL`
- Value: `https://church-production-74ca.up.railway.app`

This value is not a secret. Alternatively the agent runs this, on your explicit yes (it changes repository configuration):

```bash
gh variable set API_BASE_URL --body "https://church-production-74ca.up.railway.app" -R bbrown62450/church
```

On the **Secrets** tab there should be no repository secret (`BACKUP_DATABASE_URL` lives in the `backup` environment, Settings → Environments). If a `DATABASE_URL` repository secret exists (the old keep-alive's, which inventory H4 says was never added), delete it: nothing reads it once ops-3 is live, and until then the old workflow merely fails as it does today without it.

- [ ] **Step 4 (OWNER): Remove the deleted apps' four redirect URIs (mandatory)**

Google Cloud Console → APIs & Services → Credentials → the OAuth 2.0 client "Liturgy" → Authorized redirect URIs: remove `https://liturgy.streamlit.app/oauth2callback`, `https://liturgy.streamlit.app/`, `https://liturgy-stg.streamlit.app/oauth2callback` and `https://liturgy-stg.streamlit.app/`. Keep `https://liturgy-next.streamlit.app/oauth2callback` and `https://liturgy-next.streamlit.app/`. Save. The two deleted apps' subdomains may be claimable by anyone, and whoever claims one would receive the authorization responses Google sends for this client (sign-in, and the `gmail.send` flow through the bare-root URIs) under a consent screen the tester trusts (clarification 21).

After a few minutes, sign out of https://liturgy-next.streamlit.app/ and sign in again, to confirm that login still works. Tell the agent the date and the result. If you decide not to remove them, say so: the runbook then records it as an accepted risk, and AC 22 is not met.

- [ ] **Step 5 (agent): Confirm the API is still up and record the checks**

```bash
curl -s https://church-production-74ca.up.railway.app/health; echo
```

Expected: `{"ok":true}`. In `docs/ops-runbook.md` → Environments and variables, replace `[owner: date, any variable that differs from this table, and the Healthcheck Path]` with the date, `matches` (or the differences the owner named, and a table fix to match reality) and `Healthcheck Path /health` (or what the owner found and set). In → Streamlit freeze → Freeze record, fill the first row (the four old redirect URIs) with `removed; sign-in on liturgy-next checked` and the date, or, if the owner declined, `declined by the owner: accepted risk (a deleted app's subdomain may be claimable and would receive this client's authorization responses); AC 22 not met` and the date. If Step 1 found open ops-2 gate rows, fill each with the owner's result and date. Then:

```bash
awk '/^## Environments and variables$|^## Keep-alive$|^### What the frozen app inherits from ops-3$/{on=1} /^## Supabase lockdown record$|^## Streamlit freeze$|^## Platform limits$/{on=0} on && /\[owner/{print FNR": "$0}' docs/ops-runbook.md | wc -l
sed -n '/^| ops-2 gate/,/^$/p' docs/ops-runbook.md | grep -c '\[owner'
.venv/bin/python -m pytest -q | tail -1
git add docs/ops-runbook.md
git commit -m "Runbook: Railway variables and health check checked; old redirect URIs removed

APP_ENV=production is set and in effect before merge, and API_BASE_URL is set.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push
```

Expected: `15`; `0`; `559 passed`. (Name the ops-2 gate in the commit message too if this commit records it, and say "old redirect URIs kept: accepted risk" in the subject if the owner declined.)

- [ ] **Step 6 (OWNER): Review and merge at a quiet time, then reboot `liturgy-next` and smoke-check it**

Until the Freeze every merge to `main` reaches `liturgy-next` (for ops-3: a comment line in `app.py`, a docstring in `backend/db/engine.py`, and the deletion of `backend/keepalive.py`, which Streamlit never imported). Merge on a weekday when the tester is not using the app, never Saturday or Sunday. All CI checks must be green. Merging is outward-facing, so merge only on the owner's explicit yes:

```bash
gh pr merge --merge claude/ops-3
```

Use a merge commit (`--merge`), not squash: its sha is "the ops-3 merge commit" the Freeze branches from.

Right after the merge: Streamlit Cloud (share.streamlit.io) → `liturgy-next` → Manage app → Reboot, so no stale imported module survives the hot-pull. A reboot reinstalls the unpinned requirements (ops spec, Risks item 5), so check at once on https://liturgy-next.streamlit.app/: sign in, the church and hymnal load, a saved service loads. If that fails, stop and tell the agent: a fix on `main` (a dependency pin, or reverting ops-3) comes first, and the Freeze waits until this plan's Task 13 is adjusted to that commit. The full pre-freeze check follows in Task 13, Step 2.

From this merge until Task 14 is done, merge nothing else into `main` (hold every other PR, Dependabot's included): `liturgy-next` would hot-pull it, and the pre-freeze check would then test a newer commit than the one `streamlit-frozen` is cut from. Task 13, Step 1 stops if `main` has moved.

---

### Task 12 (OWNER + agent, after merge): deploy checks, keepalive

**Files:** none (results go into the runbook in Task 15)

- [ ] **Step 1 (OWNER): Railway deploy log, and `APP_ENV` in effect**

Railway → the API service → Deployments: the deployment for the merge commit is Active, and its details still show `APP_ENV` = `production` (Task 11, Step 2, item 4). Its deploy logs show exactly one line of this shape, with no username or password in it:

```
api.main INFO request_id=- Database: dialect=postgresql driver=psycopg2 host=aws-…pooler.supabase.com database=postgres
```

They must show no `CORS_ORIGINS allows only localhost` line and no traceback. If the deploy failed with `APP_ENV=production requires a PostgreSQL DATABASE_URL; refusing to start.`, the health check kept the previous release serving: fix `DATABASE_URL` (Task 11, Step 2) and redeploy. If a failing deployment went Active anyway (`/health` answers 5xx or not at all), roll back by hand: Deployments → the previous deployment → ⋮ → Redeploy; then fix the cause and redeploy the merge commit. (AC 18.)

- [ ] **Step 2 (agent): Production responses**

These are public, read-only requests:

```bash
API=https://church-production-74ca.up.railway.app
curl -s "$API/health/ready"; echo
curl -si "$API/me/" | tr -d '\r' | grep -iE '^HTTP|^x-request-id|^location|^\{'
curl -si -X OPTIONS "$API/me" -H 'Origin: https://worship-service-builder.vercel.app' \
  -H 'Access-Control-Request-Method: GET' \
  -H 'Access-Control-Request-Headers: authorization, x-church-id, idempotency-key, if-match, x-request-id' \
  | tr -d '\r' | grep -iE '^HTTP|^access-control-(allow-headers|max-age|allow-origin)'
curl -si "$API/health" -H 'Origin: https://worship-service-builder.vercel.app' \
  | tr -d '\r' | grep -iE '^x-request-id|^access-control-expose-headers'
```

Expected:
- `{"ok":true,"db":"ok"}`;
- a `404` status line, an `x-request-id` line and the JSON error body with the same `request_id`, and no `location` line;
- a `200` status line; `access-control-allow-headers` listing `Authorization`, `Idempotency-Key`, `If-Match`, `X-Church-Id` and `X-Request-Id`; `access-control-max-age: 600`; `access-control-allow-origin: https://worship-service-builder.vercel.app`;
- an `x-request-id` line and `access-control-expose-headers: Content-Disposition, Retry-After, X-Request-Id`.

- [ ] **Step 3 (agent, on the owner's yes): Run keepalive by hand**

```bash
gh variable list -R bbrown62450/church
gh workflow run keepalive --ref main -R bbrown62450/church
gh run list --workflow keepalive --limit 1 -R bbrown62450/church --json databaseId,createdAt,status
```

The new run takes a few seconds to appear: if the listed run was created before the dispatch, run the `gh run list` line again (no `sleep`). Then, with its `databaseId`:

```bash
gh run watch <run-id> --exit-status -R bbrown62450/church
gh run view <run-id> --log -R bbrown62450/church | grep -c '{"ok":true,"db":"ok"}'
```

Expected: `API_BASE_URL` with the Railway URL in the variable list (set in Task 11, Step 3); the run completes successfully; `1`. Note the date and the run URL for the runbook's Keep-alive record (Task 15). (AC 5.)

- [ ] **Step 4 (OWNER): The React app and request-id exposure**

On https://worship-service-builder.vercel.app, at 375 px (Chrome device mode, iPhone SE) and on desktop: sign in, the church shows in the switcher, switch church if you have two, log out. In devtools → Network, the `/me` response has an `x-request-id` header. In the console, `fetch("https://church-production-74ca.up.railway.app/health").then(r => r.headers.get("x-request-id"))` resolves to an id, not `null` (the header is exposed to JS).

Give the agent the dates and results of Steps 1–4.

---

### Task 13 (OWNER + agent): Freeze, part 1: pre-freeze checks, the "before" message, cut and protect `streamlit-frozen`

F §6.1 and the ops spec's Freeze steps 1–3, for the one production app `liturgy-next`.

**Files:** none (results go into the runbook in Task 15)

- [ ] **Step 1 (agent): Confirm what the frozen branch will inherit**

Run as one command (shell variables do not carry between commands):

```bash
git fetch origin
sha=$(gh pr view claude/ops-3 -R bbrown62450/church --json mergeCommit -q .mergeCommit.oid)
gh pr view claude/ops-3 -R bbrown62450/church --json state -q .state
test "$(git rev-parse origin/main)" = "$sha" && echo "main is at the ops-3 merge $sha" || echo "main has moved past the ops-3 merge"
git show origin/main:docs/ops-runbook.md | awk '/^## Environments and variables$|^## Keep-alive$|^### What the frozen app inherits from ops-3$/{on=1} /^## Supabase lockdown record$|^## Streamlit freeze$|^## Platform limits$/{on=0} on && /\[owner/{print FNR": "$0}' | wc -l
git show origin/main:docs/ops-runbook.md | grep -c '^| D5 manual check passed.*| \[owner\] |$'
gh run list -R bbrown62450/church --workflow ci --commit "$sha" --event push --json conclusion -q '.[0].conclusion'
```

Expected: `MERGED`; `main is at the ops-3 merge <sha>`; `15` (the Keep-alive run row, eleven Freeze record rows and the three version lines; the Railway line and the first Freeze record row were filled in Task 11); `0` (the D5 manual check on `liturgy-next` is recorded as passed; if `1`, the owner runs it now, `docs/manual-verification.md` → Ops slice, before Step 4, and Task 15 records it); `success` (CI's push run for the merge commit itself, not merely the latest run on `main`). Stop and ask the owner if `main` has moved past the ops-3 merge (another PR merged despite Task 11, Step 6: `liturgy-next` has hot-pulled it, so the pre-freeze check would test a different commit from the one `streamlit-frozen` gets), or if CI for the merge commit is not `success`.

- [ ] **Step 2 (OWNER): Pre-freeze smoke check, recorded versions and app settings**

Streamlit Cloud → `liturgy-next` → Manage app: if it was not rebooted after the ops-3 merge (Task 11, Step 6), Reboot now. The logs show a build or reboot after the merge that finished. On https://liturgy-next.streamlit.app/: sign in, the church and hymnal load, load a saved service, open Settings, and confirm the sidebar shows no "Church" selectbox (the bug-triage row A7 relies on it). If anything fails, stop: do not send the "before" message and do not cut the branch.

From the same logs, copy the Python version and the dependency-install lines (`name==version`) into a note for the agent: the pre-freeze list that the pre-flight build is compared with (Task 14, Step 2). From ⋮ → Settings, note what a new app does not inherit: the Python version (3.13), the custom subdomain (`liturgy-next`), **Sharing** (public, or private with its viewer list; the repository is public, so a new app starts public) and any other setting that is not the default.

In ⋮ → Settings → Secrets, check that `DB_POOL_SIZE = "3"` and `DB_MAX_OVERFLOW = "3"` are top-level keys: at the very top of the Secrets, above the first `[section]` line (such as `[auth]`). A key below a `[section]` line belongs to that section, and Streamlit exports only top-level keys to the environment, so the engine would silently ignore it. Tell the agent only "present at the top", "moved to the top" or "missing", never the Secrets text. If they are missing or sit below a section, add or move them to the very top and save: without them the engine still uses the code defaults 3 and 3 (ops-2), but the runbook says the keys are set. Make sure the password-manager copy of the Secrets matches what is saved now.

- [ ] **Step 3 (OWNER): Schedule the window and send the "before" message**

Only after Step 2 passed. Pick a weekday window the tester agrees to, never Saturday or Sunday, and not at minute :23 of 00, 06, 12 or 18 UTC, when `keep-awake` runs (a run that hits the window fails once, harmlessly). Plan Task 14's pre-flight for 1–3 hours before the window, on the same day: it runs a third app against the pooler, so keep that overlap short. Send (exact copy, with the production address):

> Heads-up: on {weekday, date} between {start} and {end} I'm moving the planning app to a new setup. The address stays https://liturgy-next.streamlit.app. It may be unavailable for about 5 minutes. Please don't start a new service during that window — anything you've already saved is safe.

- [ ] **Step 4 (agent, on the owner's yes): Cut `streamlit-frozen` from the ops-3 merge commit**

```bash
git fetch origin
sha=$(gh pr view claude/ops-3 -R bbrown62450/church --json mergeCommit -q .mergeCommit.oid)
git merge-base --is-ancestor "$sha" origin/main && echo "on main"
git log -1 --format='%s' "$sha"
git ls-remote --exit-code origin refs/heads/streamlit-frozen; echo "ls-remote exit $?"
```

Expected: `on main`; `Merge pull request #<n> from bbrown62450/claude/ops-3`; `ls-remote exit 2` (the branch does not exist yet). Then push it (the first line derives the sha again, because shell variables do not carry over between commands):

```bash
sha=$(gh pr view claude/ops-3 -R bbrown62450/church --json mergeCommit -q .mergeCommit.oid)
git push origin "$sha:refs/heads/streamlit-frozen"
git ls-remote origin refs/heads/streamlit-frozen
```

Expected: `<sha>	refs/heads/streamlit-frozen`. (AC 20, first half.)

- [ ] **Step 5 (OWNER): Protect `streamlit-frozen`**

GitHub → `bbrown62450/church` → Settings → Branches → Add classic branch protection rule:
- Branch name pattern: `streamlit-frozen`;
- tick "Require a pull request before merging", and under it **untick "Require approvals"** (it comes ticked, with 1 approval). You are the only reviewer, and with no bypass a required approval would block your own data-safety fixes;
- tick "Require status checks to pass before merging", search for `backend` and select it (the `ci` workflow's job; it runs on every pull request, including PRs into `streamlit-frozen`);
- tick "Do not allow bypassing the above settings";
- leave "Allow force pushes" and "Allow deletions" unticked;
- Create.

Alternatively, run this yourself in a terminal where `gh` is signed in as you, or let the agent run it on your explicit yes (it changes repository settings):

```bash
gh api -X PUT repos/bbrown62450/church/branches/streamlit-frozen/protection --input - <<'JSON'
{
  "required_status_checks": {"strict": false, "contexts": ["backend"]},
  "enforce_admins": true,
  "required_pull_request_reviews": {"required_approving_review_count": 0},
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
```

- [ ] **Step 6 (agent): Verify the protection (read-only)**

```bash
gh api repos/bbrown62450/church/branches/streamlit-frozen/protection \
  --jq '"checks=\(.required_status_checks.contexts | join(",")) pr=\(.required_pull_request_reviews != null) approvals=\(.required_pull_request_reviews.required_approving_review_count) admins=\(.enforce_admins.enabled) force_push=\(.allow_force_pushes.enabled) deletion=\(.allow_deletions.enabled)"'
```

Expected: `checks=backend pr=true approvals=0 admins=true force_push=false deletion=false`. (AC 20, second half.) If `approvals` is not `0` or `admins` is not `true`, the owner fixes the rule (Step 5) and the agent checks again. If it answers `Branch not protected` (HTTP 404), the rule was created as a ruleset instead. Then check `gh api repos/bbrown62450/church/rules/branches/streamlit-frozen --jq '[.[].type] | sort | join(",")'`, which must include `deletion`, `non_fast_forward`, `pull_request` and `required_status_checks`, and `gh api repos/bbrown62450/church/rules/branches/streamlit-frozen --jq '.[] | select(.type == "pull_request") | .parameters.required_approving_review_count'`, which must print `0`; the owner confirms the ruleset's bypass list is empty (Settings → Rules → Rulesets).

---

### Task 14 (OWNER + agent): Freeze, part 2: pre-flight on a temporary subdomain, then move `liturgy-next` to `streamlit-frozen`

The ops spec's Freeze steps 4–6 for `liturgy-next` (clarification 17). Streamlit Community Cloud cannot change an existing app's repository, branch or main file, and allows only one app per repository + branch + main file. A deleted app's subdomain may not be free again right away (ops spec, Risks item 4), and a rollback from `main` needs the same subdomain. So the new app is built and checked on a temporary subdomain while `liturgy-next` keeps serving from `main`, and the window only moves the checked app onto the production address. Below, `liturgy-frozen` is the temporary subdomain; if Streamlit says it is taken, pick another (such as `liturgy-frozen-2`) and use it wherever `liturgy-frozen` appears, in this plan and in the runbook records.

**Files:** none (results go into the runbook in Task 15)

- [ ] **Step 1 (OWNER, 1–3 hours before the window): Pre-flight `streamlit-frozen` on `liturgy-frozen`**

1. In the password manager, create the entry "liturgy-frozen Streamlit Secrets (temporary)": a copy of the current `liturgy-next` Secrets with exactly two values changed, `[auth] redirect_uri = https://liturgy-frozen.streamlit.app/oauth2callback` and `GOOGLE_OAUTH_REDIRECT_URI = https://liturgy-frozen.streamlit.app/`. Everything else stays as it is, including `DB_POOL_SIZE = "3"` and `DB_MAX_OVERFLOW = "3"` at the top, so that moving the app later changes nothing but those two values.
2. share.streamlit.io → Create app → deploy from GitHub: repository `bbrown62450/church`, branch `streamlit-frozen`, main file path `app.py`, App URL (custom subdomain) `liturgy-frozen`. Advanced settings: Python 3.13, and paste the temporary Secrets from item 1. Deploy. (The one-app rule allows it: `liturgy-next` holds `main`/`app.py`, this app holds `streamlit-frozen`/`app.py`.) Then set ⋮ → Settings → Sharing to match `liturgy-next`'s (Task 13, Step 2).
3. Only now that the subdomain is yours (a URI for a subdomain nobody holds is the risk Task 11, Step 4 removed): Google Cloud Console → APIs & Services → Credentials → the OAuth 2.0 client "Liturgy" → Authorized redirect URIs → add `https://liturgy-frozen.streamlit.app/oauth2callback` and `https://liturgy-frozen.streamlit.app/` → Save. Google can take a few minutes to apply it.
4. Manage app → logs: the build from `streamlit-frozen` finished without a traceback. Copy its Python version and installed `name==version` lines for the agent (Step 2).
5. On https://liturgy-frozen.streamlit.app/: sign in, the church and hymnal load, load a saved service, open Settings, connect Gmail and send a test email to yourself. Use this app for nothing else. If Google answers `redirect_uri_mismatch`, it has not applied item 3 yet: wait a few minutes and retry.
6. ⋮ → Settings → General: look (without saving) whether the custom subdomain can be edited. That decides Step 3's path: A if it can, B if it cannot.

While this app exists, three apps share the pooler: worst case 3 × (3 + 3) + 2 = 20 > 15, reached only if every pool fills at once. Real use is 2–4 sessions per app, and only you use `liturgy-frozen`, so keep the overlap to these few hours and end it in the window.

**Path B only: the reclaim test.** If item 6 found the subdomain not editable, test now, before production is touched, whether a deleted app's subdomain is free again at once: delete the temporary app and immediately create it again exactly as in item 2 (the URIs from item 3 stay). If Streamlit accepts `liturgy-frozen`, repeat items 4–5 on the new app and continue. If it refuses it, a deleted subdomain is not free at once, and path B would put production at risk: do not start the window; remove the two `liturgy-frozen` URIs, send the "postponed" message below, and tell the agent. The Freeze then waits for a revised procedure, or the owner applies the Contingency (Task 16).

**If the pre-flight fails** (the build fails, or the smoke check fails and it is not the `redirect_uri_mismatch` wait): do not start the window. Remove its two redirect URIs, then delete the temporary app, and send the tester (exact copy):

> Change of plan: the move planned for {weekday, date} is postponed, so nothing changes. The address stays https://liturgy-next.streamlit.app. I'll let you know the new time.

Tell the agent what failed. If a dependency release is the cause (the build log or the traceback names a package whose version differs from the pre-freeze list), the agent prepares, on your yes, a pull request into `streamlit-frozen` that pins `requirements.txt` to the pre-freeze `name==version` list. It is a data-safety fix under the Freeze policy (it keeps the tester's access), it needs the green `backend` check, and you merge it. Then repeat this step before a new window, and send a new "before" message (Task 13, Step 3).

- [ ] **Step 2 (agent): Compare the pre-flight versions with the pre-freeze list**

The owner pastes both lists in chat (they are not secret): the pre-freeze list (Task 13, Step 2) and the pre-flight build's (Step 1, item 4). Write each into a file in the scratchpad, one `name==version` per line, then:

```bash
diff <(sort <scratch>/pre-freeze.txt) <(sort <scratch>/pre-flight.txt); echo "diff exit $?"
```

`diff exit 0` means the same versions. Otherwise the `<` and `>` lines are the differences; note them for the runbook's comparison line (Task 15) and show them to the owner. A difference alone does not stop the Freeze: the pre-flight smoke check ran on exactly these versions, and in path A this build becomes production unchanged. A failed pre-flight that points at a package in the diff is the pin case of Step 1.

- [ ] **Step 3 (OWNER, in the window): Move production to the checked build**

1. `liturgy-next` → ⋮ → Settings → Secrets: check that the password-manager entry "liturgy-next Streamlit Secrets" matches it exactly; update the entry, with today's date, if it does not. Never paste it into chat or the repo.
2. `liturgy-next` → ⋮ → Delete app, and confirm. The production address is down from here until item 4.

Path A (the subdomain is editable):

3. The temporary app → ⋮ → Settings → General → custom subdomain `liturgy-next` → Save. If Streamlit says it is not available, retry every few minutes for up to 15 minutes; if it is still refused, go to **Fallback** below. The app stays on `liturgy-frozen` meanwhile.
4. The same app → ⋮ → Settings → Secrets: replace the whole text with the `liturgy-next` entry from item 1, unchanged (it differs from the temporary Secrets only in the two redirect values) → Save. Allow a minute for it to apply. This app is the pre-flight build: no reinstall.

Path B (the subdomain is not editable, and the reclaim test passed):

3. The temporary app → ⋮ → Delete app: the one-app rule needs `streamlit-frozen` / `app.py` free for the new app.
4. Create app: repository `bbrown62450/church`, branch `streamlit-frozen`, main file `app.py`, custom subdomain `liturgy-next`; Advanced settings: Python 3.13 and the `liturgy-next` Secrets from item 1, unchanged. Deploy, then set ⋮ → Settings → Sharing as noted in Task 13, Step 2. This build is a fresh install: copy its Python and `name==version` lines for the agent, who compares them with the pre-flight list as in Step 2; production runs this build. If `liturgy-next` is refused for 15 minutes, create the app with subdomain `liturgy-frozen` and the temporary Secrets instead (the reclaim test showed it comes back) and go to **Fallback**.

The URL is unchanged, so the `liturgy-next` redirect URIs, which stayed registered, are valid. The tester's session cookie resets, so they sign in once.

**Fallback: `liturgy-next` stays refused.** Production serves from the checked frozen app on https://liturgy-frozen.streamlit.app: its temporary Secrets and its two registered redirect URIs make sign-in and Gmail work there, and its pool keys are the production 3 and 3 (`liturgy-next`'s pool is gone). Then:
1. Run Step 4's checks on https://liturgy-frozen.streamlit.app/ instead, and skip its "retire" item.
2. Send the tester (exact copy, instead of Step 6's message):

   > The move took longer than planned. For now the planning app is at https://liturgy-frozen.streamlit.app — please sign in there; your church and saved services are all there. I'll tell you when it's back at https://liturgy-next.streamlit.app.

3. Tell the agent. Records PR A (Task 15) then records the Fallback and points `keep-awake` at https://liturgy-frozen.streamlit.app/. Skip Step 5 until that PR has merged (until then `keep-awake` visits the missing `liturgy-next` and fails).
4. Retry once a day at a quiet time. Path A: items 3–4 on the app. Path B: delete the `liturgy-frozen` app and create it on `liturgy-next` (path B, item 4), going back to `liturgy-frozen` if refused. If `liturgy-next` is still refused after 7 days, remove its two redirect URIs from the Google client (nobody holds that subdomain: the risk of Task 11, Step 4), and add them back as soon as the app holds it again (then wait a few minutes before the smoke check).
5. When the app is on `liturgy-next` again: run Step 4 there, send Step 6's "after" message, and have the agent, in one PR, point `keep-awake` and `PRODUCTION_STREAMLIT_URL` back at https://liturgy-next.streamlit.app/ and record the date in the runbook (Streamlit apps: Task 15's success row replaces the two Fallback rows; Freeze record: a dated line under the table).

**Rollback to `main`.** Only if the frozen app on `liturgy-next` fails Step 4's checks and cannot be fixed before the window ends. First compare its Secrets once more with the password-manager entry and fix them in ⋮ → Settings → Secrets: the build itself passed the pre-flight, and in path A only the two redirect values changed. If it still fails: delete it and create the app from branch `main`, main file `app.py`, subdomain `liturgy-next`, Python 3.13, the same Secrets and Sharing. That is the state before the Freeze (nothing else holds `main` / `app.py`). If `liturgy-next` is refused for 15 minutes, use `liturgy-frozen` with the temporary Secrets for that app instead (its URIs are still registered) and send the Fallback message; if both are refused, tell the agent at once. Verify sign-in, the church and hymnal, and a saved service, send the "after" message (or the Fallback one), stop, and tell the agent: the fallback is the Contingency (Task 16).

- [ ] **Step 4 (OWNER): Verify the frozen app, then retire the temporary subdomain**

- Manage app → logs: no traceback since the move (path B: the build from `streamlit-frozen` finished).
- ⋮ → Settings shows branch `streamlit-frozen`, main file `app.py`, Python 3.13, and the Sharing noted in Task 13, Step 2 (set it again if it differs).
- On https://liturgy-next.streamlit.app/: sign in, the church and hymnal load, load a saved service, open Settings, connect Gmail and send a test email to yourself. The Gmail check exercises the re-entered `GOOGLE_*` Secrets and `GOOGLE_OAUTH_REDIRECT_URI`. If sign-in or the Gmail connect goes to `liturgy-frozen`, the pasted Secrets have not applied yet: wait a minute and retry, then Manage app → Reboot once (a reboot reinstalls the requirements, so copy that build's versions for the agent). (AC 21.)
- Retire the temporary subdomain, right after these checks: no app holds `liturgy-frozen` any more (path A renamed the app, path B deleted it), so Google Cloud Console → the client "Liturgy" → remove `https://liturgy-frozen.streamlit.app/oauth2callback` and `https://liturgy-frozen.streamlit.app/` → Save. The list is back to the two `liturgy-next` URIs. Delete the "liturgy-frozen Streamlit Secrets (temporary)" password-manager entry.

- [ ] **Step 5 (agent, on the owner's yes): Run keep-awake by hand**

```bash
gh workflow run keep-awake --ref main -R bbrown62450/church
gh run list --workflow keep-awake --limit 1 -R bbrown62450/church --json databaseId,createdAt,status
```

The new run takes a few seconds to appear: if the listed run was created before the dispatch, run the `gh run list` line again (no `sleep`). Then, with its `databaseId`:

```bash
gh run watch <run-id> --exit-status -R bbrown62450/church
gh run view <run-id> --log -R bbrown62450/church | grep -E '(visited|FAILED) https://'
```

Expected: the run succeeds, and the grep prints exactly one line, ending in `visited https://liturgy-next.streamlit.app/`. (The pattern needs `https://` so that it skips the echoed script, whose lines read `visited {url}`.) Under the Fallback, run this only after Records PR A merged, and expect `visited https://liturgy-frozen.streamlit.app/`. (AC 22.)

- [ ] **Step 6 (OWNER): Send the "after" message (exact copy)**

> All done — the app is back at the same address. Please sign in once and let me know if anything looks different.

(Under the Fallback, the Fallback message replaces it.)

- [ ] **Step 7 (OWNER): Give the agent the results**

For Task 15, the agent needs: the dates of Tasks 13–14; the window; the merge sha and the protection check; the pre-flight result (subdomain used, build, smoke with Gmail, path A or B, the reclaim test if run) and Step 2's comparison; which of these happened: path A, path B, the Fallback or the rollback to `main`, with the minutes of downtime; Step 4's results, including Sharing, Gmail and whether a reboot was needed (and then that build's versions); whether the `liturgy-frozen` URIs were removed; the keep-awake run URL; the date the "after" (or Fallback) message was sent; and, from Task 13, Step 2, the pool-key answer and (if it was open) the D5 manual check result.

---

### Task 15 (agent + OWNER): Freeze records

Two small docs-only PRs (clarification 13). Merging PR A is itself "the next merge to `main`", so PR B records whether the frozen app pulled it. After a rollback to `main` there is only PR A, and Task 16 follows. Under the Fallback (Task 14), PR A also points `keep-awake` at the temporary URL.

**Files:**
- Modify: `docs/ops-runbook.md`
- Modify (Fallback only): `.github/workflows/keep-awake.yml` (line 24, `APP_URLS`), `backend/tests/test_ops_workflows.py` (`PRODUCTION_STREAMLIT_URL`)

- [ ] **Step 1 (agent): Records PR A: everything except the last Freeze record row**

```bash
git fetch origin
git switch -c claude/ops-3-freeze-records origin/main
```

In `docs/ops-runbook.md`, fill in the owner's values from Tasks 12–14:

1. `## Keep-alive` → the run-record row: the date, the run URL, and `green; the log shows {"ok":true,"db":"ok"}`.
2. `### Freeze record`: the Result and Date of every open row **except** the last one ("After the next merge to `main` (records PR A) …"); the first row was filled in Task 11. The `streamlit-frozen` row gets the merge commit sha. The pre-flight row names the path (A or B) and the reclaim test, if it ran. The window row says how the app reached `liturgy-next` (path A: the checked app moved onto the subdomain; path B: recreated there) and the minutes of downtime.
3. `### Recorded Python and package versions`: the Python version and the `name==version` lines of the build production runs (path A: the pre-flight build; path B: the window's build; after a Task 14, Step 4 reboot: that build), and the comparison line: `same`, or the differences from Task 14, Step 2 (and from the later comparison, if path B or a reboot made one).
4. `### Streamlit apps`: replace the whole `liturgy-next` row (the line that starts with ``| `liturgy-next` |``) with the row below; the `liturgy` row stays.

```markdown
| `liturgy-next` | https://liturgy-next.streamlit.app/ | **Production.** The owner and the tester use it. Since <freeze date> it serves repo `bbrown62450/church`, branch `streamlit-frozen`, main file `app.py`, Python 3.13, Sharing <as before>: Streamlit Cloud cannot change an app's branch, so an app from `streamlit-frozen` was checked on the temporary subdomain `liturgy-frozen` and then <moved onto | recreated under> this subdomain with the same Secrets (see Freeze record). Merges to `main` no longer reach it. From 2026-09-26 until then it deployed from `main` (`liturgy-stg` was deleted that day during ops-1's Task 9a). Its Secrets carry `[auth] redirect_uri = https://liturgy-next.streamlit.app/oauth2callback` and `GOOGLE_OAUTH_REDIRECT_URI = https://liturgy-next.streamlit.app/`, both registered on the Google OAuth client "Liturgy". `keep-awake` keeps it awake. |
```

5. `## Platform limits`: replace the bullet that starts "Values set:" (Task 7's wording) with:

```markdown
- Values set: `DB_POOL_SIZE=3` and `DB_MAX_OVERFLOW=3` as Railway service
  variables (API), and as top-level keys `DB_POOL_SIZE = "3"` and
  `DB_MAX_OVERFLOW = "3"` in the production Streamlit Secrets, at the very top
  above the first `[section]` line (a key below `[auth]` belongs to that
  section, and Streamlit does not export it to the environment): set in
  `liturgy-stg`'s on 2026-09-26; <present at the top | moved to the top | added>
  in `liturgy-next`'s on <date> (Freeze, Task 13) and carried unchanged into
  the app that serves it from `streamlit-frozen`.
```

6. If Task 13, Step 1 found the D5 manual check open: its row in "D5 fix and recovery record", with the owner's result and date.

Replace every `<…>` with the real values.

**If Task 14 rolled back to `main`:** in item 4, keep the current `liturgy-next` row and add at its end "Freeze attempted on <date>; rolled back to `main` (see Contingency)." Write `not done: rolled back to main` in every Freeze record row that did not happen, **including the last one** (the app follows `main` again, so there is no "next merge" check), and in the three version lines. In item 5, the bullet's last words "and carried unchanged into the app that serves it from `streamlit-frozen`." become "and carried unchanged into the app recreated from `main`."

**Under the Fallback:** item 4 replaces the `liturgy-next` row with these two rows instead:

```markdown
| `liturgy-next` | https://liturgy-next.streamlit.app/ | **Production address, not reclaimed yet.** Since <date> production Streamlit serves from `liturgy-frozen` (see the next row) because Streamlit Cloud refused this subdomain after the old app was deleted. The Freeze retries daily (plan Task 14, Fallback). Its two redirect URIs stay registered on the Google OAuth client "Liturgy" while the retries run. |
| `liturgy-frozen` | https://liturgy-frozen.streamlit.app/ | **Production (Fallback).** Repo `bbrown62450/church`, branch `streamlit-frozen`, main file `app.py`, Python 3.13, Sharing <as before>. Its Secrets are the `liturgy-next` ones with `redirect_uri` and `GOOGLE_OAUTH_REDIRECT_URI` pointing at `https://liturgy-frozen.streamlit.app/oauth2callback` and `https://liturgy-frozen.streamlit.app/`, both registered on the Google OAuth client. `keep-awake` visits it. Merges to `main` do not reach it. |
```

In the Freeze record, the post-freeze smoke row gets the results on `liturgy-frozen`, the "Temporary subdomain retired" row gets `not done: Fallback (production on liturgy-frozen)`, and the `keep-awake` row and the last row stay open for PR B. In item 5, the bullet's last words "into the app that serves it from `streamlit-frozen`." become "into the app that serves production from `streamlit-frozen` on `liturgy-frozen`." Then point `keep-awake` at the app that serves: in `.github/workflows/keep-awake.yml`, line 24, `APP_URLS: "https://liturgy-next.streamlit.app/"` becomes `APP_URLS: "https://liturgy-frozen.streamlit.app/"`; in `backend/tests/test_ops_workflows.py`, `PRODUCTION_STREAMLIT_URL = "https://liturgy-next.streamlit.app/"` becomes `PRODUCTION_STREAMLIT_URL = "https://liturgy-frozen.streamlit.app/"   # Fallback since <date>: liturgy-next not reclaimed yet`.

Then:

```bash
awk '/^## Environments and variables$|^## Keep-alive$|^### What the frozen app inherits from ops-3$/{on=1} /^## Supabase lockdown record$|^## Streamlit freeze$|^## Platform limits$/{on=0} on && /\[owner/{print FNR": "$0}' docs/ops-runbook.md
.venv/bin/python -m pytest -q | tail -1
git add docs/ops-runbook.md
git commit -m "Runbook: Streamlit freeze record (liturgy-next on streamlit-frozen), keepalive run

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

After a rollback, use the subject "Runbook: Streamlit freeze attempted, rolled back to main; keepalive run". Under the Fallback, also `git add .github/workflows/keep-awake.yml backend/tests/test_ops_workflows.py` and use the subject "Runbook: Streamlit freeze on liturgy-frozen (Fallback); keep-awake follows it".

Expected: the awk prints exactly one line, the last Freeze record row (after a rollback: nothing; under the Fallback: two lines, the `keep-awake` row and the last row); `559 passed`.

- [ ] **Step 2 (agent, on the owner's yes): Push and open records PR A**

Pushing a new branch and opening a PR are outward-facing: ask the owner first.

```bash
git push -u origin claude/ops-3-freeze-records
gh pr create --base main --head claude/ops-3-freeze-records \
  --title "Runbook: Streamlit freeze record" \
  --body "Records the ops-3 after-merge checks and the Streamlit freeze: streamlit-frozen cut at the ops-3 merge commit and protected; an app from it checked on the temporary subdomain liturgy-frozen, then moved onto liturgy-next (production) with the same Secrets; the temporary subdomain and its redirect URIs retired; keepalive and keep-awake runs are green; Python and package versions recorded. Merging this PR is the 'next merge to main' whose (absent) code pull on liturgy-next the follow-up records.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```

After a rollback, use the title "Runbook: Streamlit freeze attempted, rolled back to main" and the body "Records the ops-3 after-merge checks and the attempted Streamlit freeze: streamlit-frozen was cut at the ops-3 merge commit and protected, but liturgy-next could not run from it and was recreated from main with the same Secrets (see docs/ops-runbook.md → Freeze record). The keepalive run is green. The Freeze contingency PR follows (F §6.1 item 6).", plus the same last line. Under the Fallback, use the title "Runbook: Streamlit freeze on liturgy-frozen (Fallback); keep-awake follows it" and the body "Records the ops-3 after-merge checks and the Streamlit freeze: streamlit-frozen cut at the ops-3 merge commit and protected; the app from it passed its checks on liturgy-frozen, but Streamlit Cloud refused the liturgy-next subdomain after the old app was deleted, so production serves from https://liturgy-frozen.streamlit.app until liturgy-next can be reclaimed. keep-awake now visits that URL (the test constant follows). Merging this PR is the 'next merge to main' whose (absent) code pull the follow-up records.", plus the same last line.

Merge on the owner's explicit yes (`gh pr merge --merge claude/ops-3-freeze-records`), and note the merge time. After a rollback, `liturgy-next` follows `main` again: the owner reboots it after this merge and runs the smoke check (runbook → Contingency, item 5), and the agent continues with Task 16 instead of Steps 3–5. Under the Fallback, run Task 14, Step 5 now (expecting `visited https://liturgy-frozen.streamlit.app/`).

- [ ] **Step 3 (OWNER): Check that the merge did not reach the frozen app**

About 5 minutes after PR A merges: Streamlit Cloud → `liturgy-next` (under the Fallback: the `liturgy-frozen` app) → Manage app → logs. A new commit on the branch an app tracks does not show as a fresh build: it shows as a code pull, typically `Pulling code changes from Github` followed by `Updated app!`. After PR A's merge time there must be no such line and no build or restart. Then ⋮ → Settings must still show branch `streamlit-frozen`, and the app still loads. Tell the agent the result, the merge time and the date. (AC 21.) If a pull shows up, the app follows `main`: stop and check its branch setting (Task 14, Step 4).

- [ ] **Step 4 (agent): Records PR B: the last row**

```bash
git fetch origin
git switch -c claude/ops-3-freeze-records-2 origin/main
```

Fill the last Freeze record row with "PR #<A's number> merged <date/time>; no code pull (`Pulling code changes from Github`, `Updated app!`) in `liturgy-next`'s logs after it; Settings still shows `streamlit-frozen`" and the date. Under the Fallback, name the `liturgy-frozen` app instead, and also fill the `keep-awake` row with the run from Task 14, Step 5. Then:

```bash
awk '/^## Environments and variables$|^## Keep-alive$|^### What the frozen app inherits from ops-3$/{on=1} /^## Supabase lockdown record$|^## Streamlit freeze$|^## Platform limits$/{on=0} on && /\[owner/{print FNR": "$0}' docs/ops-runbook.md | wc -l
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked'
.venv/bin/python -m pytest -q | tail -1
git add docs/ops-runbook.md
git commit -m "Runbook: merges to main no longer reach liturgy-next (freeze verified)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `0` (every ops-3 marker is filled); the whole-runbook grep lists only ops-1 markers the owner may still owe (the `age` key's password-manager entry, the restore drill, the D5 "fixed" message and recovery result); `559 passed`. Under the Fallback, name `liturgy-frozen` in the subject.

- [ ] **Step 5 (agent, on the owner's yes): Push and open records PR B**

```bash
git push -u origin claude/ops-3-freeze-records-2
gh pr create --base main --head claude/ops-3-freeze-records-2 \
  --title "Runbook: freeze verified" \
  --body "Records that merging the freeze-records PR did not reach the production Streamlit app (no code pull in its logs; its settings still show streamlit-frozen), so production Streamlit is frozen on streamlit-frozen.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```

Merge on the owner's yes. The ops slice's acceptance criteria 20 and 21 are then met, and AC 22 is met if the Freeze record's first row says the four old redirect URIs were removed; if the owner declined, AC 22 stays unmet and that row records the accepted risk. Under the Fallback, AC 21 is met for the production app on `liturgy-frozen`, and for `liturgy-next` once Task 14's Fallback item 5 brings it back. Slice work can start on `main`. The ops slice as a whole is done when that whole-runbook grep is empty too (AC 23: every "Ops slice" check run and recorded).

---

### Task 16 (only if Task 14 rolled `liturgy-next` back to `main`): Contingency

F §6.1 item 6 and the ops spec's Freeze step 8, with the §6.2 amendment of 2026-09-26 (clarification 18). Skip this task when Task 14 succeeded.

**Files:**
- Modify: `app.py:2` (remove the FROZEN line)
- Create: `streamlit_tests/test_app_smoke.py`
- Modify: `backend/tests/test_ops_workflows.py` (replace `test_app_py_carries_the_frozen_header`)
- Modify: `docs/ops-runbook.md` → `### Contingency` (the Freeze record rows already say `not done: rolled back to main`, Task 15)

**Interfaces:**
- Consumes: `FROZEN_HEADER`, `ROOT` and `_read` from `test_ops_workflows.py` (Task 8); the `tmp_db` fixture (re-exported by `streamlit_tests/conftest.py`); `streamlit.testing.v1.AppTest`.
- Produces: a green `AppTest` run of `app.py` signed out, which every later PR must keep green. It covers only the signed-out page; the signed-in pages rely on the reboot and smoke check after every merge to `main` (runbook → Contingency, items 3 and 5), an accepted limit (clarification 15). Later slices then apply their own contingency shims (slice 1 invites, slice 2 lectionary shim, slice 3 hymn wrappers, slice 4's `generate_liturgy` wrapper with `LEGACY_SYSTEM_PROMPT` and `legacy_default_prompts()`, slice 5b's Gmail wrappers); ops-3 writes none of them.

- [ ] **Step 1: Write the failing test**

```bash
git fetch origin
git switch -c claude/ops-3-freeze-contingency origin/main
```

In `backend/tests/test_ops_workflows.py`, replace:

```python
def test_app_py_carries_the_frozen_header():
    lines = _read(ROOT / "app.py").splitlines()
    first = lines[1] if lines[0].startswith("#!") else lines[0]   # the line after the shebang
    assert first == FROZEN_HEADER
```

with:

```python
def test_app_py_has_no_frozen_header_while_production_runs_from_main():
    # Freeze contingency (docs/ops-runbook.md → Streamlit freeze → Contingency):
    # liturgy-next still deploys from main, so app.py must not claim to be frozen.
    assert FROZEN_HEADER not in _read(ROOT / "app.py")
```

Run: `.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py -k frozen_header`
Expected: `1 failed, 79 deselected` (`assert '# FROZEN — … in slice 7.' not in '#!/usr/bin/…'`).

- [ ] **Step 2: Remove the header**

Delete line 2 of `app.py` (`# FROZEN — production runs from branch streamlit-frozen; deleted in slice 7.`), so the file starts with the shebang and then the docstring, as before ops-3.

Run: `.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py -k frozen_header`
Expected: `1 passed, 79 deselected`.

- [ ] **Step 3: Add the `AppTest` smoke test**

Create `streamlit_tests/test_app_smoke.py`:

```python
"""Freeze contingency (ops spec, Freeze step 8; F §6.1 item 6): app.py must keep
working against main, because production Streamlit could not move to
streamlit-frozen."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app.py"


def test_app_py_runs_signed_out(tmp_db):
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()
    assert not at.exception
    assert [b.label for b in at.button] == ["Sign in with Google"]
```

Run: `.venv/bin/python -m pytest -q streamlit_tests/test_app_smoke.py`
Expected: `1 passed` (checked on 2026-09-26 against this branch with the header removed: the signed-out page renders one "Sign in with Google" button in under a second). It passes at once: it is a guard against later PRs breaking `app.py` on `main`. It does not reach the functions `app.py` calls after sign-in; the runbook's Contingency records that limit (item 3) and the manual smoke check after every merge that covers it (item 5).

- [ ] **Step 4: Record the contingency and commit**

In `docs/ops-runbook.md` → `### Contingency`, add a line at the end: "Applied on <date>: <why the app from `streamlit-frozen` could not serve `liturgy-next`>. `liturgy-next` stays on `main`, with the old season wording and no prayer library (item 4), and is rebooted and smoke-checked after every merge (item 5); the Freeze policy above does not apply until a later freeze succeeds." The Freeze record rows that did not happen already say `not done: rolled back to main` (Task 15, Step 1); leave them.

```bash
.venv/bin/python -m pytest -q | tail -1
git add app.py streamlit_tests/test_app_smoke.py backend/tests/test_ops_workflows.py docs/ops-runbook.md
git commit -m "Freeze contingency: liturgy-next stays on main; AppTest smoke for app.py (F §6.1 item 6)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `560 passed`.

- [ ] **Step 5 (agent, on the owner's yes): Push and open the contingency PR**

Pushing a new branch and opening a PR are outward-facing: ask the owner first.

```bash
git push -u origin claude/ops-3-freeze-contingency
gh pr create --base main --head claude/ops-3-freeze-contingency \
  --title "Freeze contingency: keep app.py working on main" \
  --body "liturgy-next could not be served from streamlit-frozen and was rolled back to main (see docs/ops-runbook.md → Contingency), so it keeps deploying from main. The FROZEN header is removed, and an AppTest smoke test keeps app.py working against main (F §6.1 item 6). Streamlit still gets no new features: it keeps the old season wording and never reads prayer_library (F §6.2, amendment 2026-09-26).

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```

Merge on the owner's yes. Right after the merge, reboot `liturgy-next` (Manage app → Reboot), because the merge reaches it, and run the smoke check (runbook → Contingency, item 5).

---

## Spec coverage

| Spec item / acceptance criterion (ops-3 and Freeze share) | Task |
|---|---|
| S9 `RequestIdMiddleware`: inbound id kept if `^[A-Za-z0-9-]{8,64}$`, else `uuid4().hex`; contextvar (threadpool sees it); `X-Request-Id` on `http.response.start`; reset in `finally`; non-`http` scopes pass through | 1 |
| S13 / F §1.5: `request_id` in every error body (`_body`), equal to the header; `error_body` alias; the fallback outside the middleware | 1, 2 |
| S9 `UnhandledErrorMiddleware` (pure ASGI): logs method and path (never the query) with the stack; 500 `internal_error` if not started; re-raises if started; no exception text to the client; F §7.3 row 1 | 2 |
| Middleware order in `create_app()` (UnhandledError, RequestId, CORS added in that order; `user_middleware` = CORS, RequestId, UnhandledError); `@app.exception_handler(Exception)` kept as the last resort; `/me`, `/church`, `/rubric` and the identity cache stay green | 2 |
| S9 CORS lists (F §1.10): six allowed headers, three exposed headers, `max_age=600`, credentials off | 3 |
| S11 `FastAPI(redirect_slashes=False)`: `GET /me/` and `/health/` → 404 `not_found`, no `location` | 3 |
| Logging (F §2.5): record factory installed once, `request_id` or `-`, format `name level request_id=… message`, `configure_logging` replaces the inline `basicConfig`, `LOG_LEVEL` invalid → WARNING copy and INFO | 4 |
| S10 settings: `Settings.log_level`, `Settings.app_env` (stripped, lower-cased, default `development`), `is_production`; validation in the lifespan, not in `get_settings` | 4, 5 |
| S10 startup (F §2.6 items 1–2): `describe_database` (no credentials), `check_app_env`, `enforce_production_guards` (raise on non-PostgreSQL before `init_db`; ERROR for localhost-only CORS); the lifespan order; `SUPABASE_URL` warning unchanged | 5 |
| S3 `db/health.py`: `database_ready` memoized 10 s / 5 s, single-flight lock, `SET LOCAL statement_timeout = '5s'` on Postgres, `SELECT 1`, WARNING names only the exception class, `reset_readiness_for_tests`; no FastAPI import | 6 |
| S3 `GET /health/ready`: public, sync `def`, `ReadyOut` (`ok: bool`, `db: Literal["ok"]`) at the top of `api/routes/health.py`, no SQL or `try` in the route, 503 via `db_unavailable()`; recorded F §2.2 exception; `/health` unchanged | 6 |
| Error code registry: `db_unavailable` (503) in `api/errors.py`; the inert `errors.ts` check in `test_foundation_setup.py` ("the last item in ops-3") | 6 |
| Testing → conftest: autouse `reset_readiness_for_tests()` before each test | 6 |
| S3 `keepalive.yml` rewritten exactly as specified (no secret, `permissions: {}`, `vars.API_BASE_URL`, `curl --fail-with-body … /health/ready`, missing-variable copy); `backend/keepalive.py` deleted; `test_keepalive.py` → `test_ops_workflows.py` (inv H4) | 7 |
| S15: README → Operations "Keep-alive" (`/health/ready` curl, `API_BASE_URL`, no secret); runbook "Keep-alive" section | 7 |
| S7 on `main`: `app.py` FROZEN header; `keep-awake.yml` production-only (already https://liturgy-next.streamlit.app/ on `main`; guarded by a test) | 8 |
| S15: `docs/ops-runbook.md` with the seven sections (environments; lockdown; backups; keep-alive; Streamlit freeze with record, policy, triage, D5 result, versions, contingency; platform limits with the Pool Size and pool values; incident response) | 7, 9 (sections), ops-1/ops-2 (the rest) |
| S15: `docs/manual-verification.md` "## Ops slice", for `liturgy-next` | 9 |
| Testing → `test_middleware.py`: generated 32-hex id; echo; `bad id!`, 7-char and 65-char replaced; 404/401/422 (and 405) bodies' `request_id` == header; CORS on 500 for allowed and other origins; response-already-started unit test; log record from a sync route; `-` outside a request; no nested factories; `LOG_LEVEL=verbose`; `/health/` 404 with no `location`; preflight six headers and `max-age` 600; expose headers; middleware order | 1, 2, 3, 4 |
| Testing → `test_api_app.py::test_unhandled_exception_is_a_generic_500`: `code`, `message`, 32-hex `request_id` == header, no "secret detail" | 1, 2 |
| Testing → `test_startup.py`: `describe_database` without credentials; lifespan logs `Database: dialect=sqlite driver=pysqlite`; production + SQLite raises the exact copy and the `init_db` spy is not called; `APP_ENV=staging` raises; `" Production "` accepted; localhost-only CORS ERROR, Vercel origin none (engine `postgresql://u:p@localhost:1/db`, `init_db` stubbed); development on SQLite has no ERROR; the `SUPABASE_URL` test still passes | 5 |
| Testing → `test_health_ready.py`: 200 without auth and with junk headers; 503 body with `request_id` and a class-only WARNING; sync `def`; memo 9 s / 11 s and 5 s / 6 s; 16 threads → one probe; no `sqlalchemy` import in the route | 6 |
| Testing → `test_ops_workflows.py` (ops-3 part): `keepalive.yml` contains / does not contain; `keep-awake.yml` production only (`liturgy-next`) | 7, 8 |
| Exact server messages: `/health/ready` 503; any 500; invalid `APP_ENV`; production non-Postgres; localhost CORS; `Database:` INFO; invalid `LOG_LEVEL`; `keepalive.yml` missing variable | 2, 4, 5, 6, 7 |
| User experience → Browser: `X-Request-Id` readable, `request_id` in bodies, readable 500s, slice-0 messages unchanged; Owner: Railway log lines, keepalive green | 1–4, 12 |
| AC 4 Readiness (200 no auth; 503 `db_unavailable` with `request_id`; memo; one probe; no SQL in the route) | 6, 12 |
| AC 5 Keep-alive (no secret; curls `${API_BASE_URL}/health/ready`; manual run green; `keepalive.py` gone) | 7, 11 (Step 3), 12 |
| AC 9 CORS-safe 500s | 2 |
| AC 10 Request ids (every response inside the app incl. 404, 401, 422, 500; preflight and `ServerErrorMiddleware` excluded; echo and replace; body == header; log record from a sync route) | 1, 2, 3, 4 |
| AC 11 Routing and CORS | 3, 12 |
| AC 16 Startup | 5 |
| AC 18 Railway: `APP_ENV=production` set and confirmed in effect on the Active deployment; Healthcheck Path `/health` confirmed (clarification 22); deploy log shows the pooler host, no credentials, no CORS ERROR; manual rollback named | 11, 12 |
| AC 19 Railway limit recorded (ops-1, from Step 0): confirmed present | 10 (Step 1) |
| AC 20 Branch: `streamlit-frozen` at the ops-3 merge commit (`main` still there), protected (PR with 0 approvals, `backend` check, no bypass, no force push, no deletion) | 13 |
| AC 21 Frozen app: `liturgy-next` serves from `streamlit-frozen` at https://liturgy-next.streamlit.app/; smoke passes (including Gmail); Settings show `streamlit-frozen`; a later merge causes no code pull (`Pulling code changes from Github` / `Updated app!`) and the branch setting still reads `streamlit-frozen` | 14, 15 |
| AC 22 (adapted) Second app gone: `liturgy` and `liturgy-stg` already deleted on 2026-09-26, their four redirect URIs removed before the Freeze (mandatory; if declined, an accepted risk and AC 22 unmet); `keep-awake` pings only production and its run is green; `app.py` carries the FROZEN header | 8, 11 (Step 4), 14, 15 |
| AC 23 Docs: runbook sections filled; README Operations updated; "Ops slice" checklist run on production URLs (results in the runbook) | 7, 9, 11, 15 |
| AC 24 CI green on the ops-3 PR (`backend`, `backend-postgres`, `frontend`) | 10 |
| AC 26 No `backend/cache.py` or `test_cache.py` | 10 (Step 1) |
| Behavior changes 4, 5, 6, 7, 8, 10, 11, 14, 18 | 2; 1, 4; 3; 3; 5; 6; 7; 13–15; 6 |
| Delivery plan gate after ops-2 (the tester used Streamlit from `main` for a day, nothing regressed): recorded before the ops-3 merge | 11 (Step 1) |
| Delivery plan gate: `APP_ENV=production` on Railway before merging | 11 |
| Delivery plan gate: set `API_BASE_URL` (before merging, clarification 20) and run keepalive after merging | 11 (Step 3), 12 |
| Freeze step 1: before the freeze, CI green for the merge commit and `main` still at it; D5 manual check passed; reboot and short smoke after the merge; no merges to `main` until the Freeze is done; smoke check including no "Church" selectbox; Python, package versions and app settings (Sharing) recorded; the pool keys at the top of the Secrets | 11 (Step 6), 13, 15 |
| Freeze steps 2–3: cut from the ops-3 merge commit; protect | 13 |
| Freeze steps 4–6 (for `liturgy-next`): tester "before" message (about 5 minutes) after the pre-freeze check; since Streamlit Cloud cannot switch an app's branch: a pre-flight app from `streamlit-frozen` on a temporary subdomain with its own redirect URIs, full smoke check and version comparison, then in the window delete `liturgy-next` and move the checked app onto its subdomain with the same Python 3.13, Secrets (including `DB_POOL_SIZE`/`DB_MAX_OVERFLOW`) and Sharing (path B with a reclaim test if the subdomain is not editable); Fallback URL if `liturgy-next` stays refused; rollback to `main`; removal of the deleted apps' redirect URIs (before the Freeze) and of the temporary ones (after it); verify with Gmail; "after" message | 11 (Step 4), 13, 14, 15 |
| Risks item 4 (the subdomain may not be reclaimable at once): nothing production-facing depends on a deleted subdomain coming back; the Fallback serves on the temporary subdomain, with Google, Secrets, tester-message and `keep-awake` steps | 14, 15 |
| Risks item 5 (dependency drift): the pre-flight build's versions compared with the pre-freeze list before production is touched; a pin PR into `streamlit-frozen` if the pre-flight fails on a dependency; path A puts the checked build into production without a reinstall; the production build's versions recorded | 13, 14, 15 |
| Freeze step 7: policy recorded in the runbook (incl. reboot after fixes reach the app) | 9 |
| Freeze step 8: contingency (revert the header, keep `app.py` working on `main`, `AppTest` smoke, record; old season wording and no prayer library per F §6.1 item 6 / §6.2) | 9 (runbook and its test), 16 |
| "What the frozen app inherits": verified before the cut (rubric, D5, ops-2, CI on the merge commit, ops-3 touches only a comment in Streamlit-run code) | 9, 10 (Step 2), 13 (Step 1) |
| Streamlit coupling and layering: no Streamlit under `backend/`; `db/health` imports no FastAPI; `db/` imports no `api/` | 6, 10 |
| Data access: `/health/ready` touches no table; no church-scoped route added | 6 |
| Step 0 done (Data API already off, no incident): nothing re-asked; records already in the runbook; the "Ops slice" item only confirms them | Global Constraints, 1 (Step 1), 9 (Step 6), 10 |
| Pool Size 15, 3 + 3, 14 ≤ 15: unchanged by ops-3; checked on Railway and at the top of `liturgy-next`'s Secrets; carried into the frozen app; the pre-flight's third pool kept to a few hours; recorded in the environments table and the "Values set" bullet | 7, 9, 11, 13, 14, 15 |

**Deliberately not in ops-3** (ops spec delivery plan and the facts of 2026-09-26):
- Already on `main`: ops-1 and ops-2 work (`backup.yml`, the `age` key and recipients, the D5 fix, the dead modules, `.env.example`, `shadcn`, `insert_ignore`, `ensure_user`, the identity cache, the pool code, the `backend-postgres` CI job), the rubric (PR #4), `keep-awake.yml` visiting only `liturgy-next`, and the deletion of `liturgy` and `liturgy-stg`.
- New app only, never Streamlit: the prayer library (PR #7) and the service reviewer and its season wording (PR #8).
- Slice 1:
  - Alembic, `railway.toml` and moving Railway's health check to `/health/ready`;
  - the production schema-behind gate (`details.reason = "schema_behind"`), the revision and RLS startup checks, removing `init_db()` from the lifespan;
  - `domain_errors.py`, `fields`/`details`, the Pydantic 422 mapping;
  - `test_route_guards.py` (its `PUBLIC` allowlist must hold `/health` and `/health/ready`);
  - `frontend/src/lib/api/errors.ts` and `ApiError.requestId` with "(Ref: …)";
  - the no-network fixture.
- Slice 2: `backend/cache.py`, `test_cache.py` and the rate limiter.
- Slice 4 (only under the contingency): `liturgy_prompts.LEGACY_SYSTEM_PROMPT`, `legacy_default_prompts()` and the `generate_liturgy` wrapper.
- Slice 5b: the switchover banner on `streamlit-frozen`.
- Slice 7: deleting `keep-awake.yml`, the README and manual-verification rewrite, the external uptime monitor.
