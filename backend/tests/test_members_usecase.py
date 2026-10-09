"""usecases.members: the member and invite functions of slice 6b-1 (6b spec,
"Backend changes", "Role policy", "Invite semantics", "Transactions and
locking"; Testing → test_members_usecase.py). Every write takes the
church-row lock and re-reads the caller's role under it; the policy's own
truth table is test_role_policy.py's."""
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError

from db import session_scope
from db.models import Church, Invite, Service, User
from domain_errors import Conflict, Forbidden, InvalidInput, NotFound, Rejected
from repos import invites, memberships
from repos.memberships import LastAdminError, add_membership, get_role, remove_membership, set_role
from tests.test_church_settings import _record_church_row_access
from usecases import members, onboarding

NOW = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)
NO_ACCESS = ("You don't have access to this church.", {"reason": "no_church_access"})
ADDRESSES = json.loads((Path(__file__).parent / "fixtures" / "shared" / "email_addresses.json")
                       .read_text(encoding="utf-8"))


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


def _invite(world, who="owner", **kwargs) -> dict:
    return members.create_invite(world["church"], world[who], now=NOW, **kwargs)


def _invite_row(invite_id) -> Invite:
    with session_scope() as s:
        row = s.get(Invite, invite_id)
        s.expunge(row)
        return row


def _codes(world) -> list[str]:
    return [i["code"] for i in members.list_invites(world["church"], now=NOW)]


# --- list_members ---


def test_members_are_listed_owner_admins_members_by_name_with_is_me(world, make_user):
    blank = make_user(email="aaron@example.com", name="  ")
    add_membership(blank, world["church"], "member")
    rows = members.list_members(world["church"], world["member"])
    assert [(r["email"], r["role"], r["name"], r["is_me"]) for r in rows] == [
        ("owner@example.com", "owner", "Olive Owner", False),
        ("admin@example.com", "admin", "Adam Admin", False),
        ("aaron@example.com", "member", None, False),
        ("member@example.com", "member", "Mia Member", True),
    ]
    assert set(rows[0]) == {"user_id", "email", "name", "role", "is_me"}


# --- change_role ---


def test_an_admin_makes_a_member_an_admin_and_back(world):
    up = members.change_role(world["church"], world["admin"], world["member"], "admin")
    assert up == {"user_id": world["member"], "email": "member@example.com", "name": "Mia Member", "role": "admin",
                  "is_me": False}
    assert members.change_role(world["church"], world["owner"], str(world["member"]), "member")["role"] == "member"
    assert get_role(world["member"], world["church"]) == "member"


@pytest.mark.parametrize("who, target, message", [
    ("member", "admin", "Only church admins can do this."),
    ("admin", "admin", "You can't change your own role."),
    ("owner", "owner", "You can't change your own role."),
    ("admin", "owner", "The owner's role can't be changed."),
])
def test_a_role_change_the_policy_refuses_changes_nothing(world, who, target, message):
    with pytest.raises(Forbidden) as refused:
        members.change_role(world["church"], world[who], world[target], "member")
    assert (refused.value.message, refused.value.details) == (message, None)
    assert [get_role(world[w], world["church"]) for w in ("owner", "admin", "member")] == ["owner", "admin", "member"]


def test_a_role_change_for_a_non_member_is_not_found(world, make_user):
    for target in (world["other_owner"], make_user(email="nobody@example.com"), uuid.uuid4(), "not-a-uuid"):
        with pytest.raises(NotFound) as missing:
            members.change_role(world["church"], world["owner"], target, "admin")
        assert missing.value.message in ("Member not found.", "Not found.")
    assert get_role(world["other_owner"], world["other"]) == "owner"


@pytest.mark.parametrize("new_role", ["owner", "Admin", "superuser", ""])
@pytest.mark.parametrize("target", ["member", "admin"])
def test_a_role_change_to_a_role_an_invite_cannot_carry_is_refused(world, monkeypatch, target, new_role):
    """The route's Pydantic refuses these first; called directly, the usecase
    refuses them too, so it can never make a second owner (6b-1 build
    review 1)."""
    monkeypatch.setattr(memberships, "set_role", lambda *a, **k: pytest.fail("set_role called"))
    with pytest.raises(InvalidInput) as refused:
        members.change_role(world["church"], world["owner"], world[target], new_role)
    assert (refused.value.field, refused.value.message) == ("role", "Not a valid value.")
    assert [get_role(world[w], world["church"]) for w in ("owner", "admin", "member")] == ["owner", "admin", "member"]


