"""The Catena's data files as shipped (backend/data/catena/; Voices V1 spec "The data").

Every file loads and passes the format checks, holds every section the import tool found, and
holds text only for the sections checked against the page images (the V1 plan's check record).
Each checked section's text is pinned by a hash (Voices V1 build review I2), so a later `index`
run, a find-and-replace or an editor's auto-format cannot change one character of it unnoticed.
A newly checked (or re-checked) section changes CHECKED here, its hash included, in the same commit.
"""
import hashlib
import json
import re
import shutil
from pathlib import Path

import pytest

import catena
import vanderbilt_lectionary

SECTIONS = {"Matthew": 277, "Mark": 104, "Luke": 245, "John": 190}
# Each checked section's id and the sha256 of its text (text_hash: its comments and errata).
CHECKED = {
    "Matthew": {
        "matthew-22-15-22": "aaef04e79b53ddf4bbef8329843784e8db40003f9a86e5e3c54942c4299c0250",
        "matthew-22-34-40": "ffd0027e5bdcd69dcd03587ec727c2dd317e2174d8f8e4f850cc00db2d293b8e",
        "matthew-22-41-46": "47851e05f919dbd860cd589909c1c86a9dfa2aa05097651612b4ea87b6d0d030",
        "matthew-23-1-4": "0689776e0ffeda49518517156b608066565b433260a8dc45efdf68dc096d4f3a",
        "matthew-23-5-12": "67a352121425973b5f737f86ea0af69e87e505eb9a9d58bafbbb498c8486dfef",
    },
    "Mark": {},
    "Luke": {},
    "John": {},
}
# The quotations of each checked section (the V1 plan's check record).
QUOTATIONS = {"matthew-22-15-22": 19, "matthew-22-34-40": 23, "matthew-22-41-46": 13, "matthew-23-1-4": 11,
              "matthew-23-5-12": 26}


@pytest.mark.parametrize("gospel", catena.GOSPELS)
def test_every_file_loads_with_every_section_and_text_only_where_checked(gospel):
    sections = catena.load(gospel)
    assert len(sections) == SECTIONS[gospel]
    assert [s.id for s in sections if s.checked] == list(CHECKED[gospel])
    assert {s.id: s.quotations for s in sections if s.checked} == {i: QUOTATIONS[i] for i in CHECKED[gospel]}
    assert not any(s.comments for s in sections if not s.checked)
    assert {s.volume.gospel for s in sections} == {gospel}


@pytest.mark.parametrize("gospel", catena.GOSPELS)
def test_every_verse_has_a_section_and_the_pages_follow_the_leaves(gospel):
    sections = catena.load(gospel)
    verses = catena.VERSES[gospel]
    covered = set()
    for s in sections:
        assert s.end[0] - s.start[0] <= 1, s.id                     # never more than two chapters
        for chapter in range(s.start[0], s.end[0] + 1):
            first = s.start[1] if chapter == s.start[0] else 1
            last = s.end[1] if chapter == s.end[0] else verses[chapter - 1]
            covered |= {(chapter, v) for v in range(first, last + 1)}
    # Every chapter, every verse, and no verse past its chapter's end.
    assert covered == {(c, v) for c, n in enumerate(verses, start=1) for v in range(1, n + 1)}
    for volume in {s.volume for s in sections}:
        mine = [s for s in sections if s.volume == volume]
        # One distance from scan leaf to printed page in each volume: a misread page number shows.
        assert len({s.leaves[0] - s.pages[0] for s in mine} | {s.leaves[1] - s.pages[1] for s in mine}) == 1, volume
        # The leaves run on with the verses, except where the Catena prints the verses in another
        # order: the Beatitudes in the Vulgate's, 5:5 before 5:4.
        back = [(a.id, b.id) for a, b in zip(mine, mine[1:]) if b.leaves[0] < a.leaves[0]]
        assert back == ([("matthew-5-4-4", "matthew-5-5-5")] if volume.key == "mt1" else []), volume


@pytest.mark.parametrize("gospel", catena.GOSPELS)
def test_the_file_is_one_section_a_line_and_one_checked_comment_a_line(gospel):
    text = catena.data_path(gospel).read_text(encoding="utf-8")
    lines = text.splitlines()
    assert lines[0] == f'{{"format": 1, "gospel": "{gospel}", "sections": ['
    assert lines[-1] == "]}" and text.endswith("]}\n")
    raw = json.loads(text)
    keys = catena.SECTION_KEYS | catena.CHECKED_KEYS | catena.OPTIONAL_CHECKED_KEYS
    assert all(set(s) <= keys for s in raw["sections"])            # never a draft's footnotes or warnings
    checked_comments = sum(len(s.get("comments", [])) for s in raw["sections"])
    assert len(lines) == 2 + len(raw["sections"]) + checked_comments + len(CHECKED[gospel])


