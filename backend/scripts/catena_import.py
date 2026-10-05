"""The Catena Aurea's import for Voices of the Church (V1): a developer's tool, never run in production.

The text of record is the 1841-45 Oxford printing (John Henry Parker), as scanned at archive.org
(owner's source decision, 2026-10-05). This tool reads archive.org's ABBYY OCR of each volume
(`<identifier>_abbyy.gz`: every character with its place on the page, italics, small capitals),
splits it into the Catena's sections (the Gospel verses printed together, then the fathers'
comments on them), cleans it up automatically and writes drafts. A draft is never shown in the
app: a section's text reaches backend/data/catena/ only after someone has checked it, line by
line, against the page images (the V1 plan's "Checking a section").

Commands (from the repo root; `--cache` is any directory outside the repo):

    .venv/bin/python backend/scripts/catena_import.py fetch --cache DIR
        download the eight volumes' OCR (about 100 MB) into DIR
    .venv/bin/python backend/scripts/catena_import.py draft --cache DIR GOSPEL
        write DIR/draft-<gospel>.json: every section with its cleaned OCR text (unchecked)
    .venv/bin/python backend/scripts/catena_import.py index --cache DIR GOSPEL [--checked FILE ...] [--replace ID ...]
        rewrite backend/data/catena/<gospel>.json: the draft's sections as unchecked entries
        with no text, keeping each checked section exactly as it is in the file and adding each
        checked FILE (one section, as the file holds it); a drafted section that shares a verse
        with a checked one gives way to it. Two checked sections may share only a verse the Catena
        splits; a re-check that changed a section's verses names the old one with --replace ID
    .venv/bin/python backend/scripts/catena_import.py show --cache DIR "REFERENCE"
        print the drafts of the sections overlapping REFERENCE ("Matthew 22:15-22") and the
        addresses of their page images, for checking
    .venv/bin/python backend/scripts/catena_import.py checkout --cache DIR "REFERENCE" --out DIR2
        write DIR2/<id>.json for each section overlapping REFERENCE: the draft with only the keys
        the data file allows (no footnotes, no warnings) and a placeholder "checked" the checker
        fills in; `index --checked` refuses it until then

Standard library only (plus backend/catena.py for the volumes and the file's shape).
"""
from __future__ import annotations

import argparse
import collections
import difflib
import gzip
import json
import re
import statistics
import sys
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator, Optional

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))   # run as a file, sys.path[0] is backend/scripts

import catena  # noqa: E402

ABBYY_NS = "{http://www.abbyy.com/FineReader_xml/FineReader6-schema-v1.xml}"
OCR_URL = "https://archive.org/download/{identifier}/{identifier}_abbyy.gz"

# The first chapter printed in each volume, and each Gospel's last: headings count from it.
FIRST_CHAPTER = {"mt1": 1, "mt2": 11, "mt3": 22, "mk": 1, "lk1": 1, "lk2": 11, "jn1": 1, "jn2": 11}
LAST_CHAPTER = {"Matthew": 28, "Mark": 16, "Luke": 24, "John": 21}

# The Gospel text is set larger than the comments, the footnotes smaller. Measured as the height
# of the small letters (a, c, e, ...) against the volume's commonest, at the scans' 400 dpi:
# comments 25-26 px, Gospel text 29-30, footnotes and running heads about 20.
GOSPEL_RATIO = 1.07
FOOTNOTE_RATIO = 0.88
HEADING_RATIO = 1.5      # a chapter heading's capitals (46 px) against the comments' small letters
_X_LETTERS = frozenset("acemnorsuvwxz")

# OCR slips found while checking, replaced as whole words (add one when a check finds a slip that
# recurs; never a change of the printed wording). The printing sets "æ" in Cæsar and Judæa.
SLIPS: dict[str, str] = {
    "Caesar": "Cæsar", "Csesar": "Cæsar", "Cajsar": "Cæsar", "C&sar": "Cæsar", "Ceesar": "Cæsar",
    "Caesar's": "Cæsar's", "Csesar's": "Cæsar's", "Cajsar's": "Cæsar's", "C&sar's": "Cæsar's",
    "Judsea": "Judæa", "Judaea": "Judæa", "Judasa": "Judæa",
    "thai": "that", "(o": "to", "discemer": "discerner",
}

# The same for the margin notes.
MARGIN_SLIPS: dict[str, str] = {"Horn.": "Hom.", "Horn": "Hom.", "Gloss,": "Gloss.", "Chrys,": "Chrys."}

