"""What the Word files print and how they are named (slice 5a spec, Backend
"service_output.py"; F §1.9, §2.3). Pure: no database, FastAPI or Streamlit.

- service_date_display: the date line, '%B %d, %Y' with English months
  ("October 04, 2026"), exactly as Streamlit printed it (app.py:430); the only
  date-display function (5b uses it too).
- docx_filename, content_disposition, DOCX_MIME: the download's name and
  headers (app.py:1072-1088; F §1.9).
- VARIANTS: both copies print the sermon title; only the pastor's copy prints
  Prayers of the People (owner decision 4).
- hymn_line: "Title — #138", or just the title when there is no number (no
  "#None").
- resolve_doc_readings: slice 2's resolve_readings, so the file prints the
  readings the Bulletin readings selects show.
- is_legacy_error_placeholder: Streamlit's stored "[Error generating ...]"
  texts, never printed.
- ResolvedHymn, CustomElement, ResolvedService and render_docx (Task 2): a
  service whose hymns are resolved, rendered by worship_service.build_docx.
- normalize_date_iso, coerce_number, StoredHymn, stored_hymn_entries,
  slot_map and stored_hymns (slice 5a-2): reading a saved service's stored
  date and hymns tolerantly, and the 3-slot list a save writes (F §6.2).
"""
from __future__ import annotations

import datetime
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal, Optional
from urllib.parse import quote

import scripture_refs

MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December")
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

Variant = Literal["bulletin", "pastor"]
VARIANTS: dict[str, dict[str, bool]] = {
    "bulletin": {"include_sermon": True, "include_prayers_of_the_people": False},
    "pastor": {"include_sermon": True, "include_prayers_of_the_people": True},
}

LEGACY_ERROR_PREFIXES = ("[Error generating ", "[Configure OPENAI_API_KEY to generate ",
                         "[Your OPENAI_API_KEY contains invalid")


def service_date_display(d: datetime.date) -> str:
    """'%B %d, %Y' without the locale: date(2026, 10, 4) is "October 04, 2026"."""
    return f"{MONTHS[d.month - 1]} {d.day:02d}, {d.year}"


def safe_date(display: str) -> str:
    """"October 04, 2026" -> "October_04_2026" (app.py:1072)."""
    return display.replace(", ", "_").replace(" ", "_")


def docx_filename(variant: Variant, d: datetime.date) -> str:
    """worship_October_04_2026.docx, or worship_pastor_October_04_2026.docx (app.py:1079, 1088)."""
    prefix = "worship_pastor_" if variant == "pastor" else "worship_"
    return f"{prefix}{safe_date(service_date_display(d))}.docx"


def content_disposition(filename: str) -> str:
    """The download header of F §1.9: a plain name and the RFC 5987 form."""
    return f"attachment; filename=\"{filename}\"; filename*=UTF-8''{quote(filename)}"


def hymn_line(title: str, number: Optional[int]) -> str:
    """"Holy, Holy, Holy — #138"; just the title when the number is unknown."""
    return title if number is None else f"{title} — #{number}"


def resolve_doc_readings(scriptures: list[str], selected_ot_ref: str = "",
                         selected_nt_ref: str = "") -> tuple[Optional[str], Optional[str]]:
    """The first and NT readings the files print: scripture_refs.resolve_readings,
    nothing more (a stale pick is ignored; a None reading leaves its section out)."""
    pair = scripture_refs.resolve_readings(list(scriptures), selected_ot_ref, selected_nt_ref)
    return pair.ot, pair.nt


def is_legacy_error_placeholder(text: str) -> bool:
    """Streamlit's stored generation errors (worship_service.py:713, 722, 764 before slice 4)."""
    stripped = text.strip()
    return stripped.endswith("]") and stripped.startswith(LEGACY_ERROR_PREFIXES)


SLOTS = ("opening", "response", "closing")


@dataclass(frozen=True)
class ResolvedHymn:
    """A slot's hymn as it prints: the database's title and number for a hymn id, else the snapshot sent."""
    title: str
    number: Optional[int]
    hymn_id: Optional[object] = None          # uuid.UUID when the hymn is in the church's hymnal
    hymnal: Optional[str] = None


@dataclass(frozen=True)
class CustomElement:
    label: str
    text: str
    insert_after: str                          # a liturgy_config placement key


@dataclass(frozen=True)
class ResolvedService:
    """A service ready to print: cleaned input with its hymns resolved (usecases.documents)."""
    service_date: datetime.date
    occasion: str = ""
    scriptures: tuple[str, ...] = ()
    hymns: Mapping[str, Optional[ResolvedHymn]] = field(default_factory=dict)
    liturgy: Mapping[str, str] = field(default_factory=dict)
    sermon_title: str = ""
    selected_ot_ref: str = ""
    selected_nt_ref: str = ""
    include_communion: bool = False
    custom_elements: tuple[CustomElement, ...] = ()


