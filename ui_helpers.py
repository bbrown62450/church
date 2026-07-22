"""Pure, Streamlit-free helpers so page logic is importable and unit-testable."""
from __future__ import annotations

# OAuth callback query keys we strip AFTER handling. Never a blanket
# st.query_params.clear() — that would drop ?invite=/?church= mid round-trip
# (spec §4 query-param hygiene).
OAUTH_QUERY_KEYS = ("code", "state", "scope", "authuser", "hd", "prompt", "gmail_oauth")


def capture_query_params(query_params, session) -> None:
    """Copy untrusted ?invite=/?church= into session. Runs on main()'s FIRST line
    so the values survive the login and Gmail OAuth redirects."""
    invite = query_params.get("invite")
    if invite:
        session["pending_invite_code"] = invite
    church = query_params.get("church")
    if church:
        session["active_church_id"] = church


def clear_oauth_query_params(query_params) -> None:
    """Delete ONLY the OAuth callback keys, preserving everything else."""
    for key in OAUTH_QUERY_KEYS:
        if key in query_params:
            del query_params[key]


def hymn_display_from_flat(row: dict) -> dict:
    """Map one flat repos.hymns row (Notion property keys) to the display shape
    used by the hymn selectboxes and the docx builder."""
    title = (row.get("Hymn Title") or "").strip()
    return {
        "title": title or "Unknown",
        "number": row.get("Hymn Number"),
        "link": row.get("Hymnary.org Link"),
    }


def build_title_to_info(hymns: list) -> dict:
    """{normalized-title -> display info} for the church's hymnal. Empty in -> empty
    out, which the Service Builder renders as an explicit empty-hymnal message."""
    out: dict = {}
    for row in hymns:
        title = (row.get("Hymn Title") or "").strip()
        if title:
            out[title.lower()] = hymn_display_from_flat(row)
    return out
