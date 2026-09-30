"""prayer_library: the reader and the example chooser (prayer library spec
§Data, §Writer hook; slice 4 spec, Testing `test_prayer_library.py`)."""
import prayer_library as pl


def _settings(library):
    return {"prayer_library": library}


CONFESSION_A = {"id": "p1", "type": "prayer_of_confession", "text": "Merciful God, {we} confess.",
                "added_at": "2026-09-26T15:00:00Z"}
CONFESSION_B = {"id": "p2", "type": "prayer_of_confession", "text": "Holy One, we have wandered.",
                "added_at": "2026-09-27T15:00:00Z"}
OTHER = {"id": "p3", "type": "other", "text": "A wedding prayer.", "added_at": "2026-09-27T16:00:00Z"}


def test_a_missing_key_or_junk_reads_as_the_empty_library():
    for settings in (None, {}, "junk", _settings(None), _settings([]), _settings("x"),
                     _settings({"prayers": "x"}), _settings({"prayers": [{"type": 5}]}),
                     _settings({"prayers": [{"type": "benediction"}], "voice_profile": 7})):
        assert pl.read_library(settings) == pl.EMPTY_LIBRARY, settings


def test_prayers_and_the_profile_are_read_and_bad_entries_skipped():
    library = pl.read_library(_settings({
        "prayers": [CONFESSION_A, "junk", {"type": "sermon", "text": "x"}, {"type": "benediction", "text": 3},
                    {"type": "benediction", "text": "Go."}],
        "voice_profile": "Warm and plain.",
    }))
    assert library.voice_profile == "Warm and plain."
    assert library.prayers == (
        pl.Prayer("p1", "prayer_of_confession", "Merciful God, {we} confess.", "2026-09-26T15:00:00Z"),
        pl.Prayer("", "benediction", "Go.", ""),
    )


def test_choose_example_uses_the_chooser_over_that_type_only():
    library = pl.read_library(_settings({"prayers": [CONFESSION_A, OTHER, CONFESSION_B]}))
    seen = []

    def last(texts):
        seen.append(list(texts))
        return texts[-1]

    assert pl.choose_example(library, "prayer_of_confession", choose=last) == "Holy One, we have wandered."
    assert seen == [["Merciful God, {we} confess.", "Holy One, we have wandered."]]
    assert pl.choose_example(library, "prayer_of_confession", choose=lambda texts: texts[0]) == \
        "Merciful God, {we} confess."


def test_no_example_without_that_type_and_never_an_other_prayer():
    library = pl.read_library(_settings({"prayers": [OTHER, {"type": "benediction", "text": "   "}]}))
    assert pl.choose_example(library, "benediction") is None           # blank text is no example
    assert pl.choose_example(library, "call_to_worship") is None
    assert pl.choose_example(library, "other") is None
    assert pl.choose_example(pl.EMPTY_LIBRARY, "benediction") is None


def test_limits_types_and_the_example_cut():
    assert pl.PRAYER_TYPES[-1] == "other" and len(pl.PRAYER_TYPES) == 9
    assert (pl.MAX_PRAYERS, pl.MAX_PRAYER_CHARS, pl.MAX_PROFILE_CHARS, pl.MAX_EXAMPLE_CHARS) == (
        30, 6_000, 2_000, 3_000)
    library = pl.read_library(_settings({"prayers": [{"type": "benediction", "text": "x" * 4000}]}))
    assert pl.choose_example(library, "benediction") == "x" * 3000
