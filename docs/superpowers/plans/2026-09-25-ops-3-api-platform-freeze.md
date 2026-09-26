# Ops-3: API Platform, Readiness, Keep-alive and the Streamlit Freeze — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship PR ops-3 of the ops slice, then the Freeze. ops-3 adds request ids on every response, CORS-safe 500s, the final CORS lists, `redirect_slashes=False`, logging with `request_id=`, the `APP_ENV` startup guards and `GET /health/ready`. `keepalive.yml` then curls `/health/ready` and holds no database secret. `app.py` on `main` gets its FROZEN header, and `keep-awake.yml` pings only production. The Freeze then serves the production Streamlit app `liturgy-stg` from a protected `streamlit-frozen` branch and deletes the unused `liturgy` app.

**Architecture:** Two pure-ASGI middlewares in `backend/api/middleware.py` sit inside `CORSMiddleware`, in this order: CORS → `RequestIdMiddleware` → `UnhandledErrorMiddleware`. So every response the app produces carries `X-Request-Id`, and an unexpected exception becomes the uniform 500 body with CORS headers instead of a network error. A contextvar holds the request id. Error bodies read it (`api/errors._body`), and so does a log-record factory (`api/logging_config`) that stamps `request_id` on every record. `api/startup.py` holds the pure startup checks the lifespan runs before `init_db()`. `db/health.py` holds the memoized, single-flight `SELECT 1` probe; the public route `/health/ready` only calls it. Workflows, docs and the runbook are guarded by pytest tests in `backend/tests/test_ops_workflows.py`. The Freeze is owner work plus two git commands, recorded in `docs/ops-runbook.md`.

**Tech Stack:** Python 3.11, FastAPI 0.141.1 / Starlette 1.7.0 (pure ASGI middleware, `CORSMiddleware`, `TestClient`), anyio 4.15 (copies the context into the threadpool), SQLAlchemy 2.1.1, psycopg2, pytest, PyYAML 6 (test only), GitHub Actions (`curl`), Railway, Vercel (unchanged), Streamlit Community Cloud, Google Cloud OAuth client.

**Spec:** `docs/superpowers/specs/2026-09-25-slice-ops-cleanup-design.md` ("the ops spec"). Foundations: `docs/superpowers/specs/2026-09-25-migration-foundations-design.md` ("F": §1.1, §1.5, §1.10, §2.5, §2.6 items 1–2, §3.3, §5.5, §6.1, §7.2, §7.3). Inventory: `docs/superpowers/specs/2026-09-25-streamlit-migration-inventory.md` ("inv"). Earlier PRs, assumed merged exactly as written, together with their records PRs: `docs/superpowers/plans/2026-09-25-ops-1-backups-cleanup-d5.md` ("the ops-1 plan") and `docs/superpowers/plans/2026-09-25-ops-2-identity-db.md` ("the ops-2 plan").

## Global Constraints

- Run every command from the repo root with `.venv/bin/python` (Python 3.11). The system `python3` is 3.9 and has no deps. If `.venv` is missing: `/Users/beaubrown/.local/bin/python3.11 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt`.
- Backend test command: `.venv/bin/python -m pytest -q` (pytest.ini: `pythonpath = . backend`, `testpaths = backend/tests streamlit_tests`). Baseline after ops-1, ops-2 and their records PRs: `277 passed`. This plan adds 74 tests and deletes the 5 in `test_keepalive.py`, for `346 passed`. If the baseline differs because a docs-only PR added tests, use your number and add the same deltas.
- Frontend: untouched. CI's frontend job (`npm ci`, lint, typecheck, `npm test`, build) must stay green.
- Every commit message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Commits follow TDD: test first, watch it fail, then code.
- Layering: nothing under `backend/` imports `streamlit`. `backend/db/health.py` imports neither FastAPI nor Starlette. `db/` never imports `api/`. `api/routes/health.py` holds no SQL and no `try` (the recorded exception to F §2.2 items 1 and 4: `/health` and `/health/ready` have no usecase and raise `ApiError`).
- No schema change, no Alembic, no data migration (slice 1). `init_db()` stays in the lifespan (slice 1 removes it).
- Middleware order in `create_app()` (the last added is the outermost): `add_middleware(UnhandledErrorMiddleware)`, then `RequestIdMiddleware`, then `CORSMiddleware`. The resulting stack, outside in: Starlette `ServerErrorMiddleware` → CORS → RequestId → UnhandledError → `ExceptionMiddleware` → router. The existing `@app.exception_handler(Exception)` stays as the last resort.
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
- **Streamlit apps (owner correction 1, 2026-09-25; reverses the ops spec).** `liturgy-stg`, https://liturgy-stg.streamlit.app, is the production Streamlit app. The owner and the tester use it; it is the app to keep, freeze on `streamlit-frozen` and keep awake. `liturgy`, https://liturgy.streamlit.app, is unused, and its Google sign-in already fails with `StreamlitAuthError` (its secrets config). The Freeze deletes it and its two redirect URIs. Wherever the ops spec says "delete `liturgy-stg`" or "keep-awake pings only `https://liturgy.streamlit.app/`", this plan does the opposite. Tester messages and smoke checks use `liturgy-stg`.
- **Step 0 is done (owner correction 2).** ops-1 wrote the results into `docs/ops-runbook.md`; never ask the owner to redo them. The Data API was already off (REST and GraphQL with the anon key return 503 `PGRST002`, no rows), so there was no incident. Every `public` table is owned by `postgres`, with `rolbypassrls = true`. RLS and the REVOKE / `ALTER DEFAULT PRIVILEGES` statements ran on 2026-09-25, and afterwards the Vercel app and `liturgy-stg` both still loaded the owner's church. The server is 17.6 (`- Postgres server major: 17`, `PG_MAJOR` 17). Railway closes a request after 5 minutes with no data, and allows up to 15 minutes while data flows (https://docs.railway.com/networking/public-networking/specs-and-limits, checked 2026-09-25), so the 120 s floor is met. The `age` key pair had **not** been generated on 2026-09-25; that owner step comes before backups and belongs to ops-1 (its Task 0, Step 3, and Task 7). ops-3 neither asks for it nor touches it: Task 1, Step 1's empty `[owner` grep shows that ops-1's records PR filled the runbook's Key custody row.
- **Pool (owner correction 3).** The Supavisor Pool Size is 15 (Nano compute; max client connections 200): 2 × (3 + 3) + 2 = 14 ≤ 15. `DB_POOL_SIZE=3` and `DB_MAX_OVERFLOW=3` are the code defaults (ops-2), the `backend/.env.example` values (ops-1), Railway service variables and top-level keys in the `liturgy-stg` Streamlit Secrets. ops-3 changes none of them. The owner confirms both keys in the `liturgy-stg` Secrets before the cut (Task 13, Step 3); if the Freeze recreates `liturgy-stg`, its pasted Secrets must still contain both keys. Deleting the unused `liturgy` app in the Freeze also frees its connections (Task 15 rewrites the Platform limits bullet to say so).
- Production URLs: API https://church-production-74ca.up.railway.app; frontend https://worship-service-builder.vercel.app; Supabase project `worship-staging`, ref `tbecmwtitsoxzkrvxxxu`; repo `bbrown62450/church`.
- The agent never sees or types a secret (database URLs, keys, tokens, Streamlit Secrets). Opening a PR, merging, pushing a branch other than the PR branch, setting repository variables or protection, triggering workflows and messaging the tester are outward-facing: get the owner's explicit yes first.
- These tests stay unchanged and green: `test_auth.py`, `test_api_me.py`, `test_api_security.py`, `test_docs.py`, `test_ci_workflow.py`, `test_no_streamlit_in_core.py`, the ops-2 identity tests, and all of `streamlit_tests/`. `test_api_app.py` changes exactly one test (Tasks 1–2). `test_keepalive.py` is deleted (Task 7).
- **Not in ops-3** (other PRs and slices; do not touch): `backup.yml`, the `age` recipients, `normalize-pg-url.sh` (ops-1); `db/upsert.py`, `ensure_user`, the identity cache and the pool code (ops-2); Alembic, `railway.toml`, the Railway health check move, the schema-behind gate, `domain_errors.py`, `fields`/`details`, `test_route_guards.py`, the frontend `ApiError.requestId` and "(Ref: …)" text, `frontend/src/lib/api/errors.ts` itself (slice 1); `backend/cache.py` and `backend/tests/test_cache.py` (slice 2, never create them); `OPENAI_MODEL` (slice 3); the switchover banner (5b); the root `.env.example`, deleting `keep-awake.yml`, the README rewrite (slice 7).

## Spec clarifications (recorded, not deviations of intent)

