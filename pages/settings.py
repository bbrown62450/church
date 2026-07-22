"""Church Settings page: profile, contacts, members & invites (admin-gated).

Filled in Tasks 20–21. This stub exposes the names app.py imports so the
two-page navigation is wired up from Task 17 onward.
"""


class NotAuthorizedError(Exception):
    """Raised by an action helper when the caller's role is insufficient."""


def render_settings_page(user, active):
    """Render the Settings page for the active church. Implemented in Tasks 20–21."""
    import streamlit as st

    st.title("Settings")
    st.info("Church settings will appear here.")
