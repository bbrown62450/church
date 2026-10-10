"""GET, POST and DELETE /invites over HTTP (6b spec, API, "Invite semantics"
and Testing → API; slice 6b-1): owners and admins only; single-use by
default, reusable on request, email-bound ones single-use; the exact 409s
and 422s; no-store answers; Idempotency-Key replays; codes never logged;
revocation scoped to the church; and the invites working end to end with
slice 1's POST /invites/accept."""
import logging
import uuid

import pytest
from sqlalchemy import func, select

from db import session_scope
from db.models import Invite
from repos.memberships import add_membership
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    assert_church_isolated,
    auth_headers,
    church_headers,
    isolation_world,
    make_api_client,
)

OWNER, ADMIN, MEMBER = "owner@example.com", "admin@example.com", "member@example.com"
ADMINS_ONLY = {"code": "forbidden", "message": "Only church admins can do this."}


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


def _create(client, church, body=None, *, by=ADMIN, key=None):
    headers = church_headers(by, church)
    if key is not None:
        headers["Idempotency-Key"] = key
    return client.post("/invites", headers=headers, json=body if body is not None else {})


def _list(client, church, by=ADMIN):
    return client.get("/invites", headers=church_headers(by, church))


def _rows() -> int:
    with session_scope() as s:
        return s.execute(select(func.count()).select_from(Invite)).scalar_one()


def test_member_cannot_create_list_or_revoke_invites(client, church):
    for r in (_create(client, church, by=MEMBER), _list(client, church, by=MEMBER),
              client.delete(f"/invites/{uuid.uuid4()}", headers=church_headers(MEMBER, church))):
        assert (r.status_code, _error(r)) == (403, ADMINS_ONLY)
    assert _rows() == 0


def test_admin_creates_single_use_invite(client, church):
    r = _create(client, church)
    assert r.status_code == 201, r.text
    assert r.headers["cache-control"] == "no-store"
    out = r.json()
    assert set(out) == {"id", "code", "email", "role", "reusable", "created_at", "expires_at", "created_by"}
    assert len(out["code"]) >= 22
    assert (out["email"], out["role"], out["reusable"], out["created_by"]["email"]) == (None, "member", False, ADMIN)
    assert out["created_at"].endswith("Z") or "+00:00" in out["created_at"]
    listed = _list(client, church)
    assert listed.headers["cache-control"] == "no-store"
    assert listed.json() == {"items": [out]}


def test_an_owner_creates_a_reusable_admin_link(client, church):
    out = _create(client, church, {"role": "admin", "reusable": True}, by=OWNER).json()
    assert (out["role"], out["reusable"]) == ("admin", True)


@pytest.mark.parametrize("body, fields", [
    ({"email": "x@example.com", "reusable": True}, {"reusable": "A link for one email address works once."}),
    ({"email": "not an address"}, {"email": "Enter a valid email address."}),
    ({"role": "owner"}, {"role": "Not a valid value."}),
    ({"email": "x" * 321}, {"email": "Too long (max 320 characters)."}),
])
def test_a_bad_invite_is_a_422_naming_its_field(client, church, body, fields):
    r = _create(client, church, body)
    assert (r.status_code, r.json()["error"]["code"], r.json()["error"]["fields"]) == (422, "invalid_request", fields)
    assert _rows() == 0


def test_a_church_id_in_the_body_is_refused_and_nothing_is_created(client, church, make_church, make_user):
    other = make_church(name="Hope", owner_user_id=make_user(email="h@example.com"))
    r = _create(client, church, {"church_id": str(other)})
    assert (r.status_code, r.json()["error"]["code"]) == (422, "invalid_request")
    assert _rows() == 0


