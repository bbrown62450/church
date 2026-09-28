"""The active church's profile for GET /church (S `usecases/church_profile.py`; slice 2 AC6).

get_church_profile reads the church row once and derives the fields the
builder needs: the stored time zone and whether it is a real IANA name, and
the stored default translation and the one passage text actually uses.
Slices 3 and 4 add fields to ChurchProfile (and ChurchProfileOut) additively.

The route passes only ActiveChurch.id (F §1.2 rule 1) and supplies the id,
name and role itself. The layer rules are in usecases/__init__.py: no FastAPI,
Starlette or Streamlit here (test_no_streamlit_in_core.py). The repo and
scripture_fetcher are called through their modules, so a test can patch one
function.
"""
import uuid
from dataclasses import dataclass

import scripture_fetcher
from domain_errors import Forbidden
from repos import churches
from timezones import is_valid_timezone

# require_church's own 403 (api/deps.py, api/errors.forbidden): a church
# soft-deleted between the guard and this read looks exactly like one the
# caller never belonged to (2a plan clarification 8).
NO_ACCESS_MESSAGE = "You don't have access to this church."


@dataclass(frozen=True)
class ChurchProfile:
    timezone: str
    timezone_valid: bool
    bible_translation: str | None
    effective_translation: str
    effective_translation_label: str


def get_church_profile(church_id: uuid.UUID) -> ChurchProfile:
    """The profile of a live church.

    - timezone_valid: timezones.is_valid_timezone, exact and case-sensitive
      (so "america/new_york" is False, as 6a's PATCH /church will reject it).
    - bible_translation: settings["bible_translation"] when it is a non-empty
      string, else None.
    - effective_translation: that value when this deployment offers it
      (available_translations(), so "esv" only with ESV_API_KEY set), else
      "web"; effective_translation_label is its human label.

    Raises Forbidden (403 forbidden, details.reason no_church_access) when the
    church is missing or soft-deleted.
    """
    church = churches.get_church(church_id)
    if church is None:
        raise Forbidden(NO_ACCESS_MESSAGE, details={"reason": "no_church_access"})
    timezone = church["timezone"]
    stored = (church["settings"] or {}).get("bible_translation")
    bible_translation = stored if isinstance(stored, str) and stored else None
    offered = {tid for tid, _label in scripture_fetcher.available_translations()}
    effective = (bible_translation if bible_translation in offered
                 else scripture_fetcher.DEFAULT_TRANSLATION)
    return ChurchProfile(
        timezone=timezone,
        timezone_valid=is_valid_timezone(timezone),
        bible_translation=bible_translation,
        effective_translation=effective,
        effective_translation_label=scripture_fetcher.translation_label(effective),
    )