1. **Owner correction 1 in code.** `keep-awake.yml`'s `APP_URLS` becomes exactly `https://liturgy-stg.streamlit.app/`. The spec's test ("contains `https://liturgy.streamlit.app/` and not `liturgy-stg`") is inverted to match: the one URL is `https://liturgy-stg.streamlit.app/`, and `https://liturgy.streamlit.app` is absent. Slice 7's "verify ops" row names `liturgy`; slice 7 adapts it, as that row itself allows.
2. **`test_api_app.py::test_unhandled_exception_is_a_generic_500` changes in two steps.** Task 1 adds `request_id` to every error body. The last-resort 500 then carries a fallback id but no header yet, so Task 1 asserts a 32-hex `request_id`. Task 2 puts `UnhandledErrorMiddleware` inside `RequestIdMiddleware` and tightens the test to the spec's final form: `request_id` equals the `X-Request-Id` header, and the body has exactly `code`, `message` and `request_id`.
3. **Request-id boundaries.** The spec lists the invalid inbound id "`short` (7 characters)", but `short` has 5. The test uses the 7-character `abc-123`, plus `bad id!` and a 65-character id. The valid cases include both edges: 8 characters and 64 characters.
4. **405 in the error-body test.** The spec's API section names 404s, 405s and 422s. The body test covers 404, 405, 401 and 422.
5. **`configure_logging(level) -> int`** returns the level it used, so "uses INFO" is testable. The handler it installs formats with `defaults={"request_id": "-"}`, so a record built without the factory (`logging.makeLogRecord`) never breaks a log line. `basicConfig` receives that handler rather than a bare `format=`.
6. **Blank settings mean the default.** A blank `APP_ENV` means `development`, and a blank `LOG_LEVEL` means `INFO`, as ops-2's `_int_env` treats a blank pool size. `check_app_env` receives the normalized value, so the error shows it (`got 'staging'`).
7. **Where the FROZEN header goes.** `app.py` line 1 is the shebang `#!/usr/bin/env python3`. The FROZEN comment becomes line 2, the first comment after the shebang, and the test reads it there.
8. **Readiness-reset fixture.** The spec's autouse fixture resets the memo only when `db.health` is already imported, the same pattern as ops-2's `_fresh_identity_cache`. A stale result can only exist then.
9. **The `errors.ts` check** (`test_foundation_setup.py`) accepts `"db_unavailable"` or `'db_unavailable'`, and a parametrized self-test shows it bites. It passes as soon as it is written, because the file arrives in slice 1. `test_foundation_setup.py` gains `import pytest` for the self-test.
10. **What moves out of `test_keepalive.py`.** Its workflow assertions move to `test_ops_workflows.py`. `test_backup_workflow_present` is ported as `test_backup_workflow_runs_pg_dump_on_a_schedule`. The three `ping` tests go with `keepalive.py`, and `test_health_ready.py`'s 200 and 503 tests cover the same ground through the API.
11. **Docs get tests.** The README keep-alive paragraph, the runbook's seven sections, its Keep-alive and Environments sections, the freeze subsections and the manual-verification "Ops slice" checklist are asserted in `test_ops_workflows.py`, so each docs change has a failing test first. `test_docs.py` stays unchanged.
12. **Checklist boxes stay unchecked.** `docs/manual-verification.md` is a reusable checklist, as slice 0 left its own section. Results, with dates, go into `docs/ops-runbook.md`. So AC 23's "every box is checked" means performed and recorded.
13. **Two freeze-records PRs.** The spec's "after the next merge to `main`, the app's logs show no new build" needs a merge after the redeploy. Records PR A (Task 15) is that merge. Records PR B records the check that PR A's merge triggered.
14. **Stale mentions of the keep-alive script.** The ops-2 docstring in `db/engine.py` and ops-2's "Platform limits" bullet in the runbook mention `keepalive.py`, which ops-3 deletes. Both are reworded (Task 7), and a test keeps the runbook from mentioning it again.
15. **Contingency code.** The spec's contingency (Freeze step 8) asks for an `AppTest` smoke test. Task 16 gives it in full, checked against this repo on 2026-09-25 (it passed in 0.7 s). It is used only if Task 14 fails.
16. **The old `DATABASE_URL` Actions secret.** After ops-3 only `db-backup` holds database credentials (ops spec, Backups → Decisions). Inventory H4 says the keepalive secret was never added. If a `DATABASE_URL` Actions secret does exist, the owner deletes it in Task 12, because nothing reads it any more.

## File Map

```
backend/api/middleware.py            NEW: REQUEST_ID_HEADER, current_request_id(), RequestIdMiddleware, UnhandledErrorMiddleware
backend/api/logging_config.py        NEW: LOG_FORMAT, configure_logging(level) -> int (record factory adds request_id)
backend/api/startup.py               NEW: describe_database(url), check_app_env(value), enforce_production_guards(settings, engine)
backend/db/health.py                 NEW: READY_OK_TTL, READY_FAIL_TTL, database_ready(*, clock), _probe(), reset_readiness_for_tests()
backend/api/errors.py                request_id in _body; error_body alias; db_unavailable()
backend/api/main.py                  configure_logging; lifespan guards and Database log; redirect_slashes=False; middleware order; CORS lists
backend/api/settings.py              Settings.app_env, Settings.log_level, Settings.is_production
backend/api/routes/health.py         ReadyOut; GET /health/ready
backend/db/engine.py                 module docstring: the readiness probe, not the keep-alive script
backend/keepalive.py                 DELETED
backend/tests/test_keepalive.py      DELETED (5 tests)
backend/tests/test_middleware.py     NEW (33 tests)
backend/tests/test_startup.py        NEW (14 tests)
backend/tests/test_health_ready.py   NEW (10 tests)
backend/tests/test_api_app.py        test_unhandled_exception_is_a_generic_500 asserts request_id == header
backend/tests/test_foundation_setup.py  + errors.ts "db_unavailable" check and its self-test (4 tests)
backend/tests/test_ops_workflows.py  + keepalive, keep-awake, FROZEN header, README, runbook, manual checks (13 tests)
backend/tests/conftest.py            + autouse readiness-memo reset
.github/workflows/keepalive.yml      REWRITTEN: curl ${API_BASE_URL}/health/ready, permissions {}, no secret
.github/workflows/keep-awake.yml     APP_URLS = https://liturgy-stg.streamlit.app/ only; header comment
app.py                               line 2: FROZEN header
README.md                            "Keep-alive (required)" paragraph (lines 144-149)
docs/ops-runbook.md                  + Environments and variables, Keep-alive, freeze subsections; Platform limits bullets
docs/manual-verification.md          + "## Ops slice"
```

---

### Task 1: Request ids on every response and in every error body (S9, S13)

**Files:**
- Create: `backend/api/middleware.py`
- Modify: `backend/api/errors.py:1-9` (docstring and imports), `backend/api/errors.py:40-41` (`_body`)
- Modify: `backend/api/main.py:10` (import), `backend/api/main.py:36-37` (add the middleware)
- Test: `backend/tests/test_middleware.py` (new), `backend/tests/test_api_app.py:1-3` (imports) and `:50-53` (the end of the 500 test)

**Interfaces:**
- Consumes: `api.main.create_app() -> FastAPI`; `api.deps.get_verifier` (overridden so `/me` fails on the missing token first); `api.errors._body(code, message) -> dict`.
- Produces:
  - `api.middleware.REQUEST_ID_HEADER = "X-Request-Id"`;
  - `api.middleware.current_request_id() -> Optional[str]` (None outside a request);
  - `api.middleware.RequestIdMiddleware(app)`, pure ASGI;
  - `api.errors._body(code, message)` returns `{"error": {"code", "message", "request_id"}}`;
  - `api.errors.error_body`, a public alias of `_body` (Task 2 uses it);
  - in `test_middleware.py`: `HEX32` (compiled `[0-9a-f]{32}`) and `_app_with_test_routes()`.

- [ ] **Step 1: Start the branch and check the baseline**

```bash
git fetch origin
git switch -c claude/ops-3-api-platform-freeze origin/main
test -f docs/superpowers/specs/2026-09-25-slice-ops-cleanup-design.md \
  && test -f backend/tests/test_ops_workflows.py \
  && grep -q '^DEFAULT_POOL_SIZE = 3$' backend/db/engine.py \
  && grep -q '^def ensure_user' backend/repos/users.py \
  && test -f backend/api/identity_cache.py && echo "ops-1 and ops-2 are on main"
grep -c '^### What the frozen app inherits from ops-2' docs/ops-runbook.md
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked'; echo "grep exit $?"
.venv/bin/python -m pytest -q | tail -1
```

Expected: `ops-1 and ops-2 are on main`; `1`; no marker lines and `grep exit 1` (the ops-1 and ops-2 records PRs filled every marker, so the ops-2 gate passed); `277 passed`. If any check fails, stop: ops-3 starts only after the ops-2 gate is recorded (ops-2 plan, Task 11).

If `git switch` refuses because an untracked file would be overwritten (an untracked copy of an earlier plan that `main` now has), move that copy out of the way (`mv docs/superpowers/plans/<file> "${TMPDIR:-/tmp}/"`) and switch again. Leave this plan file untracked until Task 10 commits it.

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

`_body` keeps its name, because slice 1 extends it with `fields` and `details`. `ApiError` and the four handlers in `install_error_handlers` are unchanged.

- [ ] **Step 6: Add the middleware in `backend/api/main.py`**

After line 10 (`from api.errors import install_error_handlers`), add:

```python
from api.middleware import RequestIdMiddleware
```

Replace lines 36-37:

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

Expected: `21 passed` (12 + 9), then `289 passed`.

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
- Modify: `backend/api/main.py` (import line; the `RequestIdMiddleware` line from Task 1)
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
.venv/bin/python -m pytest -q | tail -1
```

Expected: `26 passed` (17 + 9); `6 passed` (ops-2's `test_a_failed_ensure_user_is_never_cached` still gets its 500 `internal_error`, now from `UnhandledErrorMiddleware`); `294 passed`.

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

`allow_credentials` stays at its default (off): the API uses bearer tokens, not cookies. The slice-0 frontend calls only `/me` and `/church`, never with a trailing slash (`frontend/src/app/page.tsx`), so nothing depends on the old 307.

- [ ] **Step 4: Run the tests and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_middleware.py backend/tests/test_api_app.py
.venv/bin/python -m pytest -q | tail -1
```

Expected: `30 passed` (21 + 9), then `298 passed`. `test_api_app.py::test_cors_allows_only_configured_origins` still passes.

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
- Modify: `backend/api/main.py:2-4` (imports), the `api.errors` import line (add one after it), `backend/api/main.py:15-21` (logging setup)
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

Validation stays out of `get_settings`, so importing `api.main` never raises.

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

Expected: `33 passed`, then `310 passed`.

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
- Consumes: `api.settings.Settings`, `get_settings()` (Task 4); `db.get_engine() -> Engine`; `db.init_db()`; `db.engine._make_engine(url) -> Engine` (ops-2; it opens no connection); fixture `tmp_db`.
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

After this step the whole file reads as below. Compared with Task 4, three things change: the imports of `api.startup` and `get_engine`, the module `logger`, and the lifespan, which replaces lines 24-31 of the original file.

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
from api.routes import health, me
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
    return app


