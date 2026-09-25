import pytest


def test_member_cannot_edit_prompts_or_translation(tmp_db, make_user, make_church):
    from views.settings import (
        submit_prompts, reset_prompts, submit_translation, NotAuthorizedError,
    )
    from repos.memberships import add_membership
    owner = make_user(email="o@p.org")
    church = make_church(name="P", timezone="America/New_York", owner_user_id=owner)
    member = make_user(email="m@p.org")
    add_membership(member, church, "member")
    with pytest.raises(NotAuthorizedError):
        submit_prompts(member, church, {"benediction": "Go."})
    with pytest.raises(NotAuthorizedError):
        reset_prompts(member, church)
    with pytest.raises(NotAuthorizedError):
        submit_translation(member, church, "kjv")


def test_admin_prompt_save_drops_defaults_and_reset_clears(tmp_db, make_user, make_church):
    from views.settings import submit_prompts, reset_prompts
    from repos.churches import get_church_prompts
    import liturgy_prompts as lp
    owner = make_user(email="o2@p.org")
    church = make_church(name="P2", timezone="America/New_York", owner_user_id=owner)

    # A value equal to the default is NOT stored; a real change is.
    submit_prompts(owner, church, {
        "system": lp.DEFAULT_SYSTEM_PROMPT,          # unchanged -> not stored
        "benediction": "Go in peace, friends.",      # changed -> stored
    })
    assert get_church_prompts(church) == {"benediction": "Go in peace, friends."}

    reset_prompts(owner, church)
    assert get_church_prompts(church) == {}


def test_admin_translation_validated(tmp_db, make_user, make_church):
    from views.settings import submit_translation
    from repos.churches import get_church_translation
    owner = make_user(email="o3@p.org")
    church = make_church(name="P3", timezone="America/New_York", owner_user_id=owner)
    submit_translation(owner, church, "kjv")
    assert get_church_translation(church) == "kjv"
    with pytest.raises(ValueError):
        submit_translation(owner, church, "not-a-translation")
