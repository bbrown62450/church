"""The cover pictures (printed bulletin spec, "Data model"; PR 3 planning
answers 5, 8, 9; PR 3a).

- upload(church_id, user_id, data): POST /bulletin-images. The upload is
  checked and made ready to store first (bulletin_image.prepare: a 422 naming
  "image" touches no table; a 429 when another picture is being prepared).
  Then the old unused pictures of every church are removed, at most
  REMOVE_BATCH (planning answer 9; remove_unused), in a transaction of its
  own. Then, in one transaction: when the church already keeps MAX_PICTURES,
  its oldest pictures no saved service points at make room (make_room;
  every one in use: a 422, CHURCH_FULL_MESSAGE); when every church's
  pictures together would pass STORAGE_BUDGET, a 422 (STORAGE_FULL_MESSAGE,
  and a warning in the log); else the new one is stored.
- picture(church_id, image_id, if_none_match): GET /bulletin-images/{id}:
  the church's picture with its ETag, without its bytes when the browser
  already has them (If-None-Match), or a 404 (another church's id included,
  F §1.2 rule 2).
- remove_unused(session, now): the removal. A picture younger than
  RETENTION is never removed, so a draft's picture not saved yet (a draft
  lives in one browser) has 60 days; one a saved service of its church
  points at is never removed, whatever its age. It runs on every upload, of
  any church, so nothing has to run on a schedule and a church that stops
  uploading still loses its unused pictures; each upload removes at most
  REMOVE_BATCH, so one call stays short. It reads the stored bulletins of
  every church that has a picture older than RETENTION (a few hundred small
  rows at this size).
- in_use(session, church_id): the ids the church's saved services point at.
Each removal locks its candidates before it reads in_use, and a save locks
the picture it points at (repos.bulletin_images, plan review I5).
Logs carry ids, counts and sizes, never a picture (F §2.5).
"""
from __future__ import annotations

import datetime
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Optional

import bulletin_image
from db import session_scope
from db.ids import as_uuid
from domain_errors import InvalidInput, NotFound
from repos import bulletin_images as images_repo
from repos import services as services_repo
from service_bulletin import read as read_bulletin

logger = logging.getLogger(__name__)

RETENTION = datetime.timedelta(days=60)
REMOVE_BATCH = 20                     # old unused pictures removed on one upload, at most (every church)
MAX_PICTURES = 160                    # one church's stored pictures, at most
STORAGE_BUDGET = 150_000_000          # every church's pictures together, at most (bytes; plan review C3)

GONE_MESSAGE = "That picture is no longer available."
CHURCH_FULL_MESSAGE = (f"Your church keeps {MAX_PICTURES} pictures, all in saved services. Remove the picture "
                       "from an older service, then try again.")
STORAGE_FULL_MESSAGE = "The app has no room for more pictures right now. Please tell the app's administrator."


@dataclass(frozen=True)
class UploadedImage:
    id: uuid.UUID
    width: int
    height: int


@dataclass(frozen=True)
class Picture:
    etag: str                         # the id, quoted: a picture's id never names other bytes
    content_type: str
    content: Optional[bytes]          # None: the browser's copy is current (a 304)


def in_use(session, church_id: uuid.UUID) -> set[str]:
    """The picture ids the church's saved services point at (a stored bulletin's cover_image_id)."""
    ids = (read_bulletin(raw).cover_image_id for raw in services_repo.stored_bulletins(church_id, session=session))
    return {image_id for image_id in ids if image_id}


def _unused(session, church_id: uuid.UUID, cutoff: Optional[datetime.datetime]) -> list[uuid.UUID]:
    """The church's pictures (uploaded before `cutoff`, when given) no saved service points at, oldest first:
    locked first, then checked against the saved services, so a save in between is seen."""
    candidates = images_repo.ids_created_before(church_id, cutoff, session=session, lock=True)
    if not candidates:
        return []
    used = in_use(session, church_id)
    return [i for i in candidates if str(i) not in used]


def remove_unused(session, now: datetime.datetime, *, limit: Optional[int] = None) -> int:
    """Remove up to `limit` (REMOVE_BATCH) pictures, of any church, uploaded more than RETENTION before `now`
    that no saved service of their church points at; the church with the oldest such picture first."""
    limit = REMOVE_BATCH if limit is None else limit
    cutoff = now - RETENTION
    removed = 0
    for church_id in images_repo.churches_with_pictures_before(cutoff, session=session):
        if removed >= limit:
            break
        gone = _unused(session, church_id, cutoff)[:limit - removed]
        removed += images_repo.delete_images(church_id, gone, session=session)
    return removed


def make_room(session, church_id: uuid.UUID) -> int:
    """Below MAX_PICTURES after this: the church's oldest unused pictures removed, whatever their age."""
    over = images_repo.count_images(church_id, session=session) - MAX_PICTURES + 1
    if over <= 0:
        return 0
    unused = _unused(session, church_id, None)
    if len(unused) < over:
        raise InvalidInput(CHURCH_FULL_MESSAGE, field="image")
    return images_repo.delete_images(church_id, unused[:over], session=session)


def upload(church_id: uuid.UUID, user_id: uuid.UUID, data: bytes) -> UploadedImage:
    started = time.monotonic()
    cid = as_uuid(church_id)
    prepared = bulletin_image.prepare(data)
    with session_scope() as s:
        removed = remove_unused(s, datetime.datetime.now(datetime.timezone.utc))
    with session_scope() as s:
        removed += make_room(s, cid)
        total = images_repo.total_bytes(session=s)
        if total + len(prepared.content) > STORAGE_BUDGET:
            logger.warning("bulletin_images.storage_full church=%s total=%d budget=%d", cid, total,
                           STORAGE_BUDGET)
            raise InvalidInput(STORAGE_FULL_MESSAGE, field="image")
        row = images_repo.insert_image(cid, user_id, content_type=bulletin_image.CONTENT_TYPE,
                                       content=prepared.content, width=prepared.width, height=prepared.height,
                                       session=s)
        result = UploadedImage(row.id, row.width, row.height)
    logger.info("bulletin_images.upload church=%s image=%s bytes_in=%d bytes=%d size=%dx%d removed=%d ms=%d", cid,
                result.id, len(data), len(prepared.content), result.width, result.height, removed,
                round((time.monotonic() - started) * 1000))
    return result


def _matches(if_none_match: Optional[str], etag: str) -> bool:
    tags = [tag.strip().removeprefix("W/") for tag in (if_none_match or "").split(",")]
    return etag in tags or "*" in tags


def picture(church_id: uuid.UUID, image_id: uuid.UUID, if_none_match: Optional[str] = None) -> Picture:
    etag = f'"{image_id}"'
    with session_scope() as s:
        if _matches(if_none_match, etag):
            found = images_repo.has_image(church_id, image_id, session=s)
            answer = Picture(etag, bulletin_image.CONTENT_TYPE, None) if found else None
        else:
            stored = images_repo.get_picture(church_id, image_id, session=s)
            answer = None if stored is None else Picture(etag, stored.content_type, stored.content)
    if answer is None:
        raise NotFound(GONE_MESSAGE)
    return answer