# The labels as printed (in small capitals) and the father each names. "Id." ("the same") names
# the father of the comment before it.
LABELS: dict[str, Optional[str]] = {
    "Alcuin.": "Alcuin", "Ambrose": "Ambrose", "Athan.": "Athanasius", "Aug.": "Augustine",
    "Augustine": "Augustine", "Basil": "Basil", "Bede": "Bede", "Cassian": "Cassian",
    "Chrys.": "Chrysostom", "Chrysost.": "Chrysostom", "Chrysostom": "Chrysostom",
    "Chrysol.": "Peter Chrysologus", "Chrysologus.": "Peter Chrysologus", "Cyprian": "Cyprian",
    "Cyril": "Cyril of Alexandria", "Damasc.": "John of Damascus", "Damascene": "John of Damascus",
    "Didymus.": "Didymus", "Dionys.": "Dionysius", "Epiph.": "Epiphanius", "Euseb.": "Eusebius",
    "Eusebius": "Eusebius", "Gloss.": "the Gloss", "Greek Ex.": "a Greek expositor",
    "Greg.": "Gregory the Great", "Gregory": "Gregory the Great", "Greg. Naz.": "Gregory of Nazianzus",
    "Greg. Nyss.": "Gregory of Nyssa", "Haymo.": "Haymo", "Hilary": "Hilary", "Id.": None,
    "Isidore": "Isidore", "Jerome": "Jerome", "Leo": "Leo the Great", "Maxim.": "Maximus",
    "Maximus": "Maximus", "Origen": "Origen", "Pseudo-Athan.": "Pseudo-Athanasius",
    "Pseudo-Aug.": "Pseudo-Augustine", "Pseudo-Chrys.": "Pseudo-Chrysostom",
    "Pseudo-Jerome": "Pseudo-Jerome", "Pseudo-Origen": "Pseudo-Origen", "Raban.": "Rabanus Maurus",
    "Rabanus": "Rabanus Maurus", "Remig.": "Remigius", "Remigius": "Remigius",
    "Sever.": "Severianus", "Theophyl.": "Theophylact", "Theophylact": "Theophylact",
    "Tit. Bost.": "Titus of Bostra", "Titus": "Titus of Bostra", "Titus Bost.": "Titus of Bostra",
}
_LABEL_KEYS = {re.sub(r"[^A-Z]", "", label.upper()): label for label in LABELS}
# A label in a volume whose OCR lost the small capitals: a known label starting a sentence.
_TEXT_LABEL = re.compile(
    r"(?:(?<=^)|(?<=[.;:?!)] ))(" + "|".join(sorted((re.escape(k) for k in LABELS), key=len, reverse=True))
    + r")(?=\s*[;,.]?\s+[A-Z\"'(])")

LABEL_OPEN, LABEL_CLOSE, NOTE = "\x01", "\x02", "\x03"


@dataclass(frozen=True)
class Char:
    ch: str
    left: int
    right: int
    height: int
    italic: bool
    smallcaps: bool


@dataclass
class Line:
    """One printed line: its body characters and the margin note beside it."""

    leaf: int
    top: int
    chars: list[Char]
    margin: str = ""
    par_start: bool = False      # the first line of a printed paragraph: indented

    @property
    def text(self) -> str:
        return "".join(c.ch for c in self.chars)

    @property
    def x_height(self) -> float:
        heights = [c.height for c in self.chars if c.ch in _X_LETTERS]
        return statistics.median(heights) if len(heights) >= 3 else 0.0


@dataclass
class Page:
    leaf: int                 # the scan's page index, 0-based (archive.org's "n19")
    number: Optional[int]     # the printed page number, from the running head
    lines: list[Line]


@dataclass
class DraftSection:
    volume: str
    start: tuple[int, int]
    end: tuple[int, int]
    first_leaf: int
    last_leaf: int
    pages: tuple[int, int] = (0, 0)
    lines: list[Line] = field(default_factory=list)
    footnotes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ---- Reading the OCR ---------------------------------------------------------------------------

def read_pages(source) -> Iterator[Page]:
    """Every page of an ABBYY document (a path or a file object), in order."""
    leaf = -1
    for _event, element in ET.iterparse(source, events=("end",)):
        if element.tag != ABBYY_NS + "page":
            continue
        leaf += 1
        yield _page(leaf, element)
        element.clear()


def _page(leaf: int, element: ET.Element) -> Page:
    raw: list[tuple[int, list[Char], bool]] = []
    for block in element.iter(ABBYY_NS + "block"):
        if block.get("blockType") != "Text":
            continue
        for par in block.iter(ABBYY_NS + "par"):
            first = True
            for line in par.iter(ABBYY_NS + "line"):
                chars = [
                    Char(cp.text or " ", int(cp.get("l")), int(cp.get("r")), int(cp.get("b")) - int(cp.get("t")),
                         fmt.get("italic") == "true", fmt.get("smallcaps") == "true")
                    for fmt in line.iter(ABBYY_NS + "formatting")
                    for cp in fmt.iter(ABBYY_NS + "charParams")
                ]
                if chars:
                    raw.append((int(line.get("t")), chars, first))
                    first = False
    raw.sort(key=lambda item: item[0])
    lines = _split_margins(leaf, raw)
    return Page(leaf, None, lines)


