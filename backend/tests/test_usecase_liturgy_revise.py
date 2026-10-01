"""usecases.liturgy_review.revise_section (reviewer spec, "Revise" and its
Budget, Testing; slice 4 spec, reviewer amendment "Revise input budget").
SQLite `tmp_db`, and a FakeAI passed as `ai=`."""
import logging
import uuid

import pytest

import liturgy_prompts as lp
from domain_errors import Busy, DomainError, InvalidInput, NotConfigured, UpstreamError, UpstreamTimeout
from integrations.openai_client import FakeAI
from repos import churches
from usecases import liturgy_review

SECRET = "sk-secret upstream detail"
NOTES = ['Stock phrase "as we journey". Say it more naturally.', "The second line is hard to say aloud."]
INSTRUCTION = ("Revise this draft to address these notes only. Keep everything that works. Keep the same form "
               "(Leader/People lines where present) and about the same length. Output only the revised text.")


@pytest.fixture
def church(make_church):
    return make_church(name="Grace")


def set_settings(church_id, **values):
    settings = dict(churches.get_church(church_id)["settings"] or {})
    settings.update(values)
    churches.update_church(church_id, settings=settings)


def revise(church_id, section="opening_prayer", text="Gracious God, as we journey, hear us. Amen.", notes=NOTES,
           ai=None, **kw):
    kw.setdefault("occasion", "Third Sunday of Easter")
    kw.setdefault("scriptures", ["Acts 9:1-6", "John 21:1-19"])
    return liturgy_review.revise_section(church_id=church_id, user_id=uuid.uuid4(), section=section, text=text,
                                         notes=notes, ai=ai if ai is not None else FakeAI(reply=" Revised. "), **kw)


def test_the_messages_carry_the_draft_the_notes_and_the_section_s_checklist(church):
    churches.set_church_prompts(church, {"system": "Our voice."})
    set_settings(church, rubric={"prayers": {"opening_prayer": ["names one hope"]}},
                 prayer_library={"prayers": [], "voice_profile": " Plain and warm. "})
    ai = FakeAI(reply="  Gracious God, hear us. Amen.\n")
    text = revise(church, ai=ai, sermon=("Mark 4:35-41", "S" * 3000))
    assert text == "Gracious God, hear us. Amen."
    (call,) = ai.calls
    system, user = (m["content"] for m in call["messages"])
    assert system == "Our voice.\n\nWrite in the voice of this church's pastor, described here:\nPlain and warm."
    assert user == (
        "Section: Opening Prayer\n\n"
        "A good Opening Prayer:\n- names one hope\n\n"
        "Occasion: Third Sunday of Easter\n\n"
        "Readings:\n- Acts 9:1-6\n- John 21:1-19\n\n"
        "Sermon text (Mark 4:35-41), for themes only; do not quote, cite, or name it:\n" + "S" * 2000 + "\n\n"
        "Current draft:\nGracious God, as we journey, hear us. Amen.\n\n"
        "Notes:\n"
        '- Stock phrase "as we journey". Say it more naturally.\n'
        "- The second line is hard to say aloud.\n\n" + INSTRUCTION)
    assert call["json_mode"] is False
    # With the defaults (no prompts, rubric or profile saved) the system prompt is the default one.
    churches.set_church_prompts(church, {})
    set_settings(church, rubric={}, prayer_library={"prayers": [], "voice_profile": ""})
    revise(church, ai=ai)
    assert ai.calls[1]["messages"][0]["content"] == lp.DEFAULT_SYSTEM_PROMPT
    assert "A good Opening Prayer:\n- " in ai.calls[1]["messages"][1]["content"]


def test_each_section_gets_its_slice_4_token_budget_and_the_80_s_deadline(church):
    for section in lp.SECTION_ORDER:
        ai = FakeAI(reply="Revised.")
        revise(church, section=section, ai=ai, clock=lambda: 500.0)
        (call,) = ai.calls
        pop = section == "prayers_of_the_people"
        assert call["max_completion_tokens"] == (4000 if pop else 1500), section
        assert call["deadline"] == 580.0, section
        assert call.get("timeout_seconds") == (60.0 if pop else None), section


