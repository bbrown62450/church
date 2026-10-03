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
