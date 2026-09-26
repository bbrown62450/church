#!/usr/bin/env python3
"""Order hymn candidates by the rubric's preferences: older first, then more
familiar. Preferences, not filters: nothing is ever removed."""
import statistics
from typing import Any, Dict, List

from hymn_utils import get_property_value

_OLDER, _UNKNOWN, _NEWER = 0, 1, 2


def _era(hymn: Dict[str, Any], before_year: int) -> int:
    year = get_property_value(hymn, "Text Year")
    if year is None:
        return _UNKNOWN
    return _OLDER if year < before_year else _NEWER


def rank_candidates(hymns: List[Dict[str, Any]], *, prefer_before_year: int,
                    prefer_familiar: bool) -> List[Dict[str, Any]]:
    """A new list: hymns written before `prefer_before_year` first, then
    unknown years, then newer ones. Within each group, when `prefer_familiar`
    is on, hymns in more hymnals come first. An unknown count ranks as the
    median of the known counts, so it is neither pushed up nor down. The sort
    is stable, so ties keep their original order."""
    counts = [c for x in hymns if (c := get_property_value(x, "Hymnal Count")) is not None]
    median = statistics.median(counts) if counts else 0

    def key(hymn):
        era = _era(hymn, prefer_before_year)
        if not prefer_familiar:
            return (era, 0)
        count = get_property_value(hymn, "Hymnal Count")
        return (era, -(median if count is None else count))

    return sorted(hymns, key=key)


def facts_note(hymn: Dict[str, Any]) -> str:
    """'(written 1826, in 1,322 hymnals)' with whichever facts are known, or ''."""
    year = get_property_value(hymn, "Text Year")
    count = get_property_value(hymn, "Hymnal Count")
    parts = []
    if year is not None:
        parts.append(f"written {year}")
    if count is not None:
        parts.append(f"in {count:,} hymnals")
    return f"({', '.join(parts)})" if parts else ""
