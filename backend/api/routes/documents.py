"""POST /documents: the bulletin copy or the pastor's copy of the posted
service as a Word file (slice 5a spec, API; F §1.9).

Church-scoped; any member may download (owner decision 5). A pure render of
the body, so no Idempotency-Key and no rate-limit bucket (F §1.8: local work,
well under 3 s); the client waits up to 30 s. Errors are the usual JSON: 404
with details.field for a hymn id the church does not have, 422 for the body,
a logged 500 when python-docx is missing. Plain `def` (F §1.8), no SQL and no
try/except (F §2.2 rule 1).
"""
from typing import Literal

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict

import service_output
from api.deps import ActiveChurch, require_church
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
