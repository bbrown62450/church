"""The Hymns step's church-scoped routes (slice 3 spec, API; Backend 4).
Plain `def` routes that each make one usecase call with church.id only
(F §1.2 rule 1, §2.2.1). Any member may call them."""
import uuid
from dataclasses import asdict
from datetime import date
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from api.deps import ActiveChurch, CurrentUser, get_current_user, require_church
from api.errors import error_responses
from api.ratelimit import rate_limit
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


class SlotPicks(BaseModel):
    """Exclusion hints only: never resolved, loaded or echoed, so an id from
    another church or a deleted hymn is ignored, not a 404 (S API notes; the
    declared exception to F §1.2 rules 2 and 5)."""

    model_config = ConfigDict(extra="forbid")

    opening: Optional[uuid.UUID] = None
    response: Optional[uuid.UUID] = None
    closing: Optional[uuid.UUID] = None


class HymnSuggestionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_date_iso: IsoDate
    occasion: Annotated[str, StringConstraints(max_length=300)] = ""
    scriptures: list[Annotated[str, StringConstraints(max_length=200)]] = Field(default_factory=list, max_length=20)
    selected_nt_ref: Optional[Annotated[str, StringConstraints(max_length=200)]] = None
    nt_text: Optional[Annotated[str, StringConstraints(max_length=20_000)]] = None
    hymnal: Optional[Annotated[str, StringConstraints(max_length=20)]] = None
    exclude_recent: bool = True
    current_picks: SlotPicks = Field(default_factory=SlotPicks)


class SuggestedHymnOut(HymnOut):
    source: Literal["ai", "candidates"]   # "candidates" = added by the minimum top-up; the UI ignores it


class SuggestedSlots(BaseModel):
    opening: list[SuggestedHymnOut]       # at most 5, best first
    response: list[SuggestedHymnOut]
    closing: list[SuggestedHymnOut]


class HymnSuggestionsOut(BaseModel):
    hymnal: str
    nt_ref: Optional[str]                 # the NT reference used for context
    nt_text_used: bool
    excluded_recent_count: int
    slots: SuggestedSlots


def hymn_out(view: hymns.HymnView) -> HymnOut:
    return HymnOut(**asdict(view))


@router.get("/hymns", response_model=Page[HymnOut], responses=error_responses(401, 403, 422, 503))
def list_hymns(
    church: ActiveChurch = Depends(require_church),
    hymnal: Optional[str] = Query(None, max_length=20),
    q: Optional[str] = Query(None, max_length=100),
    limit: int = Query(50, ge=1, le=2000),
    offset: int = Query(0, ge=0, le=1_000_000),        # plan clarification (owner decision 1)
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


@router.post("/hymns/suggestions", response_model=HymnSuggestionsOut,
             dependencies=[Depends(rate_limit("ai"))],
             responses=error_responses(401, 403, 422, 429, 502, 503, 504))
def suggest_hymns(payload: HymnSuggestionIn, church: ActiveChurch = Depends(require_church),
                  user: CurrentUser = Depends(get_current_user)) -> HymnSuggestionsOut:
    """AI fills each empty slot with its top pick and gives every slot 2-4 other
    ideas (owner decision 3; owner answer Q1). Charged to the `ai` bucket
    (40 per 10 min per user, 400 per day per church; F §1.8)."""
    request = hymns.SuggestionRequest(
        service_date=payload.service_date_iso, occasion=payload.occasion, scriptures=payload.scriptures,
        selected_nt_ref=payload.selected_nt_ref, nt_text=payload.nt_text, hymnal=payload.hymnal,
        exclude_recent=payload.exclude_recent, current_picks=payload.current_picks.model_dump())
    result = hymns.suggest_hymns(church.id, user.id, request)
    return HymnSuggestionsOut(
        hymnal=result.hymnal, nt_ref=result.nt_ref, nt_text_used=result.nt_text_used,
        excluded_recent_count=result.excluded_recent_count,
        slots=SuggestedSlots(**{slot: [SuggestedHymnOut(**asdict(v)) for v in views]
                                for slot, views in result.slots.items()}))
