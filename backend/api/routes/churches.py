"""POST /churches: create a church; the caller becomes its owner (S API, Idempotency).

User-scoped: the route depends on get_current_user and never on
require_church, so X-Church-Id is ignored (F §1.2). get_current_user comes
before idempotency_key(), so no token plus a malformed key is 401, not 422.
The usecase runs inside run_idempotent's `call`: an Idempotency-Key replays
the first response, and the cap's 429 is never stored (F §1.6). Plain `def`,
because run_idempotent blocks on a lock. Slice 2 adds the church_create burst
bucket as one more dependency.
"""
import uuid
from dataclasses import asdict

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from api.deps import CurrentUser, get_current_user
from api.errors import error_responses
from api.idempotency import idempotency_key, run_idempotent
from api.schemas import ChurchOut, CreateChurchIn
from usecases import onboarding

router = APIRouter()


@router.post("/churches", status_code=201, response_model=ChurchOut,
             responses=error_responses(401, 422, 429, 503))
def create_church(
    payload: CreateChurchIn,
    user: CurrentUser = Depends(get_current_user),
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
