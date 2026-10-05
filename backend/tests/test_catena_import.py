"""backend/scripts/catena_import.py: the Catena's OCR into drafts and data files (Voices V1 spec
"The import tool").

The pages are invented, in the shape of archive.org's ABBYY OCR (every character with its box,
italics and small capitals) and the 1842 printing's measures at 400 dpi: the comments' small
letters 26 px high, the Gospel text's 30, the running head's 20, a chapter heading's capitals 46.
"""
import collections
import importlib.util
import io
import json
import re
import sys
from pathlib import Path

import pytest

import catena

TOOL = Path(catena.__file__).parent / "scripts" / "catena_import.py"
_spec = importlib.util.spec_from_file_location("catena_import", TOOL)
tool = importlib.util.module_from_spec(_spec)
sys.modules["catena_import"] = tool          # its dataclasses look their module up while it loads
_spec.loader.exec_module(tool)

NS = "http://www.abbyy.com/FineReader_xml/FineReader6-schema-v1.xml"
COMMENT, GOSPEL, HEAD = 26, 30, 20
LEFT, CHAR = 300, 24          # the text column starts at x = 300; each character is 24 px wide


def run(text, *, x=None, italic=False, smallcaps=False, height=COMMENT):
    return {"text": text, "x": x, "italic": italic, "smallcaps": smallcaps, "height": height}


def page(*lines, top=300):
    """An ABBYY page: each line a list of runs, one paragraph a line; a run's x (default: after
    the run before) places it, so a margin note is a run left or right of the column."""
    out = [f'<page width="2034" height="3314">']
    out.append('<block blockType="Text"><text>')
    for n, runs in enumerate(lines):
        y = top + n * 66
        out.append(f'<par><line t="{y}" b="{y + 50}">')
        x = LEFT
        for r in runs:
            x = r["x"] if r["x"] is not None else x
            attrs = (' italic="true"' if r["italic"] else "") + (' smallcaps="true"' if r["smallcaps"] else "")
            out.append(f"<formatting{attrs}>")
            for ch in r["text"]:
                h = r["height"] if ch in "acemnorsuvwxz" else int(r["height"] * 1.45) if ch.isupper() else r["height"]
                out.append(f'<charParams l="{x}" r="{x + CHAR - 2}" t="{y + 50 - h}" b="{y + 50}">{ch}</charParams>')
                x += CHAR
            out.append("</formatting>")
        out.append("</line></par>")
    out.append("</text></block></page>")
    return "".join(out)


def document(*pages):
    return io.BytesIO(f'<document xmlns="{NS}">{"".join(pages)}</document>'.encode("utf-8"))


FILL = "and some more words to make a full line of the column here"   # 25+ characters: a full line


def test_the_margin_notes_leave_the_line_and_the_running_head_gives_the_page_number():
    pages = list(tool.read_pages(document(
        page([run("749 GOSPEL ACCORDING TO CHAP. XXII.", height=HEAD)],
             [run(FILL)], [run(FILL)],
             [run("Chrys.", x=40), run("worship of God. ", x=LEFT), run("CHRYS.", smallcaps=True),
              run(" They send their disciples")],
             [run(FILL), run("Gloss.", x=LEFT + len(FILL) * CHAR + 60)]),
    )))
    (p,) = pages
    tool.number_pages(pages + [tool.Page(1, None, [])], tool.body_x_height(pages))
    lines = p.lines
    assert [line.margin for line in lines] == ["", "", "", "Chrys.", "Gloss."]
    assert lines[3].text == "worship of God. CHRYS. They send their disciples"
    assert lines[4].text == FILL


def test_a_left_margin_notes_stop_in_the_gutter_is_the_notes_not_the_texts():
    # Leaf 39 of Matthew Part III: "Acts 15, / 19." beside "but the Apostles / in the Acts forbid".
    pages = list(tool.read_pages(document(page(
        [run(FILL)], [run(FILL)],
        [run("Acts 15", x=40), run(",", x=LEFT - CHAR), run(" in the Acts forbid the believers to do")],
        [run(FILL)],
    ))))
    (p,) = pages
    assert (p.lines[2].text, p.lines[2].margin) == ("in the Acts forbid the believers to do", "Acts 15,")


