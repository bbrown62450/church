"""`usecases.prayer_library` (prayer library spec 2026-09-26, "API (slice 6a)";
6a spec, Semantics → PUT /church/prayer-library; slice 6a-3b): the read, the
locked full-replace save with the role re-read, and (Task 2) the voice-profile
draft. The church's prayers are the pastor's own words: no test here prints
one, and the logging tests check that none is logged."""
import datetime
import uuid

import pytest

import prayer_library
from db import session_scope
from db.models import Church
from domain_errors import Forbidden, InvalidInput
from repos import churches
from repos.memberships import add_membership, remove_membership, set_role
from tests.test_church_settings import _record_church_row_access
from usecases import prayer_library as library_usecase

NO_ACCESS = {"reason": "no_church_access"}
CONFESSION = "Merciful God, we confess that we have not loved you with our whole heart."
BENEDICTION = "Go in peace to love and serve the Lord."
NOON = datetime.datetime(2026, 10, 8, 16, 0, tzinfo=datetime.timezone.utc)
LATER = datetime.datetime(2026, 10, 9, 9, 30, tzinfo=datetime.timezone.utc)


@pytest.fixture
def world(tmp_db, make_user, make_church):
    owner = make_user(email="owner@example.com")
    admin = make_user(email="admin@example.com")
    member = make_user(email="member@example.com")
    cid = make_church(name="Grace", owner_user_id=owner)
    add_membership(admin, cid, "admin")
    add_membership(member, cid, "member")
    return {"church": cid, "owner": owner, "admin": admin, "member": member}


def _ids():
    """A new-id maker that hands out uuid 1, 2, 3 and so on, so a test can name them."""
    made = (uuid.UUID(int=n) for n in range(1, 100))
    return lambda: next(made)


def _save(world, prayers, profile="", *, who="owner", now=NOON, new_id=uuid.uuid4):
    return library_usecase.save_library(world["church"], world[who], prayers, profile,
                                        now=lambda: now, new_id=new_id)


def _stored(world):
    return churches.get_church(world["church"])["settings"].get("prayer_library")


def test_the_library_reads_empty_until_saved_and_a_junk_value_reads_empty(world):
    assert library_usecase.get_library(world["church"], can_edit=False) == {
        "prayers": [], "voice_profile": "", "can_edit": False}
    churches.update_church(world["church"], settings={"prayer_library": ["junk"], "foo": 1})
    assert library_usecase.get_library(world["church"], can_edit=True) == {
        "prayers": [], "voice_profile": "", "can_edit": True}


def test_a_save_normalizes_assigns_ids_and_keeps_every_other_setting(world):
    churches.update_church(world["church"], settings={"rubric": {"prefer_familiar": False}, "foo": 1})
    out = _save(world, [
        {"type": "prayer_of_confession", "text": "  " + CONFESSION.replace(" that", "\r\nthat") + "\r\n"},
        {"id": None, "type": "other", "text": "A wedding prayer."},
    ], "  Warm and plain.\r\nShort sentences.  ", new_id=_ids())
    first, second = str(uuid.UUID(int=1)), str(uuid.UUID(int=2))
    assert out == {
        "prayers": [
            {"id": first, "type": "prayer_of_confession", "text": CONFESSION.replace(" that", "\nthat"),
             "added_at": "2026-10-08T16:00:00Z"},
            {"id": second, "type": "other", "text": "A wedding prayer.", "added_at": "2026-10-08T16:00:00Z"},
        ],
        "voice_profile": "Warm and plain.\nShort sentences.",
        "can_edit": True,
    }
    assert _stored(world) == {"prayers": out["prayers"], "voice_profile": "Warm and plain.\nShort sentences."}
    settings = churches.get_church(world["church"])["settings"]
    assert (settings["rubric"], settings["foo"]) == ({"prefer_familiar": False}, 1)
    assert library_usecase.get_library(world["church"], can_edit=True) == out


