"""The church-row lock and the role re-read every church write starts with
(6a spec, "Semantics" → Locking; 6b spec, `lock_and_read_actor`), and
`usecases.church_admin` (slices 6a-1 and 6a-3a)."""
import datetime

import pytest

import liturgy_prompts
import service_rubric
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
    ({"name": "Gr\uffffce"}, "name", "Church name can't contain line breaks or control characters."),
    ({"name": "Grace\ufffe"}, "name", "Church name can't contain line breaks or control characters."),
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


def test_the_benediction_is_stored_word_safe():
    """6a-1 code review m3: what is stored is what prints (archive._xml_safe, as the bulletin settings' texts)."""
    clean = church_admin.clean_profile_patch
    sent = {"default_benediction": " Go\x00 in\x0bpeace.\x0cAmen\x07.\ufffe\uffff\r\n"}
    assert clean(sent, translations=(), church_hymnals=()) == ({}, {"default_benediction": "Go in\npeace.\nAmen."})


def test_a_hymnal_code_is_matched_trimmed_and_the_churchs_own_code_is_stored():
    """6a-1 code review m6: a code imported with spaces around it can still be chosen."""
    clean = church_admin.clean_profile_patch
    assert clean({"default_hymnal": "UMH"}, translations=(), church_hymnals=(" UMH ", "GG2013")) == (
        {}, {"default_hymnal": " UMH "})
    assert clean({"default_hymnal": " GG2013 "}, translations=(), church_hymnals=(" GG2013", "GG2013")) == (
        {}, {"default_hymnal": "GG2013"})
    with pytest.raises(InvalidInput):
        clean({"default_hymnal": " "}, translations=(), church_hymnals=("  ",))


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


# --- Liturgy prompts: get_prompts and save_prompts (slice 6a-3a) ----------------------------------------------

DEFAULTS = liturgy_prompts.default_prompts()
PROMPT_ORDER = ["system", "call_to_worship", "opening_prayer", "prayer_of_confession", "assurance",
                "prayer_for_illumination", "prayers_of_the_people", "offertory_prayer", "benediction"]


def _stored_prompts(world) -> dict:
    return churches.get_church_prompts(world["church"])


def test_the_prompts_read_every_default_and_only_the_churchs_own_wording(world):
    churches.update_church(world["church"], settings={"liturgy_prompts": {
        "benediction": "Go in peace. {occasion}",
        "offertory_prayer": "  " + DEFAULTS["offertory_prayer"] + " \r\n",
        "assurance": "   ",
        "bogus": "x",
    }})
    read = church_admin.get_prompts(world["church"], can_edit=False)
    assert read["placeholder_help"] == liturgy_prompts.PLACEHOLDER_HELP
    assert read["can_edit"] is False
    assert [f["key"] for f in read["fields"]] == PROMPT_ORDER
    assert [f["label"] for f in read["fields"]] == [
        "Overall voice", "Call to Worship", "Opening Prayer", "Prayer of Confession", "Assurance of Pardon",
        "Prayer for Illumination", "Prayers of the People", "Offertory Prayer", "Benediction"]
    assert all(f["default"] == DEFAULTS[f["key"]] for f in read["fields"])
    assert {f["key"]: (f["override"], f["customized"]) for f in read["fields"] if f["override"] is not None} == {
        "benediction": ("Go in peace. {occasion}", True)}
    assert church_admin.get_prompts(world["church"], can_edit=True)["can_edit"] is True
    churches.update_church(world["church"], settings={"liturgy_prompts": ["not", "an", "object"]})
    assert not any(f["customized"] for f in church_admin.get_prompts(world["church"], can_edit=True)["fields"])


def test_a_save_keeps_only_wording_that_differs_from_the_defaults(world):
    churches.update_church(world["church"], settings=EVERY_SETTING)
    read = church_admin.save_prompts(world["church"], world["admin"], {
        "system": DEFAULTS["system"],
        "benediction": "  Go in peace.\r\nServe the Lord.\r\n",
        "assurance": "   ",
        "offertory_prayer": "\r\n " + DEFAULTS["offertory_prayer"] + "\r\n",
        "call_to_worship": "{{Leader}}: Come, {unknown_name}.",
    })
    stored = {"benediction": "Go in peace.\nServe the Lord.", "call_to_worship": "{{Leader}}: Come, {unknown_name}."}
    assert _stored_prompts(world) == stored
    assert read["can_edit"] is True
    assert {f["key"]: f["override"] for f in read["fields"] if f["customized"]} == stored
    assert _church(world)["settings"] == {**EVERY_SETTING, "liturgy_prompts": stored}

    church_admin.save_prompts(world["church"], world["owner"], {"system": "Our {own} voice {."})
    assert _stored_prompts(world) == {"system": "Our {own} voice {."}         # sent as written: braces are fine
    church_admin.save_prompts(world["church"], world["owner"], {})
    assert _stored_prompts(world) == {}
    assert _church(world)["settings"] == {**EVERY_SETTING, "liturgy_prompts": {}}


