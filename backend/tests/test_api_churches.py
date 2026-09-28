"""POST /churches over HTTP (S API, Idempotency, Testing; AC6; F-AC7).

The usecase's own rules (trimming, the seed, the cap's arithmetic, the log
lines) are pinned in test_usecase_onboarding.py. These tests pin the HTTP
contract: statuses, the error body, X-Church-Id ignored, the dependency
order, and Idempotency-Key replay through run_idempotent.
"""
import uuid

import pytest
from sqlalchemy import func, select

from db import session_scope
from db.models import Church, Hymn, Membership
from repos.churches import create_church as repo_create_church
from repos.memberships import add_membership
from tests.api_helpers import auth_headers, church_headers, make_api_client

EMAIL = "pastor@example.com"
BODY = {"name": "Grace Church", "timezone": "America/Chicago"}
CAP_MESSAGE = "You've created 5 churches in the last 24 hours. Try again later."


@pytest.fixture
def client(tmp_db):
    return make_api_client()


def _count(model) -> int:
    with session_scope() as s:
        return s.execute(select(func.count()).select_from(model)).scalar_one()


def _key_headers(key: uuid.UUID, email: str = EMAIL) -> dict[str, str]:
    return {**auth_headers(email), "Idempotency-Key": str(key)}


def _my_churches(client, email: str = EMAIL) -> list[dict]:
    r = client.get("/me", headers=auth_headers(email))
    assert r.status_code == 200, r.text
    return r.json()["churches"]


def test_requires_token(client):
    r = client.post("/churches", json=BODY)
    assert r.status_code == 401
    error = r.json()["error"]
    assert (error["code"], error["message"]) == ("unauthenticated", "Please sign in.")
    assert _count(Church) == 0


