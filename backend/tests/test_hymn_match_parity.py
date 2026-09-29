"""Characterization of the scripture matcher (F §2.3.1; slice 3 spec, Testing
"Characterization first"): what matches today must still match, and the four
verified over-matches (inventory §0 item 5) must stop matching.

The old half calls worship_service.hymns_by_scripture with the in-memory pool;
Task 14 deletes that function and this file's old half in the same commit.
"""
from dataclasses import dataclass

import worship_service
from hymn_search import match_hymns

# (query, hymn scripture_refs) pairs that match under the old substring matcher.
STILL_MATCH = [
    ("Isaiah 6:1-8", "Isaiah 6:1-8"),             # the exact reference
    ("Matthew 17:1-9", "Matthew 17"),             # book + chapter
    ("Romans 8:28-39", "Romans 8:28"),            # the first verse
    ("Genesis 12:1-4a", "Genesis 12:1-4"),        # an a/b suffix dropped
    ("Luke 24:13-35 or Mark 16:1-8", "Mark 16:1-8"),   # the " or " alternative
    ("Psalm 23", "Psalm 23"),
]

# Verified over-matches: the old matcher says yes, the new one no.
OVER_MATCHES = [
    ("Isaiah 9:6", "Genesis 9:6"),
    ("Mark 1:9-15", "Mark 10:45"),
    ("Psalm 1", "Psalm 119"),
    ("John 3:1-17", "1 John 3:16"),
]


@dataclass(frozen=True)
class H:
    title: str
    scripture_refs: str


def _old(query: str, refs: str) -> bool:
    hymn = {"id": "h1", "Hymn Title": "Hymn", "Scripture References": refs}
    return bool(worship_service.hymns_by_scripture(None, query, all_hymns=[hymn]))


def _new(query: str, refs: str) -> bool:
    queries = [part.strip() for part in query.split(" or ")]
    return bool(match_hymns([H("Hymn", refs)], queries).items)


def test_pairs_that_match_today_still_match():
    for query, refs in STILL_MATCH:
        assert _old(query, refs), ("old", query, refs)
        assert _new(query, refs), ("new", query, refs)


def test_the_four_over_matches_no_longer_match():
    for query, refs in OVER_MATCHES:
        assert _old(query, refs), ("old", query, refs)          # the bug, as it is today
        assert not _new(query, refs), ("new", query, refs)
