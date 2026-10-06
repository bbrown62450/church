#!/usr/bin/env python3
"""Database-backed, church-scoped email contacts for bulletin distribution.

The hardcoded DEFAULT_CONTACTS have been removed: each church manages its own
recipients on the Settings page, and a new church starts with an empty list.

Every function is scoped to one church (a contact of another church is never
read, changed or deleted) and takes an optional `session`, so a usecase can
run it inside the transaction that holds the church-row lock (slice 5b-1;
6a spec, "Semantics" → Contacts). Ids go through db.ids.as_uuid, so a
malformed id is a 404, never a 500. A name that is NULL or blank (Streamlit
stored "" for a contact without one) is returned as None.
"""
import uuid
from typing import Any, Dict, List, Mapping, Optional

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from db import session_scope
from db.ids import as_uuid
from db.models import Contact


def _to_dict(c: Contact) -> Dict[str, Any]:
    name = c.name if c.name is not None and c.name.strip() else None
    return {"id": str(c.id), "name": name, "email": c.email}


def list_contacts(church_id, *, session: Optional[Session] = None) -> List[Dict[str, Any]]:
    """All contacts for a church: by creation time, then name (a NULL or blank
    name after every named one), then id, so the order never depends on the
    database (5b spec, GET /contacts)."""
    if session is not None:
        return _list_contacts(session, church_id)
    with session_scope() as own:
        return _list_contacts(own, church_id)


def _list_contacts(session, church_id) -> List[Dict[str, Any]]:
    name = func.nullif(func.trim(Contact.name), "")
    rows = session.execute(
        select(Contact)
        .where(Contact.church_id == as_uuid(church_id))
        .order_by(Contact.created_at, name.asc().nulls_last(), Contact.id)
    ).scalars().all()
    return [_to_dict(c) for c in rows]


def add_contact(church_id, *, name: str, email: str, session: Optional[Session] = None) -> Dict[str, Any]:
    """Insert a contact for a church, as given (the caller cleans it). Returns {id, name, email}."""
    if session is not None:
        return _add_contact(session, church_id, name, email)
    with session_scope() as own:
        return _add_contact(own, church_id, name, email)


def _add_contact(session, church_id, name, email) -> Dict[str, Any]:
    c = Contact(church_id=as_uuid(church_id), name=name, email=email)
    session.add(c)
    session.flush()
    return _to_dict(c)


def update_contact(contact_id, church_id, changes: Mapping[str, str], *,
                   session: Optional[Session] = None) -> Optional[Dict[str, Any]]:
    """Set the keys given ("name" and/or "email", already cleaned) on the
    church's contact. Returns it, or None when the church has no such contact."""
    if session is not None:
        return _update_contact(session, contact_id, church_id, changes)
    with session_scope() as own:
        return _update_contact(own, contact_id, church_id, changes)


def _update_contact(session, contact_id, church_id, changes) -> Optional[Dict[str, Any]]:
    c = _get(session, contact_id, church_id)
    if c is None:
        return None
    if "name" in changes:
        c.name = changes["name"]
    if "email" in changes:
        c.email = changes["email"]
    session.flush()
    return _to_dict(c)


def get_contact(contact_id, church_id, *, session: Optional[Session] = None) -> Optional[Dict[str, Any]]:
    """The church's contact, or None."""
    if session is not None:
        c = _get(session, contact_id, church_id)
        return _to_dict(c) if c is not None else None
    with session_scope() as own:
        return get_contact(contact_id, church_id, session=own)


def _get(session, contact_id, church_id) -> Optional[Contact]:
    return session.execute(
        select(Contact).where(Contact.id == as_uuid(contact_id), Contact.church_id == as_uuid(church_id))
    ).scalar_one_or_none()


def email_exists(church_id, email: str, *, exclude_id: Optional[uuid.UUID] = None,
                 session: Optional[Session] = None) -> bool:
    """True when another of the church's contacts has this address, compared
    trimmed and lower-cased (5b's rule: addresses that differ only in case are
    one; a Streamlit-era address may still have spaces around it)."""
    if session is not None:
        return _email_exists(session, church_id, email, exclude_id)
    with session_scope() as own:
        return _email_exists(own, church_id, email, exclude_id)


def _email_exists(session, church_id, email, exclude_id) -> bool:
    query = select(Contact.id).where(
        Contact.church_id == as_uuid(church_id), func.lower(func.trim(Contact.email)) == email.lower()
    )
    if exclude_id is not None:
        query = query.where(Contact.id != as_uuid(exclude_id))
    return session.execute(query.limit(1)).first() is not None


def delete_contact(contact_id, church_id, *, session: Optional[Session] = None) -> bool:
    """Delete a contact only if it belongs to `church_id`. Cross-church -> False."""
    if session is not None:
        return _delete_contact(session, contact_id, church_id)
    with session_scope() as own:
        return _delete_contact(own, contact_id, church_id)


def _delete_contact(session, contact_id, church_id) -> bool:
    result = session.execute(
        delete(Contact).where(Contact.id == as_uuid(contact_id), Contact.church_id == as_uuid(church_id))
    )
    return result.rowcount > 0


def get_contacts_for_display(church_id) -> List[Dict[str, str]]:
    """Contacts for the UI. No defaults — empty list when a church has none."""
    return list_contacts(church_id)
