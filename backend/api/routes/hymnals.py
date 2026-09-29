"""GET /hymnals: the active church's hymnals and its default (slice 3 spec,
API row 1 and Models; Backend 3.1-3.2). Any member; a thin route (F §2.2.1)."""
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.deps import ActiveChurch, require_church
from api.errors import error_responses
from usecases import hymns

router = APIRouter()


class HymnalOut(BaseModel):
    code: str                          # e.g. "GG2013"
    hymn_count: int
    scripture_ref_count: int           # hymns with non-blank scripture_refs


class HymnalListOut(BaseModel):
    items: list[HymnalOut]             # ORDER BY code
    default_hymnal: Optional[str]      # churches.settings["default_hymnal"] verbatim, or null
    effective_hymnal: Optional[str]    # default_hymnal if it is in items; else items[0].code; else null


@router.get("/hymnals", response_model=HymnalListOut, responses=error_responses(401, 403, 422, 503))
def list_hymnals(church: ActiveChurch = Depends(require_church)) -> HymnalListOut:
    overview = hymns.hymnal_overview(church.id)
    return HymnalListOut(
        items=[HymnalOut(code=i.code, hymn_count=i.hymn_count, scripture_ref_count=i.scripture_ref_count)
               for i in overview.items],
        default_hymnal=overview.default_hymnal,
        effective_hymnal=overview.effective_hymnal,
    )
