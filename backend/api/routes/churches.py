"""POST /churches: create a church; the caller becomes its owner (S API,
Idempotency). Slice 6b-1 adds the church's own lifecycle below it:
POST /church/transfer-ownership and DELETE /church (the owner only,
`require_owner`) and POST /church/leave (any member, `require_church`, so its
403 means "no longer a member"); usecases.church_admin re-reads the caller's
role under the church-row lock. GET and PATCH /church stay in routes/me.py;
FastAPI serves both modules' methods on the same path.

POST /churches:

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
from typing import Literal

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field

from api.deps import ActiveChurch, CurrentUser, get_current_user, require_church, require_owner
from api.errors import error_responses
from api.idempotency import idempotency_key, run_idempotent
from api.ratelimit import rate_limit
from api.routes.members import MemberListOut, MemberOut
from api.schemas import ChurchOut, CreateChurchIn, DeletedOut
from usecases import church_admin, onboarding

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


# --- Slice 6b-1: transfer ownership, leave, delete ---


class TransferOwnershipIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: uuid.UUID


class DeleteChurchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirm_name: str = Field(max_length=200)   # the church's name, typed; compared trimmed, case included


class LeftOut(BaseModel):
    left: Literal[True] = True


@router.post("/church/transfer-ownership", response_model=MemberListOut,
             responses=error_responses(401, 403, 404, 422, 503))
def transfer_ownership(payload: TransferOwnershipIn, church: ActiveChurch = Depends(require_owner),
                       user: CurrentUser = Depends(get_current_user)) -> MemberListOut:
    """The new owner must be another member of this church; the caller becomes an admin."""
    return MemberListOut(items=[MemberOut(**m) for m in church_admin.transfer_ownership(church.id, user.id,
                                                                                         payload.user_id)])


@router.post("/church/leave", response_model=LeftOut, responses=error_responses(401, 403, 409, 422, 503))
def leave_church(church: ActiveChurch = Depends(require_church),
                 user: CurrentUser = Depends(get_current_user)) -> LeftOut:
    church_admin.leave_church(church.id, user.id)
    return LeftOut()


@router.delete("/church", response_model=DeletedOut, responses=error_responses(401, 403, 422, 503))
def delete_church(payload: DeleteChurchIn, church: ActiveChurch = Depends(require_owner),
                  user: CurrentUser = Depends(get_current_user)) -> DeletedOut:
    church_admin.delete_church(church.id, user.id, payload.confirm_name)
    return DeletedOut()
