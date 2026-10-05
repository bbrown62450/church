"""backend/catena.py: the data files' format, the overlap with a reading, the credit (Voices V1;
spec "The data", "The API").

The format checks run on small invented files; the shipped files are test_catena_data.py's.
"""
import copy
import json
from pathlib import Path

import pytest

import catena
from catena import CatenaDataError

COMMENT = {"label": "Jerome;", "father": "Jerome", "work": None,
           "text": "Lately under Cæsar Augustus, *Then went the Pharisees.*", "notes": []}
CHECKED = {"id": "matthew-22-15-22", "start": [22, 15], "end": [22, 22], "volume": "mt3",
           "pages": [748, 752], "leaves": [19, 23], "status": "checked",
           "checked": {"on": "2026-10-05", "by": "a test"}, "comments": [COMMENT]}
UNCHECKED = {"id": "matthew-22-23-33", "start": [22, 23], "end": [22, 33], "volume": "mt3",
             "pages": [752, 760], "leaves": [23, 31], "status": "unchecked"}


def data(*sections):
    return {"format": 1, "gospel": "Matthew", "sections": [copy.deepcopy(s) for s in sections]}


def test_a_file_reads_as_sections_with_their_comments():
    checked, unchecked = catena.parse(data(CHECKED, UNCHECKED), "Matthew")
    assert checked.reference == "Matthew 22:15-22"
    assert checked.volume.identifier == "catenaurecommpt301thomuoft"
    assert (checked.pages, checked.leaves, checked.checked["on"]) == ((748, 752), (19, 23), "2026-10-05")
    assert checked.comments == (catena.Comment("Jerome;", "Jerome", None, COMMENT["text"], ()),)
    assert (unchecked.reference, unchecked.checked, unchecked.comments) == ("Matthew 22:23-33", None, ())


def breaks(change):
    broken = data(CHECKED, UNCHECKED)
    change(broken)
    with pytest.raises(CatenaDataError):
        catena.parse(broken, "Matthew")


@pytest.mark.parametrize("change", [
    lambda d: d.update(format=2),
    lambda d: d.update(gospel="Mark"),
    lambda d: d["sections"][0].update(id="matthew-22-15-21"),
    lambda d: d["sections"][1].update(id="matthew-22-15-22", start=[22, 15], end=[22, 22]),
    lambda d: d["sections"].reverse(),
    lambda d: d["sections"][0].update(volume="mk"),
    lambda d: d["sections"][0].update(status="draft"),
    lambda d: d["sections"][0].update(checked={"on": "5 Oct", "by": "a test"}),
    lambda d: d["sections"][0].update(comments=[]),
    lambda d: d["sections"][1].update(comments=[COMMENT]),
    lambda d: d["sections"][0]["comments"][0].update(father="Jerome of Stridon"),
    lambda d: d["sections"][0]["comments"][0].update(text=" Lately"),
    lambda d: d["sections"][0]["comments"][0].update(text="Lately\nunder"),
    lambda d: d["sections"][0]["comments"][0].update(text="Lately *under"),
    lambda d: d["sections"][0]["comments"][0].update(work=""),
    lambda d: d["sections"][0]["comments"][0].pop("notes"),
    lambda d: d["sections"][1].update(footnotes=["f Cf. vol. i. 139."]),
    lambda d: d["sections"][1].update(id="matthew-22-23-47", end=[22, 47]),
    lambda d: d["sections"][1].update(id="matthew-22-23-24-2", end=[24, 2]),
    lambda d: d["sections"][1].update(pages=[760, 752]),
    lambda d: d["sections"][1].update(leaves=[31]),
    lambda d: d["sections"][0].update(checked={"on": "2026-10-05", "by": "pastor@example.com"}),
    lambda d: d["sections"][0]["comments"][0].update(notes=[3]),
    lambda d: d["sections"][0]["comments"][0].update(father=None),
], ids=["format", "gospel", "id", "id twice", "order", "volume", "status", "date", "no comments",
        "text unchecked", "father", "spaces", "line break", "italics", "work", "keys", "section keys",
        "verse beyond the chapter", "three chapters", "pages backwards", "leaves", "email", "notes",
        "linking words with a label"])
