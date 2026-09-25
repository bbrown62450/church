import email_contacts
from email_contacts import (
    add_contact,
    delete_contact,
    get_contacts_for_display,
    list_contacts,
)


def test_no_default_contacts_symbol():
    # The hardcoded real emails must be gone from the code entirely.
    assert not hasattr(email_contacts, "DEFAULT_CONTACTS")


def test_contacts_are_church_isolated(tmp_db, make_user, make_church):
    u = make_user(email="c@x.org")
    a = make_church(name="A", timezone="America/New_York", owner_user_id=u)
    b = make_church(name="B", timezone="America/New_York", owner_user_id=u)

    c1 = add_contact(a, name="Mary", email="mary@x.org")
    assert set(c1) == {"id", "name", "email"}
    assert c1["name"] == "Mary"

    # New church starts empty — no defaults inherited.
    assert list_contacts(b) == []
    assert get_contacts_for_display(b) == []
    assert [c["email"] for c in list_contacts(a)] == ["mary@x.org"]


def test_delete_contact_is_church_scoped_idor(tmp_db, make_user, make_church):
    u = make_user(email="c2@x.org")
    a = make_church(name="A", timezone="America/New_York", owner_user_id=u)
    b = make_church(name="B", timezone="America/New_York", owner_user_id=u)
    cid = add_contact(a, name="Mary", email="mary@x.org")["id"]

    # Church B cannot delete Church A's contact (contact_id is the FIRST arg).
    assert delete_contact(cid, b) is False
    assert len(list_contacts(a)) == 1

    # Correct church can.
    assert delete_contact(cid, a) is True
    assert list_contacts(a) == []
