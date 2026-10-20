"""The pew voices' storage (pew voices spec 2026-10-20, "Storage"): the one
reader with the owner's five as defaults, and the save through
usecases.prayer_library.save_library (the limits, the role, the other
settings keys)."""
import datetime

import pytest

import pew_voices
from domain_errors import Forbidden, InvalidInput
from repos import churches
from repos.memberships import add_membership
from usecases import prayer_library as library_usecase

NOON = datetime.datetime(2026, 10, 20, 16, 0, tzinfo=datetime.timezone.utc)
FIVE = [
    {"description": "Sharp, very conservative, reads every word", "on": True},
    {"description": "A teenager", "on": True},
    {"description": "A man who rarely comes to church", "on": True},
    {"description": "Parents of busy young kids", "on": True},
    {"description": "Someone deeply worried about their health", "on": True},
]


@pytest.fixture
def world(tmp_db, make_user, make_church):
    owner = make_user(email="owner@example.com")
    member = make_user(email="member@example.com")
    cid = make_church(name="Grace", owner_user_id=owner)
    add_membership(member, cid, "member")
    return {"church": cid, "owner": owner, "member": member}


def _save(world, voices, *, who="owner"):
    return library_usecase.save_library(world["church"], world[who], [], "", voices, now=lambda: NOON)


def _settings(world):
    return churches.get_church(world["church"])["settings"]


def test_the_owner_s_five_are_the_default_until_saved_and_junk_reads_as_them():
    assert pew_voices.voices_out(pew_voices.DEFAULT_VOICES) == FIVE
    for settings in (None, {}, {"pew_voices": None}, {"pew_voices": {"a": 1}}, {"pew_voices": "x"}, ["junk"]):
        assert pew_voices.read_voices(settings) == pew_voices.DEFAULT_VOICES, settings


def test_a_saved_list_is_read_as_saved_an_empty_one_is_none_bad_rows_are_skipped_and_long_ones_cut():
    assert pew_voices.read_voices({"pew_voices": []}) == ()
    stored = [{"description": "A nurse", "on": False}, "junk", {"description": "  "}, {"on": True},
              {"description": "A grandmother", "on": "yes"}, {"description": "A choir member", "on": True},
              {"description": "w" * 400, "on": True}]
    assert pew_voices.read_voices({"pew_voices": stored}) == (
        pew_voices.PewVoice("A nurse", False), pew_voices.PewVoice("A grandmother", False),
        pew_voices.PewVoice("A choir member", True), pew_voices.PewVoice("w" * 300, True))


def test_turned_on_keeps_the_order_and_never_more_than_six():
    voices = tuple(pew_voices.PewVoice(f"Voice {i}", i != 2) for i in range(1, 10))
    assert [v.description for v in pew_voices.turned_on(voices)] == [
        "Voice 1", "Voice 3", "Voice 4", "Voice 5", "Voice 6", "Voice 7"]


def test_an_admin_saves_cleaned_voices_and_every_other_setting_stays(world):
    churches.update_church(world["church"], settings={"rubric": {"prefer_familiar": False}, "foo": 1})
    out = _save(world, [{"description": "  A nurse\r\non nights ", "on": True}, {"description": "A teen", "on": False}])
    assert out["pew_voices"] == [{"description": "A nurse on nights", "on": True},
                                 {"description": "A teen", "on": False}]
    settings = _settings(world)
    assert settings["pew_voices"] == out["pew_voices"]
    assert (settings["rubric"], settings["foo"]) == ({"prefer_familiar": False}, 1)
    assert library_usecase.get_library(world["church"], can_edit=False)["pew_voices"] == out["pew_voices"]


def test_a_save_without_voices_keeps_the_stored_ones_and_an_empty_list_is_kept(world):
    _save(world, [{"description": "A nurse", "on": True}])
    out = library_usecase.save_library(world["church"], world["owner"], [], "Warm.", now=lambda: NOON)
    assert out["pew_voices"] == [{"description": "A nurse", "on": True}]
    assert _settings(world)["pew_voices"] == [{"description": "A nurse", "on": True}]
    assert _save(world, [])["pew_voices"] == []
    assert library_usecase.get_library(world["church"], can_edit=True)["pew_voices"] == []


@pytest.mark.parametrize("voices, field, message", [
    ([{"description": f"Voice {i}", "on": i < 6} for i in range(13)], "pew_voices", "You can keep up to 12 voices."),
    ([{"description": " \n ", "on": True}], "pew_voices.0.description", "Describe this voice."),
    ([{"description": "A teen", "on": True}, {"description": "x" * 301, "on": False}],
     "pew_voices.1.description", "This description is too long (300 characters at most)."),
    ([{"description": f"Voice {i}", "on": True} for i in range(7)], "pew_voices", "Turn on at most 6 voices."),
])
def test_each_limit_is_refused_with_its_field_and_nothing_is_saved(world, voices, field, message):
    with pytest.raises(InvalidInput) as refused:
        _save(world, voices)
    assert (refused.value.message, refused.value.field) == (message, field)
    assert "pew_voices" not in (_settings(world) or {})


def test_six_on_three_hundred_characters_and_twelve_voices_are_allowed(world):
    voices = [{"description": ("v" * 299) + str(i % 10), "on": i < 6} for i in range(12)]
    assert len(_save(world, voices)["pew_voices"]) == 12


def test_a_member_cannot_save_voices(world):
    with pytest.raises(Forbidden):
        _save(world, [{"description": "A nurse", "on": True}], who="member")
    assert "pew_voices" not in (_settings(world) or {})
