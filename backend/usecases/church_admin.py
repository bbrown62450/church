"""Church administration (6a spec, `usecases/church_admin.py`): the writes an
owner or admin makes to the church itself. Slice 6a-1 has the profile
(PATCH /church); 6a-2, 6a-3 and 6b add their writes here.

Every write opens one session, starts with
usecases.members.lock_and_read_actor (the church-row lock and the caller's
role re-read under it) and then require_admin_role on that re-read role, so
an admin demoted after require_admin ran gets the role 403 and nothing is
written. No FastAPI, Starlette or Streamlit here (usecases/__init__.py).
"""
from domain_errors import Forbidden
from tenancy import is_admin

# require_admin's message (api/deps.py): one wording for the role 403.
ADMINS_ONLY_MESSAGE = "Only church admins can do this."


def require_admin_role(role: str) -> None:
    """Raise the role 403 (no details, so the client never treats it as a lost
    church) unless `role` is owner or admin."""
    if not is_admin(role):
        raise Forbidden(ADMINS_ONLY_MESSAGE)
