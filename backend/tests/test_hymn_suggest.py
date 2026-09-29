"""hymn_suggest: candidates, the prompt, parsing, resolution and the final
slots (slice 3 spec, Backend 3.6 steps 6-9 and 3.8; Testing
`test_hymn_suggest.py` and "Rubric"; owner decision 3; owner answer Q1 of
2026-09-29; AC11, AC19).

The rubric cases port PR #4's test_suggest_hymns.py to the new pipeline
(Task 14 deletes that file with suggest_hymns_for_service)."""
import uuid

import hymn_suggest as hs
from repos.hymns import HymnRecord
from service_rubric import default_rubric

RUBRIC = default_rubric()
NO_PICKS = {"opening": None, "response": None, "closing": None}


def rec(title, number=None, *, theme=None, refs=None, year=None, count=None, hymnal="GG2013"):
    return HymnRecord(id=uuid.uuid5(uuid.NAMESPACE_URL, f"{hymnal}/{number}/{title}"), hymnal=hymnal,
                      title=title, number=number, link=None, scripture_refs=refs, theme=theme,
                      text_year=year, hymnal_count=count)


def rubric_with(**settings):
    rubric = default_rubric()
    rubric.update(settings)
    return rubric


def titles(records):
    return [r.title for r in records]


def build(eligible, scriptures=(), *, nt_ref=None, picks=None, rubric=RUBRIC):
    return hs.build_candidates(eligible, list(scriptures), nt_ref=nt_ref,
                               current_picks=picks or NO_PICKS, rubric=rubric)


# --- T11: build_candidates -------------------------------------------------------------


def test_themes_match_at_word_starts():
    joyful, enjoy = rec("Joyful", 1, theme="joyful praise"), rec("Enjoy", 2, theme="enjoy")
    gathering = rec("Gathering", 3, theme='{"Call to Worship",Gathering}')
    assert hs.matches_theme(joyful, hs._CLOSING_THEMES)        # "joy" matches "joyful" ...
    assert not hs.matches_theme(enjoy, hs._CLOSING_THEMES)     # ... but not "enjoy"
    assert hs.matches_theme(gathering, hs._OPENING_THEMES)
    candidates = build([joyful, enjoy, gathering, rec("Plain", 4, theme="grace")])
    assert titles(candidates.by_slot["closing"][:1]) == ["Joyful"]      # focused, then the pad
    assert titles(candidates.by_slot["opening"][:1]) == ["Gathering"]


