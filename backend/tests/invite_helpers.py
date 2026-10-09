"""An invite row as it could be stored before 0008_invites_integrity.

Since slice 6b-1 the database refuses an invite whose role is neither member
nor admin (ck_invites_role). Slice 1's accept and preview still clamp such a
role (usecases.onboarding._clamp_role), so their tests store one with
SQLite's CHECK enforcement off for that one statement.
"""
from sqlalchemy import text, update

from db import session_scope
from db.models import Invite


def store_unchecked_role(code: str, role: str) -> None:
    """Set the invite's role to `role`, which ck_invites_role would refuse (SQLite tests only)."""
    with session_scope() as s:
        s.execute(text("PRAGMA ignore_check_constraints = ON"))
        try:
            s.execute(update(Invite).where(Invite.code == code).values(role=role))
        finally:
            s.execute(text("PRAGMA ignore_check_constraints = OFF"))
