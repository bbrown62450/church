#!/usr/bin/env python3
"""
Revised Common Lectionary readings for one date (slice 2).

Two sources, looked up for exactly the date asked: Lectio (lectio-api.org, by
date) and the Vanderbilt Divinity Library liturgical-year CSV. This module is
pure parsing, naming and merging plus the two fetchers and loaders; caching,
the parallel lookup and the status rules live in usecases/lectionary.py.
"""

import csv
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Literal, Optional

import httpx

from cache import CacheableFailure
from integrations import http
from scripture_refs import scripture_key, split_alternatives, split_book

logger = logging.getLogger(__name__)

LECTIO_API_URL = "https://lectio-api.org/api/v1/readings"

# Liturgical year CSV URLs: 2025-26 (Year A), 2026-27 (Year B), 2027-28 (Year C)
VANDERBILT_YEAR_URL = "https://lectionary.library.vanderbilt.edu/calendar/{year}/?season=all&download=csv"


# --- Slice 2 domain: the calendar and occasion names (S Lectionary domain; decision A) ---
#
# Pure date arithmetic: no I/O and no clock. Names come from the date alone, never from
# Lectio's season string.

ORDINALS: tuple[str, ...] = (
    "First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh",
    "Eighth", "Ninth", "Tenth", "Eleventh", "Twelfth", "Thirteenth", "Fourteenth",
    "Fifteenth", "Sixteenth", "Seventeenth", "Eighteenth", "Nineteenth", "Twentieth",
    "Twenty-First", "Twenty-Second", "Twenty-Third", "Twenty-Fourth",
    "Twenty-Fifth", "Twenty-Sixth", "Twenty-Seventh", "Twenty-Eighth",
)

_SUNDAY = 6  # date.weekday()
_WEEKDAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")

_FIXED_FEASTS = {
    (12, 24): "Christmas Eve",
    (12, 25): "Nativity of the Lord",
    (1, 1): "New Year's Day",
    (1, 6): "Epiphany of the Lord",
    (11, 1): "All Saints Day",
}
_EASTER_FEASTS = {  # days from Easter Sunday
    -46: "Ash Wednesday",
    -3: "Maundy Thursday",
    -2: "Good Friday",
    -1: "Holy Saturday",
    39: "Ascension of the Lord",
}


