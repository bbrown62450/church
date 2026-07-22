import pytest


def test_member_cannot_update_profile(tmp_db, make_user, make_church):
    from pages.settings import submit_profile_update, NotAuthorizedError
    from repos.memberships import add_membership
    owner = make_user(email="owner@f.org")
    church = make_church(name="First", timezone="America/New_York", owner_user_id=owner)
    member = make_user(email="member@f.org")
    add_membership(member, church, "member")
    with pytest.raises(NotAuthorizedError):
        submit_profile_update(member, church, name="Hacked", timezone="America/New_York")


def test_member_cannot_add_or_delete_contacts(tmp_db, make_user, make_church):
    from pages.settings import submit_add_contact, submit_delete_contact, NotAuthorizedError
    from repos.memberships import add_membership
    owner = make_user(email="o2@f.org")
    church = make_church(name="F2", timezone="America/New_York", owner_user_id=owner)
    member = make_user(email="m2@f.org")
    add_membership(member, church, "member")
    with pytest.raises(NotAuthorizedError):
        submit_add_contact(member, church, name="X", email="x@f.org")
    with pytest.raises(NotAuthorizedError):
        submit_delete_contact(member, church, "any-id")


def test_admin_can_update_profile_and_add_contact(tmp_db, make_user, make_church):
    from pages.settings import submit_profile_update, submit_add_contact
    import email_contacts
    from db import session_scope
    from db.models import Church
    owner = make_user(email="admin@g.org")
    church = make_church(name="G", timezone="America/New_York", owner_user_id=owner)
    submit_profile_update(owner, church, name="Grace Church", timezone="America/Chicago")
    with session_scope() as s:
        c = s.get(Church, church)
        assert c.name == "Grace Church" and c.timezone == "America/Chicago"
    submit_add_contact(owner, church, name="Sec", email="sec@g.org")
    assert any(x["email"] == "sec@g.org" for x in email_contacts.list_contacts(church))


def test_member_can_add_hymn(tmp_db, make_user, make_church):
    # Members may edit the hymnal (spec §5) — the hymn helper does NOT require admin.
    from pages.settings import submit_add_hymn
    from repos.memberships import add_membership
    from repos.hymns import list_hymns
    owner = make_user(email="o3@h.org")
    church = make_church(name="H", timezone="America/New_York", owner_user_id=owner)
    member = make_user(email="m3@h.org")
    add_membership(member, church, "member")
    submit_add_hymn(member, church, title="A New Song", number=700)
    assert any(h.get("Hymn Title") == "A New Song" for h in list_hymns(church))