def test_a_file_that_breaks_the_format_is_refused(change):
    breaks(change)


def test_a_printed_paragraph_and_a_second_section_on_the_same_verses_are_allowed():
    paragraphs = copy.deepcopy(CHECKED)
    paragraphs["comments"][0]["text"] = "First paragraph.\n\nSecond *paragraph*."
    again = dict(copy.deepcopy(UNCHECKED), id="matthew-22-23-33-2")
    sections = catena.parse(data(paragraphs, UNCHECKED, again), "Matthew")
    assert [s.id for s in sections] == ["matthew-22-15-22", "matthew-22-23-33", "matthew-22-23-33-2"]
    assert sections[0].comments[0].text == "First paragraph.\n\nSecond *paragraph*."


def test_the_catenas_own_linking_words_and_a_corrected_label_are_allowed_and_only_fathers_count():
    linked = copy.deepcopy(CHECKED)
    linked["comments"] += [
        {"label": None, "father": None, "work": None, "notes": [],
         "text": "It follows, *On these two commandments hang all the Law and the Prophets.*"},
        dict(COMMENT, label="Pseudo-Jerome;", father="Pseudo-Jerome", printed_label="JEROME"),
    ]
    linked["errata"] = ["Page 25. line 1. for JEROME read PSEUDO-JEROME."]
    (section,) = catena.parse(data(linked), "Matthew")
    link, corrected = section.comments[1:]
    assert (link.father, link.label, link.is_quotation) == (None, None, False)
    assert (corrected.printed_label, corrected.is_quotation) == ("JEROME", True)
    assert (section.quotations, section.errata) == (2, ("Page 25. line 1. for JEROME read PSEUDO-JEROME.",))


def test_a_section_across_chapters_has_both_in_its_id_and_reference():
    across = dict(copy.deepcopy(UNCHECKED), id="matthew-22-46-23-2", start=[22, 46], end=[23, 2])
    (section,) = catena.parse(data(across), "Matthew")
    assert (section.id, section.reference) == ("matthew-22-46-23-2", "Matthew 22:46-23:2")
    assert catena.section_id("Matthew", (22, 46), (23, 2)) == "matthew-22-46-23-2"
    assert catena.section_id("John", (1, 14), (1, 14)) == "john-1-14-14"


@pytest.mark.parametrize("reference, ids", [
    ("Matthew 22:15-22", ["matthew-22-15-22"]),
    ("Matt 22:15-22", ["matthew-22-15-22"]),
    ("Matthew 22:20-25", ["matthew-22-15-22", "matthew-22-23-33"]),
    ("Matthew 22:1-14", []),
    ("Matthew 22", ["matthew-22-15-22", "matthew-22-23-33"]),
    ("Matthew 22:15-16, 30", ["matthew-22-15-22", "matthew-22-23-33"]),
    ("Isaiah 45:1-7", []),
    ("", []),
])
def test_the_sections_that_share_a_verse_with_the_reading(monkeypatch, reference, ids):
    monkeypatch.setattr(catena, "load", lambda gospel: catena.parse(data(CHECKED, UNCHECKED), "Matthew"))
    assert [s.id for s in catena.sections_for(reference)] == ids


def test_the_gospel_and_its_passages_come_from_the_first_gospel_named():
    assert catena.gospel_of("Psalm 96:1-9; Matthew 22:15-22") == "Matthew"
    assert catena.gospel_of("Mark 1:1-8 or Luke 3:1-6") == "Mark"
    assert catena.parse_gospel_reference("Mark 1:1-8 or Luke 3:1-6") == [((1, 1), (1, 8))]
    assert catena.gospel_of("1 John 3:1-3") is None
    assert catena.parse_gospel_reference("Acts 2:1-21") == []
    # Alternatives in one Gospel: the first one's passages only.
    assert catena.parse_gospel_reference("Matthew 26:14-27:66 or Matthew 27:11-54") == [((26, 14), (27, 66))]


