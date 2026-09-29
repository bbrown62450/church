"""Scripture references: the book table, the OT/NT classifier, the reading
pickers, the one bulletin-reading rule, and fetch normalization
(S `scripture_refs.py`; spec decision 9; F §5.3).

Pure: no I/O, no FastAPI, no Streamlit. `lib/scripture-refs.ts` (slice 2b)
ports everything above "Fetch only" and runs the same shared fixture,
`backend/tests/fixtures/shared/scripture_refs.json`. The fixture is
authoritative: change it first, then both ports.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Literal, Optional

Testament = Literal["ot", "psalm", "nt"]


@dataclass(frozen=True)
class Book:
    """A canonical book. `aliases` are stored normalized (see
    `normalize_book_text`: lower-case, no periods, arabic numerals), so
    "Gen" and "Gen." both match the alias "gen". The canonical name also
    matches and is not repeated in `aliases`."""

    name: str
    testament: Testament
    aliases: tuple[str, ...] = ()


BOOKS: tuple[Book, ...] = (
    # Old Testament
    Book("Genesis", "ot", ("gen",)),
    Book("Exodus", "ot", ("ex", "exod")),
    Book("Leviticus", "ot", ("lev",)),
    Book("Numbers", "ot", ("num",)),
    Book("Deuteronomy", "ot", ("deut",)),
    Book("Joshua", "ot", ("josh",)),
    Book("Judges", "ot", ("jdg", "judg")),
    Book("Ruth", "ot"),
    Book("1 Samuel", "ot", ("1 sam",)),
    Book("2 Samuel", "ot", ("2 sam",)),
    Book("1 Kings", "ot", ("1 kgs",)),
    Book("2 Kings", "ot", ("2 kgs",)),
    Book("1 Chronicles", "ot", ("1 chr", "1 chron")),
    Book("2 Chronicles", "ot", ("2 chr", "2 chron")),
    Book("Ezra", "ot"),
    Book("Nehemiah", "ot", ("neh",)),
    Book("Esther", "ot", ("esth",)),
    Book("Job", "ot"),
    Book("Psalms", "psalm", ("ps", "psa", "psalm", "pss")),
    Book("Proverbs", "ot", ("prov",)),
    Book("Ecclesiastes", "ot", ("eccl", "eccles")),
    Book("Song of Songs", "ot", ("canticles", "song", "song of solomon")),
    Book("Isaiah", "ot", ("isa",)),
    Book("Jeremiah", "ot", ("jer",)),
    Book("Lamentations", "ot", ("lam",)),
    Book("Ezekiel", "ot", ("ezek",)),
    Book("Daniel", "ot", ("dan",)),
    Book("Hosea", "ot", ("hos",)),
    Book("Joel", "ot"),
    Book("Amos", "ot"),
    Book("Obadiah", "ot", ("obad",)),
    Book("Jonah", "ot"),
    Book("Micah", "ot", ("mic",)),
    Book("Nahum", "ot", ("nah",)),
    Book("Habakkuk", "ot", ("hab",)),
    Book("Zephaniah", "ot", ("zeph",)),
    Book("Haggai", "ot", ("hag",)),
    Book("Zechariah", "ot", ("zech",)),
    Book("Malachi", "ot", ("mal",)),
    # Deuterocanon: "ot", except Psalm 151, which is a psalm
    Book("Tobit", "ot", ("tb", "tob")),
    Book("Judith", "ot", ("jdt", "jth")),
    Book("Additions to Esther", "ot", ("add esth",)),
    Book("Wisdom of Solomon", "ot", ("wis", "wisdom", "ws")),
    Book("Sirach", "ot", ("ecclesiasticus", "ecclus", "sir")),
    Book("Baruch", "ot", ("bar",)),
    Book("Letter of Jeremiah", "ot", ("ep jer",)),
    Book("Song of the Three", "ot", ("pr azar", "prayer of azariah",
                                     "song of the three jews", "song of the three young men")),
    Book("Susanna", "ot", ("sus",)),
    Book("Bel and the Dragon", "ot", ("bel",)),
    Book("1 Maccabees", "ot", ("1 macc", "1 mc")),
    Book("2 Maccabees", "ot", ("2 macc", "2 mc")),
    Book("3 Maccabees", "ot", ("3 macc", "3 mc")),
    Book("4 Maccabees", "ot", ("4 macc", "4 mc")),
    Book("1 Esdras", "ot", ("1 esd",)),
    Book("2 Esdras", "ot", ("2 esd",)),
    Book("Prayer of Manasseh", "ot", ("pr man",)),
    Book("Psalm 151", "psalm"),
    # New Testament
    Book("Matthew", "nt", ("mat", "matt", "mt")),
    Book("Mark", "nt", ("mk",)),
    Book("Luke", "nt", ("lk",)),
    Book("John", "nt", ("jn",)),
    Book("Acts", "nt"),
    Book("Romans", "nt", ("rm", "rom")),
    Book("1 Corinthians", "nt", ("1 cor",)),
    Book("2 Corinthians", "nt", ("2 cor",)),
    Book("Galatians", "nt", ("gal",)),
    Book("Ephesians", "nt", ("eph",)),
    Book("Philippians", "nt", ("phil", "php")),
    Book("Colossians", "nt", ("col",)),
    Book("1 Thessalonians", "nt", ("1 thess",)),
    Book("2 Thessalonians", "nt", ("2 thess",)),
    Book("1 Timothy", "nt", ("1 tim",)),
    Book("2 Timothy", "nt", ("2 tim",)),
    Book("Titus", "nt", ("tit",)),
    Book("Philemon", "nt", ("philem", "phlm")),
    Book("Hebrews", "nt", ("heb",)),
    Book("James", "nt", ("jas",)),
    Book("1 Peter", "nt", ("1 pet",)),
    Book("2 Peter", "nt", ("2 pet",)),
    Book("1 John", "nt", ("1 jn",)),
    Book("2 John", "nt", ("2 jn",)),
    Book("3 John", "nt", ("3 jn",)),
    Book("Jude", "nt"),
    Book("Revelation", "nt", ("rev", "revelations")),
)


def _alias_index() -> tuple[tuple[str, Book], ...]:
    """Every lookup key (the normalized name and each alias), longest first.
    A key that maps to two books is a table bug, so it fails at import."""
    index: dict[str, Book] = {}
    for book in BOOKS:
        for key in (normalize_book_text(book.name), *book.aliases):
            if key in index:
                raise ValueError(f"alias {key!r} is used by {index[key].name} and {book.name}")
            index[key] = book
    return tuple(sorted(index.items(), key=lambda kv: (-len(kv[0]), kv[0])))


_ORDINAL_PREFIX = re.compile(r"^(iii|ii|iv|i|first|second|third|fourth|1st|2nd|3rd|4th) ")
_ORDINAL_DIGIT = {
    "i": "1", "ii": "2", "iii": "3", "iv": "4",
    "first": "1", "second": "2", "third": "3", "fourth": "4",
    "1st": "1", "2nd": "2", "3rd": "3", "4th": "4",
}


def normalize_book_text(s: str) -> str:
    """Lower-case; drop a leading "*" and whitespace; remove "."; collapse
    spaces; map a roman or ordinal prefix followed by a space
    (i|ii|iii|iv|first|second|third|fourth|1st|2nd|3rd|4th) to 1–4, so
    "Isaiah" is untouched; then put a space after a leading 1–4 glued to a
    letter ("1john" → "1 john")."""
    s = s.lower()
    s = re.sub(r"^\s*\*?\s*", "", s)
    s = s.replace(".", "")
    s = re.sub(r"\s+", " ", s).strip()
    s = _ORDINAL_PREFIX.sub(lambda m: _ORDINAL_DIGIT[m.group(1)] + " ", s, count=1)
    s = re.sub(r"^([1-4])(?=[a-z])", r"\1 ", s)
    return s


_ALIASES = _alias_index()


def clean_lines(lines: list[str]) -> list[str]:
    """Trim each line and drop the blank ones."""
    return [line.strip() for line in lines if line and line.strip()]


def split_alternatives(ref: str) -> list[str]:
    """Split on " or " (any case, any whitespace around it) and trim; empty
    pieces are dropped. Fixes the case-sensitive split (inv. C9)."""
    return [p.strip() for p in re.split(r"\s+or\s+", ref, flags=re.IGNORECASE) if p.strip()]


def split_book(ref: str) -> Optional[tuple[Book, str]]:
    """The longest book name or alias at the start of the normalized text,
    followed by the end, a space or a digit. Returns the canonical book and
    the rest of the normalized text, trimmed ("Matthew 17:1-9" →
    (Matthew, "17:1-9")), or None."""
    text = normalize_book_text(ref)
    for key, book in _ALIASES:
        if text.startswith(key):
            after = text[len(key):]
            if after == "" or after[0] == " " or after[0] in "0123456789":
                return book, after.strip()
    return None


def classify(ref: str) -> Literal["ot", "psalm", "nt", "unknown"]:
    """The testament of one alternative's book, or "unknown"."""
    hit = split_book(ref)
    return hit[0].testament if hit else "unknown"


