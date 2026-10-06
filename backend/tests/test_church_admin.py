"""The church-row lock and the role re-read every church write starts with
(6a spec, "Semantics" → Locking; 6b spec, `lock_and_read_actor`), and
`usecases.church_admin` (slice 6a-1)."""
import pytest

from db import session_scope
from domain_errors import Forbidden
from repos import churches
from repos.memberships import add_membership, set_role
from tests.test_church_settings import _record_church_row_access
from usecases import church_admin
from usecases.members import lock_and_read_actor

NO_ACCESS = {"reason": "no_church_access"}


@pytest.fixture
def world(tmp_db, make_user, make_church):
    owner = make_user(email="owner@example.com")
    admin = make_user(email="admin@example.com")
    member = make_user(email="member@example.com")
    cid = make_church(name="Example Church", owner_user_id=owner)
    add_membership(admin, cid, "admin")
    add_membership(member, cid, "member")
    return {"church": cid, "owner": owner, "admin": admin, "member": member}


def _actor_role(world, who: str) -> str:
    with session_scope() as s:
        return lock_and_read_actor(s, world["church"], world[who])


def test_the_role_is_read_under_the_church_row_lock(world):
    assert [_actor_role(world, who) for who in ("owner", "admin", "member")] == ["owner", "admin", "member"]
    set_role(world["admin"], world["church"], "member")        # demoted after the guard read "admin"
    assert _actor_role(world, "admin") == "member"
    with _record_church_row_access() as (reads, _writes):
        _actor_role(world, "owner")
    assert [locked for _session, locked in reads] == [True]


def test_a_church_or_a_membership_gone_is_no_church_access(world, make_user):
    outsider = make_user(email="outsider@example.com")
    with pytest.raises(Forbidden) as gone:
        with session_scope() as s:
            lock_and_read_actor(s, world["church"], outsider)
    assert (gone.value.message, gone.value.details) == ("You don't have access to this church.", NO_ACCESS)
    churches.soft_delete_church(world["church"])
    with pytest.raises(Forbidden) as deleted:
        _actor_role(world, "owner")
    assert deleted.value.details == NO_ACCESS


def test_require_admin_role():
    church_admin.require_admin_role("owner")
    church_admin.require_admin_role("admin")
    with pytest.raises(Forbidden) as denied:
        church_admin.require_admin_role("member")
    assert (denied.value.message, denied.value.details) == ("Only church admins can do this.", None)
