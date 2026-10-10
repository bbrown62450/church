"""usecases.church_admin's transfer, leave and delete (6b spec, "Transactions
and locking", "Role policy"; Testing → test_church_lifecycle.py; slice 6b-1):
each runs in one transaction under the church-row lock with the caller's
role re-read, and leaves every church with exactly one owner."""
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select, update

from db import session_scope
from db.models import Church, Invite, Service
from domain_errors import Conflict, Forbidden, InvalidInput, NotFound, Rejected
from repos import invites
from repos.churches import get_church, list_user_churches
from repos.integrity import find_violations
from repos.memberships import add_membership, get_role, remove_membership
from tests.test_church_settings import _record_church_row_access
from usecases import church_admin, members, onboarding

NOW = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)
NO_ACCESS = ("You don't have access to this church.", {"reason": "no_church_access"})


@pytest.fixture
def world(tmp_db, make_user, make_church):
    owner = make_user(email="owner@example.com", name="Olive Owner")
    admin = make_user(email="admin@example.com", name="Adam Admin")
    member = make_user(email="member@example.com", name="Mia Member")
    cid = make_church(name="Grace", owner_user_id=owner)
    add_membership(admin, cid, "admin")
    add_membership(member, cid, "member")
    other_owner = make_user(email="elsewhere@example.com")
    other = make_church(name="Hope", owner_user_id=other_owner)
    return {"church": cid, "owner": owner, "admin": admin, "member": member, "other": other,
            "other_owner": other_owner}


def _roles(world) -> list:
    return [get_role(world[w], world["church"]) for w in ("owner", "admin", "member")]


# --- transfer_ownership ---


def test_transfer_swaps_roles_atomically(world):
    out = church_admin.transfer_ownership(world["church"], world["owner"], world["member"])
    assert _roles(world) == ["admin", "admin", "owner"]
    assert [(m["email"], m["role"], m["is_me"]) for m in out] == [
        ("member@example.com", "owner", False), ("admin@example.com", "admin", False),
        ("owner@example.com", "admin", True)]
    assert find_violations() == []


def test_transfer_to_an_admin(world):
    church_admin.transfer_ownership(world["church"], world["owner"], str(world["admin"]))
    assert _roles(world) == ["admin", "owner", "member"]
    assert find_violations() == []


def test_transfer_to_oneself_is_a_422_naming_user_id(world):
    with pytest.raises(InvalidInput) as refused:
        church_admin.transfer_ownership(world["church"], world["owner"], world["owner"])
    assert (refused.value.message, refused.value.field) == ("Choose someone else to be the new owner.", "user_id")
    assert _roles(world) == ["owner", "admin", "member"]


def test_transfer_to_someone_not_in_this_church_is_not_found(world, make_user):
    for target in (world["other_owner"], make_user(email="nobody@example.com"), uuid.uuid4()):
        with pytest.raises(NotFound) as missing:
            church_admin.transfer_ownership(world["church"], world["owner"], target)
        assert missing.value.message == "Member not found."
    assert _roles(world) == ["owner", "admin", "member"]
    assert get_role(world["other_owner"], world["other"]) == "owner"


@pytest.mark.parametrize("who", ["admin", "member"])
def test_only_the_owner_transfers(world, who):
    with pytest.raises(Forbidden) as refused:
        church_admin.transfer_ownership(world["church"], world[who], world["member"])
    assert (refused.value.message, refused.value.details) == ("Only the owner can do that.", None)
    assert _roles(world) == ["owner", "admin", "member"]


def test_an_owner_who_already_transferred_elsewhere_is_refused(world):
    church_admin.transfer_ownership(world["church"], world["owner"], world["admin"])   # another tab, first
    with pytest.raises(Forbidden) as refused:
        church_admin.transfer_ownership(world["church"], world["owner"], world["member"])
    assert refused.value.message == "Only the owner can do that."
    assert _roles(world) == ["admin", "owner", "member"]


# --- leave_church ---


@pytest.mark.parametrize("who", ["member", "admin"])
def test_a_member_or_an_admin_leaves_and_their_services_stay(world, who):
    with session_scope() as s:
        s.add(Service(church_id=world["church"], service_date_iso="2026-10-04", occasion="", hymns=[], liturgy={},
                      scriptures=[], created_by=world[who]))
    church_admin.leave_church(world["church"], world[who])
    assert get_role(world[who], world["church"]) is None
    assert list_user_churches(world[who]) == []
    with session_scope() as s:
        assert s.execute(select(Service.created_by)).scalars().all() == [None]


def test_an_admin_who_leaves_keeps_their_invites_working(world):
    made = members.create_invite(world["church"], world["admin"], now=NOW)
    church_admin.leave_church(world["church"], world["admin"])
    with session_scope() as s:
        assert s.get(Invite, made["id"]).revoked is False