app = create_app()
```

The SUPABASE_URL warning text is unchanged (`test_api_app.py::test_lifespan_warns_when_supabase_url_unset`).

- [ ] **Step 6: Run the tests, the suite and a real uvicorn start**

```bash
.venv/bin/python -m pytest -q backend/tests/test_startup.py backend/tests/test_api_app.py
.venv/bin/python -m pytest -q | tail -1
(cd backend && DATABASE_URL="sqlite:///$(mktemp -d)/guard.db" APP_ENV=production \
  ../.venv/bin/python -m uvicorn api.main:app --port 8765 2>&1 | tail -3)
```

Expected: `23 passed` (14 + 9), then `324 passed`. uvicorn exits by itself, and the last three lines are `RuntimeError: APP_ENV=production requires a PostgreSQL DATABASE_URL; refusing to start.`, a blank line, and `ERROR:    Application startup failed. Exiting.`

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
- Modify: `backend/tests/conftest.py` (append an autouse fixture at the end, after ops-2's `_fresh_identity_cache`)
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

Expected: `21 passed` (10 + 11); `10` (no flaky run); `338 passed`.

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
- Modify: `README.md:144-149` ("Keep-alive (required)")
- Modify: `docs/ops-runbook.md` (a new `## Keep-alive` section directly above `## Streamlit freeze`; one sentence of the ops-2 pool bullet in `## Platform limits`)
- Modify: `backend/db/engine.py` (the last two lines of the module docstring, lines 10-11 after ops-2)
- Test: `backend/tests/test_ops_workflows.py` (append)

**Interfaces:**
- Consumes: from `test_ops_workflows.py` (ops-1): `ROOT`, `_read(path)`, `BACKUP_YML`, `RUNBOOK`, `README`, and the module import `yaml`.
- Produces: `KEEPALIVE_YML`, `KEEPALIVE_MUST_CONTAIN` and `KEEPALIVE_MUST_NOT_CONTAIN` in `test_ops_workflows.py`; the workflow reads the repository variable `API_BASE_URL` (the owner sets it in Task 12); the runbook section `## Keep-alive`, with a run-record row filled in Task 15.

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

Expected: `6 failed, 18 passed`. The two workflow-text tests fail on the old workflow (`'/health/ready'` missing; `'secrets.'` present). The permissions test fails with `KeyError: 'permissions'`. The files test lists both files. The README test fails with `AssertionError: /health/ready`. The runbook test fails with `IndexError: list index out of range`, because there is no `## Keep-alive` section yet. The ported backup test passes.

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

Four tries of at most 30 s plus three 20 s waits is 180 s, inside `timeout-minutes: 5`. `${API_BASE_URL%/}` drops one trailing slash, so a variable pasted with one still works. Until the owner sets the variable (Task 12), a run fails at the `::error::` line, which is intended.

- [ ] **Step 4: Delete the script and its tests**

```bash
git rm backend/keepalive.py backend/tests/test_keepalive.py
```

Nothing imports it: `grep -rnE '(import|from) keepalive' --include='*.py' backend app.py streamlit_* ui_helpers.py` prints nothing.

- [ ] **Step 5: Rewrite the README "Keep-alive (required)" paragraph**

`README.md:144-149` reads:

```markdown
### Keep-alive (required)

The free Supabase project pauses after ~7 days idle. `.github/workflows/keepalive.yml`
runs `keepalive.py` (a `SELECT 1` against `DATABASE_URL`) daily so the first
visitor each week never hits a paused/cold database. Add `DATABASE_URL` as an
Actions secret.
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

The "Backups (required)" paragraph below it (ops-1) and the rest of the README stay unchanged (slice 7).

- [ ] **Step 6: Add the runbook's Keep-alive section and fix the pool bullet**

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
  https://liturgy-stg.streamlit.app/ in headless Chromium (a plain HTTP ping
  does not count as traffic). Deleted in slice 7.

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

In `## Platform limits`, ops-2's pool bullet contains these three lines:

```markdown
  setup. `backend/keepalive.py` builds its own engine without these settings
  (ops-3 replaces it); its one short scheduled session fits in the spare
  connection (14 of 15). `backend/tests/test_ops_workflows.py` fails if the
```

Replace them with:

```markdown
  setup, and so does the API's `GET /health/ready` probe (ops-3), which holds
  at most one of the API's pooled connections at a time. The old keep-alive
  script, which built its own engine, is gone. `backend/tests/test_ops_workflows.py` fails if the
```

- [ ] **Step 7: Fix the `db/engine.py` docstring**

The module docstring (ops-2) ends with:

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

Expected: `27 passed` (24 + 3); no grep output and `grep exit 1`; `340 passed` (7 added, 5 deleted).

- [ ] **Step 9: Commit**

```bash
git add .github/workflows/keepalive.yml README.md docs/ops-runbook.md backend/db/engine.py \
        backend/tests/test_ops_workflows.py
git commit -m "keepalive: curl the API's /health/ready; delete keepalive.py (ops S3, inv H4)

The workflow needs only the repository variable API_BASE_URL and holds no
database secret or token permission. keepalive.py and test_keepalive.py are
gone; their workflow assertions live in test_ops_workflows.py. README and the
runbook's new Keep-alive section describe the curl and what to do when it is
red.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Freeze on `main`: the FROZEN header and `keep-awake.yml` production-only (S7)

**Files:**
- Modify: `app.py:1` (insert line 2)
- Modify: `.github/workflows/keep-awake.yml:1-5` (header comment), `.github/workflows/keep-awake.yml:24` (`APP_URLS`)
- Modify: `docs/ops-runbook.md` (`## Platform limits`: the bullet about the unused `liturgy` app)
- Test: `backend/tests/test_ops_workflows.py` (append)

**Interfaces:**
- Consumes: `ROOT`, `_read(path)`, `yaml` from `test_ops_workflows.py`.
- Produces: `KEEP_AWAKE_YML`, `PRODUCTION_STREAMLIT_URL = "https://liturgy-stg.streamlit.app/"`, `RETIRED_STREAMLIT_URL = "https://liturgy.streamlit.app"`, `FROZEN_HEADER`. `keep-awake` visits only `liturgy-stg` from the ops-3 merge on, so the unused `liturgy` app hibernates before the Freeze deletes it.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_ops_workflows.py`:

```python


# --- Streamlit freeze on main: keep-awake and the FROZEN header (ops-3) --------

KEEP_AWAKE_YML = ROOT / ".github" / "workflows" / "keep-awake.yml"
PRODUCTION_STREAMLIT_URL = "https://liturgy-stg.streamlit.app/"   # owner correction 1: liturgy-stg is production
RETIRED_STREAMLIT_URL = "https://liturgy.streamlit.app"           # the unused app the Freeze step deletes
FROZEN_HEADER = "# FROZEN — production runs from branch streamlit-frozen; deleted in slice 7."


def test_keep_awake_pings_only_the_production_streamlit_app():
    text = _read(KEEP_AWAKE_YML)
    steps = yaml.safe_load(text)["jobs"]["visit"]["steps"]
    urls = [url for step in steps for url in step.get("env", {}).get("APP_URLS", "").split()]
    assert urls == [PRODUCTION_STREAMLIT_URL]
    assert RETIRED_STREAMLIT_URL not in text


def test_app_py_carries_the_frozen_header():
    lines = _read(ROOT / "app.py").splitlines()
    first = lines[1] if lines[0].startswith("#!") else lines[0]   # the line after the shebang
    assert first == FROZEN_HEADER
```

`"https://liturgy.streamlit.app"` is not a substring of `"https://liturgy-stg.streamlit.app/"` (a `-` follows `liturgy` there, not a `.`), so the second assertion cannot trip on the production URL.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py 2>&1 | tail -4`

Expected: `2 failed, 24 passed`. The keep-awake test fails because the list has one more item, `'https://liturgy.streamlit.app/'`. The header test fails with `assert '"""' == '# FROZEN — production runs from branch streamlit-frozen; deleted in slice 7.'`.

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

The docstring stays the module's first statement. Nothing else in `app.py` changes. ops-3's only change to a file the Streamlit app runs is this comment line, and `streamlit-frozen`, cut from the ops-3 merge commit, carries it too, where it is also true.

- [ ] **Step 4: Point `keep-awake.yml` at production only**

Replace lines 1-5:

```yaml
# Streamlit Community Cloud hibernates apps after 12 hours without traffic.
# A plain HTTP ping does NOT count (the 200 comes from the platform's sleep
# page), so this job opens each app in headless Chromium — a real WebSocket
# session — every 6 hours, and presses the wake button if the app was asleep.
name: keep-awake
```

with:

```yaml
# Streamlit Community Cloud hibernates apps after 12 hours without traffic.
# A plain HTTP ping does NOT count (the 200 comes from the platform's sleep
# page), so this job opens each app in headless Chromium — a real WebSocket
# session — every 6 hours, and presses the wake button if the app was asleep.
# Production only: liturgy-stg, which the Streamlit freeze serves from branch
# streamlit-frozen (docs/ops-runbook.md → Streamlit freeze). Deleted in slice 7.
name: keep-awake
```

and replace line 24:

```yaml
          APP_URLS: "https://liturgy-stg.streamlit.app/ https://liturgy.streamlit.app/"
```

with:

```yaml
          APP_URLS: "https://liturgy-stg.streamlit.app/"
```

Scheduled workflows run from `main`, so this takes effect on merge, before the Freeze.

- [ ] **Step 5: Update the runbook bullet about the unused `liturgy` app**

In `docs/ops-runbook.md` → `## Platform limits`, ops-2's bullet "Until the Freeze step deletes the unused `liturgy` app, …" contains these three lines:

```markdown
  in practice it holds only the session its startup `init_db()` opens when
  today's `keep-awake` visits it (ops-3 narrows `keep-awake` to
  https://liturgy-stg.streamlit.app/ only). Retiring it frees that share.
```

Replace them with:

```markdown
  in practice it holds only the session its startup `init_db()` opens when
  someone visits it. Since ops-3 `keep-awake` no longer does, so it
  hibernates. Retiring it frees that share.
```

- [ ] **Step 6: Run the tests and the suite**

```bash
.venv/bin/python -m py_compile app.py && echo compiled
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py
.venv/bin/python -m pytest -q | tail -1
```

Expected: `compiled`, `26 passed`, `342 passed`.

