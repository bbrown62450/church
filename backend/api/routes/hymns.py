"""The Hymns step's church-scoped routes (slice 3 spec, API; Backend 4).
Plain `def` routes that each make one usecase call with church.id only
(F §1.2 rule 1, §2.2.1). Any member may call them."""
import uuid
from dataclasses import asdict
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from api.deps import ActiveChurch, require_church
from api.errors import error_responses
from api.schemas import IsoDate, Page
from usecases import hymns

router = APIRouter()


class HymnOut(BaseModel):
    id: uuid.UUID
    hymnal: str
    title: str                          # stripped; "" when NULL
    number: Optional[int]
    link: Optional[str]                 # hymnary_link verbatim; the client renders it only via safeHttpsUrl
    scripture_refs: Optional[str]
    themes: list[str]                   # hymn_search.parse_themes(theme)
    recent_use_on: Optional[date]       # nearest usage date in the recent window; null when no date given
    text_year: Optional[int]            # the year the words were written; null = unknown
    hymnal_count: Optional[int]         # hymnals that include the text; null = unknown
    newer_than_preferred: bool          # text_year is not null and >= the rubric's prefer_before_year


def hymn_out(view: hymns.HymnView) -> HymnOut:
    return HymnOut(**asdict(view))


@router.get("/hymns", response_model=Page[HymnOut], responses=error_responses(401, 403, 422, 503))
def list_hymns(
    church: ActiveChurch = Depends(require_church),
    hymnal: Optional[str] = Query(None, max_length=20),
    q: Optional[str] = Query(None, max_length=100),
    limit: int = Query(50, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    recent_for_date: Optional[IsoDate] = Query(None),
) -> Page[HymnOut]:
    """Ordered by hymnal, number (nulls last), title, id. `q` of 1-6 digits also
    matches the number. An unknown hymnal is an empty page."""
    page = hymns.list_hymns_page(church.id, hymnal=hymnal, q=q, limit=limit, offset=offset,
                                 recent_for_date=recent_for_date)
    return Page[HymnOut](items=[hymn_out(v) for v in page.items], total=page.total,
                         limit=page.limit, offset=page.offset)
