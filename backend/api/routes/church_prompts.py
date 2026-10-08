"""GET and PUT /church/liturgy-prompts (6a spec, API; slice 6a-3a): the
church's liturgy prompts, the "Overall voice" (system) prompt and one per
section.

Every member reads them (`require_church`; `can_edit` says whether the caller
may change them); owners and admins replace them (`require_admin`, then the
role re-read under the church-row lock in usecases.church_admin.save_prompts).
A prompt left out, blank or equal to its default goes back to the default, so
`{"prompts": {}}` is Reset all. Plain `def` routes that each make one usecase
call (F §2.2 rule 1), with no SQL and no try/except.
"""
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from api.deps import ActiveChurch, CurrentUser, get_current_user, require_admin, require_church
from api.errors import error_responses
from tenancy import is_admin
from usecases import church_admin

router = APIRouter()

PromptKey = Literal["system", "call_to_worship", "opening_prayer", "prayer_of_confession", "assurance",
                    "prayer_for_illumination", "prayers_of_the_people", "offertory_prayer", "benediction"]


class LiturgyPromptsIn(BaseModel):
    """The church's own wording, whole: a key left out goes back to its default."""

    model_config = ConfigDict(extra="forbid")

    prompts: dict[PromptKey, Annotated[str, Field(max_length=8000)]]


class PromptFieldOut(BaseModel):
    key: PromptKey
    label: str = Field(description='"Overall voice" for the system prompt, else the section\'s label')
    default: str
    override: Optional[str] = Field(description="the church's own wording, or null when it uses the default")
    customized: bool = Field(description="override is not null")


class LiturgyPromptsOut(BaseModel):
    placeholder_help: str = Field(description="the placeholders a section prompt may use (liturgy_prompts.PLACEHOLDER_HELP)")
    can_edit: bool = Field(description="the caller is an owner or admin")
    fields: list[PromptFieldOut] = Field(description="the system prompt first, then the sections in order")


@router.get("/church/liturgy-prompts", response_model=LiturgyPromptsOut,
            responses=error_responses(401, 403, 422, 503))
def read_prompts(church: ActiveChurch = Depends(require_church)) -> LiturgyPromptsOut:
    return LiturgyPromptsOut(**church_admin.get_prompts(church.id, can_edit=is_admin(church.role)))


@router.put("/church/liturgy-prompts", response_model=LiturgyPromptsOut,
            responses=error_responses(401, 403, 422, 503))
def save_prompts(payload: LiturgyPromptsIn, church: ActiveChurch = Depends(require_admin),
                 user: CurrentUser = Depends(get_current_user)) -> LiturgyPromptsOut:
    return LiturgyPromptsOut(**church_admin.save_prompts(church.id, user.id, payload.prompts))
