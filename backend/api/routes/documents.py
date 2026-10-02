"""POST /documents: the bulletin copy or the pastor's copy of the posted
service as a Word file (slice 5a spec, API; F §1.9).

Church-scoped; any member may download (owner decision 5). A pure render of
the body, so no Idempotency-Key and no rate-limit bucket (F §1.8: local work,
well under 3 s); the client waits up to 30 s. Errors are the usual JSON: 404
with details.field for a hymn id the church does not have, 422 for the body,
a logged 500 when python-docx is missing. Plain `def` (F §1.8), no SQL and no
try/except (F §2.2 rule 1).

POST /documents/printed (printed bulletin spec, PR 1): the printed bulletin,
two booklet pages to a legal sheet, as a print-ready PDF or an editable Word file. Its own
route because its body (format, translation) and its answer differ; it
fetches the readings' text, so it charges the `scripture` bucket one token
per upstream part (a 429 before any fetch), as POST /scripture/passages.
"""
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, StringConstraints

import printed_bulletin
import service_output
from api import ratelimit
from api.deps import ActiveChurch, CurrentUser, get_current_user, require_church
from api.errors import error_responses
from api.schemas import ServiceDraft
from usecases import documents

router = APIRouter()


class DocumentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variant: Literal["bulletin", "pastor"]
    service: ServiceDraft


DOCX_RESPONSE = {200: {"description": "The Word file (Content-Disposition names it).",
                       "content": {service_output.DOCX_MIME: {"schema": {"type": "string", "format": "binary"}}}}}


@router.post("/documents", response_class=Response,
             responses={**DOCX_RESPONSE, **error_responses(401, 403, 404, 422, 503)})
def create_document(payload: DocumentIn, church: ActiveChurch = Depends(require_church)) -> Response:
    """Built from the body every time; nothing is stored or cached (owner decision 4)."""
    result = documents.build_document(church.id, payload.service.to_input(), payload.variant)
    return Response(content=result.content, media_type=service_output.DOCX_MIME, headers={
        "Content-Disposition": service_output.content_disposition(result.filename),
        "Cache-Control": "no-store",
    })


class PrintedDocumentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: Literal["pdf", "docx"]
    # The draft's translation (null: the church's); one this deployment does not offer prints in the church's.
    translation: Optional[Annotated[str, StringConstraints(strip_whitespace=True, max_length=20)]] = None
    service: ServiceDraft


PRINTED_RESPONSE = {200: {"description": "The printed bulletin (Content-Disposition names it).",
                          "content": {printed_bulletin.PDF_MIME: {"schema": {"type": "string", "format": "binary"}},
                                      service_output.DOCX_MIME: {"schema": {"type": "string", "format": "binary"}}}}}
MEDIA_TYPES = {"pdf": printed_bulletin.PDF_MIME, "docx": service_output.DOCX_MIME}


@router.post("/documents/printed", response_class=Response,
             responses={**PRINTED_RESPONSE, **error_responses(401, 403, 404, 422, 429, 503)})
def create_printed(payload: PrintedDocumentIn, church: ActiveChurch = Depends(require_church),
                   user: CurrentUser = Depends(get_current_user)) -> Response:
    """Built from the body every time; nothing is stored or cached."""
    result = documents.build_printed(
        church.id, payload.service.to_input(), payload.format, payload.translation,
        charge=lambda n: ratelimit.consume("scripture", user_id=user.id, cost=n))
    return Response(content=result.content, media_type=MEDIA_TYPES[payload.format], headers={
        "Content-Disposition": service_output.content_disposition(result.filename),
        "Cache-Control": "no-store",
    })