@pytest.mark.parametrize("template, reason", [
    ("{curly", liturgy_prompts.UNPAIRED_BRACE),
    ("{0}", liturgy_prompts.NO_NAME),
    ("Go }", liturgy_prompts.UNPAIRED_BRACE),
    ('{"a": 1}', liturgy_prompts.NOT_ONE_WORD),
    ("{foo.bar}", liturgy_prompts.NOT_PLAIN_NAME),
    ("{occasion!r}", liturgy_prompts.HAS_SPEC),
])
def test_a_section_template_that_cannot_be_filled_is_named_and_nothing_is_saved(world, template, reason):
    churches.set_church_prompts(world["church"], {"system": "Kept."})
    with pytest.raises(InvalidInput) as bad:
        church_admin.save_prompts(world["church"], world["owner"], {"system": "Changed.", "benediction": template})
    assert (bad.value.code, bad.value.field, bad.value.message) == (
        "prompt_invalid", "prompts.benediction", f"Benediction prompt: {reason}")
    assert _stored_prompts(world) == {"system": "Kept."}


def test_the_first_bad_prompt_in_order_is_named(world):
    with pytest.raises(InvalidInput) as bad:
        church_admin.save_prompts(world["church"], world["owner"],
                                  {"benediction": "{curly", "call_to_worship": "{0}"})
    assert (bad.value.field, bad.value.message) == (
        "prompts.call_to_worship", f"Call to Worship prompt: {liturgy_prompts.NO_NAME}")
    assert church_admin.prompt_label("system") == "Overall voice"


def test_a_demoted_admin_or_a_removed_member_saves_no_prompts(world):
    set_role(world["admin"], world["church"], "member")            # after require_admin read "admin"
    with pytest.raises(Forbidden) as demoted:
        church_admin.save_prompts(world["church"], world["admin"], {"benediction": "Go."})
    assert (demoted.value.message, demoted.value.details) == ("Only church admins can do this.", None)
    remove_membership(world["member"], world["church"])
    with pytest.raises(Forbidden) as removed:
        church_admin.save_prompts(world["church"], world["member"], {"benediction": "Go."})
    assert removed.value.details == NO_ACCESS
    churches.soft_delete_church(world["church"])
    with pytest.raises(Forbidden) as deleted:
        church_admin.save_prompts(world["church"], world["owner"], {"benediction": "Go."})
    assert deleted.value.details == NO_ACCESS
    with session_scope() as s:
        assert (s.get(Church, world["church"]).settings or {}) == {}


def test_the_prompts_are_read_and_written_under_one_row_lock(world):
    with _record_church_row_access() as (reads, writes):
        church_admin.save_prompts(world["church"], world["owner"], {"benediction": "Go."})
    assert len(writes) == 1
    in_the_write = [locked for session, locked in reads if session is writes[0]]
    assert in_the_write and all(in_the_write)


# --- The service rubric: get_rubric and update_rubric (slice 6a-3a) ---------------------------------------------

THIS_YEAR = datetime.date.today().year


