"""Infrastructure probes: GET /health (liveness) and GET /health/ready (readiness).

Recorded exception to F §2.2 items 1 and 4 (ops spec, API): these are probes,
not domain operations, so there is no usecase and no DomainError. The route
calls one db-layer function, db.health.database_ready(), which holds the SQL,
the try/except and the memo, and raises ApiError through db_unavailable().
Slice 1's production schema gate comes first: it reads the revision state the
lifespan stored on app.state (db.schema_check.run_startup_checks), so the
probe's memo can never hide a schema that is behind this release.
"""
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel

from api.errors import db_unavailable
from api.settings import get_settings
from db.health import database_ready

router = APIRouter()


class ReadyOut(BaseModel):
    ok: bool
    db: Literal["ok"]


@router.get("/health")
def health() -> dict:
    """Liveness: never touches the database. Railway's deploy health check is /health/ready (its Healthcheck Path setting)."""
    return {"ok": True}


@router.get("/health/ready", response_model=ReadyOut)
def ready(request: Request) -> ReadyOut:
    """Readiness (Railway's deploy health check and keepalive.yml): 503 db_unavailable
    when, in production, the schema is behind this release, or when the database
    is not reachable. `ahead`, `unknown` and an unset state (no lifespan) pass."""
    state = getattr(request.app.state, "schema_state", None)
    if get_settings().is_production and state is not None and state.state == "behind":
        raise db_unavailable(
            "The database schema is behind this release.",
            details={"reason": "schema_behind", "current": state.current, "head": state.head},
        )
    if not database_ready():
        raise db_unavailable()
    return ReadyOut(ok=True, db="ok")
