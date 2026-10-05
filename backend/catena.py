"""The Catena Aurea on the four Gospels, as the app ships it (Voices of the Church V1).

The text of record is the 1841-45 Oxford printing (John Henry Parker), from the scans at
archive.org (owner's source decision, 2026-10-05). backend/data/catena/<gospel>.json holds every
section of the Catena (its verses, volume and printed pages); a section someone has checked
against the page images also holds its comments, exactly as printed. A section not yet checked
has no text in the file, so uncorrected OCR can never be shown (backend/scripts/catena_import.py
makes the drafts; the plan's "Checking a section" says how a section is checked).

Pure: no I/O but reading the data files (once each, lazily), no FastAPI.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

from scripture_refs import normalize_for_fetch, parse_refs, split_alternatives

FORMAT = 1
GOSPELS = ("Matthew", "Mark", "Luke", "John")
DATA_DIR = Path(__file__).resolve().parent / "data" / "catena"

PAGE_IMAGE_URL = "https://archive.org/download/{identifier}/page/n{leaf}.jpg"
PAGE_VIEW_URL = "https://archive.org/details/{identifier}/page/n{leaf}/mode/1up"

# The verses of each chapter of the four Gospels, in the English Bible's numbering, which the
# Oxford printing follows: a section's verses lie within its chapters (the format checks).
VERSES: dict[str, tuple[int, ...]] = {
    "Matthew": (25, 23, 17, 25, 48, 34, 29, 34, 38, 42, 30, 50, 58, 36, 39, 28, 27, 35, 30, 34, 46, 46, 39, 51,
                46, 75, 66, 20),
    "Mark": (45, 28, 35, 41, 43, 56, 37, 38, 50, 52, 33, 44, 37, 72, 47, 20),
    "Luke": (80, 52, 38, 44, 39, 49, 50, 56, 62, 42, 54, 59, 35, 35, 32, 31, 37, 43, 48, 47, 38, 71, 56, 53),
    "John": (51, 25, 36, 54, 47, 71, 53, 59, 41, 42, 57, 50, 38, 31, 27, 33, 26, 40, 42, 31, 25),
}

# A section's keys: every section has the first set; a checked one also "checked" and "comments",
# and "errata" when the check applied the volume's printed errata (each entry as printed).
SECTION_KEYS = frozenset({"id", "start", "end", "volume", "pages", "leaves", "status"})
CHECKED_KEYS = frozenset({"checked", "comments"})
OPTIONAL_CHECKED_KEYS = frozenset({"errata"})
# A comment's keys; "printed_label" (optional) is the label as printed when the volume's errata
# correct it ("JEROME" where the errata read PSEUDO-JEROME).
COMMENT_KEYS = frozenset({"label", "father", "work", "text", "notes"})


@dataclass(frozen=True)
class Volume:
    key: str
    gospel: str
    identifier: str          # the archive.org item
    title: str               # as the title page names the volume
    year: int                # the title page's year
    translator: Optional[str]  # as the volume names its translator; None when it names none
    holder: str              # whose copy was scanned


VOLUMES: tuple[Volume, ...] = (
    Volume("mt1", "Matthew", "catenaaureacomme00thomuoft", "Vol. I, St. Matthew, Part I", 1841,
           "Mark Pattison", "University of Toronto"),
    Volume("mt2", "Matthew", "a6788682p201thomuoft", "Vol. I, St. Matthew, Part II", 1841,
           "Mark Pattison", "Saint Mary's College of California"),
    Volume("mt3", "Matthew", "catenaurecommpt301thomuoft", "Vol. I, St. Matthew, Part III", 1842,
           "Mark Pattison", "University of Toronto"),
    Volume("mk", "Mark", "catenaaureacomme02thomuoft", "Vol. II, St. Mark", 1842,
           "John Dobree Dalgairns", "University of Toronto"),
    Volume("lk1", "Luke", "catenaaureacomme03thomuoft", "Vol. III, St. Luke, Part I", 1843,
           "Thomas Dudley Ryder", "University of Toronto"),
    Volume("lk2", "Luke", "p2catenaaureacom03thomuoft", "Vol. III, St. Luke, Part II", 1843,
           "Thomas Dudley Ryder", "University of Toronto"),
    Volume("jn1", "John", "catenaaureacomme04thomuoft", "Vol. IV, St. John, Part I", 1845,
           None, "University of Toronto"),
    Volume("jn2", "John", "p2catenaaureacom04thomuoft", "Vol. IV, St. John, Part II", 1845,
           None, "University of Toronto"),
)

# The father each printed label names, for display and (V2) the "after {Name}" credit.
FATHERS = frozenset({
    "Alcuin", "Ambrose", "Athanasius", "Augustine", "Basil", "Bede", "Cassian", "Chrysostom",
    "Cyprian", "Cyril of Alexandria", "Didymus", "Dionysius", "Epiphanius", "Eusebius",
    "Gregory of Nazianzus", "Gregory of Nyssa", "Gregory the Great", "Haymo", "Hilary", "Isidore",
    "Jerome", "John of Damascus", "Leo the Great", "Maximus", "Origen", "Peter Chrysologus",
    "Pseudo-Athanasius", "Pseudo-Augustine", "Pseudo-Chrysostom", "Pseudo-Jerome", "Pseudo-Origen",
    "Rabanus Maurus", "Remigius", "Severianus", "Theophylact", "Titus of Bostra",
    "a Greek expositor", "the Gloss",
})

_ITALICS = re.compile(r"\*[^*\n]+\*")


class CatenaDataError(ValueError):
    """A data file breaks the format: a bug in the file, caught by the tests before it ships."""


@dataclass(frozen=True)
class Comment:
    """A father's comment, or (label and father None) the Catena's own words linking the comments,
    which Aquinas prints as a paragraph of their own ("It follows, *On these two commandments...*"):
    those are no father's and are never credited to one."""

    label: Optional[str]     # as printed, in small capitals, with its stop ("Jerome;", "Chrys.")
    father: Optional[str]    # one of FATHERS; None for the Catena's own linking words
    work: Optional[str]      # the margin reference beside the label ("Chrys. Hom. lxx."), as printed
    text: str                # as printed; *...* is italic; "\n\n" separates printed paragraphs
    notes: tuple[str, ...]   # the other margin notes beside it (Scripture references), as printed
    printed_label: Optional[str] = None   # the label as printed, when the volume's errata correct it

    @property
    def is_quotation(self) -> bool:
        return self.father is not None


