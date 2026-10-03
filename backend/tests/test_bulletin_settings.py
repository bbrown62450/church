"""The church's standing bulletin settings (printed bulletin spec, PR 2a;
bulletin_settings.py): the defaults, the tolerant read and the stored shape."""
import pytest

import bulletin_settings as bs

DEFAULT_JSON = {
    "address_lines": [], "phone": "", "email": "", "website": "", "facebook": "", "service_time": "",
    "worship_leader": "", "liturgist": "", "organist": "", "stand_note": "Congregation stands if able",
    "gloria_patri_words": bs.GLORIA_PATRI,
    "starred": ["first_hymn", "gloria_patri", "affirmation_of_faith", "second_hymn", "doxology", "third_hymn",
                "benediction"],
    "leaders": {"prelude": "organist", "welcome": "liturgist", "call_to_worship": "liturgist",
                "opening_prayer": "liturgist", "prayer_of_confession": "liturgist", "assurance": "liturgist",
                "prayer_for_illumination": "liturgist", "ot_reading": "liturgist", "nt_reading": "worship_leader",
                "sermon": "worship_leader", "prayers_of_the_people": "worship_leader",
                "offertory_prayer": "worship_leader", "postlude": "organist"},
}


@pytest.mark.parametrize("settings", [None, {}, {"bulletin": None}, {"bulletin": "x"}, {"bulletin": []}, "x"])
def test_nothing_stored_reads_the_defaults(settings):
    assert bs.read(settings) == bs.BulletinSettings()
    assert bs.read(settings).to_json() == DEFAULT_JSON


def test_a_stored_value_reads_back_clean_and_in_order():
    stored = {"bible_translation": "kjv", "bulletin": {
        "address_lines": ["  100 Example Street ", "", "Springfield, ST 00000", "Line three", "Line four"],
        "phone": " (555) 010-0100 ", "email": "office@example.com", "website": "example.com",
        "facebook": "Example Church", "service_time": "10:30 a.m.", "worship_leader": "Rev. Alex Example",
        "liturgist": "Sam Sample", "organist": "Jordan Doe", "stand_note": " **Please stand if able ",
        "gloria_patri_words": "Glory be.", "starred": ["sermon", "prelude", "nope", "prelude"],
        "leaders": {"sermon": "organist", "prelude": "liturgist", "nope": "organist", "welcome": "pastor"},
    }}
    s = bs.read(stored)
    assert s.address_lines == ("100 Example Street", "Springfield, ST 00000", "Line three")
    assert (s.phone, s.stand_note, s.starred) == ("(555) 010-0100", "Please stand if able",
                                                 frozenset({"prelude", "sermon"}))
    assert s.to_json()["starred"] == ["prelude", "sermon"]
    assert s.to_json()["leaders"] == {"prelude": "liturgist", "sermon": "organist"}
    assert (s.leader("sermon"), s.leader("prelude"), s.leader("welcome")) == ("Jordan Doe", "Sam Sample", "")
    assert bs.read({"bulletin": s.to_json()}) == s


def test_a_field_of_the_wrong_type_is_its_default_and_a_long_text_is_cut():
    s = bs.read({"bulletin": {"phone": 5, "address_lines": "100 Example Street", "starred": "sermon",
                              "leaders": ["sermon"], "stand_note": None, "organist": "x" * 150,
                              "gloria_patri_words": ""}})
    assert s == bs.BulletinSettings(organist="x" * 100, gloria_patri_words="")
    assert s.leader("prelude") == "x" * 100 and s.leader("sermon") == ""


def test_every_text_but_the_gloria_patri_words_reads_as_one_line():
    """Build review I1: a control character, a C1 control or U+2028/U+2029 stored by any other path reads as a
    space, so GET always answers something PUT accepts; the Gloria Patri words keep their lines."""
    s = bs.read({"bulletin": {
        "phone": "(555)\n010-0100", "email": "x\x7fy", "website": "a \t b", "facebook": "\tExample\r\n",
        "service_time": "10:30 a.m.", "worship_leader": "Alex Example", "liturgist": "Sam\x85Sample",
        "organist": "Jo\r\nDoe", "stand_note": "\n* Please\x0bstand", "gloria_patri_words": "Glory be.\nAmen.",
        "address_lines": ["1 Main\nSt", "\x0b\t", "Springfield"],
    }})
    assert (s.phone, s.email, s.website, s.facebook) == ("(555) 010-0100", "x y", "a b", "Example")
    assert (s.service_time, s.worship_leader, s.liturgist, s.organist) == (
        "10:30 a.m.", "Alex Example", "Sam Sample", "Jo Doe")
    assert s.stand_note == "Please stand"
    assert s.address_lines == ("1 Main St", "Springfield")
    assert s.gloria_patri_words == "Glory be.\nAmen."
