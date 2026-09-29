"""POST /hymns/scripture-matches (slice 3 spec, API row 3, Models
`ScriptureMatchIn`/`HymnMatchOut`/`ScriptureMatchesOut`, API notes "Hymnal
resolution", Backend 3.5; Testing `test_api_hymn_matches.py`; AC1, AC3, AC8,
AC20)."""
import logging

import pytest

from db import session_scope
from db.models import Hymn, HymnUsage
from repos import churches
from repos.memberships import add_membership
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    assert_church_isolated,
    church_headers,
    isolation_world,
    make_api_client,
)

EMAIL = "pastor@example.com"
HYMNAL_MESSAGE = "That hymnal isn't in this church's library."


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def church(make_user, make_church):
    return make_church(name="Grace", owner_user_id=make_user(email=EMAIL))


def add(church_id, title, refs, number=None, hymnal="GG2013", **columns):
    with session_scope() as s:
        s.add(Hymn(church_id=church_id, hymnal=hymnal, title=title, number=number,
                   scripture_refs=refs, **columns))


def post(client, church_id, body, email=EMAIL, status=200):
    r = client.post("/hymns/scripture-matches", json=body, headers=church_headers(email, church_id))
    assert r.status_code == status, r.text
    return r.json()


def test_happy_path_grouped_by_strength(client, church):
    add(church, "Transfiguration Hymn", "Matt 17:1-8", 10)
    add(church, "Same Chapter", "Mark 1:1-8", 11)
    add(church, "Baptism Hymn", "Mark 1:9", 12)
    add(church, "Over-match Bait", "Mark 10:45", 13)
    add(church, "Emmaus", "Luke 24:13-35", 14)
    body = post(client, church, {"refs": [" Mark 1:9-15 ", "", "Matthew 17 OR Luke 24:30"]})
    assert body["hymnal"] == "GG2013"
    assert body["refs_used"] == ["Mark 1:9-15", "Matthew 17", "Luke 24:30"]
    assert body["unparsed_refs"] == []
    assert body["total_matched"] == 4
    assert [(h["title"], h["strength"], h["matched_refs"]) for h in body["items"]] == [
        ("Baptism Hymn", "passage", ["Mark 1:9-15"]),
        ("Transfiguration Hymn", "passage", ["Matthew 17"]),
        ("Emmaus", "passage", ["Luke 24:30"]),
        ("Same Chapter", "chapter", ["Mark 1:9-15"]),
    ]
    assert set(body["items"][0]) >= {"id", "number", "link", "themes", "recent_use_on",
                                     "text_year", "hymnal_count", "newer_than_preferred"}


def test_refs_blank_after_trimming_is_422(client, church):
    add(church, "Any", "John 3:16")
    for refs in ([], ["", "   "], [" or "]):
        error = post(client, church, {"refs": refs}, status=422)["error"]
        assert (error["code"], error["message"]) == ("invalid_request", "Enter at least one scripture reference.")
        assert error["fields"] == {"refs": "Enter at least one scripture reference."}


def test_a_hymnal_the_church_lacks_is_422_with_one_message(client, isolation_world):
    world = isolation_world
    add(world.church_a, "A", "John 3:16")
    add(world.church_b, "B", "John 3:16", hymnal="BONLY")
    for code in ("BONLY", "NOWHERE", ""):
        error = post(client, world.church_a, {"refs": ["John 3"], "hymnal": code},
                     email=world.a, status=422)["error"]
        assert (error["message"], error["fields"]) == (HYMNAL_MESSAGE, {"hymnal": HYMNAL_MESSAGE}), code


def test_unreadable_references_are_reported(client, church):
    add(church, "Mountain", "Matthew 17:1-9")
    body = post(client, church, {"refs": ["Transfiguration", "Matthew 17"]})
    assert body["unparsed_refs"] == ["Transfiguration"]
    assert [h["title"] for h in body["items"]] == ["Mountain"]


