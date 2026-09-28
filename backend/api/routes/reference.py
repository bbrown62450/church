"""GET /translations: the Bible translations this deployment offers (S API row 2).

User-scoped reference data: the route depends on get_current_user and never
on require_church, so X-Church-Id is ignored (F §1.2). It reads no church data.
"esv" is listed, last, only while ESV_API_KEY is set (until slice 7 this
is the configuration exception). Plain `def`, like every route here.
"""
from fastapi import APIRouter, Depends

from api.deps import CurrentUser, get_current_user
from api.errors import error_responses
from api.schemas import TranslationOut, TranslationsOut
from usecases import passages

router = APIRouter()


@router.get("/translations", response_model=TranslationsOut,
            responses=error_responses(401, 422, 503))
def translations(user: CurrentUser = Depends(get_current_user)) -> TranslationsOut:
    options = passages.translation_options()
    return TranslationsOut(
        default=options.default,
        esv_available=options.esv_available,
        items=[TranslationOut(id=tid, label=label) for tid, label in options.items],
    )