def test_the_same_role_writes_nothing(world, monkeypatch):
    monkeypatch.setattr(memberships, "set_role", lambda *a, **k: pytest.fail("set_role called"))
    assert members.change_role(world["church"], world["owner"], world["admin"], "admin")["role"] == "admin"


def test_in_an_ownerless_church_one_admin_demotes_another(world, make_user):
    second = make_user(email="second@example.com")
    add_membership(second, world["church"], "admin")
    set_role(world["owner"], world["church"], "admin")             # made ownerless outside the app
    assert members.change_role(world["church"], world["admin"], second, "member")["role"] == "member"


def test_a_last_admin_error_from_the_repo_is_a_409_not_a_500(world, monkeypatch):
    def refuse(*_args, **_kwargs):
        raise LastAdminError("Cannot demote the last owner/admin of this church.")

    monkeypatch.setattr(memberships, "set_role", refuse)
    with pytest.raises(Conflict) as refused:
        members.change_role(world["church"], world["owner"], world["admin"], "member")
    assert (refused.value.code, refused.value.message) == (
        "last_admin", "Cannot demote the last owner/admin of this church.")


def test_a_demoted_admin_gets_the_role_403_without_a_reason(world):
    set_role(world["admin"], world["church"], "member")          # after require_admin read "admin"
    with pytest.raises(Forbidden) as refused:
        members.change_role(world["church"], world["admin"], world["member"], "admin")
    assert (refused.value.message, refused.value.details) == ("Only church admins can do this.", None)
    assert get_role(world["member"], world["church"]) == "member"


WRITES = {
    "change_role": lambda w: members.change_role(w["church"], w["admin"], w["member"], "admin"),
    "remove_member": lambda w: members.remove_member(w["church"], w["admin"], w["member"]),
    "create_invite": lambda w: members.create_invite(w["church"], w["admin"], email="new@example.com", now=NOW),
    "revoke_invite": lambda w: members.revoke_invite(w["church"], w["admin"], w["invite"]),
}


@pytest.mark.parametrize("gone", ["church deleted", "actor removed"])
@pytest.mark.parametrize("write", sorted(WRITES))
def test_a_write_after_the_church_or_the_callers_membership_went_is_no_church_access(world, write, gone):
    world["invite"] = _invite(world)["id"]
    if gone == "church deleted":
        with session_scope() as s:                 # as a DELETE /church racing this write would leave it
            s.execute(update(Church).where(Church.id == world["church"])
                      .values(deleted_at=NOW))
    else:
        remove_membership(world["admin"], world["church"])
    with pytest.raises(Forbidden) as refused:
        WRITES[write](world)
    assert (refused.value.message, refused.value.details) == NO_ACCESS
    assert get_role(world["member"], world["church"]) == "member"
    with session_scope() as s:
        assert s.execute(select(Invite.email, Invite.revoked)).all() == [(None, False)]


def test_every_write_reads_the_church_row_locked_in_its_own_session(world):
    invite_id = _invite(world)["id"]
    calls = [lambda: members.change_role(world["church"], world["owner"], world["member"], "admin"),
             lambda: members.remove_member(world["church"], world["owner"], world["member"]),
             lambda: members.create_invite(world["church"], world["owner"], now=NOW),
             lambda: members.revoke_invite(world["church"], world["owner"], invite_id)]
    for call in calls:
        with _record_church_row_access() as (reads, _writes):
            call()
        assert reads and reads[0][1] is True and len({id(session) for session, _ in reads}) == 1


# --- remove_member ---


def test_removing_a_member_keeps_their_services_and_revokes_every_invite_they_made(world):
    with session_scope() as s:
        s.add(Service(church_id=world["church"], service_date_iso="2026-10-04", occasion="", hymns=[], liturgy={},
                      scriptures=[], created_by=world["admin"]))
    made = [members.create_invite(world["church"], world["admin"], now=NOW, **kw)["id"]
            for kw in ({}, {"reusable": True}, {"email": "e@example.com", "role": "admin"})]
    owners = _invite(world, reusable=True)["id"]
    add_membership(world["admin"], world["other"], "admin")
    elsewhere = members.create_invite(world["other"], world["admin"], now=NOW)["id"]
    assert members.remove_member(world["church"], world["owner"], world["admin"]) == 3
    assert get_role(world["admin"], world["church"]) is None
    assert [_invite_row(i).revoked for i in made] == [True, True, True]
    assert (_invite_row(owners).revoked, _invite_row(elsewhere).revoked) == (False, False)
    with session_scope() as s:
        assert s.execute(select(Service.created_by)).scalars().all() == [None]


