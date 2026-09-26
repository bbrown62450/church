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


_AFTER_SLOT = {"OPENING": "RESPONSE CANDIDATES", "RESPONSE": "CLOSING CANDIDATES",
               "CLOSING": "Respond with a JSON object"}


def candidates(prompt, slot):
    """The titles listed under one slot's CANDIDATES heading, in prompt order."""
    block = prompt.split(f"{slot} CANDIDATES")[1].split(_AFTER_SLOT[slot])[0]
    return [line[2:].split(" (#")[0] for line in block.splitlines() if line.startswith("- ")]


def prompt_for(fake, hymns, rubric):
    """The prompt sent for `hymns` under `rubric` (the latest request)."""
    worship_service.suggest_hymns_for_service(
        db=None, occasion="Trinity Sunday", scriptures=["Isaiah 6:1-8"],
        api_key="test-key", all_hymns=hymns, rubric=rubric,
    )
    return fake.requests[-1]["messages"][0]["content"]


def rubric_with(**settings):
    rubric = default_rubric()
    rubric.update(settings)
    return rubric


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


def test_candidate_headings_add_no_fixed_role_hints(fake):
    # The church's checklists alone say what each slot needs: a fixed hint such
    # as "prefer joyful/sending hymns" would contradict a quiet, reflective closing.
    rubric = default_rubric()
    rubric["hymns"]["closing"] = ["is quiet and reflective"]
    prompt = prompt_for(fake, HYMNS, rubric)
    headings = [line for line in prompt.splitlines() if "CANDIDATES" in line]
    assert headings == ["OPENING CANDIDATES:", "RESPONSE CANDIDATES:", "CLOSING CANDIDATES:"]
    assert "joyful" not in prompt


@pytest.mark.parametrize("rubric", [{}, {"prefer_before_year": 1900}])
def test_a_partial_rubric_falls_back_to_the_defaults(fake, rubric):
    # A church's sparse overrides ({} when nothing is customized) are filled in
    # from the defaults rather than raising KeyError.
    suggest(rubric=rubric)
    prompt = prompt_of(fake)
    assert "A good Closing (Sending) Hymn:\n- is joyful and upbeat" in prompt
    year = rubric.get("prefer_before_year", 1970)
    assert f"Prefer hymns written before {year} and hymns found in many hymnals" in prompt


def test_a_church_year_decides_which_hymns_rank_as_older(fake):
    # Same familiarity, so only the year can reorder them.
    hymns = [hymn("Gathering of 1920", 1, "gathering", 1920, 100),
             hymn("Gathering of 1880", 2, "gathering", 1880, 100)]
    both_older = prompt_for(fake, hymns, rubric_with(prefer_before_year=1970))
    assert candidates(both_older, "OPENING") == ["Gathering of 1920", "Gathering of 1880"]
    only_1880_older = prompt_for(fake, hymns, rubric_with(prefer_before_year=1900))
    assert candidates(only_1880_older, "OPENING") == ["Gathering of 1880", "Gathering of 1920"]


def test_turning_familiarity_off_keeps_the_given_order_within_an_era(fake):
    hymns = [hymn("Rare Gathering", 1, "gathering", 1850, 5),
             hymn("Common Gathering", 2, "gathering", 1850, 3000)]
    familiar = prompt_for(fake, hymns, rubric_with(prefer_familiar=True))
    assert candidates(familiar, "OPENING") == ["Common Gathering", "Rare Gathering"]
    not_familiar = prompt_for(fake, hymns, rubric_with(prefer_familiar=False))
    assert candidates(not_familiar, "OPENING") == ["Rare Gathering", "Common Gathering"]


def test_response_candidates_are_ranked_by_the_church_rubric(fake):
    # Every HYMNS entry cites Isaiah 6:3, so all four are scripture matches (a
    # reference keeps at most 30 matches, which this list stays well under).
    # Before 1990, "Go Forth Rejoicing" (1985) counts as older and leads
    # "Newer Gathering Song" (1995) despite being in fewer hymnals.
    prompt = prompt_for(fake, HYMNS, rubric_with(prefer_before_year=1990))
    assert candidates(prompt, "RESPONSE") == [
        "Holy, Holy, Holy", "Rejoice, the Lord Is King", "Go Forth Rejoicing", "Newer Gathering Song",
    ]


def test_a_long_list_keeps_places_for_hymns_newer_than_the_church_year(fake):
    # 70 closing hymns before 1900, then five from the 1920s, all equally familiar.
    hymns = [hymn(f"Old Joy {i}", 100 + i, "joy", 1800 + i, 10) for i in range(70)]
    hymns += [hymn(f"Joy of 192{i}", 200 + i, "joy", 1920 + i, 10) for i in range(5)]

    # Under the default 1970 the 1920s hymns count as older, so they rank last and are cut.
    closing = candidates(prompt_for(fake, hymns, default_rubric()), "CLOSING")
    assert len(closing) == 60
    assert not any(title.startswith("Joy of 192") for title in closing)

    # Before 1900 they are newer, so the shortlist keeps places for them.
    closing = candidates(prompt_for(fake, hymns, rubric_with(prefer_before_year=1900)), "CLOSING")
    assert len(closing) == 60
    assert closing[0] == "Old Joy 0"
    assert closing[-5:] == [f"Joy of 192{i}" for i in range(5)]


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


def test_a_long_run_of_older_hymns_does_not_crowd_out_newer_or_unknown_ones(monkeypatch):
    # 70 older closing hymns would fill all 60 places if the list were simply cut.
    hymns = [hymn(f"Old Joy {i}", 100 + i, "joy, praise", 1700 + i, 10) for i in range(70)]
    hymns.append(hymn("Newer Sending Song", 500, "sending", 1990, 5000))
    hymns += [hymn(f"Unknown Joy {i}", 600 + i, "joy") for i in range(5)]
    client = FakeOpenAI(json.dumps({"opening": [], "response": [], "closing": []}))
    monkeypatch.setattr(worship_service, "OpenAI", lambda api_key: client)
    worship_service.suggest_hymns_for_service(
        db=None, occasion="Easter", scriptures=["Isaiah 6:1-8"],
        api_key="test-key", all_hymns=hymns,
    )
    closing = prompt_of(client).split("CLOSING CANDIDATES")[1]
    lines = [line for line in closing.splitlines() if line.startswith("- ")]
    assert len(lines) == 60
    assert any(line.startswith("- Newer Sending Song ") for line in lines)
    assert any(line.startswith("- Unknown Joy 0 ") for line in lines)
    assert lines[0].startswith("- Old Joy")                     # older hymns still lead
    assert lines[-1].startswith("- Newer Sending Song ")        # and the list stays in ranked order
