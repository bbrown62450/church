"""POST /church/transfer-ownership, POST /church/leave and DELETE /church over
HTTP (6b spec, API and Testing → API; slice 6b-1): only the owner transfers
and deletes; transfer answers the members afterwards; leave refuses the owner
and the last admin of an ownerless church; delete needs the church's exact
name and revokes its invites; and church isolation."""
import uuid

import pytest

from repos.churches import get_church
from repos.memberships import add_membership, get_role, remove_membership
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    assert_church_isolated,
    auth_headers,
    church_headers,
    isolation_world,
    make_api_client,
)

OWNER, ADMIN, MEMBER = "owner@example.com", "admin@example.com", "member@example.com"
OWNER_ONLY = {"code": "forbidden", "message": "Only the owner can do that."}


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def people(make_user, make_church):
    ids = {email: make_user(email=email) for email in (OWNER, ADMIN, MEMBER)}
    cid = make_church(name="Grace", owner_user_id=ids[OWNER])
    add_membership(ids[ADMIN], cid, "admin")
    add_membership(ids[MEMBER], cid, "member")
    return cid, ids


def _error(r) -> dict:
    error = dict(r.json()["error"])
    error.pop("request_id")
    return error


def _transfer(client, church, to, *, by=OWNER):
    return client.post("/church/transfer-ownership", headers=church_headers(by, church), json={"user_id": str(to)})


def _delete(client, church, name, *, by=OWNER):
    return client.request("DELETE", "/church", headers=church_headers(by, church), json={"confirm_name": name})


def _my_churches(client, email) -> list:
    return [c["name"] for c in client.get("/me", headers=auth_headers(email)).json()["churches"]]


def test_admin_cannot_transfer_or_delete(client, people):
    church, ids = people
    for r in (_transfer(client, church, ids[MEMBER], by=ADMIN), _delete(client, church, "Grace", by=ADMIN)):
        assert (r.status_code, _error(r)) == (403, OWNER_ONLY)
    assert get_church(church) is not None and get_role(ids[OWNER], church) == "owner"


def test_the_owner_transfers_and_becomes_an_admin(client, people):
    church, ids = people
    r = _transfer(client, church, ids[MEMBER])
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert items[0]["email"] == MEMBER and items[0]["role"] == "owner"
    assert sorted((m["email"], m["role"], m["is_me"]) for m in items[1:]) == [(ADMIN, "admin", False),
                                                                              (OWNER, "admin", True)]
    assert client.get("/church", headers=church_headers(OWNER, church)).json()["role"] == "admin"
    r = _transfer(client, church, ids[ADMIN])                           # no longer the owner
    assert (r.status_code, _error(r)) == (403, OWNER_ONLY)


def test_a_transfer_to_oneself_a_stranger_or_a_bad_body_is_refused(client, people, make_user):
    church, ids = people
    r = _transfer(client, church, ids[OWNER])
    assert (r.status_code, r.json()["error"]["fields"]) == (422, {"user_id": "Choose someone else to be the new owner."})
    for stranger in (make_user(email="stranger@example.com"), uuid.uuid4()):
        r = _transfer(client, church, stranger)
        assert (r.status_code, _error(r)) == (404, {"code": "not_found", "message": "Member not found."})
    for body in ({}, {"user_id": "not-a-uuid"}, {"user_id": str(ids[MEMBER]), "role": "owner"}):
        r = client.post("/church/transfer-ownership", headers=church_headers(OWNER, church), json=body)
        assert r.status_code == 422
    assert get_role(ids[OWNER], church) == "owner"


@pytest.mark.parametrize("who", [ADMIN, MEMBER])
def test_a_member_or_an_admin_leaves(client, people, who):
    church, _ids = people
    r = client.post("/church/leave", headers=church_headers(who, church))
    assert (r.status_code, r.json()) == (200, {"left": True})
    assert _my_churches(client, who) == []
    r = client.post("/church/leave", headers=church_headers(who, church))     # again: no longer a member
    assert (r.status_code, r.json()["error"]["details"]) == (403, {"reason": "no_church_access"})


def test_the_owner_and_the_last_admin_of_an_ownerless_church_cannot_leave(client, people):
    church, ids = people
    r = client.post("/church/leave", headers=church_headers(OWNER, church))
    assert (r.status_code, _error(r)) == (409, {
        "code": "owner_must_transfer",
        "message": "Transfer ownership before you leave. If you're the only person in the church, delete it instead."})
    remove_membership(ids[OWNER], church)                               # made ownerless outside the app
    r = client.post("/church/leave", headers=church_headers(ADMIN, church))
    assert (r.status_code, _error(r)) == (409, {
        "code": "last_admin", "message": "You're the last admin. Make someone else an admin before you leave."})
    assert get_role(ids[ADMIN], church) == "admin"


def test_delete_needs_the_exact_name_and_leaves_everyone_without_the_church(client, people, make_user):
    church, ids = people
    make_user(email="x@example.com")
    code = client.post("/invites", headers=church_headers(OWNER, church), json={}).json()["code"]
    r = _delete(client, church, "grace")
    assert (r.status_code, r.json()["error"]["fields"]) == (422, {"confirm_name": "Church name did not match."})
    assert client.request("DELETE", "/church", headers=church_headers(OWNER, church)).status_code == 422  # no body
    r = _delete(client, church, "  Grace ")
    assert (r.status_code, r.json()) == (200, {"deleted": True})
    assert get_church(church) is None
    assert [_my_churches(client, email) for email in (OWNER, ADMIN, MEMBER)] == [[], [], []]
    r = client.post("/invites/accept", headers=auth_headers("x@example.com"), json={"code": code})
    assert (r.status_code, r.json()["error"]["message"]) == (400, "This invite has been revoked.")


def test_every_lifecycle_route_is_church_isolated(client, isolation_world, make_user):
    w = isolation_world
    a_member = make_user(email="am@example.com")
    add_membership(a_member, w.church_a, "member")
    assert_church_isolated(client, "POST", "/church/leave", world=w)             # a@ owns A: the control is a 409
    r = client.request("DELETE", "/church", headers=church_headers(w.a, w.church_a),
                       json={"confirm_name": "Church B"})                        # B's name, acting in A
    assert (r.status_code, r.json()["error"]["fields"]) == (422, {"confirm_name": "Church name did not match."})
    assert_church_isolated(client, "DELETE", "/church", world=w, json={"confirm_name": "Church B"})
    assert get_church(w.church_a) is not None and get_church(w.church_b) is not None
    assert_church_isolated(client, "POST", "/church/transfer-ownership", world=w, json={"user_id": str(a_member)})
    assert get_role(a_member, w.church_a) == "owner"                             # the control, last