def _split_margins(leaf: int, raw: list[tuple[int, list[Char], bool]]) -> list[Line]:
    """Takes the margin notes out of each line: the characters left or right of the text column."""
    full = [chars for _t, chars, _p in raw if sum(1 for c in chars if not c.ch.isspace()) >= 25]
    if not full:
        return [Line(leaf, top, _strip(chars), "", par) for top, chars, par in raw]
    col_left = statistics.median(next(c.left for c in chars if not c.ch.isspace()) for chars in full)
    col_right = statistics.median(next(c.right for c in reversed(chars) if not c.ch.isspace()) for chars in full)
    lines = []
    for top, chars, par in raw:
        # The right margin starts at the first letter or digit beyond the column's end (after a gap):
        # the OCR often reads a note's first letter as part of the line's last word ("Inasmuch M").
        cut = next((i for i, c in enumerate(chars)
                    if c.ch.isalnum() and c.left > col_right - 6
                    and (i == 0 or chars[i - 1].ch.isspace() or c.left - chars[i - 1].right >= 12)), len(chars))
        left = [c for c in chars[:cut] if c.right < col_left - 20]
        body = _strip([c for c in chars[:cut] if not c.right < col_left - 20])
        # A left-margin note's last stop can stand in the gutter just before the column ("Acts 15," beside
        # "in the Acts"): punctuation before the column's first letter is the note's, never the text's.
        while left and body and body[0].ch in ",.;:" and body[0].left < col_left - 2:
            left.append(body.pop(0))
            body = _strip(body)
        margin = left + chars[cut:]
        indented = bool(body) and body[0].left > col_left + 30
        line = Line(leaf, top, body, _margin_text(margin), par and indented)
        if line.text.strip() or line.margin:
            lines.append(line)
    return lines


def _strip(chars: list[Char]) -> list[Char]:
    start, end = 0, len(chars)
    while start < end and chars[start].ch.isspace():
        start += 1
    while end > start and chars[end - 1].ch.isspace():
        end -= 1
    return chars[start:end]


def _margin_text(chars: list[Char]) -> str:
    out = ""
    for i, c in enumerate(chars):
        if i and c.left - chars[i - 1].right > 12 and not out.endswith(" ") and c.ch not in ",.;:":
            out += " "
        out += c.ch
    out = re.sub(r"\s+", " ", out).strip()
    return " ".join(MARGIN_SLIPS.get(word, word) for word in out.split(" ")) if out else ""


def body_x_height(pages: list[Page]) -> float:
    """The commonest small-letter height of the volume's full lines: the comments' type."""
    heights = collections.Counter(round(line.x_height) for page in pages for line in page.lines
                                  if len(line.text) >= 40 and line.x_height)
    return float(heights.most_common(1)[0][0])


def number_pages(pages: list[Page], body: float) -> None:
    """Each page's printed number: from its running head (a small line at the top) where the OCR
    reads one at the volume's usual distance from the leaf, or at a distance three pages nearby
    agree on (a plate moves it), else counted from the pages before. The OCR drops digits ("620"
    read as "20" on two pages running), so agreeing with one neighbour is not enough."""
    read: dict[int, int] = {}
    for page in pages:
        for line in page.lines[:2]:
            if line.x_height and line.x_height < body * FOOTNOTE_RATIO or not line.x_height:
                m = re.match(r"^\s*(\d{1,4})\b", line.text) or re.search(r"\b(\d{1,4})\s*$", line.text)
                if m:
                    read[page.leaf] = int(m.group(1))
                    break
    offsets = collections.Counter(n - leaf for leaf, n in read.items())
    if not offsets:
        return
    usual = offsets.most_common(1)[0][0]
    for page in pages:
        n = read.get(page.leaf)
        offset = None if n is None else n - page.leaf
        nearby = sum(1 for d in range(-3, 4) if read.get(page.leaf + d, -10_000) - page.leaf - d == offset)
        page.number = n if offset == usual or (offset is not None and nearby >= 3) else None
    known = [(p.leaf, p.number) for p in pages if p.number is not None]
    for page in pages:
        if page.number is None:
            before = [(leaf, n) for leaf, n in known if leaf < page.leaf]
            page.number = before[-1][1] + page.leaf - before[-1][0] if before else page.leaf + usual


def is_running_head(line: Line, index: int, body: float) -> bool:
    caps = [c.height for c in line.chars if c.ch.isupper()]
    small = not caps or statistics.median(caps) < body * HEADING_RATIO
    return index < 3 and small and (not line.x_height or line.x_height < body * FOOTNOTE_RATIO) and bool(
        re.search(r"\d|VER|CHAP|ST\.|GOSPEL", line.text))


# ---- Sections ----------------------------------------------------------------------------------

