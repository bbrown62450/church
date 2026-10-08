"""The prayer library's routes (prayer library spec 2026-09-26, "API (slice
6a)"; 6a spec, API rows; slice 6a-3b).

- GET /church/prayer-library (`require_church`): the prayers in the order
  they were saved, the voice profile, and `can_edit` (the caller is an owner
  or admin).
- PUT /church/prayer-library (`require_admin`, then the role re-read under
  the church-row lock in usecases.prayer_library.save_library): a full
  replace. A saved prayer is sent back with its `id` and keeps its
  `added_at`; a new one is sent without an id.
- POST /church/prayer-library/voice-profile-draft (`require_admin`, then
  `rate_limit("ai")`, cost 1, in that order, so a member's 403 spends no
  token): a voice profile drafted from the saved prayers (75 s deadline).
  The draft is not stored. AI failures are 503, 504 or 502, as on
  /hymns/suggestions.

Plain `def` routes that each make one usecase call (F §2.2 rule 1), with no
SQL and no try/except. Request models at the top, `extra="forbid"`. The
usecase checks the spec's limits after trimming (30 prayers, 6,000
characters each, a 2,000-character profile) with the spec's messages; the
models' larger bounds only stop a body no page would send.
"""
from typing import Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from api.deps import ActiveChurch, CurrentUser, get_current_user, require_admin, require_church
from api.errors import error_responses
from api.ratelimit import rate_limit
from tenancy import is_admin
from usecases import prayer_library

router = APIRouter()

# prayer_library.PRAYER_TYPES: the eight section keys, then "other" (test_api_prayer_library pins it).
PrayerType = Literal["call_to_worship", "opening_prayer", "prayer_of_confession", "assurance",
                     "prayer_for_illumination", "prayers_of_the_people", "offertory_prayer", "benediction",
                     "other"]


class PrayerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Optional[str] = Field(None, max_length=64, description="a saved prayer's id; left out for a new prayer")
    type: str = Field(max_length=40, description='a section key or "other" ("Choose a prayer type." otherwise)')
    text: str = Field(max_length=20_000)


class PrayerLibraryIn(BaseModel):
    """The whole library: a prayer left out is removed."""

    model_config = ConfigDict(extra="forbid")

    prayers: list[PrayerIn] = Field(max_length=100)
    voice_profile: str = Field(max_length=20_000)


class PrayerOut(BaseModel):
    id: str
    type: PrayerType
    text: str
    added_at: str = Field(description='when it was first saved, e.g. "2026-10-08T16:00:00Z"')


class PrayerLibraryOut(BaseModel):
    prayers: list[PrayerOut] = Field(description="in the order they were saved")
    voice_profile: str
    can_edit: bool = Field(description="the caller is an owner or admin")


class VoiceProfileDraftOut(BaseModel):
    draft: str = Field(description="at most 2,000 characters; not stored")


@router.get("/church/prayer-library", response_model=PrayerLibraryOut,
            responses=error_responses(401, 403, 422, 503))
def read_library(church: ActiveChurch = Depends(require_church)) -> PrayerLibraryOut:
    return PrayerLibraryOut(**prayer_library.get_library(church.id, can_edit=is_admin(church.role)))


@router.put("/church/prayer-library", response_model=PrayerLibraryOut,
            responses=error_responses(401, 403, 422, 503))
def save_library(payload: PrayerLibraryIn, church: ActiveChurch = Depends(require_admin),
                 user: CurrentUser = Depends(get_current_user)) -> PrayerLibraryOut:
    return PrayerLibraryOut(**prayer_library.save_library(
        church.id, user.id, [p.model_dump() for p in payload.prayers], payload.voice_profile))


@router.post("/church/prayer-library/voice-profile-draft", response_model=VoiceProfileDraftOut,
             dependencies=[Depends(require_admin), Depends(rate_limit("ai"))],
             responses=error_responses(401, 403, 422, 429, 502, 503, 504))
def draft_voice_profile(church: ActiveChurch = Depends(require_admin)) -> VoiceProfileDraftOut:
    """A voice profile drafted from the church's saved prayers, for the admin
    to review before it replaces anything. Charged 1 `ai` token per request
    (40 per 10 min per user, 400 per day per church; F §1.8), a 422 included."""
    return VoiceProfileDraftOut(draft=prayer_library.draft_voice_profile(church.id))
