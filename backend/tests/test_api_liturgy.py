"""GET /liturgy/config and POST /liturgy/generate (slice 4 spec, API; Testing
`test_api_liturgy.py`; AC1, AC4, AC5, AC7, AC8). The AI is a FakeAI
(integrations.openai_client.set_ai_for_tests)."""
import logging
import uuid

import pytest

import liturgy_config
from api import ratelimit
from db import session_scope
from db.models import Hymn
from integrations import openai_client
from repos import churches
from repos.memberships import add_membership
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    assert_church_isolated,
    auth_headers,
    church_headers,
    isolation_world,
    make_api_client,
)

EMAIL = "pastor@example.com"
HYMN_GONE = "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step."


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def owner(make_user):
    return make_user(email=EMAIL)


@pytest.fixture
def church(owner, make_church):
    return make_church(name="Grace", owner_user_id=owner)


def install(reply="Draft.", **kw):
    fake = openai_client.FakeAI(reply=reply, **kw)
    openai_client.set_ai_for_tests(fake)
    return fake


def add_hymn(church_id, title="Holy, Holy, Holy", number=138):
    with session_scope() as s:
        row = Hymn(church_id=church_id, hymnal="GG2013", title=title, number=number)
        s.add(row)
        s.flush()
        return str(row.id)


def generate(client, church_id, body, email=EMAIL, status=200):
    r = client.post("/liturgy/generate", json=body, headers=church_headers(email, church_id))
    assert r.status_code == status, r.text
    return r.json()


def test_config_is_user_scoped(client, owner):
    assert client.get("/liturgy/config").status_code == 401
    r = client.get("/liturgy/config", headers=auth_headers(EMAIL))           # no X-Church-Id
    assert r.status_code == 200, r.text


def test_config_serves_liturgy_config(client, owner):
    body = client.get("/liturgy/config", headers=auth_headers(EMAIL)).json()
    assert [s["key"] for s in body["sections"]] == liturgy_config.SECTION_ORDER
    assert body["sections"][5] == {"key": "prayers_of_the_people", "label": "Prayers of the People",
                                   "default_enabled": False, "rows": 8, "pastor_copy_only": True, "hint": None}
    assert [(p["key"], p["label"]) for p in body["custom_placements"]] == list(liturgy_config.CUSTOM_PLACEMENTS)
    assert body["outline"] == liturgy_config.outline_as_json() and len(body["outline"]) == 16
    assert body["assurance_response"] == "People: Thanks be to God! Amen."
    assert body["default_benediction_fallback"] == "Halverson"
    assert body["communion"]["default_rule"] == "first_sunday_of_month"
    assert body["communion"]["toggle_label"] == "Include communion liturgy (The Sacrament of the Lord's Supper)"
    assert len(body["communion"]["blocks"]) == len(liturgy_config.COMMUNION_BLOCKS)
    assert body["limits"] == {"max_section_text": 20_000, "max_sermon_title": 300, "max_custom_elements": 30,
                              "max_custom_label": 200, "max_custom_text": 10_000, "max_sections_per_request": 4}
    assert body["ai_available"] is False                   # no key in tests
    install()
    assert client.get("/liturgy/config", headers=auth_headers(EMAIL)).json()["ai_available"] is True


def test_generate_mixes_overrides_answers_and_errors_in_one_200(client, church):
    churches.set_church_prompts(church, {"opening_prayer": "{"})
    install(reply="  A generated call.  ")
    body = generate(client, church, {
        "occasion": "Third Sunday of Easter", "scriptures": ["Acts 9:1-6"],
        "sections": ["call_to_worship", "benediction", "opening_prayer", "call_to_worship"],
        "overrides": {"benediction": " Go in peace. ", "assurance": "not requested"},
    })
    assert body == {"results": [
        {"section": "call_to_worship", "status": "generated", "text": "A generated call.", "error": None},
        {"section": "benediction", "status": "override", "text": " Go in peace. ", "error": None},
        {"section": "opening_prayer", "status": "error", "text": None, "error": {
            "code": "prompt_invalid",
            "message": "The Opening Prayer prompt in Settings has a problem: It has a { or } without a "
                       "partner. Use {{ or }} to print a brace. An admin can fix it under Settings → "
                       "Liturgy prompts."}},
    ]}


def test_without_ai_a_typed_section_still_comes_back(client, church):
    """F acceptance 15 through the API: 200, override verbatim, ai_not_configured."""
    body = generate(client, church, {"sections": ["benediction", "call_to_worship"],
                                     "overrides": {"benediction": "Go in peace."}})
    assert [(r["status"], r["text"], r["error"]) for r in body["results"]] == [
        ("override", "Go in peace.", None),
        ("error", None, {"code": "ai_not_configured", "message": "AI not configured. Type this section yourself."}),
    ]


def test_generate_needs_a_token_and_a_membership(client, church, isolation_world, make_user):
    assert client.post("/liturgy/generate", json={"sections": ["benediction"]}).status_code == 401
    world = isolation_world
    install()
    assert_church_isolated(client, "POST", "/liturgy/generate", world=world, json={"sections": ["benediction"]})
    theirs = add_hymn(world.church_b)
    r = client.post("/liturgy/generate", headers=church_headers(world.a, world.church_a),
                    json={"sections": ["benediction"], "hymns": {"opening": {"hymn_id": theirs, "title": "x"}}})
    assert (r.status_code, r.json()["error"]["code"], r.json()["error"]["message"]) == (404, "not_found", HYMN_GONE)
    for role in ("member", "admin"):
        email = f"{role}@example.com"
        add_membership(make_user(email=email), church, role)
        assert generate(client, church, {"sections": ["benediction"]}, email=email)["results"][0]["status"] == \
            "generated"
    assert generate(client, church, {"sections": ["benediction"]})["results"][0]["status"] == "generated"


