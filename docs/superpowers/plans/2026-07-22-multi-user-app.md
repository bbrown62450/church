# Multi-Church Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the single-tenant Worship Service Builder into a multi-church app: people sign in with Google, each church's data is fully isolated, onboarding is self-serve (create a church or join by invite), and four pre-existing security bugs are fixed along the way.

**Architecture:** Streamlit native OIDC (`st.login`/`st.user`) provides identity and cookie-backed sessions. A SQLAlchemy data layer (SQLite for local dev, Supabase Postgres in production, selected by `DATABASE_URL`) replaces Notion + local JSON. Every church-scoped query is guarded server-side by `require_active_church`, which re-validates the active church against the caller's memberships on every request. The existing modules (`service_archive`, `hymn_usage`, `email_contacts`, the hymn source) are rewritten DB-backed and church-scoped behind small repos. A one-time script migrates the founder's Notion data (hymns become a shared starter catalog). The `gmail.send` OAuth flow is kept but hardened (DB-backed tokens/state, sender bound to the logged-in user).

**Tech Stack:** Python, Streamlit `>=1.45` (`streamlit[auth]`, Authlib), SQLAlchemy `>=2.0`, `psycopg2-binary`, Supabase Postgres (session pooler), pytest. AI via existing shared `OPENAI_API_KEY`.

## Global Constraints

_These apply to every task; each task's requirements implicitly include this section._

- **Dependencies:** `streamlit[auth]>=1.45.0` (use `st.user`, never `st.experimental_user`), `SQLAlchemy>=2.0`, `psycopg2-binary`. Keep `notion-client` **migration-only**. Remove the `APP_PASSWORD` gate and the legacy shared-SMTP path.
- **Backend portability:** models use generic SQLAlchemy types only (`Uuid`, `JSON`, `String`, `Text`, `Integer`, `Boolean`, `DateTime`) and Python-side defaults (`default=uuid.uuid4`, `default=lambda: datetime.now(timezone.utc)`). No server-side defaults. Runs on SQLite (dev) and Postgres (prod).
- **Tenancy:** every church-scoped query filters by a `church_id` derived server-side from the caller's membership — never from a query param, form field, or client-set session value. `require_active_church` / `validate_active_church` is the single gate.
- **Session key:** the active church is stored under the session key `active_church_id` (one canonical key everywhere — capture, switcher, guard).
- **Connection (prod):** Supabase **session pooler** URL (IPv4) in `DATABASE_URL`; engine built with `pool_pre_ping=True`, `pool_recycle=280`, cached with `@st.cache_resource` in the app.
- **TDD:** each task = write failing test -> run (fail) -> implement -> run (pass) -> commit. Tests use the shared `tests/conftest.py` fixtures (`tmp_db`, `make_user`, `make_church`, `seed_catalog`). Streamlit-only code is tested via extracted pure helpers.
- **Commits:** end each commit message with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

A canonical **Shared Interfaces** reference (every module's exact signatures) is included as an appendix at the end of this plan — consult it whenever a task consumes another task's output.

---

# Multi-Church Support — TDD Implementation Plan (Tasks 1–3: Foundation)

> **Cross-task invariant:** `tests/conftest.py` is **created once here in Task 1** and only ever *modified* by later tasks — never re-created. Its fixtures import the `db` layer **lazily inside each fixture body** (deferred imports), so this file collects cleanly in Task 1 even though `db/` does not exist yet; the imports only resolve once Tasks 2–3 land. There is no Streamlit code in these three tasks, so nothing needs the "extract a pure helper" treatment yet.

---

### Task 1: Project foundation — dependencies, gitignore, shared test fixtures

**Files:**
- Modify: `requirements.txt`
- Modify: `.gitignore`
- Create: `tests/__init__.py` (empty — makes `tests` importable)
- Create: `tests/conftest.py` (ALL shared fixtures: `tmp_db`, `make_user`, `make_church`, `seed_catalog`)
- Test (Create): `tests/test_foundation_setup.py`

**Interfaces:**
- *Consumes (deferred / not yet existing — imported inside fixture bodies):*
  - `from db import reset_engine_for_tests, init_db, session_scope` (Task 2)
  - `from db.models import User, Church, Membership, HymnCatalog` (Task 3)
- *Produces (every later task's tests rely on these exact fixture signatures):*
  - `tmp_db` → yields `sqlalchemy.Engine` (fresh SQLite bound via `reset_engine_for_tests`, tables via `init_db`, `PRAGMA foreign_keys=ON`).
  - `make_user(email="person@example.com", *, name="Person", google_sub=None, picture=None) -> uuid.UUID`
  - `make_church(name="First Church", timezone="America/New_York", owner_user_id=None) -> uuid.UUID` (inserts church + owner `Membership`; mints an owner user when `owner_user_id is None`).
  - `seed_catalog(n=3) -> int` (inserts `n` `HymnCatalog` rows with `scripture_refs` **and** `theme` populated; returns `n`).

- [ ] **Step 1: Write the failing test**

`tests/__init__.py`:
```python
```
*(intentionally empty)*

`tests/test_foundation_setup.py`:
```python
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_requirements_pins_runtime_and_migration_deps():
    text = (ROOT / "requirements.txt").read_text()
    assert "streamlit[auth]>=1.45.0" in text
    assert "SQLAlchemy>=2.0" in text
    assert "psycopg2-binary" in text
    # notion-client is kept ONLY for the one-time migration script.
    assert "notion-client" in text
    assert "migration only" in text.lower()
    # The old shared-password-era bare streamlit pin must be gone.
    assert "\nstreamlit>=1.28.0" not in text


def test_gitignore_covers_local_db_and_secrets():
    text = (ROOT / ".gitignore").read_text()
    assert "data/*.db" in text
    assert ".streamlit/secrets.toml" in text
```

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/test_foundation_setup.py -q`
  Expected: **FAIL** — `test_requirements_pins_runtime_and_migration_deps` fails on `assert "streamlit[auth]>=1.45.0" in text` (requirements.txt still lists bare `streamlit>=1.28.0`, no SQLAlchemy/psycopg2), and `test_gitignore_covers_local_db_and_secrets` fails on `assert "data/*.db" in text`.

- [ ] **Step 3: Write the implementation**

Edit `requirements.txt` — replace the entire file contents:

*Before:*
```
notion-client>=2.2.1
python-dotenv>=1.0.0
beautifulsoup4>=4.12.0
requests>=2.31.0
httpx>=0.25.0
lxml>=4.9.0
playwright>=1.40.0
openai>=1.0.0
python-docx>=1.0.0
streamlit>=1.28.0
```

*After:*
```
# --- Runtime ---
streamlit[auth]>=1.45.0
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

Edit `.gitignore` — replace the "Local data" region:

*Before:*
```
# Local data (optional: remove data/*.json to commit archive/usage)
data/*.json
```

*After:*
```
# Local data (optional: remove data/*.json to commit archive/usage)
data/*.json

# Local SQLite dev databases (never commit church data)
data/*.db

# Streamlit auth/DB secrets (client_id, client_secret, cookie_secret, DATABASE_URL)
.streamlit/secrets.toml
```

Create `tests/conftest.py`:
```python
"""Shared pytest fixtures for the multi-church test suite.

Created once (Task 1); later tasks MODIFY this file, never re-create it.

Design note: db-layer imports live INSIDE each fixture body (deferred), not at
module top level. That keeps this conftest collectable before db/ exists, and
lets every later task's tests depend on a single canonical set of factories.
"""
import uuid

import pytest


@pytest.fixture
def tmp_db(tmp_path):
    """Fresh, isolated SQLite database for one test.

    Binds the engine DIRECTLY via reset_engine_for_tests (not os.environ),
    creates all tables via init_db, and enforces FK ON DELETE on SQLite so
    later cascade/tenancy tests behave like Postgres. Yields the Engine.
    """
    from sqlalchemy import event

    from db import reset_engine_for_tests, init_db

    url = f"sqlite:///{tmp_path / 'test.db'}"
    engine = reset_engine_for_tests(url)

    if engine.dialect.name == "sqlite":
        @event.listens_for(engine, "connect")
        def _enable_sqlite_fks(dbapi_conn, _rec):  # pragma: no cover - driver hook
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

    init_db()
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def make_user(tmp_db):
    """Factory: insert a users row, return its id (uuid.UUID)."""
    from db import session_scope
    from db.models import User

    def _make(email="person@example.com", *, name="Person",
              google_sub=None, picture=None):
        user_id = uuid.uuid4()
        with session_scope() as s:
            s.add(User(
                id=user_id,
                email=email.strip().lower(),
                name=name,
                google_sub=google_sub,
                picture=picture,
            ))
        return user_id

    return _make


@pytest.fixture
def make_church(tmp_db, make_user):
    """Factory: insert a churches row + owner membership; return church id (uuid.UUID).

    When owner_user_id is None, a fresh owner user is created. owner_user_id is a
    uuid.UUID user id (as returned by make_user).
    """
    from db import session_scope
    from db.models import Church, Membership

    def _make(name="First Church", timezone="America/New_York", owner_user_id=None):
        if owner_user_id is None:
            owner_user_id = make_user(email=f"owner-{uuid.uuid4().hex[:8]}@example.com")
        church_id = uuid.uuid4()
        with session_scope() as s:
            s.add(Church(id=church_id, name=name, timezone=timezone))
            s.add(Membership(church_id=church_id, user_id=owner_user_id, role="owner"))
        return church_id

    return _make


@pytest.fixture
def seed_catalog(tmp_db):
    """Factory: insert n HymnCatalog rows with scripture_refs + theme populated.

    Returns the number of rows inserted.
    """
    from db import session_scope
    from db.models import HymnCatalog

    def _seed(n=3):
        with session_scope() as s:
            for i in range(1, n + 1):
                s.add(HymnCatalog(
                    title=f"Hymn {i}",
                    number=i,
                    scripture_refs=f"John {i}:1-{i + 2}",
                    theme="praise, grace",
                    hymnary_link=f"https://hymnary.org/hymn/{i}",
                    audio_url=None,
                ))
        return n

    return _seed
```

- [ ] **Step 4: Run test to verify it passes**
  Run: `pytest tests/test_foundation_setup.py -q`
  Expected: **PASS** (2 passed). Fixtures are not exercised by this test — their deferred `db` imports stay unresolved until Task 3, so collection succeeds without `db/`.

- [ ] **Step 5: Commit**
```
git add requirements.txt .gitignore tests/__init__.py tests/conftest.py tests/test_foundation_setup.py
git commit -m "Task 1: deps (streamlit[auth]/SQLAlchemy/psycopg2), gitignore db+secrets, shared test fixtures"
```

---

### Task 2: Database engine & session layer

**Files:**
- Create: `db/__init__.py` (re-exports the public surface)
- Create: `db/engine.py`
- Test (Create): `tests/test_engine.py`

**Interfaces:**
- *Consumes:* nothing (leaf of the dependency graph).
- *Produces (imported by every later db-touching task, exactly these names):*
  - `Base` — SQLAlchemy declarative base (Task 3 models subclass it).
  - `get_engine() -> Engine` — cached in module global `_engine`; `pool_pre_ping=True`, `pool_recycle` for Postgres.
  - `SessionLocal` — `sessionmaker`, rebound whenever the engine changes.
  - `session_scope()` — contextmanager; commit on success, rollback on exception, always close.
  - `get_session = session_scope` — alias (identity-equal).
  - `init_db() -> None` — `Base.metadata.create_all(get_engine())` after importing models.
  - `reset_engine_for_tests(url) -> Engine` — disposes any prior engine, binds a new one **directly** from `url` (not `os.environ`), returns the Engine.
- Import contract satisfied: `from db import init_db, session_scope` works.

- [ ] **Step 1: Write the failing test**

`tests/test_engine.py`:
```python
import pytest
from sqlalchemy import Engine, text


def test_public_imports_are_reexported():
    # `from db import ...` must expose the whole surface (Task 3 imports Base from here).
    from db import (  # noqa: F401
        Base, get_engine, SessionLocal, session_scope,
        get_session, init_db, reset_engine_for_tests,
    )


def test_get_session_is_session_scope_alias():
    from db import get_session, session_scope
    assert get_session is session_scope


def test_reset_engine_returns_engine_and_binds_directly(tmp_path):
    from db import reset_engine_for_tests, SessionLocal
    url = f"sqlite:///{tmp_path / 'e.db'}"
    engine = reset_engine_for_tests(url)
    assert isinstance(engine, Engine)
    # SessionLocal is rebound to the engine reset_engine_for_tests created.
    assert SessionLocal().get_bind() is engine


def test_session_scope_commits_on_success(tmp_path):
    from db import reset_engine_for_tests, session_scope
    reset_engine_for_tests(f"sqlite:///{tmp_path / 'c.db'}")
    with session_scope() as s:
        s.execute(text("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)"))
        s.execute(text("INSERT INTO t (v) VALUES ('a')"))
    with session_scope() as s:  # a NEW session must see the committed row
        row = s.execute(text("SELECT v FROM t")).fetchone()
    assert row[0] == "a"


def test_session_scope_rolls_back_on_exception(tmp_path):
    from db import reset_engine_for_tests, session_scope
    reset_engine_for_tests(f"sqlite:///{tmp_path / 'r.db'}")
    with session_scope() as s:
        s.execute(text("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)"))
    with pytest.raises(RuntimeError):
        with session_scope() as s:
            s.execute(text("INSERT INTO t (v) VALUES ('b')"))
            raise RuntimeError("boom")
    with session_scope() as s:
        count = s.execute(text("SELECT COUNT(*) FROM t")).fetchone()
    assert count[0] == 0
```

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/test_engine.py -q`
  Expected: **FAIL** — collection error `ModuleNotFoundError: No module named 'db'` (the `db` package does not exist yet).

- [ ] **Step 3: Write the implementation**

Create `db/engine.py`:
```python
"""SQLAlchemy engine + session plumbing.

One engine is cached per process (`_engine`). Both SQLite (local dev) and
Postgres (Supabase, prod) are driven from the same models, selected by
DATABASE_URL. Tests bypass the env var via reset_engine_for_tests(url).
"""
import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

# Cached engine (module global). Rebound by get_engine / reset_engine_for_tests.
_engine = None

# Bound lazily; reconfigured whenever the engine changes.
SessionLocal = sessionmaker(autoflush=False, expire_on_commit=False)


def _database_url() -> str:
    return os.environ.get("DATABASE_URL", "sqlite:///data/church.db")


def _make_engine(url: str) -> Engine:
    kwargs = {"pool_pre_ping": True, "future": True}
    if url.startswith("sqlite"):
        # Streamlit reruns across threads; SQLite needs this relaxed.
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        # Retire connections the Supabase pooler may have dropped.
        kwargs["pool_recycle"] = 1800
    return create_engine(url, **kwargs)


def get_engine() -> Engine:
    """Return the process-wide engine, creating it (from DATABASE_URL) once."""
    global _engine
    if _engine is None:
        _engine = _make_engine(_database_url())
        SessionLocal.configure(bind=_engine)
    return _engine


def reset_engine_for_tests(url: str) -> Engine:
    """Dispose any existing engine and bind a fresh one directly from `url`.

    Does NOT touch os.environ — the url is used verbatim. Returns the Engine.
    """
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = _make_engine(url)
    SessionLocal.configure(bind=_engine)
    return _engine


def init_db() -> None:
    """Create all tables. Imports models so every table is registered on Base."""
    from db import models  # noqa: F401  (registers all mappers on Base.metadata)
    Base.metadata.create_all(bind=get_engine())


@contextmanager
def session_scope():
    """Transactional scope: commit on success, rollback on error, always close."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# Canonical alias — some call sites read better as `with get_session() as s:`.
get_session = session_scope
```

Create `db/__init__.py`:
```python
"""Public database surface. Import from `db`, not `db.engine`, elsewhere."""
from db.engine import (
    Base,
    get_engine,
    SessionLocal,
    session_scope,
    get_session,
    init_db,
    reset_engine_for_tests,
)

__all__ = [
    "Base",
    "get_engine",
    "SessionLocal",
    "session_scope",
    "get_session",
    "init_db",
    "reset_engine_for_tests",
]
```

- [ ] **Step 4: Run test to verify it passes**
  Run: `pytest tests/test_engine.py -q`
  Expected: **PASS** (5 passed). `init_db` is not called by these tests, so its `from db import models` is never triggered before Task 3 exists.

- [ ] **Step 5: Commit**
```
git add db/__init__.py db/engine.py tests/test_engine.py
git commit -m "Task 2: db.engine (Base, cached engine, session_scope/get_session, init_db, reset_engine_for_tests) + db re-exports"
```

---

### Task 3: ORM models (all tables)

**Files:**
- Create: `db/models.py`
- Test (Create): `tests/test_models.py`

**Interfaces:**
- *Consumes:* `from db.engine import Base` (Task 2); `from db import session_scope` (Task 2); fixtures `tmp_db`, `seed_catalog` (Task 1).
- *Produces (mapped classes later repo tasks import):* `User`, `Church`, `Membership`, `Invite`, `HymnCatalog`, `Hymn`, `Service`, `HymnUsage`, `Contact`, `GmailToken`, `OAuthState`.
  - **`Service` has `service_date_iso: str` AND `service_date_display: str`** — no `DATE` column (per locked interface).
  - `Membership` has composite PK `(church_id, user_id)`, a `CHECK role IN ('owner','admin','member')`, and a secondary index on `user_id`.
  - All FKs carry explicit `ondelete`: church-scoped content `CASCADE`; `services.created_by` / `invites.created_by` `SET NULL`.

- [ ] **Step 1: Write the failing test**

`tests/test_models.py`:
```python
import uuid

import pytest
from sqlalchemy.exc import IntegrityError


def test_church_user_membership_service_roundtrip(tmp_db):
    from db import session_scope
    from db.models import User, Church, Membership, Service

    uid = uuid.uuid4()
    cid = uuid.uuid4()
    sid = uuid.uuid4()

    with session_scope() as s:
        s.add(User(id=uid, email="pastor@example.com", name="Pastor"))
        s.add(Church(id=cid, name="Grace Church", timezone="America/New_York"))
        s.add(Membership(church_id=cid, user_id=uid, role="owner"))
        s.add(Service(
            id=sid,
            church_id=cid,
            created_by=uid,
            service_date_iso="2026-07-26",
            service_date_display="Sunday, July 26, 2026",
            occasion="Ordinary Time",
            scriptures=["Ps 23", "John 10:1-10"],
            hymns=[{"title": "Amazing Grace", "number": 649}],
            liturgy={"opening": "Let us worship God."},
            sermon_title="The Good Shepherd",
            selected_ot_ref="Ps 23",
            selected_nt_ref="John 10:1-10",
            include_communion=True,
        ))

    with session_scope() as s:
        svc = s.get(Service, sid)
        assert svc.church_id == cid
        assert svc.created_by == uid
        assert svc.service_date_iso == "2026-07-26"
        assert svc.service_date_display == "Sunday, July 26, 2026"
        assert svc.scriptures == ["Ps 23", "John 10:1-10"]
        assert svc.hymns[0]["number"] == 649
        assert svc.liturgy["opening"] == "Let us worship God."
        assert svc.include_communion is True

        mem = s.get(Membership, {"church_id": cid, "user_id": uid})
        assert mem.role == "owner"
        assert s.get(Church, cid).name == "Grace Church"
        assert s.get(User, uid).email == "pastor@example.com"


def test_membership_role_check_constraint_rejects_bad_role(tmp_db):
    from db import session_scope
    from db.models import User, Church, Membership

    uid = uuid.uuid4()
    cid = uuid.uuid4()
    with session_scope() as s:
        s.add(User(id=uid, email="a@example.com", name="A"))
        s.add(Church(id=cid, name="C", timezone="America/New_York"))

    with pytest.raises(IntegrityError):
        with session_scope() as s:
            s.add(Membership(church_id=cid, user_id=uid, role="superadmin"))


def test_seed_catalog_fixture_populates_enrichment(tmp_db, seed_catalog):
    from db import session_scope
    from db.models import HymnCatalog

    assert seed_catalog(4) == 4
    with session_scope() as s:
        rows = s.query(HymnCatalog).all()
    assert len(rows) == 4
    assert all(r.scripture_refs for r in rows)
    assert all(r.theme for r in rows)
```

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/test_models.py -q`
  Expected: **FAIL** — inside the `tmp_db` fixture, `init_db()` runs `from db import models`, which raises `ModuleNotFoundError: No module named 'db.models'`; all three tests error at setup.

- [ ] **Step 3: Write the implementation**

Create `db/models.py`:
```python
"""ORM models — one relational schema serving SQLite (dev) and Postgres (prod).

Portability rules (both backends): generic types only (Uuid, JSON), Python-side
defaults only (uuid4, utcnow) — never server defaults. Church content cascades
to the CHURCH; authorship FKs (created_by) SET NULL so history survives a
departing author.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)

from db.engine import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False, unique=True)  # normalized lower-case
    google_sub = Column(String, unique=True)
    name = Column(String)
    picture = Column(String)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    last_login_at = Column(DateTime(timezone=True))


class Church(Base):
    __tablename__ = "churches"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    timezone = Column(String, nullable=False)
    settings = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    deleted_at = Column(DateTime(timezone=True))  # soft delete


class Membership(Base):
    __tablename__ = "memberships"

    church_id = Column(
        Uuid, ForeignKey("churches.id", ondelete="CASCADE"), primary_key=True
    )
    user_id = Column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    __table_args__ = (
        CheckConstraint(
            "role IN ('owner','admin','member')", name="ck_memberships_role"
        ),
        Index("ix_memberships_user_id", "user_id"),
    )


class Invite(Base):
    __tablename__ = "invites"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    church_id = Column(
        Uuid, ForeignKey("churches.id", ondelete="CASCADE"), nullable=False
    )
    code = Column(String, nullable=False, unique=True)
    email = Column(String)  # nullable; when set, one pending per (church, email)
    role = Column(String, nullable=False, default="member")
    created_by = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, nullable=False, default=False)
    accepted_at = Column(DateTime(timezone=True))

    __table_args__ = (
        # NULL emails are distinct on both SQLite and Postgres, so many
        # code-only invites coexist while an email-bound one is single-pending.
        UniqueConstraint("church_id", "email", name="uq_invites_church_email"),
        Index("ix_invites_church_id", "church_id"),
    )


class HymnCatalog(Base):
    """Shared starter hymnal (template). Never church-scoped; never mutated by a church."""
    __tablename__ = "hymn_catalog"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    title = Column(String)
    number = Column(Integer)
    scripture_refs = Column(Text)
    theme = Column(Text)
    hymnary_link = Column(Text)
    audio_url = Column(Text)


class Hymn(Base):
    """Per-church, editable hymnal. Seeded from HymnCatalog at church creation."""
    __tablename__ = "hymns"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    church_id = Column(
        Uuid, ForeignKey("churches.id", ondelete="CASCADE"), nullable=False
    )
    title = Column(String)
    number = Column(Integer)
    scripture_refs = Column(Text)
    theme = Column(Text)
    hymnary_link = Column(Text)
    audio_url = Column(Text)

    __table_args__ = (
        Index("ix_hymns_church_id", "church_id"),
        Index("ix_hymns_church_number", "church_id", "number"),
    )


class Service(Base):
    """Archived worship service. Date is stored as iso + display strings (no DATE)."""
    __tablename__ = "services"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    church_id = Column(
        Uuid, ForeignKey("churches.id", ondelete="CASCADE"), nullable=False
    )
    created_by = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    service_date_iso = Column(String)
    service_date_display = Column(String)
    occasion = Column(String)
    scriptures = Column(JSON)
    hymns = Column(JSON)  # denormalized title/number snapshot, no FK to hymns
    liturgy = Column(JSON)
    sermon_title = Column(String)
    selected_ot_ref = Column(String)
    selected_nt_ref = Column(String)
    include_communion = Column(Boolean, nullable=False, default=False)
    saved_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    __table_args__ = (
        Index("ix_services_church_saved_at", "church_id", "saved_at"),
    )


class HymnUsage(Base):
    """Drives 'exclude hymns used in the last 12 weeks'. Idempotent per dedupe key."""
    __tablename__ = "hymn_usage"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    church_id = Column(
        Uuid, ForeignKey("churches.id", ondelete="CASCADE"), nullable=False
    )
    date_iso = Column(String, nullable=True)
    hymn_number = Column(Integer)
    hymn_title = Column(String)  # denormalized, no FK to hymns
    recorded_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    __table_args__ = (
        UniqueConstraint(
            "church_id", "date_iso", "hymn_number", "hymn_title",
            name="uq_hymn_usage_dedupe",
        ),
        Index("ix_hymn_usage_church_date", "church_id", "date_iso"),
    )


class Contact(Base):
    """Configurable per-church email destinations."""
    __tablename__ = "contacts"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    church_id = Column(
        Uuid, ForeignKey("churches.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String)
    email = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    __table_args__ = (
        Index("ix_contacts_church_id", "church_id"),
    )


class GmailToken(Base):
    """User-scoped (not church-scoped): connect Gmail once, send in any church."""
    __tablename__ = "gmail_tokens"

    user_id = Column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    refresh_token = Column(Text, nullable=False)
    google_email = Column(String)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)


class OAuthState(Base):
    """CSRF state for the gmail.send flow; survives the redirect, single-use."""
    __tablename__ = "oauth_states"

    state = Column(String, primary_key=True)
    user_id = Column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False)
```

- [ ] **Step 4: Run test to verify it passes**
  Run: `pytest tests/test_models.py -q`
  Expected: **PASS** (3 passed). Also run the whole suite so far: `pytest -q` → all of Task 1 + 2 + 3 tests pass (the `tmp_db` FK pragma lets the `CHECK` constraint surface as `IntegrityError`, and generic `JSON` round-trips lists/dicts on SQLite).

- [ ] **Step 5: Commit**
```
git add db/models.py tests/test_models.py
git commit -m "Task 3: ORM models for all tables (Service iso+display, composite membership PK, role CHECK, FK ondelete, indexes)"
```

---

I have everything I need: the SPEC (`docs/superpowers/specs/2026-07-22-multi-user-app-design.md`) and the locked signatures from the task prompt (no separate LOCKED file exists on disk — the signatures are authoritative inline). Here is the plan for Tasks 4-8.

### Task 4: `repos` package + Users repository

**Files:**
- Create: `repos/__init__.py`
- Create: `repos/users.py`
- Test: `tests/test_users_repo.py`

**Interfaces:**
- Consumes (from Task 1): `from db import session_scope` (contextmanager: commit/rollback/close); `db.models.User` with attrs `id, email, google_sub, name, picture, created_at, last_login_at`. Conftest fixtures `tmp_db`, `make_user(email=..., name=..., google_sub=..., picture=...) -> uuid.UUID`.
- Produces: `repos.users.upsert_user(email, name=None, picture=None, google_sub=None) -> uuid.UUID` (normalizes/lower-cases email, idempotent on email, refreshes `last_login_at`); `repos.users.get_user(user_id) -> dict | None`; `repos.users.get_user_by_email(email) -> dict | None`.

- [ ] **Step 1: Write the failing test** — `tests/test_users_repo.py`
```python
import uuid

from repos.users import upsert_user, get_user, get_user_by_email


def test_upsert_user_lowercases_and_creates(tmp_db):
    uid = upsert_user(email="Beau.Brown@Example.COM", name="Beau", google_sub="sub-1")
    assert isinstance(uid, uuid.UUID)
    row = get_user(uid)
    assert row["email"] == "beau.brown@example.com"
    assert row["name"] == "Beau"
    assert row["google_sub"] == "sub-1"


def test_upsert_user_is_idempotent_on_normalized_email(tmp_db):
    uid1 = upsert_user(email="a@b.com", name="First")
    uid2 = upsert_user(email="A@B.COM", name="Second", picture="http://x/y.png")
    assert uid1 == uid2
    row = get_user(uid1)
    assert row["name"] == "Second"            # updated in place
    assert row["picture"] == "http://x/y.png"


def test_get_user_by_email_matches_normalized(tmp_db):
    uid = upsert_user(email="Carol@Example.com")
    assert get_user_by_email("carol@example.com")["id"] == uid
    assert get_user_by_email("  CAROL@EXAMPLE.COM ")["id"] == uid


def test_get_user_missing_returns_none(tmp_db):
    assert get_user(uuid.uuid4()) is None
    assert get_user_by_email("nobody@example.com") is None


def test_upsert_user_rejects_empty_email(tmp_db):
    import pytest
    with pytest.raises(ValueError):
        upsert_user(email="   ")
```

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/test_users_repo.py`
  Expected: FAIL — `ModuleNotFoundError: No module named 'repos'` (the package and module do not exist yet).

- [ ] **Step 3: Write the implementation**

`repos/__init__.py`:
```python
"""Data-access repositories (church-scoped, IDOR-safe) for the multi-church app."""
```

`repos/users.py`:
```python
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select

from db import session_scope
from db.models import User


def _normalize_email(email) -> str:
    return (email or "").strip().lower()


def _to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "google_sub": user.google_sub,
        "name": user.name,
        "picture": user.picture,
    }


def upsert_user(email, name=None, picture=None, google_sub=None) -> uuid.UUID:
    """Create or refresh a user keyed on the normalized (lower-cased) email.

    Returns the user's id. Idempotent on email: a repeat call updates the
    name/picture/google_sub (when provided) and stamps last_login_at.
    """
    normalized = _normalize_email(email)
    if not normalized:
        raise ValueError("email is required")
    now = datetime.now(timezone.utc)
    with session_scope() as session:
        user = session.execute(
            select(User).where(User.email == normalized)
        ).scalar_one_or_none()
        if user is None:
            user = User(
                email=normalized,
                google_sub=google_sub,
                name=name,
                picture=picture,
                last_login_at=now,
            )
            session.add(user)
        else:
            if google_sub is not None:
                user.google_sub = google_sub
            if name is not None:
                user.name = name
            if picture is not None:
                user.picture = picture
            user.last_login_at = now
        session.flush()
        return user.id


def get_user(user_id) -> Optional[dict]:
    with session_scope() as session:
        user = session.get(User, user_id)
        return _to_dict(user) if user is not None else None


def get_user_by_email(email) -> Optional[dict]:
    normalized = _normalize_email(email)
    if not normalized:
        return None
    with session_scope() as session:
        user = session.execute(
            select(User).where(User.email == normalized)
        ).scalar_one_or_none()
        return _to_dict(user) if user is not None else None
```

- [ ] **Step 4: Run test to verify it passes**
  Run: `pytest tests/test_users_repo.py`
  Expected: PASS (5 passed).

