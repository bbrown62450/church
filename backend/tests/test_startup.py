"""Startup: database target log, APP_ENV and the production guards (ops slice, F §2.6 items 1-2);
the Catena's data files read and checked (Voices V1 build review M6)."""
import logging
import shutil

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url

import api.main
import catena
from api import settings as settings_mod
from api.startup import check_app_env, describe_database
from db.engine import _make_engine
from db.schema_check import RevisionState

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
def schema_check_calls(monkeypatch):
    """Replace api.main.run_startup_checks with a spy: the first code that touches
    the database (slice 1). The list records each call's is_production."""
    calls = []

    def spy(_engine, *, is_production):
        calls.append(is_production)
        return RevisionState("0004_invites_reusable", "0004_invites_reusable", "current")

    monkeypatch.setattr(api.main, "run_startup_checks", spy)
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
def test_production_warns_when_cors_allows_only_localhost(api_env, monkeypatch, caplog, schema_check_calls,
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
    assert schema_check_calls == [True]


def test_development_on_sqlite_starts_without_errors(api_env, tmp_db, caplog):
    with caplog.at_level(logging.INFO):
        _start(api.main.create_app())
    assert [r for r in caplog.records if r.levelno >= logging.ERROR] == []


@pytest.fixture
def fresh_catena():
    """catena.load keeps each Gospel once read: start each test with none read, and leave none of
    a test's files behind."""
    catena.load.cache_clear()
    yield
    catena.load.cache_clear()


def test_startup_reads_and_checks_the_four_catena_files(api_env, tmp_db, caplog, fresh_catena):
    # Voices V1 build review M6: a broken data file fails the start (and so Railway's health
    # check on the deploy), not every GET /voices after it.
    with caplog.at_level(logging.INFO):
        _start(api.main.create_app())
    assert catena.load.cache_info().currsize == 4
    (line,) = [r.getMessage() for r in caplog.records if r.getMessage().startswith("Catena: ")]
    assert line.startswith("Catena: 816 sections, 5 checked, in ")


def test_a_broken_catena_file_refuses_to_start(api_env, tmp_db, monkeypatch, tmp_path, fresh_catena):
    for gospel in catena.GOSPELS:
        shutil.copy(catena.data_path(gospel), tmp_path / catena.data_path(gospel).name)
    broken = tmp_path / "john.json"
    broken.write_text(broken.read_text(encoding="utf-8").replace('"volume": "jn2"', '"volume": "mk"', 1),
                      encoding="utf-8")
    monkeypatch.setattr(catena, "DATA_DIR", tmp_path)
    with pytest.raises(catena.CatenaDataError, match="volume mk is not John"):
        _start(api.main.create_app())
