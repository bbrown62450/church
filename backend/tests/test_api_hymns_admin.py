"""POST, PATCH and DELETE /hymns over HTTP (6a spec, API rows and Models;
slice 6a-2): who may do what (members add and edit, admins delete and set the
year and familiarity), the exact errors with their fields, the 409, and church
isolation. Ports streamlit_tests' test_member_can_add_hymn."""
from datetime import date

import pytest

from db import session_scope
from db.models import Hymn
from repos.memberships import add_membership
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    assert_church_isolated,
    church_headers,
    isolation_world,
    make_api_client,
)

OWNER = "owner@example.com"
MEMBER = "member@example.com"
ADMINS_ONLY = {"code": "forbidden", "message": "Only church admins can do this."}
THIS_YEAR = date.today().year


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def church(make_user, make_church):
    cid = make_church(name="Grace", owner_user_id=make_user(email=OWNER))
    add_membership(make_user(email=MEMBER), cid, "member")
    with session_scope() as s:
        s.add(Hymn(church_id=cid, hymnal="GG2013", title="Holy, Holy, Holy", number=138))
    return cid


def _error(r) -> dict:
    error = dict(r.json()["error"])
    error.pop("request_id")
    return error


def _add(client, church, body, email=MEMBER):
    return client.post("/hymns", headers=church_headers(email, church), json=body)


def _titles(client, church, q="") -> list[str]:
    r = client.get(f"/hymns?q={q}", headers=church_headers(MEMBER, church))
    assert r.status_code == 200, r.text
    return [h["title"] for h in r.json()["items"]]


def test_a_member_adds_and_edits_a_hymn_and_it_is_listed(client, church):
    r = _add(client, church, {"title": " Be Thou My Vision ", "number": 339, "scripture_refs": "Psalm 16:5",
                              "theme": "Guidance, Vision", "link": "https://hymnary.org/hymn/GG2013/339"})
    assert r.status_code == 201, r.text
    added = r.json()
    assert set(added) == {"id", "hymnal", "title", "number", "scripture_refs", "theme", "link", "text_year",
                          "hymnal_count"}
    assert (added["hymnal"], added["title"], added["theme"], added["text_year"]) == (
        "GG2013", "Be Thou My Vision", "Guidance, Vision", None)
    assert _titles(client, church, "339") == ["Be Thou My Vision"]

    r = client.patch(f"/hymns/{added['id']}", headers=church_headers(MEMBER, church),
                     json={"title": "Be Thou My Vision!", "theme": None})
    assert r.status_code == 200, r.text
    assert (r.json()["title"], r.json()["theme"], r.json()["number"]) == ("Be Thou My Vision!", None, 339)
    assert _titles(client, church) == ["Holy, Holy, Holy", "Be Thou My Vision!"]


def test_only_admins_delete_a_hymn_or_send_its_year_or_familiarity(client, church):
    hid = _add(client, church, {"title": "Doomed", "number": 1}).json()["id"]
    for method, path, body in (("DELETE", f"/hymns/{hid}", None),
                               ("POST", "/hymns", {"title": "Facts", "text_year": 1826}),
                               ("POST", "/hymns", {"title": "Facts", "hymnal_count": 0}),
                               ("PATCH", f"/hymns/{hid}", {"text_year": None}),
                               ("PATCH", f"/hymns/{hid}", {"hymnal_count": 12})):
        r = client.request(method, path, headers=church_headers(MEMBER, church), json=body)
        assert (r.status_code, _error(r)) == (403, ADMINS_ONLY), f"{method} {path} {body}"
    r = client.patch(f"/hymns/{hid}", headers=church_headers(OWNER, church),
                     json={"text_year": 1826, "hymnal_count": 1322})
    assert (r.status_code, r.json()["text_year"], r.json()["hymnal_count"]) == (200, 1826, 1322)
    r = client.delete(f"/hymns/{hid}", headers=church_headers(OWNER, church))
    assert (r.status_code, r.json()) == (200, {"deleted": True})
    r = client.delete(f"/hymns/{hid}", headers=church_headers(OWNER, church))
    assert (r.status_code, _error(r)) == (404, {"code": "not_found", "message": "Hymn not found."})
    assert _titles(client, church) == ["Holy, Holy, Holy"]


