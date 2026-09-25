# React + FastAPI Slice 0 (Foundation) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Merge the multi-church branch into `main`, move the Python code into `backend/`, add a FastAPI API with Supabase-Auth sign-in and the church-membership guard, add a Next.js frontend with Google login and a church switcher, and deploy both — while the Streamlit app keeps working on the same database.

**Architecture:** Next.js (Vercel) signs users in with Supabase Auth (Google only) and calls FastAPI (Railway) with `Authorization: Bearer <jwt>` and `X-Church-Id`. FastAPI verifies the JWT against Supabase's JWKS, upserts the user via the existing `auth.upsert_from_claims`, and re-checks church membership on every church-scoped request via the existing `tenancy.validate_active_church`. The database (Supabase Postgres) and its tables are unchanged.

**Tech Stack:** Python 3.11, FastAPI, Uvicorn, PyJWT[crypto], SQLAlchemy 2, pytest · Next.js 16 (App Router, TypeScript), Tailwind, shadcn/ui, `@supabase/ssr`, Vitest · Supabase Auth + Postgres · Railway · Vercel · GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-25-react-fastapi-migration-design.md`

## Global Constraints

- Python 3.11 for everything backend (local venv at `.venv/`, built from `/Users/beaubrown/.local/bin/python3.11`; system `python3` is 3.9 and has no deps).
- Nothing under `backend/` may import `streamlit`. A test enforces this.
- The Streamlit entry stays `app.py` at the repo root (Streamlit Community Cloud can't change an app's main file in place).
- No database schema changes in slice 0.
- Secrets (OpenAI, Google client secret, Gmail tokens, `DATABASE_URL`) exist only in backend env vars. The frontend holds only `NEXT_PUBLIC_*` values.
- The backend never trusts a client-supplied church id; every church-scoped route goes through `require_church`.
- Only Google sign-in is accepted: enforced in code (`app_metadata.provider == "google"`) and in Supabase settings.
- Error body is always `{"error": {"code": "<slug>", "message": "<text>"}}` with codes `unauthenticated` (401), `forbidden` (403), `not_found` (404), `invalid_request` (422), `auth_unavailable` (503), `internal_error` (500).
- Run all Python commands from the repo root with `.venv/bin/python` unless a step says otherwise.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## File Map (end state of slice 0)

```
app.py                         Streamlit entry (unchanged name); prepends backend/ to sys.path
streamlit_auth.py              Streamlit login helpers (split out of auth.py)
streamlit_tenancy.py           Streamlit session-state church helpers (split out of tenancy.py)
streamlit_views/               was views/ (Streamlit settings page)
ui_helpers.py                  unchanged, stays at root (Streamlit-only helpers)
streamlit_tests/               tests for the Streamlit-only modules above
pytest.ini                     runs backend/tests + streamlit_tests together
requirements.txt               -r backend/requirements.txt + streamlit[auth] (Streamlit Cloud reads this)
requirements-dev.txt           -r requirements.txt + pytest
backend/
  api/__init__.py
  api/main.py                  create_app(), CORS, error handlers, routers
  api/settings.py              Settings (SUPABASE_URL, CORS_ORIGINS)
  api/errors.py                ApiError + handlers (uniform error body)
  api/security.py              TokenVerifier, jwks_key_resolver, claims_to_profile
  api/deps.py                  get_current_user, require_church, require_admin
  api/schemas.py               Pydantic response models
  api/routes/__init__.py
  api/routes/health.py         GET /health
  api/routes/me.py             GET /me, GET /church
  auth.py tenancy.py db/ repos/ worship_service.py ... (moved, Streamlit-free)
  tests/                       moved tests + new api tests + jwt_helpers.py
  requirements.txt  .env.example  Procfile  .python-version