def test_revoke_reusable_also_revokes_every_live_reusable_link_counting_each_once(world):
    theirs = members.create_invite(world["church"], world["admin"], now=NOW, reusable=True)["id"]
    owners_reusable = _invite(world, reusable=True)["id"]
    owners_single = _invite(world)["id"]
    assert members.remove_member(world["church"], world["owner"], world["admin"], revoke_reusable=True) == 2
    assert [_invite_row(i).revoked for i in (theirs, owners_reusable, owners_single)] == [True, True, False]


@pytest.mark.parametrize("who, target, message", [
    ("member", "admin", "Only church admins can do this."),
    ("admin", "admin", "To leave this church, use Leave church in Danger zone."),
    ("owner", "owner", "To leave this church, use Leave church in Danger zone."),
    ("admin", "owner", "The owner can't be removed."),
])
def test_a_removal_the_policy_refuses_changes_nothing(world, who, target, message):
    with pytest.raises(Forbidden) as refused:
        members.remove_member(world["church"], world[who], world[target])
    assert refused.value.message == message
    assert get_role(world[target], world["church"]) == target


def test_removing_another_churchs_member_is_not_found(world):
    with pytest.raises(NotFound) as missing:
        members.remove_member(world["church"], world["owner"], world["other_owner"])
    assert missing.value.message == "Member not found."
    assert get_role(world["other_owner"], world["other"]) == "owner"


def test_in_an_ownerless_church_with_two_admins_one_removes_the_other(world, make_user):
    second = make_user(email="second@example.com")
    add_membership(second, world["church"], "admin")
    remove_membership(world["owner"], world["church"])             # made ownerless outside the app
    assert members.remove_member(world["church"], second, world["admin"]) == 0
    assert get_role(world["admin"], world["church"]) is None


def test_removal_revokes_another_admins_pending_invite_for_the_removed_persons_email(world, make_user):
    """The owner invited Jo by email; Jo joined through another link, so that
    invite is still pending. After an admin removes Jo it stops working, and
    Jo's email in another church is untouched (plan review M1)."""
    bound = _invite(world, email="Jo@Example.com")
    jo = make_user(email="jo@example.com", name="Jo")
    add_membership(jo, world["church"], "member")                  # joined through a code-only link
    elsewhere = members.create_invite(world["other"], world["other_owner"], email="jo@example.com", now=NOW)
    assert members.remove_member(world["church"], world["admin"], jo) == 1
    assert (_invite_row(bound["id"]).revoked, _invite_row(elsewhere["id"]).revoked) == (True, False)
    with pytest.raises(Rejected) as refused:
        onboarding.accept_invite(user_id=jo, user_email="jo@example.com", code=bound["code"], now=NOW)
    assert refused.value.details == {"reason": "revoked"}
    assert get_role(jo, world["church"]) is None


@pytest.mark.parametrize("stored", [" jo@example.com", "  Jo@Example.com  "])
def test_removal_revokes_a_pending_invite_whose_stored_email_has_spaces(world, make_user, stored):
    """An invite stored with spaces around its email (only a direct database
    write or an older release could store one) is still the removed person's:
    accept compares strip().lower(), so the removal must too (6b-1 build
    review 2)."""
    bound = _invite(world, email="jo@example.com")
    with session_scope() as s:
        s.execute(update(Invite).where(Invite.id == bound["id"]).values(email=stored))
    jo = make_user(email="jo@example.com", name="Jo")
    add_membership(jo, world["church"], "member")                  # joined through a code-only link
    assert members.remove_member(world["church"], world["admin"], jo) == 1
    assert _invite_row(bound["id"]).revoked is True
    with pytest.raises(Rejected) as refused:
        onboarding.accept_invite(user_id=jo, user_email="jo@example.com", code=bound["code"], now=NOW)
    assert refused.value.details == {"reason": "revoked"}