def test_recent_use_on_is_set_for_the_date(client, church):
    add(church, "Recent", "Psalm 23")
    add(church, "Not recent", "Psalm 23:1")
    with session_scope() as s:
        s.add(HymnUsage(church_id=church, date_iso="2026-09-20", hymn_number=5, hymn_title="recent"))
    body = post(client, church, {"refs": ["Psalm 23"], "recent_for_date": "2026-10-04"})
    assert {h["title"]: h["recent_use_on"] for h in body["items"]} == {
        "Recent": "2026-09-20", "Not recent": None}
    assert all(h["recent_use_on"] is None for h in post(client, church, {"refs": ["Psalm 23"]})["items"])


def test_one_debug_line_counts_parsed_and_unparsed(client, church, caplog):
    # S Risks, "Unknown scripture_refs formats": counts only, never a title or a reference.
    add(church, "Readable", "John 3:16")
    add(church, "Odd", "Genesis 1.1; see the preface")
    caplog.set_level(logging.DEBUG, logger="usecases.hymns")
    post(client, church, {"refs": ["John 3", "Transfiguration"]})
    lines = [r.getMessage() for r in caplog.records if r.getMessage().startswith("hymn_matches")]
    assert lines == ["hymn_matches refs=2 refs_unparsed=1 hymns=2 hymns_with_unparsed=1 matched=1"]


def test_an_empty_church_hymnal_is_200_and_empty(client, church):
    assert post(client, church, {"refs": ["John 3:16"]}) == {
        "hymnal": None, "refs_used": ["John 3:16"], "unparsed_refs": [], "total_matched": 0, "items": []}


def test_null_hymnal_is_the_effective_one_and_a_named_one_is_used(client, church):
    add(church, "Green", "John 3:16", hymnal="GG2013")
    add(church, "Blue", "John 3:16", hymnal="PH1990")
    stored = churches.get_church(church)["settings"] or {}
    churches.update_church(church, settings={**stored, "default_hymnal": "PH1990"})
    assert [h["title"] for h in post(client, church, {"refs": ["John 3"]})["items"]] == ["Blue"]
    body = post(client, church, {"refs": ["John 3"], "hymnal": "GG2013"})
    assert (body["hymnal"], [h["title"] for h in body["items"]]) == ("GG2013", ["Green"])


def test_matches_carry_the_facts_and_the_newer_flag(client, church):
    add(church, "Newer", "John 3:16", text_year=1985, hymnal_count=40)
    add(church, "Older", "John 3:17", text_year=1826, hymnal_count=1322)
    items = post(client, church, {"refs": ["John 3"]})["items"]
    assert {h["title"]: (h["text_year"], h["hymnal_count"], h["newer_than_preferred"]) for h in items} == {
        "Newer": (1985, 40, True), "Older": (1826, 1322, False)}


def test_body_limits_and_extra_fields_are_422(client, church):
    for body in ({"refs": ["John 3"], "extra": 1}, {"refs": ["x" * 201]}, {"refs": ["John 3"] * 21},
                 {"refs": ["John 3"], "hymnal": "H" * 21}, {"refs": ["John 3"], "limit_per_ref": 0},
                 {"refs": ["John 3"], "max_results": 101}, {"refs": ["John 3"], "recent_for_date": "2026-10-4"}):
        error = post(client, church, body, status=422)["error"]
        assert (error["code"], error["message"]) == ("invalid_request", "The request was not valid."), body


def test_isolation_and_every_role(client, isolation_world, make_user):
    world = isolation_world
    add(world.church_a, "A's hymn", "John 3:16")
    add(world.church_b, "B's hymn", "John 3:16")
    assert_church_isolated(client, "POST", "/hymns/scripture-matches", world=world, json={"refs": ["John 3"]})
    assert [h["title"] for h in post(client, world.church_a, {"refs": ["John 3"]}, email=world.a)["items"]] == [
        "A's hymn"]
    for role in ("admin", "member"):
        email = f"{role}@example.com"
        add_membership(make_user(email=email), world.church_a, role)
        assert post(client, world.church_a, {"refs": ["John 3"]}, email=email)["total_matched"] == 1