frontend/
  src/proxy.ts                 session refresh + redirect to /login
  src/lib/supabase/{client,server,proxy}.ts
  src/lib/api.ts (+ api.test.ts)       fetch wrapper, ApiError
  src/lib/church.ts (+ church.test.ts) Church/Me types, active-church selection
  src/app/layout.tsx  src/app/page.tsx  src/app/login/page.tsx  src/app/auth/callback/route.ts
  src/components/app-header.tsx
  src/components/ui/*          shadcn/ui generated
  vitest.config.ts  .env.example
.github/workflows/ci.yml       backend tests + frontend checks on PRs
```

---

### Task 1: Merge the multi-church branch into `main`

This task has no new code. It lands the multi-church work on `main` and starts the slice-0 branch.

**Files:** none changed (git operations only)

**Interfaces:**
- Produces: branch `claude/react-fastapi-slice0` off the updated `origin/main`, containing the spec and this plan.

- [ ] **Step 1: Make sure the branch is fully pushed**

```bash
git fetch origin
git log --oneline origin/claude/multi-user-app-support-edd5eb..claude/multi-user-app-support-edd5eb
```
Expected: no output. If commits are listed, run `git push origin claude/multi-user-app-support-edd5eb`.

- [ ] **Step 2: Confirm it's a fast-forward of main**

```bash
git merge-base --is-ancestor origin/main origin/claude/multi-user-app-support-edd5eb && echo fast-forward-ok
```
Expected: `fast-forward-ok`

- [ ] **Step 3: Run the branch's test suite**

```bash
git switch --detach origin/claude/multi-user-app-support-edd5eb
test -x .venv/bin/python || /Users/beaubrown/.local/bin/python3.11 -m venv .venv
.venv/bin/pip install -q -r requirements.txt pytest
.venv/bin/python -m pytest -q | tail -3
```
Expected: all tests pass. Record the pass count (e.g. `127 passed`); Task 3 must end with the same count plus the new tests.

- [ ] **Step 4: Open the PR**

```bash
gh pr create --base main --head claude/multi-user-app-support-edd5eb \
  --title "Multi-church app: Supabase Postgres, Google login, church isolation" \
  --body "Merges the multi-church rework (SQLAlchemy + Supabase, Streamlit OIDC login, per-church tenancy, ~30 test files) into main as the base for the React + FastAPI migration (docs/superpowers/specs/2026-09-25-react-fastapi-migration-design.md).

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```

- [ ] **Step 5: Ask the user to approve the merge, then merge**

Merging to `main` is shared and outward-facing — get an explicit yes first. Then:

```bash
gh pr merge --merge claude/multi-user-app-support-edd5eb
```

- [ ] **Step 6: Start the slice-0 branch with the spec and plan**

```bash
git fetch origin
git switch -c claude/react-fastapi-slice0 origin/main
git checkout claude/church-app-stack-review-975f27 -- \
  docs/superpowers/specs/2026-09-25-react-fastapi-migration-design.md \
  docs/superpowers/plans/2026-09-25-react-fastapi-slice0.md
git commit -m "Add React + FastAPI migration spec and slice 0 plan

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
.venv/bin/python -m pytest -q | tail -1
```
Expected: same pass count as Step 3.

---

### Task 2: Split Streamlit helpers out of `auth.py` and `tenancy.py`

Still at the repo root — the move to `backend/` is Task 3. Doing the split first keeps each diff reviewable.

**Files:**
- Create: `streamlit_auth.py`, `streamlit_tenancy.py`, `tests/test_streamlit_tenancy.py`, `tests/test_no_streamlit_in_core.py`
- Modify: `auth.py` (remove Streamlit functions), `tenancy.py` (remove session-state functions), `app.py:39-40` (imports), `tests/test_tenancy.py` (keep only DB-level tests)

**Interfaces:**
- Consumes: existing `auth.upsert_from_claims(claims: dict) -> uuid.UUID`, `auth._normalize_email(str) -> str`, `tenancy.validate_active_church(candidate, user_id) -> dict | None`, `tenancy.is_admin(role) -> bool`, `repos.churches.list_user_churches(user_id) -> list[dict]`.
- Produces: `auth` and `tenancy` import without Streamlit. `streamlit_auth.require_login()`, `streamlit_auth.current_user_id()`, `streamlit_auth.do_logout()`; `streamlit_tenancy.require_active_church(user_id, state=None)`, `set_active_church(...)`, `clear_all_church_state(state=None)`, `CHURCH_SCOPED_STATE_KEYS`, `CHURCH_SCOPED_STATE_PREFIXES` — same signatures and behavior as before, new module names.

- [ ] **Step 1: Write the failing test**

Create `tests/test_no_streamlit_in_core.py`:

```python
"""The API imports auth and tenancy, and the API must run without Streamlit."""
import subprocess
import sys
from pathlib import Path

# The directory that holds tests/ — the repo root now, backend/ after the move.
CODE_DIR = Path(__file__).resolve().parents[1]


def test_auth_and_tenancy_do_not_import_streamlit():
    code = "import sys, auth, tenancy; sys.exit(1 if 'streamlit' in sys.modules else 0)"
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=CODE_DIR, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr or "streamlit was imported"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_no_streamlit_in_core.py -v`
Expected: FAIL (`auth.py` does `import streamlit as st`).

- [ ] **Step 3: Create `streamlit_auth.py`**

```python
"""Streamlit login shell around auth.upsert_from_claims (st.user / st.login).

Removed in the final migration slice together with the Streamlit app.
"""
import uuid
from typing import Optional

import streamlit as st
from sqlalchemy import select

from auth import _normalize_email, upsert_from_claims
from db import session_scope
from db.models import User


def require_login() -> dict:
    """Ensure a signed-in Streamlit user; render a gate and stop otherwise.

    On success upserts the users row and returns
    {"user_id": UUID, "email": str, "name": str, "picture": str}.
    """
    if not getattr(st.user, "is_logged_in", False):
        st.title("Worship Service Builder")
        st.write("Please sign in with Google to continue.")
        st.button("Sign in with Google", on_click=st.login)
        st.stop()

    user_id = upsert_from_claims(
        {
            "email": st.user.email,
            "sub": getattr(st.user, "sub", None),
            "name": getattr(st.user, "name", None),
            "picture": getattr(st.user, "picture", None),
        }
    )
    return {
        "user_id": user_id,
        "email": _normalize_email(st.user.email),
        "name": getattr(st.user, "name", None),
        "picture": getattr(st.user, "picture", None),
    }


def current_user_id() -> Optional[uuid.UUID]:
    """The signed-in user's id via a read-only lookup, or None if not logged in."""
    if not getattr(st.user, "is_logged_in", False):
        return None
    email = _normalize_email(st.user.email)
    if not email:
        return None
    with session_scope() as session:
        user = session.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()
        return user.id if user else None


def do_logout() -> None:
    """Clear church-scoped session state, then the app's local identity cookie.

    Clearing church state first matters on a shared browser: the next user must
    not inherit the previous user's active church / cached hymnal.
    """
    from streamlit_tenancy import clear_all_church_state

    clear_all_church_state()
    st.logout()
```

- [ ] **Step 4: Trim `auth.py` to the Streamlit-free core**

Replace the module docstring and imports, and delete `require_login`, `current_user_id`, and `do_logout` (they now live in `streamlit_auth.py`). The file becomes:

```python
"""Identity helpers shared by every front end.

upsert_from_claims turns a plain dict of identity claims (email, sub, name,
picture) into a persisted users row and returns its id. Users are keyed on the
normalized (lower-cased) email; google_sub is a stable secondary identifier.
Streamlit login helpers live in streamlit_auth.py.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select

from db import session_scope
from db.models import User


def _normalize_email(email: Optional[str]) -> str:
    return (email or "").strip().lower()
```
followed by the existing `upsert_from_claims` function, unchanged.

- [ ] **Step 5: Create `streamlit_tenancy.py`**

```python
"""Streamlit session-state side of tenancy: which church is active in this
browser session. The database check itself is tenancy.validate_active_church.

Removed in the final migration slice together with the Streamlit app.
"""
from typing import Optional

from repos.churches import list_user_churches
from tenancy import validate_active_church

# Every church-scoped key that a church switch (or a drop to zero churches) must
# pop from st.session_state so no stale previous-church read can survive.
CHURCH_SCOPED_STATE_KEYS = (
    "active_church_id",
    "active_church_name",
    "active_church_role",
    "_cached_all_hymns",
    "_hymn_title_to_info",
    "_cached_saved_services",
    "scripture_hymns",
    "scripture_refs_used",
    "opening",
    "response",
    "closing",
    "opening_man",
    "response_man",
    "closing_man",
    "editing_service_id",
    "load_service_id",
    "liturgy",
    "include_communion",
    "custom_elements",
)

# Dynamic key families (e.g. liturgy_opening, liturgy_response, ...).
CHURCH_SCOPED_STATE_PREFIXES = ("liturgy_",)


def _session_state():
    import streamlit as st
    return st.session_state


def set_active_church(church_id, name=None, role=None, state=None) -> None:
    store = state if state is not None else _session_state()
    store["active_church_id"] = church_id
    if name is not None:
        store["active_church_name"] = name
    if role is not None:
        store["active_church_role"] = role


def clear_all_church_state(state=None) -> None:
    """Pop every church-scoped key (exact names + prefix families) so a church
    switch or a zero-church transition cannot leak previous-church data."""
    store = state if state is not None else _session_state()
    for key in list(store.keys()):
        if key in CHURCH_SCOPED_STATE_KEYS or any(
            key.startswith(p) for p in CHURCH_SCOPED_STATE_PREFIXES
        ):
            store.pop(key, None)


def require_active_church(user_id, state=None) -> Optional[dict]:
    """Run at the top of every church-scoped render. Reads the untrusted
    active_church_id from session, validates it against the user's real
    membership, and on failure falls back to the user's first church (or the
    zero-church empty state). Writes the validated selector back to session.
    Returns {"church_id","name","role"} or None.
    """
    store = state if state is not None else _session_state()
    validated = validate_active_church(store.get("active_church_id"), user_id)
    if validated is None:
        churches = list_user_churches(user_id)
        if not churches:
            clear_all_church_state(store)
            return None
        validated = validate_active_church(churches[0]["id"], user_id)
        if validated is None:
            clear_all_church_state(store)
            return None
    set_active_church(
        validated["church_id"],
        name=validated["name"],
        role=validated["role"],
        state=store,
    )
    return validated
```

- [ ] **Step 6: Trim `tenancy.py` to the database core**

The whole file becomes:

```python
"""Church membership checks shared by every front end.

validate_active_church is the single tenancy guard: given an untrusted church
id and a user id, it re-derives membership and role from the database.
Streamlit session-state helpers live in streamlit_tenancy.py.
"""
import uuid
from typing import Optional

from sqlalchemy import select

from db import session_scope
from db.models import Church, Membership

_ADMIN_ROLES = ("owner", "admin")


def is_admin(role) -> bool:
    return role in _ADMIN_ROLES


def _coerce_uuid(value) -> Optional[uuid.UUID]:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return None


def validate_active_church(candidate_church_id, user_id) -> Optional[dict]:
    """Pure tenancy core. Given an *untrusted* candidate church id and a user id,
    confirm the user has a membership in that church and the church is not
    soft-deleted, and re-derive the role from the database. Returns
    {"church_id","name","role"} or None. Never trusts a session-cached role.
    """
    cid = _coerce_uuid(candidate_church_id)
    if cid is None or user_id is None:
        return None
    with session_scope() as session:
        row = session.execute(
            select(Church.id, Church.name, Membership.role)
            .join(Membership, Membership.church_id == Church.id)
            .where(
                Membership.church_id == cid,
                Membership.user_id == user_id,
                Church.deleted_at.is_(None),
            )
        ).one_or_none()
        if row is None:
            return None
        return {"church_id": row.id, "name": row.name, "role": row.role}
```

- [ ] **Step 7: Point `app.py` at the new modules**

In `app.py`, replace lines 39–40:

```python
from auth import require_login, do_logout
from tenancy import require_active_church
```
with:
```python
from streamlit_auth import require_login, do_logout
from streamlit_tenancy import require_active_church
```

- [ ] **Step 8: Split the tenancy tests**

In `tests/test_tenancy.py`, change the import block at the top to:

```python
from tenancy import validate_active_church, is_admin
```
and delete these tests from it (they move below): `test_require_active_church_ignores_forged_session_value`, `test_require_active_church_zero_church_returns_none_and_clears`, `test_set_active_church_writes_selector_keys`, `test_clear_all_church_state_pops_scoped_and_prefixed_keys`, `test_church_scoped_keys_cover_known_state`.

Create `tests/test_streamlit_tenancy.py`:

```python
import uuid

from repos.churches import create_church
from streamlit_tenancy import (
    require_active_church, set_active_church, clear_all_church_state,
    CHURCH_SCOPED_STATE_KEYS, CHURCH_SCOPED_STATE_PREFIXES,
)


def test_require_active_church_ignores_forged_session_value(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    cid = create_church(name="First", timezone="UTC", owner_user_id=owner)
    state = {"active_church_id": uuid.uuid4()}       # forged: not the user's church
    out = require_active_church(owner, state=state)
    assert out["church_id"] == cid                   # fell back to real membership
    assert state["active_church_id"] == cid          # session corrected server-side
    assert state["active_church_role"] == "owner"


def test_require_active_church_zero_church_returns_none_and_clears(tmp_db, make_user):
    user = make_user(email="lonely@x.com")
    state = {"active_church_id": uuid.uuid4(), "_cached_all_hymns": {"x": 1}}
    out = require_active_church(user, state=state)
    assert out is None
    assert "_cached_all_hymns" not in state          # church-scoped state cleared


def test_set_active_church_writes_selector_keys():
    state = {}
    set_active_church(uuid.uuid4(), name="Grace", role="admin", state=state)
    assert state["active_church_name"] == "Grace"
    assert state["active_church_role"] == "admin"


def test_clear_all_church_state_pops_scoped_and_prefixed_keys():
    state = {
        "_cached_all_hymns": 1,
        "liturgy_opening": "x",   # prefix match
        "opening_man": "y",       # exact match
        "keep_me": "stays",
    }
    clear_all_church_state(state)
    assert state == {"keep_me": "stays"}


def test_church_scoped_keys_cover_known_state():
    for k in ("_cached_all_hymns", "scripture_hymns", "custom_elements", "include_communion"):
        assert k in CHURCH_SCOPED_STATE_KEYS
    assert "liturgy_" in CHURCH_SCOPED_STATE_PREFIXES
```

- [ ] **Step 9: Run the full suite**

Run: `.venv/bin/python -m pytest -q | tail -1`
Expected: all pass; count = Task 1 count + 1 (the new no-Streamlit test).

- [ ] **Step 10: Commit**

```bash
git add auth.py tenancy.py streamlit_auth.py streamlit_tenancy.py app.py \
  tests/test_tenancy.py tests/test_streamlit_tenancy.py tests/test_no_streamlit_in_core.py
git commit -m "Split Streamlit helpers out of auth and tenancy

auth.py and tenancy.py are now importable without Streamlit so the
upcoming API can reuse them.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Move the Python core into `backend/`

**Files:**
- Move: `db/`, `repos/`, `tests/`, and every root `*.py` except `app.py`, `ui_helpers.py`, `streamlit_auth.py`, `streamlit_tenancy.py` → `backend/`
- Move: `views/` → `streamlit_views/`
- Move: Streamlit-only tests → `streamlit_tests/`
- Create: `pytest.ini`, `requirements-dev.txt`, `backend/requirements.txt`, `streamlit_tests/__init__.py`, `streamlit_tests/conftest.py`
- Modify: `requirements.txt`, `app.py` (sys.path + views import), `streamlit_tests/test_settings_*.py` (import path), `backend/tests/test_foundation_setup.py`, `backend/tests/test_docs.py`, `backend/tests/test_keepalive.py`, `backend/migrate_to_db.py:506`, `.github/workflows/keepalive.yml`

**Interfaces:**
- Consumes: Task 2's Streamlit-free `auth.py` / `tenancy.py`.
- Produces: `backend/` is the Python import root for all core modules (`db`, `repos`, `auth`, `tenancy`, …). `pytest` from the repo root runs everything. Backend test helpers are importable as `tests.<module>`.

- [ ] **Step 1: Update the foundation test for the new layout (failing test)**

Replace the contents of `tests/test_foundation_setup.py` (it moves with `tests/` in Step 2, which is why `ROOT` is `parents[2]`) with:

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]   # repo root (this file is backend/tests/...)


def test_backend_requirements_pin_runtime_and_migration_deps():
    text = (ROOT / "backend" / "requirements.txt").read_text()
    assert "SQLAlchemy>=2.0" in text
    assert "psycopg2-binary" in text
    # notion-client is kept ONLY for the one-time migration script.
    assert "notion-client" in text
    assert "migration only" in text.lower()
    # The API must not depend on Streamlit.
    assert "streamlit" not in text.lower()


def test_root_requirements_add_streamlit_on_top_of_backend():
    text = (ROOT / "requirements.txt").read_text()
    assert "-r backend/requirements.txt" in text
    assert "streamlit[auth]>=1.45.0" in text
    # The old shared-password-era bare streamlit pin must be gone.
    assert "\nstreamlit>=1.28.0" not in text


def test_gitignore_covers_local_db_and_secrets():
    text = (ROOT / ".gitignore").read_text()
    assert "data/*.db" in text
    assert ".streamlit/secrets.toml" in text
```

- [ ] **Step 2: Move the files**

```bash
mkdir -p backend streamlit_tests
git mv db repos tests backend/
for f in *.py; do
  case "$f" in
    app.py|ui_helpers.py|streamlit_auth.py|streamlit_tenancy.py) ;;
    *) git mv "$f" backend/ ;;
  esac
done
git mv views streamlit_views
git mv backend/tests/test_app_helpers.py backend/tests/test_onboarding.py \
  backend/tests/test_selectbox_safety.py backend/tests/test_settings_members_invites.py \
  backend/tests/test_settings_profile_contacts.py backend/tests/test_settings_prompts_translation.py \
  backend/tests/test_streamlit_tenancy.py streamlit_tests/
ls
```
Expected root listing: `README.md app.py backend data docs requirements.txt streamlit_auth.py streamlit_tenancy.py streamlit_tests streamlit_views ui_helpers.py` (plus dotfiles).

- [ ] **Step 3: Split the requirements**

Create `backend/requirements.txt`:

```
# --- Runtime ---
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

# --- migration only (one-time Notion -> Postgres import; NOT a runtime dependency) ---
notion-client>=2.2.1
```

Replace root `requirements.txt` with:

```
# Streamlit app (legacy UI, removed in the final migration slice).
# Streamlit Community Cloud installs this file.
-r backend/requirements.txt
streamlit[auth]>=1.45.0
```

Create `requirements-dev.txt`:

```
-r requirements.txt
pytest>=8.0
```

- [ ] **Step 4: Configure pytest for two test folders**

Create `pytest.ini`:

```ini
[pytest]
pythonpath = . backend
testpaths = backend/tests streamlit_tests
```

Create `streamlit_tests/__init__.py` (empty).

Create `streamlit_tests/conftest.py`:

```python
"""Reuse the backend's database fixtures for the Streamlit-only tests."""
from tests.conftest import make_church, make_user, seed_catalog, tmp_db  # noqa: F401
```

- [ ] **Step 5: Fix import paths**

```bash
sed -i '' 's/from views\.settings import/from streamlit_views.settings import/' streamlit_tests/test_settings_*.py
sed -i '' 's/^import views\.settings as settings_page$/import streamlit_views.settings as settings_page/' app.py
grep -rn "views\.settings" app.py streamlit_tests | grep -v streamlit_views
```
Expected: no output from the final grep.

In `app.py`, directly after the module docstring (before `import logging`), insert:

```python
import sys
from pathlib import Path

# The core Python modules live in backend/ (shared with the FastAPI app).
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))
```

- [ ] **Step 6: Fix repo-root paths in moved tests and scripts**

In `backend/tests/test_docs.py` and `backend/tests/test_keepalive.py`, change:
```python
ROOT = pathlib.Path(__file__).resolve().parent.parent
```
to:
```python
ROOT = pathlib.Path(__file__).resolve().parents[2]   # repo root
```

In `backend/migrate_to_db.py` line 506, change:
```python
    path = os.path.join(os.path.dirname(__file__), "data", "email_contacts.json")
```
to:
```python
    path = os.path.join(os.path.dirname(__file__), "..", "data", "email_contacts.json")
```

In `.github/workflows/keepalive.yml`, add `working-directory: backend` to the last step:
```yaml
      - name: SELECT 1
        working-directory: backend
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: python keepalive.py
```

- [ ] **Step 7: Run the full suite**

```bash
.venv/bin/pip install -q -r requirements-dev.txt
.venv/bin/python -m pytest -q | tail -1
```
Expected: zero failures, nothing skipped; count = end of Task 2 + 1 (the foundation test file went from 2 tests to 3).

- [ ] **Step 8: Smoke-test the Streamlit app**

```bash
.venv/bin/python -m streamlit run app.py --server.headless true --server.port 8599 &
sleep 8; curl -s http://localhost:8599/_stcore/health; echo
```
Expected: `ok`. Then open http://localhost:8599 in the browser pane and confirm the "Please sign in with Google" page renders with no traceback (the script only executes when a browser session connects). Stop the server: `kill %1`.

- [ ] **Step 9: Commit**

```bash
git add -A
git status --short | head -40
git commit -m "Move the Python core into backend/

Streamlit entry stays app.py at the root and prepends backend/ to
sys.path, so the live Streamlit Cloud apps need no settings change.
Streamlit-only tests move to streamlit_tests/; pytest.ini runs both.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
Check `git status --short` shows renames (`R`), not delete+add pairs, for moved files.

---

### Task 4: FastAPI app skeleton — settings, error shape, CORS, `/health`

**Files:**
- Create: `backend/api/__init__.py`, `backend/api/settings.py`, `backend/api/errors.py`, `backend/api/main.py`, `backend/api/routes/__init__.py`, `backend/api/routes/health.py`, `backend/.env.example`
- Modify: `backend/requirements.txt`
- Test: `backend/tests/test_api_app.py`

**Interfaces:**
- Produces:
  - `api.settings.Settings(supabase_url: str, cors_origins: tuple[str, ...])` with properties `jwks_url` and `token_issuer`; `api.settings.get_settings() -> Settings` (lru-cached; tests call `get_settings.cache_clear()`); `api.settings._split_origins(raw: str) -> tuple[str, ...]`.
  - `api.errors.ApiError(status: int, code: str, message: str)`; factories `unauthenticated(message=...)`, `forbidden(message=...)`, `auth_unavailable()`; `install_error_handlers(app)`.
  - `api.main.create_app() -> FastAPI` and module-level `app`.

- [ ] **Step 1: Add dependencies**

In `backend/requirements.txt`, add these three lines at the top of the `# --- Runtime ---` block:

```
fastapi>=0.115
uvicorn[standard]>=0.30
PyJWT[crypto]>=2.8
```
Then: `.venv/bin/pip install -q -r requirements-dev.txt`

- [ ] **Step 2: Write the failing tests**

Create `backend/tests/test_api_app.py`:

```python
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter
from fastapi.testclient import TestClient

from api import settings as settings_mod
from api.main import create_app
from api.settings import _split_origins

BACKEND = Path(__file__).resolve().parents[1]


def test_health_ok():
    r = TestClient(create_app()).get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_unknown_route_uses_error_shape():
    r = TestClient(create_app()).get("/nope")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


def test_validation_error_uses_error_shape():
    app = create_app()
    router = APIRouter()

    @router.get("/needs-int")
    def needs_int(n: int):
        return {"n": n}

    app.include_router(router)
    r = TestClient(app).get("/needs-int?n=abc")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "invalid_request"


def test_unhandled_exception_is_a_generic_500():
    app = create_app()
    router = APIRouter()

    @router.get("/boom")
    def boom():
        raise RuntimeError("secret detail")

    app.include_router(router)
    r = TestClient(app, raise_server_exceptions=False).get("/boom")
    assert r.status_code == 500
    assert r.json() == {"error": {"code": "internal_error", "message": "Something went wrong."}}
    assert "secret detail" not in r.text


def test_cors_allows_only_configured_origins(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://church.example.app")
    settings_mod.get_settings.cache_clear()
    try:
        client = TestClient(create_app())
        preflight = {"Access-Control-Request-Method": "GET"}
        ok = client.options("/health", headers={"Origin": "https://church.example.app", **preflight})
        assert ok.headers.get("access-control-allow-origin") == "https://church.example.app"
        bad = client.options("/health", headers={"Origin": "https://evil.example", **preflight})
        assert "access-control-allow-origin" not in bad.headers
    finally:
        settings_mod.get_settings.cache_clear()


def test_split_origins_trims_slashes_and_blanks():
    assert _split_origins(" https://a.app/ , ,http://localhost:3000") == (
        "https://a.app",
        "http://localhost:3000",
    )


def test_settings_derive_supabase_urls(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://abc.supabase.co/")
    settings_mod.get_settings.cache_clear()
    try:
        s = settings_mod.get_settings()
        assert s.jwks_url == "https://abc.supabase.co/auth/v1/.well-known/jwks.json"
        assert s.token_issuer == "https://abc.supabase.co/auth/v1"
    finally:
        settings_mod.get_settings.cache_clear()


def test_api_does_not_import_streamlit():
    code = "import sys, api.main; sys.exit(1 if 'streamlit' in sys.modules else 0)"
    result = subprocess.run([sys.executable, "-c", code], cwd=BACKEND, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr or "streamlit was imported"
```

- [ ] **Step 3: Run them to verify they fail**

Run: `.venv/bin/python -m pytest backend/tests/test_api_app.py -v`
Expected: collection error `ModuleNotFoundError: No module named 'api'`.

- [ ] **Step 4: Implement settings, errors, health, and the app**

Create `backend/api/__init__.py` and `backend/api/routes/__init__.py` (both empty).

Create `backend/api/settings.py`:

```python
"""Runtime configuration for the API, read from environment variables."""
import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    cors_origins: tuple[str, ...]

    @property
    def jwks_url(self) -> str:
        return f"{self.supabase_url}/auth/v1/.well-known/jwks.json"

    @property
    def token_issuer(self) -> str:
        return f"{self.supabase_url}/auth/v1"


def _split_origins(raw: str) -> tuple[str, ...]:
    return tuple(o.strip().rstrip("/") for o in raw.split(",") if o.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings(
        supabase_url=os.environ.get("SUPABASE_URL", "").strip().rstrip("/"),
        cors_origins=_split_origins(os.environ.get("CORS_ORIGINS", "http://localhost:3000")),
    )
```

Create `backend/api/errors.py`:

```python
"""One error shape for every API failure: {"error": {"code", "message"}}."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

_HTTP_CODES = {
    400: "bad_request",
    401: "unauthenticated",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
}


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def unauthenticated(message: str = "Please sign in.") -> ApiError:
    return ApiError(401, "unauthenticated", message)


def forbidden(message: str = "You don't have access to this church.") -> ApiError:
    return ApiError(403, "forbidden", message)


def auth_unavailable() -> ApiError:
    return ApiError(503, "auth_unavailable", "Sign-in is temporarily unavailable. Try again shortly.")


def _body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_request: Request, exc: ApiError):
        return JSONResponse(_body(exc.code, exc.message), status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def _invalid(_request: Request, _exc: RequestValidationError):
        return JSONResponse(_body("invalid_request", "The request was not valid."), status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_request: Request, exc: StarletteHTTPException):
        code = _HTTP_CODES.get(exc.status_code, "error")
        message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return JSONResponse(_body(code, message), status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, _exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(_body("internal_error", "Something went wrong."), status_code=500)
```

Create `backend/api/routes/health.py`:

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"ok": True}
```

Create `backend/api/main.py`:

```python
"""FastAPI entry point. Run from backend/: uvicorn api.main:app --reload"""
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.errors import install_error_handlers
from api.routes import health
from api.settings import get_settings
from db import init_db

load_dotenv()

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(name)s %(levelname)s %(message)s",
    )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()   # create_all: no-op on existing tables, creates them for local SQLite
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Worship Service Builder API", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Church-Id"],
    )
    install_error_handlers(app)
    app.include_router(health.router)
    return app


app = create_app()
```

Create `backend/.env.example`:

```
# Copy to backend/.env for local dev. Never commit .env.

# Database. Local: the SAME SQLite file the Streamlit app uses (run from backend/).
# Production: the Supabase SESSION POOLER URL (see README).
DATABASE_URL=sqlite:///../data/app.db

# Supabase project URL, e.g. https://<project-ref>.supabase.co
# Used to fetch the public keys that sign users' access tokens.
SUPABASE_URL=

# Comma-separated browser origins allowed to call the API.
CORS_ORIGINS=http://localhost:3000

# Carried over for later slices (liturgy generation, Gmail sending).
OPENAI_API_KEY=
OPENAI_MODEL=gpt-3.5-turbo
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_OAUTH_REDIRECT_URI=
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest backend/tests/test_api_app.py -v`
Expected: 8 passed.

- [ ] **Step 6: Run the full suite and commit**

```bash
.venv/bin/python -m pytest -q | tail -1
git add backend/api backend/requirements.txt backend/.env.example backend/tests/test_api_app.py
git commit -m "Add FastAPI skeleton: health, CORS, uniform error shape

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Supabase token verification

**Files:**
- Create: `backend/api/security.py`, `backend/tests/jwt_helpers.py`
- Test: `backend/tests/test_api_security.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `api.security.InvalidToken(Exception)`, `api.security.AuthUnavailable(Exception)`
  - `api.security.KeyResolver = Callable[[str], Any]` — takes the raw token, returns a verification key.
  - `api.security.jwks_key_resolver(jwks_url: str) -> KeyResolver`
  - `api.security.TokenVerifier(key_resolver: KeyResolver, issuer: str, audience: str = "authenticated")` with `.verify(token: str) -> dict` (claims). Raises `InvalidToken` or `AuthUnavailable`.
  - `api.security.claims_to_profile(claims: dict) -> dict` returning `{"email", "sub", "name", "picture"}` for `auth.upsert_from_claims`.
  - `tests.jwt_helpers`: `ISSUER: str`, `SIGNING_KEY` (RSA private key), `new_rsa_key()`, `make_token(*, email=..., provider="google", google_sub="google-sub-1", name="Pat Tor", picture="https://x/p.png", aud="authenticated", iss=ISSUER, expires_in=3600, key=None) -> str`.

- [ ] **Step 1: Create the test token helper**

Create `backend/tests/jwt_helpers.py`:

```python
"""Mint Supabase-shaped access tokens signed with a local test key."""
import time
import uuid

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

ISSUER = "https://test-project.supabase.co/auth/v1"


def new_rsa_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


SIGNING_KEY = new_rsa_key()


def make_token(
    *,
    email="pastor@example.com",
    provider="google",
    google_sub="google-sub-1",
    name="Pat Tor",
    picture="https://x/p.png",
    aud="authenticated",
    iss=ISSUER,
    expires_in=3600,
    key=None,
) -> str:
    now = int(time.time())
    claims = {
        "sub": str(uuid.uuid4()),          # Supabase's own user id (not used by us)
        "aud": aud,
        "iss": iss,
        "iat": now,
        "exp": now + expires_in,
        "role": "authenticated",
        "email": email,
        "app_metadata": {"provider": provider, "providers": [provider]},
        "user_metadata": {
            "email": email,
            "provider_id": google_sub,
            "sub": google_sub,
            "full_name": name,
            "name": name,
            "avatar_url": picture,
            "picture": picture,
        },
    }
    return jwt.encode(claims, key or SIGNING_KEY, algorithm="RS256", headers={"kid": "test-key"})
```

- [ ] **Step 2: Write the failing tests**

Create `backend/tests/test_api_security.py`:

```python
import jwt
import pytest
from jwt import PyJWKClient
from jwt.algorithms import RSAAlgorithm
from jwt.exceptions import PyJWKClientConnectionError

from api.security import (
    AuthUnavailable,
    InvalidToken,
    TokenVerifier,
    claims_to_profile,
    jwks_key_resolver,
)
from tests.jwt_helpers import ISSUER, SIGNING_KEY, make_token, new_rsa_key


def _verifier():
    return TokenVerifier(lambda _token: SIGNING_KEY.public_key(), issuer=ISSUER)


def test_valid_google_token_returns_claims():
    claims = _verifier().verify(make_token(email="a@b.com"))
    assert claims["email"] == "a@b.com"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"expires_in": -60},
        {"aud": "anon"},
        {"iss": "https://someone-else.supabase.co/auth/v1"},
        {"provider": "email"},
        {"key": new_rsa_key()},
    ],
    ids=["expired", "wrong-audience", "wrong-issuer", "non-google-provider", "bad-signature"],
)
def test_rejects_bad_tokens(kwargs):
    with pytest.raises(InvalidToken):
        _verifier().verify(make_token(**kwargs))


def test_rejects_garbage():
    with pytest.raises(InvalidToken):
        _verifier().verify("not-a-jwt")


def test_rejects_hmac_signed_token():
    """Algorithm confusion: only RS256/ES256 are accepted."""
    forged = jwt.encode(
        {"aud": "authenticated", "iss": ISSUER, "sub": "x", "exp": 9999999999,
         "app_metadata": {"provider": "google"}},
        "shared-secret",
        algorithm="HS256",
    )
    with pytest.raises(InvalidToken):
        _verifier().verify(forged)


def test_key_fetch_failure_fails_closed():
    def unreachable(_token):
        raise PyJWKClientConnectionError("jwks down")

    with pytest.raises(AuthUnavailable):
        TokenVerifier(unreachable, issuer=ISSUER).verify(make_token())


def test_jwks_resolver_finds_key_by_kid(monkeypatch):
    jwk = RSAAlgorithm.to_jwk(SIGNING_KEY.public_key(), as_dict=True)
    jwk.update({"kid": "test-key", "alg": "RS256", "use": "sig"})
    monkeypatch.setattr(PyJWKClient, "fetch_data", lambda self: {"keys": [jwk]})
    resolve = jwks_key_resolver("https://test-project.supabase.co/auth/v1/.well-known/jwks.json")
    claims = TokenVerifier(resolve, issuer=ISSUER).verify(make_token())
    assert claims["email"] == "pastor@example.com"


def test_claims_to_profile_maps_google_identity():
    token = make_token(email="p@x.com", google_sub="g-123", name="Pat", picture="https://x/p.png")
    claims = jwt.decode(token, options={"verify_signature": False})
    assert claims_to_profile(claims) == {
        "email": "p@x.com",
        "sub": "g-123",
        "name": "Pat",
        "picture": "https://x/p.png",
    }
```

- [ ] **Step 3: Run them to verify they fail**

Run: `.venv/bin/python -m pytest backend/tests/test_api_security.py -v`
Expected: collection error `ModuleNotFoundError: No module named 'api.security'`.

- [ ] **Step 4: Implement `api/security.py`**

```python
"""Verify Supabase access tokens and map them to our identity claims.

Supabase signs access tokens with an asymmetric key and publishes the public
keys at {SUPABASE_URL}/auth/v1/.well-known/jwks.json. We verify signature,
expiry, audience and issuer, and accept only Google sign-ins: users are keyed
by email, so a password signup using someone else's address must never pass.
"""
from typing import Any, Callable

import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError

ALGORITHMS = ["RS256", "ES256"]

KeyResolver = Callable[[str], Any]


class InvalidToken(Exception):
    """Missing, malformed, forged, expired, or not a Google sign-in."""


class AuthUnavailable(Exception):
    """The signing keys could not be fetched. Callers must fail closed."""


def jwks_key_resolver(jwks_url: str) -> KeyResolver:
    """Resolve a token's key from Supabase's JWKS (cached; refetched on unknown kid)."""
    client = PyJWKClient(jwks_url, cache_keys=True)

    def resolve(token: str):
        return client.get_signing_key_from_jwt(token).key

    return resolve


class TokenVerifier:
    def __init__(self, key_resolver: KeyResolver, issuer: str, audience: str = "authenticated"):
        self._resolve_key = key_resolver
        self._issuer = issuer
        self._audience = audience

    def verify(self, token: str) -> dict:
        try:
            key = self._resolve_key(token)
        except PyJWKClientConnectionError as exc:
            raise AuthUnavailable(str(exc)) from exc
        except (PyJWKClientError, jwt.PyJWTError) as exc:
            raise InvalidToken(str(exc)) from exc
        try:
            claims = jwt.decode(
                token,
                key,
                algorithms=ALGORITHMS,
                audience=self._audience,
                issuer=self._issuer,
                options={"require": ["exp", "sub", "aud", "iss"]},
            )
        except jwt.PyJWTError as exc:
            raise InvalidToken(str(exc)) from exc
        if (claims.get("app_metadata") or {}).get("provider") != "google":
            raise InvalidToken("Only Google sign-in is allowed.")
        return claims


def claims_to_profile(claims: dict) -> dict:
    """Shape Supabase claims for auth.upsert_from_claims.

    `sub` is Google's subject id (user_metadata.provider_id), matching what the
    Streamlit login stored in users.google_sub — not Supabase's own user id.
    """
    meta = claims.get("user_metadata") or {}
    return {
        "email": claims.get("email") or meta.get("email"),
        "sub": meta.get("provider_id") or meta.get("sub"),
        "name": meta.get("full_name") or meta.get("name"),
        "picture": meta.get("avatar_url") or meta.get("picture"),
    }
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest backend/tests/test_api_security.py -v`
Expected: 11 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/api/security.py backend/tests/jwt_helpers.py backend/tests/test_api_security.py
git commit -m "Verify Supabase access tokens (JWKS, Google-only)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Request guards and the `/me` and `/church` endpoints

**Files:**
- Create: `backend/api/deps.py`, `backend/api/schemas.py`, `backend/api/routes/me.py`
- Modify: `backend/api/main.py` (include the `me` router)
- Test: `backend/tests/test_api_me.py`

**Interfaces:**
- Consumes: `TokenVerifier`, `InvalidToken`, `AuthUnavailable`, `claims_to_profile`, `jwks_key_resolver` (Task 5); `get_settings` (Task 4); `unauthenticated`, `forbidden`, `auth_unavailable`, `ApiError` (Task 4); `auth.upsert_from_claims`; `tenancy.validate_active_church`, `tenancy.is_admin`; `repos.churches.list_user_churches(user_id) -> list[{"id","name","role"}]`.
- Produces:
  - `api.deps.CurrentUser(id: uuid.UUID, email: str, name: str | None, picture: str | None)`
  - `api.deps.ActiveChurch(id: uuid.UUID, name: str, role: str)`
  - `api.deps.get_verifier() -> TokenVerifier` (lru-cached; tests override it via `app.dependency_overrides[get_verifier]`)
  - `api.deps.get_current_user(...) -> CurrentUser`, `api.deps.require_church(...) -> ActiveChurch`, `api.deps.require_admin(church) -> ActiveChurch`
  - `GET /me` → `{"user": {id, email, name, picture}, "churches": [{id, name, role}]}`; `GET /church` → `{id, name, role}`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_api_me.py`:

```python
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from jwt.exceptions import PyJWKClientConnectionError
from sqlalchemy import select

from api.deps import ActiveChurch, get_verifier, require_admin
from api.errors import ApiError
from api.main import create_app
from api.security import TokenVerifier
from db import session_scope
from db.models import Church, User
from tests.jwt_helpers import ISSUER, SIGNING_KEY, make_token


def _test_verifier():
    return TokenVerifier(lambda _token: SIGNING_KEY.public_key(), issuer=ISSUER)


@pytest.fixture
def client(tmp_db):
    app = create_app()
    app.dependency_overrides[get_verifier] = _test_verifier
    return TestClient(app)


def _auth(email="pastor@example.com", **kwargs):
    return {"Authorization": f"Bearer {make_token(email=email, **kwargs)}"}


def test_me_requires_a_token(client):
    r = client.get("/me")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthenticated"


def test_me_rejects_non_bearer_scheme(client):
    assert client.get("/me", headers={"Authorization": "Basic abc"}).status_code == 401


def test_me_rejects_non_google_token(client):
    assert client.get("/me", headers=_auth(provider="email")).status_code == 401


def test_me_creates_user_from_google_identity(client):
    r = client.get("/me", headers=_auth(email="New@Example.com", google_sub="g-42", name="New Person"))
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["email"] == "new@example.com"
    assert body["user"]["name"] == "New Person"
    assert body["churches"] == []
    with session_scope() as s:
        user = s.execute(select(User).where(User.email == "new@example.com")).scalar_one()
        # google_sub comes from user-editable metadata, so the API never writes it.
        assert user.google_sub is None
        assert str(user.id) == body["user"]["id"]


def test_me_matches_existing_streamlit_user_by_email(client, make_user):
    existing = make_user(email="pastor@example.com", google_sub="google-sub-1")
    r = client.get("/me", headers=_auth(email="pastor@example.com", google_sub="google-sub-1"))
    assert r.json()["user"]["id"] == str(existing)


def test_me_lists_only_the_callers_churches(client, make_user, make_church):
    me_id = make_user(email="pastor@example.com")
    mine = make_church(name="Grace", owner_user_id=me_id)
    make_church(name="Someone Else's")
    r = client.get("/me", headers=_auth())
    assert r.json()["churches"] == [{"id": str(mine), "name": "Grace", "role": "owner"}]


def test_church_returns_the_active_church_for_a_member(client, make_user, make_church):
    me_id = make_user(email="pastor@example.com")
    cid = make_church(name="Grace", owner_user_id=me_id)
    r = client.get("/church", headers={**_auth(), "X-Church-Id": str(cid)})
    assert r.status_code == 200
    assert r.json() == {"id": str(cid), "name": "Grace", "role": "owner"}


@pytest.mark.parametrize(
    "church_header", [None, "", "not-a-uuid", str(uuid.uuid4())],
    ids=["missing", "empty", "malformed", "unknown"],
)
def test_church_rejects_missing_malformed_or_unknown_ids(client, make_user, church_header):
    make_user(email="pastor@example.com")
    headers = _auth()
    if church_header is not None:
        headers["X-Church-Id"] = church_header
    r = client.get("/church", headers=headers)
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "forbidden"


def test_church_blocks_other_churches(client, make_user, make_church):
    """Cross-church isolation: a real church id the caller doesn't belong to is refused."""
    make_user(email="pastor@example.com")
    other = make_church(name="Other Church")
    r = client.get("/church", headers={**_auth(), "X-Church-Id": str(other)})
    assert r.status_code == 403
    assert "Other Church" not in r.text


def test_church_blocks_soft_deleted_church(client, make_user, make_church):
    me_id = make_user(email="pastor@example.com")
    cid = make_church(name="Closed", owner_user_id=me_id)
    with session_scope() as s:
        s.get(Church, cid).deleted_at = datetime.now(timezone.utc)
    r = client.get("/church", headers={**_auth(), "X-Church-Id": str(cid)})
    assert r.status_code == 403


def test_church_requires_a_token(client, make_church):
    cid = make_church()
    assert client.get("/church", headers={"X-Church-Id": str(cid)}).status_code == 401


def test_key_outage_returns_503(tmp_db):
    def unreachable(_token):
        raise PyJWKClientConnectionError("jwks down")

    app = create_app()
    app.dependency_overrides[get_verifier] = lambda: TokenVerifier(unreachable, issuer=ISSUER)
    r = TestClient(app).get("/me", headers=_auth())
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "auth_unavailable"


def test_require_admin_allows_owner_and_admin_only():
    for role in ("owner", "admin"):
        church = ActiveChurch(id=uuid.uuid4(), name="Grace", role=role)
        assert require_admin(church) is church
    with pytest.raises(ApiError) as exc:
        require_admin(ActiveChurch(id=uuid.uuid4(), name="Grace", role="member"))
    assert exc.value.status == 403
```

- [ ] **Step 2: Run them to verify they fail**

Run: `.venv/bin/python -m pytest backend/tests/test_api_me.py -v`
Expected: collection error `ModuleNotFoundError: No module named 'api.deps'`.

- [ ] **Step 3: Implement the guards**

Create `backend/api/deps.py`:

```python
"""Request guards: who is calling (get_current_user) and for which church
(require_church). Every church-scoped route must depend on require_church."""
import uuid
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

from fastapi import Depends, Header

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


@dataclass(frozen=True)
class CurrentUser:
    id: uuid.UUID
    email: str
    name: Optional[str]
    picture: Optional[str]


@dataclass(frozen=True)
class ActiveChurch:
    id: uuid.UUID
    name: str
    role: str


@lru_cache
def get_verifier() -> TokenVerifier:
    settings = get_settings()
    return TokenVerifier(jwks_key_resolver(settings.jwks_url), issuer=settings.token_issuer)


def _bearer_token(authorization: Optional[str]) -> str:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise unauthenticated()
    return token.strip()


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    verifier: TokenVerifier = Depends(get_verifier),
) -> CurrentUser:
    token = _bearer_token(authorization)
    try:
        claims = verifier.verify(token)
    except AuthUnavailable:
        raise auth_unavailable() from None
    except InvalidToken:
        raise unauthenticated() from None
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


def require_church(
    user: CurrentUser = Depends(get_current_user),
    x_church_id: Optional[str] = Header(default=None),
) -> ActiveChurch:
    validated = validate_active_church(x_church_id, user.id)
    if validated is None:
        raise forbidden()
    return ActiveChurch(id=validated["church_id"], name=validated["name"], role=validated["role"])


def require_admin(church: ActiveChurch = Depends(require_church)) -> ActiveChurch:
    if not is_admin(church.role):
        raise forbidden("Only church admins can do this.")
    return church
```

Create `backend/api/schemas.py`:

```python
"""Response models (also documented at /docs)."""
import uuid
from typing import Optional

from pydantic import BaseModel


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None


class ChurchOut(BaseModel):
    id: uuid.UUID
    name: str
    role: str


class MeOut(BaseModel):
    user: UserOut
    churches: list[ChurchOut]
```

Create `backend/api/routes/me.py`:

```python
from fastapi import APIRouter, Depends

from api.deps import ActiveChurch, CurrentUser, get_current_user, require_church
from api.schemas import ChurchOut, MeOut, UserOut
from repos.churches import list_user_churches

router = APIRouter()


@router.get("/me", response_model=MeOut)
def me(user: CurrentUser = Depends(get_current_user)) -> MeOut:
    return MeOut(
        user=UserOut(id=user.id, email=user.email, name=user.name, picture=user.picture),
        churches=[ChurchOut(**church) for church in list_user_churches(user.id)],
    )


@router.get("/church", response_model=ChurchOut)
def church(active: ActiveChurch = Depends(require_church)) -> ChurchOut:
    return ChurchOut(id=active.id, name=active.name, role=active.role)
```

In `backend/api/main.py`, change `from api.routes import health` to `from api.routes import health, me`, and after `app.include_router(health.router)` add:

```python
    app.include_router(me.router)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest backend/tests/test_api_me.py -v`
Expected: 16 passed.

- [ ] **Step 5: Run the full suite and commit**

```bash
.venv/bin/python -m pytest -q | tail -1
git add backend/api backend/tests/test_api_me.py
git commit -m "Add sign-in and church guards with /me and /church

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Next.js frontend with Supabase Google login

**Files:**
- Create (generated): `frontend/` via `create-next-app@16`, `frontend/src/components/ui/*` via shadcn
- Create: `frontend/src/lib/supabase/client.ts`, `frontend/src/lib/supabase/server.ts`, `frontend/src/lib/supabase/proxy.ts`, `frontend/src/proxy.ts`, `frontend/src/app/login/page.tsx`, `frontend/src/app/auth/callback/route.ts`, `frontend/.env.example`
- Modify: `frontend/src/app/page.tsx` (placeholder), `frontend/src/app/layout.tsx`, `frontend/.gitignore`, `frontend/package.json` (scripts)

**Interfaces:**
- Produces: `createClient()` from `@/lib/supabase/client` (browser) and `await createClient()` from `@/lib/supabase/server`; `/login` and `/auth/callback` routes; every other route redirects to `/login` when signed out. Env names: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_API_URL`.

- [ ] **Step 1: Scaffold the app**

```bash
npx create-next-app@16 frontend --typescript --tailwind --eslint --app --src-dir \
  --import-alias "@/*" --use-npm --yes
cd frontend
npx shadcn@latest init -d
npx shadcn@latest add button card dropdown-menu select sonner avatar skeleton -y
npm install @supabase/supabase-js @supabase/ssr
npm install -D vitest
cd ..
```
If `shadcn init` asks which component library to use, choose **Radix**. Confirm `frontend/src/components/ui/button.tsx` exists.

- [ ] **Step 2: Add scripts, env example, and un-ignore it**

In `frontend/package.json` `"scripts"`, add:

```json
    "typecheck": "tsc --noEmit",
    "test": "vitest run"
```

Append to `frontend/.gitignore`:

```
!.env.example
```

Create `frontend/.env.example`:

```
# Copy to frontend/.env.local for local dev. These are public (shipped to the browser).
NEXT_PUBLIC_SUPABASE_URL=https://<project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_URL=http://localhost:8000
```

- [ ] **Step 3: Supabase clients and the session proxy**

Create `frontend/src/lib/supabase/client.ts`:

```ts
import { createBrowserClient } from "@supabase/ssr";

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  );
}
```

Create `frontend/src/lib/supabase/server.ts`:

```ts
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

export async function createClient() {
  const cookieStore = await cookies();
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options),
            );
          } catch {
            // Called from a Server Component; the proxy refreshes the session instead.
          }
        },
      },
    },
  );
}
```

Create `frontend/src/lib/supabase/proxy.ts`:

```ts
import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

const PUBLIC_PATHS = ["/login", "/auth"];

/** Refresh the Supabase session cookie and send signed-out visitors to /login. */
export async function updateSession(request: NextRequest) {
  let response = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
          response = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options),
          );
        },
      },
    },
  );

  // Must run before any redirect decision: it refreshes an expired session.
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const isPublic = PUBLIC_PATHS.some((p) => request.nextUrl.pathname.startsWith(p));
  if (!user && !isPublic) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    return NextResponse.redirect(url);
  }
  return response;
}
```

Create `frontend/src/proxy.ts` (Next 16 renamed `middleware.ts` to `proxy.ts`):

```ts
import type { NextRequest } from "next/server";
import { updateSession } from "@/lib/supabase/proxy";

