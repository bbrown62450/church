"""The Hymns step's reads and the AI suggestions (slice 3 spec, Backend 3;
owner decisions 3 and 9; owner answers of 2026-09-29).

- resolve_default_hymnal: the stored default_hymnal and the effective one
  (GET /hymnals and GET /church both use it, so they never disagree).
- hymnal_overview: GET /hymnals.
- list_hymns_page: GET /hymns, each hymn as a HymnView with its recent use
  and the rubric's newer-than-preferred flag.
- scripture_matches: POST /hymns/scripture-matches.
- suggest_hymns: POST /hymns/suggestions. Reads in one session that closes
  before any external call (F §1.8), then the NT text (10 s budget on its
  own pool), then one OpenAI call, all inside a 75 s deadline.

Every function takes the active church's id only (F §1.2 rule 1) and reads in
one session. The layer rules are in usecases/__init__.py: no FastAPI,
Starlette or Streamlit here (test_no_streamlit_in_core.py). Repos are called
through their modules, so a test can patch one function.
"""
from __future__ import annotations

import contextvars
import logging
import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session

import hymn_suggest
import hymn_usage
from db import session_scope
from domain_errors import DomainError, InvalidInput, NotConfigured
from hymn_ranking import is_newer_than_preferred
from hymn_search import match_hymns, parse_themes, usage_key
from integrations import openai_client
from repos import churches
from repos import hymns as hymn_repo
from repos.hymns import HymnalSummary, HymnRecord
from scripture_refs import default_nt_ref, parse_refs, split_alternatives
import scripture_fetcher
from service_rubric import merge_rubric
from usecases import passages

logger = logging.getLogger(__name__)


REFS_MESSAGE = "Enter at least one scripture reference."
HYMNAL_MESSAGE = "That hymnal isn't in this church's library."
EMPTY_POOL_MESSAGE = "This hymnal has no hymns to suggest from."
ALL_RECENT_MESSAGE = ("Every hymn in this hymnal was used within 12 weeks of this service. "
                      "Turn off \u201cExclude\u201d and try again.")
AI_NOT_CONFIGURED_MESSAGE = "AI suggestions aren't set up on this app yet."

SUGGEST_BUDGET_S = 75.0            # the server deadline for POST /hymns/suggestions (F §1.8)
NT_FETCH_BUDGET_S = 10.0           # the NT text fetch's share of it
NT_TRANSLATION = "web"             # never ESV on the server (S Behavior change 8)
NT_MAX_PARTS = 4                   # the fetch takes the first alternative only, and skips it past this
MAX_COMPLETION_TOKENS = 1200

# The NT fetch runs here so its 10 s budget holds although get_passage_text
# takes no deadline (up to 20 s). An abandoned fetch finishes in the
# background and still fills slice 2's passage cache.
_NT_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="nt-fetch")


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


# --- AI suggestions (S Backend 3.6-3.8) ---------------------------------------------


@dataclass(frozen=True)
class SuggestionRequest:
    service_date: date
    occasion: str = ""
    scriptures: list[str] = field(default_factory=list)
    selected_nt_ref: Optional[str] = None
    nt_text: Optional[str] = None
    hymnal: Optional[str] = None
    exclude_recent: bool = True
    current_picks: dict[str, Optional[uuid.UUID]] = field(
        default_factory=lambda: {"opening": None, "response": None, "closing": None})


@dataclass(frozen=True)
class SuggestedView(HymnView):
    source: str                        # "ai", or "candidates" (the minimum top-up)


@dataclass(frozen=True)
class HymnSuggestions:
    hymnal: str
    nt_ref: Optional[str]
    nt_text_used: bool
    excluded_recent_count: int
    slots: dict[str, list[SuggestedView]]


def reset_for_tests() -> None:
    """Tests: join the NT pool (every blocked fetch released first) and build a new one."""
    global _NT_EXECUTOR
    _NT_EXECUTOR.shutdown(wait=True)
    _NT_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="nt-fetch")


def _nt_context(client_text: Optional[str], nt_ref: Optional[str], fetch_text: Callable,
                deadline: float, clock: Callable[[], float]) -> tuple[Optional[str], str]:
    """(text, source): the client's text, else WEB fetched within NT_FETCH_BUDGET_S
    and the deadline. A timeout, a failure or no text is (None, ...), never raised."""
    if (client_text or "").strip():
        return client_text, "client"
    if not nt_ref:
        return None, "none"
    # One suggestion must not drain the shared bible-api budget (review 3a T13-14).
    sections = scripture_fetcher.plan_sections(nt_ref)
    if not sections or len(sections[0][1]) > NT_MAX_PARTS:
        return None, "skipped"
    future = _NT_EXECUTOR.submit(contextvars.copy_context().run, fetch_text,
                                 sections[0][0].strip(), NT_TRANSLATION)
    try:
        text = future.result(timeout=max(0.0, min(NT_FETCH_BUDGET_S, deadline - clock())))
    except FutureTimeout:
        future.cancel()                           # a fetch not yet started never runs late
        return None, "timeout"
    except Exception as exc:                      # the fetch must never fail the suggestions
        logger.warning("hymn_suggestions nt_fetch_failed error=%s", type(exc).__name__)
        return None, "none"
    return (text, "fetched") if (text or "").strip() else (None, "none")


