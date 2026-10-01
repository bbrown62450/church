"""POST /liturgy/review and POST /liturgy/revise (reviewer spec, API and Testing
"Routes"; slice 4 spec, reviewer amendment). The AI is a FakeAI
(integrations.openai_client.set_ai_for_tests)."""
import json
import logging
import uuid

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

EMAIL = "pastor@example.com"
STOCK = 'Stock phrase "as we journey". Say it more naturally.'
CARDS = [
    {"section": "call_to_worship", "origin": "typed", "text": "Leader: Gracious God, as we journey, we come."},
    {"section": "opening_prayer", "origin": "ai", "text": "Gracious God, we praise you. Amen."},
]
REVISE = {"section": "opening_prayer", "text": "Gracious God, as we journey, hear us.", "notes": [STOCK],
          "occasion": "Third Sunday of Easter", "scriptures": ["Acts 9:1-6"]}


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def owner(make_user):
    return make_user(email=EMAIL)


@pytest.fixture
def church(owner, make_church):
    return make_church(name="Grace", owner_user_id=owner)


def install(reply='{"cards": [], "service_notes": []}', **kw):
    fake = openai_client.FakeAI(reply=reply, **kw)
    openai_client.set_ai_for_tests(fake)
    return fake


def set_settings(church_id, **values):
    settings = dict(churches.get_church(church_id)["settings"] or {})
    settings.update(values)
    churches.update_church(church_id, settings=settings)


def post(client, path, church_id, body, email=EMAIL, status=200):
    r = client.post(path, json=body, headers=church_headers(email, church_id))
    assert r.status_code == status, r.text
    return r.json()


def test_review_without_ai_returns_the_code_notes_in_a_200(client, church):
    body = post(client, "/liturgy/review", church, {"occasion": "Easter", "cards": CARDS})
    assert body == {
        "cards": [
            {"section": "call_to_worship", "notes": [{"tag": "rules", "text": STOCK, "source": "code"}]},
            {"section": "opening_prayer", "notes": []},
        ],
        "service_notes": [{"tag": "repetition", "text": 'Several prayers open with "Gracious God".', "source": "code"}],
        "ai_status": "not_configured",
    }


def test_review_with_the_ai_merges_its_notes_and_an_empty_bucket_is_still_a_200(client, church, owner,
                                                                                 limiter_clock):
    ai = install(json.dumps({"cards": [{"section": "opening_prayer",
                                        "notes": [{"tag": "theology", "text": "Praise is not a payment."}]}],
                             "service_notes": []}))
    for _ in range(39):                                          # one ai token left
        ratelimit.consume("ai", user_id=owner, church_id=church)
    body = post(client, "/liturgy/review", church, {"cards": CARDS})
    assert body["ai_status"] == "ok" and len(ai.calls) == 1
    assert body["cards"][1]["notes"] == [{"tag": "theology", "text": "Praise is not a payment.", "source": "ai"}]
    body = post(client, "/liturgy/review", church, {"cards": CARDS})         # the bucket is empty: no 429
    assert body["ai_status"] == "rate_limited" and len(ai.calls) == 1
    assert body["cards"][0]["notes"] == [{"tag": "rules", "text": STOCK, "source": "code"}]
    limiter_clock.advance(15)
    assert post(client, "/liturgy/review", church, {"cards": CARDS})["ai_status"] == "ok"


def test_both_routes_need_a_token_and_a_membership(client, church, isolation_world, make_user):
    install()
    for path, body in (("/liturgy/review", {"cards": CARDS}), ("/liturgy/revise", REVISE)):
        assert client.post(path, json=body).status_code == 401
        assert_church_isolated(client, "POST", path, world=isolation_world, json=body)
        for role in ("member", "admin"):
            email = f"{role}-{path[9:]}@example.com"
            add_membership(make_user(email=email), church, role)
            post(client, path, church, body, email=email)


def test_another_church_s_prompt_rubric_and_profile_never_reach_the_ai(client, isolation_world):
    world = isolation_world
    churches.set_church_prompts(world.church_b, {"system": "SECRET-B-VOICE"})
    set_settings(world.church_b, rubric={"prayers": {"opening_prayer": ["SECRET-B-POINT"]}},
                 prayer_library={"prayers": [], "voice_profile": "SECRET-B-PROFILE"})
    churches.set_church_prompts(world.church_a, {"system": "A-VOICE"})
    ai = install()
    post(client, "/liturgy/review", world.church_a, {"cards": CARDS}, email=world.a)
    ai.reply = "Revised."
    post(client, "/liturgy/revise", world.church_a, REVISE, email=world.a)
    sent = json.dumps([call["messages"] for call in ai.calls])
    assert len(ai.calls) == 2 and "A-VOICE" in sent and "SECRET-B" not in sent


