"""The printed bulletin's content (printed bulletin spec, PR 1;
printed_bulletin.py), with the church's bulletin settings (PR 2a)."""
import dataclasses
import datetime

import bulletin_settings as bs
import printed_bulletin as pb
from liturgy_config import ASSURANCE_RESPONSE, DEFAULT_BENEDICTION_FALLBACK
from service_output import CustomElement, ResolvedHymn, ResolvedService

SUNDAY = datetime.date(2026, 10, 4)
# Invented details: a church's settings with every standing field filled in.
SETTINGS = bs.BulletinSettings(
    address_lines=("100 Example Street", "Springfield, ST 00000"), phone="(555) 010-0100",
    email="office@example.com", website="example.com", facebook="Example Church", service_time="10:30 a.m.",
    worship_leader="Rev. Alex Example", liturgist="Sam Sample", organist="Jordan Doe")


def service(**changes) -> pb.PrintedService:
    resolved = ResolvedService(
        service_date=SUNDAY, occasion="World Communion Sunday", scriptures=("Psalm 80:7-15", "Matthew 21:33-46"),
        hymns={"opening": ResolvedHymn("God Is Here!", 409), "response": ResolvedHymn("Ride On", None),
               "closing": ResolvedHymn("Jesus Shall Reign", 265)},
        liturgy={"call_to_worship": "Leader: Lift up your hearts. People: We lift them up.",
                 "opening_prayer": "God of wisdom, hear us.", "prayer_of_confession": "Merciful God, forgive us.",
                 "assurance": "Leader: In Christ we are forgiven. People: Thanks be to God!",
                 "prayer_for_illumination": "Open our hearts.", "prayers_of_the_people": "We pray for all.",
                 "offertory_prayer": "Bless these gifts.", "benediction": DEFAULT_BENEDICTION_FALLBACK},
        sermon_title="Who Said?",
        custom_elements=(CustomElement("Anthem", "Chancel Choir", "sermon"), CustomElement("Ending", "", "end")))
    base = dict(church_name="Example Church", resolved=resolved,
                ot=pb.Reading("Psalm 80:7-15", "Turn us again, God.\nCause your face to shine.\n\nWe will be saved."),
                nt=pb.Reading("Matthew 21:33-46", None), translation_label="World English Bible (WEB)",
                settings=SETTINGS)
    base.update(changes)
    return pb.PrintedService(**base)


def texts(lines: list[pb.Line]) -> list[str]:
    return [line.text for line in lines]


def test_the_date_and_the_filenames():
    assert pb.printed_date(SUNDAY) == "October 4, 2026"
    assert pb.printed_date(datetime.date(2026, 9, 27)) == "September 27, 2026"
    assert pb.printed_filename("pdf", SUNDAY) == "printed_bulletin_October_04_2026.pdf"
    assert pb.printed_filename("docx", SUNDAY) == "printed_bulletin_October_04_2026.docx"


def test_a_reading_prints_as_paragraphs():
    assert pb.reading_paragraphs("Turn us again.\n Cause your face\n\tto shine.\n\n\nWe will be saved.\n") == [
        "Turn us again. Cause your face to shine.", "We will be saved."]
    assert pb.reading_paragraphs("  \n\n ") == []


def test_the_order_of_worship_follows_the_outline_with_the_sample_s_parts():
    lines = pb.order_of_worship(service())
    elements = [line.spans[0].text for line in lines if line.style in ("element", "section")]
    assert elements == [
        "October 4, 2026", "GATHERING FOR WORSHIP", "PRELUDE:", "WELCOME AND ANNOUNCEMENTS", "CALL TO WORSHIP",
        "OPENING PRAYER", "*HYMN:", "PRAYER OF CONFESSION", "ASSURANCE OF PARDON", "*SUNG RESPONSE:",
        "PRAYER FOR ILLUMINATION", "RECEIVING THE WORD", "FIRST READING:", "NEW TESTAMENT READING:", "SERMON:",
        "ANTHEM", "*AFFIRMATION OF FAITH:", "*HYMN:", "PRAYERS OF THE PEOPLE/THE LORD’S PRAYER",
        "RESPONDING TO THE WORD", "OFFERING OUR GIFTS", "*SUNG RESPONSE:", "OFFERTORY PRAYER",
        "SENDING OUT TO SERVE", "*HYMN:", "*BENEDICTION", "POSTLUDE:", "ENDING"]
    assert texts(lines[:5]) == ["THE SERVICE FOR THE LORD’S DAY", "Example Church",
                                "Rev. Alex Example, Worship Leader", "Sam Sample, Liturgist", "Jordan Doe, Organist"]
    assert lines[5].right == "10:30 a.m."
    assert lines[-1] == pb.Line("note", (pb.Span("*Congregation stands if able"),))


