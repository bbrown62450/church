"""FastAPI entry point. Run from backend/: uvicorn api.main:app --reload"""
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from api.errors import install_error_handlers
from api.logging_config import configure_logging
from api.middleware import RequestIdMiddleware, UnhandledErrorMiddleware
from api.routes import (churches, health, hymnals, hymns, invites, lectionary, me, reference, rubric,
                        scripture)
from api.settings import get_settings
from api.startup import check_app_env, describe_database, enforce_production_guards
from db import get_engine
from db.schema_check import run_startup_checks
from integrations import openai_client

load_dotenv()
configure_logging(get_settings().log_level)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    check_app_env(settings.app_env)
    engine = get_engine()                                   # creating the engine opens no connection
    logger.info("Database: %s", describe_database(engine.url))
    enforce_production_guards(settings, engine)             # before anything touches the database
    # Alembic owns the schema (F §3.3): no create_all here. Logs, never raises;
    # /health/ready reads the state (Task 12's gate).
    app.state.schema_state = run_startup_checks(engine, is_production=settings.is_production)
    if not settings.supabase_url:
        logger.warning("SUPABASE_URL is not set; every authenticated request will return 503.")
    openai_client.log_startup_state()                       # one "AI: ..." line, never the key
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    # No trailing-slash redirects: a cross-origin 307 drops Authorization (F §1.1).
    app = FastAPI(title="Worship Service Builder API", lifespan=lifespan, redirect_slashes=False)
    # The last middleware added is the outermost: CORS → RequestId → UnhandledError
    # → GZip (F §2.5), so CORS decorates the 500s that UnhandledError produces, and
    # GZip (slice 3; GET /hymns?limit=2000 is ~200 KB of JSON) is innermost.
    app.add_middleware(GZipMiddleware, minimum_size=1024)
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
    app.include_router(churches.router)
    app.include_router(invites.router)
    app.include_router(reference.router)
    app.include_router(lectionary.router)
    app.include_router(scripture.router)
    app.include_router(hymnals.router)
    app.include_router(hymns.router)
    return app


app = create_app()
