"""GET /voices: the fathers on a Gospel passage, from the Catena Aurea (Voices V1 spec "The API").

User-scoped reference data, like GET /translations: the route depends on get_current_user and
never on require_church, so X-Church-Id is ignored (F §1.2). No rate-limit bucket: the answer
is static text read from the shipped files, with no AI and no upstream call. The browser may keep
it for an hour (`private, max-age=3600`): the text changes only with a deploy. Plain `def`, one
usecase call (F §2.2 rule 1).
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

import catena
from api.deps import CurrentUser, get_current_user
from api.errors import error_responses
from api.schemas import VoiceCommentOut, VoiceSectionOut, VoicesOut
from usecases import voices

router = APIRouter()

CACHE_CONTROL = "private, max-age=3600"


def _section(section: catena.Section) -> VoiceSectionOut:
    first, last = section.pages
    v = section.volume
    return VoiceSectionOut(
        id=section.id,
        reference=section.reference,
        pages=f"{first}-{last}" if last != first else str(first),
        volume=f"{v.title} ({v.year})",
        scan_url=catena.page_view_url(v, section.leaves[0]),
        status="checked" if section.checked else "unchecked",
        comments=[VoiceCommentOut(label=c.label, father=c.father, work=c.work, text=c.text, notes=list(c.notes),
                                  printed_label=c.printed_label)
                  for c in section.comments],
    )


@router.get("/voices", response_model=VoicesOut, responses=error_responses(401, 422, 503))
def read_voices(
    response: Response,
    reference: Annotated[str, Query(min_length=1, max_length=200)],
    user: CurrentUser = Depends(get_current_user),
) -> VoicesOut:
    found = voices.voices_for(reference)
    response.headers["Cache-Control"] = CACHE_CONTROL
    return VoicesOut(reference=found.reference, gospel=found.gospel, quotation_count=found.quotation_count,
                     credit=found.credit, sections=[_section(s) for s in found.sections])