_VERSE = re.compile(r"^\s*(?:Ver\.\s*)?(\d[\d ]{0,3}?)\s*[.,]\s")
_CHAPTER = re.compile(r"^\s*C\s*H\s*A\s*[JP]\S*\s*\.?\s*([IVXLl1]+)\s*[.,]?\s*", re.I)
_ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50}
_SIGNATURE = re.compile(r"^\s*(VOL\.\s+[IVX]+\.?.*|\d{0,2}\s*[A-Z]{1,2}\s*\d?)\s*$")


def roman(text: str) -> Optional[int]:
    text = text.upper().replace("1", "I")
    total = 0
    for i, ch in enumerate(text):
        if ch not in _ROMAN:
            return None
        value = _ROMAN[ch]
        total += -value if i + 1 < len(text) and _ROMAN.get(text[i + 1], 0) > value else value
    return total or None


# A "verse 1" this many lines or fewer before a chapter heading is not one (a numbered line of the
# comments set large, or a misread number): the heading that follows moves the chapter.
HEADING_LOOKAHEAD = 60


def _heading(line: Line, body: float) -> Optional[re.Match]:
    """A chapter heading: "CHAP. VII." in capitals half again as tall as the comments' small letters."""
    heading = _CHAPTER.match(line.text)
    caps = [c.height for c in line.chars[:6] if c.ch.isupper()]
    return heading if heading and caps and statistics.median(caps) >= body * HEADING_RATIO else None


def sections(volume: catena.Volume, pages: list[Page]) -> list[DraftSection]:
    """The volume's sections, in order: each starts where Gospel text follows comments. A chapter
    heading starts the next chapter: its numeral when that is one or two on, else the chapter after. A verse 1 with no heading moves the chapter on too (with a warning),
    unless a heading follows within HEADING_LOOKAHEAD lines; and when the next heading names the
    chapter that verse 1 moved to, the verse 1 was a misread number: the verses read since are
    put back in the chapter before."""
    body = body_x_height(pages)
    first, last = FIRST_CHAPTER[volume.key], LAST_CHAPTER[volume.gospel]
    chapter = first - 1
    out: list[DraftSection] = []
    current: Optional[DraftSection] = None
    mode = "front"
    last_verse: Optional[int] = None
    flow = [(page, line) for page in pages for i, line in enumerate(page.lines)
            if not is_running_head(line, i, body) and not _SIGNATURE.match(line.text)]
    headings = [k for k, (_page, line) in enumerate(flow) if _heading(line, body)]
    bumped: Optional[int] = None         # the section a verse 1 without a heading moved on, by index
    for k, (page, line) in enumerate(flow):
        text = line.text
        if not text.strip():                                 # a margin note's line of its own
            if current is not None and mode == "comment":
                current.lines.append(line)
            continue
        heading = _heading(line, body)
        if heading:
            said = roman(heading.group(1))
            if said is not None and said == chapter and bumped is not None:   # that verse 1 was misread
                for section in out[bumped:]:
                    section.start, section.end = ((c - 1 if c == chapter else c, v) for c, v in (section.start, section.end))
                    section.warnings = [w for w in section.warnings if w != f"no heading found before chapter {chapter}"]
                out[bumped].warnings.append(f"a verse 1 before chapter {chapter}'s heading was not one")
                chapter = said
            elif said is not None and chapter < said <= min(chapter + 2, last):
                chapter = said
            else:
                chapter += 1
                if current is not None:
                    current.warnings.append(f"a chapter heading read as {heading.group(0).strip()!r}: chapter {chapter}")
            last_verse = None
            bumped = None
            text = text[heading.end():]
            if len(text.strip()) < 3:
                continue
        xh = line.x_height
        if xh >= body * GOSPEL_RATIO:
            if chapter < first:
                continue
            m = _VERSE.match(text)
            verse = int(m.group(1).replace(" ", "")) if m else None
            if verse == 1 and last_verse is not None:
                if any(k < h <= k + HEADING_LOOKAHEAD for h in headings):   # the heading comes after it
                    verse = None
                else:                                                     # a chapter heading the OCR missed
                    chapter += 1
                    last_verse = None
                    bumped = len(out) - 1 if out else None
                    if current is not None:
                        current.warnings.append(f"no heading found before chapter {chapter}")
            if mode != "gospel":
                if verse is None:
                    continue                                 # a title, not a section
                current = DraftSection(volume.key, (chapter, verse), (chapter, verse), page.leaf, page.leaf)
                out.append(current)
                mode = "gospel"
            if verse is not None and current is not None:
                if last_verse is not None and verse != last_verse + 1:
                    current.warnings.append(f"verse {verse} follows {last_verse} (chapter {chapter})")
                current.end = (chapter, verse)
                last_verse = verse
            if current is not None:
                current.last_leaf = page.leaf
        elif xh >= body * FOOTNOTE_RATIO or (not xh and mode == "comment" and current and len(text) > 2):
            if current is None:
                continue
            mode = "comment"
            current.lines.append(line)
            current.last_leaf = page.leaf
        elif current is not None and mode == "comment" and text.strip():
            if not re.match(r"^\s*VOL\.", text):
                current.footnotes.append(re.sub(r"\s+", " ", text).strip())
    numbers = {p.leaf: p.number for p in pages}
    for section in out:
        section.pages = (numbers.get(section.first_leaf) or 0, numbers.get(section.last_leaf) or 0)
    return out


