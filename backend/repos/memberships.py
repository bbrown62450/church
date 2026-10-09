from typing import Optional

from sqlalchemy import case, select, func, update
from sqlalchemy.orm import Session

from db import session_scope
from db.ids import as_uuid
from db.models import Membership, User, Service
from db.upsert import insert_ignore

_ADMIN_ROLES = ("owner", "admin")


class LastAdminError(Exception):
    """Raised when an operation would leave a church with zero owners/admins."""


def _lock_admin_user_ids(session, church_id) -> list:
    """Row-lock the church's owner/admin memberships (SELECT ... FOR UPDATE on
    Postgres; a no-op on SQLite) so concurrent mutual removal cannot zero the
    admin count. Returns the locked admin user_ids."""
    return session.execute(
        select(Membership.user_id)
        .where(
            Membership.church_id == church_id,
            Membership.role.in_(_ADMIN_ROLES),
        )
        .with_for_update()
    ).scalars().all()


def get_role(user_id, church_id, *, session: Optional[Session] = None) -> Optional[str]:
    if session is not None:
        return _get_role(session, user_id, church_id)
    with session_scope() as own:
        return _get_role(own, user_id, church_id)


def _get_role(session, user_id, church_id) -> Optional[str]:
    m = session.get(Membership, {"church_id": church_id, "user_id": user_id})
    return m.role if m is not None else None


def ensure_membership(
    church_id, user_id, role: str, *, session: Optional[Session] = None
) -> tuple[str, bool]:
    """Add `user_id` to `church_id` with `role` unless a membership exists;
    return (stored role, inserted). An existing membership keeps its role
    (role changes go through set_role).

    INSERT ... ON CONFLICT DO NOTHING, then a select: two concurrent same-user
    accepts never hit the primary key; the second waits for the first's row,
    inserts nothing (rowcount 0 on both dialects) and gets inserted=False.
    """
    cid, uid = as_uuid(church_id), as_uuid(user_id)
    if session is not None:
        return _ensure_membership(session, cid, uid, role)
    with session_scope() as own:
        return _ensure_membership(own, cid, uid, role)


def _ensure_membership(session, church_id, user_id, role) -> tuple[str, bool]:
    result = session.execute(
        insert_ignore(Membership.__table__)
        .values(church_id=church_id, user_id=user_id, role=role)
        .on_conflict_do_nothing(index_elements=["church_id", "user_id"])
    )
    stored = session.execute(
        select(Membership.role).where(
            Membership.church_id == church_id, Membership.user_id == user_id
        )
    ).scalar_one()
    return stored, result.rowcount == 1


def count_admins(church_id) -> int:
    with session_scope() as session:
        return session.execute(
            select(func.count())
            .select_from(Membership)
            .where(
                Membership.church_id == church_id,
                Membership.role.in_(_ADMIN_ROLES),
            )
        ).scalar_one()


def add_membership(user_id, church_id, role) -> None:
    """Idempotent add. If the membership already exists it is left unchanged
    (no duplicate row); role changes go through set_role."""
    with session_scope() as session:
        existing = session.get(
            Membership, {"church_id": church_id, "user_id": user_id}
        )
        if existing is not None:
            return
        session.add(Membership(church_id=church_id, user_id=user_id, role=role))


def set_role(user_id, church_id, role, *, session: Optional[Session] = None) -> None:
    """Change a member's role. Demoting the last owner/admin to member is
    rejected under a row lock. Runs in the caller's `session` (slice 6b's
    usecases, under the church-row lock) or in its own scope; ids go through
    as_uuid."""
    uid, cid = as_uuid(user_id), as_uuid(church_id)
    if session is not None:
        _set_role(session, uid, cid, role)
        return
    with session_scope() as own:
        _set_role(own, uid, cid, role)


def _set_role(session, user_id, church_id, role) -> None:
    m = session.get(Membership, {"church_id": church_id, "user_id": user_id})
    if m is None:
        return
    if m.role in _ADMIN_ROLES and role not in _ADMIN_ROLES:
        admins = _lock_admin_user_ids(session, church_id)
        if len(admins) <= 1:
            raise LastAdminError(
                "Cannot demote the last owner/admin of this church."
            )
    m.role = role


