from repos.churches import (
    create_church,
    get_church_prompts, set_church_prompts,
    get_church_translation, set_church_translation,
)


def test_prompts_default_empty_then_store_and_reset(tmp_db, make_user):
    owner = make_user(email="o@x.org")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    assert get_church_prompts(cid) == {}

    set_church_prompts(cid, {"system": "My voice.", "benediction": "  ", "bogus": "x"})
    stored = get_church_prompts(cid)
    assert stored == {"system": "My voice."}     # blank dropped, unknown key dropped

    # Clearing a key resets it (blank -> not persisted)
    set_church_prompts(cid, {"system": ""})
    assert get_church_prompts(cid) == {}


def test_translation_default_none_then_set(tmp_db, make_user):
    owner = make_user(email="o2@x.org")
    cid = create_church(name="C2", timezone="UTC", owner_user_id=owner)
    assert get_church_translation(cid) is None
    set_church_translation(cid, "esv")
    assert get_church_translation(cid) == "esv"


def test_settings_keys_are_independent(tmp_db, make_user):
    owner = make_user(email="o3@x.org")
    cid = create_church(name="C3", timezone="UTC", owner_user_id=owner)
    set_church_translation(cid, "kjv")
    set_church_prompts(cid, {"benediction": "Go in peace."})
    # writing prompts must not clobber the translation, and vice versa
    assert get_church_translation(cid) == "kjv"
    assert get_church_prompts(cid) == {"benediction": "Go in peace."}
