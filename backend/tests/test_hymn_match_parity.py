"""Characterization of the scripture matcher (F §2.3.1; slice 3 spec, Testing
"Characterization first"): what matched under the old substring matcher still
matches, and the four verified over-matches (inventory §0 item 5) do not.

Task 5 ran each pair through worship_service.hymns_by_scripture as well; Task
14 deleted that function and this file's old half in the same commit.
"""
from dataclasses import dataclass

from hymn_search import match_hymns

# (query, hymn scripture_refs) pairs that matched under the old substring matcher.
STILL_MATCH = [
    ("Isaiah 6:1-8", "Isaiah 6:1-8"),             # the exact reference
    ("Matthew 17:1-9", "Matthew 17"),             # book + chapter
    ("Romans 8:28-39", "Romans 8:28"),            # the first verse
    ("Genesis 12:1-4a", "Genesis 12:1-4"),        # an a/b suffix dropped
    ("Luke 24:13-35 or Mark 16:1-8", "Mark 16:1-8"),   # the " or " alternative
    ("Psalm 23", "Psalm 23"),
]

# Verified over-matches: the old matcher said yes; the new one says no.
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


def _new(query: str, refs: str) -> bool:
    queries = [part.strip() for part in query.split(" or ")]
    return bool(match_hymns([H("Hymn", refs)], queries).items)


def test_pairs_that_matched_before_still_match():
    for query, refs in STILL_MATCH:
        assert _new(query, refs), (query, refs)


def test_the_four_over_matches_no_longer_match():
    for query, refs in OVER_MATCHES:
        assert not _new(query, refs), (query, refs)


def test_the_old_hymn_code_is_gone():
    """AC9: the Streamlit-era matcher, suggester, display helper, audio
    resolver and Notion path are deleted, with lxml, their only user's package."""
    from pathlib import Path

    import worship_service

    for name in ("_BOOK_ABBREVS", "_scripture_search_variants", "hymns_by_scripture", "_OPENING_THEMES",
                 "_CLOSING_THEMES", "_hymn_matches_theme", "suggest_hymns_for_service",
                 "hymn_display_info", "_hymnary_audio_url", "resolve_hymnary_audio_url",
                 "_hymnary_audio_resolve_cache", "_CANDIDATES_PER_SLOT", "_CANDIDATES_KEPT_FOR_NEWER"):
        assert not hasattr(worship_service, name), name
    source = Path(worship_service.__file__).read_text()
    assert "load_dotenv" not in source and "NotionHymnsDB" not in source
    requirements = (Path(worship_service.__file__).parent / "requirements.txt").read_text()
    assert "lxml" not in requirements
    assert callable(worship_service.build_docx)       # generate_liturgy went in slice 4a