- [ ] **Step 7: Commit**

```bash
git add app.py .github/workflows/keep-awake.yml docs/ops-runbook.md backend/tests/test_ops_workflows.py
git commit -m "Streamlit freeze on main: FROZEN header; keep-awake pings only liturgy-stg (F §6.1)

liturgy-stg is the production Streamlit app (owner correction); the unused
liturgy app is no longer kept awake and is deleted in the Freeze step.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Runbook sections and the "Ops slice" manual checks (S15)

**Files:**
- Modify: `docs/ops-runbook.md` (the intro bullet about ops-3; a new `## Environments and variables` directly above `## Supabase lockdown record`; five new `###` subsections directly above `## Platform limits`)
- Modify: `docs/manual-verification.md` (append `## Ops slice` after line 45)
- Test: `backend/tests/test_ops_workflows.py` (append)

**Interfaces:**
- Consumes: `ROOT`, `_read(path)`, `RUNBOOK`, `re` from `test_ops_workflows.py`.
- Produces: `RUNBOOK_SECTIONS` (the seven `##` headings in order), `FREEZE_SUBSECTIONS`, `MANUAL_VERIFICATION` and `_section(text, heading) -> str`. The runbook's `[owner: …]` markers for ops-3 are one line in "Environments and variables" (filled in Task 11), one Keep-alive run row (Task 7) and eleven "Freeze record" rows plus two version lines (Tasks 13–15).

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
                 "API_BASE_URL", "BACKUP_DATABASE_URL", "NEXT_PUBLIC_API_URL", "streamlit-frozen"):
        assert name in section, name


def test_manual_verification_has_the_ops_slice_checklist():
    section = _section(_read(MANUAL_VERIFICATION), "## Ops slice")
    for needle in ("/health/ready", "x-request-id", "/me/", "streamlit-frozen", "keep-awake",
                   "https://liturgy-stg.streamlit.app", "db-backup", "375 px"):
        assert needle in section, needle
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py 2>&1 | tail -6`

Expected: `4 failed, 26 passed`. The order test fails `At index 0 diff: '## Supabase lockdown record' != '## Environments and variables'`. The freeze test lists the five missing subsections, starting with `'### What the frozen app inherits from ops-3'`. The environments and manual-verification tests fail with `IndexError: list index out of range`.

- [ ] **Step 3: Replace the runbook's ops-3 intro bullet**

In `docs/ops-runbook.md`, replace (ops-1):

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
deploy health check `/health` (slice 1 moves it to `/health/ready`).

| Variable | Value | Since |
|---|---|---|
| `DATABASE_URL` | Supabase session-pooler URL (secret) | slice 0 |
| `SUPABASE_URL` | `https://tbecmwtitsoxzkrvxxxu.supabase.co` | slice 0 |
| `CORS_ORIGINS` | `https://worship-service-builder.vercel.app`: exact origins, comma-separated, no trailing slash | slice 0 |
| `APP_ENV` | `production`, set before ops-3 merged. The API then refuses to start on anything but PostgreSQL, and logs an ERROR when `CORS_ORIGINS` lists only localhost. | ops-3 |
| `LOG_LEVEL` | optional: `DEBUG`, `INFO` (the default when unset), `WARNING` or `ERROR` | ops-3 |
| `DB_POOL_SIZE`, `DB_MAX_OVERFLOW` | `3` and `3` (see Platform limits) | ops-1; read since ops-2 |
| `OPENAI_API_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI` | carried over for later slices (secrets) | slice 0 |

Checked against Railway → the API service → Variables (names only):
[owner: date, and any variable that differs from this table]

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
| Secret | `BACKUP_DATABASE_URL` | `db-backup` (see Backups) | ops-1 |
| Variable | `API_BASE_URL` = `https://church-production-74ca.up.railway.app` | `keepalive` (see Keep-alive) | ops-3 |

No other secret is needed. Nothing reads a `DATABASE_URL` Actions secret since
ops-3; if one exists, delete it.

**Streamlit Community Cloud.**

| App | Source | Secrets (names only) |
|---|---|---|
| `liturgy-stg`, https://liturgy-stg.streamlit.app/ (production) | repo `bbrown62450/church`, main file `app.py`, branch `main` until the Freeze, then `streamlit-frozen` | the `[auth]` block (Google sign-in), `DATABASE_URL`, `OPENAI_API_KEY` and the `GOOGLE_*` gmail.send client (README → Local setup), plus the top-level `DB_POOL_SIZE = "3"` and `DB_MAX_OVERFLOW = "3"` |
| `liturgy`, https://liturgy.streamlit.app/ (unused) | deleted in the Freeze | — |

**Supabase**, project `worship-staging` (ref `tbecmwtitsoxzkrvxxxu`, Nano
compute, Postgres 17.6): Data API off (see Supabase lockdown record); Auth
providers: Google only; `mailer_autoconfirm` off; session pooler Pool Size 15
(see Platform limits).

**Google OAuth client** (Google Cloud Console → APIs & Services →
Credentials): the Streamlit redirect URIs are
`https://liturgy-stg.streamlit.app/oauth2callback` and the bare root
`https://liturgy-stg.streamlit.app/`. The Freeze removes the two `liturgy`
ones. No other redirect URI is touched.

````

(Paste the content between the four-backtick fences.)

- [ ] **Step 5: Add the freeze subsections**

Insert directly above the line `## Platform limits`, so they follow ops-2's `### What the frozen app inherits from ops-2` and its gate table:

````markdown
### What the frozen app inherits from ops-3

Nothing that the Streamlit app runs. ops-3 changes the FastAPI app
(`backend/api/`, which Streamlit never imports), adds `backend/db/health.py`
(imported only by the API), deletes the old keep-alive script (never
imported), edits a docstring in `backend/db/engine.py`, changes workflows and
docs, and adds the FROZEN comment at the top of `app.py`. So
`streamlit-frozen`, cut from the ops-3 merge commit, runs what `liturgy-stg`
already ran after ops-2:

- the D5 fix (ops-1; manual check passed, see "D5 fix and recovery record");
- `ensure_user` through `upsert_from_claims`, and the 3 + 3 pool with
  `connect_timeout=10` (ops-2; gate passed, see the table above);
- without the six dead modules (ops-1), which it never imported.

`streamlit_tests/` passed on the ops-3 PR, and the pre-freeze smoke check
below runs on the ops-3 build.

### Freeze record

The ops spec's Freeze steps, with the app names swapped (owner correction,
2026-09-25): `liturgy-stg` is kept and frozen; the unused `liturgy` is deleted.

| Step | Result | Date |
|---|---|---|
| Pre-freeze smoke check on https://liturgy-stg.streamlit.app/ (built from the ops-3 merge on `main`): sign in, the church loads, an archived service loads, Settings opens, and the sidebar has no "Church" selectbox | [owner] | [owner] |
| Tester "before" message sent, with the window | [owner: window] | [owner] |
| `streamlit-frozen` created at the ops-3 merge commit | [owner: commit sha] | [owner] |
| `streamlit-frozen` protected: pull request required, `backend` check required, no force pushes, no deletion | [owner] | [owner] |
| `liturgy-stg` serves from `streamlit-frozen` (branch changed in place, or app recreated with subdomain `liturgy-stg`, same Python version and secrets) | [owner: which way] | [owner] |
| Post-freeze smoke check on https://liturgy-stg.streamlit.app/ passed; the app's settings show branch `streamlit-frozen` | [owner] | [owner] |
| Unused `liturgy` app deleted | [owner] | [owner] |
| Google OAuth client: `https://liturgy.streamlit.app/oauth2callback` and `https://liturgy.streamlit.app/` removed; the two `liturgy-stg` URIs kept | [owner] | [owner] |
| `keep-awake` run by hand: green, one URL | [owner: run URL] | [owner] |
| Tester "after" message sent | [owner] | [owner] |
| After the next merge to `main`, `liturgy-stg` shows no new build | [owner: the merge, and what the logs showed] | [owner] |

### Freeze policy

- Only data-safety fixes (data loss, corruption, leakage, security) go into
  `streamlit-frozen`, as pull requests into that branch; CI runs on them. The
  one planned exception is the slice 5b switchover banner.
- A fix that also concerns backend code on `main` is fixed on `main`
  separately, with its own tests.
- Streamlit code on `main` is not maintained (F §2.3.7); the FROZEN comment
  at the top of `app.py` on `main` says so.
- If a Streamlit Cloud reboot breaks the frozen app because a dependency
  released a new version, pin the versions recorded below in the frozen
  branch's `requirements.txt`. That counts as a data-safety fix: it restores
  the tester's access to their data.
- Merges to `main` no longer redeploy `liturgy-stg`. `keep-awake` (on `main`)
  still keeps it awake.

### Recorded Python and package versions

From `liturgy-stg`'s build log just before the freeze (Streamlit Cloud →
`liturgy-stg` → Manage app → logs, the dependency-install lines).

- Python: [owner]
- Packages:

```
[owner: paste the installed name==version lines from the build log]
```

### Contingency

If `liturgy-stg` cannot be moved to `streamlit-frozen` (F §6.1.6):
1. Keep `liturgy-stg` on `main`, and leave `streamlit-frozen` in place as a
   record.
2. Remove the FROZEN comment from `app.py` on `main`.
3. From then on every PR keeps `app.py` working against `main`: no signature
   change to a function `app.py` calls without a compatible wrapper, and
   `streamlit_tests/test_app_smoke.py` (an `AppTest` run of `app.py`
   signed out) stays green.
4. Record the decision and the date here.

````

(Paste the content between the four-backtick fences; the inner three-backtick block belongs in the runbook.)

- [ ] **Step 6: Append the "Ops slice" checklist to `docs/manual-verification.md`**

Append after line 45 (the last Slice 0 item):

