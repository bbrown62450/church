"""Streamlit session-state side of tenancy: which church is active in this
browser session. The database check itself is tenancy.validate_active_church.

Removed in the final migration slice together with the Streamlit app.
"""
from typing import Optional

from repos.churches import list_user_churches
from tenancy import validate_active_church

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
