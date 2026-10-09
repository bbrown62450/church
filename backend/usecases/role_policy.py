"""Who may change roles, remove people, leave and transfer ownership (6b spec,
"Role policy"; owner decision 5; slice 6b-1).

Pure functions over a state the database can hold: no database, no FastAPI,
Starlette or Streamlit (usecases/__init__.py). The usecases call them with
the caller's role re-read under the church-row lock
(usecases.members.lock_and_read_actor), after looking up the target: a
missing target is the usecase's 404, never a policy outcome, so nothing here
raises NotFound. Each check stops at the first rule that refuses, in the
spec's evaluation order, so every case has one message. The rows of
tests/fixtures/shared/role_policy.json (every reachable state, 51 rows) pin
each outcome; slice 6b-2's People page mirrors the change-role and remove
rows to decide which actions it shows.
"""
import uuid
from typing import Literal

from domain_errors import Conflict, Forbidden, InvalidInput

ADMIN_ROLES = ("owner", "admin")

NOT_ADMIN = "Only church admins can do this."
OWN_ROLE = "You can't change your own role."
OWNERS_ROLE = "The owner's role can't be changed."
REMOVE_SELF = "To leave this church, use Leave church in Danger zone."
REMOVE_OWNER = "The owner can't be removed."
OWNER_ONLY = "Only the owner can do that."
TRANSFER_TO_SELF = "Choose someone else to be the new owner."
OWNER_MUST_TRANSFER = ("Transfer ownership before you leave. If you're the only person in the church, "
                       "delete it instead.")
LAST_ADMIN = "You're the last admin. Make someone else an admin before you leave."


def check_role_change(*, actor_id: uuid.UUID, actor_role: str, target_id: uuid.UUID, target_role: str,
                      new_role: str) -> Literal["change", "noop"]:
    """PATCH /members/{user_id}: "change", or "noop" when the target already
    has `new_role` (member or admin; Pydantic and usecases.members.change_role
    refuse any other role before this).
    Refuses a non-admin, a change to one's own role and a change to the
    owner's role."""
    if actor_role not in ADMIN_ROLES:
        raise Forbidden(NOT_ADMIN)
    if target_id == actor_id:
        raise Forbidden(OWN_ROLE)
    if target_role == "owner":
        raise Forbidden(OWNERS_ROLE)
    return "noop" if new_role == target_role else "change"


def check_remove(*, actor_id: uuid.UUID, actor_role: str, target_id: uuid.UUID, target_role: str) -> None:
    """DELETE /members/{user_id}: refuses a non-admin, removing oneself (that
    is Leave church) and removing the owner."""
    if actor_role not in ADMIN_ROLES:
        raise Forbidden(NOT_ADMIN)
    if target_id == actor_id:
        raise Forbidden(REMOVE_SELF)
    if target_role == "owner":
        raise Forbidden(REMOVE_OWNER)


def check_leave(*, role: str, admin_count: int) -> None:
    """POST /church/leave: the owner must transfer first (409
    owner_must_transfer); the only owner or admin of a church (one with no
    owner, made before slice 6b) may not leave it with nobody to run it (409
    last_admin). `admin_count` counts owner and admin memberships, the
    leaver's included."""
    if role == "owner":
        raise Conflict(OWNER_MUST_TRANSFER, code="owner_must_transfer")
    if role in ADMIN_ROLES and admin_count <= 1:
        raise Conflict(LAST_ADMIN, code="last_admin")


def check_transfer(*, actor_id: uuid.UUID, actor_role: str, target_id: uuid.UUID) -> None:
    """POST /church/transfer-ownership: only the owner, and to someone else
    (422 naming user_id)."""
    if actor_role != "owner":
        raise Forbidden(OWNER_ONLY)
    if target_id == actor_id:
        raise InvalidInput(TRANSFER_TO_SELF, field="user_id")
