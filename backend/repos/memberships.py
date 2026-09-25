from typing import Optional

from sqlalchemy import select, func, update

from db import session_scope
from db.models import Membership, User, Service

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


def get_role(user_id, church_id) -> Optional[str]:
    with session_scope() as session:
        m = session.get(Membership, {"church_id": church_id, "user_id": user_id})
        return m.role if m is not None else None


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


def set_role(user_id, church_id, role) -> None:
    """Change a member's role. Demoting the last owner/admin to member is
    rejected under a row lock."""
    with session_scope() as session:
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


def remove_membership(user_id, church_id) -> None:
    """Remove a member. Removing the last owner/admin is rejected under a row
    lock. The member's authored services are preserved but their
    services.created_by is nulled (history survives the author leaving)."""
    with session_scope() as session:
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
