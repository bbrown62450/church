"""POST /hymns/suggestions (slice 3 spec, API row 4, Models, Backend 3.6-3.8;
Testing `test_api_hymn_suggestions.py`, "Isolation and roles", "Rate limit",
"Rubric"; owner decision 3; owner answer Q1 of 2026-09-29; AC4-AC8, AC11,
AC18-AC20). The AI is a FakeAI (integrations.openai_client.set_ai_for_tests);
the NT text fetcher is patched on usecases.passages."""
import json
import re
import threading
import time
import uuid

import pytest

from api import ratelimit
from db import session_scope
from db.models import Hymn, HymnUsage
from domain_errors import Busy, NotConfigured, UpstreamError, UpstreamTimeout
from integrations import openai_client
from repos import churches
from repos.memberships import add_membership
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    assert_church_isolated,
    church_headers,
    isolation_world,
    make_api_client,
)
from usecases import hymns as hymns_usecase
from usecases import passages

EMAIL = "pastor@example.com"
DATE = "2026-10-04"


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def owner(make_user):
    return make_user(email=EMAIL)


@pytest.fixture
def church(owner, make_church):
    return make_church(name="Grace", owner_user_id=owner)


@pytest.fixture
def fetched(monkeypatch):
    """The NT fetcher: records (ref, translation) and returns the passage text."""
    calls = []

    def fetch(ref, translation):
        calls.append((ref, translation))
        return f"Text of {ref}."

    monkeypatch.setattr(passages, "get_passage_text", fetch)
    return calls


def add(church_id, title, number, *, theme=None, refs=None, year=None, count=None, hymnal="GG2013"):
    with session_scope() as s:
        row = Hymn(church_id=church_id, hymnal=hymnal, title=title, number=number, theme=theme,
                   scripture_refs=refs, text_year=year, hymnal_count=count)
        s.add(row)
        s.flush()
        return str(row.id)


def hymnal(church_id, n=30, **kw):
    return [add(church_id, f"Hymn {i}", i, theme="gathering, joy", refs="Psalm 23", **kw)
            for i in range(1, n + 1)]


def use(church_id, title, date_iso):
    with session_scope() as s:
        s.add(HymnUsage(church_id=church_id, date_iso=date_iso, hymn_number=None, hymn_title=title))


def tokens_for(prompt, slot, n=5):
    line = next(line for line in prompt.splitlines() if line.startswith(f"{slot.upper()} CANDIDATES: "))
    return line.split(": ", 1)[1].split(", ")[:n]


def first_tokens(messages):
    """A FakeAI reply: each slot's first five candidate tokens."""
    prompt = messages[1]["content"]
    return json.dumps({slot: tokens_for(prompt, slot) for slot in ("opening", "response", "closing")})


def install(reply=first_tokens, **kw):
    fake = openai_client.FakeAI(reply=reply, **kw)
    openai_client.set_ai_for_tests(fake)
    return fake


def suggest(client, church_id, body=None, email=EMAIL, status=200):
    r = client.post("/hymns/suggestions", json={"service_date_iso": DATE, **(body or {})},
                    headers=church_headers(email, church_id))
    assert r.status_code == status, r.text
    return r.json()


def slot_titles(body):
    return {slot: [h["title"] for h in items] for slot, items in body["slots"].items()}


def prompt_of(fake, call=-1):
    return fake.calls[call]["messages"][1]["content"]


def test_happy_path_distinct_tops_at_most_five_with_facts(client, church, fetched):
    hymnal(church, year=1985, count=40)
    add(church, "Holy, Holy, Holy", 100, theme="gathering", refs="Psalm 23", year=1826, count=1322)
    fake = install()
    body = suggest(client, church, {"scriptures": ["Psalm 23"]})
    assert body["hymnal"] == "GG2013" and body["excluded_recent_count"] == 0
    assert all(1 <= len(items) <= 5 for items in body["slots"].values())
    tops = [items[0]["id"] for items in body["slots"].values()]
    assert len(set(tops)) == 3
    first = body["slots"]["opening"][0]
    assert first["title"] == "Holy, Holy, Holy"                    # older and familiar ranks first
    assert (first["text_year"], first["hymnal_count"], first["newer_than_preferred"], first["source"]) == (
        1826, 1322, False, "ai")
    assert body["slots"]["opening"][1]["newer_than_preferred"] is True      # 1985
    (call,) = fake.calls
    assert (call["max_completion_tokens"], call["json_mode"]) == (1200, True)