def gospel_page(leaf_number, *extra, head=True):
    lines = []
    if head:
        lines.append([run(f"VER. 15-22. ST. MATTHEW. {leaf_number}", height=HEAD)])
    return page(*lines, *extra)


def test_gospel_lines_after_comments_start_a_section_and_a_heading_moves_the_chapter():
    pages = list(tool.read_pages(document(
        page([run("CHAP. XXII.", height=32)],
             [run("1. And Jesus answered and spake unto them", height=GOSPEL)],
             [run("2. The kingdom of heaven is like unto a king,", height=GOSPEL)],
             [run("PSEUDO-CHRYS.", smallcaps=True), run(" " + FILL)], [run(FILL)]),
        gospel_page(749,
                    [run("15. Then went the Pharisees, and took counsel", height=GOSPEL)],
                    [run("how they might entangle him in his talk.", height=GOSPEL)],
                    [run("16. And they sent out unto him their disciples", height=GOSPEL)],
                    [run("JEROME", smallcaps=True), run(" ; " + FILL)], [run(FILL)], [run(FILL)],
                    [run(FILL)], [run(FILL)], [run(FILL)]),
    )))
    body = tool.body_x_height(pages)
    tool.number_pages(pages, body)
    found = tool.sections(catena.volume("mt3"), pages)
    assert [(s.start, s.end, s.first_leaf, s.last_leaf) for s in found] == [
        ((22, 1), (22, 2), 0, 0), ((22, 15), (22, 16), 1, 1)]
    assert len(found[1].lines) == 6
    tool.continuity(found)
    assert found[1].warnings == ["verse 15 follows 2 (chapter 22)", "starts at 22:15 after 22:2"]


def test_verse_one_without_a_heading_moves_the_chapter_on_and_says_so():
    pages = list(tool.read_pages(document(page(
        [run("CHAP. XXII.", height=32)],
        [run("46. And no man was able to answer him a word,", height=GOSPEL)],
        [run("JEROME", smallcaps=True), run("; " + FILL)], [run(FILL)],
        [run("1. Then spake Jesus to the multitude, and", height=GOSPEL)],
        [run("CHRYS.", smallcaps=True), run(" " + FILL)], [run(FILL)], [run(FILL)],
    ))))
    found = tool.sections(catena.volume("mt3"), pages)
    assert [(s.start, s.end) for s in found] == [((22, 46), (22, 46)), ((23, 1), (23, 1))]
    assert found[0].warnings == ["no heading found before chapter 23"]


def gospel_line(text):
    return [run(text, height=GOSPEL)]


def test_a_chapter_heading_after_a_misread_verse_1_keeps_the_verses_in_their_chapter():
    # A large-type line read as "1." just before the heading: not a verse.
    soon = list(tool.read_pages(document(page(
        [run("CHAP. XXII.", height=32)], gospel_line("44. The Lord said unto my Lord, Sit thou on"),
        [run("AUG.", smallcaps=True), run(" " + FILL)], [run(FILL)],
        gospel_line("1. If David then call him Lord, how is he his"), [run(FILL)], [run(FILL)],
        [run("CHAP. XXIII.", height=32)], gospel_line("1. Then spake Jesus to the multitude, and"),
        [run("CHRYS.", smallcaps=True), run(" " + FILL)], [run(FILL)],
    ))))
    found = tool.sections(catena.volume("mt3"), soon)
    assert [(s.start, s.end) for s in found] == [((22, 44), (22, 44)), ((23, 1), (23, 1))]
    # "45." read as "1." inside the Gospel text, the heading a page later: the verses go back to chapter 22.
    late = list(tool.read_pages(document(page(
        [run("CHAP. XXII.", height=32)], gospel_line("44. The Lord said unto my Lord, Sit thou on"),
        gospel_line("1. If David then call him Lord, how is he his"),
        gospel_line("46. And no man was able to answer him a word,"),
        [run("AUG.", smallcaps=True), run(" " + FILL)], *([run(FILL)] for _ in range(tool.HEADING_LOOKAHEAD + 5)),
        [run("CHAP. XXIII.", height=32)], gospel_line("1. Then spake Jesus to the multitude, and"),
        [run("CHRYS.", smallcaps=True), run(" " + FILL)], [run(FILL)],
    ))))
    found = tool.sections(catena.volume("mt3"), late)
    assert [(s.start, s.end) for s in found] == [((22, 44), (22, 46)), ((23, 1), (23, 1))]
    assert "a verse 1 before chapter 23's heading was not one" in found[0].warnings
    assert "no heading found before chapter 23" not in found[0].warnings