def test_invalid_bodies_are_422_with_fields_and_never_reach_the_ai(client, church):
    ai = install()
    card = CARDS[0]
    review_cases = [
        ({}, "cards"),
        ({"cards": []}, "cards"),
        ({"cards": [dict(card, section=s) for s in
                    ("call_to_worship", "opening_prayer", "prayer_of_confession", "assurance",
                     "prayer_for_illumination", "prayers_of_the_people", "offertory_prayer", "benediction")]
                   + [card]}, "cards"),
        ({"cards": [card, dict(card, origin="ai")]}, "cards"),                  # one card per section
        ({"cards": [dict(card, section="offering")]}, "cards.0.section"),
        ({"cards": [dict(card, origin="empty")]}, "cards.0.origin"),
        ({"cards": [dict(card, text="x" * 20_001)]}, "cards.0.text"),
        ({"cards": [dict(card, extra=1)]}, "cards.0.extra"),
        ({"cards": [card], "church_id": str(uuid.uuid4())}, "church_id"),
        ({"cards": [card], "occasion": "o" * 301}, "occasion"),
        ({"cards": [card], "scriptures": ["Mark 1"] * 21}, "scriptures"),
        ({"cards": [card], "scriptures": ["r" * 201]}, "scriptures.0"),
        ({"cards": [card], "sermon_text": {"ref": "Mark 4", "text": "x" * 20_001}}, "sermon_text.text"),
        ({"cards": [card], "rubric": {}}, "rubric"),                            # never from the client
    ]
    revise_cases = [
        (dict(REVISE, notes=[]), "notes"),
        (dict(REVISE, notes=["a", "b", "c", "d"]), "notes"),
        (dict(REVISE, notes=["n" * 241]), "notes.0"),
        (dict(REVISE, text="x" * 20_001), "text"),
        (dict(REVISE, section="custom"), "section"),
        ({k: v for k, v in REVISE.items() if k != "text"}, "text"),
        (dict(REVISE, system_prompt="mine"), "system_prompt"),
        (dict(REVISE, sermon_text={"ref": "r" * 201, "text": "x"}), "sermon_text.ref"),
        (dict(REVISE, text=""), "text"),                                          # an empty draft
        (dict(REVISE, text=" \n\t "), "text"),                                    # a blank draft
        (dict(REVISE, notes=[""]), "notes.0"),                                    # an empty note
        (dict(REVISE, notes=[STOCK, "  \n "]), "notes"),                          # a blank note
    ]
    for path, cases in (("/liturgy/review", review_cases), ("/liturgy/revise", revise_cases)):
        for body, field in cases:
            r = client.post(path, json=body, headers=church_headers(EMAIL, church))
            assert r.status_code == 422, (path, body, r.text)
            error = r.json()["error"]
            assert error["code"] == "invalid_request" and field in error["fields"], (path, field, error)
    assert ai.calls == []
    post(client, "/liturgy/review", church, {"cards": [card], "sermon_text": {"ref": "r" * 200, "text": "x" * 20_000}})
    post(client, "/liturgy/review", church, {"cards": [dict(card, text="")]})         # a blank card is allowed


def test_revise_returns_the_text_and_ai_failures_are_http_statuses(client, church):
    ai = install(reply="  Gracious God, hear us.  ")
    assert post(client, "/liturgy/revise", church, REVISE) == {"text": "Gracious God, hear us."}
    assert ai.calls[0]["max_completion_tokens"] == 1500
    cases = [
        (dict(available=False), 503, "ai_not_configured", "AI isn't set up on this app yet."),
        (dict(error=Busy("x", code="ai_busy")), 503, "ai_busy", "The AI service is busy. Try again in a minute."),
        (dict(error=UpstreamTimeout("x", code="ai_timeout")), 504, "ai_timeout",
         "The AI took too long to answer. Try again."),
        (dict(error=UpstreamError("x", code="ai_upstream_error")), 502, "ai_upstream_error",
         "The AI service had a problem. Try again."),
    ]
    for kw, status, code, message in cases:
        install(**kw)
        error = post(client, "/liturgy/revise", church, REVISE, status=status)["error"]
        assert (error["code"], error["message"]) == (code, message)
    churches.set_church_prompts(church, {"system": "s" * 8000})
    ai = install(reply="Revised.")
    error = post(client, "/liturgy/revise", church, dict(REVISE, text="d" * 20_000), status=422)["error"]
    assert (error["code"], error["message"], ai.calls) == ("prompt_invalid", "This prayer is too long to revise.", [])
    assert "fields" not in error


def test_revise_costs_one_ai_token_and_the_41st_is_429(client, church, owner, limiter_clock):
    install(reply="Revised.")
    for _ in range(39):
        ratelimit.consume("ai", user_id=owner, church_id=church)
    post(client, "/liturgy/revise", church, REVISE)                  # the 40th
    r = client.post("/liturgy/revise", json=REVISE, headers=church_headers(EMAIL, church))
    assert (r.status_code, r.json()["error"]["code"], r.headers["Retry-After"]) == (429, "rate_limited", "15")
    limiter_clock.advance(15)
    post(client, "/liturgy/revise", church, REVISE)


def test_info_logs_carry_no_prayer_text_or_notes(client, church, caplog):
    install(reply=json.dumps({"cards": [{"section": "opening_prayer",
                                         "notes": [{"tag": "theology", "text": "SECRET-NOTE"}]}]}))
    cards = [{"section": "opening_prayer", "origin": "ai", "text": "SECRET-TEXT"}]
    with caplog.at_level(logging.INFO):
        post(client, "/liturgy/review", church, {"occasion": "SECRET-OCCASION", "cards": cards,
                                                 "sermon_text": {"ref": "Mark 4", "text": "SECRET-SERMON"}})
        install(reply="SECRET-ANSWER")
        post(client, "/liturgy/revise", church, dict(REVISE, text="SECRET-DRAFT", notes=["SECRET-NOTE"]))
    info = "\n".join(r.getMessage() for r in caplog.records if r.levelno >= logging.INFO)
    assert "liturgy.review" in info and "ai_status=ok" in info and "liturgy.revise" in info
    assert "SECRET" not in info
