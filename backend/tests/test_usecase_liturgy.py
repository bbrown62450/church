"""usecases.liturgy.generate_liturgy (slice 4 spec, Backend 3 and its 2026-09-26
amendment; Testing `test_usecase_liturgy.py`; API semantics 1-10; AC3-AC6,
AC8, AC10, AC19, AC21). SQLite `tmp_db`, and a FakeAI passed as `ai=`."""
import logging
import threading
import uuid

import pytest

import liturgy_prompts as lp
from db import get_engine, session_scope
from db.models import Hymn
from domain_errors import Busy, NotConfigured, NotFound, RateLimited, UpstreamError, UpstreamTimeout
from integrations.openai_client import FakeAI
from repos import churches
from repos import hymns as hymn_repo
from usecases import liturgy
from usecases.liturgy import HymnRefData

SECRET = "sk-secret upstream detail"


@pytest.fixture
def church(make_church):
    return make_church(name="Grace")


def add_hymn(church_id, title, number, hymnal="GG2013"):
    with session_scope() as s:
        row = Hymn(church_id=church_id, hymnal=hymnal, title=title, number=number)
        s.add(row)
        s.flush()
        return row.id


def run(church_id, sections, *, overrides=None, hymns=None, ai=None, **kw):
    return liturgy.generate_liturgy(
        church_id=church_id, user_id=uuid.uuid4(), occasion="Third Sunday of Easter",
        scriptures=["Acts 9:1-6", "John 21:1-19"], hymns=hymns or {}, sections=sections,
        overrides=overrides or {}, ai=ai if ai is not None else FakeAI(reply="  A draft.  "), **kw)


def by_section(outcomes):
    return {o.section: o for o in outcomes}


def user_message(call):
    return call["messages"][1]["content"]


def set_settings(church_id, **values):
    settings = dict(churches.get_church(church_id)["settings"] or {})
    settings.update(values)
    churches.update_church(church_id, settings=settings)


def test_without_ai_an_override_is_verbatim_and_the_rest_not_configured(church):
    """F acceptance 15; semantics 3 and 5."""
    ai = FakeAI(available=False)
    charged = []
    outcomes = run(church, ["call_to_worship", "benediction"], overrides={"benediction": "  Go in peace.  "},
                   ai=ai, charge=charged.append)
    assert outcomes == [
        liturgy.SectionOutcome("call_to_worship", "error", None, "ai_not_configured",
                               "AI not configured. Type this section yourself."),
        liturgy.SectionOutcome("benediction", "override", "  Go in peace.  ", None, None),
    ]
    assert ai.calls == [] and charged == []


def test_answers_are_stripped_and_the_church_s_prompts_are_read_fresh(church):
    churches.set_church_prompts(church, {"system": "First voice.", "benediction": "Bless {occasion}."})
    ai = FakeAI(reply="  Go now in peace.\n")
    (outcome,) = run(church, ["benediction"], ai=ai, clock=lambda: 1000.0)
    assert (outcome.status, outcome.text) == ("generated", "Go now in peace.")
    assert ai.calls[0]["messages"][0]["content"] == "First voice."
    assert user_message(ai.calls[0]).startswith("Bless Third Sunday of Easter.")
    assert ai.calls[0]["max_completion_tokens"] == 1500
    assert ai.calls[0]["deadline"] == 1080.0            # F §1.8: 80 s from the start of the usecase
    churches.set_church_prompts(church, {"system": "Second voice."})
    run(church, ["benediction"], ai=ai)
    assert ai.calls[1]["messages"][0]["content"] == "Second voice."
    assert user_message(ai.calls[1]).startswith(lp.render(lp.DEFAULT_SECTION_PROMPTS["benediction"],
                                                          occasion="Third Sunday of Easter",
                                                          scriptures="- Acts 9:1-6\n- John 21:1-19"))