def is_nt_ref(ref: str) -> bool:
    """classify(ref) == "nt" (the name app.py used; slice 5a uses it)."""
    return classify(ref) == "nt"


def expand_ref_options(refs: list[str]) -> list[str]:
    """Clean the lines, expand every alternative, and de-duplicate in
    first-seen order (app.py's version was case-sensitive and kept
    duplicates)."""
    out: list[str] = []
    for line in clean_lines(refs):
        for alt in split_alternatives(line):
            if alt not in out:
                out.append(alt)
    return out


def picker_options(scriptures: list[str]) -> dict[str, list[str]]:
    """The two bulletin pickers: "nt" holds the NT options; "ot" holds
    everything else (ot, psalm and unknown), as app.py did."""
    options = expand_ref_options(scriptures)
    return {
        "ot": [o for o in options if classify(o) != "nt"],
        "nt": [o for o in options if classify(o) == "nt"],
    }


@dataclass(frozen=True)
class ReadingPair:
    ot: Optional[str]
    nt: Optional[str]
    ot_auto: bool
    nt_auto: bool


def _first_alternative_is_nt(line: str) -> bool:
    alternatives = split_alternatives(line)
    return bool(alternatives) and is_nt_ref(alternatives[0])


def resolve_readings(scriptures: list[str], ot_pick: Optional[str] = "",
                     nt_pick: Optional[str] = "") -> ReadingPair:
    """The only bulletin-reading rule (S `resolve_readings`; spec decision 9).

    A pick counts only when it is one of the current options for its side;
    otherwise that side is automatic. The automatic OT is the first line;
    the automatic NT is the first line other than the effective OT (whole-line
    comparison) whose first alternative is NT, so a Psalm is never the
    automatic NT. Lines are returned as written.
    """
    entries = clean_lines(scriptures)
    options = picker_options(entries)
    ot_pick = (ot_pick or "").strip()
    if ot_pick not in options["ot"]:
        ot_pick = ""
    nt_pick = (nt_pick or "").strip()
    if nt_pick not in options["nt"]:
        nt_pick = ""
    # The automatic OT skips the NT pick, so one reading never fills both slots
    # (owner, 2026-09-28: Acts picked as NT in Easter season).
    ot = ot_pick or next((e for e in entries if e != nt_pick), None)
    nt = nt_pick or next((e for e in entries if e != ot and _first_alternative_is_nt(e)), None)
    return ReadingPair(ot=ot, nt=nt, ot_auto=not ot_pick, nt_auto=not nt_pick)


