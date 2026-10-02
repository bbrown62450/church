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
"""
from __future__ import annotations

import datetime
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