def test_a_pending_invite_whose_stored_email_has_spaces_is_invite_exists(world):
    bound = _invite(world, email="jo@example.com")
    with session_scope() as s:
        s.execute(update(Invite).where(Invite.id == bound["id"]).values(email=" jo@example.com"))
    with pytest.raises(Conflict) as refused:
        _invite(world, email="jo@example.com")
    assert refused.value.code == "invite_exists"


def test_an_accept_whose_claim_comes_after_a_removal_claims_nothing(world, make_user, monkeypatch):
    """The accept read the admin's single-use link before the admin's removal
    committed; its claim then finds the link revoked, stamps nothing and the
    joiner is not let in (plan review M2; on Postgres the claim waits for the
    removal's row lock, then re-reads the row)."""
    joiner = make_user(email="joiner@example.com")
    link = members.create_invite(world["church"], world["admin"], now=NOW)
    real_claim = invites.claim

    def removal_commits_first(invite_id, user_id, now, *, session=None):
        members.remove_member(world["church"], world["owner"], world["admin"])   # its own transaction
        return real_claim(invite_id, user_id, now, session=session)

    monkeypatch.setattr(invites, "claim", removal_commits_first)
    with pytest.raises(Rejected) as refused:
        onboarding.accept_invite(user_id=joiner, user_email="joiner@example.com", code=link["code"], now=NOW)
    assert refused.value.details == {"reason": "used"}           # the loser's words since slice 1
    assert get_role(joiner, world["church"]) is None
    assert (_invite_row(link["id"]).revoked, _invite_row(link["id"]).accepted_at) == (True, None)


# --- invites ---


@pytest.mark.parametrize("raw, stored", [("  Right@X.com ", "right@x.com"), ("", None), ("   ", None), (None, None)])
def test_clean_invite_email(raw, stored):
    assert members.clean_invite_email(raw) == stored


@pytest.mark.parametrize("raw", ["no-at"] + [raw for raw in ADDRESSES["invalid"] if raw.strip()])
def test_an_address_the_app_cannot_use_is_refused(raw):
    with pytest.raises(InvalidInput) as refused:
        members.clean_invite_email(raw)
    assert (refused.value.message, refused.value.field) == ("Enter a valid email address.", "email")


@pytest.mark.parametrize("case", ADDRESSES["valid"], ids=lambda case: case["raw"])
def test_a_valid_address_is_stored_lower_cased(case):
    assert members.clean_invite_email(case["raw"]) == case["normalized"].lower()


def test_an_invite_is_single_use_member_by_default_for_seven_days(world):
    out = _invite(world, who="admin")
    assert len(out["code"]) >= 22
    assert {k: out[k] for k in ("email", "role", "reusable", "created_at", "expires_at")} == {
        "email": None, "role": "member", "reusable": False, "created_at": NOW, "expires_at": NOW + timedelta(days=7)}
    assert out["created_by"] == {"user_id": world["admin"], "name": "Adam Admin", "email": "admin@example.com"}
    second = members.create_invite(world["church"], world["owner"], reusable=True, role="admin",
                                   now=NOW + timedelta(minutes=1))
    assert (second["reusable"], second["role"]) == (True, "admin")
    assert _codes(world) == [second["code"], out["code"]]


@pytest.mark.parametrize("kwargs, field, message", [
    ({"email": "x@example.com", "reusable": True}, "reusable", "A link for one email address works once."),
    ({"email": "not an address"}, "email", "Enter a valid email address."),
    ({"role": "owner"}, "role", "Not a valid value."),
])
def test_a_bad_invite_is_refused_and_nothing_is_stored(world, kwargs, field, message):
    with pytest.raises(InvalidInput) as refused:
        _invite(world, **kwargs)
    assert (refused.value.field, refused.value.message) == (field, message)
    assert _codes(world) == []


def test_inviting_a_members_email_in_any_case_is_a_conflict(world):
    with pytest.raises(Conflict) as refused:
        _invite(world, email=" Member@Example.COM ")
    assert (refused.value.code, refused.value.message) == ("conflict",
                                                           "member@example.com is already a member of this church.")


def test_a_second_pending_invite_for_an_email_is_invite_exists(world):
    _invite(world, email="new@example.com")
    with pytest.raises(Conflict) as refused:
        _invite(world, email="NEW@example.com", role="admin")
    assert (refused.value.code, refused.value.message) == (
        "invite_exists", "There's already a pending invite for new@example.com. Copy its link below or revoke it first.")