def default_reading_pair(scriptures: list[str]) -> ReadingPair:
    """resolve_readings with no picks."""
    return resolve_readings(scriptures, "", "")


def default_nt_ref(scriptures: list[str]) -> Optional[str]:
    """The automatic NT reading (slice 3's hymn matching uses it)."""
    return default_reading_pair(scriptures).nt


# ---- Fetch only (Python only; the displayed text never changes) ----------


def normalize_for_fetch(ref: str) -> str:
    """The text sent upstream: drop a leading "*"; en and em dashes → "-";
    drop a verse-part letter after a digit ("9a" → "9"); remove parentheses;
    put a comma between two verse groups separated only by whitespace
    ("1-14 15-20" → "1-14, 15-20"); collapse doubled commas and spaces."""
    s = re.sub(r"^\s*\*\s*", "", ref)
    s = s.replace("–", "-").replace("—", "-")
    s = re.sub(r"(?<=\d)[A-Za-z](?![A-Za-z])", "", s)
    s = s.replace("(", "").replace(")", "")
    s = re.sub(r"(?<=\d)\s+(?=\d)", ", ", s)
    s = re.sub(r",(\s*,)+", ",", s)
    return re.sub(r"\s+", " ", s).strip()


def _book_name_from_ref(ref: str) -> Optional[str]:
    """The book in "Genesis 2:15-17" or "2 Kings 2:1-12"; None without a
    chapter:verse."""
    m = re.match(r"^(.+?)\s+\d+:\d+", ref.strip())
    if not m:
        return None
    return m.group(1).strip()


