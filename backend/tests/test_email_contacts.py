from datetime import datetime, timezone

import pytest

import email_contacts
from db import session_scope
from db.models import Contact
from domain_errors import NotFound
from email_contacts import (
    add_contact,
    delete_contact,
    email_exists,
    get_contact,
    get_contacts_for_display,
    list_contacts,
    update_contact,
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


# --- slice 5b-1: the order, blank names, edits, the duplicate check, a session -------------------

def _seed(church_id, rows):
    """Contacts with the given (name, email, created_at), straight into the table."""
    with session_scope() as s:
        for name, email, created_at in rows:
            s.add(Contact(church_id=church_id, name=name, email=email, created_at=created_at))


def test_contacts_are_listed_by_creation_then_name_with_blank_names_last(tmp_db, make_user, make_church):
    church = make_church(name="A", owner_user_id=make_user(email="c3@x.org"))
    first, later = datetime(2026, 1, 1, tzinfo=timezone.utc), datetime(2026, 2, 1, tzinfo=timezone.utc)
    _seed(church, [("Zoe", "zoe@x.org", first), ("", "blank@x.org", first), (None, "null@x.org", first),
                   ("  ", "spaces@x.org", first), ("Amy", "amy@x.org", first), ("Bob", "bob@x.org", later)])
    listed = list_contacts(church)
    assert [c["email"] for c in listed[:2]] == ["amy@x.org", "zoe@x.org"]
    assert sorted(c["email"] for c in listed[2:5]) == ["blank@x.org", "null@x.org", "spaces@x.org"]
    assert [c["id"] for c in listed[2:5]] == sorted(c["id"] for c in listed[2:5])     # nameless: by id
    assert listed[5]["email"] == "bob@x.org"
    assert [c["name"] for c in listed] == ["Amy", "Zoe", None, None, None, "Bob"]


def test_update_contact_sets_only_the_keys_given_and_never_another_church(tmp_db, make_user, make_church):
    u = make_user(email="c4@x.org")
    a = make_church(name="A", owner_user_id=u)
    b = make_church(name="B", owner_user_id=u)
    cid = add_contact(a, name="Mary", email="mary@x.org")["id"]
    assert update_contact(cid, a, {"name": ""}) == {"id": cid, "name": None, "email": "mary@x.org"}
    assert update_contact(cid, a, {"email": "mary.jones@x.org"})["email"] == "mary.jones@x.org"
    assert update_contact(cid, b, {"name": "Taken"}) is None
    assert get_contact(cid, b) is None
    assert get_contact(cid, a) == {"id": cid, "name": None, "email": "mary.jones@x.org"}


def test_email_exists_ignores_case_and_can_leave_one_contact_out(tmp_db, make_user, make_church):
    u = make_user(email="c5@x.org")
    a = make_church(name="A", owner_user_id=u)
    b = make_church(name="B", owner_user_id=u)
    cid = add_contact(a, name="Mary", email="Mary@X.org")["id"]
    assert email_exists(a, "mary@x.org") and email_exists(a, "MARY@X.ORG")
    assert not email_exists(a, "mary@x.org", exclude_id=cid)
    assert not email_exists(b, "mary@x.org")


def test_email_exists_ignores_spaces_around_a_saved_address(tmp_db, make_user, make_church):
    a = make_church(name="A", owner_user_id=make_user(email="c8@x.org"))
    cid = add_contact(a, name="", email=" Mary@X.org ")["id"]          # as Streamlit saved it, untrimmed
    assert email_exists(a, "mary@x.org")
    assert not email_exists(a, "mary@x.org", exclude_id=cid)           # an edit of that contact itself


def test_a_malformed_id_is_not_found(tmp_db, make_user, make_church):
    a = make_church(name="A", owner_user_id=make_user(email="c6@x.org"))
    for call in (lambda: update_contact("not-a-uuid", a, {"name": "X"}), lambda: delete_contact("not-a-uuid", a),
                 lambda: get_contact("not-a-uuid", a)):
        with pytest.raises(NotFound):
            call()


def test_the_writes_join_the_callers_session(tmp_db, make_user, make_church):
    a = make_church(name="A", owner_user_id=make_user(email="c7@x.org"))
    with session_scope() as s:
        cid = add_contact(a, name="Mary", email="mary@x.org", session=s)["id"]
        assert email_exists(a, "mary@x.org", session=s)
        update_contact(cid, a, {"name": "Mary J."}, session=s)
        assert [c["name"] for c in list_contacts(a, session=s)] == ["Mary J."]
        assert delete_contact(cid, a, session=s) is True
    assert list_contacts(a) == []