def test_a_short_list_is_padded_to_40_with_an_even_sample_in_hymnal_order():
    hymns = [rec(f"Hymn {n}", n) for n in range(1, 201)]
    hymns[99] = rec("Gathering Song", 100, theme="gathering")
    opening = build(hymns).by_slot["opening"]
    assert len(opening) == 40
    assert opening[0].title == "Gathering Song"                 # focused first
    rest = [h for h in hymns if h.title != "Gathering Song"]
    assert opening[1:] == [rest[(i * 199) // 39] for i in range(39)]   # no facts: the plain sample
    assert opening[-1].number > 180                             # not the first 40 (the Advent bias)


def test_response_is_the_passage_tier_then_the_chapter_tier_capped_at_50():
    hymns = [rec(f"Chapter {n}", n, refs="Mark 1:1") for n in range(1, 31)]
    hymns += [rec(f"Passage {n}", 100 + n, refs="John 3:16") for n in range(1, 31)]
    response = build(hymns, ["John 3:14-21", "Mark 1:9"]).by_slot["response"]
    assert len(response) == 50
    assert titles(response[:30]) == [f"Passage {n}" for n in range(1, 31)]
    assert titles(response[30:]) == [f"Chapter {n}" for n in range(1, 21)]


def test_the_nt_reading_leads_the_response_list_and_survives_the_cap():
    hymns = [rec(f"OT {n}", n, refs="Isaiah 6:3") for n in range(1, 31)]
    hymns += [rec(f"Psalm {n}", 100 + n, refs="Psalm 23") for n in range(1, 31)]
    hymns += [rec(f"Gospel {n}", 200 + n, refs="Mark 1:10") for n in range(1, 6)]
    scriptures = ["Isaiah 6:1-8", "Psalm 23", "Romans 8:12-17", "Mark 1:9-15"]
    response = build(hymns, scriptures, nt_ref="Mark 1:9-15").by_slot["response"]
    assert titles(response[:5]) == [f"Gospel {n}" for n in range(1, 6)]
    assert len(response) == 50
    assert hs.response_refs("Mark 1:9-15", scriptures) == [
        "Mark 1:9-15", "Isaiah 6:1-8", "Psalm 23", "Romans 8:12-17"]


def test_a_long_theme_list_without_facts_is_sampled_evenly():
    hymns = [rec(f"Joy {n}", n, theme="joy") for n in range(1, 121)]
    candidates = build(hymns)
    closing = candidates.by_slot["closing"]
    assert len(closing) == 50 and candidates.modes["closing"] == "sampled"
    assert [h.number for h in closing] == [1 + (i * 120) // 50 for i in range(50)]
    assert any(h.number > 80 for h in closing)                  # hymns from the last third


def test_other_slots_picks_are_left_out_and_a_slots_own_pick_stays():
    hymns = [rec(f"Praise {n}", n, theme="gathering, joy", refs="Psalm 23") for n in range(1, 6)]
    picked = hymns[2]
    picks = {"opening": None, "response": picked.id, "closing": None}
    candidates = build(hymns, ["Psalm 23"], picks=picks)
    assert picked in candidates.by_slot["response"]
    assert picked not in candidates.by_slot["opening"]
    assert picked not in candidates.by_slot["closing"]


def test_focused_lists_are_ranked_by_the_rubric():
    hymns = [rec("Newer", 1, theme="joy", year=1995, count=40),
             rec("Unknown", 2, theme="joy"),
             rec("Old rare", 3, theme="joy", year=1850, count=5),
             rec("Old common", 4, theme="joy", year=1840, count=3000),
             rec("Old median", 5, theme="joy", year=1800)]          # unknown count: the median
    closing = build(hymns).by_slot["closing"][:5]
    assert titles(closing) == ["Old common", "Old median", "Old rare", "Unknown", "Newer"]
    unfamiliar = build(hymns, rubric=rubric_with(prefer_familiar=False)).by_slot["closing"][:5]
    assert titles(unfamiliar) == ["Old rare", "Old common", "Old median", "Unknown", "Newer"]
    by_1845 = build(hymns, rubric=rubric_with(prefer_before_year=1845)).by_slot["closing"][:5]
    # 1850 now counts as newer; within the newer hymns the more familiar leads.
    assert titles(by_1845) == ["Old common", "Old median", "Unknown", "Newer", "Old rare"]


def test_a_long_ranked_list_keeps_ten_places_for_newer_hymns():
    hymns = [rec(f"Old {n}", n, theme="joy", year=1800 + n, count=10) for n in range(60)]
    hymns += [rec(f"New {n}", 100 + n, theme="joy", year=1990 + n % 10, count=10) for n in range(20)]
    candidates = build(hymns)
    closing = candidates.by_slot["closing"]
    assert len(closing) == 50 and candidates.modes["closing"] == "ranked"
    assert sum(h.title.startswith("New") for h in closing) == 10
    assert closing[0].title == "Old 0" and closing[-1].title.startswith("New")


def test_the_pad_follows_the_focused_hymns_and_is_ranked():
    hymns = [rec(f"Pad {n}", n, year=(1990 if n % 2 else 1850), count=n) for n in range(1, 101)]
    hymns[0] = rec("Gathering A", 1, theme="gathering", year=1995)
    hymns[1] = rec("Gathering B", 2, theme="gathering", year=1800)
    hymns[2] = rec("Gathering C", 3, theme="gathering")
    opening = build(hymns).by_slot["opening"]
    assert len(opening) == 40
    assert titles(opening[:3]) == ["Gathering B", "Gathering C", "Gathering A"]
    pad = opening[3:]
    assert len(pad) == 37
    older = [h for h in pad if h.text_year == 1850]
    assert pad[:len(older)] == older                           # older first within the pad
    assert [h.hymnal_count for h in older] == sorted((h.hymnal_count for h in older), reverse=True)
