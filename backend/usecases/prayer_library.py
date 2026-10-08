"""The prayer library's usecases (prayer library spec 2026-09-26, "API (slice
6a)"; 6a spec, Semantics → PUT /church/prayer-library; slice 6a-3b).

The library is churches.settings["prayer_library"]: {"prayers": [{"id",
"type", "text", "added_at"}], "voice_profile": str}, read through the one
reader, prayer_library.read_library (slice 4), so a missing or junk value
reads as the empty library here as it does for the liturgy writer.

- get_library(church_id, *, can_edit): GET /church/prayer-library, the
  prayers in the order they were saved.
- save_library(church_id, actor_id, prayers, voice_profile): PUT, a full
  replace in one session that starts with lock_and_read_actor and
  require_admin_role (an admin demoted meanwhile gets the role 403 before the
  body is looked at), then clean_library, then the ids, then merge_settings
  in that session, so every other settings key stays as it was.

The prayers are the pastor's own words and may be private: no log line here
holds a prayer's text or the voice profile, at any level. No FastAPI,
Starlette or Streamlit (tests/test_no_streamlit_in_core.py).
"""
from __future__ import annotations

import datetime
import uuid
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Optional

import prayer_library
from db import session_scope
from domain_errors import InvalidInput
from repos import churches
from usecases.church_admin import require_admin_role
from usecases.members import lock_and_read_actor

TEXT_REQUIRED = "Prayer text is required."
TEXT_TOO_LONG = "This prayer is too long (6,000 characters at most)."
TYPE_REQUIRED = "Choose a prayer type."
TOO_MANY = "You can keep up to 30 prayers."
PROFILE_TOO_LONG = "The voice profile is too long (2,000 characters at most)."


def _utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def clean_text(text: str) -> str:
    """A prayer's or the profile's text as stored: CRLF line ends as LF, trimmed."""
    return text.replace("\r\n", "\n").strip()


def library_out(library: prayer_library.PrayerLibrary, *, can_edit: bool) -> dict:
    """GET and PUT's answer: the prayers in saved order, the profile, and whether the caller may edit."""
    return {"prayers": [{"id": p.id, "type": p.type, "text": p.text, "added_at": p.added_at}
                        for p in library.prayers],
            "voice_profile": library.voice_profile, "can_edit": can_edit}


def get_library(church_id: uuid.UUID, *, can_edit: bool) -> dict:
    """GET /church/prayer-library (any member)."""
    church = churches.get_church(church_id)
    return library_out(prayer_library.read_library((church or {}).get("settings")), can_edit=can_edit)


def clean_library(prayers: Sequence[Mapping[str, Any]], voice_profile: str) -> tuple[list[dict], str]:
    """PUT's body, normalized and checked (pure). Each row is {"id"?, "type",
    "text"}; texts and the profile are cleaned (clean_text) and the limits
    counted after that. The first failure raises InvalidInput naming its
    field: "prayers" for more than 30, then row by row "prayers.<i>.type" and
    "prayers.<i>.text", then "voice_profile". Returns ([{"id", "type",
    "text"}], profile); "id" is what was sent (or None)."""
    if len(prayers) > prayer_library.MAX_PRAYERS:
        raise InvalidInput(TOO_MANY, field="prayers")
    rows = []
    for i, row in enumerate(prayers):
        if row.get("type") not in prayer_library.PRAYER_TYPES:
            raise InvalidInput(TYPE_REQUIRED, field=f"prayers.{i}.type")
        text = clean_text(row.get("text") or "")
        if not text:
            raise InvalidInput(TEXT_REQUIRED, field=f"prayers.{i}.text")
        if len(text) > prayer_library.MAX_PRAYER_CHARS:
            raise InvalidInput(TEXT_TOO_LONG, field=f"prayers.{i}.text")
        rows.append({"id": row.get("id"), "type": row["type"], "text": text})
    profile = clean_text(voice_profile)
    if len(profile) > prayer_library.MAX_PROFILE_CHARS:
        raise InvalidInput(PROFILE_TOO_LONG, field="voice_profile")
    return rows, profile


def _is_uuid(value: Any) -> bool:
    try:
        return isinstance(value, str) and str(uuid.UUID(value)) == value
    except ValueError:
        return False


def with_ids(rows: Sequence[Mapping[str, Any]], stored: prayer_library.PrayerLibrary, *, added_at: str,
             new_id: Callable[[], uuid.UUID]) -> list[dict]:
    """The rows to store, each with its id and added_at: a row whose id is a
    stored prayer's keeps that id and its added_at; a new row, and a row whose
    id matches no stored prayer or repeats an earlier row's, gets a fresh id
    and `added_at` (prayer library spec, PUT semantics)."""
    known = {p.id: p.added_at for p in stored.prayers if _is_uuid(p.id)}
    seen: set[str] = set()
    out = []
    for row in rows:
        ident: Optional[str] = row.get("id")
        if ident in known and ident not in seen:
            kept = {"id": ident, "added_at": known[ident]}
        else:
            kept = {"id": str(new_id()), "added_at": added_at}
        seen.add(kept["id"])
        out.append({"id": kept["id"], "type": row["type"], "text": row["text"], "added_at": kept["added_at"]})
    return out


def save_library(church_id: uuid.UUID, actor_id: uuid.UUID, prayers: Sequence[Mapping[str, Any]],
                 voice_profile: str, *, now: Callable[[], datetime.datetime] = _utc_now,
                 new_id: Callable[[], uuid.UUID] = uuid.uuid4) -> dict:
    """PUT /church/prayer-library: replace the church's library, under the
    church-row lock with the caller's role re-read, keeping every other
    settings key. Returns the library as get_library does."""
    with session_scope() as s:
        role = lock_and_read_actor(s, church_id, actor_id)
        require_admin_role(role)
        rows, profile = clean_library(prayers, voice_profile)
        locked = churches.lock_church(s, church_id)          # the row lock_and_read_actor holds
        stored = prayer_library.read_library(locked.settings if locked is not None else None)
        value = {"prayers": with_ids(rows, stored, added_at=now().strftime("%Y-%m-%dT%H:%M:%SZ"), new_id=new_id),
                 "voice_profile": profile}
        churches.merge_settings(church_id, {"prayer_library": value}, session=s)
    return library_out(prayer_library.read_library({"prayer_library": value}), can_edit=True)
