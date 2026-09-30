"""Liturgy generation, one result per section (slice 4 spec, Backend 3 and its
2026-09-26 amendment; API "POST /liturgy/generate semantics" 1-10; F §1.8, §2.8).

generate_liturgy:
1. Deduplicates the sections (first occurrence kept) and splits them into
   typed ones (a non-blank override) and ones that need the AI.
2. Reads, in one session that closes before any AI call (F §1.8): the slot
   hymns by id, within the church (any id it cannot find is a 404 for the
   whole request); and, only when a section needs the AI, the church's prompt
   overrides, rubric overrides and prayer library, fresh on every call.
3. Typed sections come back as "override" with the text exactly as sent.
4. With no AI configured, each section that needs it is ai_not_configured.
5. Otherwise builds each section's messages (a PromptInvalid is that section's
   prompt_invalid), charges the `ai` bucket once for the sections left
   (charge(n), never with 0; a 429 it raises stops every AI call), and runs
   them at most 4 at a time, each inside an 80 s deadline from the start of
   the call (F §1.8: with the last attempt's 5 s connect, at most 85 s, inside
   the page's 90 s). AI failures, an empty answer and an answer over 20 000
   characters are per-section errors with this module's messages; upstream
   text is never returned.
6. Returns the outcomes in request order.

Logs one `liturgy.generate` INFO line per call (counts, codes, which optional
blocks were present or dropped, the duration); prompts and outputs only at
DEBUG (F §2.5). Writes nothing. The layer rules are in usecases/__init__.py:
no FastAPI, Starlette or Streamlit here (test_no_streamlit_in_core.py).
"""
from __future__ import annotations

import contextvars
import logging
import random
import time
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable, Literal, Mapping, Optional, Sequence

import liturgy_prompts
import prayer_library
from db import session_scope
from domain_errors import Busy, DomainError, NotConfigured, NotFound, UpstreamError, UpstreamTimeout
from integrations import openai_client
from liturgy_config import LIMITS, SECTION_LABELS, SECTIONS_BY_KEY
from repos import churches
from repos import hymns as hymn_repo

logger = logging.getLogger(__name__)

HYMN_GONE_MESSAGE = "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step."
SECTION_MESSAGES = {
    "ai_not_configured": "AI not configured. Type this section yourself.",
    "ai_busy": "The AI service is busy. Try again in a minute.",
    "ai_timeout": "The AI took too long to answer. Try again.",
    "ai_upstream_error": "The AI service had a problem. Try again.",
}
PROMPT_INVALID_MESSAGE = ("The {label} prompt in Settings has a problem: {reason} "
                          "An admin can fix it under Settings → Liturgy prompts.")
MAX_PARALLEL = 4                               # sections of one request at a time
MAX_ANSWER_CHARS = LIMITS.max_section_text     # a longer answer could not be saved (5a)
# The server deadline passed to complete() (F §1.8): every slot wait, attempt and
# retry ends by it; only the last attempt's connect (5 s) can run past, so a call
# answers within 85 s, inside the client's 90 s.
GENERATE_BUDGET_S = 80.0

Status = Literal["override", "generated", "error"]


@dataclass(frozen=True)
class HymnRefData:
    """One slot's pick as the route received it (api.schemas.HymnRef, without Pydantic)."""
    hymn_id: Optional[uuid.UUID]
    title: str
    number: Optional[int]
    hymnal: Optional[str] = None


@dataclass(frozen=True)
class SectionOutcome:
    section: str
    status: Status
    text: Optional[str]                 # None only when status == "error"
    error_code: Optional[str]
    error_message: Optional[str]


def _override(section: str, text: str) -> SectionOutcome:
    return SectionOutcome(section, "override", text, None, None)


def _error(section: str, code: str, message: Optional[str] = None) -> SectionOutcome:
    return SectionOutcome(section, "error", None, code, message or SECTION_MESSAGES[code])