def test_ai_failures_map_to_their_codes_and_never_leak(church, caplog):
    cases = [
        (FakeAI(error=UpstreamTimeout(SECRET, code="ai_timeout")), "ai_timeout",
         "The AI took too long to answer. Try again."),
        (FakeAI(error=Busy(SECRET, code="ai_busy")), "ai_busy", "The AI service is busy. Try again in a minute."),
        (FakeAI(error=UpstreamError(SECRET, code="ai_upstream_error")), "ai_upstream_error",
         "The AI service had a problem. Try again."),
        (FakeAI(error=NotConfigured(SECRET, code="ai_not_configured")), "ai_not_configured",
         "AI not configured. Type this section yourself."),
        (FakeAI(error=RuntimeError(SECRET)), "ai_upstream_error", "The AI service had a problem. Try again."),
        (FakeAI(reply="   "), "ai_upstream_error", "The AI service had a problem. Try again."),
        (FakeAI(reply="x" * 20_001), "ai_upstream_error", "The AI service had a problem. Try again."),
    ]
    for ai, code, message in cases:
        (outcome,) = run(church, ["opening_prayer"], ai=ai)
        assert (outcome.status, outcome.text, outcome.error_code, outcome.error_message) == (
            "error", None, code, message), code
        assert "secret" not in repr(outcome)
    assert "RuntimeError" in caplog.text                  # the unexpected one is logged with its stack
    (ok,) = run(church, ["opening_prayer"], ai=FakeAI(reply="y" * 20_000))
    assert ok.status == "generated"


def test_a_malformed_template_fails_only_its_own_section(church, caplog):
    churches.set_church_prompts(church, {"call_to_worship": '{"a": 1}'})
    set_settings(church, prayer_library={"prayers": [{"type": "call_to_worship", "text": "Come, all."}]})
    ai = FakeAI(reply="Draft.")
    with caplog.at_level(logging.INFO, logger="usecases.liturgy"):
        outcomes = by_section(run(church, ["call_to_worship", "opening_prayer"], ai=ai))
    assert outcomes["call_to_worship"].error_message == (
        "The Call to Worship prompt in Settings has a problem: Placeholders must be a single word such as "
        "{occasion}. To print a { or } as text, write {{ or }}. An admin can fix it under Settings → "
        "Liturgy prompts.")
    assert outcomes["call_to_worship"].error_code == "prompt_invalid"
    assert outcomes["opening_prayer"].status == "generated" and len(ai.calls) == 1
    # The Call to Worship example never reached the AI, so the log names none.
    assert " ai=1 " in caplog.text and " voice=none " in caplog.text


def test_the_length_cap_is_the_same_prompt_invalid_message(church):
    # A 20 000-character system prompt is possible only from unvalidated Streamlit writes.
    churches.set_church_prompts(church, {"system": "s" * 20_000})
    (outcome,) = liturgy.generate_liturgy(
        church_id=church, user_id=uuid.uuid4(), occasion="Easter", hymns={}, overrides={},
        scriptures=[f"{i:02d}" + "r" * 198 for i in range(20)], sections=["benediction"],
        ai=FakeAI(reply="Draft."))
    assert (outcome.error_code, outcome.error_message) == (
        "prompt_invalid",
        "The Benediction prompt in Settings has a problem: It is too long once the readings, hymns and "
        "rubric checklist are added. An admin can fix it under Settings → Liturgy prompts.")


def test_hymns_resolve_within_the_church(church, make_church):
    mine = add_hymn(church, "Holy, Holy, Holy", 138)
    theirs = add_hymn(make_church(name="Other"), "Not Mine", 2)
    ai = FakeAI(reply="Draft.")
    run(church, ["prayers_of_the_people"], ai=ai, hymns={
        "opening": HymnRefData(hymn_id=mine, title="What the client says", number=999),
        "response": None,
        "closing": HymnRefData(hymn_id=None, title="An Archived Hymn", number=None),
    })
    user = user_message(ai.calls[0])
    assert "- Holy, Holy, Holy (#138)\n- An Archived Hymn" in user and "What the client" not in user
    for bad in (theirs, uuid.uuid4(), "not-a-uuid"):
        with pytest.raises(NotFound) as raised:
            run(church, ["benediction"], overrides={"benediction": "Go."},
                hymns={"opening": HymnRefData(hymn_id=bad, title="x", number=1)})
        assert raised.value.message == "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step."


