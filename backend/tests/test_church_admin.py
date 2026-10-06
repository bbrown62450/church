"""The church-row lock and the role re-read every church write starts with
(6a spec, "Semantics" → Locking; 6b spec, `lock_and_read_actor`), and
`usecases.church_admin` (slice 6a-1)."""
import pytest

from db import session_scope
from db.models import Church
from domain_errors import Forbidden, InvalidInput
from repos import churches
from repos.hymns import add_hymn
from repos.memberships import add_membership, remove_membership, set_role
from tests.test_church_settings import _record_church_row_access
from usecases import church_admin, church_profile
from usecases.members import lock_and_read_actor

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


def _actor_role(world, who: str) -> str:
    with session_scope() as s:
        return lock_and_read_actor(s, world["church"], world[who])


def test_the_role_is_read_under_the_church_row_lock(world):
    assert [_actor_role(world, who) for who in ("owner", "admin", "member")] == ["owner", "admin", "member"]
    set_role(world["admin"], world["church"], "member")        # demoted after the guard read "admin"
    assert _actor_role(world, "admin") == "member"
    with _record_church_row_access() as (reads, _writes):
        _actor_role(world, "owner")
    assert [locked for _session, locked in reads] == [True]


def test_a_church_or_a_membership_gone_is_no_church_access(world, make_user):
    outsider = make_user(email="outsider@example.com")
    with pytest.raises(Forbidden) as gone:
        with session_scope() as s:
            lock_and_read_actor(s, world["church"], outsider)
    assert (gone.value.message, gone.value.details) == ("You don't have access to this church.", NO_ACCESS)
    churches.soft_delete_church(world["church"])
    with pytest.raises(Forbidden) as deleted:
        _actor_role(world, "owner")
    assert deleted.value.details == NO_ACCESS


def test_require_admin_role():
    church_admin.require_admin_role("owner")
    church_admin.require_admin_role("admin")
    with pytest.raises(Forbidden) as denied:
        church_admin.require_admin_role("member")
    assert (denied.value.message, denied.value.details) == ("Only church admins can do this.", None)


# --- PATCH /church: clean_profile_patch and update_profile (slice 6a-1) ------------------------------

TRANSLATIONS = ("web", "kjv", "asv")


@pytest.mark.parametrize("changes, field, message", [
    ({"name": "   "}, "name", "Church name is required."),
    ({"name": "Gr\x00ace"}, "name", "Church name can't contain line breaks or control characters."),
    ({"name": "Grace\nChurch"}, "name", "Church name can't contain line breaks or control characters."),
    ({"timezone": ""}, "timezone", "Timezone is required."),
    ({"timezone": "Mars/Olympus"}, "timezone", "Unknown timezone."),
    ({"timezone": "America/New York"}, "timezone", "Unknown timezone."),
    ({"timezone": "../etc"}, "timezone", "Unknown timezone."),
    ({"timezone": "america/new_york"}, "timezone", "Unknown timezone."),
    ({"bible_translation": "xyz"}, "bible_translation", "Unknown or unavailable translation."),
    ({"bible_translation": "esv"}, "bible_translation", "Unknown or unavailable translation."),
    ({"default_hymnal": "PH1990"}, "default_hymnal", "Choose one of your church's hymnals."),
    ({"default_hymnal": "PH1990", "bible_translation": "xyz", "timezone": "x", "name": " "}, "name",
     "Church name is required."),
    ({"default_hymnal": "PH1990", "bible_translation": "xyz"}, "bible_translation",
     "Unknown or unavailable translation."),
])
def test_a_bad_field_is_named_and_the_first_in_order_wins(changes, field, message):
    with pytest.raises(InvalidInput) as bad:
        church_admin.clean_profile_patch(changes, translations=TRANSLATIONS, church_hymnals=("GG2013",))
    assert (bad.value.field, bad.value.message) == (field, message)


def test_the_fields_sent_are_cleaned_and_nothing_else():
    clean = church_admin.clean_profile_patch
    assert clean({}, translations=TRANSLATIONS, church_hymnals=()) == ({}, {})
    assert clean({"name": " Example Church ", "timezone": " America/Chicago ", "bible_translation": "kjv",
                  "default_hymnal": "GG2013", "default_benediction": "  Go in peace.\r\nAmen.\r\n"},
                 translations=TRANSLATIONS, church_hymnals=("GG2013",)) == (
        {"name": "Example Church", "timezone": "America/Chicago"},
        {"bible_translation": "kjv", "default_hymnal": "GG2013", "default_benediction": "Go in peace.\nAmen."},
    )
    assert clean({"default_benediction": "   "}, translations=(), church_hymnals=()) == ({}, {"default_benediction": ""})


