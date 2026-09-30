"""The prayer library's reader and example chooser (prayer library spec
2026-09-26 §Data and §Writer hook; slice 4 spec, Interfaces 6a).

The library is churches.settings["prayer_library"]:
{"prayers": [{"id", "type", "text", "added_at"}], "voice_profile": str}.
Slice 4a only reads it (the liturgy writer's voice hook); 6a's Prayers page
writes it and imports these limits and this reader, so there is one reader.

- read_library(settings): a missing key or a value of the wrong shape reads
  as the empty library; a prayer entry of the wrong shape is skipped. Never
  raises.
- choose_example(library, section, *, choose): one uniformly random prayer
  of that section's type, cut to MAX_EXAMPLE_CHARS, or None. An "other"
  prayer is never an example.

Pure: no FastAPI, no database (tests/test_no_streamlit_in_core.py).
"""
from __future__ import annotations

import random
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Optional

from liturgy_config import SECTION_ORDER

PRAYER_TYPES: tuple[str, ...] = (*SECTION_ORDER, "other")
MAX_PRAYERS = 30
MAX_PRAYER_CHARS = 6_000
MAX_PROFILE_CHARS = 2_000
MAX_EXAMPLE_CHARS = 3_000       # the writer's cut (prayer library spec, Writer hook "Budget")


@dataclass(frozen=True)
class Prayer:
    id: str
    type: str          # a SectionKey or "other"
    text: str
    added_at: str


@dataclass(frozen=True)
class PrayerLibrary:
    prayers: tuple[Prayer, ...]
    voice_profile: str


EMPTY_LIBRARY = PrayerLibrary(prayers=(), voice_profile="")


def _prayer(entry: Any) -> Optional[Prayer]:
    if not isinstance(entry, Mapping):
        return None
    kind, text = entry.get("type"), entry.get("text")
    if kind not in PRAYER_TYPES or not isinstance(text, str):
        return None
    ident, added = entry.get("id"), entry.get("added_at")
    return Prayer(id=ident if isinstance(ident, str) else "", type=kind, text=text,
                  added_at=added if isinstance(added, str) else "")


def read_library(settings: Any) -> PrayerLibrary:
    """The church's library from its settings; the empty library when it is
    missing or of the wrong shape. Never raises."""
    stored = settings.get("prayer_library") if isinstance(settings, Mapping) else None
    if not isinstance(stored, Mapping):
        return EMPTY_LIBRARY
    entries = stored.get("prayers", [])
    if not isinstance(entries, list):
        return EMPTY_LIBRARY
    profile = stored.get("voice_profile", "")
    prayers = tuple(p for p in (_prayer(entry) for entry in entries) if p is not None)
    return PrayerLibrary(prayers=prayers, voice_profile=profile if isinstance(profile, str) else "")


def choose_example(library: PrayerLibrary, section: str, *,
                   choose: Callable[[Sequence[str]], str] = random.choice) -> Optional[str]:
    """A random prayer whose type is `section` (never "other"), stripped and
    then cut to MAX_EXAMPLE_CHARS (so leading blank lines never use up the
    budget); None when the library has none of that type."""
    if section == "other":
        return None
    texts = [p.text for p in library.prayers if p.type == section and p.text.strip()]
    if not texts:
        return None
    return choose(texts).strip()[:MAX_EXAMPLE_CHARS]
