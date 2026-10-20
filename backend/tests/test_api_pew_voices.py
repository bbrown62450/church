"""POST /liturgy/pews and the pew voices on GET/PUT /church/prayer-library over
HTTP (pew voices spec 2026-10-20, "API", "Storage", Testing). The AI is a
FakeAI (integrations.openai_client.set_ai_for_tests); no test reaches OpenAI."""
import json
import logging

import pytest

from api import ratelimit
from domain_errors import Busy, UpstreamError, UpstreamTimeout
from integrations import openai_client
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
PEWS = "/liturgy/pews"
LIBRARY = "/church/prayer-library"
CARDS = [{"section": "opening_prayer", "origin": "ai", "text": "Gracious God, we praise you. Amen."}]
REACTION = {"voices": [{"voice": 2, "reactions": [{"prayer": "opening_prayer", "kind": "missed",
                                                   "text": "Too fast for me."}]}]}


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def people(make_user):
    return {email: make_user(email=email) for email in (OWNER, ADMIN, MEMBER)}


@pytest.fixture
def church(people, make_church):
    cid = make_church(name="Grace", owner_user_id=people[OWNER])
    add_membership(people[ADMIN], cid, "admin")
    add_membership(people[MEMBER], cid, "member")
    return cid


def install(reply=json.dumps(REACTION), **kw):
    fake = openai_client.FakeAI(reply=reply, **kw)
    openai_client.set_ai_for_tests(fake)
    return fake


def post(client, church_id, body=None, email=OWNER, status=200):
    r = client.post(PEWS, json=body or {"cards": CARDS}, headers=church_headers(email, church_id))
    assert r.status_code == status, r.text
    return r.json()


def put(client, church_id, voices, email=OWNER, status=200):
    body = {"prayers": [], "voice_profile": "", "pew_voices": voices}
    r = client.put(LIBRARY, json=body, headers=church_headers(email, church_id))
    assert r.status_code == status, r.text
    return r.json()


def test_every_member_hears_from_the_pews(client, church):
    install()
    for email in (OWNER, ADMIN, MEMBER):
        body = post(client, church, email=email)
        assert [v["description"] for v in body["voices"]][:2] == ["Sharp, very conservative, reads every word",
                                                                   "A teenager"]
        assert body["voices"][1]["reactions"] == [{"text": "Too fast for me.", "section": "opening_prayer",
                                                   "kind": "missed"}]
        assert body["voices"][0]["reactions"] == [] and len(body["voices"]) == 5


def test_one_tap_costs_one_ai_token_and_the_41st_is_429(client, church, people, limiter_clock):
    ai = install()
    for _ in range(39):
        ratelimit.consume("ai", user_id=people[OWNER], church_id=church)
    post(client, church)                                             # the 40th
    r = client.post(PEWS, json={"cards": CARDS}, headers=church_headers(OWNER, church))
    assert (r.status_code, r.json()["error"]["code"], r.headers["Retry-After"]) == (429, "rate_limited", "15")
    assert len(ai.calls) == 1
    limiter_clock.advance(15)
    post(client, church)
    assert len(ai.calls) == 2


def test_no_ai_or_no_voice_on_spends_no_token(client, church, people, limiter_clock):
    for _ in range(40):
        ratelimit.consume("ai", user_id=people[OWNER], church_id=church)  # the bucket is empty
    install(available=False)
    assert post(client, church, status=503)["error"]["code"] == "ai_not_configured"
    put(client, church, [{"description": "A teen", "on": False}])
    ai = install()
    error = post(client, church, status=422)["error"]
    assert error["message"] == "Turn on at least one voice in Settings → Prayers." and ai.calls == []