@dataclass(frozen=True)
class Section:
    id: str
    gospel: str
    start: tuple[int, int]   # (chapter, verse)
    end: tuple[int, int]
    volume: Volume
    pages: tuple[int, int]   # the printed pages, first and last
    leaves: tuple[int, int]  # the scan's page indexes (archive.org's "n19"), first and last
    checked: Optional[dict]  # {"on": "YYYY-MM-DD", "by": "..."} once checked; None before
    comments: tuple[Comment, ...]
    errata: tuple[str, ...] = ()   # the volume's printed errata applied to this section, as printed

    @property
    def quotations(self) -> int:
        """The fathers' comments (not the Catena's own linking words)."""
        return sum(1 for c in self.comments if c.is_quotation)

    @property
    def reference(self) -> str:
        (c1, v1), (c2, v2) = self.start, self.end
        if c1 == c2:
            return f"{self.gospel} {c1}:{v1}" + (f"-{v2}" if v2 != v1 else "")
        return f"{self.gospel} {c1}:{v1}-{c2}:{v2}"


def section_id(gospel: str, start: tuple[int, int], end: tuple[int, int]) -> str:
    """"matthew-22-15-22"; a section across chapters "matthew-16-28-17-9"."""
    (c1, v1), (c2, v2) = start, end
    tail = f"{v2}" if c1 == c2 else f"{c2}-{v2}"
    return f"{gospel.lower()}-{c1}-{v1}-{tail}"


def data_path(gospel: str) -> Path:
    return DATA_DIR / f"{gospel.lower()}.json"


def volume(key: str) -> Volume:
    for v in VOLUMES:
        if v.key == key:
            return v
    raise KeyError(key)


def page_image_url(v: Volume, leaf: int) -> str:
    return PAGE_IMAGE_URL.format(identifier=v.identifier, leaf=leaf)


def page_view_url(v: Volume, leaf: int) -> str:
    return PAGE_VIEW_URL.format(identifier=v.identifier, leaf=leaf)


