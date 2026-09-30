"""The liturgy prompts, pinned before worship_service.generate_liturgy goes
(slice 4 spec, Testing "Characterization first" `test_liturgy_generation.py`;
AC3, AC19). The system message is compared with the merged system prompt,
never quoted (the reviewer add-on changes the default's season sentences;
S "Tests before and after")."""
import liturgy_prompts as lp

OCCASION = "Third Sunday of Easter"
SCRIPTURES = ["Acts 9:1-6", "Psalm 30", "Revelation 5:11-14", "John 21:1-19"]
SLOTS = {"opening": lp.ResolvedHymn("Holy, Holy, Holy", 138),
         "response": lp.ResolvedHymn("Be Thou My Vision", 450),
         "closing": lp.ResolvedHymn("Lift High the Cross", 826)}


def _messages(section, overrides=None, **context):
    ctx = lp.build_context(occasion=OCCASION, scriptures=context.pop("scriptures", SCRIPTURES),
                           hymns_by_slot=context.pop("hymns_by_slot", SLOTS), **context)
    return lp.build_messages(section, lp.merge_prompts(overrides), ctx)


def test_the_system_message_is_the_merged_system_prompt():
    assert _messages("benediction")[0]["content"] == lp.default_prompts()["system"]
    assert _messages("benediction", {"system": "Our own voice."})[0]["content"] == "Our own voice."


def test_scripture_lines_or_none_specified():
    user = _messages("call_to_worship")[1]["content"]
    assert "- Acts 9:1-6\n- Psalm 30\n- Revelation 5:11-14\n- John 21:1-19" in user
    assert "None specified." in _messages("call_to_worship", scriptures=[])[1]["content"]


def test_church_overrides_are_applied():
    user = _messages("benediction", {"benediction": "Bless {occasion} with {opening_hymn}."})[1]["content"]
    assert user.startswith("Bless Third Sunday of Easter with Holy, Holy, Holy.")
    assert "A good Benediction:" in user


def test_opening_hymn_comes_from_the_opening_slot():
    """BC-8: generate_liturgy used the first filled slot (the positional bug)."""
    slots = {"opening": None, "response": SLOTS["response"], "closing": SLOTS["closing"]}
    user = _messages("call_to_worship", hymns_by_slot=slots)[1]["content"]
    assert "Opening hymn: N/A." in user and "Be Thou My Vision" not in user


def test_a_hymn_without_a_number_has_no_hash_none():
    """BC-8: generate_liturgy printed "(#None)"."""
    slots = {"opening": lp.ResolvedHymn("Archived Hymn", None)}
    user = _messages("prayers_of_the_people", hymns_by_slot=slots)[1]["content"]
    assert "Hymns: - Archived Hymn." in user and "(#None)" not in user


def test_the_old_generate_liturgy_is_gone():
    """S Backend 6: deleted after its behavior was pinned above and in
    test_generate_liturgy.py, with its UI-shaped error strings."""
    from pathlib import Path

    import worship_service

    for name in ("generate_liturgy", "_sermon_text_block", "SERMON_TEXT_LIMIT", "OpenAI"):
        assert not hasattr(worship_service, name), name
    source = Path(worship_service.__file__).read_text(encoding="utf-8")
    for text in ("Settings → Secrets", "Configure OPENAI_API_KEY", "gpt-3.5-turbo", "[Error generating"):
        assert text not in source, text
