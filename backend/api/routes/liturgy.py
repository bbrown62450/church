"""The Liturgy step's routes (slice 4 spec, API; Backend 4).

- GET /liturgy/config (user-scoped, F §1.1): the sections, custom placements,
  order of worship, communion text and limits from liturgy_config, and
  whether AI is set up (never why).
- POST /liturgy/generate (church-scoped): one result per requested section.
  AI and prompt failures come back per section inside the 200 (the declared
  deviation from F §1.5, §1.8 and §2.8); the request-level errors (401, 403,
  404 for a hymn id, 422, 429) stay HTTP errors. The usecase charges the `ai`
  bucket through `charge`, only for sections that reach the AI.

Plain `def` routes (F §1.8), no SQL and no try/except (F §2.2 rule 1).
"""
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

import liturgy_config
from api import ratelimit
from api.deps import ActiveChurch, CurrentUser, get_current_user, require_church
from api.errors import error_responses
from api.schemas import SectionKey, SermonText, SlotHymns
from integrations import openai_client
from usecases import liturgy

router = APIRouter()


class GenerateLiturgyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    occasion: str = Field("", max_length=300)
    scriptures: list[Annotated[str, Field(max_length=200)]] = Field(default_factory=list, max_length=20)
    hymns: SlotHymns = Field(default_factory=SlotHymns)
    sections: list[SectionKey] = Field(min_length=1, max_length=4)      # the UI sends exactly 1
    overrides: dict[SectionKey, Annotated[str, Field(max_length=20_000)]] = Field(default_factory=dict)
    sermon_text: Optional[SermonText] = None     # the effective NT reading and its text, never ESV


class SectionError(BaseModel):
    code: Literal["ai_not_configured", "ai_busy", "ai_timeout", "ai_upstream_error", "prompt_invalid"]
    message: str


class SectionResult(BaseModel):
    section: SectionKey
    status: Literal["override", "generated", "error"]
    text: Optional[str]            # None only when status == "error"
    error: Optional[SectionError]


class GenerateLiturgyOut(BaseModel):
    results: list[SectionResult]   # one per requested section, request order, duplicates removed


class SectionSpecOut(BaseModel):
    key: SectionKey
    label: str
    default_enabled: bool
    rows: int
    pastor_copy_only: bool
    hint: Optional[str]


class PlacementOut(BaseModel):
    key: str
    label: str


class OutlineItemOut(BaseModel):
    kind: Literal["section", "landmark", "communion"]
    key: str                        # a section key, or a landmark key (first_hymn, ot_reading, ...)
    label: str                      # the docx heading text (the first reading's is 5a's "First Reading")
    value_source: Literal["none", "hymn_opening", "hymn_response", "hymn_closing",
                          "reading_ot", "reading_nt", "sermon_title", "fixed"]
    fixed_text: Optional[str]       # "Apostles' Creed" for affirmation_of_faith
    anchors_after: list[str]        # placement keys whose custom elements follow this item


class CommunionBlockOut(BaseModel):
    style: Literal["heading1", "heading2", "text", "response", "blank"]
    text: str


class CommunionOut(BaseModel):
    title: str
    toggle_label: str
    default_rule: Literal["first_sunday_of_month"]
    blocks: list[CommunionBlockOut]


class LiturgyLimitsOut(BaseModel):
    max_section_text: int
    max_sermon_title: int
    max_custom_elements: int
    max_custom_label: int
    max_custom_text: int
    max_sections_per_request: int


class LiturgyConfigOut(BaseModel):
    sections: list[SectionSpecOut]          # SECTION_ORDER
    custom_placements: list[PlacementOut]   # the 17, in app.py's order
    outline: list[OutlineItemOut]
    assurance_response: str                 # "People: Thanks be to God! Amen."
    default_benediction_fallback: str       # "Halverson"
    communion: CommunionOut
    limits: LiturgyLimitsOut
    ai_available: bool                      # openai_client.ai_available(); never why


@router.get("/liturgy/config", response_model=LiturgyConfigOut, responses=error_responses(401, 422, 503))
def get_liturgy_config(user: CurrentUser = Depends(get_current_user)) -> LiturgyConfigOut:
    lc = liturgy_config
    return LiturgyConfigOut(
        sections=[SectionSpecOut(key=s.key, label=s.label, default_enabled=s.default_enabled, rows=s.rows,
                                 pastor_copy_only=s.pastor_copy_only, hint=s.hint) for s in lc.SECTIONS],
        custom_placements=[PlacementOut(key=key, label=label) for key, label in lc.CUSTOM_PLACEMENTS],
        outline=[OutlineItemOut(**item) for item in lc.outline_as_json()],
        assurance_response=lc.ASSURANCE_RESPONSE,
        default_benediction_fallback=lc.DEFAULT_BENEDICTION_FALLBACK,
        communion=CommunionOut(title=lc.COMMUNION_TITLE, toggle_label=lc.COMMUNION_TOGGLE_LABEL,
                               default_rule="first_sunday_of_month",
                               blocks=[CommunionBlockOut(style=b.style, text=b.text) for b in lc.COMMUNION_BLOCKS]),
        limits=LiturgyLimitsOut(**vars(lc.LIMITS)),
        ai_available=openai_client.ai_available(),
    )


def _hymn(ref) -> Optional[liturgy.HymnRefData]:
    if ref is None:
        return None
    return liturgy.HymnRefData(hymn_id=ref.hymn_id, title=ref.title, number=ref.number, hymnal=ref.hymnal)


@router.post("/liturgy/generate", response_model=GenerateLiturgyOut,
             responses=error_responses(401, 403, 404, 422, 429, 503))
def generate_liturgy(payload: GenerateLiturgyIn, church: ActiveChurch = Depends(require_church),
                     user: CurrentUser = Depends(get_current_user)) -> GenerateLiturgyOut:
    """Typed text comes back as sent; the rest is written by the AI, at most 4
    sections at a time. Charged to the `ai` bucket per section that reaches the
    AI (40 per 10 min per user, 400 per day per church; F §1.8)."""
    sermon = (payload.sermon_text.ref, payload.sermon_text.text) if payload.sermon_text else None
    outcomes = liturgy.generate_liturgy(
        church_id=church.id, user_id=user.id, occasion=payload.occasion, scriptures=payload.scriptures,
        hymns={slot: _hymn(getattr(payload.hymns, slot)) for slot in ("opening", "response", "closing")},
        sections=payload.sections, overrides=payload.overrides, sermon=sermon,
        charge=lambda n: ratelimit.consume("ai", user_id=user.id, church_id=church.id, cost=n))
    return GenerateLiturgyOut(results=[
        SectionResult(section=o.section, status=o.status, text=o.text,
                      error=SectionError(code=o.error_code, message=o.error_message) if o.error_code else None)
        for o in outcomes])
