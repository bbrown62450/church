"""/members over HTTP (6b spec, API and Testing → API; slice 6b-1): every
member reads the list with emails; owners and admins change roles and remove
people under the policy's exact messages; a removal revokes the removed
person's invites (and, when asked, every reusable link), end to end with
slice 1's accept; a write whose church or caller went after the guard ran is
the no_church_access 403; and church isolation."""
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

import pytest
from fastapi import Depends, Header

from api.deps import CurrentUser, get_current_user, require_church
from db import session_scope
from db.models import Church
from repos.memberships import add_membership, get_role, remove_membership
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    assert_church_isolated,
    auth_headers,
    church_headers,
    isolation_world,
    make_api_client,
)

OWNER, ADMIN, MEMBER = "owner@example.com", "admin@example.com", "member@example.com"
NO_ACCESS = {"code": "forbidden", "message": "You don't have access to this church.",
             "details": {"reason": "no_church_access"}}


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def church(make_user, make_church):
    cid = make_church(name="Grace", owner_user_id=make_user(email=OWNER))
    add_membership(make_user(email=ADMIN), cid, "admin")
    add_membership(make_user(email=MEMBER), cid, "member")
    return cid


def _error(r) -> dict:
    error = dict(r.json()["error"])
    error.pop("request_id")
    return error


def _id(client, church, email) -> str:
    r = client.get("/members", headers=church_headers(OWNER, church))
    return next(m["user_id"] for m in r.json()["items"] if m["email"] == email)


def _role(client, church, email, role, *, by=OWNER):
    return client.patch(f"/members/{_id(client, church, email)}", headers=church_headers(by, church),
                        json={"role": role})


def _remove(client, church, email, *, by=OWNER, query=""):
    return client.delete(f"/members/{_id(client, church, email)}{query}", headers=church_headers(by, church))


def test_a_member_reads_every_member_with_emails(client, church):
    r = client.get("/members", headers=church_headers(MEMBER, church))
    assert r.status_code == 200, r.text
    assert [(m["email"], m["role"], m["is_me"]) for m in r.json()["items"]] == [
        (OWNER, "owner", False), (ADMIN, "admin", False), (MEMBER, "member", True)]
    assert set(r.json()["items"][0]) == {"user_id", "email", "name", "role", "is_me"}
    assert client.get("/members", headers=auth_headers(MEMBER)).status_code == 403   # no X-Church-Id


def test_an_admin_makes_a_member_an_admin_and_back(client, church):
    r = _role(client, church, MEMBER, "admin", by=ADMIN)
    assert (r.status_code, r.json()["email"], r.json()["role"], r.json()["is_me"]) == (200, MEMBER, "admin", False)
    assert _role(client, church, MEMBER, "member", by=ADMIN).json()["role"] == "member"


def test_member_cannot_change_role_or_remove(client, church):
    for r in (_role(client, church, ADMIN, "member", by=MEMBER), _remove(client, church, ADMIN, by=MEMBER)):
        assert (r.status_code, _error(r)) == (403, {"code": "forbidden", "message": "Only church admins can do this."})


@pytest.mark.parametrize("by, target, verb, message", [
    (ADMIN, OWNER, "patch", "The owner's role can't be changed."),
    (ADMIN, OWNER, "delete", "The owner can't be removed."),
    (ADMIN, ADMIN, "patch", "You can't change your own role."),
    (ADMIN, ADMIN, "delete", "To leave this church, use Leave church in Danger zone."),
    (OWNER, OWNER, "patch", "You can't change your own role."),
])
def test_the_policy_messages_over_http(client, church, by, target, verb, message):
    r = (_role(client, church, target, "member", by=by) if verb == "patch"
         else _remove(client, church, target, by=by))
    assert (r.status_code, _error(r)) == (403, {"code": "forbidden", "message": message})


def test_owner_cannot_be_removed_even_by_self(client, church):
    """The Streamlit scenario of the last admin removing themselves: now a 403, and the owner stays."""
    r = _remove(client, church, OWNER, by=OWNER)
    assert (r.status_code, _error(r)["message"]) == (403, "To leave this church, use Leave church in Danger zone.")
    assert _id(client, church, OWNER)


@pytest.mark.parametrize("body", [{"role": "owner"}, {"role": "pastor"}, {}, {"role": "admin", "church_id": "x"}])
def test_a_role_that_cannot_be_assigned_is_a_422(client, church, body):
    r = client.patch(f"/members/{_id(client, church, MEMBER)}", headers=church_headers(OWNER, church), json=body)
    assert (r.status_code, r.json()["error"]["code"]) == (422, "invalid_request")
    if body.get("role") == "owner":
        assert r.json()["error"]["fields"] == {"role": "Not a valid value."}


def test_a_malformed_id_or_flag_is_a_422_and_a_stranger_is_a_404(client, church, make_user):
    headers = church_headers(OWNER, church)
    assert client.patch("/members/not-a-uuid", headers=headers, json={"role": "admin"}).status_code == 422
    assert client.delete(f"/members/{_id(client, church, MEMBER)}?revoke_reusable=maybe",
                         headers=headers).status_code == 422
    stranger = make_user(email="stranger@example.com")
    for r in (client.patch(f"/members/{stranger}", headers=headers, json={"role": "admin"}),
              client.delete(f"/members/{uuid.uuid4()}", headers=headers)):
        assert (r.status_code, _error(r)) == (404, {"code": "not_found", "message": "Member not found."})


