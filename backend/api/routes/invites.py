"""Joining a church with an invite code (S API; F §4.3, §7.4; AC7, AC9).

Both routes are user-scoped: the caller comes from the token and X-Church-Id is
ignored. The code travels only in the JSON body, never in a path or a query
string, and no log line carries it (the usecase logs ids and reasons only).
Plain `def` routes: each parses, calls one usecase and maps its dataclass.

Slice 6b adds GET/POST /invites and DELETE /invites/{invite_id} to this module,
below these two: the fixed paths /invites/preview and /invites/accept must stay
declared before any /invites/{invite_id} route.
"""
from dataclasses import asdict

from fastapi import APIRouter, Depends

from api.deps import CurrentUser, get_current_user
from api.errors import error_responses
from api.schemas import ChurchOut, InviteAcceptOut, InviteCodeIn, InvitePreviewOut
from usecases import onboarding

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
