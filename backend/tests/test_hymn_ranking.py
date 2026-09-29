from dataclasses import dataclass

from hymn_ranking import facts_note, is_newer_than_preferred, rank_candidates, shortlist


def h(name, year=None, count=None):
    return {"id": name, "Hymn Title": name, "Text Year": year, "Hymnal Count": count}


def titles(hymns):
    return [x["Hymn Title"] for x in hymns]


def test_older_first_then_unknown_then_newer():
    hymns = [h("new", 1990), h("unknown"), h("old", 1826), h("edge", 1970)]
    ranked = rank_candidates(hymns, prefer_before_year=1970, prefer_familiar=False)
    assert titles(ranked) == ["old", "unknown", "new", "edge"]   # 1970 is not "before 1970"


def test_familiar_first_within_each_era():
    hymns = [h("old-rare", 1800, 10), h("old-famous", 1850, 3000), h("new-famous", 1990, 900)]
    ranked = rank_candidates(hymns, prefer_before_year=1970, prefer_familiar=True)
    assert titles(ranked) == ["old-famous", "old-rare", "new-famous"]


def test_unknown_count_ranks_as_the_median():
    hymns = [h("low", 1800, 10), h("unknown", 1800), h("high", 1800, 1000), h("mid", 1800, 100)]
    ranked = rank_candidates(hymns, prefer_before_year=1970, prefer_familiar=True)
    # median of known counts (10, 100, 1000) is 100; ties keep input order
    assert titles(ranked) == ["high", "unknown", "mid", "low"]


def test_familiarity_off_keeps_input_order_within_era():
    hymns = [h("b", 1800, 10), h("a", 1800, 3000)]
    assert titles(rank_candidates(hymns, prefer_before_year=1970, prefer_familiar=False)) == ["b", "a"]


def test_does_not_mutate_input_and_handles_empty():
    hymns = [h("new", 1990), h("old", 1800)]
    rank_candidates(hymns, prefer_before_year=1970, prefer_familiar=True)
    assert titles(hymns) == ["new", "old"]
    assert rank_candidates([], prefer_before_year=1970, prefer_familiar=True) == []


def test_facts_note():
    assert facts_note(h("x", 1826, 1322)) == "(written 1826, in 1,322 hymnals)"
    assert facts_note(h("x", 1826)) == "(written 1826)"
    assert facts_note(h("x", None, 84)) == "(in 84 hymnals)"
    assert facts_note(h("x")) == ""


def test_shortlist_keeps_everything_within_the_limit():
    ranked = [h("old", 1800), h("unknown"), h("new", 1990)]
    assert titles(shortlist(ranked, limit=3, prefer_before_year=1970, reserve=1)) == ["old", "unknown", "new"]


def test_shortlist_reserves_places_for_unknown_and_newer_hymns_in_turn():
    ranked = ([h(f"old{i}", 1800 + i) for i in range(6)]
              + [h("unknown1"), h("unknown2"), h("unknown3")]
              + [h("new1", 1990), h("new2", 1991)])
    picked = shortlist(ranked, limit=6, prefer_before_year=1970, reserve=3)
    # three places go to unknown1, new1, unknown2 (alternating); the rest are the top older hymns
    assert titles(picked) == ["old0", "old1", "old2", "unknown1", "unknown2", "new1"]


def test_shortlist_gives_unused_reserved_places_back_to_older_hymns():
    ranked = [h(f"old{i}", 1800 + i) for i in range(6)] + [h("new1", 1990)]
    picked = shortlist(ranked, limit=5, prefer_before_year=1970, reserve=3)
    assert titles(picked) == ["old0", "old1", "old2", "old3", "new1"]


# --- slice 3a: accessors for typed records, and the newer-than-preferred rule ---

@dataclass(frozen=True)
class Rec:
    name: str
    text_year: int | None = None
    hymnal_count: int | None = None


def test_accessors_over_records_give_the_same_order_as_flat_dicts():
    rows = [("Newer", 1995, 40), ("Unknown", None, None), ("Old rare", 1850, 5),
            ("Old common", 1840, 900), ("Unknown common", None, 3000)]
    flat = [h(n, y, c) for n, y, c in rows]
    records = [Rec(n, y, c) for n, y, c in rows]
    year_of, count_of = (lambda r: r.text_year), (lambda r: r.hymnal_count)
    for familiar in (True, False):
        want = titles(rank_candidates(flat, prefer_before_year=1970, prefer_familiar=familiar))
        got = rank_candidates(records, prefer_before_year=1970, prefer_familiar=familiar,
                              year_of=year_of, count_of=count_of)
        assert [r.name for r in got] == want
    ranked = rank_candidates(records, prefer_before_year=1970, prefer_familiar=True,
                             year_of=year_of, count_of=count_of)
    assert [r.name for r in shortlist(ranked, limit=3, prefer_before_year=1970, reserve=1,
                                      year_of=year_of)] == ["Old common", "Old rare", "Unknown common"]
    assert facts_note(Rec("x", 1826, 1322), year_of=year_of, count_of=count_of) == (
        "(written 1826, in 1,322 hymnals)")
    assert facts_note(Rec("x"), year_of=year_of, count_of=count_of) == ""


def test_is_newer_than_preferred():
    assert is_newer_than_preferred(None, 1970) is False
    assert is_newer_than_preferred(1969, 1970) is False
    assert is_newer_than_preferred(1970, 1970) is True
    assert is_newer_than_preferred(1985, 1970) is True
    assert is_newer_than_preferred(1985, None) is False     # no preference: never flagged
