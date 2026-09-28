from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy import select

from db import session_scope
from db.models import Invite
from repos.churches import create_church
from repos.invites import (
    create_invite, get_invite_by_code, list_invites, revoke_invite,
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


def test_expired_invite_excluded_from_active(tmp_db, make_user):
    # The accept half is test_usecase_onboarding.py::test_invite_rejections[accept-expired].
    owner = make_user(email="o@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    code = create_invite(church_id=cid, created_by=owner)
    with session_scope() as s:
        inv = s.execute(select(Invite).where(Invite.code == code)).scalar_one()
        inv.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    assert list_invites(cid) == []


def test_revoke_invite_is_church_scoped(tmp_db, make_user):
    # The accept half is test_usecase_onboarding.py::test_invite_rejections[accept-revoked].
    owner = make_user(email="o@x.com")
    other_owner = make_user(email="oo@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    other_cid = create_church(name="D", timezone="UTC", owner_user_id=other_owner)
    code = create_invite(church_id=cid, created_by=owner)
    inv = get_invite_by_code(code)

    revoke_invite(inv["id"], other_cid)           # wrong church -> no-op (IDOR-safe)
    assert [i["code"] for i in list_invites(cid)] == [code]

    revoke_invite(inv["id"], cid)                 # correct church
    assert list_invites(cid) == []
    assert get_invite_by_code(code)["revoked"] is True


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