def _prompt_invalid(section: str, reason: str) -> SectionOutcome:
    return _error(section, "prompt_invalid",
                  PROMPT_INVALID_MESSAGE.format(label=SECTION_LABELS[section], reason=reason))


def dedupe(sections: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(sections))


def sections_needing_ai(sections: Sequence[str], overrides: Mapping[str, str]) -> list[str]:
    """The requested sections (deduplicated, in order) whose override is missing or blank."""
    return [s for s in dedupe(sections) if not (overrides.get(s) or "").strip()]


def _resolved(ref: Optional[HymnRefData], found: Mapping[uuid.UUID, Any]) -> Optional[liturgy_prompts.ResolvedHymn]:
    if ref is None:
        return None
    if ref.hymn_id is None:                                 # an archived snapshot, used as sent
        return liturgy_prompts.ResolvedHymn(ref.title or "", ref.number)
    record = found[ref.hymn_id]
    return liturgy_prompts.ResolvedHymn(record.title or "", record.number)


def _generate_one(ai: Any, section: str, prompt: liturgy_prompts.BuiltPrompt,
                  deadline: float) -> SectionOutcome:
    if logger.isEnabledFor(logging.DEBUG):                 # prompts at DEBUG only (F §2.5)
        logger.debug("liturgy.generate section=%s messages=%r", section, prompt.messages)
    spec = SECTIONS_BY_KEY[section]
    extra = {} if spec.timeout_seconds is None else {"timeout_seconds": spec.timeout_seconds}
    try:
        text = ai.complete(prompt.messages, max_completion_tokens=spec.max_completion_tokens,
                           deadline=deadline, **extra)
    except NotConfigured:
        return _error(section, "ai_not_configured")
    except Busy:
        return _error(section, "ai_busy")
    except UpstreamTimeout:
        return _error(section, "ai_timeout")
    except UpstreamError:
        return _error(section, "ai_upstream_error")
    except Exception:
        logger.exception("liturgy.generate section=%s unexpected error", section)
        return _error(section, "ai_upstream_error")
    text = text.strip() if isinstance(text, str) else ""
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("liturgy.generate section=%s answer=%r", section, text)
    if not text or len(text) > MAX_ANSWER_CHARS:
        logger.warning("liturgy.generate section=%s unusable answer chars=%d", section, len(text))
        return _error(section, "ai_upstream_error")
    return SectionOutcome(section, "generated", text, None, None)


def generate_liturgy(*, church_id: uuid.UUID, user_id: uuid.UUID,
                     occasion: str, scriptures: Sequence[str],
                     hymns: Mapping[str, Optional[HymnRefData]],
                     sections: Sequence[str], overrides: Mapping[str, str],
                     sermon: Optional[tuple[str, str]] = None,
                     charge: Callable[[int], None] = lambda n: None,
                     ai: Any = openai_client,
                     choose: Callable[[Sequence[str]], str] = random.choice,
                     clock: Callable[[], float] = time.monotonic) -> list[SectionOutcome]:
    """One outcome per requested section, in request order (see the module
    docstring). user_id is for the rate limit only (the route's charge).
    clock is time.monotonic, the clock complete() reads its deadline on."""
    started = clock()
    deadline = started + GENERATE_BUDGET_S
    wanted = dedupe(sections)
    need_ai = sections_needing_ai(wanted, overrides)
    facts: dict[str, Any] = {"church": church_id, "sections": len(wanted), "ai": 0}
    try:
        outcomes = _generate(church_id, occasion, scriptures, hymns, wanted, need_ai, overrides,
                             sermon, charge, ai, choose, deadline, facts)
    except DomainError as exc:
        _log(facts, started, clock, outcome=exc.code)
        raise
    except Exception:
        _log(facts, started, clock, outcome="internal_error")
        raise
    counts = Counter(o.status for o in outcomes)
    codes = Counter(o.error_code for o in outcomes if o.error_code)
    facts["outcomes"] = ",".join(f"{k}:{counts[k]}" for k in ("generated", "override", "error"))
    facts["codes"] = ",".join(f"{code}:{n}" for code, n in sorted(codes.items())) or "-"
    _log(facts, started, clock, outcome="ok")
    return outcomes


