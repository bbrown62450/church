"""GET and PUT /church/liturgy-prompts over HTTP (6a spec, API rows; slice
6a-3a): every member reads the prompts, owners and admins replace them; the
cleaning is generation's own (`clean_prompt_overrides`), a bad section
template is a 422 naming it, and the routes are church-isolated. Ports
`streamlit_tests/test_settings_prompts_translation.py`'s prompt assertions
(F §5.1)."""
import pytest

import liturgy_prompts
from repos import churches
from repos.memberships import add_membership
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    assert_church_isolated,
    church_headers,
    isolation_world,
    make_api_client,
)

OWNER = "owner@example.com"
ADMIN = "admin@example.com"
MEMBER = "member@example.com"
PATH = "/church/liturgy-prompts"
DEFAULTS = liturgy_prompts.default_prompts()


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def church(make_user, make_church):
    cid = make_church(name="Grace", owner_user_id=make_user(email=OWNER))
    add_membership(make_user(email=ADMIN), cid, "admin")
    add_membership(make_user(email=MEMBER), cid, "member")
    return cid


def _error(r) -> dict:
    error = dict(r.json()["error"])
    error.pop("request_id")
    return error


def _overrides(body) -> dict:
    return {f["key"]: f["override"] for f in body["fields"] if f["customized"]}


def test_a_member_reads_every_prompt_and_may_not_change_them(client, church):
    r = client.get(PATH, headers=church_headers(MEMBER, church))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["can_edit"] is False
    assert body["placeholder_help"] == liturgy_prompts.PLACEHOLDER_HELP
    assert body["fields"][0] == {"key": "system", "label": "Overall voice", "default": DEFAULTS["system"],
                                 "override": None, "customized": False}
    assert [f["key"] for f in body["fields"]] == liturgy_prompts.PROMPT_KEYS
    assert client.get(PATH, headers=church_headers(ADMIN, church)).json()["can_edit"] is True
    for payload in ({"prompts": {"benediction": "Go in peace."}}, {"prompts": {}}):
        r = client.put(PATH, json=payload, headers=church_headers(MEMBER, church))
        assert (r.status_code, _error(r)) == (403, {"code": "forbidden", "message": "Only church admins can do this."})
    assert churches.get_church_prompts(church) == {}


def test_an_admin_saves_only_what_differs_from_the_defaults_and_resets_all(client, church):
    h = church_headers(ADMIN, church)
    r = client.put(PATH, json={"prompts": {
        "system": DEFAULTS["system"],
        "benediction": "  Go in peace.\r\nServe the Lord.\r\n",
        "offertory_prayer": "\r\n " + DEFAULTS["offertory_prayer"] + " \r\n",
        "assurance": "   ",
    }}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["can_edit"] is True
    assert _overrides(r.json()) == {"benediction": "Go in peace.\nServe the Lord."}
    assert client.get(PATH, headers=church_headers(MEMBER, church)).json()["fields"] == r.json()["fields"]
    assert churches.get_church_prompts(church) == {"benediction": "Go in peace.\nServe the Lord."}

    r = client.put(PATH, json={"prompts": {}}, headers=church_headers(OWNER, church))
    assert r.status_code == 200
    assert _overrides(r.json()) == {}
    assert churches.get_church_prompts(church) == {}


def test_a_bad_template_is_a_422_naming_its_prompt_and_nothing_is_saved(client, church):
    h = church_headers(OWNER, church)
    r = client.put(PATH, json={"prompts": {"system": "Changed.", "benediction": "Go in peace {"}}, headers=h)
    assert r.status_code == 422
    assert _error(r) == {
        "code": "prompt_invalid",
        "message": "Benediction prompt: It has a { or } without a partner. Use {{ or }} to print a brace.",
        "fields": {"prompts.benediction": "Benediction prompt: It has a { or } without a partner. "
                                          "Use {{ or }} to print a brace."},
    }
    assert churches.get_church_prompts(church) == {}


@pytest.mark.parametrize("payload, fields", [
    ({"prompts": {"sermon": "Preach."}}, {"prompts.sermon.[key]": "Not a valid value."}),
    ({"prompts": {"benediction": "x" * 8001}}, {"prompts.benediction": "Too long (max 8000 characters)."}),
    ({"prompts": {"benediction": None}}, {"prompts.benediction": "Not a valid value."}),
    ({"prompts": {}, "church_id": "elsewhere"}, {"church_id": "Not a valid value."}),
    ({}, {"prompts": "Required."}),
])
def test_an_unknown_key_a_long_prompt_or_an_extra_field_is_invalid_request(client, church, payload, fields):
    r = client.put(PATH, json=payload, headers=church_headers(OWNER, church))
    assert r.status_code == 422
    assert _error(r) == {"code": "invalid_request", "message": "The request was not valid.", "fields": fields}


def test_the_prompt_routes_are_isolated_between_churches(client, isolation_world):
    world = isolation_world
    assert_church_isolated(client, "GET", PATH, world=world)
    assert_church_isolated(client, "PUT", PATH, world=world, json={"prompts": {"benediction": "Go."}})
    assert churches.get_church_prompts(world.church_b) == {}
    assert churches.get_church_prompts(world.church_a) == {"benediction": "Go."}
