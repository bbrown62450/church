"""Shared helpers for API tests: signed-in headers, a test client, and the
cross-church isolation check every church-scoped route gets (F §1.2 rule 5;
S tests/api_helpers.py).

Use from a test module:

    from tests.api_helpers import assert_church_isolated, isolation_world  # noqa: F401 (fixture)

`isolation_world` is a pytest fixture: importing it into the test module is
what makes pytest find it (only the root conftest may declare pytest_plugins).
"""
import uuid
from dataclasses import dataclass
from typing import Any, Optional

import pytest
from fastapi.testclient import TestClient

from tests.jwt_helpers import ISSUER, SIGNING_KEY, make_token

# require_church's 403 body without its request_id (F §1.2, S "no_church_access").
NO_CHURCH_ACCESS = {
    "code": "forbidden",
    "message": "You don't have access to this church.",
    "details": {"reason": "no_church_access"},
}


def auth_headers(email: str) -> dict[str, str]:
    """A signed-in Google user with this email (token from tests.jwt_helpers)."""
    return {"Authorization": f"Bearer {make_token(email=email)}"}


def church_headers(email: str, church_id: uuid.UUID) -> dict[str, str]:
    """auth_headers plus X-Church-Id: the caller acting in that church."""
    return {**auth_headers(email), "X-Church-Id": str(church_id)}


def make_api_client() -> TestClient:
    """A TestClient on a fresh app whose token verifier trusts tests.jwt_helpers'
    signing key. Built without `with`, so the lifespan does not run. Call it
    after `tmp_db` (the routes use the engine that fixture binds)."""
    from api.deps import get_verifier
    from api.main import create_app
    from api.security import TokenVerifier

    app = create_app()
    app.dependency_overrides[get_verifier] = lambda: TokenVerifier(
        lambda _token: SIGNING_KEY.public_key(), issuer=ISSUER
    )
    return TestClient(app)


@dataclass(frozen=True)
class IsolationWorld:
    """Church A (a@ owns it), church B (b@ owns it) and an outsider who
    belongs to neither."""
    church_a: uuid.UUID
    church_b: uuid.UUID
    a: str = "a@example.com"
    b: str = "b@example.com"
    outsider: str = "o@example.com"


@pytest.fixture
def isolation_world(tmp_db, make_user, make_church) -> IsolationWorld:
    a, b, outsider = "a@example.com", "b@example.com", "o@example.com"
    church_a = make_church(name="Church A", owner_user_id=make_user(email=a))
    church_b = make_church(name="Church B", owner_user_id=make_user(email=b))
    make_user(email=outsider)                     # signed up, member of neither church
    return IsolationWorld(church_a=church_a, church_b=church_b, a=a, b=b, outsider=outsider)


def _error_without_request_id(response) -> dict:
    error = dict(response.json()["error"])
    error.pop("request_id")
    return error


def assert_church_isolated(
    client: TestClient,
    method: str,
    path: str,
    *,
    world: IsolationWorld,
    json: Any = None,
    resource_path_b: Optional[str] = None,
) -> None:
    """Nobody reaches church B through `method path` without belonging to it.

    1. The outsider and a@, each sending X-Church-Id = B, get 403 `forbidden`
       "You don't have access to this church." with details.reason
       `no_church_access`.
    2. When `resource_path_b` is given (a path naming one of church B's
       resources), a@ acting in church A gets 404 `not_found` there: an id
       from another church is never a 403 (F §1.2 rule 2).
    3. Control: a@ acting in church A on `path` gets neither 401, 403 nor 404,
       so the denials above come from the church check and not from a broken
       request. It runs last, so a route that changes church A (PATCH, DELETE)
       does so only after the checks.
    """
    for email in (world.outsider, world.a):
        r = client.request(method, path, headers=church_headers(email, world.church_b), json=json)
        assert r.status_code == 403, f"{method} {path} as {email} in church B: {r.status_code} {r.text}"
        assert _error_without_request_id(r) == NO_CHURCH_ACCESS

    if resource_path_b is not None:
        r = client.request(method, resource_path_b,
                           headers=church_headers(world.a, world.church_a), json=json)
        assert r.status_code == 404, (
            f"{method} {resource_path_b} as {world.a} in church A: {r.status_code} {r.text}"
        )
        assert r.json()["error"]["code"] == "not_found"

    r = client.request(method, path, headers=church_headers(world.a, world.church_a), json=json)
    assert r.status_code not in (401, 403, 404), (
        f"control: {method} {path} as {world.a} in church A: {r.status_code} {r.text}"
    )