def test_the_two_conflicts_have_their_codes_and_words(client, church):
    _create(client, church, {"email": "new@example.com"})
    r = _create(client, church, {"email": " NEW@example.com "})
    assert (r.status_code, _error(r)) == (409, {
        "code": "invite_exists",
        "message": "There's already a pending invite for new@example.com. Copy its link below or revoke it first."})
    r = _create(client, church, {"email": "Member@Example.com"})
    assert (r.status_code, _error(r)) == (409, {"code": "conflict",
                                                "message": "member@example.com is already a member of this church."})


def test_an_idempotency_key_replays_the_same_invite_once(client, church):
    key = str(uuid.uuid4())
    first = _create(client, church, {"role": "admin"}, key=key)
    again = _create(client, church, {"role": "admin"}, key=key)
    assert (first.status_code, again.status_code) == (201, 201)
    assert (again.json()["id"], again.json()["code"]) == (first.json()["id"], first.json()["code"])
    assert again.headers["idempotent-replayed"] == "true" and again.headers["cache-control"] == "no-store"
    assert _rows() == 1
    r = _create(client, church, {"role": "member"}, key=key)
    assert (r.status_code, r.json()["error"]["code"]) == (422, "idempotency_mismatch")


def test_codes_and_emails_never_reach_the_logs(client, church, caplog):
    caplog.set_level(logging.DEBUG)
    out = _create(client, church, {"email": "secret@example.com"}).json()
    _list(client, church)
    client.delete(f"/invites/{out['id']}", headers=church_headers(ADMIN, church))
    text = "\n".join(f"{r.getMessage()} {r.args}" for r in caplog.records)
    assert out["code"] not in text and "secret@example.com" not in text
    assert f"invite_id={out['id']}" in text


def test_revoking_is_idempotent_and_scoped_to_the_church(client, church, make_church, make_user):
    out = _create(client, church).json()
    for _ in range(2):
        r = client.delete(f"/invites/{out['id']}", headers=church_headers(ADMIN, church))
        assert (r.status_code, r.json()) == (200, {"revoked": True})
    assert _list(client, church).json() == {"items": []}
    other = make_church(name="Hope", owner_user_id=make_user(email="h@example.com"))
    theirs = _create(client, other, by="h@example.com").json()
    r = client.delete(f"/invites/{theirs['id']}", headers=church_headers(ADMIN, church))
    assert (r.status_code, _error(r)) == (404, {"code": "not_found", "message": "Invite not found."})
    assert _list(client, other, by="h@example.com").json()["items"] == [theirs]
    assert client.delete("/invites/not-a-uuid", headers=church_headers(ADMIN, church)).status_code == 422


def test_a_single_use_link_works_once_and_a_reusable_one_for_everyone(client, church, make_user):
    for email in ("x@example.com", "y@example.com"):
        make_user(email=email)
    single = _create(client, church).json()
    assert client.post("/invites/accept", headers=auth_headers("x@example.com"),
                       json={"code": single["code"]}).status_code == 200
    r = client.post("/invites/accept", headers=auth_headers("y@example.com"), json={"code": single["code"]})
    assert (r.status_code, r.json()["error"]["message"]) == (400, "This invite has already been used.")
    reusable = _create(client, church, {"reusable": True}).json()
    for email in ("x@example.com", "y@example.com"):
        r = client.post("/invites/accept", headers=auth_headers(email), json={"code": reusable["code"]})
        assert r.status_code == 200, r.text
    assert [i["id"] for i in _list(client, church).json()["items"]] == [reusable["id"]]


def test_every_invites_route_is_church_isolated(client, isolation_world):
    w = isolation_world
    theirs = _create(client, w.church_b, by=w.b).json()
    mine = _create(client, w.church_a, by=w.a).json()
    assert_church_isolated(client, "GET", "/invites", world=w)
    assert_church_isolated(client, "POST", "/invites", world=w, json={})
    assert_church_isolated(client, "DELETE", f"/invites/{mine['id']}", world=w,
                           resource_path_b=f"/invites/{theirs['id']}")
    assert _list(client, w.church_b, by=w.b).json()["items"] == [theirs]
