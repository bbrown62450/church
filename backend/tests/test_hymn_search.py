"""hymn_search: the scripture matcher and its helpers (slice 3 spec, Backend 2
"Matching" and "Required results"; Testing `test_hymn_search.py`; owner
decision 9; owner answer Q2: the recent-use key is the title alone; AC3)."""
from dataclasses import dataclass

from hymn_search import evenly_spaced, match_hymns, normalize_title, parse_themes, usage_key


@dataclass(frozen=True)
class H:
    title: str
    scripture_refs: str | None
    id: str = ""


def pool(*refs):
    return [H(title=f"Hymn {i}", scripture_refs=r, id=f"h{i}") for i, r in enumerate(refs)]


def strengths(result):
    return [(m.record.id, m.strength) for m in result.items]


# The spec's required-results table (S Backend 2); the first four are the
# verified over-matches of inventory §0 item 5.
REQUIRED = [
    ("Isaiah 9:6", "Genesis 9:6", None),
    ("Mark 1:9-15", "Mark 10:45", None),
    ("Psalm 1", "Psalm 119", None),
    ("John 3:1-17", "1 John 3:16", None),
    ("Matthew 17", "Matt 17:1-8", "passage"),
    ("Psalm 99", "Psalms 99", "passage"),
    ("Genesis 12:1-4a", "Genesis 12:1", "passage"),
    ("Mark 1:9-15", "Mark 1:1-8", "chapter"),
    ("Isaiah 9:2-7; 11:1", "Isaiah 11:1-9", "passage"),
    ("Luke 24:13-35 or Mark 16:1-8", "Mark 16:6", "passage"),
    ("Jude 24-25", "Jude 24", "passage"),
    ("Baruch 5:1-9", "Bar 5:5", "passage"),
    ("Wisdom of Solomon 1:13-15; 2:23-24", "Wis 2:23", "passage"),
    ("Sirach 27:4-7", "Ecclesiasticus 27:4", "passage"),
    ("Song of Solomon 2:8-13", "Song 2:10", "passage"),
    ("Transfiguration", "Matthew 17:1-9", None),
]


def test_required_results_table():
    for query, hymn_refs, expected in REQUIRED:
        result = match_hymns(pool(hymn_refs), [query])
        got = result.items[0].strength if result.items else None
        assert got == expected, (query, hymn_refs, got)
    assert match_hymns(pool("Matthew 17"), ["Transfiguration"]).unparsed_refs == ("Transfiguration",)
    assert match_hymns(pool("Bar 5:5"), ["Baruch 5:1-9"]).unparsed_refs == ()


def test_passage_tier_first_then_first_ref_then_pool_order():
    hymns = pool("Mark 1:1-8",          # h0: chapter for ref 0
                  "Psalm 23",           # h1: passage for ref 1
                  "Mark 1:12",          # h2: passage for ref 0
                  "Psalm 23:4; Mark 1:10")   # h3: passage for both
    result = match_hymns(hymns, ["Mark 1:9-15", "Psalm 23:1-6"])
    assert strengths(result) == [("h2", "passage"), ("h3", "passage"), ("h1", "passage"),
                                 ("h0", "chapter")]


def test_limit_per_ref_max_results_and_total():
    hymns = pool(*["John 3:16"] * 5, *["Psalm 23"] * 5)
    result = match_hymns(hymns, ["John 3", "Psalm 23"], limit_per_ref=3, max_results=4)
    assert result.total_matched == 6                      # 3 per ref, before max_results
    assert [m.record.id for m in result.items] == ["h0", "h1", "h2", "h5"]


def test_a_hymn_counts_once_and_lists_every_matching_ref():
    result = match_hymns(pool("John 3:16; Psalm 23:1"), ["Psalm 23", "John 3:1-17", "Mark 1"])
    (match,) = result.items
    assert match.matched_refs == ("Psalm 23", "John 3:1-17")
    assert result.total_matched == 1
    assert result.refs_used == ("Psalm 23", "John 3:1-17", "Mark 1")


def test_unparsed_hymn_text_falls_back_on_word_boundaries():
    hymns = pool("Psalm 1 (paraphrase)", "Psalm 119 (paraphrase)", "1 John 3 (echo)",
                 "John 3 (echo)")
    assert strengths(match_hymns(hymns, ["Psalm 1"])) == [("h0", "chapter")]
    assert strengths(match_hymns(hymns, ["John 3:16"])) == [("h3", "chapter")]
    # The fallback never yields more than "chapter".
    assert strengths(match_hymns(pool("Psalm 23 (metrical)"), ["Psalm 23:1"])) == [("h0", "chapter")]
    # Owner decision 1: a dotted verse still names its chapter; every chapter of
    # a query range (up to 11) is tried; a mid-string ordinal is a digit, so
    # "see I John 3" is 1 John, not John; a key of 2 characters or fewer is not tried.
    assert strengths(match_hymns(pool("cf. John 3.16"), ["John 3:16"])) == [("h0", "chapter")]
    assert strengths(match_hymns(pool("Isaiah 41 (paraphrase)"), ["Isaiah 40-42"])) == [("h0", "chapter")]
    assert match_hymns(pool("Isaiah 52 (paraphrase)"), ["Isaiah 40-60"]).items == ()
    assert match_hymns(pool("see I John 3 (echo)"), ["John 3:16"]).items == ()
    assert match_hymns(pool("see III John 1 (echo)", "and 2nd John 1"), ["John 1:1"]).items == ()
    assert strengths(match_hymns(pool("see First John 3 (echo)"), ["1 John 3"])) == [("h0", "chapter")]
    assert match_hymns(pool("this is 9 (note)"), ["Isaiah 9"]).items == ()