def easter_date(year: int) -> date:
    """Easter Sunday for `year` (Anonymous Gregorian algorithm)."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def advent_sunday(year: int) -> date:
    """The First Sunday of Advent in `year`: the Sunday from Nov 27 to Dec 3."""
    nov27 = date(year, 11, 27)
    return nov27 + timedelta(days=(_SUNDAY - nov27.weekday()) % 7)


def liturgical_year_for(d: date) -> str:
    """The Vanderbilt year file that holds `d`, e.g. "2025-26" (fixes inv. C2).

    A year file runs from Advent 1 to the day before the next Advent 1.
    """
    y = d.year if d >= advent_sunday(d.year) else d.year - 1
    return f"{y}-{(y + 1) % 100:02d}"


def ordinal_word(n: int) -> str:
    """1 -> "First" ... 28 -> "Twenty-Eighth"; ValueError outside 1-28.

    28 is the largest count after Pentecost in any year (clarification 9).
    """
    if not 1 <= n <= len(ORDINALS):
        raise ValueError(f"no ordinal word for {n}")
    return ORDINALS[n - 1]


def _baptism_of_the_lord(year: int) -> date:
    """The first Sunday after Jan 6 (Jan 7-13). A Sunday Jan 6 is the Epiphany itself."""
    jan6 = date(year, 1, 6)
    return jan6 + timedelta(days=(_SUNDAY - jan6.weekday()) % 7 or 7)


def _ordinary_time_name(d: date) -> str | None:
    """The computed ordinary-time name of a Sunday, ignoring the named days.

    "{Ordinal} Sunday after the Epiphany" from the Baptism of the Lord ("First") to
    Transfiguration Sunday, and "{Ordinal} Sunday after Pentecost" from Trinity Sunday
    ("First") to Christ the King. None for any other date. `sunday_name` checks the
    named days first; the Vanderbilt Proper rename (Task 6b) uses this directly when
    `sunday_name(d)` is "All Saints Day" (clarification 30).
    """
    if d.weekday() != _SUNDAY:
        return None
    easter = easter_date(d.year)
    baptism = _baptism_of_the_lord(d.year)
    transfiguration = easter - timedelta(days=49)
    if baptism <= d <= transfiguration:
        return f"{ordinal_word((d - baptism).days // 7 + 1)} Sunday after the Epiphany"
    pentecost = easter + timedelta(days=49)
    if pentecost < d < advent_sunday(d.year):
        return f"{ordinal_word((d - pentecost).days // 7)} Sunday after Pentecost"
    return None


def sunday_name(d: date) -> str | None:
    """The occasion name of a Sunday, from the date alone; None for any other day.

    Checked in this order: the Christmas season (owner answer Q3), Advent, Lent, Palm
    Sunday, Easter and its Sundays, the Day of Pentecost; then the named days, which
    always win over the computed ordinal (decision A); then `_ordinary_time_name`.
    The Sunday before Advent 1 is "Christ the King" (owner decision 2026-09-28).
    A Sunday Dec 25 or Jan 6 returns None: `lectio_set_name` then takes
    "Nativity of the Lord" or "Epiphany of the Lord" from `weekday_feast_name`.
    """
    if d.weekday() != _SUNDAY:
        return None
    y = d.year
    if (d.month == 12 and d.day >= 26) or (d.month == 1 and d.day == 1):
        return "First Sunday after Christmas Day"
    if d.month == 1 and 2 <= d.day <= 5:
        return "Second Sunday after Christmas Day"
    advent1 = advent_sunday(y)
    if advent1 <= d <= date(y, 12, 24):
        return f"{ORDINALS[(d - advent1).days // 7]} Sunday of Advent"
    easter = easter_date(y)
    palm = easter - timedelta(days=7)
    lent1 = easter - timedelta(days=42)
    if lent1 <= d < palm:
        return f"{ORDINALS[(d - lent1).days // 7]} Sunday in Lent"
    if d == palm:
        return "Palm Sunday"
    if d == easter:
        return "Easter Sunday"
    pentecost = easter + timedelta(days=49)
    if easter < d < pentecost:
        return f"{ORDINALS[(d - easter).days // 7]} Sunday of Easter"
    if d == pentecost:
        return "Day of Pentecost"
    if d == _baptism_of_the_lord(y):
        return "Baptism of the Lord"
    if d == easter - timedelta(days=49):
        return "Transfiguration Sunday"
    if d == pentecost + timedelta(days=7):
        return "Trinity Sunday"
    if d.month == 11 and d.day == 1:
        return "All Saints Day"
    if d == advent1 - timedelta(days=7):
        return "Christ the King"
    return _ordinary_time_name(d)


def weekday_feast_name(d: date) -> str | None:
    """The feast on `d`, or None. Date-only: a fixed feast on a Sunday is still named."""
    fixed = _FIXED_FEASTS.get((d.month, d.day))
    if fixed is not None:
        return fixed
    return _EASTER_FEASTS.get((d - easter_date(d.year)).days)


def church_season(d: date) -> str:
    """The church season of `d`, for the AI hymn prompt (slice 3b plan, owner answer 3).

    Date arithmetic only, from the same calendar as the occasion names: "Advent" from
    Advent 1 to December 23; "Christmas Eve"; "Christmas" from December 25 to January 5;
    "Epiphany of the Lord" (January 6); "Season after the Epiphany" to the day before
    Ash Wednesday (Transfiguration Sunday included); "Lent" to the Saturday before Palm
    Sunday; "Holy Week" from Palm Sunday to Holy Saturday; "Easter" from Easter Day to
    the day before Pentecost; "Day of Pentecost"; then "Season after Pentecost" to the
    day before Advent 1 (Christ the King included). Every date has exactly one.
    """
    if (d.month == 12 and d.day >= 25) or (d.month == 1 and d.day <= 5):
        return "Christmas"
    if d.month == 12 and d.day == 24:
        return "Christmas Eve"
    advent1 = advent_sunday(d.year)
    if d >= advent1:
        return "Advent"
    if d.month == 1 and d.day == 6:
        return "Epiphany of the Lord"
    easter = easter_date(d.year)
    pentecost = easter + timedelta(days=49)
    if d < easter - timedelta(days=46):
        return "Season after the Epiphany"
    if d < easter - timedelta(days=7):
        return "Lent"
    if d < easter:
        return "Holy Week"
    if d < pentecost:
        return "Easter"
    if d == pentecost:
        return "Day of Pentecost"
    return "Season after Pentecost"


@dataclass(frozen=True)
class LectioGroup:
    """One Lectio reading group; `scriptures` is the four lines minus blanks (Task 6b parses)."""

    first: str
    psalm: str
    second: str
    gospel: str
    scriptures: tuple[str, ...]


@dataclass(frozen=True)
class LectioDay:
    """One Lectio date: its groups, plus `season` and `year` ("" when missing) and `dayName`."""

    groups: tuple[LectioGroup, ...]
    season: str
    year: str
    day_name: str | None


# A bare Proper number ("Proper 23", "proper 22 (27)", "Proper 22\xa0(27)") is never shown (owner decision A):
# lectio_set_name falls through past such a dayName and _vanderbilt_name renames such a Sunday row.
_PROPER = re.compile(r"proper\s+\d+(\s*\(\d+\))?", re.IGNORECASE)


def _is_proper(text: str) -> bool:
    """True when `text`, trimmed and with its whitespace (NBSP included) collapsed, is only a Proper number."""
    return _PROPER.fullmatch(" ".join(text.split())) is not None


def lectio_set_name(day: LectioDay, d: date) -> str:
    """The name of a Lectio-only set on `d` (S "Names for Lectio-only sets").

    1. Lectio's dayName, when present and not just a Proper number;
    2. `sunday_name(d)`, then `weekday_feast_name(d)`: so a weekday never gets a Sunday
       name, and a Sunday Dec 25 or Jan 6 gets its feast name (owner answer Q3);
    3. "{season} — Year {year}", when both are present;
    4. the weekday's name ("Sunday" for a Sunday).
    `merge` (Task 6b) adds " (2)", " (3)" when several sets share a name.
    """
    day_name = (day.day_name or "").strip()
    if day_name and not _is_proper(day_name):
        return day_name
    computed = sunday_name(d) or weekday_feast_name(d)
    if computed:
        return computed
    season, year = day.season.strip(), day.year.strip()
    if season and year:
        return f"{season} — Year {year}"
    return _WEEKDAY_NAMES[d.weekday()]


# ---------------------------------------------------------------------------
# Slice 2a (Task 6b): Vanderbilt and Lectio parsing, the draft-limit guard and
# the merge (S "Lectionary domain": Vanderbilt parsing, Lectio parsing, Merge).
# Pure: no I/O. The fetchers and loaders follow at the end of the file.
# ---------------------------------------------------------------------------

MAX_SET_LINES = 20        # ServiceDraft's scripture limit (S "Draft-limit guard")
MAX_LINE_CHARS = 200      # ServiceDraft's per-line limit
MAX_NAME_CHARS = 300      # the Occasion field's limit (S :142; clarification 34)
MAX_SETS = 10             # the most Lectio groups, and merged sets, one date yields (owner decision 1)

_VANDERBILT_FIELDS = [
    "Liturgical Date", "Calendar Date", "First reading", "Psalm",
    "Second reading", "Gospel", "Art", "Prayer",
]
_COMPOUND_PSALM = re.compile(r"\sPsalms?\s+\d")
_LEADING_STAR = re.compile(r"^\*\s*")
_JOINER_TAIL = re.compile(r"(\s+and|\s*,)$", re.IGNORECASE)
_LECTIO_TYPES = ("first", "psalm", "second", "gospel")


class LectionaryFormatError(ValueError):
    """The Vanderbilt body is not the year CSV (for example an HTML page served as 200)."""


@dataclass(frozen=True)
class VRow:
    """One Vanderbilt CSV row. The reading cells are the raw cell text, trimmed and unquoted."""

    liturgical_date: str
    calendar_date: date
    first: str
    psalm: str
    second: str
    gospel: str


@dataclass(frozen=True)
class ReadingSet:
    """One reading set. `first`..`gospel` feed matching; the API exposes `name`, `scriptures` and `source`.

    For a Vanderbilt set each of the four fields is the cleaned cell text, unsplit; `scriptures` holds the
    split lines (clarification 12). For a Lectio or merged set they are the Lectio group's citations.
    """

    name: str
    first: str
    psalm: str
    second: str
    gospel: str
    scriptures: tuple[str, ...]
    source: Literal["lectio", "vanderbilt", "merged"]


def _parse_calendar_date(cell: str) -> date | None:
    """A Vanderbilt calendar date such as "Feb 15, 2026" or "January 06, 2027"; None when it does not parse."""
    text = (cell or "").strip().strip('"').strip()
    for fmt in ("%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _field(raw: dict, name: str) -> str:
    return (raw.get(name) or "").strip().strip('"').strip()


def _label(text: str) -> str:
    """A header label compared loosely: case and runs of whitespace are ignored."""
    return " ".join(text.strip().strip('"').split()).casefold()


# Art and Prayer are never read, so a header may stop after Gospel.
_REQUIRED_LABELS = [_label(name) for name in _VANDERBILT_FIELDS[:6]]


def _header_columns(line: str) -> list[str]:
    """The header line's labels, stripped of a BOM and quotes, compared loosely (`_label`)."""
    (cells,) = csv.reader([line.lstrip("\ufeff")])
    return [_label(cell) for cell in cells]


