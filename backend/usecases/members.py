"""The church's members (6b spec, `usecases/members.py`). Slice 6a-1 creates
the module with only the helper every church write shares (6a and 6b specs,
"Assumed interfaces"); 6b adds its member and invite functions here.

lock_and_read_actor runs inside the write's own session: it locks the church
row (repos.churches.lock_church, SELECT ... FOR UPDATE) and re-reads the
caller's membership under that lock, so the role a write acts on is the one
stored now, never the snapshot require_church or require_admin read in an
earlier transaction. No FastAPI, Starlette or Streamlit here
(usecases/__init__.py).
"""
import uuid

from sqlalchemy.orm import Session

from domain_errors import Forbidden
from repos import churches, memberships

# require_church's own 403 (api/deps.py): a church soft-deleted, or a
# membership removed, after the guard ran looks exactly like no access.
NO_ACCESS_MESSAGE = "You don't have access to this church."


def lock_and_read_actor(s: Session, church_id: uuid.UUID, actor_id: uuid.UUID) -> str:
    """Lock the church row in `s` and return the caller's role read under the
    lock ("owner", "admin" or "member"). Raises Forbidden (403, details.reason
    no_church_access) when the church is missing or soft-deleted, or the
    caller is no longer a member."""
    if churches.lock_church(s, church_id) is None:
        raise Forbidden(NO_ACCESS_MESSAGE, details={"reason": "no_church_access"})
    role = memberships.get_role(actor_id, church_id, session=s)
    if role is None:
        raise Forbidden(NO_ACCESS_MESSAGE, details={"reason": "no_church_access"})
    return role
