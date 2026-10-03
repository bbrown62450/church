"""The printed bulletin's content (printed bulletin spec, PR 1): what the
bulletin prints, page by page, as plain data that printed_pdf and
printed_docx both render. Pure: no database, FastAPI, reportlab or
python-docx here.

- PrintedService: a service ready to print (the resolved service, the
  church's name, the readings with their text and the translation's label).
- cover, order_of_worship, announcements: the three parts of the booklet as
  Lines (one printed paragraph each). The order of worship follows
  liturgy_config.OUTLINE (the Word copies' order) with the parts the owner's
  sample bulletin adds (Prelude, Welcome and Announcements, the sung
  responses, the Offering, the Postlude) and its four section headings.
- The standing details (the church's contact lines, the people who lead and
  what each leads, the service time, the stars, the stand note and the Gloria
  Patri words) come from the church's bulletin settings (PR 2a,
  bulletin_settings); a blank one prints nothing (PR 2 planning answer 3).
  The weekly fields (the music, the announcements, the cover picture) print
  as [bracketed placeholders] until PR 2b's Bulletin step and PR 3 fill them.
- printed_date, printed_filename, PDF_MIME.
"""
from __future__ import annotations

import datetime
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, Optional

from bulletin_settings import GLORIA_PATRI, BulletinSettings
from liturgy_config import ASSURANCE_RESPONSE, COMMUNION_BLOCKS
from service_output import MONTHS, ResolvedHymn, ResolvedService, safe_date, service_date_display

PDF_MIME = "application/pdf"
Format = Literal["pdf", "docx"]

# One booklet page: half a legal sheet (14 x 8.5 in, landscape), 7 x 8.5 in.
PAGE_WIDTH = 504.0          # points
PAGE_HEIGHT = 612.0

# The weekly fields' placeholders, until PR 2b's Bulletin step and PR 3 fill them.
PRELUDE = ("[Prelude title]", "[Composer]")
POSTLUDE = ("[Postlude title]", "[Composer]")
COVER_PICTURE = "[Cover picture]"
TEXT_UNAVAILABLE = "[Reading text unavailable]"

# The header's people, as "{name}, Worship Leader" (bulletin_settings.ROLES order).
ROLE_TITLES = {"worship_leader": "Worship Leader", "liturgist": "Liturgist", "organist": "Organist"}

APOSTLES_CREED = (
    "I believe in God, the Father almighty, Maker of heaven and earth, and in Jesus Christ his only "
    "Son, our Lord; who was conceived by the Holy Ghost, born of the Virgin Mary, suffered under "
    "Pontius Pilate, was crucified, dead, and buried; he descended into hell; the third day he rose "
    "again from the dead; he ascended into heaven, and sitteth on the right hand of God the Father "
    "Almighty; from thence he shall come to judge the quick and the dead. I believe in the Holy "
    "Ghost; the holy catholic church; the communion of saints; the forgiveness of sins; the "
    "resurrection of the body; and the life everlasting. Amen.")

Style = Literal["header", "element", "section", "body", "bold", "hanging", "indent", "note", "credit",
                "title", "box", "contact", "center"]


@dataclass(frozen=True)
class Span:
    text: str
    bold: bool = False
    italic: bool = False


@dataclass(frozen=True)
class Line:
    """One printed paragraph. `right` prints right-aligned on the same line
    (an element's leader, or the service time)."""
    style: Style
    spans: tuple[Span, ...]
    right: str = ""

    @property
    def text(self) -> str:
        return "".join(span.text for span in self.spans)


@dataclass(frozen=True)
class Reading:
    reference: str
    text: Optional[str]            # None: the text could not be fetched (TEXT_UNAVAILABLE prints)


@dataclass(frozen=True)
class PrintedService:
    church_name: str
    resolved: ResolvedService
    ot: Optional[Reading] = None
    nt: Optional[Reading] = None
    translation_label: str = ""
    settings: BulletinSettings = BulletinSettings()      # the church's standing settings (PR 2a)