def test_ai_errors_return_their_code_and_exact_message(client, church, fetched):
    hymnal(church)
    cases = [
        (install, {"available": False}, 503, "ai_not_configured", "AI suggestions aren't set up on this app yet."),
        (install, {"error": NotConfigured("quota", code="ai_not_configured")}, 503, "ai_not_configured",
         "AI suggestions aren't set up on this app yet."),
        (install, {"error": UpstreamTimeout(openai_client.TIMEOUT_MESSAGE, code="ai_timeout")}, 504,
         "ai_timeout", "The AI took too long to answer. Try again."),
        (install, {"error": Busy(openai_client.BUSY_MESSAGE, code="ai_busy")}, 503, "ai_busy",
         "The AI service is busy. Try again in a minute."),
        (install, {"error": UpstreamError(openai_client.UPSTREAM_MESSAGE, code="ai_upstream_error")}, 502,
         "ai_upstream_error", "The AI service had a problem. Try again."),
        (install, {"reply": "Sorry, I can't help with that."}, 502, "ai_upstream_error",
         "The AI gave an answer we couldn't use. Try again."),
        (install, {"reply": '{"opening": ["H999"], "response": [], "closing": []}'}, 502,
         "ai_upstream_error", "The AI gave an answer we couldn't use. Try again."),
    ]
    for setup, kw, status, code, message in cases:
        setup(**kw)
        error = suggest(client, church, status=status)["error"]
        assert (error["code"], error["message"]) == (code, message), kw
        assert set(error) == {"code", "message", "request_id"}, kw


def test_client_nt_text_skips_the_fetch(client, church, fetched):
    hymnal(church)
    fake = install()
    body = suggest(client, church, {"selected_nt_ref": "Mark 1:9-15", "nt_text": "Client text " * 300})
    assert fetched == [] and body["nt_text_used"] is True and body["nt_ref"] == "Mark 1:9-15"
    excerpt = prompt_of(fake).split("NT PASSAGE TEXT (excerpt): ")[1].split("\n")[0]
    assert excerpt.startswith("Client text") and len(excerpt) == 1500


def test_the_fetch_is_web_for_the_selected_or_the_default_nt_reading(client, church, fetched):
    hymnal(church)
    install()
    suggest(client, church, {"selected_nt_ref": " Mark 1:9-15 ", "scriptures": ["Isaiah 6:1-8"]})
    body = suggest(client, church, {"scriptures": ["Isaiah 6:1-8", "Psalm 29", "Romans 8:12-17",
                                                   "John 3:1-17"]})
    assert fetched == [("Mark 1:9-15", "web"), ("Romans 8:12-17", "web")]
    assert (body["nt_ref"], body["nt_text_used"]) == ("Romans 8:12-17", True)


def test_a_failed_or_empty_fetch_is_tolerated(client, church, monkeypatch):
    hymnal(church)
    install()
    for fetch in (lambda ref, tr: None, lambda ref, tr: 1 / 0):
        monkeypatch.setattr(passages, "get_passage_text", fetch)
        body = suggest(client, church, {"selected_nt_ref": "Mark 1:9-15"})
        assert body["nt_text_used"] is False


def test_a_hung_fetch_is_cut_off_by_its_budget(client, church, monkeypatch):
    hymnal(church)
    fake = install()
    release = threading.Event()
    monkeypatch.setattr(passages, "get_passage_text", lambda ref, tr: release.wait(5) and "late")
    monkeypatch.setattr(hymns_usecase, "NT_FETCH_BUDGET_S", 0.05)
    try:
        started = time.monotonic()
        body = suggest(client, church, {"selected_nt_ref": "Mark 1:9-15"})
        assert time.monotonic() - started < 1.0
        assert body["nt_text_used"] is False and len(fake.calls) == 1
    finally:
        release.set()


def test_the_ai_gets_the_75_second_deadline(client, church, fetched, monkeypatch):
    hymnal(church)
    fake = install()
    before = time.monotonic()
    suggest(client, church)
    after = time.monotonic()
    deadline = fake.calls[0]["deadline"]
    assert before + hymns_usecase.SUGGEST_BUDGET_S <= deadline <= after + hymns_usecase.SUGGEST_BUDGET_S