def _expand_part(part: str, last_book: Optional[str]) -> str:
    """Prefix a bare "3:1-7" with the carried book."""
    part = part.strip()
    if re.match(r"^\d+:\d+", part) and last_book:
        return f"{last_book} {part}"
    return part


def split_parts(ref: str) -> list[str]:
    """Split on ";" (dropping empty pieces) and carry the book into parts
    shaped like "3:1-7". Moved unchanged from scripture_fetcher.fetch_passage,
    quirks included: "Psalm 42; 43" leaves "43" bare, and a first part with
    no chapter:verse never sets the book."""
    last_book: Optional[str] = None
    parts: list[str] = []
    for raw in (p.strip() for p in ref.strip().split(";")):
        if not raw:
            continue
        full = _expand_part(raw, last_book)
        if not last_book:
            last_book = _book_name_from_ref(full)
        parts.append(full)
    return parts


_AND = re.compile(r"\s+and\s+")


def split_joined(ref: str) -> list[str]:
    """Split on " and " only where the text after it starts with a known book
    (the Easter Vigil's paired lines), and trim. "Psalm 42 and 43" stays
    whole."""
    text = ref.strip()
    pieces: list[str] = []
    start = 0
    for m in _AND.finditer(text):
        if split_book(text[m.end():]) is not None:
            pieces.append(text[start:m.start()].strip())
            start = m.end()
    pieces.append(text[start:].strip())
    return [p for p in pieces if p]


def scripture_key(ref: str) -> str:
    """A comparison key: normalize_for_fetch, lower-case, then remove
    whitespace, commas, periods and parentheses."""
    return re.sub(r"[\s,.()]", "", normalize_for_fetch(ref).lower())


# ---- Parsing for hymn matching (slice 3; Python only) ------------------------
#
# parse_refs reads a query reference or a hymn's scripture_refs field into
# book/chapter/verse spans (S Backend 2, owner decision 9). It reads the same
# BOOKS as classify, plus PARSE_ALIASES: the old matcher's abbreviations
# (worship_service._BOOK_ABBREVS) that BOOKS lacks. They live here, not in
# BOOKS, so the shared fixture and the TypeScript port stay unchanged (slice 3a
# plan, clarification 3); "is" (Isaiah) is one, which split_book and classify
# still do not accept.

PARSE_ALIASES: dict[str, str] = {
    "ge": "Genesis", "gn": "Genesis", "nm": "Numbers", "dt": "Deuteronomy",
    "jos": "Joshua", "est": "Esther", "prv": "Proverbs", "ecc": "Ecclesiastes",
    "sos": "Song of Songs", "is": "Isaiah", "jr": "Jeremiah", "ezk": "Ezekiel",
    "dnl": "Daniel", "ob": "Obadiah", "jon": "Jonah", "zep": "Zephaniah",
    "zec": "Zechariah", "mrk": "Mark", "luk": "Luke", "jhn": "John", "joh": "John",
    "1 thes": "1 Thessalonians", "2 thes": "2 Thessalonians", "phm": "Philemon",
    "jm": "James", "1 jhn": "1 John", "2 jhn": "2 John", "3 jhn": "3 John",
    "jud": "Jude", "rv": "Revelation",
}

