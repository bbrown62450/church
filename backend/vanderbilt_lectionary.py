#!/usr/bin/env python3
"""
Fetch Revised Common Lectionary readings by date.
Primary: Lectio API (http://lectio-api.org) — works reliably.
Fallback: Vanderbilt Divinity Library CSV (often returns 403 or HTML).
"""

import csv
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Literal, Optional

import httpx

from scripture_refs import scripture_key, split_alternatives, split_book

logger = logging.getLogger(__name__)

LECTIO_API_URL = "https://lectio-api.org/api/v1/readings"

# Liturgical year CSV URLs: 2025-26 (Year A), 2026-27 (Year B), 2027-28 (Year C)
VANDERBILT_YEAR_URL = "https://lectionary.library.vanderbilt.edu/calendar/{year}/?season=all&download=csv"

# Cache by liturgical year to avoid repeated fetches
_cache: Dict[str, List[Dict[str, str]]] = {}


def _liturgical_year_for_date(d: datetime) -> str:
    """Return liturgical year string (e.g. '2025-26') for a given date."""
    # Advent starts late Nov; so 2025-26 runs ~Nov 30 2025 through ~Nov 28 2026
    if d.month > 11 or (d.month == 11 and d.day >= 29):
        return f"{d.year}-{str(d.year + 1)[2:]}"
    return f"{d.year - 1}-{str(d.year)[2:]}"


def _parse_csv_date(s: str) -> Optional[datetime]:
    """Parse Vanderbilt CSV calendar date, e.g. 'Feb 15, 2026' or 'Jan 06, 2027'."""
    if not s or not s.strip():
        return None
    s = s.strip().strip('"')
    try:
        return datetime.strptime(s, "%b %d, %Y")
    except ValueError:
        try:
            return datetime.strptime(s, "%B %d, %Y")
        except ValueError:
            return None


def _normalize_date_for_match(d: datetime) -> datetime:
    """Return the Sunday on or before d (for matching to lectionary rows)."""
    weekday = d.weekday()  # 0=Mon, 6=Sun
    days_since_sunday = (weekday + 1) % 7
    return d - timedelta(days=days_since_sunday)


def _easter_date(year: int) -> date:
    """Compute Easter Sunday for the given year (Anonymous Gregorian algorithm)."""
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


def _ordinal_sunday_label(ordinal: int, season: str) -> str:
    """Return e.g. 'First Sunday in Lent', 'Palm Sunday' for 6th in Lent."""
    ordinals = ("First", "Second", "Third", "Fourth", "Fifth", "Sixth")
    if season == "Lent" and ordinal == 6:
        return "Palm Sunday"
    if ordinal <= 6 and ordinal >= 1:
        return f"{ordinals[ordinal - 1]} Sunday in {season}"
    return ""


