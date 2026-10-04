"""A service's weekly bulletin fields (printed bulletin spec, "Data model";
PR 2b; service_bulletin.py): the tolerant read, the stored shape and what
carries forward to the next week."""
import pytest

import service_bulletin as sb

EMPTY_JSON = {
    "prelude": {"title": "", "composer": ""}, "postlude": {"title": "", "composer": ""},
    "people": {"worship_leader": None, "liturgist": None, "organist": None}, "leaders": {},
    "announcements": {"ushers": "", "deacon": "", "coffee_hour": "", "activities": "", "prayer_concerns": "",
                      "collection": "", "other": ""},
    "reading_text": {"ot": "", "nt": ""}, "unchecked": [],
}


@pytest.mark.parametrize("raw", [None, {}, "x", [], {"prelude": "x", "people": [], "announcements": 5}])
def test_nothing_stored_reads_as_an_empty_bulletin(raw):
    assert sb.read(raw) == sb.ServiceBulletin()
    assert sb.read(raw).to_json() == EMPTY_JSON
    assert sb.read(raw).is_blank()


def test_a_stored_value_reads_back_clean():
    stored = {
        "prelude": {"title": "  Morning\nVoluntary ", "composer": "Pat Example"},
        "postlude": {"title": "Festive Postlude", "composer": 7},
        "people": {"worship_leader": " Rev. Guest ", "liturgist": "", "organist": 3, "pastor": "x"},
        "leaders": {"sermon": " Rev. Guest\t", "nope": "Sam Sample", "welcome": "  ", "offering": None},
        "announcements": {"ushers": "Sam Sample,\r\nJordan Doe", "deacon": "x" * 150,
                          "activities": "  Tuesday: Bible study.\nWednesday: Choir.  ", "other": None},
        "reading_text": {"ot": " In you, Lord, I put my trust.\n\nAmen. ", "nt": ["x"]},
        "unchecked": ["coffee_hour", "nope", 3, "prelude", "coffee_hour"],
        "cover_image_id": "later",
    }
    b = sb.read(stored)
    assert b.prelude == sb.Music("Morning Voluntary", "Pat Example")
    assert b.postlude == sb.Music("Festive Postlude", "")
    assert b.people == {"worship_leader": "Rev. Guest", "liturgist": "", "organist": None}
    assert b.leaders == {"sermon": "Rev. Guest"}
    assert (b.announcements.ushers, b.announcements.deacon) == ("Sam Sample, Jordan Doe", "x" * 100)
    assert b.announcements.activities == "Tuesday: Bible study.\nWednesday: Choir."
    assert (b.ot_text, b.nt_text) == ("In you, Lord, I put my trust.\n\nAmen.", "")
    assert b.unchecked == ("prelude", "coffee_hour")                     # known boxes, once each, in order
    assert not b.is_blank()
    assert sb.read(b.to_json()) == b


def test_what_carries_forward_is_the_music_and_the_announcements():
    week = sb.read({"prelude": {"title": "Morning Voluntary", "composer": ""}, "people": {"organist": "Sam Sample"},
                    "leaders": {"sermon": "Rev. Guest"}, "announcements": {"coffee_hour": "The Example family"},
                    "reading_text": {"nt": "Pasted."}, "unchecked": ["prelude"]})
    assert week.carried() == sb.ServiceBulletin(prelude=sb.Music("Morning Voluntary", ""),
                                                announcements=sb.Announcements(coffee_hour="The Example family"))


def test_map_texts_changes_every_text_and_keeps_the_standing_people():
    week = sb.read({"prelude": {"title": "a"}, "people": {"liturgist": "b"}, "leaders": {"sermon": "c"},
                    "announcements": {"other": "d"}, "reading_text": {"ot": "e"}})
    upper = week.map_texts(str.upper)
    assert upper.to_json()["prelude"]["title"] == "A"
    assert upper.people == {"worship_leader": None, "liturgist": "B", "organist": None}
    assert (upper.leaders, upper.announcements.other, upper.ot_text) == ({"sermon": "C"}, "D", "E")