def test_the_ai_bucket_is_charged_once_for_the_sections_that_reach_the_ai(church):
    events = []
    ai = FakeAI(reply=lambda messages: events.append("complete") or "Draft.")

    def charge(n):
        events.append(("charge", n))

    run(church, ["call_to_worship", "benediction"], ai=ai, charge=charge)
    assert events == [("charge", 2), "complete", "complete"]
    cases = [
        ({"call_to_worship": '{"a": 1}'}, ["call_to_worship", "benediction"], {}, [1]),
        ({"call_to_worship": '{"a": 1}'}, ["call_to_worship"], {}, []),
        ({}, ["benediction"], {"benediction": "Go."}, []),
    ]
    for stored, sections, overrides, expected in cases:
        churches.set_church_prompts(church, stored)
        charged = []
        run(church, sections, overrides=overrides, ai=FakeAI(reply="Draft."), charge=charged.append)
        assert charged == expected, (stored, sections)
    charged = []
    run(church, ["benediction"], ai=FakeAI(available=False), charge=charged.append)
    with pytest.raises(NotFound):
        run(church, ["benediction"], charge=charged.append,
            hymns={"opening": HymnRefData(hymn_id=uuid.uuid4(), title="x", number=1)})
    assert charged == []


def test_a_charge_that_raises_stops_every_ai_call(church, caplog):
    ai = FakeAI(reply="Draft.")

    def charge(n):
        raise RateLimited("Too many requests. Try again in 15 seconds.", retry_after_seconds=15)

    with caplog.at_level(logging.INFO, logger="usecases.liturgy"), pytest.raises(RateLimited):
        run(church, ["call_to_worship", "benediction"], ai=ai, charge=charge)
    assert ai.calls == []
    assert " ai=0 " in caplog.text and "outcome=rate_limited" in caplog.text     # no AI call was made


def test_request_order_after_dedupe_with_four_sections_at_a_time(church):
    barrier = threading.Barrier(4, timeout=5)
    running, peak, lock = [0], [0], threading.Lock()

    def reply(messages):
        with lock:
            running[0] += 1
            peak[0] = max(peak[0], running[0])
        barrier.wait()                                   # all four are in complete() together
        with lock:
            running[0] -= 1
        return "Draft of " + messages[1]["content"][:20]

    sections = ["benediction", "assurance", "benediction", "call_to_worship", "offertory_prayer"]
    outcomes = run(church, sections, ai=FakeAI(reply=reply))
    assert [o.section for o in outcomes] == ["benediction", "assurance", "call_to_worship", "offertory_prayer"]
    assert all(o.status == "generated" for o in outcomes) and peak[0] == 4


def test_one_session_reads_everything_and_none_is_open_during_an_ai_call(church, monkeypatch):
    real = liturgy.session_scope
    state = {"opened": 0, "open": 0, "during_ai": []}

    class Counting:
        def __enter__(self):
            state["opened"] += 1
            state["open"] += 1
            self.inner = real()
            return self.inner.__enter__()

        def __exit__(self, *exc):
            state["open"] -= 1
            return self.inner.__exit__(*exc)

    set_settings(church, rubric={"prayers": {"benediction": ["is short"]}},
                 prayer_library={"prayers": [{"type": "benediction", "text": "Go gently."}]})
    churches.set_church_prompts(church, {"system": "Our voice."})
    hymn = add_hymn(church, "Holy, Holy, Holy", 138)
    # Counted in the usecase and in both repos it reads through, so a repo that
    # opened a session of its own would show as a second one.
    for module in (liturgy, churches, hymn_repo):
        monkeypatch.setattr(module, "session_scope", Counting)
    pool = get_engine().pool

    def reply(messages):
        state["during_ai"].append((state["open"], pool.checkedout()))
        return "Draft."

    ai = FakeAI(reply=reply)
    run(church, ["benediction", "assurance"], ai=ai,
        hymns={"opening": HymnRefData(hymn_id=hymn, title="x", number=1)})
    # One session in all; during each AI call no session is open and no
    # connection is checked out of the pool, whoever opened it.
    assert state["opened"] == 1 and state["during_ai"] == [(0, 0), (0, 0)]
    benediction = next(c for c in ai.calls if "Benediction" in user_message(c))
    assert benediction["messages"][0]["content"] == "Our voice."
    assert "A good Benediction:\n- is short" in user_message(benediction)
    assert user_message(benediction).endswith("Do not reuse its lines or phrases:\nGo gently.")