def test_a_known_id_keeps_its_added_at_and_an_unknown_or_repeated_id_is_new(world):
    saved = _save(world, [{"type": "benediction", "text": BENEDICTION}])["prayers"][0]
    out = _save(world, [
        {"id": saved["id"], "type": "benediction", "text": BENEDICTION + " Amen."},
        {"id": saved["id"], "type": "benediction", "text": "A second one."},
        {"id": str(uuid.uuid4()), "type": "opening_prayer", "text": "Gracious God."},
        {"id": "not-a-uuid", "type": "other", "text": "Something."},
    ], now=LATER, new_id=_ids())
    assert [(p["id"], p["added_at"]) for p in out["prayers"]] == [
        (saved["id"], "2026-10-08T16:00:00Z"),
        (str(uuid.UUID(int=1)), "2026-10-09T09:30:00Z"),
        (str(uuid.UUID(int=2)), "2026-10-09T09:30:00Z"),
        (str(uuid.UUID(int=3)), "2026-10-09T09:30:00Z"),
    ]
    assert out["prayers"][0]["text"] == BENEDICTION + " Amen."
    assert _save(world, [], "", now=LATER) == {"prayers": [], "voice_profile": "", "can_edit": True}
    assert _stored(world) == {"prayers": [], "voice_profile": ""}


@pytest.mark.parametrize("prayers, profile, field, message", [
    ([{"type": "benediction", "text": "   \r\n "}], "", "prayers.0.text", "Prayer text is required."),
    ([{"type": "benediction", "text": "Go."}, {"type": "benediction", "text": "x" * 6_001}], "",
     "prayers.1.text", "This prayer is too long (6,000 characters at most)."),
    ([{"type": "", "text": "Go."}], "", "prayers.0.type", "Choose a prayer type."),
    ([{"type": "sermon", "text": "Go."}], "", "prayers.0.type", "Choose a prayer type."),
    ([{"type": "benediction", "text": "Go."}] * 31, "", "prayers", "You can keep up to 30 prayers."),
    ([], "x" * 2_001, "voice_profile", "The voice profile is too long (2,000 characters at most)."),
    ([{"type": "", "text": " "}, {"type": "benediction", "text": ""}], "x" * 2_001, "prayers.0.type",
     "Choose a prayer type."),
    ([{"type": "benediction", "text": "Go."}, {"type": "other", "text": ""}], "x" * 2_001, "prayers.1.text",
     "Prayer text is required."),
])
def test_a_bad_library_is_named_by_its_field_and_nothing_is_saved(world, prayers, profile, field, message):
    _save(world, [{"type": "benediction", "text": BENEDICTION}], "Kept.")
    before = _stored(world)
    with pytest.raises(InvalidInput) as bad:
        _save(world, prayers, profile)
    assert (bad.value.code, bad.value.field, bad.value.message) == ("invalid_request", field, message)
    assert _stored(world) == before


def test_the_limits_are_counted_after_trimming(world):
    out = _save(world, [{"type": "other", "text": "  " + "x" * 6_000 + "\r\n"}] * 30, " " + "y" * 2_000 + " ")
    assert len(out["prayers"]) == 30 and {len(p["text"]) for p in out["prayers"]} == {6_000}
    assert len(out["voice_profile"]) == 2_000
    assert (prayer_library.MAX_PRAYERS, prayer_library.MAX_PRAYER_CHARS, prayer_library.MAX_PROFILE_CHARS) == (
        30, 6_000, 2_000)


def test_a_member_a_demoted_admin_or_a_removed_member_saves_nothing(world):
    with pytest.raises(Forbidden) as member:
        _save(world, [{"type": "benediction", "text": "Go."}], who="member")
    assert (member.value.message, member.value.details) == ("Only church admins can do this.", None)
    set_role(world["admin"], world["church"], "member")            # after require_admin read "admin"
    with pytest.raises(Forbidden) as demoted:
        _save(world, [{"type": "", "text": ""}], who="admin")      # the role first, before the body is read
    assert (demoted.value.message, demoted.value.details) == ("Only church admins can do this.", None)
    remove_membership(world["member"], world["church"])
    with pytest.raises(Forbidden) as removed:
        _save(world, [], who="member")
    assert removed.value.details == NO_ACCESS
    churches.soft_delete_church(world["church"])
    with pytest.raises(Forbidden) as deleted:
        _save(world, [])
    assert deleted.value.details == NO_ACCESS
    with session_scope() as s:
        assert (s.get(Church, world["church"]).settings or {}) == {}


def test_the_library_is_read_and_written_under_one_row_lock(world):
    with _record_church_row_access() as (reads, writes):
        _save(world, [{"type": "benediction", "text": "Go."}])
    assert len(writes) == 1
    in_the_write = [locked for session, locked in reads if session is writes[0]]
    assert in_the_write and all(in_the_write)