@pytest.mark.parametrize("patch, message", [
    (["not", "an", "object"], "The rubric update must be an object."),
    ({"hymns": ["x"]}, "'hymns' must be an object of checklists."),
    ({"prayers": {"sermon": ["x"]}}, "Unknown prayers checklist: 'sermon'."),
    ({"hymns": {"closing": []}}, "A checklist must be a non-empty list of points."),
    ({"hymns": {"closing": ["x"] * 13}}, "A checklist can have at most 12 points."),
    ({"hymns": {"closing": ["x", "  "]}}, "Each checklist point must be non-empty text."),
    ({"prayers": {"benediction": ["Go\x07 in peace"]}}, "Checklist points cannot contain control characters."),
    ({"prayers": {"benediction": ["x" * 301]}}, "Each checklist point must be at most 300 characters."),
    ({"prefer_before_year": 1499}, f"The preferred year must be between 1500 and {THIS_YEAR}."),
    ({"prefer_before_year": THIS_YEAR + 1}, f"The preferred year must be between 1500 and {THIS_YEAR}."),
    ({"prefer_familiar": "yes"}, "prefer_familiar must be true or false."),
    ({"prefer_older": True}, "Unknown rubric setting: 'prefer_older'."),
])
def test_a_bad_rubric_patch_is_invalid_rubric_with_its_message_and_writes_nothing(world, patch, message):
    churches.update_church_rubric(world["church"], {"prefer_familiar": False})
    with pytest.raises(InvalidInput) as bad:
        church_admin.update_rubric(world["church"], world["owner"], patch)
    assert (bad.value.code, bad.value.field, bad.value.message) == ("invalid_rubric", None, message)
    assert churches.get_church_rubric_overrides(world["church"]) == {"prefer_familiar": False}


def test_a_rubric_change_and_a_reset_answer_what_is_stored_with_the_defaults(world):
    churches.update_church(world["church"], settings=EVERY_SETTING)
    out = church_admin.update_rubric(world["church"], world["admin"], {
        "prayers": {"benediction": ["  Sends   the people\nout. "]}, "prefer_before_year": 1900})
    assert out["defaults"] == service_rubric.default_rubric()
    assert out["rubric"]["prayers"]["benediction"] == ["Sends the people out."]
    assert (out["rubric"]["prefer_before_year"], out["rubric"]["prefer_familiar"]) == (1900, False)
    assert out["customized"] == ["prayers.benediction", "prefer_before_year", "prefer_familiar"]
    assert church_admin.get_rubric(world["church"]) == out
    assert _church(world)["settings"] == {**EVERY_SETTING, "rubric": {
        "prefer_familiar": False, "prayers": {"benediction": ["Sends the people out."]}, "prefer_before_year": 1900}}

    out = church_admin.update_rubric(world["church"], world["owner"], {
        "prayers": {"benediction": None}, "prefer_before_year": None, "prefer_familiar": None})
    assert out == {"rubric": service_rubric.default_rubric(), "customized": [],
                   "defaults": service_rubric.default_rubric()}
    assert _church(world)["settings"] == {**EVERY_SETTING, "rubric": {}}


def test_a_stored_rubric_that_is_not_an_object_reads_as_the_defaults(world):
    churches.update_church(world["church"], settings={"rubric": ["junk"], "foo": 1})
    assert church_admin.get_rubric(world["church"])["customized"] == []
    out = church_admin.update_rubric(world["church"], world["owner"], {"hymns": {"closing": ["Joyful."]}})
    assert out["customized"] == ["hymns.closing"]
    assert _church(world)["settings"] == {"rubric": {"hymns": {"closing": ["Joyful."]}}, "foo": 1}


def test_a_demoted_admin_or_a_removed_member_changes_no_rubric(world):
    set_role(world["admin"], world["church"], "member")            # after require_admin read "admin"
    with pytest.raises(Forbidden) as demoted:
        church_admin.update_rubric(world["church"], world["admin"], {"prefer_familiar": False})
    assert (demoted.value.message, demoted.value.details) == ("Only church admins can do this.", None)
    with pytest.raises(Forbidden):                                  # the role first, before the patch is read
        church_admin.update_rubric(world["church"], world["admin"], {"prefer_before_year": 1})
    remove_membership(world["member"], world["church"])
    with pytest.raises(Forbidden) as removed:
        church_admin.update_rubric(world["church"], world["member"], {"prefer_familiar": False})
    assert removed.value.details == NO_ACCESS
    churches.soft_delete_church(world["church"])
    with pytest.raises(Forbidden) as deleted:
        church_admin.update_rubric(world["church"], world["owner"], {"prefer_familiar": False})
    assert deleted.value.details == NO_ACCESS
    with session_scope() as s:
        assert (s.get(Church, world["church"]).settings or {}) == {}


def test_the_rubric_is_read_and_written_under_one_row_lock(world):
    with _record_church_row_access() as (reads, writes):
        church_admin.update_rubric(world["church"], world["owner"], {"prefer_familiar": False})
    assert len(writes) == 1
    in_the_write = [locked for session, locked in reads if session is writes[0]]
    assert in_the_write and all(in_the_write)