def printed_date(d: datetime.date) -> str:
    """"October 4, 2026": the owner's bulletin writes the day without a leading zero."""
    return f"{MONTHS[d.month - 1]} {d.day}, {d.year}"


def printed_filename(fmt: Format, d: datetime.date) -> str:
    """printed_bulletin_October_04_2026.pdf (or .docx), the Word copies' date form."""
    return f"printed_bulletin_{safe_date(service_date_display(d))}.{fmt}"


# --- text helpers ---

_PEOPLE_LEADER = re.compile(r"\b(Leader|People):\s*", re.IGNORECASE)
_ASSURANCE_PEOPLE = re.compile(r"(?:^|(?<=\s))People:", re.IGNORECASE | re.MULTILINE)


def reading_paragraphs(text: str) -> list[str]:
    """A passage as printed paragraphs: a blank line starts a new paragraph;
    the verse line breaks inside one become spaces."""
    paragraphs = [" ".join(chunk.split()) for chunk in re.split(r"\n\s*\n", text)]
    return [p for p in paragraphs if p]


def _leader_people(text: str) -> list[Line]:
    """worship_service._add_leader_people_paragraph's reading: Leader lines in
    normal type, People lines in bold, each with a hanging indent."""
    matches = list(_PEOPLE_LEADER.finditer(text))
    if not matches:
        return [Line("body", (Span(text),))]
    lines = []
    if matches[0].start() > 0 and text[:matches[0].start()].strip():
        lines.append(Line("body", (Span(text[:matches[0].start()].strip()),)))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[m.end():end].strip()
        if m.group(1).lower() == "people":
            lines.append(Line("hanging", (Span("People: ", bold=True), Span(content, bold=True))))
        else:
            lines.append(Line("hanging", (Span("Leader: "), Span(content))))
    return lines


def _assurance(text: str) -> list[Line]:
    """worship_service._add_assurance_paragraph's reading: the text up to a
    typed "People:" label, then ASSURANCE_RESPONSE in bold, once."""
    leader = text.strip()
    people = _ASSURANCE_PEOPLE.search(leader)
    if people:
        leader = leader[: people.start()].strip()
    if leader.startswith("Leader:"):
        leader = leader[7:].strip()
    lines = [Line("hanging", (Span("Leader: "), Span(leader)))] if leader else []
    return [*lines, Line("bold", (Span(ASSURANCE_RESPONSE, bold=True),))]


def _element(s: BulletinSettings, key: str, label: str, *value: Span) -> Line:
    """An element's heading: the label in capitals and bold (with the stand
    star when the settings star it), then its value, and the leader's name
    right-aligned (none when the element has no role or the role no name)."""
    star = "*" if key in s.starred else ""
    return Line("element", (Span(f"{star}{label.upper()}", bold=True), *value), right=s.leader(key))


def _quoted(text: str) -> Span:
    return Span(f"“{text}”", bold=True, italic=True)


def _hymn(s: BulletinSettings, key: str, hymn: Optional[ResolvedHymn]) -> list[Line]:
    """*HYMN: #409 "God Is Here!"; an empty slot prints nothing (as the Word copies)."""
    if hymn is None or not hymn.title.strip():
        return []
    number = [] if hymn.number is None else [Span(f"#{hymn.number}  ", bold=True)]
    return [_element(s, key, "Hymn:", Span("  "), *number, _quoted(hymn.title))]


def _text_element(s: BulletinSettings, key: str, label: str, text: str, style: Style = "body") -> list[Line]:
    if not text:
        return []
    return [_element(s, key, label), Line(style, (Span(text, bold=style == "bold"),))]


def _custom(s: BulletinSettings, anchor: str, resolved: ResolvedService) -> list[Line]:
    lines = []
    for element in resolved.custom_elements:
        if element.insert_after == anchor and element.label:
            lines.append(_element(s, "", element.label))
            if element.text:
                lines.append(Line("body", (Span(element.text),)))
    return lines


