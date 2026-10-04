"""The cover pictures, church-scoped (printed bulletin spec, "Data model";
PR 3a; table bulletin_images, migration 0007_bulletin_images).

Every query of one church's pictures filters on church_id, so another
church's picture is simply absent (the usecase's 404, or no picture
printed); the two that look at every church's (churches_with_pictures_before
and total_bytes, for the removal and the storage budget) return no picture.
Each function runs in the caller's session (F §2.2 rule 3);
usecases.bulletin_images, usecases.archive and usecases.documents own the
transactions. The picture's bytes are read only by get_picture (a projection
elsewhere, so a list never loads them).

Locks (plan review I5; PR 3a build review M1, M3): the removal takes the
pictures it is about to remove `FOR UPDATE` (lock_images) and then reads again
which pictures the saved services point at, and a save takes the picture it
points at `FOR SHARE` (has_image with lock=True), so a save never points at a
picture being removed: one waits for the other. A picture in use is never
locked by the removal. lock_uploads (a transaction-level advisory lock on
Postgres) makes one upload at a time count the church's pictures, make room,
check the storage budget and store. SQLite ignores all three (one writer at
a time).
"""
import datetime
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from db.ids import as_uuid
from db.models import BulletinImage


@dataclass(frozen=True)
class StoredPicture:
    content_type: str
    content: bytes


def insert_image(church_id, created_by, *, content_type: str, content: bytes, width: int, height: int,
                 session: Session) -> BulletinImage:
    """Add a picture; flushed, so it has its id and created_at."""
    row = BulletinImage(church_id=as_uuid(church_id), created_by=None if created_by is None else as_uuid(created_by),
                        content_type=content_type, bytes=content, width=width, height=height)
    session.add(row)
    session.flush()
    return row


def get_picture(church_id, image_id, *, session: Session) -> Optional[StoredPicture]:
    """The church's picture with this id (its type and bytes), or None."""
    row = session.execute(select(BulletinImage.content_type, BulletinImage.bytes).where(
        BulletinImage.id == as_uuid(image_id), BulletinImage.church_id == as_uuid(church_id))).first()
    return None if row is None else StoredPicture(row.content_type, bytes(row.bytes))


def has_image(church_id, image_id, *, session: Session, lock: bool = False) -> bool:
    """Whether the church has this picture; with lock, it is held (FOR SHARE) until the transaction ends."""
    query = select(BulletinImage.id).where(
        BulletinImage.id == as_uuid(image_id), BulletinImage.church_id == as_uuid(church_id))
    return session.execute(query.with_for_update(read=True) if lock else query).first() is not None


def ids_created_before(church_id, cutoff: Optional[datetime.datetime] = None, *,
                       session: Session) -> list[uuid.UUID]:
    """The church's pictures, oldest first, those uploaded before `cutoff` only when given
    (ix_bulletin_images_church_created). No lock."""
    query = select(BulletinImage.id).where(BulletinImage.church_id == as_uuid(church_id))
    if cutoff is not None:
        query = query.where(BulletinImage.created_at < cutoff)
    return list(session.execute(query.order_by(BulletinImage.created_at, BulletinImage.id)).scalars())


def lock_images(church_id, image_ids: Iterable[uuid.UUID], *, session: Session) -> list[uuid.UUID]:
    """These pictures of the church that are still there, oldest first, held FOR UPDATE until the
    transaction ends (a save's FOR SHARE on one waits, and this waits for one)."""
    ids = [as_uuid(i) for i in image_ids]
    if not ids:
        return []
    return list(session.execute(select(BulletinImage.id).where(
        BulletinImage.church_id == as_uuid(church_id), BulletinImage.id.in_(ids))
        .order_by(BulletinImage.created_at, BulletinImage.id).with_for_update()).scalars())


def lock_uploads(*, session: Session) -> None:
    """One upload at a time, every church, until the transaction ends: its count, room-making, budget check
    and insert (a transaction-level advisory lock on Postgres; SQLite has one writer at a time)."""
    if session.get_bind().dialect.name == "postgresql":
        session.execute(text("SELECT pg_advisory_xact_lock(hashtext('bulletin_images.upload'))"))


def churches_with_pictures_before(cutoff: datetime.datetime, *, session: Session) -> list[uuid.UUID]:
    """Every church with a picture uploaded before `cutoff`, the one with the oldest first."""
    oldest = func.min(BulletinImage.created_at)
    return list(session.execute(select(BulletinImage.church_id).where(BulletinImage.created_at < cutoff)
                                .group_by(BulletinImage.church_id).order_by(oldest)).scalars())


def count_images(church_id, *, session: Session) -> int:
    return int(session.execute(select(func.count()).select_from(BulletinImage).where(
        BulletinImage.church_id == as_uuid(church_id))).scalar_one())


def total_bytes(*, session: Session) -> int:
    """Every church's pictures together, in bytes (Postgres reads each size without the picture)."""
    return int(session.execute(select(func.coalesce(func.sum(func.length(BulletinImage.bytes)), 0))).scalar_one())


def delete_images(church_id, image_ids: Iterable[uuid.UUID], *, session: Session) -> int:
    """Remove these pictures of the church; how many went."""
    ids = [as_uuid(i) for i in image_ids]
    if not ids:
        return 0
    result = session.execute(delete(BulletinImage).where(
        BulletinImage.church_id == as_uuid(church_id), BulletinImage.id.in_(ids)))
    return int(result.rowcount or 0)
