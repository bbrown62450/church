#!/usr/bin/env python3
"""Database-backed, church-scoped email contacts for bulletin distribution.

The hardcoded DEFAULT_CONTACTS have been removed: each church manages its own
recipients on the Settings page, and a new church starts with an empty list.
"""
import uuid
from typing import Any, Dict, List

from sqlalchemy import delete, select

from db import session_scope
from db.models import Contact


def _as_uuid(value: Any) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


def _to_dict(c: Contact) -> Dict[str, str]:
    return {"id": str(c.id), "name": c.name, "email": c.email}


def list_contacts(church_id) -> List[Dict[str, str]]:
    """All contacts for a church, ordered by creation then name."""
    cid = _as_uuid(church_id)
    with session_scope() as session:
        rows = (
            session.execute(
                select(Contact)
                .where(Contact.church_id == cid)
                .order_by(Contact.created_at, Contact.name)
            )
            .scalars()
            .all()
        )
        return [_to_dict(c) for c in rows]


def add_contact(church_id, *, name: str, email: str) -> Dict[str, str]:
    """Insert a contact for a church. Returns {id, name, email}."""
    cid = _as_uuid(church_id)
    with session_scope() as session:
        c = Contact(church_id=cid, name=name, email=email)
        session.add(c)
        session.flush()
        return _to_dict(c)


def delete_contact(contact_id, church_id) -> bool:
    """Delete a contact only if it belongs to `church_id`. Cross-church -> False."""
    cid = _as_uuid(church_id)
    with session_scope() as session:
        result = session.execute(
            delete(Contact).where(
                Contact.id == _as_uuid(contact_id), Contact.church_id == cid
            )
        )
        return result.rowcount > 0


def get_contacts_for_display(church_id) -> List[Dict[str, str]]:
    """Contacts for the UI. No defaults — empty list when a church has none."""
    return list_contacts(church_id)
