"""GET /hymnals and GET /church's hymnal fields (slice 3 spec, API row 1 and
row 5, Models `HymnalOut`/`HymnalListOut`, Backend 3.1-3.2; Testing
`test_api_hymnals.py`; AC1, AC2, AC8)."""
import pytest

from db import session_scope
from db.models import Hymn
from repos import churches
from repos.memberships import add_membership
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    assert_church_isolated,
    church_headers,
    isolation_world,
    make_api_client,
)

EMAIL = "pastor@example.com"


@pytest.fixture
def client(tmp_db):
    return make_api_client()


def _hymns(church_id, hymnal, count, *, refs_every=0):
    with session_scope() as s:
        for n in range(1, count + 1):
            refs = "John 3:16" if refs_every and n % refs_every == 0 else None
            s.add(Hymn(church_id=church_id, hymnal=hymnal, title=f"{hymnal} {n}", number=n,
                       scripture_refs=refs))


def _set_default(church_id, value):
    church = churches.get_church(church_id)
    churches.update_church(church_id, settings={**(church["settings"] or {}), "default_hymnal": value})


def _get(client, church_id, path="/hymnals", email=EMAIL):
    r = client.get(path, headers=church_headers(email, church_id))
    assert r.status_code == 200, r.text
    return r.json()


def _church(make_user, make_church):
    return make_church(name="Grace", owner_user_id=make_user(email=EMAIL))


def test_counts_and_scripture_ref_counts_ordered_by_code(client, make_user, make_church):
    cid = _church(make_user, make_church)
    _hymns(cid, "PH1990", 3)
    _hymns(cid, "GG2013", 4, refs_every=2)
    assert _get(client, cid) == {
        "items": [{"code": "GG2013", "hymn_count": 4, "scripture_ref_count": 2},
                  {"code": "PH1990", "hymn_count": 3, "scripture_ref_count": 0}],
        "default_hymnal": None,
        "effective_hymnal": "GG2013",
    }


def test_a_stored_default_the_church_has_is_effective(client, make_user, make_church):
    cid = _church(make_user, make_church)
    _hymns(cid, "GG2013", 1)
    _hymns(cid, "PH1990", 1)
    _set_default(cid, "PH1990")
    body = _get(client, cid)
    assert (body["default_hymnal"], body["effective_hymnal"]) == ("PH1990", "PH1990")


def test_a_stored_default_the_church_lacks_falls_back_alphabetically(client, make_user, make_church):
    cid = _church(make_user, make_church)
    _hymns(cid, "PH1990", 1)
    _hymns(cid, "GG2013", 1)
    _set_default(cid, "UMH")
    body = _get(client, cid)
    assert (body["default_hymnal"], body["effective_hymnal"]) == ("UMH", "GG2013")


def test_a_stored_default_that_is_not_a_string_or_is_blank_is_unset(client, make_user, make_church):
    cid = _church(make_user, make_church)
    _hymns(cid, "PH1990", 1)
    for value in (7, "   ", "", None, ["PH1990"]):
        _set_default(cid, value)
        body = _get(client, cid)
        assert (body["default_hymnal"], body["effective_hymnal"]) == (None, "PH1990"), value


def test_a_church_with_no_hymns_has_no_hymnal(client, make_user, make_church):
    cid = _church(make_user, make_church)
    _set_default(cid, "GG2013")
    assert _get(client, cid) == {"items": [], "default_hymnal": "GG2013", "effective_hymnal": None}


def test_get_church_returns_the_same_two_values(client, make_user, make_church):
    cid = _church(make_user, make_church)
    for setup in (lambda: None, lambda: _hymns(cid, "PH1990", 2), lambda: _hymns(cid, "GG2013", 2),
                  lambda: _set_default(cid, "PH1990"), lambda: _set_default(cid, "UMH")):
        setup()
        hymnals, profile = _get(client, cid), _get(client, cid, "/church")
        assert (profile["default_hymnal"], profile["effective_hymnal"]) == (
            hymnals["default_hymnal"], hymnals["effective_hymnal"])


def test_church_isolation_and_every_role(client, isolation_world, make_user):
    world = isolation_world
    _hymns(world.church_a, "GG2013", 2)
    _hymns(world.church_b, "ZZB", 2)
    assert_church_isolated(client, "GET", "/hymnals", world=world)
    assert [i["code"] for i in _get(client, world.church_a, email=world.a)["items"]] == ["GG2013"]
    for role in ("admin", "member"):
        email = f"{role}@example.com"
        add_membership(make_user(email=email), world.church_a, role)
        assert _get(client, world.church_a, email=email)["effective_hymnal"] == "GG2013"
