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


def test_short_prayers_default_to_three_sentences_at_most():
    assert "no more than 3 sentences" in lp.DEFAULT_SECTION_PROMPTS["prayer_for_illumination"]
    assert "3-5" not in lp.DEFAULT_SECTION_PROMPTS["prayer_for_illumination"]
    assert lp.DEFAULT_SECTION_PROMPTS["offertory_prayer"].startswith(
        "Write an Offertory Prayer for: {occasion}. No more than three sentences:"
    )


# --- slice 4a: the template validator (slice 4 spec, Backend 2; Testing; AC6) ---

import liturgy_config

BRACE = "It has a { or } without a partner. Use {{ or }} to print a brace."
ONE_WORD = ("Placeholders must be a single word such as {occasion}. "
            "To print a { or } as text, write {{ or }}.")
MALFORMED = [
    (["{", "}", "{a!}", "{a[}"], BRACE),
    (["{}", "{0}"], "Placeholders need a name, such as {occasion}."),
    (["{a.b}", "{a[0]}", "{a[x]}", "{occasion.upper}"],
     "Placeholders must be a plain name such as {occasion}, with no dots or brackets."),
    (['{"a": 1}', '{"title"}', "{ occasion }", "{a b}"], ONE_WORD),
    (["{a!r}", "{a:d}", "{occasion:>10}"], "Placeholders can't include ! or :. Write just {occasion}."),
    (["x" * 8001], "This prompt is too long (max 8,000 characters)."),
]


def test_check_template_rejects_each_malformed_case_with_its_message():
    for templates, message in MALFORMED:
        for template in templates:
            check = lp.check_template("benediction", template)
            assert (check.ok, check.message, check.unknown_placeholders) == (False, message, ()), template
            assert lp.template_error(template) == message, template


def test_defaults_literal_braces_unknown_placeholders_and_the_system_prompt_pass():
    for key, template in lp.default_prompts().items():
        assert lp.check_template(key, template) == lp.TemplateCheck(True, None, ()), key
        if key != "system":
            assert lp.template_error(template) is None, key
    assert lp.check_template("call_to_worship", "Hi {ocassion} and {occasion} {ocassion}") == \
        lp.TemplateCheck(True, None, ("ocassion",))
    assert lp.check_template("call_to_worship", "{{literal}}").ok
    assert lp.check_template("system", 'Answer as JSON: {"a": 1} {').ok        # never formatted
    assert lp.check_template("system", "x" * 8001).message == "This prompt is too long (max 8,000 characters)."
    assert lp.check_template("call_to_worship", "x" * 8000).ok
    assert "no more than 3 sentences" in lp.DEFAULT_SECTION_PROMPTS["prayer_for_illumination"]
    assert "No more than three sentences" in lp.DEFAULT_SECTION_PROMPTS["offertory_prayer"]


def test_validate_prompts_reports_only_what_merge_prompts_would_use():
    assert lp.validate_prompts({"bogus": "x", "benediction": "{", "system": "{"}) == {"benediction": BRACE}
    assert lp.validate_prompts({"benediction": "   ", "opening_prayer": 5, "assurance": None}) == {}
    assert lp.validate_prompts({"call_to_worship": '{"a": 1}', "offertory_prayer": "{0}"}) == {
        "call_to_worship": ONE_WORD, "offertory_prayer": "Placeholders need a name, such as {occasion}."}
    assert lp.validate_prompts("not a mapping") == {}


def test_clean_prompt_overrides_drops_defaults_blanks_and_unknown_keys():
    """Ports streamlit_tests/test_settings_prompts_translation.py
    test_admin_prompt_save_drops_defaults_and_reset_clears."""
    submitted = {
        "system": lp.DEFAULT_SYSTEM_PROMPT,              # unchanged -> not stored
        "benediction": "  Go in peace, friends.  ",      # changed -> stored, stripped
        "opening_prayer": "   ",                         # blank -> not stored
        "bogus": "x",                                    # unknown key -> not stored
        "assurance": None,
    }
    assert lp.clean_prompt_overrides(submitted) == {"benediction": "Go in peace, friends."}
    defaults = {"benediction": "Go in peace, friends."}
    assert lp.clean_prompt_overrides(submitted, defaults) == {"system": lp.DEFAULT_SYSTEM_PROMPT}
    assert lp.clean_prompt_overrides({}) == {}


def test_clean_prompt_overrides_reads_crlf_as_lf():
    default = lp.DEFAULT_SECTION_PROMPTS["benediction"]
    assert lp.clean_prompt_overrides({"benediction": "Line one.\r\nLine two.\r\n"}) == {
        "benediction": "Line one.\nLine two."}
    multi = {"benediction": "Bless us.\nKeep us."}
    assert lp.clean_prompt_overrides({"benediction": "Bless us.\r\nKeep us."}, multi) == {}
    assert lp.clean_prompt_overrides({"benediction": "Bless us.\nKeep us."},
                                     {"benediction": "Bless us.\r\nKeep us."}) == {}
    assert lp.clean_prompt_overrides({"benediction": default.replace(". ", ".\r\n")}) != {}
    assert lp.clean_prompt_overrides({"benediction": default + "\r\n"}) == {}


def test_section_order_and_labels_come_from_liturgy_config():
    assert lp.SECTION_ORDER is liturgy_config.SECTION_ORDER
    assert lp.SECTION_LABELS is liturgy_config.SECTION_LABELS
    assert lp.PROMPT_KEYS == ["system"] + liturgy_config.SECTION_ORDER


def test_merge_prompts_ignores_values_that_are_not_strings():
    merged = lp.merge_prompts({"benediction": 5, "system": ["x"], "assurance": "Mine."})
    assert merged["benediction"] == lp.DEFAULT_SECTION_PROMPTS["benediction"]
    assert merged["system"] == lp.DEFAULT_SYSTEM_PROMPT
    assert merged["assurance"] == "Mine."
