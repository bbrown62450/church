"""scripture_refs.parse_refs and the span tests (slice 3 spec, Backend 2
"Parsing"; Testing `test_scripture_refs_parse.py`; owner decision 9; AC3).

Slice 2's shared fixture (test_scripture_refs.py) still pins BOOKS, split_book
and classify; parse_refs adds PARSE_ALIASES and SINGLE_CHAPTER_BOOKS on top.
"""
import csv
from pathlib import Path

import pytest

import scripture_refs as sr
from scripture_refs import RefSpan, parse_refs, same_chapter, spans_overlap

SAMPLE = Path(__file__).resolve().parent / "hymn_fixtures" / "scripture_refs_sample.csv"


def spans(text):
    """(book, start, end) for each span; asserts nothing was left unparsed."""
    parsed = parse_refs(text)
    assert parsed.unparsed == (), (text, parsed.unparsed)
    return [(s.book, s.start, s.end) for s in parsed.spans]


def test_every_alias_maps_to_its_book():
    for book in sr.BOOKS:
        for key in (sr.normalize_book_text(book.name), *book.aliases):
            assert parse_refs(f"{key} 1:1").spans[0].book == book.name, key
    for alias, name in sr.PARSE_ALIASES.items():
        assert parse_refs(f"{alias} 1:1").spans[0].book == name, alias
        assert alias in sr.book_keys(name)
    # The old matcher's abbreviations work in both directions (inventory D4).
    assert spans("Matt 17:1-8") == spans("Matthew 17:1-8")
    assert spans("Is 9:6") == [("Isaiah", (9, 6), (9, 6))]
    assert sr.classify("Is 9:6") == "unknown"                  # the shared fixture is unchanged


def test_ordinals_and_no_space_forms():
    expected = [("1 Corinthians", (13, 1), (13, 13))]
    for text in ("1 Cor 13:1-13", "I Cor. 13:1-13", "First Corinthians 13:1-13",
                 "1st Corinthians 13:1-13", "1Cor 13:1-13", "1cor13:1-13"):
        assert spans(text) == expected, text
    assert spans("II Kings 2:1-12") == [("2 Kings", (2, 1), (2, 12))]
    assert spans("3 Jn 2") == [("3 John", (1, 2), (1, 2))]


def test_psalm_forms():
    for text in ("Ps 99", "Pss 99", "Psalm 99", "Psalms 99", "Psa. 99"):
        assert spans(text) == [("Psalms", (99, 0), (99, 999))], text


def test_ranges_suffixes_and_ff():
    assert spans("Genesis 12:1-4a") == [("Genesis", (12, 1), (12, 4))]
    assert spans("Mark 1:9b-15") == [("Mark", (1, 9), (1, 15))]
    assert spans("John 1:1-2:3") == [("John", (1, 1), (2, 3))]
    assert spans("Isaiah 40-42") == [("Isaiah", (40, 0), (42, 999))]
    assert spans("Luke 4:14ff") == [("Luke", (4, 14), (4, 999))]
    assert spans("Luke 4:14f") == [("Luke", (4, 14), (4, 999))]
    assert spans("Matthew 5:3c") == [("Matthew", (5, 3), (5, 3))]


def test_semicolon_carry_forward_and_commas():
    assert spans("Isaiah 9:2-7; 11:1") == [("Isaiah", (9, 2), (9, 7)), ("Isaiah", (11, 1), (11, 1))]
    assert spans("Psalm 42; 43") == [("Psalms", (42, 0), (42, 999)), ("Psalms", (43, 0), (43, 999))]
    # A comma continues the location list unless a book follows it.
    assert spans("Romans 4:1-5, 13-17") == [("Romans", (4, 1), (4, 5)), ("Romans", (4, 13), (4, 17))]
    assert spans("Isaiah 6:1-8, Revelation 4:8") == [("Isaiah", (6, 1), (6, 8)),
                                                     ("Revelation", (4, 8), (4, 8))]
    assert spans("Psalm 23:1\nJohn 10:11") == [("Psalms", (23, 1), (23, 1)), ("John", (10, 11), (10, 11))]
    assert spans("John 1:1-2:3, 5") == [("John", (1, 1), (2, 3)), ("John", (2, 5), (2, 5))]


def test_single_chapter_books():
    assert spans("Jude 24-25") == [("Jude", (1, 24), (1, 25))]
    assert spans("Philemon 1:4-7") == [("Philemon", (1, 4), (1, 7))]
    assert spans("Obadiah 15") == [("Obadiah", (1, 15), (1, 15))]
    assert spans("2 John 4") == [("2 John", (1, 4), (1, 4))]


def test_en_dash_case_insensitive_or_and_whole_books():
    assert spans("Mark 1:9–15") == [("Mark", (1, 9), (1, 15))]
    assert spans("Mark 1:9—15") == [("Mark", (1, 9), (1, 15))]
    assert spans("Luke 24:13-35 OR Mark 16:1-8") == [("Luke", (24, 13), (24, 35)),
                                                     ("Mark", (16, 1), (16, 8))]
    assert spans("Ruth") == [("Ruth", (1, 0), (999, 999))]


def test_garbage_goes_to_unparsed():
    assert parse_refs("Transfiguration") == sr.ParsedRefs((), ("Transfiguration",))
    parsed = parse_refs("Psalm 23; see the preface; 5-3")
    assert [s.book for s in parsed.spans] == ["Psalms"]
    assert parsed.unparsed == ("see the preface", "5-3")          # a range that runs backwards
    assert parse_refs("  ") == sr.ParsedRefs((), ())
    assert parse_refs("Psalm 0").unparsed == ("Psalm 0",)