def test_each_element_prints_as_the_sample():
    lines = pb.order_of_worship(service())
    by_text = {line.text: line for line in lines}
    assert by_text["*HYMN:  #409  “God Is Here!”"].right == ""
    assert "*HYMN:  “Ride On”" in by_text                      # no number, no "#None"
    assert by_text["CALL TO WORSHIP"].right == "Sam Sample"
    assert by_text["NEW TESTAMENT READING:  Matthew 21:33-46"].right == "Rev. Alex Example"
    assert by_text["PRELUDE:  ‘[Prelude title]’"].right == "Jordan Doe"
    assert by_text["SERMON:  “Who Said?”"].right == "Rev. Alex Example"
    leader, people = by_text["Leader: Lift up your hearts."], by_text["People: We lift them up."]
    assert (leader.style, [s.bold for s in leader.spans]) == ("hanging", [False, False])
    assert (people.style, [s.bold for s in people.spans]) == ("hanging", [True, True])
    assert by_text["Merciful God, forgive us."].spans[0].bold
    i = texts(lines).index("ASSURANCE OF PARDON")
    assert texts(lines[i + 1:i + 3]) == ["Leader: In Christ we are forgiven.", ASSURANCE_RESPONSE]
    i = texts(lines).index("FIRST READING:  Psalm 80:7-15")
    assert texts(lines[i + 1:i + 3]) == ["Turn us again, God. Cause your face to shine.", "We will be saved."]
    i = texts(lines).index("NEW TESTAMENT READING:  Matthew 21:33-46")
    assert texts(lines[i + 1:i + 3]) == ["[Reading text unavailable]",
                                         "Scripture readings are from the World English Bible (WEB)."]
    assert pb.APOSTLES_CREED in by_text and pb.GLORIA_PATRI in by_text and DEFAULT_BENEDICTION_FALLBACK in by_text
    assert "We pray for all." not in by_text                            # the prayers are the pastor's to pray
    assert "ANTHEM" in by_text and "Chancel Choir" in by_text and "ENDING" in by_text


def test_what_is_missing_is_left_out_or_a_placeholder():
    sparse = pb.PrintedService(church_name="Example Church", resolved=ResolvedService(
        service_date=SUNDAY, hymns={"opening": None, "response": None, "closing": None}),
        ot=None, nt=None, translation_label="World English Bible (WEB)")
    lines = texts(pb.order_of_worship(sparse))
    assert not any(line.startswith(("*HYMN", "FIRST READING", "NEW TESTAMENT", "CALL TO WORSHIP", "*BENEDICTION",
                                    "Scripture readings")) for line in lines)
    assert "SERMON:  “[Sermon title]”" in lines


def test_communion_prints_after_the_second_hymn():
    resolved = service().resolved
    with_communion = service(resolved=ResolvedService(**{**resolved.__dict__, "include_communion": True}))
    lines = texts(pb.order_of_worship(with_communion))
    second = lines.index("*HYMN:  “Ride On”")
    prayers = lines.index("PRAYERS OF THE PEOPLE/THE LORD’S PRAYER")
    assert "The Sacrament of the Lord's Supper" in lines[second + 1:prayers]
    assert "The Sacrament of the Lord's Supper" not in texts(pb.order_of_worship(service()))