def continuity(found: list[DraftSection]) -> None:
    """Warns where a section does not start just after the one before it."""
    for before, after in zip(found, found[1:]):
        (c1, v1), (c2, v2) = before.end, after.start
        if not ((c2 == c1 and v2 == v1 + 1) or (c2 == c1 + 1 and v2 == 1)):
            after.warnings.append(f"starts at {c2}:{v2} after {c1}:{v1}")


# ---- Cleaning ----------------------------------------------------------------------------------

def vocabulary(lines: Iterable[Line]) -> tuple[collections.Counter, collections.Counter]:
    """Word counts and within-line word-pair counts of the OCR, to undo the line-end hyphenation."""
    words: collections.Counter = collections.Counter()
    pairs: collections.Counter = collections.Counter()
    for line in lines:
        tokens = re.findall(r"[A-Za-z']+(?:-[A-Za-z']+)*", line.text.lower())
        words.update(tokens)
        pairs.update(f"{a} {b}" for a, b in zip(tokens, tokens[1:]))
    return words, pairs


def marked(line: Line) -> str:
    """The line with italics as *...* and small-capital labels between LABEL_OPEN and LABEL_CLOSE.
    A space is italic only between two italic characters, so a marker never holds a space at its
    edge."""
    chars = line.chars
    italics = [c.italic and not c.ch.isspace() for c in chars]
    for i, c in enumerate(chars):
        if c.ch.isspace():
            before = next((italics[j] for j in range(i - 1, -1, -1) if not chars[j].ch.isspace()), False)
            after = next((italics[j] for j in range(i + 1, len(chars)) if not chars[j].ch.isspace()), False)
            italics[i] = before and after
    out = ""
    italic = smallcaps = False
    for c, now_italic in zip(chars, italics):
        now_caps = (c.smallcaps and (c.ch.isalpha() or c.ch in ".-")) or (c.ch.isspace() and smallcaps and c.smallcaps)
        if (now_italic, now_caps) != (italic, smallcaps):
            out += ("*" if italic else "") + (LABEL_CLOSE if smallcaps else "")
            out += (LABEL_OPEN if now_caps else "") + ("*" if now_italic else "")
            italic, smallcaps = now_italic, now_caps
        out += c.ch
    return out + ("*" if italic else "") + (LABEL_CLOSE if smallcaps else "")


def join(left: str, right: str, words: collections.Counter, pairs: collections.Counter) -> str:
    """Joins two lines, putting back together a word the line end broke: the printing hyphenates it,
    and the OCR mostly drops the hyphen, so the two halves are joined when the whole word is found
    unbroken in the eight volumes at least as often as the two halves side by side ("popu" +
    "lace"; never "the" + "plan"). A hyphen the OCR kept goes when the whole word is found
    elsewhere ("un-known"), else stays ("self-satisfied"). A word found nowhere else stays apart
    for the checker ("com monest")."""
    if left.endswith("-" + LABEL_CLOSE) and right.startswith(LABEL_OPEN):     # "PSEUDO-" / "CHRYS."
        return left[:-1] + right[1:]
    lm = re.search(r"([A-Za-z']+)(-?)([*\x02]*)$", left)
    rm = re.match(r"([*\x01]*)([A-Za-z']+)", right)
    if lm and rm:
        a, hyphen, b = lm.group(1), lm.group(2), rm.group(2)
        whole, hyphenated = (a + b).lower(), f"{a}-{b}".lower()
        if hyphen:
            if words[whole] > words[hyphenated]:
                return left[: lm.start(2)] + lm.group(3) + right
            return left + right
        if words[whole] and words[whole] >= pairs[f"{a.lower()} {b.lower()}"]:
            return left + right
    return left + " " + right