def test_a_page_number_the_ocr_misread_on_pages_running_is_counted_from_the_leaves():
    # Matthew Part II, pages 616-622: the OCR read "620" and "621" as "20" and "21".
    pages = list(tool.read_pages(document(*(
        gospel_page(n, [run(FILL)], [run(FILL)], [run(FILL)]) for n in (616, 617, 618, 619, 20, 21, 622)))))
    tool.number_pages(pages, tool.body_x_height(pages))
    assert [p.number for p in pages] == [616, 617, 618, 619, 620, 621, 622]


def test_the_index_fills_the_verses_no_section_has():
    def entry(start, end, status="unchecked"):
        return {"id": "", "start": start, "end": end, "volume": "mt1", "pages": [1, 2], "leaves": [3, 4],
                "status": status}
    found = [entry([1, 2], [1, 2]), entry([1, 16], [1, 20]), entry([2, 3], [2, 5]),
             dict(entry([2, 6], [2, 9], "checked"), id="matthew-2-6-9"), entry([2, 12], [2, 23])]
    assert tool.fill_gaps("Matthew", found) == 4
    assert [(s["id"], s["start"], s["end"]) for s in found] == [
        ("matthew-1-1-15", [1, 1], [1, 15]), ("matthew-1-16-25", [1, 16], [1, 25]),
        ("matthew-2-1-5", [2, 1], [2, 5]), ("matthew-2-6-9", [2, 6], [2, 9]),
        ("matthew-2-10-23", [2, 10], [2, 23])]


def test_a_word_broken_at_the_line_end_is_joined_when_the_volumes_have_it_whole():
    words = collections.Counter({"populace": 3, "the": 900, "plan": 4, "unknown": 2, "commonest": 0})
    pairs = collections.Counter({"the plan": 2})
    assert tool.join("because of the popu", "lace, they", words, pairs) == "because of the populace, they"
    assert tool.join("Such as the", "plan was", words, pairs) == "Such as the plan was"
    assert tool.join("Who as un-", "known to Him", words, pairs) == "Who as unknown to Him"
    assert tool.join("on the other hand, self-", "satisfied in", words, pairs) == "on the other hand, self-satisfied in"
    assert tool.join("This is the com", "monest act", words, pairs) == "This is the com monest act"
    assert tool.join("saying, *Master,*", "*we know*", words, pairs) == "saying, *Master,* *we know*"


def test_the_cleanup_spaces_italics_and_known_slips():
    assert tool.clean("what thinkest Thou ?  Is it lawful ; to  Csesar , or not") == (
        "what thinkest Thou? Is it lawful; to Cæsar, or not")
    assert tool.clean("saying, *Master,* *we know that Thou art true.* They") == (
        "saying, *Master, we know that Thou art true.* They")
    assert tool.clean("*for**bidding to marry*") == "*forbidding to marry*"
    assert tool.clean("Judsea and C&sar's discemer") == "Judæa and Cæsar's discerner"
    assert tool.clean("Caesarea") == "Caesarea"                    # a whole word only