def _church(world) -> dict:
    return churches.get_church(world["church"])


# Every key the app keeps in churches.settings, plus one it does not know: a profile save changes only its own.
EVERY_SETTING = {
    "bible_translation": "esv",
    "default_hymnal": "HL1955",
    "default_benediction": "Halverson",
    "bulletin": {"phone": "555-0100", "starred": ["call_to_worship"]},
    "rubric": {"prefer_familiar": False},
    "liturgy_prompts": {"benediction": "Go."},
    "prayer_library": {"confession": ["Merciful God, we confess."]},
    "foo": 1,
}


def test_only_the_fields_sent_are_written_and_other_settings_stay(world, monkeypatch):
    monkeypatch.delenv("ESV_API_KEY", raising=False)
    add_hymn(world["church"], hymnal="GG2013", number=1, title="Holy, Holy, Holy")
    churches.update_church(world["church"], settings=EVERY_SETTING)
    stored = church_admin.update_profile(world["church"], world["admin"], {"name": "Example Church Two"})
    assert stored == {"name": "Example Church Two", "role": "admin"}
    church = _church(world)
    assert (church["name"], church["timezone"]) == ("Example Church Two", "America/New_York")
    assert church["settings"] == EVERY_SETTING

    church_admin.update_profile(world["church"], world["owner"], {
        "bible_translation": "kjv", "default_benediction": "Go in peace.", "default_hymnal": "GG2013"})
    assert _church(world)["settings"] == {**EVERY_SETTING, "bible_translation": "kjv",
                                          "default_benediction": "Go in peace.", "default_hymnal": "GG2013"}

    church_admin.update_profile(world["church"], world["owner"], {"default_benediction": ""})
    assert _church(world)["settings"]["default_benediction"] == ""
    assert church_profile.get_church_profile(world["church"]).default_benediction == ""


def test_one_bad_field_writes_nothing(world):
    with pytest.raises(InvalidInput):
        church_admin.update_profile(world["church"], world["owner"],
                                    {"name": "Renamed", "default_benediction": "Go.", "bible_translation": "xyz"})
    church = _church(world)
    assert (church["name"], church["settings"]) == ("Example Church", {})


def test_the_default_hymnal_must_be_one_the_church_has(world):
    add_hymn(world["church"], hymnal="GG2013", number=1, title="Holy, Holy, Holy")
    with pytest.raises(InvalidInput) as bad:
        church_admin.update_profile(world["church"], world["owner"], {"default_hymnal": "PH1990"})
    assert bad.value.field == "default_hymnal"
    church_admin.update_profile(world["church"], world["owner"], {"default_hymnal": "GG2013"})
    assert _church(world)["settings"] == {"default_hymnal": "GG2013"}


def test_a_demoted_admin_or_a_removed_member_writes_nothing(world):
    set_role(world["admin"], world["church"], "member")            # after require_admin read "admin"
    with pytest.raises(Forbidden) as demoted:
        church_admin.update_profile(world["church"], world["admin"], {"name": "Renamed"})
    assert (demoted.value.message, demoted.value.details) == ("Only church admins can do this.", None)
    remove_membership(world["member"], world["church"])
    with pytest.raises(Forbidden) as removed:
        church_admin.update_profile(world["church"], world["member"], {"name": "Renamed"})
    assert removed.value.details == NO_ACCESS
    churches.soft_delete_church(world["church"])
    with pytest.raises(Forbidden) as deleted:
        church_admin.update_profile(world["church"], world["owner"], {"name": "Renamed"})
    assert deleted.value.details == NO_ACCESS
    with session_scope() as s:
        assert s.get(Church, world["church"]).name == "Example Church"


def test_the_profile_is_read_and_written_under_one_row_lock(world):
    with _record_church_row_access() as (reads, writes):
        church_admin.update_profile(world["church"], world["owner"], {"name": "Renamed", "bible_translation": "kjv"})
    assert len(writes) == 1
    assert reads and all(session is writes[0] and locked for session, locked in reads)