def test_no_409_is_documented_for_a_role_change_or_a_removal(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert sorted(paths["/members/{user_id}"]["patch"]["responses"]) == ["200", "401", "403", "404", "422", "503"]
    assert sorted(paths["/members/{user_id}"]["delete"]["responses"]) == ["200", "401", "403", "404", "422", "503"]


# --- removal sticks (end to end with slice 1's POST /invites/accept) ---


def _create(client, church, *, by=OWNER, **body) -> dict:
    r = client.post("/invites", headers=church_headers(by, church), json=body)
    assert r.status_code == 201, r.text
    return r.json()


def _accept(client, email, code):
    return client.post("/invites/accept", headers=auth_headers(email), json={"code": code})


def test_a_removed_member_cannot_rejoin_with_a_reusable_link_revoked_on_removal(client, church, make_user):
    make_user(email="x@example.com")
    link = _create(client, church, reusable=True)
    assert _accept(client, "x@example.com", link["code"]).status_code == 200
    r = _remove(client, church, "x@example.com", query="?revoke_reusable=true")
    assert (r.status_code, r.json()["removed"]) == (200, True) and r.json()["revoked_invites"] >= 1
    r = _accept(client, "x@example.com", link["code"])
    assert (r.status_code, r.json()["error"]["message"]) == (400, "This invite has been revoked.")


def test_without_the_flag_a_reusable_link_still_lets_them_rejoin(client, church, make_user):
    make_user(email="x@example.com")
    link = _create(client, church, reusable=True)
    _accept(client, "x@example.com", link["code"])
    assert _remove(client, church, "x@example.com").json() == {"removed": True, "revoked_invites": 0}
    assert _accept(client, "x@example.com", link["code"]).status_code == 200


def test_a_removed_admin_cannot_redeem_the_invites_they_made(client, church, make_user):
    make_user(email="y@example.com")
    single = _create(client, church, by=ADMIN)
    promoting = _create(client, church, by=ADMIN, role="admin", email="y@example.com")
    assert _remove(client, church, ADMIN).json() == {"removed": True, "revoked_invites": 2}
    for email, invite in ((ADMIN, single), ("y@example.com", promoting)):
        r = _accept(client, email, invite["code"])
        assert (r.status_code, r.json()["error"]["message"]) == (400, "This invite has been revoked.")


def test_a_used_single_use_link_stays_used_after_a_removal(client, church, make_user):
    make_user(email="x@example.com")
    single = _create(client, church)
    assert _accept(client, "x@example.com", single["code"]).status_code == 200
    _remove(client, church, "x@example.com")
    r = _accept(client, "x@example.com", single["code"])
    assert (r.status_code, r.json()["error"]["message"]) == (400, "This invite has already been used.")


# --- the church or the caller gone after the guard ran ---


def _late(client, change):
    """Wrap require_church: run the real guard, then change the database before the route body."""
    def late_guard(user: CurrentUser = Depends(get_current_user),
                   x_church_id: Optional[str] = Header(default=None)):
        active = require_church(user, x_church_id)
        change(active, user)
        return active

    client.app.dependency_overrides[require_church] = late_guard


def _soft_delete(active, _user):
    with session_scope() as s:
        s.get(Church, active.id).deleted_at = datetime.now(timezone.utc)


def _drop_caller(active, user):
    remove_membership(user.id, active.id)


WRITES = [
    ("PATCH", "/members/{member}", {"role": "admin"}),
    ("DELETE", "/members/{member}", None),
    ("POST", "/invites", {"email": "late@example.com"}),
    ("DELETE", "/invites/{invite}", None),
    ("POST", "/church/transfer-ownership", {"user_id": "{member}"}),
    ("POST", "/church/leave", None),
    ("DELETE", "/church", {"confirm_name": "Grace"}),
]


@pytest.mark.parametrize("method, path, body", WRITES, ids=[f"{m} {p}" for m, p, _ in WRITES])
def test_a_write_whose_church_was_deleted_after_the_guard_is_no_church_access(client, church, method, path, body):
    names = {"member": _id(client, church, MEMBER), "invite": _create(client, church)["id"]}
    _late(client, _soft_delete)
    r = client.request(method, path.format(**names), headers=church_headers(OWNER, church),
                       json=json.loads(json.dumps(body).replace("{member}", names["member"])) if body else None)
    assert (r.status_code, _error(r)) == (403, NO_ACCESS)
    client.app.dependency_overrides.clear()
    assert get_role(uuid.UUID(names["member"]), church) == "member"


@pytest.mark.parametrize("method, path, body", [WRITES[0], WRITES[2]], ids=["PATCH /members", "POST /invites"])
def test_a_write_whose_caller_was_removed_after_the_guard_is_no_church_access(client, church, method, path, body):
    member = _id(client, church, MEMBER)
    _late(client, _drop_caller)
    r = client.request(method, path.format(member=member), headers=church_headers(ADMIN, church), json=body)
    assert (r.status_code, _error(r)) == (403, NO_ACCESS)


def test_a_role_403_carries_no_reason(client, church):
    r = _role(client, church, ADMIN, "member", by=MEMBER)
    assert "details" not in r.json()["error"]


# --- church isolation ---


def test_every_members_route_is_church_isolated(client, isolation_world, make_user):
    w = isolation_world
    a_member = make_user(email="am@example.com")
    add_membership(a_member, w.church_a, "member")
    b_member = make_user(email="bm@example.com")
    add_membership(b_member, w.church_b, "member")
    assert_church_isolated(client, "GET", "/members", world=w)
    assert_church_isolated(client, "PATCH", f"/members/{a_member}", world=w, json={"role": "admin"},
                           resource_path_b=f"/members/{b_member}")
    assert_church_isolated(client, "DELETE", f"/members/{a_member}", world=w,
                           resource_path_b=f"/members/{b_member}")
    assert get_role(b_member, w.church_b) == "member"