# N and N-M are verses of chapter 1 in these books. Psalm 151 is one too, so
# "Psalm 151:1" (the key, then ":") is its verse 1 (owner decision 1).
SINGLE_CHAPTER_BOOKS = frozenset({
    "Obadiah", "Philemon", "2 John", "3 John", "Jude", "Song of the Three",
    "Letter of Jeremiah", "Susanna", "Bel and the Dragon", "Prayer of Manasseh",
    "Psalm 151",
})

WHOLE_CHAPTER_START = 0     # verse 0: from the start of the chapter
WHOLE_CHAPTER_END = 999     # verse 999: to the end of the chapter
WHOLE_BOOK_END = 999        # chapter 999: to the end of the book
MAX_CHAPTER = 150           # no book has more chapters (Psalms); a larger one is unparsed

# A period between digits ("John 3.16"): normalize_book_text drops periods, so
# the segment would read as chapter 316 (or "Ps 1.1" as Psalm 11). Unparsed.
_DOTTED_VERSE = re.compile(r"\d\s*\.\s*\d")


def _parse_index() -> tuple[tuple[str, Book], ...]:
    by_name = {book.name: book for book in BOOKS}
    index = dict(_ALIASES)
    for alias, name in PARSE_ALIASES.items():
        if alias in index:
            raise ValueError(f"parse alias {alias!r} is already a BOOKS key")
        index[alias] = by_name[name]                 # KeyError: not a BOOKS name
    for name in SINGLE_CHAPTER_BOOKS:
        by_name[name]                                # KeyError: not a BOOKS name
    return tuple(sorted(index.items(), key=lambda kv: (-len(kv[0]), kv[0])))


_PARSE_INDEX = _parse_index()


def book_keys(book_name: str) -> tuple[str, ...]:
    """Every normalized key that names the book (BOOKS and PARSE_ALIASES), longest first."""
    return tuple(key for key, book in _PARSE_INDEX if book.name == book_name)


@dataclass(frozen=True)
class RefSpan:
    """One passage: canonical book, (chapter, verse) start and end, inclusive.
    A whole chapter runs from verse 0 to verse 999; a whole book from 1:0 to 999:999.
    `broad` marks a whole-book reference (of a book with more than one chapter)
    and a chapter-only "ff" ("Psalm 148ff", chapter 148 only): hymn matching
    ranks them "chapter" at most (owner answer B, 2026-09-29). It is left out
    of equality, so the span itself still compares by book, start and end."""

    book: str
    start: tuple[int, int]
    end: tuple[int, int]
    broad: bool = field(default=False, compare=False)


@dataclass(frozen=True)
class ParsedRefs:
    spans: tuple[RefSpan, ...]
    unparsed: tuple[str, ...]        # normalized text of segments that could not be read


def _match_book(segment: str) -> Optional[tuple[Book, str]]:
    """The longest book key at the start of the normalized segment, followed by
    the end, a space, a digit or a ":" (dropped, so "Psalm 151:1" is Psalm 151
    verse 1), and the rest (normalized, trimmed)."""
    text = normalize_book_text(segment)
    for key, book in _PARSE_INDEX:
        if text.startswith(key):
            after = text[len(key):]
            if after == "" or after[0] == " " or after[0] in "0123456789":
                return book, after.strip()
            if after[0] == ":":
                return book, after[1:].strip()
    return None


_ITEM = re.compile(
    r"(?P<a>\d+)[a-d]?"
    r"(?::(?P<b>\d+)[a-d]?)?"
    r"(?:(?P<ff>ff?)|-(?P<c>\d+)[a-d]?(?::(?P<d>\d+)[a-d]?)?)?"
)


