"""Church integrity checks (6b spec, "Church integrity runbook"; slice 6b-1).

find_violations reads, never writes, and returns ids and counts only: no
email, name or invite code. The kinds, in this order:
- owner_count: a church in use whose owner count is not exactly one
  {"kind", "church_id", "owners"};
- no_admin: a church in use with no owner or admin {"kind", "church_id"};
- invite_role: an invite whose role is neither member nor admin
  {"kind", "church_id", "invite_id"} (0008_invites_integrity repairs these,
  and the database refuses new ones);
- pending_duplicate: more than one pending invite (email set, not revoked,
  not accepted) for one church and email in any capitalization
  {"kind", "church_id", "invites"} (0008 refuses to run over these).
Within a kind, rows are ordered by church id (then invite id). A church in
use is one not soft-deleted; invites are checked in every church.
backend/scripts/check_integrity.py prints them; the README's "Before
0008_invites_integrity" step 2 query counts the same things.
"""
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from db import session_scope
from db.models import Church, Invite, Membership

ROLES = ("member", "admin")


def find_violations(*, session: Optional[Session] = None) -> list[dict]:
    if session is not None:
        return _find_violations(session)
    with session_scope() as own:
        return _find_violations(own)


def _find_violations(s: Session) -> list[dict]:
    owners = (
        select(func.count()).select_from(Membership)
        .where(Membership.church_id == Church.id, Membership.role == "owner")
        .scalar_subquery()
    )
    admins = (
        select(func.count()).select_from(Membership)
        .where(Membership.church_id == Church.id, Membership.role.in_(("owner", "admin")))
        .scalar_subquery()
    )
    in_use = Church.deleted_at.is_(None)
    found = [
        {"kind": "owner_count", "church_id": church_id, "owners": count}
        for church_id, count in s.execute(
            select(Church.id, owners).where(in_use, owners != 1).order_by(Church.id))
    ]
    found += [
        {"kind": "no_admin", "church_id": church_id}
        for church_id in s.execute(select(Church.id).where(in_use, admins == 0).order_by(Church.id)).scalars()
    ]
    found += [
        {"kind": "invite_role", "church_id": church_id, "invite_id": invite_id}
        for church_id, invite_id in s.execute(
            select(Invite.church_id, Invite.id).where(Invite.role.not_in(ROLES))
            .order_by(Invite.church_id, Invite.id))
    ]
    pending = and_(Invite.email.is_not(None), Invite.revoked.is_(False), Invite.accepted_at.is_(None))
    found += [
        {"kind": "pending_duplicate", "church_id": church_id, "invites": count}
        for church_id, count in s.execute(
            select(Invite.church_id, func.count()).where(pending)
            .group_by(Invite.church_id, func.lower(Invite.email))
            .having(func.count() > 1)
            .order_by(Invite.church_id, func.lower(Invite.email)))
    ]
    return found