def test_ai_failures_are_http_statuses(client, church):
    for kw, status, code in [
        (dict(error=Busy("x", code="ai_busy")), 503, "ai_busy"),
        (dict(error=UpstreamTimeout("x", code="ai_timeout")), 504, "ai_timeout"),
        (dict(error=UpstreamError("x", code="ai_upstream_error")), 502, "ai_upstream_error"),
        (dict(reply="not json"), 502, "ai_upstream_error"),
    ]:
        install(**kw)
        assert post(client, church, status=status)["error"]["code"] == code


def test_a_bad_body_is_422_and_never_reaches_the_ai(client, church):
    ai = install()
    for body in ({}, {"cards": []}, {"cards": CARDS, "voices": ["mine"]}, {"cards": [dict(CARDS[0], section="x")]}):
        r = client.post(PEWS, json=body, headers=church_headers(OWNER, church))
        assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_request", body
    assert ai.calls == []


def test_the_route_needs_a_token_and_is_church_isolated(client, isolation_world):
    world = isolation_world
    settings = dict(churches.get_church(world.church_b)["settings"] or {})
    churches.update_church(world.church_b, settings={**settings, "pew_voices": [{"description": "SECRET-B", "on": True}]})
    ai = install()
    assert client.post(PEWS, json={"cards": CARDS}).status_code == 401
    assert_church_isolated(client, "POST", PEWS, world=world, json={"cards": CARDS})
    post(client, world.church_a, email=world.a)
    assert "SECRET-B" not in json.dumps([call["messages"] for call in ai.calls])


def test_admins_edit_the_voices_and_members_only_read_them(client, church):
    assert client.get(LIBRARY, headers=church_headers(MEMBER, church)).json()["pew_voices"][1] == {
        "description": "A teenager", "on": True}
    r = client.put(LIBRARY, json={"prayers": [], "voice_profile": "", "pew_voices": []},
                   headers=church_headers(MEMBER, church))
    assert r.status_code == 403
    assert len(client.get(LIBRARY, headers=church_headers(MEMBER, church)).json()["pew_voices"]) == 5
    saved = put(client, church, [{"description": "A nurse", "on": True}], email=ADMIN)
    assert saved["pew_voices"] == [{"description": "A nurse", "on": True}]
    assert client.get(LIBRARY, headers=church_headers(MEMBER, church)).json()["pew_voices"] == saved["pew_voices"]


def test_more_than_six_on_is_refused_with_its_field(client, church):
    error = put(client, church, [{"description": f"Voice {i}", "on": True} for i in range(7)], status=422)["error"]
    assert (error["message"], list(error["fields"])) == ("Turn on at most 6 voices.", ["pew_voices"])
    error = put(client, church, [{"description": "x" * 301, "on": True}], status=422)["error"]
    assert list(error["fields"]) == ["pew_voices.0.description"]
    r = client.put(LIBRARY, json={"prayers": [], "voice_profile": "", "pew_voices": [{"description": "A", "on": 1, "x": 2}]},
                   headers=church_headers(OWNER, church))
    assert r.status_code == 422


def test_no_log_record_down_to_debug_holds_a_prayer_a_voice_or_a_reaction(client, church, caplog):
    put(client, church, [{"description": "SECRET-VOICE", "on": True}])
    install(json.dumps({"voices": [{"voice": 1, "reactions": [{"prayer": None, "text": "SECRET-REACTION"}]}]}))
    cards = [{"section": "opening_prayer", "origin": "typed", "text": "SECRET-PRAYER"}]
    caplog.set_level(logging.INFO)
    for name in ("api", "usecases"):                    # the routes and the usecases, down to DEBUG
        caplog.set_level(logging.DEBUG, logger=name)
    body = post(client, church, {"cards": cards, "occasion": "SECRET-OCCASION"})
    put(client, church, [{"description": "SECRET-SAVED", "on": True}])
    assert body["voices"][0]["reactions"][0]["text"] == "SECRET-REACTION"
    logged = "\n".join(r.getMessage() for r in caplog.records)
    assert "liturgy.pews" in logged and "SECRET" not in logged
