"""Passage text for the readings step (S "Passages", API row 3; F §1.8, §2.7; slice 2a).

plan_passages validates and plans; it is pure, so the route can charge the
`scripture` bucket one token per upstream part (len(plan.parts)) before any
work, and a 422 charges nothing. load_passages then fetches every part of
every ref on one module-level pool shared by all requests, with a deadline
per request: a part not finished by then is `unavailable`, and a part that
has not started is cancelled. So a request answers within ~20 s however
busy the pool is, inside the client's 30 s timeout (S :315).

The part, section and passage statuses are derived once, by
scripture_fetcher.assemble_passage; get_passage_text (slice 3) is
scripture_fetcher's, re-exported under the same name.

No FastAPI, no Streamlit (tests/test_no_streamlit_in_core.py). Exact
messages come from DomainErrors (usecases/__init__.py).
"""
import logging
from concurrent.futures import Future, ThreadPoolExecutor, wait
from dataclasses import dataclass

import scripture_fetcher
from domain_errors import InvalidInput
from scripture_fetcher import Part, Passage

logger = logging.getLogger(__name__)

MAX_PARTS = 20
DEADLINE_SECONDS = 20.0
POOL_WORKERS = 4

REFS_MESSAGE = "Enter a scripture reference."
TOO_MANY_MESSAGE = "Too many passages in one request."
TRANSLATION_MESSAGE = "Unknown or unavailable translation."

# Slice 3 imports it from here (S Hand-offs row 3).
get_passage_text = scripture_fetcher.get_passage_text

_POOL = ThreadPoolExecutor(max_workers=POOL_WORKERS, thread_name_prefix="passages")


@dataclass(frozen=True)
class PassagePlan:
    """The validated request. `plans[i]` is scripture_fetcher.plan_parts(refs[i]):
    one list of parts per alternative that has parts, and `alternatives[i]` names
    those alternatives, index for index. `parts` is every part of every
    alternative of every ref, in order; its length is the rate-limit cost."""

    translation: str
    refs: tuple[str, ...]
    plans: tuple[list[list[str]], ...]
    parts: tuple[str, ...]
    alternatives: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class PassagesResult:
    translation: str
    translation_label: str
    passages: list[Passage]          # same order as the plan's refs


@dataclass(frozen=True)
class TranslationOptions:
    default: str
    esv_available: bool
    items: list[tuple[str, str]]     # (id, label), scripture_fetcher.TRANSLATIONS order


def _sections(ref: str) -> tuple[tuple[str, ...], list[list[str]]]:
    """The alternatives of `ref` that have parts, and their parts.

    scripture_fetcher.plan_sections drops an alternative with no parts (";"),
    so alternatives[i] always names plan[i], and plan == plan_parts(ref)."""
    sections = scripture_fetcher.plan_sections(ref)
    return tuple(alternative for alternative, _parts in sections), [parts for _alternative, parts in sections]


def plan_passages(refs: list[str], translation: str) -> PassagePlan:
    """Check the request and plan it (S "plan_passages"). Checks run in this
    order: refs, then translation, then the part count.

    - no refs, a blank ref, or a ref with no parts (";") → "Enter a scripture
      reference." on `refs`, so the cost is always at least 1 (2a clarification 33);
    - a translation this deployment does not offer (ESV without its key) →
      "Unknown or unavailable translation." on `translation`;
    - more than MAX_PARTS parts in all → "Too many passages in one request." on `refs`.
    """
    trimmed = tuple(ref.strip() for ref in refs)
    if not trimmed or any(not ref for ref in trimmed):
        raise InvalidInput(REFS_MESSAGE, field="refs")
    planned = [_sections(ref) for ref in trimmed]
    if any(not plan for _alternatives, plan in planned):
        raise InvalidInput(REFS_MESSAGE, field="refs")
    if translation not in {tid for tid, _label in scripture_fetcher.available_translations()}:
        raise InvalidInput(TRANSLATION_MESSAGE, field="translation")
    parts = tuple(part for _alternatives, plan in planned for section in plan for part in section)
    if len(parts) > MAX_PARTS:
        raise InvalidInput(TOO_MANY_MESSAGE, field="refs")
    return PassagePlan(
        translation=translation,
        refs=trimmed,
        plans=tuple(plan for _alternatives, plan in planned),
        parts=parts,
        alternatives=tuple(alternatives for alternatives, _plan in planned),
    )


def _part_result(future: Future, part: str) -> Part:
    """A finished part's own result; an unfinished or cancelled one is `unavailable`.

    fetch_part never raises for an upstream failure, so an exception here is
    a bug, and result() lets it surface as a 500."""
    if future.done() and not future.cancelled():
        return future.result()
    return Part(reference=part, status="unavailable", text=None)


def load_passages(plan: PassagePlan, *, deadline: float = DEADLINE_SECONDS) -> PassagesResult:
    """Fetch every part of the plan on the shared pool and reassemble in order.

    The tasks are one flat list (no nested submission to the same pool, which
    could deadlock). After `deadline` seconds, unfinished parts are
    `unavailable` and parts not yet started are cancelled; a running part
    finishes in the background, and its own cache entry (if any) still helps
    the next request. The deadline is counted from submission; planning and
    the rate-limit charge before it take microseconds."""
    futures = [_POOL.submit(scripture_fetcher.fetch_part, part, plan.translation) for part in plan.parts]
    _done, not_done = wait(futures, timeout=deadline)
    for future in not_done:
        future.cancel()
    if not_done:
        logger.warning("passages_deadline unfinished=%d of=%d", len(not_done), len(futures))
    results = iter([_part_result(future, part) for future, part in zip(futures, plan.parts)])
    passages = []
    for ref, alternatives, sections in zip(plan.refs, plan.alternatives, plan.plans):
        parts = [[next(results) for _part in section] for section in sections]
        passages.append(scripture_fetcher.assemble_passage(ref, list(alternatives), parts))
    return PassagesResult(
        translation=plan.translation,
        translation_label=scripture_fetcher.translation_label(plan.translation),
        passages=passages,
    )


def translation_options() -> TranslationOptions:
    """What GET /translations offers: "web" by default, ESV only when its key is set."""
    return TranslationOptions(
        default=scripture_fetcher.DEFAULT_TRANSLATION,
        esv_available=scripture_fetcher.esv_configured(),
        items=scripture_fetcher.available_translations(),
    )


def reset_for_tests() -> None:
    """Join the pool, then start a new one and a new part cache (2a clarification 39).

    Joining first lets a straggler from an earlier test (a part blocked on a
    test's event) finish before the part cache is rebuilt, so it cannot write
    into the next test's cache. Called by an autouse fixture in tests/conftest.py."""
    global _POOL
    _POOL.shutdown(wait=True, cancel_futures=True)
    _POOL = ThreadPoolExecutor(max_workers=POOL_WORKERS, thread_name_prefix="passages")
    scripture_fetcher.reset_for_tests()
