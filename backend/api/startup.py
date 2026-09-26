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