def clean(text: str) -> str:
    """Spacing, the italics markers and the known OCR slips."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\*(\s*)\*", r"\1", text)                     # italics broken by a line end
    text = re.sub(r" +([;:?!,.)])", r"\1", text)
    text = re.sub(r"\( +", "(", text)
    for wrong, right in SLIPS.items():
        text = re.sub(rf"(?<![\w&]){re.escape(wrong)}(?![\w&])", right, text)
    return re.sub(r" {2,}", " ", text).strip()


def match_label(ocr: str) -> tuple[str, Optional[str], bool]:
    """(the label as printed, its father, known) for the OCR of a small-capital label."""
    key = re.sub(r"[^A-Z]", "", ocr.upper())
    close = [key] if key in _LABEL_KEYS else difflib.get_close_matches(key, list(_LABEL_KEYS), n=1, cutoff=0.5)
    if close:
        label = _LABEL_KEYS[close[0]]
        return label, LABELS[label], True
    return ocr.strip().title(), None, False


def comments(section: DraftSection, words: collections.Counter, pairs: collections.Counter,
             smallcaps: bool = True) -> list[dict]:
    """The section's comments: one for each label, with its work reference and other margin notes."""
    notes: list[str] = []
    text = ""
    previous_margin = False
    for line in section.lines:
        piece = marked(line) if smallcaps else marked(line).replace(LABEL_OPEN, "").replace(LABEL_CLOSE, "")
        if not smallcaps:
            piece = _TEXT_LABEL.sub(lambda m: f"{LABEL_OPEN}{m.group(1)}{LABEL_CLOSE}", piece)
        if line.margin:
            # A note goes on over the next lines, unless one ended (a reference ends in a number and a
            # stop: "Matt. 25, 40.") or a label on this line starts a comment with its own reference.
            ended = bool(notes) and re.search(r"\d\s*[.,;>]$", notes[-1]) is not None
            if previous_margin and notes and not ended and LABEL_OPEN not in piece:
                notes[-1] += " " + line.margin
            else:
                notes.append(line.margin)
                tag = f"{NOTE}{len(notes) - 1}{NOTE}"
                pos = piece.find(LABEL_CLOSE)
                piece = piece[: pos + 1] + tag + piece[pos + 1:] if pos >= 0 else tag + piece
        previous_margin = bool(line.margin)
        piece = re.sub(r"^-(?=[a-z])", "", piece)               # a margin note's hyphen left behind
        if line.par_start and text and not piece.lstrip("*").startswith(LABEL_OPEN):
            piece = "\n\n" + piece
        if piece.strip():
            text = piece if not text else join(text, piece, words, pairs)
    out: list[dict] = []
    for chunk in re.split(f"(?={LABEL_OPEN})", text):
        m = re.match(f"{LABEL_OPEN}([^{LABEL_CLOSE}]*){LABEL_CLOSE}((?:{NOTE}\\d+{NOTE})?)\\s*([;:.,]?)(.*)", chunk, re.S)
        if not m:
            if chunk.strip() and out:
                out[-1]["text"] += " " + chunk
            continue
        ocr_label, work_tag, stop, body = m.groups()
        label, father, known = match_label(ocr_label)
        inside = re.search(r"[;.:]$", ocr_label.strip())             # "JEROME." keeps its stop
        stop = stop if stop in (";", ".", ":") else inside.group(0) if inside and known else ""
        if not label.endswith(".") and stop:
            label += stop
        if father is None and known and out:                    # "Id.": the same father
            father = out[-1]["father"]
        work = notes[int(work_tag.strip(NOTE))] if work_tag else None
        body_notes = [notes[int(n)] for n in re.findall(f"{NOTE}(\\d+){NOTE}", body)]
        body = re.sub(f"{NOTE}\\d+{NOTE}", "", body)
        out.append({"label": label, "father": father or "?", "work": work, "text": body, "notes": body_notes})
    for comment in out:
        paragraphs = [clean(p) for p in comment["text"].split("\n\n")]
        comment["text"] = "\n\n".join(p for p in paragraphs if p)
    return out


# ---- The files ---------------------------------------------------------------------------------

def corpus_vocabulary(cache: Path) -> tuple[collections.Counter, collections.Counter]:
    """The words of all eight volumes (kept in DIR/vocabulary.json after the first time)."""
    path = cache / "vocabulary.json"
    if path.exists():
        saved = json.loads(path.read_text(encoding="utf-8"))
        return collections.Counter(saved["words"]), collections.Counter(saved["pairs"])
    words: collections.Counter = collections.Counter()
    pairs: collections.Counter = collections.Counter()
    for volume in catena.VOLUMES:
        w, p = vocabulary(line for page in read_pages(gzip.open(cache / f"{volume.identifier}_abbyy.gz"))
                          for line in page.lines)
        words += w
        pairs += p
    path.write_text(json.dumps({"words": words, "pairs": pairs}), encoding="utf-8")
    return words, pairs


def build_draft(gospel: str, cache: Path) -> dict:
    """Every section of a Gospel, with its cleaned OCR text (never shipped; checked by hand)."""
    words, pairs = corpus_vocabulary(cache)
    drafted: list[dict] = []
    found_all: list[DraftSection] = []
    for volume in (v for v in catena.VOLUMES if v.gospel == gospel):
        pages = list(read_pages(gzip.open(cache / f"{volume.identifier}_abbyy.gz")))
        body = body_x_height(pages)
        number_pages(pages, body)
        found = sections(volume, pages)
        has_smallcaps = sum(1 for page in pages for line in page.lines for c in line.chars if c.smallcaps) > 1000
        for s in found:
            s.comments = comments(s, words, pairs, has_smallcaps)   # type: ignore[attr-defined]
        found_all += found
    continuity(found_all)
    seen: collections.Counter = collections.Counter()
    for s in found_all:
        base = catena.section_id(gospel, s.start, s.end)
        seen[base] += 1
        drafted.append({
            "id": base if seen[base] == 1 else f"{base}-{seen[base]}",
            "start": list(s.start), "end": list(s.end),
            "volume": s.volume, "pages": list(s.pages), "leaves": [s.first_leaf, s.last_leaf],
            "comments": s.comments,                                  # type: ignore[attr-defined]
            "footnotes": s.footnotes, "warnings": s.warnings,
        })
    return {"gospel": gospel, "sections": drafted}