def _is_header_line(line: str) -> bool:
    folded = " ".join(line.split()).casefold()
    return "calendar date" in folded and "liturgical date" in folded and "<" not in line


def parse_vanderbilt_csv(text: str) -> list[VRow]:
    """Parse a Vanderbilt year CSV: skip the preamble, use the fixed field names, keep rows whose date parses.

    Raises LectionaryFormatError when no header line exists (an HTML page, an empty body). A line holding
    markup (`<`) is never the header, so an HTML calendar table with both labels on one line still raises.
    It also raises when the header's first six labels are not `_VANDERBILT_FIELDS`' in order (case and
    spacing ignored; Art, Prayer and extra trailing columns are optional), when the csv module rejects the
    body (a field over its size limit, for example after an unbalanced quote), and when there are data
    lines but none parses, so a malformed body is never cached as an empty success. A header alone gives [].
    """
    lines = [line for line in text.splitlines() if line.strip()]
    header = next(
        (i for i, line in enumerate(lines) if _is_header_line(line)),
        None,
    )
    if header is None:
        raise LectionaryFormatError("no Vanderbilt CSV header line")
    data_lines = lines[header + 1:]
    rows: list[VRow] = []
    try:
        if _header_columns(lines[header])[: len(_REQUIRED_LABELS)] != _REQUIRED_LABELS:
            raise LectionaryFormatError("unexpected Vanderbilt CSV columns")
        for raw in csv.DictReader(data_lines, fieldnames=_VANDERBILT_FIELDS):
            calendar_date = _parse_calendar_date(raw.get("Calendar Date") or "")
            if calendar_date is None:
                continue
            rows.append(
                VRow(
                    liturgical_date=_field(raw, "Liturgical Date"),
                    calendar_date=calendar_date,
                    first=_field(raw, "First reading"),
                    psalm=_field(raw, "Psalm"),
                    second=_field(raw, "Second reading"),
                    gospel=_field(raw, "Gospel"),
                )
            )
    except csv.Error as e:
        raise LectionaryFormatError("malformed Vanderbilt CSV") from e
    if data_lines and not rows:
        raise LectionaryFormatError("no Vanderbilt CSV row has a calendar date")
    return rows


