"""Church membership checks shared by every front end.

validate_active_church is the single tenancy guard: given an untrusted church
id and a user id, it re-derives membership and role from the database.
Streamlit session-state helpers live in streamlit_tenancy.py.
"""
import uuid
from typing import Optional

from sqlalchemy import select

from db import session_scope
from db.models import Church, Membership

_ADMIN_ROLES = ("owner", "admin")


def is_admin(role) -> bool:
    return role in _ADMIN_ROLES


def _coerce_uuid(value) -> Optional[uuid.UUID]:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return None


def validate_active_church(candidate_church_id, user_id) -> Optional[dict]:
    """Pure tenancy core. Given an *untrusted* candidate church id and a user id,
    confirm the user has a membership in that church and the church is not
    soft-deleted, and re-derive the role from the database. Returns
    {"church_id","name","role"} or None. Never trusts a session-cached role.
    """
    cid = _coerce_uuid(candidate_church_id)
    if cid is None or user_id is None:
        return None
    with session_scope() as session:
        row = session.execute(
            select(Church.id, Church.name, Membership.role)
            .join(Membership, Membership.church_id == Church.id)
            .where(
                Membership.church_id == cid,
                Membership.user_id == user_id,
                Church.deleted_at.is_(None),
            )
        ).one_or_none()
        if row is None:
            return None
        return {"church_id": row.id, "name": row.name, "role": row.role}