def test_the_cover_and_the_back_page():
    assert texts(pb.cover(service())) == [
        "Example Church", "[Cover picture]", "Matthew 21:33-46", "October 4, 2026", "100 Example Street",
        "Springfield, ST 00000", "(555) 010-0100", "office@example.com", "example.com", "FB: Example Church"]
    assert texts(pb.cover(service(nt=None)))[2] == "Psalm 80:7-15"
    assert texts(pb.announcements(service())) == [
        "ANNOUNCEMENTS", "October 4, 2026", "Ushers/Counters: [Names]", "Deacon of the Week: [Name]",
        "Coffee Hour: [Name]", "THIS WEEK’S ACTIVITIES AT A GLANCE", "[Activities]", "PRAYERS AND CONCERNS",
        "[Prayer concerns]", "ITEMS FOR COLLECTION", "[Collection items]"]


def test_a_blank_setting_prints_nothing():
    lines = pb.order_of_worship(service(settings=bs.BulletinSettings()))       # nothing saved yet
    assert texts(lines[:3]) == ["THE SERVICE FOR THE LORD’S DAY", "Example Church", "October 4, 2026"]
    assert lines[2].right == ""
    assert all(line.right == "" for line in lines)                          # roles, but no names
    assert texts(pb.cover(service(settings=bs.BulletinSettings(phone="(555) 010-0100", facebook="Example Church")))
                 )[4:] == ["(555) 010-0100", "FB: Example Church"]
    assert texts(pb.cover(service(settings=bs.BulletinSettings())))[4:] == []
    bare = texts(pb.order_of_worship(service(settings=bs.BulletinSettings(
        stand_note="", gloria_patri_words="", starred=frozenset(), leaders={}))))
    i = bare.index("SUNG RESPONSE:  “Gloria Patri”")
    assert bare[i + 1] == "PRAYER FOR ILLUMINATION"                         # no words under it
    assert not any(line.startswith("*") for line in bare)                   # no stars, no stand note
    assert bare[-1] == "ENDING"
    unstarred = texts(pb.order_of_worship(service(ot=None, settings=bs.BulletinSettings(
        starred=frozenset({"ot_reading"})))))                               # starred, but not printed this week
    assert unstarred[-1] == "ENDING" and not any(line.startswith("*") for line in unstarred)


def test_the_settings_choose_the_stars_the_leaders_and_the_words():
    settings = bs.BulletinSettings(organist="Jordan Doe", starred=frozenset({"prelude", "sermon"}),
                                   leaders={"sermon": "organist", "welcome": "liturgist"},
                                   stand_note="Please stand if able", gloria_patri_words="Glory be.")
    lines = pb.order_of_worship(service(settings=settings))
    by_text = {line.text: line for line in lines}
    assert by_text["*PRELUDE:  ‘[Prelude title]’"].right == ""               # starred; no role now
    assert by_text["*SERMON:  “Who Said?”"].right == "Jordan Doe"
    assert by_text["WELCOME AND ANNOUNCEMENTS"].right == ""                 # a role with no name
    assert "HYMN:  #409  “God Is Here!”" in by_text and "Glory be." in by_text
    assert lines[-1] == pb.Line("note", (pb.Span("*Please stand if able"),))


def test_a_custom_element_marked_by_hand_does_not_bring_the_stand_note():
    """Build review M2: the stand note follows only an element the settings star, not a custom element whose
    label starts with "*" (a church marking standing by hand)."""
    marked = service(resolved=dataclasses.replace(service().resolved, custom_elements=(
        CustomElement("*Anthem", "Chancel Choir", "sermon"),)), settings=bs.BulletinSettings(starred=frozenset()))
    lines = texts(pb.order_of_worship(marked))
    assert "*ANTHEM" in lines and "*Congregation stands if able" not in lines
    starred = service(resolved=marked.resolved, settings=bs.BulletinSettings(starred=frozenset({"sermon"})))
    assert texts(pb.order_of_worship(starred))[-1] == "*Congregation stands if able"
