"""The service reviewer's routes (reviewer spec, API; slice 4 spec, reviewer
amendment "Routes"; F §1.5, §1.8).

- POST /liturgy/review (church-scoped): the notes for each card and across
  the service. Always 200 once the request is valid: AI failures and an empty
  `ai` bucket come back as `ai_status` with the code notes (the declared
  deviation from F §1.5 and §1.8). The usecase charges the bucket 1 through
  `charge`, only when it calls the AI.
- POST /liturgy/revise (church-scoped, `rate_limit("ai")`, cost 1): an AI
  draft revised to address its notes. AI failures are HTTP statuses (503,
  504, 502), as on /hymns/suggestions; a draft too long to revise is 422
  prompt_invalid "This prayer is too long to revise.".

The rubric, the system prompt and the voice profile are read on the server,
never taken from the client. Plain `def` routes (F §1.8), no SQL and no
try/except (F §2.2 rule 1). Request models at the top, `extra="forbid"`.
"""
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, field_validator

from api import ratelimit
from api.deps import ActiveChurch, CurrentUser, get_current_user, require_church
from api.errors import error_responses
from api.ratelimit import rate_limit
from api.schemas import SectionKey, SermonText
from usecases import liturgy_review

router = APIRouter()

NoteTag = Literal["checklist", "rules", "voice", "read_aloud", "theology", "repetition"]
CardOrigin = Literal["ai", "typed", "archive", "default"]
Scriptures = list[Annotated[str, Field(max_length=200)]]


class ReviewCardIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section: SectionKey
    origin: CardOrigin
    text: str = Field(max_length=20_000)


class ReviewIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    occasion: str = Field("", max_length=300)
    scriptures: Scriptures = Field(default_factory=list, max_length=20)
    sermon_text: Optional[SermonText] = None     # the same resolved sermon text as generation, never ESV
    cards: list[ReviewCardIn] = Field(min_length=1, max_length=8)

    @field_validator("cards")
    @classmethod
    def one_card_per_section(cls, cards: list[ReviewCardIn]) -> list[ReviewCardIn]:
        if len({card.section for card in cards}) != len(cards):
            raise ValueError("Each section can be sent once.")
        return cards


class ReviseIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section: SectionKey
    text: str = Field(min_length=1, max_length=20_000)
    notes: list[Annotated[str, Field(min_length=1, max_length=240)]] = Field(min_length=1, max_length=3)
    occasion: str = Field("", max_length=300)
    scriptures: Scriptures = Field(default_factory=list, max_length=20)
    sermon_text: Optional[SermonText] = None

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, text: str) -> str:
        if not text.strip():
            raise ValueError("The draft is empty.")
        return text

    @field_validator("notes")
    @classmethod
    def notes_not_blank(cls, notes: list[str]) -> list[str]:
        if any(not note.strip() for note in notes):
            raise ValueError("A note is empty.")
        return notes


class NoteOut(BaseModel):
    tag: NoteTag
    text: str
    source: Literal["code", "ai"]


class CardNotesOut(BaseModel):
    section: SectionKey
    notes: list[NoteOut]          # at most 3, most important first (code notes first)


class ReviewOut(BaseModel):
    cards: list[CardNotesOut]     # one per card sent, in request order
    service_notes: list[NoteOut]  # the "Across the service" box, at most 3
    ai_status: Literal["ok", "not_configured", "busy", "timeout", "rate_limited", "error"]


class ReviseOut(BaseModel):
    text: str


def _sermon(sermon_text: Optional[SermonText]) -> Optional[tuple[str, str]]:
    return (sermon_text.ref, sermon_text.text) if sermon_text else None


def _note(note) -> NoteOut:
    return NoteOut(tag=note.tag, text=note.text, source=note.source)


@router.post("/liturgy/review", response_model=ReviewOut, responses=error_responses(401, 403, 422, 503))
def review_service(payload: ReviewIn, church: ActiveChurch = Depends(require_church),
                   user: CurrentUser = Depends(get_current_user)) -> ReviewOut:
    """Notes for every card sent and across the service: the code checks always,
    the AI review when it can run (75 s deadline; F §1.8). Charged 1 `ai` token
    only when the AI is called (40 per 10 min per user, 400 per day per church)."""
    outcome = liturgy_review.review_service(
        church_id=church.id, user_id=user.id, occasion=payload.occasion, scriptures=payload.scriptures,
        cards=[liturgy_review.ReviewCard(c.section, c.origin, c.text) for c in payload.cards],
        sermon=_sermon(payload.sermon_text),
        charge=lambda n: ratelimit.consume("ai", user_id=user.id, church_id=church.id, cost=n))
    return ReviewOut(cards=[CardNotesOut(section=c.section, notes=[_note(n) for n in c.notes])
                            for c in outcome.cards],
                     service_notes=[_note(n) for n in outcome.service_notes], ai_status=outcome.ai_status)


@router.post("/liturgy/revise", response_model=ReviseOut, dependencies=[Depends(rate_limit("ai"))],
             responses=error_responses(401, 403, 422, 429, 502, 503, 504))
def revise_section(payload: ReviseIn, church: ActiveChurch = Depends(require_church),
                   user: CurrentUser = Depends(get_current_user)) -> ReviseOut:
    """The draft revised to address these notes only; the rest is kept. Charged
    1 `ai` token per request (F §1.8)."""
    text = liturgy_review.revise_section(
        church_id=church.id, user_id=user.id, section=payload.section, text=payload.text, notes=payload.notes,
        occasion=payload.occasion, scriptures=payload.scriptures, sermon=_sermon(payload.sermon_text))
    return ReviseOut(text=text)