def test_italics_never_hold_a_space_at_their_edge():
    line = tool.Line(0, 0, [tool.Char(ch, 0, 0, 26, italic, False)
                            for text, italic in (("saying, ", False), ("Master, ", True), ("that", False))
                            for ch in text])
    assert tool.marked(line) == "saying, *Master,* that"


@pytest.mark.parametrize("ocr, printed, father", [
    ("PSEUDO-CHRYS.", "Pseudo-Chrys.", "Pseudo-Chrysostom"),
    ("Jkkomk;", "Jerome", "Jerome"),
    ("Ciirys.", "Chrys.", "Chrysostom"),
    ("CHRYS,", "Chrys.", "Chrysostom"),
    ("GREG. NYSS.", "Greg. Nyss.", "Gregory of Nyssa"),
    ("Greek Ex.", "Greek Ex.", "a Greek expositor"),
])
def test_an_ocr_label_is_matched_to_the_label_as_printed(ocr, printed, father):
    assert tool.match_label(ocr) == (printed, father, True)


def test_an_unknown_label_is_kept_for_the_checker():
    assert tool.match_label("VOL.") == ("Vol.", None, False)


def test_every_known_label_names_a_known_father():
    assert {f for f in tool.LABELS.values() if f} <= catena.FATHERS


def section_of(*lines):
    s = tool.DraftSection("mt3", (22, 15), (22, 22), 0, 0)
    for n, (body, margin, par) in enumerate(lines):
        chars = [tool.Char(ch, 0, 0, 26, italic, caps)
                 for text, italic, caps in body for ch in text]
        s.lines.append(tool.Line(0, n, chars, margin, par))
    return s


def test_comments_split_at_labels_with_their_margin_references_notes_and_paragraphs():
    words = collections.Counter({"populace": 2})
    s = section_of(
        ([("PSEUDO-CHRYS.", False, True), (" As when one seeks. ", False, False), ("Then went", True, False)], "", False),
        ([("the Pharisees.", True, False), (" ", False, False), ("GLOSS.", False, True), (" Who as unknown", False, False)], "Gloss.", False),
        ([("to Him, because of the popu", False, False)], "ord.", False),
        ([("lace. ", False, False), ("ID.", False, True), (" The same.", False, False)], "", False),
        ([("ORIGEN", False, True), ("; From this place.", False, False)], "", True),
        ([("Another paragraph, forbidding to marry.", False, False)], "1 Tim. 4, 3.", True),
    )
    assert tool.comments(s, words, collections.Counter()) == [
        {"label": "Pseudo-Chrys.", "father": "Pseudo-Chrysostom", "work": None,
         "text": "As when one seeks. *Then went the Pharisees.*", "notes": []},
        {"label": "Gloss.", "father": "the Gloss", "work": "Gloss. ord.",
         "text": "Who as unknown to Him, because of the populace.", "notes": []},
        {"label": "Id.", "father": "the Gloss", "work": None, "text": "The same.", "notes": []},
        {"label": "Origen;", "father": "Origen", "work": None,
         "text": "From this place.\n\nAnother paragraph, forbidding to marry.", "notes": ["1 Tim. 4, 3."]},
    ]


def test_without_small_capitals_a_known_label_starting_a_sentence_is_one():
    s = section_of(([("Raban. The Lord having sent out His disciples. Chrys. Having sent them forth, "
                      "and Jerome said so.", False, False)], "", False))
    out = tool.comments(s, collections.Counter(), collections.Counter(), smallcaps=False)
    assert [(c["label"], c["text"]) for c in out] == [
        ("Raban.", "The Lord having sent out His disciples."),
        ("Chrys.", "Having sent them forth, and Jerome said so.")]


