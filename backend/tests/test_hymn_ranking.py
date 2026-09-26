from hymn_ranking import facts_note, rank_candidates


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