def test_bad_key_without_token_is_401(client):
    """get_current_user runs before idempotency_key() (clarification 10)."""
    r = client.post("/churches", json=BODY, headers={"Idempotency-Key": "not-a-uuid"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthenticated"

    signed_in = client.post("/churches", json=BODY,
                            headers={**auth_headers(EMAIL), "Idempotency-Key": "not-a-uuid"})
    assert signed_in.status_code == 422
    error = signed_in.json()["error"]
    assert (error["code"], error["message"]) == ("invalid_request", "Idempotency-Key must be a UUID.")
    assert "fields" not in error
    assert _count(Church) == 0


def test_create_201_listed_in_me_and_usable(client, seed_catalog):
    seed_catalog(3)
    r = client.post("/churches", json={"name": "  Grace Church  ", "timezone": "America/Chicago"},
                    headers=auth_headers(EMAIL))
    assert r.status_code == 201, r.text
    body = r.json()
    assert set(body) == {"id", "name", "role"}
    assert (body["name"], body["role"]) == ("Grace Church", "owner")
    church_id = uuid.UUID(body["id"])

    assert _my_churches(client) == [body]
    usable = client.get("/church", headers=church_headers(EMAIL, church_id))
    assert usable.status_code == 200, usable.text
    assert usable.json() == body
    with session_scope() as s:
        assert s.get(Church, church_id).timezone == "America/Chicago"
        hymns = s.execute(select(func.count()).select_from(Hymn)
                          .where(Hymn.church_id == church_id)).scalar_one()
    assert hymns == 3                                   # one hymn per catalog row (AC6)
    assert (_count(Church), _count(Membership)) == (1, 1)


def test_x_church_id_is_ignored(client, make_user, make_church):
    other = make_church(name="Other Church", owner_user_id=make_user(email="other@example.com"))
    for headers in (church_headers(EMAIL, other), {**auth_headers(EMAIL), "X-Church-Id": "not-a-uuid"}):
        r = client.post("/churches", json=BODY, headers=headers)
        assert r.status_code == 201, r.text
        assert r.json()["role"] == "owner"
    mine = _my_churches(client)
    assert [(c["name"], c["role"]) for c in mine] == [("Grace Church", "owner")] * 2
    assert str(other) not in {c["id"] for c in mine}


def test_duplicate_names_and_second_church_allowed(client, make_user, make_church):
    """Names need not be unique, and a member of one church can create another."""
    member = make_user(email=EMAIL)
    old_first = make_church(name="Old First", owner_user_id=make_user(email="owner@example.com"))
    add_membership(member, old_first, "member")

    mine = client.post("/churches", json=BODY, headers=auth_headers(EMAIL))
    again = client.post("/churches", json=BODY, headers=auth_headers(EMAIL))
    theirs = client.post("/churches", json=BODY, headers=auth_headers("friend@example.com"))
    assert (mine.status_code, again.status_code, theirs.status_code) == (201, 201, 201)
    assert len({mine.json()["id"], again.json()["id"], theirs.json()["id"]}) == 3
    assert [(c["name"], c["role"]) for c in _my_churches(client)] == [
        ("Grace Church", "owner"), ("Grace Church", "owner"), ("Old First", "member")]


@pytest.mark.parametrize("body, message, field", [
    ({"name": "   ", "timezone": "America/Chicago"}, "Church name is required.", "name"),
    ({"name": "Grace Church", "timezone": " "}, "Timezone is required.", "timezone"),
    ({"name": "Grace Church", "timezone": "Mars/Olympus"}, "Unknown timezone.", "timezone"),
], ids=["name", "tz-blank", "tz-unknown"])
def test_validation_messages(client, body, message, field):
    r = client.post("/churches", json=body, headers=auth_headers(EMAIL))
    assert r.status_code == 422
    error = r.json()["error"]
    assert (error["code"], error["message"]) == ("invalid_request", message)
    assert error["fields"] == {field: message}
    assert _count(Church) == 0


def test_name_too_long(client):
    r = client.post("/churches", json={"name": "x" * 201, "timezone": "America/Chicago"},
                    headers=auth_headers(EMAIL))
    assert r.status_code == 422
    error = r.json()["error"]
    assert (error["code"], error["message"]) == ("invalid_request", "The request was not valid.")
    assert error["fields"] == {"name": "Too long (max 200 characters)."}

    zone = client.post("/churches", json={"name": "Grace Church", "timezone": "x" * 65},
                       headers=auth_headers(EMAIL))
    assert zone.status_code == 422
    assert zone.json()["error"]["fields"] == {"timezone": "Too long (max 64 characters)."}
    assert _count(Church) == 0

    at_limit = client.post("/churches", json={"name": "x" * 200, "timezone": "America/Chicago"},
                           headers=auth_headers(EMAIL))
    assert at_limit.status_code == 201, at_limit.text


def test_extra_field_rejected(client):
    r = client.post("/churches", json={**BODY, "owner_user_id": str(uuid.uuid4())},
                    headers=auth_headers(EMAIL))
    assert r.status_code == 422
    error = r.json()["error"]
    assert (error["code"], error["message"]) == ("invalid_request", "The request was not valid.")
    assert error["fields"] == {"owner_user_id": "Not a valid value."}
    assert _count(Church) == 0


def test_key_replay_one_church_same_body(client):
    """F-AC7: a replay returns the first response and creates one church."""
    key = uuid.uuid4()
    first = client.post("/churches", json=BODY, headers=_key_headers(key))
    again = client.post("/churches", json=BODY, headers=_key_headers(key))
    assert (first.status_code, again.status_code) == (201, 201)
    assert "Idempotent-Replayed" not in first.headers
    assert again.headers["Idempotent-Replayed"] == "true"
    assert again.content == first.content
    assert _count(Church) == 1
    assert _my_churches(client) == [first.json()]


def test_key_mismatch_422(client):
    key = uuid.uuid4()
    assert client.post("/churches", json=BODY, headers=_key_headers(key)).status_code == 201
    r = client.post("/churches", json={**BODY, "name": "Hope Church"}, headers=_key_headers(key))
    assert r.status_code == 422
    error = r.json()["error"]
    assert (error["code"], error["message"]) == (
        "idempotency_mismatch", "This request was already sent with different details.")
    assert "fields" not in error
    assert _count(Church) == 1


def test_blank_then_corrected_with_new_key_201(client):
    """The client's flow (S Idempotency): a 4xx is stored under its key, so the
    corrected body goes out under a new key."""
    blank = {**BODY, "name": ""}
    first_key = uuid.uuid4()
    r = client.post("/churches", json=blank, headers=_key_headers(first_key))
    assert r.status_code == 422
    assert r.json()["error"]["fields"] == {"name": "Church name is required."}
    replay = client.post("/churches", json=blank, headers=_key_headers(first_key))
    assert (replay.status_code, replay.headers.get("Idempotent-Replayed")) == (422, "true")
    stale = client.post("/churches", json=BODY, headers=_key_headers(first_key))
    assert stale.json()["error"]["code"] == "idempotency_mismatch"
    assert _count(Church) == 0

    fixed = client.post("/churches", json=BODY, headers=_key_headers(uuid.uuid4()))
    assert fixed.status_code == 201, fixed.text
    assert fixed.json()["name"] == "Grace Church"
    assert _count(Church) == 1


def test_cap_429_not_replayed(client, make_user):
    """AC6: with five churches this user created in the last 24 h, the sixth is 429.

    The five are made through repos.churches.create_church, not HTTP, so slice 2's
    church_create burst bucket (3 per minute) is never reached: slice 2 keeps
    this test green unchanged. run_idempotent never stores a RateLimited, so the
    same key runs again (429 again, not a replay).
    """
    user_id = make_user(email=EMAIL)
    for n in range(5):
        repo_create_church(name=f"Church {n}", timezone="America/Chicago", owner_user_id=user_id)
    key = uuid.uuid4()

    for _attempt in range(2):
        r = client.post("/churches", json=BODY, headers=_key_headers(key))
        assert r.status_code == 429, r.text
        error = r.json()["error"]
        assert (error["code"], error["message"]) == ("rate_limited", CAP_MESSAGE)
        assert "fields" not in error
        seconds = error["details"]["retry_after_seconds"]
        assert isinstance(seconds, int) and 1 <= seconds <= 24 * 60 * 60
        assert r.headers["Retry-After"] == str(seconds)
        assert "Idempotent-Replayed" not in r.headers
    assert _count(Church) == 5