- [ ] **Step 5: Commit**
```bash
git add repos/__init__.py repos/users.py tests/test_users_repo.py
git commit -m "Add repos.users: upsert_user (normalized email) + get_user" \
  -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Churches repository (atomic create + starter hymnal seed)

**Files:**
- Create: `repos/churches.py`
- Test: `tests/test_churches_repo.py`

**Interfaces:**
- Consumes: `from db import session_scope`; `db.models.Church` (`id, name, timezone, settings, deleted_at`), `db.models.Membership` (`church_id, user_id, role`), `db.models.Invite` (`church_id, revoked, accepted_at`); `repos.hymns.seed_church_from_catalog(church_id, session) -> int` (Task 3 canonical — copies `hymn_catalog` rows into per-church `hymns`, does **not** commit); conftest `make_user`, `seed_catalog(n) -> list[uuid.UUID]`.
- Produces: `create_church(*, name, timezone, owner_user_id) -> uuid.UUID`; `get_church(church_id) -> dict | None` (excludes soft-deleted); `list_user_churches(user_id) -> list[dict]` = `[{"id":UUID,"name":str,"role":str}]`; `soft_delete_church(church_id) -> None` (sets `deleted_at` AND revokes pending invites); `update_church(church_id, *, name=None, timezone=None, settings=None) -> None`.

- [ ] **Step 1: Write the failing test** — `tests/test_churches_repo.py`
```python
import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func

from db import session_scope
from db.models import Hymn, Invite, Church
from repos.churches import (
    create_church, get_church, list_user_churches, soft_delete_church, update_church,
)


def test_create_church_is_atomic_owns_and_seeds(tmp_db, make_user, seed_catalog):
    seed_catalog(5)
    owner = make_user(email="owner@x.com", name="Owner")
    cid = create_church(name="First Pres", timezone="America/New_York", owner_user_id=owner)
    assert isinstance(cid, uuid.UUID)

    ch = get_church(cid)
    assert ch["name"] == "First Pres"
    assert ch["timezone"] == "America/New_York"

    # creator gets an owner membership
    assert list_user_churches(owner) == [{"id": cid, "name": "First Pres", "role": "owner"}]

    # hymnal seeded synchronously from the shared catalog (5 rows copied)
    with session_scope() as s:
        n = s.execute(
            select(func.count()).select_from(Hymn).where(Hymn.church_id == cid)
        ).scalar_one()
    assert n == 5


def test_get_church_and_list_exclude_soft_deleted(tmp_db, make_user):
    owner = make_user(email="o2@x.com")
    cid = create_church(name="Grace", timezone="UTC", owner_user_id=owner)
    soft_delete_church(cid)
    assert get_church(cid) is None
    assert list_user_churches(owner) == []


def test_soft_delete_revokes_pending_invites(tmp_db, make_user):
    owner = make_user(email="o3@x.com")
    cid = create_church(name="Hope", timezone="UTC", owner_user_id=owner)
    with session_scope() as s:
        s.add(Invite(
            church_id=cid, code="pending-code", role="member", created_by=owner,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7), revoked=False,
        ))
    soft_delete_church(cid)
    with session_scope() as s:
        inv = s.execute(select(Invite).where(Invite.code == "pending-code")).scalar_one()
        assert inv.revoked is True


def test_update_church_changes_profile(tmp_db, make_user):
    owner = make_user(email="o4@x.com")
    cid = create_church(name="Old", timezone="UTC", owner_user_id=owner)
    update_church(cid, name="New Name", timezone="America/Chicago", settings={"theme": "dark"})
    ch = get_church(cid)
    assert ch["name"] == "New Name"
    assert ch["timezone"] == "America/Chicago"
    assert ch["settings"] == {"theme": "dark"}
```

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/test_churches_repo.py`
  Expected: FAIL — `ModuleNotFoundError: No module named 'repos.churches'`.

- [ ] **Step 3: Write the implementation** — `repos/churches.py`
```python
import datetime as _dt
import uuid
from typing import Optional

from sqlalchemy import select, update

from db import session_scope
from db.models import Church, Membership, Invite


def create_church(*, name, timezone, owner_user_id) -> uuid.UUID:
    """Create a church, its creator's owner membership, and seed the per-church
    hymnal from the shared catalog — all in one transaction (atomic, so no admin
    ever sees a half-populated hymnal). Returns the new church id.
    """
    with session_scope() as session:
        church = Church(name=name, timezone=timezone)
        session.add(church)
        session.flush()  # assign church.id (Python-side uuid default)
        session.add(
            Membership(church_id=church.id, user_id=owner_user_id, role="owner")
        )
        # Deferred import: repos.hymns is created in a later task, so import it
        # locally (right before use) to keep repos.churches importable on its own.
        from repos.hymns import seed_church_from_catalog
        seed_church_from_catalog(church.id, session)
        new_id = church.id
        return new_id


def get_church(church_id) -> Optional[dict]:
    with session_scope() as session:
        church = session.get(Church, church_id)
        if church is None or church.deleted_at is not None:
            return None
        return {
            "id": church.id,
            "name": church.name,
            "timezone": church.timezone,
            "settings": church.settings,
        }


def list_user_churches(user_id) -> list:
    with session_scope() as session:
        rows = session.execute(
            select(Church.id, Church.name, Membership.role)
            .join(Membership, Membership.church_id == Church.id)
            .where(Membership.user_id == user_id, Church.deleted_at.is_(None))
            .order_by(Church.name)
        ).all()
        return [{"id": r.id, "name": r.name, "role": r.role} for r in rows]


def soft_delete_church(church_id) -> None:
    """Soft-delete the church (excluded from every query afterward) and revoke
    all still-pending invites for it."""
    with session_scope() as session:
        church = session.get(Church, church_id)
        if church is None or church.deleted_at is not None:
            return
        church.deleted_at = _dt.datetime.now(_dt.timezone.utc)
        session.execute(
            update(Invite)
            .where(
                Invite.church_id == church_id,
                Invite.revoked.is_(False),
                Invite.accepted_at.is_(None),
            )
            .values(revoked=True)
        )


def update_church(church_id, *, name=None, timezone=None, settings=None) -> None:
    with session_scope() as session:
        church = session.get(Church, church_id)
        if church is None or church.deleted_at is not None:
            return
        if name is not None:
            church.name = name
        if timezone is not None:
            church.timezone = timezone
        if settings is not None:
            church.settings = settings
```

- [ ] **Step 4: Run test to verify it passes**
  Run: `pytest tests/test_churches_repo.py`
  Expected: PASS (4 passed).

- [ ] **Step 5: Commit**
```bash
git add repos/churches.py tests/test_churches_repo.py
git commit -m "Add repos.churches: atomic create+seed, soft-delete revokes invites" \
  -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Memberships repository (last-admin invariant + authorship nulling)

**Files:**
- Create: `repos/memberships.py`
- Test: `tests/test_memberships_repo.py`

**Interfaces:**
- Consumes: `from db import session_scope`; `db.models.Membership` (composite PK `(church_id, user_id)`, `role`), `db.models.User` (`id, email, name`), `db.models.Service` (`church_id, created_by`); `repos.churches.create_church(*, name, timezone, owner_user_id)`; conftest `make_user`.
- Produces: `LastAdminError(Exception)`; `get_role(user_id, church_id) -> str | None`; `add_membership(user_id, church_id, role) -> None` (no-dup, idempotent); `set_role(user_id, church_id, role) -> None` (row-locked last-admin guard); `remove_membership(user_id, church_id) -> None` (row-locked last-admin guard; nulls `services.created_by` for that user+church); `list_members(church_id) -> list[dict]` = `[{"user_id":UUID,"email":str,"name":str,"role":str}]`; `count_admins(church_id) -> int`.

- [ ] **Step 1: Write the failing test** — `tests/test_memberships_repo.py`
```python
import pytest
from datetime import datetime, timezone

from sqlalchemy import select

from db import session_scope
from db.models import Service, Membership
from repos.churches import create_church
from repos.memberships import (
    LastAdminError, get_role, add_membership, set_role,
    remove_membership, list_members, count_admins,
)


def test_add_membership_no_duplicate(tmp_db, make_user):
    owner = make_user(email="owner@x.com", name="Owner")
    member = make_user(email="m@x.com", name="Mem")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    add_membership(member, cid, "member")
    add_membership(member, cid, "member")  # duplicate ignored
    assert get_role(member, cid) == "member"
    assert count_admins(cid) == 1
    with session_scope() as s:
        rows = s.execute(select(Membership).where(Membership.church_id == cid)).all()
    assert len(rows) == 2


def test_list_members_joins_users(tmp_db, make_user):
    owner = make_user(email="owner@x.com", name="Owner")
    member = make_user(email="zoe@x.com", name="Zoe")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    add_membership(member, cid, "admin")
    rows = list_members(cid)
    assert {"user_id": owner, "email": "owner@x.com", "name": "Owner", "role": "owner"} in rows
    assert {"user_id": member, "email": "zoe@x.com", "name": "Zoe", "role": "admin"} in rows