```markdown

## Ops slice

Run on the production URLs: https://worship-service-builder.vercel.app (at
375 px in Chrome device mode, iPhone SE, and on desktop),
https://church-production-74ca.up.railway.app, and
https://liturgy-stg.streamlit.app, the production Streamlit app (the unused
`liturgy` app is deleted in the Freeze). Record each result, with its date,
in `docs/ops-runbook.md`.

- [ ] Step 0 recorded in `docs/ops-runbook.md` (done on 2026-09-25; confirm the records are there, do not redo the checks): the exposure checks (the Data API was already off: REST and GraphQL with the anon key return 503 `PGRST002` and no rows, so no incident), GraphQL introspection, table owners and BYPASSRLS, `server_version` 17.6 and the `- Postgres server major: 17` line, the pooler Pool Size 15 with 2 × (3 + 3) + 2 = 14 ≤ 15, and Railway's request limit with its source. If a later exposure check ever returns rows: the incident record, including the users/contacts audit and where the forensic dump is kept.
- [ ] D5 workaround message sent to the tester on day one.
- [ ] D5 fix, after ops-1 is live on `liturgy-stg`, in a throwaway church: sign in with a second Google account that has no church and create "Ops test". Tick "Exclude hymns used in the last 12 weeks", pick three hymns, generate the liturgy, click "Prepare bulletin copy": the three picks are still selected. Click "Prepare pastor's copy": both Word files list the three hymns. Save, then load the service again with the box still ticked: its three hymns are in the slots. Delete "Ops test" in Settings → Danger zone. Then run the recovery queries, record the result, and send the tester the "fixed" message.
- [ ] https://worship-service-builder.vercel.app, after the lockdown and after each ops merge: sign in, the church shows in the switcher, switch church if you have two, log out.
- [ ] `db-backup` run by hand: green, with an artifact `backup-*.dump.age`; the log shows no URL or password. The restore drill's counts match production.
- [ ] `https://church-production-74ca.up.railway.app/health/ready` → `{"ok":true,"db":"ok"}`. The `keepalive` run by hand is green.
- [ ] Railway deploy log after ops-3: `Database: dialect=postgresql driver=psycopg2 host=…pooler.supabase.com database=postgres`, with no username or password, and no `CORS_ORIGINS allows only localhost` ERROR line.
- [ ] Browser devtools on the Vercel app: the `/me` response has an `x-request-id` header, and it is readable from JS: in the console, `fetch("https://church-production-74ca.up.railway.app/health").then(r => r.headers.get("x-request-id"))` resolves to an id, not `null`.
- [ ] `curl -i https://church-production-74ca.up.railway.app/me/` → 404 JSON with `request_id`, and no `location` header (not a 307).
- [ ] `liturgy-stg` before the freeze and after the redeploy: sign in, load the church, load an archived service, open Settings. The app's settings show branch `streamlit-frozen`. After the next merge to `main`, no new Streamlit build.
- [ ] The unused `liturgy` app is gone; its two redirect URIs (`https://liturgy.streamlit.app/oauth2callback` and `https://liturgy.streamlit.app/`) are removed from the Google OAuth client; `keep-awake` is green with one URL, https://liturgy-stg.streamlit.app/.
```

The boxes stay unchecked: this is a reusable checklist, as slice 0 left its own section, and results go into the runbook (clarification 12).

- [ ] **Step 7: Run the tests and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_docs.py
grep -n '^## ' docs/ops-runbook.md
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
.venv/bin/python -m pytest -q | tail -1
```

Expected: `33 passed` (30 + 3); the seven `##` headings in the order of `RUNBOOK_SECTIONS`; `15` marker lines (the Railway check line, the Keep-alive run row, 11 Freeze record rows, and the two version lines); `346 passed`.

- [ ] **Step 8: Commit**

```bash
git add docs/ops-runbook.md docs/manual-verification.md backend/tests/test_ops_workflows.py
git commit -m "Runbook: environments, freeze record and policy; 'Ops slice' manual checks (S15)

The runbook now has the spec's seven sections. The freeze record, the
recorded versions and the Railway check are [owner: …] markers, filled
before merge and after the Freeze.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Full verification, local smoke and the ops-3 pull request

**Files:** none changed (this plan file is committed in Step 5)

**Interfaces:**
- Consumes: everything from Tasks 1–9.
- Produces: an open PR `claude/ops-3-api-platform-freeze` → `main` with green CI.

- [ ] **Step 1: Run the whole suite and the acceptance checks**

```bash
.venv/bin/python -m pytest -q | tail -1
ls backend/keepalive.py backend/tests/test_keepalive.py backend/cache.py backend/tests/test_cache.py 2>&1 | grep -c "No such file"
(cd backend && ../.venv/bin/python -c "import sys, api.main, db.health; print(sorted(m for m in sys.modules if m.split('.')[0] == 'streamlit'))")
grep -nE '^(from|import) ' backend/db/health.py backend/db/engine.py | grep -E 'api|fastapi|starlette|streamlit'; echo "grep exit $?"
git diff --stat origin/main...HEAD -- frontend backend/.env.example .github/workflows/backup.yml .github/workflows/ci.yml \
  .github/backup backend/repos backend/auth.py backend/api/deps.py backend/api/identity_cache.py backend/db/upsert.py
grep -n '^- Postgres server major: 17$\|docs.railway.com/networking/public-networking/specs-and-limits' docs/ops-runbook.md | wc -l
```

Expected, in order:
- `346 passed`;
- `4` (the keep-alive script and its tests are gone; slice 2's cache files were never created);
- `[]` (the API and the readiness module pull in no Streamlit);
- no output and `grep exit 1` (`db/` imports no `api/`, FastAPI, Starlette or Streamlit);
- nothing: ops-3 touches no ops-1 or ops-2 file, no frontend file and no other workflow;
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

So the Streamlit app's behavior on `streamlit-frozen` is exactly what `liturgy-stg` ran after ops-2, as the runbook's "What the frozen app inherits from ops-3" says.

- [ ] **Step 3: Local smoke test with a real uvicorn**

```bash
tmp=$(mktemp -d)
DATABASE_URL="sqlite:///$tmp/smoke.db" APP_ENV=development CORS_ORIGINS=https://worship-service-builder.vercel.app \
  .venv/bin/python -m uvicorn --app-dir backend api.main:app --port 8765 > "$tmp/uvicorn.log" 2>&1 &
pid=$!
for i in $(seq 30); do curl -s localhost:8765/health >/dev/null && break; sleep 0.3; done
curl -s localhost:8765/health/ready; echo
curl -si localhost:8765/me/ | tr -d '\r' | grep -iE '^HTTP|^x-request-id|^location|^\{'
curl -si localhost:8765/health -H 'X-Request-Id: smoke-test-0001' | tr -d '\r' | grep -i '^x-request-id'
curl -si -X OPTIONS localhost:8765/me -H 'Origin: https://worship-service-builder.vercel.app' \
  -H 'Access-Control-Request-Method: GET' \
  -H 'Access-Control-Request-Headers: authorization, x-church-id, idempotency-key, if-match, x-request-id' \
  | tr -d '\r' | grep -iE '^HTTP|^access-control-(allow-headers|max-age|allow-origin)'
curl -si localhost:8765/health -H 'Origin: https://worship-service-builder.vercel.app' \
  | tr -d '\r' | grep -i '^access-control-expose-headers'
kill "$pid"; sleep 1
grep 'Database:' "$tmp/uvicorn.log"
```

Run it as one block (shell state does not carry between separate commands). Expected (checked in a scratch copy on 2026-09-25):

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
api.main INFO request_id=- Database: dialect=sqlite driver=pysqlite host=- database=<tmp>/smoke.db
```

There is no `location` line for `/me/`.

- [ ] **Step 4: Check the runbook markers**

Run: `grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l`
Expected: `15` (the Railway check line, the Keep-alive run row, 11 Freeze record rows, and the two version lines). Every ops-1 and ops-2 marker was already filled (Task 1, Step 1).

