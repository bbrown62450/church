"""GET /hymnal-sources, POST /hymnals and DELETE /hymnals/{code} over HTTP (6a
spec, API rows; slice 6a-2): owners and admins only, the bundled PH1990 added
once, a hymnal removed but never the only or the default one, the exact errors,
and church isolation."""
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


@pytest.fixture
def client(tmp_db):
    return make_api_client()


def _seed(church_id, hymnal="GG2013", count=2):
    with session_scope() as s:
        for n in range(1, count + 1):
            s.add(Hymn(church_id=church_id, hymnal=hymnal, title=f"{hymnal} {n}", number=n))


@pytest.fixture
def church(make_user, make_church):
    cid = make_church(name="Grace", owner_user_id=make_user(email=OWNER))
    add_membership(make_user(email=MEMBER), cid, "member")
    _seed(cid)
    return cid


def _error(r) -> dict:
    error = dict(r.json()["error"])
    error.pop("request_id")
    return error


def _sources(client, church) -> dict:
    r = client.get("/hymnal-sources", headers=church_headers(OWNER, church))
    assert r.status_code == 200, r.text
    return {s["code"]: s for s in r.json()["items"]}


def _codes(client, church) -> list[tuple[str, int]]:
    r = client.get("/hymnals", headers=church_headers(MEMBER, church))
    return [(h["code"], h["hymn_count"]) for h in r.json()["items"]]


def test_an_admin_adds_ph1990_once_and_removes_it(client, church):
    assert _sources(client, church)["PH1990"] == {"code": "PH1990", "label": "The Presbyterian Hymnal (1990)",
                                                  "hymn_count": 605, "has_scripture_refs": False, "present": False}
    r = client.post("/hymnals", headers=church_headers(OWNER, church), json={"code": "PH1990"})
    assert (r.status_code, r.json()) == (200, {"code": "PH1990", "label": "The Presbyterian Hymnal (1990)",
                                               "inserted": 605, "updated": 0})
    r = client.post("/hymnals", headers=church_headers(OWNER, church), json={"code": "PH1990"})
    assert (r.status_code, r.json()["inserted"]) == (200, 0)
    assert _sources(client, church)["PH1990"]["present"] is True
    assert _codes(client, church) == [("GG2013", 2), ("PH1990", 605)]
    r = client.delete("/hymnals/PH1990", headers=church_headers(OWNER, church))
    assert (r.status_code, r.json()) == (200, {"deleted": True, "hymns_deleted": 605})
    assert _codes(client, church) == [("GG2013", 2)]


def test_a_member_may_not_list_add_or_remove_hymnals(client, church):
    _seed(church, "PH1990", 1)
    for method, path, body in (("GET", "/hymnal-sources", None), ("POST", "/hymnals", {"code": "PH1990"}),
                               ("DELETE", "/hymnals/PH1990", None)):
        r = client.request(method, path, headers=church_headers(MEMBER, church), json=body)
        assert (r.status_code, _error(r)) == (403, ADMINS_ONLY), f"{method} {path}"
    assert _codes(client, church) == [("GG2013", 2), ("PH1990", 1)]


def test_the_errors_of_adding_and_removing(client, church):
    owner = church_headers(OWNER, church)
    r = client.post("/hymnals", headers=owner, json={"code": "XX2000"})
    assert (r.status_code, r.json()["error"]["fields"]) == (422, {"code": "That hymnal isn't available to add."})
    r = client.post("/hymnals", headers=owner, json={"code": "X" * 21})
    assert (r.status_code, r.json()["error"]["fields"]) == (422, {"code": "Too long (max 20 characters)."})
    r = client.post("/hymnals", headers=owner, json={"code": "PH1990", "church_id": str(church)})
    assert (r.status_code, r.json()["error"]["code"]) == (422, "invalid_request")
    r = client.delete("/hymnals/G", headers=owner)
    assert (r.status_code, r.json()["error"]["code"]) == (422, "invalid_request")
    r = client.delete("/hymnals/XX2000", headers=owner)
    assert (r.status_code, _error(r)) == (404, {"code": "not_found", "message": "Your church doesn't have that hymnal."})
    r = client.delete("/hymnals/GG2013", headers=owner)
    assert (r.status_code, _error(r)) == (409, {"code": "conflict", "message": "You can't remove your only hymnal."})
    _seed(church, "PH1990", 1)
    r = client.delete("/hymnals/GG2013", headers=owner)
    assert (r.status_code, _error(r)["message"]) == (
        409, "GG2013 is your default hymnal. Choose a different default in Church profile first.")
    assert _codes(client, church) == [("GG2013", 2), ("PH1990", 1)]


def test_hymnal_routes_are_isolated_between_churches(client, isolation_world):
    world = isolation_world
    _seed(world.church_a)
    _seed(world.church_a, "PH1990", 1)
    _seed(world.church_b)
    _seed(world.church_b, "PH1990", 3)
    assert_church_isolated(client, "GET", "/hymnal-sources", world=world)
    assert_church_isolated(client, "POST", "/hymnals", world=world, json={"code": "PH1990"})
    assert_church_isolated(client, "DELETE", "/hymnals/PH1990", world=world)
    r = client.get("/hymnals", headers=church_headers(world.b, world.church_b))
    assert [(h["code"], h["hymn_count"]) for h in r.json()["items"]] == [("GG2013", 2), ("PH1990", 3)]
    r = client.get("/hymnals", headers=church_headers(world.a, world.church_a))
    assert [h["code"] for h in r.json()["items"]] == ["GG2013"]
