#!/usr/bin/env python3
"""Hymn year and familiarity from Hymnary.org's public scripture API.

Hymnary.org's website sits behind a bot challenge, so we never scrape it. The
public API (API_URL?reference=...) answers plain requests and returns, for
each text that cites the reference: its title, "number of hymnals" (our
familiarity signal), often "date", and people fields with life dates such as
"Perronet, Edward, 1721-1792".

The API returns at most RESULT_CAP texts per reference, sorted by first line,
with no way to page past them: under "Psalm 23" it stops at "When it seems
that all is hopeless" and never lists "Ye Servants of God" (723 hymnals).
Hymns cited only by such a broad reference can therefore stay unknown, and
the CLI names every reference that hit the cap.

The fetch function is injected so tests never touch the network; the CLI in
backfill_hymn_facts.py supplies the real, throttled one.
"""
import re
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy import or_, select

from db import session_scope
from db.models import Hymn, HymnCatalog

API_URL = "https://hymnary.org/api/scripture"
PEOPLE_FIELDS = ("author", "translator", "paraphraser", "adapter", "alterer")
BIRTH_ONLY_OFFSET = 35   # a living writer born in 1936 counts as writing around 1971
WRITE_BATCH = 50
RESULT_CAP = 100         # most texts the API returns for one reference

Fetch = Callable[[str], Any]

_YEAR = re.compile(r"\b(1\d{3}|20\d{2})\b")
_LIFE = re.compile(r"(\d{4})\s*-\s*(\d{4})?")
_REF_BREAK = re.compile(r"\s*(?:;|\n|,(?=\s*[1-3]?\s?[A-Za-z]))\s*")
_ARTICLE = re.compile(r"^(the|a|an) ")


def _person_year(value: str) -> Optional[int]:
    """Latest year a writer could have written: the death year, or the birth
    year + BIRTH_ONLY_OFFSET when only a birth year is known."""
    years = [int(died) if died else int(born) + BIRTH_ONLY_OFFSET
             for born, died in _LIFE.findall(value)]
    return max(years) if years else None


def text_year(record: Dict[str, Any]) -> Optional[int]:
    """The year the words were written: the first 4-digit year in `date`, else
    the latest year implied by the writers' life dates. None when unknown."""
    match = _YEAR.search(str(record.get("date") or ""))
    if match:
        return int(match.group(1))
    years = [y for field in PEOPLE_FIELDS
             if (y := _person_year(str(record.get(field) or ""))) is not None]
    return max(years) if years else None


def hymnal_count(record: Dict[str, Any]) -> Optional[int]:
    digits = re.sub(r"\D", "", str(record.get("number of hymnals") or ""))
    return int(digits) if digits else None


def normalize_title(title: str) -> str:
    """Lowercase, punctuation dropped, a leading "the/a/an" removed."""
    t = re.sub(r"[^\w\s]", " ", (title or "").lower())
    t = re.sub(r"\s+", " ", t).strip()
    return _ARTICLE.sub("", t)


def split_refs(refs: Optional[str]) -> List[str]:
    """Split stored scripture references on ';', newlines, and commas that
    start a new book ("Isaiah 6:1-8, Revelation 4:8"), but not on commas
    inside one reference ("Romans 4:1-5, 13-17")."""
    return [r for r in _REF_BREAK.split((refs or "").strip()) if r]


def _records(results: Any) -> List[Any]:
    """The text records in one API response: a dict keyed by first line, a
    list, or [] / None when nothing cites the reference."""
    return list(results.values()) if isinstance(results, dict) else list(results or [])


def is_truncated(results: Any) -> bool:
    """True when a response holds RESULT_CAP texts, so the API may have cut
    off texts that also cite the reference."""
    return len(_records(results)) >= RESULT_CAP


def _text_id(record: Dict[str, Any]) -> str:
    """Identifies one text, so a text listed under two references counts once."""
    return record.get("text link") or repr(sorted(record.items()))


def find_facts(title: str, refs: Optional[str], fetch: Fetch,
               cache: Dict[str, Any]) -> Optional[Dict[str, Optional[int]]]:
    """Look up one hymn: query each of its references (cached per reference),
    collect every text whose title matches, and return the facts of one of
    them, or None when nothing matches.

    Hymnary often gives one title to several texts (under "Psalm 23", a modern
    "The Lord's My Shepherd" in 14 hymnals is listed before the Rous metrical
    psalm in 769). We take the text printed in the most hymnals, since that is
    the one a hymnal is most likely to mean by the title; ties go to the
    earliest listed. Both facts come from that one record, so a text never
    borrows another text's year.

    That choice needs every same-title text in hand. When several texts share
    the title and any response hit RESULT_CAP, the cap may have dropped the
    most-published one, so we return None: a guess is never overwritten, while
    an unknown can still be filled by hand. The live "Psalm 23" response is
    capped, so "The Lord's My Shepherd" cited only by it stays unknown. A
    single match in a capped response is still taken; nothing in the response
    shows it is ambiguous."""
    want = normalize_title(title)
    if not want:
        return None
    matches: Dict[str, Dict[str, Any]] = {}
    truncated = False
    for ref in split_refs(refs):
        if ref not in cache:
            cache[ref] = fetch(ref)
        truncated = truncated or is_truncated(cache[ref])
        for record in _records(cache[ref]):
            if isinstance(record, dict) and normalize_title(record.get("title", "")) == want:
                matches.setdefault(_text_id(record), record)
    if not matches or (truncated and len(matches) > 1):
        return None
    best = None
    for record in matches.values():
        count = hymnal_count(record)
        if best is None or (count is not None and (best[1] is None or count > best[1])):
            best = (record, count)
    return {"text_year": text_year(best[0]), "hymnal_count": best[1]}


def _write(updates: List[tuple]) -> None:
    """Fill blanks only: a value set since we read the row is kept."""
    with session_scope() as session:
        for model, row_id, values in updates:
            row = session.get(model, row_id)
            if row is None:
                continue
            for attr, value in values.items():
                if getattr(row, attr) is None:
                    setattr(row, attr, value)


def run_backfill(fetch: Fetch, *, dry_run: bool = False,
                 on_progress: Optional[Callable[[int, int], None]] = None) -> Dict[str, int]:
    """Fill blank text_year / hymnal_count on hymn_catalog and hymns rows.

    Never overwrites a value, so re-runs are safe and manual corrections
    survive. Network calls happen outside any database transaction; writes go
    in batches of WRITE_BATCH.
    """
    targets = []
    with session_scope() as session:
        for model in (HymnCatalog, Hymn):
            rows = session.execute(
                select(model.id, model.title, model.scripture_refs, model.text_year, model.hymnal_count)
                .where(or_(model.text_year.is_(None), model.hymnal_count.is_(None)))
            ).all()
            targets += [(model, *row) for row in rows]

    cache: Dict[str, Any] = {}
    stats = {"checked": 0, "matched": 0, "updated": 0, "unknown": 0}
    pending: List[tuple] = []
    for model, row_id, title, refs, year, count in targets:
        stats["checked"] += 1
        facts = find_facts(title or "", refs, fetch, cache)
        if facts is None:
            stats["unknown"] += 1
        else:
            stats["matched"] += 1
            current = {"text_year": year, "hymnal_count": count}
            values = {k: v for k, v in facts.items() if v is not None and current[k] is None}
            if values:
                stats["updated"] += 1
                pending.append((model, row_id, values))
        if not dry_run and len(pending) >= WRITE_BATCH:
            _write(pending)
            pending = []
        if on_progress:
            on_progress(stats["checked"], len(targets))
    if not dry_run and pending:
        _write(pending)
    return stats
