"""PR #4's liturgy tests (the rubric checklist and the sermon text), retargeted
from worship_service.generate_liturgy to liturgy_prompts.build_context /
build_messages and usecases.liturgy before that function was deleted (slice 4
spec, Testing amendment "Characterization (PR #4)"; AC19). Each case keeps its
assertion."""
import uuid

import pytest

import liturgy_prompts
from integrations.openai_client import FakeAI
from service_rubric import default_rubric
from usecases import liturgy

SLOTS = {"opening": liturgy_prompts.ResolvedHymn("Holy, Holy, Holy", 138)}


def generate(sections, *, rubric=None, prompt_overrides=None, sermon_text=None):
    """The messages each section would send, as generate_liturgy's fake client recorded them."""
    ref, text = sermon_text or (None, None)
    ctx = liturgy_prompts.build_context(
        occasion="Third Sunday of Easter", scriptures=["Acts 9:1-6", "John 21:1-19"],
        hymns_by_slot=SLOTS, rubric=rubric, sermon_ref=ref, sermon_text=text)
    prompts = liturgy_prompts.merge_prompts(prompt_overrides)
    return [liturgy_prompts.build_messages(section, prompts, ctx) for section in sections]


def user_message(messages):
    return messages[1]["content"]


def test_each_section_gets_its_default_checklist():
    benediction, confession = generate(["benediction", "prayer_of_confession"])
    assert "A good Benediction:\n- speaks a blessing to the people" in user_message(benediction)
    assert "A good Prayer of Confession:\n- names real, specific failings that are common to all people" in \
        user_message(confession)
    assert benediction[0]["content"] == liturgy_prompts.DEFAULT_SYSTEM_PROMPT


def test_a_church_rubric_replaces_the_checklist():
    rubric = default_rubric()
    rubric["prayers"]["benediction"] = ["ends with the Aaronic blessing"]
    (messages,) = generate(["benediction"], rubric=rubric)
    text = user_message(messages)
    assert "A good Benediction:\n- ends with the Aaronic blessing" in text
    assert "speaks a blessing to the people" not in text


@pytest.mark.parametrize("rubric", [{}, {"hymns": {"closing": ["Joyful."]}}])
def test_a_partial_rubric_falls_back_to_the_defaults(rubric):
    # A church's sparse overrides ({} when nothing is customized) are filled in
    # from the defaults rather than raising KeyError.
    (messages,) = generate(["benediction"], rubric=rubric)
    assert "A good Benediction:\n- speaks a blessing to the people" in user_message(messages)


def test_edited_prompts_still_get_the_checklist():
    (messages,) = generate(["benediction"], prompt_overrides={"benediction": "My own benediction instruction."})
    text = user_message(messages)
    assert text.startswith("My own benediction instruction.")
    assert "A good Benediction:" in text


def test_sermon_text_is_appended_for_themes_only():
    (messages,) = generate(["prayer_of_confession"],
                           sermon_text=("John 21:1-19", "Simon Peter said, I am going fishing."))
    assert ("Sermon text (John 21:1-19), for themes only; do not quote, cite, or name it:\n"
            "Simon Peter said, I am going fishing.") in user_message(messages)


def test_sermon_text_is_truncated():
    (messages,) = generate(["benediction"], sermon_text=("John 21:1-19", "x" * 5000))
    text = user_message(messages)
    assert "x" * liturgy_prompts.SERMON_TEXT_LIMIT in text
    assert "x" * (liturgy_prompts.SERMON_TEXT_LIMIT + 1) not in text


@pytest.mark.parametrize("sermon_text", [
    None, ("John 21:1-19", "[Could not load text]"), ("John 21:1-19", "  "), ("", "Some text."),
])
def test_missing_or_failed_sermon_text_is_skipped(sermon_text):
    (messages,) = generate(["benediction"], sermon_text=sermon_text)
    assert "Sermon text" not in user_message(messages)


def test_user_written_sections_are_not_sent_to_the_ai(make_church):
    ai = FakeAI(reply="Draft.")
    outcomes = liturgy.generate_liturgy(
        church_id=make_church(), user_id=uuid.uuid4(), occasion="Third Sunday of Easter",
        scriptures=["Acts 9:1-6"], hymns={}, sections=["benediction"],
        overrides={"benediction": "Go in peace."}, sermon=("John 21:1-19", "Simon Peter said."), ai=ai)
    assert [(o.section, o.status, o.text) for o in outcomes] == [("benediction", "override", "Go in peace.")]
    assert ai.calls == []
