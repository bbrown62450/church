import pytest
from sqlalchemy import select

import hymnary_facts as hf
from db import session_scope
from db.models import Hymn, HymnCatalog


@pytest.mark.parametrize("record, year", [
    ({"date": "1826"}, 1826),
    ({"date": "c. 1200", "author": "Perronet, Edward, 1721-1792"}, 1200),   # date wins
    ({"author": "Perronet, Edward, 1721-1792"}, 1792),
    ({"author": "Heermann, Johann, 1585-1647", "translator": "Bridges, Robert, 1844-1930"}, 1930),
    ({"translator": "Seiss, Joseph A. (Joseph Augustus) 1823-1904"}, 1904),
    ({"author": "Wren, Brian, 1936-"}, 1936 + hf.BIRTH_ONLY_OFFSET),
    ({"author": "Latin hymn, 12th cent."}, None),
    ({}, None),
])
def test_text_year(record, year):
    assert hf.text_year(record) == year


@pytest.mark.parametrize("record, count", [
    ({"number of hymnals": "3918"}, 3918),
    ({"number of hymnals": "1,322"}, 1322),
    ({"number of hymnals": ""}, None),
    ({}, None),
])
def test_hymnal_count(record, count):
    assert hf.hymnal_count(record) == count


def test_normalize_title_ignores_case_punctuation_and_leading_article():
    assert hf.normalize_title("Holy, Holy, Holy! Lord God Almighty") == \
        hf.normalize_title("holy holy holy lord god almighty")
    assert hf.normalize_title("The Church's One Foundation") == hf.normalize_title("Church's One Foundation")
    assert hf.normalize_title("O Come, All Ye Faithful") != hf.normalize_title("Come, All Ye Faithful")
    assert hf.normalize_title("  ") == ""


@pytest.mark.parametrize("refs, expected", [
    ("Isaiah 6:1-8; Revelation 4:8", ["Isaiah 6:1-8", "Revelation 4:8"]),
    ("Isaiah 6:1-8, Revelation 4:8", ["Isaiah 6:1-8", "Revelation 4:8"]),
    ("Romans 4:1-5, 13-17", ["Romans 4:1-5, 13-17"]),
    ("Psalm 23, 1 John 4:7", ["Psalm 23", "1 John 4:7"]),
    ("Psalm 23\nJohn 10:11", ["Psalm 23", "John 10:11"]),
    ("", []),
    (None, []),
])
def test_split_refs(refs, expected):
    assert hf.split_refs(refs) == expected


HOLY = {"title": "Holy, Holy, Holy! Lord God Almighty", "number of hymnals": "1322",
        "author": "Heber, Reginald, 1783-1826"}


class FakeFetch:
    """Stands in for the Hymnary API: {reference: json}. Counts calls per reference."""

    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def __call__(self, ref):
        self.calls.append(ref)
        return self.responses.get(ref, [])


def test_find_facts_matches_by_title_and_caches_each_reference():
    fetch = FakeFetch({"Isaiah 6:3": {"x": {"title": "Other Hymn"}, "Holy": HOLY}})
    cache = {}
    facts = hf.find_facts("Holy, Holy, Holy", "Isaiah 6:3", fetch, cache)
    assert facts is None   # "Holy, Holy, Holy" is not the full Hymnary title
    facts = hf.find_facts("Holy, Holy, Holy! Lord God Almighty", "Isaiah 6:3", fetch, cache)
    assert facts == {"text_year": 1826, "hymnal_count": 1322}
    assert fetch.calls == ["Isaiah 6:3"]   # second lookup served from the cache


# Hymnary often gives one title to several texts. Under "Psalm 23" the API lists
# a modern "The Lord's My Shepherd" in 14 hymnals before the Rous metrical psalm
# in 769, and the Rous record carries no date or people fields.
SHEPHERD_MODERN = {"title": "The Lord's My Shepherd", "number of hymnals": "14",
                   "author": "Townend, Stuart, 1963-"}
SHEPHERD_ROUS = {"title": "The Lord's my Shepherd", "number of hymnals": "769"}
SHEPHERD_UNCOUNTED = {"title": "The Lord's My Shepherd", "number of hymnals": ""}


def test_find_facts_takes_the_most_published_text_when_titles_collide():
    fetch = FakeFetch({"Psalm 23": {"a": SHEPHERD_UNCOUNTED, "b": SHEPHERD_MODERN,
                                    "c": SHEPHERD_ROUS}})
    facts = hf.find_facts("The Lord's My Shepherd", "Psalm 23", fetch, {})
    # Both facts come from the one chosen text: the modern text's year is not borrowed.
    assert facts == {"text_year": None, "hymnal_count": 769}


def test_find_facts_compares_matches_across_all_references():
    fetch = FakeFetch({"John 10:11": {"a": SHEPHERD_MODERN},
                       "Psalm 23": {"a": SHEPHERD_MODERN, "b": SHEPHERD_ROUS}})
    facts = hf.find_facts("The Lord's My Shepherd", "John 10:11; Psalm 23", fetch, {})
    assert facts == {"text_year": None, "hymnal_count": 769}
    assert fetch.calls == ["John 10:11", "Psalm 23"]


def test_find_facts_handles_empty_results_and_missing_refs():
    fetch = FakeFetch({})
    assert hf.find_facts("Anything", "Jude 1:25", fetch, {}) is None   # API returns []
    assert hf.find_facts("Anything", "", fetch, {}) is None
    assert hf.find_facts("", "Jude 1:25", fetch, {}) is None


def test_run_backfill_fills_blanks_without_overwriting(tmp_db, make_church):
    cid = make_church()
    with session_scope() as s:
        s.add(HymnCatalog(title=HOLY["title"], scripture_refs="Isaiah 6:3"))
        s.add(Hymn(church_id=cid, title=HOLY["title"], scripture_refs="Isaiah 6:3", text_year=1800))
        s.add(Hymn(church_id=cid, title="Unknown Hymn", scripture_refs="Isaiah 6:3"))
        s.add(Hymn(church_id=cid, title="No Refs"))
    fetch = FakeFetch({"Isaiah 6:3": {"Holy": HOLY}})

    stats = hf.run_backfill(fetch)

    assert stats == {"checked": 4, "matched": 2, "updated": 2, "unknown": 2}
    assert fetch.calls == ["Isaiah 6:3"]
    with session_scope() as s:
        cat = s.execute(select(HymnCatalog)).scalar_one()
        assert (cat.text_year, cat.hymnal_count) == (1826, 1322)
        holy = s.execute(select(Hymn).where(Hymn.title == HOLY["title"])).scalar_one()
        assert (holy.text_year, holy.hymnal_count) == (1800, 1322)   # 1800 kept
    assert hf.run_backfill(fetch)["checked"] == 2   # only the two unknowns remain blank


def test_run_backfill_dry_run_writes_nothing(tmp_db):
    with session_scope() as s:
        s.add(HymnCatalog(title=HOLY["title"], scripture_refs="Isaiah 6:3"))
    stats = hf.run_backfill(FakeFetch({"Isaiah 6:3": {"Holy": HOLY}}), dry_run=True)
    assert stats["updated"] == 1
    with session_scope() as s:
        assert s.execute(select(HymnCatalog)).scalar_one().text_year is None