def test_one_token_per_slot_is_topped_up_to_three(client, church, fetched):
    hymnal(church)

    def one_each(messages):             # one different hymn per slot
        prompt = messages[1]["content"]
        return json.dumps({slot: [tokens_for(prompt, slot)[i]]
                           for i, slot in enumerate(("opening", "response", "closing"))})

    install(reply=one_each)
    body = suggest(client, church, {"scriptures": ["Psalm 23"]})
    for slot, items in body["slots"].items():
        assert [h["source"] for h in items] == ["ai", "candidates", "candidates"], slot


def test_the_nt_readings_matches_lead_the_response_candidates(client, church, fetched):
    for i in range(1, 31):
        add(church, f"OT {i}", i, refs="Isaiah 6:3")
    for i in range(1, 4):
        add(church, f"Gospel {i}", 100 + i, refs="Mark 1:10")
    fake = install()
    suggest(client, church, {"scriptures": ["Isaiah 6:1-8", "Mark 1:9-15"], "selected_nt_ref": "Mark 1:9-15"})
    prompt = prompt_of(fake)
    lines = {line.split(" | ")[0]: line.split(" | ")[1] for line in prompt.splitlines()
             if re.match(r"^H\d+ \| ", line)}
    assert [lines[t] for t in tokens_for(prompt, "response", n=3)] == ["Gospel 1", "Gospel 2", "Gospel 3"]


def test_exclude_recent_leaves_recent_hymns_out_of_prompt_and_answer(client, church, fetched):
    hymnal(church, n=20)
    use(church, "hymn 1", "2026-09-27")              # within 12 weeks before
    use(church, "Hymn 2", "2026-12-27")              # the last day after
    use(church, "Hymn 3", DATE)                      # the service date itself: not excluded
    use(church, "Hymn 4", "2026-07-11")              # one day too early
    fake = install()
    body = suggest(client, church, {"scriptures": ["Psalm 23"]})
    assert body["excluded_recent_count"] == 2
    prompt = prompt_of(fake)
    assert "| Hymn 1 |" not in prompt and "| Hymn 2 |" not in prompt
    assert "| Hymn 3 |" in prompt and "| Hymn 4 |" in prompt
    returned = {t for titles in slot_titles(body).values() for t in titles}
    assert not {"Hymn 1", "Hymn 2"} & returned


def test_without_exclusion_recent_hymns_may_appear_with_their_date(client, church, fetched):
    hymnal(church, n=3)
    use(church, "Hymn 1", "2026-09-27")
    install()
    body = suggest(client, church, {"exclude_recent": False, "scriptures": ["Psalm 23"]})
    recent = {h["title"]: h["recent_use_on"] for items in body["slots"].values() for h in items}
    assert recent["Hymn 1"] == "2026-09-27" and body["excluded_recent_count"] == 0


def test_empty_pool_and_everything_recent_are_422(client, church, make_church, fetched):
    install()
    error = suggest(client, church, status=422)["error"]
    assert (error["message"], error["fields"]) == (
        "This hymnal has no hymns to suggest from.", {"hymnal": "This hymnal has no hymns to suggest from."})
    add(church, "   ", 1)                                            # blank titles never count
    assert suggest(client, church, status=422)["error"]["message"] == "This hymnal has no hymns to suggest from."
    add(church, "Only", 2)
    use(church, "Only", "2026-09-27")
    error = suggest(client, church, status=422)["error"]
    assert error["message"] == ("Every hymn in this hymnal was used within 12 weeks of this service. "
                                "Turn off “Exclude” and try again.")
    assert "fields" not in error
    for code in ("NOWHERE", ""):
        error = suggest(client, church, {"hymnal": code}, status=422)["error"]
        assert error["fields"] == {"hymnal": "That hymnal isn't in this church's library."}


def test_body_limits_and_extra_fields_are_422(client, church, fetched):
    hymnal(church, n=3)
    install()
    for body in ({"surprise": 1}, {"occasion": "o" * 301}, {"scriptures": ["x" * 201]},
                 {"scriptures": ["John 3"] * 21}, {"nt_text": "t" * 20_001},
                 {"current_picks": {"offertory": None}}, {"service_date_iso": "2026-10-4"}):
        error = suggest(client, church, body, status=422)["error"]
        assert (error["code"], error["message"]) == ("invalid_request", "The request was not valid."), body
    r = client.post("/hymns/suggestions", json={}, headers=church_headers(EMAIL, church))
    assert r.json()["error"]["fields"] == {"service_date_iso": "Required."}


