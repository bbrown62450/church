"""The Affirmation of Faith (affirmation spec, 2026-10-24): the module, and
what the Word files, the printed bulletin (PDF and Word) and the email's
attachments print for each choice, switched off, and for a service from
before the change (no affirmation sent): exactly as today."""
from datetime import date
from io import BytesIO

import pytest
from docx import Document
from docx.shared import Inches
from pypdf import PdfReader

import affirmation as af
import printed_bulletin as pb
import worship_service
from service_output import ResolvedService, render_docx
from usecases import archive, documents
from usecases import email as email_usecase

OWN = "We trust in God the Holy Spirit,\neverywhere the giver and renewer of life."
# Today's two printed lines, written out (printed_bulletin before this change).
TODAY_HEADING = "*AFFIRMATION OF FAITH:  “The Apostles’ Creed”"
TODAY_CREED_START = "I believe in God, the Father almighty, Maker of heaven and earth"


def test_the_creeds_are_the_texts_checked_for_this_change():
    assert af.APOSTLES_CREED.startswith(TODAY_CREED_START)
    assert af.APOSTLES_CREED.endswith("the resurrection of the body; and the life everlasting. Amen.")
    assert "\n" not in af.APOSTLES_CREED and len(af.APOSTLES_CREED) == 611
    lines = af.NICENE_CREED.split("\n")
    assert len(lines) == 32                                    # ELLC's 32 sense lines
    assert lines[0] == "We believe in one God," and lines[-1] == "and the life of the world to come. Amen."
    assert lines[25] == "who proceeds from the Father and the Son,"   # line 26, without ELLC's brackets
    assert "[" not in af.NICENE_CREED and "\u2014" not in af.NICENE_CREED
    assert af.NICENE_CREDIT == ("English translations of the Nicene Creed, © 1998 English Language Liturgical "
                                "Consultation (ELLC), and used by permission. www.englishtexts.org")
    assert pb.APOSTLES_CREED is af.APOSTLES_CREED


@pytest.mark.parametrize("raw, expected", [
    (None, af.Affirmation()),
    ("nicene", af.Affirmation()),
    ({}, af.Affirmation()),
    ({"include": False, "choice": "nicene", "text": "x"}, af.Affirmation(False, "nicene", "")),
    ({"include": "no", "choice": "own", "text": OWN}, af.Affirmation(True, "own", OWN)),
    ({"choice": "brief_statement", "text": OWN}, af.Affirmation(True, "apostles", "")),
    ({"choice": "own", "text": 5}, af.Affirmation(True, "own", "")),
])
def test_read_is_tolerant(raw, expected):
    assert af.read(raw) == expected


def test_to_json_prints_and_the_church_default():
    assert af.Affirmation().to_json() == {"include": True, "choice": "apostles", "text": ""}
    assert af.Affirmation(True, "nicene", "kept?").to_json() == {"include": True, "choice": "nicene", "text": ""}
    assert [a.prints() for a in (af.Affirmation(), af.Affirmation(False), af.Affirmation(True, "own", " \n"),
                                 af.Affirmation(True, "own", OWN))] == [True, False, False, True]
    assert af.resolve_default(None) == af.resolve_default({}) == af.resolve_default("x") == af.Affirmation()
    assert af.resolve_default({"default_affirmation": {"choice": "own", "text": OWN, "include": False}}) == \
        af.Affirmation(True, "own", OWN)


# --- the Word files ---

def _docx(affirmation=None) -> list[str]:
    kwargs = {} if affirmation is None else {"affirmation": affirmation}
    content = worship_service.build_docx(
        occasion="", date_display="October 04, 2026", hymns_by_slot={}, liturgy={}, ot_ref=None, nt_ref=None,
        custom_elements=[{"label": "Anthem", "text": "", "insert_after": "affirmation_of_faith"}], **kwargs)
    return [p.text for p in Document(BytesIO(content)).paragraphs]


def _after_sermon(paragraphs: list[str]) -> list[str]:
    return paragraphs[paragraphs.index("[Sermon title]") + 2:]


def test_the_word_file_for_each_choice():
    today = _after_sermon(_docx())
    assert today[:4] == ["Affirmation of Faith", "Apostles' Creed", "", "Anthem"]
    assert _docx(af.Affirmation()) == _docx()                                   # the default is today's file
    assert _after_sermon(_docx(af.Affirmation(True, "nicene")))[:4] == [
        "Affirmation of Faith", "Nicene Creed", "", "Anthem"]
    assert _after_sermon(_docx(af.Affirmation(True, "own", OWN)))[:4] == ["Affirmation of Faith", OWN, "", "Anthem"]


@pytest.mark.parametrize("off", [af.Affirmation(False, "apostles"), af.Affirmation(False, "own", OWN),
                                 af.Affirmation(True, "own", "  ")])
def test_switched_off_or_blank_own_text_prints_nothing_in_the_word_file(off):
    paragraphs = _docx(off)
    assert "Affirmation of Faith" not in paragraphs and "Apostles' Creed" not in paragraphs
    assert OWN not in paragraphs
    assert _after_sermon(paragraphs)[0] == "Anthem"                              # its custom element still prints


def test_both_word_copies_follow_the_choice():
    resolved = ResolvedService(service_date=date(2026, 10, 4), affirmation=af.Affirmation(False))
    for variant in ("bulletin", "pastor"):
        assert "Affirmation of Faith" not in [p.text for p in Document(BytesIO(render_docx(resolved, variant))).paragraphs]


# --- the printed bulletin ---

def _lines(a=None) -> list[pb.Line]:
    resolved = ResolvedService(service_date=date(2026, 10, 4), **({} if a is None else {"affirmation": a}))
    return pb.order_of_worship(pb.PrintedService(church_name="Grace", resolved=resolved))


