"""The pew voices' reader, defaults and limits (pew voices spec 2026-10-20,
"Storage").

The voices are churches.settings["pew_voices"]: a list of {"description":
str, "on": bool} in the order shown. Settings → Prayers writes them (through
usecases.prayer_library.save_library) and POST /liturgy/pews reads the
turned-on ones (usecases.pew_voices), both through read_voices, so there is
one reader.

- read_voices(settings): a missing key or a value that is not a list reads as
  the owner's five, all on (DEFAULT_VOICES); a saved empty list is no voices;
  an entry of the wrong shape or with a blank description is skipped, and a
  description longer than 300 characters (only a hand edit could store one)
  is cut to 300. Never raises.
- clean_description(text): whitespace runs as one space, trimmed.

Pure: no FastAPI, no database (tests/test_no_streamlit_in_core.py).
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

MAX_VOICES = 12
MAX_ON = 6
MAX_DESCRIPTION_CHARS = 300

# The owner's five (planning answer 4, 2026-10-20): short descriptions, no invented first names. A church that
# saved its own list keeps it even if these change later (they are read only when nothing was saved).
DEFAULT_DESCRIPTIONS: tuple[str, ...] = (
    "Sharp, very conservative, reads every word",
    "A teenager",
    "A man who rarely comes to church",
    "Parents of busy young kids",
    "Someone deeply worried about their health",
)


@dataclass(frozen=True)
class PewVoice:
    description: str
    on: bool


DEFAULT_VOICES: tuple[PewVoice, ...] = tuple(PewVoice(d, True) for d in DEFAULT_DESCRIPTIONS)


def clean_description(text: str) -> str:
    """A description as stored: every run of whitespace (line breaks too) as one space, trimmed."""
    return " ".join((text or "").split())


def read_voices(settings: Any) -> tuple[PewVoice, ...]:
    """The church's voices from its settings; the defaults when none were ever saved. Never raises."""
    stored = settings.get("pew_voices") if isinstance(settings, Mapping) else None
    if not isinstance(stored, list):
        return DEFAULT_VOICES
    voices = []
    for entry in stored:
        if not isinstance(entry, Mapping):
            continue
        description = entry.get("description")
        if isinstance(description, str) and description.strip():
            voices.append(PewVoice(description=description[:MAX_DESCRIPTION_CHARS], on=entry.get("on") is True))
    return tuple(voices)


def turned_on(voices: tuple[PewVoice, ...]) -> list[PewVoice]:
    """The voices that are on, in order, at most MAX_ON (a hand-edited row past the limit is left out)."""
    return [v for v in voices if v.on][:MAX_ON]


def voices_out(voices: tuple[PewVoice, ...]) -> list[dict]:
    return [{"description": v.description, "on": v.on} for v in voices]