def _liturgical_sunday_name(sunday_date: date, season: str, year: str) -> Optional[str]:
    """
    Compute 'Nth Sunday in Season' for common RCL seasons.
    Returns e.g. 'Fourth Sunday in Lent', 'Palm Sunday', 'First Sunday of Advent'.
    """
    y = sunday_date.year

    if season == "Lent":
        easter = _easter_date(y)
        palm_sunday = easter - timedelta(days=7)
        first_sunday_lent = palm_sunday - timedelta(days=35)
        if first_sunday_lent <= sunday_date <= palm_sunday:
            weeks = (sunday_date - first_sunday_lent).days // 7
            return _ordinal_sunday_label(weeks + 1, "Lent")
    elif season == "Advent":
        # First Sunday of Advent: Sunday on or after Nov 27 (4th Sun before Christmas)
        for cand in (date(y, 11, d) for d in range(27, 31)):
            if cand.weekday() == 6:  # Sunday
                first_advent = cand
                break
        else:
            first_advent = date(y, 12, 1)
            while first_advent.weekday() != 6:
                first_advent += timedelta(days=1)
        if first_advent <= sunday_date <= date(y, 12, 24):
            weeks = (sunday_date - first_advent).days // 7
            if weeks < 4:
                ordinals = ("First", "Second", "Third", "Fourth")
                return f"{ordinals[weeks]} Sunday of Advent"
    elif season == "Epiphany":
        # First Sunday after Epiphany (Jan 6); last is Transfiguration (Sun before Lent)
        epiphany = date(y, 1, 6)
        sun_after_epiphany = epiphany
        while sun_after_epiphany.weekday() != 6:
            sun_after_epiphany += timedelta(days=1)
        if epiphany.weekday() == 6:
            sun_after_epiphany += timedelta(days=7)
        easter = _easter_date(y)
        ash_wed = easter - timedelta(days=46)
        last_epiphany = ash_wed
        while last_epiphany.weekday() != 6:
            last_epiphany -= timedelta(days=1)
        if sun_after_epiphany <= sunday_date <= last_epiphany:
            weeks = (sunday_date - sun_after_epiphany).days // 7
            if weeks == 0:
                return "Baptism of the Lord"
            # Last Sunday after Epiphany = Transfiguration
            first_sun_lent = (easter - timedelta(days=7)) - timedelta(days=35)
            if sunday_date >= first_sun_lent - timedelta(days=7):
                return "Transfiguration Sunday"
            return f"{['Second', 'Third', 'Fourth', 'Fifth', 'Sixth', 'Seventh', 'Eighth', 'Ninth'][weeks - 1]} Sunday after Epiphany"
    elif season == "Easter":
        easter = _easter_date(y)
        if sunday_date >= easter and sunday_date <= easter + timedelta(days=49):
            weeks = (sunday_date - easter).days // 7
            if weeks == 0:
                return "Easter Sunday"
            ordinals = ("Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh")
            if weeks <= 6:
                return f"{ordinals[weeks - 1]} Sunday of Easter"

    return None


def fetch_lectionary_year(year_str: str) -> List[Dict[str, str]]:
    """Download and parse CSV for one liturgical year. Results cached."""
    if year_str in _cache:
        logger.debug("Using cached lectionary for year %s", year_str)
        return _cache[year_str]
    url = VANDERBILT_YEAR_URL.format(year=year_str)
    logger.info("Fetching lectionary CSV for year %s from %s", year_str, url)
    try:
        r = httpx.get(
            url,
            timeout=20.0,
            headers={"User-Agent": "Mozilla/5.0 (compatible; WorshipBuilder/1.0)"},
        )
        r.raise_for_status()
        text = r.text
        logger.info("Lectionary CSV fetched: %d bytes", len(text))
    except Exception as e:
        logger.warning("Failed to fetch lectionary: %s", e)
        _cache[year_str] = []
        return []

    rows = []
    lines = [L for L in text.splitlines() if L.strip()]
    # Find the header line (contains "Calendar Date")
    start = 0
    for i, line in enumerate(lines):
        if "Calendar Date" in line and "Liturgical Date" in line:
            start = i
            break
    if start >= len(lines):
        _cache[year_str] = []
        return []
    reader = csv.DictReader(lines[start:], fieldnames=[
        "Liturgical Date", "Calendar Date", "First reading", "Psalm",
        "Second reading", "Gospel", "Art", "Prayer",
    ])
    header = next(reader)
    for row in reader:
        cal = (row.get("Calendar Date") or "").strip().strip('"')
        if _parse_csv_date(cal):
            rows.append(row)
    _cache[year_str] = rows
    logger.info("Parsed %d lectionary rows for year %s", len(rows), year_str)
    return rows


