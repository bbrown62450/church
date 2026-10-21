"""No prompt, prayer, note, reaction or AI answer reaches a log record, at any
level down to DEBUG, on the four AI routes: /liturgy/generate, /liturgy/review,
/liturgy/revise and /liturgy/pews (F §2.5; pew voices plan, the owner's answer
A of 2026-10-20). The `api`, `usecases` and `integrations` loggers are captured
at DEBUG, and each record is read as a handler would write it, its exception
text included. The pews case also marks the church's voice description. The
AI is a FakeAI; no test reaches OpenAI."""
import json
import logging

import pytest

from integrations import openai_client
from repos import churches
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
    church_id = make_church(name="Grace", owner_user_id=make_user(email=EMAIL))
    settings = dict(churches.get_church(church_id)["settings"] or {})
    settings["pew_voices"] = [{"description": "SECRET-VOICE A nurse on nights", "on": True}]
    churches.update_church(church_id, settings=settings)
    return church_id


def logged(caplog) -> str:
    """Every record as a handler would write it: the logger, the message and any exception or stack text."""
    formatter = logging.Formatter("%(name)s %(message)s")
    return "\n".join(formatter.format(record) for record in caplog.records)


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
    if path == "/liturgy/pews":                                         # the marked voice reached the AI
        assert "SECRET-VOICE" in fake.calls[0]["messages"][1]["content"]
    assert caplog.records and "SECRET" not in logged(caplog)


def test_a_failed_pews_call_logs_no_voice_prayer_or_upstream_text_even_in_exception_text(client, church, caplog):
    body, _ = CALLS["/liturgy/pews"]
    fake = openai_client.FakeAI(error=RuntimeError("SECRET-UPSTREAM the SDK quoting SECRET-VOICE and SECRET-PRAYER"))
    openai_client.set_ai_for_tests(fake)
    for name in ("api", "usecases", "integrations"):
        caplog.set_level(logging.DEBUG, logger=name)
    r = client.post("/liturgy/pews", json=body, headers=church_headers(EMAIL, church))
    assert r.status_code == 502 and "SECRET" not in r.text
    assert len(fake.calls) == 1
    assert caplog.records and "SECRET" not in logged(caplog)
