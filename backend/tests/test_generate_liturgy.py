from types import SimpleNamespace

import pytest

import liturgy_prompts
import worship_service
from service_rubric import default_rubric


class FakeOpenAI:
    """Stands in for openai.OpenAI: records each request and returns a fixed text."""

    def __init__(self):
        self.requests = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.requests.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="Draft."))])


@pytest.fixture
def fake(monkeypatch):
    client = FakeOpenAI()
    monkeypatch.setattr(worship_service, "OpenAI", lambda api_key: client)
    return client


def generate(sections, **kwargs):
    return worship_service.generate_liturgy(
        occasion="Third Sunday of Easter", scriptures=["Acts 9:1-6", "John 21:1-19"],
        hymns=[{"title": "Holy, Holy, Holy", "number": 138}], sections=sections,
        api_key="test-key", **kwargs,
    )


def user_message(request):
    return request["messages"][1]["content"]


def test_each_section_gets_its_default_checklist(fake):
    out = generate(["benediction", "prayer_of_confession"])
    assert out == {"benediction": "Draft.", "prayer_of_confession": "Draft."}
    benediction, confession = (user_message(r) for r in fake.requests)
    assert "A good Benediction:\n- speaks a blessing to the people" in benediction
    assert "A good Prayer of Confession:\n- names real, specific failings that are common to all people" in confession
    assert fake.requests[0]["messages"][0]["content"] == liturgy_prompts.DEFAULT_SYSTEM_PROMPT


def test_a_church_rubric_replaces_the_checklist(fake):
    rubric = default_rubric()
    rubric["prayers"]["benediction"] = ["ends with the Aaronic blessing"]
    generate(["benediction"], rubric=rubric)
    text = user_message(fake.requests[0])
    assert "A good Benediction:\n- ends with the Aaronic blessing" in text
    assert "speaks a blessing to the people" not in text


def test_edited_prompts_still_get_the_checklist(fake):
    generate(["benediction"], prompt_overrides={"benediction": "My own benediction instruction."})
    text = user_message(fake.requests[0])
    assert text.startswith("My own benediction instruction.")
    assert "A good Benediction:" in text


def test_sermon_text_is_appended_for_themes_only(fake):
    generate(["prayer_of_confession"], sermon_text=("John 21:1-19", "Simon Peter said, I am going fishing."))
    text = user_message(fake.requests[0])
    assert ("Sermon text (John 21:1-19), for themes only; do not quote, cite, or name it:\n"
            "Simon Peter said, I am going fishing.") in text


def test_sermon_text_is_truncated(fake):
    generate(["benediction"], sermon_text=("John 21:1-19", "x" * 5000))
    text = user_message(fake.requests[0])
    assert "x" * worship_service.SERMON_TEXT_LIMIT in text
    assert "x" * (worship_service.SERMON_TEXT_LIMIT + 1) not in text


@pytest.mark.parametrize("sermon_text", [
    None, ("John 21:1-19", "[Could not load text]"), ("John 21:1-19", "  "), ("", "Some text."),
])
def test_missing_or_failed_sermon_text_is_skipped(fake, sermon_text):
    generate(["benediction"], sermon_text=sermon_text)
    assert "Sermon text" not in user_message(fake.requests[0])


def test_user_written_sections_are_not_sent_to_the_ai(fake):
    out = generate(["benediction"], user_overrides={"benediction": "Go in peace."})
    assert out == {"benediction": "Go in peace."}
    assert fake.requests == []
