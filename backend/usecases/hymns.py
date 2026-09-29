"""The Hymns step's reads and the AI suggestions (slice 3 spec, Backend 3;
owner decisions 3 and 9; owner answers of 2026-09-29).

- resolve_default_hymnal: the stored default_hymnal and the effective one
  (GET /hymnals and GET /church both use it, so they never disagree).
- hymnal_overview: GET /hymnals.

Every function takes the active church's id only (F §1.2 rule 1) and reads in
one session. The layer rules are in usecases/__init__.py: no FastAPI,
Starlette or Streamlit here (test_no_streamlit_in_core.py). Repos are called
through their modules, so a test can patch one function.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy.orm import Session

from db import session_scope
from repos import churches
from repos import hymns as hymn_repo
from repos.hymns import HymnalSummary


@dataclass(frozen=True)
class DefaultHymnal:
    default_hymnal: Optional[str]      # settings["default_hymnal"] verbatim, when a non-blank string
    effective_hymnal: Optional[str]    # the default if the church has it, else the first code, else None


@dataclass(frozen=True)
class HymnalOverview:
    items: list[HymnalSummary]
    default_hymnal: Optional[str]
    effective_hymnal: Optional[str]


def _stored_default(settings: Any) -> Optional[str]:
    value = (settings or {}).get("default_hymnal") if isinstance(settings, dict) else None
    return value if isinstance(value, str) and value.strip() else None


def _resolve(settings: Any, codes: list[str]) -> DefaultHymnal:
    stored = _stored_default(settings)
    effective = stored if stored in codes else (codes[0] if codes else None)
    return DefaultHymnal(default_hymnal=stored, effective_hymnal=effective)


def _settings(church_id: uuid.UUID, session: Session) -> Any:
    church = churches.get_church(church_id, session=session)
    return church["settings"] if church else None


def resolve_default_hymnal(church_id: uuid.UUID, *, session: Optional[Session] = None) -> DefaultHymnal:
    """S Backend 3.1: the alphabetical fallback matches Streamlit (app.py:650)."""
    def work(s: Session) -> DefaultHymnal:
        codes = [summary.code for summary in hymn_repo.hymnal_summaries(church_id, session=s)]
        return _resolve(_settings(church_id, s), codes)

    if session is not None:
        return work(session)
    with session_scope() as own:
        return work(own)


def hymnal_overview(church_id: uuid.UUID) -> HymnalOverview:
    """S Backend 3.2: the hymnals (ORDER BY code) and the default, in one session."""
    with session_scope() as s:
        items = hymn_repo.hymnal_summaries(church_id, session=s)
        resolved = _resolve(_settings(church_id, s), [item.code for item in items])
    return HymnalOverview(items=items, default_hymnal=resolved.default_hymnal,
                          effective_hymnal=resolved.effective_hymnal)