def test_every_line_break_in_a_free_text_is_a_newline_and_a_pasted_reading_keeps_one_blank_line():
    """Plan review fix M2: U+2028, U+2029 and U+0085 (pasted from Pages or Word) would print as "?" in the
    PDF; a pasted reading's runs of blank lines are one paragraph break, and it is cut at 10 000."""
    b = sb.read({"announcements": {"prayer_concerns": "For Sam\u2028For Lee\u2029For all\x85Amen.\r\nEnd",
                                   "coffee_hour": "The Example\u2028family"},
                 "reading_text": {"ot": "Verse one.\r\n\r\n \n\nVerse two.\u2029\u2029Verse three.\nAmen.",
                                  "nt": "x" * 12_000}})
    assert b.announcements.prayer_concerns == "For Sam\nFor Lee\nFor all\nAmen.\nEnd"
    assert b.announcements.coffee_hour == "The Example family"
    assert b.ot_text == "Verse one.\n\nVerse two.\n\nVerse three.\nAmen."
    assert b.nt_text == "x" * 10_000


def test_a_control_character_goes_before_the_other_rules_so_the_text_reads_back_the_same():
    """Build review fixes M1 and M2: what a Word file cannot hold is deleted before the blank lines are
    collapsed (else deleting it later leaves extra blank lines, so the stored text and GET disagree), and a
    free text loses its C1 controls (the PDF prints them as "?") once U+0085 is a line break."""
    raw = {"announcements": {"activities": "Line one\x02\x85\x9bLine two\x7f", "ushers": "Sam\x01Sample ￾",
                             "other": "Ends with a stray \udc80"},
           "reading_text": {"ot": "Verse one.\n\n\x01\n\nVerse two.", "nt": "One.\r\x01\nTwo.\x90"}}
    b = sb.read(raw)
    assert b.ot_text == "Verse one.\n\nVerse two."
    assert b.nt_text == "One.\nTwo."
    assert b.announcements.activities == "Line one\nLine two"
    assert b.announcements.ushers == "Sam Sample"                          # one line: a control is a space
    assert b.announcements.other == "Ends with a stray"
    assert sb.read(b.to_json()) == b                                       # read again, nothing changes


def test_the_cover_picture_is_read_stored_and_carried():
    """PR 3a: cover_image_id is a picture's id or None (no picture this week); a bulletin that does not say
    (a page from before PR 3b) is cover_given False and stores no key. It carries forward with the music."""
    picture_id = "0B4C2B0E-1111-4222-8333-444455556666"
    week = sb.read({"cover_image_id": picture_id, "prelude": {"title": "Morning Voluntary"},
                    "people": {"organist": "Sam Sample"}})
    assert (week.cover_image_id, week.cover_given) == (picture_id.lower(), True)
    assert week.to_json()["cover_image_id"] == picture_id.lower()
    assert sb.read(week.to_json()) == week
    assert week.carried() == sb.ServiceBulletin(prelude=sb.Music("Morning Voluntary", ""),
                                                cover_image_id=picture_id.lower(), cover_given=True)
    assert week.map_texts(str.upper).cover_image_id == picture_id.lower()
    none = sb.read({"cover_image_id": None})
    assert (none.cover_image_id, none.cover_given, none.to_json()["cover_image_id"]) == (None, True, None)
    for unsaid in ({}, {"prelude": {"title": "x"}}):
        assert (sb.read(unsaid).cover_given, "cover_image_id" in sb.read(unsaid).to_json()) == (False, False)
    for bad in ("later", 7, "", ["x"]):
        assert (sb.read({"cover_image_id": bad}).cover_image_id, sb.read({"cover_image_id": bad}).cover_given) == (
            None, True)
