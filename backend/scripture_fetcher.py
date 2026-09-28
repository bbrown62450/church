#!/usr/bin/env python3
"""Fetch full Bible passage text by reference (S "Passages"; F §2.3.3, §2.7).

Two sources:
  * bible-api.com — no key, several public-domain translations (default: WEB).
  * api.esv.org   — the ESV, when ESV_API_KEY is configured (register free at
                    https://api.esv.org). ESV text is © Crossway; the short
                    "(ESV)" copyright is kept on the returned text.

A reference is planned into sections and parts (plan_sections, plan_parts):
one section per " or " alternative, and one part per upstream call inside it
(" and "-joined readings and ";" pieces are fetched separately, each
normalized for fetching by scripture_refs.normalize_for_fetch). fetch_part
makes at most one upstream call; assemble_passage derives every section and
passage status and text from the parts (S Status rules), so fetch_passage
here and usecases.passages.load_passages (which runs parts on a pool under a
deadline) report the same statuses.

bible-api parts are cached for 7 days by (translation, normalized part); a
not-found answer is cached too, as NOT_FOUND. Transient failures and budget
misses are never cached, so "Try again" works. ESV text is never cached
(Crossway terms, F §2.7). Every uncached part first takes a token from the
process-wide upstream budget (integrations.budget); with none left it is not
sent and is `unavailable`.

Configuration exception (S; until slice 7): _esv_key() reads ESV_API_KEY from
the environment at call time, not from api/settings.py.

Logs name the upstream and a reason, never the reference, a body or a query
string (F §2.5). No FastAPI, no Streamlit (tests/test_no_streamlit_in_core.py).
"""

import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Tuple
from urllib.parse import quote

import httpx

from cache import TTLCache
from integrations import budget, http
from scripture_refs import normalize_for_fetch, split_alternatives, split_book, split_joined, split_parts

logger = logging.getLogger(__name__)

# bible-api.com: GET https://bible-api.com/{passage}?translation=web
BIBLE_API_BASE = "https://bible-api.com"
ESV_API_BASE = "https://api.esv.org/v3/passage/text/"

BIBLE_API_READ_TIMEOUT = 10.0
ESV_READ_TIMEOUT = 10.0

PART_CACHE_MAXSIZE = 2000
PART_CACHE_TTL_SECONDS = 7 * 24 * 60 * 60   # 604 800

DEFAULT_TRANSLATION = "web"

# translation id -> (human label, source). Order here is the display order.
TRANSLATIONS: Dict[str, Tuple[str, str]] = {
    "web": ("World English Bible (WEB)", "bible-api"),
    "kjv": ("King James Version (KJV)", "bible-api"),
    "asv": ("American Standard Version (ASV)", "bible-api"),
    "ylt": ("Young's Literal Translation (YLT)", "bible-api"),
    "dra": ("Douay-Rheims 1899 (DRA)", "bible-api"),
    "darby": ("Darby Bible", "bible-api"),
    "bbe": ("Bible in Basic English (BBE)", "bible-api"),
    "oeb-us": ("Open English Bible, US (OEB)", "bible-api"),
    "webbe": ("World English Bible, British (WEBBE)", "bible-api"),
    "esv": ("English Standard Version (ESV)", "esv"),
}

PartStatus = Literal["ok", "not_found", "unavailable"]


@dataclass(frozen=True)
class Part:
    """One upstream call: `reference` is the normalized part that was fetched."""
    reference: str
    status: PartStatus
    text: Optional[str]


@dataclass(frozen=True)
class Section:
    """One " or " alternative, as written; `text` joins its ok parts."""
    reference: str
    status: PartStatus
    text: Optional[str]


@dataclass(frozen=True)
class Passage:
    """One reference as sent (trimmed), with every section, always."""
    reference: str
    status: PartStatus
    sections: Tuple[Section, ...]


class _NotFound:
    """The part-cache value for a reference the upstream does not have."""

    __slots__ = ()

    def __repr__(self) -> str:
        return "NOT_FOUND"


NOT_FOUND = _NotFound()


