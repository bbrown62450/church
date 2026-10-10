"""Invites: joining a church with an invite code (S API; F §4.3, §7.4; AC7,
AC9), and an admin's invites (6b spec, API; slice 6b-1).

POST /invites/preview and /invites/accept are user-scoped: the caller comes
from the token and X-Church-Id is ignored. GET and POST /invites and
DELETE /invites/{invite_id} are for the church's owners and admins
(`require_admin`, then usecases.members re-reads the caller's role under the
church-row lock). An invite code is a bearer secret: it travels only in a
JSON body (the accept and preview requests, and the admin-only GET and POST
answers, which are `Cache-Control: no-store`), never in a path or a query
string, and no log line carries it (the usecases log ids and reasons only).
POST /invites takes an optional Idempotency-Key (api/idempotency.py), so a
retried create never makes a second link. Plain `def` routes: each parses,
calls one usecase and maps its answer. The fixed paths /invites/preview and
/invites/accept are declared before /invites/{invite_id}.
"""
import uuid
from dataclasses import asdict
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, ConfigDict, Field

from api.deps import ActiveChurch, CurrentUser, get_current_user, require_admin
from api.errors import error_responses
from api.idempotency import idempotency_key, run_idempotent
from api.schemas import ChurchOut, InviteAcceptOut, InviteCodeIn, InvitePreviewOut
from usecases import members, onboarding

router = APIRouter()


@router.post("/invites/preview", response_model=InvitePreviewOut,
             responses=error_responses(400, 401, 422, 503))
def preview_invite(payload: InviteCodeIn, user: CurrentUser = Depends(get_current_user)) -> InvitePreviewOut:
    """What the invite offers (church, role, expiry) without joining: writes nothing."""
    preview = onboarding.preview_invite(user_id=user.id, user_email=user.email, code=payload.code)
    return InvitePreviewOut(**asdict(preview))


@router.post("/invites/accept", response_model=InviteAcceptOut,
             responses=error_responses(400, 401, 422, 503))
def accept_invite(payload: InviteCodeIn, user: CurrentUser = Depends(get_current_user)) -> InviteAcceptOut:
    """Join the invite's church; for an existing member, a 200 that changes nothing."""
    accepted = onboarding.accept_invite(user_id=user.id, user_email=user.email, code=payload.code)
    return InviteAcceptOut(church=ChurchOut(**asdict(accepted.church)),
                           already_member=accepted.already_member, message=accepted.message)


# --- Slice 6b-1: an admin's invites ---

AssignableRole = Literal["member", "admin"]
NO_STORE = "no-store"


class InviteCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: AssignableRole = "member"
    email: str | None = Field(None, max_length=320)   # blank or null: anyone with the link
    reusable: bool = False


class InviteCreatorOut(BaseModel):
    user_id: uuid.UUID
    name: str | None
    email: str


class InviteOut(BaseModel):
    id: uuid.UUID
    code: str                 # a bearer secret, for admins only; the client builds /join?code=
    email: str | None
    role: AssignableRole
    reusable: bool
    created_at: datetime
    expires_at: datetime
    created_by: InviteCreatorOut | None   # null when the creator's account is gone


class InviteListOut(BaseModel):
    items: list[InviteOut]    # newest first


class RevokedOut(BaseModel):
    revoked: Literal[True] = True


@router.get("/invites", response_model=InviteListOut, responses=error_responses(401, 403, 422, 503))
def list_invites(response: Response, church: ActiveChurch = Depends(require_admin)) -> InviteListOut:
    response.headers["Cache-Control"] = NO_STORE
    return InviteListOut(items=[InviteOut(**i) for i in members.list_invites(church.id)])


@router.post("/invites", status_code=201, response_model=InviteOut,
             responses=error_responses(401, 403, 409, 422, 503))
def create_invite(
    payload: InviteCreateIn,
    church: ActiveChurch = Depends(require_admin),
    user: CurrentUser = Depends(get_current_user),
    key: uuid.UUID | None = Depends(idempotency_key()),
) -> Response:
    response = run_idempotent(
        user_id=user.id,
        route="/invites",
        key=key,
        payload=payload,
        status_code=201,
        church_id=church.id,
        call=lambda: InviteOut(**members.create_invite(church.id, user.id, role=payload.role, email=payload.email,
                                                       reusable=payload.reusable)),
    )
    response.headers["Cache-Control"] = NO_STORE
    return response


@router.delete("/invites/{invite_id}", response_model=RevokedOut, responses=error_responses(401, 403, 404, 422, 503))
def revoke_invite(invite_id: uuid.UUID, church: ActiveChurch = Depends(require_admin),
                  user: CurrentUser = Depends(get_current_user)) -> RevokedOut:
    members.revoke_invite(church.id, user.id, invite_id)
    return RevokedOut()