def _reading(s: BulletinSettings, key: str, label: str, reading: Optional[Reading]) -> list[Line]:
    if reading is None:
        return []
    lines = [_element(s, key, f"{label}:", Span(f"  {reading.reference}", bold=True))]
    if reading.text is None:
        return [*lines, Line("body", (Span(TEXT_UNAVAILABLE),))]
    return [*lines, *(Line("body", (Span(p),)) for p in reading_paragraphs(reading.text))]


def _communion(s: BulletinSettings) -> list[Line]:
    """liturgy_config.COMMUNION_BLOCKS, as the Word copies print them."""
    lines = []
    for block in COMMUNION_BLOCKS:
        if block.style == "heading1":
            lines.append(Line("section", (Span(block.text, bold=True, italic=True),)))
        elif block.style == "heading2":
            lines.append(_element(s, "", block.text))
        elif block.style == "response":
            lines.append(Line("bold", (Span(block.text, bold=True),)))
        elif block.style == "text":
            lines.append(Line("body", (Span(block.text),)))
    return lines


def _section(title: str) -> Line:
    return Line("section", (Span(title, bold=True, italic=True),))


def _music(s: BulletinSettings, key: str, label: str, piece: tuple[str, str]) -> list[Line]:
    title, composer = piece
    return [_element(s, key, f"{label}:", Span("  "), Span(f"‘{title}’", bold=True, italic=True)),
            Line("indent", (Span(f"- {composer}"),))]


def _header(ps: PrintedService) -> list[Line]:
    """"THE SERVICE FOR THE LORD'S DAY", the church, each person with a name
    ("{name}, Worship Leader"), and the date with the service time across."""
    s = ps.settings
    people = [Line("header", (Span(f"{getattr(s, role)}, {title}", bold=True),))
              for role, title in ROLE_TITLES.items() if getattr(s, role)]
    return [
        Line("header", (Span("THE SERVICE FOR THE LORD’S DAY", bold=True),)),
        Line("header", (Span(ps.church_name, bold=True),)),
        *people,
        Line("element", (Span(printed_date(ps.resolved.service_date), bold=True),), right=s.service_time),
    ]