def test_the_owner_must_transfer_before_leaving_even_alone(world, make_user, make_church):
    with pytest.raises(Conflict) as refused:
        church_admin.leave_church(world["church"], world["owner"])
    alone = make_user(email="alone@example.com")
    solo = make_church(name="Solo", owner_user_id=alone)
    with pytest.raises(Conflict) as alone_refused:
        church_admin.leave_church(solo, alone)
    for exc in (refused.value, alone_refused.value):
        assert (exc.code, exc.message) == ("owner_must_transfer", "Transfer ownership before you leave. If you're the "
                                                                   "only person in the church, delete it instead.")
    assert (get_role(world["owner"], world["church"]), get_role(alone, solo)) == ("owner", "owner")


def test_ownerless_sole_admin_cannot_leave(world):
    remove_membership(world["owner"], world["church"])              # made ownerless outside the app
    with pytest.raises(Conflict) as refused:
        church_admin.leave_church(world["church"], world["admin"])
    assert (refused.value.code, refused.value.message) == (
        "last_admin", "You're the last admin. Make someone else an admin before you leave.")
    assert get_role(world["admin"], world["church"]) == "admin"
    church_admin.leave_church(world["church"], world["member"])      # a member still may


# --- delete_church ---


def test_delete_needs_the_exact_name_after_trimming(world):
    for typed in ("grace", "Grace Church", ""):
        with pytest.raises(InvalidInput) as refused:
            church_admin.delete_church(world["church"], world["owner"], typed)
        assert (refused.value.message, refused.value.field) == ("Church name did not match.", "confirm_name")
    assert get_church(world["church"]) is not None
    church_admin.delete_church(world["church"], world["owner"], "  Grace  ")
    assert get_church(world["church"]) is None


def test_delete_trims_the_stored_name_too_and_keeps_case(world):
    """A name stored with spaces around it (an old client, or by hand) matches
    what the owner types, both trimmed; case still counts (plan review M3)."""
    with session_scope() as s:
        s.execute(update(Church).where(Church.id == world["church"]).values(name=" Grace Chapel  "))
    with pytest.raises(InvalidInput) as refused:
        church_admin.delete_church(world["church"], world["owner"], "grace chapel")
    assert refused.value.field == "confirm_name"
    church_admin.delete_church(world["church"], world["owner"], "Grace Chapel")
    assert get_church(world["church"]) is None


def test_delete_soft_deletes_and_revokes_every_invite_even_a_used_reusable_one(world):
    reusable = members.create_invite(world["church"], world["owner"], reusable=True, now=NOW)
    invites.claim(reusable["id"], world["member"], NOW)
    single = members.create_invite(world["church"], world["owner"], now=NOW)
    church_admin.delete_church(world["church"], world["owner"], "Grace")
    with session_scope() as s:
        assert s.get(Church, world["church"]).deleted_at is not None
        assert [s.get(Invite, i["id"]).revoked for i in (reusable, single)] == [True, True]
    for invite in (reusable, single):
        with pytest.raises(Rejected) as rejected:
            onboarding.accept_invite(user_id=world["other_owner"], user_email="elsewhere@example.com",
                                     code=invite["code"], now=NOW)
        assert rejected.value.message == "This invite has been revoked."


@pytest.mark.parametrize("who", ["admin", "member"])
def test_only_the_owner_deletes(world, who):
    with pytest.raises(Forbidden) as refused:
        church_admin.delete_church(world["church"], world[who], "Grace")
    assert (refused.value.message, refused.value.details) == ("Only the owner can do that.", None)
    assert get_church(world["church"]) is not None


# --- lost access under the lock, and the lock itself ---

WRITES = {
    "transfer_ownership": lambda w: church_admin.transfer_ownership(w["church"], w["owner"], w["member"]),
    "leave_church": lambda w: church_admin.leave_church(w["church"], w["owner"]),
    "delete_church": lambda w: church_admin.delete_church(w["church"], w["owner"], "Grace"),
}


@pytest.mark.parametrize("gone", ["church deleted", "actor removed"])
@pytest.mark.parametrize("write", sorted(WRITES))
def test_a_write_after_the_church_or_the_callers_membership_went_is_no_church_access(world, write, gone):
    if gone == "church deleted":
        with session_scope() as s:
            s.execute(update(Church).where(Church.id == world["church"]).values(deleted_at=NOW))
    else:
        remove_membership(world["owner"], world["church"])
    with pytest.raises(Forbidden) as refused:
        WRITES[write](world)
    assert (refused.value.message, refused.value.details) == NO_ACCESS
    assert [get_role(world[w], world["church"]) for w in ("admin", "member")] == ["admin", "member"]


def test_each_write_reads_the_church_row_locked_in_its_own_session(world):
    calls = [lambda: church_admin.transfer_ownership(world["church"], world["owner"], world["admin"]),
             lambda: church_admin.leave_church(world["church"], world["owner"]),       # now an admin
             lambda: church_admin.delete_church(world["church"], world["admin"], "Grace")]
    for call in calls:
        with _record_church_row_access() as (reads, _writes):
            call()
        assert reads and reads[0][1] is True and len({id(session) for session, _ in reads}) == 1
