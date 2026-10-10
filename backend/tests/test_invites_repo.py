from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy import delete, select, update

from db import session_scope
from db.models import Invite, User
from domain_errors import NotFound
from repos.churches import create_church
from repos.invites import (
    create_invite, get_invite_by_code, list_invites, revoke_invite,
    find_pending_email_invite, insert_invite, list_active_invites, revoke_expired_email_invites,
    revoke_invites_created_by, revoke_pending_email_invites, revoke_reusable_invites,
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


# --- Slice 6b-1: the People routes' reads and revocations ---

NOW = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)


def _set(code, **values):
    with session_scope() as s:
        s.execute(update(Invite).where(Invite.code == code).values(**values))


def _revoked(code) -> bool:
    return get_invite_by_code(code)["revoked"]


def test_insert_invite_returns_the_whole_row(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    with session_scope() as s:
        row = insert_invite(church_id=cid, created_by=owner, role="admin", email="  Mary@X.com ",
                            reusable=False, now=NOW, session=s)
    assert len(row["code"]) >= 22
    assert {k: row[k] for k in ("church_id", "email", "role", "created_by", "reusable", "revoked", "accepted_at")} == {
        "church_id": cid, "email": "mary@x.com", "role": "admin", "created_by": owner, "reusable": False,
        "revoked": False, "accepted_at": None}
    assert (row["created_at"], row["expires_at"]) == (NOW, NOW + timedelta(days=7))
    assert get_invite_by_code(row["code"])["id"] == row["id"]


def test_list_active_invites_shows_live_ones_newest_first_with_their_creator(tmp_db, make_user):
    owner = make_user(email="o@x.com", name="Olive")
    gone = make_user(email="gone@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    codes = {}
    for hours, key, creator, kwargs in ((1, "old", owner, {}), (2, "reusable_used", owner, {"reusable": True}),
                                        (3, "single_used", owner, {}), (4, "revoked", owner, {}),
                                        (5, "expired", owner, {}), (6, "by_gone", gone, {"email": "p@x.com"})):
        codes[key] = create_invite(church_id=cid, created_by=creator, **kwargs)
        _set(codes[key], created_at=NOW + timedelta(hours=hours), expires_at=NOW + timedelta(days=7))
    for key in ("reusable_used", "single_used"):
        _set(codes[key], accepted_at=NOW)
    _set(codes["revoked"], revoked=True)
    _set(codes["expired"], expires_at=NOW)
    with session_scope() as s:
        s.execute(delete(User).where(User.id == gone))
    rows = list_active_invites(cid, now=NOW)
    assert [r["code"] for r in rows] == [codes["by_gone"], codes["reusable_used"], codes["old"]]
    assert rows[0]["created_by"] is None and rows[0]["email"] == "p@x.com"
    assert rows[2]["created_by"] == {"user_id": owner, "name": "Olive", "email": "o@x.com"}
    assert (rows[2]["created_at"], rows[2]["expires_at"]) == (NOW + timedelta(hours=1), NOW + timedelta(days=7))
    assert set(rows[2]) == {"id", "code", "email", "role", "reusable", "created_at", "expires_at", "created_by"}


def test_pending_email_lookups_ignore_case_and_revoke_only_the_expired(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    live = create_invite(church_id=cid, created_by=owner, email="mary@x.com")
    with session_scope() as s:
        assert find_pending_email_invite(cid, "MARY@x.com", now=NOW, session=s)["code"] == live
        assert revoke_expired_email_invites(cid, "Mary@X.com", now=NOW, session=s) == 0
    _set(live, expires_at=NOW)
    with session_scope() as s:
        assert find_pending_email_invite(cid, "mary@x.com", now=NOW, session=s) is None
        assert revoke_expired_email_invites(cid, "mary@x.com", now=NOW, session=s) == 1
    assert _revoked(live) is True


def test_revoke_created_by_and_revoke_reusable_count_their_rows_in_one_church(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    admin = make_user(email="a@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    other = create_church(name="D", timezone="UTC", owner_user_id=admin)
    by_admin = [create_invite(church_id=cid, created_by=admin, **kw)
                for kw in ({}, {"reusable": True}, {"email": "e@x.com", "role": "admin"})]
    elsewhere = create_invite(church_id=other, created_by=admin, reusable=True)
    owners_reusable = create_invite(church_id=cid, created_by=owner, reusable=True)
    owners_single = create_invite(church_id=cid, created_by=owner)
    with session_scope() as s:
        assert revoke_invites_created_by(cid, admin, session=s) == 3
        assert revoke_invites_created_by(cid, admin, session=s) == 0
        assert revoke_reusable_invites(cid, session=s) == 1
    assert [_revoked(c) for c in by_admin] == [True, True, True]
    assert (_revoked(owners_reusable), _revoked(owners_single), _revoked(elsewhere)) == (True, False, False)


def test_revoke_invite_says_whether_the_church_has_it(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    other = create_church(name="D", timezone="UTC", owner_user_id=owner)
    code = create_invite(church_id=cid, created_by=owner)
    invite_id = str(get_invite_by_code(code)["id"])
    assert revoke_invite(invite_id, other) is False and _revoked(code) is False
    assert revoke_invite(invite_id, str(cid)) is True and _revoked(code) is True
    assert revoke_invite(invite_id, cid) is True                    # already revoked: still the church's
    with pytest.raises(NotFound):
        revoke_invite("not-a-uuid", cid)


def test_revoke_pending_email_invites_takes_every_pending_one_for_the_email_expired_too(tmp_db, make_user):
    """A removal revokes the pending invites for the removed person's email,
    whoever made them (plan review M1)."""
    owner = make_user(email="o@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    other = create_church(name="D", timezone="UTC", owner_user_id=owner)
    used = create_invite(church_id=cid, created_by=owner, email="mary@x.com")
    _set(used, accepted_at=NOW)
    expired = create_invite(church_id=cid, created_by=owner, email="Mary@x.com", role="admin")
    _set(expired, expires_at=NOW)
    someone_else = create_invite(church_id=cid, created_by=owner, email="ann@x.com")
    elsewhere = create_invite(church_id=other, created_by=owner, email="mary@x.com")
    with session_scope() as s:
        assert revoke_pending_email_invites(cid, " MARY@X.com ", session=s) == 1      # the expired one
    live = create_invite(church_id=cid, created_by=owner, email="mary@x.com")
    with session_scope() as s:
        assert revoke_pending_email_invites(cid, "mary@x.com", session=s) == 1
        assert revoke_pending_email_invites(cid, "mary@x.com", session=s) == 0
    assert [_revoked(c) for c in (live, expired, used, someone_else, elsewhere)] == [True, True, False, False, False]


def test_claim_stamps_only_a_live_invite(tmp_db, make_user):
    """claim's UPDATE also requires the invite unrevoked and unexpired, so an
    accept that read the invite before a removal revoked it claims nothing
    (plan review M2)."""
    owner = make_user(email="o@x.com")
    joiner = make_user(email="j@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    revoked, expired, live = (create_invite(church_id=cid, created_by=owner) for _ in range(3))
    _set(revoked, revoked=True)
    _set(expired, expires_at=NOW)
    _set(live, expires_at=NOW)
    assert claim(get_invite_by_code(revoked)["id"], joiner, NOW - timedelta(minutes=1)) is False
    assert claim(get_invite_by_code(expired)["id"], joiner, NOW + timedelta(seconds=1)) is False
    assert claim(get_invite_by_code(live)["id"], joiner, NOW) is True          # expires_at == now: still live
    assert [get_invite_by_code(c)["accepted_by"] for c in (revoked, expired, live)] == [None, None, joiner]
