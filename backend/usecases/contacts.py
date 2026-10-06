"""The church's contacts, the people the bulletin is emailed to (slice 5b-1;
5b spec GET /contacts; 6a spec "Contacts" and "Semantics" → Contacts).

Every member reads the list; owners and admins add, edit and delete. Each
write opens one session and starts with usecases.members.lock_and_read_actor
(the church-row lock and the caller's role re-read under it), then
church_admin.require_admin_role, so a caller demoted after require_admin ran
gets the role 403, and the duplicate check and the write run under the lock:
two admins adding the same address at once get one contact and one 409.

An address goes through email_addresses.normalize_address, the rule 5b-2
applies again when it sends, so an address saved here can always be emailed.
The list says, for each contact, whether its stored address passes that rule
(`email_valid`): contacts saved before the rule (in Streamlit) are shown, and
flagged when they would fail, so an admin can fix them on the Contacts page.
No FastAPI, Starlette or Streamlit here (usecases/__init__.py).
"""
import re
import uuid
from collections.abc import Mapping
from typing import Optional

import email_contacts
from bulletin_settings import NOT_ONE_LINE
from db import session_scope
from domain_errors import Conflict, InvalidInput, NotFound
from email_addresses import InvalidAddress, normalize_address
from usecases.church_admin import require_admin_role
from usecases.members import lock_and_read_actor

EMAIL_REQUIRED = "Email is required."
EMAIL_INVALID = "Enter a valid email address."
EMAIL_TAKEN = "That email is already in your contacts."
NAME_NOT_ONE_LINE = "Name can't contain line breaks or control characters."
CONTACT_NOT_FOUND = "Contact not found."

# A contact's name is one line in the list and, from 5b-2, in the email dialog: no control character (NUL,
# which Postgres refuses in text, among them), no U+2028/U+2029, no U+FFFE/U+FFFF (the church name's rule).
_NOT_ONE_LINE = re.compile(f"[{NOT_ONE_LINE}\ufffe\uffff]")


def email_is_valid(email: str) -> bool:
    """True when `email` passes normalize_address (5b-2 can send to it)."""
    try:
        normalize_address(email)
    except InvalidAddress:
        return False
    return True


def _out(contact: dict) -> dict:
    """A contact as the API returns it: a NULL or blank name as None (the repo
    returns it as stored, for the frozen Streamlit pages), and `email_valid`."""
    name = contact["name"] if contact["name"] is not None and contact["name"].strip() else None
    return {**contact, "name": name, "email_valid": email_is_valid(contact["email"])}


def list_contacts(church_id: uuid.UUID) -> list[dict]:
    """GET /contacts: every contact of the church, in email_contacts.list_contacts'
    order, each {id, name (None when blank), email, email_valid}."""
    return [_out(c) for c in email_contacts.list_contacts(church_id)]


def normalize_email(value: Optional[str]) -> str:
    """A contact's address as stored: normalize_address's answer (trimmed, the
    domain lower-cased). Blank or None: InvalidInput "Email is required.";
    refused by the rule: InvalidInput "Enter a valid email address."."""
    if value is None or not value.strip():
        raise InvalidInput(EMAIL_REQUIRED, field="email")
    try:
        return normalize_address(value)
    except InvalidAddress:
        raise InvalidInput(EMAIL_INVALID, field="email") from None


def clean_name(value: Optional[str]) -> str:
    """A contact's name as stored: trimmed, "" for none (Streamlit's value for
    a nameless contact, which the list returns as None). One line only."""
    name = (value or "").strip()
    if _NOT_ONE_LINE.search(name):
        raise InvalidInput(NAME_NOT_ONE_LINE, field="name")
    return name


def add_contact(church_id: uuid.UUID, actor_id: uuid.UUID, *, name: Optional[str], email: Optional[str]) -> dict:
    """POST /contacts: the new contact. The name is checked before the email;
    an address already in the church's contacts (any case) is a 409."""
    with session_scope() as s:
        require_admin_role(lock_and_read_actor(s, church_id, actor_id))
        clean = clean_name(name)
        address = normalize_email(email)
        if email_contacts.email_exists(church_id, address, session=s):
            raise Conflict(EMAIL_TAKEN)
        return _out(email_contacts.add_contact(church_id, name=clean, email=address, session=s))


def update_contact(church_id: uuid.UUID, actor_id: uuid.UUID, contact_id: uuid.UUID,
                   changes: Mapping[str, Optional[str]]) -> dict:
    """PATCH /contacts/{id}: only the keys sent ("name": None or blank clears
    it; "email": None or blank is "Email is required."). An unknown id, or
    another church's, is a 404 before any field is checked; an address another
    of the church's contacts has (any case) is a 409."""
    with session_scope() as s:
        require_admin_role(lock_and_read_actor(s, church_id, actor_id))
        if email_contacts.get_contact(contact_id, church_id, session=s) is None:
            raise NotFound(CONTACT_NOT_FOUND)
        clean: dict[str, str] = {}
        if "name" in changes:
            clean["name"] = clean_name(changes["name"])
        if "email" in changes:
            clean["email"] = normalize_email(changes["email"])
            if email_contacts.email_exists(church_id, clean["email"], exclude_id=contact_id, session=s):
                raise Conflict(EMAIL_TAKEN)
        return _out(email_contacts.update_contact(contact_id, church_id, clean, session=s))


def delete_contact(church_id: uuid.UUID, actor_id: uuid.UUID, contact_id: uuid.UUID) -> None:
    """DELETE /contacts/{id}; an unknown id, or another church's, is a 404."""
    with session_scope() as s:
        require_admin_role(lock_and_read_actor(s, church_id, actor_id))
        if not email_contacts.delete_contact(contact_id, church_id, session=s):
            raise NotFound(CONTACT_NOT_FOUND)