def _item_span(book: Book, item: str, context: Optional[int]) -> Optional[tuple[RefSpan, Optional[int]]]:
    """One location item and the chapter a following bare number belongs to (or None)."""
    m = _ITEM.fullmatch(item.replace(" ", ""))
    if not m:
        return None
    a, b, c, d = (int(g) if g else None for g in m.group("a", "b", "c", "d"))
    ff = bool(m.group("ff"))
    broad = False
    if b is not None:                                       # C:V, C:V-V, C:V-C:V, C:Vff
        start = (a, b)
        if ff:
            end = (a, WHOLE_CHAPTER_END)
        elif c is None:
            end = (a, b)
        elif d is None:
            end = (a, c)
        else:
            end = (c, d)
    elif d is not None:                                     # C-C:V
        start, end = (a, WHOLE_CHAPTER_START), (c, d)
    elif book.name in SINGLE_CHAPTER_BOOKS or context is not None:   # verses
        chapter = 1 if book.name in SINGLE_CHAPTER_BOOKS else context
        start = (chapter, a)
        end = (chapter, WHOLE_CHAPTER_END if ff else (c if c is not None else a))
    else:                                                   # C, C-C, Cff (that chapter only)
        start = (a, WHOLE_CHAPTER_START)
        end = (c if c is not None else a, WHOLE_CHAPTER_END)
        broad = ff                                          # owner answer B
    if start[0] < 1 or start > end or end[0] > MAX_CHAPTER:
        return None
    has_verses = b is not None or d is not None or context is not None
    return RefSpan(book.name, start, end, broad), (end[0] if has_verses else None)


def _segment_spans(book: Book, location: str) -> Optional[list[RefSpan]]:
    if not location:
        return [RefSpan(book.name, (1, WHOLE_CHAPTER_START), (WHOLE_BOOK_END, WHOLE_CHAPTER_END),
                        broad=book.name not in SINGLE_CHAPTER_BOOKS)]
    spans: list[RefSpan] = []
    context: Optional[int] = None
    for item in location.split(","):
        found = _item_span(book, item.strip(), context)
        if found is None:
            return None
        span, context = found
        spans.append(span)
    return spans


def split_segments(alternative: str) -> list[str]:
    """Split on ";" and newlines, and on "," when the text after it starts with a book."""
    out: list[str] = []
    for piece in re.split(r"[;\n]", alternative):
        piece = re.sub(r"\s+", " ", piece).strip()
        start = 0
        for m in re.finditer(",", piece):
            if _match_book(piece[m.end():]) is not None:
                out.append(piece[start:m.start()].strip())
                start = m.end()
        out.append(piece[start:].strip())
    return [s for s in out if s]


@lru_cache(maxsize=4096)
def parse_refs(text: str) -> ParsedRefs:
    """Every passage in `text` (S Backend 2 steps 1-7). Pure and cached on the raw string."""
    text = unicodedata.normalize("NFKC", text or "").replace("–", "-").replace("—", "-")
    spans: list[RefSpan] = []
    unparsed: list[str] = []
    for alternative in split_alternatives(text):
        book: Optional[Book] = None
        for segment in split_segments(alternative):
            if _DOTTED_VERSE.search(segment):
                unparsed.append(segment)
                continue
            hit = _match_book(segment)
            if hit is not None:
                book, location = hit
            elif book is not None:
                location = normalize_book_text(segment)
            else:
                unparsed.append(segment)
                continue
            found = _segment_spans(book, location)
            if found is None:
                unparsed.append(segment)
            else:
                spans.extend(found)
    return ParsedRefs(tuple(spans), tuple(unparsed))


def spans_overlap(a: RefSpan, b: RefSpan) -> bool:
    """Same book and the passages share at least one verse."""
    return a.book == b.book and a.start <= b.end and b.start <= a.end


def same_chapter(a: RefSpan, b: RefSpan) -> bool:
    """Same book and the chapter ranges intersect."""
    return a.book == b.book and a.start[0] <= b.end[0] and b.start[0] <= a.end[0]