def _clean_text(cell: str) -> str:
    """A reading cell's text: whitespace collapsed, quotes stripped, a link dropped, a leading "* " removed."""
    text = " ".join((cell or "").split()).strip('"').strip()
    if text.startswith("http"):
        return ""
    return _LEADING_STAR.sub("", text)


def clean_cell(cell: str) -> list[str]:
    """The scripture lines in one Vanderbilt reading cell (S "Cell cleanup")."""
    text = _clean_text(cell)
    if not text:
        return []
    if " - " in text:
        # The Easter Vigil: " - "-separated segments with headings. Keep every segment that starts with a
        # book, whole, so each vigil reading stays next to its psalm (11 lines; splitting pairs gives 21).
        # Only a cell with a heading (a segment with no book and no digit) is split: "Luke 2:1 - 20" is whole.
        segments = [segment.strip() for segment in text.split(" - ")]
        if any(_is_heading(segment) for segment in segments):
            return [segment for segment in segments if segment and split_book(segment) is not None]
        return [text]
    match = _COMPOUND_PSALM.search(text)
    if match:
        raw_head = text[: match.start()].strip()
        head = _JOINER_TAIL.sub("", raw_head).strip()
        found = split_book(head)
        # Split a two-track cell "<reading> Psalm <n>" (or "<reading> and Psalm <n>") only when the head is
        # a non-Psalm reading and does not end in " or", so "Psalm 105:1-11, 45b or Psalm 128" stays whole
        # (clarification 10).
        if found is not None and found[0].testament != "psalm" and not raw_head.lower().endswith(" or") and not head.lower().endswith(" or"):
            return [head, text[match.start():].strip()]
    return [text]