def _affirmation_lines(lines: list[pb.Line]) -> list[tuple[str, str]]:
    start = next(i for i, line in enumerate(lines) if line.text.startswith("SERMON:")) + 1
    end = next(i for i, line in enumerate(lines) if "PRAYERS OF THE PEOPLE" in line.text)
    return [(line.style, line.text) for line in lines[start:end]]


def test_the_printed_bulletin_for_each_choice():
    assert _affirmation_lines(_lines()) == [("element", TODAY_HEADING), ("bold", af.APOSTLES_CREED)]
    assert _lines(af.Affirmation()) == _lines()
    # The Nicene Creed: one paragraph per sense line, with a hanging indent (a wrapped line reads as one).
    assert _affirmation_lines(_lines(af.Affirmation(True, "nicene"))) == [
        ("element", "*AFFIRMATION OF FAITH:  “The Nicene Creed”"),
        *[("hanging", sense) for sense in af.NICENE_CREED.split("\n")], ("credit", af.NICENE_CREDIT)]
    assert _affirmation_lines(_lines(af.Affirmation(True, "own", OWN))) == [
        ("element", "*AFFIRMATION OF FAITH:"), ("bold", OWN)]
    creed = [line for line in _lines(af.Affirmation(True, "nicene")) if line.style == "hanging"]
    assert len(creed) == 32 and all(span.bold for line in creed for span in line.spans)


def test_switched_off_prints_nothing_in_the_printed_bulletin_and_loses_its_star():
    for off in (af.Affirmation(False), af.Affirmation(True, "own", "")):
        assert _affirmation_lines(_lines(off)) == []
    on = pb.order_of_worship(pb.PrintedService(church_name="Grace", resolved=ResolvedService(
        service_date=date(2026, 10, 4)), settings=pb.BulletinSettings(starred=frozenset({"affirmation_of_faith"}),
                                                                       stand_note="Please stand.")))
    off = pb.order_of_worship(pb.PrintedService(church_name="Grace", resolved=ResolvedService(
        service_date=date(2026, 10, 4), affirmation=af.Affirmation(False)),
        settings=pb.BulletinSettings(starred=frozenset({"affirmation_of_faith"}), stand_note="Please stand.")))
    assert on[-1].text == "*Please stand." and all("Please stand." not in line.text for line in off)


# --- the files as the routes and the email build them ---

@pytest.fixture
def church(make_user, make_church):
    return make_church(name="Grace", owner_user_id=make_user(email="pastor@example.com"))


def _input(a=None) -> archive.ServiceInput:
    return archive.ServiceInput(service_date=date(2026, 10, 4), affirmation=a)


def _pdf_text(content: bytes) -> str:
    return " ".join(" ".join(page.extract_text().split()) for page in PdfReader(BytesIO(content)).pages)


def _docx_text(content: bytes) -> str:
    return "\n".join(p.text for p in Document(BytesIO(content)).paragraphs)


def _printed(church, a, fmt):
    return documents.build_printed(church, _input(a), fmt, None, charge=lambda n: None).content


def test_the_downloads_for_each_choice(church):
    assert "Apostles' Creed" in _docx_text(documents.build_document(church, _input(), "bulletin").content)
    nicene = _pdf_text(_printed(church, af.Affirmation(True, "nicene"), "pdf"))
    assert "AFFIRMATION OF FAITH: “The Nicene Creed” We believe in one God," in nicene
    assert "Consultation (ELLC), and used by permission." in nicene
    own = _docx_text(_printed(church, af.Affirmation(True, "own", OWN), "docx"))
    assert OWN in own
    today = _pdf_text(_printed(church, None, "pdf"))
    assert "AFFIRMATION OF FAITH: “The Apostles’ Creed” I believe in God" in today


def test_the_printed_word_file_gives_each_nicene_sense_line_a_hanging_indent(church):
    paragraphs = Document(BytesIO(_printed(church, af.Affirmation(True, "nicene"), "docx"))).paragraphs
    first = next(p for p in paragraphs if p.text == "We believe in one God,")
    last = next(p for p in paragraphs if p.text == "and the life of the world to come. Amen.")
    for p in (first, last):
        fmt = p.paragraph_format
        assert (fmt.left_indent, fmt.first_line_indent) == (Inches(0.5), Inches(-0.5))
        assert all(run.bold for run in p.runs)


def test_switched_off_prints_nothing_in_any_download_or_the_email(church):
    off = af.Affirmation(False, "nicene")
    assert "Affirmation of Faith" not in _docx_text(documents.build_document(church, _input(off), "pastor").content)
    assert "AFFIRMATION OF FAITH" not in _pdf_text(_printed(church, off, "pdf"))
    assert "AFFIRMATION OF FAITH" not in _docx_text(_printed(church, off, "docx"))
    files = email_usecase._attachments(church, _input(off), ["docx", "pdf"], None, lambda n: None)
    assert [f.filename for f in files] == ["worship_October_04_2026.docx", "printed_bulletin_October_04_2026.pdf"]
    assert "Affirmation of Faith" not in _docx_text(files[0].content)
    assert "AFFIRMATION OF FAITH" not in _pdf_text(files[1].content) and "We believe" not in _pdf_text(files[1].content)


def test_own_text_is_made_word_safe_and_trimmed(church):
    clean = archive.clean_input(_input(af.Affirmation(True, "own", "  Line one\r\nLine\x00 two  ")))
    assert clean.affirmation == af.Affirmation(True, "own", "Line one\nLine two")
    assert archive.clean_input(_input()).affirmation is None
