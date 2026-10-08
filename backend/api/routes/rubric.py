"""The church's service rubric: any member reads it; admins change it.

PATCH takes 6a's locking rule (slice 6a-3a; 6a spec, Semantics → PATCH
/rubric): usecases.church_admin.update_rubric takes the church-row lock and
re-reads the caller's role under it, so an admin demoted after require_admin
ran gets the role 403. Both answers carry the additive `defaults`.
"""
from typing import Any, Dict

from fastapi import APIRouter, Body, Depends

from api.deps import ActiveChurch, CurrentUser, get_current_user, require_admin, require_church
from api.errors import error_responses
from api.schemas import RubricOut
from usecases import church_admin

router = APIRouter()


@router.get("/rubric", response_model=RubricOut, responses=error_responses(401, 403, 422, 503))
def read_rubric(church: ActiveChurch = Depends(require_church)) -> RubricOut:
    return RubricOut(**church_admin.get_rubric(church.id))


@router.patch("/rubric", response_model=RubricOut, responses=error_responses(401, 403, 422, 503))
def change_rubric(
    patch: Dict[str, Any] = Body(...),
    church: ActiveChurch = Depends(require_admin),
    user: CurrentUser = Depends(get_current_user),
) -> RubricOut:
    """Sparse update: send only what changes; null resets an item to its default."""
    return RubricOut(**church_admin.update_rubric(church.id, user.id, patch))
