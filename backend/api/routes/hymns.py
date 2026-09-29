"""The Hymns step's church-scoped routes (slice 3 spec, API; Backend 4).
Plain `def` routes that each make one usecase call with church.id only
(F §1.2 rule 1, §2.2.1). Any member may call them."""
import uuid
from dataclasses import asdict
from datetime import date
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

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


class ScriptureMatchIn(BaseModel):
    """POST /hymns/scripture-matches. Refs blank after trimming are the usecase's
    422 "Enter at least one scripture reference." (fields.refs)."""

    model_config = ConfigDict(extra="forbid")

    refs: list[Annotated[str, StringConstraints(max_length=200)]] = Field(default_factory=list, max_length=20)
    hymnal: Optional[Annotated[str, StringConstraints(max_length=20)]] = None   # null = effective_hymnal
    recent_for_date: Optional[IsoDate] = None
    limit_per_ref: int = Field(50, ge=1, le=100)
    max_results: int = Field(20, ge=1, le=100)


class HymnMatchOut(HymnOut):
    strength: Literal["passage", "chapter"]
    matched_refs: list[str]            # the query references (after the " or " split) that matched


class ScriptureMatchesOut(BaseModel):
    hymnal: Optional[str]
    refs_used: list[str]               # trimmed, non-blank, after the " or " split, in order
    unparsed_refs: list[str]           # query refs that could not be read as scripture
    total_matched: int                 # before max_results truncation
    items: list[HymnMatchOut]          # passage tier first, then chapter tier


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


@router.post("/hymns/scripture-matches", response_model=ScriptureMatchesOut,
             responses=error_responses(401, 403, 422, 503))
def scripture_matches(payload: ScriptureMatchIn,
                      church: ActiveChurch = Depends(require_church)) -> ScriptureMatchesOut:
    found = hymns.scripture_matches(church.id, refs=payload.refs, hymnal=payload.hymnal,
                                    recent_for_date=payload.recent_for_date,
                                    limit_per_ref=payload.limit_per_ref, max_results=payload.max_results)
    return ScriptureMatchesOut(hymnal=found.hymnal, refs_used=found.refs_used,
                               unparsed_refs=found.unparsed_refs, total_matched=found.total_matched,
                               items=[HymnMatchOut(**asdict(m)) for m in found.items])