export async function proxy(request: NextRequest) {
  return updateSession(request);
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)"],
};
```

- [ ] **Step 4: Login page and OAuth callback**

Create `frontend/src/app/login/page.tsx`:

```tsx
"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { createClient } from "@/lib/supabase/client";

export default function LoginPage() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function signIn() {
    setBusy(true);
    setError(null);
    const { error } = await createClient().auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}/auth/callback` },
    });
    if (error) {
      setError(error.message);
      setBusy(false);
    }
  }

  return (
    <main className="flex min-h-dvh items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Worship Service Builder</CardTitle>
          <CardDescription>Plan Sunday services with your church.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Button className="w-full" onClick={signIn} disabled={busy}>
            {busy ? "Redirecting…" : "Sign in with Google"}
          </Button>
          {error && <p className="text-sm text-destructive">{error}</p>}
        </CardContent>
      </Card>
    </main>
  );
}
```

Create `frontend/src/app/auth/callback/route.ts`:

```ts
import { NextResponse } from "next/server";

import { createClient } from "@/lib/supabase/server";

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) return NextResponse.redirect(`${origin}/`);
  }
  return NextResponse.redirect(`${origin}/login?error=auth`);
}
```

- [ ] **Step 5: Layout and a placeholder home page**

Replace `frontend/src/app/layout.tsx`:

