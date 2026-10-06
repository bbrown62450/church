"""/contacts over HTTP (slice 5b-1; 5b spec GET /contacts, 6a spec POST, PATCH
and DELETE /contacts): who may read and write, the order and the null names,
each address's check, the exact errors, and church isolation. The shared
address fixture runs through POST /contacts, as it runs through
normalize_address, so a contact can be saved exactly when it can be emailed."""
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from db import session_scope
from db.models import Contact
from repos.memberships import add_membership
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    assert_church_isolated,
    church_headers,
    isolation_world,
    make_api_client,
)

OWNER = "owner@example.com"
MEMBER = "member@example.com"
ADDRESSES = json.loads((Path(__file__).parent / "fixtures" / "shared" / "email_addresses.json").read_text(encoding="utf-8"))
ADMINS_ONLY = {"code": "forbidden", "message": "Only church admins can do this."}


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def church(make_user, make_church):
    cid = make_church(name="Grace", owner_user_id=make_user(email=OWNER))
    add_membership(make_user(email=MEMBER), cid, "member")
    return cid


def _error(r) -> dict:
    error = dict(r.json()["error"])
    error.pop("request_id")
    return error


def _list(client, church, email=OWNER) -> list[dict]:
    r = client.get("/contacts", headers=church_headers(email, church))
    assert r.status_code == 200, r.text
    return r.json()["items"]


def _add(client, church, body, email=OWNER):
    return client.post("/contacts", headers=church_headers(email, church), json=body)


def test_a_member_reads_the_list_in_order_with_blank_names_null_and_bad_addresses_flagged(client, church):
    at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    with session_scope() as s:
        for name, email in (("Zoe", "zoe@example.org"), ("", "blank@example.org"), (None, "null@example.org"),
                            ("Amy", "a@example.org, b@example.org")):
            s.add(Contact(church_id=church, name=name, email=email, created_at=at))
    items = _list(client, church, email=MEMBER)
    assert [(c["name"], c["email"], c["email_valid"]) for c in items[:2]] == [
        ("Amy", "a@example.org, b@example.org", False), ("Zoe", "zoe@example.org", True)]
    assert sorted((c["name"], c["email"], c["email_valid"]) for c in items[2:]) == [
        (None, "blank@example.org", True), (None, "null@example.org", True)]
    assert set(items[0]) == {"id", "name", "email", "email_valid"}


def test_an_admin_adds_edits_and_deletes_a_contact(client, church, make_user):
    add_membership(make_user(email="admin@example.com"), church, "admin")
    r = _add(client, church, {"name": " Mary ", "email": " Mary@Example.ORG "}, email="admin@example.com")
    assert r.status_code == 201, r.text
    mary = r.json()
    assert {k: mary[k] for k in ("name", "email", "email_valid")} == {
        "name": "Mary", "email": "Mary@example.org", "email_valid": True}
    assert _list(client, church) == [mary]

    path = f"/contacts/{mary['id']}"
    r = client.patch(path, headers=church_headers(OWNER, church), json={"name": "Mary Jones"})
    assert (r.status_code, r.json()["name"], r.json()["email"]) == (200, "Mary Jones", "Mary@example.org")
    r = client.patch(path, headers=church_headers(OWNER, church), json={"name": None, "email": "mary@example.org"})
    assert (r.status_code, r.json()["name"], r.json()["email"]) == (200, None, "mary@example.org")

    r = client.delete(path, headers=church_headers(OWNER, church))
    assert (r.status_code, r.json()) == (200, {"deleted": True})
    assert _list(client, church) == []
    r = client.delete(path, headers=church_headers(OWNER, church))
    assert (r.status_code, _error(r)) == (404, {"code": "not_found", "message": "Contact not found."})


def test_a_member_cannot_add_edit_or_delete(client, church):
    mary = _add(client, church, {"name": "Mary", "email": "mary@example.org"}).json()
    for method, path, body in (("POST", "/contacts", {"email": "x@example.org"}),
                               ("PATCH", f"/contacts/{mary['id']}", {"name": "Renamed"}),
                               ("DELETE", f"/contacts/{mary['id']}", None)):
        r = client.request(method, path, headers=church_headers(MEMBER, church), json=body)
        assert (r.status_code, _error(r)) == (403, ADMINS_ONLY), f"{method} {path}"
    assert [(c["name"], c["email"]) for c in _list(client, church)] == [("Mary", "mary@example.org")]


