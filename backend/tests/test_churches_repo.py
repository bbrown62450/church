import uuid
from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy import select, func, update

from db import session_scope
from db.models import Hymn, Invite, Church
from domain_errors import NotFound
from repos.churches import (
    create_church, create_church_seeded, get_church, list_user_churches,
    recent_owned_creations, soft_delete_church, update_church,
)
from repos.memberships import add_membership


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


class _Abort(Exception):
    """Raised inside a caller's session_scope to roll that transaction back."""


NOW = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)


def _set_created_at(church_id, when):
    """The repo stamps created_at itself; cap tests move it to a fixed time."""
    with session_scope() as s:
        s.execute(update(Church).where(Church.id == church_id).values(created_at=when))


def _hymn_count(church_id=None):
    with session_scope() as s:
        q = select(func.count()).select_from(Hymn)
        if church_id is not None:
            q = q.where(Hymn.church_id == church_id)
        return s.execute(q).scalar_one()


def test_create_church_seeded_returns_id_and_hymn_count(tmp_db, make_user, seed_catalog):
    seed_catalog(4)
    owner = make_user(email="seeded@x.com")
    cid, seeded = create_church_seeded(
        name="Grace", timezone="America/Chicago", owner_user_id=str(owner),  # ids go through as_uuid
    )
    assert isinstance(cid, uuid.UUID)
    assert seeded == 4
    assert _hymn_count(cid) == 4
    assert list_user_churches(owner) == [{"id": cid, "name": "Grace", "role": "owner"}]
    with pytest.raises(NotFound):
        create_church(name="Bad", timezone="UTC", owner_user_id="not-a-uuid")


def test_create_church_uses_caller_session_without_commit(tmp_db, make_user, seed_catalog):
    seed_catalog(2)
    owner = make_user(email="caller@x.com")
    with pytest.raises(_Abort):
        with session_scope() as s:
            cid = create_church(name="Grace", timezone="UTC", owner_user_id=owner, session=s)
            assert get_church(cid, session=s)["name"] == "Grace"
            assert s.execute(
                select(func.count()).select_from(Hymn).where(Hymn.church_id == cid)
            ).scalar_one() == 2
            raise _Abort  # the caller's rollback undoes the church, membership and hymns
    assert get_church(cid) is None
    assert list_user_churches(owner) == []
    assert _hymn_count() == 0


def test_recent_owned_creations_lists_owned_recent_and_soft_deleted(tmp_db, make_user):
    owner = make_user(email="cap@x.com")
    a = create_church(name="A", timezone="UTC", owner_user_id=owner)
    b = create_church(name="B", timezone="UTC", owner_user_id=owner)
    c = create_church(name="C", timezone="UTC", owner_user_id=owner)
    _set_created_at(a, NOW - timedelta(hours=1))
    _set_created_at(b, NOW - timedelta(hours=23))
    _set_created_at(c, NOW - timedelta(hours=5))
    soft_delete_church(b)  # deleting a church does not free a slot

    since = NOW - timedelta(hours=24)
    expected = [NOW - timedelta(hours=23), NOW - timedelta(hours=5), NOW - timedelta(hours=1)]
    times = recent_owned_creations(owner, since=since)
    assert times == expected  # oldest first, soft-deleted included
    assert all(t.tzinfo is timezone.utc for t in times)  # aware UTC, even from SQLite
    with session_scope() as s:
        assert recent_owned_creations(str(owner), since=since, session=s) == expected


def test_recent_owned_creations_skips_old_and_admin_only(tmp_db, make_user):
    owner = make_user(email="cap2@x.com")
    other = make_user(email="other@x.com")
    old = create_church(name="Old", timezone="UTC", owner_user_id=owner)
    edge = create_church(name="Edge", timezone="UTC", owner_user_id=owner)
    new = create_church(name="New", timezone="UTC", owner_user_id=owner)
    theirs = create_church(name="Theirs", timezone="UTC", owner_user_id=other)
    add_membership(owner, theirs, "admin")  # admin there, not owner: not counted
    _set_created_at(old, NOW - timedelta(hours=25))
    _set_created_at(edge, NOW - timedelta(hours=24))  # exactly `since`: not after it
    _set_created_at(new, NOW - timedelta(hours=2))
    _set_created_at(theirs, NOW - timedelta(hours=1))

    since = NOW - timedelta(hours=24)
    assert recent_owned_creations(owner, since=since) == [NOW - timedelta(hours=2)]
    assert recent_owned_creations(other, since=since) == [NOW - timedelta(hours=1)]
    # A non-UTC `since` means the same instant (SQLite compares naive UTC text).
    eastern = since.astimezone(timezone(timedelta(hours=-4)))
    assert recent_owned_creations(owner, since=eastern) == [NOW - timedelta(hours=2)]


def test_rubric_overrides_read_in_the_callers_session(tmp_db, make_user):
    """Slice 3 reads the rubric in the same session as the hymns (F §2.2 rule 3)."""
    from repos.churches import get_church_rubric_overrides, update_church_rubric

    cid = create_church(name="Grace", timezone="America/New_York", owner_user_id=make_user())
    update_church_rubric(cid, {"prefer_before_year": 1900})
    with session_scope() as s:
        assert get_church_rubric_overrides(cid, session=s) == {"prefer_before_year": 1900}
    assert get_church_rubric_overrides(cid) == {"prefer_before_year": 1900}
    assert get_church_rubric_overrides(uuid.uuid4()) == {}