DRAFT = {"gospel": "Matthew", "sections": [
    {"id": "matthew-22-1-14", "start": [22, 1], "end": [22, 14], "volume": "mt3", "pages": [738, 748],
     "leaves": [9, 19], "comments": [], "footnotes": [], "warnings": []},
    {"id": "matthew-22-15-21", "start": [22, 15], "end": [22, 21], "volume": "mt3", "pages": [748, 752],
     "leaves": [19, 23], "comments": [{"label": "x"}], "footnotes": [], "warnings": ["a warning"]},
]}
CHECKED = {"id": "matthew-22-15-22", "start": [22, 15], "end": [22, 22], "volume": "mt3", "pages": [748, 752],
           "leaves": [19, 23], "status": "checked", "checked": {"on": "2026-10-05", "by": "a test"},
           "comments": [{"label": "Jerome;", "father": "Jerome", "work": None, "text": "Lately.", "notes": []},
                        {"label": "Hilary;", "father": "Hilary", "work": None, "text": "For if.", "notes": []}]}


def test_the_index_keeps_each_checked_section_and_drops_the_drafts_it_covers():
    merged = tool.merged_index("Matthew", DRAFT, {"sections": [CHECKED]})
    assert [s["id"] for s in merged["sections"]] == ["matthew-22-1-14", "matthew-22-15-22"]
    assert merged["sections"][0] == {"id": "matthew-22-1-14", "start": [22, 1], "end": [22, 14], "volume": "mt3",
                                     "pages": [738, 748], "leaves": [9, 19], "status": "unchecked"}
    assert merged["sections"][1] is CHECKED
    catena.parse(merged, "Matthew")


def test_the_data_file_is_one_section_a_line_and_reads_back(tmp_path):
    merged = tool.merged_index("Matthew", DRAFT, {"sections": [CHECKED]})
    text = tool.data_text(merged)
    assert text.splitlines() == [
        '{"format": 1, "gospel": "Matthew", "sections": [',
        '{"id": "matthew-22-1-14", "start": [22, 1], "end": [22, 14], "volume": "mt3", "pages": [738, 748], '
        '"leaves": [9, 19], "status": "unchecked"},',
        '{"id": "matthew-22-15-22", "start": [22, 15], "end": [22, 22], "volume": "mt3", "pages": [748, 752], '
        '"leaves": [19, 23], "status": "checked", "checked": {"on": "2026-10-05", "by": "a test"}, "comments": [',
        '{"label": "Jerome;", "father": "Jerome", "work": null, "text": "Lately.", "notes": []},',
        '{"label": "Hilary;", "father": "Hilary", "work": null, "text": "For if.", "notes": []}',
        "]}",
        "]}",
    ]
    assert json.loads(text) == merged


def test_index_adds_a_checked_file_and_refuses_one_that_breaks_the_format(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(catena, "DATA_DIR", tmp_path / "data")
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "draft-matthew.json").write_text(json.dumps(DRAFT), encoding="utf-8")
    checked = tmp_path / "checked.json"
    checked.write_text(json.dumps(CHECKED), encoding="utf-8")
    assert tool.main(["index", "Matthew", "--cache", str(cache), "--checked", str(checked)]) == 0
    assert capsys.readouterr().out.startswith("Matthew: 2 sections, 1 checked -> ")
    assert [s.id for s in catena.parse(json.loads((tmp_path / "data" / "matthew.json").read_text()), "Matthew")] == [
        "matthew-22-1-14", "matthew-22-15-22"]
    checked.write_text(json.dumps(dict(CHECKED, comments=[dict(CHECKED["comments"][0], father="Somebody")])),
                       encoding="utf-8")
    with pytest.raises(catena.CatenaDataError):
        tool.main(["index", "Matthew", "--cache", str(cache), "--checked", str(checked)])


