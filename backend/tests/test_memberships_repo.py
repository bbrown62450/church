import pytest
from datetime import datetime, timezone

from sqlalchemy import select

from db import session_scope
from db.models import Service, Membership
from repos.churches import create_church
from repos.memberships import (
    LastAdminError, get_role, add_membership, set_role,
    remove_membership, list_members, count_admins,
)


def test_add_membership_no_duplicate(tmp_db, make_user):
    owner = make_user(email="owner@x.com", name="Owner")
    member = make_user(email="m@x.com", name="Mem")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    add_membership(member, cid, "member")
    add_membership(member, cid, "member")  # duplicate ignored
    assert get_role(member, cid) == "member"
    assert count_admins(cid) == 1
    with session_scope() as s:
        rows = s.execute(select(Membership).where(Membership.church_id == cid)).all()
    assert len(rows) == 2


def test_list_members_joins_users(tmp_db, make_user):
    owner = make_user(email="owner@x.com", name="Owner")
    member = make_user(email="zoe@x.com", name="Zoe")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    add_membership(member, cid, "admin")
    rows = list_members(cid)
    assert {"user_id": owner, "email": "owner@x.com", "name": "Owner", "role": "owner"} in rows
    assert {"user_id": member, "email": "zoe@x.com", "name": "Zoe", "role": "admin"} in rows


def test_remove_last_admin_is_rejected(tmp_db, make_user):
    owner = make_user(email="owner@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    with pytest.raises(LastAdminError):
        remove_membership(owner, cid)
    assert get_role(owner, cid) == "owner"  # unchanged after rejection


def test_remove_member_preserves_content_and_nulls_authorship(tmp_db, make_user):
    owner = make_user(email="owner@x.com")
    author = make_user(email="author@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    add_membership(author, cid, "member")
    with session_scope() as s:
        s.add(Service(
            church_id=cid, created_by=author,
            service_date_iso="2026-07-19", service_date_display="July 19, 2026",
            saved_at=datetime.now(timezone.utc),
        ))
    remove_membership(author, cid)
    assert get_role(author, cid) is None
    with session_scope() as s:
        svc = s.execute(select(Service).where(Service.church_id == cid)).scalar_one()
        assert svc.created_by is None  # history survives, authorship nulled


def test_set_role_demote_last_admin_rejected(tmp_db, make_user):
    owner = make_user(email="owner@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    with pytest.raises(LastAdminError):
        set_role(owner, cid, "member")
    assert get_role(owner, cid) == "owner"


def test_set_role_demote_ok_when_second_admin_exists(tmp_db, make_user):
    owner = make_user(email="owner@x.com")
    admin2 = make_user(email="a2@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    add_membership(admin2, cid, "admin")
    set_role(owner, cid, "member")
    assert get_role(owner, cid) == "member"
    assert count_admins(cid) == 1
