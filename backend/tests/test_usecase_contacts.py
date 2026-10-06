"""usecases.contacts (slice 5b-1; 6a spec "Semantics" → Contacts): the list
with each address's check, the address and name rules, the duplicate check,
and every write under the church-row lock with the role re-read under it."""
import pytest

import email_contacts
from domain_errors import Conflict, Forbidden, InvalidInput, NotFound
from email_addresses import normalize_address
from repos import churches
from repos.memberships import add_membership, remove_membership, set_role
from tests.test_church_settings import _record_church_row_access
from usecases import contacts

NO_ACCESS = {"reason": "no_church_access"}


@pytest.fixture
def world(tmp_db, make_user, make_church):
    owner = make_user(email="owner@example.com")
    admin = make_user(email="admin@example.com")
    member = make_user(email="member@example.com")
    cid = make_church(name="Example Church", owner_user_id=owner)
    add_membership(admin, cid, "admin")
    add_membership(member, cid, "member")
    return {"church": cid, "owner": owner, "admin": admin, "member": member}


def _emails(world) -> list[str]:
    return [c["email"] for c in email_contacts.list_contacts(world["church"])]


@pytest.mark.parametrize("raw, stored", [
    (" Mary@Example.ORG ", "Mary@example.org"),
    ("pastor+bulletin@example.org", "pastor+bulletin@example.org"),
])
def test_an_address_is_stored_as_the_send_time_rule_returns_it(raw, stored):
    assert contacts.normalize_email(raw) == stored
    assert normalize_address(stored) == stored


@pytest.mark.parametrize("raw, message", [
    ("", "Email is required."),
    ("   ", "Email is required."),
    (None, "Email is required."),
    ("maryexample.org", "Enter a valid email address."),
    ("mary@@example.org", "Enter a valid email address."),
    ("mary jones@example.org", "Enter a valid email address."),
    ("a@b", "Enter a valid email address."),
    ("josé@example.org", "Enter a valid email address."),
    ("a@bücher.de", "Enter a valid email address."),
])
def test_a_missing_or_invalid_address_is_named(raw, message):
    with pytest.raises(InvalidInput) as bad:
        contacts.normalize_email(raw)
    assert (bad.value.field, bad.value.message) == ("email", message)


def test_a_name_is_trimmed_blank_is_stored_as_empty_and_it_stays_on_one_line():
    assert contacts.clean_name("  Mary Jones ") == "Mary Jones"
    assert contacts.clean_name("   ") == ""
    assert contacts.clean_name(None) == ""
    for bad in ("Mary\nJones", "Mary\x00", "Mary\u2028Jones"):
        with pytest.raises(InvalidInput) as refused:
            contacts.clean_name(bad)
        assert (refused.value.field, refused.value.message) == (
            "name", "Name can't contain line breaks or control characters.")


def test_an_admin_adds_a_contact_and_a_duplicate_in_any_case_is_refused(world):
    added = contacts.add_contact(world["church"], world["admin"], name=" Mary ", email=" Mary@Example.ORG ")
    assert {k: added[k] for k in ("name", "email", "email_valid")} == {
        "name": "Mary", "email": "Mary@example.org", "email_valid": True}
    with pytest.raises(Conflict) as taken:
        contacts.add_contact(world["church"], world["owner"], name="Other", email="MARY@example.org")
    assert taken.value.message == "That email is already in your contacts."
    nameless = contacts.add_contact(world["church"], world["owner"], name="  ", email="office@example.org")
    assert nameless["name"] is None
    assert _emails(world) == ["Mary@example.org", "office@example.org"]


