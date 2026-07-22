from datetime import datetime, timezone, timedelta

from sqlalchemy import select

from db import session_scope
from db.models import Invite, Church
from repos.churches import create_church
from repos.memberships import get_role
from repos.invites import (
    create_invite, get_invite_by_code, accept_invite, list_invites, revoke_invite,
)


def test_create_invite_returns_secure_code_and_lists_active(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    code = create_invite(church_id=cid, created_by=owner)
    assert isinstance(code, str) and len(code) >= 22   # >=128 bits, url-safe
    inv = get_invite_by_code(code)
    assert inv["church_id"] == cid and inv["role"] == "member"
    assert [i["code"] for i in list_invites(cid)] == [code]


def test_accept_invite_adds_membership(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    joiner = make_user(email="join@x.com")
    cid = create_church(name="Grace", timezone="UTC", owner_user_id=owner)
    code = create_invite(church_id=cid, created_by=owner)
    ok, msg = accept_invite(code, joiner)
    assert ok is True and "Grace" in msg
    assert get_role(joiner, cid) == "member"


def test_accept_invite_already_member_is_noop(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    cid = create_church(name="Grace", timezone="UTC", owner_user_id=owner)
    code = create_invite(church_id=cid, created_by=owner)
    ok, msg = accept_invite(code, owner)          # already the owner
    assert ok is True
    assert get_role(owner, cid) == "owner"        # role not downgraded to member


def test_accept_invite_rejects_soft_deleted_church(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    joiner = make_user(email="j@x.com")
    cid = create_church(name="Gone", timezone="UTC", owner_user_id=owner)
    code = create_invite(church_id=cid, created_by=owner)
    # soft-delete the church directly, leaving the invite live, to hit the
    # church-availability branch specifically.
    with session_scope() as s:
        s.get(Church, cid).deleted_at = datetime.now(timezone.utc)
    ok, msg = accept_invite(code, joiner)
    assert ok is False
    assert get_role(joiner, cid) is None


def test_email_bound_invite_matches_email_and_is_single_use(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    wrong = make_user(email="wrong@x.com")
    right = make_user(email="right@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    code = create_invite(church_id=cid, created_by=owner, email="Right@X.com", role="admin")

    ok, _ = accept_invite(code, wrong)            # mismatched email
    assert ok is False
    assert get_role(wrong, cid) is None

    ok, _ = accept_invite(code, right)            # case-insensitive match; role honored
    assert ok is True
    assert get_role(right, cid) == "admin"

    ok2, msg2 = accept_invite(code, right)        # single-use consumed
    assert ok2 is False and "used" in msg2.lower()


def test_expired_invite_rejected_and_excluded_from_active(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    joiner = make_user(email="j@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    code = create_invite(church_id=cid, created_by=owner)
    with session_scope() as s:
        inv = s.execute(select(Invite).where(Invite.code == code)).scalar_one()
        inv.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    ok, msg = accept_invite(code, joiner)
    assert ok is False and "expired" in msg.lower()
    assert list_invites(cid) == []


def test_revoke_invite_blocks_accept_and_is_church_scoped(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    other_owner = make_user(email="oo@x.com")
    joiner = make_user(email="j@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    other_cid = create_church(name="D", timezone="UTC", owner_user_id=other_owner)
    code = create_invite(church_id=cid, created_by=owner)
    inv = get_invite_by_code(code)

    revoke_invite(inv["id"], other_cid)           # wrong church -> no-op (IDOR-safe)
    assert [i["code"] for i in list_invites(cid)] == [code]

    revoke_invite(inv["id"], cid)                 # correct church
    assert list_invites(cid) == []
    ok, _ = accept_invite(code, joiner)
    assert ok is False