def test_whole_book_and_chapter_only_ff_tags_rank_as_chapter_at_most():
    """Owner answer B (2026-09-29): a whole-book tag and a chapter-only "ff" tag
    never make a passage match; "Psalm 148ff" is chapter 148 only."""
    assert strengths(match_hymns(pool("Psalms"), ["Psalm 23:1-6"])) == [("h0", "chapter")]
    assert strengths(match_hymns(pool("Psalm 148ff"), ["Psalm 148:1-6"])) == [("h0", "chapter")]
    assert match_hymns(pool("Psalm 148ff"), ["Psalm 150"]).items == ()
    assert strengths(match_hymns(pool("Psalm 148"), ["Psalm 148:1-6"])) == [("h0", "passage")]
    assert strengths(match_hymns(pool("Luke 4:14ff"), ["Luke 4:16-21"])) == [("h0", "passage")]
    assert strengths(match_hymns(pool("Jude"), ["Jude 24-25"])) == [("h0", "passage")]  # one chapter
    # Owner decision 1: Psalm 151 is one chapter, and "Psalm 151:1" names it.
    assert strengths(match_hymns(pool("Psalm 151:1"), ["Psalm 151 1-7"])) == [("h0", "passage")]


def test_blank_titles_and_blank_refs_are_skipped():
    hymns = [H("", "John 3:16", "blank-title"), H("  ", "John 3:16", "space-title"),
             H("Ok", None, "no-refs"), H("Ok", "   ", "blank-refs"), H("Kept", "John 3:16", "kept")]
    assert [m.record.id for m in match_hymns(hymns, ["John 3"]).items] == ["kept"]
    assert match_hymns(hymns, []).items == ()


def test_parse_themes():
    assert parse_themes(None) == []
    assert parse_themes(["Praise", " grace ", "", None, "praise"]) == ["Praise", "grace"]
    assert parse_themes('{Praise,"Call to Worship","Joy, Hope"}') == [
        "Praise", "Call to Worship", "Joy, Hope"]
    assert parse_themes("praise, grace; joy") == ["praise", "grace", "joy"]
    assert parse_themes("  ") == []


def test_normalize_title_and_usage_key_is_the_title_alone():
    assert normalize_title("  Holy,  Holy,\tHoly ") == "holy, holy, holy"
    assert normalize_title(None) == ""
    assert normalize_title("ＡＢＣ") == "abc"                       # NFKC
    # Owner answer Q2 (2026-09-29): the same title matches across numbers and hymnals.
    assert usage_key("Amazing Grace") == usage_key(" amazing  grace ")
    # Owner answer A (2026-09-29): punctuation, hyphens, curly quotes and "Oh" do not split a title.
    for one, other in (("Come, Thou Long-Expected Jesus", "Come, Thou Long Expected Jesus"),
                       ("The Lord's My Shepherd", "The Lord’s My Shepherd"),
                       ("Holy, Holy, Holy! Lord God Almighty", "Holy, Holy, Holy, Lord God Almighty"),
                       ("Amazing Grace", "Amazing Grace!"),
                       ("O God, Our Help in Ages Past", "Oh God Our Help in Ages Past")):
        assert usage_key(one) == usage_key(other), (one, other)
    assert usage_key("The Church's One Foundation") != usage_key("Church's One Foundation")   # articles stay
    assert usage_key("Come, Thou Long-Expected Jesus") == "come thou long expected jesus"
    assert normalize_title("Amazing Grace!") == "amazing grace!"          # exact-title resolution unchanged


def test_evenly_spaced_is_deterministic_and_in_range():
    items = list(range(120))
    sample = evenly_spaced(items, 50)
    assert sample == evenly_spaced(items, 50)
    assert len(sample) == 50 and len(set(sample)) == 50
    assert sample[0] == 0 and sample[-1] >= 80                       # reaches the last third
    assert sample == [items[(i * 120) // 50] for i in range(50)]
    assert evenly_spaced(items[:3], 40) == [0, 1, 2]
    assert evenly_spaced(items, 0) == []
