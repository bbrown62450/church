"""Slice 6b-1's writes on real Postgres (6b spec, Testing → Postgres;
"Transactions and locking"): every membership, invite, transfer, leave and
delete write takes the church-row lock and re-reads the caller's role under
it, so two writes to one church serialize, and the loser sees the winner's
result. The partial unique index refuses a second pending invite for an email
even without the lock.

Skipped without TEST_DATABASE_URL; CI's backend-postgres job runs it. SQLite
ignores FOR UPDATE, so only these tests prove the waiting. Each forces the
race the same way: a function the first write calls through its module after
taking the lock waits until the test lets it go; the second write is started
meanwhile and must still be waiting a second later. A write that never gets
there fails the test after 10 s instead of passing vacuously.
"""
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from db import session_scope
from db.models import Invite
from domain_errors import Conflict, Forbidden, NotFound
from repos import churches, invites
from repos.churches import create_church
from repos.integrity import find_violations
from repos.memberships import add_membership, get_role, remove_membership
from repos.users import ensure_user
from usecases import church_admin, members, role_policy

pytestmark = pytest.mark.postgres
NOW = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def world(pg_db):
    ids = {who: ensure_user(f"{who}@example.com", who.title()).id for who in ("owner", "b", "c")}
    church = create_church(name="Grace", timezone="America/New_York", owner_user_id=ids["owner"])
    add_membership(ids["b"], church, "admin")
    add_membership(ids["c"], church, "member")
    return church, ids