def test_invalid_bodies_are_422_with_fields(client, church):
    cases = [
        ({"sections": ["offering"]}, "sections.0"),
        ({"sections": ["benediction"] * 5}, "sections"),
        ({"sections": []}, "sections"),
        ({}, "sections"),
        ({"sections": ["benediction"], "extra": 1}, "extra"),
        ({"sections": ["benediction"], "church_id": str(uuid.uuid4())}, "church_id"),
        ({"sections": ["benediction"], "occasion": "o" * 301}, "occasion"),
        ({"sections": ["benediction"], "scriptures": ["Mark 1"] * 21}, "scriptures"),
        ({"sections": ["benediction"], "scriptures": ["r" * 201]}, "scriptures.0"),
        ({"sections": ["benediction"], "overrides": {"benediction": "x" * 20_001}}, "overrides.benediction"),
        ({"sections": ["benediction"], "overrides": {"offering": "x"}}, "overrides.offering.[key]"),
        ({"sections": ["benediction"], "hymns": {"opening": {"title": "t" * 301}}}, "hymns.opening.title"),
        ({"sections": ["benediction"], "hymns": {"opening": {"number": -1}}}, "hymns.opening.number"),
        ({"sections": ["benediction"], "hymns": {"opening": {"title": "x", "slot": "opening"}}},
         "hymns.opening.slot"),
        ({"sections": ["benediction"], "hymns": {"opening": {"hymnal": "H" * 21}}}, "hymns.opening.hymnal"),
        ({"sections": ["benediction"], "hymns": {"offertory": None}}, "hymns.offertory"),
        ({"sections": ["benediction"], "sermon_text": {"ref": "r" * 201, "text": "x"}}, "sermon_text.ref"),
        ({"sections": ["benediction"], "sermon_text": {"ref": "Mark 4", "text": "x" * 20_001}}, "sermon_text.text"),
        ({"sections": ["benediction"], "sermon_text": {"ref": "Mark 4", "text": "x", "translation": "esv"}},
         "sermon_text.translation"),
    ]
    for body, field in cases:
        r = client.post("/liturgy/generate", json=body, headers=church_headers(EMAIL, church))
        assert r.status_code == 422, (body, r.text)
        error = r.json()["error"]
        assert error["code"] == "invalid_request" and field in error["fields"], (field, error)


def test_hymn_ref_and_sermon_text_accept_what_f_1_3_allows(client, church):
    install()
    for hymn in ({"hymn_id": None, "title": "t" * 300}, {"title": "Old", "hymnal": "H"},
                 {"title": "Old", "hymnal": "old code", "number": 0}):
        generate(client, church, {"sections": ["benediction"], "hymns": {"closing": hymn}})
    generate(client, church, {"sections": ["benediction"],
                              "sermon_text": {"ref": "r" * 200, "text": "x" * 20_000}})
    generate(client, church, {"sections": ["benediction"]})        # sermon_text is optional (additive)


def test_the_41st_ai_section_in_ten_minutes_is_429(client, church, owner, limiter_clock):
    install()
    for _ in range(36):
        ratelimit.consume("ai", user_id=owner, church_id=church)
    four = ["call_to_worship", "opening_prayer", "assurance", "benediction"]
    assert len(generate(client, church, {"sections": four})["results"]) == 4        # sections 37-40
    r = client.post("/liturgy/generate", json={"sections": ["benediction"]}, headers=church_headers(EMAIL, church))
    assert (r.status_code, r.json()["error"]["code"], r.headers["Retry-After"]) == (429, "rate_limited", "15")
    limiter_clock.advance(15)
    generate(client, church, {"sections": ["benediction"]})


def test_only_sections_that_reach_the_ai_are_charged(client, church, owner, limiter_clock):
    for _ in range(40):                                        # the user's bucket is empty
        ratelimit.consume("ai", user_id=owner, church_id=church)
    generate(client, church, {"sections": ["benediction"], "overrides": {"benediction": "Go."}})
    generate(client, church, {"sections": ["benediction"]})                        # AI not configured
    install()
    generate(client, church, {"sections": ["benediction"], "hymns": {"opening": {"hymn_id": str(uuid.uuid4())}}},
             status=404)
    churches.set_church_prompts(church, {"benediction": "{0}"})
    body = generate(client, church, {"sections": ["benediction"]})                 # only prompt_invalid
    assert body["results"][0]["error"]["code"] == "prompt_invalid"
    r = client.post("/liturgy/generate", json={"sections": ["assurance"]}, headers=church_headers(EMAIL, church))
    assert r.status_code == 429                                  # one that reaches the AI is charged


def test_info_logs_carry_no_prompt_or_answer(client, church, caplog):
    install(reply="SECRET-ANSWER words")
    churches.set_church_prompts(church, {"benediction": "SECRET-PROMPT {occasion}"})
    with caplog.at_level(logging.INFO):
        generate(client, church, {"occasion": "SECRET-OCCASION", "sections": ["benediction", "assurance"],
                                  "overrides": {"assurance": "SECRET-TYPED"},
                                  "sermon_text": {"ref": "Mark 4:35-41", "text": "SECRET-SERMON"}})
    info = "\n".join(r.getMessage() for r in caplog.records if r.levelno >= logging.INFO)
    assert "liturgy.generate" in info and "outcomes=generated:1,override:1,error:0" in info
    assert "sermon=yes" in info and "outcome=ok" in info
    assert "SECRET" not in info
