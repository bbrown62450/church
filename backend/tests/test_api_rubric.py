import pytest
from fastapi.testclient import TestClient

from api.deps import get_verifier
from api.main import create_app
from api.security import TokenVerifier
from repos.memberships import add_membership
from service_rubric import default_rubric
from tests.jwt_helpers import ISSUER, SIGNING_KEY, make_token


@pytest.fixture
def client(tmp_db):
    app = create_app()
    app.dependency_overrides[get_verifier] = lambda: TokenVerifier(
        lambda _token: SIGNING_KEY.public_key(), issuer=ISSUER
    )
    return TestClient(app)


def _headers(email, church_id):
    return {"Authorization": f"Bearer {make_token(email=email)}", "X-Church-Id": str(church_id)}


@pytest.fixture
def church(make_user, make_church):
    """A church owned by owner@x.org with member@x.org as a plain member."""
    owner = make_user(email="owner@x.org")
    cid = make_church(name="Grace", owner_user_id=owner)
    add_membership(make_user(email="member@x.org"), cid, "member")
    return cid


def test_member_reads_the_default_rubric(client, church):
    r = client.get("/rubric", headers=_headers("member@x.org", church))
    assert r.status_code == 200
    assert r.json() == {"rubric": default_rubric(), "customized": []}


def test_reading_requires_membership(client, church, make_user):
    make_user(email="stranger@x.org")
    r = client.get("/rubric", headers=_headers("stranger@x.org", church))
    assert r.status_code == 403


def test_member_cannot_change_the_rubric(client, church):
    r = client.patch("/rubric", json={"prefer_familiar": False}, headers=_headers("member@x.org", church))
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "forbidden"


def test_owner_changes_then_resets_an_item(client, church):
    h = _headers("owner@x.org", church)
    r = client.patch("/rubric", json={"hymns": {"closing": ["Joyful and sending."]}}, headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["rubric"]["hymns"]["closing"] == ["Joyful and sending."]
    assert body["customized"] == ["hymns.closing"]
    assert client.get("/rubric", headers=h).json() == body

    r = client.patch("/rubric", json={"hymns": {"closing": None}}, headers=h)
    assert r.json() == {"rubric": default_rubric(), "customized": []}


def test_invalid_values_return_a_readable_422(client, church):
    r = client.patch("/rubric", json={"prefer_before_year": 1400}, headers=_headers("owner@x.org", church))
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "invalid_rubric"
    assert "between 1500" in r.json()["error"]["message"]


def test_non_object_body_is_rejected(client, church):
    r = client.patch("/rubric", json=["x"], headers=_headers("owner@x.org", church))
    assert r.status_code == 422


def test_edits_stay_in_their_church(client, church, make_church, make_user):
    other = make_church(name="Other", owner_user_id=make_user(email="other@x.org"))
    client.patch("/rubric", json={"prefer_familiar": False}, headers=_headers("owner@x.org", church))
    r = client.get("/rubric", headers=_headers("other@x.org", other))
    assert r.json() == {"rubric": default_rubric(), "customized": []}