def order_of_worship(ps: PrintedService) -> list[Line]:
    """The inside pages: the service header, then the elements in OUTLINE
    order with the sample's additions, each custom element after its anchor."""
    r = ps.resolved
    s = ps.settings
    lit: Mapping[str, str] = r.liturgy
    hymns = r.hymns
    sermon = r.sermon_title.strip() or "[Sermon title]"
    lines: list[Line] = [
        *_header(ps),
        _section("GATHERING FOR WORSHIP"),
        *_music(s, "prelude", "Prelude", PRELUDE),
        _element(s, "welcome", "Welcome and Announcements"),
    ]
    if lit.get("call_to_worship"):
        lines += [_element(s, "call_to_worship", "Call to Worship"), *_leader_people(lit["call_to_worship"])]
    lines += _custom(s, "call_to_worship", r)
    lines += _text_element(s, "opening_prayer", "Opening Prayer", lit.get("opening_prayer", ""))
    lines += _custom(s, "opening_prayer", r)
    lines += _hymn(s, "first_hymn", hymns.get("opening"))
    lines += _custom(s, "first_hymn", r)
    lines += _text_element(s, "prayer_of_confession", "Prayer of Confession", lit.get("prayer_of_confession", ""),
                           "bold")
    lines += _custom(s, "prayer_of_confession", r)
    if lit.get("assurance"):
        lines += [_element(s, "assurance", "Assurance of Pardon"), *_assurance(lit["assurance"])]
    lines += _custom(s, "assurance", r)
    lines.append(_element(s, "gloria_patri", "Sung Response:", Span("  "), _quoted("Gloria Patri")))
    if s.gloria_patri_words:
        lines.append(Line("bold", (Span(s.gloria_patri_words, bold=True, italic=True),)))
    lines += _text_element(s, "prayer_for_illumination", "Prayer for Illumination",
                           lit.get("prayer_for_illumination", ""))
    lines += _custom(s, "prayer_for_illumination", r)
    lines.append(_section("RECEIVING THE WORD"))
    lines += _reading(s, "ot_reading", "First Reading", ps.ot)
    lines += _custom(s, "ot_reading", r)
    lines += _reading(s, "nt_reading", "New Testament Reading", ps.nt)
    if (ps.ot or ps.nt) and ps.translation_label:
        lines.append(Line("credit", (Span(f"Scripture readings are from the {ps.translation_label}.", italic=True),)))
    lines += _custom(s, "nt_reading", r)
    lines.append(_element(s, "sermon", "Sermon:", Span("  "), _quoted(sermon)))
    lines += _custom(s, "sermon", r)
    lines += [_element(s, "affirmation_of_faith", "Affirmation of Faith:", Span("  "),
                       Span("“The Apostles’ Creed”", bold=True)),
              Line("bold", (Span(APOSTLES_CREED, bold=True),))]
    lines += _custom(s, "affirmation_of_faith", r)
    lines += _hymn(s, "second_hymn", hymns.get("response"))
    lines += _custom(s, "second_hymn", r)
    if r.include_communion:
        lines += _communion(s)
    lines += _custom(s, "communion", r)
    lines.append(_element(s, "prayers_of_the_people", "Prayers of the People/The Lord’s Prayer"))
    lines += _custom(s, "prayers_of_the_people", r)
    lines += [_section("RESPONDING TO THE WORD"),
              _element(s, "offering", "Offering Our Gifts"),
              _element(s, "doxology", "Sung Response:", Span("  "), _quoted("Doxology"))]
    lines += _text_element(s, "offertory_prayer", "Offertory Prayer", lit.get("offertory_prayer", ""))
    lines += _custom(s, "offertory_prayer", r)
    lines.append(_section("SENDING OUT TO SERVE"))
    lines += _hymn(s, "third_hymn", hymns.get("closing"))
    lines += _custom(s, "third_hymn", r)
    lines += _custom(s, "benediction", r)
    lines += _text_element(s, "benediction", "Benediction", lit.get("benediction", ""))
    lines += _music(s, "postlude", "Postlude", POSTLUDE)
    lines += _custom(s, "end", r)
    if s.stand_note and any(line.style == "element" and line.text.startswith("*") for line in lines):
        lines.append(Line("note", (Span(f"*{s.stand_note}"),)))       # only under a star that printed
    return lines


def contact_lines(s: BulletinSettings) -> list[str]:
    """The cover's contact lines from the settings, the blank ones left out:
    the address lines, the phone, the email, the website, "FB: {name}"."""
    facebook = [f"FB: {s.facebook}"] if s.facebook else []
    return [*s.address_lines, *(text for text in (s.phone, s.email, s.website) if text), *facebook]


def cover(ps: PrintedService) -> list[Line]:
    """The front page: the church's name, the picture's place with the
    sermon reading and the date over it, and the church's contact lines."""
    reading = ps.nt or ps.ot
    return [
        Line("title", (Span(ps.church_name, bold=True),)),
        Line("box", (Span(COVER_PICTURE),)),
        Line("box", (Span(reading.reference if reading else ""),)),
        Line("box", (Span(printed_date(ps.resolved.service_date)),)),
        *(Line("contact", (Span(text),)) for text in contact_lines(ps.settings)),
    ]


def announcements(ps: PrintedService) -> list[Line]:
    """The back page: PR 2's announcements form, as placeholders for now."""
    return [
        Line("header", (Span("ANNOUNCEMENTS", bold=True),)),
        Line("header", (Span(printed_date(ps.resolved.service_date), bold=True),)),
        Line("center", (Span("Ushers/Counters: ", bold=True), Span("[Names]"))),
        Line("center", (Span("Deacon of the Week: ", bold=True), Span("[Name]"))),
        Line("center", (Span("Coffee Hour: ", bold=True), Span("[Name]"))),
        _section("THIS WEEK’S ACTIVITIES AT A GLANCE"),
        Line("center", (Span("[Activities]"),)),
        _section("PRAYERS AND CONCERNS"),
        Line("center", (Span("[Prayer concerns]"),)),
        _section("ITEMS FOR COLLECTION"),
        Line("center", (Span("[Collection items]"),)),
    ]