@pytest.mark.parametrize("body, field, message", [
    ({"name": "Mary"}, "email", "Email is required."),
    ({"email": "   "}, "email", "Email is required."),
    ({"email": "mary@example"}, "email", "Enter a valid email address."),
    ({"name": "Mary\nJones", "email": "mary@example.org"}, "name",
     "Name can't contain line breaks or control characters."),
    ({"name": "x" * 201, "email": "mary@example.org"}, "name", "Too long (max 200 characters)."),
    ({"email": "m" * 321}, "email", "Too long (max 320 characters)."),
])
def test_a_bad_field_is_a_422_naming_it(client, church, body, field, message):
    r = _add(client, church, body)
    assert r.status_code == 422, r.text
    assert (r.json()["error"]["code"], r.json()["error"]["fields"]) == ("invalid_request", {field: message})
    assert _list(client, church) == []


def test_an_address_already_saved_in_any_case_is_a_409(client, church):
    mary = _add(client, church, {"name": "Mary", "email": "mary@example.org"}).json()
    office = _add(client, church, {"email": "office@example.org"}).json()
    taken = {"code": "conflict", "message": "That email is already in your contacts."}
    r = _add(client, church, {"name": "Again", "email": "MARY@example.org"})
    assert (r.status_code, _error(r)) == (409, taken)
    r = client.patch(f"/contacts/{office['id']}", headers=church_headers(OWNER, church),
                     json={"email": "Mary@Example.org"})
    assert (r.status_code, _error(r)) == (409, taken)
    r = client.patch(f"/contacts/{mary['id']}", headers=church_headers(OWNER, church),
                     json={"email": "MARY@example.org"})                       # its own address, new case
    assert (r.status_code, r.json()["email"]) == (200, "MARY@example.org")


def test_every_shared_address_case_is_accepted_or_refused_as_normalize_address_says(client, church):
    for case in ADDRESSES["valid"]:
        r = _add(client, church, {"email": case["raw"]})
        assert (r.status_code, r.json().get("email")) == (201, case["normalized"]), case["raw"]
    for raw in ADDRESSES["invalid"]:
        r = _add(client, church, {"email": raw})
        assert r.status_code == 422, raw
        assert r.json()["error"]["fields"] == {"email": "Enter a valid email address."}, raw
    assert [c["email"] for c in _list(client, church)] == [case["normalized"] for case in ADDRESSES["valid"]]


def test_unknown_fields_and_malformed_ids_are_422(client, church):
    r = _add(client, church, {"email": "mary@example.org", "church_id": str(church)})
    assert (r.status_code, r.json()["error"]["code"]) == (422, "invalid_request")
    r = client.patch("/contacts/not-a-uuid", headers=church_headers(OWNER, church), json={"name": "X"})
    assert (r.status_code, r.json()["error"]["code"]) == (422, "invalid_request")


def test_contacts_are_isolated_between_churches(client, isolation_world):
    world = isolation_world
    theirs = _add(client, world.church_b, {"name": "Theirs", "email": "theirs@example.org"}, email=world.b).json()
    assert_church_isolated(client, "GET", "/contacts", world=world)
    assert_church_isolated(client, "POST", "/contacts", world=world, json={"email": "ours@example.org"})
    second = _add(client, world.church_a, {"email": "second@example.org"}, email=world.a).json()
    assert_church_isolated(client, "PATCH", f"/contacts/{second['id']}", world=world, json={"name": "Ours"},
                           resource_path_b=f"/contacts/{theirs['id']}")
    assert_church_isolated(client, "DELETE", f"/contacts/{second['id']}", world=world,
                           resource_path_b=f"/contacts/{theirs['id']}")
    assert [(c["name"], c["email"]) for c in _list(client, world.church_b, email=world.b)] == [
        ("Theirs", "theirs@example.org")]
    assert [c["email"] for c in _list(client, world.church_a, email=world.a)] == ["ours@example.org"]