def test_the_rubric_is_read_fresh_and_a_bad_one_falls_back(client, church, fetched):
    hymnal(church, n=5)
    fake = install()
    suggest(client, church)
    assert "A good Closing (Sending) Hymn:\n- is joyful and upbeat" in prompt_of(fake)
    churches.update_church_rubric(church, {"hymns": {"closing": ["ends with a rousing doxology"]},
                                           "prefer_before_year": 1900})
    suggest(client, church)
    assert "A good Closing (Sending) Hymn:\n- ends with a rousing doxology" in prompt_of(fake)
    assert "Prefer hymns written before 1900" in prompt_of(fake)
    stored = churches.get_church(church)["settings"]
    churches.update_church(church, settings={**stored, "rubric": {"prefer_before_year": "x"}})
    suggest(client, church)
    assert "Prefer hymns written before 1970" in prompt_of(fake)


def test_isolation_roles_and_another_churchs_ids(client, isolation_world, make_user, fetched):
    world = isolation_world
    for i in range(1, 6):
        add(world.church_a, f"A {i}", i, theme="joy", refs="Psalm 23")
    b_id = add(world.church_b, "B's secret hymn", 1, theme="joy", refs="Psalm 23", hymnal="BONLY")
    churches.update_church_rubric(world.church_b, {"hymns": {"closing": ["B's own checklist"]}})
    fake = install()
    assert_church_isolated(client, "POST", "/hymns/suggestions", world=world,
                           json={"service_date_iso": DATE})
    body = suggest(client, world.church_a, {"current_picks": {"opening": b_id}}, email=world.a)
    everything = json.dumps(body) + prompt_of(fake)
    assert b_id not in everything and "B's secret hymn" not in everything
    assert "B's own checklist" not in prompt_of(fake)
    assert suggest(client, world.church_a, {"hymnal": "BONLY"}, email=world.a, status=422)["error"][
        "message"] == "That hymnal isn't in this church's library."
    use(world.church_b, "A 1", "2026-09-27")                      # B's usage never marks A's hymns
    body = suggest(client, world.church_a, email=world.a)
    assert body["excluded_recent_count"] == 0
    for role in ("admin", "member"):
        email = f"{role}@example.com"
        add_membership(make_user(email=email), world.church_a, role)
        suggest(client, world.church_a, email=email)


def test_the_41st_call_by_a_user_in_ten_minutes_is_429(client, church, owner, fetched, limiter_clock):
    hymnal(church, n=3)
    install()
    for _ in range(40):
        ratelimit.consume("ai", user_id=owner, church_id=church)
    r = client.post("/hymns/suggestions", json={"service_date_iso": DATE}, headers=church_headers(EMAIL, church))
    assert r.status_code == 429, r.text
    assert r.json()["error"]["code"] == "rate_limited"
    assert r.headers["Retry-After"] == "15"                      # 40 per 600 s: one token every 15 s
    limiter_clock.advance(15)
    assert suggest(client, church)["hymnal"] == "GG2013"


def test_the_401st_call_by_a_church_in_a_day_is_429(client, church, make_user, make_church, fetched,
                                                     limiter_clock):
    hymnal(church, n=3)
    install()
    for _ in range(399):
        ratelimit.consume("ai", user_id=uuid.uuid4(), church_id=church)
    assert suggest(client, church)["hymnal"] == "GG2013"         # the church's 400th today
    r = client.post("/hymns/suggestions", json={"service_date_iso": DATE}, headers=church_headers(EMAIL, church))
    assert r.status_code == 429, r.text
    other = make_church(name="Other", owner_user_id=make_user(email="other@example.com"))
    hymnal(other, n=3)
    assert suggest(client, other, email="other@example.com")["hymnal"] == "GG2013"


def test_a_rejected_request_still_spends_a_token(client, church, owner, fetched, limiter_clock):
    # F §1.8: rate_limit("ai") is a dependency, resolved before the body is validated
    # and before the usecase runs, so both kinds of 422 cost a token (plan, "Buckets").
    hymnal(church, n=3)
    fake = install()
    for _ in range(38):
        ratelimit.consume("ai", user_id=owner, church_id=church)
    suggest(client, church, {"extra": 1}, status=422)              # Pydantic: the 39th token
    suggest(client, church, {"hymnal": "NOWHERE"}, status=422)     # the usecase: the 40th
    r = client.post("/hymns/suggestions", json={"service_date_iso": DATE}, headers=church_headers(EMAIL, church))
    assert r.status_code == 429, r.text
    assert fake.calls == []