def _without_nt_text(messages: list[dict]) -> list[dict]:
    return [{**m, "content": re.sub(r"(?m)^(NT PASSAGE TEXT \(excerpt\):).*$", r"\1 [omitted]",
                                    m.get("content") or "")} for m in messages]


def _per_slot(values: dict[str, Any]) -> str:
    return "/".join(str(values[slot]) for slot in hymn_suggest.SLOTS)


def suggest_hymns(church_id: uuid.UUID, user_id: uuid.UUID, req: SuggestionRequest, *,
                  ai: Any = openai_client, fetch_text: Optional[Callable] = None,
                  clock: Callable[[], float] = time.monotonic) -> HymnSuggestions:
    """S Backend 3.6 steps 0-10. user_id is for the rate limit only (the route's
    dependency charges it); nothing here writes."""
    started = clock()
    deadline = started + SUGGEST_BUDGET_S
    fetch = fetch_text or passages.get_passage_text
    facts: dict[str, Any] = {"hymnal": "-", "pool": 0, "excluded": 0, "nt_source": "-"}
    try:
        with session_scope() as s:                                   # step 1: read, then close
            code = selected_hymnal(church_id, req.hymnal, s)
            pool = hymn_repo.list_hymnal_records(church_id, code, session=s) if code else []
            usage = hymn_usage.usage_near(church_id, req.service_date, session=s)
            overrides = churches.get_church_rubric_overrides(church_id, session=s)
        rubric = merge_rubric(overrides)
        pool = [h for h in pool if (h.title or "").strip()]
        facts.update(hymnal=code or "-", pool=len(pool))
        if not pool:                                                  # step 2
            raise InvalidInput(EMPTY_POOL_MESSAGE, field="hymnal")
        eligible = ([h for h in pool if usage_key(h.title) not in usage]   # step 3
                    if req.exclude_recent else pool)
        excluded = len(pool) - len(eligible)
        facts["excluded"] = excluded
        if not eligible:
            raise InvalidInput(ALL_RECENT_MESSAGE)
        if not ai.ai_available():                                     # step 4
            raise NotConfigured(AI_NOT_CONFIGURED_MESSAGE, code="ai_not_configured")
        nt_ref = (req.selected_nt_ref or "").strip() or default_nt_ref(req.scriptures)   # step 5
        nt_text, facts["nt_source"] = _nt_context(req.nt_text, nt_ref, fetch, deadline, clock)
        candidates = hymn_suggest.build_candidates(eligible, req.scriptures, nt_ref=nt_ref,  # step 6
                                                   current_picks=req.current_picks, rubric=rubric)
        messages, token_map = hymn_suggest.build_prompt(                                  # step 7
            candidates, occasion=req.occasion, scriptures=req.scriptures, nt_ref=nt_ref,
            nt_text=nt_text, rubric=rubric)
        if logger.isEnabledFor(logging.DEBUG):                    # nt_text is never logged (S §6)
            logger.debug("hymn_suggestions prompt=%r", _without_nt_text(messages))
        try:
            raw = ai.complete(messages, max_completion_tokens=MAX_COMPLETION_TOKENS,     # step 8
                              json_mode=True, deadline=deadline)
        except NotConfigured:
            raise NotConfigured(AI_NOT_CONFIGURED_MESSAGE, code="ai_not_configured") from None
        parsed = hymn_suggest.parse_suggestion_json(raw)                                  # step 9
        resolved = hymn_suggest.resolve_suggestions(parsed, token_map, eligible, candidates)
        final = hymn_suggest.finalize_slots(resolved, req.current_picks, candidates)
    except DomainError as exc:
        _log(facts, started, clock, outcome=exc.code)
        raise
    except Exception:
        _log(facts, started, clock, outcome="internal_error")    # one line per call (S 3.6 step 10)
        raise
    year = rubric["prefer_before_year"]
    slots = {slot: [SuggestedView(**asdict(hymn_view(item.record, usage=usage, prefer_before_year=year)),
                                  source=item.source) for item in items]
             for slot, items in final.items()}
    facts.update(
        candidates=_per_slot({k: len(v) for k, v in candidates.by_slot.items()}),
        resolved=_per_slot({k: len(v) for k, v in resolved.items()}),
        topped_up=_per_slot({k: sum(i.source == "candidates" for i in v) for k, v in final.items()}),
        modes=_per_slot(candidates.modes),
        newer_or_unknown=_per_slot({k: sum(r.text_year is None or r.text_year >= year for r in v)
                                    for k, v in candidates.by_slot.items()}),
        prefer_before_year=year, prefer_familiar=rubric["prefer_familiar"],
        rubric_customized=bool(overrides))
    _log(facts, started, clock, outcome="ok")
    return HymnSuggestions(hymnal=code, nt_ref=nt_ref, nt_text_used=nt_text is not None,
                           excluded_recent_count=excluded, slots=slots)


def _log(facts: dict[str, Any], started: float, clock: Callable[[], float], *, outcome: str) -> None:
    """One line per call (S Backend 3.6 step 10, 3.8 "Logs"): counts, modes,
    the model, the duration and the outcome. Never the prompt, nt_text or titles."""
    details = " ".join(f"{key}={value}" for key, value in facts.items())
    logger.info("hymn_suggestions %s model=%s duration_ms=%d outcome=%s", details,
                openai_client.ai_settings().model or "-", round((clock() - started) * 1000), outcome)
