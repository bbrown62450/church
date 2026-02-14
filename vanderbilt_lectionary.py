#!/usr/bin/env python3
"""
Fetch Revised Common Lectionary readings by date from Vanderbilt Divinity Library.
Uses their CSV exports: https://lectionary.library.vanderbilt.edu/
"""

import csv
from datetime import datetime
from typing import Optional, List, Dict, Any
import httpx

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
    from datetime import timedelta
    weekday = d.weekday()  # 0=Mon, 6=Sun
    days_since_sunday = (weekday + 1) % 7
    return d - timedelta(days=days_since_sunday)


def fetch_lectionary_year(year_str: str) -> List[Dict[str, str]]:
    """Download and parse CSV for one liturgical year. Results cached."""
    if year_str in _cache:
        return _cache[year_str]
    url = VANDERBILT_YEAR_URL.format(year=year_str)
    try:
        r = httpx.get(
            url,
            timeout=20.0,
            headers={"User-Agent": "Mozilla/5.0 (compatible; WorshipBuilder/1.0)"},
        )
        r.raise_for_status()
        text = r.text
    except Exception:
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
        return None

    target = _normalize_date_for_match(date)
    target_ts = target.date()

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
            return {
                "liturgical_date": (row.get("Liturgical Date") or "").strip().strip('"'),
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
            return {
                "liturgical_date": (row.get("Liturgical Date") or "").strip().strip('"'),
                "calendar_date": cal_str,
                "first_reading": first,
                "psalm": psalm,
                "second_reading": second,
                "gospel": gospel,
                "scriptures": scriptures,
            }
    return None


def get_readings_for_date_string(date_str: str) -> Optional[Dict[str, Any]]:
    """
    Parse a date string (e.g. 'February 15, 2026', 'Feb 15, 2026', '2026-02-15')
    and return lectionary readings for that Sunday.
    """
    date_str = date_str.strip()
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d", "%-m/%-d/%Y", "%m/%d/%Y", "%d %B %Y"):
        try:
            d = datetime.strptime(date_str, fmt)
            return get_readings_for_date(d)
        except ValueError:
            continue
    return None