def test_an_edit_changes_only_what_is_sent_and_checks_duplicates_but_not_itself(world):
    mary = contacts.add_contact(world["church"], world["owner"], name="Mary", email="mary@example.org")
    contacts.add_contact(world["church"], world["owner"], name="Office", email="office@example.org")
    edited = contacts.update_contact(world["church"], world["admin"], mary["id"], {"name": "Mary Jones"})
    assert (edited["name"], edited["email"]) == ("Mary Jones", "mary@example.org")
    edited = contacts.update_contact(world["church"], world["admin"], mary["id"], {"email": "MARY@example.org"})
    assert (edited["name"], edited["email"]) == ("Mary Jones", "MARY@example.org")       # itself: no conflict
    assert contacts.update_contact(world["church"], world["admin"], mary["id"], {"name": None})["name"] is None
    with pytest.raises(Conflict):
        contacts.update_contact(world["church"], world["admin"], mary["id"], {"email": "Office@Example.org"})
    with pytest.raises(InvalidInput) as blank:
        contacts.update_contact(world["church"], world["admin"], mary["id"], {"email": None})
    assert (blank.value.field, blank.value.message) == ("email", "Email is required.")
    assert _emails(world) == ["MARY@example.org", "office@example.org"]


def test_an_unknown_contact_or_another_churchs_is_not_found(world, make_church):
    other = make_church(name="Other Church", owner_user_id=world["owner"])
    theirs = contacts.add_contact(other, world["owner"], name="Theirs", email="theirs@example.org")
    for call in (lambda: contacts.update_contact(world["church"], world["owner"], theirs["id"], {"email": "bad"}),
                 lambda: contacts.delete_contact(world["church"], world["owner"], theirs["id"])):
        with pytest.raises(NotFound) as missing:
            call()
        assert missing.value.message == "Contact not found."
    assert [c["email"] for c in email_contacts.list_contacts(other)] == ["theirs@example.org"]
    contacts.delete_contact(other, world["owner"], theirs["id"])
    assert email_contacts.list_contacts(other) == []


def test_the_list_flags_each_saved_address_the_send_time_rule_refuses(world):
    for name, email in (("Mary", "mary@example.org"), ("Two", "a@example.org, b@example.org"),
                        ("", "office@example"), (None, " Office@Example.ORG "), ("  ", "pastor@example.org")):
        email_contacts.add_contact(world["church"], name=name, email=email)     # as Streamlit saved them
    listed = contacts.list_contacts(world["church"])
    assert [(c["name"], c["email"], c["email_valid"]) for c in listed] == [
        ("Mary", "mary@example.org", True),
        ("Two", "a@example.org, b@example.org", False),
        (None, "office@example", False),
        (None, " Office@Example.ORG ", True),
        (None, "pastor@example.org", True),
    ]


def test_a_member_a_demoted_admin_or_a_removed_member_writes_nothing(world):
    mary = contacts.add_contact(world["church"], world["owner"], name="Mary", email="mary@example.org")
    writes = (lambda who: contacts.add_contact(world["church"], world[who], name="X", email="x@example.org"),
              lambda who: contacts.update_contact(world["church"], world[who], mary["id"], {"name": "Renamed"}),
              lambda who: contacts.delete_contact(world["church"], world[who], mary["id"]))
    set_role(world["admin"], world["church"], "member")            # after require_admin read "admin"
    for who in ("member", "admin"):
        for write in writes:
            with pytest.raises(Forbidden) as denied:
                write(who)
            assert (denied.value.message, denied.value.details) == ("Only church admins can do this.", None)
    remove_membership(world["member"], world["church"])
    with pytest.raises(Forbidden) as removed:
        writes[0]("member")
    assert removed.value.details == NO_ACCESS
    churches.soft_delete_church(world["church"])
    with pytest.raises(Forbidden) as deleted:
        writes[0]("owner")
    assert deleted.value.details == NO_ACCESS
    assert [(c["name"], c["email"]) for c in email_contacts.list_contacts(world["church"])] == [
        ("Mary", "mary@example.org")]


def test_each_write_reads_the_church_row_under_its_lock(world):
    for write in (lambda: contacts.add_contact(world["church"], world["owner"], name="Mary", email="mary@example.org"),
                  lambda: contacts.update_contact(world["church"], world["owner"],
                                                  email_contacts.list_contacts(world["church"])[0]["id"],
                                                  {"email": "mary.jones@example.org"}),
                  lambda: contacts.delete_contact(world["church"], world["owner"],
                                                  email_contacts.list_contacts(world["church"])[0]["id"])):
        with _record_church_row_access() as (reads, _writes):
            write()
        assert [locked for _session, locked in reads] == [True]
