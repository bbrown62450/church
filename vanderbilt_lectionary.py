#!/usr/bin/env python3
"""
Fetch Revised Common Lectionary readings by date.
Primary: Lectio API (http://lectio-api.org) — works reliably.
Fallback: Vanderbilt Divinity Library CSV (often returns 403 or HTML).
"""

import csv
import logging
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any
import httpx

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


def get_readings_for_date(
    date: datetime,
) -> Optional[Dict[str, Any]]:
    """
    Get Revised Common Lectionary readings for the Sunday on or before the given date.
    Returns dict with: liturgical_date, calendar_date, first_reading, psalm, second_reading, gospel, scriptures (list).
    """
    year_str = _liturgical_year_for_date(date)
    rows = fetch_lectionary_year(year_str)
    if not rows:
        logger.warning("No lectionary rows for year %s", year_str)
        return None

    target = _normalize_date_for_match(date)
    target_ts = target.date()
    logger.info("Looking for readings for date %s (Sunday %s), liturgical year %s", date, target_ts, year_str)

    for row in rows:
        cal_str = (row.get("Calendar Date") or "").strip().strip('"')
        row_date = _parse_csv_date(cal_str)
        if not row_date:
            continue
        if row_date.date() == target_ts:
            first = (row.get("First reading") or "").strip().strip('"')
            psalm = (row.get("Psalm") or "").strip().strip('"')
            second = (row.get("Second reading") or "").strip().strip('"')
            gospel = (row.get("Gospel") or "").strip().strip('"')
            scriptures = [first, psalm, second, gospel]
            scriptures = [s for s in scriptures if s and not s.startswith("http")]
            liturgical_date = (row.get("Liturgical Date") or "").strip().strip('"')
            logger.info("Found exact match for %s: liturgical_date=%r", target_ts, liturgical_date)
            return {
                "liturgical_date": liturgical_date,
                "calendar_date": cal_str,
                "first_reading": first,
                "psalm": psalm,
                "second_reading": second,
                "gospel": gospel,
                "scriptures": scriptures,
            }

    # No exact match: try nearest previous Sunday
    for row in reversed(rows):
        cal_str = (row.get("Calendar Date") or "").strip().strip('"')
        row_date = _parse_csv_date(cal_str)
        if row_date and row_date.date() <= target_ts:
            first = (row.get("First reading") or "").strip().strip('"')
            psalm = (row.get("Psalm") or "").strip().strip('"')
            second = (row.get("Second reading") or "").strip().strip('"')
            gospel = (row.get("Gospel") or "").strip().strip('"')
            scriptures = [first, psalm, second, gospel]
            scriptures = [s for s in scriptures if s and not s.startswith("http")]
            liturgical_date = (row.get("Liturgical Date") or "").strip().strip('"')
            logger.info("Found nearest Sunday match for %s (using %s): liturgical_date=%r", target_ts, row_date.date(), liturgical_date)
            return {
                "liturgical_date": liturgical_date,
                "calendar_date": cal_str,
                "first_reading": first,
                "psalm": psalm,
                "second_reading": second,
                "gospel": gospel,
                "scriptures": scriptures,
            }
    logger.warning("No lectionary match for date %s", target_ts)
    return None


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


def get_readings_for_date_string(date_str: str) -> Optional[Dict[str, Any]]:
    """
    Parse a date string (e.g. 'February 15, 2026', 'Feb 15, 2026', '2026-02-15')
    and return lectionary readings for that Sunday.
    Tries Lectio API first (reliable); falls back to Vanderbilt CSV (often blocked).
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
        return None

    # Normalize to Sunday on or before (same as Vanderbilt) for consistent Sunday readings
    target_sunday = _normalize_date_for_match(d)
    date_iso = target_sunday.strftime("%Y-%m-%d")
    logger.info("Parsed date -> %s, normalized to Sunday %s", d, date_iso)

    # Try Lectio API first (works when Vanderbilt returns 403/HTML)
    result = _get_readings_from_lectio(date_iso)
    if result:
        return result

    # Fallback to Vanderbilt
    result = get_readings_for_date(d)
    logger.info("Vanderbilt fallback returned: %s", "dict" if result else "None")
    return result