def test_impossible_chapters_and_dotted_verses_are_unparsed():
    # normalize_book_text drops periods, so "John 3.16" would read as John 316.
    for text in ("John 3.16", "Ps 1.1", "Ps 23. 1", "John 316", "Genesis 151", "Isaiah 40-160",
                 "John 3:16-200:1"):
        assert parse_refs(text) == sr.ParsedRefs((), (text,)), text
    assert spans("Psalm 150") == [("Psalms", (150, 0), (150, 999))]
    assert spans("Psalm 119:105") == [("Psalms", (119, 105), (119, 105))]
    assert spans("Psalm 148ff") == [("Psalms", (148, 0), (148, 999))]      # owner answer B: that chapter only
    assert parse_refs("Psalm 148ff").spans[0].broad and parse_refs("Psalms").spans[0].broad
    assert not any(parse_refs(t).spans[0].broad for t in ("Psalm 148", "Jude", "Jude 3ff", "Luke 4:14ff"))
    assert spans("Psalm 151:1") == [("Psalm 151", (1, 1), (1, 1))]         # owner decision 1
    assert spans("Psalm 151 1-7") == [("Psalm 151", (1, 1), (1, 7))]
    assert spans("I Cor. 13:1") == [("1 Corinthians", (13, 1), (13, 1))]
    # "Esd" alone could be 1 or 2 Esdras, so it names no book.
    assert parse_refs("Esd 1").unparsed == ("Esd 1",)
    assert spans("2 Esd 7:1") == [("2 Esdras", (7, 1), (7, 1))]


def test_deuterocanon_parses_and_classifies_as_ot():
    cases = {
        "Baruch 5:1-9": ("Baruch", (5, 1), (5, 9)),
        "Bar 5:5": ("Baruch", (5, 5), (5, 5)),
        "Wis 2:23": ("Wisdom of Solomon", (2, 23), (2, 23)),
        "Sirach 10:12-18": ("Sirach", (10, 12), (10, 18)),
        "Sir 27:4-7": ("Sirach", (27, 4), (27, 7)),
        "Ecclesiasticus 27:4": ("Sirach", (27, 4), (27, 4)),
        "Tobit 8:5-8": ("Tobit", (8, 5), (8, 8)),
        "Judith 9:11": ("Judith", (9, 11), (9, 11)),
        "1 Macc 2:1": ("1 Maccabees", (2, 1), (2, 1)),
        "2 Maccabees 7:1": ("2 Maccabees", (7, 1), (7, 1)),
        "Song of the Three 35-65": ("Song of the Three", (1, 35), (1, 65)),
    }
    for text, expected in cases.items():
        assert spans(text) == [expected], text
        assert sr.classify(text) == "ot", text
    assert spans("Wisdom of Solomon 1:13-15; 2:23-24") == [
        ("Wisdom of Solomon", (1, 13), (1, 15)), ("Wisdom of Solomon", (2, 23), (2, 24))]


def test_the_longest_alias_wins():
    assert spans("Song 2:8-13") == [("Song of Songs", (2, 8), (2, 13))]
    assert spans("Song of Solomon 2:10") == [("Song of Songs", (2, 10), (2, 10))]
    assert spans("Song of the Three Jews 35") == [("Song of the Three", (1, 35), (1, 35))]


def test_spans_overlap_and_same_chapter():
    def one(text):
        (span,) = parse_refs(text).spans
        return span

    assert spans_overlap(one("Matthew 17"), one("Matt 17:1-8"))
    assert spans_overlap(one("Genesis 12:1-4a"), one("Genesis 12:1"))
    assert not spans_overlap(one("Mark 1:9-15"), one("Mark 1:1-8"))
    assert same_chapter(one("Mark 1:9-15"), one("Mark 1:1-8"))
    assert not same_chapter(one("Mark 1:9-15"), one("Mark 10:45"))
    assert not same_chapter(one("Isaiah 9:6"), one("Genesis 9:6"))
    assert not same_chapter(one("Psalm 1"), one("Psalm 119"))
    assert not same_chapter(one("John 3:1-17"), one("1 John 3:16"))
    assert RefSpan("John", (3, 1), (3, 17)) == one("John 3:1-17")


def test_parse_refs_is_cached_on_the_raw_string():
    parse_refs.cache_clear()
    first = parse_refs("Psalm 23")
    assert parse_refs("Psalm 23") is first
    assert parse_refs.cache_info().hits == 1
    assert parse_refs.cache_info().maxsize == 4096


def test_sample_parses_at_least_98_percent_of_segments():
    """AC3 on the committed sample (backend/tests/hymn_fixtures/README.md says
    whether it is the owner's export or the synthetic stand-in)."""
    with SAMPLE.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) >= 100
    assert set(rows[0]) == {"hymnal", "number", "title", "scripture_refs"}
    segments = unparsed = 0
    for row in rows:
        for alternative in sr.split_alternatives(row["scripture_refs"]):
            segments += len(sr.split_segments(alternative))
        unparsed += len(parse_refs(row["scripture_refs"]).unparsed)
    assert segments > 0
    assert (segments - unparsed) / segments >= 0.98, (segments, unparsed)