class _Transient(Exception):
    """Raised inside the part-cache loader for an upstream failure or a budget
    miss. TTLCache stores only values and CacheableFailures, so this is never
    cached; fetch_part turns it into `unavailable` (2a clarification 36)."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


_SKIP_REASONS = ("budget", "no_key")   # the part was never sent

_PART_CACHE: "TTLCache[Tuple[str, str], object]" = TTLCache(
    maxsize=PART_CACHE_MAXSIZE, ttl_ok=PART_CACHE_TTL_SECONDS, ttl_fail=0)


def reset_for_tests(clock=time.monotonic) -> None:
    """Tests: a new, empty part cache on `clock`. A new object rather than
    clear(), so a part still loading from an earlier test writes into the old,
    orphaned cache (2a clarification 39)."""
    global _PART_CACHE
    _PART_CACHE = TTLCache(maxsize=PART_CACHE_MAXSIZE, ttl_ok=PART_CACHE_TTL_SECONDS,
                           ttl_fail=0, clock=clock)


def _esv_key() -> str:
    return os.getenv("ESV_API_KEY", "").strip()


def esv_configured() -> bool:
    return bool(_esv_key())


def available_translations() -> List[Tuple[str, str]]:
    """[(id, label), ...] usable on this deployment. ESV only when its key is set."""
    out = []
    for tid, (label, source) in TRANSLATIONS.items():
        if source == "esv" and not esv_configured():
            continue
        out.append((tid, label))
    return out


def translation_label(translation_id: Optional[str]) -> str:
    """Human label for a translation id (falls back gracefully)."""
    tid = (translation_id or DEFAULT_TRANSLATION)
    entry = TRANSLATIONS.get(tid)
    return entry[0] if entry else tid


# --- planning (pure) ---

# Spellings scripture_refs accepts that bible-api may not (owner 2026-09-28): a part
# starting with one is sent under the book's name ("Rm 8:1" -> "Romans 8:1").
_FETCH_AS_BOOK_NAME = frozenset({"revelations", "mat", "rm", "php", "jdg", "eccles"})
_LEADING_WORD = re.compile(r"([A-Za-z]+)\.?(?=[\s\d]|$)")


def _book_name_for_fetch(part: str) -> str:
    match = _LEADING_WORD.match(part)
    if match and match.group(1).lower() in _FETCH_AS_BOOK_NAME:
        found = split_book(part)
        if found is not None:
            return found[0].name + part[match.end():]
    return part


def plan_sections(reference: str) -> List[Tuple[str, List[str]]]:
    """[(alternative as written, [normalized parts])], one pair per section.

    Alternatives and parts that come out empty are dropped, so ";" plans to []
    and a section never has zero parts (2a clarification 33)."""
    sections = []
    for alternative in split_alternatives(reference):
        if not alternative.strip():
            continue
        parts = [_book_name_for_fetch(normalize_for_fetch(piece))
                 for joined in split_joined(alternative)
                 for piece in split_parts(joined)]
        parts = [part for part in parts if part]
        if parts:
            sections.append((alternative, parts))
    return sections


def plan_parts(reference: str) -> List[List[str]]:
    """The normalized parts of each section, in order (S "Planning"). The same
    plan drives fetching, the rate-limit cost and reassembly."""
    return [parts for _alternative, parts in plan_sections(reference)]


# --- one part: one upstream call at most ---

def _bible_api_part(part: str, translation: str) -> object:
    """The part-cache loader: text, or NOT_FOUND; raises _Transient otherwise."""
    if not budget.try_acquire("bible_api"):
        raise _Transient("budget")
    url = f"{BIBLE_API_BASE}/{quote(part.lower(), safe=':,-')}"
    try:
        response = http.get(url, params={"translation": translation},
                            read_timeout=BIBLE_API_READ_TIMEOUT)
    except httpx.TimeoutException:
        raise _Transient("timeout") from None
    except httpx.HTTPError:
        raise _Transient("network") from None
    if response.status_code == 404:
        return NOT_FOUND
    if response.status_code != 200:
        raise _Transient(f"status_{response.status_code}")
    try:
        data = response.json()
    except ValueError:
        raise _Transient("bad_json") from None
    if not isinstance(data, dict):
        raise _Transient("bad_json")
    text = data.get("text")
    if not isinstance(text, str):
        raise _Transient("bad_json")        # unreadable, never cached (owner decision 1)
    return text.strip() or NOT_FOUND


def _esv_part(part: str) -> object:
    """Text or NOT_FOUND from the ESV API; raises _Transient otherwise. Never cached."""
    key = _esv_key()
    if not key:
        raise _Transient("no_key")
    if not budget.try_acquire("esv"):
        raise _Transient("budget")
    params = {
        "q": part,
        "include-headings": "false",
        "include-footnotes": "false",
        "include-verse-numbers": "false",
        "include-passage-references": "false",
        "include-short-copyright": "true",   # keeps the required "(ESV)" credit
    }
    try:
        response = http.get(ESV_API_BASE, params=params,
                            headers={"Authorization": f"Token {key}"},
                            read_timeout=ESV_READ_TIMEOUT)
    except httpx.TimeoutException:
        raise _Transient("timeout") from None
    except httpx.HTTPError:
        raise _Transient("network") from None
    if response.status_code != 200:
        raise _Transient(f"status_{response.status_code}")
    try:
        data = response.json()
    except ValueError:
        raise _Transient("bad_json") from None
    passages = data.get("passages") if isinstance(data, dict) else None
    if not isinstance(passages, list):
        raise _Transient("bad_json")        # unreadable is "unavailable", not "not found"
    text = "\n\n".join(p.strip() for p in passages if isinstance(p, str) and p.strip())
    return text or NOT_FOUND


def fetch_part(part: str, translation: str) -> Part:
    """One normalized part: the cache (bible-api only), then the budget, then
    one upstream call. Never raises for an upstream failure (S Status rules)."""
    source = (TRANSLATIONS.get(translation) or (None, "bible-api"))[1]
    upstream = "esv" if source == "esv" else "bible_api"
    try:
        if upstream == "esv":
            result = _esv_part(part)
        else:
            result = _PART_CACHE.get_or_load(
                (translation, part.lower()), lambda: _bible_api_part(part, translation))
    except _Transient as exc:
        if exc.reason in _SKIP_REASONS:
            logger.info("passage_part_skipped reason=%s upstream=%s", exc.reason, upstream)
        else:
            logger.warning("passage_part_failed reason=%s upstream=%s", exc.reason, upstream)
        return Part(part, "unavailable", None)
    if result is NOT_FOUND:
        return Part(part, "not_found", None)
    return Part(part, "ok", result)


# --- statuses and texts (S Status rules; the one derivation) ---

def _combined_status(statuses: List[PartStatus]) -> PartStatus:
    """ok when every item is ok; else unavailable if any is; else not_found.
    No items at all is not_found, so an empty plan never reads as ok."""
    if statuses and all(s == "ok" for s in statuses):
        return "ok"
    if "unavailable" in statuses:
        return "unavailable"
    return "not_found"


def _joined(texts: List[Optional[str]]) -> Optional[str]:
    return "\n\n".join(t for t in texts if t) or None


def assemble_passage(reference: str, alternatives: List[str],
                     parts: List[List[Part]]) -> Passage:
    """Sections and passage from each alternative's fetched parts, in plan
    order. `alternatives` and `parts` come from the same plan_sections call."""
    sections = tuple(
        Section(
            reference=alternative,
            status=_combined_status([p.status for p in section_parts]),
            text=_joined([p.text for p in section_parts if p.status == "ok"]),
        )
        for alternative, section_parts in zip(alternatives, parts, strict=True)
    )
    return Passage(reference=reference,
                   status=_combined_status([s.status for s in sections]),
                   sections=sections)


def fetch_passage(reference: str, translation: str = DEFAULT_TRANSLATION) -> Passage:
    """Fetch every part of `reference`, one after another (no pool, no
    deadline; 2a clarification 27), and derive the statuses."""
    ref = reference.strip()
    sections = plan_sections(ref)
    parts = [[fetch_part(part, translation) for part in section_parts]
             for _alternative, section_parts in sections]
    return assemble_passage(ref, [alternative for alternative, _parts in sections], parts)


def get_passage_text(reference: str, translation: str = DEFAULT_TRANSLATION) -> Optional[str]:
    """The text of the `ok` sections joined with blank lines, or None. Never a
    sentinel (S; fixes inv. C9). usecases.passages re-exports it for slice 3."""
    passage = fetch_passage(reference, translation=translation)
    return _joined([s.text for s in passage.sections if s.status == "ok"])
