"""Identity helpers shared by every front end.

upsert_from_claims turns a plain dict of identity claims (email, sub, name,
picture) into a persisted users row and returns its id. Users are keyed on the
normalized (lower-cased) email; google_sub is a stable secondary identifier.
It is a thin wrapper over repos.users.ensure_user (F §2.4), kept with this
signature for Streamlit (streamlit_auth.py) and migrate_to_db.py.
Streamlit login helpers live in streamlit_auth.py.
"""

import uuid
from typing import Optional

from repos.users import ensure_user


def _normalize_email(email: Optional[str]) -> str:
    return (email or "").strip().lower()


def upsert_from_claims(claims: dict) -> uuid.UUID:
    """Create or update the users row for a set of OIDC claims; return its id.

    Pure w.r.t. Streamlit: accepts a plain dict (email, sub, name, picture) so it
    is unit-testable with no running Streamlit session. Idempotent on the
    normalized email, safe under concurrent first calls, and writes
    last_login_at at most hourly (repos.users.LAST_SEEN_RESOLUTION).
    """
    email = _normalize_email(claims.get("email"))
    if not email:
        raise ValueError("OIDC claims are missing an email address.")
    return ensure_user(email, claims.get("name"), claims.get("picture"),
                       google_sub=claims.get("sub")).id
