import liturgy_prompts as lp


def test_default_prompts_has_system_and_every_section():
    d = lp.default_prompts()
    assert d["system"] == lp.DEFAULT_SYSTEM_PROMPT
    for section in lp.SECTION_ORDER:
        assert d[section] == lp.DEFAULT_SECTION_PROMPTS[section]


def test_merge_prompts_applies_nonblank_overrides_only():
    merged = lp.merge_prompts({"system": "My voice.", "benediction": "  ", "call_to_worship": "CTW!"})
    assert merged["system"] == "My voice."
    assert merged["call_to_worship"] == "CTW!"
    # blank override is ignored -> default retained
    assert merged["benediction"] == lp.DEFAULT_SECTION_PROMPTS["benediction"]


def test_merge_prompts_ignores_unknown_keys():
    merged = lp.merge_prompts({"bogus": "x"})
    assert "bogus" not in merged
    assert merged == lp.default_prompts()


def test_merge_prompts_none_is_all_defaults():
    assert lp.merge_prompts(None) == lp.default_prompts()


def test_render_fills_known_placeholders():
    out = lp.render(
        "Occasion {occasion}; refs {scriptures}; open {opening_hymn}; all {hymns}",
        occasion="Easter", scriptures="- John 20", opening_hymn="Jesus Christ Is Risen", hymns="- a\n- b",
    )
    assert "Occasion Easter" in out
    assert "refs - John 20" in out
    assert "open Jesus Christ Is Risen" in out


def test_render_is_safe_against_unknown_placeholders():
    # An admin who types a stray {mystery} must not crash generation.
    out = lp.render("Hello {mystery} for {occasion}", occasion="Lent")
    assert out == "Hello  for Lent"