def _gospel_spans(reference: str) -> list:
    """The Gospel spans of the first alternative that names a Gospel, all of its first Gospel.
    Optional verses in parentheses count as read ("Luke 2:1-14 (15-20)", "John 1:(1-9) 10-18")."""
    for alternative in split_alternatives(reference):
        spans = [s for s in parse_refs(normalize_for_fetch(alternative)).spans if s.book in GOSPELS]
        if spans:
            return [s for s in spans if s.book == spans[0].book]
    return []


def parse_gospel_reference(reference: str) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    """The Gospel passages of a reference as (start, end) pairs, all of one Gospel (the first named)."""
    return [(s.start, s.end) for s in _gospel_spans(reference)]


def gospel_of(reference: str) -> Optional[str]:
    spans = _gospel_spans(reference)
    return spans[0].book if spans else None


def _comment(raw: dict, where: str) -> Comment:
    if not COMMENT_KEYS <= set(raw) <= COMMENT_KEYS | {"printed_label"}:
        raise CatenaDataError(f"{where}: a comment has the keys label, father, work, text, notes (and printed_label)")
    if raw["father"] is None:
        if raw["label"] is not None or raw["work"] is not None or "printed_label" in raw:
            raise CatenaDataError(f"{where}: the Catena's own words have no label, work or printed label")
    elif raw["father"] not in FATHERS:
        raise CatenaDataError(f"{where}: unknown father {raw['father']!r}")
    elif not isinstance(raw["label"], str) or not raw["label"]:
        raise CatenaDataError(f"{where}: an empty label")
    if "printed_label" in raw and (not isinstance(raw["printed_label"], str) or not raw["printed_label"].strip()):
        raise CatenaDataError(f"{where}: an empty printed label")
    if not isinstance(raw["notes"], list) or not all(isinstance(n, str) and n.strip() for n in raw["notes"]):
        raise CatenaDataError(f"{where}: notes are a list of margin notes")
    text = raw["text"]
    if not isinstance(text, str) or not text.strip() or text != text.strip():
        raise CatenaDataError(f"{where}: empty text, or spaces around it")
    if re.search(r"(?<!\n)\n(?!\n)|\n{3,}|  ", text):
        raise CatenaDataError(f"{where}: a line break or a double space inside the text")
    if _ITALICS.sub("", text).count("*"):
        raise CatenaDataError(f"{where}: an italic marker without its pair")
    if raw["work"] is not None and (not isinstance(raw["work"], str) or not raw["work"].strip()):
        raise CatenaDataError(f"{where}: an empty work")
    return Comment(raw["label"], raw["father"], raw["work"], text, tuple(raw["notes"]), raw.get("printed_label"))


def _pair(value, where: str, what: str) -> tuple[int, int]:
    if not (isinstance(value, list) and len(value) == 2 and all(type(n) is int and n > 0 for n in value)):
        raise CatenaDataError(f"{where}: {what} is two positive numbers")
    return value[0], value[1]