```tsx
import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import { Toaster } from "@/components/ui/sonner";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
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
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        {children}
        <Toaster richColors />
      </body>
    </html>
  );
}
```

Replace `frontend/src/app/page.tsx` (Task 9 replaces it with the real home):

```tsx
export default function Home() {
  return <main className="p-4">Signed in.</main>;
}
```

- [ ] **Step 6: Verify lint, types, and build**

```bash
cd frontend
cp .env.example .env.local
npm run lint && npm run typecheck && npm run build
cd ..
```
Expected: all three succeed. (`.env.local` holds placeholder values for now; Task 11 fills in real ones. It is gitignored.)

- [ ] **Step 7: Commit**

```bash
git add frontend
git status --short frontend | grep -E "\.env\.local|node_modules|\.next/" && echo "STOP: ignored files staged"
git commit -m "Add Next.js frontend with Supabase Google login

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
The `grep` must print nothing before committing.

---

### Task 8: API client and active-church selection (unit-tested)

**Files:**
- Create: `frontend/vitest.config.ts`, `frontend/src/lib/api.ts`, `frontend/src/lib/church.ts`
- Test: `frontend/src/lib/api.test.ts`, `frontend/src/lib/church.test.ts`

**Interfaces:**
- Consumes: `NEXT_PUBLIC_API_URL`.
- Produces:
  - `class ApiError extends Error { status: number; code: string }`
  - `apiFetch<T>(path: string, opts: { token: string; churchId?: string | null; init?: RequestInit; baseUrl?: string; fetchImpl?: typeof fetch }): Promise<T>` — status `0` / code `network_error` when the server is unreachable.
  - `type Church = { id: string; name: string; role: "owner" | "admin" | "member" }`
  - `type Me = { user: { id: string; email: string; name: string | null; picture: string | null }; churches: Church[] }`
  - `pickActiveChurch(churches: Church[], storedId: string | null): Church | null`
  - `readStoredChurchId(): string | null`, `storeChurchId(id: string | null): void` (localStorage key `activeChurchId`; never throw).

- [ ] **Step 1: Configure Vitest**

Create `frontend/vitest.config.ts`:

```ts
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  test: { environment: "node", include: ["src/**/*.test.ts"] },
});
```

- [ ] **Step 2: Write the failing tests**

Create `frontend/src/lib/church.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import { type Church, pickActiveChurch } from "./church";

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
});
```

Create `frontend/src/lib/api.test.ts`:

```ts
import { describe, expect, it, vi } from "vitest";

