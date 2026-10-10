"""/members: the church's people (6b spec, API; slice 6b-1).

Every member reads the list, with emails (decision 5; `require_church`);
owners and admins change a member's role and remove people (`require_admin`,
then usecases.members re-reads the caller's role under the church-row lock
and applies usecases.role_policy). Plain `def` routes, one usecase call each,
no SQL and no try/except (F §2.2 rule 1). A `user_id` is looked up as a
membership of this church: anyone else is a 404.
"""
import uuid
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from api.deps import ActiveChurch, CurrentUser, get_current_user, require_admin, require_church
from api.errors import error_responses
from usecases import members

router = APIRouter()

Role = Literal["owner", "admin", "member"]
AssignableRole = Literal["member", "admin"]


class MemberOut(BaseModel):
    user_id: uuid.UUID
    email: str
    name: str | None          # a blank stored name is null
    role: Role
    is_me: bool


class MemberListOut(BaseModel):
    items: list[MemberOut]    # the owner, admins, members; each by name (else email), then user_id


class RoleChangeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: AssignableRole      # "owner" is never assigned: ownership moves only by a transfer


class RemovedOut(BaseModel):
    removed: Literal[True] = True
    revoked_invites: int      # the invites the removal revoked, each once


@router.get("/members", response_model=MemberListOut, responses=error_responses(401, 403, 422, 503))
def list_members(church: ActiveChurch = Depends(require_church),
                 user: CurrentUser = Depends(get_current_user)) -> MemberListOut:
    return MemberListOut(items=[MemberOut(**m) for m in members.list_members(church.id, user.id)])


@router.patch("/members/{user_id}", response_model=MemberOut, responses=error_responses(401, 403, 404, 422, 503))
def change_role(user_id: uuid.UUID, payload: RoleChangeIn, church: ActiveChurch = Depends(require_admin),
                user: CurrentUser = Depends(get_current_user)) -> MemberOut:
    return MemberOut(**members.change_role(church.id, user.id, user_id, payload.role))


@router.delete("/members/{user_id}", response_model=RemovedOut, responses=error_responses(401, 403, 404, 422, 503))
def remove_member(user_id: uuid.UUID, revoke_reusable: bool = False, church: ActiveChurch = Depends(require_admin),
                  user: CurrentUser = Depends(get_current_user)) -> RemovedOut:
    """Also revokes every invite the removed person created, and with
    `revoke_reusable=true` every live reusable invite of the church."""
    return RemovedOut(revoked_invites=members.remove_member(church.id, user.id, user_id,
                                                            revoke_reusable=revoke_reusable))
