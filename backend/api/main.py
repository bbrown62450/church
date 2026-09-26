"""FastAPI entry point. Run from backend/: uvicorn api.main:app --reload"""
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.errors import install_error_handlers
from api.logging_config import configure_logging
from api.middleware import RequestIdMiddleware, UnhandledErrorMiddleware
from api.routes import health, me, rubric
from api.settings import get_settings
from db import init_db

load_dotenv()
configure_logging(get_settings().log_level)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()   # create_all: no-op on existing tables, creates them for local SQLite
    if not get_settings().supabase_url:
        logging.getLogger(__name__).warning(
            "SUPABASE_URL is not set; every authenticated request will return 503."
        )
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
    app.include_router(rubric.router)
    return app


app = create_app()
