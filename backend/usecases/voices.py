"""Voices of the Church: the Catena's comments on a Gospel passage (Voices V1 spec "The API").

Reads the shipped data files through `catena` (each read once, then kept); no database, no AI,
no upstream call. No FastAPI, no Streamlit (tests/test_no_streamlit_in_core.py).
"""
from dataclasses import dataclass

import catena
from domain_errors import InvalidInput

NOT_A_GOSPEL = "Choose a passage from Matthew, Mark, Luke or John."
CHECK = "Check the chapter and verse."


@dataclass(frozen=True)
class Voices:
    reference: str
    gospel: str
    sections: tuple[catena.Section, ...]
    credit: str

    @property
    def quotation_count(self) -> int:
        """The fathers' comments; the Catena's own linking words are not a quotation."""
        return sum(s.quotations for s in self.sections)


def voices_for(reference: str) -> Voices:
    """The sections sharing a verse with the reference's passages in its first Gospel, checked or
    not, in order. A reference with no Gospel passage is a 422 naming `reference`, and so is one
    whose verses lie outside the Gospel ("Matthew 29:1", "Matthew 22:99"): every verse of a Gospel
    is in a section, so no section means no such verse."""
    gospel = catena.gospel_of(reference)
    if gospel is None:
        raise InvalidInput(NOT_A_GOSPEL, field="reference")
    sections = catena.sections_for(reference)
    if not sections:
        raise InvalidInput(_outside(gospel, catena.parse_gospel_reference(reference)), field="reference")
    return Voices(reference=reference, gospel=gospel, sections=sections, credit=catena.credit(gospel, sections))


def _outside(gospel: str, passages: list) -> str:
    """"Matthew has 28 chapters. ..." or "Matthew 22 has 46 verses. ..." for the first passage."""
    verses = catena.VERSES[gospel]
    chapter = passages[0][0][0]
    if not 1 <= chapter <= len(verses):
        return f"{gospel} has {len(verses)} chapters. {CHECK}"
    return f"{gospel} {chapter} has {verses[chapter - 1]} verses. {CHECK}"
