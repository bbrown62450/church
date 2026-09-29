"""The Hymns step's reads and the AI suggestions (slice 3 spec, Backend 3;
owner decisions 3 and 9; owner answers of 2026-09-29).

- resolve_default_hymnal: the stored default_hymnal and the effective one
  (GET /hymnals and GET /church both use it, so they never disagree).
- hymnal_overview: GET /hymnals.
- list_hymns_page: GET /hymns, each hymn as a HymnView with its recent use
  and the rubric's newer-than-preferred flag.
- scripture_matches: POST /hymns/scripture-matches.

Every function takes the active church's id only (F §1.2 rule 1) and reads in
one session. The layer rules are in usecases/__init__.py: no FastAPI,
Starlette or Streamlit here (test_no_streamlit_in_core.py). Repos are called
through their modules, so a test can patch one function.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import date
from typing import Any, Optional

from sqlalchemy.orm import Session

import hymn_usage
from db import session_scope
from domain_errors import InvalidInput
from hymn_ranking import is_newer_than_preferred
from hymn_search import match_hymns, parse_themes, usage_key
from repos import churches
from repos import hymns as hymn_repo
from repos.hymns import HymnalSummary, HymnRecord
from scripture_refs import parse_refs, split_alternatives
from service_rubric import merge_rubric

logger = logging.getLogger(__name__)


REFS_MESSAGE = "Enter at least one scripture reference."
HYMNAL_MESSAGE = "That hymnal isn't in this church's library."


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


@dataclass(frozen=True)
class HymnView:
    """HymnOut's fields (S API Models): one read model for every route that returns hymns."""

    id: uuid.UUID
    hymnal: str
    title: str                         # stripped; "" when NULL
    number: Optional[int]
    link: Optional[str]                # hymnary_link verbatim; the client renders it only via safeHttpsUrl
    scripture_refs: Optional[str]
    themes: list[str]
    recent_use_on: Optional[date]      # the usage date nearest the service date; None without a date
    text_year: Optional[int]
    hymnal_count: Optional[int]
    newer_than_preferred: bool         # text_year known and >= the rubric's prefer_before_year


@dataclass(frozen=True)
class HymnPage:
    items: list[HymnView]
    total: int
    limit: int
    offset: int


def church_rubric(church_id: uuid.UUID, session: Session) -> dict:
    """The church's merged rubric, read fresh (S Backend 3.8). merge_rubric
    falls back to the defaults for any invalid stored value."""
    return merge_rubric(churches.get_church_rubric_overrides(church_id, session=session))


def hymn_view(record: HymnRecord, *, usage: Optional[dict[str, date]],
              prefer_before_year: int) -> HymnView:
    return HymnView(
        id=record.id,
        hymnal=record.hymnal,
        title=(record.title or "").strip(),
        number=record.number,
        link=record.link,
        scripture_refs=record.scripture_refs,
        themes=parse_themes(record.theme),
        recent_use_on=usage.get(usage_key(record.title)) if usage is not None else None,
        text_year=record.text_year,
        hymnal_count=record.hymnal_count,
        newer_than_preferred=is_newer_than_preferred(record.text_year, prefer_before_year),
    )


def list_hymns_page(church_id: uuid.UUID, *, hymnal: Optional[str], q: Optional[str], limit: int,
                    offset: int, recent_for_date: Optional[date]) -> HymnPage:
    """S Backend 3.3: one session for the page, the usage window and the rubric."""
    with session_scope() as s:
        records, total = hymn_repo.query_hymns(church_id, hymnal=hymnal, q=q, limit=limit,
                                               offset=offset, session=s)
        usage = (hymn_usage.usage_near(church_id, recent_for_date, session=s)
                 if recent_for_date is not None else None)
        year = church_rubric(church_id, s)["prefer_before_year"]
    return HymnPage(items=[hymn_view(r, usage=usage, prefer_before_year=year) for r in records],
                    total=total, limit=limit, offset=offset)


@dataclass(frozen=True)
class HymnMatchView(HymnView):
    strength: str                      # "passage" or "chapter"
    matched_refs: list[str]            # the query refs (after the " or " split) that matched


@dataclass(frozen=True)
class ScriptureMatches:
    hymnal: Optional[str]
    refs_used: list[str]
    unparsed_refs: list[str]
    total_matched: int
    items: list[HymnMatchView]


def clean_refs(refs: list[str]) -> list[str]:
    """Trimmed, blanks dropped, each split on " or " (any case), in order."""
    return [alternative for ref in refs for alternative in split_alternatives(ref or "")]


def selected_hymnal(church_id: uuid.UUID, requested: Optional[str], session: Session) -> Optional[str]:
    """None asks for the effective hymnal (None when the church has none). A code
    the church lacks is InvalidInput on `hymnal`, with the same message whether
    it exists in another church or nowhere (S API notes)."""
    codes = [summary.code for summary in hymn_repo.hymnal_summaries(church_id, session=session)]
    if requested is None:
        return _resolve(_settings(church_id, session), codes).effective_hymnal
    if requested not in codes:
        raise InvalidInput(HYMNAL_MESSAGE, field="hymnal")
    return requested


def scripture_matches(church_id: uuid.UUID, *, refs: list[str], hymnal: Optional[str],
                      recent_for_date: Optional[date], limit_per_ref: int,
                      max_results: int) -> ScriptureMatches:
    """S Backend 3.5: passage tier first, then chapter; every hymn a HymnView."""
    refs_used = clean_refs(refs)
    if not refs_used:
        raise InvalidInput(REFS_MESSAGE, field="refs")
    with session_scope() as s:
        code = selected_hymnal(church_id, hymnal, s)
        if code is None:
            return ScriptureMatches(hymnal=None, refs_used=refs_used, unparsed_refs=[],
                                    total_matched=0, items=[])
        records = hymn_repo.list_hymnal_records(church_id, code, session=s)
        usage = (hymn_usage.usage_near(church_id, recent_for_date, session=s)
                 if recent_for_date is not None else None)
        year = church_rubric(church_id, s)["prefer_before_year"]
    result = match_hymns(records, refs_used, limit_per_ref=limit_per_ref, max_results=max_results)
    if logger.isEnabledFor(logging.DEBUG):       # counts only (S Risks; clarification 29)
        logger.debug("hymn_matches refs=%d refs_unparsed=%d hymns=%d hymns_with_unparsed=%d matched=%d",
                     len(result.refs_used), len(result.unparsed_refs), len(records),
                     sum(1 for r in records if parse_refs(r.scripture_refs or "").unparsed),
                     result.total_matched)
    items = [HymnMatchView(**asdict(hymn_view(m.record, usage=usage, prefer_before_year=year)),
                           strength=m.strength, matched_refs=list(m.matched_refs))
             for m in result.items]
    return ScriptureMatches(hymnal=code, refs_used=list(result.refs_used),
                            unparsed_refs=list(result.unparsed_refs),
                            total_matched=result.total_matched, items=items)