PLACEHOLDER_CHECKED = {"on": "YYYY-MM-DD", "by": "<who>, word by word against the page images"}


def checkout_entry(drafted: dict) -> dict:
    """A drafted section as the file to check and correct: only the data file's keys (the draft's
    footnotes and warnings are unchecked OCR and never enter the repository)."""
    return index_entry(drafted) | {"status": "checked", "checked": dict(PLACEHOLDER_CHECKED),
                                   "comments": drafted["comments"]}


def index_entry(drafted: dict) -> dict:
    return {key: drafted[key] for key in ("id", "start", "end", "volume", "pages", "leaves")} | {"status": "unchecked"}


def _after(gospel: str, verse: list[int]) -> list[int]:
    """The verse after this one (the next chapter's first after a chapter's last)."""
    chapter, v = verse
    return [chapter, v + 1] if v < catena.VERSES[gospel][chapter - 1] else [chapter + 1, 1]


def _before(gospel: str, verse: list[int]) -> list[int]:
    chapter, v = verse
    return [chapter, v - 1] if v > 1 else [chapter - 1, catena.VERSES[gospel][chapter - 2]]


def fill_gaps(gospel: str, sections: list[dict]) -> int:
    """The Catena comments on every verse, so a verse no section has is a verse number the OCR
    missed. An unchecked section takes the gap after it, up to the verse before the next section
    or its chapter's end; a gap at a chapter's start goes to the unchecked section after it, which
    then starts at verse 1. A checked section is never changed. Ids follow the verses. Returns how
    many sections changed."""
    verses = catena.VERSES[gospel]
    last = [len(verses), verses[-1]]

    def open_(section: Optional[dict]) -> bool:
        return section is not None and section["status"] == "unchecked"

    changed: set[int] = set()
    bounds: list[Optional[dict]] = [None, *sections, None]
    for before, after in zip(bounds, bounds[1:]):
        want = [1, 1] if before is None else None if before["end"] == last else _after(gospel, before["end"])
        if want is None or (after is not None and after["start"] <= want):
            continue
        stop = last if after is None else _before(gospel, after["start"])   # the gap is want .. stop
        if open_(before) and stop[0] == before["end"][0]:
            before["end"] = stop                                            # the rest of its chapter at most
            changed.add(id(before))
            continue
        if open_(before) and before["end"][0] < stop[0] and before["end"][1] < verses[before["end"][0] - 1]:
            before["end"] = [before["end"][0], verses[before["end"][0] - 1]]
            changed.add(id(before))
        if open_(after) and after["start"][1] > 1 and (before is None or before["end"][0] < after["start"][0]
                                                       or not open_(before)):
            after["start"] = [after["start"][0], 1] if before is None or before["end"][0] < after["start"][0] else want
            changed.add(id(after))
    taken = {section["id"] for section in sections if section["status"] == "checked"}
    for section in sections:
        if section["status"] == "unchecked":
            base = ident = catena.section_id(gospel, tuple(section["start"]), tuple(section["end"]))
            n = 1
            while ident in taken:
                n += 1
                ident = f"{base}-{n}"
            taken.add(ident)
            section["id"] = ident
    return len(changed)


def merged_index(gospel: str, draft: dict, existing: Optional[dict]) -> dict:
    """The data file: every checked section of the file as it is, and the draft's other sections
    with no text (a drafted section that shares a verse with a checked one gives way to it), with
    the gaps between sections filled (fill_gaps)."""
    checked = [s for s in (existing or {}).get("sections", []) if s.get("status") == "checked"]

    def shares_a_verse(drafted: dict) -> bool:
        return any(c["start"] <= drafted["end"] and drafted["start"] <= c["end"] for c in checked)

    kept = [index_entry(s) for s in draft["sections"] if not shares_a_verse(s)]
    merged = sorted(checked + kept, key=lambda s: (s["start"], s["end"]))
    fill_gaps(gospel, merged)
    return {"format": catena.FORMAT, "gospel": gospel, "sections": merged}


def split_verse(a: dict, b: dict) -> bool:
    """Two sections that share only the verse the Catena splits between them: the last verse of the
    first is the first of the second ("matthew-2-7-9", "matthew-2-9-9")."""
    first, second = sorted((a, b), key=lambda s: (s["start"], s["end"]))
    return first["end"] == second["start"]


