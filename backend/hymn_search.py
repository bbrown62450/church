"""Pure hymn helpers for slice 3 (S Backend 1 and 2; owner decision 9; owner
answer Q2 of 2026-09-29):

- normalize_title and usage_key: the recent-use key is the title alone,
  punctuation ignored, so a hymn sung from one hymnal is recognized when it is
  picked from another under a different number (owner answers Q2 and A).
- parse_themes: a hymn's theme field (None, a list, "A, B", "A; B" or a
  Postgres array literal '{A,"B c"}') as a clean list.
- match_hymns: scripture matching on parsed book/chapter/verse spans, in two
  tiers, "passage" and "chapter".
- evenly_spaced: a deterministic even sample.

No I/O, no FastAPI, no Streamlit. Records are anything with `title` and
`scripture_refs` attributes (repos.hymns.HymnRecord).
"""
from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Literal, Optional, Sequence

import scripture_refs
from scripture_refs import RefSpan, parse_refs, same_chapter, spans_overlap

Strength = Literal["passage", "chapter"]
_TIER = {"passage": 0, "chapter": 1}


def normalize_title(title: Optional[str]) -> str:
    """NFKC, whitespace collapsed, stripped and casefolded."""
    text = unicodedata.normalize("NFKC", title or "")
    return re.sub(r"\s+", " ", text).strip().casefold()


_DASHES = re.compile(r"[-‐‑–—]")


def usage_key(title: Optional[str]) -> str:
    """The recent-use key: the title alone (owner answer Q2), ignoring
    punctuation (owner answer A, 2026-09-29): NFKC; curly apostrophes as "'";
    hyphens and dashes as spaces; everything but letters, digits, "_" and
    spaces removed; whitespace collapsed; casefolded; a leading "oh " as "o ".
    Leading articles stay. normalize_title is unchanged (exact-title resolution)."""
    text = unicodedata.normalize("NFKC", title or "").replace("’", "'").replace("‘", "'")
    text = _DASHES.sub(" ", text)
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip().casefold()
    return "o " + text[3:] if text.startswith("oh ") else text


def _split_array_literal(body: str) -> list[str]:
    """The items of a Postgres array literal body: commas split, double quotes group."""
    items, current, quoted, escaped = [], [], False, False
    for ch in body:
        if escaped:
            current.append(ch)
            escaped = False
        elif ch == "\\" and quoted:
            escaped = True
        elif ch == '"':
            quoted = not quoted
        elif ch == "," and not quoted:
            items.append("".join(current))
            current = []
        else:
            current.append(ch)
    items.append("".join(current))
    return items


def parse_themes(theme: Any) -> list[str]:
    """Clean theme strings in first-seen order, blanks and repeats dropped."""
    if theme is None:
        raw: list[str] = []
    elif isinstance(theme, (list, tuple)):
        raw = [str(t) for t in theme if t is not None]
    else:
        text = str(theme).strip()
        if text.startswith("{") and text.endswith("}"):
            raw = _split_array_literal(text[1:-1])
        else:
            raw = re.split(r"[,;]", text)
    out: list[str] = []
    for item in raw:
        cleaned = re.sub(r"\s+", " ", item).strip().strip('"').strip()
        if cleaned and cleaned.casefold() not in {o.casefold() for o in out}:
            out.append(cleaned)
    return out


def evenly_spaced(items: Sequence[Any], k: int) -> list[Any]:
    """items[floor(i * len / k)] for i in 0..k-1; the whole list when k >= len."""
    n = len(items)
    if k >= n:
        return list(items)
    if k <= 0:
        return []
    return [items[math.floor(i * n / k)] for i in range(k)]


@dataclass(frozen=True)
class HymnMatch:
    record: Any
    strength: Strength
    matched_refs: tuple[str, ...]


@dataclass(frozen=True)
class MatchResult:
    items: tuple[HymnMatch, ...]
    total_matched: int
    refs_used: tuple[str, ...]
    unparsed_refs: tuple[str, ...]


