"""Voices of the Church: the Catena's comments on a Gospel passage (Voices V1 spec "The API").

Reads the shipped data files through `catena` (each read once, then kept); no database, no AI,
no upstream call. No FastAPI, no Streamlit (tests/test_no_streamlit_in_core.py).
"""
from dataclasses import dataclass

import catena
from domain_errors import InvalidInput

NOT_A_GOSPEL = "Choose a passage from Matthew, Mark, Luke or John."


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
    not, in order. A reference with no Gospel passage is a 422 naming `reference`."""
    gospel = catena.gospel_of(reference)
    if gospel is None:
        raise InvalidInput(NOT_A_GOSPEL, field="reference")
    sections = catena.sections_for(reference)
    return Voices(reference=reference, gospel=gospel, sections=sections, credit=catena.credit(gospel, sections))