@pytest.mark.parametrize("body, field, message", [
    ({}, "title", "Hymn title is required."),
    ({"title": None}, "title", "Hymn title is required."),
    ({"title": "X", "number": 0}, "number", "Hymn number must be a whole number."),
    ({"title": "X", "number": 1.5}, "number", "Not a valid value."),
    ({"title": "X", "hymnal": "PH1990"}, "hymnal", "Choose one of your church's hymnals."),
    ({"title": "X", "link": "http://example.org"}, "link", "Links must start with https://."),
    ({"title": "X", "text_year": THIS_YEAR + 1}, "text_year", f"Year must be a whole number from 1 to {THIS_YEAR}."),
    ({"title": "X", "hymnal_count": 100001}, "hymnal_count",
     "Number of hymnals must be a whole number from 0 to 100000."),
    ({"title": "x" * 301}, "title", "Too long (max 300 characters)."),
])
def test_a_bad_field_is_a_422_naming_it(client, church, body, field, message):
    r = _add(client, church, body, email=OWNER)
    assert r.status_code == 422, r.text
    assert (r.json()["error"]["code"], r.json()["error"]["fields"]) == ("invalid_request", {field: message})
    assert _titles(client, church) == ["Holy, Holy, Holy"]


def test_the_same_hymn_twice_is_a_409(client, church):
    r = _add(client, church, {"title": "holy, holy, HOLY", "number": 138})
    assert (r.status_code, _error(r)) == (409, {"code": "conflict",
                                               "message": "GG2013 already has #138 holy, holy, HOLY."})
    hid = _add(client, church, {"title": "Untitled"}).json()["id"]
    r = client.patch(f"/hymns/{hid}", headers=church_headers(MEMBER, church),
                     json={"title": "Holy, Holy, Holy", "number": 138})
    assert (r.status_code, _error(r)["message"]) == (409, "GG2013 already has #138 Holy, Holy, Holy.")


def test_unknown_fields_and_malformed_or_unknown_ids(client, church):
    r = _add(client, church, {"title": "X", "church_id": str(church)})
    assert (r.status_code, r.json()["error"]["code"]) == (422, "invalid_request")
    r = client.patch("/hymns/not-a-uuid", headers=church_headers(MEMBER, church), json={"title": "X"})
    assert (r.status_code, r.json()["error"]["code"]) == (422, "invalid_request")
    r = client.patch("/hymns/00000000-0000-4000-8000-000000000000", headers=church_headers(MEMBER, church),
                     json={"title": "X"})
    assert (r.status_code, _error(r)) == (404, {"code": "not_found", "message": "Hymn not found."})


def test_hymn_writes_are_isolated_between_churches(client, isolation_world):
    world = isolation_world
    theirs = _add(client, world.church_b, {"title": "Theirs"}, email=world.b).json()
    assert_church_isolated(client, "POST", "/hymns", world=world, json={"title": "Ours"})
    ours = _add(client, world.church_a, {"title": "Second"}, email=world.a).json()
    assert_church_isolated(client, "PATCH", f"/hymns/{ours['id']}", world=world, json={"title": "Ours 2"},
                           resource_path_b=f"/hymns/{theirs['id']}")
    assert_church_isolated(client, "DELETE", f"/hymns/{ours['id']}", world=world,
                           resource_path_b=f"/hymns/{theirs['id']}")
    r = client.get("/hymns", headers=church_headers(world.b, world.church_b))
    assert [h["title"] for h in r.json()["items"]] == ["Theirs"]
