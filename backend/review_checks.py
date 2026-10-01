"""The service reviewer's code checks (reviewer spec, "Layer 1: code checks";
slice 4 spec, "Amendment 2026-09-26: service reviewer").

Deterministic and free: they run on every review, even with no OpenAI key, and
their notes come first because they are certain. Each note is
Note(tag, text, source="code"); `match` is the quoted text an AI note repeats
(usecases.liturgy_review drops such a repeat).

- check_card(text), in the table's order, each point once:
  1. stock seasonal phrases, any case ("in this season of", "as we journey",
     "on this … Sunday" with one to four words between, "in this ordinary
     time"), in the order they appear;
  2. naming Ordinary Time, wherever it appears outside a stock phrase that
     already said so;
  3. a scripture reference: a book name or alias from scripture_refs.BOOKS
     (the one book table; no second list), written with a capital letter,
     followed by a chapter number ("Mark 4", "1 Sam 3:10"), and kept only
     when scripture_refs.parse_refs reads it as a passage (so "Psalm 1" is
     never "Psalm 119", and "Psalm 200" is no reference).
- check_openings(texts): the first two words of each card after any leading
  "Leader:" or "People:" label, any case, punctuation dropped; each pair two
  or more cards share is one "Across the service" note.

A word in a stock phrase or an opening is 1 to 30 characters, and a note's
text and match are cut to MAX_NOTE_CHARS, so a giant word or a run of
spaces never makes a long note.

Pure: no I/O, no FastAPI, no AI (tests/test_no_streamlit_in_core.py).
"""
from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from functools import lru_cache

import scripture_refs

TAGS = ("checklist", "rules", "voice", "read_aloud", "theology", "repetition")
MAX_NOTE_CHARS = 240                                 # a note's text, and its quoted match, at most


@dataclass(frozen=True)
class Note:
    tag: str                                         # one of TAGS
    text: str                                        # one sentence
    source: str = "code"                             # "code" or "ai"
    match: str = field(default="", compare=False)    # a code note's quoted text, for the merge


STOCK_PHRASE = re.compile(
    r"\b(?:in this season of|as we journey|on this (?:[\w'’-]{1,30}\s+){1,4}?sunday|in this ordinary time)\b",
    re.IGNORECASE,
)
ORDINARY_TIME = re.compile(r"\bordinary time\b", re.IGNORECASE)
STOCK_NOTE = 'Stock phrase "{match}". Say it more naturally.'
ORDINARY_NOTE = "Names Ordinary Time. Leave the season unnamed."
CITES_NOTE = "Cites {match}. Draw on the reading's themes without naming it."
OPENING_NOTE = 'Several prayers open with "{words}".'

_LABEL = re.compile(r"^\s*(?:leader|people)\s*:\s*", re.IGNORECASE)
_WORD = re.compile(r"(?<![^\W_])[^\W_]{1,30}(?:['’][^\W_]{1,30})*(?![^\W_])")   # a longer run is no word


def _clip(text: str) -> str:
    return text[:MAX_NOTE_CHARS]


def scripture_book_keys() -> tuple[str, ...]:
    """Every BOOKS name (normalized) and alias, longest first: what a reference can start with."""
    keys = {scripture_refs.normalize_book_text(book.name) for book in scripture_refs.BOOKS}
    keys.update(alias for book in scripture_refs.BOOKS for alias in book.aliases)
    return tuple(sorted(keys, key=lambda k: (-len(k), k)))


def _key_pattern(key: str) -> str:
    """'1 sam' -> '1\\s*sam\\.?': a numeral may touch the name; words are spaced; an abbreviation may end in '.'."""
    first, *rest = key.split(" ")
    if first.isdigit() and rest:
        head = re.escape(first) + r"\s*" + re.escape(rest[0])
        rest = rest[1:]
    else:
        head = re.escape(first)
    return r"\s+".join([head, *(re.escape(word) for word in rest)]) + r"\.?"


@lru_cache(maxsize=1)
def _reference_pattern() -> re.Pattern[str]:
    books = "|".join(_key_pattern(key) for key in scripture_book_keys())
    return re.compile(
        r"(?<![\w])(?P<book>" + books + r")\s+"
        r"(?P<loc>\d{1,3}(?::\d{1,3}[a-d]?(?:[-–]\d{1,3}(?::\d{1,3})?[a-d]?)?)?)(?![\w:])",
        re.IGNORECASE,
    )


def _is_reference(match: re.Match[str]) -> bool:
    book = match.group("book")
    letter = next((c for c in book if c.isalpha()), "")
    if not letter.isupper():                         # "we mark 3 years" is a verb, not Mark 3
        return False
    parsed = scripture_refs.parse_refs(f"{book} {match.group('loc')}")
    return bool(parsed.spans) and not parsed.unparsed


def check_card(text: str) -> list[Note]:
    """The code notes for one card, in the table's order, each point once."""
    notes: list[Note] = []
    seen: set[str] = set()

    def add(note: Note) -> None:
        if note.text.lower() not in seen:
            seen.add(note.text.lower())
            notes.append(note)

    stock = list(STOCK_PHRASE.finditer(text or ""))
    for m in stock:
        quoted = _clip(m.group(0))
        add(Note("rules", _clip(STOCK_NOTE.format(match=quoted)), match=quoted))
    inside = [(m.start(), m.end()) for m in stock if ORDINARY_TIME.search(m.group(0))]
    for m in ORDINARY_TIME.finditer(text or ""):
        if not any(start <= m.start() and m.end() <= end for start, end in inside):
            add(Note("rules", ORDINARY_NOTE, match=m.group(0)))
            break
    for m in _reference_pattern().finditer(text or ""):
        if _is_reference(m):
            cited = _clip(m.group(0).strip())
            add(Note("rules", _clip(CITES_NOTE.format(match=cited)), match=cited))
    return notes


def opening_words(text: str) -> list[str]:
    """The first two words after any leading "Leader:" or "People:" label, punctuation dropped."""
    return _WORD.findall(_LABEL.sub("", text or "", count=1))[:2]


def check_openings(texts: Sequence[str]) -> list[Note]:
    """One "Across the service" note per opening pair that two or more cards share, in order."""
    first: dict[str, str] = {}
    counts: dict[str, int] = {}
    for text in texts:
        words = opening_words(text)
        if len(words) < 2:
            continue
        key = " ".join(w.lower() for w in words)
        first.setdefault(key, " ".join(words))
        counts[key] = counts.get(key, 0) + 1
    return [Note("repetition", _clip(OPENING_NOTE.format(words=_clip(words))), match=_clip(words))
            for key, words in first.items() if counts[key] > 1]
