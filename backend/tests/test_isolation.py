"""Cross-church isolation for every church-scoped route (F §1.2 rule 5).

Each church-scoped route gets one test here (or in its own slice's test file)
through tests.api_helpers.assert_church_isolated. The routes on main today
(GET /church, GET /rubric, PATCH /rubric) name no resource id, so only the 403
half and the control apply; routes with ids pass resource_path_b.
"""
import pytest

from service_rubric import default_rubric
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    assert_church_isolated,
    church_headers,
    isolation_world,
    make_api_client,
)


@pytest.fixture
def client(tmp_db):
    return make_api_client()


def test_get_church_is_isolated(client, isolation_world):
    assert_church_isolated(client, "GET", "/church", world=isolation_world)


def test_get_rubric_is_isolated(client, isolation_world):
    assert_church_isolated(client, "GET", "/rubric", world=isolation_world)


def test_patch_rubric_is_isolated(client, isolation_world):
    assert_church_isolated(client, "PATCH", "/rubric", world=isolation_world,
                           json={"prefer_familiar": False})
    # The denied PATCHes changed nothing in church B; the control changed church A.
    b = client.get("/rubric", headers=church_headers(isolation_world.b, isolation_world.church_b))
    assert b.json() == {"rubric": default_rubric(), "customized": []}
    a = client.get("/rubric", headers=church_headers(isolation_world.a, isolation_world.church_a))
    assert a.json()["customized"] == ["prefer_familiar"]
