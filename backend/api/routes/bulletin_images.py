"""The cover pictures: /bulletin-images (printed bulletin spec, API; PR 3
planning answers 5, 8, 9; PR 3a).

Church-scoped; any member may upload and see one (planning answer 8: every
member can edit a service). Plain `def` routes that each make one usecase
call (F §2.2 rule 1), with no SQL and no try/except.
- POST /bulletin-images: the picture itself is the request body (a JPEG or
  a PNG of at most 10 MB, any Content-Type but JSON; no multipart, so no
  python-multipart: it is installed here only through Streamlit). 201
  {id, width, height}. 422 naming "image" for anything else
  (api.middleware.UploadSizeMiddleware refuses a body over 10 MB before it
  is read; with no Content-Type the body is taken too, with
  application/json it is a 400). The `picture` bucket (F §1.8): 20 an hour
  a member, 60 a day a church; a 429 also when another picture is being
  prepared (bulletin_image). A church keeps at most 160 pictures, and all
  churches' pictures together at most 150 MB (a 422 past either;
  usecases.bulletin_images). No Idempotency-Key: a retried upload stores a
  second copy, which the 60-day removal takes.
- GET /bulletin-images/{id}: the church's picture (image/jpeg). The browser
  keeps it only privately and asks again each time (`private, no-cache`,
  `Vary: Authorization, X-Church-Id`), with its ETag, the id: a 304 without
  the bytes when it has them (plan review I4). `nosniff`. 404 for an id
  the church does not have.
"""
import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Body, Depends, Header
from fastapi.responses import Response

from api import ratelimit
from api.deps import ActiveChurch, CurrentUser, get_current_user, require_church
from api.errors import error_responses
from api.schemas import BulletinImageOut
from usecases import bulletin_images

router = APIRouter()

PICTURE_RESPONSE = {200: {"description": "The picture (a JPEG).",
                          "content": {"image/jpeg": {"schema": {"type": "string", "format": "binary"}}}},
                    304: {"description": "Not modified: the browser's copy (If-None-Match) is current."}}
# Kept by the browser only, for this sign-in and church, and checked again on each use (a 304 is cheap).
PICTURE_HEADERS = {"Cache-Control": "private, no-cache", "Vary": "Authorization, X-Church-Id",
                   "X-Content-Type-Options": "nosniff"}


@router.post("/bulletin-images", status_code=201, response_model=BulletinImageOut,
             responses=error_responses(401, 403, 422, 429, 503))
def upload_image(
    # An empty body is not refused by the framework, so the sign-in and the church are checked first and
    # bulletin_image says "Choose a JPEG or PNG picture." (an iCloud photo not downloaded yet is 0 bytes).
    image: Annotated[bytes, Body(media_type="application/octet-stream")] = b"",
    user: CurrentUser = Depends(get_current_user),
    church: ActiveChurch = Depends(require_church),
    _limit: None = Depends(ratelimit.rate_limit("picture")),
) -> BulletinImageOut:
    uploaded = bulletin_images.upload(church.id, user.id, image)
    return BulletinImageOut(id=uploaded.id, width=uploaded.width, height=uploaded.height)


@router.get("/bulletin-images/{image_id}", response_class=Response,
            responses={**PICTURE_RESPONSE, **error_responses(401, 403, 404, 422, 503)})
def get_image(image_id: uuid.UUID, church: ActiveChurch = Depends(require_church),
              if_none_match: Annotated[Optional[str], Header()] = None) -> Response:
    found = bulletin_images.picture(church.id, image_id, if_none_match)
    headers = {**PICTURE_HEADERS, "ETag": found.etag}
    if found.content is None:
        return Response(status_code=304, headers=headers)
    return Response(content=found.content, media_type=found.content_type, headers=headers)