def test_checkout_writes_only_the_keys_the_file_allows_and_index_waits_for_the_check(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(catena, "DATA_DIR", tmp_path / "data")
    cache, out = tmp_path / "cache", tmp_path / "check"
    cache.mkdir()
    drafted = dict(DRAFT["sections"][1], comments=CHECKED["comments"], footnotes=["f Cf. vol. i. 139."])
    (cache / "draft-matthew.json").write_text(json.dumps(dict(DRAFT, sections=[DRAFT["sections"][0], drafted])),
                                              encoding="utf-8")
    assert tool.main(["checkout", "Matthew 22:15-22", "--cache", str(cache), "--out", str(out)]) == 0
    assert capsys.readouterr().out.splitlines()[:2] == [
        f"matthew-22-15-21 -> {out / 'matthew-22-15-21.json'}",
        "https://archive.org/download/catenaurecommpt301thomuoft/page/n19.jpg"]
    written = json.loads((out / "matthew-22-15-21.json").read_text(encoding="utf-8"))
    assert set(written) == {"id", "start", "end", "volume", "pages", "leaves", "status", "checked", "comments"}
    assert written["checked"] == {"on": "YYYY-MM-DD", "by": "<who>, word by word against the page images"}
    with pytest.raises(catena.CatenaDataError):
        tool.main(["index", "Matthew", "--cache", str(cache), "--checked", str(out / "matthew-22-15-21.json")])


@pytest.mark.parametrize("gospel", catena.GOSPELS)
def test_no_checked_text_carries_a_slip_the_import_knows(gospel):
    for section in catena.load(gospel):
        for comment in section.comments:
            for slip in tool.SLIPS:
                assert not re.search(rf"(?<![\w&]){re.escape(slip)}(?![\w&])", comment.text), (section.id, slip)


def test_a_label_broken_at_the_line_end_is_one_label():
    left = f"tempt Jesus. {tool.LABEL_OPEN}PSEUDO-{tool.LABEL_CLOSE}"
    right = f"{tool.LABEL_OPEN}CHRYS.{tool.LABEL_CLOSE} Or the Pharisees"
    assert tool.join(left, right, collections.Counter(), collections.Counter()) == (
        f"tempt Jesus. {tool.LABEL_OPEN}PSEUDO-CHRYS.{tool.LABEL_CLOSE} Or the Pharisees")


def test_a_note_beginning_inside_the_last_word_runs_over_its_own_lines_until_a_reference_ends():
    end = LEFT + len(FILL) * CHAR                                  # the column's right edge
    pages = list(tool.read_pages(document(page(
        [run(FILL)], [run(FILL)], [run(FILL)],
        [run("said below, Inasmuch"), run("Matt.", x=end + 4)],      # no space: the OCR's "Inasmuch M"
        [run("25, 40.", x=end + 4)],                               # the note's next line, beside no text
        [run("it unto me. "), run("AUG.", smallcaps=True), run(" Let no one"), run("Aug. de", x=end + 4)],
        [run("Cons.", x=end + 4)],
        [run(FILL)],
    ))))
    (p,) = pages
    assert [(line.text, line.margin) for line in p.lines[3:7]] == [
        ("said below, Inasmuch", "Matt."), ("", "25, 40."), ("it unto me. AUG. Let no one", "Aug. de"), ("", "Cons.")]
    s = tool.DraftSection("mt3", (22, 34), (22, 40), 0, 0, lines=[
        tool.Line(0, 0, [tool.Char(ch, 0, 0, 26, False, ch in "ORIGEN") for ch in "ORIGEN; All who ask"]),
        *p.lines[3:7]])
    out = tool.comments(s, collections.Counter(), collections.Counter())
    assert [(c["label"], c["work"], c["notes"]) for c in out] == [
        ("Origen;", None, ["Matt. 25, 40."]), ("Aug.", "Aug. de Cons.", [])]


def test_a_page_signature_is_not_text():
    pages = list(tool.read_pages(document(page(
        [run("CHAP. XXII.", height=32)],
        [run("15. Then went the Pharisees, and took counsel", height=GOSPEL)],
        [run("JEROME", smallcaps=True), run("; " + FILL)], [run(FILL)], [run(FILL)], [run(FILL)],
        [run("VOL. I. 3 D")], [run("3 D 2")],
    ))))
    (section,) = tool.sections(catena.volume("mt3"), pages)
    assert [line.text for line in section.lines if "D" in line.text] == []
