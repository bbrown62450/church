import uuid
from typing import Optional

from sqlalchemy import select

from db import session_scope
from db.models import Church, Membership
from repos.churches import list_user_churches

_ADMIN_ROLES = ("owner", "admin")

# Every church-scoped key that a church switch (or a drop to zero churches) must
# pop from st.session_state so no stale previous-church read can survive.
CHURCH_SCOPED_STATE_KEYS = (
    "active_church_id",
    "active_church_name",
    "active_church_role",
    "_cached_all_hymns",
    "_hymn_title_to_info",
    "_cached_saved_services",
    "scripture_hymns",
    "scripture_refs_used",
    "opening",
    "response",
    "closing",
    "opening_man",
    "response_man",
    "closing_man",
    "editing_service_id",
    "load_service_id",
    "liturgy",
    "include_communion",
    "custom_elements",
)

# Dynamic key families (e.g. liturgy_opening, liturgy_response, ...).
CHURCH_SCOPED_STATE_PREFIXES = ("liturgy_",)


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


def _session_state():
    import streamlit as st
    return st.session_state


def set_active_church(church_id, name=None, role=None, state=None) -> None:
    store = state if state is not None else _session_state()
    store["active_church_id"] = church_id
    if name is not None:
        store["active_church_name"] = name
    if role is not None:
        store["active_church_role"] = role


def clear_all_church_state(state=None) -> None:
    """Pop every church-scoped key (exact names + prefix families) so a church
    switch or a zero-church transition cannot leak previous-church data."""
    store = state if state is not None else _session_state()
    for key in list(store.keys()):
        if key in CHURCH_SCOPED_STATE_KEYS or any(
            key.startswith(p) for p in CHURCH_SCOPED_STATE_PREFIXES
        ):
            store.pop(key, None)


def require_active_church(user_id, state=None) -> Optional[dict]:
    """Run at the top of every church-scoped render. Reads the untrusted
    active_church_id from session, validates it against the user's real
    membership, and on failure falls back to the user's first church (or the
    zero-church empty state). Writes the validated selector back to session.
    Returns {"church_id","name","role"} or None.
    """
    store = state if state is not None else _session_state()
    validated = validate_active_church(store.get("active_church_id"), user_id)
    if validated is None:
        churches = list_user_churches(user_id)
        if not churches:
            clear_all_church_state(store)
            return None
        validated = validate_active_church(churches[0]["id"], user_id)
        if validated is None:
            clear_all_church_state(store)
            return None
    set_active_church(
        validated["church_id"],
        name=validated["name"],
        role=validated["role"],
        state=store,
    )
    return validated