def test_ai_failures_raise_their_codes_with_this_app_s_messages(church, caplog):
    cases = [
        (FakeAI(available=False), "ai_not_configured", 503, "AI isn't set up on this app yet."),
        (FakeAI(error=NotConfigured(SECRET, code="ai_not_configured")), "ai_not_configured", 503,
         "AI isn't set up on this app yet."),
        (FakeAI(error=Busy(SECRET, code="ai_busy")), "ai_busy", 503, "The AI service is busy. Try again in a minute."),
        (FakeAI(error=UpstreamTimeout(SECRET, code="ai_timeout")), "ai_timeout", 504,
         "The AI took too long to answer. Try again."),
        (FakeAI(error=UpstreamError(SECRET, code="ai_upstream_error")), "ai_upstream_error", 502,
         "The AI service had a problem. Try again."),
        (FakeAI(error=RuntimeError(SECRET)), "ai_upstream_error", 502, "The AI service had a problem. Try again."),
        (FakeAI(reply="   "), "ai_upstream_error", 502, "The AI service had a problem. Try again."),
        (FakeAI(reply="x" * 20_001), "ai_upstream_error", 502, "The AI service had a problem. Try again."),
    ]
    for ai, code, status, message in cases:
        with pytest.raises(DomainError) as raised:
            revise(church, ai=ai)
        assert (raised.value.code, raised.value.status, raised.value.message) == (code, status, message), code
    assert "RuntimeError" in caplog.text and SECRET not in str(raised.value)
    assert revise(church, ai=FakeAI(reply="y" * 20_000)) == "y" * 20_000


def test_the_budget_drops_the_profile_then_the_sermon_then_the_checklist_then_refuses(church):
    churches.set_church_prompts(church, {"system": "s" * 8000})
    set_settings(church, rubric={"prayers": {"prayers_of_the_people": [f"{i:02d}" + "c" * 298 for i in range(12)]}},
                 prayer_library={"prayers": [], "voice_profile": "v" * 2000})
    sermon = ("Mark 4:35-41", "x" * 2000)
    # 8 000 system + 2 000 profile + about 3 700 checklist + 2 000 sermon + the draft: each case's draft
    # length leaves the prompt over the cap until the named blocks are gone.
    cases = [(6_000, ()), (8_000, ("profile",)), (10_000, ("profile", "sermon")),
             (13_000, ("profile", "sermon", "checklist"))]
    for draft_chars, dropped in cases:
        ai = FakeAI(reply="Revised.")
        revise(church, section="prayers_of_the_people", text="d" * draft_chars, ai=ai, sermon=sermon)
        system, user = (m["content"] for m in ai.calls[0]["messages"])
        assert len(system) + len(user) <= lp.MAX_PROMPT_CHARS, dropped
        assert ("v" * 2000 in system) is ("profile" not in dropped), dropped
        assert ("Sermon text (Mark 4:35-41)" in user) is ("sermon" not in dropped), dropped
        assert ("A good Prayers of the People:" in user) is ("checklist" not in dropped), dropped
        assert "d" * draft_chars in user and user.endswith(INSTRUCTION)
    # S4's example: an 8 000-character system prompt and a 20 000-character draft never reach the AI.
    ai = FakeAI(reply="Revised.")
    with pytest.raises(InvalidInput) as raised:
        revise(church, section="prayers_of_the_people", text="d" * 20_000, ai=ai, sermon=sermon)
    assert (raised.value.code, raised.value.status, raised.value.message) == (
        "prompt_invalid", 422, "This prayer is too long to revise.")
    assert ai.calls == []


def test_the_info_line_carries_no_prayer_text_or_notes(church, caplog):
    with caplog.at_level(logging.INFO, logger="usecases.liturgy_review"):
        revise(church, text="SECRET-TEXT", notes=["SECRET-NOTE"], ai=FakeAI(reply="SECRET-ANSWER"),
               occasion="SECRET-OCCASION")
    info = "\n".join(r.getMessage() for r in caplog.records if r.levelno >= logging.INFO)
    assert "liturgy.revise" in info and " section=opening_prayer notes=1 " in info and "outcome=ok" in info
    assert "SECRET" not in info
