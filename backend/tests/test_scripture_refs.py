"""scripture_refs (S `scripture_refs.py`; spec decision 9; AC8, Python half).

The shared fixture pins everything slice 2b's lib/scripture-refs.ts ports, and
2b's Vitest file reads the same JSON. Fixture tests loop over their cases inside
one test, so the count stays stable when 5a adds cases. The fetch-only helpers
(normalize_for_fetch, split_parts, split_joined) are Python-only (S :722).
"""
import dataclasses
import json
from pathlib import Path

import pytest

import scripture_refs as sr

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "shared" / "scripture_refs.json"
SECTIONS = (
    "books", "split_alternatives", "split_book", "classify", "is_nt_ref",
    "expand_ref_options", "clean_lines", "picker_options", "resolve_readings",
    "default_reading_pair", "default_nt_ref", "scripture_key",
)

ISAIAH = ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"]
EASTER = ["Acts 10:34-43", "Psalm 118:1-2, 14-24", "Colossians 3:1-4", "John 20:1-18"]

# Every resolve_readings example in S `scripture_refs.py`, verbatim:
# (scriptures, ot_pick, nt_pick, (ot, nt, ot_auto, nt_auto)).
SPEC_RESOLVE_EXAMPLES = [
    (ISAIAH, "", "", ("Isaiah 5:1-7", "Philippians 3:4b-14", True, True)),
    (EASTER, "", "", ("Acts 10:34-43", "Colossians 3:1-4", True, True)),
    (EASTER, "Psalm 118:1-2, 14-24", "", ("Psalm 118:1-2, 14-24", "Acts 10:34-43", False, True)),
    (["Romans 8:1-11", "Psalm 23", "John 10:1-10"], "Psalm 23", "",
     ("Psalm 23", "Romans 8:1-11", False, True)),
    (ISAIAH, "", "Matthew 21:33-46", ("Isaiah 5:1-7", "Matthew 21:33-46", True, False)),
    (ISAIAH, "Isaiah 5:1-8", "", ("Isaiah 5:1-7", "Philippians 3:4b-14", True, True)),
    (ISAIAH, "", "Psalm 80:7-15", ("Isaiah 5:1-7", "Philippians 3:4b-14", True, True)),
    (["Isaiah 9:2-7", "Psalm 96"], "", "", ("Isaiah 9:2-7", None, True, True)),
]

# Case-name needles for the categories S Testing and 5a's doc_readings.json require.
REQUIRED_RESOLVE_CASES = (
    "S mixed: Easter lines, OT pick Psalm 118",
    "S mixed: a list starting with an epistle",
    "S mixed: Isaiah lines, NT pick Matthew",
    "S stale: OT pick that is no longer a line",
    "5a: RCL order",
    "5a: only OT and Psalm",
    "5a: gospel-only NT",
    "5a: an ' or ' entry",
    "5a: selected refs win",
    "5a: Easter order",
    "5a: blank entries",
    "5a stale: NT pick that is no longer a line",
    "5a: Psalm sent as NT pick",
    "A13: whole-line compare",
    "case-insensitive or",
    "deuterocanon",
    "abbreviations and roman numerals",
    "unknown first line",
)


def _fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _pair(pair: sr.ReadingPair) -> dict:
    return dataclasses.asdict(pair)


def test_fixture_books_match_BOOKS():
    assert _fixture()["books"] == [
        {"name": b.name, "testament": b.testament, "aliases": list(b.aliases)} for b in sr.BOOKS
    ]
    assert len(sr.BOOKS) == 66 + 18                       # the canon plus the S deuterocanon list
    assert sum(b.testament == "nt" for b in sr.BOOKS) == 27
    assert {b.name for b in sr.BOOKS if b.testament == "psalm"} == {"Psalms", "Psalm 151"}
    keys = [sr.normalize_book_text(b.name) for b in sr.BOOKS] + [a for b in sr.BOOKS for a in b.aliases]
    assert len(keys) == len(set(keys))                    # every lookup key names one book
    assert all(a == sr.normalize_book_text(a) for b in sr.BOOKS for a in b.aliases)
    with pytest.raises(dataclasses.FrozenInstanceError):
        sr.BOOKS[0].name = "Changed"


def test_fixture_split_alternatives():
    for case in _fixture()["split_alternatives"]:
        assert sr.split_alternatives(case["ref"]) == case["expected"], case["ref"]


def test_fixture_split_book():
    for case in _fixture()["split_book"]:
        hit = sr.split_book(case["ref"])
        got = None if hit is None else {"book": hit[0].name, "rest": hit[1]}
        assert got == case["expected"], case["ref"]