_DOTTED = re.compile(r"(\d)\s*\.\s*(\d)")
_MID_ORDINAL = re.compile(r"(?<![0-9a-z])(iii|ii|i|first|second|third|1st|2nd|3rd) (?=[a-z])")
_ORDINAL_DIGIT = {"i": "1", "ii": "2", "iii": "3", "first": "1", "second": "2", "third": "3",
                  "1st": "1", "2nd": "2", "3rd": "3"}
_FALLBACK_CHAPTERS = 11          # a query range's first chapter and the next ten


def _text_fallback(query: RefSpan, hymn_text: str) -> bool:
    """A boundary-aware test on a hymn segment the parser could not read: the
    query's book (any key longer than 2 characters) and one of its chapters
    (the first 11), never inside a longer number or after "1 " (so "Psalm 1"
    never hits "Psalm 119", "John 3" never "1 John 3"). A dotted verse
    ("3.16") reads as "3:16", and an ordinal inside the text ("see I John")
    as its digit (owner decision 1)."""
    text = scripture_refs.normalize_book_text(_DOTTED.sub(r"\1:\2", hymn_text))
    text = _MID_ORDINAL.sub(lambda m: _ORDINAL_DIGIT[m.group(1)] + " ", text)
    first = query.start[0]
    last = min(query.end[0], first + _FALLBACK_CHAPTERS - 1)
    chapters = "|".join(str(c) for c in range(first, last + 1))
    for key in scripture_refs.book_keys(query.book):
        if len(key) <= 2:
            continue
        pattern = r"(?<![0-9a-z])(?<!\d )" + re.escape(key) + r"\s*(?:" + chapters + r")(?![0-9])"
        if re.search(pattern, text):
            return True
    return False


def _strength(query: tuple[RefSpan, ...], hymn: scripture_refs.ParsedRefs) -> Optional[Strength]:
    # A whole-book or chapter-only "ff" hymn tag is too broad for "passage" (owner answer B).
    if any(spans_overlap(q, h) for q in query for h in hymn.spans if not h.broad):
        return "passage"
    if any(same_chapter(q, h) for q in query for h in hymn.spans):
        return "chapter"
    if any(_text_fallback(q, text) for q in query for text in hymn.unparsed):
        return "chapter"
    return None


def match_hymns(pool: Sequence[Any], refs: Sequence[str], *, limit_per_ref: int = 50,
                max_results: int = 20) -> MatchResult:
    """Hymns in `pool` whose scripture_refs match any of `refs` (already trimmed
    and split on " or "). Passage tier first, then chapter; within a tier by
    the first matching ref, then pool order. `limit_per_ref` caps the hymns
    attributed to each ref (a hymn counts once, at its first ref);
    `total_matched` is counted after that cap and before `max_results`."""
    queries: list[tuple[str, tuple[RefSpan, ...]]] = []
    unparsed: list[str] = []
    for ref in refs:
        parsed = parse_refs(ref)
        if parsed.spans:
            queries.append((ref, parsed.spans))
        else:
            unparsed.append(ref)
    found = []
    for position, hymn in enumerate(pool):
        title = (getattr(hymn, "title", None) or "").strip()
        text = (getattr(hymn, "scripture_refs", None) or "").strip()
        if not title or not text or not queries:
            continue
        parsed = parse_refs(text)
        best: Optional[Strength] = None
        first: Optional[int] = None
        matched: list[str] = []
        for index, (ref, spans) in enumerate(queries):
            strength = _strength(spans, parsed)
            if strength is None:
                continue
            matched.append(ref)
            first = index if first is None else first
            if best is None or _TIER[strength] < _TIER[best]:
                best = strength
        if best is not None:
            found.append((_TIER[best], first, position, HymnMatch(hymn, best, tuple(matched))))
    found.sort(key=lambda row: row[:3])
    per_ref: dict[int, int] = {}
    kept: list[HymnMatch] = []
    for _tier, first, _position, match in found:
        if per_ref.get(first, 0) >= limit_per_ref:
            continue
        per_ref[first] = per_ref.get(first, 0) + 1
        kept.append(match)
    return MatchResult(items=tuple(kept[:max_results]), total_matched=len(kept),
                       refs_used=tuple(refs), unparsed_refs=tuple(unparsed))
