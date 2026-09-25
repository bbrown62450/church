import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func

from db import session_scope
from db.models import Hymn, Invite, Church
from repos.churches import (
    create_church, get_church, list_user_churches, soft_delete_church, update_church,
)


def test_create_church_is_atomic_owns_and_seeds(tmp_db, make_user, seed_catalog):
    seed_catalog(5)
    owner = make_user(email="owner@x.com", name="Owner")
    cid = create_church(name="First Pres", timezone="America/New_York", owner_user_id=owner)
    assert isinstance(cid, uuid.UUID)

    ch = get_church(cid)
    assert ch["name"] == "First Pres"
    assert ch["timezone"] == "America/New_York"

    # creator gets an owner membership
    assert list_user_churches(owner) == [{"id": cid, "name": "First Pres", "role": "owner"}]

    # hymnal seeded synchronously from the shared catalog (5 rows copied)
    with session_scope() as s:
        n = s.execute(
            select(func.count()).select_from(Hymn).where(Hymn.church_id == cid)
        ).scalar_one()
    assert n == 5


def test_get_church_and_list_exclude_soft_deleted(tmp_db, make_user):
    owner = make_user(email="o2@x.com")
    cid = create_church(name="Grace", timezone="UTC", owner_user_id=owner)
    soft_delete_church(cid)
    assert get_church(cid) is None
    assert list_user_churches(owner) == []


def test_soft_delete_revokes_pending_invites(tmp_db, make_user):
    owner = make_user(email="o3@x.com")
    cid = create_church(name="Hope", timezone="UTC", owner_user_id=owner)
    with session_scope() as s:
        s.add(Invite(
            church_id=cid, code="pending-code", role="member", created_by=owner,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7), revoked=False,
        ))
    soft_delete_church(cid)
    with session_scope() as s:
        inv = s.execute(select(Invite).where(Invite.code == "pending-code")).scalar_one()
        assert inv.revoked is True


def test_update_church_changes_profile(tmp_db, make_user):
    owner = make_user(email="o4@x.com")
    cid = create_church(name="Old", timezone="UTC", owner_user_id=owner)
    update_church(cid, name="New Name", timezone="America/Chicago", settings={"theme": "dark"})
    ch = get_church(cid)
    assert ch["name"] == "New Name"
    assert ch["timezone"] == "America/Chicago"
    assert ch["settings"] == {"theme": "dark"}