def test_the_rubric_is_read_fresh_per_church_and_a_bad_one_falls_back(church, make_church):
    other = make_church(name="Other")
    set_settings(other, rubric={"prayers": {"benediction": ["mentions the harbor"]}})
    ai = FakeAI(reply="Draft.")
    set_settings(church, rubric={"prayers": {"benediction": ["ends with the Aaronic blessing"]}})
    run(church, ["benediction"], ai=ai)
    set_settings(church, rubric={"prayers": {"benediction": ["is one sentence"]}})
    run(church, ["benediction"], ai=ai)
    set_settings(church, rubric={"prayers": {"benediction": "not a list"}})
    run(church, ["benediction"], ai=ai)
    first, second, fallback = (user_message(c) for c in ai.calls)
    assert "A good Benediction:\n- ends with the Aaronic blessing" in first
    assert "A good Benediction:\n- is one sentence" in second and "Aaronic" not in second
    assert "A good Benediction:\n- speaks a blessing to the people" in fallback
    assert not any("harbor" in user_message(c) for c in ai.calls)


def test_the_library_is_read_fresh_and_an_empty_one_changes_nothing(church):
    ai = FakeAI(reply="Draft.")
    run(church, ["prayer_of_confession"], ai=ai)
    set_settings(church, prayer_library={"prayers": [], "voice_profile": "   "})
    run(church, ["prayer_of_confession"], ai=ai)
    set_settings(church, prayer_library={"voice_profile": "Plain and warm.", "prayers": [
        {"type": "prayer_of_confession", "text": "Merciful God, {we} confess."},
        {"type": "prayer_of_confession", "text": "Holy One, we have wandered."},
        {"type": "other", "text": "A wedding prayer."}]})
    run(church, ["prayer_of_confession"], ai=ai, choose=lambda texts: texts[-1])
    baseline, empty, voiced = (c["messages"] for c in ai.calls)
    assert empty == baseline
    assert voiced[0]["content"] == baseline[0]["content"] + (
        "\n\nWrite in the voice of this church's pastor, described here:\nPlain and warm.")
    assert voiced[1]["content"] == baseline[1]["content"] + (
        "\n\nFor voice only, here is a Prayer of Confession this pastor wrote. Do not reuse its lines or "
        "phrases:\nHoly One, we have wandered.")


def test_the_sermon_goes_to_every_ai_section_and_no_override(church):
    ai = FakeAI(reply="Draft.")
    outcomes = run(church, ["call_to_worship", "benediction", "assurance"], ai=ai,
                   overrides={"assurance": "Leader: In Christ we are forgiven."},
                   sermon=("Mark 4:35-41", "He said to the sea, Peace! Be still!"))
    block = "Sermon text (Mark 4:35-41), for themes only; do not quote, cite, or name it:\nHe said to the sea"
    assert len(ai.calls) == 2 and all(block in user_message(c) for c in ai.calls)
    assert by_section(outcomes)["assurance"].text == "Leader: In Christ we are forgiven."


def test_the_worst_case_prayers_of_the_people_fits_and_gets_4000_tokens(church):
    """PR #7 §Privacy; index open item 18."""
    set_settings(church,
                 rubric={"prayers": {"prayers_of_the_people": ["p" * 300] * 12}},
                 prayer_library={"voice_profile": "v" * 2000,
                                 "prayers": [{"type": "prayers_of_the_people", "text": "e" * 6000}]})
    ai = FakeAI(reply="Draft.")
    (outcome,) = run(church, ["prayers_of_the_people"], ai=ai, sermon=("Mark 4:35-41", "x" * 20_000),
                     hymns={slot: HymnRefData(hymn_id=None, title="h" * 300, number=100)
                            for slot in ("opening", "response", "closing")})
    (call,) = ai.calls
    assert outcome.status == "generated" and call["max_completion_tokens"] == 4000
    assert sum(len(m["content"]) for m in call["messages"]) <= lp.MAX_PROMPT_CHARS
    assert "e" * 3000 in user_message(call) and "e" * 3001 not in user_message(call)
    assert call["messages"][0]["content"].endswith("v" * 2000)


def test_prayers_of_the_people_gets_60_second_attempts_inside_the_deadline(church):
    """S Risks 1: 60 s per attempt; the 80 s deadline decides whether a retry fits."""
    ai = FakeAI(reply="Draft.")
    run(church, ["prayers_of_the_people", "benediction"], ai=ai, clock=lambda: 1000.0)
    calls = {("Prayers of the People" in user_message(c)): c for c in ai.calls}
    assert (calls[True]["timeout_seconds"], calls[True]["deadline"]) == (60.0, 1080.0)
    assert "timeout_seconds" not in calls[False] and calls[False]["deadline"] == 1080.0
