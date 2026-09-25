"""The church's service rubric: any member reads it; admins change it."""
from typing import Any, Dict

from fastapi import APIRouter, Body, Depends

from api.deps import ActiveChurch, require_admin, require_church
from api.errors import ApiError
from api.schemas import RubricOut
from repos.churches import get_church_rubric_overrides, update_church_rubric
from service_rubric import customized_keys, merge_rubric

router = APIRouter()


def _rubric_out(church_id) -> RubricOut:
    overrides = get_church_rubric_overrides(church_id)
    return RubricOut(rubric=merge_rubric(overrides), customized=customized_keys(overrides))


@router.get("/rubric", response_model=RubricOut)
def read_rubric(church: ActiveChurch = Depends(require_church)) -> RubricOut:
    return _rubric_out(church.id)


@router.patch("/rubric", response_model=RubricOut)
def change_rubric(
    patch: Dict[str, Any] = Body(...),
    church: ActiveChurch = Depends(require_admin),
) -> RubricOut:
    """Sparse update: send only what changes; null resets an item to its default."""
    try:
        update_church_rubric(church.id, patch)
    except ValueError as exc:
        raise ApiError(422, "invalid_rubric", str(exc)) from None
    return _rubric_out(church.id)
