import pytest
from ui_helpers import pick_invite_code


def test_pick_invite_code_typed_wins_over_pending():
    assert pick_invite_code("PENDING", "TYPED") == "TYPED"


def test_pick_invite_code_falls_back_to_pending():
    assert pick_invite_code("PENDING", "") == "PENDING"
    assert pick_invite_code("PENDING", None) == "PENDING"


def test_pick_invite_code_blank_when_neither():
    assert pick_invite_code(None, None) == ""
    assert pick_invite_code("  ", "  ") == ""


def test_create_church_makes_owner_and_seeds_hymnal(tmp_db, make_user, seed_catalog):
    from repos.churches import create_church, list_user_churches
    from repos.hymns import list_hymns
    seed_catalog(5)
    user = make_user(email="founder@b.org")
    cid = create_church(name="New Life", timezone="America/New_York", owner_user_id=user)
    mine = list_user_churches(user)
    assert any(c["id"] == cid and c["role"] == "owner" for c in mine)
    assert len(list_hymns(cid)) == 5  # seeded atomically from the catalog


def test_accept_captured_invite_joins_as_member(tmp_db, make_user):
    from repos.churches import create_church, list_user_churches
    from repos.invites import create_invite, accept_invite
    owner = make_user(email="owner@a.org")
    cid = create_church(name="Grace", timezone="America/New_York", owner_user_id=owner)
    joiner = make_user(email="joiner@a.org")
    code = create_invite(church_id=cid, created_by=owner)
    ok, _msg = accept_invite(code, joiner)
    assert ok is True
    assert any(c["id"] == cid and c["role"] == "member" for c in list_user_churches(joiner))
