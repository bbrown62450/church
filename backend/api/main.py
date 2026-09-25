"""FastAPI entry point. Run from backend/: uvicorn api.main:app --reload"""
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.errors import install_error_handlers
from api.routes import health, me
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
    app.include_router(me.router)
    return app


app = create_app()