def _row_to_reading(row: Dict[str, str]) -> Dict[str, Any]:
    """Convert a Vanderbilt CSV row to a reading dict."""
    cal_str = (row.get("Calendar Date") or "").strip().strip('"')
    first = (row.get("First reading") or "").strip().strip('"')
    psalm = (row.get("Psalm") or "").strip().strip('"')
    second = (row.get("Second reading") or "").strip().strip('"')
    gospel = (row.get("Gospel") or "").strip().strip('"')
    scriptures = [first, psalm, second, gospel]
    scriptures = [s for s in scriptures if s and not s.startswith("http")]
    liturgical_date = (row.get("Liturgical Date") or "").strip().strip('"')
    return {
        "liturgical_date": liturgical_date,
        "calendar_date": cal_str,
        "first_reading": first,
        "psalm": psalm,
        "second_reading": second,
        "gospel": gospel,
        "scriptures": scriptures,
    }


def get_readings_for_date(
    date: datetime,
) -> List[Dict[str, Any]]:
    """
    Get Revised Common Lectionary readings for the Sunday on or before the given date.
    Returns a list of reading dicts (usually 1, but 2 for Palm Sunday: Palms + Passion).
    Each dict has: liturgical_date, calendar_date, first_reading, psalm, second_reading, gospel, scriptures.
    """
    year_str = _liturgical_year_for_date(date)
    rows = fetch_lectionary_year(year_str)
    if not rows:
        logger.warning("No lectionary rows for year %s", year_str)
        return []

    target = _normalize_date_for_match(date)
    target_ts = target.date()
    logger.info("Looking for readings for date %s (Sunday %s), liturgical year %s", date, target_ts, year_str)

    # Collect ALL rows that match the target date (e.g. Palm Sunday has Palms + Passion)
    matches = []
    for row in rows:
        cal_str = (row.get("Calendar Date") or "").strip().strip('"')
        row_date = _parse_csv_date(cal_str)
        if not row_date:
            continue
        if row_date.date() == target_ts:
            reading = _row_to_reading(row)
            logger.info("Found exact match for %s: liturgical_date=%r", target_ts, reading["liturgical_date"])
            matches.append(reading)

    if matches:
        return matches

    # No exact match: try nearest previous Sunday
    for row in reversed(rows):
        cal_str = (row.get("Calendar Date") or "").strip().strip('"')
        row_date = _parse_csv_date(cal_str)
        if row_date and row_date.date() <= target_ts:
            reading = _row_to_reading(row)
            logger.info("Found nearest Sunday match for %s (using %s): liturgical_date=%r", target_ts, row_date.date(), reading["liturgical_date"])
            return [reading]
    logger.warning("No lectionary match for date %s", target_ts)
    return []