def _is_heading(segment: str) -> bool:
    """A Vigil heading such as "Old Testament": it starts with no book and holds no digit."""
    return bool(segment) and split_book(segment) is None and not any(ch.isdigit() for ch in segment)


def fits_draft_limits(item: ReadingSet | LectioGroup) -> bool:
    """True when the set fits the draft: 1-20 lines of 1-200 characters, and a 1-300-character name.

    The name check applies to a ReadingSet only (a Lectio group has no name until `merge` names it).
    A rejected set is logged at WARNING with its name and lengths, never its readings; it is never truncated.
    """
    lines = item.scriptures
    name = item.name if isinstance(item, ReadingSet) else None
    fits = (
        1 <= len(lines) <= MAX_SET_LINES
        and all(1 <= len(line) <= MAX_LINE_CHARS for line in lines)
        and (name is None or 1 <= len(name) <= MAX_NAME_CHARS)
    )
    if not fits:
        logger.warning(
            "reading_set_dropped name=%r name_chars=%d lines=%d line_chars=%s",
            "(lectio group)" if name is None else name[:80],
            0 if name is None else len(name),
            len(lines),
            [len(line) for line in lines[:25]],
        )
    return fits


def _vanderbilt_name(raw: str, d: date) -> str:
    """A row's set name: its own text, except a bare Proper number (`_PROPER`) on a Sunday (owner decision A)."""
    if d.weekday() != 6 or not _is_proper(raw):
        return raw
    name = sunday_name(d)
    if name == "All Saints Day":
        # The All Saints row keeps that name; the Proper row takes the computed ordinal (clarification 30).
        name = _ordinary_time_name(d)
    return name or raw


def vanderbilt_sets_on(rows: list[VRow], d: date) -> list[ReadingSet]:
    """The Vanderbilt sets for exactly `d`, in file order; [] when no row has that date (no nearest row).

    After the Proper rename a repeated name gets " (2)", " (3)" (as in `_lectio_only_sets`); a set whose
    suffixed name no longer fits the draft is dropped by fits_draft_limits (clarification 34).
    """
    sets: list[ReadingSet] = []
    counts: dict[str, int] = {}
    used: set[str] = set()
    for row in rows:
        if row.calendar_date != d:
            continue
        base = _vanderbilt_name(row.liturgical_date, d)
        name = base
        if name in used:
            index = counts.get(base, 1)
            while name in used:
                index += 1
                name = f"{base} ({index})"
            counts[base] = index
        used.add(name)
        cells = (row.first, row.psalm, row.second, row.gospel)
        candidate = ReadingSet(
            name=name,
            first=_clean_text(row.first),
            psalm=_clean_text(row.psalm),
            second=_clean_text(row.second),
            gospel=_clean_text(row.gospel),
            scriptures=tuple(line for cell in cells for line in clean_cell(cell)),
            source="vanderbilt",
        )
        if name != base and not fits_draft_limits(candidate):
            continue
        sets.append(candidate)
    return sets


def _lectio_group(by_type: dict[str, str]) -> LectioGroup:
    first, psalm, second, gospel = (by_type.get(kind, "") for kind in _LECTIO_TYPES)
    return LectioGroup(
        first=first,
        psalm=psalm,
        second=second,
        gospel=gospel,
        scriptures=tuple(s for s in (first, psalm, second, gospel) if s),
    )


def _lectio_text(value: object) -> str:
    """A Lectio text field: a string, or an int (not a bool) as its digits; anything else is ""."""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    return ""


