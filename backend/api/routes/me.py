from dataclasses import asdict

from fastapi import APIRouter, Depends

from api.deps import ActiveChurch, CurrentUser, get_current_user, require_church
from api.errors import error_responses
from api.schemas import ChurchOut, ChurchProfileOut, MeOut, UserOut
from repos.churches import list_user_churches
from usecases import church_profile

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
