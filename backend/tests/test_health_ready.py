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
