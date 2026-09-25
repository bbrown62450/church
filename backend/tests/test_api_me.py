import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from jwt.exceptions import PyJWKClientConnectionError
from sqlalchemy import select

from api.deps import ActiveChurch, get_verifier, require_admin
from api.errors import ApiError
from api.main import create_app
from api.security import TokenVerifier
from db import session_scope
from db.models import Church, User
from tests.jwt_helpers import ISSUER, SIGNING_KEY, make_token


def _test_verifier():
    return TokenVerifier(lambda _token: SIGNING_KEY.public_key(), issuer=ISSUER)


@pytest.fixture
def client(tmp_db):
    app = create_app()
    app.dependency_overrides[get_verifier] = _test_verifier
    return TestClient(app)


def _auth(email="pastor@example.com", **kwargs):
    return {"Authorization": f"Bearer {make_token(email=email, **kwargs)}"}


def test_me_requires_a_token(client):
    r = client.get("/me")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthenticated"


def test_me_rejects_non_bearer_scheme(client):
    assert client.get("/me", headers={"Authorization": "Basic abc"}).status_code == 401


def test_me_rejects_non_google_token(client):
    assert client.get("/me", headers=_auth(provider="email")).status_code == 401


def test_me_creates_user_from_google_identity(client):
    r = client.get("/me", headers=_auth(email="New@Example.com", google_sub="g-42", name="New Person"))
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["email"] == "new@example.com"
    assert body["user"]["name"] == "New Person"
    assert body["churches"] == []
    with session_scope() as s:
        user = s.execute(select(User).where(User.email == "new@example.com")).scalar_one()
        # google_sub comes from user-editable metadata, so the API never writes it.
        assert user.google_sub is None
        assert str(user.id) == body["user"]["id"]


def test_me_matches_existing_streamlit_user_by_email(client, make_user):
    existing = make_user(email="pastor@example.com", google_sub="google-sub-1")
    r = client.get("/me", headers=_auth(email="pastor@example.com", google_sub="google-sub-1"))
    assert r.json()["user"]["id"] == str(existing)


def test_me_lists_only_the_callers_churches(client, make_user, make_church):
    me_id = make_user(email="pastor@example.com")
    mine = make_church(name="Grace", owner_user_id=me_id)
    make_church(name="Someone Else's")
    r = client.get("/me", headers=_auth())
    assert r.json()["churches"] == [{"id": str(mine), "name": "Grace", "role": "owner"}]


def test_church_returns_the_active_church_for_a_member(client, make_user, make_church):
    me_id = make_user(email="pastor@example.com")
    cid = make_church(name="Grace", owner_user_id=me_id)
    r = client.get("/church", headers={**_auth(), "X-Church-Id": str(cid)})
    assert r.status_code == 200
    assert r.json() == {"id": str(cid), "name": "Grace", "role": "owner"}


@pytest.mark.parametrize(
    "church_header", [None, "", "not-a-uuid", str(uuid.uuid4())],
    ids=["missing", "empty", "malformed", "unknown"],
)
def test_church_rejects_missing_malformed_or_unknown_ids(client, make_user, church_header):
    make_user(email="pastor@example.com")
    headers = _auth()
    if church_header is not None:
        headers["X-Church-Id"] = church_header
    r = client.get("/church", headers=headers)
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "forbidden"


def test_church_blocks_other_churches(client, make_user, make_church):
    """Cross-church isolation: a real church id the caller doesn't belong to is refused."""
    make_user(email="pastor@example.com")
    other = make_church(name="Other Church")
    r = client.get("/church", headers={**_auth(), "X-Church-Id": str(other)})
    assert r.status_code == 403
    assert "Other Church" not in r.text


def test_church_blocks_soft_deleted_church(client, make_user, make_church):
    me_id = make_user(email="pastor@example.com")
    cid = make_church(name="Closed", owner_user_id=me_id)
    with session_scope() as s:
        s.get(Church, cid).deleted_at = datetime.now(timezone.utc)
    r = client.get("/church", headers={**_auth(), "X-Church-Id": str(cid)})
    assert r.status_code == 403


def test_church_requires_a_token(client, make_church):
    cid = make_church()
    assert client.get("/church", headers={"X-Church-Id": str(cid)}).status_code == 401


def test_key_outage_returns_503(tmp_db):
    def unreachable(_token):
        raise PyJWKClientConnectionError("jwks down")

    app = create_app()
    app.dependency_overrides[get_verifier] = lambda: TokenVerifier(unreachable, issuer=ISSUER)
    r = TestClient(app).get("/me", headers=_auth())
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "auth_unavailable"


def test_require_admin_allows_owner_and_admin_only():
    for role in ("owner", "admin"):
        church = ActiveChurch(id=uuid.uuid4(), name="Grace", role=role)
        assert require_admin(church) is church
    with pytest.raises(ApiError) as exc:
        require_admin(ActiveChurch(id=uuid.uuid4(), name="Grace", role="member"))
    assert exc.value.status == 403
