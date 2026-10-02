"""/services (slice 5a spec, API; Testing `test_api_services.py`; acceptance
criteria 6-10; F §1.6 church-scope amendment; owner answers 4 and 6, 2026-10-01)."""
import uuid

import pytest
from sqlalchemy import func, select

from db import session_scope
from db.models import Hymn, HymnUsage, Service
from repos.memberships import add_membership
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    assert_church_isolated,
    church_headers,
    isolation_world,
    make_api_client,
)

EMAIL = "pastor@example.com"
GONE = "That service is no longer in the archive."
HYMN_GONE = "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step."
CONFLICT = "This service was changed by someone else. Reload it to see their changes."
SERVICE = {
    "service_date_iso": "2026-10-04",
    "occasion": "World Communion Sunday",
    "scriptures": ["Isaiah 5:1-7", "Philippians 3:4b-14"],
    "hymns": {"opening": {"hymn_id": None, "title": "Old Favorite", "number": 12, "hymnal": "PH1990"},
              "response": None, "closing": None},
    "hymnal": None,
    "liturgy": {"call_to_worship": "Come.", "benediction": "Go in peace."},
    "sermon_title": "Living Water",
    "selected_ot_ref": "",
    "selected_nt_ref": "",
    "include_communion": True,
    "custom_elements": [{"label": "Anthem", "text": "Choir", "insert_after": "sermon"}],
}


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def pastor(make_user):
    return make_user(email=EMAIL)


@pytest.fixture
def church(pastor, make_church):
    return make_church(name="Grace", owner_user_id=pastor)


def call(client, method, path, church_id, *, email=EMAIL, json=None, **headers):
    return client.request(method, path, json=json, headers={**church_headers(email, church_id), **headers})


def create(client, church_id, body=SERVICE, **headers):
    r = call(client, "POST", "/services", church_id, json=body, **headers)
    assert r.status_code == 201, r.text
    return r.json()


def error(r):
    body = r.json()["error"]
    return body["code"], body["message"]


def service_count():
    with session_scope() as s:
        return s.execute(select(func.count()).select_from(Service)).scalar_one()


def test_create_open_list_replace_delete(client, church, pastor):
    made = create(client, church)
    assert made["hymns"] == {
        "opening": {"hymn_id": None, "title": "Old Favorite", "number": 12, "hymnal": "PH1990", "in_hymnal": False},
        "response": None, "closing": None}
    assert (made["service_date_iso"], made["service_date"]) == ("2026-10-04", "October 04, 2026")
    assert made["liturgy"] == {"call_to_worship": "Come.", "benediction": "Go in peace."}
    assert made["include_communion"] is True
    assert made["custom_elements"] == SERVICE["custom_elements"]
    # The author's name as the sign-in token last gave it (tests.jwt_helpers), else the email.
    assert made["created_by"] == {"id": str(pastor), "name": "Pat Tor"} and made["saved_at"].endswith("+00:00")
    sid = made["id"]
    opened = call(client, "GET", f"/services/{sid}", church)
    assert (opened.status_code, opened.json()) == (200, made)
    listed = call(client, "GET", "/services", church).json()
    assert (listed["total"], listed["limit"], listed["offset"]) == (1, 20, 0)
    assert listed["items"] == [{key: made[key] for key in (
        "id", "service_date_iso", "service_date", "occasion", "sermon_title", "saved_at", "created_by")}]
    r = call(client, "PUT", f"/services/{sid}", church, json={**SERVICE, "occasion": "Changed"},
             **{"If-Match": made["saved_at"]})
    assert r.status_code == 200, r.text
    assert r.json()["occasion"] == "Changed" and r.json()["saved_at"] > made["saved_at"]
    r = call(client, "DELETE", f"/services/{sid}", church)
    assert (r.status_code, r.json()) == (200, {"deleted": True})
    assert call(client, "GET", f"/services/{sid}", church).status_code == 404


def test_hymn_use_follows_save_and_delete(client, church):
    first = create(client, church)
    create(client, church, {**SERVICE, "hymns": {"closing": {"title": "Early Hymn", "number": 5}}})

    def used():
        with session_scope() as s:
            return sorted(s.execute(select(HymnUsage.hymn_title).where(
                HymnUsage.church_id == church, HymnUsage.date_iso == "2026-10-04")).scalars().all())

    assert used() == ["Early Hymn", "Old Favorite"]
    call(client, "DELETE", f"/services/{first['id']}", church)
    assert used() == ["Early Hymn"]


