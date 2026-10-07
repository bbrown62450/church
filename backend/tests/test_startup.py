"""Startup: database target log, APP_ENV and the production guards (ops slice, F §2.6 items 1-2)."""
import logging

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url

import api.main
from api import settings as settings_mod
from api.startup import check_app_env, describe_database, gmail_config_problems
from db.engine import _make_engine
from db.schema_check import RevisionState
from google_oauth import GoogleOAuthConfig

SQLITE_REFUSED = "APP_ENV=production requires a PostgreSQL DATABASE_URL; refusing to start."
LOCALHOST_CORS = ("CORS_ORIGINS allows only localhost origins in production; "
                  "browsers on the real site will be blocked.")


@pytest.fixture
def api_env(monkeypatch):
    """No APP_ENV, CORS_ORIGINS or GOOGLE_* from the developer's shell; get_settings() re-reads the env."""
    for name in ("APP_ENV", "CORS_ORIGINS", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_OAUTH_REDIRECT_URI"):
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


# --- slice 5b-2: the Gmail configuration (5b spec, "Configuration and startup checks") ------------

SITE = "https://worship-service-builder.vercel.app"
CALLBACK = f"{SITE}/gmail/callback"


def _gmail(client_id="client-123", secret="secret-456", redirect=CALLBACK, origins=(SITE,), env="production"):
    return settings_mod.Settings(supabase_url="", cors_origins=origins, app_env=env, google_client_id=client_id,
                                 google_client_secret=secret, google_oauth_redirect_uri=redirect)


@pytest.mark.parametrize("settings, problems", [
    (_gmail(), []),
    (_gmail(client_id="", secret="", redirect=""), []),
    (_gmail(secret=""), ["Gmail sending is disabled until GOOGLE_CLIENT_SECRET is set."]),
    (_gmail(client_id="", redirect=""),
     ["Gmail sending is disabled until GOOGLE_CLIENT_ID and GOOGLE_OAUTH_REDIRECT_URI are set."]),
    (_gmail(redirect="https://liturgy.streamlit.app/", origins=(SITE,)),
     ["GOOGLE_OAUTH_REDIRECT_URI should be the site's address followed by /gmail/callback.",
      "GOOGLE_OAUTH_REDIRECT_URI's site is not one of CORS_ORIGINS."]),
    (_gmail(redirect="http://localhost:3000/gmail/callback", origins=("http://localhost:3000",)),
     ["GOOGLE_OAUTH_REDIRECT_URI must start with https:// in production."]),
    (_gmail(redirect="http://localhost:3000/gmail/callback", origins=("http://localhost:3000",), env="development"),
     []),
], ids=["configured", "not-configured", "one-missing", "two-missing", "streamlit-root", "http-in-production",
        "http-in-development"])
def test_gmail_configuration_problems(settings, problems):
    assert gmail_config_problems(settings) == problems


def test_the_google_config_comes_from_the_environment_and_never_shows_the_secret(api_env):
    api_env.setenv("GOOGLE_CLIENT_ID", " client-123 ")
    api_env.setenv("GOOGLE_CLIENT_SECRET", " secret-456\n")
    api_env.setenv("GOOGLE_OAUTH_REDIRECT_URI", f" {CALLBACK} ")
    settings = settings_mod.get_settings()
    assert settings.google_oauth == GoogleOAuthConfig("client-123", "secret-456", CALLBACK)
    assert "secret-456" not in repr(settings) and "secret-456" not in repr(settings.google_oauth)


@pytest.mark.parametrize("secret, lines", [
    ("secret-456", [(logging.INFO, "Gmail: configured")]),
    ("", [(logging.WARNING, "Gmail: Gmail sending is disabled until GOOGLE_CLIENT_SECRET is set.")]),
], ids=["configured", "missing-secret"])
def test_startup_logs_the_gmail_configuration(api_env, tmp_db, caplog, secret, lines):
    api_env.setenv("CORS_ORIGINS", "http://localhost:3000")
    api_env.setenv("GOOGLE_CLIENT_ID", "client-123")
    api_env.setenv("GOOGLE_CLIENT_SECRET", secret)
    api_env.setenv("GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:3000/gmail/callback")
    with caplog.at_level(logging.INFO):
        _start(api.main.create_app())
    assert [(r.levelno, r.getMessage()) for r in caplog.records if r.getMessage().startswith("Gmail: ")] == lines
    assert all("secret-456" not in r.getMessage() and "client-123" not in r.getMessage() for r in caplog.records)