def parse_lectio_payload(payload: object) -> LectioDay | None:
    """A Lectio response body as a LectioDay; None when `data` is missing or has no usable readings.

    Alternatives (`isAlternative` exactly true) are skipped (parity) and a new group starts when a reading
    type repeats (Trinity 2026); the type is matched case-insensitively. At most MAX_SETS groups are kept.
    An unexpected shape raises TypeError, so the loader's except clause covers it (clarification 15);
    `season`, `year` and `dayName` keep a string or an int, and are "" otherwise.
    """
    if not isinstance(payload, dict):
        raise TypeError("Lectio payload is not a JSON object")
    data = payload.get("data")
    if not data:
        return None
    if not isinstance(data, dict):
        raise TypeError("Lectio 'data' is not an object")
    readings = data.get("readings") or []
    if not isinstance(readings, list):
        raise TypeError("Lectio 'readings' is not a list")
    groups: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for reading in readings:
        if not isinstance(reading, dict):
            raise TypeError("a Lectio reading is not an object")
        if reading.get("isAlternative") is True:
            continue
        kind = reading.get("type")
        if not isinstance(kind, str) or kind.lower() not in _LECTIO_TYPES:
            continue
        kind = kind.lower()
        citation = reading.get("citation") or ""
        if not isinstance(citation, str):
            raise TypeError("a Lectio citation is not a string")
        if kind in current:
            groups.append(current)
            current = {}
        current[kind] = citation.strip()
    if current:
        groups.append(current)
    if not groups:
        return None
    if len(groups) > MAX_SETS:
        logger.warning("lectio_groups_capped groups=%d kept=%d", len(groups), MAX_SETS)
        groups = groups[:MAX_SETS]
    day_name = _lectio_text(data.get("dayName"))
    return LectioDay(
        groups=tuple(_lectio_group(group) for group in groups),
        season=_lectio_text(data.get("season")),
        year=_lectio_text(data.get("year")),
        day_name=day_name or None,
    )


def _set_from_group(group: LectioGroup, name: str, source: Literal["lectio", "merged"]) -> ReadingSet:
    return ReadingSet(
        name=name,
        first=group.first,
        psalm=group.psalm,
        second=group.second,
        gospel=group.gospel,
        scriptures=group.scriptures,
        source=source,
    )


def _lectio_only_sets(lectio: LectioDay, d: date) -> list[ReadingSet]:
    """Every Lectio group as a set, named by lectio_set_name, the second and later with " (2)", " (3)".

    Each named set is checked again with fits_draft_limits, now that it has a name (clarification 34).
    """
    base = lectio_set_name(lectio, d)
    sets: list[ReadingSet] = []
    for index, group in enumerate(lectio.groups):
        name = base if index == 0 else f"{base} ({index + 1})"
        candidate = _set_from_group(group, name, "lectio")
        if fits_draft_limits(candidate):
            sets.append(candidate)
    return sets


def _cap_sets(sets: list[ReadingSet]) -> list[ReadingSet]:
    if len(sets) > MAX_SETS:
        logger.warning("reading_sets_capped sets=%d kept=%d", len(sets), MAX_SETS)
        return sets[:MAX_SETS]
    return sets


def merge(
    lectio: LectioDay | None, v_sets: list[ReadingSet], d: date
) -> tuple[list[ReadingSet], int | None]:
    """Merge the day's Lectio groups into its Vanderbilt sets (S "Merge"); returns (sets, default_index).

    Both inputs have already passed fits_draft_limits. A Lectio group replaces at most one Vanderbilt set,
    matched by scripture_key(gospel) against each of the set's gospel alternatives, and keeps that set's
    name; unmatched groups are dropped when Vanderbilt has rows. default_index is None only when sets is [].
    At most MAX_SETS sets come out; the rest are dropped with one warning.
    """
    has_lectio = lectio is not None and bool(lectio.groups)
    if not v_sets:
        if not has_lectio:
            return [], None
        sets = _cap_sets(_lectio_only_sets(lectio, d))
        return sets, (len(sets) - 1 if sets else None)
    sets = _cap_sets(list(v_sets))
    if not has_lectio:
        return sets, len(sets) - 1
    matched: set[int] = set()
    for group in lectio.groups:
        key = scripture_key(group.gospel)
        if not key:
            continue
        for index, v_set in enumerate(sets):
            if index in matched:
                continue
            if key in {scripture_key(alt) for alt in split_alternatives(v_set.gospel)}:
                sets[index] = _set_from_group(group, v_set.name, "merged")
                matched.add(index)
                break
    return sets, (max(matched) if matched else len(sets) - 1)


# --- Fetchers and loaders (S "Fetchers", "Loaders"; slice 2a T7) -------------
# One outbound client (integrations.http). Only httpx.HTTPError and a JSON
# ValueError are caught (clarification 18): anything else, such as the test
# suite's no-network RuntimeError, is a bug and surfaces as one.