def text_hash(section: dict) -> str:
    """The sha256 of a checked section's text as the file holds it: its comments (every key of each,
    in order) and its errata, serialized one canonical way (sorted keys, no spaces, UTF-8)."""
    text = {"comments": section["comments"], "errata": section.get("errata", [])}
    canonical = json.dumps(text, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def changed_since_checked(gospel: str) -> list[str]:
    """The checked sections whose text no longer has the hash pinned in CHECKED."""
    raw = json.loads(catena.data_path(gospel).read_text(encoding="utf-8"))
    return [s["id"] for s in raw["sections"]
            if s["status"] == "checked" and CHECKED[gospel].get(s["id"]) != text_hash(s)]


@pytest.mark.parametrize("gospel", catena.GOSPELS)
def test_each_checked_sections_text_is_exactly_the_text_that_was_checked(gospel):
    assert changed_since_checked(gospel) == []


def test_one_letter_changed_in_a_checked_comment_fails_its_pin(tmp_path, monkeypatch):
    # The review's case: "Christ" becoming "Chryst" in one comment of Matthew 22:41-46 passed every
    # other data test.
    for gospel in catena.GOSPELS:
        shutil.copy(catena.data_path(gospel), tmp_path / catena.data_path(gospel).name)
    path = tmp_path / "matthew.json"
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    start = next(i for i, line in enumerate(lines) if line.startswith('{"id": "matthew-22-41-46"'))
    at = next(i for i in range(start + 1, len(lines)) if "Christ" in lines[i])
    lines[at] = lines[at].replace("Christ", "Chryst", 1)
    path.write_text("".join(lines), encoding="utf-8")
    monkeypatch.setattr(catena, "DATA_DIR", tmp_path)
    assert changed_since_checked("Matthew") == ["matthew-22-41-46"]
    assert [changed_since_checked(g) for g in ("Mark", "Luke", "John")] == [[], [], []]


def test_matthew_22_15_22_is_the_printed_text_of_pages_748_to_752():
    (section,) = catena.sections_for("Matthew 22:15-22")
    assert (section.pages, section.leaves, section.volume.year) == ((748, 752), (19, 23), 1842)
    assert section.checked["on"] == "2026-10-05"
    labels = [c.label for c in section.comments]
    assert labels == ["Pseudo-Chrys.", "Gloss.", "Jerome;", "Chrys.", "Pseudo-Chrys.", "Gloss.", "Chrys.",
                      "Jerome;", "Chrys.", "Pseudo-Chrys.", "Jerome;", "Pseudo-Chrys.", "Jerome;", "Hilary;",
                      "Chrys.", "Jerome;", "Hilary;", "Origen;", "Jerome;"]
    assert [c.work for c in section.comments if c.work] == ["Gloss. ord.", "Chrys. Hom. lxx.", "Gloss. non occ."]
    assert section.comments[17].notes == ("1 Tim. 4, 3.",)
    assert section.comments[0].text.startswith("As when one seeks to dam a stream of running water,")
    assert section.comments[-1].text.endswith(
        "*When they had heard these words, they marvelled, and left Him, and went their way,* "
        "carrying away their unbelief and wonder together.")
    whole = " ".join(c.text for c in section.comments)
    for printed in ("Cæsar", "Judæa", "pourtrayed", "tempters", "discerner", "self-satisfied", "populace"):
        assert printed in whole
    for slip in ("Caesar", "Csesar", "discemer", "  ", " ;", " ?"):
        assert slip not in whole



def test_the_sundays_after_the_test_sunday_are_checked_through_november_1():
    # October 25: Matthew 22:34-46; November 1 (the default set): Matthew 23:1-12.
    for reference, ids in (("Matthew 22:34-46", ["matthew-22-34-40", "matthew-22-41-46"]),
                           ("Matthew 23:1-12", ["matthew-23-1-4", "matthew-23-5-12"])):
        found = catena.sections_for(reference)
        assert [s.id for s in found] == ids
        assert all(s.checked for s in found)
    (aug,) = [c for c in catena.sections_for("Matthew 22:37")[0].comments if c.work == "Aug. de Doctr. Christ. i. 22."][:1]
    assert "final good¹;" in aug.text and aug.notes == ("¹ alia re frui.", "² al. bonum.")
    # The plan review's correction: no comma after "Apostles" (leaf 39; it was the margin note's).
    (origen,) = [c for c in catena.sections_for("Matthew 23:3")[0].comments if "in the Acts forbid" in c.text]
    assert "but the Apostles in the Acts forbid the believers" in origen.text


def test_the_catenas_own_linking_words_stand_apart_under_no_fathers_name():
    # Matthew 22:39-40 (leaf 35): Aquinas's own paragraph after Hilary's comment, not Hilary's.
    comments = catena.sections_for("Matthew 22:40")[0].comments
    hilary, link, aug = comments[17:20]
    assert (hilary.father, hilary.text.endswith("can profit to salvation.")) == ("Hilary", True)
    assert (link.label, link.father, link.work, link.is_quotation) == (None, None, None, False)
    assert link.text == "It follows, *On these two commandments hang all the Law and the Prophets.*"
    assert aug.text == "*Hang,* that is, refer thither as their end."
    assert [s.id for s in catena.load("Matthew") for c in s.comments if not c.is_quotation] == ["matthew-22-34-40"]


@pytest.mark.parametrize("gospel", catena.GOSPELS)
def test_a_stop_after_italic_words_is_set_inside_them_as_the_printing_does(gospel):
    # The README's rule: the printing sets a stop after italic words in italic ("*Master,*"); a scan
    # cannot tell an italic comma or full stop from a roman one, so these follow the word before.
    # A semicolon the page shows roman stays outside ("*they will not*;", leaf 40).
    for section in catena.load(gospel):
        for comment in section.comments:
            assert not re.search(r"[\w'’]\*[,.:?!]", comment.text), (section.id, comment.text)


def test_every_gospel_line_of_the_recorded_lectionaries_finds_its_sections():
    # Optional verses in parentheses ("Luke 2:1-14 (15-20)", Christmas Eve) count as read.
    lines = [line for path in sorted((Path(__file__).parent / "fixtures" / "vanderbilt").glob("*.csv"))
             for row in vanderbilt_lectionary.parse_vanderbilt_csv(path.read_text(encoding="utf-8"))
             for line in vanderbilt_lectionary.clean_cell(row.gospel)]
    assert "Luke 2:(1-7) 8-20" in lines and len(lines) == 20
    assert [line for line in lines if not catena.sections_for(line)] == []
