import pytest
from datetime import datetime, timezone

from sqlalchemy import event, select

from db import session_scope
from db.models import Service, Membership
from repos.churches import create_church
from repos.memberships import (
    LastAdminError, get_role, add_membership, set_role,
    remove_membership, list_members, count_admins, ensure_membership,
    count_owner_admins, get_member, is_member_email, list_member_rows, transfer_ownership,
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


class _Abort(Exception):
    """Raised inside a caller's session_scope to roll that transaction back."""


def test_ensure_membership_inserts_then_reports_existing(tmp_db, make_user):
    owner = make_user(email="owner@x.com")
    joiner = make_user(email="j@x.com")
    late = make_user(email="late@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)

    assert ensure_membership(cid, joiner, "admin") == ("admin", True)
    assert ensure_membership(str(cid), str(joiner), "member") == ("admin", False)  # role kept
    assert ensure_membership(cid, owner, "member") == ("owner", False)
    assert get_role(joiner, cid) == "admin"

    with pytest.raises(_Abort):
        with session_scope() as s:
            assert ensure_membership(cid, late, "member", session=s) == ("member", True)
            assert get_role(late, cid, session=s) == "member"
            raise _Abort
    assert get_role(late, cid) is None  # the caller's rollback removed it


# --- Slice 6b-1: the People routes' reads, the session variants and the transfer ---


def test_list_member_rows_orders_the_owner_then_admins_then_members_by_name(tmp_db, make_user):
    owner = make_user(email="zed@x.com", name="Zed")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    people = {key: make_user(email=email, name=name) for key, email, name in (
        ("bea", "bea@x.com", "bea"), ("amy", "amy@x.com", ""), ("cal", "cal@x.com", "Cal"),
        ("al", "al@x.com", None), ("dot", "dot@x.com", "Dot"))}
    for key, role in (("bea", "admin"), ("amy", "admin"), ("cal", "member"), ("al", "member"), ("dot", "member")):
        add_membership(people[key], cid, role)
    rows = list_member_rows(cid)
    assert [(r["email"], r["role"]) for r in rows] == [
        ("zed@x.com", "owner"), ("amy@x.com", "admin"), ("bea@x.com", "admin"),
        ("al@x.com", "member"), ("cal@x.com", "member"), ("dot@x.com", "member")]
    assert rows[1] == {"user_id": people["amy"], "email": "amy@x.com", "name": "", "role": "admin"}


def test_member_lookups_are_scoped_to_the_church(tmp_db, make_user):
    owner = make_user(email="owner@x.com")
    other_owner = make_user(email="other@x.com")
    admin = make_user(email="Admin@X.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    other = create_church(name="D", timezone="UTC", owner_user_id=other_owner)
    add_membership(admin, cid, "admin")
    with session_scope() as s:
        assert get_member(cid, str(admin), session=s) == {
            "user_id": admin, "email": "admin@x.com", "name": "Person", "role": "admin"}
        assert get_member(cid, other_owner, session=s) is None
        assert (count_owner_admins(cid, session=s), count_owner_admins(other, session=s)) == (2, 1)
        assert is_member_email(cid, " ADMIN@x.com ", session=s) is True
        assert is_member_email(other, "admin@x.com", session=s) is False


def test_set_role_and_remove_membership_write_in_the_callers_session(tmp_db, make_user):
    owner = make_user(email="owner@x.com")
    member = make_user(email="m@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    add_membership(member, cid, "member")
    with pytest.raises(RuntimeError), session_scope() as s:
        set_role(str(member), str(cid), "admin", session=s)
        assert get_role(member, cid, session=s) == "admin"
        raise RuntimeError("roll back")
    assert get_role(member, cid) == "member"
    with session_scope() as s:
        remove_membership(member, cid, session=s)
    assert get_role(member, cid) is None


def test_transfer_ownership_demotes_then_promotes(tmp_db, make_user):
    owner = make_user(email="owner@x.com")
    heir = make_user(email="heir@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    add_membership(heir, cid, "member")
    roles = []

    @event.listens_for(tmp_db, "before_cursor_execute")
    def _record(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("UPDATE memberships"):
            roles.append(parameters[0])

    with session_scope() as s:
        transfer_ownership(cid, owner, heir, session=s)
    event.remove(tmp_db, "before_cursor_execute", _record)
    assert roles == ["admin", "owner"]
    assert (get_role(owner, cid), get_role(heir, cid)) == ("admin", "owner")