LECTIO_READ_TIMEOUT = 10.0
VANDERBILT_READ_TIMEOUT = 15.0

# Media types are compared without their parameters ("; charset=utf-8").
# Lectio: application/json or any "+json" type. Vanderbilt: S's two types
# (clarification 19) plus other CSV-ish types, because the fixtures are synthetic and the
# real type is unrecorded; HTML is still refused and the parser rejects anything not CSV.
VANDERBILT_MEDIA_TYPES = frozenset({
    "text/plain", "text/csv", "application/csv", "text/comma-separated-values",
    "application/vnd.ms-excel", "application/octet-stream",
})


class SourceFailed(CacheableFailure):
    """An expected lectionary source failure: a network error, a timeout, a
    403/5xx/429, a wrong content type, undecodable JSON or a CSV with no
    header. The usecase's caches keep it for 5 minutes (S "Loaders").

    `timeout` is True only for an httpx timeout (or the usecase's source
    deadline), so an all-timeout lookup is a 504 rather than a 502."""

    def __init__(self, *, timeout: bool):
        super().__init__("lectionary source timed out" if timeout else "lectionary source failed")
        self.timeout = timeout


def _media_type(response: httpx.Response) -> str:
    """The response's media type, lower-cased, without parameters ("" if absent)."""
    return response.headers.get("content-type", "").split(";", 1)[0].strip().lower()


def _get(url: str, *, params: Optional[dict[str, str]], read_timeout: float) -> httpx.Response:
    try:
        return http.get(url, params=params, read_timeout=read_timeout)
    except httpx.HTTPError as e:     # includes the https-only hook's UnsupportedProtocol
        raise SourceFailed(timeout=isinstance(e, httpx.TimeoutException)) from e


def fetch_lectio(d: date) -> Optional[dict]:
    """GET Lectio for exactly `d`. 404 → None (a definitive none); a 200 JSON
    object → the payload; anything else → SourceFailed (S "Fetchers")."""
    response = _get(
        LECTIO_API_URL,
        params={"date": d.isoformat(), "tradition": "rcl"},
        read_timeout=LECTIO_READ_TIMEOUT,
    )
    if response.status_code == 404:
        return None
    media = _media_type(response)
    if response.status_code != 200 or not (media == "application/json" or media.endswith("+json")):
        raise SourceFailed(timeout=False)
    try:
        payload = response.json()
    except ValueError as e:          # JSONDecodeError and UnicodeDecodeError are ValueErrors
        raise SourceFailed(timeout=False) from e
    if not isinstance(payload, dict):
        raise SourceFailed(timeout=False)
    return payload


def fetch_vanderbilt_year(year: str) -> Optional[str]:
    """GET one liturgical-year CSV ("2025-26"). 404 → None; a 200 text/plain or
    text/csv → the text; anything else (an HTML 200 included) → SourceFailed."""
    response = _get(
        VANDERBILT_YEAR_URL.format(year=year),
        params=None,
        read_timeout=VANDERBILT_READ_TIMEOUT,
    )
    if response.status_code == 404:
        return None
    if response.status_code != 200 or _media_type(response) not in VANDERBILT_MEDIA_TYPES:
        raise SourceFailed(timeout=False)
    return response.text


def load_vanderbilt_year(year: str) -> list[VRow]:
    """What the Vanderbilt cache stores: rows (24 h), [] for a 404 (24 h), or a
    SourceFailed (5 min). An exception that escapes is a bug: not cached."""
    text = fetch_vanderbilt_year(year)                        # raises SourceFailed
    if text is None:                                          # 404: definitive none
        return []
    try:
        return parse_vanderbilt_csv(text)
    except LectionaryFormatError as e:                        # e.g. HTML served as 200
        raise SourceFailed(timeout=False) from e


def load_lectio(d: date) -> Optional[LectioDay]:
    """What the Lectio cache stores: a LectioDay or None (24 h), or a
    SourceFailed (5 min). An exception that escapes is a bug: not cached."""
    payload = fetch_lectio(d)                                 # raises SourceFailed
    if payload is None:                                       # 404: definitive none
        return None
    try:
        return parse_lectio_payload(payload)                  # None when data/readings are empty
    except (KeyError, TypeError, ValueError) as e:            # unexpected JSON shape
        raise SourceFailed(timeout=False) from e
