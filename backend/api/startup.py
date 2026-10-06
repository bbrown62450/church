"""Startup checks the API lifespan runs before anything touches the database
(F §2.6 items 1 and 2; ops slice).

- describe_database: the database target for the startup log line, never
  with the username or password.
- check_app_env: APP_ENV must be "development" or "production".
- enforce_production_guards: in production, refuse to start on anything but
  PostgreSQL (a missing DATABASE_URL would otherwise mean an ephemeral SQLite
  file on Railway), and log an ERROR when CORS_ORIGINS lists only localhost.
- gmail_config_problems and log_gmail_state (slice 5b-2; 5b spec,
  "Configuration and startup checks"): one "Gmail: configured" or "Gmail:
  not configured" line, or a WARNING for each problem with the GOOGLE_*
  variables. Never refuses to start, and never logs a value.

A RuntimeError here makes uvicorn exit with "Application startup failed"; on
Railway the new deploy then fails and the previous release keeps serving.
"""
import logging
from urllib.parse import urlsplit

from sqlalchemy.engine import URL, Engine

from api.settings import Settings

logger = logging.getLogger(__name__)

APP_ENVS = ("development", "production")
GMAIL_VARIABLES = ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_OAUTH_REDIRECT_URI")
GMAIL_CALLBACK_PATH = "/gmail/callback"
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


def gmail_config_problems(settings: Settings) -> list[str]:
    """What is wrong with the GOOGLE_* variables, as log lines (none when all
    three are set and right, or none is set: Gmail is then simply off)."""
    values = (settings.google_client_id, settings.google_client_secret, settings.google_oauth_redirect_uri)
    missing = [name for name, value in zip(GMAIL_VARIABLES, values) if not value]
    if len(missing) == len(GMAIL_VARIABLES):
        return []
    problems = []
    if missing:
        names = missing[0] if len(missing) == 1 else f"{', '.join(missing[:-1])} and {missing[-1]}"
        problems.append(f"Gmail sending is disabled until {names} {'is' if len(missing) == 1 else 'are'} set.")
    uri = settings.google_oauth_redirect_uri
    if uri:
        parts = urlsplit(uri)
        if parts.path != GMAIL_CALLBACK_PATH:
            problems.append(f"GOOGLE_OAUTH_REDIRECT_URI should be the site's address followed by {GMAIL_CALLBACK_PATH}.")
        if f"{parts.scheme}://{parts.netloc}" not in settings.cors_origins:
            problems.append("GOOGLE_OAUTH_REDIRECT_URI's site is not one of CORS_ORIGINS.")
        if settings.is_production and parts.scheme != "https":
            problems.append("GOOGLE_OAUTH_REDIRECT_URI must start with https:// in production.")
    return problems


def log_gmail_state(settings: Settings) -> None:
    problems = gmail_config_problems(settings)
    for problem in problems:
        logger.warning("Gmail: %s", problem)
    if not problems:
        logger.info("Gmail: %s", "configured" if settings.google_oauth.configured else "not configured")