def _get_readings_from_lectio(date_iso: str) -> Optional[Dict[str, Any]]:
    """
    Fetch RCL readings from Lectio API for a given date (YYYY-MM-DD).
    Returns same format as Vanderbilt: liturgical_date, calendar_date, first_reading, psalm, second_reading, gospel, scriptures.
    """
    try:
        r = httpx.get(
            LECTIO_API_URL,
            params={"date": date_iso, "tradition": "rcl"},
            timeout=15.0,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logger.warning("Lectio API fetch failed: %s", e)
        return None

    payload = data.get("data")
    if not payload:
        logger.warning("Lectio API returned no data")
        return None

    readings = payload.get("readings", [])
    season = (payload.get("season") or "").strip()
    year = (payload.get("year") or "").strip()
    day_name = (payload.get("dayName") or "").strip()

    # Build liturgical_date: dayName from API, else "Nth Sunday in Lent" etc., else "Season — Year X"
    if day_name:
        liturgical_date = day_name
    else:
        try:
            d = datetime.strptime(date_iso, "%Y-%m-%d").date()
            computed = _liturgical_sunday_name(d, season, year)
            liturgical_date = computed if computed else f"{season} — Year {year}"
        except (ValueError, TypeError):
            liturgical_date = f"{season} — Year {year}" if (season and year) else (season or "Sunday")

    # Extract readings by type (prefer non-alternative)
    by_type = {}
    for rd in readings:
        if rd.get("isAlternative"):
            continue
        t = rd.get("type")
        if t and t not in by_type:
            by_type[t] = (rd.get("citation") or "").strip()

    first = by_type.get("first", "")
    psalm = by_type.get("psalm", "")
    second = by_type.get("second", "")
    gospel = by_type.get("gospel", "")

    scriptures = [s for s in [first, psalm, second, gospel] if s]

    # Calendar date in "Mar 15, 2026" format
    try:
        d = datetime.strptime(date_iso, "%Y-%m-%d")
        calendar_date = d.strftime("%b %d, %Y")
    except ValueError:
        calendar_date = date_iso

    logger.info("Lectio API: liturgical_date=%r for %s", liturgical_date, date_iso)

    return {
        "liturgical_date": liturgical_date,
        "calendar_date": calendar_date,
        "first_reading": first,
        "psalm": psalm,
        "second_reading": second,
        "gospel": gospel,
        "scriptures": scriptures,
    }


def get_readings_for_date_string(date_str: str) -> List[Dict[str, Any]]:
    """
    Parse a date string (e.g. 'February 15, 2026', 'Feb 15, 2026', '2026-02-15')
    and return lectionary readings for that Sunday.
    Returns a list of reading dicts (usually 1, but 2 for Palm Sunday: Palms + Passion).
    Tries Lectio API first; also checks Vanderbilt CSV for additional reading sets.
    """
    date_str = date_str.strip()
    logger.info("get_readings_for_date_string called with date_str=%r", date_str)

    # Parse to datetime and ISO
    d = None
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d", "%m/%d/%Y", "%d %B %Y"):
        try:
            d = datetime.strptime(date_str, fmt)
            break
        except ValueError:
            continue

    if not d:
        logger.warning("Could not parse date string %r with any format", date_str)
        return []

    # Normalize to Sunday on or before (same as Vanderbilt) for consistent Sunday readings
    target_sunday = _normalize_date_for_match(d)
    date_iso = target_sunday.strftime("%Y-%m-%d")
    logger.info("Parsed date -> %s, normalized to Sunday %s", d, date_iso)

    # Try Lectio API (reliable readings)
    lectio_result = _get_readings_from_lectio(date_iso)

    # Also get Vanderbilt CSV readings (may have additional sets, e.g. Liturgy of the Palms)
    vanderbilt_results = get_readings_for_date(d)
    logger.info("Vanderbilt returned %d reading set(s)", len(vanderbilt_results))

    if not lectio_result and not vanderbilt_results:
        return []

    if not lectio_result:
        return vanderbilt_results

    if not vanderbilt_results or len(vanderbilt_results) <= 1:
        # No extra sets from Vanderbilt — just use Lectio
        return [lectio_result]

    # Multiple Vanderbilt sets (e.g. Palm Sunday: Palms + Passion).
    # Use Vanderbilt as the base structure, but replace the Passion set with
    # Lectio data (which has better readings for the main service).
    result = []
    replaced = False
    for v_reading in vanderbilt_results:
        v_name = v_reading["liturgical_date"].lower()
        if not replaced and "passion" in v_name:
            # Replace Vanderbilt Passion entry with Lectio data, keeping the liturgical_date label
            lectio_result["liturgical_date"] = v_reading["liturgical_date"]
            result.append(lectio_result)
            replaced = True
        else:
            result.append(v_reading)
    if not replaced:
        # Lectio didn't match any Passion entry — append it
        result.append(lectio_result)
    logger.info("Merged results: %d reading set(s): %s", len(result), [r["liturgical_date"] for r in result])
    return result


# --- Slice 2 domain: the calendar and occasion names (S Lectionary domain; decision A) ---
#
# Pure date arithmetic: no I/O and no clock. Names come from the date alone, never from
# Lectio's season string. The code above is the Streamlit-era path; Task 7 deletes it
# (including the private `_easter_date`, which `easter_date` below replaces).

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
# Pure: no I/O. Task 7 adds the fetchers and loaders and deletes the old code.
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