def test_fixture_classify_and_is_nt_ref():
    data = _fixture()
    for case in data["classify"]:
        assert sr.classify(case["ref"]) == case["expected"], case["ref"]
        assert sr.is_nt_ref(case["ref"]) is (case["expected"] == "nt"), case["ref"]
    for case in data["is_nt_ref"]:
        assert sr.is_nt_ref(case["ref"]) is case["expected"], case["ref"]


def test_fixture_expand_ref_options_and_clean_lines():
    data = _fixture()
    for case in data["expand_ref_options"]:
        assert sr.expand_ref_options(case["refs"]) == case["expected"], case["refs"]
    for case in data["clean_lines"]:
        assert sr.clean_lines(case["lines"]) == case["expected"], case["lines"]


def test_fixture_picker_options():
    for case in _fixture()["picker_options"]:
        assert sr.picker_options(case["scriptures"]) == case["expected"], case["scriptures"]


def test_fixture_resolve_readings():
    for case in _fixture()["resolve_readings"]:
        got = sr.resolve_readings(case["scriptures"], case["ot_pick"], case["nt_pick"])
        assert _pair(got) == case["expected"], case["name"]
        if got.nt_auto and got.nt is not None:            # never a Psalm as the automatic NT
            assert sr.is_nt_ref(sr.split_alternatives(got.nt)[0]), case["name"]


def test_fixture_default_reading_pair_and_default_nt_ref():
    data = _fixture()
    for case in data["default_reading_pair"]:
        assert _pair(sr.default_reading_pair(case["scriptures"])) == case["expected"], case["scriptures"]
    for case in data["default_nt_ref"]:
        assert sr.default_nt_ref(case["scriptures"]) == case["expected"], case["scriptures"]
    for case in data["resolve_readings"]:
        s = case["scriptures"]
        assert sr.default_reading_pair(s) == sr.resolve_readings(s, "", ""), case["name"]
        assert sr.default_nt_ref(s) == sr.resolve_readings(s).nt, case["name"]
    with pytest.raises(dataclasses.FrozenInstanceError):
        sr.default_reading_pair(ISAIAH).nt = "John 3:16"


def test_fixture_scripture_key():
    for case in _fixture()["scripture_key"]:
        assert sr.scripture_key(case["ref"]) == case["expected"], case["ref"]


def test_normalize_book_text():
    cases = {
        "  *1 John 3:1-3": "1 john 3:1-3",
        "* Acts 2:14a": "acts 2:14a",
        "Gen.  1:1": "gen 1:1",
        "I Cor. 13:1": "1 cor 13:1",
        "II Kings 2:1-12": "2 kings 2:1-12",
        "III John 1": "3 john 1",
        "IV Maccabees 1:1": "4 maccabees 1:1",
        "First Samuel 3": "1 samuel 3",
        "Second Corinthians 5": "2 corinthians 5",
        "Third John": "3 john",
        "Fourth Maccabees": "4 maccabees",
        "1st Peter 2": "1 peter 2",
        "2nd Timothy": "2 timothy",
        "3rd John": "3 john",
        "4th Maccabees": "4 maccabees",
        "1john 3:16": "1 john 3:16",
        "Isaiah 9:2": "isaiah 9:2",
        "Iv": "iv",
        "  Psalm   23  ": "psalm 23",
    }
    for raw, expected in cases.items():
        assert sr.normalize_book_text(raw) == expected, raw


def test_fixture_has_every_section_and_about():
    data = _fixture()
    about = data["_about"]
    assert set(SECTIONS) <= set(data)
    for name in data:
        if name == "_about":
            continue
        assert data[name], f"{name} is empty"
        assert isinstance(about.get(name), str) and about[name], f"_about does not document {name}"
    assert '"book"' in about["split_book"] and "null" in about["split_book"]
    assert '"ot"' in about["picker_options"] and '"nt"' in about["picker_options"]
    assert "snake_case" in about["resolve_readings"] and "otAuto" in about["resolve_readings"]