import { apiFetch } from "./api";

function jsonFetch(status: number, body: unknown) {
  return vi.fn<typeof fetch>(
    async () =>
      new Response(JSON.stringify(body), {
        status,
        headers: { "Content-Type": "application/json" },
      }),
  );
}

describe("apiFetch", () => {
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
      code: "error",
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
});
```

- [ ] **Step 3: Run them to verify they fail**

Run: `cd frontend && npm test; cd ..`
Expected: FAIL — cannot resolve `./church` and `./api`.

- [ ] **Step 4: Implement**

Create `frontend/src/lib/church.ts`:

```ts
export type Church = { id: string; name: string; role: "owner" | "admin" | "member" };

export type Me = {
  user: { id: string; email: string; name: string | null; picture: string | null };
  churches: Church[];
};

const ACTIVE_CHURCH_KEY = "activeChurchId";

/** The remembered church if the user still belongs to it, else their first church. */
export function pickActiveChurch(churches: Church[], storedId: string | null): Church | null {
  return churches.find((c) => c.id === storedId) ?? churches[0] ?? null;
}

export function readStoredChurchId(): string | null {
  try {
    return window.localStorage.getItem(ACTIVE_CHURCH_KEY);
  } catch {
    return null;
  }
}

export function storeChurchId(id: string | null): void {
  try {
    if (id) window.localStorage.setItem(ACTIVE_CHURCH_KEY, id);
    else window.localStorage.removeItem(ACTIVE_CHURCH_KEY);
  } catch {
    // Storage unavailable (e.g. private mode): the choice just won't be remembered.
  }
}
```

Create `frontend/src/lib/api.ts`:

```ts
export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type ApiOptions = {
  token: string;
  churchId?: string | null;
  init?: RequestInit;
  baseUrl?: string;
  fetchImpl?: typeof fetch;
};

