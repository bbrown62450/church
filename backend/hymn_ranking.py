#!/usr/bin/env python3
"""Order hymn candidates by the rubric's preferences: older first, then more
familiar. Preferences, not filters: ranking never removes a hymn, and cutting a
ranked list short keeps places for newer hymns.

The hymns are flat Notion-key dicts by default ("Text Year", "Hymnal Count").
Slice 3 passes typed records with the keyword-only accessors `year_of` and
`count_of` (for example `lambda r: r.text_year`), so there is one
implementation for both shapes."""
import statistics
from itertools import zip_longest
from typing import Any, Callable, List, Optional

from hymn_utils import get_property_value

_OLDER, _UNKNOWN, _NEWER = 0, 1, 2

Accessor = Callable[[Any], Optional[int]]


def _flat_year(hymn: Any) -> Optional[int]:
    return get_property_value(hymn, "Text Year")


def _flat_count(hymn: Any) -> Optional[int]:
    return get_property_value(hymn, "Hymnal Count")


def is_newer_than_preferred(year: Optional[int], prefer_before_year: Optional[int]) -> bool:
    """True when the words' year is known and not before the preferred year
    (the rule PR #4's hymn_display_info used for its newer_than_preferred)."""
    return year is not None and prefer_before_year is not None and year >= prefer_before_year


def _era(hymn: Any, before_year: int, year_of: Accessor) -> int:
    year = year_of(hymn)
    if year is None:
        return _UNKNOWN
    return _OLDER if year < before_year else _NEWER


def rank_candidates(hymns: List[Any], *, prefer_before_year: int, prefer_familiar: bool,
                    year_of: Accessor = _flat_year, count_of: Accessor = _flat_count) -> List[Any]:
    """A new list: hymns written before `prefer_before_year` first, then
    unknown years, then newer ones. Within each group, when `prefer_familiar`
    is on, hymns in more hymnals come first. An unknown count ranks as the
    median of the known counts, so it is neither pushed up nor down. The sort
    is stable, so ties keep their original order."""
    counts = [c for x in hymns if (c := count_of(x)) is not None]
    median = statistics.median(counts) if counts else 0

    def key(hymn):
        era = _era(hymn, prefer_before_year, year_of)
        if not prefer_familiar:
            return (era, 0)
        count = count_of(hymn)
        return (era, -(median if count is None else count))

    return sorted(hymns, key=key)


def shortlist(ranked: List[Any], *, limit: int, prefer_before_year: int,
              reserve: int, year_of: Accessor = _flat_year) -> List[Any]:
    """At most `limit` hymns from a list already ordered by `rank_candidates`,
    still in that order. Up to `reserve` places go to the best-ranked hymns of
    unknown year and newer hymns, taken from each group in turn, so a long run
    of older hymns cannot push them out of view; places they do not need go
    back to the older hymns."""
    if len(ranked) <= limit:
        return list(ranked)
    by_era = {_UNKNOWN: [], _NEWER: []}
    for i, hymn in enumerate(ranked):
        era = _era(hymn, prefer_before_year, year_of)
        if era in by_era:
            by_era[era].append(i)
    alternating = [i for pair in zip_longest(by_era[_UNKNOWN], by_era[_NEWER])
                   for i in pair if i is not None]
    keep = set(alternating[:min(reserve, limit)])
    for i in range(len(ranked)):
        if len(keep) >= limit:
            break
        keep.add(i)
    return [ranked[i] for i in sorted(keep)]


def facts_note(hymn: Any, *, year_of: Accessor = _flat_year,
               count_of: Accessor = _flat_count) -> str:
    """'(written 1826, in 1,322 hymnals)' with whichever facts are known, or ''."""
    year = year_of(hymn)
    count = count_of(hymn)
    parts = []
    if year is not None:
        parts.append(f"written {year}")
    if count is not None:
        parts.append(f"in {count:,} hymnals")
    return f"({', '.join(parts)})" if parts else ""