def _generate(church_id, occasion, scriptures, hymns, wanted, need_ai, overrides, sermon,
              charge, ai, choose, deadline, facts) -> list[SectionOutcome]:
    ids = [ref.hymn_id for ref in hymns.values() if ref is not None and ref.hymn_id is not None]
    stored_prompts: Mapping[str, Any] = {}
    rubric_overrides: Mapping[str, Any] = {}
    library = prayer_library.EMPTY_LIBRARY
    with session_scope() as s:                                   # read, then close (F §1.8)
        found = hymn_repo.get_hymns_by_ids(church_id, ids, session=s) if ids else {}
        if any(hymn_id not in found for hymn_id in ids):
            raise NotFound(HYMN_GONE_MESSAGE)
        if need_ai:
            stored_prompts = churches.get_church_prompts(church_id, session=s)
            rubric_overrides = churches.get_church_rubric_overrides(church_id, session=s)
            church = churches.get_church(church_id, session=s)
            library = prayer_library.read_library((church or {}).get("settings"))
    outcomes = {section: _override(section, overrides[section])
                for section in wanted if section not in need_ai}
    if need_ai and not ai.ai_available():
        outcomes.update({section: _error(section, "ai_not_configured") for section in need_ai})
    elif need_ai:
        sermon_ref, sermon_text = sermon or (None, None)
        ctx = liturgy_prompts.build_context(
            occasion=occasion, scriptures=scriptures,
            hymns_by_slot={slot: _resolved(ref, found) for slot, ref in hymns.items()},
            rubric=rubric_overrides, sermon_ref=sermon_ref, sermon_text=sermon_text)
        prompts = liturgy_prompts.merge_prompts(stored_prompts)
        built: dict[str, liturgy_prompts.BuiltPrompt] = {}
        examples = 0                            # chosen for sections that reach the AI
        for section in need_ai:
            example = prayer_library.choose_example(library, section, choose=choose)
            voice = liturgy_prompts.VoiceContext(profile=library.voice_profile, example=example)
            try:
                built[section] = liturgy_prompts.build_prompt(section, prompts, ctx, voice=voice)
            except liturgy_prompts.PromptInvalid as exc:
                outcomes[section] = _prompt_invalid(section, exc.reason)
            else:
                examples += example is not None
        facts.update(
            rubric="custom" if rubric_overrides else "default",
            sermon="yes" if ctx.sermon else "no",
            voice=",".join(name for name, present in (("profile", library.voice_profile.strip()),
                                                      ("example", examples)) if present) or "none",
            dropped=",".join(dict.fromkeys(n for p in built.values() for n in p.dropped)) or "-")
        if built:
            facts["ai"] = len(built)
            charge(len(built))                  # once; a RateLimited here stops every AI call
            with ThreadPoolExecutor(max_workers=min(MAX_PARALLEL, len(built)),
                                    thread_name_prefix="liturgy") as pool:
                futures = {section: pool.submit(contextvars.copy_context().run, _generate_one,
                                                ai, section, prompt, deadline)
                           for section, prompt in built.items()}
                outcomes.update({section: future.result() for section, future in futures.items()})
    return [outcomes[section] for section in wanted]


def _log(facts: Mapping[str, Any], started: float, clock: Callable[[], float], *, outcome: str) -> None:
    """One line per call (S Backend 3 "Logging"): never a prompt, an answer or
    any client text."""
    details = " ".join(f"{key}={value}" for key, value in facts.items())
    logger.info("liturgy.generate %s duration_ms=%d outcome=%s", details,
                round((clock() - started) * 1000), outcome)
