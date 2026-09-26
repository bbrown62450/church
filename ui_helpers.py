"""Pure, Streamlit-free helpers so page logic is importable and unit-testable."""
from __future__ import annotations

from hymn_usage import is_hymn_recently_used

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


def pick_invite_code(pending, typed) -> str:
    """Invite code to attempt: a typed value wins; otherwise the captured ?invite=."""
    typed = (typed or "").strip()
    if typed:
        return typed
    return (pending or "").strip()


def coerce_selectbox_value(current, options) -> str:
    """Reset a stored selectbox value to '' when it's not among the current options,
    so switching churches never raises StreamlitAPIException (spec §5)."""
    if current in options:
        return current
    return ""


def hymn_options_excluding_recent(title_to_info: dict, recent_used: set, keep: set[str]) -> list[str]:
    """Sorted title keys without recently used hymns, but never without a key in `keep`
    (the hymns already picked in the three slots).

    inv D5: Prepare records the picks under the service date (still counts as
    recent because the cutoff has no upper bound), so without `keep` the next
    rerun drops them from the options, safe_hymn_selectbox resets them to '' and
    the next Prepare or Save stores the service without hymns. A key in `keep`
    that is not in `title_to_info` (a renamed or deleted hymn) is not added.
    """
    return sorted(
        key for key, info in title_to_info.items()
        if key in keep
        or not is_hymn_recently_used(info.get("number"), info.get("title") or "", recent_used)
    )


def picked_hymn_keys(session) -> set[str]:
    """The title keys picked in the three hymn slots, without empty slots.

    `session` is anything with `.get`: st.session_state in app.py, a dict in tests.
    """
    return {session.get(slot) or "" for slot in ("opening", "response", "closing")} - {""}