def render_docx(resolved: ResolvedService, variant: Variant) -> bytes:
    """The Word file of one variant: worship_service.build_docx with the resolved
    readings, the slot hymns and the variant's flags."""
    import worship_service          # here, not at the top: worship_service imports hymn_line from this module

    ot, nt = resolve_doc_readings(list(resolved.scriptures), resolved.selected_ot_ref, resolved.selected_nt_ref)
    hymns = {slot: None if (h := resolved.hymns.get(slot)) is None else {"title": h.title, "number": h.number}
             for slot in SLOTS}
    return worship_service.build_docx(
        occasion=resolved.occasion,
        date_display=service_date_display(resolved.service_date),
        hymns_by_slot=hymns,
        liturgy=dict(resolved.liturgy),
        ot_ref=ot,
        nt_ref=nt,
        sermon_title=resolved.sermon_title,
        include_communion=resolved.include_communion,
        custom_elements=[{"label": e.label, "text": e.text, "insert_after": e.insert_after}
                         for e in resolved.custom_elements],
        **VARIANTS[variant],
    )


# --- slice 5a-2: saved services (5a spec, "service_output.py" and "Normalizing stored data") ---

_ISO_PREFIX = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


def normalize_date_iso(raw: object) -> Optional[str]:
    """A stored services.service_date_iso as YYYY-MM-DD, or None: the first 10
    characters when they are a real calendar date ("2026-10-04" and the
    Notion-era "2026-10-04T00:00:00.000Z" both give "2026-10-04"); None for
    NULL, "", "October 4", "2026-02-30" and anything else. GET /services,
    GET /services/{id} and the hymn-use rebuild all read dates through it."""
    if not isinstance(raw, str) or not _ISO_PREFIX.fullmatch(raw[:10]):
        return None
    try:
        datetime.date.fromisoformat(raw[:10])
    except ValueError:
        return None
    return raw[:10]


def coerce_number(value: object) -> Optional[int]:
    """A stored hymn number as an int, or None: an int (not a bool), a string of
    ASCII digits, or a whole float; anything else is None. Never raises."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().isascii() and value.strip().isdigit():
        return int(value.strip())
    return None


@dataclass(frozen=True)
class StoredHymn:
    """One entry of a stored services.hymns list, read tolerantly."""
    slot: Optional[str]                        # one of SLOTS, else None
    title: str                                 # stripped, never blank
    number: Optional[int]
    hymn_id: Optional[str]                     # as stored (a string), else None
    hymnal: Optional[str]


def _stored_hymn(entry: object) -> Optional[StoredHymn]:
    if not isinstance(entry, dict):
        return None
    title = entry.get("title")
    if not isinstance(title, str) or not title.strip():
        return None
    slot = entry.get("slot")
    hymn_id = entry.get("hymn_id")
    hymnal = entry.get("hymnal")
    return StoredHymn(slot=slot if slot in SLOTS else None, title=title.strip(),
                      number=coerce_number(entry.get("number")),
                      hymn_id=hymn_id if isinstance(hymn_id, str) and hymn_id.strip() else None,
                      hymnal=hymnal.strip() if isinstance(hymnal, str) and hymnal.strip() else None)


def stored_hymn_entries(raw: object) -> list[Optional[StoredHymn]]:
    """Every entry of a stored services.hymns value, in order, a 4th and later
    entry included (the hymn-use rebuild counts them). A value that is not a
    list gives []; a non-dict entry, a title that is not a string and a blank
    title give None. Never raises: one malformed legacy row cannot fail a save."""
    if not isinstance(raw, list):
        return []
    return [_stored_hymn(entry) for entry in raw]


def slot_map(raw: object) -> dict[str, Optional[StoredHymn]]:
    """The stored hymns by slot (F §4.6 step 3). When the value is a non-empty
    list whose every entry is a dict with a valid "slot" (what 5a-2 writes),
    each entry goes to its slot (the first one wins); otherwise (Streamlit's
    compacted [{title, number}] lists) entries 0-2 map to opening, response
    and closing, and a 4th entry is ignored."""
    entries = stored_hymn_entries(raw)
    slotted = bool(entries) and all(isinstance(e, dict) and e.get("slot") in SLOTS for e in raw)
    if slotted:
        result: dict[str, Optional[StoredHymn]] = {slot: None for slot in SLOTS}
        for entry, parsed in zip(raw, entries):
            if parsed is not None and result[entry["slot"]] is None:
                result[entry["slot"]] = parsed
        return result
    return {slot: entries[i] if i < len(entries) else None for i, slot in enumerate(SLOTS)}


def stored_hymns(hymns: Mapping[str, Optional[ResolvedHymn]]) -> list[dict]:
    """What 5a-2 writes to services.hymns: exactly 3 entries in slot order,
    {slot, title, number, hymn_id, hymnal}; an empty slot has title "" and
    nulls; hymn_id is the id as a string, or JSON null (F §6.2)."""
    out = []
    for slot in SLOTS:
        hymn = hymns.get(slot)
        if hymn is None:
            out.append({"slot": slot, "title": "", "number": None, "hymn_id": None, "hymnal": None})
        else:
            out.append({"slot": slot, "title": hymn.title, "number": hymn.number,
                        "hymn_id": None if hymn.hymn_id is None else str(hymn.hymn_id), "hymnal": hymn.hymnal})
    return out
