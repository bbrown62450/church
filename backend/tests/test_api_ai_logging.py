"""No prompt, prayer, note, reaction or AI answer reaches a log record, at any
level down to DEBUG, on the four AI routes: /liturgy/generate, /liturgy/review,
/liturgy/revise and /liturgy/pews (F §2.5; pew voices plan, the owner's answer
A of 2026-10-20). The `api`, `usecases` and `integrations` loggers are captured
at DEBUG. The AI is a FakeAI; no test reaches OpenAI."""
import json
import logging

import pytest

from integrations import openai_client
from tests.api_helpers import church_headers, make_api_client

EMAIL = "pastor@example.com"
CARDS = [{"section": "opening_prayer", "origin": "typed", "text": "SECRET-PRAYER Gracious God, hear us."}]
CALLS = {
    "/liturgy/generate": (
        {"sections": ["opening_prayer"], "occasion": "SECRET-OCCASION", "scriptures": ["Mark 4:35-41"]},
        "SECRET-ANSWER Holy God, hear us. Amen.",
    ),
    "/liturgy/review": (
        {"occasion": "SECRET-OCCASION", "cards": CARDS},
        json.dumps({"cards": [{"section": "opening_prayer", "notes": [{"tag": "theology", "text": "SECRET-ANSWER A note."}]}],
                    "service_notes": []}),
    ),
    "/liturgy/revise": (
        {"section": "opening_prayer", "text": "SECRET-PRAYER Gracious God.", "notes": ["SECRET-NOTE Shorter."],
         "occasion": "SECRET-OCCASION", "scriptures": []},
        "SECRET-ANSWER Gracious God, hear us.",
    ),
    "/liturgy/pews": (
        {"occasion": "SECRET-OCCASION", "cards": CARDS},
        json.dumps({"voices": [{"voice": 1, "reactions": [{"prayer": None, "text": "SECRET-ANSWER A reaction."}]}]}),
    ),
}


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def church(make_user, make_church):
    return make_church(name="Grace", owner_user_id=make_user(email=EMAIL))


@pytest.mark.parametrize("path", list(CALLS))
def test_no_log_record_down_to_debug_holds_the_prompt_the_prayers_or_the_answer(client, church, caplog, path):
    body, reply = CALLS[path]
    fake = openai_client.FakeAI(reply=reply)
    openai_client.set_ai_for_tests(fake)
    for name in ("api", "usecases", "integrations"):
        caplog.set_level(logging.DEBUG, logger=name)
    r = client.post(path, json=body, headers=church_headers(EMAIL, church))
    assert r.status_code == 200, r.text
    assert len(fake.calls) == 1 and "SECRET-ANSWER" in r.text          # the AI was called and its answer used
    logged = "\n".join(f"{record.name} {record.getMessage()}" for record in caplog.records)
    assert caplog.records and "SECRET" not in logged