def _hold(monkeypatch, module, name):
    """Make module.name wait inside the first call until released; returns (inside, release)."""
    inside, release = threading.Event(), threading.Event()
    real = getattr(module, name)
    calls = []

    def held(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            inside.set()               # the first write holds the church-row lock here
            assert release.wait(10), f"the test never released {name}"
        return real(*args, **kwargs)

    monkeypatch.setattr(module, name, held)
    return inside, release


def _race(first, second, inside, release):
    """Run `first`, wait until it holds the lock, start `second`, check it waits, release.
    Returns both outcomes (a value or the exception)."""
    def outcome(future):
        try:
            return future.result(10)
        except Exception as exc:       # noqa: BLE001 - the loser's refusal is the result
            return exc

    with ThreadPoolExecutor(2) as pool:
        a = pool.submit(first)
        assert inside.wait(10), "the first write never took the lock"
        b = pool.submit(second)
        threading.Event().wait(1)      # time for the second to finish if nothing held it
        assert not b.done(), "the second write did not wait for the church-row lock"
        release.set()
        return outcome(a), outcome(b)


def test_two_transfers_at_once_leave_one_owner(world, monkeypatch):
    church, ids = world
    inside, release = _hold(monkeypatch, role_policy, "check_transfer")
    first, second = _race(lambda: church_admin.transfer_ownership(church, ids["owner"], ids["b"]),
                          lambda: church_admin.transfer_ownership(church, ids["owner"], ids["c"]),
                          inside, release)
    assert [m["role"] for m in first if m["user_id"] == ids["b"]] == ["owner"]
    assert isinstance(second, Forbidden) and second.message == "Only the owner can do that."
    assert [get_role(ids[w], church) for w in ("owner", "b", "c")] == ["admin", "owner", "member"]
    assert find_violations() == []


def test_a_transfer_to_someone_leaving_never_leaves_the_church_ownerless(world, monkeypatch):
    church, ids = world
    inside, release = _hold(monkeypatch, role_policy, "check_transfer")
    _transfer, leave = _race(lambda: church_admin.transfer_ownership(church, ids["owner"], ids["c"]),
                             lambda: church_admin.leave_church(church, ids["c"]), inside, release)
    assert isinstance(leave, Conflict) and leave.code == "owner_must_transfer"
    assert get_role(ids["c"], church) == "owner"
    monkeypatch.undo()
    other = create_church(name="Hope", timezone="UTC", owner_user_id=ids["owner"])
    add_membership(ids["c"], other, "member")
    inside, release = _hold(monkeypatch, role_policy, "check_leave")
    _left, transfer = _race(lambda: church_admin.leave_church(other, ids["c"]),
                            lambda: church_admin.transfer_ownership(other, ids["owner"], ids["c"]), inside, release)
    assert isinstance(transfer, NotFound) and transfer.message == "Member not found."
    assert get_role(ids["owner"], other) == "owner"
    assert find_violations() == []


def test_two_admins_of_an_ownerless_church_removing_each_other_leave_one(world, monkeypatch):
    church, ids = world
    remove_membership(ids["owner"], church)
    add_membership(ids["owner"], church, "admin")          # now an ownerless church with two admins
    inside, release = _hold(monkeypatch, role_policy, "check_remove")
    first, second = _race(lambda: members.remove_member(church, ids["owner"], ids["b"]),
                          lambda: members.remove_member(church, ids["b"], ids["owner"]), inside, release)
    assert first == 0
    assert isinstance(second, Forbidden) and second.details == {"reason": "no_church_access"}
    assert (get_role(ids["owner"], church), get_role(ids["b"], church)) == ("admin", None)
    assert [v["kind"] for v in find_violations()] == ["owner_count"]   # the seeded ownerless church only


def test_two_invites_for_one_email_at_once_make_one(world, monkeypatch):
    church, ids = world
    inside, release = _hold(monkeypatch, members, "clean_invite_email")
    first, second = _race(lambda: members.create_invite(church, ids["owner"], email="new@example.com"),
                          lambda: members.create_invite(church, ids["b"], email="NEW@example.com"), inside, release)
    assert first["email"] == "new@example.com"
    assert isinstance(second, Conflict) and second.code == "invite_exists"
    with session_scope() as s:
        assert s.execute(select(Invite.email)).scalars().all() == ["new@example.com"]


def test_the_pending_email_index_refuses_a_second_insert_even_without_the_lock(world):
    """Two transactions that never take the church-row lock (a direct write):
    the second insert waits on the first's index entry and fails once it commits."""
    church, ids = world
    inserted, release = threading.Event(), threading.Event()

    def first():
        with session_scope() as s:
            invites.insert_invite(church_id=church, created_by=ids["owner"], role="member", email="a@example.com",
                                  reusable=False, session=s)
            inserted.set()
            assert release.wait(10)

    def second():
        with session_scope() as s:
            invites.insert_invite(church_id=church, created_by=ids["b"], role="admin", email="A@example.com",
                                  reusable=False, session=s)

    with ThreadPoolExecutor(2) as pool:
        a = pool.submit(first)
        assert inserted.wait(10)
        b = pool.submit(second)
        threading.Event().wait(1)
        assert not b.done(), "the second insert did not wait for the first's index entry"
        release.set()
        a.result(10)
        with pytest.raises(IntegrityError, match="uq_invites_pending_email"):
            b.result(10)


def test_a_profile_save_and_a_role_change_at_once_both_happen(world, monkeypatch):
    church, ids = world
    inside, release = _hold(monkeypatch, church_admin, "clean_profile_patch")
    profile, role = _race(lambda: church_admin.update_profile(church, ids["owner"], {"default_benediction": "Go."}),
                          lambda: members.change_role(church, ids["b"], ids["c"], "admin"), inside, release)
    assert profile["name"] == "Grace" and role["role"] == "admin"
    assert churches.get_church(church)["settings"]["default_benediction"] == "Go."


def test_a_delete_and_an_invite_at_once_leave_no_live_invite(world, monkeypatch):
    church, ids = world
    inside, release = _hold(monkeypatch, members, "clean_invite_email")
    _invite, _deleted = _race(lambda: members.create_invite(church, ids["b"], email="late@example.com"),
                              lambda: church_admin.delete_church(church, ids["owner"], "Grace"), inside, release)
    with session_scope() as s:
        assert s.execute(select(Invite.revoked)).scalars().all() == [True]     # made, then revoked by the delete
    monkeypatch.undo()
    other = create_church(name="Hope", timezone="UTC", owner_user_id=ids["owner"])
    add_membership(ids["b"], other, "admin")
    inside, release = _hold(monkeypatch, churches, "soft_delete_church")
    _deleted, invite = _race(lambda: church_admin.delete_church(other, ids["owner"], "Hope"),
                             lambda: members.create_invite(other, ids["b"], email="later@example.com"),
                             inside, release)
    assert isinstance(invite, Forbidden) and invite.details == {"reason": "no_church_access"}
    with session_scope() as s:
        assert s.execute(select(Invite.id).where(Invite.church_id == other)).all() == []
