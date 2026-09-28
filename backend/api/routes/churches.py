"""POST /churches: create a church; the caller becomes its owner (S API, Idempotency).

User-scoped: the route depends on get_current_user and never on
require_church, so X-Church-Id is ignored (F §1.2). The dependencies run in
order: get_current_user, then the church_create burst guard (3 per minute per
user; F §1.8, slice 2), then idempotency_key(). So no token is 401 and spends
no token, and no token plus a malformed key is 401, not 422. A malformed key,
a body 422 and a replay each spend one (FastAPI validates the body after the
dependencies), and with none left the guard's 429 comes first. A body that is
not JSON at all is refused before any dependency runs, so it spends nothing.
The guard only stops scripted bursts: the real limit is the usecase's durable
cap (5 creates per user per rolling 24 h), which creates a minute apart reach.
The usecase runs inside run_idempotent's `call`: an Idempotency-Key replays
the first response. Neither 429 is ever stored (F §1.6): the guard's is raised
before run_idempotent, and run_idempotent never stores the cap's. Plain `def`,
because run_idempotent blocks on a lock.
"""
import uuid
from dataclasses import asdict

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from api.deps import CurrentUser, get_current_user
from api.errors import error_responses
from api.idempotency import idempotency_key, run_idempotent
from api.ratelimit import rate_limit
from api.schemas import ChurchOut, CreateChurchIn
from usecases import onboarding

router = APIRouter()


@router.post("/churches", status_code=201, response_model=ChurchOut,
             responses=error_responses(401, 422, 429, 503))
def create_church(
    payload: CreateChurchIn,
    user: CurrentUser = Depends(get_current_user),
    rl: None = Depends(rate_limit("church_create")),
    key: uuid.UUID | None = Depends(idempotency_key()),
) -> Response:
    return run_idempotent(
        user_id=user.id,
        route="/churches",
        key=key,
        payload=payload,
        status_code=201,
        call=lambda: ChurchOut(**asdict(onboarding.create_church(
            user_id=user.id, name=payload.name, timezone=payload.timezone))),
    )
