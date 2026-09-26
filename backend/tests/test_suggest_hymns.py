import json
from types import SimpleNamespace

import pytest

import worship_service
from service_rubric import default_rubric


class FakeOpenAI:
    """Stands in for openai.OpenAI: records each request and returns `reply`."""

    def __init__(self, reply):
        self.reply = reply
        self.requests = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.requests.append(kwargs)
        message = SimpleNamespace(content=self.reply)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def hymn(title, number, theme, year=None, count=None):
    return {"id": title, "Hymn Title": title, "Hymn Number": number, "Theme": theme,
            "Scripture References": "Isaiah 6:3", "Hymnary.org Link": None,
            "Text Year": year, "Hymnal Count": count}


HYMNS = [
    hymn("Newer Gathering Song", 1, "gathering", 1995, 40),
    hymn("Holy, Holy, Holy", 2, "gathering, praise", 1826, 1322),
    hymn("Go Forth Rejoicing", 3, "sending, joy", 1985, 20),
    hymn("Rejoice, the Lord Is King", 4, "joy, praise", 1744, 900),
]


@pytest.fixture
def fake(monkeypatch):
    reply = json.dumps({"opening": ["Holy, Holy, Holy"], "response": ["Holy, Holy, Holy"],
                        "closing": ["Go Forth Rejoicing", "Rejoice, the Lord Is King"]})
    client = FakeOpenAI(reply)
    monkeypatch.setattr(worship_service, "OpenAI", lambda api_key: client)
    return client


def suggest(**kwargs):
    return worship_service.suggest_hymns_for_service(
        db=None, occasion="Trinity Sunday", scriptures=["Isaiah 6:1-8"],
        api_key="test-key", all_hymns=HYMNS, **kwargs,
    )


def prompt_of(fake):
    return fake.requests[0]["messages"][0]["content"]


def test_prompt_uses_the_default_slot_checklists_and_preferences(fake):
    suggest()
    prompt = prompt_of(fake)
    assert "A good Closing (Sending) Hymn:\n- is joyful and upbeat" in prompt
    assert "- sends people out to serve others and share God's love" in prompt
    assert "A good Opening (Gathering) Hymn:" in prompt
    assert "Must be joyful, upbeat, or sending" not in prompt   # old hard-coded roles are gone
    assert ("Prefer hymns written before 1970 and hymns found in many hymnals; "
            "choose a newer hymn only when it fits clearly better.") in prompt


def test_candidates_show_facts_and_rank_older_familiar_first(fake):
    suggest()
    prompt = prompt_of(fake)
    assert "Holy, Holy, Holy (#2) (written 1826, in 1,322 hymnals)" in prompt
    opening = prompt.split("OPENING CANDIDATES")[1].split("RESPONSE CANDIDATES")[0]
    assert opening.index("Holy, Holy, Holy") < opening.index("Newer Gathering Song")


def test_a_church_rubric_changes_the_prompt(fake):
    rubric = default_rubric()
    rubric["hymns"]["closing"] = ["ends with a rousing doxology"]
    rubric["prefer_before_year"] = 1900
    rubric["prefer_familiar"] = False
    suggest(rubric=rubric)
    prompt = prompt_of(fake)
    assert "A good Closing (Sending) Hymn:\n- ends with a rousing doxology" in prompt
    assert "is joyful and upbeat" not in prompt
    assert "Prefer hymns written before 1900; choose a newer hymn" in prompt
    assert "hymns found in many hymnals" not in prompt


def test_results_carry_year_and_newer_flag(fake):
    result = suggest()
    closing = {info["title"]: info for info in result["closing"]}
    assert closing["Go Forth Rejoicing"]["year"] == 1985
    assert closing["Go Forth Rejoicing"]["newer_than_preferred"] is True
    assert closing["Rejoice, the Lord Is King"]["newer_than_preferred"] is False
    assert closing["Rejoice, the Lord Is King"]["hymnal_count"] == 900


def test_hymn_display_info_without_a_preference_never_flags():
    info = worship_service.hymn_display_info(HYMNS[0])
    assert info["year"] == 1995
    assert info["newer_than_preferred"] is False