def test_an_email_can_be_invited_again_after_a_revoke_an_acceptance_or_expiry(world):
    first = _invite(world, email="new@example.com")
    members.revoke_invite(world["church"], world["owner"], first["id"])
    second = _invite(world, email="new@example.com")
    invites.claim(second["id"], world["member"], NOW)                # accepted
    third = _invite(world, email="new@example.com")
    later = NOW + timedelta(days=8)                                  # third has expired by then
    fourth = members.create_invite(world["church"], world["owner"], email="new@example.com", now=later)
    assert _invite_row(third["id"]).revoked is True
    assert _invite_row(fourth["id"]).revoked is False


def test_a_unique_index_race_is_invite_exists_too(world, monkeypatch):
    _invite(world, email="new@example.com")
    monkeypatch.setattr(invites, "find_pending_email_invite", lambda *a, **k: None)   # as if the other was not seen
    with pytest.raises(Conflict) as refused:
        _invite(world, email="new@example.com")
    assert refused.value.code == "invite_exists"
    with session_scope() as s:
        assert s.execute(select(Invite.email)).scalars().all() == ["new@example.com"]


def test_an_integrity_error_from_another_constraint_is_not_invite_exists(world, monkeypatch):
    """Only uq_invites_pending_email is answered as invite_exists; anything
    else the database refuses is raised as it is (plan review M4)."""
    real_insert = invites.insert_invite
    monkeypatch.setattr(invites, "insert_invite", lambda **kw: real_insert(**{**kw, "role": "owner"}))
    with pytest.raises(IntegrityError, match="ck_invites_role"):
        _invite(world, email="new@example.com")
    assert _codes(world) == []


def test_creating_an_invite_logs_ids_never_the_code_or_the_email(world, caplog):
    caplog.set_level(logging.INFO, logger="usecases.members")
    out = _invite(world, email="secret@example.com", role="admin")
    [record] = [r for r in caplog.records if r.name == "usecases.members"]
    assert record.getMessage() == (f"invite_created church_id={world['church']} invite_id={out['id']} role=admin "
                                   "reusable=False email_bound=True")


def test_the_invite_list_hides_used_single_use_revoked_and_expired_and_keeps_used_reusable(world):
    single = _invite(world)
    reusable = _invite(world, reusable=True)
    revoked = _invite(world)
    expiring = members.create_invite(world["church"], world["owner"], now=NOW - timedelta(days=7))
    by_admin = members.create_invite(world["church"], world["admin"], now=NOW + timedelta(minutes=1))
    for invite in (single, reusable):
        invites.claim(invite["id"], world["member"], NOW)
    members.revoke_invite(world["church"], world["owner"], revoked["id"])
    with session_scope() as s:
        s.execute(update(User).where(User.id == world["admin"]).values(name=""))
    listed = members.list_invites(world["church"], now=NOW)
    assert [i["id"] for i in listed] == [by_admin["id"], reusable["id"]]
    assert listed[0]["created_by"] == {"user_id": world["admin"], "name": None, "email": "admin@example.com"}
    remove_membership(world["admin"], world["church"])
    with session_scope() as s:
        s.execute(delete(User).where(User.id == world["admin"]))
    assert members.list_invites(world["church"], now=NOW)[0]["created_by"] is None
    assert expiring["id"] not in [i["id"] for i in listed]


def test_revoking_an_invite_is_idempotent_and_church_scoped(world):
    mine = _invite(world)
    theirs = members.create_invite(world["other"], world["other_owner"], now=NOW)
    members.revoke_invite(world["church"], world["admin"], mine["id"])
    members.revoke_invite(world["church"], world["admin"], str(mine["id"]))       # again: still fine
    assert _invite_row(mine["id"]).revoked is True
    for invite_id in (theirs["id"], uuid.uuid4(), "not-a-uuid"):
        with pytest.raises(NotFound):
            members.revoke_invite(world["church"], world["admin"], invite_id)
    assert _invite_row(theirs["id"]).revoked is False


def test_a_member_may_not_create_or_revoke_invites(world):
    invite_id = _invite(world)["id"]
    for call in (lambda: _invite(world, who="member"),
                 lambda: members.revoke_invite(world["church"], world["member"], invite_id)):
        with pytest.raises(Forbidden) as refused:
            call()
        assert (refused.value.message, refused.value.details) == ("Only church admins can do this.", None)
    assert _invite_row(invite_id).revoked is False