def test_remove_last_admin_is_rejected(tmp_db, make_user):
    owner = make_user(email="owner@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    with pytest.raises(LastAdminError):
        remove_membership(owner, cid)
    assert get_role(owner, cid) == "owner"  # unchanged after rejection


def test_remove_member_preserves_content_and_nulls_authorship(tmp_db, make_user):
    owner = make_user(email="owner@x.com")
    author = make_user(email="author@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    add_membership(author, cid, "member")
    with session_scope() as s:
        s.add(Service(
            church_id=cid, created_by=author,
            service_date_iso="2026-07-19", service_date_display="July 19, 2026",
            saved_at=datetime.now(timezone.utc),
        ))
    remove_membership(author, cid)
    assert get_role(author, cid) is None
    with session_scope() as s:
        svc = s.execute(select(Service).where(Service.church_id == cid)).scalar_one()
        assert svc.created_by is None  # history survives, authorship nulled


def test_set_role_demote_last_admin_rejected(tmp_db, make_user):
    owner = make_user(email="owner@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    with pytest.raises(LastAdminError):
        set_role(owner, cid, "member")
    assert get_role(owner, cid) == "owner"


def test_set_role_demote_ok_when_second_admin_exists(tmp_db, make_user):
    owner = make_user(email="owner@x.com")
    admin2 = make_user(email="a2@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    add_membership(admin2, cid, "admin")
    set_role(owner, cid, "member")
    assert get_role(owner, cid) == "member"
    assert count_admins(cid) == 1
```

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/test_memberships_repo.py`
  Expected: FAIL — `ModuleNotFoundError: No module named 'repos.memberships'`.

- [ ] **Step 3: Write the implementation** — `repos/memberships.py`
```python
from typing import Optional

from sqlalchemy import select, func, update

from db import session_scope
from db.models import Membership, User, Service

_ADMIN_ROLES = ("owner", "admin")


class LastAdminError(Exception):
    """Raised when an operation would leave a church with zero owners/admins."""


def _lock_admin_user_ids(session, church_id) -> list:
    """Row-lock the church's owner/admin memberships (SELECT ... FOR UPDATE on
    Postgres; a no-op on SQLite) so concurrent mutual removal cannot zero the
    admin count. Returns the locked admin user_ids."""
    return session.execute(
        select(Membership.user_id)
        .where(
            Membership.church_id == church_id,
            Membership.role.in_(_ADMIN_ROLES),
        )
        .with_for_update()
    ).scalars().all()


def get_role(user_id, church_id) -> Optional[str]:
    with session_scope() as session:
        m = session.get(Membership, {"church_id": church_id, "user_id": user_id})
        return m.role if m is not None else None


def count_admins(church_id) -> int:
    with session_scope() as session:
        return session.execute(
            select(func.count())
            .select_from(Membership)
            .where(
                Membership.church_id == church_id,
                Membership.role.in_(_ADMIN_ROLES),
            )
        ).scalar_one()


def add_membership(user_id, church_id, role) -> None:
    """Idempotent add. If the membership already exists it is left unchanged
    (no duplicate row); role changes go through set_role."""
    with session_scope() as session:
        existing = session.get(
            Membership, {"church_id": church_id, "user_id": user_id}
        )
        if existing is not None:
            return
        session.add(Membership(church_id=church_id, user_id=user_id, role=role))


def set_role(user_id, church_id, role) -> None:
    """Change a member's role. Demoting the last owner/admin to member is
    rejected under a row lock."""
    with session_scope() as session:
        m = session.get(Membership, {"church_id": church_id, "user_id": user_id})
        if m is None:
            return
        if m.role in _ADMIN_ROLES and role not in _ADMIN_ROLES:
            admins = _lock_admin_user_ids(session, church_id)
            if len(admins) <= 1:
                raise LastAdminError(
                    "Cannot demote the last owner/admin of this church."
                )
        m.role = role


def remove_membership(user_id, church_id) -> None:
    """Remove a member. Removing the last owner/admin is rejected under a row
    lock. The member's authored services are preserved but their
    services.created_by is nulled (history survives the author leaving)."""
    with session_scope() as session:
        m = session.get(Membership, {"church_id": church_id, "user_id": user_id})
        if m is None:
            return
        if m.role in _ADMIN_ROLES:
            admins = _lock_admin_user_ids(session, church_id)
            if len(admins) <= 1:
                raise LastAdminError(
                    "Cannot remove the last owner/admin of this church."
                )
        session.execute(
            update(Service)
            .where(Service.church_id == church_id, Service.created_by == user_id)
            .values(created_by=None)
        )
        session.delete(m)


def list_members(church_id) -> list:
    with session_scope() as session:
        rows = session.execute(
            select(User.id, User.email, User.name, Membership.role)
            .join(Membership, Membership.user_id == User.id)
            .where(Membership.church_id == church_id)
            .order_by(User.email)
        ).all()
        return [
            {"user_id": r.id, "email": r.email, "name": r.name, "role": r.role}
            for r in rows
        ]
```

- [ ] **Step 4: Run test to verify it passes**
  Run: `pytest tests/test_memberships_repo.py`
  Expected: PASS (6 passed).

- [ ] **Step 5: Commit**
```bash
git add repos/memberships.py tests/test_memberships_repo.py
git commit -m "Add repos.memberships: last-admin guard + authorship nulling" \
  -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Invites repository (secure codes, email-bound single-use, soft-delete rejection)

**Files:**
- Create: `repos/invites.py`
- Test: `tests/test_invites_repo.py`

**Interfaces:**
- Consumes: `from db import session_scope`; `db.models.Invite` (`id, church_id, code, email, role, created_by, created_at, expires_at, revoked, accepted_at`), `db.models.Church` (`id, name, deleted_at`), `db.models.Membership` (composite PK, `role`), `db.models.User` (`id, email`); `repos.churches.create_church`, `soft_delete_church`; `repos.memberships.get_role`; conftest `make_user`.
- Produces: `create_invite(*, church_id, created_by, role="member", email=None, ttl_days=7) -> str` (returns ≥128-bit code); `get_invite_by_code(code) -> dict | None`; `accept_invite(code, user_id) -> tuple[bool, str]` (rejects soft-deleted church; email-bound = single-use + email must match; already-member = no-op success); `list_invites(church_id) -> list[dict]` (active/pending only); `revoke_invite(invite_id, church_id) -> None` (church-scoped, IDOR-safe).

- [ ] **Step 1: Write the failing test** — `tests/test_invites_repo.py`
```python
from datetime import datetime, timezone, timedelta

from sqlalchemy import select

from db import session_scope
from db.models import Invite, Church
from repos.churches import create_church
from repos.memberships import get_role
from repos.invites import (
    create_invite, get_invite_by_code, accept_invite, list_invites, revoke_invite,
)


def test_create_invite_returns_secure_code_and_lists_active(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    code = create_invite(church_id=cid, created_by=owner)
    assert isinstance(code, str) and len(code) >= 22   # >=128 bits, url-safe
    inv = get_invite_by_code(code)
    assert inv["church_id"] == cid and inv["role"] == "member"
    assert [i["code"] for i in list_invites(cid)] == [code]


def test_accept_invite_adds_membership(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    joiner = make_user(email="join@x.com")
    cid = create_church(name="Grace", timezone="UTC", owner_user_id=owner)
    code = create_invite(church_id=cid, created_by=owner)
    ok, msg = accept_invite(code, joiner)
    assert ok is True and "Grace" in msg
    assert get_role(joiner, cid) == "member"


def test_accept_invite_already_member_is_noop(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    cid = create_church(name="Grace", timezone="UTC", owner_user_id=owner)
    code = create_invite(church_id=cid, created_by=owner)
    ok, msg = accept_invite(code, owner)          # already the owner
    assert ok is True
    assert get_role(owner, cid) == "owner"        # role not downgraded to member


def test_accept_invite_rejects_soft_deleted_church(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    joiner = make_user(email="j@x.com")
    cid = create_church(name="Gone", timezone="UTC", owner_user_id=owner)
    code = create_invite(church_id=cid, created_by=owner)
    # soft-delete the church directly, leaving the invite live, to hit the
    # church-availability branch specifically.
    with session_scope() as s:
        s.get(Church, cid).deleted_at = datetime.now(timezone.utc)
    ok, msg = accept_invite(code, joiner)
    assert ok is False
    assert get_role(joiner, cid) is None


def test_email_bound_invite_matches_email_and_is_single_use(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    wrong = make_user(email="wrong@x.com")
    right = make_user(email="right@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    code = create_invite(church_id=cid, created_by=owner, email="Right@X.com", role="admin")

    ok, _ = accept_invite(code, wrong)            # mismatched email
    assert ok is False
    assert get_role(wrong, cid) is None

    ok, _ = accept_invite(code, right)            # case-insensitive match; role honored
    assert ok is True
    assert get_role(right, cid) == "admin"

    ok2, msg2 = accept_invite(code, right)        # single-use consumed
    assert ok2 is False and "used" in msg2.lower()


def test_expired_invite_rejected_and_excluded_from_active(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    joiner = make_user(email="j@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    code = create_invite(church_id=cid, created_by=owner)
    with session_scope() as s:
        inv = s.execute(select(Invite).where(Invite.code == code)).scalar_one()
        inv.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    ok, msg = accept_invite(code, joiner)
    assert ok is False and "expired" in msg.lower()
    assert list_invites(cid) == []


def test_revoke_invite_blocks_accept_and_is_church_scoped(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    other_owner = make_user(email="oo@x.com")
    joiner = make_user(email="j@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    other_cid = create_church(name="D", timezone="UTC", owner_user_id=other_owner)
    code = create_invite(church_id=cid, created_by=owner)
    inv = get_invite_by_code(code)

    revoke_invite(inv["id"], other_cid)           # wrong church -> no-op (IDOR-safe)
    assert [i["code"] for i in list_invites(cid)] == [code]

    revoke_invite(inv["id"], cid)                 # correct church
    assert list_invites(cid) == []
    ok, _ = accept_invite(code, joiner)
    assert ok is False
```

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/test_invites_repo.py`
  Expected: FAIL — `ModuleNotFoundError: No module named 'repos.invites'`.

- [ ] **Step 3: Write the implementation** — `repos/invites.py`
```python
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

from sqlalchemy import select

from db import session_scope
from db.models import Invite, Church, Membership, User


def _normalize_email(email) -> Optional[str]:
    if email is None:
        return None
    normalized = email.strip().lower()
    return normalized or None


def _as_utc(value: datetime) -> datetime:
    """Normalize a stored timestamp to aware-UTC. SQLite returns naive
    datetimes; Postgres returns aware ones. Assume naive == UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _to_dict(inv: Invite) -> dict:
    return {
        "id": inv.id,
        "church_id": inv.church_id,
        "code": inv.code,
        "email": inv.email,
        "role": inv.role,
        "created_by": inv.created_by,
        "expires_at": inv.expires_at,
        "revoked": inv.revoked,
        "accepted_at": inv.accepted_at,
    }


def create_invite(*, church_id, created_by, role="member", email=None, ttl_days=7) -> str:
    """Create an invite and return its code. Code is >=128 bits of url-safe
    entropy (secrets.token_urlsafe(32) == 256 bits)."""
    code = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    with session_scope() as session:
        session.add(Invite(
            church_id=church_id,
            code=code,
            email=_normalize_email(email),
            role=role,
            created_by=created_by,
            expires_at=now + timedelta(days=ttl_days),
            revoked=False,
        ))
        return code


def get_invite_by_code(code) -> Optional[dict]:
    with session_scope() as session:
        inv = session.execute(
            select(Invite).where(Invite.code == code)
        ).scalar_one_or_none()
        return _to_dict(inv) if inv is not None else None


def accept_invite(code, user_id) -> Tuple[bool, str]:
    """Accept an invite for user_id. Returns (ok, message). No enumerable
    difference between distinct failure causes beyond the message text.

    Rejects: unknown/revoked/expired codes; a soft-deleted church; email-bound
    codes whose email does not match the accepting user, or that were already
    used (single-use). Accepting when already a member is a no-op success.
    """
    now = datetime.now(timezone.utc)
    with session_scope() as session:
        inv = session.execute(
            select(Invite).where(Invite.code == code)
        ).scalar_one_or_none()
        if inv is None:
            return (False, "Invalid invite code.")
        if inv.revoked:
            return (False, "This invite has been revoked.")
        if inv.expires_at is not None and _as_utc(inv.expires_at) < now:
            return (False, "This invite has expired.")

        email_bound = inv.email is not None
        if email_bound and inv.accepted_at is not None:
            return (False, "This invite has already been used.")

        church = session.get(Church, inv.church_id)
        if church is None or church.deleted_at is not None:
            return (False, "This church is no longer available.")

        if email_bound:
            user = session.get(User, user_id)
            user_email = user.email if user is not None else None
            if user_email is None or user_email.strip().lower() != inv.email:
                return (False, "This invite was issued for a different email address.")

        existing = session.get(
            Membership, {"church_id": inv.church_id, "user_id": user_id}
        )
        if existing is None:
            session.add(Membership(
                church_id=inv.church_id, user_id=user_id, role=inv.role
            ))
        if email_bound:
            inv.accepted_at = now  # single-use for email-bound invites
        return (True, f"Joined {church.name}.")


def list_invites(church_id) -> list:
    """Active (pending) invites for a church: not revoked, not accepted, not
    expired. Newest first."""
    now = datetime.now(timezone.utc)
    with session_scope() as session:
        rows = session.execute(
            select(Invite)
            .where(Invite.church_id == church_id, Invite.revoked.is_(False))
            .order_by(Invite.created_at.desc())
        ).scalars().all()
        result = []
        for inv in rows:
            if inv.accepted_at is not None:
                continue
            if inv.expires_at is not None and _as_utc(inv.expires_at) < now:
                continue
            result.append({
                "id": inv.id,
                "code": inv.code,
                "email": inv.email,
                "role": inv.role,
                "created_by": inv.created_by,
                "expires_at": inv.expires_at,
            })
        return result


def revoke_invite(invite_id, church_id) -> None:
    """Revoke an invite, scoped to church_id so a caller can never revoke
    another church's invite by id (IDOR-safe)."""
    with session_scope() as session:
        inv = session.get(Invite, invite_id)
        if inv is None or inv.church_id != church_id:
            return
        inv.revoked = True
```

- [ ] **Step 4: Run test to verify it passes**
  Run: `pytest tests/test_invites_repo.py`
  Expected: PASS (7 passed).

- [ ] **Step 5: Commit**
```bash
git add repos/invites.py tests/test_invites_repo.py
git commit -m "Add repos.invites: secure codes, email-bound single-use, IDOR-safe revoke" \
  -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Tenancy guard (`validate_active_church` pure core + active-church helpers)

**Files:**
- Create: `tenancy.py`
- Test: `tests/test_tenancy.py`

**Interfaces:**
- Consumes: `from db import session_scope`; `db.models.Church` (`id, name, deleted_at`), `db.models.Membership` (`church_id, user_id, role`); `repos.churches.create_church`, `list_user_churches`; `repos.memberships.add_membership`; conftest `make_user`.
- Produces: `validate_active_church(candidate_church_id, user_id) -> dict | None` (**pure tested core**; returns `{"church_id","name","role"}`; coerces/rejects forged candidates); `require_active_church(user_id, state=None) -> dict | None` (same shape; validates the session value, else falls back to the user's real membership list, else zero-church `None`); `set_active_church(church_id, name=None, role=None, state=None) -> None`; `clear_all_church_state(state=None) -> None`; `is_admin(role) -> bool`; `CHURCH_SCOPED_STATE_KEYS` (tuple); `CHURCH_SCOPED_STATE_PREFIXES` (tuple).

**Streamlit note:** the session-touching helpers (`require_active_church`, `set_active_church`, `clear_all_church_state`) take an **injectable `state` mapping** defaulting to `st.session_state`. Tests inject a plain `dict`, so the tenancy logic — including the "reject a forged `?church=`/session value" path — is unit-tested end-to-end against a real temp DB and **never imports Streamlit**. `validate_active_church` and `is_admin` are pure. The `?church=` query-param capture into session is handled upstream in `main()` (spec §4 query-param hygiene) and is out of scope for these units.

- [ ] **Step 1: Write the failing test** — `tests/test_tenancy.py`
```python
import uuid
from datetime import datetime, timezone

from db import session_scope
from db.models import Church
from repos.churches import create_church
from tenancy import (
    validate_active_church, require_active_church, set_active_church,
    clear_all_church_state, is_admin,
    CHURCH_SCOPED_STATE_KEYS, CHURCH_SCOPED_STATE_PREFIXES,
)


def test_validate_returns_role_for_member(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    cid = create_church(name="First", timezone="UTC", owner_user_id=owner)
    assert validate_active_church(cid, owner) == {
        "church_id": cid, "name": "First", "role": "owner",
    }


def test_validate_rejects_non_member(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    outsider = make_user(email="out@x.com")
    cid = create_church(name="First", timezone="UTC", owner_user_id=owner)
    assert validate_active_church(cid, outsider) is None


def test_validate_rejects_soft_deleted_church(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    cid = create_church(name="First", timezone="UTC", owner_user_id=owner)
    with session_scope() as s:
        s.get(Church, cid).deleted_at = datetime.now(timezone.utc)
    assert validate_active_church(cid, owner) is None


def test_validate_rejects_forged_and_null_candidates(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    create_church(name="First", timezone="UTC", owner_user_id=owner)
    assert validate_active_church("not-a-uuid", owner) is None   # garbage string
    assert validate_active_church(uuid.uuid4(), owner) is None   # unknown id
    assert validate_active_church(None, owner) is None


def test_validate_accepts_string_uuid_of_real_membership(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    cid = create_church(name="First", timezone="UTC", owner_user_id=owner)
    out = validate_active_church(str(cid), owner)   # e.g. from a ?church= param
    assert out["church_id"] == cid and out["role"] == "owner"


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


def test_is_admin():
    assert is_admin("owner") is True
    assert is_admin("admin") is True
    assert is_admin("member") is False
    assert is_admin(None) is False


def test_church_scoped_keys_cover_known_state():
    for k in ("_cached_all_hymns", "scripture_hymns", "custom_elements", "include_communion"):
        assert k in CHURCH_SCOPED_STATE_KEYS
    assert "liturgy_" in CHURCH_SCOPED_STATE_PREFIXES
```

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/test_tenancy.py`
  Expected: FAIL — `ModuleNotFoundError: No module named 'tenancy'`.

- [ ] **Step 3: Write the implementation** — `tenancy.py`
```python
import uuid
from typing import Optional

from sqlalchemy import select

from db import session_scope
from db.models import Church, Membership
from repos.churches import list_user_churches

_ADMIN_ROLES = ("owner", "admin")

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

- [ ] **Step 4: Run test to verify it passes**
  Run: `pytest tests/test_tenancy.py`
  Expected: PASS (11 passed).

- [ ] **Step 5: Commit**
```bash
git add tenancy.py tests/test_tenancy.py
git commit -m "Add tenancy guard: validate_active_church pure core + session helpers" \
  -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

I have everything I need. The SPEC, the four existing modules I'm rewriting, the exact Notion property key names (`"Hymn Title"`, `"Hymn Number"`, `"Scripture References"`, `"Theme"`, `"Hymnary.org Link"`), and confirmation there's no test infra yet. Here are Tasks 9-12.

### Task 9: Per-Church Hymn Repository (`repos/hymns.py`) + flat-dict `get_property_value`

**Files:**
- Create: `repos/hymns.py`
- Modify: `hymn_utils.py` (make `get_property_value` accept the flat-dict shape too)
- Modify: `tests/conftest.py` (no re-create — add nothing new; Task 1 fixtures are reused as-is)
- Test: `tests/test_hymns_repo.py`, `tests/test_hymn_utils.py`

**Interfaces:**

*Consumes (from earlier tasks — exact):*
- `db` (Task 5/6): `session_scope()` contextmanager (commit/rollback/close), `init_db`, `reset_engine_for_tests(url) -> Engine`.
- `db.models` (Task 5/6): `Hymn(id: Uuid pk, church_id: Uuid, title: str, number: int|None, scripture_refs: str|None, theme: str|None, hymnary_link: str|None, audio_url: str|None)`; `HymnCatalog(id, title, number, scripture_refs, theme, hymnary_link, audio_url)` (no `church_id`).
- `tests/conftest.py` (Task 1): factory fixtures `tmp_db`, `make_user(email=..., name=...) -> uuid.UUID`, `make_church(*, name, timezone, owner_user_id) -> uuid.UUID` (wraps `repos.churches.create_church`, so it seeds hymns from the **current** `hymn_catalog`), `seed_catalog(n)` (inserts `n` `HymnCatalog` rows and commits).

*Produces (later tasks + `repos.churches.create_church` rely on these exact names):*
- `repos/hymns.py`:
  - `list_hymns(church_id) -> list[dict]` — flat Notion-key dicts: `{"id", "Hymn Title", "Hymn Number", "Scripture References", "Theme", "Hymnary.org Link", "Audio"}`.
  - `add_hymn(church_id, *, title, number=None, scripture_refs=None, theme=None, hymnary_link=None, audio_url=None) -> dict`
  - `update_hymn(hymn_id, church_id, *, title, number=None, scripture_refs=None, theme=None, hymnary_link=None, audio_url=None) -> dict | None` (IDOR-safe: cross-church id → `None`)
  - `delete_hymn(hymn_id, church_id) -> bool` (IDOR-safe: cross-church id → `False`)
  - `seed_church_from_catalog(church_id, session) -> int` — **CANONICAL**; `repos.churches.create_church` imports THIS one and calls it inside its creation transaction (uses the passed session, does **not** commit).
- `hymn_utils.get_property_value(hymn, prop_name)` — unchanged signature, now also reads flat dicts produced by `list_hymns`.

- [ ] **Step 1: Write the failing tests**

`tests/test_hymn_utils.py`:
```python
from hymn_utils import get_property_value


def test_get_property_value_nested_notion_shape():
    nested = {
        "properties": {
            "Hymn Title": {"type": "title", "title": [{"plain_text": "Be Thou My Vision"}]},
            "Hymn Number": {"type": "number", "number": 339},
            "Scripture References": {"type": "rich_text", "rich_text": [{"plain_text": "Prov 3:5"}]},
            "Theme": {"type": "multi_select", "multi_select": [{"name": "Trust"}, {"name": "Guidance"}]},
            "Hymnary.org Link": {"type": "url", "url": "https://hymnary.org/text/be_thou"},
        }
    }
    assert get_property_value(nested, "Hymn Title") == "Be Thou My Vision"
    assert get_property_value(nested, "Hymn Number") == 339
    assert get_property_value(nested, "Scripture References") == "Prov 3:5"
    assert get_property_value(nested, "Theme") == ["Trust", "Guidance"]
    assert get_property_value(nested, "Hymnary.org Link") == "https://hymnary.org/text/be_thou"
    assert get_property_value(nested, "Absent") is None


def test_get_property_value_flat_dict_shape():
    flat = {
        "id": "abc",
        "Hymn Title": "Be Thou My Vision",
        "Hymn Number": 339,
        "Scripture References": "Prov 3:5",
        "Theme": "Trust",
        "Hymnary.org Link": "https://hymnary.org/text/be_thou",
    }
    assert get_property_value(flat, "Hymn Title") == "Be Thou My Vision"
    assert get_property_value(flat, "Hymn Number") == 339
    assert get_property_value(flat, "Scripture References") == "Prov 3:5"
    assert get_property_value(flat, "Theme") == "Trust"
    assert get_property_value(flat, "Hymnary.org Link") == "https://hymnary.org/text/be_thou"
    assert get_property_value(flat, "Absent") is None
```

`tests/test_hymns_repo.py`:
```python
from db import session_scope
from repos.hymns import (
    add_hymn,
    delete_hymn,
    list_hymns,
    seed_church_from_catalog,
    update_hymn,
)


def test_add_hymn_maps_to_flat_notion_keys(tmp_db, make_user, make_church):
    owner = make_user(email="owner@grace.org")
    # Catalog is empty here, so the church is created with 0 hymns.
    cid = make_church(name="Grace", timezone="America/New_York", owner_user_id=owner)
    assert list_hymns(cid) == []

    created = add_hymn(
        cid,
        title="Amazing Grace",
        number=378,
        scripture_refs="Eph 2:8",
        theme="Grace",
        hymnary_link="https://hymnary.org/text/amazing_grace",
    )
    assert created["Hymn Title"] == "Amazing Grace"
    assert "id" in created

    hymns = list_hymns(cid)
    assert len(hymns) == 1
    h = hymns[0]
    assert set(h) >= {
        "id",
        "Hymn Title",
        "Hymn Number",
        "Scripture References",
        "Theme",
        "Hymnary.org Link",
        "Audio",
    }
    assert h["Hymn Title"] == "Amazing Grace"
    assert h["Hymn Number"] == 378
    assert h["Scripture References"] == "Eph 2:8"
    assert h["Theme"] == "Grace"
    assert h["Hymnary.org Link"] == "https://hymnary.org/text/amazing_grace"


def test_update_hymn_is_church_scoped_idor_safe(tmp_db, make_user, make_church):
    owner = make_user(email="owner2@grace.org")
    a = make_church(name="A", timezone="America/New_York", owner_user_id=owner)
    b = make_church(name="B", timezone="America/New_York", owner_user_id=owner)
    created = add_hymn(a, title="Holy, Holy, Holy", number=1)
    hid = created["id"]

    # Church B cannot touch Church A's hymn.
    assert update_hymn(hid, b, title="HACKED", number=999) is None
    unchanged = list_hymns(a)[0]
    assert unchanged["Hymn Title"] == "Holy, Holy, Holy"
    assert unchanged["Hymn Number"] == 1

    # Correct church can update.
    updated = update_hymn(hid, a, title="Holy, Holy, Holy!", number=2, theme="Trinity")
    assert updated is not None
    assert updated["Hymn Title"] == "Holy, Holy, Holy!"
    assert updated["Hymn Number"] == 2
    assert updated["Theme"] == "Trinity"


def test_delete_hymn_is_church_scoped_idor_safe(tmp_db, make_user, make_church):
    owner = make_user(email="owner3@grace.org")
    a = make_church(name="A", timezone="America/New_York", owner_user_id=owner)
    b = make_church(name="B", timezone="America/New_York", owner_user_id=owner)
    hid = add_hymn(a, title="For All the Saints", number=326)["id"]

    # Cross-church delete is a no-op.
    assert delete_hymn(hid, b) is False
    assert len(list_hymns(a)) == 1

    # Same-church delete works.
    assert delete_hymn(hid, a) is True
    assert list_hymns(a) == []


def test_seed_church_from_catalog_returns_count_and_copies_rows(
    tmp_db, make_user, make_church, seed_catalog
):
    owner = make_user(email="seed@grace.org")
    # Created against an empty catalog -> 0 hymns to start.
    cid = make_church(name="Seeded", timezone="America/New_York", owner_user_id=owner)
    assert list_hymns(cid) == []

    seed_catalog(3)
    with session_scope() as session:
        n = seed_church_from_catalog(cid, session)
    assert n == 3
    assert len(list_hymns(cid)) == 3
```

- [ ] **Step 2: Run tests to verify they fail**
  Run: `pytest tests/test_hymn_utils.py tests/test_hymns_repo.py -q`
  Expected: FAIL — `tests/test_hymns_repo.py` errors at collection with `ModuleNotFoundError: No module named 'repos.hymns'`; `test_get_property_value_flat_dict_shape` FAILS with `AssertionError` (current code returns `None` for a flat dict because there is no `"properties"` envelope).

- [ ] **Step 3: Write the implementation**

Modify `hymn_utils.py` (full new content):
```python
"""Shared helpers for reading hymn properties.

Supports two shapes:
  * Nested Notion page shape: {"properties": {<name>: {"type": ..., ...}}}
  * Flat dict shape produced by repos.hymns.list_hymns:
    {<Notion property name>: <plain value>}
"""
from typing import Any, Dict


def get_property_value(hymn: Dict[str, Any], prop_name: str) -> Any:
    """Get the value of a property from a hymn object (nested or flat)."""
    # Flat shape: the Notion property names are top-level keys mapping directly
    # to plain values. Detect it by the absence of a Notion "properties" envelope.
    if "properties" not in hymn:
        return hymn.get(prop_name)

    props = hymn.get("properties", {})
    prop_data = props.get(prop_name, {})
    prop_type = prop_data.get("type")

    if prop_type == "title":
        return "".join([t.get("plain_text", "") for t in prop_data.get("title", [])])
    elif prop_type == "rich_text":
        text = "".join([t.get("plain_text", "") for t in prop_data.get("rich_text", [])])
        return text if text else None
    elif prop_type == "number":
        return prop_data.get("number")
    elif prop_type == "url":
        return prop_data.get("url")
    elif prop_type == "date":
        date_obj = prop_data.get("date")
        return date_obj.get("start") if date_obj else None
    elif prop_type == "multi_select":
        return [opt.get("name") for opt in prop_data.get("multi_select", []) if opt.get("name")]
    return None
```

Create `repos/hymns.py`:
```python
"""Per-church hymn repository (database-backed, church-scoped, IDOR-safe).

Public hymn dicts use the flat Notion-property key shape so existing helpers
(hymn_utils.get_property_value, worship_service.*) consume them unchanged.
"""
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from db import session_scope
from db.models import Hymn, HymnCatalog


def _as_uuid(value: Any) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


def _hymn_to_dict(h: Hymn) -> Dict[str, Any]:
    """Map a Hymn row to the flat Notion-key dict the app consumes."""
    return {
        "id": str(h.id),
        "Hymn Title": h.title,
        "Hymn Number": h.number,
        "Scripture References": h.scripture_refs,
        "Theme": h.theme,
        "Hymnary.org Link": h.hymnary_link,
        "Audio": h.audio_url,
    }


def list_hymns(church_id) -> List[Dict[str, Any]]:
    """All hymns for a church, ordered by number then title. Flat-key dicts."""
    cid = _as_uuid(church_id)
    with session_scope() as session:
        rows = (
            session.execute(
                select(Hymn)
                .where(Hymn.church_id == cid)
                .order_by(Hymn.number, Hymn.title)
            )
            .scalars()
            .all()
        )
        return [_hymn_to_dict(h) for h in rows]


def add_hymn(
    church_id,
    *,
    title: str,
    number: Optional[int] = None,
    scripture_refs: Optional[str] = None,
    theme: Optional[str] = None,
    hymnary_link: Optional[str] = None,
    audio_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Insert a hymn for a church. Returns the flat-key dict (with new id)."""
    cid = _as_uuid(church_id)
    with session_scope() as session:
        h = Hymn(
            church_id=cid,
            title=title,
            number=number,
            scripture_refs=scripture_refs,
            theme=theme,
            hymnary_link=hymnary_link,
            audio_url=audio_url,
        )
        session.add(h)
        session.flush()
        return _hymn_to_dict(h)


def update_hymn(
    hymn_id,
    church_id,
    *,
    title: str,
    number: Optional[int] = None,
    scripture_refs: Optional[str] = None,
    theme: Optional[str] = None,
    hymnary_link: Optional[str] = None,
    audio_url: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Update a hymn only if it belongs to `church_id`. Cross-church -> None."""
    cid = _as_uuid(church_id)
    with session_scope() as session:
        h = session.execute(
            select(Hymn).where(Hymn.id == _as_uuid(hymn_id), Hymn.church_id == cid)
        ).scalar_one_or_none()
        if h is None:
            return None
        h.title = title
        h.number = number
        h.scripture_refs = scripture_refs
        h.theme = theme
        h.hymnary_link = hymnary_link
        h.audio_url = audio_url
        session.flush()
        return _hymn_to_dict(h)


def delete_hymn(hymn_id, church_id) -> bool:
    """Delete a hymn only if it belongs to `church_id`. Cross-church -> False."""
    cid = _as_uuid(church_id)
    with session_scope() as session:
        result = session.execute(
            delete(Hymn).where(Hymn.id == _as_uuid(hymn_id), Hymn.church_id == cid)
        )
        return result.rowcount > 0


def seed_church_from_catalog(church_id, session: Session) -> int:
    """CANONICAL seed: copy every hymn_catalog row into a church's hymns.

    Uses the caller-supplied session (part of create_church's transaction) and
    does NOT commit. Returns the number of hymns seeded.
    """
    cid = _as_uuid(church_id)
    rows = session.execute(select(HymnCatalog)).scalars().all()
    count = 0
    for c in rows:
        session.add(
            Hymn(
                church_id=cid,
                title=c.title,
                number=c.number,
                scripture_refs=c.scripture_refs,
                theme=c.theme,
                hymnary_link=c.hymnary_link,
                audio_url=c.audio_url,
            )
        )
        count += 1
    session.flush()
    return count
```

- [ ] **Step 4: Run tests to verify they pass**
  Run: `pytest tests/test_hymn_utils.py tests/test_hymns_repo.py -q`
  Expected: PASS (7 passed).

- [ ] **Step 5: Commit**
  `git add repos/hymns.py hymn_utils.py tests/test_hymns_repo.py tests/test_hymn_utils.py && git commit -m "Task 9: church-scoped hymns repo + flat-dict get_property_value"`

---

### Task 10: DB-backed Service Archive (`service_archive.py`)

**Files:**
- Modify: `service_archive.py` (full rewrite — file/Notion storage removed, DB-backed, `church_id` on every function)
- Test: `tests/test_service_archive.py`

**Interfaces:**

*Consumes (exact):*
- `db`: `session_scope()`.
- `db.models`: `Service(id: Uuid pk, church_id: Uuid, created_by: Uuid|None, service_date_iso: str, service_date_display: str, occasion: str, scriptures: JSON, hymns: JSON, liturgy: JSON, sermon_title: str, selected_ot_ref: str, selected_nt_ref: str, include_communion: bool, saved_at: datetime)` — **no DATE column**; the two date fields are `service_date_iso` and `service_date_display`, and `saved_at` defaults Python-side to `datetime.now(timezone.utc)`.
- `tests/conftest.py`: `tmp_db`, `make_user`, `make_church`.

*Produces (consumed by the app-rewrite task):*
- `list_saved_services(church_id) -> list[dict]` (most recent first by `saved_at`)
- `save_service(church_id, *, created_by=None, service_date, service_date_iso, occasion, scriptures, hymns, liturgy, sermon_title="", selected_ot_ref="", selected_nt_ref="", include_communion=False) -> dict`
- `get_service(service_id, church_id) -> dict | None` (**cross-church id -> None**)
- `update_service(service_id, church_id, *, service_date, service_date_iso, occasion, scriptures, hymns, liturgy, sermon_title="", selected_ot_ref="", selected_nt_ref="", include_communion=False) -> dict | None` (**cross-church id -> None**)
- `delete_service(service_id, church_id) -> bool` (**cross-church id -> False**)
- Each returned dict: `{"id","church_id","created_by","service_date","service_date_iso","occasion","scriptures","hymns","liturgy","sermon_title","selected_ot_ref","selected_nt_ref","include_communion","saved_at"}` (`service_date` is the display string; `hymns` is the denormalized `[{"title","number"}]` snapshot; `saved_at` is ISO8601 string).

- [ ] **Step 1: Write the failing test**

`tests/test_service_archive.py`:
```python
from service_archive import (
    delete_service,
    get_service,
    list_saved_services,
    save_service,
    update_service,
)

_KW = dict(
    service_date="July 5, 2026",
    service_date_iso="2026-07-05",
    occasion="Ordinary",
    scriptures=["John 3:16"],
    hymns=[{"title": "Holy, Holy, Holy", "number": 1, "extra": "dropped"}],
    liturgy={"opening": "Call to worship"},
    sermon_title="Grace Abounds",
    selected_ot_ref="Ps 23",
    selected_nt_ref="John 3",
    include_communion=True,
)


def test_save_service_returns_snapshot(tmp_db, make_user, make_church):
    u = make_user(email="s@x.org")
    a = make_church(name="A", timezone="America/New_York", owner_user_id=u)
    saved = save_service(a, created_by=u, **_KW)
    assert saved["church_id"] == str(a)
    assert saved["created_by"] == str(u)
    assert saved["occasion"] == "Ordinary"
    # hymns are denormalized to title/number only.
    assert saved["hymns"] == [{"title": "Holy, Holy, Holy", "number": 1}]
    assert saved["include_communion"] is True
    assert saved["saved_at"]  # ISO timestamp present


def test_get_update_delete_are_church_scoped_idor(tmp_db, make_user, make_church):
    u = make_user(email="s2@x.org")
    a = make_church(name="A", timezone="America/New_York", owner_user_id=u)
    b = make_church(name="B", timezone="America/New_York", owner_user_id=u)
    sid = save_service(a, created_by=u, **_KW)["id"]

    # Same church can read it.
    assert get_service(sid, a) is not None
    # Church B cannot read/update/delete Church A's service.
    assert get_service(sid, b) is None
    assert update_service(sid, b, **{**_KW, "occasion": "HACKED"}) is None
    assert delete_service(sid, b) is False

    # Original untouched.
    still = get_service(sid, a)
    assert still["occasion"] == "Ordinary"

    # Correct church can update then delete.
    updated = update_service(sid, a, **{**_KW, "occasion": "Revised"})
    assert updated["occasion"] == "Revised"
    assert delete_service(sid, a) is True
    assert get_service(sid, a) is None


def test_list_saved_services_is_church_scoped(tmp_db, make_user, make_church):
    u = make_user(email="s3@x.org")
    a = make_church(name="A", timezone="America/New_York", owner_user_id=u)
    b = make_church(name="B", timezone="America/New_York", owner_user_id=u)
    save_service(a, created_by=u, **{**_KW, "occasion": "A1"})
    save_service(a, created_by=u, **{**_KW, "occasion": "A2"})
    save_service(b, created_by=u, **{**_KW, "occasion": "B1"})

    a_list = list_saved_services(a)
    b_list = list_saved_services(b)
    assert {s["occasion"] for s in a_list} == {"A1", "A2"}
    assert [s["occasion"] for s in b_list] == ["B1"]
```

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/test_service_archive.py -q`
  Expected: FAIL — the current `save_service` is keyword-only with no positional `church_id` and no `created_by`/`service_date` params, so `save_service(a, created_by=u, service_date=...)` raises `TypeError: save_service() got an unexpected keyword argument 'created_by'` / positional-arg error at collection/run time.

- [ ] **Step 3: Write the implementation**

Modify `service_archive.py` (full new content):
```python
#!/usr/bin/env python3
"""Database-backed, church-scoped worship service archive.

Every function is scoped to a validated `church_id` (derived server-side by the
active-church guard). Reads/updates/deletes for an id outside the caller's
church return "not found" (None / False) — the IDOR fix.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select

from db import session_scope
from db.models import Service


def _as_uuid(value: Any) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


def _hymn_snapshot(hymns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [{"title": h.get("title"), "number": h.get("number")} for h in (hymns or [])]


def _to_dict(s: Service) -> Dict[str, Any]:
    return {
        "id": str(s.id),
        "church_id": str(s.church_id),
        "created_by": str(s.created_by) if s.created_by else None,
        "service_date": s.service_date_display,
        "service_date_iso": s.service_date_iso,
        "occasion": s.occasion,
        "scriptures": s.scriptures or [],
        "hymns": s.hymns or [],
        "liturgy": s.liturgy or {},
        "sermon_title": s.sermon_title or "",
        "selected_ot_ref": s.selected_ot_ref or "",
        "selected_nt_ref": s.selected_nt_ref or "",
        "include_communion": bool(s.include_communion),
        "saved_at": s.saved_at.isoformat() if s.saved_at else None,
    }


def list_saved_services(church_id) -> List[Dict[str, Any]]:
    """All services for a church, most recent first (by saved_at)."""
    cid = _as_uuid(church_id)
    with session_scope() as session:
        rows = (
            session.execute(
                select(Service)
                .where(Service.church_id == cid)
                .order_by(Service.saved_at.desc())
            )
            .scalars()
            .all()
        )
        return [_to_dict(s) for s in rows]


def save_service(
    church_id,
    *,
    created_by=None,
    service_date: str,
    service_date_iso: str,
    occasion: str,
    scriptures: List[str],
    hymns: List[Dict[str, Any]],
    liturgy: Dict[str, str],
    sermon_title: str = "",
    selected_ot_ref: str = "",
    selected_nt_ref: str = "",
    include_communion: bool = False,
) -> Dict[str, Any]:
    """Insert a service for a church. Returns the saved dict (with id, saved_at)."""
    cid = _as_uuid(church_id)
    with session_scope() as session:
        s = Service(
            church_id=cid,
            created_by=_as_uuid(created_by) if created_by else None,
            service_date_display=service_date,
            service_date_iso=service_date_iso,
            occasion=occasion,
            scriptures=list(scriptures or []),
            hymns=_hymn_snapshot(hymns),
            liturgy=dict(liturgy or {}),
            sermon_title=sermon_title or "",
            selected_ot_ref=selected_ot_ref or "",
            selected_nt_ref=selected_nt_ref or "",
            include_communion=bool(include_communion),
        )
        session.add(s)
        session.flush()
        return _to_dict(s)


def get_service(service_id, church_id) -> Optional[Dict[str, Any]]:
    """Return one service only if it belongs to `church_id`. Else None."""
    cid = _as_uuid(church_id)
    with session_scope() as session:
        s = session.execute(
            select(Service).where(
                Service.id == _as_uuid(service_id), Service.church_id == cid
            )
        ).scalar_one_or_none()
        return _to_dict(s) if s is not None else None


def update_service(
    service_id,
    church_id,
    *,
    service_date: str,
    service_date_iso: str,
    occasion: str,
    scriptures: List[str],
    hymns: List[Dict[str, Any]],
    liturgy: Dict[str, str],
    sermon_title: str = "",
    selected_ot_ref: str = "",
    selected_nt_ref: str = "",
    include_communion: bool = False,
) -> Optional[Dict[str, Any]]:
    """Update a service only if it belongs to `church_id`. Cross-church -> None."""
    cid = _as_uuid(church_id)
    with session_scope() as session:
        s = session.execute(
            select(Service).where(
                Service.id == _as_uuid(service_id), Service.church_id == cid
            )
        ).scalar_one_or_none()
        if s is None:
            return None
        s.service_date_display = service_date
        s.service_date_iso = service_date_iso
        s.occasion = occasion
        s.scriptures = list(scriptures or [])
        s.hymns = _hymn_snapshot(hymns)
        s.liturgy = dict(liturgy or {})
        s.sermon_title = sermon_title or ""
        s.selected_ot_ref = selected_ot_ref or ""
        s.selected_nt_ref = selected_nt_ref or ""
        s.include_communion = bool(include_communion)
        s.saved_at = datetime.now(timezone.utc)
        session.flush()
        return _to_dict(s)


def delete_service(service_id, church_id) -> bool:
    """Delete a service only if it belongs to `church_id`. Cross-church -> False."""
    cid = _as_uuid(church_id)
    with session_scope() as session:
        result = session.execute(
            delete(Service).where(
                Service.id == _as_uuid(service_id), Service.church_id == cid
            )
        )
        return result.rowcount > 0
```

- [ ] **Step 4: Run test to verify it passes**
  Run: `pytest tests/test_service_archive.py -q`
  Expected: PASS (3 passed).

- [ ] **Step 5: Commit**
  `git add service_archive.py tests/test_service_archive.py && git commit -m "Task 10: DB-backed church-scoped service archive (IDOR fix)"`

---

### Task 11: DB-backed Hymn Usage (`hymn_usage.py`)

**Files:**
- Modify: `hymn_usage.py` (full rewrite — file/Notion storage removed, DB-backed, church-scoped, idempotent writes)
- Test: `tests/test_hymn_usage.py`

**Interfaces:**

*Consumes (exact):*
- `db`: `session_scope()`.
- `db.models`: `HymnUsage(id: Uuid pk, church_id: Uuid, service_date_iso: str, hymn_number: int|None, hymn_title: str, recorded_at: datetime)` — `service_date_iso` is stored as a `YYYY-MM-DD` string (consistent with the "no DATE column" decision; lexicographic compare drives the 12-week window).
- `tests/conftest.py`: `tmp_db`, `make_user`, `make_church`.

*Produces (consumed by the service-builder task):*
- `get_recently_used_identifiers(church_id, weeks=12) -> set[tuple[int|None, str]]` (each `(number, title.lower())`, filtered to this church only)
- `record_usage(church_id, date_str, hymns) -> bool` — parses `date_str` to ISO; returns `False` if unparseable; **idempotent** per `(church_id, service_date_iso, hymn_number, hymn_title)`.
- `is_hymn_recently_used(number, title, recent_set) -> bool` (pure; unchanged behavior)

- [ ] **Step 1: Write the failing test**

`tests/test_hymn_usage.py`:
```python
from datetime import date, timedelta

from db import session_scope
from db.models import HymnUsage
from hymn_usage import (
    get_recently_used_identifiers,
    is_hymn_recently_used,
    record_usage,
)

RECENT = (date.today() - timedelta(days=7)).isoformat()


def test_usage_is_church_scoped(tmp_db, make_user, make_church):
    u = make_user(email="u@x.org")
    a = make_church(name="A", timezone="America/New_York", owner_user_id=u)
    b = make_church(name="B", timezone="America/New_York", owner_user_id=u)

    assert record_usage(a, RECENT, [{"number": 100, "title": "Holy, Holy, Holy"}]) is True

    a_set = get_recently_used_identifiers(a, weeks=12)
    b_set = get_recently_used_identifiers(b, weeks=12)
    assert (100, "holy, holy, holy") in a_set
    assert (100, "holy, holy, holy") not in b_set
    assert b_set == set()
    # is_hymn_recently_used consumes the church-scoped set.
    assert is_hymn_recently_used(100, "Holy, Holy, Holy", a_set) is True
    assert is_hymn_recently_used(100, "Holy, Holy, Holy", b_set) is False


def test_record_usage_is_idempotent(tmp_db, make_user, make_church):
    u = make_user(email="u2@x.org")
    a = make_church(name="A", timezone="America/New_York", owner_user_id=u)
    hymns = [{"number": 100, "title": "Holy, Holy, Holy"}]
    assert record_usage(a, RECENT, hymns) is True
    assert record_usage(a, RECENT, hymns) is True  # re-prepared bulletin

    with session_scope() as session:
        count = session.query(HymnUsage).filter(HymnUsage.church_id == a).count()
    assert count == 1


def test_record_usage_rejects_unparseable_date(tmp_db, make_user, make_church):
    u = make_user(email="u3@x.org")
    a = make_church(name="A", timezone="America/New_York", owner_user_id=u)
    assert record_usage(a, "not a date", [{"number": 1, "title": "X"}]) is False


def test_old_usage_excluded_from_window(tmp_db, make_user, make_church):
    u = make_user(email="u4@x.org")
    a = make_church(name="A", timezone="America/New_York", owner_user_id=u)
    old = (date.today() - timedelta(weeks=20)).isoformat()
    assert record_usage(a, old, [{"number": 55, "title": "Old Hymn"}]) is True
    assert (55, "old hymn") not in get_recently_used_identifiers(a, weeks=12)
```

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/test_hymn_usage.py -q`
  Expected: FAIL — the current `get_recently_used_identifiers(weeks=12)` / `record_usage(date_str, hymns)` take no `church_id`, so `record_usage(a, RECENT, hymns)` raises `TypeError` (too many positional args) and `from db.models import HymnUsage` may not yet be importable at collection — test errors.

- [ ] **Step 3: Write the implementation**

Modify `hymn_usage.py` (full new content):
```python
#!/usr/bin/env python3
"""Database-backed, church-scoped hymn-usage tracking.

Drives the "exclude hymns used in the last 12 weeks" filter. All reads and
writes are scoped to a validated `church_id`; writes are idempotent per
(church_id, service_date_iso, hymn_number, hymn_title) so re-preparing a
bulletin never inflates the exclusion set.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import select

from db import session_scope
from db.models import HymnUsage


def _as_uuid(value: Any) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


def _parse_date_to_iso(date_str: str) -> Optional[str]:
    """Parse common date strings to YYYY-MM-DD. Returns None if unparseable."""
    s = (date_str or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%m/%d/%Y", "%d %B %Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _coerce_number(num: Any) -> Optional[int]:
    if num is None or isinstance(num, int):
        return num
    try:
        return int(num)
    except (TypeError, ValueError):
        return None


def _hymn_key(number: Optional[int], title: str) -> Tuple[Optional[int], str]:
    """Normalized (number, title_lower) for matching."""
    return (number, (title or "").strip().lower())


def get_recently_used_identifiers(church_id, weeks: int = 12) -> Set[Tuple[Optional[int], str]]:
    """Set of (number, title_lower) used by THIS church in the last `weeks` weeks."""
    cid = _as_uuid(church_id)
    cutoff = (datetime.now(timezone.utc).date() - timedelta(weeks=weeks)).isoformat()
    with session_scope() as session:
        rows = session.execute(
            select(HymnUsage.hymn_number, HymnUsage.hymn_title).where(
                HymnUsage.church_id == cid,
                HymnUsage.service_date_iso >= cutoff,
            )
        ).all()
    return {_hymn_key(number, title) for number, title in rows}


def record_usage(church_id, date_str: str, hymns: List[Dict[str, Any]]) -> bool:
    """Record a service's hymns for a church. Idempotent per dedupe key.

    `date_str` may be e.g. "February 15, 2026" or "2026-02-15".
    Returns True if recorded (or nothing to record); False if date unparseable.
    """
    iso = _parse_date_to_iso(date_str)
    if not iso:
        return False
    cid = _as_uuid(church_id)

    payload: List[Tuple[Optional[int], str]] = []
    for h in hymns:
        title = (h.get("title") or "").strip()
        if not title:
            continue
        payload.append((_coerce_number(h.get("number")), title))
    if not payload:
        return True

    with session_scope() as session:
        existing = session.execute(
            select(HymnUsage.hymn_number, HymnUsage.hymn_title).where(
                HymnUsage.church_id == cid,
                HymnUsage.service_date_iso == iso,
            )
        ).all()
        seen = {(n, t) for n, t in existing}
        for num, title in payload:
            if (num, title) in seen:
                continue
            session.add(
                HymnUsage(
                    church_id=cid,
                    service_date_iso=iso,
                    hymn_number=num,
                    hymn_title=title,
                )
            )
            seen.add((num, title))
    return True


def is_hymn_recently_used(
    number: Optional[int],
    title: str,
    recent_set: Set[Tuple[Optional[int], str]],
) -> bool:
    """True if this hymn (number, title) is in the recent-usage set."""
    return _hymn_key(number, title) in recent_set
```

- [ ] **Step 4: Run test to verify it passes**
  Run: `pytest tests/test_hymn_usage.py -q`
  Expected: PASS (4 passed).

- [ ] **Step 5: Commit**
  `git add hymn_usage.py tests/test_hymn_usage.py && git commit -m "Task 11: DB-backed church-scoped idempotent hymn usage"`

---

### Task 12: DB-backed Email Contacts (`email_contacts.py`)

**Files:**
- Modify: `email_contacts.py` (full rewrite — JSON storage and `DEFAULT_CONTACTS` removed, DB-backed, church-scoped)
- Test: `tests/test_email_contacts.py`

**Interfaces:**

*Consumes (exact):*
- `db`: `session_scope()`.
- `db.models`: `Contact(id: Uuid pk, church_id: Uuid, name: str, email: str, created_at: datetime)`.
- `tests/conftest.py`: `tmp_db`, `make_user`, `make_church`.

*Produces (consumed by the Settings + send-bulletin tasks):*
- `list_contacts(church_id) -> list[dict]` — each `{"id","name","email"}` (id is `str`)
- `add_contact(church_id, *, name, email) -> dict` — `{"id","name","email"}`
- `delete_contact(contact_id, church_id) -> bool` — **contact_id FIRST**; cross-church id -> `False`
- `get_contacts_for_display(church_id) -> list[dict]` — thin alias of `list_contacts`; **no defaults**
- **Removed:** module-level `DEFAULT_CONTACTS` (and the hardcoded personal/office emails).

- [ ] **Step 1: Write the failing test**

`tests/test_email_contacts.py`:
```python
import email_contacts
from email_contacts import (
    add_contact,
    delete_contact,
    get_contacts_for_display,
    list_contacts,
)


def test_no_default_contacts_symbol():
    # The hardcoded real emails must be gone from the code entirely.
    assert not hasattr(email_contacts, "DEFAULT_CONTACTS")


def test_contacts_are_church_isolated(tmp_db, make_user, make_church):
    u = make_user(email="c@x.org")
    a = make_church(name="A", timezone="America/New_York", owner_user_id=u)
    b = make_church(name="B", timezone="America/New_York", owner_user_id=u)

    c1 = add_contact(a, name="Mary", email="mary@x.org")
    assert set(c1) == {"id", "name", "email"}
    assert c1["name"] == "Mary"

    # New church starts empty — no defaults inherited.
    assert list_contacts(b) == []
    assert get_contacts_for_display(b) == []
    assert [c["email"] for c in list_contacts(a)] == ["mary@x.org"]


def test_delete_contact_is_church_scoped_idor(tmp_db, make_user, make_church):
    u = make_user(email="c2@x.org")
    a = make_church(name="A", timezone="America/New_York", owner_user_id=u)
    b = make_church(name="B", timezone="America/New_York", owner_user_id=u)
    cid = add_contact(a, name="Mary", email="mary@x.org")["id"]

    # Church B cannot delete Church A's contact (contact_id is the FIRST arg).
    assert delete_contact(cid, b) is False
    assert len(list_contacts(a)) == 1

    # Correct church can.
    assert delete_contact(cid, a) is True
    assert list_contacts(a) == []
```

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/test_email_contacts.py -q`
  Expected: FAIL — collection errors with `ImportError: cannot import name 'add_contact' from 'email_contacts'` (the current module exposes only `load_contacts`/`save_contacts`/`get_contacts_for_display` and still defines `DEFAULT_CONTACTS`).

- [ ] **Step 3: Write the implementation**

Modify `email_contacts.py` (full new content):
```python
#!/usr/bin/env python3
"""Database-backed, church-scoped email contacts for bulletin distribution.

The hardcoded DEFAULT_CONTACTS have been removed: each church manages its own
recipients on the Settings page, and a new church starts with an empty list.
"""
import uuid
from typing import Any, Dict, List

from sqlalchemy import delete, select

from db import session_scope
from db.models import Contact


def _as_uuid(value: Any) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


def _to_dict(c: Contact) -> Dict[str, str]:
    return {"id": str(c.id), "name": c.name, "email": c.email}


def list_contacts(church_id) -> List[Dict[str, str]]:
    """All contacts for a church, ordered by creation then name."""
    cid = _as_uuid(church_id)
    with session_scope() as session:
        rows = (
            session.execute(
                select(Contact)
                .where(Contact.church_id == cid)
                .order_by(Contact.created_at, Contact.name)
            )
            .scalars()
            .all()
        )
        return [_to_dict(c) for c in rows]


def add_contact(church_id, *, name: str, email: str) -> Dict[str, str]:
    """Insert a contact for a church. Returns {id, name, email}."""
    cid = _as_uuid(church_id)
    with session_scope() as session:
        c = Contact(church_id=cid, name=name, email=email)
        session.add(c)
        session.flush()
        return _to_dict(c)


def delete_contact(contact_id, church_id) -> bool:
    """Delete a contact only if it belongs to `church_id`. Cross-church -> False."""
    cid = _as_uuid(church_id)
    with session_scope() as session:
        result = session.execute(
            delete(Contact).where(
                Contact.id == _as_uuid(contact_id), Contact.church_id == cid
            )
        )
        return result.rowcount > 0


def get_contacts_for_display(church_id) -> List[Dict[str, str]]:
    """Contacts for the UI. No defaults — empty list when a church has none."""
    return list_contacts(church_id)
```

- [ ] **Step 4: Run test to verify it passes**
  Run: `pytest tests/test_email_contacts.py -q`
  Expected: PASS (3 passed).

- [ ] **Step 5: Commit**
  `git add email_contacts.py tests/test_email_contacts.py && git commit -m "Task 12: DB-backed church-scoped contacts, remove DEFAULT_CONTACTS"`

---

Read complete. I have the SPEC (`docs/superpowers/specs/2026-07-22-multi-user-app-design.md`) and the current `google_oauth.py`; the LOCKED INTERFACES are the signature block in my instructions. Here are Tasks 13–16.

### Task 13: Identity core — `auth.py`

**Files:**
- Create: `auth.py`
- Test: `tests/test_auth.py`
- Modify: none (uses existing `tests/conftest.py` fixtures; do **not** re-create it)

**Interfaces:**
- Consumes (earlier tasks): `db.session_scope()` contextmanager; `db.models.User` (columns `id: UUID pk`, `email` unique/normalized-lowercase, `google_sub` unique, `name`, `picture`, `created_at`, `last_login_at`); conftest fixture `tmp_db`.
- Produces (later tasks rely on): `auth.upsert_from_claims(claims: dict) -> uuid.UUID`; `auth.require_login() -> dict` = `{"user_id": UUID, "email": str, "name": str, "picture": str}`; `auth.current_user_id() -> uuid.UUID | None`; `auth.do_logout() -> None`.
- **Streamlit boundary:** `require_login` / `current_user_id` / `do_logout` touch `st.user` / `st.login` / `st.logout` and are thin shells. The testable core is the pure `upsert_from_claims(claims: dict)`, which is what the tests exercise.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_auth.py
import uuid

import pytest
from sqlalchemy import func, select

import auth
from db import session_scope
from db.models import User


def _claims(email="Pastor@Example.com", sub="google-sub-1",
            name="Pat Tor", picture="http://x/p.png"):
    return {"email": email, "sub": sub, "name": name, "picture": picture}


def test_upsert_creates_user_with_normalized_email(tmp_db):
    uid = auth.upsert_from_claims(_claims())
    assert isinstance(uid, uuid.UUID)
    with session_scope() as s:
        user = s.execute(select(User).where(User.id == uid)).scalar_one()
        assert user.email == "pastor@example.com"      # lower-cased
        assert user.google_sub == "google-sub-1"
        assert user.name == "Pat Tor"
        assert user.last_login_at is not None


def test_upsert_is_idempotent_by_normalized_email(tmp_db):
    first = auth.upsert_from_claims(_claims(email="Pastor@Example.com"))
    second = auth.upsert_from_claims(
        _claims(email="pastor@example.com", name="New Name", picture="http://x/q.png")
    )
    assert first == second                              # same row, not a duplicate
    with session_scope() as s:
        count = s.execute(select(func.count()).select_from(User)).scalar_one()
        assert count == 1
        user = s.execute(select(User).where(User.id == first)).scalar_one()
        assert user.name == "New Name"                  # updated in place
        assert user.picture == "http://x/q.png"


def test_upsert_requires_email(tmp_db):
    with pytest.raises(ValueError):
        auth.upsert_from_claims({"email": "  ", "sub": "x"})
```

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/test_auth.py -q`
  Expected: FAIL with `ModuleNotFoundError: No module named 'auth'` (the module does not exist yet).

- [ ] **Step 3: Write the implementation**

```python
# auth.py
"""Identity/auth helpers built on Streamlit's native OIDC (st.user / st.login).

The Streamlit surface (require_login / current_user_id / do_logout) is a thin
shell around one pure, unit-tested function: upsert_from_claims, which turns a
plain dict of OIDC claims into a persisted users row and returns its id. Users
are keyed on the normalized (lower-cased) email; google_sub is a stable
secondary identifier.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

import streamlit as st
from sqlalchemy import select

from db import session_scope
from db.models import User


def _normalize_email(email: Optional[str]) -> str:
    return (email or "").strip().lower()


def upsert_from_claims(claims: dict) -> uuid.UUID:
    """Create or update the users row for a set of OIDC claims; return its id.

    Pure w.r.t. Streamlit: accepts a plain dict (email, sub, name, picture) so it
    is unit-testable with no running Streamlit session. Idempotent on the
    normalized email.
    """
    email = _normalize_email(claims.get("email"))
    if not email:
        raise ValueError("OIDC claims are missing an email address.")
    sub = (claims.get("sub") or "").strip() or None
    name = (claims.get("name") or "").strip() or None
    picture = (claims.get("picture") or "").strip() or None
    now = datetime.now(timezone.utc)

    with session_scope() as session:
        user = session.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()
        if user is None:
            user = User(
                email=email,
                google_sub=sub,
                name=name,
                picture=picture,
                last_login_at=now,
            )
            session.add(user)
            session.flush()          # populate python-side default id
        else:
            if sub:
                user.google_sub = sub
            if name:
                user.name = name
            if picture:
                user.picture = picture
            user.last_login_at = now
        return user.id               # captured before session_scope commits


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
    """Clear the app's local identity cookie (Streamlit native logout)."""
    st.logout()
```

- [ ] **Step 4: Run test to verify it passes**
  Run: `pytest tests/test_auth.py -q`
  Expected: PASS (3 passed).

- [ ] **Step 5: Commit**
  `git add auth.py tests/test_auth.py && git commit -m "Add auth.py: Google OIDC identity (upsert_from_claims + require_login)"`

---

### Task 14: User-scoped Gmail token store — `GmailToken` table

**Files:**
- Modify: `google_oauth.py` (replace JSON token store; user-key `_access_token_for`; wire `exchange_code`/`send_email` to it)
- Test: `tests/test_gmail_token_store.py`
- Modify: none in `tests/conftest.py`

**Interfaces:**
- Consumes: `db.session_scope`; `db.models.User`; `db.models.GmailToken` (already defined in Task 3 — pk `user_id`, `refresh_token` not-null, `google_email`, `created_at`); `auth.upsert_from_claims(claims) -> uuid.UUID` (Task 13); conftest `make_user(...) -> uuid.UUID`.
- Produces: `google_oauth.save_user_token(user_id, google_email, refresh_token) -> None`; `google_oauth.is_connected(user_id) -> bool`; `google_oauth.disconnect(user_id) -> None`; `google_oauth._access_token_for(user_id) -> str`; `google_oauth.send_email(user_id, ...)` (sender derived from the row). Note: `exchange_code(code)` stays transitional here — Task 16 adds `expected_user_id` + the mismatch rejection.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_gmail_token_store.py
import uuid

import pytest

import google_oauth
from db import session_scope
from db.models import GmailToken


class _FakeResp:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self._payload = payload or {}
        self.text = ""

    def json(self):
        return self._payload


def test_save_and_is_connected(tmp_db, make_user):
    uid = make_user(email="a@example.com")
    assert google_oauth.is_connected(uid) is False
    google_oauth.save_user_token(uid, "a@example.com", "refresh-abc")
    assert google_oauth.is_connected(uid) is True
    with session_scope() as s:
        row = s.get(GmailToken, uid)
        assert row.refresh_token == "refresh-abc"
        assert row.google_email == "a@example.com"


def test_save_replaces_single_row(tmp_db, make_user):
    uid = make_user(email="a@example.com")
    google_oauth.save_user_token(uid, "a@example.com", "refresh-1")
    google_oauth.save_user_token(uid, "a@example.com", "refresh-2")
    with session_scope() as s:
        rows = s.query(GmailToken).filter(GmailToken.user_id == uid).all()
        assert len(rows) == 1
        assert rows[0].refresh_token == "refresh-2"


def test_disconnect(tmp_db, make_user):
    uid = make_user(email="a@example.com")
    google_oauth.save_user_token(uid, "a@example.com", "refresh-abc")
    google_oauth.disconnect(uid)
    assert google_oauth.is_connected(uid) is False


def test_access_token_for_unconnected_raises(tmp_db, make_user):
    uid = make_user(email="a@example.com")
    with pytest.raises(RuntimeError):
        google_oauth._access_token_for(uid)


def test_access_token_for_returns_fresh_token(tmp_db, make_user, monkeypatch):
    uid = make_user(email="a@example.com")
    google_oauth.save_user_token(uid, "a@example.com", "refresh-abc")
    monkeypatch.setattr(
        google_oauth.requests, "post",
        lambda *a, **k: _FakeResp(200, {"access_token": "fresh-xyz"}),
    )
    assert google_oauth._access_token_for(uid) == "fresh-xyz"


def test_access_token_for_revoked_grant_disconnects(tmp_db, make_user, monkeypatch):
    uid = make_user(email="a@example.com")
    google_oauth.save_user_token(uid, "a@example.com", "refresh-abc")
    monkeypatch.setattr(
        google_oauth.requests, "post",
        lambda *a, **k: _FakeResp(400, {"error": "invalid_grant"}),
    )
    with pytest.raises(RuntimeError):
        google_oauth._access_token_for(uid)
    assert google_oauth.is_connected(uid) is False   # revoked grant is dropped
```

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/test_gmail_token_store.py -q`
  Expected: FAIL — `GmailToken` already exists (from Task 3), but `google_oauth`'s token store is still the old email-keyed JSON store, so the user-id-keyed `save_user_token(uid, ...)` / `is_connected(uid)` / `_access_token_for(uid)` calls hit the wrong signatures/behavior (TypeError or wrong result).

- [ ] **Step 3: Write the implementation**

**3a. `google_oauth.py` — Edit 1: imports.** Replace:

```python
import base64
import json
import os
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional, Union
from urllib.parse import urlencode

import requests
```

with:

```python
import base64
import os
import uuid
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional, Union
from urllib.parse import urlencode

import requests
from sqlalchemy import select

import auth
from db import session_scope
from db.models import GmailToken
```

**Edit 2: drop the JSON-file constants.** Replace:

```python
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
TOKENS_FILE = os.path.join(DATA_DIR, "gmail_tokens.json")

_TIMEOUT = 30
```

with:

```python
_TIMEOUT = 30
```

**Edit 3: replace the entire JSON token-store section** (from the `# Token store ...` banner through `disconnect`, i.e. `_load_tokens`, `_save_tokens`, `list_connected`, `is_connected`, `save_user_token`, `disconnect`) with the user-scoped store:

```python
# --------------------------------------------------------------------------- #
# Token store (gmail_tokens table, keyed by user_id — user-scoped, not church)
# --------------------------------------------------------------------------- #
def is_connected(user_id: uuid.UUID) -> bool:
    """True when the user has a stored Gmail refresh token."""
    with session_scope() as session:
        row = session.get(GmailToken, user_id)
        return bool(row and row.refresh_token)


def save_user_token(user_id: uuid.UUID, google_email: str, refresh_token: str) -> None:
    """Persist (or replace) a user's Gmail refresh token; one row per user."""
    with session_scope() as session:
        row = session.get(GmailToken, user_id)
        if row is None:
            session.add(
                GmailToken(
                    user_id=user_id,
                    google_email=google_email,
                    refresh_token=refresh_token,
                )
            )
        else:
            row.google_email = google_email
            row.refresh_token = refresh_token


def disconnect(user_id: uuid.UUID) -> None:
    """Forget a user's stored Gmail credentials."""
    with session_scope() as session:
        row = session.get(GmailToken, user_id)
        if row is not None:
            session.delete(row)
```

**Edit 4: replace `_access_token_for`.** Replace:

```python
def _access_token_for(email: str) -> str:
    """Get a fresh access token for a connected user via their refresh token."""
    refresh_token = _load_tokens().get(email, {}).get("refresh_token")
    if not refresh_token:
        raise RuntimeError(f"{email} is not connected. Connect the Gmail account first.")
    resp = requests.post(
        TOKEN_URI,
        data={
            "client_id": _client_id(),
            "client_secret": _client_secret(),
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=_TIMEOUT,
    )
    if not resp.ok:
        # A revoked or expired grant lands here; drop it so the UI re-prompts.
        if resp.status_code in (400, 401):
            disconnect(email)
        raise RuntimeError(
            _google_error(resp)
            + " You may need to reconnect your Gmail account."
        )
    token = resp.json().get("access_token")
    if not token:
        raise RuntimeError("Google did not return a fresh access token.")
    return token
```

with:

```python
def _access_token_for(user_id: uuid.UUID) -> str:
    """Get a fresh access token for a connected user via their refresh token."""
    with session_scope() as session:
        row = session.get(GmailToken, user_id)
        refresh_token = row.refresh_token if row else None
    if not refresh_token:
        raise RuntimeError("This account is not connected. Connect Gmail first.")
    resp = requests.post(
        TOKEN_URI,
        data={
            "client_id": _client_id(),
            "client_secret": _client_secret(),
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=_TIMEOUT,
    )
    if not resp.ok:
        # A revoked or expired grant lands here; drop it so the UI re-prompts.
        if resp.status_code in (400, 401):
            disconnect(user_id)
        raise RuntimeError(
            _google_error(resp) + " You may need to reconnect your Gmail account."
        )
    token = resp.json().get("access_token")
    if not token:
        raise RuntimeError("Google did not return a fresh access token.")
    return token
```

**Edit 5: keep `exchange_code(code)` coherent with the user-keyed store (transitional).** Replace its persistence tail:

```python
    email = _fetch_email(access_token)
    if not email:
        raise RuntimeError("Could not read your email address from Google.")

    if refresh_token:
        save_user_token(email, refresh_token)
    elif not is_connected(email):
        # No refresh token now and none stored before: Google only returns one
        # on first consent. prompt=consent should prevent this, but guard anyway.
        raise RuntimeError(
            "Google did not return a refresh token. Remove this app's access at "
            "https://myaccount.google.com/permissions and connect again."
        )
    return {"email": email, "refresh_token": refresh_token}
```

with:

```python
    email = _fetch_email(access_token)
    if not email:
        raise RuntimeError("Could not read your email address from Google.")

    # Transitional: bind the token to a user row. Task 16 replaces this with an
    # explicit expected_user_id + email-match check (the §4 security fix).
    user_id = auth.upsert_from_claims({"email": email})
    if refresh_token:
        save_user_token(user_id, email, refresh_token)
    elif not is_connected(user_id):
        raise RuntimeError(
            "Google did not return a refresh token. Remove this app's access at "
            "https://myaccount.google.com/permissions and connect again."
        )
    return {"user_id": user_id, "email": email, "refresh_token": refresh_token}
```

**Edit 6: `send_email` now takes `user_id` and derives the sender from the stored row** (a caller-supplied address can never be the sender). Replace the whole `send_email` function:

```python
def send_email(
    sender_email: str,
    to_email: Union[str, List[str]],
    subject: str,
    body_plain: str,
    *,
    attachment_bytes: Optional[bytes] = None,
    attachment_filename: Optional[str] = None,
) -> Optional[str]:
    """
    Send an email as ``sender_email`` via the Gmail API using that user's
    connected credentials. Returns None on success, or an error string.
    """
    if not is_configured():
        return (
            "Google sign-in isn't configured. Set GOOGLE_CLIENT_ID, "
            "GOOGLE_CLIENT_SECRET and GOOGLE_OAUTH_REDIRECT_URI."
        )

    if isinstance(to_email, list):
        recipients = [e.strip() for e in to_email if (e or "").strip()]
    else:
        recipients = [e.strip() for e in (to_email or "").split(",") if e.strip()]
    if not recipients:
        return "Recipient email is required."

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.attach(MIMEText(body_plain, "plain"))

    if attachment_bytes and attachment_filename:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment_bytes)
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition", "attachment", filename=attachment_filename
        )
        msg.attach(part)

    try:
        access_token = _access_token_for(sender_email)
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        resp = requests.post(
            GMAIL_SEND_URI,
            headers={"Authorization": f"Bearer {access_token}"},
            json={"raw": raw},
            timeout=_TIMEOUT,
        )
        if not resp.ok:
            return _google_error(resp)
        return None
    except Exception as e:  # noqa: BLE001 - surface any failure to the UI
        return str(e)
```

with:

```python
def send_email(
    user_id: uuid.UUID,
    to_email: Union[str, List[str]],
    subject: str,
    body_plain: str,
    *,
    attachment_bytes: Optional[bytes] = None,
    attachment_filename: Optional[str] = None,
) -> Optional[str]:
    """
    Send an email as the user's connected Gmail via the Gmail API. Returns None
    on success, or an error string.

    The sender ("From") is taken solely from the user's stored GmailToken row —
    never from a caller-supplied address — so nobody can send as an account they
    have not connected (fixes the §4 sender-spoofing bug).
    """
    if not is_configured():
        return (
            "Google sign-in isn't configured. Set GOOGLE_CLIENT_ID, "
            "GOOGLE_CLIENT_SECRET and GOOGLE_OAUTH_REDIRECT_URI."
        )

    with session_scope() as session:
        row = session.get(GmailToken, user_id)
        sender_email = row.google_email if row else None
        has_token = bool(row and row.refresh_token)
    if not has_token or not sender_email:
        return "Your account isn't connected to Gmail. Connect your Gmail first."

    if isinstance(to_email, list):
        recipients = [e.strip() for e in to_email if (e or "").strip()]
    else:
        recipients = [e.strip() for e in (to_email or "").split(",") if e.strip()]
    if not recipients:
        return "Recipient email is required."

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.attach(MIMEText(body_plain, "plain"))

    if attachment_bytes and attachment_filename:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment_bytes)
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition", "attachment", filename=attachment_filename
        )
        msg.attach(part)

    try:
        access_token = _access_token_for(user_id)
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        resp = requests.post(
            GMAIL_SEND_URI,
            headers={"Authorization": f"Bearer {access_token}"},
            json={"raw": raw},
            timeout=_TIMEOUT,
        )
        if not resp.ok:
            return _google_error(resp)
        return None
    except Exception as e:  # noqa: BLE001 - surface any failure to the UI
        return str(e)
```

- [ ] **Step 4: Run test to verify it passes**
  Run: `pytest tests/test_gmail_token_store.py -q`
  Expected: PASS (6 passed).

- [ ] **Step 5: Commit**
  `git add google_oauth.py tests/test_gmail_token_store.py && git commit -m "Move Gmail token store to user-scoped GmailToken table"`

---

### Task 15: OAuth CSRF state (`OAuthState`) + callback marker

**Files:**
- Modify: `google_oauth.py` (`create_state`, `consume_state`, `should_handle_gmail_callback`, `_redirect_uri_with_marker`, marker in `build_auth_url`)
- Test: `tests/test_oauth_state.py`
- Modify: none in `tests/conftest.py`

**Interfaces:**
- Consumes: `db.session_scope`; `db.models.OAuthState` (already defined in Task 3 — pk `state`, `user_id` fk, `created_at`, `expires_at`); conftest `make_user(...) -> uuid.UUID`; `google_oauth.SCOPES`, `AUTH_URI`, `_client_id/_client_secret/_redirect_uri` (existing).
- Produces: `google_oauth.create_state(user_id) -> str`; `google_oauth.consume_state(state) -> uuid.UUID | None` (single-use + TTL); `google_oauth.should_handle_gmail_callback(query_params, is_logged_in) -> bool` (pure); `google_oauth.GMAIL_OAUTH_MARKER = "gmail_oauth"`; `google_oauth._redirect_uri_with_marker() -> str`; `build_auth_url(state)` now redirects to app-root **plus** the marker.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_oauth_state.py
from datetime import datetime, timedelta, timezone

import pytest

import google_oauth
from db import session_scope
from db.models import OAuthState


def test_create_state_persists_row(tmp_db, make_user):
    uid = make_user(email="a@example.com")
    state = google_oauth.create_state(uid)
    assert isinstance(state, str) and len(state) >= 20
    with session_scope() as s:
        row = s.get(OAuthState, state)
        assert row is not None
        assert row.user_id == uid


def test_consume_state_is_single_use(tmp_db, make_user):
    uid = make_user(email="a@example.com")
    state = google_oauth.create_state(uid)
    assert google_oauth.consume_state(state) == uid
    assert google_oauth.consume_state(state) is None      # already consumed
    with session_scope() as s:
        assert s.get(OAuthState, state) is None            # row deleted


def test_consume_unknown_or_empty_state_returns_none(tmp_db):
    assert google_oauth.consume_state("nope") is None
    assert google_oauth.consume_state("") is None


def test_consume_expired_state_returns_none_and_deletes(tmp_db, make_user):
    uid = make_user(email="a@example.com")
    state = google_oauth.create_state(uid)
    with session_scope() as s:
        s.get(OAuthState, state).expires_at = (
            datetime.now(timezone.utc) - timedelta(minutes=1)
        )
    assert google_oauth.consume_state(state) is None
    with session_scope() as s:
        assert s.get(OAuthState, state) is None            # consumed even if expired


@pytest.mark.parametrize(
    "params,is_logged_in,expected",
    [
        ({"gmail_oauth": "1", "code": "abc"}, True, True),
        ({"code": "abc"}, True, False),                     # no marker -> st.login's
        ({"gmail_oauth": "1"}, True, False),                # no code
        ({"gmail_oauth": "1", "code": "abc"}, False, False),  # not logged in
        ({}, True, False),
    ],
)
def test_should_handle_gmail_callback(params, is_logged_in, expected):
    assert google_oauth.should_handle_gmail_callback(params, is_logged_in) is expected


def test_build_auth_url_carries_marker_and_state(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")
    monkeypatch.setenv("GOOGLE_OAUTH_REDIRECT_URI", "https://app.example/")
    url = google_oauth.build_auth_url("state-token-123")
    assert "gmail_oauth%3D1" in url          # marker rides inside redirect_uri (url-encoded)
    assert "state=state-token-123" in url
```

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/test_oauth_state.py -q`
  Expected: FAIL — `OAuthState` already exists (from Task 3), but `google_oauth.create_state`/`consume_state`/`should_handle_gmail_callback` are undefined, so the tests error at call time (`AttributeError`).

- [ ] **Step 3: Write the implementation**

**3a. `google_oauth.py` — Edit 1: imports.** Add `import secrets`, the datetime import, and `OAuthState`. Replace:

```python
import base64
import os
import uuid
from email import encoders
```

with:

```python
import base64
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from email import encoders
```

and replace:

```python
from db.models import GmailToken
```

with:

```python
from db.models import GmailToken, OAuthState
```

**Edit 2: add module constants.** Replace:

```python
_TIMEOUT = 30
```

with:

```python
_TIMEOUT = 30

# Marker appended to the manual gmail.send redirect (app root) so its ?code=
# is distinguishable from Streamlit's internal /oauth2callback (§1).
GMAIL_OAUTH_MARKER = "gmail_oauth"
# Short TTL for a single-use CSRF state.
STATE_TTL = timedelta(minutes=10)
```

**Edit 3: add the marker helper** next to `_redirect_uri` (insert immediately after the `_redirect_uri()` function):

```python
def _redirect_uri_with_marker() -> str:
    """The app-root redirect_uri plus the gmail_oauth marker query param."""
    base = _redirect_uri()
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}{GMAIL_OAUTH_MARKER}=1"
```

**Edit 4: put the marker into `build_auth_url` and drop `include_granted_scopes`** (§4). Replace:

```python
def build_auth_url(state: str) -> str:
    """URL to send the user to Google's consent screen."""
    params = {
        "client_id": _client_id(),
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",       # request a refresh token
        "prompt": "consent",            # ensure a refresh token is returned
        "include_granted_scopes": "true",
        "state": state,
    }
    return f"{AUTH_URI}?{urlencode(params)}"
```

with:

```python
def build_auth_url(state: str) -> str:
    """URL to send the user to Google's consent screen for the gmail.send grant.

    The redirect target is the app root plus the gmail_oauth marker so the return
    trip is distinguishable from Streamlit's internal /oauth2callback handler and
    is only processed by should_handle_gmail_callback().
    """
    params = {
        "client_id": _client_id(),
        "redirect_uri": _redirect_uri_with_marker(),
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",       # request a refresh token
        "prompt": "consent",            # ensure a refresh token is returned
        "state": state,
    }
    return f"{AUTH_URI}?{urlencode(params)}"


def create_state(user_id: uuid.UUID) -> str:
    """Create a single-use CSRF state bound to the user; return the opaque token."""
    state = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    with session_scope() as session:
        session.add(
            OAuthState(
                state=state,
                user_id=user_id,
                created_at=now,
                expires_at=now + STATE_TTL,
            )
        )
    return state


def consume_state(state: str) -> Optional[uuid.UUID]:
    """Validate and consume a CSRF state; return the bound user_id on success.

    Single-use: the row is deleted whenever found (valid *or* expired). Returns
    None for missing / expired / already-used states — never raises, and a
    missing state is never treated as a pass (§4).
    """
    if not state:
        return None
    with session_scope() as session:
        row = session.get(OAuthState, state)
        if row is None:
            return None
        user_id = row.user_id
        expires_at = row.expires_at
        session.delete(row)  # consumed regardless of validity
    if expires_at is None:
        return None
    if expires_at.tzinfo is None:            # SQLite may hand back naive datetimes
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None
    return user_id


def should_handle_gmail_callback(query_params, is_logged_in: bool) -> bool:
    """Whether a ?code= belongs to the manual gmail.send flow (vs. st.login).

    Pure/testable. True only when the gmail marker is present, an auth code is
    present, and a login session already exists — keeping Streamlit's internal
    handler from grabbing the manual code and enforcing "never exchange a token
    before authentication" (§4).
    """
    if not is_logged_in or not query_params:
        return False
    has_marker = str(query_params.get(GMAIL_OAUTH_MARKER, "")) in ("1", "true", "True")
    has_code = bool(query_params.get("code"))
    return has_marker and has_code
```

- [ ] **Step 4: Run test to verify it passes**
  Run: `pytest tests/test_oauth_state.py -q`
  Expected: PASS (10 passed — 5 parametrized cases + 5 others).

- [ ] **Step 5: Commit**
  `git add google_oauth.py tests/test_oauth_state.py && git commit -m "Enforce OAuth CSRF state via single-use OAuthState + callback marker"`

---

### Task 16: Token exchange bound to the signed-in user (`exchange_code(code, expected_user_id)`)

**Files:**
- Modify: `google_oauth.py` (`exchange_code` gains `expected_user_id` + email-match rejection; add `_user_email`; drop the transitional `auth` upsert)
- Test: `tests/test_gmail_exchange.py`
- Modify: none in `tests/conftest.py`

**Interfaces:**
- Consumes: `google_oauth.save_user_token/is_connected/_access_token_for/send_email` (Task 14); `google_oauth._fetch_email`, `TOKEN_URI`, `_redirect_uri_with_marker` (Task 15); `db.models.User`; conftest `make_user(...) -> uuid.UUID`.
- Produces: `google_oauth.exchange_code(code, expected_user_id) -> dict` = `{"user_id": UUID, "email": str, "refresh_token": str|None}` — raises `RuntimeError` unless the Google-returned email equals the signed-in user's email. `send_email(user_id, ...)` sender-integrity is verified here. `SCOPES` remains `openid` + `userinfo.email` + `gmail.send`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_gmail_exchange.py
import uuid

import pytest

import google_oauth


class _FakeResp:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self._payload = payload or {}
        self.text = ""

    def json(self):
        return self._payload


def test_scopes_unchanged():
    assert google_oauth.SCOPES == [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/gmail.send",
    ]


def test_exchange_code_rejects_email_mismatch(tmp_db, make_user, monkeypatch):
    uid = make_user(email="owner@example.com")
    monkeypatch.setattr(
        google_oauth.requests, "post",
        lambda *a, **k: _FakeResp(200, {"access_token": "at", "refresh_token": "rt"}),
    )
    # Google says the authorizing account is someone else -> must be rejected.
    monkeypatch.setattr(google_oauth, "_fetch_email", lambda token: "attacker@example.com")
    with pytest.raises(RuntimeError):
        google_oauth.exchange_code("auth-code", expected_user_id=uid)
    assert google_oauth.is_connected(uid) is False        # nothing saved on mismatch


def test_exchange_code_saves_on_match_case_insensitive(tmp_db, make_user, monkeypatch):
    uid = make_user(email="owner@example.com")
    monkeypatch.setattr(
        google_oauth.requests, "post",
        lambda *a, **k: _FakeResp(200, {"access_token": "at", "refresh_token": "rt"}),
    )
    monkeypatch.setattr(google_oauth, "_fetch_email", lambda token: "Owner@Example.com")
    result = google_oauth.exchange_code("auth-code", expected_user_id=uid)
    assert result["user_id"] == uid
    assert result["email"] == "Owner@Example.com"
    assert google_oauth.is_connected(uid) is True


def test_exchange_code_unknown_user_rejected(tmp_db, monkeypatch):
    monkeypatch.setattr(
        google_oauth.requests, "post",
        lambda *a, **k: _FakeResp(200, {"access_token": "at", "refresh_token": "rt"}),
    )
    with pytest.raises(RuntimeError):
        google_oauth.exchange_code("auth-code", expected_user_id=uuid.uuid4())


def test_send_email_refuses_when_user_not_connected(tmp_db, make_user, monkeypatch):
    uid = make_user(email="nogmail@example.com")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")
    monkeypatch.setenv("GOOGLE_OAUTH_REDIRECT_URI", "https://app.example/")
    err = google_oauth.send_email(uid, "to@example.com", "Subject", "Body")
    assert err is not None
    assert "connect" in err.lower()                        # no token -> cannot send
```

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/test_gmail_exchange.py -q`
  Expected: FAIL — `test_exchange_code_rejects_email_mismatch` errors with `TypeError: exchange_code() got an unexpected keyword argument 'expected_user_id'` (the Task 14 signature is `exchange_code(code)` and performs no email match).

- [ ] **Step 3: Write the implementation**

**`google_oauth.py` — Edit 1: imports.** The transitional upsert is gone; look up the user directly. Replace:

```python
import auth
from db import session_scope
from db.models import GmailToken, OAuthState
```

with:

```python
from db import session_scope
from db.models import GmailToken, OAuthState, User
```

**Edit 2: add the user-email lookup helper** (insert immediately after `_redirect_uri_with_marker`):

```python
def _user_email(user_id: uuid.UUID) -> Optional[str]:
    """The stored (normalized) email for a user id, or None if unknown."""
    with session_scope() as session:
        user = session.get(User, user_id)
        return user.email if user else None
```

**Edit 3: rewrite `exchange_code`** to require `expected_user_id` and reject a Google email that isn't the signed-in user's (§4). Replace the whole function (the Task 14 transitional version) with:

```python
def exchange_code(code: str, expected_user_id: uuid.UUID) -> dict:
    """Exchange an authorization code for tokens and store them for the signed-in
    user only.

    Security (§4): the refresh token is saved *only if* the Google account that
    authorized equals the signed-in user's email. A mismatch raises RuntimeError
    and stores nothing, so a user can never connect (or later send as) an account
    that isn't theirs. Returns {"user_id": UUID, "email": str, "refresh_token": str|None}.
    """
    expected_email = _user_email(expected_user_id)
    if not expected_email:
        raise RuntimeError("Sign in before connecting a Gmail account.")

    resp = requests.post(
        TOKEN_URI,
        data={
            "code": code,
            "client_id": _client_id(),
            "client_secret": _client_secret(),
            "redirect_uri": _redirect_uri_with_marker(),
            "grant_type": "authorization_code",
        },
        timeout=_TIMEOUT,
    )
    if not resp.ok:
        raise RuntimeError(_google_error(resp))
    payload = resp.json()
    access_token = payload.get("access_token")
    refresh_token = payload.get("refresh_token")
    if not access_token:
        raise RuntimeError("Google did not return an access token.")

    google_email = _fetch_email(access_token)
    if not google_email:
        raise RuntimeError("Could not read your email address from Google.")

    if google_email.strip().lower() != expected_email.strip().lower():
        raise RuntimeError(
            "That Google account doesn't match your signed-in email. "
            "Connect the Gmail account you're logged in with."
        )

    if refresh_token:
        save_user_token(expected_user_id, google_email, refresh_token)
    elif not is_connected(expected_user_id):
        raise RuntimeError(
            "Google did not return a refresh token. Remove this app's access at "
            "https://myaccount.google.com/permissions and connect again."
        )
    return {
        "user_id": expected_user_id,
        "email": google_email,
        "refresh_token": refresh_token,
    }
```

`send_email(user_id, ...)` already derives its sender solely from the stored `GmailToken` row (Task 14) and returns a refusal when the user has no token — `test_send_email_refuses_when_user_not_connected` locks that behavior in; no further change to `send_email` is needed.

- [ ] **Step 4: Run test to verify it passes**
  Run: `pytest tests/test_gmail_exchange.py -q && pytest tests/test_auth.py tests/test_gmail_token_store.py tests/test_oauth_state.py -q`
  Expected: PASS (5 passed for this file; the earlier auth/token/state suites remain green).

- [ ] **Step 5: Commit**
  `git add google_oauth.py tests/test_gmail_exchange.py && git commit -m "Reject Gmail token exchange when Google email != signed-in user"`

---

I have everything I need: the spec, the current `app.py`, `google_oauth.py`, the hymn schema (Notion keys: `Hymn Title`, `Hymn Number`, `Hymnary.org Link`, `Scripture References`, `Theme`), and all locked signatures. Here is the plan for Tasks 17–21.

### Task 17: `app.py` restructure (init_db, query-param capture, gated Gmail callback, login/active-church guards, two-page navigation, church-scoped Service Builder)
**Files:**
- Modify: `/Users/beaubrown/Desktop/projects/church/app.py`
- Create: `/Users/beaubrown/Desktop/projects/church/ui_helpers.py` (Streamlit-free pure helpers)
- Create: `/Users/beaubrown/Desktop/projects/church/pages/__init__.py`
- Create: `/Users/beaubrown/Desktop/projects/church/pages/settings.py` (stub: `NotAuthorizedError` + `render_settings_page`; filled in Tasks 20–21)
- Test: `/Users/beaubrown/Desktop/projects/church/tests/test_app_helpers.py`

**Interfaces:**
- Consumes: `db.init_db()`; `auth.require_login() -> dict{"user_id":UUID,"email","name","picture"}`; `tenancy.require_active_church(user_id) -> dict|None{"church_id","name","role"}`; `google_oauth.should_handle_gmail_callback(query_params, is_logged_in)->bool`, `exchange_code(code, expected_user_id)`, `consume_state(state)->UUID|None`, `create_state(user_id)->str`, `is_connected(user_id)->bool`, `send_email(user_id, to_email, subject, body_plain, *, attachment_bytes=None, attachment_filename=None)`; `repos.hymns.list_hymns(church_id)->list[dict]` (flat Notion keys); `repos.churches.list_user_churches(user_id)->list[dict{id,name,role}]`; `service_archive.list_saved_services(church_id)`, `save_service(*, church_id, created_by, service_date, service_date_iso, occasion, scriptures, hymns, liturgy, sermon_title, selected_ot_ref, selected_nt_ref, include_communion)->dict`, `update_service(service_id, church_id, *, ...)->dict|None`, `get_service(service_id, church_id)->dict|None`; `hymn_usage.record_usage(church_id, service_date, hymns)`, `get_recently_used_identifiers(church_id, weeks=12)`, `is_hymn_recently_used(number, title, recent)`; `email_contacts.list_contacts(church_id)`.
- Produces: `ui_helpers.capture_query_params(query_params, session)`, `clear_oauth_query_params(query_params)`, `hymn_display_from_flat(row)->dict{title,number,link}`, `build_title_to_info(hymns)->dict{normtitle:info}`; `app.render_service_builder(user, active)`; `pages.settings.render_settings_page(user, active)`, `pages.settings.NotAuthorizedError`.

- [ ] **Step 1: Write the failing test** — `tests/test_app_helpers.py`
```python
import pytest
from ui_helpers import (
    capture_query_params,
    clear_oauth_query_params,
    hymn_display_from_flat,
    build_title_to_info,
)


def test_capture_query_params_copies_invite_and_church():
    session = {}
    qp = {"invite": "ABC123", "church": "11111111-1111-1111-1111-111111111111"}
    capture_query_params(qp, session)
    assert session["pending_invite_code"] == "ABC123"
    assert session["active_church_id"] == "11111111-1111-1111-1111-111111111111"


def test_capture_query_params_ignores_missing_and_keeps_prior():
    session = {"pending_invite_code": "OLD"}
    capture_query_params({}, session)
    assert session["pending_invite_code"] == "OLD"
    assert "active_church_id" not in session


def test_clear_oauth_query_params_is_targeted_not_blanket():
    qp = {"code": "x", "state": "y", "scope": "z", "invite": "KEEP", "church": "KEEP2"}
    clear_oauth_query_params(qp)
    assert "code" not in qp and "state" not in qp and "scope" not in qp
    # invite/church survive the OAuth round-trip (spec §4 query-param hygiene)
    assert qp["invite"] == "KEEP"
    assert qp["church"] == "KEEP2"


def test_hymn_display_from_flat_maps_notion_keys_and_trims():
    row = {"id": "h1", "Hymn Title": "  Amazing Grace ", "Hymn Number": 378,
           "Hymnary.org Link": "https://hymnary.org/x"}
    assert hymn_display_from_flat(row) == {
        "title": "Amazing Grace", "number": 378, "link": "https://hymnary.org/x"}


def test_build_title_to_info_lowercases_skips_blank_and_handles_empty():
    rows = [
        {"id": "1", "Hymn Title": "Holy, Holy, Holy", "Hymn Number": 1, "Hymnary.org Link": None},
        {"id": "2", "Hymn Title": "", "Hymn Number": None, "Hymnary.org Link": None},
    ]
    m = build_title_to_info(rows)
    assert set(m.keys()) == {"holy, holy, holy"}
    assert m["holy, holy, holy"]["number"] == 1
    # empty hymnal -> empty map: this is what drives the explicit empty-hymnal message
    assert build_title_to_info([]) == {}
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/test_app_helpers.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'ui_helpers'`.

- [ ] **Step 3: Write the implementation**

**3a — Create `ui_helpers.py` (pure, no Streamlit import):**
```python
"""Pure, Streamlit-free helpers so page logic is importable and unit-testable."""
from __future__ import annotations

# OAuth callback query keys we strip AFTER handling. Never a blanket
# st.query_params.clear() — that would drop ?invite=/?church= mid round-trip
# (spec §4 query-param hygiene).
OAUTH_QUERY_KEYS = ("code", "state", "scope", "authuser", "hd", "prompt", "gmail_oauth")


def capture_query_params(query_params, session) -> None:
    """Copy untrusted ?invite=/?church= into session. Runs on main()'s FIRST line
    so the values survive the login and Gmail OAuth redirects."""
    invite = query_params.get("invite")
    if invite:
        session["pending_invite_code"] = invite
    church = query_params.get("church")
    if church:
        session["active_church_id"] = church


def clear_oauth_query_params(query_params) -> None:
    """Delete ONLY the OAuth callback keys, preserving everything else."""
    for key in OAUTH_QUERY_KEYS:
        if key in query_params:
            del query_params[key]


def hymn_display_from_flat(row: dict) -> dict:
    """Map one flat repos.hymns row (Notion property keys) to the display shape
    used by the hymn selectboxes and the docx builder."""
    title = (row.get("Hymn Title") or "").strip()
    return {
        "title": title or "Unknown",
        "number": row.get("Hymn Number"),
        "link": row.get("Hymnary.org Link"),
    }


def build_title_to_info(hymns: list) -> dict:
    """{normalized-title -> display info} for the church's hymnal. Empty in -> empty
    out, which the Service Builder renders as an explicit empty-hymnal message."""
    out: dict = {}
    for row in hymns:
        title = (row.get("Hymn Title") or "").strip()
        if title:
            out[title.lower()] = hymn_display_from_flat(row)
    return out
```

**3b — `app.py` imports (before/after of lines 14–29):**
```python
# BEFORE
from notion_hymns import NotionHymnsDB
from hymn_utils import get_property_value
from worship_service import (
    hymns_by_scripture,
    hymn_display_info,
    generate_liturgy,
    build_docx,
    suggest_hymns_for_service,
)
from vanderbilt_lectionary import get_readings_for_date_string
from scripture_fetcher import get_passage_text
from hymn_usage import get_recently_used_identifiers, record_usage, is_hymn_recently_used
from service_archive import list_saved_services, save_service, update_service, get_service
from email_send import send_gmail
from email_contacts import get_contacts_for_display
import google_oauth
```
```python
# AFTER
from worship_service import generate_liturgy, build_docx
from vanderbilt_lectionary import get_readings_for_date_string
from scripture_fetcher import get_passage_text
from hymn_usage import get_recently_used_identifiers, record_usage, is_hymn_recently_used
from service_archive import list_saved_services, save_service, update_service, get_service
from email_contacts import list_contacts
from repos.hymns import list_hymns
from repos.churches import list_user_churches
import google_oauth

from db import init_db
from auth import require_login
from tenancy import require_active_church
from ui_helpers import (
    capture_query_params,
    clear_oauth_query_params,
    build_title_to_info,
)
import pages.settings as settings_page
```
(Deletions applied: `NotionHymnsDB`, `get_property_value`, `hymns_by_scripture`/`hymn_display_info`/`suggest_hymns_for_service`, `send_gmail`, `get_contacts_for_display`. The Notion-backed "Find hymns matching scripture" expander and "Suggest hymns (AI)" block are removed in 3d — they depended on the removed Notion runtime dependency; DB-backed replacements are out of scope for this restructure.)

**3c — `app.py` engine init, gated callback, new `main()`, church switcher, onboarding placeholder.** Replace the module-level `get_db()`/`_new_oauth_state()`/`_handle_gmail_oauth_callback()`/`_active_gmail_user()` (old lines 150–210) and the whole `main()` (old lines 241–265, top gate) with:
```python
@st.cache_resource
def _init_db_once():
    """Create the schema once per process (cached resource)."""
    init_db()
    return True


def _handle_gmail_callback(user):
    """Process the manual gmail.send OAuth redirect (?code=&state=). Only reached
    when should_handle_gmail_callback() is True AND the user is logged in."""
    qp = st.query_params
    code = qp.get("code")
    returned_state = qp.get("state")
    # CSRF: state must be present, single-use, and bound to THIS user (spec §4.3).
    state_user = google_oauth.consume_state(returned_state) if returned_state else None
    if state_user is None or str(state_user) != str(user["user_id"]):
        st.session_state.oauth_error = "Sign-in expired or was invalid. Please try again."
        clear_oauth_query_params(qp)
        st.rerun()
        return
    try:
        # Refuses unless the Google-returned email == the logged-in user (spec §4.4).
        google_oauth.exchange_code(code, user["user_id"])
    except Exception as e:  # noqa: BLE001 - surface the reason to the user
        st.session_state.oauth_error = str(e)
    clear_oauth_query_params(qp)
    st.rerun()


def _render_gmail_sidebar(user_id, user_email):
    """Sidebar controls for connecting / disconnecting the caller's own Gmail."""
    with st.sidebar:
        st.divider()
        st.subheader("✉️ Gmail")
        if st.session_state.get("oauth_error"):
            st.error(st.session_state.pop("oauth_error"))
        if not google_oauth.is_configured():
            st.caption("Per-user Gmail sending isn't configured on this deployment.")
            return
        if google_oauth.is_connected(user_id):
            st.success(f"Connected: {user_email}")
            if st.button("Disconnect", key="gmail_disconnect"):
                google_oauth.disconnect(user_id)
                st.rerun()
        else:
            st.caption("Connect Google to send worship emails from your own Gmail.")
            st.link_button(
                "Connect your Gmail",
                google_oauth.build_auth_url(google_oauth.create_state(user_id)),
            )


CHURCH_SCOPED_SESSION_KEYS = (
    "_cached_all_hymns", "_hymn_title_to_info", "_cached_saved_services",
    "scripture_hymns", "scripture_refs_used", "opening", "response", "closing",
    "open_man", "resp_man", "close_man", "editing_service_id", "load_service_id",
    "liturgy", "liturgy_call_to_worship", "liturgy_opening_prayer",
    "liturgy_prayer_of_confession", "liturgy_assurance",
    "liturgy_prayer_for_illumination", "liturgy_prayers_of_the_people",
    "liturgy_offertory_prayer", "liturgy_benediction", "include_communion",
    "custom_elements", "selected_ot_ref", "selected_nt_ref",
)


def _reset_church_scoped_state():
    for k in CHURCH_SCOPED_SESSION_KEYS:
        st.session_state.pop(k, None)


def render_church_switcher(user, active):
    """Sidebar switcher for users in >1 church. Switching resets all church-scoped
    state so a stale previous-church read is impossible (spec §5)."""
    churches = list_user_churches(user["user_id"])
    if len(churches) <= 1:
        return
    with st.sidebar:
        labels = {c["name"]: c["id"] for c in churches}
        current_name = active["name"]
        picked = st.selectbox(
            "Church", list(labels.keys()),
            index=list(labels.keys()).index(current_name) if current_name in labels else 0,
            key="church_switcher",
        )
        if labels[picked] != active["church_id"]:
            _reset_church_scoped_state()
            st.session_state["active_church_id"] = str(labels[picked])
            st.rerun()


def render_onboarding(user):
    # Placeholder; fully implemented in Task 18.
    st.title("Welcome")
    st.info("You don't belong to a church yet. Create one or join by invite.")


def main():
    # 1) FIRST LINE: capture untrusted ?invite=/?church= before any gate/OAuth.
    capture_query_params(st.query_params, st.session_state)

    # 2) Ensure the schema exists (cached, once per process).
    _init_db_once()

    # 3) Identity via Streamlit-native Google OIDC. Stops on the login screen if
    #    not signed in; returns {"user_id","email","name","picture"}.
    user = require_login()

    # 4) Manual gmail.send OAuth callback — only OUR flow, only while logged in.
    if google_oauth.should_handle_gmail_callback(st.query_params, True):
        _handle_gmail_callback(user)

    # 5) Server-verified active church (role re-derived per request).
    active = require_active_church(user["user_id"])
    if active is None:
        render_onboarding(user)
        return

    render_church_switcher(user, active)
    _render_gmail_sidebar(user["user_id"], user["email"])

    def _service_builder_page():
        render_service_builder(user, active)

    def _settings_page():
        settings_page.render_settings_page(user, active)

    nav = st.navigation([
        st.Page(_service_builder_page, title="Service Builder", icon="✝️", default=True),
        st.Page(_settings_page, title="Settings", icon="⚙️"),
    ])
    nav.run()
```
Also delete the module-level `APP_PASSWORD`/`authenticated`/`gmail_user`/`oauth_state` session seeds (old lines 119–126) since the shared-password gate and `?gmail=` mechanism are removed.

**3d — `render_service_builder(user, active)`: concrete before/after edit regions** (the former `main()` body from old line 267 onward becomes this function, indented, with these substitutions applied):
```python
def render_service_builder(user, active):
    church_id = active["church_id"]
    user_id = user["user_id"]
```

Region — archive restore (old line 269):
```python
# BEFORE
        loaded = get_service(st.session_state.load_service_id)
# AFTER
        loaded = get_service(st.session_state.load_service_id, church_id)
```

Region — archive list (old line 425):
```python
# BEFORE
                saved = list_saved_services()
# AFTER
                saved = list_saved_services(church_id)
```

Region — hymn loading (replaces `get_db()`/`use_notion`/the whole `db.list_hymns()`+`get_property_value` block, old lines 299–306 and 577–622, and drops the Notion "Find hymns" + "Suggest hymns (AI)" UI):
```python
# AFTER
    st.header("Hymns")
    exclude_recent_hymns = st.checkbox(
        "Exclude hymns used in the last 12 weeks",
        value=False,
        help="When checked, hymns from recent services are hidden from the dropdowns.",
    )
    all_hymns = st.session_state.get("_cached_all_hymns")
    if all_hymns is None:
        try:
            with st.spinner("Loading this church's hymnal…"):
                all_hymns = list_hymns(church_id)
            st.session_state["_cached_all_hymns"] = all_hymns
        except Exception as e:  # noqa: BLE001
            logger.exception("Failed to load hymns")
            st.error(f"Could not load hymns: {e}. Click **Refresh hymn list** to retry.")
            all_hymns = []
            st.session_state["_cached_all_hymns"] = []
    if st.button("Refresh hymn list", key="refresh_hymns"):
        st.session_state.pop("_cached_all_hymns", None)
        st.rerun()

    title_to_info = build_title_to_info(all_hymns)
    if not title_to_info:
        # Explicit empty-hymnal message — never a silent swap to free-text inputs.
        st.warning(
            "This church's hymnal is empty. Add hymns on the **Settings → Hymns** "
            "page to enable hymn selection."
        )

    if exclude_recent_hymns and title_to_info:
        recent_used = get_recently_used_identifiers(church_id, weeks=12)
        titles_sorted = sorted(
            k for k in title_to_info
            if not is_hymn_recently_used(
                title_to_info[k].get("number"), title_to_info[k].get("title") or "", recent_used)
        )
        excluded = len(title_to_info) - len(titles_sorted)
        if excluded > 0:
            st.caption(f"Hymns used in the last 12 weeks are excluded ({excluded} excluded).")
    else:
        titles_sorted = sorted(title_to_info.keys(), key=str.lower)

    def _hymn_label(x):
        if not x:
            return "— Select —"
        return (title_to_info.get(x) or {}).get("title") or x
```

Region — hymn selection fragment (drops the manual `*_man` text-input fallback; selectboxes stay `st.selectbox` here and are converted to `safe_hymn_selectbox` in Task 19):
```python
# AFTER
    @st.fragment
    def hymn_selection_fragment():
        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader("Opening")
            st.caption("Gathering / call to worship")
            if titles_sorted:
                st.selectbox("Opening hymn", options=[""] + titles_sorted,
                             format_func=_hymn_label, key="opening")
        with col2:
            st.subheader("After sermon")
            st.caption("Response to scripture (NT reading)")
            if titles_sorted:
                st.selectbox("Response hymn", options=[""] + titles_sorted,
                             format_func=_hymn_label, key="response")
        with col3:
            st.subheader("Closing")
            st.caption("Joyful / sending")
            if titles_sorted:
                st.selectbox("Closing hymn", options=[""] + titles_sorted,
                             format_func=_hymn_label, key="closing")

    hymn_selection_fragment()

    hymns_ordered = []
    for slot in ("opening", "response", "closing"):
        choice = st.session_state.get(slot, "")
        if choice and choice in title_to_info:
            hymns_ordered.append(title_to_info[choice])
```

Region — record usage (old lines 919 and 942):
```python
# BEFORE
                if hymns_ordered and record_usage(service_date_str, hymns_ordered):
                    pass
# AFTER
                if hymns_ordered:
                    record_usage(church_id, service_date_str, hymns_ordered)
```

Region — editing-id church check + save/update (old lines 946–981):
```python
# AFTER
        editing_id = st.session_state.get("editing_service_id")
        if editing_id:
            existing = get_service(editing_id, church_id)
            if existing and existing.get("service_date_iso") != date_iso:
                st.session_state.editing_service_id = None
                editing_id = None
        save_btn_label = "Save changes" if editing_id else "Save this service to archive"
        if st.button(save_btn_label, key="save_archive"):
            save_kw = dict(
                service_date=service_date_str,
                service_date_iso=service_date_picked.isoformat(),
                occasion=occasion,
                scriptures=scriptures,
                hymns=hymns_ordered,
                liturgy=st.session_state.liturgy,
                sermon_title=st.session_state.get("sermon_title") or "",
                selected_ot_ref=st.session_state.get("selected_ot_ref") or "",
                selected_nt_ref=st.session_state.get("selected_nt_ref") or "",
                include_communion=st.session_state.get("include_communion", False),
            )
            try:
                if editing_id:
                    updated = update_service(editing_id, church_id, **save_kw)
                    if updated:
                        st.success("Service updated in archive.")
                    else:
                        st.session_state.editing_service_id = None
                        out = save_service(church_id=church_id, created_by=user_id, **save_kw)
                        st.session_state.editing_service_id = out.get("id")
                        st.success("Service saved to archive.")
                else:
                    out = save_service(church_id=church_id, created_by=user_id, **save_kw)
                    st.session_state.editing_service_id = out.get("id")
                    st.success("Service saved to archive.")
                st.session_state.pop("_cached_saved_services", None)
                st.rerun()
            except Exception as e:  # noqa: BLE001
                st.error(f"Archive save failed: {e}")
```

Region — email send (old lines 1013–1083; delete `_active_gmail_user`, `send_gmail` SMTP fallback, `get_contacts_for_display`):
```python
# AFTER
        if st.session_state.docx_bytes_secretary:
            with st.expander("Email to secretary", expanded=True):
                st.caption("Send the secretary .docx and a friendly message via Gmail.")
                connected = google_oauth.is_configured() and google_oauth.is_connected(user_id)
                if google_oauth.is_configured():
                    if connected:
                        st.caption(f"Sending as **{user['email']}** (your connected Gmail).")
                    else:
                        st.warning("Connect your Gmail in the sidebar to send from your own account.")
                contacts = list_contacts(church_id)
                contact_options = [f"{c['name']} <{c['email']}>" for c in contacts]
                email_to_contact = {f"{c['name']} <{c['email']}>": c["email"] for c in contacts}
                selected_contacts = st.multiselect(
                    "Recipients", options=contact_options, default=contact_options,
                    key="email_recipients", help="Select one or more saved contacts.")
                additional_emails = st.text_input(
                    "Additional emails (comma-separated)", key="secretary_email_extra",
                    placeholder="other@example.com")
                email_message = st.text_area("Message", key="email_message", height=100)
                if st.button("Send email to secretary", key="send_email_sec"):
                    recipient_emails = [email_to_contact[c] for c in selected_contacts]
                    if additional_emails and additional_emails.strip():
                        recipient_emails.extend(
                            e.strip() for e in additional_emails.split(",") if e.strip())
                    if not recipient_emails:
                        st.error("Please select at least one recipient or enter an email address.")
                    elif not connected:
                        st.error("Connect your Gmail in the sidebar first, then try again.")
                    else:
                        subject = f"Worship service — {service_date_str}"
                        body = (email_message or "Hi! Here’s the worship bulletin for this Sunday.").strip()
                        attachment_filename = f"worship_{safe_date}.docx"
                        err = google_oauth.send_email(
                            user_id, recipient_emails, subject, body,
                            attachment_bytes=st.session_state.docx_bytes_secretary,
                            attachment_filename=attachment_filename,
                        )
                        if err:
                            st.error(f"Email failed: {err}")
                        else:
                            st.success(f"Email sent to {len(recipient_emails)} recipient(s).")
```

**3e — Create `pages/__init__.py`** (empty) and **`pages/settings.py` stub:**
```python
#!/usr/bin/env python3
"""Settings page. Action helpers re-check role server-side (filled in Tasks 20-21)."""
import streamlit as st


class NotAuthorizedError(Exception):
    """Raised when a caller attempts an action their role does not permit."""


def render_settings_page(user, active):
    st.title("Settings")
    st.info("Settings coming online.")
```

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/test_app_helpers.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**
```
git add ui_helpers.py app.py pages/__init__.py pages/settings.py tests/test_app_helpers.py
git commit -m "Task 17: restructure app.py for multi-church (init_db, query-param capture, gated Gmail callback, login/active-church guards, two-page nav, church-scoped Service Builder)"
```

---

### Task 18: Onboarding (create church / join by code or captured invite link)
**Files:**
- Modify: `/Users/beaubrown/Desktop/projects/church/app.py` (replace `render_onboarding` placeholder)
- Modify: `/Users/beaubrown/Desktop/projects/church/ui_helpers.py` (add `pick_invite_code`)
- Test: `/Users/beaubrown/Desktop/projects/church/tests/test_onboarding.py`

**Interfaces:**
- Consumes: `repos.churches.create_church(*, name, timezone, owner_user_id) -> uuid.UUID`, `list_user_churches(user_id) -> list[dict{id,name,role}]`; `repos.invites.create_invite(*, church_id, created_by, role="member", email=None, ttl_days=7) -> str`, `accept_invite(code, user_id) -> tuple[bool,str]`; `repos.hymns.list_hymns(church_id)`.
- Produces: `ui_helpers.pick_invite_code(pending, typed) -> str`; `app.render_onboarding(user)`.

- [ ] **Step 1: Write the failing test** — `tests/test_onboarding.py`
```python
import pytest
from ui_helpers import pick_invite_code


def test_pick_invite_code_typed_wins_over_pending():
    assert pick_invite_code("PENDING", "TYPED") == "TYPED"


def test_pick_invite_code_falls_back_to_pending():
    assert pick_invite_code("PENDING", "") == "PENDING"
    assert pick_invite_code("PENDING", None) == "PENDING"


def test_pick_invite_code_blank_when_neither():
    assert pick_invite_code(None, None) == ""
    assert pick_invite_code("  ", "  ") == ""


def test_create_church_makes_owner_and_seeds_hymnal(tmp_db, make_user, seed_catalog):
    from repos.churches import create_church, list_user_churches
    from repos.hymns import list_hymns
    seed_catalog(5)
    user = make_user(email="founder@b.org")
    cid = create_church(name="New Life", timezone="America/New_York", owner_user_id=user)
    mine = list_user_churches(user)
    assert any(c["id"] == cid and c["role"] == "owner" for c in mine)
    assert len(list_hymns(cid)) == 5  # seeded atomically from the catalog


def test_accept_captured_invite_joins_as_member(tmp_db, make_user):
    from repos.churches import create_church, list_user_churches
    from repos.invites import create_invite, accept_invite
    owner = make_user(email="owner@a.org")
    cid = create_church(name="Grace", timezone="America/New_York", owner_user_id=owner)
    joiner = make_user(email="joiner@a.org")
    code = create_invite(church_id=cid, created_by=owner)
    ok, _msg = accept_invite(code, joiner)
    assert ok is True
    assert any(c["id"] == cid and c["role"] == "member" for c in list_user_churches(joiner))
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/test_onboarding.py -q`
Expected: FAIL with `ImportError: cannot import name 'pick_invite_code' from 'ui_helpers'`.

- [ ] **Step 3: Write the implementation**

Append to `ui_helpers.py`:
```python
def pick_invite_code(pending, typed) -> str:
    """Invite code to attempt: a typed value wins; otherwise the captured ?invite=."""
    typed = (typed or "").strip()
    if typed:
        return typed
    return (pending or "").strip()
```

Add the import in `app.py` (extend the `ui_helpers` import in 3b):
```python
from ui_helpers import (
    capture_query_params,
    clear_oauth_query_params,
    build_title_to_info,
    pick_invite_code,
)
from repos.churches import list_user_churches, create_church
from repos.invites import accept_invite
```

Replace the `render_onboarding` placeholder in `app.py`:
```python
def render_onboarding(user):
    """Signed-in user with no membership: create a church or join by invite."""
    user_id = user["user_id"]
    st.title("Welcome to Worship Service Builder")
    st.caption(f"Signed in as {user['email']}. You don't belong to a church yet.")

    pending_code = st.session_state.get("pending_invite_code")
    if pending_code:
        st.info("You opened an invite link. Review and accept it below.")

    tab_join, tab_create = st.tabs(["Join a church", "Create a church"])

    with tab_join:
        typed = st.text_input("Invite code", value=pending_code or "", key="onboard_invite_code")
        if st.button("Join church", key="onboard_join"):
            code = pick_invite_code(pending_code, typed)
            if not code:
                st.error("Enter an invite code, or open your invite link again.")
            else:
                try:
                    ok, msg = accept_invite(code, user_id)
                except Exception as e:  # noqa: BLE001
                    ok, msg = False, str(e)
                if ok:
                    st.session_state.pop("pending_invite_code", None)
                    st.query_params.clear()  # onboarding is terminal; safe to clear here
                    st.success(msg or "Joined. Loading your church…")
                    st.rerun()
                else:
                    st.error(msg or "That invite code is not valid.")

    with tab_create:
        with st.form("onboard_create_church"):
            name = st.text_input("Church name", key="onboard_church_name")
            timezone = st.text_input("Timezone", value="America/New_York",
                                     key="onboard_church_tz",
                                     help="e.g. America/New_York — drives first-Sunday and the 12-week window.")
            if st.form_submit_button("Create church"):
                if not name.strip():
                    st.error("Church name is required.")
                elif not timezone.strip():
                    st.error("Timezone is required.")
                else:
                    try:
                        cid = create_church(name=name.strip(),
                                            timezone=timezone.strip(),
                                            owner_user_id=user_id)
                        st.session_state["active_church_id"] = str(cid)
                        st.success("Church created. Loading…")
                        st.rerun()
                    except Exception as e:  # noqa: BLE001
                        st.error(f"Could not create church: {e}")
```

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/test_onboarding.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**
```
git add ui_helpers.py app.py tests/test_onboarding.py
git commit -m "Task 18: onboarding — create church (owner + seeded hymnal) or join via code/captured invite link"
```

---

### Task 19: Selectbox safety (`safe_hymn_selectbox` + pure `coerce_selectbox_value`)
**Files:**
- Modify: `/Users/beaubrown/Desktop/projects/church/ui_helpers.py` (add `coerce_selectbox_value`)
- Modify: `/Users/beaubrown/Desktop/projects/church/app.py` (add `safe_hymn_selectbox`; convert the three hymn selectboxes)
- Test: `/Users/beaubrown/Desktop/projects/church/tests/test_selectbox_safety.py`

**Interfaces:**
- Consumes: `ui_helpers.coerce_selectbox_value(current, options) -> str`.
- Produces: `app.safe_hymn_selectbox(label, options, key, format_func)`.

- [ ] **Step 1: Write the failing test** — `tests/test_selectbox_safety.py`
```python
import pytest
from ui_helpers import coerce_selectbox_value


def test_valid_value_is_kept():
    assert coerce_selectbox_value("holy", ["", "holy", "amazing"]) == "holy"


def test_stale_value_resets_to_empty():
    # The church-switch crash today: stored value not in the new church's options.
    assert coerce_selectbox_value("hymn_from_other_church", ["", "a", "b"]) == ""


def test_empty_stays_empty():
    assert coerce_selectbox_value("", ["", "a"]) == ""


def test_missing_none_resets_to_empty():
    assert coerce_selectbox_value(None, ["", "a"]) == ""
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/test_selectbox_safety.py -q`
Expected: FAIL with `ImportError: cannot import name 'coerce_selectbox_value' from 'ui_helpers'`.

- [ ] **Step 3: Write the implementation**

Append to `ui_helpers.py`:
```python
def coerce_selectbox_value(current, options) -> str:
    """Reset a stored selectbox value to '' when it's not among the current options,
    so switching churches never raises StreamlitAPIException (spec §5)."""
    if current in options:
        return current
    return ""
```

Add to `app.py` (near the other helpers; import `coerce_selectbox_value`):
```python
from ui_helpers import (
    capture_query_params,
    clear_oauth_query_params,
    build_title_to_info,
    pick_invite_code,
    coerce_selectbox_value,
)


def safe_hymn_selectbox(label, options, key, format_func):
    """A hymn selectbox that first coerces a stale stored value to '' (guarding
    against StreamlitAPIException when the church's options changed), then renders."""
    current = st.session_state.get(key, "")
    coerced = coerce_selectbox_value(current, options)
    if coerced != current:
        st.session_state[key] = coerced
    return st.selectbox(label, options=options, key=key, format_func=format_func)
```

Convert the three selectboxes inside `hymn_selection_fragment` (before/after):
```python
# BEFORE (Opening)
                st.selectbox("Opening hymn", options=[""] + titles_sorted,
                             format_func=_hymn_label, key="opening")
# AFTER (Opening)
                safe_hymn_selectbox("Opening hymn", [""] + titles_sorted, "opening", _hymn_label)
```
```python
# BEFORE (Response)
                st.selectbox("Response hymn", options=[""] + titles_sorted,
                             format_func=_hymn_label, key="response")
# AFTER (Response)
                safe_hymn_selectbox("Response hymn", [""] + titles_sorted, "response", _hymn_label)
```
```python
# BEFORE (Closing)
                st.selectbox("Closing hymn", options=[""] + titles_sorted,
                             format_func=_hymn_label, key="closing")
# AFTER (Closing)
                safe_hymn_selectbox("Closing hymn", [""] + titles_sorted, "closing", _hymn_label)
```

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/test_selectbox_safety.py -q`
Expected: PASS (4 passed). Note: `safe_hymn_selectbox` itself calls `st.*`, so only the pure `coerce_selectbox_value` is unit-tested (per the extract-and-test-pure-helpers rule).

- [ ] **Step 5: Commit**
```
git add ui_helpers.py app.py tests/test_selectbox_safety.py
git commit -m "Task 19: safe_hymn_selectbox coerces stale session values to '' (no crash on church switch)"
```

---

### Task 20: Settings — profile + contacts (admin-gated) and hymn CRUD (member-editable)
**Files:**
- Modify (rewrite from stub): `/Users/beaubrown/Desktop/projects/church/pages/settings.py`
- Test: `/Users/beaubrown/Desktop/projects/church/tests/test_settings_profile_contacts.py`

**Interfaces:**
- Consumes: `tenancy.is_admin(role)`; `repos.memberships.get_role(user_id, church_id)`, `add_membership(user_id, church_id, role)`; `db.session_scope()`, `db.models.Church`; `email_contacts.add_contact(church_id, *, name, email)`, `list_contacts(church_id) -> list[dict{id,name,email}]`, `delete_contact(contact_id, church_id)`; `repos.hymns.list_hymns(church_id)`, `add_hymn(church_id, *, title, number, scripture_refs, theme, hymnary_link)`, `update_hymn(hymn_id, church_id, **fields)`, `delete_hymn(hymn_id, church_id)`.
- Produces: `pages.settings.NotAuthorizedError`; `submit_profile_update(user_id, church_id, *, name, timezone)`, `submit_add_contact(user_id, church_id, *, name, email)`, `submit_delete_contact(user_id, church_id, contact_id)`, `submit_add_hymn(...)`, `submit_update_hymn(...)`, `submit_delete_hymn(...)`; extended `render_settings_page(user, active)`.

- [ ] **Step 1: Write the failing test** — `tests/test_settings_profile_contacts.py`
```python
import pytest


def test_member_cannot_update_profile(tmp_db, make_user, make_church):
    from pages.settings import submit_profile_update, NotAuthorizedError
    from repos.memberships import add_membership
    owner = make_user(email="owner@f.org")
    church = make_church(name="First", timezone="America/New_York", owner_user_id=owner)
    member = make_user(email="member@f.org")
    add_membership(member, church, "member")
    with pytest.raises(NotAuthorizedError):
        submit_profile_update(member, church, name="Hacked", timezone="America/New_York")


def test_member_cannot_add_or_delete_contacts(tmp_db, make_user, make_church):
    from pages.settings import submit_add_contact, submit_delete_contact, NotAuthorizedError
    from repos.memberships import add_membership
    owner = make_user(email="o2@f.org")
    church = make_church(name="F2", timezone="America/New_York", owner_user_id=owner)
    member = make_user(email="m2@f.org")
    add_membership(member, church, "member")
    with pytest.raises(NotAuthorizedError):
        submit_add_contact(member, church, name="X", email="x@f.org")
    with pytest.raises(NotAuthorizedError):
        submit_delete_contact(member, church, "any-id")


def test_admin_can_update_profile_and_add_contact(tmp_db, make_user, make_church):
    from pages.settings import submit_profile_update, submit_add_contact
    import email_contacts
    from db import session_scope
    from db.models import Church
    owner = make_user(email="admin@g.org")
    church = make_church(name="G", timezone="America/New_York", owner_user_id=owner)
    submit_profile_update(owner, church, name="Grace Church", timezone="America/Chicago")
    with session_scope() as s:
        c = s.get(Church, church)
        assert c.name == "Grace Church" and c.timezone == "America/Chicago"
    submit_add_contact(owner, church, name="Sec", email="sec@g.org")
    assert any(x["email"] == "sec@g.org" for x in email_contacts.list_contacts(church))


def test_member_can_add_hymn(tmp_db, make_user, make_church):
    # Members may edit the hymnal (spec §5) — the hymn helper does NOT require admin.
    from pages.settings import submit_add_hymn
    from repos.memberships import add_membership
    from repos.hymns import list_hymns
    owner = make_user(email="o3@h.org")
    church = make_church(name="H", timezone="America/New_York", owner_user_id=owner)
    member = make_user(email="m3@h.org")
    add_membership(member, church, "member")
    submit_add_hymn(member, church, title="A New Song", number=700)
    assert any(h.get("Hymn Title") == "A New Song" for h in list_hymns(church))
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/test_settings_profile_contacts.py -q`
Expected: FAIL with `ImportError: cannot import name 'submit_profile_update' from 'pages.settings'`.

- [ ] **Step 3: Write the implementation** — rewrite `pages/settings.py`:
```python
#!/usr/bin/env python3
"""Settings page: church profile, contacts, and hymn library.

Every state-changing action goes through a helper that RE-CHECKS the caller's
role server-side (spec §2 active-church guard, §5 roles) and raises
NotAuthorizedError when the caller lacks permission — hiding UI is not enough.
Streamlit rendering is a thin shell over these tested helpers.
"""
import logging

import streamlit as st

from db import session_scope
from db.models import Church
from tenancy import is_admin
from repos.memberships import get_role
import email_contacts
from repos import hymns as hymns_repo

logger = logging.getLogger(__name__)


class NotAuthorizedError(Exception):
    """Raised when a caller attempts an action their role does not permit."""


def _require_admin(user_id, church_id):
    role = get_role(user_id, church_id)
    if not is_admin(role):
        raise NotAuthorizedError("You must be an admin to do that.")
    return role


def _require_member(user_id, church_id):
    role = get_role(user_id, church_id)
    if role is None:
        raise NotAuthorizedError("You are not a member of this church.")
    return role


# --------------------------------------------------------------------------- #
# Action helpers (no Streamlit; unit-tested)
# --------------------------------------------------------------------------- #
def submit_profile_update(user_id, church_id, *, name, timezone):
    _require_admin(user_id, church_id)
    name = (name or "").strip()
    timezone = (timezone or "").strip()
    if not name:
        raise ValueError("Church name is required.")
    if not timezone:
        raise ValueError("Timezone is required.")
    with session_scope() as s:
        church = s.get(Church, church_id)
        if church is None or church.deleted_at is not None:
            raise ValueError("Church not found.")
        church.name = name
        church.timezone = timezone


def submit_add_contact(user_id, church_id, *, name, email):
    _require_admin(user_id, church_id)
    email = (email or "").strip()
    if not email:
        raise ValueError("Email is required.")
    return email_contacts.add_contact(church_id, name=(name or "").strip(), email=email)


def submit_delete_contact(user_id, church_id, contact_id):
    _require_admin(user_id, church_id)
    email_contacts.delete_contact(contact_id, church_id)


def submit_add_hymn(user_id, church_id, *, title, number=None,
                    scripture_refs="", theme="", hymnary_link=""):
    _require_member(user_id, church_id)
    if not (title or "").strip():
        raise ValueError("Hymn title is required.")
    return hymns_repo.add_hymn(
        church_id, title=title.strip(), number=number,
        scripture_refs=scripture_refs, theme=theme, hymnary_link=hymnary_link)


def submit_update_hymn(user_id, church_id, hymn_id, **fields):
    _require_member(user_id, church_id)
    return hymns_repo.update_hymn(hymn_id, church_id, **fields)


def submit_delete_hymn(user_id, church_id, hymn_id):
    _require_member(user_id, church_id)
    hymns_repo.delete_hymn(hymn_id, church_id)


# --------------------------------------------------------------------------- #
# Render (Streamlit shell)
# --------------------------------------------------------------------------- #
def render_settings_page(user, active):
    user_id = user["user_id"]
    church_id = active["church_id"]
    role = active["role"]
    admin = is_admin(role)

    with session_scope() as s:
        church = s.get(Church, church_id)
        current_tz = church.timezone if church else ""

    st.title("Settings")
    st.caption(f"{active['name']} — you are **{role}**.")

    tab_profile, tab_contacts, tab_hymns = st.tabs(["Church profile", "Contacts", "Hymns"])

    with tab_profile:
        if not admin:
            st.info("Only admins can edit the church profile.")
        with st.form("church_profile"):
            name = st.text_input("Church name", value=active["name"])
            timezone = st.text_input("Timezone", value=current_tz)
            if st.form_submit_button("Save profile", disabled=not admin):
                try:
                    submit_profile_update(user_id, church_id, name=name, timezone=timezone)
                    st.success("Profile updated.")
                    st.rerun()
                except (NotAuthorizedError, ValueError) as e:
                    st.error(str(e))

    with tab_contacts:
        contacts = email_contacts.list_contacts(church_id)
        for c in contacts:
            col_a, col_b = st.columns([4, 1])
            col_a.write(f"**{c['name']}** — {c['email']}")
            if admin and col_b.button("Delete", key=f"del_contact_{c['id']}"):
                try:
                    submit_delete_contact(user_id, church_id, c["id"])
                    st.rerun()
                except NotAuthorizedError as e:
                    st.error(str(e))
        if admin:
            with st.form("add_contact"):
                cname = st.text_input("Name", key="new_contact_name")
                cemail = st.text_input("Email", key="new_contact_email")
                if st.form_submit_button("Add contact"):
                    try:
                        submit_add_contact(user_id, church_id, name=cname, email=cemail)
                        st.success("Contact added.")
                        st.rerun()
                    except (NotAuthorizedError, ValueError) as e:
                        st.error(str(e))
        else:
            st.info("Only admins can add or remove contacts.")

    with tab_hymns:
        st.caption("Members may edit this church's hymnal.")
        hymns = hymns_repo.list_hymns(church_id)
        st.write(f"{len(hymns)} hymns.")
        with st.form("add_hymn"):
            htitle = st.text_input("Title", key="new_hymn_title")
            hnum = st.text_input("Number", key="new_hymn_number")
            hrefs = st.text_input("Scripture references", key="new_hymn_refs")
            if st.form_submit_button("Add hymn"):
                try:
                    submit_add_hymn(
                        user_id, church_id, title=htitle,
                        number=int(hnum) if hnum.strip().isdigit() else None,
                        scripture_refs=hrefs)
                    st.success("Hymn added.")
                    st.rerun()
                except (NotAuthorizedError, ValueError) as e:
                    st.error(str(e))
        for h in hymns[:50]:
            col_a, col_b = st.columns([4, 1])
            col_a.write(f"#{h.get('Hymn Number') or '—'} — {h.get('Hymn Title')}")
            if col_b.button("Delete", key=f"del_hymn_{h['id']}"):
                try:
                    submit_delete_hymn(user_id, church_id, h["id"])
                    st.rerun()
                except NotAuthorizedError as e:
                    st.error(str(e))
```

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/test_settings_profile_contacts.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**
```
git add pages/settings.py tests/test_settings_profile_contacts.py
git commit -m "Task 20: Settings profile + contacts (admin-gated, server-rechecked) and member-editable hymn CRUD"
```

---

### Task 21: Settings — members & invites (admin-gated) + owner-only transfer/delete
**Files:**
- Modify: `/Users/beaubrown/Desktop/projects/church/pages/settings.py` (append helpers + extend render)
- Test: `/Users/beaubrown/Desktop/projects/church/tests/test_settings_members_invites.py`

**Interfaces:**
- Consumes: `repos.memberships.get_role(user_id, church_id)`, `set_role(user_id, church_id, role)`, `remove_membership(user_id, church_id)` (raises `LastAdminError`), `list_members(church_id) -> list[dict{user_id,email,name,role}]`, `LastAdminError`; `repos.churches.soft_delete_church(church_id)`; `repos.invites.create_invite(*, church_id, created_by, role="member", email=None) -> str`, `list_invites(church_id)`, `revoke_invite(invite_id, church_id)`.
- Produces: `apply_role_change(actor_user_id, church_id, target_user_id, new_role)`, `apply_remove_member(actor_user_id, church_id, target_user_id)`, `do_create_invite(actor_user_id, church_id, *, role="member", email=None) -> str`, `do_revoke_invite(actor_user_id, church_id, invite_id)`, `transfer_ownership(actor_user_id, church_id, new_owner_user_id)`, `delete_this_church(actor_user_id, church_id)`, `_require_owner(user_id, church_id)`.

- [ ] **Step 1: Write the failing test** — `tests/test_settings_members_invites.py`
```python
import pytest


def test_member_rejected_by_action_helpers(tmp_db, make_user, make_church):
    from pages.settings import (
        apply_role_change, apply_remove_member, do_create_invite,
        do_revoke_invite, NotAuthorizedError,
    )
    from repos.memberships import add_membership
    owner = make_user(email="o@c.org")
    church = make_church(name="C", timezone="America/New_York", owner_user_id=owner)
    m1 = make_user(email="m1@c.org"); add_membership(m1, church, "member")
    m2 = make_user(email="m2@c.org"); add_membership(m2, church, "member")
    with pytest.raises(NotAuthorizedError):
        apply_role_change(m1, church, m2, "admin")
    with pytest.raises(NotAuthorizedError):
        apply_remove_member(m1, church, m2)
    with pytest.raises(NotAuthorizedError):
        do_create_invite(m1, church)
    with pytest.raises(NotAuthorizedError):
        do_revoke_invite(m1, church, "any-id")


def test_remove_last_admin_surfaces_lastadmin_error(tmp_db, make_user, make_church):
    from pages.settings import apply_remove_member
    from repos.memberships import LastAdminError
    owner = make_user(email="o@d.org")
    church = make_church(name="D", timezone="America/New_York", owner_user_id=owner)
    with pytest.raises(LastAdminError):
        apply_remove_member(owner, church, owner)  # owner is the last admin


def test_owner_only_transfer_and_delete(tmp_db, make_user, make_church):
    from pages.settings import transfer_ownership, delete_this_church, NotAuthorizedError
    from repos.memberships import add_membership, get_role
    owner = make_user(email="o@e.org")
    church = make_church(name="E", timezone="America/New_York", owner_user_id=owner)
    admin = make_user(email="a@e.org"); add_membership(admin, church, "admin")
    # An admin (not owner) is rejected by the owner-only helpers.
    with pytest.raises(NotAuthorizedError):
        transfer_ownership(admin, church, owner)
    with pytest.raises(NotAuthorizedError):
        delete_this_church(admin, church)
    # The owner can transfer: new owner becomes 'owner', old owner demoted to 'admin'.
    transfer_ownership(owner, church, admin)
    assert get_role(admin, church) == "owner"
    assert get_role(owner, church) == "admin"


def test_admin_can_create_invite(tmp_db, make_user, make_church):
    from pages.settings import do_create_invite
    owner = make_user(email="o@k.org")
    church = make_church(name="K", timezone="America/New_York", owner_user_id=owner)
    code = do_create_invite(owner, church, role="member")
    assert isinstance(code, str) and len(code) >= 20
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/test_settings_members_invites.py -q`
Expected: FAIL with `ImportError: cannot import name 'apply_role_change' from 'pages.settings'`.

- [ ] **Step 3: Write the implementation**

Extend the imports in `pages/settings.py` (before/after):
```python
# BEFORE
from repos.memberships import get_role
import email_contacts
from repos import hymns as hymns_repo
# AFTER
from repos.memberships import (
    get_role, set_role, remove_membership, list_members, LastAdminError,
)
from repos.churches import soft_delete_church
from repos.invites import create_invite, list_invites, revoke_invite
import email_contacts
from repos import hymns as hymns_repo
```

Append the helpers to `pages/settings.py`:
```python
def _require_owner(user_id, church_id):
    role = get_role(user_id, church_id)
    if role != "owner":
        raise NotAuthorizedError("Only the owner can do that.")
    return role


def apply_role_change(actor_user_id, church_id, target_user_id, new_role):
    _require_admin(actor_user_id, church_id)
    set_role(target_user_id, church_id, new_role)  # may raise LastAdminError on demotion


def apply_remove_member(actor_user_id, church_id, target_user_id):
    _require_admin(actor_user_id, church_id)
    remove_membership(target_user_id, church_id)  # surfaces LastAdminError to the UI


def do_create_invite(actor_user_id, church_id, *, role="member", email=None):
    _require_admin(actor_user_id, church_id)
    return create_invite(church_id=church_id, created_by=actor_user_id, role=role, email=email)


def do_revoke_invite(actor_user_id, church_id, invite_id):
    _require_admin(actor_user_id, church_id)
    revoke_invite(invite_id, church_id)


def transfer_ownership(actor_user_id, church_id, new_owner_user_id):
    _require_owner(actor_user_id, church_id)
    set_role(new_owner_user_id, church_id, "owner")
    set_role(actor_user_id, church_id, "admin")


def delete_this_church(actor_user_id, church_id):
    _require_owner(actor_user_id, church_id)
    soft_delete_church(church_id)  # soft delete; also revokes pending invites
```

Extend the render tabs (before/after inside `render_settings_page`):
```python
# BEFORE
    tab_profile, tab_contacts, tab_hymns = st.tabs(["Church profile", "Contacts", "Hymns"])
# AFTER
    tab_profile, tab_contacts, tab_hymns, tab_members, tab_invites, tab_danger = st.tabs(
        ["Church profile", "Contacts", "Hymns", "Members", "Invites", "Danger zone"])
```

Append these tab blocks at the end of `render_settings_page` (after the `tab_hymns` block):
```python
    with tab_members:
        if not admin:
            st.info("Only admins can manage members.")
        role_options = ["member", "admin", "owner"]
        for m in list_members(church_id):
            cols = st.columns([3, 2, 1])
            cols[0].write(f"**{m['name'] or m['email']}** ({m['email']}) — {m['role']}")
            if admin and m["user_id"] != user_id:
                new_role = cols[1].selectbox(
                    "Role", role_options, index=role_options.index(m["role"]),
                    key=f"role_{m['user_id']}", label_visibility="collapsed")
                if new_role != m["role"] and cols[1].button("Update", key=f"chg_{m['user_id']}"):
                    try:
                        apply_role_change(user_id, church_id, m["user_id"], new_role)
                        st.rerun()
                    except (NotAuthorizedError, LastAdminError) as e:
                        st.error(str(e))
                if cols[2].button("Remove", key=f"rm_{m['user_id']}"):
                    try:
                        apply_remove_member(user_id, church_id, m["user_id"])
                        st.rerun()
                    except (NotAuthorizedError, LastAdminError) as e:
                        st.error(str(e))

    with tab_invites:
        if not admin:
            st.info("Only admins can manage invites.")
        else:
            with st.form("create_invite"):
                inv_email = st.text_input("Bind to email (optional)")
                inv_role = st.selectbox("Role", ["member", "admin"])
                if st.form_submit_button("Create invite"):
                    try:
                        code = do_create_invite(
                            user_id, church_id, role=inv_role,
                            email=(inv_email.strip() or None))
                        st.success(f"Invite code: `{code}`")
                    except NotAuthorizedError as e:
                        st.error(str(e))
            for inv in list_invites(church_id):
                cols = st.columns([3, 1])
                cols[0].write(f"`{inv['code']}` — {inv.get('email') or 'any'} — {inv['role']}")
                if cols[1].button("Revoke", key=f"revoke_{inv['id']}"):
                    try:
                        do_revoke_invite(user_id, church_id, inv["id"])
                        st.rerun()
                    except NotAuthorizedError as e:
                        st.error(str(e))

    with tab_danger:
        if role != "owner":
            st.info("Only the owner can transfer ownership or delete the church.")
        else:
            st.subheader("Transfer ownership")
            others = [m for m in list_members(church_id) if m["user_id"] != user_id]
            if others:
                labels = {f"{m['name'] or m['email']} ({m['email']})": m["user_id"] for m in others}
                pick = st.selectbox("New owner", list(labels.keys()), key="transfer_pick")
                if st.button("Transfer ownership"):
                    try:
                        transfer_ownership(user_id, church_id, labels[pick])
                        st.success("Ownership transferred. You are now an admin.")
                        st.rerun()
                    except NotAuthorizedError as e:
                        st.error(str(e))
            else:
                st.caption("Invite another member first to transfer ownership.")
            st.divider()
            st.subheader("Delete this church")
            confirm = st.text_input("Type the church name to confirm", key="delete_confirm")
            if st.button("Delete church", type="primary"):
                if confirm.strip() == active["name"]:
                    try:
                        delete_this_church(user_id, church_id)
                        st.session_state.pop("active_church_id", None)
                        st.success("Church deleted.")
                        st.rerun()
                    except NotAuthorizedError as e:
                        st.error(str(e))
                else:
                    st.error("Church name did not match.")
```

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/test_settings_members_invites.py -q`
Expected: PASS (4 passed). Full-suite check: `pytest -q` → all green.

- [ ] **Step 5: Commit**
```
git add pages/settings.py tests/test_settings_members_invites.py
git commit -m "Task 21: Settings members & invites (admin-gated, server-rechecked) + owner-only transfer/delete; surfaces LastAdminError"
```

---

Both context files are read. The SPEC is `docs/superpowers/specs/2026-07-22-multi-user-app-design.md`; the LOCKED INTERFACES arrived inline in my instructions (CRITICAL SIGNATURES). Here are Tasks 22-25.

### Task 22: Migration CLI — founder + hymn catalog

**Files:**
- Create: `/Users/beaubrown/Desktop/projects/church/migrate_to_db.py`
- Create (test): `/Users/beaubrown/Desktop/projects/church/tests/test_migrate_hymns.py`

**Interfaces:**
- Consumes (locked): `db.session_scope()`, `db.init_db()`; `repos.churches.create_church(*, name, timezone, owner_user_id) -> uuid.UUID`; `repos.churches.list_user_churches(user_id) -> list[dict]` (`[{"id":UUID,"name":str,"role":str}]`); `repos.hymns.seed_church_from_catalog(church_id, session) -> int`; `repos.hymns.list_hymns(church_id) -> list[dict]` (flat Notion keys); `auth.upsert_from_claims(claims) -> uuid.UUID`; `hymn_utils.get_property_value(hymn, prop_name)`.
- Consumes (model contract from the hymn-models task): `db.models.HymnCatalog(title:str, number:int|None, scripture_refs, theme, hymnary_link, audio_url)` and `db.models.Hymn(church_id, title:str, number:int|None, scripture_refs, theme, hymnary_link, audio_url)` — discrete typed columns, no `props` blob; `list_hymns` returns flat Notion-key dicts (`{"id", "Hymn Title", "Hymn Number", "Scripture References", "Theme", "Hymnary.org Link", "Audio"}`) built from those columns.
- Produces (later migration task relies on these exact names): `parse_hymn_page(page)->dict`, `upsert_catalog_hymn(session, parsed)->bool`, `import_hymn_catalog(session, pages)->dict`, `ensure_founder_user(email, name)->uuid.UUID`, `ensure_founder_church(user_id, name, tz)->uuid.UUID`, `_ensure_church_seeded(session, church_id)->int`, `fetch_notion_hymns()->list`, `run_migration(*, founder_email, church_name, timezone, hymn_pages=None)->dict`, `_print_report(report)`, `main(argv=None)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_migrate_hymns.py
import uuid

from migrate_to_db import parse_hymn_page, import_hymn_catalog, run_migration
from db import session_scope
from repos.churches import list_user_churches
from repos.hymns import list_hymns


def _hymn_page(number, title, scripture=""):
    props = {
        "Hymn Title": {"type": "title", "title": [{"plain_text": title}]},
        "Hymn Number": {"type": "number", "number": number},
    }
    if scripture:
        props["Scripture References"] = {
            "type": "rich_text",
            "rich_text": [{"plain_text": scripture}],
        }
    return {"id": f"page-{number}", "properties": props}


def test_parse_hymn_page_flattens_notion_keys():
    parsed = parse_hymn_page(_hymn_page(43, "Holy, Holy, Holy", "Revelation 4:8"))
    assert parsed["number"] == 43
    assert parsed["title"] == "Holy, Holy, Holy"
    assert parsed["props"]["Hymn Title"] == "Holy, Holy, Holy"
    assert parsed["props"]["Scripture References"] == "Revelation 4:8"


def test_import_hymn_catalog_is_idempotent(tmp_db):
    pages = [
        _hymn_page(43, "Holy, Holy, Holy", "Revelation 4:8"),
        _hymn_page(649, "Amazing Grace", "John 9:25"),
    ]
    with session_scope() as session:
        first = import_hymn_catalog(session, pages)
    assert first == {"inserted": 2, "updated": 0, "total": 2}
    with session_scope() as session:
        second = import_hymn_catalog(session, pages)
    assert second["inserted"] == 0
    assert second["updated"] == 2


def test_run_migration_creates_owner_church_and_seeds(tmp_db):
    pages = [
        _hymn_page(43, "Holy, Holy, Holy", "Revelation 4:8"),
        _hymn_page(649, "Amazing Grace", "John 9:25"),
    ]
    report = run_migration(
        founder_email="Beau@Example.com",
        church_name="Conner Presbyterian",
        timezone="America/New_York",
        hymn_pages=pages,
    )
    user_id = uuid.UUID(report["founder_user_id"])
    owned = [c for c in list_user_churches(user_id) if c["role"] == "owner"]
    assert any(c["name"] == "Conner Presbyterian" for c in owned)

    church_id = uuid.UUID(report["church_id"])
    hymns = list_hymns(church_id)
    assert len(hymns) == 2
    assert {"Holy, Holy, Holy", "Amazing Grace"} <= {h.get("Hymn Title") for h in hymns}


def test_run_migration_is_idempotent(tmp_db):
    pages = [_hymn_page(1, "Come Thou Fount", "1 Samuel 7:12")]
    first = run_migration(
        founder_email="beau@example.com",
        church_name="Conner Presbyterian",
        timezone="America/New_York",
        hymn_pages=pages,
    )
    second = run_migration(
        founder_email="beau@example.com",
        church_name="Conner Presbyterian",
        timezone="America/New_York",
        hymn_pages=pages,
    )
    assert second["church_id"] == first["church_id"]
    user_id = uuid.UUID(second["founder_user_id"])
    named = [c for c in list_user_churches(user_id) if c["name"] == "Conner Presbyterian"]
    assert len(named) == 1
    assert len(list_hymns(uuid.UUID(second["church_id"]))) == 1
```

Note: `run_migration` here passes `hymn_pages=` so no Notion I/O occurs. These tests stay green after Task 23 extends `run_migration` (the passed hymns carry `Scripture References`, so the added enrichment validation passes, and the archive/usage/contacts fetchers short-circuit to `[]` when `NOTION_*` env vars are unset — the case in CI).

- [ ] **Step 2: Run test to verify it fails**
- Run: `python -m pytest tests/test_migrate_hymns.py -q`
- Expected: FAIL — collection error `ModuleNotFoundError: No module named 'migrate_to_db'` (file does not exist yet).

- [ ] **Step 3: Write the implementation**

```python
# migrate_to_db.py
#!/usr/bin/env python3
"""One-time migration: Notion + legacy JSON -> the multi-church app database.

Creates the founder user and their church (as owner), imports the enriched
Notion hymn database into `hymn_catalog`, and seeds the founder church's
`hymns` from that catalog. Safe to re-run to convergence (idempotent).

Usage:
    python migrate_to_db.py \
        --founder-email beau@example.com \
        --church-name "Conner Presbyterian" \
        --timezone America/New_York
"""

import argparse
import sys

from sqlalchemy import func, select

from db import init_db, session_scope
from db.models import Hymn, HymnCatalog
from repos.churches import create_church, list_user_churches
from repos.hymns import seed_church_from_catalog
from auth import upsert_from_claims
from hymn_utils import get_property_value

# Notion hymn property names carried verbatim into `props` (flat Notion keys).
_CATALOG_PROPERTY_NAMES = (
    "Hymn Title",
    "Hymn Number",
    "Hymnary.org Link",
    "Scripture References",
    "Theme",
    "Text",
    "Tune",
    "Tune Name",
    "Composer",
    "Lyricist",
    "Meter",
    "Music Date",
    "Lyrics Date",
)


def _norm_title(title):
    return (title or "").strip().lower()


def parse_hymn_page(page):
    """Notion hymn page -> flat catalog row {'number', 'title', 'props'}. Pure."""
    props = {}
    for name in _CATALOG_PROPERTY_NAMES:
        value = get_property_value(page, name)
        if value is not None and value != "":
            props[name] = value
    title = (props.get("Hymn Title") or "").strip()
    number = props.get("Hymn Number")
    if number is not None and not isinstance(number, int):
        try:
            number = int(number)
        except (TypeError, ValueError):
            number = None
    return {"number": number, "title": title, "props": props}


def upsert_catalog_hymn(session, parsed):
    """Insert/update one hymn_catalog row keyed by (number, normalized title).

    Returns True if a new row was inserted, False if an existing row was
    updated. Idempotent -> safe to re-run to convergence. Duplicate-title
    settings with different numbers (e.g. multiple "Gloria") are not collapsed.
    """
    number = parsed.get("number")
    norm = _norm_title(parsed.get("title"))
    props = parsed.get("props") or {}
    stmt = select(HymnCatalog)
    if number is None:
        stmt = stmt.where(HymnCatalog.number.is_(None))
    else:
        stmt = stmt.where(HymnCatalog.number == number)
    match = next(
        (row for row in session.execute(stmt).scalars() if _norm_title(row.title) == norm),
        None,
    )
    if match is None:
        session.add(
            HymnCatalog(
                title=parsed.get("title") or "",
                number=number,
                scripture_refs=props.get("Scripture References"),
                theme=props.get("Theme"),
                hymnary_link=props.get("Hymnary.org Link"),
                audio_url=props.get("audio_url"),
            )
        )
        return True
    match.title = parsed.get("title") or ""
    match.scripture_refs = props.get("Scripture References")
    match.theme = props.get("Theme")
    match.hymnary_link = props.get("Hymnary.org Link")
    match.audio_url = props.get("audio_url")
    return False


def import_hymn_catalog(session, pages):
    """Load Notion hymn pages into hymn_catalog. Returns a count report."""
    inserted = updated = 0
    for page in pages:
        parsed = parse_hymn_page(page)
        if not parsed["title"]:
            continue
        if upsert_catalog_hymn(session, parsed):
            inserted += 1
        else:
            updated += 1
    return {"inserted": inserted, "updated": updated, "total": inserted + updated}


def ensure_founder_user(email, name):
    """Create/refresh the founder's users row (keyed on normalized email)."""
    claims = {
        "email": email,
        "name": name,
        "sub": None,
        "picture": None,
        "email_verified": True,
    }
    return upsert_from_claims(claims)


def ensure_founder_church(user_id, name, tz):
    """Return the founder's owned church of this name, creating it if absent.

    create_church atomically seeds the church's hymns from hymn_catalog, so
    the catalog must be imported *before* this call.
    """
    for church in list_user_churches(user_id):
        if church["name"] == name and church["role"] == "owner":
            return church["id"]
    return create_church(name=name, timezone=tz, owner_user_id=user_id)


def _ensure_church_seeded(session, church_id):
    """Seed the church from catalog only if it has no hymns yet (convergence
    after a partial run that created the church before the catalog existed)."""
    count = session.execute(
        select(func.count()).select_from(Hymn).where(Hymn.church_id == church_id)
    ).scalar_one()
    if count == 0:
        return seed_church_from_catalog(church_id, session)
    return count


def fetch_notion_hymns():
    """Read the enriched hymn database from Notion (real I/O; not unit-tested)."""
    from notion_hymns import NotionHymnsDB

    return NotionHymnsDB().list_hymns()


def run_migration(*, founder_email, church_name, timezone, hymn_pages=None):
    """Founder user + church + hymn catalog. Returns a report dict."""
    user_id = ensure_founder_user(founder_email, founder_email.split("@")[0])
    if hymn_pages is None:
        hymn_pages = fetch_notion_hymns()
    with session_scope() as session:
        catalog_report = import_hymn_catalog(session, hymn_pages)
    church_id = ensure_founder_church(user_id, church_name, timezone)
    with session_scope() as session:
        seeded = _ensure_church_seeded(session, church_id)
    return {
        "founder_user_id": str(user_id),
        "church_id": str(church_id),
        "catalog": catalog_report,
        "hymns_seeded": seeded,
    }


def _print_report(report):
    print("=== Migration report ===")
    for key, value in report.items():
        print(f"{key}: {value}")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="One-time migration: Notion -> app database (founder church)."
    )
    parser.add_argument("--founder-email", required=True)
    parser.add_argument("--church-name", required=True)
    parser.add_argument("--timezone", default="America/New_York")
    args = parser.parse_args(argv)
    init_db()
    report = run_migration(
        founder_email=args.founder_email.strip().lower(),
        church_name=args.church_name,
        timezone=args.timezone,
    )
    _print_report(report)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**
- Run: `python -m pytest tests/test_migrate_hymns.py -q`
- Expected: PASS (4 passed).

- [ ] **Step 5: Commit**
```bash
git add migrate_to_db.py tests/test_migrate_hymns.py
git commit -m "Add migrate_to_db CLI: founder user+church, Notion hymn catalog import, idempotent seed"
```

---

### Task 23: Migration — archive, usage, contacts + enrichment validation

**Files:**
- Modify: `/Users/beaubrown/Desktop/projects/church/migrate_to_db.py`
- Create (test): `/Users/beaubrown/Desktop/projects/church/tests/test_migrate_archive.py`

**Interfaces:**
- Consumes (locked): `db.session_scope()`; `repos.hymns.list_hymns`; the Task 22 functions (`ensure_founder_user`, `ensure_founder_church`, `import_hymn_catalog`, `_ensure_church_seeded`, `fetch_notion_hymns`).
- Consumes (model contract from models task): `db.models.Service(church_id, created_by, service_date_iso:str, service_date_display:str, occasion, scriptures:JSON, hymns:JSON, liturgy:JSON, sermon_title, selected_ot_ref, selected_nt_ref, include_communion:bool, saved_at:datetime)` — note Service has **both** `service_date_iso` and `service_date_display`, **no** DATE column; `db.models.HymnUsage(church_id, service_date_iso:str, hymn_number:int|None, hymn_title:str, recorded_at)`; `db.models.Contact(church_id, name, email, created_at)`; `db.models.Hymn(church_id, title, number, scripture_refs, theme, hymnary_link, audio_url)` — discrete typed columns, no `props` blob.
- Produces: `detect_truncated_liturgy(raw)->bool` (PURE, TESTED), `extract_meta(liturgy)->tuple[str,bool]` (PURE, TESTED), `_iso_to_display(iso)`, `_parse_dt(value)->datetime`, `parse_archive_page(page)->dict`, `import_services(session, church_id, created_by, pages)->dict`, `parse_usage_page(page)->dict`, `import_usage(session, church_id, pages)->dict`, `import_contacts(session, church_id, contacts)->dict`, `validate_enrichment(session, church_id)->dict` (aborts `sys.exit(2)` on empty), `fetch_notion_archive_pages`, `fetch_notion_usage_pages`, `fetch_legacy_contacts`, extended `run_migration(...)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_migrate_archive.py
import json

import pytest
from sqlalchemy import select

from migrate_to_db import (
    detect_truncated_liturgy,
    extract_meta,
    parse_archive_page,
    import_services,
    import_usage,
    import_contacts,
    validate_enrichment,
)
from db import session_scope
from db.models import Contact, Hymn, HymnUsage, Service


# ---- pure helpers -------------------------------------------------------

def test_detect_truncated_liturgy():
    assert detect_truncated_liturgy(None) is False
    assert detect_truncated_liturgy('{"call": "short"}') is False          # short + valid
    assert detect_truncated_liturgy('{"call": "short') is False            # short + invalid
    assert detect_truncated_liturgy('{"a":"' + "x" * 2000 + '"}') is False # long + valid
    assert detect_truncated_liturgy('{"a":"' + "x" * 2000) is True         # long + cut off


def test_extract_meta():
    assert extract_meta({"_sermon_title": "Grace", "_include_communion": True}) == ("Grace", True)
    assert extract_meta({"call": "x"}) == ("", False)
    assert extract_meta(None) == ("", False)


def _archive_page(occasion, saved_at, liturgy=None, service_date=None, truncate=False):
    if truncate:
        liturgy_text = '{"call": "' + "x" * 2100      # invalid JSON, over the 2000 cap
    else:
        liturgy_text = json.dumps(liturgy or {})
    props = {
        "Occasion": {"type": "rich_text", "rich_text": [{"plain_text": occasion}]},
        "Liturgy": {"type": "rich_text", "rich_text": [{"plain_text": liturgy_text}]},
        "Scriptures": {"type": "rich_text", "rich_text": [{"plain_text": "Isaiah 6:1-8"}]},
        "Hymns": {"type": "rich_text", "rich_text": [{"plain_text": "[]"}]},
        "Selected OT": {"type": "rich_text", "rich_text": []},
        "Selected NT": {"type": "rich_text", "rich_text": []},
        "Saved at": {"type": "date", "date": {"start": saved_at}},
    }
    if service_date:
        props["Service date"] = {"type": "date", "date": {"start": service_date}}
    return {"id": "pg", "properties": props}


def test_parse_archive_page_extracts_meta_and_keeps_saved_at():
    page = _archive_page(
        "Trinity Sunday",
        "2026-02-15T12:00:00Z",
        liturgy={"call": "Come", "_sermon_title": "Holy", "_include_communion": True},
        service_date="2026-02-15",
    )
    svc = parse_archive_page(page)
    assert svc["occasion"] == "Trinity Sunday"
    assert svc["sermon_title"] == "Holy"
    assert svc["include_communion"] is True
    assert svc["liturgy"] == {"call": "Come"}          # meta keys stripped
    assert svc["service_date_iso"] == "2026-02-15"
    assert svc["service_date_display"] == "February 15, 2026"
    assert svc["saved_at"] == "2026-02-15T12:00:00Z"   # carried verbatim
    assert svc["truncated"] is False


def test_parse_archive_page_flags_truncated():
    svc = parse_archive_page(_archive_page("Big Service", "2026-01-01T00:00:00Z", truncate=True))
    assert svc["truncated"] is True
    assert svc["liturgy"] == {}
    assert svc["sermon_title"] == ""


# ---- DB importers -------------------------------------------------------

def test_import_services_preserves_saved_at_and_dedupes(tmp_db, make_user, make_church):
    uid = make_user(email="beau@example.com")
    cid = make_church(name="First", owner_user_id=uid, timezone="America/New_York")
    pages = [_archive_page("Advent 1", "2025-11-30T15:00:00Z", liturgy={"call": "x"})]
    with session_scope() as session:
        first = import_services(session, cid, uid, pages)
    assert first["imported"] == 1
    with session_scope() as session:
        second = import_services(session, cid, uid, pages)
    assert second["imported"] == 0 and second["skipped"] == 1
    with session_scope() as session:
        rows = session.execute(select(Service).where(Service.church_id == cid)).scalars().all()
    assert len(rows) == 1
    assert rows[0].saved_at.year == 2025
    assert rows[0].saved_at.month == 11
    assert rows[0].saved_at.day == 30


def test_import_services_flags_truncated(tmp_db, make_user, make_church):
    uid = make_user(email="a@b.com")
    cid = make_church(name="Second", owner_user_id=uid, timezone="America/New_York")
    pages = [_archive_page("Truncated one", "2025-10-05T00:00:00Z", truncate=True)]
    with session_scope() as session:
        report = import_services(session, cid, uid, pages)
    assert report["flagged"] == 1
    assert report["flagged_rows"] == ["2025-10-05T00:00:00Z"]


def test_import_usage_dedupes(tmp_db, make_user, make_church):
    uid = make_user(email="c@d.com")
    cid = make_church(name="Third", owner_user_id=uid, timezone="America/New_York")
    page = {
        "id": "u1",
        "properties": {
            "Date": {"type": "date", "date": {"start": "2026-01-04"}},
            "Hymn number": {"type": "number", "number": 43},
            "Hymn title": {"type": "rich_text", "rich_text": [{"plain_text": "Holy, Holy, Holy"}]},
        },
    }
    with session_scope() as session:
        first = import_usage(session, cid, [page])
    with session_scope() as session:
        second = import_usage(session, cid, [page])
    assert first["imported"] == 1
    assert second["imported"] == 0 and second["skipped"] == 1
    with session_scope() as session:
        rows = session.execute(select(HymnUsage).where(HymnUsage.church_id == cid)).scalars().all()
    assert len(rows) == 1


def test_import_contacts_founder_only_and_dedupes(tmp_db, make_user, make_church):
    uid = make_user(email="e@f.com")
    cid = make_church(name="Fourth", owner_user_id=uid, timezone="America/New_York")
    contacts = [
        {"name": "Mary", "email": "Mary@example.com"},
        {"name": "Mary again", "email": "mary@example.com"},   # dup (case-insensitive)
        {"name": "No email", "email": ""},
    ]
    with session_scope() as session:
        report = import_contacts(session, cid, contacts)
    assert report["imported"] == 1 and report["skipped"] == 1
    with session_scope() as session:
        rows = session.execute(select(Contact).where(Contact.church_id == cid)).scalars().all()
    assert len(rows) == 1 and rows[0].email == "mary@example.com"


def test_validate_enrichment_passes(tmp_db, make_user, make_church):
    uid = make_user(email="g@h.com")
    cid = make_church(name="Fifth", owner_user_id=uid, timezone="America/New_York")
    with session_scope() as session:
        session.add(Hymn(
            church_id=cid, title="Amazing Grace", number=649,
            scripture_refs="John 9:25", theme="grace",
            hymnary_link=None, audio_url=None,
        ))
    with session_scope() as session:
        report = validate_enrichment(session, cid)
    assert report["with_scripture"] == 1
    assert report["sample_matches"] == 1


def test_validate_enrichment_aborts_when_empty(tmp_db, make_user, make_church):
    uid = make_user(email="i@j.com")
    cid = make_church(name="Sixth", owner_user_id=uid, timezone="America/New_York")
    with session_scope() as session:
        with pytest.raises(SystemExit) as excinfo:
            validate_enrichment(session, cid)
    assert excinfo.value.code == 2
```

- [ ] **Step 2: Run test to verify it fails**
- Run: `python -m pytest tests/test_migrate_archive.py -q`
- Expected: FAIL — `ImportError: cannot import name 'detect_truncated_liturgy' from 'migrate_to_db'` (archive/usage/contacts/validate helpers not defined yet).

- [ ] **Step 3: Write the implementation**

Edit 1 — replace the import block (top of `migrate_to_db.py`):

Old:
```python
import argparse
import sys

from sqlalchemy import func, select

from db import init_db, session_scope
from db.models import Hymn, HymnCatalog
```
New:
```python
import argparse
import json
import sys
from datetime import datetime, timezone as dtz

from sqlalchemy import func, select

from db import init_db, session_scope
from db.models import Contact, Hymn, HymnCatalog, HymnUsage, Service
```

Edit 2 — insert the new helpers and replace `run_migration` with its extended form. Find the `fetch_notion_hymns`/`run_migration` region and substitute:

Old:
```python
    return NotionHymnsDB().list_hymns()


def run_migration(*, founder_email, church_name, timezone, hymn_pages=None):
    """Founder user + church + hymn catalog. Returns a report dict."""
    user_id = ensure_founder_user(founder_email, founder_email.split("@")[0])
    if hymn_pages is None:
        hymn_pages = fetch_notion_hymns()
    with session_scope() as session:
        catalog_report = import_hymn_catalog(session, hymn_pages)
    church_id = ensure_founder_church(user_id, church_name, timezone)
    with session_scope() as session:
        seeded = _ensure_church_seeded(session, church_id)
    return {
        "founder_user_id": str(user_id),
        "church_id": str(church_id),
        "catalog": catalog_report,
        "hymns_seeded": seeded,
    }
```
New:
```python
    return NotionHymnsDB().list_hymns()


def _iso_to_display(iso):
    """YYYY-MM-DD -> 'February 15, 2026' (blank/invalid pass through)."""
    if not iso:
        return ""
    try:
        return datetime.strptime(iso[:10], "%Y-%m-%d").strftime("%B %d, %Y")
    except ValueError:
        return iso


def _parse_dt(value):
    """Parse a Notion date/timestamp string to an aware UTC datetime.

    Falls back to 'now' only when the source value is missing/unparseable.
    """
    if not value:
        return datetime.now(dtz.utc)
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        try:
            parsed = datetime.strptime(text[:10], "%Y-%m-%d")
        except ValueError:
            return datetime.now(dtz.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dtz.utc)
    return parsed


def detect_truncated_liturgy(raw):
    """True when a stored liturgy rich-text is *likely truncated*.

    Notion capped the field at 2000 chars, so fully-generated bulletins were
    already cut off before this project. A value at/near the cap that no
    longer parses as JSON is treated as truncated. Pure; no I/O.
    """
    if raw is None:
        return False
    text = raw.strip()
    if len(text) < 1990:
        return False
    try:
        json.loads(text)
        return False
    except (ValueError, TypeError):
        return True


def extract_meta(liturgy):
    """Pull (sermon_title, include_communion) out of liturgy meta keys. Pure.

    sermon_title and include_communion are not Notion columns; they were
    embedded as `_sermon_title` / `_include_communion` in the liturgy JSON.
    """
    if not isinstance(liturgy, dict):
        return "", False
    sermon_title = liturgy.get("_sermon_title") or ""
    include_communion = bool(liturgy.get("_include_communion", False))
    return str(sermon_title), include_communion


def parse_archive_page(page):
    """Notion archive page -> service dict (Service shape). Pure."""
    props = page.get("properties", {})

    def rich(name):
        prop = props.get(name, {})
        if prop.get("type") != "rich_text":
            return ""
        return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))

    def date(name):
        prop = props.get(name, {})
        if prop.get("type") != "date":
            return ""
        value = prop.get("date")
        return value.get("start", "") if value else ""

    liturgy_raw = rich("Liturgy")
    truncated = detect_truncated_liturgy(liturgy_raw)
    liturgy = {}
    if liturgy_raw and not truncated:
        try:
            liturgy = json.loads(liturgy_raw)
        except (ValueError, TypeError):
            liturgy = {}
    if not isinstance(liturgy, dict):
        liturgy = {}
    sermon_title, include_communion = extract_meta(liturgy)
    liturgy_clean = {k: v for k, v in liturgy.items() if not k.startswith("_")}

    hymns_raw = rich("Hymns")
    hymns = []
    if hymns_raw:
        try:
            hymns = json.loads(hymns_raw)
        except (ValueError, TypeError):
            hymns = []

    service_date_iso = date("Service date")
    scriptures = [s for s in rich("Scriptures").splitlines() if s.strip()]
    return {
        "service_date_iso": service_date_iso,
        "service_date_display": _iso_to_display(service_date_iso),
        "occasion": rich("Occasion"),
        "scriptures": scriptures,
        "hymns": hymns,
        "liturgy": liturgy_clean,
        "sermon_title": sermon_title,
        "selected_ot_ref": rich("Selected OT"),
        "selected_nt_ref": rich("Selected NT"),
        "include_communion": include_communion,
        "saved_at": date("Saved at"),
        "truncated": truncated,
    }


def import_services(session, church_id, created_by, pages):
    """Import archive pages under one church, preserving saved_at verbatim;
    dedupe by (church_id, saved_at, occasion). Flags truncated-liturgy rows."""
    imported = skipped = flagged = 0
    flagged_rows = []
    for page in pages:
        svc = parse_archive_page(page)
        if svc["truncated"]:
            flagged += 1
            flagged_rows.append(svc.get("saved_at") or svc.get("occasion") or "?")
        saved_at = _parse_dt(svc["saved_at"])
        exists = session.execute(
            select(Service.id).where(
                Service.church_id == church_id,
                Service.saved_at == saved_at,
                Service.occasion == svc["occasion"],
            )
        ).first()
        if exists:
            skipped += 1
            continue
        session.add(
            Service(
                church_id=church_id,
                created_by=created_by,
                service_date_iso=svc["service_date_iso"],
                service_date_display=svc["service_date_display"],
                occasion=svc["occasion"],
                scriptures=svc["scriptures"],
                hymns=svc["hymns"],
                liturgy=svc["liturgy"],
                sermon_title=svc["sermon_title"],
                selected_ot_ref=svc["selected_ot_ref"],
                selected_nt_ref=svc["selected_nt_ref"],
                include_communion=svc["include_communion"],
                saved_at=saved_at,
            )
        )
        imported += 1
    return {
        "imported": imported,
        "skipped": skipped,
        "flagged": flagged,
        "flagged_rows": flagged_rows,
    }


def parse_usage_page(page):
    """Notion usage page -> {'service_date_iso','hymn_number','hymn_title'}. Pure."""
    props = page.get("properties", {})
    number = None
    num_prop = props.get("Hymn number", {})
    if num_prop.get("type") == "number":
        number = num_prop.get("number")
    if number is not None and not isinstance(number, int):
        try:
            number = int(number)
        except (TypeError, ValueError):
            number = None
    title = ""
    title_prop = props.get("Hymn title", {})
    if title_prop.get("type") == "rich_text":
        title = "".join(t.get("plain_text", "") for t in title_prop.get("rich_text", []))
    date_iso = ""
    date_prop = props.get("Date", {})
    if date_prop.get("type") == "date":
        value = date_prop.get("date")
        date_iso = value.get("start", "") if value else ""
    return {"service_date_iso": date_iso, "hymn_number": number, "hymn_title": title}


def import_usage(session, church_id, pages):
    """Import hymn usage under one church; dedupe by
    (church_id, service_date_iso, hymn_number, hymn_title)."""
    imported = skipped = 0
    for page in pages:
        row = parse_usage_page(page)
        if not row["hymn_title"]:
            continue
        filters = [
            HymnUsage.church_id == church_id,
            HymnUsage.service_date_iso == row["service_date_iso"],
            HymnUsage.hymn_title == row["hymn_title"],
        ]
        if row["hymn_number"] is None:
            filters.append(HymnUsage.hymn_number.is_(None))
        else:
            filters.append(HymnUsage.hymn_number == row["hymn_number"])
        if session.execute(select(HymnUsage.id).where(*filters)).first():
            skipped += 1
            continue
        session.add(
            HymnUsage(
                church_id=church_id,
                service_date_iso=row["service_date_iso"],
                hymn_number=row["hymn_number"],
                hymn_title=row["hymn_title"],
            )
        )
        imported += 1
    return {"imported": imported, "skipped": skipped}


def import_contacts(session, church_id, contacts):
    """Import saved contacts into the founder church only; dedupe by email."""
    imported = skipped = 0
    for contact in contacts:
        email = (contact.get("email") or "").strip().lower()
        if not email:
            continue
        exists = session.execute(
            select(Contact.id).where(
                Contact.church_id == church_id,
                func.lower(Contact.email) == email,
            )
        ).first()
        if exists:
            skipped += 1
            continue
        session.add(
            Contact(
                church_id=church_id,
                name=(contact.get("name") or "").strip(),
                email=email,
            )
        )
        imported += 1
    return {"imported": imported, "skipped": skipped}


def validate_enrichment(session, church_id):
    """Sample-check that the founder church's hymns are enriched.

    Empty results (no hymns, none with scripture references, or a scripture
    lookup that returns nothing) are a migration *failure*, not user error:
    print a report to stderr and exit non-zero.
    """
    hymns = session.execute(
        select(Hymn).where(Hymn.church_id == church_id)
    ).scalars().all()

    def scripture_of(hymn):
        return (hymn.scripture_refs or "").strip()

    total = len(hymns)
    with_scripture = sum(1 for h in hymns if scripture_of(h))
    sample_ref = ""
    sample_matches = 0
    for hymn in hymns:
        ref = scripture_of(hymn)
        if ref:
            sample_ref = ref
            token = ref.split()[0].lower()
            sample_matches = sum(1 for h in hymns if token in scripture_of(h).lower())
            break
    report = {
        "total_hymns": total,
        "with_scripture": with_scripture,
        "sample_ref": sample_ref,
        "sample_matches": sample_matches,
    }
    if total == 0 or with_scripture == 0 or sample_matches == 0:
        print(f"MIGRATION VALIDATION FAILED: {report}", file=sys.stderr)
        sys.exit(2)
    return report


def _notion_query_all(database_id):
    """Page through a Notion database, returning raw page dicts (real I/O)."""
    import os

    import httpx

    api_key = os.getenv("NOTION_API_KEY")
    if not api_key or not database_id:
        return []
    client = httpx.Client(
        base_url="https://api.notion.com/v1",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        },
        timeout=30.0,
    )
    results = []
    cursor = None
    with client:
        while True:
            body = {"page_size": 100}
            if cursor:
                body["start_cursor"] = cursor
            response = client.post(f"/databases/{database_id}/query", json=body)
            response.raise_for_status()
            data = response.json()
            results.extend(data.get("results", []))
            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")
    return results


def fetch_notion_archive_pages():
    import os

    return _notion_query_all(os.getenv("NOTION_ARCHIVE_DATABASE_ID") or "")


def fetch_notion_usage_pages():
    import os

    return _notion_query_all(os.getenv("NOTION_USAGE_DATABASE_ID") or "")


def fetch_legacy_contacts():
    """Read the founder's saved recipients from the legacy JSON (one-time).

    Returns [] when absent — DEFAULT_CONTACTS is removed from the app, so no
    other church can inherit those personal/office emails.
    """
    import os

    path = os.path.join(os.path.dirname(__file__), "data", "email_contacts.json")
    if not os.path.isfile(path):
        return []
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (ValueError, OSError):
        return []
    contacts = data.get("contacts", [])
    return contacts if isinstance(contacts, list) else []


def run_migration(
    *,
    founder_email,
    church_name,
    timezone,
    hymn_pages=None,
    archive_pages=None,
    usage_pages=None,
    contacts=None,
):
    """Full founder migration: user, catalog, church seed, archive, usage,
    contacts, then enrichment validation. Returns a report dict. Re-runnable
    to convergence via the stable dedupe keys in each importer."""
    user_id = ensure_founder_user(founder_email, founder_email.split("@")[0])
    if hymn_pages is None:
        hymn_pages = fetch_notion_hymns()
    with session_scope() as session:
        catalog_report = import_hymn_catalog(session, hymn_pages)
    church_id = ensure_founder_church(user_id, church_name, timezone)
    with session_scope() as session:
        seeded = _ensure_church_seeded(session, church_id)
    if archive_pages is None:
        archive_pages = fetch_notion_archive_pages()
    if usage_pages is None:
        usage_pages = fetch_notion_usage_pages()
    if contacts is None:
        contacts = fetch_legacy_contacts()
    with session_scope() as session:
        services_report = import_services(session, church_id, user_id, archive_pages)
        usage_report = import_usage(session, church_id, usage_pages)
        contacts_report = import_contacts(session, church_id, contacts)
    with session_scope() as session:
        enrichment = validate_enrichment(session, church_id)
    return {
        "founder_user_id": str(user_id),
        "church_id": str(church_id),
        "catalog": catalog_report,
        "hymns_seeded": seeded,
        "services": services_report,
        "usage": usage_report,
        "contacts": contacts_report,
        "enrichment": enrichment,
    }
```

`main()` is unchanged — it already calls `init_db()` then `run_migration(...)` (which now also runs archive/usage/contacts import and aborts non-zero if enrichment validation fails) and prints the report including flagged truncated rows.

- [ ] **Step 4: Run test to verify it passes**
- Run: `python -m pytest tests/test_migrate_archive.py tests/test_migrate_hymns.py -q`
- Expected: PASS (all archive tests plus the still-green Task 22 tests).

- [ ] **Step 5: Commit**
```bash
git add migrate_to_db.py tests/test_migrate_archive.py
git commit -m "migrate_to_db: archive/usage/contacts import, truncation flagging, enrichment validation"
```

---

### Task 24: Keep-alive + backup ops (CI cron)

**Files:**
- Create: `/Users/beaubrown/Desktop/projects/church/keepalive.py`
- Create: `/Users/beaubrown/Desktop/projects/church/.github/workflows/keepalive.yml`
- Create: `/Users/beaubrown/Desktop/projects/church/.github/workflows/backup.yml`
- Create (test): `/Users/beaubrown/Desktop/projects/church/tests/test_keepalive.py`

**Interfaces:**
- Consumes: `DATABASE_URL` env var; SQLAlchemy `create_engine`/`text` (no app modules — keepalive is standalone so the CI job needs only `SQLAlchemy` + `psycopg2-binary`).
- Produces: `keepalive.ping(database_url:str)->bool`, `keepalive.main()->int`. CI workflows: `keepalive.yml` (daily `SELECT 1`), `backup.yml` (daily `pg_dump`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_keepalive.py
import pathlib

from keepalive import ping

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_ping_ok_on_sqlite(tmp_path):
    url = f"sqlite:///{tmp_path / 'keepalive.db'}"
    assert ping(url) is True


def test_ping_false_on_empty_url():
    assert ping("") is False


def test_ping_false_on_unreachable():
    assert ping("postgresql+psycopg2://u:p@127.0.0.1:1/none") is False


def test_keepalive_workflow_has_daily_cron():
    text = (ROOT / ".github" / "workflows" / "keepalive.yml").read_text(encoding="utf-8")
    assert "schedule:" in text
    assert "cron:" in text
    assert "python keepalive.py" in text


def test_backup_workflow_present():
    text = (ROOT / ".github" / "workflows" / "backup.yml").read_text(encoding="utf-8")
    assert "pg_dump" in text
    assert "schedule:" in text
```

- [ ] **Step 2: Run test to verify it fails**
- Run: `python -m pytest tests/test_keepalive.py -q`
- Expected: FAIL — `ModuleNotFoundError: No module named 'keepalive'` (module and workflow files do not exist yet).

- [ ] **Step 3: Write the implementation**

```python
# keepalive.py
#!/usr/bin/env python3
"""Keep the (free-tier Supabase) database warm.

The free Supabase project pauses after ~7 days idle, so the first visitor each
week would otherwise hit a cold/paused database. A scheduled `SELECT 1` (see
.github/workflows/keepalive.yml) keeps it awake. Standalone: imports no app
modules, so CI needs only SQLAlchemy + a Postgres driver.
"""

import os
import sys

from sqlalchemy import create_engine, text


def ping(database_url: str) -> bool:
    """Open a short-lived connection and run SELECT 1. Returns True on success."""
    if not database_url:
        return False
    try:
        engine = create_engine(database_url, pool_pre_ping=True)
        try:
            with engine.connect() as conn:
                value = conn.execute(text("SELECT 1")).scalar()
            return value == 1
        finally:
            engine.dispose()
    except Exception:
        return False


def main() -> int:
    url = os.getenv("DATABASE_URL", "")
    ok = ping(url)
    print("keepalive: OK" if ok else "keepalive: FAILED",
          file=sys.stdout if ok else sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
```

```yaml
# .github/workflows/keepalive.yml
name: keepalive
on:
  schedule:
    - cron: "17 9 * * *"   # daily at 09:17 UTC
  workflow_dispatch: {}

jobs:
  ping:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install driver
        run: pip install "SQLAlchemy>=2.0" psycopg2-binary
      - name: SELECT 1
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: python keepalive.py
```

```yaml
# .github/workflows/backup.yml
# Backups (required): Supabase Free retains NO backups, so schedule our own
# pg_dump. NOTE: GitHub artifacts are retained only ~30 days and are not a
# durable store — for real retention, add a step that uploads the dump to
# object storage (e.g. S3/GCS/Backblaze) with a longer lifecycle.
name: db-backup
on:
  schedule:
    - cron: "37 8 * * *"   # daily at 08:37 UTC
  workflow_dispatch: {}

jobs:
  dump:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: pg_dump
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: |
          sudo apt-get update && sudo apt-get install -y postgresql-client
          ts=$(date -u +%Y%m%dT%H%M%SZ)
          pg_dump "$DATABASE_URL" --no-owner --no-privileges -f "backup-$ts.sql"
          gzip "backup-$ts.sql"
      - uses: actions/upload-artifact@v4
        with:
          name: db-backup
          path: backup-*.sql.gz
          retention-days: 30
```

- [ ] **Step 4: Run test to verify it passes**
- Run: `python -m pytest tests/test_keepalive.py -q`
- Expected: PASS (5 passed).

- [ ] **Step 5: Commit**
```bash
git add keepalive.py .github/workflows/keepalive.yml .github/workflows/backup.yml tests/test_keepalive.py
git commit -m "Add keepalive.py (SELECT 1) + daily keepalive/backup GitHub Actions crons"
```

---

### Task 25: Docs — README, .env.example, manual verification checklist

**Files:**
- Modify (full rewrite): `/Users/beaubrown/Desktop/projects/church/README.md`
- Modify (full rewrite): `/Users/beaubrown/Desktop/projects/church/.env.example`
- Create: `/Users/beaubrown/Desktop/projects/church/docs/manual-verification.md`
- Create (test): `/Users/beaubrown/Desktop/projects/church/tests/test_docs.py`

**Interfaces:**
- Consumes: nothing at runtime — pure documentation. Per the "Streamlit-only / non-code" rule these are verified by a **doc-consistency pytest** (asserts required strings are present/removed), not by exercising app code.
- Produces: an updated README (two Google OAuth redirect URIs, `secrets.toml [auth]`, Supabase session-pooler `DATABASE_URL`, migration command, keep-alive), a rewritten `.env.example`, and `docs/manual-verification.md` (the deployed-URL manual checklist).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_docs.py
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def test_readme_documents_multiuser_ops():
    readme = _read("README.md")
    assert "[auth]" in readme                          # Streamlit login secrets block
    assert "/oauth2callback" in readme                 # login redirect URI (URI #1)
    assert "gmail_oauth=1" in readme                   # app-root gmail.send redirect (URI #2)
    assert "pooler.supabase.com" in readme             # session-pooler DATABASE_URL
    assert "python migrate_to_db.py" in readme         # migration command
    assert ("keep-alive" in readme.lower()) or ("keepalive" in readme.lower())


def test_env_example_updated():
    env = _read(".env.example")
    assert "DATABASE_URL" in env
    for removed in ("APP_PASSWORD", "GMAIL_APP_PASSWORD", "GMAIL_ADDRESS"):
        assert removed not in env


def test_manual_verification_checklist_exists():
    checklist = _read("docs/manual-verification.md").lower()
    assert ("oauth2callback" in checklist) or ("cors" in checklist)
    assert "invite" in checklist
    assert "login" in checklist
```

- [ ] **Step 2: Run test to verify it fails**
- Run: `python -m pytest tests/test_docs.py -q`
- Expected: FAIL — `test_readme_documents_multiuser_ops` (current README has no `[auth]`/`pooler.supabase.com`/`python migrate_to_db.py`), `test_env_example_updated` (current `.env.example` still contains `APP_PASSWORD`, `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`), and `test_manual_verification_checklist_exists` (`docs/manual-verification.md` missing → `FileNotFoundError`).

- [ ] **Step 3: Write the implementation**

Write `/Users/beaubrown/Desktop/projects/church/README.md` (full replacement):

```markdown
# Worship Service Builder — Multi-Church

Plan worship services (lectionary lookup, scripture-matched hymn suggestions,
AI-written PC(USA)-friendly liturgy, Word export, service archive, and
"exclude hymns used in the last 12 weeks"). Multiple churches share one
deployment; each church's hymnal, archive, contacts, and members are fully
isolated. People sign in with Google, then create a church (becoming owner) or
join one by invite.

## Architecture at a glance

- **Auth:** Streamlit native OIDC (`st.login` / `st.user`) with Google. Login
  uses only `openid` + `email` scopes. Sending a bulletin uses a **separate,
  opt-in** `gmail.send` grant (`google_oauth.py`).
- **Storage:** one relational database via SQLAlchemy 2.x, selected by
  `DATABASE_URL`. SQLite for local dev, Supabase Postgres in production.
- **Tenancy:** every request re-derives the caller's membership + role
  server-side (`tenancy.require_active_church`); all church data is filtered by
  the validated `church_id`.

## Local setup

```bash
pip install -r requirements.txt
cp .env.example .env          # fill in values (never commit .env)
```

`.env` holds the environment variables (`DATABASE_URL`, `OPENAI_API_KEY`,
the `GOOGLE_*` gmail.send client, and the migration-only `NOTION_*`). The
**Streamlit login** config is separate — see the `[auth]` block below.

### Streamlit login: `.streamlit/secrets.toml`

```toml
[auth]
redirect_uri = "http://localhost:8501/oauth2callback"
cookie_secret = "<strong random string>"
client_id = "<google client id>"
client_secret = "<google client secret>"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

The `redirect_uri` **must** end in `/oauth2callback` and be registered on the
Google OAuth client. It differs between dev (`localhost:8501`) and prod (the
Streamlit Cloud URL), so each environment needs its own value.

### Run

```bash
streamlit run app.py
```

## Google OAuth client — two redirect URIs

A single Google "Web application" OAuth client backs both flows and needs
**two** registered redirect URIs (each must match exactly — scheme, host, path,
trailing slash):

1. `https://<app>/oauth2callback` — for `st.login` (handled internally by
   Streamlit; never reaches app code). This is the `[auth]` `redirect_uri`.
2. `https://<app>/` (the app root) — for the manual `gmail.send` flow. The
   manual redirect carries the marker `?gmail_oauth=1`, and
   `google_oauth.should_handle_gmail_callback(...)` processes a `?code=` **only**
   when that marker is present, so it never collides with Streamlit's login
   handler. Set `GOOGLE_OAUTH_REDIRECT_URI` to this app-root value.

Enable the **Gmail API**, and while the app is unverified add each sender under
**Test users** (up to 100). A dedicated OAuth client for `gmail.send` is an
allowed, slightly safer alternative to reusing the login client.

## Database

- **Local dev:** `DATABASE_URL=sqlite:///data/app.db`.
- **Production (Supabase):** use the **session pooler** host, e.g.
  `postgresql+psycopg2://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres`.
  Do **not** use the direct `db.<ref>.supabase.co` host — it is IPv6-only on the
  free tier and unreachable from Streamlit Community Cloud's IPv4-only egress.

Store `DATABASE_URL` in Streamlit secrets (App → Settings → Secrets).

## One-time migration (Notion + legacy contacts → database)

Import the founder church's existing Notion data (hymns, archive, usage) and
saved contacts. Set `NOTION_API_KEY`, `NOTION_DATABASE_ID`,
`NOTION_ARCHIVE_DATABASE_ID`, `NOTION_USAGE_DATABASE_ID`, and `DATABASE_URL`,
then:

```bash
python migrate_to_db.py \
  --founder-email beau@example.com \
  --church-name "Conner Presbyterian" \
  --timezone America/New_York
```

It creates the founder user + church (owner), imports the enriched Notion hymns
into `hymn_catalog`, seeds the founder church's hymns, imports the archive and
hymn usage, and copies contacts into the **founder church only**. It is
**re-runnable to convergence** (idempotent) and prints a report of counts plus
any liturgy rows flagged as truncated. Enrichment is validated at the end; an
empty scripture lookup aborts the run non-zero.

## Operations

### Keep-alive (required)

The free Supabase project pauses after ~7 days idle. `.github/workflows/keepalive.yml`
runs `keepalive.py` (a `SELECT 1` against `DATABASE_URL`) daily so the first
visitor each week never hits a paused/cold database. Add `DATABASE_URL` as an
Actions secret.

### Backups (required)

Supabase Free retains no backups. `.github/workflows/backup.yml` runs a daily
`pg_dump` and uploads the compressed dump as a build artifact. Artifacts are
short-lived — for durable retention, extend the job to push the dump to object
storage.

### Limits & upgrade path

Free tier: 500 MB DB, ample connections for a handful of churches. Each church
owns an independent copy of the ~700-hymn hymnal, so catalog-wide corrections
do not propagate automatically. Scaling to many churches may require the paid
tier (which also enables direct IPv4 connections).

## Removed since single-tenant

`APP_PASSWORD`, the shared SMTP fallback (`GMAIL_ADDRESS` / `GMAIL_APP_PASSWORD`),
the `?gmail=<email>` sender mechanism, and Notion as a **runtime** dependency
(Notion is now used only by `migrate_to_db.py`).

## Deployment verification

Before relying on production, run through `docs/manual-verification.md` on the
deployed URL (the two OAuth flows, login round-trip, and invite-link survival
cannot be fully covered by unit tests).
```

Write `/Users/beaubrown/Desktop/projects/church/.env.example` (full replacement):

```bash
# Copy to .env and fill in values. Never commit .env.
# NOTE: Streamlit login lives in .streamlit/secrets.toml under [auth],
#       NOT in this file. See README ("Streamlit login").

# --- Database (required) ---
# Local dev: SQLite. Production: Supabase SESSION POOLER URL, e.g.
#   postgresql+psycopg2://postgres.<ref>:<pw>@aws-0-<region>.pooler.supabase.com:5432/postgres
DATABASE_URL=sqlite:///data/app.db

# --- OpenAI (shared across all churches; required for liturgy generation) ---
OPENAI_API_KEY=
OPENAI_MODEL=gpt-3.5-turbo

# --- Gmail "send" flow (per-user, opt-in) ---
# Web OAuth client. The redirect URI is the APP ROOT (it carries ?gmail_oauth=1),
# NOT /oauth2callback (that path is reserved for Streamlit login).
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8501/

# --- Notion (MIGRATION ONLY: python migrate_to_db.py) ---
# Not used at runtime. Needed once to import the founder church's data.
NOTION_API_KEY=
NOTION_DATABASE_ID=
NOTION_ARCHIVE_DATABASE_ID=
NOTION_USAGE_DATABASE_ID=
```

Write `/Users/beaubrown/Desktop/projects/church/docs/manual-verification.md`:

```markdown
# Manual Verification Checklist (deployed URL)

Run these on the **deployed** Streamlit Cloud URL after configuring `[auth]`,
`DATABASE_URL`, and the `GOOGLE_*` gmail.send client. These flows depend on real
redirects/cookies and cannot be fully covered by unit tests.

## 1. Gmail callback with `[auth]` CORS/XSRF enabled
- [ ] Enabling `[auth]` auto-enables Streamlit's CORS/XSRF protection. Confirm
      the manual gmail.send return to the **app root** with `?code=...&gmail_oauth=1`
      is delivered to app code (a top-level GET) and is **not** swallowed by
      Streamlit's internal `/oauth2callback` login handler.
- [ ] Click **Connect your Gmail**, complete Google consent, and confirm the
      refresh token is saved and a test bulletin sends from your own address.
- [ ] Confirm the sender is always the logged-in `st.user.email` (a spoofed
      `?gmail=` param has no effect) and that a missing/invalid OAuth `state`
      is rejected on callback.

## 2. Login round-trip
- [ ] Sign in with Google (`st.login`), reload, and confirm the 30-day cookie
      keeps you signed in.
- [ ] Sign out (`st.logout`) and confirm the app returns to the signed-out state.
- [ ] First-ever sign-in creates the user record; a user with no church sees the
      create-or-join empty state.

## 3. Invite link survives login
- [ ] Open an invite link (`?invite=CODE`) while signed out. After the Google
      login round-trip (and any gmail-connect round-trip), confirm the `?invite`
      param is preserved and the church is joined as `member`.
- [ ] Confirm an expired/revoked code fails cleanly, and accepting when already
      a member is a no-op.
```

- [ ] **Step 4: Run test to verify it passes**
- Run: `python -m pytest tests/test_docs.py -q`
- Expected: PASS (3 passed).

- [ ] **Step 5: Commit**
```bash
git add README.md .env.example docs/manual-verification.md tests/test_docs.py
git commit -m "Docs: multi-church README (two OAuth URIs, [auth], session pooler, migration, keep-alive), .env.example, manual verification checklist"
```

---

## Appendix A — Shared Interfaces (canonical signatures)

_Binding reference. If any task body disagrees with this appendix, THIS appendix wins._

# LOCKED INTERFACES — copy signatures VERBATIM. Any deviation is a bug.

These resolve all cross-layer contracts. Every task consumes/produces EXACTLY these
names, argument orders, and return shapes. IDs are `uuid.UUID`; repos accept `str|UUID`
and coerce with `uuid.UUID(str(x))` at boundaries (Streamlit passes strings).

## db/engine.py
- `Base(DeclarativeBase)`.
- `get_engine() -> Engine` — from `DATABASE_URL` env (default `sqlite:///./data/app.db`), `pool_pre_ping=True, pool_recycle=280`, process-cached in a module global `_engine`.
- `SessionLocal` — `sessionmaker`, rebound on engine (re)creation.
- `session_scope()` — **CANONICAL** contextmanager yielding `Session`; commit on success, rollback+reraise on error, always close. `get_session = session_scope` (alias).
- `init_db() -> None` — import `db.models`, `Base.metadata.create_all(get_engine())`, ensure sqlite `data/` dir.
- `reset_engine_for_tests(url: str) -> Engine` — dispose old, rebuild engine+SessionLocal against `url`, **return the Engine**.
## db/__init__.py — RE-EXPORT: `from db.engine import Base, get_engine, SessionLocal, session_scope, get_session, init_db, reset_engine_for_tests`. So `from db import init_db, session_scope` works.

## db/models.py — attribute names are LOCKED
- `User(id:Uuid pk, email:str unique not null [lowercased], google_sub:str unique nullable, name:str nullable, picture:str nullable, created_at:datetime, last_login_at:datetime nullable)`
- `Church(id:Uuid pk, name:str not null, timezone:str not null default "America/New_York", settings:JSON nullable, created_at:datetime, deleted_at:datetime nullable)`
- `Membership(church_id:Uuid fk churches.id CASCADE, user_id:Uuid fk users.id CASCADE, role:str not null CheckConstraint role in ('owner','admin','member'), created_at:datetime)` — composite PK (church_id,user_id); index `ix_memberships_user_id`.
- `Invite(id:Uuid pk, church_id:Uuid fk churches.id CASCADE, code:str unique not null, email:str nullable, role:str not null default "member", created_by:Uuid fk users.id SET NULL nullable, created_at:datetime, expires_at:datetime not null, revoked:bool default False, accepted_at:datetime nullable)` — index on code, index on church_id.
- `HymnCatalog(id:Uuid pk, title:str, number:int nullable, scripture_refs:Text nullable, theme:Text nullable, hymnary_link:str nullable, audio_url:str nullable)`
- `Hymn(id:Uuid pk, church_id:Uuid fk churches.id CASCADE not null, title:str, number:int nullable, scripture_refs:Text nullable, theme:Text nullable, hymnary_link:str nullable, audio_url:str nullable)` — index `ix_hymns_church_id`.
- `Service(id:Uuid pk, church_id:Uuid fk churches.id CASCADE not null, created_by:Uuid fk users.id SET NULL nullable, service_date_iso:str nullable, service_date_display:str nullable, occasion:str nullable, scriptures:JSON, hymns:JSON, liturgy:JSON, sermon_title:str nullable, selected_ot_ref:str nullable, selected_nt_ref:str nullable, include_communion:bool default False, saved_at:datetime not null)` — index (church_id, saved_at). NOTE: two date fields — `service_date_iso` (YYYY-MM-DD) and `service_date_display` ("February 15, 2026"). NO separate DATE column.
- `HymnUsage(id:Uuid pk, church_id:Uuid fk churches.id CASCADE not null, date_iso:str, hymn_number:int nullable, hymn_title:str, recorded_at:datetime)` — index (church_id, date_iso).
- `Contact(id:Uuid pk, church_id:Uuid fk churches.id CASCADE not null, name:str, email:str not null, created_at:datetime)`
- `GmailToken(user_id:Uuid pk fk users.id CASCADE, refresh_token:Text not null, google_email:str, created_at:datetime)`
- `OAuthState(state:str pk, user_id:Uuid fk users.id CASCADE, created_at:datetime, expires_at:datetime not null)`

## repos/users.py
- `upsert_user(email, *, google_sub=None, name=None, picture=None) -> uuid.UUID`  (lowercases email; updates name/picture/google_sub/last_login_at)
- `get_user(user_id) -> User | None`

## repos/churches.py
- `create_church(*, name, timezone, owner_user_id) -> uuid.UUID`  — ONE transaction: insert Church, insert Membership(owner), call `repos.hymns.seed_church_from_catalog(church_id, session)`. Returns **church id (UUID)**.
- `get_church(church_id) -> Church | None`  (returns None if deleted_at set)
- `list_user_churches(user_id) -> list[dict]`  — `[{"id": UUID, "name": str, "role": str}]`, non-deleted, ordered by name.
- `soft_delete_church(church_id) -> None`  — set deleted_at AND revoke all pending invites for the church.
- `update_church(church_id, *, name=None, timezone=None) -> None`

## repos/memberships.py  (arg order: user_id FIRST)
- `LastAdminError(Exception)` — defined here.
- `get_role(user_id, church_id) -> str | None`  (non-deleted church else None)
- `add_membership(user_id, church_id, role) -> None`  (no duplicate; ON CONFLICT do nothing)
- `list_members(church_id) -> list[dict]`  — JOIN users: `[{"user_id": UUID, "email": str, "name": str, "role": str}]`
- `count_admins(church_id) -> int`  (owner+admin)
- `remove_membership(user_id, church_id) -> None`  — RAISES LastAdminError if it would zero owner/admin count (row-lock via with_for_update). ALSO `UPDATE services SET created_by=NULL WHERE church_id=:cid AND created_by=:uid`.
- `set_role(user_id, church_id, role) -> None`  — same last-admin guard on demote.

## repos/invites.py
- `create_invite(*, church_id, created_by, role="member", email=None, ttl_days=7) -> str`  — returns **code** = `secrets.token_urlsafe(32)`.
- `get_invite_by_code(code) -> Invite | None`
- `accept_invite(code, user_id) -> tuple[bool, str]`  — validate: exists, not revoked, not expired, church not soft-deleted. Email-bound invites: reject if `accepted_at` already set (single-use) AND require accepting user's normalized email == invite.email. On success: add_membership (no-op if already member); for email-bound set accepted_at. Returns `(True, church_name)` or `(False, reason)`.
- `list_invites(church_id) -> list[dict]`  — active only: `[{"id": UUID, "code": str, "email": str|None, "role": str, "expires_at": datetime}]`
- `revoke_invite(invite_id) -> None`

## repos/hymns.py  (returns FLAT Notion-key dicts so worship_service.py works unchanged)
- `list_hymns(church_id) -> list[dict]`  — each: `{"id": str, "Hymn Title": str, "Hymn Number": int|None, "Scripture References": str|None, "Theme": str|None, "Hymnary.org Link": str|None, "audio_url": str|None}`
- `add_hymn(church_id, *, title, number=None, scripture_refs=None, theme=None, hymnary_link=None, audio_url=None) -> uuid.UUID`
- `update_hymn(hymn_id, church_id, **fields) -> None`  (IDOR-safe: no-op if church mismatch)
- `delete_hymn(hymn_id, church_id) -> bool`  (IDOR-safe)
- `seed_church_from_catalog(church_id, session) -> int`  — **CANONICAL** (Task 5's create_church imports THIS). Bulk INSERT hymns from hymn_catalog; returns count.

## hymn_utils.py CHANGE
- `get_property_value(hymn, prop_name)` — if `"properties" in hymn`: existing Notion logic; ELSE `return hymn.get(prop_name)` (flat-dict support).

## service_archive.py  (DB-backed; church_id on every fn; drop Notion/JSON)
- `list_saved_services(church_id) -> list[dict]`  (most recent first; dict keys: id, service_date, service_date_iso, occasion, scriptures, hymns, liturgy, sermon_title, selected_ot_ref, selected_nt_ref, include_communion, saved_at). `service_date`=display string, `service_date_iso`=iso.
- `save_service(*, church_id, created_by, service_date, service_date_iso, occasion, scriptures, hymns, liturgy, sermon_title="", selected_ot_ref="", selected_nt_ref="", include_communion=False) -> dict`  (writes service_date_display=service_date, service_date_iso=service_date_iso)
- `get_service(service_id, church_id) -> dict | None`  — None if row.church_id != church_id (IDOR fix) or malformed id.
- `update_service(service_id, church_id, *, <same kwargs as save minus created_by>) -> dict | None`
- `delete_service(service_id, church_id) -> bool`

## hymn_usage.py  (DB-backed, church-scoped; keep `_parse_date_to_iso`)
- `get_recently_used_identifiers(church_id, weeks=12) -> set[tuple[int|None, str]]`  ((number, title_lower))
- `record_usage(church_id, date_str, hymns) -> bool`  (idempotent per (church_id,date_iso,number,title))
- `is_hymn_recently_used(number, title, recent_set) -> bool`  (unchanged)

## email_contacts.py  (DB-backed per church; NO hardcoded defaults)
- `list_contacts(church_id) -> list[dict]`  — `[{"id": UUID, "name": str, "email": str}]`
- `add_contact(church_id, name, email) -> dict`
- `delete_contact(contact_id, church_id) -> bool`  (contact_id FIRST)
- `get_contacts_for_display(church_id) -> list[dict]`  (alias of list_contacts)

## auth.py
- `upsert_from_claims(claims: dict) -> uuid.UUID`  — pure helper (email/sub/name/picture) → upsert_user. UNIT-TESTED.
- `require_login() -> dict | None`  — if not `st.user.is_logged_in`: render `st.login("google")` button, return None. Else upsert once/session, cache `st.session_state["_user_id"]`. Returns `{"user_id": UUID, "email": str, "name": str, "picture": str}`.
- `current_user_id() -> uuid.UUID | None`
- `do_logout() -> None`  — `tenancy.clear_all_church_state()` then `st.logout()`.

## tenancy.py
- `CHURCH_SCOPED_STATE_KEYS: list[str]` = ["_cached_all_hymns","_hymn_title_to_info","_cached_saved_services","scripture_hymns","scripture_refs_used","opening","response","closing","open_man","resp_man","close_man","editing_service_id","load_service_id","liturgy","include_communion","custom_elements"] (plus any runtime `liturgy_*`).
- `validate_active_church(candidate_church_id, user_id) -> dict | None`  — **pure, UNIT-TESTED**: coerce candidate; `get_role(user_id, candidate)`; if role and church live → `{"church_id": UUID, "name": str, "role": str}` else None.
- `require_active_church(user_id) -> dict | None`  — reads candidate from `st.session_state.get("active_church_id")` (or captured `?church=`), calls validate_active_church; on invalid falls back to first of `list_user_churches`; None if user has no church. On active-church change vs `_active_church_rendered`, call clear_all_church_state. Returns `{"church_id","name","role"}`.
- `set_active_church(church_id) -> None`
- `clear_all_church_state() -> None`  — pop all CHURCH_SCOPED_STATE_KEYS + any `liturgy_*`.
- `is_admin(role) -> bool`  — `role in ("owner","admin")`.

## google_oauth.py  (gmail.send only; DB-backed)
- SCOPES = ["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/gmail.send"]  (userinfo.email kept ONLY to verify the connecting Google account == logged-in user).
- `save_user_token(user_id, google_email, refresh_token) -> None`  (GmailToken table)
- `is_connected(user_id) -> bool`
- `disconnect(user_id) -> None`
- `_access_token_for(user_id) -> str`
- `create_state(user_id) -> str`  (OAuthState row)
- `consume_state(state) -> uuid.UUID | None`  (single-use: delete row; TTL 600s; None if missing/expired)
- `build_auth_url(state) -> str`  — redirect_uri = app ROOT; include marker so callback only fires for gmail flow.
- `should_handle_gmail_callback(query_params: dict, is_logged_in: bool) -> bool`  — pure, UNIT-TESTED: True only if marker present, code present, AND is_logged_in.
- `exchange_code(code, expected_user_id) -> dict`  — exchange; fetch google email; RAISE if google_email.lower() != logged-in user's email; else save_user_token(expected_user_id, google_email, refresh_token).
- `send_email(user_id, to_email, subject, body_plain, *, attachment_bytes=None, attachment_filename=None) -> str | None`  — sender derived from user's GmailToken row; NO email/sender arg.

## app.py  (structure)
- Order in main(): `init_db()` → `capture_query_params()` (reads ?invite= AND ?church= into session, FIRST, before any gate) → gmail callback via `should_handle_gmail_callback(...)` (marker+login gated) → `user = require_login()` (return if None) → `active = require_active_church(user["user_id"])`; if None → render onboarding, return → else `st.navigation([Service Builder, Settings])`.
- Engine cached via `@st.cache_resource` in app (test override preserved).
- Email section: recipients from `list_contacts(church_id)`; send via `send_email(user["user_id"], ...)`.
- Remove APP_PASSWORD, `_active_gmail_user`, all `?gmail=` reads, `send_gmail` import, `NotionHymnsDB` for hymns (use `list_hymns(church_id)`).
- Empty-hymnal: explicit message when `list_hymns(church_id)` is empty (no silent free-text fallback).
- `clear_oauth_query_params()` deletes only OAUTH_QUERY_KEYS (code,state,scope,authuser,hd,prompt,gmail_oauth) — never blanket clear.

## pages/settings.py  (admin-gated; role re-checked IN EACH ACTION HELPER)
- `NotAuthorizedError(Exception)`.
- Action helpers each re-check role server-side and RAISE NotAuthorizedError if not admin/owner: `submit_profile_update(user_id, church_id, name, timezone)`, `submit_add_contact(user_id, church_id, name, email)`, `submit_delete_contact(user_id, church_id, contact_id)`, `apply_role_change(actor_user_id, church_id, target_user_id, role)`, `apply_remove_member(actor_user_id, church_id, target_user_id)`, `do_create_invite(user_id, church_id, role, email)`, `do_revoke_invite(user_id, church_id, invite_id)`. UNIT-TEST that a member actor is rejected.
- Owner-only: `transfer_ownership(actor_user_id, church_id, target_user_id)` (target→owner, actor→admin), `delete_this_church(actor_user_id, church_id)` (soft delete + reset active church). Re-check role==owner.
- Hymn management UI: add/update/delete via repos/hymns.

## migrate_to_db.py
- CLI: `--founder-email --church-name --timezone`. Reads Notion (NotionHymnsDB.list_hymns; notion_archive.list_saved_services; notion_usage). Writes founder user+church(owner); hymn_catalog from Notion; seed founder church.
- `detect_truncated_liturgy(raw: str) -> bool` (len≈2000 & json.loads fails) — pure, tested.
- `extract_meta(liturgy: dict) -> tuple[str, bool]` (_sermon_title, _include_communion) — pure, tested.
- `validate_enrichment(session, church_id) -> None` — sample scripture lookup returns matches AND enrichment populated; else raise/abort non-zero.
- Preserve saved_at; dedupe usage; contacts→founder church only. Gmail tokens NOT migrated. Idempotent. Print report.

## tests/conftest.py  (Task 1 CREATES with ALL shared fixtures; later tasks MODIFY, never re-create)
- puts repo root on sys.path.
- `tmp_db` fixture → temp sqlite via reset_engine_for_tests + init_db; yields Engine.
- `make_user(email="a@b.com", **kw) -> uuid.UUID` (returns id).
- `make_church(name="Test", timezone="America/New_York", owner_user_id=None) -> uuid.UUID`.
- `seed_catalog(n=3) -> None` (inserts HymnCatalog rows with scripture_refs+theme populated).

## .gitignore — add `data/*.db` and `.streamlit/secrets.toml`.