@pytest.mark.parametrize("role", ["member", "admin"])
def test_any_member_may_save_replace_and_delete(client, church, make_user, role):
    other = f"{role}@example.com"
    add_membership(make_user(email=other), church, role)
    made = create(client, church)
    r = call(client, "POST", "/services", church, email=other, json=SERVICE)
    assert r.status_code == 201, r.text
    r = call(client, "PUT", f"/services/{made['id']}", church, email=other, json=SERVICE,
             **{"If-Match": made["saved_at"]})
    assert r.status_code == 200, r.text
    assert r.json()["created_by"] == made["created_by"]          # the author stays the first saver
    assert call(client, "DELETE", f"/services/{made['id']}", church, email=other).status_code == 200


def test_every_route_is_church_isolated(client, isolation_world):
    world = isolation_world
    r = call(client, "POST", "/services", world.church_b, email=world.b, json=SERVICE)
    theirs_id = r.json()["id"]
    theirs_saved = r.json()["saved_at"]
    mine = call(client, "POST", "/services", world.church_a, email=world.a, json=SERVICE).json()
    assert_church_isolated(client, "GET", "/services", world=world)
    assert_church_isolated(client, "GET", f"/services/{mine['id']}", world=world,
                           resource_path_b=f"/services/{theirs_id}")
    assert_church_isolated(client, "POST", "/services", world=world, json=SERVICE)
    # PUT: church B's id is a 404 even with its real saved_at; a@'s own service then saves.
    r = client.put(f"/services/{theirs_id}", json=SERVICE,
                   headers={**church_headers(world.a, world.church_a), "If-Match": theirs_saved})
    assert (r.status_code, error(r)) == (404, ("not_found", GONE))
    assert_church_isolated(client, "DELETE", f"/services/{mine['id']}", world=world,
                           resource_path_b=f"/services/{theirs_id}")
    assert call(client, "GET", f"/services/{theirs_id}", world.church_b, email=world.b).status_code == 200


def test_another_church_s_hymn_id_is_a_404_naming_the_slot_and_writes_nothing(client, isolation_world):
    world = isolation_world
    with session_scope() as s:
        hymn = Hymn(church_id=world.church_b, hymnal="GG2013", title="Their Hymn", number=1)
        s.add(hymn)
        s.flush()
        theirs = str(hymn.id)
    for hymn_id in (theirs, str(uuid.uuid4())):
        body = {**SERVICE, "hymns": {"response": {"hymn_id": hymn_id, "title": "x", "number": 1, "hymnal": None}}}
        r = call(client, "POST", "/services", world.church_a, email=world.a, json=body)
        assert r.status_code == 404, r.text
        assert r.json()["error"]["details"] == {"field": "hymns.response.hymn_id"}
        assert error(r) == ("not_found", HYMN_GONE)
    assert service_count() == 0


def test_put_check_order_and_messages(client, church):
    made = create(client, church)
    path = f"/services/{made['id']}"
    r = call(client, "PUT", f"/services/{uuid.uuid4()}", church, json=SERVICE)
    assert (r.status_code, error(r)) == (404, ("not_found", GONE))
    assert "details" not in r.json()["error"]                       # not a hymn 404: the client POSTs instead
    r = call(client, "PUT", path, church, json=SERVICE)
    assert (r.status_code, error(r)) == (422, ("invalid_request", "If-Match is required."))
    r = call(client, "PUT", path, church, json=SERVICE, **{"If-Match": "yesterday"})
    assert (r.status_code, error(r)) == (422, ("invalid_request", "If-Match must be the service's saved_at timestamp."))
    r = call(client, "PUT", path, church, json=SERVICE, **{"If-Match": "2026-01-01T00:00:00+00:00"})
    assert (r.status_code, error(r)) == (409, ("conflict", CONFLICT))
    assert r.json()["error"]["details"] == {"current_saved_at": made["saved_at"]}
    ok = call(client, "PUT", path, church, json=SERVICE, **{"If-Match": made["saved_at"]})
    assert ok.status_code == 200
    stale = call(client, "PUT", path, church, json=SERVICE, **{"If-Match": made["saved_at"]})
    assert (stale.status_code, stale.json()["error"]["details"]) == (409, {"current_saved_at": ok.json()["saved_at"]})


