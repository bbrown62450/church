from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy import select

from db import session_scope
from db.models import Invite, Church
from repos.churches import create_church
from repos.memberships import get_role
from repos.invites import (
    create_invite, get_invite_by_code, accept_invite, list_invites, revoke_invite,
)
from repos.invites import _as_utc, as_utc, claim, find_by_code


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


class _Abort(Exception):
    """Raised inside a caller's session_scope to roll that transaction back."""


NOON = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)


def test_create_invite_reusable_flag_and_dict_keys(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    single = get_invite_by_code(create_invite(church_id=cid, created_by=owner))
    assert single["reusable"] is False and single["accepted_by"] is None
    shared = get_invite_by_code(create_invite(church_id=cid, created_by=owner, reusable=True))
    assert shared["reusable"] is True and shared["accepted_by"] is None

    with pytest.raises(_Abort):
        with session_scope() as s:
            code = create_invite(church_id=cid, created_by=owner, session=s)
            row = s.execute(select(Invite).where(Invite.code == code)).scalar_one()
            assert row.church_id == cid  # written in the caller's transaction ...
            raise _Abort
    assert get_invite_by_code(code) is None  # ... and never committed by the repo


def test_find_by_code_returns_row_or_none(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    code = create_invite(church_id=cid, created_by=owner, email="Bound@X.com", role="admin")
    inv = find_by_code(code)
    assert isinstance(inv, Invite)
    assert (inv.code, inv.church_id, inv.email, inv.role, inv.reusable) == (
        code, cid, "bound@x.com", "admin", False,
    )
    assert find_by_code("no-such-code") is None
    with session_scope() as s:
        assert find_by_code(code, session=s) is s.get(Invite, inv.id)  # the caller's session's row


def test_claim_first_wins_second_gets_false(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    first = make_user(email="first@x.com")
    second = make_user(email="second@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    inv = find_by_code(create_invite(church_id=cid, created_by=owner))

    assert claim(inv.id, first, NOON) is True
    assert claim(inv.id, second, NOON + timedelta(minutes=5)) is False
    with session_scope() as s:
        assert claim(str(inv.id), str(second), NOON, session=s) is False
    stored = find_by_code(inv.code)
    assert stored.accepted_by == first  # stamped once, by the first claimer
    assert as_utc(stored.accepted_at) == NOON


def test_claim_zero_rows_leaves_loaded_row_untouched(tmp_db, make_user):
    """A row loaded before another request stamped it keeps its loaded values
    after a claim that matched nothing (synchronize_session=False); the caller
    refreshes to see the winner, as usecases.onboarding.accept_invite does.
    The default synchronization would copy the loser's id into the row."""
    owner = make_user(email="o@x.com")
    winner = make_user(email="winner@x.com")
    loser = make_user(email="loser@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    code = create_invite(church_id=cid, created_by=owner)

    with session_scope() as s:
        inv = find_by_code(code, session=s)  # loaded while still unclaimed
        assert claim(inv.id, winner, NOON) is True  # another request wins in its own transaction
        assert claim(inv.id, loser, NOON, session=s) is False
        assert inv.accepted_by is None and inv.accepted_at is None  # never the loser's id
        s.refresh(inv)
        assert inv.accepted_by == winner


def test_as_utc_is_exported_and_aliased():
    assert _as_utc is as_utc
    naive = datetime(2026, 9, 28, 12, 0)
    assert as_utc(naive) == NOON and as_utc(naive).tzinfo is timezone.utc
    eastern = datetime(2026, 9, 28, 8, 0, tzinfo=timezone(timedelta(hours=-4)))
    assert as_utc(eastern) == NOON and as_utc(eastern).tzinfo is timezone.utc
