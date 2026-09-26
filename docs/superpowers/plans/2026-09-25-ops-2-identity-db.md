# Ops-2: Identity Race Fix, Identity Cache and Pool Settings — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship PR ops-2 of the ops slice: first sign-ins no longer race, and authenticated requests stop writing `users` on every call. The pieces are `db/upsert.py`, `repos.users.ensure_user`, a thin `auth.upsert_from_claims` wrapper, the removal of `repos.users.upsert_user`, and a success-only identity cache in `api/deps.py`. The PR also sizes the Postgres pool for the Supabase pooler (3 + 3, `connect_timeout=10`). Then it passes the gate: the tester uses Streamlit for a day and nothing regresses.

**Architecture:** One identity write path serves both apps. `repos.users.ensure_user` runs `INSERT … ON CONFLICT (email) DO NOTHING`, then a SELECT, then at most one UPDATE, all in one transaction. The UPDATE runs only for a changed truthy profile value, or when `last_login_at` is more than an hour old. `insert_ignore` picks the Postgres or SQLite `insert()` construct from the process engine. Streamlit and `migrate_to_db.py` keep calling `auth.upsert_from_claims`, now a wrapper with the same signature. The API's `get_current_user` still verifies the token on every request. In front of `ensure_user` it keeps a thread-safe LRU cache with a 300 s TTL, keyed by email, so an unchanged profile costs no database work. `db/engine.py` reads `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` (defaults 3 and 3) and sets `connect_timeout=10` for Postgres. Streamlit still deploys from `main`, so every change reaches the tester when the PR merges. That is why the gate exists.

**Tech Stack:** Python 3.11, SQLAlchemy 2.1 (`sqlalchemy.dialects.postgresql.insert` / `sqlite.insert` with `on_conflict_do_nothing`), FastAPI 0.141 / Starlette 1.7 `TestClient`, psycopg2, pytest, SQLite (tests), Supabase Postgres 17.6 through the Supavisor session pooler (production).

**Spec:** `docs/superpowers/specs/2026-09-25-slice-ops-cleanup-design.md` ("the ops spec"). Foundations: `docs/superpowers/specs/2026-09-25-migration-foundations-design.md` ("F", §2.4, §2.6 item 6, §2.7, §7.3). Inventory: `docs/superpowers/specs/2026-09-25-streamlit-migration-inventory.md` ("inv"). Previous PR: `docs/superpowers/plans/2026-09-25-ops-1-backups-cleanup-d5.md` ("the ops-1 plan"). This plan assumes ops-1 and its records PR are merged exactly as written.

## Global Constraints

- Run every command from the repo root with `.venv/bin/python` (Python 3.11). The system `python3` is 3.9 and has no deps. If `.venv` is missing: `/Users/beaubrown/.local/bin/python3.11 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt`.
- Backend test command: `.venv/bin/python -m pytest -q` (pytest.ini: `pythonpath = . backend`, `testpaths = backend/tests streamlit_tests`). Baseline after ops-1: `230 passed`. This plan adds 47 tests, for `277 passed`. If the baseline differs because a later docs-only PR added tests, use your number and add the same deltas.
- Every commit message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Commits follow TDD: test first, watch it fail, then code.
- Nothing under `backend/` imports `streamlit`. The new modules `db/upsert.py` and `api/identity_cache.py` import neither Streamlit nor FastAPI. `db/` never imports `api/`: pool settings are read from the environment inside `db/engine.py`, the same way `DATABASE_URL` is.
- No schema changes, no Alembic, no data migration (slice 1).
- Never create `backend/cache.py` or `backend/tests/test_cache.py` (slice 2). The identity cache is the private class in `backend/api/identity_cache.py`.
- Identity rules (F §2.4):
  - users are matched by the normalized email (`strip().lower()`);
  - the API never passes `google_sub` (`api/security.py` `claims_to_profile`);
  - `LAST_SEEN_RESOLUTION = timedelta(hours=1)`;
  - a falsy name or picture never blanks a stored one;
  - the cache is `IdentityCache(maxsize=1024, ttl=300)` and stores only the result of an `ensure_user` call that returned;
  - token verification runs on every request and is never cached;
  - `require_church` → `validate_active_church` runs on every request and is never cached.
