"""Infrastructure probes: GET /health (liveness) and GET /health/ready (readiness).

Recorded exception to F §2.2 items 1 and 4 (ops spec, API): these are probes,
not domain operations, so there is no usecase and no DomainError. The route
calls one db-layer function, db.health.database_ready(), which holds the SQL,
the try/except and the memo, and raises ApiError through db_unavailable().
Slice 1 adds its production schema-behind gate here, before the probe.
"""
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from api.errors import db_unavailable
from db.health import database_ready

router = APIRouter()


class ReadyOut(BaseModel):
    ok: bool
    db: Literal["ok"]


@router.get("/health")
def health() -> dict:
    """Liveness: never touches the database (Railway's deploy health check until slice 1)."""
    return {"ok": True}


@router.get("/health/ready", response_model=ReadyOut)
def ready() -> ReadyOut:
    """Readiness: 503 db_unavailable when the database is not reachable (keepalive.yml)."""
    if not database_ready():
        raise db_unavailable()
    return ReadyOut(ok=True, db="ok")