@pytest.mark.parametrize("method, path", [("GET", "/services/not-a-uuid"), ("PUT", "/services/not-a-uuid"),
                                          ("DELETE", "/services/not-a-uuid"), ("GET", "/services?limit=0"),
                                          ("GET", "/services?limit=201"), ("GET", "/services?offset=-1")])
def test_malformed_ids_and_paging_are_422(client, church, method, path):
    r = call(client, method, path, church, json=SERVICE if method == "PUT" else None)
    assert (r.status_code, r.json()["error"]["code"]) == (422, "invalid_request")


@pytest.mark.parametrize("change, field", [
    ({"extra": 1}, "extra"),
    ({"custom_elements": [{"label": "A", "text": "", "insert_after": "bogus"}]}, "custom_elements.0.insert_after"),
    ({"service_date_iso": "2026-10-04T00:00:00"}, "service_date_iso"),
    ({"custom_elements": [{"label": " ", "text": "", "insert_after": "end"}]}, "custom_elements.0.label"),
])
def test_a_bad_body_is_a_422_naming_the_field(client, church, change, field):
    r = call(client, "POST", "/services", church, json={**SERVICE, **change})
    assert r.status_code == 422, r.text
    assert field in r.json()["error"]["fields"]
    assert service_count() == 0


def test_deleting_twice_is_a_404(client, church):
    made = create(client, church)
    assert call(client, "DELETE", f"/services/{made['id']}", church).status_code == 200
    r = call(client, "DELETE", f"/services/{made['id']}", church)
    assert (r.status_code, error(r)) == (404, ("not_found", GONE))


def test_a_stored_unknown_place_comes_back_as_end_and_survives_a_put(client, church):
    made = create(client, church)
    with session_scope() as s:
        s.get(Service, uuid.UUID(made["id"])).custom_elements = [{"label": "Old", "text": "x", "insert_after": "bogus"}]
    opened = call(client, "GET", f"/services/{made['id']}", church).json()
    assert opened["custom_elements"] == [{"label": "Old", "text": "x", "insert_after": "end"}]
    r = call(client, "PUT", f"/services/{made['id']}", church,
             json={**SERVICE, "custom_elements": opened["custom_elements"]}, **{"If-Match": opened["saved_at"]})
    assert r.status_code == 200 and r.json()["custom_elements"] == opened["custom_elements"]


# --- Idempotency-Key (F §1.6 and its church-scope amendment) ------------------------------

KEY = "6f1c2a52-3a8e-4c3e-9d57-2f0b1f6f1a11"


def test_a_replayed_key_returns_the_first_answer_and_saves_once(client, church):
    first = create(client, church, **{"Idempotency-Key": KEY})
    again = call(client, "POST", "/services", church, json=SERVICE, **{"Idempotency-Key": KEY})
    assert (again.status_code, again.json()) == (201, first)
    assert again.headers["idempotent-replayed"] == "true"
    assert service_count() == 1
    r = call(client, "POST", "/services", church, json={**SERVICE, "occasion": "Other"}, **{"Idempotency-Key": KEY})
    assert (r.status_code, error(r)) == (422, ("idempotency_mismatch",
                                               "This request was already sent with different details."))


def test_a_corrected_retry_needs_a_new_key(client, church):
    gone = {**SERVICE, "hymns": {"opening": {"hymn_id": str(uuid.uuid4()), "title": "x"}}}
    assert call(client, "POST", "/services", church, json=gone, **{"Idempotency-Key": KEY}).status_code == 404
    r = call(client, "POST", "/services", church, json=SERVICE, **{"Idempotency-Key": KEY})
    assert error(r)[0] == "idempotency_mismatch"           # the stored 404 holds the key
    create(client, church, **{"Idempotency-Key": str(uuid.uuid4())})
    assert service_count() == 1


def test_the_same_key_in_two_churches_saves_in_each(client, church, pastor, make_church):
    # The key store is scoped by church (F §1.6 amendment 2026-09-28): the same
    # member, key and body in another church saves there instead of replaying
    # the first church's answer.
    second = make_church(name="Hope", owner_user_id=pastor)
    first = create(client, church, **{"Idempotency-Key": KEY})
    other = call(client, "POST", "/services", second, json=SERVICE, **{"Idempotency-Key": KEY})
    assert other.status_code == 201, other.text
    assert "idempotent-replayed" not in other.headers
    assert other.json()["id"] != first["id"]
    assert call(client, "GET", "/services", second).json()["total"] == 1
    assert call(client, "GET", f"/services/{first['id']}", second).status_code == 404