- [ ] **Step 5: Push and open the PR (get the owner's go-ahead first)**

```bash
git add docs/superpowers/plans/2026-09-25-ops-3-api-platform-freeze.md
git commit -m "Add the ops-3 implementation plan

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" || true   # "nothing to commit" is fine if it is already committed
git push -u origin claude/ops-3-api-platform-freeze
gh pr create --base main --head claude/ops-3-api-platform-freeze \
  --title "ops-3: request ids, CORS-safe 500s, startup guards, /health/ready, keepalive, freeze on main" \
  --body "PR ops-3 of the ops slice (docs/superpowers/specs/2026-09-25-slice-ops-cleanup-design.md; plan docs/superpowers/plans/2026-09-25-ops-3-api-platform-freeze.md).

- RequestIdMiddleware and UnhandledErrorMiddleware (pure ASGI), order CORS → RequestId → UnhandledError: X-Request-Id on every response the app produces, request_id in every error body, unexpected 500s arrive with CORS headers (S9, S13, F §7.3).
- Final CORS lists (Idempotency-Key, If-Match, X-Request-Id; exposes Content-Disposition, Retry-After, X-Request-Id; max-age 600) and redirect_slashes=False (S11).
- Logging: request_id= on every line; LOG_LEVEL validated. Startup: 'Database: dialect=… driver=… host=… database=…' without credentials; APP_ENV=production refuses a non-PostgreSQL DATABASE_URL before init_db and logs an ERROR for localhost-only CORS (S10).
- GET /health/ready: memoized (10 s ok / 5 s failed), single-flight SELECT 1 in db/health.py; 503 db_unavailable (S3).
- keepalive.yml curls \${API_BASE_URL}/health/ready with no secret; backend/keepalive.py and test_keepalive.py deleted (inv H4).
- app.py FROZEN header; keep-awake.yml pings only https://liturgy-stg.streamlit.app/ (owner correction: liturgy-stg is production; the unused liturgy app is deleted in the Freeze).
- README keep-alive, runbook (environments, keep-alive, freeze record and policy), 'Ops slice' manual checks.
- Tests: +74, -5 (346 total).

Before merge: owner sets APP_ENV=production on Railway (plan Task 11). After merge: API_BASE_URL variable and a keepalive run (Task 12), then the Freeze (Tasks 13-15).

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
gh pr checks --watch
```

Expected: the `backend` and `frontend` checks pass, and the Vercel preview deployment reports success (the frontend is unchanged).

---

### Task 11 (OWNER, before merge): `APP_ENV=production` on Railway, the variables check, merge

The ops spec's gate: set `APP_ENV=production` on Railway **before** merging. The code on Railway before the merge ignores it, so setting it early is harmless. Once ops-3 is live, the guard needs it.

**Files:**
- Modify (by the agent, from the owner's answer): `docs/ops-runbook.md` → Environments and variables, the `[owner: …]` "Checked against Railway" line

- [ ] **Step 1 (OWNER): Set and check the Railway variables**

Railway → the project → the API service → Variables:
1. Add `APP_ENV` = `production`. Optionally add `LOG_LEVEL` = `INFO` (unset means `INFO` too).
2. Check, by name and without copying any secret value, that these are present:
   - `DATABASE_URL` starts with `postgresql` (or `postgres`) and points at the Supabase **pooler**. It must not be empty or `sqlite:…`: once ops-3 is live, that would stop the new deploy with `APP_ENV=production requires a PostgreSQL DATABASE_URL; refusing to start.`, and the previous release would keep serving;
   - `CORS_ORIGINS` contains `https://worship-service-builder.vercel.app`, not only `localhost`;
   - `DB_POOL_SIZE` = `3` and `DB_MAX_OVERFLOW` = `3`;
   - `SUPABASE_URL`, and the carried-over `OPENAI_API_KEY` and `GOOGLE_*` variables.
3. Saving redeploys the current code. Wait until the deployment is Active.

Then tell the agent the date, and any variable name that differs from the runbook's Railway table.

- [ ] **Step 2 (agent): Confirm the API is still up and record the check**

```bash
curl -s https://church-production-74ca.up.railway.app/health; echo
```

Expected: `{"ok":true}`. In `docs/ops-runbook.md` → Environments and variables, replace `[owner: date, and any variable that differs from this table]` with the date and `matches` (or the differences the owner named, and a table fix to match reality). Then:

```bash
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
.venv/bin/python -m pytest -q | tail -1
git add docs/ops-runbook.md
git commit -m "Runbook: Railway variables checked; APP_ENV=production set before merge

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push
```

Expected: `14`, then `346 passed`.

- [ ] **Step 3 (OWNER): Review and merge at a quiet time**

Every merge to `main` still rebuilds `liturgy-stg` until the Freeze (for ops-3, only a comment line changes in `app.py`), which briefly restarts the app. Merge on a weekday when the tester is not using it, never Saturday or Sunday. All CI checks must be green. Merging is outward-facing, so merge only on the owner's explicit yes:

```bash
gh pr merge --merge claude/ops-3-api-platform-freeze
```

Use a merge commit (`--merge`), not squash: its sha is "the ops-3 merge commit" the Freeze branches from.

---

### Task 12 (OWNER + agent, after merge): deploy checks, `API_BASE_URL`, keepalive

**Files:** none (results go into the runbook in Task 15)

- [ ] **Step 1 (OWNER): Railway deploy log**

Railway → the API service → Deployments: the deployment for the merge commit is Active. Its deploy logs show exactly one line of this shape, with no username or password in it:

```
api.main INFO request_id=- Database: dialect=postgresql driver=psycopg2 host=aws-…pooler.supabase.com database=postgres
```

They must show no `CORS_ORIGINS allows only localhost` line and no traceback. If the deploy failed with `APP_ENV=production requires a PostgreSQL DATABASE_URL; refusing to start.`, the previous release is still serving: fix `DATABASE_URL` (Task 11, Step 1) and redeploy. (AC 18.)

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

- [ ] **Step 3 (OWNER): The Actions variable `API_BASE_URL`**

GitHub → `bbrown62450/church` → Settings → Secrets and variables → Actions → **Variables** tab → New repository variable:
- Name: `API_BASE_URL`
- Value: `https://church-production-74ca.up.railway.app`

This value is not a secret. Alternatively the agent runs this, on your explicit yes (it changes repository configuration):

```bash
gh variable set API_BASE_URL --body "https://church-production-74ca.up.railway.app" -R bbrown62450/church
```

On the **Secrets** tab, the only secret should be `BACKUP_DATABASE_URL`. If a `DATABASE_URL` secret exists (the old keep-alive's, which inventory H4 says was never added), delete it: nothing reads it since ops-3.

- [ ] **Step 4 (agent, on the owner's yes): Run keepalive by hand**

```bash
gh variable list -R bbrown62450/church
gh workflow run keepalive --ref main -R bbrown62450/church
sleep 5; gh run list --workflow keepalive --limit 1 -R bbrown62450/church
gh run watch <run-id> --exit-status -R bbrown62450/church
gh run view <run-id> --log -R bbrown62450/church | grep -c '{"ok":true,"db":"ok"}'
```

Expected: `API_BASE_URL` with the Railway URL in the variable list; the run completes successfully; `1`. Note the date and the run URL for the runbook's Keep-alive record (Task 15). (AC 5.)

- [ ] **Step 5 (OWNER): The React app and request-id exposure**

On https://worship-service-builder.vercel.app, at 375 px (Chrome device mode, iPhone SE) and on desktop: sign in, the church shows in the switcher, switch church if you have two, log out. In devtools → Network, the `/me` response has an `x-request-id` header. In the console, `fetch("https://church-production-74ca.up.railway.app/health").then(r => r.headers.get("x-request-id"))` resolves to an id, not `null` (the header is exposed to JS).

Give the agent the dates and results of Steps 1–5.

---

### Task 13 (OWNER + agent): Freeze, part 1: pre-freeze checks, cut and protect `streamlit-frozen`

F §6.1 and the ops spec's Freeze steps 1–3, with owner correction 1: the app that is kept and frozen is `liturgy-stg`.

**Files:** none (results go into the runbook in Task 15)

- [ ] **Step 1 (agent): Confirm what the frozen branch will inherit**

```bash
git fetch origin
gh pr view claude/ops-3-api-platform-freeze -R bbrown62450/church --json state,mergeCommit \
  -q '.state + " " + .mergeCommit.oid'
git show origin/main:docs/ops-runbook.md | grep -n '\[owner' | grep -v 'An entry marked' | wc -l
gh run list --workflow ci --branch main --limit 1 -R bbrown62450/church --json headSha,conclusion \
  -q '.[0].headSha + " " + .[0].conclusion'
```

Expected: `MERGED <sha>`; `14` (the Keep-alive run row, the 11 Freeze record rows and the two version lines. The Railway line was filled in Task 11, and the D5 rows and the ops-2 gate before ops-3 started); `<the same sha> success`. If CI on `main` is not green for the merge commit, stop.

- [ ] **Step 2 (OWNER): Schedule the window and send the "before" message**

Pick a weekday window the tester agrees to, never Saturday or Sunday. Send (exact copy, with the production address):

> Heads-up: on {weekday, date} between {start} and {end} I'm moving the planning app to a new setup. The address stays https://liturgy-stg.streamlit.app. It may be unavailable for up to 15 minutes. Please don't start a new service during that window — anything you've already saved is safe.

- [ ] **Step 3 (OWNER): Pre-freeze smoke check and recorded versions**

Streamlit Cloud (share.streamlit.io) → `liturgy-stg` → Manage app → logs: the latest build started after the ops-3 merge and finished. On https://liturgy-stg.streamlit.app/: sign in, the church loads, load an archived service, open Settings, and confirm the sidebar shows no "Church" selectbox (the bug-triage row A7 relies on it). If anything fails, stop: do not cut the branch.

From the same build log, copy the Python version and the dependency-install lines (`name==version`) into a note for the agent. Also note, from ⋮ → Settings, the app's Python version and custom subdomain (`liturgy-stg`), and check in ⋮ → Settings → Secrets that the top-level `DB_POOL_SIZE = "3"` and `DB_MAX_OVERFLOW = "3"` are there (ops-1 set them; owner correction 3). Tell the agent only "present" or "missing", never the Secrets text. If they are missing, add both lines and save before the cut: without them the Streamlit app's engine still uses the code defaults 3 and 3 (ops-2), but the runbook says the keys are set.

- [ ] **Step 4 (agent, on the owner's yes): Cut `streamlit-frozen` from the ops-3 merge commit**

```bash
git fetch origin
sha=$(gh pr view claude/ops-3-api-platform-freeze -R bbrown62450/church --json mergeCommit -q .mergeCommit.oid)
git merge-base --is-ancestor "$sha" origin/main && echo "on main"
git log -1 --format='%s' "$sha"
git ls-remote --exit-code origin refs/heads/streamlit-frozen; echo "ls-remote exit $?"
```

Expected: `on main`; `Merge pull request #<n> from bbrown62450/claude/ops-3-api-platform-freeze`; `ls-remote exit 2` (the branch does not exist yet). Then push it (the first line derives the sha again, because shell variables do not carry over between commands):

```bash
sha=$(gh pr view claude/ops-3-api-platform-freeze -R bbrown62450/church --json mergeCommit -q .mergeCommit.oid)
git push origin "$sha:refs/heads/streamlit-frozen"
git ls-remote origin refs/heads/streamlit-frozen
```

Expected: `<sha>	refs/heads/streamlit-frozen`. (AC 20, first half.)

- [ ] **Step 5 (OWNER): Protect `streamlit-frozen`**

GitHub → `bbrown62450/church` → Settings → Branches → Add classic branch protection rule:
- Branch name pattern: `streamlit-frozen`;
- tick "Require a pull request before merging" (required approvals: 0, since you are the only reviewer);
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
  --jq '"checks=\(.required_status_checks.contexts | join(",")) pr=\(.required_pull_request_reviews != null) force_push=\(.allow_force_pushes.enabled) deletion=\(.allow_deletions.enabled)"'
```

Expected: `checks=backend pr=true force_push=false deletion=false`. (AC 20, second half.) If it answers `Branch not protected` (HTTP 404), the rule was created as a ruleset instead. Then check `gh api repos/bbrown62450/church/rules/branches/streamlit-frozen --jq '[.[].type] | sort | join(",")'`, which must include `deletion`, `non_fast_forward`, `pull_request` and `required_status_checks`.

---

### Task 14 (OWNER): Freeze, part 2: serve `liturgy-stg` from `streamlit-frozen`, retire `liturgy`

The ops spec's Freeze steps 4–6, with the app names swapped. Do this inside the window announced in Task 13.

**Files:** none (results go into the runbook in Task 15)

- [ ] **Step 1: Try to change the branch in place**

Streamlit Cloud → `liturgy-stg` → ⋮ → Settings. If the app's settings let you change the branch, set it to `streamlit-frozen`, save, then ⋮ → Reboot app. Go to Step 3.

- [ ] **Step 2: Otherwise, delete and recreate `liturgy-stg` from `streamlit-frozen`**

1. ⋮ → Settings → Secrets: copy the whole Secrets text into your password manager (entry "liturgy-stg Streamlit secrets", with the date). It includes the `[auth]` block and the top-level `DB_POOL_SIZE = "3"` and `DB_MAX_OVERFLOW = "3"`.
2. Note the Python version and the custom subdomain `liturgy-stg` (Task 13, Step 3).
3. ⋮ → Delete app, and confirm.
4. Create app → deploy from GitHub: repository `bbrown62450/church`, branch `streamlit-frozen`, main file path `app.py`, App URL (custom subdomain) `liturgy-stg`. Under Advanced settings, pick the same Python version and paste the Secrets from item 1. Deploy.

The URL is unchanged, so the Google redirect URIs `https://liturgy-stg.streamlit.app/oauth2callback` and `https://liturgy-stg.streamlit.app/` stay valid. The tester's session cookie resets, so they sign in once.

If Streamlit refuses the subdomain `liturgy-stg` (ops spec, Risks item 4), retry after a few minutes. If it is still refused before the window ends, stop and tell the agent: the address would change, and the fallback is the Contingency (Task 16). Do not send the "after" message.

- [ ] **Step 3: Verify the frozen app**

- Manage app → logs: a build from branch `streamlit-frozen` finished without a traceback.
- ⋮ → Settings shows branch `streamlit-frozen`.
- On https://liturgy-stg.streamlit.app/: sign in, the church loads, load an archived service, open Settings. (AC 21.)

- [ ] **Step 4: Delete the unused `liturgy` app and its redirect URIs**

1. Streamlit Cloud → `liturgy` → ⋮ → Delete app, and confirm. (Its sign-in was already broken, and nobody uses it.)
2. Google Cloud Console → APIs & Services → Credentials → the OAuth 2.0 client the Streamlit apps use → Authorized redirect URIs: remove `https://liturgy.streamlit.app/oauth2callback` and `https://liturgy.streamlit.app/`. Keep `https://liturgy-stg.streamlit.app/oauth2callback` and `https://liturgy-stg.streamlit.app/`. Save.
3. After a few minutes, sign out of https://liturgy-stg.streamlit.app/ and sign in again, to confirm that login still works. (AC 22.)

- [ ] **Step 5 (agent, on the owner's yes): Run keep-awake by hand**

```bash
gh workflow run keep-awake --ref main -R bbrown62450/church
sleep 5; gh run list --workflow keep-awake --limit 1 -R bbrown62450/church
gh run watch <run-id> --exit-status -R bbrown62450/church
gh run view <run-id> --log -R bbrown62450/church | grep -E '(visited|FAILED) https://'
```

Expected: the run succeeds, and the grep prints exactly one line, ending in `visited https://liturgy-stg.streamlit.app/`. (The pattern needs `https://` so that it skips the echoed script, whose lines read `visited {url}`.) (AC 22.)

- [ ] **Step 6: Send the "after" message (exact copy)**

> All done — the app is back at the same address. Please sign in once and let me know if anything looks different.

- [ ] **Step 7: Give the agent the results**

For Task 15, the agent needs: the dates of Tasks 13–14; the window; the merge sha and the protection check; which way `liturgy-stg` moved (in place or recreated); the smoke results; the `liturgy` deletion and redirect-URI removal; the keep-awake run URL; the date the "after" message was sent; and, from Task 13, Step 3, the Python and package versions and whether the two pool keys were present in the Secrets.

---

### Task 15 (agent + OWNER): Freeze records

Two small docs-only PRs (clarification 13). Merging PR A is itself "the next merge to `main`", so PR B records whether `liturgy-stg` rebuilt.

**Files:**
- Modify: `docs/ops-runbook.md`

- [ ] **Step 1: Records PR A: everything except the "no new build" row**

```bash
git fetch origin
git switch -c claude/ops-3-freeze-records origin/main
```

In `docs/ops-runbook.md`, fill in the owner's values from Tasks 12–14:

1. `## Keep-alive` → the run-record row: the date, the run URL, and `green; the log shows {"ok":true,"db":"ok"}`.
2. `### Freeze record`: the Result and Date of every row **except** the last one ("After the next merge to `main`, `liturgy-stg` shows no new build"). The `streamlit-frozen` row gets the merge commit sha.
3. `### Recorded Python and package versions`: the Python version, and the `name==version` lines inside the code block.
4. `### Streamlit apps`: replace the whole `liturgy-stg` row and the whole `liturgy` row with:

```markdown
| `liturgy-stg` | https://liturgy-stg.streamlit.app/ | **Production.** The owner and the tester use it. Serves repo `bbrown62450/church`, branch `streamlit-frozen`, main file `app.py`, since <freeze date> (see Freeze record); merges to `main` no longer redeploy it. `keep-awake` keeps it awake. |
| `liturgy` | https://liturgy.streamlit.app/ | **Deleted** on <date>, with its two Google redirect URIs. Its sign-in had failed with `StreamlitAuthError`, and nobody used it. |
```

5. `## Platform limits`: replace the whole bullet that starts "Until the Freeze step deletes the unused `liturgy` app" with:

```markdown
- The unused `liturgy` app was deleted on <date> (see Freeze record), so the
  budget above covers every client: the API and `liturgy-stg` at 3 + 3 each,
  plus the backup job's session and the SQL editor. Real use by one tester is
  2–4 sessions.
```

Replace `<freeze date>` and `<date>` with the real dates. If Task 14 recreated the app, mention it in the `liturgy-stg` row ("recreated on <date>").

```bash
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked'
.venv/bin/python -m pytest -q | tail -1
git add docs/ops-runbook.md
git commit -m "Runbook: Streamlit freeze record (liturgy-stg on streamlit-frozen, liturgy deleted), keepalive run

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -u origin claude/ops-3-freeze-records
gh pr create --base main --head claude/ops-3-freeze-records \
  --title "Runbook: Streamlit freeze record" \
  --body "Records the ops-3 after-merge checks and the Streamlit freeze: streamlit-frozen cut at the ops-3 merge commit and protected; liturgy-stg (production) serves from it; the unused liturgy app and its redirect URIs are gone; keepalive and keep-awake runs are green; Python and package versions recorded. Merging this PR is the 'next merge to main' whose (absent) liturgy-stg rebuild the follow-up records.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```

Expected: the grep prints exactly one line, the last Freeze record row; `346 passed`. Merge on the owner's explicit yes (`gh pr merge --merge claude/ops-3-freeze-records`).

- [ ] **Step 2 (OWNER): Check that the merge did not redeploy `liturgy-stg`**

About 5 minutes after PR A merges: Streamlit Cloud → `liturgy-stg` → Manage app → logs show no new build after the merge time, and https://liturgy-stg.streamlit.app/ still loads. Tell the agent the result and the date. (AC 21.) If a build did start, the app still follows `main`: stop and check its branch setting (Task 14, Step 3).

- [ ] **Step 3: Records PR B: the last row**

```bash
git fetch origin
git switch -c claude/ops-3-freeze-records-2 origin/main
```

Fill the last Freeze record row with "PR #<A's number> merged <date/time>; no new `liturgy-stg` build" and the date. Then:

```bash
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked'; echo "grep exit $?"
.venv/bin/python -m pytest -q | tail -1
git add docs/ops-runbook.md
git commit -m "Runbook: merges to main no longer redeploy liturgy-stg (freeze verified)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -u origin claude/ops-3-freeze-records-2
gh pr create --base main --head claude/ops-3-freeze-records-2 \
  --title "Runbook: freeze verified" \
  --body "Records that merging the freeze-records PR did not rebuild liturgy-stg, so production Streamlit is frozen on streamlit-frozen. Every item of the 'Ops slice' checklist in docs/manual-verification.md has now been run on the production URLs, with results in docs/ops-runbook.md. The ops slice is done.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```

Expected: no marker lines and `grep exit 1`; `346 passed`. Merge on the owner's yes. The ops slice's acceptance criteria 20–22 are then met, and slice work can start on `main`.

---

### Task 16 (only if Task 14 cannot move `liturgy-stg` to `streamlit-frozen`): Contingency

F §6.1.6 and the ops spec's Freeze step 8. Skip this task when Task 14 succeeded.

**Files:**
- Modify: `app.py:2` (remove the FROZEN line)
- Create: `streamlit_tests/test_app_smoke.py`
- Modify: `backend/tests/test_ops_workflows.py` (replace `test_app_py_carries_the_frozen_header`)
- Modify: `docs/ops-runbook.md` → `### Contingency` and `### Freeze record`

**Interfaces:**
- Consumes: `FROZEN_HEADER`, `ROOT` and `_read` from `test_ops_workflows.py`; the `tmp_db` fixture (re-exported by `streamlit_tests/conftest.py`); `streamlit.testing.v1.AppTest`.
- Produces: a green `AppTest` run of `app.py` signed out, which every later PR must keep green.

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
    # liturgy-stg still deploys from main, so app.py must not claim to be frozen.
    assert FROZEN_HEADER not in _read(ROOT / "app.py")
```

Run: `.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py -k frozen_header`
Expected: FAIL (`assert '# FROZEN — …' not in '#!/usr/bin/env python3\n# FROZEN — …'`).

- [ ] **Step 2: Remove the header**

Delete line 2 of `app.py` (`# FROZEN — production runs from branch streamlit-frozen; deleted in slice 7.`), so the file starts with the shebang and then the docstring, as before ops-3.

Run: `.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py -k frozen_header`
Expected: `1 passed`.

- [ ] **Step 3: Add the `AppTest` smoke test**

Create `streamlit_tests/test_app_smoke.py`:

```python
"""Freeze contingency (ops spec, Freeze step 8; F §6.1.6): app.py must keep
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
Expected: `1 passed` (checked on 2026-09-25: the signed-out page renders "Please sign in with Google to continue." and one "Sign in with Google" button in under a second). It passes at once: it is a guard against later PRs breaking `app.py` on `main`.

- [ ] **Step 4: Record the contingency and open the PR**

In `docs/ops-runbook.md` → `### Contingency`, add a line at the end: "Applied on <date>: <why the redeploy was impossible>. `liturgy-stg` stays on `main`; the Freeze policy above does not apply until a later freeze succeeds." In `### Freeze record`, write "not done: contingency applied" in the rows that could not happen.

```bash
.venv/bin/python -m pytest -q | tail -1
git add app.py streamlit_tests/test_app_smoke.py backend/tests/test_ops_workflows.py docs/ops-runbook.md
git commit -m "Freeze contingency: liturgy-stg stays on main; AppTest smoke for app.py (F §6.1.6)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -u origin claude/ops-3-freeze-contingency
gh pr create --base main --head claude/ops-3-freeze-contingency \
  --title "Freeze contingency: keep app.py working on main" \
  --body "liturgy-stg could not be moved to streamlit-frozen (see docs/ops-runbook.md → Contingency). The FROZEN header is removed, and an AppTest smoke test keeps app.py working against main (F §6.1.6).

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```

Expected: `347 passed`. Merge on the owner's yes.

---

## Spec coverage

| Spec item / acceptance criterion (ops-3 and Freeze share) | Task |
|---|---|
| S9 `RequestIdMiddleware`: inbound id kept if `^[A-Za-z0-9-]{8,64}$`, else `uuid4().hex`; contextvar (threadpool sees it); `X-Request-Id` on `http.response.start`; reset in `finally`; non-`http` scopes pass through | 1 |
| S13 / F §1.5: `request_id` in every error body (`_body`), equal to the header; `error_body` alias; the fallback outside the middleware | 1, 2 |
| S9 `UnhandledErrorMiddleware` (pure ASGI): logs method and path (never the query) with the stack; 500 `internal_error` if not started; re-raises if started; no exception text to the client; F §7.3 row 1 | 2 |
| Middleware order in `create_app()` (UnhandledError, RequestId, CORS added in that order; `user_middleware` = CORS, RequestId, UnhandledError); `@app.exception_handler(Exception)` kept as the last resort | 2 |
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
| S7 on `main`: `app.py` FROZEN header; `keep-awake.yml` production-only, i.e. https://liturgy-stg.streamlit.app/ (owner correction 1) | 8 |
| S15: `docs/ops-runbook.md` with the seven sections (environments; lockdown; backups; keep-alive; Streamlit freeze with record, policy, triage, D5 result, versions; platform limits with the Pool Size and pool values; incident response) | 7, 9 (sections), ops-1/ops-2 (the rest) |
| S15: `docs/manual-verification.md` "## Ops slice", with the app names swapped | 9 |
| Testing → `test_middleware.py`: generated 32-hex id; echo; `bad id!`, 7-char and 65-char replaced; 404/401/422 (and 405) bodies' `request_id` == header; CORS on 500 for allowed and other origins; response-already-started unit test; log record from a sync route; `-` outside a request; no nested factories; `LOG_LEVEL=verbose`; `/health/` 404 with no `location`; preflight six headers and `max-age` 600; expose headers; middleware order | 1, 2, 3, 4 |
| Testing → `test_api_app.py::test_unhandled_exception_is_a_generic_500`: `code`, `message`, 32-hex `request_id` == header, no "secret detail" | 1, 2 |
| Testing → `test_startup.py`: `describe_database` without credentials; lifespan logs `Database: dialect=sqlite driver=pysqlite`; production + SQLite raises the exact copy and the `init_db` spy is not called; `APP_ENV=staging` raises; `" Production "` accepted; localhost-only CORS ERROR, Vercel origin none (engine `postgresql://u:p@localhost:1/db`, `init_db` stubbed); development on SQLite has no ERROR; the `SUPABASE_URL` test still passes | 5 |
| Testing → `test_health_ready.py`: 200 without auth and with junk headers; 503 body with `request_id` and a class-only WARNING; sync `def`; memo 9 s / 11 s and 5 s / 6 s; 16 threads → one probe; no `sqlalchemy` import in the route | 6 |
| Testing → `test_ops_workflows.py` (ops-3 part): `keepalive.yml` contains / does not contain; `keep-awake.yml` production only | 7, 8 |
| Exact server messages: `/health/ready` 503; any 500; invalid `APP_ENV`; production non-Postgres; localhost CORS; `Database:` INFO; invalid `LOG_LEVEL`; `keepalive.yml` missing variable | 2, 4, 5, 6, 7 |
| User experience → Browser: `X-Request-Id` readable, `request_id` in bodies, readable 500s, slice-0 messages unchanged; Owner: Railway log lines, keepalive green | 1–4, 12 |
| AC 4 Readiness (200 no auth; 503 `db_unavailable` with `request_id`; memo; one probe; no SQL in the route) | 6, 12 |
| AC 5 Keep-alive (no secret; curls `${API_BASE_URL}/health/ready`; manual run green; `keepalive.py` gone) | 7, 12 |
| AC 9 CORS-safe 500s | 2 |
| AC 10 Request ids (every response inside the app incl. 404, 401, 422, 500; preflight and `ServerErrorMiddleware` excluded; echo and replace; body == header; log record from a sync route) | 1, 2, 3, 4 |
| AC 11 Routing and CORS | 3, 12 |
| AC 16 Startup | 5 |
| AC 18 Railway: `APP_ENV=production` set; deploy log shows the pooler host, no credentials, no CORS ERROR | 11, 12 |
| AC 19 Railway limit recorded (ops-1, from Step 0; owner correction 2): confirmed present | 10 (Step 1) |
| AC 20 Branch: `streamlit-frozen` at the ops-3 merge commit, protected (PR, `backend` check, no force push, no deletion) | 13 |
| AC 21 Frozen app: `liturgy-stg` serves from `streamlit-frozen` at https://liturgy-stg.streamlit.app/; smoke passes; a later merge does not redeploy it (owner correction 1) | 14, 15 |
| AC 22 Staging gone, swapped: `liturgy` deleted and its two redirect URIs removed; `keep-awake` pings only production and its run is green; `app.py` carries the FROZEN header | 8, 14, 15 |
| AC 23 Docs: runbook sections filled; README Operations updated; "Ops slice" checklist run on production URLs (results in the runbook) | 7, 9, 11, 15 |
| AC 24 CI green on the ops-3 PR | 10 |
| AC 26 No `backend/cache.py` or `test_cache.py` | 10 (Step 1) |
| Behavior changes 4, 5, 6, 7, 8, 10, 11, 14, 18 | 2; 1, 4; 3; 3; 5; 6; 7; 13–15; 6 |
| Delivery plan gate: `APP_ENV=production` on Railway before merging | 11 |
| Delivery plan gate: after merging, set `API_BASE_URL` and run keepalive | 12 |
| Freeze step 1: before the freeze, CI green; smoke check including no "Church" selectbox; Python and package versions recorded | 13, 15 |
| Freeze steps 2–3: cut from the ops-3 merge commit; protect | 13 |
| Freeze steps 4–6 (swapped): tester "before" message; redeploy `liturgy-stg` in place or delete-and-recreate with the same subdomain and secrets (including `DB_POOL_SIZE`/`DB_MAX_OVERFLOW`, owner correction 3); delete `liturgy` and its redirect URIs; verify; "after" message | 13, 14 |
| Freeze step 7: policy recorded in the runbook | 9 |
| Freeze step 8: contingency (revert the header, keep `app.py` working on `main`, `AppTest` smoke, record) | 9 (runbook), 16 |
| "What the frozen app inherits": verified before the cut (D5 record, ops-2 gate, CI on the merge commit, ops-3 touches only a comment in Streamlit-run code) | 9, 10 (Step 2), 13 (Step 1) |
| Streamlit coupling and layering: no Streamlit under `backend/`; `db/health` imports no FastAPI; `db/` imports no `api/` | 6, 10 |
| Data access: `/health/ready` touches no table; no church-scoped route added | 6 |
| Owner correction 2 (Step 0 done; Data API already off, no incident; `age` key still ops-1's): nothing re-asked; records already in the runbook; the "Ops slice" item only confirms them | Global Constraints, 1 (Step 1), 9 (Step 6), 10 |
| Owner correction 3 (Pool Size 15, 3 + 3, 14 ≤ 15): unchanged by ops-3; checked on Railway and in the `liturgy-stg` Secrets; carried into a recreated `liturgy-stg`; recorded in the environments table; `liturgy`'s connections freed by its deletion | 9, 11, 13, 14, 15 |

**Deliberately not in ops-3** (ops spec delivery plan and owner corrections):
- ops-1 and ops-2 work: `backup.yml`, the `age` key and recipients, the D5 fix, the dead modules, `.env.example`, `shadcn`, `insert_ignore`, `ensure_user`, the identity cache and the pool code.
- Slice 1:
  - Alembic, `railway.toml` and moving Railway's health check to `/health/ready`;
  - the production schema-behind gate (`details.reason = "schema_behind"`), the revision and RLS startup checks, removing `init_db()` from the lifespan;
  - `domain_errors.py`, `fields`/`details`, the Pydantic 422 mapping;
  - `test_route_guards.py` (its `PUBLIC` allowlist must hold `/health` and `/health/ready`);
  - `frontend/src/lib/api/errors.ts` and `ApiError.requestId` with "(Ref: …)";
  - the Postgres CI job and the no-network fixture.
- Slice 2: `backend/cache.py`, `test_cache.py` and the rate limiter.
- Slice 5b: the switchover banner on `streamlit-frozen`.
- Slice 7: deleting `keep-awake.yml`, the README and manual-verification rewrite, the external uptime monitor.