/** Call the FastAPI backend. The server re-checks the church on every request. */
export async function apiFetch<T>(
  path: string,
  {
    token,
    churchId,
    init,
    baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "",
    fetchImpl = fetch,
  }: ApiOptions,
): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Authorization", `Bearer ${token}`);
  if (churchId) headers.set("X-Church-Id", churchId);

  let res: Response;
  try {
    res = await fetchImpl(`${baseUrl}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "network_error", "Can't reach the server. Check your connection and try again.");
  }
  if (res.ok) return (await res.json()) as T;

  let code = "error";
  let message = "Something went wrong.";
  try {
    const body = await res.json();
    code = body?.error?.code ?? code;
    message = body?.error?.message ?? message;
  } catch {
    // Non-JSON error body (e.g. a proxy's HTML page); keep the generic message.
  }
  throw new ApiError(res.status, code, message);
}
```

- [ ] **Step 5: Run the tests, types, and lint**

Run: `cd frontend && npm test && npm run typecheck && npm run lint; cd ..`
Expected: 10 tests pass; typecheck and lint clean.

- [ ] **Step 6: Commit**

```bash
git add frontend/vitest.config.ts frontend/src/lib
git commit -m "Add API client and active-church selection with tests

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Signed-in home with church switcher

**Files:**
- Create: `frontend/src/components/app-header.tsx`
- Modify: `frontend/src/app/page.tsx` (replace placeholder)

**Interfaces:**
- Consumes: `apiFetch`, `ApiError` (`@/lib/api`); `Church`, `Me`, `pickActiveChurch`, `readStoredChurchId`, `storeChurchId` (`@/lib/church`); `createClient` (`@/lib/supabase/client`); shadcn `avatar`, `button`, `card`, `dropdown-menu`, `select`, `skeleton`; `toast` from `sonner`.
- Produces: `AppHeader({ user, churches, active, onSelectChurch, onSignOut })`.

- [ ] **Step 1: Header component**

Create `frontend/src/components/app-header.tsx`:

```tsx
"use client";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { Church, Me } from "@/lib/church";

type Props = {
  user: Me["user"];
  churches: Church[];
  active: Church | null;
  onSelectChurch: (church: Church) => void;
  onSignOut: () => void;
};

export function AppHeader({ user, churches, active, onSelectChurch, onSignOut }: Props) {
  const initial = (user.name ?? user.email).slice(0, 1).toUpperCase();

  return (
    <header className="sticky top-0 z-10 border-b bg-background/95 backdrop-blur">
      <div className="mx-auto flex max-w-3xl items-center gap-3 px-4 py-3">
        <div className="min-w-0 flex-1">
          {churches.length > 0 ? (
            <Select
              value={active?.id ?? ""}
              onValueChange={(id) => {
                const church = churches.find((c) => c.id === id);
                if (church) onSelectChurch(church);
              }}
            >
              <SelectTrigger className="w-full max-w-xs" aria-label="Active church">
                <SelectValue placeholder="Choose a church" />
              </SelectTrigger>
              <SelectContent>
                {churches.map((c) => (
                  <SelectItem key={c.id} value={c.id}>
                    {c.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : (
            <span className="font-semibold">Worship Service Builder</span>
          )}
        </div>

        <DropdownMenu>
          <DropdownMenuTrigger
            aria-label="Account menu"
            className="rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <Avatar className="size-9">
              {user.picture && <AvatarImage src={user.picture} alt="" />}
              <AvatarFallback>{initial}</AvatarFallback>
            </Avatar>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel className="font-normal">
              <div className="text-sm font-medium">{user.name ?? user.email}</div>
              <div className="text-xs text-muted-foreground">{user.email}</div>
              {active && <div className="text-xs text-muted-foreground">Role: {active.role}</div>}
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={onSignOut}>Log out</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
```

- [ ] **Step 2: Home page**

Replace `frontend/src/app/page.tsx`:

```tsx
"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { AppHeader } from "@/components/app-header";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, apiFetch } from "@/lib/api";
import {
  type Church,
  type Me,
  pickActiveChurch,
  readStoredChurchId,
  storeChurchId,
} from "@/lib/church";
import { createClient } from "@/lib/supabase/client";

async function accessToken(): Promise<string | null> {
  const { data } = await createClient().auth.getSession();
  return data.session?.access_token ?? null;
}

export default function Home() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [active, setActive] = useState<Church | null>(null);

  const signOut = useCallback(async () => {
    storeChurchId(null);
    await createClient().auth.signOut();
    router.replace("/login");
  }, [router]);

  const handleError = useCallback(
    async (err: unknown) => {
      if (err instanceof ApiError && err.status === 401) return signOut();
      toast.error(err instanceof Error ? err.message : "Something went wrong.");
    },
    [signOut],
  );

  // Ask the server to confirm the church; it re-checks membership every time.
  const selectChurch = useCallback(
    async (church: Church) => {
      const token = await accessToken();
      if (!token) return signOut();
      try {
        const confirmed = await apiFetch<Church>("/church", { token, churchId: church.id });
        storeChurchId(confirmed.id);
        setActive(confirmed);
      } catch (err) {
        if (err instanceof ApiError && err.status === 403) {
          storeChurchId(null);
          setActive(null);
          toast.error("You no longer have access to that church. Pick another.");
          return;
        }
        await handleError(err);
      }
    },
    [signOut, handleError],
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const token = await accessToken();
      if (!token) return signOut();
      try {
        const result = await apiFetch<Me>("/me", { token });
        if (cancelled) return;
        setMe(result);
        const chosen = pickActiveChurch(result.churches, readStoredChurchId());
        if (chosen) await selectChurch(chosen);
      } catch (err) {
        if (!cancelled) await handleError(err);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [signOut, handleError, selectChurch]);

  if (!me) return <HomeSkeleton />;

  return (
    <div className="min-h-dvh">
      <AppHeader
        user={me.user}
        churches={me.churches}
        active={active}
        onSelectChurch={selectChurch}
        onSignOut={signOut}
      />
      <main className="mx-auto grid max-w-3xl gap-4 p-4">
        {me.churches.length === 0 ? (
          <Card>
            <CardHeader>
              <CardTitle>No church yet</CardTitle>
              <CardDescription>
                Creating or joining a church is coming in the next update.
              </CardDescription>
            </CardHeader>
          </Card>
        ) : (
          <>
            <Card>
              <CardHeader>
                <CardTitle>Service Builder</CardTitle>
                <CardDescription>
                  Readings, hymns, and liturgy for {active?.name ?? "your church"} are coming soon.
                  Until then, keep using the current app.
                </CardDescription>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Settings</CardTitle>
                <CardDescription>Church profile, members, and invites are coming later.</CardDescription>
              </CardHeader>
            </Card>
          </>
        )}
      </main>
    </div>
  );
}

function HomeSkeleton() {
  return (
    <div className="mx-auto grid max-w-3xl gap-4 p-4">
      <Skeleton className="h-10 w-48" />
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-24 w-full" />
    </div>
  );
}
```

- [ ] **Step 3: Verify**

Run: `cd frontend && npm run lint && npm run typecheck && npm test && npm run build; cd ..`
Expected: all succeed. (End-to-end behavior is checked in Task 11 once Supabase is configured.)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/page.tsx frontend/src/components/app-header.tsx
git commit -m "Add signed-in home with church switcher and account menu

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: CI on every pull request

**Files:**
- Create: `.github/workflows/ci.yml`
- Test: `backend/tests/test_ci_workflow.py`

**Interfaces:**
- Consumes: `requirements-dev.txt`, `pytest.ini` (Task 3); frontend scripts `lint`, `typecheck`, `test`, `build` (Task 7).

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_ci_workflow.py`:

```python
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_ci_runs_backend_tests_and_frontend_checks_on_prs():
    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "pull_request" in text
    assert "python -m pytest" in text
    for script in ("npm run lint", "npm run typecheck", "npm test", "npm run build"):
        assert script in text
```

- [ ] **Step 2: Run it to verify it fails**

Run: `.venv/bin/python -m pytest backend/tests/test_ci_workflow.py -v`
Expected: FAIL with `FileNotFoundError`.

- [ ] **Step 3: Add the workflow**

Create `.github/workflows/ci.yml`:

```yaml
name: ci
on:
  pull_request:
  push:
    branches: [main]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
      - run: pip install -r requirements-dev.txt
      - run: python -m pytest -q

  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    env:
      # Build-time placeholders; real values live in Vercel.
      NEXT_PUBLIC_SUPABASE_URL: https://ci-placeholder.supabase.co
      NEXT_PUBLIC_SUPABASE_ANON_KEY: ci-placeholder
      NEXT_PUBLIC_API_URL: http://localhost:8000
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm run lint
      - run: npm run typecheck
      - run: npm test
      - run: npm run build
```

- [ ] **Step 4: Run the test to verify it passes, then commit**

```bash
.venv/bin/python -m pytest backend/tests/test_ci_workflow.py -v
git add .github/workflows/ci.yml backend/tests/test_ci_workflow.py
git commit -m "Add CI: backend tests and frontend checks on PRs

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: Configure Supabase Auth and verify locally end to end

Dashboard steps are done by the user (they own the accounts). The agent prepares values, runs the local stack, and verifies.

**Files:**
- Local only (gitignored): `backend/.env`, `frontend/.env.local`

**Interfaces:**
- Consumes: everything from Tasks 4–9.

- [ ] **Step 1: Check the project signs tokens with asymmetric keys**

```bash
curl -s https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json
```
Expected: `{"keys":[{...,"alg":"RS256" or "ES256",...}]}`. If `keys` is empty, the project still uses the legacy shared secret: in the Supabase dashboard go to **Project Settings → JWT Keys**, migrate to the new signing keys, and rotate so the asymmetric key is in use. Re-run the curl until a key appears.

- [ ] **Step 2: Enable Google sign-in in Supabase (user)**

1. Google Cloud Console → the existing OAuth client used for the Streamlit login → **Authorized redirect URIs** → add `https://<project-ref>.supabase.co/auth/v1/callback`. Keep the existing URIs.
2. Supabase → **Authentication → Sign In / Providers → Google** → enable, paste that client's ID and secret.
3. Same page: **disable** Email, Phone, and every other provider.
4. Supabase → **Authentication → URL Configuration**: Site URL `http://localhost:3000` for now; Redirect URLs: add `http://localhost:3000/**`.

- [ ] **Step 3: Fill in local env files**

`backend/.env` (from `backend/.env.example`): set `SUPABASE_URL=https://<project-ref>.supabase.co`, keep `DATABASE_URL=sqlite:///../data/app.db` and `CORS_ORIGINS=http://localhost:3000`.

`frontend/.env.local`: set `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` (Supabase → Project Settings → API Keys; the publishable/anon key), `NEXT_PUBLIC_API_URL=http://localhost:8000`.

- [ ] **Step 4: Give your account a local test church**

```bash
cd backend
GOOGLE_EMAIL="<your Google address>" ../.venv/bin/python - <<'PY'
import os
from dotenv import load_dotenv
load_dotenv()
from db import init_db
from auth import upsert_from_claims
from repos.churches import create_church
init_db()
uid = upsert_from_claims({"email": os.environ["GOOGLE_EMAIL"]})
print(create_church(name="Local Test Church", timezone="America/New_York", owner_user_id=uid))
PY
cd ..
```
Expected: a UUID is printed.

- [ ] **Step 5: Run both servers**

Add `.claude/launch.json` entries (or reuse existing ones) and start with the preview tool:

```json
{
  "version": "0.0.1",
  "configurations": [
    {
      "name": "api",
      "runtimeExecutable": "bash",
      "runtimeArgs": ["-c", "cd backend && ../.venv/bin/python -m uvicorn api.main:app --reload --port 8000"],
      "port": 8000
    },
    {
      "name": "web",
      "runtimeExecutable": "bash",
      "runtimeArgs": ["-c", "cd frontend && npm run dev"],
      "port": 3000
    }
  ]
}
```

- [ ] **Step 6: Verify in the browser pane**

1. `http://localhost:8000/health` → `{"ok":true}`.
2. `http://localhost:3000` → redirected to `/login`.
3. Click **Sign in with Google**, complete the Google flow → back on `/` showing **Local Test Church** in the switcher and the placeholder cards.
4. Account menu shows your name, email, and `Role: owner`.
5. Resize to 375px wide (mobile preset): header and cards fit with no horizontal scroll.
6. **Log out** → back to `/login`; visiting `/` redirects to `/login`.
7. In the browser console on `/`, run `localStorage.setItem("activeChurchId", crypto.randomUUID())` and reload → the app falls back to Local Test Church (forged id ignored).

Record the outcome of each check. Stop both servers when done.

---

### Task 12: Deploy backend to Railway and frontend to Vercel; update docs

**Files:**
- Create: `backend/Procfile`, `backend/.python-version`
- Modify: `backend/tests/test_foundation_setup.py` (Procfile test), `README.md`, `docs/manual-verification.md`

**Interfaces:**
- Consumes: the whole slice.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_foundation_setup.py`:

```python
def test_backend_deploy_files_run_uvicorn_on_python_311():
    procfile = (ROOT / "backend" / "Procfile").read_text()
    assert "uvicorn api.main:app" in procfile
    assert "$PORT" in procfile
    assert (ROOT / "backend" / ".python-version").read_text().strip() == "3.11"
```

Run: `.venv/bin/python -m pytest backend/tests/test_foundation_setup.py -v`
Expected: FAIL (`FileNotFoundError` for the Procfile).

- [ ] **Step 2: Add the deploy files**

Create `backend/Procfile`:

```
web: uvicorn api.main:app --host 0.0.0.0 --port $PORT
```

Create `backend/.python-version`:

```
3.11
```

Run: `.venv/bin/python -m pytest -q | tail -1` → all pass.

- [ ] **Step 3: Document the new stack**

Add this section to `README.md` directly after the title/intro paragraph (keep every existing section; `backend/tests/test_docs.py` checks for several of them):

````markdown
## New web app (React + FastAPI) — migration in progress

The app is moving off Streamlit in slices (see
`docs/superpowers/specs/2026-09-25-react-fastapi-migration-design.md`). Until the
last slice lands, the Streamlit app (`app.py`) keeps working on the same database.

| Part | Folder | Hosted on |
|---|---|---|
| Frontend (Next.js, React) | `frontend/` | Vercel |
| API (FastAPI) | `backend/` | Railway |
| Sign-in (Google only) + database | — | Supabase |

**Run locally** (two terminals):

```bash
cd backend && ../.venv/bin/python -m uvicorn api.main:app --reload --port 8000
cd frontend && npm run dev
```

Copy `backend/.env.example` → `backend/.env` and `frontend/.env.example` →
`frontend/.env.local` first. Tests: `.venv/bin/python -m pytest -q` (backend and
Streamlit) and `cd frontend && npm test`.
````

Append to `docs/manual-verification.md`:

```markdown
## Slice 0 — React + FastAPI foundation

On the deployed Vercel URL, on a phone and on a desktop:

- [ ] `/` redirects to `/login` when signed out.
- [ ] Sign in with Google returns to `/` and shows your church in the switcher.
- [ ] Account menu shows name, email, and your role.
- [ ] Switching churches (if you have more than one) updates the role shown.
- [ ] Log out returns to `/login`.
- [ ] `https://<railway-domain>/health` returns `{"ok":true}`.
- [ ] `https://<railway-domain>/me` without a token returns 401 with the error shape.
- [ ] The Streamlit app still signs in and loads your church.
```

Run: `.venv/bin/python -m pytest -q | tail -1` → all pass. Commit:

```bash
git add backend/Procfile backend/.python-version backend/tests/test_foundation_setup.py README.md docs/manual-verification.md
git commit -m "Add Railway deploy files and document the new stack

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 4: Open the slice-0 PR and let CI run**

```bash
git push -u origin claude/react-fastapi-slice0
gh pr create --base main --title "Slice 0: FastAPI + Next.js foundation" --body "Implements slice 0 of docs/superpowers/specs/2026-09-25-react-fastapi-migration-design.md: backend/ restructure, FastAPI with Supabase-Auth and church guards (/health, /me, /church), Next.js frontend with Google login and church switcher, CI.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```
Bind the PR with the ccd_pr tools and confirm both CI jobs are green before deploying.

- [ ] **Step 5: Deploy the backend on Railway (user, guided)**

1. Railway → New Project → Deploy from GitHub repo → `bbrown62450/church`, branch `claude/react-fastapi-slice0` for the first deploy (switch to `main` after merge).
2. Service **Settings**: Root Directory `backend`; Healthcheck Path `/health`; Networking → Generate Domain.
3. **Variables**: `DATABASE_URL` (the Supabase session-pooler URL, same as Streamlit's), `SUPABASE_URL`, `CORS_ORIGINS=http://localhost:3000` (updated in Step 7), and the carried-over `OPENAI_API_KEY`, `OPENAI_MODEL`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI`.
4. Verify: `curl -s https://<railway-domain>/health` → `{"ok":true}`; `curl -s https://<railway-domain>/me` → 401 `{"error":{"code":"unauthenticated",...}}`.

- [ ] **Step 6: Deploy the frontend on Vercel (user, guided)**

1. Vercel → Add New Project → import `bbrown62450/church` → Root Directory `frontend` (framework auto-detected as Next.js).
2. Environment variables: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_API_URL=https://<railway-domain>`.
3. Deploy; note the production URL `https://<app>.vercel.app`.

- [ ] **Step 7: Connect the pieces**

1. Railway → Variables → `CORS_ORIGINS=https://<app>.vercel.app,http://localhost:3000` (service redeploys).
2. Supabase → Authentication → URL Configuration: Site URL `https://<app>.vercel.app`; add Redirect URL `https://<app>.vercel.app/**` (keep the localhost entry).

- [ ] **Step 8: Production verification**

Run the "Slice 0" checklist in `docs/manual-verification.md` against the Vercel URL, including on a phone. Confirm the Streamlit apps (`liturgy.streamlit.app`, `liturgy-stg.streamlit.app`) still sign in once this branch is merged (they deploy with `app.py` at the root unchanged, but now install through `-r backend/requirements.txt`). Report each checklist item's result to the user.

- [ ] **Step 9: Merge (with user approval)**

After the user approves, merge the PR, then switch Railway's deploy branch to `main`. Vercel deploys `main` to production automatically.

---

## Spec coverage check

| Spec section | Task |
|---|---|
| 0.1 Merge | 1 |
| 0.2 Restructure (backend/, Streamlit split, requirements, workflows) | 2, 3 |
| 0.3 Authentication (JWKS, aud/iss/exp, Google-only, claim mapping, 503) | 5, 6 |
| 0.4 Tenancy (`require_church`, `require_admin`) | 6 |
| 0.5 Endpoints (`/health`, `/me`, `/church`) | 4, 6 |
| 0.6 Errors + CORS | 4 |
| 0.7 Frontend (login, callback, proxy, api wrapper, switcher, mobile) | 7, 8, 9, 11 |
| 0.8 Configuration (.env.example both sides) | 4, 7 |
| 0.9 Deployment | 11, 12 |
| 0.10 Testing (token cases, cross-church 403, CI, manual) | 5, 6, 8, 10, 11, 12 |
| Success criteria 1–5 | 1/3, 11–12, 6, 12, 10 |