def test_normalize_for_fetch():
    cases = {
        "Isaiah 50:4-9a": "Isaiah 50:4-9",
        "Philippians 3:4b-14": "Philippians 3:4-14",
        "Luke 24:13-35b": "Luke 24:13-35",
        "John 1:1–14": "John 1:1-14",
        "John 1:1—14": "John 1:1-14",
        "Luke 2:1-14 (15-20)": "Luke 2:1-14, 15-20",
        "Luke 2:1-14, (15-20)": "Luke 2:1-14, 15-20",
        "John 1:(1-9), 10-18": "John 1:1-9, 10-18",
        "* Acts 2:14a, 22-32": "Acts 2:14, 22-32",
        "*Acts 2:14a": "Acts 2:14",
        "Luke 2:1-14 15-20": "Luke 2:1-14, 15-20",
        "Luke 2:1-14,, 15-20": "Luke 2:1-14, 15-20",
        "Luke  2:1-14": "Luke 2:1-14",
        "1 John 3:1-7": "1 John 3:1-7",
        "Genesis 2:15-17; 3:1-7": "Genesis 2:15-17; 3:1-7",
        "Proverbs 8:1-8, 19-21; 9:4b-6": "Proverbs 8:1-8, 19-21; 9:4-6",
    }
    for raw, expected in cases.items():
        assert sr.normalize_for_fetch(raw) == expected, raw


def test_split_parts_carries_book_and_keeps_quirks():
    assert sr.split_parts("Genesis 2:15-17; 3:1-7") == ["Genesis 2:15-17", "Genesis 3:1-7"]
    assert sr.split_parts("2 Kings 2:1-12") == ["2 Kings 2:1-12"]
    assert sr.split_parts("Proverbs 8:1-8, 19-21; 9:4b-6") == ["Proverbs 8:1-8, 19-21", "Proverbs 9:4b-6"]
    assert sr.split_parts("Wisdom of Solomon 1:13-15; 2:23-24") == [
        "Wisdom of Solomon 1:13-15", "Wisdom of Solomon 2:23-24"]
    assert sr.split_parts(" Isaiah 9:1-4; ; 9:5-7; ") == ["Isaiah 9:1-4", "Isaiah 9:5-7"]
    # Quirks kept from scripture_fetcher.fetch_passage: a bare chapter is not carried,
    # and a first part with no chapter:verse never sets the book.
    assert sr.split_parts("Psalm 42; 43") == ["Psalm 42", "43"]
    assert sr.split_parts("Psalm 42; 43:1-5") == ["Psalm 42", "43:1-5"]
    assert sr.split_parts(";") == []
    assert sr.split_parts("") == []


def test_split_joined():
    assert sr.split_joined("Genesis 1:1-2:4a and Psalm 136:1-9, 23-26") == [
        "Genesis 1:1-2:4a", "Psalm 136:1-9, 23-26"]
    assert sr.split_joined("Psalm 42 and 43") == ["Psalm 42 and 43"]
    assert sr.split_joined("Ezekiel 36:24-28 and Psalm 42 and 43") == ["Ezekiel 36:24-28", "Psalm 42 and 43"]
    assert sr.split_joined("Romans 6:3-11 and Psalm 114") == ["Romans 6:3-11", "Psalm 114"]
    assert sr.split_joined("Bel and the Dragon 1:1-22") == ["Bel and the Dragon 1:1-22"]
    assert sr.split_joined("  Luke 24:1-12  ") == ["Luke 24:1-12"]
    assert sr.split_joined("") == []


def test_every_spec_example_is_in_the_fixture():
    data = _fixture()
    resolve = [(c["scriptures"], c["ot_pick"], c["nt_pick"], c["expected"]) for c in data["resolve_readings"]]
    for scriptures, ot_pick, nt_pick, (ot, nt, ot_auto, nt_auto) in SPEC_RESOLVE_EXAMPLES:
        expected = {"ot": ot, "nt": nt, "ot_auto": ot_auto, "nt_auto": nt_auto}
        assert (scriptures, ot_pick, nt_pick, expected) in resolve, (scriptures, ot_pick, nt_pick)
    names = " | ".join(c["name"] for c in data["resolve_readings"])
    for needle in REQUIRED_RESOLVE_CASES:
        assert needle in names, needle
    # S Testing: split_book's longest alias, "1 John" vs "John", "1john", "I Cor.", "Song of Songs"
    split_book_refs = {c["ref"] for c in data["split_book"]}
    for ref in ("Matthew 17:1-9", "1 John 3:1-7", "John 3:1-17", "1john 4:7-21",
                "I Cor. 13:1-13", "Song of Songs 2:8-13", "Song of the Three 35-65"):
        assert ref in split_book_refs, ref
    # S :881: abbreviations, roman numerals, deuterocanon and unknown all classified
    assert {c["expected"] for c in data["classify"]} == {"ot", "psalm", "nt", "unknown"}
    # S normalize_for_fetch examples and the scripture_key equality
    keys = {c["ref"]: c["expected"] for c in data["scripture_key"]}
    assert keys["Luke 2:1-14 (15-20)"] == keys["Luke 2:1-14, (15-20)"] == "luke2:1-1415-20"
    assert keys["Isaiah 50:4-9a"] == "isaiah50:4-9"