- `auth.upsert_from_claims(claims: dict) -> uuid.UUID` keeps its signature and its error text `OIDC claims are missing an email address.` (callers: `streamlit_auth.py:28`, `backend/migrate_to_db.py:130`).
- **Pool budget (owner correction 3, 2026-09-25; overrides the spec's 5 and 5).** The Supabase session pooler (Supavisor, Nano compute) has Pool Size 15 and max client connections 200. The spec's trigger 2 × (5 + 5) + 2 = 22 > 15 fires. So `DEFAULT_POOL_SIZE = 3` and `DEFAULT_MAX_OVERFLOW = 3`: 2 × (3 + 3) + 2 = 14 ≤ 15. The same values are in `backend/.env.example` (ops-1), on Railway, and in the `liturgy-stg` Streamlit Secrets (ops-1 plan, Task 9, Step 1; checked again in Task 9 here). Postgres also gets `pool_pre_ping=True`, `pool_recycle=1800` and `connect_args={"connect_timeout": 10}`.
- Exact copy (ops spec, "Exact server messages"), raised as `ValueError` when the engine is created: `DB_POOL_SIZE must be an integer >= 1 (got '{value}').` · `DB_MAX_OVERFLOW must be an integer >= 0 (got '{value}').`
- **Streamlit apps (owner correction 1, 2026-09-25; reverses the ops spec).** `liturgy-stg`, https://liturgy-stg.streamlit.app, is the production Streamlit app: the owner and the tester use it. During ops-2 it still deploys from `main`, so the gate and every smoke check use it. `liturgy`, https://liturgy.streamlit.app, is unused, and its Google sign-in already fails with `StreamlitAuthError`. ops-2 does not touch it: the Freeze step deletes it and its redirect URIs.
- **Step 0 is done (owner correction 2).** ops-1 wrote the results into `docs/ops-runbook.md`; never ask the owner to redo them:
  - the Data API was already off (REST and GraphQL with the anon key return HTTP 503 `PGRST002`, no rows), so there was no incident;
  - every `public` table is owned by `postgres`, and `current_user` `postgres` has `rolbypassrls = true`;
  - RLS and the REVOKEs were applied on 2026-09-25, and afterwards both apps still loaded the owner's church;
  - the server is 17.6, recorded as `- Postgres server major: 17`;
  - Railway allows 5 minutes idle and up to 15 minutes while data flows.
  ops-2 changes none of this. The one open Step 0 item, the owner's `age` key pair, belongs to ops-1's backups (ops-1 plan, Task 0), not to ops-2.
- The agent never sees or types a secret (database URLs, keys, tokens). Opening a PR, merging, reverting and messaging the tester are outward-facing: get the owner's explicit yes first.
- These tests stay unchanged and green: `test_auth.py`, `test_api_me.py`, `test_api_app.py`, `test_api_security.py`, `test_docs.py`, `test_ci_workflow.py`, `test_no_streamlit_in_core.py`, `test_keepalive.py`, and all of `streamlit_tests/`. `test_users_repo.py` is ported (Task 3), as the spec says.
- **Not in ops-2** (other PRs and slices; do not touch):
  - ops-3: `api/middleware.py`, `request_id`, CORS lists, `redirect_slashes`, `api/logging_config.py`, `api/startup.py`, `api/settings.py`, `api/main.py`, `api/errors.py`, `db/health.py` and `/health/ready`, `keepalive.yml`, `keepalive.py` (it builds its own engine, so the ops-2 pool settings do not reach it), `keep-awake.yml` (which then pings only https://liturgy-stg.streamlit.app/), the `app.py` FROZEN header, the README and `docs/manual-verification.md`;
  - the Freeze step;
  - slice 1: the `@pytest.mark.postgres` re-run of the race test (it should include the Streamlit `google_sub` case of the Task 8 smoke) and the Postgres CI job;
  - slice 2: `backend/cache.py`;
  - slice 7: `migrate_to_db.py` and the `db/engine.py` default URL.

## Spec clarifications (recorded, not deviations of intent)

1. **Pool numbers (owner correction 3).** Wherever the spec says 5 and 5 (Backend changes → Engine and pool; Testing → `test_engine.py`; AC 17; Behavior change 9; "What the frozen app inherits"), this plan uses 3 and 3. A new test in `test_ops_workflows.py` ties the code defaults to the runbook's recorded Pool Size (15) and to `backend/.env.example`, so the three cannot drift apart.
2. **Streamlit app names (owner correction 1).** The spec's gate says "the tester uses Streamlit (still deployed from `main`)". Here that means `liturgy-stg`. The runbook's new subsection "What the frozen app inherits from ops-2" names it.
3. **`FakeClock` lives in `backend/tests/conftest.py`** (spec: conftest). `test_identity_cache.py` imports it with `from tests.conftest import FakeClock`, the same import style as `tests.jwt_helpers`. `backend/` has no `__init__.py`, so pytest registers the conftest as `tests.conftest` and the import gets the same module.
4. **The API concurrency test uses a barrier.** The spec asks for two concurrent `/me` calls on a `ThreadPoolExecutor`. Without coordination the second call may simply hit the cache the first one filled, and the test would prove nothing. So a 2-party `threading.Barrier` wraps `api.deps.ensure_user`, and both requests are guaranteed to miss the cache and run `ensure_user` together. This test guards the new API path; it is not the proof that the old path raced. Its red phase is only `AttributeError` (no `api.deps.ensure_user` yet), and after Task 4 the old path already goes through the race-free `ensure_user`. The regression proof for the race is Task 2's `test_concurrent_first_calls_create_one_row`.
5. **Statement counting.** A `before_cursor_execute` listener (spec) records each statement with its whitespace collapsed. A users INSERT starts with `INSERT INTO users `, a users UPDATE starts with `UPDATE users `, and a users SELECT starts with `SELECT ` and contains the whole word `FROM users`. `/me`'s church listing (`FROM churches JOIN memberships`) is not counted. After the TTL, `ensure_user` also runs its no-op `INSERT … ON CONFLICT DO NOTHING`. The spec's TTL assertion (one SELECT, no UPDATE) does not count it, and neither does this plan.
6. **Removal guard.** Task 3 adds `test_upsert_user_is_folded_into_ensure_user` (`not hasattr(repos.users, "upsert_user")`), so the removal has a failing test first. The five ported tests keep their assertions.
7. **`google_sub` normalization.** `ensure_user` strips `google_sub` and turns an empty one into None (spec step 2), as `upsert_from_claims` did.
8. **Comment fixes.** `db/engine.py:43` (spec), `db/models.py:42` (spec), plus the `claims_to_profile` docstring in `api/security.py:105-115`. That docstring named `auth.upsert_from_claims` as its caller, which stops being true in Task 6.
9. **Production precondition.** On Postgres, `ON CONFLICT (email)` needs a unique constraint or a non-partial unique index on exactly `users(email)`. There is no local Postgres and no Postgres CI job until slice 1. So the owner checks production's unique indexes on `users` before merging (Task 9, Step 1; a `UNIQUE` constraint shows up there as its backing index), and the agent runs a throwaway Postgres 17 smoke test when Docker is available (Task 8, Step 3).
10. **Runbook.** ops-1 recorded the Pool Size, the arithmetic and the values set. ops-2 replaces the two "until ops-2" bullets in "Platform limits", which become stale. It also adds "What the frozen app inherits from ops-2" with the gate record, which the Freeze step relies on ("verifies each before the branch is cut").
11. **Blank or padded settings.** `_int_env` strips the value; blank or unset means the default. The message shows the stripped value.
12. **`google_sub` is written by the UPDATE, not the INSERT (changes spec step 3's INSERT; same intent: a race-free first sign-in).** The spec's INSERT carries `google_sub`. On Postgres its `ON CONFLICT (email)` arbiter does not cover the separate unique index `users_google_sub_key`. So two concurrent first Streamlit sign-ins for the same new Google account (two tabs) can both pass the arbiter pre-check. Postgres checks every non-arbiter unique index normally, so the second then waits for the first to commit and raises `IntegrityError` on `users_google_sub_key`. The SQLite race test cannot show this, because SQLite serializes writers. Leaving `google_sub` out of the INSERT lets step 5 collect it and step 6's UPDATE write it. A concurrent UPDATE of the same row waits on the row lock and does not conflict with itself. The cost is one extra UPDATE on a user's first Streamlit sign-in. The spec's note still holds: a `google_sub` already used by another email raises `IntegrityError`, now from the UPDATE, and the whole transaction rolls back. The API path never passes `google_sub`, so it is unaffected. `test_ensure_user_stores_google_sub_only_when_passed` pins this: the first call runs one INSERT and one UPDATE.
13. **A revert keeps the gate honest.** The gate table is added in the ops-2 PR itself (Task 7), so reverting the merge also removes it. The revert PR therefore adds, in a separate commit, an "ops-2 regression" paragraph under the runbook's Incident record that says the gate FAILED and ops-3 must not start (Task 10, Step 4). The re-land PR starts by reverting the revert, which brings back the code, the pool bullets and the gate table. Task 11 checks that the gate heading exists, so "no `[owner` markers" cannot pass just because the table is gone.

## File Map

```
backend/db/upsert.py                     NEW: insert_ignore(table, *, dialect_name=None)
backend/repos/users.py                   + UserRow, LAST_SEEN_RESOLUTION, ensure_user(); - upsert_user()
backend/db/models.py                     comment on users.last_login_at (line 42)
backend/auth.py                          upsert_from_claims becomes a wrapper over ensure_user (same signature)
backend/api/identity_cache.py            NEW: CachedIdentity, IdentityCache (thread-safe LRU + TTL, success-only)
backend/api/deps.py                      _identity_cache, clear_identity_cache(), cached get_current_user
backend/api/security.py                  claims_to_profile docstring (names its real caller)
backend/db/engine.py                     DEFAULT_POOL_SIZE/DEFAULT_MAX_OVERFLOW, _int_env, _engine_kwargs, comments
backend/tests/conftest.py                + FakeClock, autouse clear_identity_cache, identity_clock fixture
backend/tests/test_upsert.py             NEW (4 tests)
backend/tests/test_identity.py           NEW (26 tests: ensure_user, race, wrapper, API identity)
backend/tests/test_identity_cache.py     NEW (6 tests)
backend/tests/test_users_repo.py         ported from upsert_user to ensure_user (+1 removal guard)
backend/tests/test_engine.py             + 9 pool tests
backend/tests/test_ops_workflows.py      + pool budget vs runbook and .env.example (1 test)
docs/ops-runbook.md                      Platform limits pool bullets; "What the frozen app inherits from ops-2"
```

---

### Task 1: `db/upsert.py` — `insert_ignore` (S8)

**Files:**
- Create: `backend/db/upsert.py`
- Test: `backend/tests/test_upsert.py` (new)

**Interfaces:**
- Consumes: `db.engine.get_engine() -> Engine` (the process engine that `SessionLocal` is bound to, including after `reset_engine_for_tests`); `db.models.User`; fixture `tmp_db`.
- Produces: `db.upsert.insert_ignore(table: Table | type, *, dialect_name: str | None = None) -> postgresql.Insert | sqlite.Insert`. Callers chain `.values(...).on_conflict_do_nothing(index_elements=[...])`. It raises `NotImplementedError` for any dialect other than `postgresql` and `sqlite`. Later users: Task 2 (`ensure_user`), slice 1 (`insert_ignore(Membership)`), slice 5a (`insert_ignore(HymnUsage.__table__)`).

- [ ] **Step 1: Start the branch and check the baseline**

```bash
git fetch origin
git switch -c claude/ops-2-identity-db origin/main
test -f docs/ops-runbook.md && test -f backend/tests/test_ops_workflows.py \
  && grep -qx 'DB_POOL_SIZE=3' backend/.env.example && echo "ops-1 is on main"
grep -c '^- Supabase session pooler (Supavisor) Pool Size: 15' docs/ops-runbook.md
.venv/bin/python -m pytest -q | tail -1
```
Expected: `ops-1 is on main`, then `1`, then `230 passed`. If the first line is missing, stop: ops-2 builds on ops-1.

If `git switch` refuses because an untracked file would be overwritten (for example an untracked copy of the ops-1 plan, which `main` now has), move that copy out of the way (`mv docs/superpowers/plans/2026-09-25-ops-1-backups-cleanup-d5.md "${TMPDIR:-/tmp}/"`) and switch again. Leave this plan file untracked until Task 8 commits it.

- [ ] **Step 2: Write the failing tests**

Create `backend/tests/test_upsert.py`:

```python
"""db.upsert.insert_ignore: INSERT … ON CONFLICT DO NOTHING on SQLite and Postgres."""
import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.dialects import postgresql, sqlite

from db import session_scope
from db.models import User
from db.upsert import insert_ignore


def _insert_user(target, email="dup@example.com"):
    return (
        insert_ignore(target)
        .values(id=uuid.uuid4(), email=email)
        .on_conflict_do_nothing(index_elements=["email"])
    )


def _user_count():
    with session_scope() as s:
        return s.execute(select(func.count()).select_from(User)).scalar_one()


def test_insert_ignore_inserts_once_and_ignores_the_duplicate(tmp_db):
    stmt = _insert_user(User.__table__)
    assert isinstance(stmt, sqlite.Insert)          # dialect taken from the process engine
    with session_scope() as s:
        s.execute(stmt)
    with session_scope() as s:
        s.execute(_insert_user(User.__table__))     # same email, new id: ignored, no IntegrityError
    assert _user_count() == 1


def test_insert_ignore_accepts_a_mapped_class(tmp_db):
    with session_scope() as s:
        s.execute(_insert_user(User))
        s.execute(_insert_user(User))
    assert _user_count() == 1


def test_insert_ignore_rejects_other_dialects():
    with pytest.raises(NotImplementedError):
        insert_ignore(User.__table__, dialect_name="mysql")


def test_insert_ignore_compiles_on_conflict_do_nothing_for_postgres():
    stmt = (
        insert_ignore(User.__table__, dialect_name="postgresql")
        .values(id=uuid.uuid4(), email="dup@example.com")
        .on_conflict_do_nothing(index_elements=["email"])
    )
    assert isinstance(stmt, postgresql.Insert)
    sql = str(stmt.compile(dialect=postgresql.dialect()))   # compiles without connecting
    assert "ON CONFLICT (email) DO NOTHING" in sql
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_upsert.py`
Expected: collection error `ModuleNotFoundError: No module named 'db.upsert'`, `1 error`.

- [ ] **Step 4: Create `backend/db/upsert.py`**

```python
"""Dialect-aware INSERT that supports ``.on_conflict_do_nothing()`` (F §2.4).

SQLAlchemy has no portable "insert or ignore": PostgreSQL and SQLite each have
their own ``insert()`` construct with ``on_conflict_do_nothing``. insert_ignore
picks the right one for the process engine, so callers write one statement:

    insert_ignore(User.__table__).values(...).on_conflict_do_nothing(index_elements=["email"])

Used by repos.users.ensure_user (ops); later by membership accept (slice 1)
and hymn usage recording (slice 5a).
"""
from typing import Optional, Union

from sqlalchemy import Table
from sqlalchemy.dialects import postgresql, sqlite

from db.engine import get_engine

_INSERTS = {"postgresql": postgresql.insert, "sqlite": sqlite.insert}


def insert_ignore(
    table: Union[Table, type], *, dialect_name: Optional[str] = None
) -> Union[postgresql.Insert, sqlite.Insert]:
    """Dialect insert() that supports .on_conflict_do_nothing(); postgresql or sqlite only.

    `table` is a Table or a mapped class. The dialect is the process engine's
    (get_engine(), the one SessionLocal is bound to); `dialect_name` overrides
    it only so tests can compile the Postgres form without connecting.
    """
    name = dialect_name or get_engine().dialect.name
    try:
        make_insert = _INSERTS[name]
    except KeyError:
        raise NotImplementedError(
            f"insert_ignore supports postgresql and sqlite, not {name!r}"
        ) from None
    return make_insert(table)
```

`db/__init__.py` is unchanged: callers import `from db.upsert import insert_ignore`, and `test_engine.py::test_public_imports_are_reexported` keeps its list.

- [ ] **Step 5: Run the tests and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_upsert.py
.venv/bin/python -m pytest -q | tail -1
```
Expected: `4 passed`, then `234 passed`.

- [ ] **Step 6: Commit**

```bash
git add backend/db/upsert.py backend/tests/test_upsert.py
git commit -m "Add db.upsert.insert_ignore: dialect insert with ON CONFLICT DO NOTHING (F §2.4)

Picks the postgresql or sqlite insert() construct from the process engine,
so one statement works on Supabase and in the SQLite tests.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: `repos.users.ensure_user`, the race fix and hourly `last_login_at` (S8, F §7.3)

**Files:**
- Modify: `backend/repos/users.py:1-12` (imports and `_normalize_email`; `ensure_user` goes after them)
- Modify: `backend/db/models.py:42` (comment)
- Test: `backend/tests/test_identity.py` (new)

**Interfaces:**
- Consumes: `db.upsert.insert_ignore` (Task 1); `db.session_scope`; `db.models.User`; fixture `tmp_db`.
- Produces, in `repos.users`:
  - `UserRow` (frozen dataclass: `id: uuid.UUID`, `email: str`, `name: str | None`, `picture: str | None`, `last_login_at: datetime | None`, timezone-aware UTC);
  - `LAST_SEEN_RESOLUTION = timedelta(hours=1)`;
  - `ensure_user(email: str, name: str | None = None, picture: str | None = None, *, google_sub: str | None = None, now: datetime | None = None, session: Session | None = None) -> UserRow`. It raises `ValueError("email is required")` for an empty email. Its INSERT never carries `google_sub`; the UPDATE writes it (clarification 12).
- Produces, in `backend/tests/test_identity.py` (used by Tasks 4 and 6): `NOW`, `_utc(value)`, `_stored(email) -> User`, `_user_count() -> int`, and the context manager `users_statements(engine)`. That manager yields a dict which, after the `with` block, holds `{"insert": n, "update": n, "select": n}` for the `users` table.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_identity.py`:

```python
"""Identity (ops slice, F §2.4): repos.users.ensure_user, the race fix and fewer writes."""
import re
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import event, func, select, update

from db import session_scope
from db.models import User
from repos.users import LAST_SEEN_RESOLUTION, UserRow, ensure_user, get_user_by_email

NOW = datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)


def _utc(value):
    """SQLite hands back naive datetimes; they were written as UTC."""
    return value if value is None or value.tzinfo else value.replace(tzinfo=timezone.utc)


def _stored(email):
    with session_scope() as s:
        return s.execute(select(User).where(User.email == email)).scalar_one()


def _user_count():
    with session_scope() as s:
        return s.execute(select(func.count()).select_from(User)).scalar_one()


@contextmanager
def users_statements(engine):
    """Record every SQL statement on `engine`; yields counts of users INSERT/SELECT/UPDATE."""
    seen = []

    def _record(_conn, _cursor, statement, _params, _context, _executemany):
        seen.append(" ".join(statement.split()))

    counts = {}
    event.listen(engine, "before_cursor_execute", _record)
    try:
        yield counts
    finally:
        event.remove(engine, "before_cursor_execute", _record)
        counts["insert"] = sum(s.startswith("INSERT INTO users ") for s in seen)
        counts["update"] = sum(s.startswith("UPDATE users ") for s in seen)
        counts["select"] = sum(s.startswith("SELECT ") and bool(re.search(r"\bFROM users\b", s))
                               for s in seen)


# --- ensure_user ------------------------------------------------------------

def test_ensure_user_creates_a_normalized_user_stamped_now(tmp_db):
    row = ensure_user("  New.Person@Example.COM ", "New Person", "https://x/p.png", now=NOW)
    assert isinstance(row, UserRow)
    assert row.email == "new.person@example.com"
    assert (row.name, row.picture, row.last_login_at) == ("New Person", "https://x/p.png", NOW)
    user = _stored("new.person@example.com")
    assert user.id == row.id
    assert _utc(user.created_at) == NOW
    assert _utc(user.last_login_at) == NOW
    assert user.google_sub is None                     # the API path never passes it


def test_ensure_user_stores_google_sub_only_when_passed(tmp_db):
    with users_statements(tmp_db) as first:
        ensure_user("streamlit@example.com", google_sub="  google-sub-9 ")
    # The UPDATE writes google_sub, never the INSERT: ON CONFLICT (email) does not
    # cover users_google_sub_key, so concurrent first sign-ins would collide on it.
    assert (first["insert"], first["update"]) == (1, 1)
    assert _stored("streamlit@example.com").google_sub == "google-sub-9"
    ensure_user("streamlit@example.com")               # a later call without it keeps it
    assert _stored("streamlit@example.com").google_sub == "google-sub-9"


def test_ensure_user_is_idempotent_across_case(tmp_db):
    first = ensure_user("Pastor@Example.com", now=NOW)
    second = ensure_user("pastor@EXAMPLE.com", now=NOW)
    assert first.id == second.id
    assert _user_count() == 1


def test_ensure_user_updates_name_and_picture_only_when_truthy_and_different(tmp_db):
    ensure_user("pat@example.com", "Pat", "https://x/1.png", now=NOW)
    with users_statements(tmp_db) as same:
        row = ensure_user("pat@example.com", "Pat", "https://x/1.png", now=NOW)
    assert same["update"] == 0
    with users_statements(tmp_db) as changed:
        row = ensure_user("pat@example.com", "Pat Tor", "https://x/2.png", now=NOW)
    assert changed["update"] == 1                      # one UPDATE for both fields
    assert (row.name, row.picture) == ("Pat Tor", "https://x/2.png")
    user = _stored("pat@example.com")
    assert (user.name, user.picture) == ("Pat Tor", "https://x/2.png")


@pytest.mark.parametrize("falsy", [None, "", "   "])
def test_a_falsy_name_or_picture_never_blanks_the_stored_one(tmp_db, falsy):
    ensure_user("pat@example.com", "Pat", "https://x/1.png", now=NOW)
    row = ensure_user("pat@example.com", falsy, falsy, now=NOW)
    assert (row.name, row.picture) == ("Pat", "https://x/1.png")
    user = _stored("pat@example.com")
    assert (user.name, user.picture) == ("Pat", "https://x/1.png")


def test_last_login_at_is_written_at_most_hourly(tmp_db):
    assert LAST_SEEN_RESOLUTION == timedelta(hours=1)
    ensure_user("pat@example.com", now=NOW)
    with users_statements(tmp_db) as within_the_hour:
        row = ensure_user("pat@example.com", now=NOW + timedelta(minutes=59))
    assert within_the_hour["update"] == 0
    assert row.last_login_at == NOW
    with users_statements(tmp_db) as after_the_hour:
        row = ensure_user("pat@example.com", now=NOW + timedelta(minutes=61))
    assert after_the_hour["update"] == 1
    assert row.last_login_at == NOW + timedelta(minutes=61)
    assert _utc(_stored("pat@example.com").last_login_at) == NOW + timedelta(minutes=61)


def test_a_naive_stored_last_login_at_is_read_as_utc(tmp_db):
    ensure_user("pat@example.com", now=NOW)
    with session_scope() as s:                         # what SQLite (or an old row) holds: no tzinfo
        s.execute(update(User).where(User.email == "pat@example.com")
                  .values(last_login_at=datetime(2026, 9, 25, 11, 30)))
    with users_statements(tmp_db) as thirty_minutes:
        ensure_user("pat@example.com", now=NOW)        # 11:30 UTC is 30 min before NOW
    assert thirty_minutes["update"] == 0
    with users_statements(tmp_db) as sixty_one_minutes:
        ensure_user("pat@example.com", now=NOW + timedelta(minutes=31))
    assert sixty_one_minutes["update"] == 1


@pytest.mark.parametrize("email", ["", "   ", None])
def test_ensure_user_requires_an_email(tmp_db, email):
    with pytest.raises(ValueError, match="email is required"):
        ensure_user(email)
    assert _user_count() == 0


def test_ensure_user_joins_the_callers_transaction(tmp_db):
    with pytest.raises(RuntimeError):
        with session_scope() as s:
            row = ensure_user("tx@example.com", "Tx", session=s)
            assert s.execute(select(User.id).where(User.email == "tx@example.com")).scalar_one() == row.id
            raise RuntimeError("roll back the outer scope")
    assert get_user_by_email("tx@example.com") is None


def test_concurrent_first_calls_create_one_row(tmp_db):
    """F §7.3: the first-request duplicate-email race. Eight threads released
    together all get the same id, and exactly one row exists. (Slice 1 adds a
    @pytest.mark.postgres copy.)"""
    workers = 8
    barrier = threading.Barrier(workers)
    ids, errors = [], []

    def call():
        try:
            barrier.wait(timeout=10)
            ids.append(ensure_user("race@example.com", "Racer").id)
        except Exception as exc:  # noqa: BLE001 - any failure fails the test below
            errors.append(repr(exc))

    threads = [threading.Thread(target=call) for _ in range(workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert errors == []
    assert len(ids) == workers and len(set(ids)) == 1
    assert _user_count() == 1
```

The race test has teeth. With today's select-then-insert code (`auth.upsert_from_claims`), the same eight-thread barrier produced `IntegrityError` on every one of five runs (checked 2026-09-25).

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_identity.py`
Expected: collection error `ImportError: cannot import name 'LAST_SEEN_RESOLUTION' from 'repos.users'`, `1 error`.

- [ ] **Step 3: Add `ensure_user` to `backend/repos/users.py`**

Replace lines 1-12 of `backend/repos/users.py`:

```python
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select

from db import session_scope
from db.models import User


def _normalize_email(email) -> str:
    return (email or "").strip().lower()
```

with:

```python
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from db import session_scope
from db.models import User
from db.upsert import insert_ignore

# users.last_login_at means "last seen, to the hour": ensure_user rewrites it
# only when the stored value is older than this (F §2.4).
LAST_SEEN_RESOLUTION = timedelta(hours=1)

_users = User.__table__


@dataclass(frozen=True)
class UserRow:
    id: uuid.UUID
    email: str
    name: Optional[str]
    picture: Optional[str]
    last_login_at: Optional[datetime]


def _normalize_email(email) -> str:
    return (email or "").strip().lower()


def _clean(value: Optional[str]) -> Optional[str]:
    """Strip; an empty string becomes None."""
    return (value or "").strip() or None


def _as_utc(value: Optional[datetime]) -> Optional[datetime]:
    """SQLite returns naive datetimes; every stored value was written as UTC."""
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)


def ensure_user(
    email: str,
    name: Optional[str] = None,
    picture: Optional[str] = None,
    *,
    google_sub: Optional[str] = None,
    now: Optional[datetime] = None,
    session: Optional[Session] = None,
) -> UserRow:
    """Return the users row for `email`, creating it if needed (F §2.4).

    One transaction (the caller's `session`, or its own scope):
    1. INSERT ... ON CONFLICT (email) DO NOTHING, so concurrent first calls
       never raise IntegrityError. The INSERT carries no google_sub: the
       arbiter covers only the email, not users_google_sub_key;
    2. SELECT the row by email;
    3. one UPDATE, only when a truthy name, picture or google_sub differs from
       the stored value, or last_login_at is NULL or older than
       LAST_SEEN_RESOLUTION. Concurrent UPDATEs of the same row wait on its
       row lock instead of conflicting.
    A falsy value never blanks a stored one. Only Streamlit passes google_sub
    (the API never does, see api.security.claims_to_profile); a google_sub
    already used by another email still raises IntegrityError (from the
    UPDATE), and the transaction rolls back.
    """
    normalized = _normalize_email(email)
    if not normalized:
        raise ValueError("email is required")
    name, picture, google_sub = _clean(name), _clean(picture), _clean(google_sub)
    now = now or datetime.now(timezone.utc)
    if session is not None:
        return _ensure_user(session, normalized, name, picture, google_sub, now)
    with session_scope() as own:
        return _ensure_user(own, normalized, name, picture, google_sub, now)


def _ensure_user(session, email, name, picture, google_sub, now) -> UserRow:
    session.execute(
        insert_ignore(_users)
        .values(id=uuid.uuid4(), email=email, name=name, picture=picture,
                created_at=now, last_login_at=now)   # no google_sub: see step 3
        .on_conflict_do_nothing(index_elements=["email"])
    )
    row = session.execute(
        select(_users.c.id, _users.c.email, _users.c.name, _users.c.picture,
               _users.c.google_sub, _users.c.last_login_at)
        .where(_users.c.email == email)
    ).one()
    changes = {}
    if name and name != row.name:
        changes["name"] = name
    if picture and picture != row.picture:
        changes["picture"] = picture
    if google_sub and google_sub != row.google_sub:
        changes["google_sub"] = google_sub
    last_seen = _as_utc(row.last_login_at)
    if last_seen is None or last_seen < now - LAST_SEEN_RESOLUTION:
        changes["last_login_at"] = last_seen = now
    if changes:
        session.execute(update(_users).where(_users.c.id == row.id).values(**changes))
    return UserRow(
        id=row.id,
        email=row.email,
        name=changes.get("name", row.name),
        picture=changes.get("picture", row.picture),
        last_login_at=last_seen,
    )
```

The rest of the file (`_to_dict`, `upsert_user`, `get_user`, `get_user_by_email`) stays for now. After this step `_to_dict` starts at line 114, and `upsert_user` spans lines 124-156, followed by two blank lines. Task 3 deletes it.

- [ ] **Step 4: Comment `last_login_at` in `backend/db/models.py`**

Replace line 42:

```python
    last_login_at = Column(DateTime(timezone=True))
```

with:

```python
    # Last seen, to the hour (see repos.users.LAST_SEEN_RESOLUTION).
    last_login_at = Column(DateTime(timezone=True))
```

The column is unchanged, and nothing reads it (`grep -rn last_login_at --include='*.py' backend app.py streamlit_*` finds only writers and tests).

- [ ] **Step 5: Run the tests, the race test repeatedly, and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_identity.py
for i in $(seq 1 20); do .venv/bin/python -m pytest -q -p no:cacheprovider \
  backend/tests/test_identity.py::test_concurrent_first_calls_create_one_row | tail -1; done | grep -c "1 passed"
.venv/bin/python -m pytest -q | tail -1
```
Expected: `14 passed`; then `20` (no flaky run); then `248 passed`.

- [ ] **Step 6: Commit**

```bash
git add backend/repos/users.py backend/db/models.py backend/tests/test_identity.py
git commit -m "Add repos.users.ensure_user: race-free insert, hourly last_login_at (F §2.4, §7.3)

INSERT ... ON CONFLICT (email) DO NOTHING, then SELECT, then one UPDATE only
for a changed truthy name/picture/google_sub or a last_login_at older than an
hour. Eight concurrent first calls now create one row instead of raising
IntegrityError. google_sub is written by the UPDATE, not the INSERT, so the
users_google_sub_key index cannot break a concurrent first Streamlit sign-in.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Fold `repos.users.upsert_user` into `ensure_user` (S14)

**Files:**
- Modify: `backend/repos/users.py:124-158` (delete `upsert_user` and the two blank lines after it)
- Test: `backend/tests/test_users_repo.py:1-38` (ported, plus one guard test)

**Interfaces:**
- Consumes: `repos.users.ensure_user`, `UserRow` (Task 2); `get_user(user_id) -> dict | None`, `get_user_by_email(email) -> dict | None` (unchanged; never exposed through the API).
- Produces: `repos.users` without `upsert_user`. Its only callers were tests (inv A2).

- [ ] **Step 1: Port the tests and add the removal guard**

Replace the whole of `backend/tests/test_users_repo.py` with:

```python
import uuid

import pytest

from repos.users import UserRow, ensure_user, get_user, get_user_by_email


def test_ensure_user_lowercases_and_creates(tmp_db):
    row = ensure_user("Beau.Brown@Example.COM", "Beau", google_sub="sub-1")
    assert isinstance(row, UserRow)
    assert isinstance(row.id, uuid.UUID)
    stored = get_user(row.id)
    assert stored["email"] == "beau.brown@example.com"
    assert stored["name"] == "Beau"
    assert stored["google_sub"] == "sub-1"


def test_ensure_user_is_idempotent_on_normalized_email(tmp_db):
    first = ensure_user("a@b.com", "First")
    second = ensure_user("A@B.COM", "Second", "http://x/y.png")
    assert first.id == second.id
    stored = get_user(first.id)
    assert stored["name"] == "Second"            # updated in place
    assert stored["picture"] == "http://x/y.png"


def test_get_user_by_email_matches_normalized(tmp_db):
    uid = ensure_user("Carol@Example.com").id
    assert get_user_by_email("carol@example.com")["id"] == uid
    assert get_user_by_email("  CAROL@EXAMPLE.COM ")["id"] == uid


def test_get_user_missing_returns_none(tmp_db):
    assert get_user(uuid.uuid4()) is None
    assert get_user_by_email("nobody@example.com") is None


def test_ensure_user_rejects_empty_email(tmp_db):
    with pytest.raises(ValueError):
        ensure_user("   ")


def test_upsert_user_is_folded_into_ensure_user():
    # ops spec S14: one identity write path. Its "overwrite when not None" rule
    # is gone; ensure_user overwrites only with truthy values.
    import repos.users

    assert not hasattr(repos.users, "upsert_user")
```

The five ported tests keep their assertions: lower-casing, `google_sub` stored, idempotent update, the `get_user` / `get_user_by_email` lookups, and empty email rejected. Their setup now calls `ensure_user(…)` (and `.id`) where it called `upsert_user(email=…)`.

- [ ] **Step 2: Run the tests to verify the guard fails**

Run: `.venv/bin/python -m pytest -q backend/tests/test_users_repo.py`
Expected: `1 failed, 5 passed`. `test_upsert_user_is_folded_into_ensure_user` fails with `assert not True` (`hasattr(<module 'repos.users' …>, 'upsert_user')`).

- [ ] **Step 3: Delete `upsert_user`**

In `backend/repos/users.py`, delete lines 124-158: the function that begins

```python
def upsert_user(email, name=None, picture=None, google_sub=None) -> uuid.UUID:
    """Create or refresh a user keyed on the normalized (lower-cased) email.
```

and ends

```python
            user.last_login_at = now
        session.flush()
        return user.id
```

together with the two blank lines after it, so that `_to_dict` is followed by two blank lines and `def get_user(user_id) -> Optional[dict]:`. Every import stays in use (`datetime` by `ensure_user`, `select` by `get_user_by_email`).

- [ ] **Step 4: Run the tests, the whole-word search and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_users_repo.py
grep -rnw 'upsert_user' --include='*.py' backend app.py streamlit_* ui_helpers.py | grep -v '^backend/tests/test_users_repo.py'; echo "grep exit $?"
.venv/bin/python -m pytest -q | tail -1
```
Expected: `6 passed`; no grep output and `grep exit 1` (only the guard test names it); then `249 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/repos/users.py backend/tests/test_users_repo.py
git commit -m "Remove repos.users.upsert_user; its tests move to ensure_user (S14)

Its only callers were tests. The surviving rule is ensure_user's: overwrite
name, picture and google_sub only with truthy values.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: `auth.upsert_from_claims` becomes a thin wrapper

**Files:**
- Modify: `backend/auth.py:1-60` (whole file)
- Test: `backend/tests/test_identity.py` (append)

**Interfaces:**
- Consumes: `repos.users.ensure_user` (Task 2); helper `_stored` in `test_identity.py` (Task 2).
- Produces: `auth.upsert_from_claims(claims: dict) -> uuid.UUID`, the same signature and the same `ValueError("OIDC claims are missing an email address.")`. It delegates to `ensure_user(email, claims.get("name"), claims.get("picture"), google_sub=claims.get("sub"))`. `auth._normalize_email` stays (`streamlit_auth.py:11` imports it). Task 6 moves `api/deps.py` off this wrapper; Streamlit and `migrate_to_db.py` keep using it.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_identity.py`:

```python


# --- auth.upsert_from_claims (Streamlit and migrate_to_db.py) -----------------

def test_upsert_from_claims_delegates_to_ensure_user(tmp_db, monkeypatch):
    import auth

    calls = []

    def spy(email, name=None, picture=None, **kwargs):
        calls.append(((email, name, picture), kwargs))
        return ensure_user(email, name, picture, **kwargs)

    monkeypatch.setattr(auth, "ensure_user", spy)
    user_id = auth.upsert_from_claims(
        {"email": " Pastor@Example.com", "sub": "google-sub-1", "name": "Pat Tor", "picture": "http://x/p.png"}
    )
    assert calls == [(("pastor@example.com", "Pat Tor", "http://x/p.png"), {"google_sub": "google-sub-1"})]
    assert _stored("pastor@example.com").id == user_id
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m pytest -q backend/tests/test_identity.py::test_upsert_from_claims_delegates_to_ensure_user`
Expected: FAIL, `AttributeError: <module 'auth' from '…/backend/auth.py'> has no attribute 'ensure_user'`.

- [ ] **Step 3: Rewrite `backend/auth.py`**

Replace the whole file with:

```python
"""Identity helpers shared by every front end.

upsert_from_claims turns a plain dict of identity claims (email, sub, name,
picture) into a persisted users row and returns its id. Users are keyed on the
normalized (lower-cased) email; google_sub is a stable secondary identifier.
It is a thin wrapper over repos.users.ensure_user (F §2.4), kept with this
signature for Streamlit (streamlit_auth.py) and migrate_to_db.py.
Streamlit login helpers live in streamlit_auth.py.
"""

import uuid
from typing import Optional

from repos.users import ensure_user


def _normalize_email(email: Optional[str]) -> str:
    return (email or "").strip().lower()


def upsert_from_claims(claims: dict) -> uuid.UUID:
    """Create or update the users row for a set of OIDC claims; return its id.

    Pure w.r.t. Streamlit: accepts a plain dict (email, sub, name, picture) so it
    is unit-testable with no running Streamlit session. Idempotent on the
    normalized email, safe under concurrent first calls, and writes
    last_login_at at most hourly (repos.users.LAST_SEEN_RESOLUTION).
    """
    email = _normalize_email(claims.get("email"))
    if not email:
        raise ValueError("OIDC claims are missing an email address.")
    return ensure_user(email, claims.get("name"), claims.get("picture"),
                       google_sub=claims.get("sub")).id
```

Behavior on the Streamlit path is unchanged except as the spec intends. `google_sub` is still written when Google supplies one. Name and picture are still overwritten only when truthy. `last_login_at` is now written at most hourly. A rerun now runs `INSERT … ON CONFLICT DO NOTHING` plus a SELECT, instead of a SELECT plus an unconditional UPDATE. A user's very first Streamlit sign-in runs one UPDATE after the INSERT, to store `google_sub` (clarification 12). "Safe under concurrent first calls" covers both unique indexes: the email through the arbiter, and `google_sub` because only the row-locked UPDATE writes it.

- [ ] **Step 4: Run the identity, auth and API tests, the import check and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_identity.py backend/tests/test_auth.py \
  backend/tests/test_api_me.py backend/tests/test_no_streamlit_in_core.py
.venv/bin/python -c "import sys; sys.path[:0] = ['.', 'backend']; import streamlit_auth, migrate_to_db; print('imports ok')"
.venv/bin/python -m pytest -q | tail -1
```
Expected: `36 passed` (15 + 3 + 17 + 1; `test_auth.py` is unchanged, including its `google_sub` assertion); `imports ok`; `250 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/auth.py backend/tests/test_identity.py
git commit -m "auth.upsert_from_claims: thin wrapper over ensure_user (F §2.4)

Same signature and error text for Streamlit and migrate_to_db.py; Streamlit
sign-in is now race-free and writes last_login_at at most hourly.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: `api/identity_cache.py` — the success-only identity cache (S8)

**Files:**
- Create: `backend/api/identity_cache.py`
- Modify: `backend/tests/conftest.py` (insert `FakeClock` between line 11, `import pytest`, and line 14, the `tmp_db` fixture's `@pytest.fixture`)
- Test: `backend/tests/test_identity_cache.py` (new)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `api.identity_cache.CachedIdentity` (frozen dataclass: `user_id: uuid.UUID`, `name: str | None`, `picture: str | None`);
  - `api.identity_cache.IdentityCache(maxsize: int = 1024, ttl: float = 300.0, *, clock: Callable[[], float] = time.monotonic)`, with `get(email) -> CachedIdentity | None` (None when absent or expired; an expired entry is dropped, and a hit refreshes recency), `put(email, identity) -> None` (evicts the least recently used entry above `maxsize`), `clear() -> None` and `__len__() -> int`;
  - `tests.conftest.FakeClock(start: float = 1000.0)`, with `now() -> float` and `advance(seconds: float) -> None`. Task 6 uses it.

- [ ] **Step 1: Add `FakeClock` to the conftest and write the failing tests**

In `backend/tests/conftest.py`, after line 11 (`import pytest`) and its two blank lines, insert the class, so that the top of the file after the module docstring reads:

```python
import uuid

import pytest


class FakeClock:
    """A monotonic clock tests move by hand: pass `clock.now` where code takes a clock."""

    def __init__(self, start: float = 1000.0):
        self.value = start

    def now(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


@pytest.fixture
def tmp_db(tmp_path):
```

Create `backend/tests/test_identity_cache.py`:

```python
"""api.identity_cache: the private, success-only identity cache (ops slice, F §2.4)."""
import threading
import uuid

from api.identity_cache import CachedIdentity, IdentityCache
from tests.conftest import FakeClock


def _identity(name="Pat"):
    return CachedIdentity(user_id=uuid.uuid4(), name=name, picture=None)


def test_get_returns_the_identity_before_the_ttl_and_none_after():
    clock = FakeClock()
    cache = IdentityCache(maxsize=10, ttl=300, clock=clock.now)
    pat = _identity()
    cache.put("pat@example.com", pat)
    clock.advance(299)
    assert cache.get("pat@example.com") == pat
    clock.advance(2)                                     # 301 s after the put
    assert cache.get("pat@example.com") is None
    assert len(cache) == 0                               # the expired entry was dropped
    assert cache.get("nobody@example.com") is None


def test_the_least_recently_used_entry_is_evicted():
    cache = IdentityCache(maxsize=2, ttl=300)
    cache.put("a@example.com", _identity("A"))
    cache.put("b@example.com", _identity("B"))
    cache.put("c@example.com", _identity("C"))           # maxsize + 1
    assert len(cache) == 2
    assert cache.get("a@example.com") is None
    assert cache.get("b@example.com").name == "B"
    assert cache.get("c@example.com").name == "C"


def test_get_refreshes_recency():
    cache = IdentityCache(maxsize=2, ttl=300)
    cache.put("a@example.com", _identity("A"))
    cache.put("b@example.com", _identity("B"))
    assert cache.get("a@example.com").name == "A"        # a is now the most recent
    cache.put("c@example.com", _identity("C"))
    assert cache.get("b@example.com") is None
    assert cache.get("a@example.com").name == "A"


def test_clear_empties_the_cache():
    cache = IdentityCache()
    cache.put("a@example.com", _identity())
    cache.put("b@example.com", _identity())
    cache.clear()
    assert len(cache) == 0
    assert cache.get("a@example.com") is None


def test_concurrent_puts_and_gets_are_safe():
    cache = IdentityCache(maxsize=64, ttl=300)
    errors = []

    def work(worker):
        try:
            for i in range(1000):
                email = f"user{(worker * 7 + i) % 100}@example.com"
                if i % 2:
                    cache.put(email, _identity())
                else:
                    cache.get(email)
        except Exception as exc:  # noqa: BLE001 - any failure fails the test below
            errors.append(repr(exc))

    threads = [threading.Thread(target=work, args=(n,)) for n in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    assert len(cache) <= 64
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_identity_cache.py`
Expected: collection error `ModuleNotFoundError: No module named 'api.identity_cache'`, `1 error`.

- [ ] **Step 3: Create `backend/api/identity_cache.py`**

```python
"""Process-local identity cache in front of repos.users.ensure_user (F §2.4).

Used only by api.deps.get_current_user. Keyed by normalized email; holds the
user id plus the name and picture as stored after the last ensure_user, so an
unchanged profile needs no database work for up to `ttl` seconds.

Success-only by construction: the only value ever stored is the result of an
ensure_user call that returned. There is no failure entry, so a database error
can never be remembered as an identity (F §2.7).

Deliberately not backend/cache.py: slice 2 owns that module (TTLCache with
get_or_load and CacheableFailure), whose interface does not fit a lookup that
must compare the incoming profile before deciding to load.
"""
import threading
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class CachedIdentity:
    user_id: uuid.UUID
    name: Optional[str]      # as stored after the last ensure_user
    picture: Optional[str]


class IdentityCache:
    """Thread-safe LRU map with a TTL. One lock guards an OrderedDict."""

    def __init__(self, maxsize: int = 1024, ttl: float = 300.0,
                 *, clock: Callable[[], float] = time.monotonic):
        if maxsize < 1:
            raise ValueError("maxsize must be >= 1")
        self._maxsize = maxsize
        self._ttl = ttl
        self._clock = clock
        self._lock = threading.Lock()
        self._entries: "OrderedDict[str, tuple[float, CachedIdentity]]" = OrderedDict()

    def get(self, email: str) -> Optional[CachedIdentity]:
        """The cached identity, or None when absent or expired (expired entries are dropped)."""
        with self._lock:
            entry = self._entries.get(email)
            if entry is None:
                return None
            expires_at, identity = entry
            if self._clock() >= expires_at:
                del self._entries[email]
                return None
            self._entries.move_to_end(email)
            return identity

    def put(self, email: str, identity: CachedIdentity) -> None:
        with self._lock:
            self._entries[email] = (self._clock() + self._ttl, identity)
            self._entries.move_to_end(email)
            while len(self._entries) > self._maxsize:
                self._entries.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)
```

- [ ] **Step 4: Run the tests and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_identity_cache.py
.venv/bin/python -m pytest -q | tail -1
ls backend/cache.py backend/tests/test_cache.py 2>&1 | grep -c "No such file"
```
Expected: `5 passed`, then `255 passed`, then `2` (no slice-2 cache files).

- [ ] **Step 5: Commit**

```bash
git add backend/api/identity_cache.py backend/tests/test_identity_cache.py backend/tests/conftest.py
git commit -m "Add api.identity_cache: thread-safe, success-only LRU identity cache (F §2.4)

Private to get_current_user; not backend/cache.py, which belongs to slice 2.
FakeClock in conftest drives its TTL in tests.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Identity cache in `get_current_user` — race fix and no per-request writes (S8, F §7.3)

**Files:**
- Modify: `backend/api/deps.py:10-20` (imports; add the module cache and `clear_identity_cache`), `backend/api/deps.py:66-76` (end of `get_current_user`; add `_clean` and `_user_id_for`)
- Modify: `backend/api/security.py:105-115` (`claims_to_profile` docstring)
- Modify: `backend/tests/conftest.py` (append two fixtures at the end of the file, after the `seed_catalog` fixture: `identity_clock` in Step 1, the autouse reset in Step 3)
- Test: `backend/tests/test_identity.py` (one import added; append the API section), `backend/tests/test_identity_cache.py` (append the success-only test)

**Interfaces:**
- Consumes: `repos.users.ensure_user`, `UserRow` (Task 2); `CachedIdentity`, `IdentityCache` (Task 5); `FakeClock` (Task 5); `users_statements`, `_stored`, `_user_count` in `test_identity.py` (Task 2); `tests.jwt_helpers.make_token(email=…, provider=…, name=…, expires_in=…)`, `ISSUER`, `SIGNING_KEY`; fixtures `tmp_db`, `make_user`, `make_church`.
- Produces:
  - `api.deps._identity_cache: IdentityCache`, a module attribute that `get_current_user` reads on every call;
  - `api.deps.clear_identity_cache() -> None`;
  - `api.deps.ensure_user`, the module-level name, which tests monkeypatch;
  - `get_current_user` returns `CurrentUser(id, email, name=profile["name"], picture=profile["picture"])`, unchanged from slice 0;
  - conftest's autouse `_fresh_identity_cache` (calls `clear_identity_cache()` only when `api.deps` is already in `sys.modules`), and the fixture `identity_clock -> FakeClock` (swaps `api.deps._identity_cache` for `IdentityCache(maxsize=1024, ttl=300, clock=clock.now)`).

- [ ] **Step 1: Write the `identity_clock` fixture and the failing tests**

The autouse cache reset comes in Step 3, with the cache itself. The old code has no cache to reset, so leaving it out here lets the red run below show each test failing for its own reason.

Append to `backend/tests/conftest.py`:

```python


@pytest.fixture
def identity_clock(monkeypatch):
    """Swap api.deps' identity cache for one on a FakeClock; return the clock.

    Works because get_current_user reads api.deps._identity_cache on every call.
    """
    import api.deps
    from api.identity_cache import IdentityCache

    clock = FakeClock()
    monkeypatch.setattr(api.deps, "_identity_cache",
                        IdentityCache(maxsize=1024, ttl=300, clock=clock.now))
    return clock
```

In `backend/tests/test_identity.py`, replace the import lines

```python
import re
import threading
from contextlib import contextmanager
```

with

```python
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
```

and append to the end of `backend/tests/test_identity.py`:

```python


# --- get_current_user: identity cache in front of ensure_user ------------------

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


def _auth(email="pastor@example.com", **kwargs):
    from tests.jwt_helpers import make_token

    return {"Authorization": f"Bearer {make_token(email=email, **kwargs)}"}


def test_ten_sequential_requests_touch_users_once(client, tmp_db):
    headers = _auth()
    with users_statements(tmp_db) as counts:
        for _ in range(10):
            assert client.get("/me", headers=headers).status_code == 200
    assert counts == {"insert": 1, "update": 0, "select": 1}


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


def test_an_expired_entry_reads_users_again_without_writing(client, tmp_db, identity_clock):
    headers = _auth()
    assert client.get("/me", headers=headers).status_code == 200
    identity_clock.advance(301)
    with users_statements(tmp_db) as counts:
        assert client.get("/me", headers=headers).status_code == 200
    assert counts["select"] == 1
    assert counts["update"] == 0


def test_a_fresh_entry_does_no_users_work(client, tmp_db, identity_clock):
    headers = _auth()
    assert client.get("/me", headers=headers).status_code == 200
    identity_clock.advance(299)
    with users_statements(tmp_db) as counts:
        assert client.get("/me", headers=headers).status_code == 200
    assert counts == {"insert": 0, "update": 0, "select": 0}


def test_a_profile_change_updates_once_even_on_a_cache_hit(client, tmp_db):
    assert client.get("/me", headers=_auth(name="Pat Tor")).status_code == 200
    with users_statements(tmp_db) as changed:
        r = client.get("/me", headers=_auth(name="Pat Tor Jr."))
    assert changed["update"] == 1
    assert r.json()["user"]["name"] == "Pat Tor Jr."
    assert _stored("pastor@example.com").name == "Pat Tor Jr."
    with users_statements(tmp_db) as again:            # the cache now holds the new name
        client.get("/me", headers=_auth(name="Pat Tor Jr."))
    assert again == {"insert": 0, "update": 0, "select": 0}


def test_different_users_never_share_a_cached_identity(client):
    a = client.get("/me", headers=_auth(email="a@example.com")).json()["user"]
    b = client.get("/me", headers=_auth(email="b@example.com")).json()["user"]
    assert a["id"] != b["id"]
    assert (a["email"], b["email"]) == ("a@example.com", "b@example.com")
    again = client.get("/me", headers=_auth(email="a@example.com")).json()["user"]
    assert again["id"] == a["id"]


def _warm_church(client, make_user, make_church, name="Grace"):
    """The caller owns a church, and /church has just warmed the identity cache."""
    me_id = make_user(email="pastor@example.com")
    church_id = make_church(name=name, owner_user_id=me_id)
    headers = {**_auth(), "X-Church-Id": str(church_id)}
    assert client.get("/church", headers=headers).status_code == 200
    return me_id, church_id, headers


def test_removing_a_membership_takes_effect_with_a_warm_cache(client, make_user, make_church):
    from db.models import Membership

    me_id, church_id, headers = _warm_church(client, make_user, make_church)
    with session_scope() as s:
        s.delete(s.get(Membership, (church_id, me_id)))
    r = client.get("/church", headers=headers)
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "forbidden"


def test_soft_deleting_a_church_takes_effect_with_a_warm_cache(client, make_user, make_church):
    from db.models import Church

    me_id, _church_id, _headers = _warm_church(client, make_user, make_church)
    second = make_church(name="Second", owner_user_id=me_id)
    second_headers = {**_auth(), "X-Church-Id": str(second)}
    assert client.get("/church", headers=second_headers).status_code == 200
    with session_scope() as s:
        s.get(Church, second).deleted_at = datetime.now(timezone.utc)
    assert client.get("/church", headers=second_headers).status_code == 403


def test_another_church_is_refused_with_a_warm_cache(client, make_user, make_church):
    _warm_church(client, make_user, make_church)
    other = make_church(name="Other Church")
    r = client.get("/church", headers={**_auth(), "X-Church-Id": str(other)})
    assert r.status_code == 403
    assert "Other Church" not in r.text


@pytest.mark.parametrize("bad_token", [
    {"expires_in": -120},          # expired beyond the 30 s leeway
    {"provider": "email"},         # not a Google sign-in
], ids=["expired", "other-provider"])
def test_the_token_is_verified_even_when_the_identity_is_cached(client, bad_token):
    assert client.get("/me", headers=_auth()).status_code == 200      # identity now cached
    r = client.get("/me", headers=_auth(**bad_token))
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthenticated"
```

Append to the end of `backend/tests/test_identity_cache.py`:

```python


def test_a_failed_ensure_user_is_never_cached(tmp_db, monkeypatch):
    """Success-only: a database error propagates as a 500 and caches nothing;
    the next request runs ensure_user again."""
    from fastapi.testclient import TestClient
    from sqlalchemy.exc import OperationalError

    import api.deps
    from api.deps import get_verifier
    from api.main import create_app
    from api.security import TokenVerifier
    from repos.users import ensure_user
    from tests.jwt_helpers import ISSUER, SIGNING_KEY, make_token

    app = create_app()
    app.dependency_overrides[get_verifier] = lambda: TokenVerifier(
        lambda _token: SIGNING_KEY.public_key(), issuer=ISSUER)
    client = TestClient(app, raise_server_exceptions=False)
    headers = {"Authorization": f"Bearer {make_token(email='pastor@example.com')}"}

    def database_down(*_args, **_kwargs):
        raise OperationalError("INSERT INTO users ...", {}, Exception("server closed the connection"))

    monkeypatch.setattr(api.deps, "ensure_user", database_down)
    r = client.get("/me", headers=headers)
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "internal_error"
    assert len(api.deps._identity_cache) == 0

    calls = []

    def recovered(*args, **kwargs):
        calls.append(args)
        return ensure_user(*args, **kwargs)

    monkeypatch.setattr(api.deps, "ensure_user", recovered)
    r = client.get("/me", headers=headers)
    assert r.status_code == 200
    assert len(calls) == 1
    assert len(api.deps._identity_cache) == 1
```

The 500 body is asserted by `code` only: ops-3 adds `request_id` to it.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_identity.py backend/tests/test_identity_cache.py`
Expected: `4 failed, 26 passed, 2 errors` (checked 2026-09-25 in a scratch copy with Tasks 1–5 applied):
- failing on their assertions: `test_ten_sequential_requests_touch_users_once` (`{'insert': 10, …, 'select': 10} == {'insert': 1, …, 'select': 1}`: today every `/me` runs `ensure_user`) and `test_a_profile_change_updates_once_even_on_a_cache_hit` (its last check sees `{'insert': 1, …, 'select': 1}`, not zeros);
- failing with `AttributeError: <module 'api.deps' …> has no attribute 'ensure_user'` (the monkeypatch target does not exist yet): `test_concurrent_first_requests_both_succeed_with_one_id` (clarification 4) and `test_a_failed_ensure_user_is_never_cached`;
- erroring in setup with `AttributeError: … has no attribute '_identity_cache'` (`identity_clock` has nothing to swap yet): `test_an_expired_entry_reads_users_again_without_writing` and `test_a_fresh_entry_does_no_users_work`. The "a cache hit does no users work" behaviour is seen failing on its assertion in the ten-request test above;
- passing: the 20 tests from Tasks 2, 4 and 5, plus 6 regression guards that pass on the old code by design, because the old code has no cache to get wrong: `test_different_users_never_share_a_cached_identity`, the three warm-cache tenancy tests, and both `test_the_token_is_verified_even_when_the_identity_is_cached` cases. They must stay green once the cache exists.

- [ ] **Step 3: Add the autouse cache reset and wire the cache into `backend/api/deps.py`**

Append to `backend/tests/conftest.py`, after `identity_clock`:

```python


@pytest.fixture(autouse=True)
def _fresh_identity_cache():
    """Every test gets a new SQLite file but reuses the same emails, so a user id
    cached by an earlier test must never leak into this one (ops slice, F §2.4).

    Clears only when api.deps is already imported: a stale entry can exist only
    then, and tests that never touch the API stay independent of that layer
    (the deferred-import rule at the top of this file)."""
    import sys

    deps = sys.modules.get("api.deps")
    if deps is not None:
        deps.clear_identity_cache()
    yield
```

A test that uses the API imports `api.deps` before its first request, so the behaviour is the same as an unconditional reset, and an `api.deps` import error can no longer break every backend test. `streamlit_tests/conftest.py` re-exports only `make_church`, `make_user`, `seed_catalog` and `tmp_db`, so the autouse fixture applies to `backend/tests` only. That is intended: no Streamlit test goes through the API.

Then, in `backend/api/deps.py`, replace lines 10-20:

```python
from api.errors import auth_unavailable, forbidden, unauthenticated
from api.security import (
    AuthUnavailable,
    InvalidToken,
    TokenVerifier,
    claims_to_profile,
    jwks_key_resolver,
)
from api.settings import get_settings
from auth import upsert_from_claims
from tenancy import is_admin, validate_active_church
```

with:

```python
from api.errors import auth_unavailable, forbidden, unauthenticated
from api.identity_cache import CachedIdentity, IdentityCache
from api.security import (
    AuthUnavailable,
    InvalidToken,
    TokenVerifier,
    claims_to_profile,
    jwks_key_resolver,
)
from api.settings import get_settings
from repos.users import ensure_user
from tenancy import is_admin, validate_active_church

# Normalized email -> the user id and profile last written (F §2.4). Read as a
# module attribute on every call, so tests can swap in one on a fake clock.
_identity_cache = IdentityCache(maxsize=1024, ttl=300)


def clear_identity_cache() -> None:
    """Forget every cached identity (tests; see backend/tests/conftest.py)."""
    _identity_cache.clear()
```

Then replace the end of `get_current_user`, originally lines 66-76 (lines 76-86 after the replacement above adds 10 lines):

```python
    profile = claims_to_profile(claims)
    try:
        user_id = upsert_from_claims(profile)
    except ValueError:  # token carried no email
        raise unauthenticated() from None
    return CurrentUser(
        id=user_id,
        email=profile["email"].strip().lower(),
        name=profile["name"],
        picture=profile["picture"],
    )
```

with:

```python
    profile = claims_to_profile(claims)
    email = (profile["email"] or "").strip().lower()
    if not email:  # token carried no email
        raise unauthenticated()
    user_id = _user_id_for(email, _clean(profile["name"]), _clean(profile["picture"]))
    return CurrentUser(id=user_id, email=email, name=profile["name"], picture=profile["picture"])


def _clean(value: Optional[str]) -> Optional[str]:
    return (value or "").strip() or None


def _user_id_for(email: str, name: Optional[str], picture: Optional[str]) -> uuid.UUID:
    """The caller's user id: from the cache when the profile is unchanged, else ensure_user.

    Token verification has already run: it runs on every request and is never
    cached. Tenancy (require_church) is never cached either.
    """
    cache = _identity_cache
    cached = cache.get(email)
    if cached is not None and name in (None, cached.name) and picture in (None, cached.picture):
        return cached.user_id                       # no database work for identity
    row = ensure_user(email, name, picture)         # never google_sub (security.claims_to_profile)
    cache.put(email, CachedIdentity(user_id=row.id, name=row.name, picture=row.picture))
    return row.id
```

The first half of `get_current_user` (bearer parsing, `verifier.verify` on every request, and the 401/503 mapping) is unchanged. So are `require_church` and `require_admin`: `validate_active_church` still runs on every request.

- [ ] **Step 4: Fix the `claims_to_profile` docstring in `backend/api/security.py`**

Replace lines 105-115:

```python
    """Shape Supabase claims for auth.upsert_from_claims.

    `sub` is always None: `user_metadata` is editable by the signed-in user
    (it's account metadata, not an identity claim we control), so it must
    never be trusted as a source of identity. `google_sub` is only used to
    key rows created by the old Streamlit login, not for lookups here, so
    `auth.upsert_from_claims` simply leaves it alone (it only writes
    `google_sub` when `sub` is truthy) and those rows keep the value
    Streamlit stored. `name` and `picture` stay sourced from
    `user_metadata` because they're display-only, not used for identity.
    """
```

with:

```python
    """Shape Supabase claims for api.deps.get_current_user.

    `sub` is always None: `user_metadata` is editable by the signed-in user
    (it's account metadata, not an identity claim we control), so it must
    never be trusted as a source of identity. `google_sub` is only used to
    key rows created by the old Streamlit login, not for lookups here, so
    `get_current_user` never passes it to `repos.users.ensure_user` (which
    writes `google_sub` only when given a truthy one) and those rows keep the
    value Streamlit stored. `name` and `picture` stay sourced from
    `user_metadata` because they're display-only, not used for identity.
    """
```

- [ ] **Step 5: Run the tests, the concurrency tests repeatedly, and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_identity.py backend/tests/test_identity_cache.py \
  backend/tests/test_api_me.py backend/tests/test_auth.py
for i in $(seq 1 10); do .venv/bin/python -m pytest -q -p no:cacheprovider \
  backend/tests/test_identity.py -k concurrent | tail -1; done | grep -c "2 passed"
.venv/bin/python -m pytest -q | tail -1
```
Expected: `52 passed` (26 + 6 + 17 + 3; `test_api_me.py` and `test_auth.py` are unchanged); then `10`; then `267 passed`.

- [ ] **Step 6: Commit**

```bash
git add backend/api/deps.py backend/api/security.py backend/tests/conftest.py \
        backend/tests/test_identity.py backend/tests/test_identity_cache.py
git commit -m "get_current_user: identity cache in front of ensure_user (F §2.4, §7.3)

Concurrent first requests for a new email now both return 200 with one id,
and an unchanged profile costs no users query for 5 minutes and at most one
write an hour. Tokens are still verified on every request, tenancy is never
cached, and a failed ensure_user caches nothing.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Pool and connect-timeout settings, engine comment, runbook (S10 pool part; owner correction 3)

**Files:**
- Modify: `backend/db/engine.py:1-6` (module docstring), `backend/db/engine.py:39-48` (`_make_engine`; add the defaults, `_int_env` and `_engine_kwargs` before it)
- Modify: `docs/ops-runbook.md` (the two "until ops-2" bullets in "Platform limits"; a new subsection before `## Platform limits`)
- Test: `backend/tests/test_engine.py` (append after line 76), `backend/tests/test_ops_workflows.py` (append)

**Interfaces:**
- Consumes: `ROOT`, `_read(path)`, `RUNBOOK` and `re` from `test_ops_workflows.py` (ops-1); the runbook line `- Supabase session pooler (Supavisor) Pool Size: 15 …` and the `backend/.env.example` lines `DB_POOL_SIZE=3` / `DB_MAX_OVERFLOW=3` (ops-1).
- Produces:
  - `db.engine.DEFAULT_POOL_SIZE = 3` and `db.engine.DEFAULT_MAX_OVERFLOW = 3`;
  - `db.engine._int_env(name: str, default: int, *, minimum: int) -> int`, which raises `ValueError` with the exact copy;
  - `db.engine._engine_kwargs(url: str) -> dict`. Postgres gets `pool_pre_ping`, `future`, `pool_size`, `max_overflow`, `pool_recycle=1800` and `connect_args={"connect_timeout": 10}`. SQLite gets `pool_pre_ping`, `future` and `connect_args={"check_same_thread": False}`;
  - `_make_engine(url)` calls `create_engine(url, **_engine_kwargs(url))`. The API, `liturgy-stg` and the CLIs that go through `db.get_engine()` / `session_scope()` (`migrate_to_db.py`, `migrate_add_hymnal.py`) get the same settings. The exception is `backend/keepalive.py`: it builds its own engine (`create_engine(_normalize_url(database_url), pool_pre_ping=True)`), so it gets no pool settings and no `connect_timeout`. ops-3 owns it (the `keepalive.yml` rewrite deletes it). Its one short scheduled session fits in the one spare connection (14 of 15).

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_engine.py`:

```python


# --- Postgres pool and connect timeout (ops slice, F §2.6 item 6) -------------
# The Supabase session pooler's Pool Size is 15 (Nano), so the defaults are
# 3 + 3: 2 x (3 + 3) + 2 = 14 <= 15 (docs/ops-runbook.md -> Platform limits).

PG_URL = "postgresql://u:p@h/db"


@pytest.fixture
def pool_env(monkeypatch):
    """No DB_POOL_SIZE / DB_MAX_OVERFLOW from the developer's shell; tests set them."""
    monkeypatch.delenv("DB_POOL_SIZE", raising=False)
    monkeypatch.delenv("DB_MAX_OVERFLOW", raising=False)
    return monkeypatch


def test_postgres_engine_kwargs_default_to_the_pooler_budget(pool_env):
    from db.engine import _engine_kwargs

    kwargs = _engine_kwargs(PG_URL)
    assert kwargs["pool_size"] == 3
    assert kwargs["max_overflow"] == 3
    assert kwargs["pool_recycle"] == 1800
    assert kwargs["pool_pre_ping"] is True
    assert kwargs["connect_args"] == {"connect_timeout": 10}


def test_pool_settings_come_from_the_environment(pool_env):
    from db.engine import _engine_kwargs

    pool_env.setenv("DB_POOL_SIZE", "2")
    pool_env.setenv("DB_MAX_OVERFLOW", "0")
    kwargs = _engine_kwargs(PG_URL)
    assert (kwargs["pool_size"], kwargs["max_overflow"]) == (2, 0)


def test_blank_pool_settings_use_the_defaults(pool_env):
    from db.engine import _engine_kwargs

    pool_env.setenv("DB_POOL_SIZE", "")
    pool_env.setenv("DB_MAX_OVERFLOW", "  ")
    kwargs = _engine_kwargs(PG_URL)
    assert (kwargs["pool_size"], kwargs["max_overflow"]) == (3, 3)


@pytest.mark.parametrize("name, value, message", [
    ("DB_POOL_SIZE", "abc", "DB_POOL_SIZE must be an integer >= 1 (got 'abc')."),
    ("DB_POOL_SIZE", "0", "DB_POOL_SIZE must be an integer >= 1 (got '0')."),
    ("DB_MAX_OVERFLOW", "-1", "DB_MAX_OVERFLOW must be an integer >= 0 (got '-1')."),
    ("DB_MAX_OVERFLOW", "2.5", "DB_MAX_OVERFLOW must be an integer >= 0 (got '2.5')."),
])
def test_invalid_pool_settings_raise_at_engine_creation(pool_env, name, value, message):
    from db.engine import _make_engine

    pool_env.setenv(name, value)
    with pytest.raises(ValueError) as exc:
        _make_engine(PG_URL)
    assert str(exc.value) == message


def test_sqlite_engine_kwargs_have_no_pool_size(pool_env):
    from db.engine import _engine_kwargs

    pool_env.setenv("DB_POOL_SIZE", "abc")          # ignored: SQLite never reads it
    kwargs = _engine_kwargs("sqlite:///data/app.db")
    assert "pool_size" not in kwargs and "max_overflow" not in kwargs
    assert kwargs["connect_args"] == {"check_same_thread": False}
    assert kwargs["pool_pre_ping"] is True


def test_postgres_engine_uses_the_pool_size_without_connecting(pool_env):
    from db.engine import _make_engine

    engine = _make_engine("postgresql://u:p@localhost:5432/db")   # no connection is opened
    try:
        assert engine.pool.size() == 3
    finally:
        engine.dispose()
```

Append to `backend/tests/test_ops_workflows.py`:

```python


# --- Pool budget: code defaults vs the recorded pooler size (ops-2) -----------

POOL_SIZE_LINE = re.compile(r"^- Supabase session pooler \(Supavisor\) Pool Size: (\d+)", re.MULTILINE)


def test_pool_defaults_fit_the_recorded_pooler_size():
    from db.engine import DEFAULT_MAX_OVERFLOW, DEFAULT_POOL_SIZE

    sizes = POOL_SIZE_LINE.findall(_read(RUNBOOK))
    assert len(sizes) == 1, f"want one '- Supabase session pooler (Supavisor) Pool Size: <N>' line, found {sizes}"
    # Two apps (the API and liturgy-stg) each at their pool limit, plus the backup
    # job's session and the owner's SQL editor (ops spec, Risks item 2).
    assert 2 * (DEFAULT_POOL_SIZE + DEFAULT_MAX_OVERFLOW) + 2 <= int(sizes[0])
    env_example = _read(ROOT / "backend" / ".env.example")
    assert f"\nDB_POOL_SIZE={DEFAULT_POOL_SIZE}\n" in env_example
    assert f"\nDB_MAX_OVERFLOW={DEFAULT_MAX_OVERFLOW}\n" in env_example
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_engine.py backend/tests/test_ops_workflows.py`
Expected: `10 failed, 26 passed`.
- The `_engine_kwargs` tests fail with `ImportError: cannot import name '_engine_kwargs'`.
- The four invalid-value cases fail with `Failed: DID NOT RAISE`.
- The pool-size test fails with `assert 5 == 3`.
- The budget test fails with `ImportError: cannot import name 'DEFAULT_MAX_OVERFLOW'`.
- The 10 existing engine tests and the 16 ops-1 workflow tests pass.

- [ ] **Step 3: Implement the pool settings in `backend/db/engine.py`**

Replace the module docstring, lines 1-6:

```python
"""SQLAlchemy engine + session plumbing.

One engine is cached per process (`_engine`). Both SQLite (local dev) and
Postgres (Supabase, prod) are driven from the same models, selected by
DATABASE_URL. Tests bypass the env var via reset_engine_for_tests(url).
"""
```

with:

```python
"""SQLAlchemy engine + session plumbing.

One engine is cached per process (`_engine`). Both SQLite (local dev) and
Postgres (Supabase, prod) are driven from the same models, selected by
DATABASE_URL. Tests bypass the env var via reset_engine_for_tests(url).

The Postgres pool is read from DB_POOL_SIZE / DB_MAX_OVERFLOW (defaults 3 and
3) when the engine is created. The API, the Streamlit app and the CLIs that
call get_engine() or session_scope() use this engine, and they share the
Supabase session pooler (docs/ops-runbook.md → Platform limits). keepalive.py
builds its own engine and does not get these settings.
"""
```

Replace `_make_engine`, lines 39-48 of the original file (lines 45-54 after the docstring change):

```python
def _make_engine(url: str) -> Engine:
    url = _normalize_url(url)
    kwargs = {"pool_pre_ping": True, "future": True}
    if url.startswith("sqlite"):
        # Streamlit reruns across threads; SQLite needs this relaxed.
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        # Retire connections the Supabase pooler may have dropped.
        kwargs["pool_recycle"] = 1800
    return create_engine(url, **kwargs)
```

with:

```python
# Postgres pool per process. The Supabase session pooler's Pool Size is 15
# (Nano), shared by the API and the Streamlit app: 2 x (3 + 3) + 2 = 14 <= 15.
# backend/tests/test_ops_workflows.py checks these against docs/ops-runbook.md.
DEFAULT_POOL_SIZE = 3
DEFAULT_MAX_OVERFLOW = 3


def _int_env(name: str, default: int, *, minimum: int) -> int:
    """An integer setting from the environment; blank or unset means `default`."""
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        value = None
    if value is None or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum} (got '{raw}').")
    return value


def _engine_kwargs(url: str) -> dict:
    """create_engine() keyword arguments for `url`; opens no connection, so tests inspect it."""
    kwargs = {"pool_pre_ping": True, "future": True}
    if url.startswith("sqlite"):
        # FastAPI runs sync routes in a threadpool; SQLite needs this relaxed.
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs["pool_size"] = _int_env("DB_POOL_SIZE", DEFAULT_POOL_SIZE, minimum=1)
        kwargs["max_overflow"] = _int_env("DB_MAX_OVERFLOW", DEFAULT_MAX_OVERFLOW, minimum=0)
        # Retire connections the Supabase pooler may have dropped.
        kwargs["pool_recycle"] = 1800
        # Without it libpq waits for the OS TCP timeout (minutes) when the
        # pooler is unreachable, tying up a threadpool worker.
        kwargs["connect_args"] = {"connect_timeout": 10}
    return kwargs


def _make_engine(url: str) -> Engine:
    url = _normalize_url(url)
    return create_engine(url, **_engine_kwargs(url))
```

The default `DATABASE_URL` (`sqlite:///data/church.db`) stays: slice 7 owns it.

- [ ] **Step 4: Run the tests to verify they pass**

```bash
.venv/bin/python -m pytest -q backend/tests/test_engine.py backend/tests/test_ops_workflows.py
```
Expected: `36 passed`.

- [ ] **Step 5: Update `docs/ops-runbook.md`**

In `## Platform limits`, replace these two bullets (ops-1 wrote them):

```markdown
- Hand-off to ops-2: the engine's code defaults must be 3 and 3, not the
  spec's 5 and 5.
- Until ops-2 merges, no code reads these variables: `backend/db/engine.py`
  sets no pool size, so each process can hold SQLAlchemy's default 5 + 10 = 15
  sessions. The API, `liturgy-stg` and (until it is deleted) `liturgy` can
  together ask for 45 against 15. Real use by one tester is 2–4. Deleting
  the unused `liturgy` app frees its share.
```

with:

```markdown
- Since ops-2, `backend/db/engine.py` reads `DB_POOL_SIZE` and
  `DB_MAX_OVERFLOW` whenever it creates a Postgres engine, with code defaults
  3 and 3 (`DEFAULT_POOL_SIZE`, `DEFAULT_MAX_OVERFLOW`), plus `pool_pre_ping`,
  `pool_recycle=1800` and `connect_timeout=10`. The API, `liturgy-stg` and the
  CLIs that use `db.get_engine()` or `session_scope()` share that engine
  setup. `backend/keepalive.py` builds its own engine without these settings
  (ops-3 replaces it); its one short scheduled session fits in the spare
  connection (14 of 15). `backend/tests/test_ops_workflows.py` fails if the
  code defaults stop fitting the Pool Size line above or stop matching
  `backend/.env.example`. An invalid value stops the process when the engine
  is created, with `DB_POOL_SIZE must be an integer >= 1 (got '…').` or
  `DB_MAX_OVERFLOW must be an integer >= 0 (got '…').`
- Until the Freeze step deletes the unused `liturgy` app, it adds to the
  worst case: at most 3 + 3 more if it deploys from `main`, or SQLAlchemy's
  5 + 10 if it does not. Its Google sign-in fails before any user query, so
  in practice it holds only the session its startup `init_db()` opens when
  today's `keep-awake` visits it (ops-3 narrows `keep-awake` to
  https://liturgy-stg.streamlit.app/ only). Retiring it frees that share.
  Real use by one tester is 2–4 sessions.
```

Leave the Pool Size, Budget and "Values set" bullets as ops-1 and its records PR left them.

Then insert this subsection directly above the line `## Platform limits`, so it ends the `## Streamlit freeze` section after "D5 fix and recovery record":

```markdown
### What the frozen app inherits from ops-2

`liturgy-stg` still deploys from `main`, so ops-2 went live on it when it
merged, before the freeze locks it in (ops spec, Delivery plan):

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
| Production `users` has a unique constraint or non-partial unique index on exactly `(email)`, the `ON CONFLICT` target | [owner] | [owner] |
| API deploy of the ops-2 merge live; sign-in on https://worship-service-builder.vercel.app works | [owner] | [owner] |
| New `liturgy-stg` build after the merge; smoke check passed on https://liturgy-stg.streamlit.app/ | [owner] | [owner] |
| The tester used `liturgy-stg` for at least one day and nothing regressed | [owner: days used, what the tester reported, log check] | [owner] |

```

- [ ] **Step 6: Check the runbook and run the suite**

```bash
grep -c 'Until ops-2 merges' docs/ops-runbook.md
grep -n '^### What the frozen app inherits from ops-2\|^## Platform limits' docs/ops-runbook.md
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py | tail -1
.venv/bin/python -m pytest -q | tail -1
```
Expected: `0`; two lines, the `###` subsection first and `## Platform limits` exactly 21 lines later; `17 passed`; `277 passed`.

- [ ] **Step 7: Commit**

```bash
git add backend/db/engine.py backend/tests/test_engine.py backend/tests/test_ops_workflows.py docs/ops-runbook.md
git commit -m "Postgres pool 3+3 with connect_timeout=10, from DB_POOL_SIZE/DB_MAX_OVERFLOW (F §2.6)

The Supabase session pooler's Pool Size is 15 (Nano): 2 x (3 + 3) + 2 = 14.
Invalid values stop the process at engine creation with the spec's copy. A
test ties the code defaults to the runbook's Pool Size and .env.example. The
SQLite comment no longer cites Streamlit reruns. The runbook records what
liturgy-stg inherits and the ops-2 gate.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Full verification, Postgres smoke and the ops-2 pull request

**Files:** none changed (this plan file is committed in Step 5)

**Interfaces:**
- Consumes: everything from Tasks 1–7.
- Produces: an open PR `claude/ops-2-identity-db` → `main`, with green CI.

- [ ] **Step 1: Run the whole suite and the acceptance checks**

```bash
.venv/bin/python -m pytest -q | tail -1
grep -rnw 'upsert_user' --include='*.py' backend app.py streamlit_* ui_helpers.py | grep -v '^backend/tests/test_users_repo.py'; echo "grep exit $?"
ls backend/cache.py backend/tests/test_cache.py 2>&1 | grep -c "No such file"
.venv/bin/python -c "import sys; sys.path[:0] = ['backend']; import db.upsert, repos.users, auth, api.identity_cache; print(sorted(m for m in sys.modules if m.split('.')[0] in ('streamlit', 'fastapi', 'starlette') or (m.startswith('api.') and m != 'api.identity_cache')))"
grep -nE '^(from|import) ' backend/db/upsert.py backend/db/engine.py | grep -E 'api|fastapi|streamlit'; echo "grep exit $?"
git diff --stat origin/main...HEAD -- backend/api/main.py backend/api/errors.py backend/api/settings.py backend/api/routes \
  backend/.env.example .github app.py ui_helpers.py streamlit_auth.py frontend README.md docs/manual-verification.md
```
Expected, in order:
- `277 passed`;
- no grep output and `grep exit 1`;
- `2`;
- `[]` (none of the new modules pulls in Streamlit, FastAPI or another `api` module);
- no output and `grep exit 1` (`db/` imports no `api/`);
- the last command prints nothing: ops-2 touches no ops-3 file, no workflow, no Streamlit file and no frontend file.

- [ ] **Step 2: Check the runbook markers**

Run: `grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked'`
Expected: exactly the 4 lines of the "ops-2 gate" table. ops-1's records PR filled every ops-1 marker. If an ops-1 marker still shows, tell the owner; it belongs to the ops-1 plan (Task 12), not to this PR.

- [ ] **Step 3: Postgres smoke test (only if `docker` is on PATH)**

On Postgres, `ON CONFLICT (email)` and the pool settings cannot be exercised by the SQLite suite, and the Postgres CI job arrives in slice 1. Check `command -v docker` first. This machine had no Docker on 2026-09-25. If there is none, skip this step and write "Postgres smoke: skipped (no Docker); owner runs it in Task 9, Step 3" in the PR body.

```bash
ready=no
docker run --rm -d --name ops2-pg -e POSTGRES_PASSWORD=ops2 -p 127.0.0.1:55432:5432 postgres:17 \
  && for i in $(seq 60); do
       docker exec ops2-pg pg_isready -h 127.0.0.1 -U postgres >/dev/null 2>&1 && { ready=yes; break; }
       sleep 1
     done
echo "postgres ready: $ready"
[ "$ready" = yes ] && DATABASE_URL=postgresql://postgres:ops2@127.0.0.1:55432/postgres .venv/bin/python - <<'PY'
import sys
import threading

sys.path[:0] = [".", "backend"]
from sqlalchemy import func, select

from db import get_engine, init_db, session_scope
from db.models import User
from repos.users import ensure_user

init_db()


def race(email, **kwargs):
    """Eight concurrent first calls for one new email: (distinct ids, errors)."""
    barrier = threading.Barrier(8)
    ids, errors = [], []

    def call():
        try:
            barrier.wait(timeout=10)
            ids.append(ensure_user(email, "Racer", **kwargs).id)
        except Exception as exc:  # noqa: BLE001
            errors.append(repr(exc))

    threads = [threading.Thread(target=call) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return set(ids), errors


api_ids, api_errors = race("race@example.com")                              # API path: no google_sub
st_ids, st_errors = race("tabs@example.com", google_sub="google-sub-tabs")  # Streamlit, several tabs
row = ensure_user("RACE@example.com", "Racer Two")
with session_scope() as s:
    count = s.execute(select(func.count()).select_from(User)).scalar_one()
    sub = s.execute(select(User.google_sub).where(User.email == "tabs@example.com")).scalar_one()
engine = get_engine()
print(engine.dialect.name, engine.pool.size(), api_errors + st_errors, len(api_ids), len(st_ids),
      count, sub, row.name, row.id in api_ids)
PY
docker stop ops2-pg 2>/dev/null
```
Expected: `postgres ready: yes`, then `postgresql 3 [] 1 1 2 google-sub-tabs Racer Two True`. The readiness wait is bounded: if `docker run` fails (Docker Desktop not running, port 55432 in use, image pull error) or the server is not ready within 60 s, it prints `postgres ready: no` and skips the script. Then stop, fix Docker, and run the block again; do not open the PR on a skipped smoke if Docker is present. Each race runs eight threads on a 3 + 3 pool, so two of them wait briefly for a connection. The second race is the Streamlit case of clarification 12: several tabs sign in a new Google account at once, with `google_sub`. Only Postgres can exercise it, because SQLite serializes writers. With `google_sub` in the INSERT, two threads that both pass the arbiter pre-check could raise `IntegrityError` on `users_google_sub_key` (timing-dependent); with it written only by the UPDATE, no thread can. The same script against SQLite printed `sqlite 5 [] 1 1 2 google-sub-tabs Racer Two True` on 2026-09-25; SQLite does not use the Postgres pool settings. Anything else means stop and investigate before opening the PR.

- [ ] **Step 4: Frontend untouched**

Run: `git diff --stat origin/main...HEAD -- frontend`
Expected: nothing. CI's frontend job still runs on the PR and must pass.

- [ ] **Step 5: Push and open the PR (get the owner's go-ahead first)**

```bash
git add docs/superpowers/plans/2026-09-25-ops-2-identity-db.md
git commit -m "Add the ops-2 implementation plan

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" || true   # "nothing to commit" is fine if it is already committed
git push -u origin claude/ops-2-identity-db
gh pr create --base main --head claude/ops-2-identity-db \
  --title "ops-2: identity race fix, identity cache and pool settings" \
  --body "PR ops-2 of the ops slice (docs/superpowers/specs/2026-09-25-slice-ops-cleanup-design.md; plan docs/superpowers/plans/2026-09-25-ops-2-identity-db.md).

- db/upsert.py insert_ignore; repos.users.ensure_user (INSERT ... ON CONFLICT (email) DO NOTHING, SELECT, one UPDATE only for a changed truthy profile or a last_login_at older than an hour; google_sub is written by the UPDATE, never the INSERT, so users_google_sub_key cannot break concurrent first Streamlit sign-ins); repos.users.upsert_user removed, its tests ported (S8, S14).
- auth.upsert_from_claims is a thin wrapper with the same signature, so Streamlit (liturgy-stg, still deployed from main) and migrate_to_db.py get the race fix and hourly last_login_at.
- api/identity_cache.py and the cache in get_current_user: token verified on every request, tenancy never cached, success-only, 1024 entries / 300 s (F §2.4, §7.3).
- Postgres pool DB_POOL_SIZE/DB_MAX_OVERFLOW, defaults 3 and 3 (Supavisor Pool Size 15: 2 x (3+3) + 2 = 14), pool_recycle 1800, connect_timeout 10; exact-copy errors for invalid values (S10 pool part).
- Comment fixes: db/engine.py SQLite comment, models.last_login_at, claims_to_profile docstring. Runbook: pool bullets and the ops-2 gate table.
- Tests: +47 (277 total), including 8-thread ensure_user and 2-request /me race tests.
- Postgres smoke: <paste the Task 8 Step 3 output, or 'skipped (no Docker); owner runs it in Task 9, Step 3'>

Owner steps before merge: plan Task 9 (unique index on users(email), pool values present and 3 on Railway and liturgy-stg). After merge: Task 10 (deploy checks, liturgy-stg smoke check, one day of tester use), then Task 11 records the gate.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
gh pr checks --watch
```
Replace the `<paste …>` line with the actual Step 3 result before running `gh pr create`. Expected: the `backend` and `frontend` checks pass.

---

### Task 9 (OWNER, before merge): unique index on `users(email)` in production, pool values, Postgres smoke, merge

Merging puts ops-2 live on `liturgy-stg` at once (it deploys from `main`). Every sign-in and rerun then runs `INSERT … ON CONFLICT (email) DO NOTHING`. These checks make sure that works on the real database first. The owner passes results to the agent; no secret goes into chat.

**Files:** none (results go into the runbook in Task 11)

- [ ] **Step 1 (OWNER): Confirm production `users` has a unique index on exactly `email`**

`ON CONFLICT (email)` works with either a `UNIQUE (email)` constraint or a plain `CREATE UNIQUE INDEX … (email)`. Every unique constraint is backed by a unique index, so listing the unique indexes covers both. Supabase Dashboard → SQL editor (project `worship-staging`), run:

```sql
select ix.indexname, ix.indexdef, coalesce(c.condeferrable, false) as deferrable
from pg_indexes ix
left join pg_constraint c
  on c.conrelid = 'public.users'::regclass and c.conname = ix.indexname
where ix.schemaname = 'public' and ix.tablename = 'users'
  and ix.indexdef ilike 'create unique index%'
order by 1;
```

Expected: three rows (the names may differ; the definitions must not):
- `users_email_key | CREATE UNIQUE INDEX users_email_key ON public.users USING btree (email) | false`;
- `users_google_sub_key | … USING btree (google_sub) | false`;
- `users_pkey | … USING btree (id) | false`.

It passes when at least one row ends in `USING btree (email)`: exactly the plain `email` column, with no `WHERE` clause after it (partial index), and `deferrable` is `false`. **Stop and do not merge**, and tell the agent, if there is no such row, or if the only `email` match is on `lower(email)`, has a `WHERE` clause, or is deferrable. Postgres rejects `ON CONFLICT (email)` without a matching non-partial, non-deferrable unique index, so every sign-in would fail.

Give the agent the result and the date (for the gate table's first row).

- [ ] **Step 2 (OWNER): Confirm the pool values in both apps**

ops-1's plan (Task 9, Step 1) set them, and the runbook's "Values set" line has the date. From this PR on the code reads them, so check the exact values now. The code defaults are also 3 and 3, but owner correction 3 requires the values to be set explicitly in both apps, and a typo such as `3 ,` would stop the app at engine creation.
- Railway → the API service → Variables: both `DB_POOL_SIZE` and `DB_MAX_OVERFLOW` are present, and each is `3`. If either is missing or has another value, set it to `3` (saving redeploys the API).
- Streamlit Cloud (share.streamlit.io) → `liturgy-stg` → ⋮ → Settings → Secrets: the top-level keys `DB_POOL_SIZE = "3"` and `DB_MAX_OVERFLOW = "3"` are both present and sit above the first `[section]` header. Fix them if not, at a time the tester is not using the app, because saving restarts it. Do not change the unused `liturgy` app: the Freeze step deletes it.

If you had to add or change a value in either app, tell the agent the date. The runbook's "Values set" line was then not true until that date, so the agent corrects it in the Task 11 records PR.

- [ ] **Step 3 (OWNER, only if Task 8 skipped the Postgres smoke): Run it on your machine**

Requires Docker (as for the restore drill). Do not use the main checkout (`/Users/beaubrown/Desktop/projects/church`): it has no `.venv`, and `git switch claude/ops-2-identity-db` fails there with "already used by worktree", because the agent's worktree has that branch checked out. Instead make a throwaway, detached worktree of the pushed branch with its own `.venv` (a few minutes for the install):

```bash
cd /Users/beaubrown/Desktop/projects/church
git fetch origin
git worktree add --detach "${TMPDIR:-/tmp}/ops2-smoke" origin/claude/ops-2-identity-db
cd "${TMPDIR:-/tmp}/ops2-smoke"
/Users/beaubrown/.local/bin/python3.11 -m venv .venv && .venv/bin/pip install -q -r requirements-dev.txt
```

Then, in that directory:

```bash
ready=no
docker run --rm -d --name ops2-pg -e POSTGRES_PASSWORD=ops2 -p 127.0.0.1:55432:5432 postgres:17 \
  && for i in $(seq 60); do
       docker exec ops2-pg pg_isready -h 127.0.0.1 -U postgres >/dev/null 2>&1 && { ready=yes; break; }
       sleep 1
     done
echo "postgres ready: $ready"
[ "$ready" = yes ] && DATABASE_URL=postgresql://postgres:ops2@127.0.0.1:55432/postgres .venv/bin/python - <<'PY'
import sys
import threading

sys.path[:0] = [".", "backend"]
from sqlalchemy import func, select

from db import get_engine, init_db, session_scope
from db.models import User
from repos.users import ensure_user

init_db()


def race(email, **kwargs):
    """Eight concurrent first calls for one new email: (distinct ids, errors)."""
    barrier = threading.Barrier(8)
    ids, errors = [], []

    def call():
        try:
            barrier.wait(timeout=10)
            ids.append(ensure_user(email, "Racer", **kwargs).id)
        except Exception as exc:  # noqa: BLE001
            errors.append(repr(exc))

    threads = [threading.Thread(target=call) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return set(ids), errors


api_ids, api_errors = race("race@example.com")                              # API path: no google_sub
st_ids, st_errors = race("tabs@example.com", google_sub="google-sub-tabs")  # Streamlit, several tabs
row = ensure_user("RACE@example.com", "Racer Two")
with session_scope() as s:
    count = s.execute(select(func.count()).select_from(User)).scalar_one()
    sub = s.execute(select(User.google_sub).where(User.email == "tabs@example.com")).scalar_one()
engine = get_engine()
print(engine.dialect.name, engine.pool.size(), api_errors + st_errors, len(api_ids), len(st_ids),
      count, sub, row.name, row.id in api_ids)
PY
docker stop ops2-pg 2>/dev/null
```

This container is throwaway and local; the password `ops2` is not a secret. Expected: `postgres ready: yes`, then `postgresql 3 [] 1 1 2 google-sub-tabs Racer Two True`. `postgres ready: no` means Docker did not start the container within 60 s (Docker Desktop not running, port 55432 in use, image pull error): fix that and run the block again. Paste only the `postgresql …` line to the agent, who adds it to the PR description. Anything else: do not merge.

Then clean up the throwaway worktree:

```bash
cd /Users/beaubrown/Desktop/projects/church
git worktree remove --force "${TMPDIR:-/tmp}/ops2-smoke"
```

- [ ] **Step 4 (OWNER): Review and merge at a quiet time**

Merging rebuilds `liturgy-stg` (a short restart), so merge on a weekday when the tester is not using it, never Saturday or Sunday. All CI checks must be green and Steps 1–3 done. Merging is outward-facing: merge only on the owner's explicit yes.

```bash
gh pr merge --merge claude/ops-2-identity-db
```

---

### Task 10 (OWNER, after merge): deploy checks, smoke check and the one-day tester gate

This is the delivery-plan gate: "For at least one day the tester uses Streamlit (still deployed from `main`) and nothing regresses." ops-3 does not start until it passes.

**Files:** none (results go into the runbook in Task 11)

- [ ] **Step 1 (OWNER): API deploy and the React app**

- Railway → the API service → Deployments: the deployment for the merge commit is Active. Its logs show a normal start, with no `DB_POOL_SIZE must` or `DB_MAX_OVERFLOW must` line and no traceback.
- On https://worship-service-builder.vercel.app, at 375 px (Chrome device mode, iPhone SE) and on desktop: sign in, the church shows in the switcher, switch church if you have two, log out. (Ops spec, Manual checks: "after each ops merge".)

- [ ] **Step 2 (OWNER): `liturgy-stg` rebuilt and the smoke check**

- Streamlit Cloud → `liturgy-stg` → Manage app → logs: a new build started after the merge commit landed, and it finished without a traceback.
- On https://liturgy-stg.streamlit.app/: sign in, the church loads, load an archived service, open Settings. (Not the `liturgy` app: it is unused and its sign-in is already broken.)
- The `liturgy-stg` proof is that sign-in and the church load succeed, and its logs show no `IntegrityError` and no traceback.
- In the Supabase SQL editor: `select email, last_login_at, now() - last_login_at as age from users order by last_login_at desc nulls last limit 5;`. Your own row's `age` is under 1 hour (read `age`, not `last_login_at`, which the editor shows in UTC). This confirms that an `ensure_user` write path works on production. It does not show which app wrote it: the Vercel sign-in in Step 1 runs the same `ensure_user` just before, and the `liturgy-stg` sign-in then writes nothing, because the stored value is under an hour old.

- [ ] **Step 3 (OWNER): At least one day of normal tester use**

Let the tester use https://liturgy-stg.streamlit.app/ as usual for at least one full day: sign in, load a service, pick hymns, Prepare, Save. The spec prescribes no message copy for this; if you ask the tester, just ask whether anything looked different or failed. Afterwards, check both logs for the day:
- Streamlit Cloud → `liturgy-stg` → Manage app → logs;
- Railway → the API service → Logs.

Search each for `Traceback`, `IntegrityError`, `OperationalError`, `QueuePool limit`, `DB_POOL_SIZE must`, `DB_MAX_OVERFLOW must` and (Railway) `Unhandled error on`. None should appear. A `QueuePool limit of size 3 overflow 3 reached` line would mean the pool is too small for real use: report it rather than raising the values, which must still fit the Pool Size of 15.

- [ ] **Step 4 (OWNER → agent): Contingency if anything regressed**

Revert the merge (outward-facing; only on the owner's yes). Timing: merging the revert redeploys `liturgy-stg` like any merge to `main`. If the regression blocks the tester, merge it right away. Otherwise merge it on a weekday when the tester is not using `liturgy-stg`, never Saturday or Sunday.

The revert removes everything the ops-2 PR added. That includes the runbook's "What the frozen app inherits from ops-2" subsection with its gate table, and the new pool bullets (the old "until ops-2" bullets come back, and they are true again). So the revert PR has two commits: the pure revert, then a docs-only commit that records the failed gate. Keep them separate, because a re-land reverts only the first.

Commit 1, the revert. `--no-commit` plus an explicit message keeps the Co-Authored-By trailer, which `--no-edit` would drop:

```bash
git fetch origin
git switch -c claude/revert-ops-2 origin/main
git revert -m 1 --no-commit <ops-2 merge commit sha>
git commit -m "Revert ops-2 (<one-line reason>)

This reverts merge commit <ops-2 merge commit sha>.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
.venv/bin/python -m pytest -q | tail -1
grep -c '^### What the frozen app inherits from ops-2' docs/ops-runbook.md
```
Expected: `230 passed` (plus any tests from later PRs), then `0` (the gate table is gone).

Commit 2, the record. Append this paragraph to the end of `### Incident record` in `docs/ops-runbook.md`, after the existing "None: the Data API was already off" paragraph. It goes there, and not where the gate table was, so that reverting the revert later applies without a conflict:

```markdown

ops-2 regression (<date found>): ops-2 (PR #<n>) was merged on <date> and
reverted on <date> (PR #<revert n>) after <what the tester or the logs
showed>. The ops-2 gate FAILED. ops-3 must not start until a re-land of
ops-2 is merged and its gate table ("What the frozen app inherits from
ops-2", which returns with the re-land) is filled with passing results.
```

```bash
grep -c '^ops-2 regression (' docs/ops-runbook.md
.venv/bin/python -m pytest -q | tail -1
git add docs/ops-runbook.md
git commit -m "Runbook: ops-2 reverted, gate failed

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -u origin claude/revert-ops-2
gh pr create --base main --head claude/revert-ops-2 --title "Revert ops-2" \
  --body "Reverts ops-2 after a regression on liturgy-stg: <what the tester or the logs showed>. Records the failed ops-2 gate in docs/ops-runbook.md (Incident record); ops-3 must not start.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```
Expected: `1`, then the same count as after commit 1. After the merge, `liturgy-stg` and Railway redeploy the pre-ops-2 code. Task 11 does not run for this attempt: its table no longer exists.

**Re-landing ops-2.** Once a merge commit is reverted, merging the same branch again does not bring the reverted changes back, even with a fix commit on top: git treats them as already merged. So the re-land branch starts from `origin/main` by reverting the revert. `<revert commit sha>` is commit 1 above, "Revert ops-2 (…)"; not the revert PR's merge commit and not the runbook commit:

```bash
git fetch origin
git switch -c claude/ops-2-reland origin/main
git revert --no-commit <revert commit sha>
git commit -m "Re-land ops-2 (revert the revert)

This reverts commit <revert commit sha>.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
This brings back the code, the tests, the pool bullets and the gate table with fresh `[owner]` markers. Then add the fix test first and the fix (TDD, new commits). Run Task 8 again (its counts become 277 plus the fix's tests), then Tasks 9–11 for the re-land PR. Keep the "ops-2 regression" paragraph: it is the record of attempt 1.

- [ ] **Step 5 (OWNER → agent): Give the agent the gate results**

Pass on, with dates:
- the Step 1 result from Task 9 (the unique index on exactly `email` present), and the date of any pool value you had to add or fix in Task 9, Step 2;
- the API deploy and Vercel sign-in (Step 1);
- the `liturgy-stg` build and smoke check (Step 2);
- the days the tester used the app, what the tester reported, and the log check (Step 3).

---

### Task 11: Record the ops-2 gate (docs-only PR)

Run this only when every gate check passed. If Task 10, Step 4 reverted ops-2, the gate FAILED: the table is gone from `main`, the revert PR recorded the failure, and this task waits for the re-land PR's gate.

**Files:**
- Modify: `docs/ops-runbook.md` (the four "ops-2 gate" rows; the pool "Values set" date only if Task 9, Step 2 changed a value)

**Interfaces:**
- Consumes: the Task 9, Steps 1–2 and Task 10 results.
- Produces: a runbook whose "What the frozen app inherits from ops-2" subsection exists and has no `[owner` markers. That is the signal that ops-3 may start.

- [ ] **Step 1: Fill the gate table**

```bash
git fetch origin
git switch -c claude/ops-2-records origin/main
grep -c '^### What the frozen app inherits from ops-2' docs/ops-runbook.md
```
Expected: `1`. If it prints `0`, stop: ops-2 is not on `main` (it was reverted or never merged), and there is no gate to record.

In `docs/ops-runbook.md` → Streamlit freeze → "What the frozen app inherits from ops-2", replace each row's two `[owner…]` markers with the result and the date the owner gave. For the last row, write the days used, what the tester reported, and "no errors in the Streamlit or Railway logs".

If the owner had to add or fix a pool value in Task 9, Step 2, also change the date on the "Values set" line in `## Platform limits` to that date, and add "(corrected before the ops-2 merge)".

- [ ] **Step 2: Check and commit**

```bash
grep -c '^### What the frozen app inherits from ops-2' docs/ops-runbook.md
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked'; echo "grep exit $?"
.venv/bin/python -m pytest -q | tail -1
git add docs/ops-runbook.md
git commit -m "Runbook: record the ops-2 gate (unique email index, deploys, one day of tester use)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -u origin claude/ops-2-records
gh pr create --base main --head claude/ops-2-records \
  --title "Runbook: ops-2 gate record" \
  --body "Fills the ops-2 gate table in docs/ops-runbook.md: production unique index on users(email), API and liturgy-stg deploys, and at least one day of tester use with no regression.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```
Expected: `1` (the heading is there, so the next check cannot pass just because the table is missing); then no marker lines and `grep exit 1`; then `277 passed` (for a re-land, 277 plus the fix's tests).

Merge after the owner's yes, and at a quiet time: every merge to `main` redeploys `liturgy-stg`, so merge on a weekday when the tester is not using it, never Saturday or Sunday. The ops-2 gate is then passed, and ops-3 can start.

---

## Spec coverage

| Spec item / acceptance criterion (ops-2 share) | Task |
|---|---|
| S8: `backend/db/upsert.py` `insert_ignore(table, *, dialect_name=None)`; `Table` or mapped class; dialect from `get_engine()`; postgresql/sqlite only, else `NotImplementedError` | 1 |
| Testing → `test_upsert.py`: insert once, second execute leaves one row; mapped class the same; `mysql` raises; Postgres compiles to `ON CONFLICT (email) DO NOTHING` without connecting | 1 |
| S8 / F §2.4: `UserRow`, `LAST_SEEN_RESOLUTION = 1 h`, `ensure_user(email, name, picture, *, google_sub, now, session)`; algorithm steps 1–6 (normalize, clean, insert-ignore, select, collect truthy/hourly updates, one UPDATE), except that the INSERT carries no `google_sub` and the UPDATE writes it (clarification 12); naive datetimes read as UTC; own `session_scope()` or the caller's session (F §2.2.3) | 2 |
| Testing → `test_identity.py` `ensure_user`: normalized email, `created_at == last_login_at == now`, `google_sub` only when passed (and written by the UPDATE); idempotent across case; name/picture only when truthy and different; falsy never blanks; +59 min no UPDATE, +61 min UPDATE (statement listener); naive stored value as UTC; empty email `ValueError`; `session=` joins the caller's transaction | 2 |
| Testing → race: 8 threads on a `Barrier`, same id, `count(*) == 1` (Postgres copy is slice 1) | 2 |
| AC 12 (second half: eight concurrent `ensure_user` calls create one row); F §7.3 row 2 | 2 |
| `db/models.py:42` comment "last seen, to the hour (see repos.users.LAST_SEEN_RESOLUTION)" | 2 |
| S14: `repos.users.upsert_user` deleted; Testing → `test_users_repo.py` ported (same assertions; setup via `ensure_user(…).id`; import line drops `upsert_user`) | 3 |
| Behavior changes 15 (`upsert_user` removed) and 16 ("overwrite when truthy" only) | 2, 3 |
| `auth.upsert_from_claims` thin wrapper, same signature and error text, for `streamlit_auth.py:28` and `migrate_to_db.py:130`; inv H1 (its call keeps working) | 4 |
| Testing → wrapper delegates to `ensure_user`; `test_auth.py` passes unchanged, including the `google_sub` assertion; AC 15 | 4 |
| S8: `backend/api/identity_cache.py` `CachedIdentity`, `IdentityCache(maxsize=1024, ttl=300.0, *, clock)`: one lock, `OrderedDict`, LRU, expired entries dropped, success-only, not `cache.TTLCache` | 5 |
| Testing → `test_identity_cache.py`: TTL with fake clock and `len` drops; LRU at `maxsize + 1`; `get` refreshes recency; `clear`; 8 threads × 1 000 | 5 |
| Testing → conftest: `FakeClock` (`now()`, `advance(seconds)`) | 5 |
| S8: `api.deps._identity_cache = IdentityCache(maxsize=1024, ttl=300)`, `clear_identity_cache()`, `get_current_user` reads the module attribute per call; flow steps 1–6 (verify every request; 401 on empty email; cleaned name/picture; hit with unchanged profile → no DB; else `ensure_user` without `google_sub`, `put` only after it returns; same `CurrentUser` shape) | 6 |
| Testing → conftest: autouse `clear_identity_cache()`; `identity_clock` monkeypatches `api.deps._identity_cache` | 6 |
| Testing → success-only: `ensure_user` raising `OperationalError` → 500, cache empty; restored → runs once, 200 | 6 |
| Testing → API identity: ten sequential `/me` = 1 INSERT, 0 UPDATE, 1 SELECT; two concurrent `/me` same id; TTL 301 s → 1 SELECT, 0 UPDATE; 299 s → no users statement; profile change → 1 UPDATE on a hit; no cross-user leak; tenancy not cached (membership removed, church soft-deleted, other church → 403 without its name); token still verified on a hit (expired, other provider) | 6 |
| AC 12 (first half), AC 13, AC 14; F acceptance criterion 3; F §7.3 rows 2 and 3; Behavior changes 1, 2, 3 | 2, 6 |
| AC 26: no `backend/cache.py` or `test_cache.py`; the identity cache stores only successful results; a TTL test drives it through `identity_clock` | 5, 6, 8 (Step 1) |
| Data access: `require_church` unchanged and uncached; regression tests with a warm cache | 6 |
| S10 (pool part) / F §2.6 item 6: `_engine_kwargs(url)`; `_int_env` (blank = default, exact-copy `ValueError`); Postgres `pool_size`/`max_overflow` from `DB_POOL_SIZE`/`DB_MAX_OVERFLOW`, `pool_recycle=1800`, `pool_pre_ping`, `connect_args={"connect_timeout": 10}`; SQLite `check_same_thread=False`, no pool keys | 7 |
| Owner correction 3: defaults 3 and 3 (Supavisor Pool Size 15, Nano, max clients 200; 2 × (3 + 3) + 2 = 14 ≤ 15), the same on Railway and in the `liturgy-stg` Secrets; arithmetic in the runbook, guarded by a test against the runbook and `.env.example` | 7, 9 (Step 2) |
| Testing → `test_engine.py`: defaults (3/3 per correction 3), recycle, pre-ping, `connect_args`; `DB_POOL_SIZE=2`, `DB_MAX_OVERFLOW=0` honored; `abc` and `0` raise the exact copy, blank gives the default; SQLite has no pool keys and `check_same_thread` is False; `_make_engine(...).pool.size() == 3` without connecting | 7 |
| AC 17 (pool, per correction 3); Behavior change 9; Exact copy for invalid `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` | 7 |
| Comment fixes: `db/engine.py:43` ("FastAPI runs sync routes in a threadpool; SQLite needs this relaxed."); also the `claims_to_profile` docstring (clarification 8) | 6, 7 |
| Risks item 2: pool values set in both apps before ops-2 merges and recorded; the stale "until ops-2" runbook text replaced | 7, 9 (Step 2) |
| Streamlit coupling: nothing under `backend/` imports streamlit; the new modules import neither Streamlit nor FastAPI; `db/` does not import `api/`; `test_no_streamlit_in_core.py` and `test_api_does_not_import_streamlit` stay green | 4, 8 (Step 1) |
| "What the frozen app inherits" (the `ensure_user` and pool parts), recorded in the runbook and verified before the Freeze | 7, 10, 11 |
| Delivery plan gate: merged; for at least one day the tester uses Streamlit (`liturgy-stg`, owner correction 1), still deployed from `main`, and nothing regresses; on a regression, a revert with a failed-gate record and a revert-the-revert re-land (clarification 13) | 9 (Step 4), 10, 11 |
| AC 24 (ops-2 share): backend suite and frontend checks green on the ops-2 PR | 8 |
| Unchanged-and-green list (`test_auth`, `test_api_me`, `test_api_app`, `test_api_security`, `test_docs`, `test_ci_workflow`, `test_no_streamlit_in_core`, `test_keepalive`, all of `streamlit_tests/`) | every task's full-suite run; 8 |

**Deliberately not in ops-2** (ops spec delivery plan and owner corrections):
- ops-3:
  - `RequestIdMiddleware`, `UnhandledErrorMiddleware`, middleware order and CORS lists;
  - `request_id` in error bodies and `redirect_slashes=False`;
  - `api/logging_config.py`, `api/startup.py`, `APP_ENV`/`LOG_LEVEL` settings and the startup guards;
  - `db/health.py`, `/health/ready`, `db_unavailable` and the `reset_readiness_for_tests` autouse fixture;
  - the `keepalive.yml` rewrite, deleting `keepalive.py` and `test_keepalive.py`, `keep-awake.yml` (pings only https://liturgy-stg.streamlit.app/, owner correction 1);
  - the `app.py` FROZEN header, the README and `docs/manual-verification.md` updates, and the runbook's environment, keep-alive and freeze-record sections.
- The Freeze step: cut and protect `streamlit-frozen`, and redeploy `liturgy-stg` from it. Delete the unused `liturgy` app and its redirect URIs.
- Slice 1: the `@pytest.mark.postgres` copy of the race test (with the Streamlit `google_sub` case) and the Postgres CI job.
- Slice 2: `backend/cache.py` and `backend/tests/test_cache.py`.
- Slice 7: the `db/engine.py` default URL and `migrate_to_db.py`.