def overlapping_checked(sections: list[dict]) -> list[tuple[str, str]]:
    """Pairs of checked sections that share more than a split verse: a re-check that moved a
    section's verses (a new id) beside the old checked section it should replace."""
    checked = [s for s in sections if s.get("status") == "checked"]
    return [(a["id"], b["id"]) for i, a in enumerate(checked) for b in checked[i + 1:]
            if a["start"] <= b["end"] and b["start"] <= a["end"] and not split_verse(a, b)]


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def data_text(data: dict) -> str:
    """A data file's text: one section a line, and a checked section's comments one a line, so a
    check's diff shows what changed."""
    one = lambda value: json.dumps(value, ensure_ascii=False)  # noqa: E731
    lines = [f'{{"format": {one(data["format"])}, "gospel": {one(data["gospel"])}, "sections": [']
    for i, section in enumerate(data["sections"]):
        end = "," if i + 1 < len(data["sections"]) else ""
        if section.get("status") != "checked":
            lines.append(one(section) + end)
            continue
        head = {k: v for k, v in section.items() if k != "comments"}
        lines.append(one(head)[:-1] + ', "comments": [')
        comments = section["comments"]
        lines += [one(c) + ("," if j + 1 < len(comments) else "") for j, c in enumerate(comments)]
        lines.append("]}" + end)
    lines.append("]}")
    return "\n".join(lines) + "\n"


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("fetch", "draft", "index", "show", "checkout"))
    parser.add_argument("what", nargs="?", default="")
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--checked", type=Path, action="append", default=[],
                        help="index: a checked section (JSON) to put in the file in place of its draft")
    parser.add_argument("--replace", action="append", default=[], metavar="ID",
                        help="index: a checked section of the file that a --checked file replaces (new verses)")
    parser.add_argument("--out", type=Path, help="checkout: the directory to write the sections to check")
    args = parser.parse_intermixed_args(argv)
    cache: Path = args.cache
    cache.mkdir(parents=True, exist_ok=True)
    if args.command == "fetch":
        for volume in catena.VOLUMES:
            target = cache / f"{volume.identifier}_abbyy.gz"
            if not target.exists():
                print(f"fetching {volume.identifier}")
                urllib.request.urlretrieve(OCR_URL.format(identifier=volume.identifier), target)
        return 0
    gospel = args.what.split(" ")[0].capitalize()
    if gospel not in catena.GOSPELS:
        parser.error("name a Gospel: Matthew, Mark, Luke or John")
    draft_path = cache / f"draft-{gospel.lower()}.json"
    if args.command == "draft":
        draft = build_draft(gospel, cache)
        write_json(draft_path, draft)
        warned = sum(1 for s in draft["sections"] if s["warnings"])
        print(f"{gospel}: {len(draft['sections'])} sections, {warned} with warnings -> {draft_path}")
        return 0
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    if args.command == "index":
        path = catena.data_path(gospel)
        existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"sections": []}
        unknown = set(args.replace) - {s["id"] for s in existing["sections"] if s.get("status") == "checked"}
        if unknown:
            parser.error(f"--replace names no checked section of the file: {', '.join(sorted(unknown))}")
        existing["sections"] = [s for s in existing["sections"] if s["id"] not in args.replace]
        for checked in args.checked:
            section = json.loads(checked.read_text(encoding="utf-8"))
            existing["sections"] = [s for s in existing["sections"] if s["id"] != section["id"]] + [section]
        merged = merged_index(gospel, draft, existing)
        catena.parse(merged, gospel)                     # a checked section that breaks the format stops here
        for a, b in overlapping_checked(merged["sections"]):
            raise catena.CatenaDataError(f"{gospel}: the checked sections {a} and {b} share verses; pass "
                                         f"--replace with the one the other replaces")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data_text(merged), encoding="utf-8")
        done = sum(1 for s in merged["sections"] if s["status"] == "checked")
        print(f"{gospel}: {len(merged['sections'])} sections, {done} checked -> {path}")
        return 0
    if args.command == "checkout" and args.out is None:
        parser.error("checkout needs --out DIR")
    spans = catena.parse_gospel_reference(args.what)
    for section in draft["sections"]:
        start, end = tuple(section["start"]), tuple(section["end"])
        if any(start <= s_end and s_start <= end for s_start, s_end in spans):
            volume = catena.volume(section["volume"])
            if args.command == "checkout":
                write_json(args.out / f"{section['id']}.json", checkout_entry(section))
                print(f"{section['id']} -> {args.out / (section['id'] + '.json')}")
            else:
                print(json.dumps(section, ensure_ascii=False, indent=1))
            for leaf in range(section["leaves"][0], section["leaves"][1] + 1):
                print(catena.page_image_url(volume, leaf))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