def remove_membership(user_id, church_id, *, session: Optional[Session] = None) -> None:
    """Remove a member. Removing the last owner/admin is rejected under a row
    lock. The member's authored services are preserved but their
    services.created_by is nulled (history survives the author leaving).
    Runs in the caller's `session` or in its own scope; ids go through
    as_uuid."""
    uid, cid = as_uuid(user_id), as_uuid(church_id)
    if session is not None:
        _remove_membership(session, uid, cid)
        return
    with session_scope() as own:
        _remove_membership(own, uid, cid)


def _remove_membership(session, user_id, church_id) -> None:
    m = session.get(Membership, {"church_id": church_id, "user_id": user_id})
    if m is None:
        return
    if m.role in _ADMIN_ROLES:
        admins = _lock_admin_user_ids(session, church_id)
        if len(admins) <= 1:
            raise LastAdminError(
                "Cannot remove the last owner/admin of this church."
            )
    session.execute(
        update(Service)
        .where(Service.church_id == church_id, Service.created_by == user_id)
        .values(created_by=None)
    )
    session.delete(m)


def transfer_ownership(church_id, owner_id, new_owner_id, *, session: Session) -> None:
    """Make `new_owner_id` the owner and `owner_id` an admin, as two Core
    UPDATEs in this order: demote, then promote. (The ORM's unit of work
    orders same-table UPDATEs by primary key, not by assignment, and a promote
    first would hold two owners for one statement, which slice 6b-2's
    one-owner index refuses.) The caller holds the church-row lock and has
    checked both memberships."""
    cid = as_uuid(church_id)
    for user_id, role in ((as_uuid(owner_id), "admin"), (as_uuid(new_owner_id), "owner")):
        session.execute(
            update(Membership)
            .where(Membership.church_id == cid, Membership.user_id == user_id)
            .values(role=role)
            .execution_options(synchronize_session=False)
        )


def _member_query(church_id):
    return (
        select(User.id, User.email, User.name, Membership.role)
        .join(Membership, Membership.user_id == User.id)
        .where(Membership.church_id == church_id)
    )


def _member_dict(row) -> dict:
    return {"user_id": row.id, "email": row.email, "name": row.name, "role": row.role}


def list_member_rows(church_id, *, session: Optional[Session] = None) -> list[dict]:
    """The church's members {user_id, email, name, role} in the order
    GET /members shows them (slice 6b): the owner, then admins, then members,
    each by lower(name, or the email when the name is blank), then user_id."""
    cid = as_uuid(church_id)
    order = (
        case((Membership.role == "owner", 0), (Membership.role == "admin", 1), else_=2),
        func.lower(func.coalesce(func.nullif(User.name, ""), User.email)),
        User.id,
    )
    if session is not None:
        return [_member_dict(r) for r in session.execute(_member_query(cid).order_by(*order))]
    with session_scope() as own:
        return [_member_dict(r) for r in own.execute(_member_query(cid).order_by(*order))]


def get_member(church_id, user_id, *, session: Session) -> Optional[dict]:
    """One membership of this church {user_id, email, name, role}, or None
    (a user who belongs only to another church is None too)."""
    row = session.execute(_member_query(as_uuid(church_id)).where(Membership.user_id == as_uuid(user_id))).first()
    return _member_dict(row) if row is not None else None


def count_owner_admins(church_id, *, session: Session) -> int:
    """How many owner and admin memberships the church has, read under the
    same admin-row lock set_role and remove_membership take."""
    return len(_lock_admin_user_ids(session, as_uuid(church_id)))


def is_member_email(church_id, email: str, *, session: Session) -> bool:
    """True when a member of this church has `email` (compared lower-cased)."""
    return session.execute(
        select(func.count()).select_from(Membership)
        .join(User, User.id == Membership.user_id)
        .where(Membership.church_id == as_uuid(church_id), func.lower(User.email) == email.strip().lower())
    ).scalar_one() > 0


def list_members(church_id) -> list:
    with session_scope() as session:
        rows = session.execute(
            select(User.id, User.email, User.name, Membership.role)
            .join(Membership, Membership.user_id == User.id)
            .where(Membership.church_id == church_id)
            .order_by(User.email)
        ).all()
        return [
            {"user_id": r.id, "email": r.email, "name": r.name, "role": r.role}
            for r in rows
        ]
