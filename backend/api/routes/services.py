"""The archive: /services (slice 5a spec, API; owner answers 4 and 6, 2026-10-01).

Church-scoped; any member may save, open and delete (owner decision 5). Plain
`def` routes that each make one usecase call (F §2.2 rule 1), with no SQL and
no try/except.
- POST /services: 201 ServiceOut. An Idempotency-Key replays the first answer
  for the same user in the same church (F §1.6 and its church-scope
  amendment): run_idempotent gets church.id.
- PUT /services/{id}: If-Match carries the saved_at last received ("*"
  saves over whatever is there); 404, then 422 (If-Match missing or
  unreadable, a list of several included), then 409, then the body's own errors.
- DELETE /services/{id}: {"deleted": true}; the date's hymn use is then
  recalculated from the services still saved for it (owner answer 6).
- GET /services: 20 a page by default, newest service date first, undated last.
"""
import uuid
from dataclasses import asdict
from typing import Optional

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import Response

from api.deps import ActiveChurch, CurrentUser, get_current_user, require_church
from api.errors import error_responses
from api.idempotency import idempotency_key, run_idempotent
from api.schemas import DeletedOut, Page, ServiceDraft, ServiceOut, ServiceSummary
from usecases import archive

router = APIRouter()


def service_out(record: archive.ServiceRecord) -> ServiceOut:
    return ServiceOut(**asdict(record))


@router.get("/services", response_model=Page[ServiceSummary], responses=error_responses(401, 403, 422, 503))
def list_services(
    church: ActiveChurch = Depends(require_church),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0, le=1_000_000),
) -> Page[ServiceSummary]:
    page = archive.list_services(church.id, limit=limit, offset=offset)
    return Page[ServiceSummary](items=[ServiceSummary(**asdict(item)) for item in page.items], total=page.total,
                                limit=page.limit, offset=page.offset)


@router.get("/services/{service_id}", response_model=ServiceOut, responses=error_responses(401, 403, 404, 422, 503))
def get_service(service_id: uuid.UUID, church: ActiveChurch = Depends(require_church)) -> ServiceOut:
    return service_out(archive.get_service(church.id, service_id))


@router.post("/services", status_code=201, response_model=ServiceOut,
             responses=error_responses(401, 403, 404, 422, 503))
def create_service(
    payload: ServiceDraft,
    user: CurrentUser = Depends(get_current_user),
    church: ActiveChurch = Depends(require_church),
    key: Optional[uuid.UUID] = Depends(idempotency_key()),
) -> Response:
    return run_idempotent(
        user_id=user.id,
        church_id=church.id,
        route="/services",
        key=key,
        payload=payload,
        status_code=201,
        call=lambda: service_out(archive.create_service(church.id, user.id, payload.to_input())),
    )


@router.put("/services/{service_id}", response_model=ServiceOut,
            responses=error_responses(401, 403, 404, 409, 422, 503))
def replace_service(
    service_id: uuid.UUID,
    payload: ServiceDraft,
    church: ActiveChurch = Depends(require_church),
    if_match: Optional[str] = Header(default=None, alias="If-Match"),
) -> ServiceOut:
    return service_out(archive.replace_service(church.id, service_id, payload.to_input(), if_match=if_match))


@router.delete("/services/{service_id}", response_model=DeletedOut,
               responses=error_responses(401, 403, 404, 422, 503))
def delete_service(service_id: uuid.UUID, church: ActiveChurch = Depends(require_church)) -> DeletedOut:
    archive.delete_service(church.id, service_id)
    return DeletedOut()