@pytest.mark.parametrize("line, passages", [
    ("Luke 2:1-14 (15-20)", [((2, 1), (2, 14)), ((2, 15), (2, 20))]),
    ("Luke 2:(1-7) 8-20", [((2, 1), (2, 7)), ((2, 8), (2, 20))]),
    ("John 1:(1-9) 10-18", [((1, 1), (1, 9)), ((1, 10), (1, 18))]),
    ("Luke 9:28-36 (37-43a)", [((9, 28), (9, 36)), ((9, 37), (9, 43))]),
    ("Mark 15:1-39 (40-47)", [((15, 1), (15, 39)), ((15, 40), (15, 47))]),
])
def test_optional_verses_in_parentheses_are_read_as_part_of_the_reading(line, passages):
    assert catena.parse_gospel_reference(line) == passages
    assert catena.gospel_of(line) == line.split(" ")[0]


def test_the_credit_names_the_edition_the_translator_and_the_copies_scanned():
    (section,) = catena.parse(data(CHECKED), "Matthew")
    assert catena.credit("Matthew", (section,)) == (
        "From the Catena Aurea of Thomas Aquinas, vol. I, St. Matthew, translated by Mark Pattison, "
        "edited by John Henry Newman (Oxford: John Henry Parker, 1841-42). Scanned from the "
        "University of Toronto's copy at archive.org.")
    assert catena.credit("John") == (
        "From the Catena Aurea of Thomas Aquinas, vol. IV, St. John, translator not named in the volume, "
        "edited by John Henry Newman (Oxford: John Henry Parker, 1845). Scanned from the University of "
        "Toronto's copy at archive.org.")
    assert "Whiston" not in "".join(catena.credit(g) for g in catena.GOSPELS)


def test_the_credit_for_matthew_11_to_21_names_saint_marys_copy_with_no_article():
    # The wording the owner approved (Q2, clarification 8): "Saint Mary's College of California's
    # copy", never "the Saint Mary's ..." (Voices V1 build review M1).
    (part_two,) = [s for s in catena.load("Matthew") if s.start == (11, 1)]
    assert catena.credit("Matthew", (part_two,)) == (
        "From the Catena Aurea of Thomas Aquinas, vol. I, St. Matthew, translated by Mark Pattison, "
        "edited by John Henry Newman (Oxford: John Henry Parker, 1841-42). Scanned from Saint Mary's "
        "College of California's copy at archive.org.")
    last_of_part_two = [s for s in catena.load("Matthew") if s.volume.key == "mt2"][-1]
    first_of_part_three = [s for s in catena.load("Matthew") if s.volume.key == "mt3"][0]
    assert catena.credit("Matthew", (last_of_part_two, first_of_part_three)).endswith(
        "Scanned from Saint Mary's College of California's and the University of Toronto's copies at archive.org.")
    assert "the Saint Mary's" not in "".join(catena.credit(g) for g in catena.GOSPELS)


def test_the_scan_addresses():
    volume = catena.volume("mt3")
    assert catena.page_image_url(volume, 19) == "https://archive.org/download/catenaurecommpt301thomuoft/page/n19.jpg"
    assert catena.page_view_url(volume, 19) == "https://archive.org/details/catenaurecommpt301thomuoft/page/n19/mode/1up"


SHARED = json.loads((Path(__file__).parent / "fixtures" / "shared" / "voices_references.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", SHARED["both"], ids=lambda case: case["ref"])
def test_the_server_reads_every_reference_the_panel_asks_for(case):
    # shared/voices_references.json (Voices V1 build review M3): frontend/src/lib/voices.test.ts
    # runs the same cases against gospelOf.
    assert catena.gospel_of(case["ref"]) == case["gospel"]


def test_the_server_refuses_what_the_panel_never_asks_and_reads_what_it_waits_on():
    assert {ref: catena.gospel_of(ref) for ref in SHARED["neither"]} == {ref: None for ref in SHARED["neither"]}
    assert all(catena.gospel_of(ref) is not None for ref in SHARED["client_waits"])
