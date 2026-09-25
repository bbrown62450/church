from fastapi import APIRouter, Depends

from api.deps import ActiveChurch, CurrentUser, get_current_user, require_church
from api.schemas import ChurchOut, MeOut, UserOut
from repos.churches import list_user_churches

router = APIRouter()


@router.get("/me", response_model=MeOut)
def me(user: CurrentUser = Depends(get_current_user)) -> MeOut:
    return MeOut(
        user=UserOut(id=user.id, email=user.email, name=user.name, picture=user.picture),
        churches=[ChurchOut(**church) for church in list_user_churches(user.id)],
    )


@router.get("/church", response_model=ChurchOut)
def church(active: ActiveChurch = Depends(require_church)) -> ChurchOut:
    return ChurchOut(id=active.id, name=active.name, role=active.role)
