from dataclasses import asdict

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from api.deps import ActiveChurch, CurrentUser, get_current_user, require_admin, require_church
from api.errors import error_responses
from api.schemas import ChurchOut, ChurchProfileOut, MeOut, UserOut
from repos.churches import list_user_churches
from usecases import church_admin, church_profile

router = APIRouter()


@router.get("/me", response_model=MeOut, responses=error_responses(401, 422, 503))
def me(user: CurrentUser = Depends(get_current_user)) -> MeOut:
    return MeOut(
        user=UserOut(id=user.id, email=user.email, name=user.name, picture=user.picture),
        churches=[ChurchOut(**church) for church in list_user_churches(user.id)],
    )


@router.get("/church", response_model=ChurchProfileOut,
            responses=error_responses(401, 403, 422, 503))
def church(active: ActiveChurch = Depends(require_church)) -> ChurchProfileOut:
    # The usecase gets the id only (F §1.2 rule 1); id, name and role come from the guard.
    profile = church_profile.get_church_profile(active.id)
    return ChurchProfileOut(id=active.id, name=active.name, role=active.role, **asdict(profile))


class ChurchPatchIn(BaseModel):
    """PATCH /church (6a spec, Models): every field optional; omitted or null
    leaves it unchanged. "" for default_benediction means no default."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, max_length=200)
    timezone: str | None = Field(None, max_length=64)
    bible_translation: str | None = Field(None, max_length=20)
    default_hymnal: str | None = Field(None, max_length=20)
    default_benediction: str | None = Field(None, max_length=4000)


@router.patch("/church", response_model=ChurchProfileOut,
              responses=error_responses(401, 403, 422, 503))
def update_church(payload: ChurchPatchIn, active: ActiveChurch = Depends(require_admin),
                  user: CurrentUser = Depends(get_current_user)) -> ChurchProfileOut:
    """Owners and admins change the church's profile: only the fields sent,
    in one locked transaction (usecases.church_admin.update_profile). Answers
    the profile as GET /church does, with the role re-read under the lock."""
    stored = church_admin.update_profile(active.id, user.id, payload.model_dump(exclude_none=True))
    profile = church_profile.get_church_profile(active.id)
    return ChurchProfileOut(id=active.id, name=stored["name"], role=stored["role"], **asdict(profile))
