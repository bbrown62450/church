"""GET and PUT /church/bulletin-settings (printed bulletin spec, PR 2a; PR 2
planning answers 1 and 2): any member reads them, admins and owners change
them, stored whole in churches.settings["bulletin"] next to the church's
other settings."""
import pytest

from db import session_scope
from db.models import Church
from repos.memberships import add_membership
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    assert_church_isolated,
    church_headers,
    isolation_world,
    make_api_client,
)
from tests.test_bulletin_settings import DEFAULT_JSON

PATH = "/church/bulletin-settings"
BODY = {
    "address_lines": ["100 Example Street", "Springfield, ST 00000"], "phone": "(555) 010-0100",
    "email": "office@example.com", "website": "example.com", "facebook": "Example Church",
    "service_time": "10:30 a.m.", "worship_leader": "Rev. Alex Example", "liturgist": "Sam Sample",
    "organist": "Jordan Doe", "stand_note": "Congregation stands if able", "gloria_patri_words": "Glory be.",
    "starred": ["first_hymn", "doxology"], "leaders": {"sermon": "worship_leader", "postlude": "organist"},
}


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def church(make_user, make_church):
    """Owned by owner@example.com, with admin@ and member@ in it."""
    cid = make_church(name="Example Church", owner_user_id=make_user(email="owner@example.com"))
    add_membership(make_user(email="admin@example.com"), cid, "admin")
    add_membership(make_user(email="member@example.com"), cid, "member")
    return cid


def get(client, church, email="member@example.com"):
    return client.get(PATH, headers=church_headers(email, church))


def put(client, church, body, email="admin@example.com"):
    return client.put(PATH, json=body, headers=church_headers(email, church))


def stored(church) -> dict:
    with session_scope() as s:
        return s.get(Church, church).settings


def test_a_member_reads_the_defaults_before_anything_is_saved(client, church):
    r = get(client, church)
    assert r.status_code == 200, r.text
    assert r.json() == DEFAULT_JSON


def test_an_admin_saves_them_whole_and_the_other_settings_stay(client, church):
    with session_scope() as s:
        s.get(Church, church).settings = {"bible_translation": "kjv", "default_hymnal": "GG2013"}
    r = put(client, church, BODY)
    assert r.status_code == 200, r.text
    assert r.json() == BODY
    assert get(client, church).json() == BODY
    assert stored(church) == {"bible_translation": "kjv", "default_hymnal": "GG2013", "bulletin": BODY}
    smaller = {**BODY, "starred": [], "leaders": {}, "address_lines": []}
    assert put(client, church, smaller, email="owner@example.com").json() == smaller       # owners too
    assert stored(church)["bulletin"] == smaller and stored(church)["bible_translation"] == "kjv"


def test_what_is_saved_is_trimmed_and_in_order(client, church):
    r = put(client, church, {**BODY, "phone": "  (555) 010-0100 ", "address_lines": [" 100 Example Street ", " "],
                             "stand_note": "*Please stand if able", "starred": ["doxology", "first_hymn", "doxology"],
                             "gloria_patri_words": "Glory\x00 be.\r\nAmen.",
                             "leaders": {"postlude": "organist", "sermon": "worship_leader"}})
    assert r.status_code == 200, r.text
    assert r.json() == {**BODY, "address_lines": ["100 Example Street"], "stand_note": "Please stand if able",
                        "gloria_patri_words": "Glory be.\nAmen."}
    assert list(stored(church)["bulletin"]["leaders"]) == ["sermon", "postlude"]


def test_a_member_cannot_change_them(client, church):
    r = put(client, church, BODY, email="member@example.com")
    assert r.status_code == 403, r.text
    assert r.json()["error"]["code"] == "forbidden"
    assert r.json()["error"]["message"] == "Only church admins can do this."
    assert "bulletin" not in stored(church)


def test_a_stored_value_of_the_wrong_shape_reads_as_the_defaults(client, church):
    with session_scope() as s:
        s.get(Church, church).settings = {"bulletin": {"phone": 7, "starred": "x", "leaders": {"sermon": "pastor"},
                                                       "organist": "Jordan Doe"}}
    assert get(client, church).json() == {**DEFAULT_JSON, "organist": "Jordan Doe", "leaders": {}}


@pytest.mark.parametrize("change, field", [
    ({"phone": "1" * 41}, "phone"),
    ({"phone": "(555)\n010-0100"}, "phone"),
    ({"address_lines": ["100 Example\tStreet"]}, "address_lines.0"),
    ({"address_lines": ["a", "b", "c", "d"]}, "address_lines"),
    ({"starred": ["anthem"]}, "starred.0"),
    ({"leaders": {"sermon": "pastor"}}, "leaders.sermon"),
    ({"leaders": {"anthem": "organist"}}, "leaders.anthem.[key]"),
    ({"extra": "x"}, "extra"),
])
def test_a_bad_body_is_a_422_naming_the_field(client, church, change, field):
    r = put(client, church, {**BODY, **change})
    assert r.status_code == 422, r.text
    assert field in r.json()["error"]["fields"], r.text
    assert "bulletin" not in stored(church)


def test_every_field_is_required(client, church):
    body = {k: v for k, v in BODY.items() if k != "gloria_patri_words"}
    r = put(client, church, body)
    assert r.status_code == 422 and "gloria_patri_words" in r.json()["error"]["fields"], r.text


def test_only_members_of_the_church(client, isolation_world):
    assert_church_isolated(client, "GET", PATH, world=isolation_world)
    assert_church_isolated(client, "PUT", PATH, world=isolation_world, json=BODY)


@pytest.mark.parametrize("bulletin", [
    {"phone": "(555)\x0b010-0100", "organist": "Jo\r\nDoe", "email": "x\x7fy", "website": "a\tb",
     "liturgist": "Sam Sample", "address_lines": ["1 Main\nSt"]},
])
def test_a_stored_control_character_reads_as_a_space_and_put_takes_it_back(client, church, bulletin):
    """Build review I1: GET always answers something PUT accepts, whatever another path stored."""
    with session_scope() as s:
        s.get(Church, church).settings = {"bulletin": bulletin}
    r = get(client, church)
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body["phone"], body["organist"], body["email"], body["website"], body["liturgist"]) == (
        "(555) 010-0100", "Jo Doe", "x y", "a b", "Sam Sample")
    assert body["address_lines"] == ["1 Main St"]
    assert put(client, church, body).status_code == 200


@pytest.mark.parametrize("char", [" ", " ", "\x85"])
def test_a_unicode_line_break_is_not_one_line(client, church, char):
    """Build review M5: U+2028, U+2029 and U+0085 are line breaks too (Word prints them as one)."""
    for change, field in (({"organist": f"Jo{char}Doe"}, "organist"),
                          ({"address_lines": [f"100 Example{char}Street"]}, "address_lines.0")):
        r = put(client, church, {**BODY, **change})
        assert r.status_code == 422, r.text
        assert field in r.json()["error"]["fields"], r.text
    assert "bulletin" not in stored(church)