def parse(data: dict, gospel: str) -> tuple[Section, ...]:
    """A data file's sections, checked against the format (CatenaDataError on any break)."""
    if data.get("format") != FORMAT or data.get("gospel") != gospel:
        raise CatenaDataError(f"{gospel}: format {data.get('format')!r} for {data.get('gospel')!r}")
    out: list[Section] = []
    seen: set[str] = set()
    verses = VERSES[gospel]
    for raw in data["sections"]:
        where = f"{gospel} {raw.get('id')}"
        allowed = SECTION_KEYS | (CHECKED_KEYS | OPTIONAL_CHECKED_KEYS if raw.get("status") == "checked" else set())
        required = SECTION_KEYS | (CHECKED_KEYS if raw.get("status") == "checked" else set())
        if not required <= set(raw) <= allowed:
            raise CatenaDataError(f"{where}: the keys {sorted(set(raw) ^ required)} (a draft's footnotes or "
                                  "warnings never go in the file)")
        start, end = _pair(raw["start"], where, "start"), _pair(raw["end"], where, "end")
        for chapter, verse in (start, end):
            if chapter > len(verses) or verse > verses[chapter - 1]:
                raise CatenaDataError(f"{where}: {chapter}:{verse} is not a verse of {gospel}")
        if end[0] - start[0] > 1:
            raise CatenaDataError(f"{where}: a section spans more than two chapters")
        pages, leaves = _pair(raw["pages"], where, "pages"), _pair(raw["leaves"], where, "leaves")
        if pages[0] > pages[1] or leaves[0] > leaves[1]:
            raise CatenaDataError(f"{where}: pages and leaves run forwards")
        base = section_id(gospel, start, end)
        if not re.fullmatch(re.escape(base) + r"(-[2-9])?", raw["id"]) or not start <= end:
            raise CatenaDataError(f"{where}: the id does not match the verses")
        if raw["id"] in seen:
            raise CatenaDataError(f"{where}: the id is used twice")
        seen.add(raw["id"])
        v = volume(raw["volume"])
        if v.gospel != gospel:
            raise CatenaDataError(f"{where}: volume {v.key} is not {gospel}")
        if out and (start, end) < (out[-1].start, out[-1].end):
            raise CatenaDataError(f"{where}: out of order after {out[-1].id}")
        status = raw["status"]
        errata: tuple[str, ...] = ()
        if status == "checked":
            checked = raw["checked"]
            if (not isinstance(checked, dict) or set(checked) != {"on", "by"}
                    or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(checked["on"]))
                    or not isinstance(checked["by"], str) or not checked["by"].strip() or "@" in checked["by"]):
                raise CatenaDataError(f"{where}: checked is on (YYYY-MM-DD) and by (a role, no email address)")
            comments = tuple(_comment(c, where) for c in raw["comments"])
            if not any(c.is_quotation for c in comments):
                raise CatenaDataError(f"{where}: a checked section with no comments")
            errata = tuple(raw.get("errata", ()))
            if "errata" in raw and (not errata or not all(isinstance(e, str) and e.strip() for e in errata)):
                raise CatenaDataError(f"{where}: errata are the entries applied, as printed")
        elif status == "unchecked":
            checked, comments = None, ()
        else:
            raise CatenaDataError(f"{where}: status {status!r}")
        out.append(Section(raw["id"], gospel, start, end, v, pages, leaves, checked, comments, errata))
    return tuple(out)


@lru_cache(maxsize=len(GOSPELS))
def load(gospel: str) -> tuple[Section, ...]:
    """A Gospel's sections, read from its data file on first use and kept (the file ships with the app)."""
    return parse(json.loads(data_path(gospel).read_text(encoding="utf-8")), gospel)


def sections_for(reference: str) -> tuple[Section, ...]:
    """The sections that share at least one verse with the reference's Gospel passages, in order."""
    gospel = gospel_of(reference)
    if gospel is None:
        return ()
    spans = parse_gospel_reference(reference)
    return tuple(s for s in load(gospel)
                 if any(s.start <= end and start <= s.end for start, end in spans))


# The panel's credit line: the edition, the Gospel's volume, its translator as the volume names
# them, and the copies scanned (rights check §1; never CCEL's "William Whiston").
_GOSPEL_VOLUME = {"Matthew": "vol. I, St. Matthew", "Mark": "vol. II, St. Mark",
                  "Luke": "vol. III, St. Luke", "John": "vol. IV, St. John"}


def credit(gospel: str, shown: tuple[Section, ...] = ()) -> str:
    """"From the Catena Aurea of Thomas Aquinas, vol. I, St. Matthew, translated by Mark Pattison,
    edited by John Henry Newman (Oxford: John Henry Parker, 1841-42). Scanned from the University
    of Toronto's copy at archive.org." The copies are those of the sections shown (else the
    Gospel's)."""
    volumes = [v for v in VOLUMES if v.gospel == gospel]
    years = sorted({v.year for v in volumes})
    span = str(years[0]) if len(years) == 1 else f"{years[0]}-{str(years[-1])[2:]}"
    translator = volumes[0].translator
    translated = f"translated by {translator}" if translator else "translator not named in the volume"
    holders = list(dict.fromkeys(s.volume.holder for s in shown)) or list(dict.fromkeys(v.holder for v in volumes))
    copies = " and ".join(f"{h}'s" for h in holders) + (" copy" if len(holders) == 1 else " copies")
    return (f"From the Catena Aurea of Thomas Aquinas, {_GOSPEL_VOLUME[gospel]}, {translated}, edited by "
            f"John Henry Newman (Oxford: John Henry Parker, {span}). Scanned from the {copies} at archive.org.")
