"""Saved services, church-scoped (slice 5a-2; 5a spec "Data access and tenancy").

Every query filters on church_id, so another church's service is simply
absent (the usecase's 404). Each function runs in the caller's session, or
its own when none is given (F §2.2 rule 3); usecases.archive owns the
transactions. service_archive.py stays as the frozen Streamlit branch left it
(slice 7 deletes it).
"""
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db import session_scope
from db.ids import as_uuid
from db.models import Service, User


@dataclass(frozen=True)
class SummaryRow:
    """One row of the archive list: no JSON columns (a projection)."""
    id: uuid.UUID
    service_date_iso: Optional[str]
    service_date_display: Optional[str]
    occasion: Optional[str]
    sermon_title: Optional[str]
    saved_at: datetime
    created_by: Optional[uuid.UUID]
    author_name: Optional[str]
    author_email: Optional[str]


# Newest service date first, with NULL and a legacy "" last; then the latest
# save, then the id (F §1.4: nulls_last spelled out, an id tie-breaker).
LIST_ORDER = (func.nullif(Service.service_date_iso, "").desc().nulls_last(),
              Service.saved_at.desc(), Service.id.desc())


def _in(session: Optional[Session], work):
    if session is not None:
        return work(session)
    with session_scope() as own:
        return work(own)


def get_service(church_id, service_id, *, session: Session, for_update: bool = False) -> Optional[Service]:
    """The church's service with this id, or None. `for_update` locks the row
    (SELECT ... FOR UPDATE; nothing on SQLite) until the transaction ends."""
    stmt = select(Service).where(Service.id == as_uuid(service_id), Service.church_id == as_uuid(church_id))
    if for_update:
        stmt = stmt.with_for_update()
    return session.execute(stmt).scalar_one_or_none()


def list_page(church_id, *, limit: int, offset: int,
              session: Optional[Session] = None) -> tuple[list[SummaryRow], int]:
    """One page of the church's services in LIST_ORDER, and the church's total."""
    cid = as_uuid(church_id)

    def work(s: Session) -> tuple[list[SummaryRow], int]:
        total = s.execute(select(func.count()).select_from(Service).where(Service.church_id == cid)).scalar_one()
        rows = s.execute(
            select(Service.id, Service.service_date_iso, Service.service_date_display, Service.occasion,
                   Service.sermon_title, Service.saved_at, Service.created_by, User.name, User.email)
            .outerjoin(User, User.id == Service.created_by)
            .where(Service.church_id == cid)
            .order_by(*LIST_ORDER).limit(limit).offset(offset)
        ).all()
        return [SummaryRow(*row) for row in rows], int(total)

    return _in(session, work)


def author(user_id, *, session: Session) -> Optional[tuple[uuid.UUID, Optional[str], str]]:
    """(id, name, email) of the user who created a service, or None (removed)."""
    if user_id is None:
        return None
    row = session.execute(select(User.id, User.name, User.email).where(User.id == as_uuid(user_id))).first()
    return None if row is None else (row.id, row.name, row.email)


def insert_service(church_id, created_by, fields: dict, *, session: Session) -> Service:
    """Add a service with these column values (usecases.archive builds them); flushed, so it has its id."""
    row = Service(church_id=as_uuid(church_id), created_by=None if created_by is None else as_uuid(created_by),
                  **fields)
    session.add(row)
    session.flush()
    return row


def update_service(row: Service, fields: dict, *, session: Session) -> Service:
    """Replace these columns of a service already read (and locked) in `session`; created_by never changes."""
    for name, value in fields.items():
        setattr(row, name, value)
    session.flush()
    return row


def delete_service(row: Service, *, session: Session) -> None:
    session.delete(row)
    session.flush()
