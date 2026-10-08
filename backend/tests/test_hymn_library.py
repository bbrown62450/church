"""usecases.hymn_library (6a spec "Semantics" → POST and PATCH /hymns, POST and
DELETE /hymnals; slice 6a-2): the field rules, the duplicate rule, who may do
what, the bundled hymnals, and every write under the church-row lock with the
caller's role re-read under it."""
from datetime import date

import pytest
from sqlalchemy import select

import hymnary_facts
from db import session_scope
from db.models import Hymn, HymnCatalog
from domain_errors import Conflict, Forbidden, InvalidInput, NotFound
from repos import churches
from repos.hymns import hymnal_summaries, list_hymns
from repos.memberships import add_membership, remove_membership, set_role
from tests.test_church_settings import _record_church_row_access
from tests.test_hymnary_facts import HOLY, FakeFetch
from usecases import hymn_library

NO_ACCESS = {"reason": "no_church_access"}
THIS_YEAR = date.today().year
EMPTY = {"title": None, "number": None, "hymnal": None, "scripture_refs": None, "theme": None, "link": None,
         "text_year": None, "hymnal_count": None}


@pytest.fixture
def world(tmp_db, make_user, make_church):
    owner = make_user(email="owner@example.com")
    admin = make_user(email="admin@example.com")
    member = make_user(email="member@example.com")
    cid = make_church(name="Grace", owner_user_id=owner)
    add_membership(admin, cid, "admin")
    add_membership(member, cid, "member")
    with session_scope() as s:
        for n, title in ((1, "Holy, Holy, Holy"), (2, "Amazing Grace")):
            s.add(Hymn(church_id=cid, hymnal="GG2013", title=title, number=n))
    return {"church": cid, "owner": owner, "admin": admin, "member": member}


def _hymn(**fields) -> dict:
    return {**EMPTY, **fields}


def _add(world, who="member", **fields) -> dict:
    return hymn_library.create_hymn(world["church"], world[who], _hymn(**fields))


def _refused(call, field, message):
    with pytest.raises(InvalidInput) as bad:
        call()
    assert (bad.value.field, bad.value.message) == (field, message)


def _rows(world) -> list[tuple]:
    return [(h["Hymnal"], h["Hymn Number"], h["Hymn Title"]) for h in list_hymns(world["church"])]


def test_a_member_adds_a_hymn_with_tidy_fields_and_blanks_as_null(world):
    added = _add(world, title="  Be Thou\nMy\tVision ", number=339, scripture_refs="  Psalm 16:5;\n John 15:5 ",
                 theme=" ", link=" https://hymnary.org/hymn/GG2013/339 ")
    assert {k: v for k, v in added.items() if k != "id"} == {
        "hymnal": "GG2013", "title": "Be Thou My Vision", "number": 339, "scripture_refs": "Psalm 16:5; John 15:5",
        "theme": None, "link": "https://hymnary.org/hymn/GG2013/339", "text_year": None, "hymnal_count": None}
    bare = _add(world, title="No Number")
    assert (bare["number"], bare["link"], bare["scripture_refs"]) == (None, None, None)


@pytest.mark.parametrize("fields, field, message", [
    ({}, "title", "Hymn title is required."),
    ({"title": " \t\n"}, "title", "Hymn title is required."),
    ({"title": "X", "number": 0}, "number", "Hymn number must be a whole number."),
    ({"title": "X", "number": 100000}, "number", "Hymn number must be a whole number."),
    ({"title": "X", "hymnal": "PH1990"}, "hymnal", "Choose one of your church's hymnals."),
    ({"title": "X", "link": "http://hymnary.org/hymn/GG2013/1"}, "link", "Links must start with https://."),
    ({"title": "X", "link": "https://"}, "link", "Links must start with https://."),
    ({"title": "X", "link": "hymnary.org"}, "link", "Links must start with https://."),
    ({"title": "X", "link": "https://hymnary.org/a b"}, "link", "Links can't contain spaces."),
    ({"title": "X", "text_year": 0}, "text_year", f"Year must be a whole number from 1 to {THIS_YEAR}."),
    ({"title": "X", "text_year": THIS_YEAR + 1}, "text_year", f"Year must be a whole number from 1 to {THIS_YEAR}."),
    ({"title": "X", "hymnal_count": -1}, "hymnal_count", "Number of hymnals must be a whole number from 0 to 100000."),
    ({"title": "X", "hymnal_count": 100001}, "hymnal_count", "Number of hymnals must be a whole number from 0 to 100000."),
])
def test_a_bad_field_is_named_and_nothing_is_added(world, fields, field, message):
    _refused(lambda: _add(world, who="admin", **fields), field, message)
    assert len(_rows(world)) == 2


def test_the_hymnal_defaults_to_the_effective_one_and_a_church_with_none_may_name_one(world, make_church):
    with session_scope() as s:
        s.add(Hymn(church_id=world["church"], hymnal="AA2000", title="First by code", number=1))
    assert _add(world, title="Alphabetical")["hymnal"] == "AA2000"
    churches.update_profile(world["church"], settings_patch={"default_hymnal": "GG2013"})
    assert _add(world, title="Stored default")["hymnal"] == "GG2013"
    assert _add(world, title="Chosen", hymnal=" AA2000 ")["hymnal"] == "AA2000"

    empty = make_church(name="New", owner_user_id=world["owner"])
    assert hymn_library.create_hymn(empty, world["owner"], _hymn(title="First"))["hymnal"] == "GG2013"
    other = make_church(name="Newer", owner_user_id=world["owner"])
    assert hymn_library.create_hymn(other, world["owner"], _hymn(title="First", hymnal="XX_1990"))["hymnal"] == "XX_1990"
    _refused(lambda: hymn_library.create_hymn(make_church(name="N3", owner_user_id=world["owner"]), world["owner"],
                                              _hymn(title="First", hymnal="X")), "hymnal",
             "Choose one of your church's hymnals.")


def test_an_admin_sets_the_year_and_familiarity_and_a_member_may_not(world):
    added = _add(world, who="admin", title="Holy, Holy, Holy! Lord God Almighty", number=138, text_year=1826,
                 hymnal_count=1322)
    assert (added["text_year"], added["hymnal_count"]) == (1826, 1322)
    for facts in ({"text_year": 1826}, {"hymnal_count": 0}):
        with pytest.raises(Forbidden) as denied:
            _add(world, title="Member's", **facts)
        assert (denied.value.message, denied.value.details) == ("Only church admins can do this.", None)
    assert _add(world, title="Member's", text_year=None, hymnal_count=None)["title"] == "Member's"
    assert len(_rows(world)) == 4


def test_the_same_hymnal_number_and_title_words_is_a_409(world):
    with pytest.raises(Conflict) as taken:
        _add(world, title="  holy,  HOLY, holy ", number=1)
    assert taken.value.message == "GG2013 already has #1 holy, HOLY, holy."
    _add(world, title="Untitled Tune")
    with pytest.raises(Conflict) as again:
        _add(world, title="untitled tune")
    assert again.value.message == "GG2013 already has untitled tune."
    assert _add(world, title="Holy, Holy, Holy", number=3)["number"] == 3        # another number is another hymn


def _first(world) -> dict:
    with session_scope() as s:
        h = s.execute(select(Hymn).where(Hymn.church_id == world["church"], Hymn.hymnal == "GG2013",
                                         Hymn.number == 1)).scalar_one()
        h.audio_url = "https://example.org/holy.mp3"
        h.scripture_refs, h.theme, h.hymnary_link = "Isaiah 6:3", "Trinity", "https://hymnary.org/hymn/GG2013/1"
        return {"id": h.id}


def test_an_edit_changes_only_what_is_sent_and_null_clears(world):
    hid = _first(world)["id"]
    edited = hymn_library.update_hymn(world["church"], world["member"], hid, {"title": "Holy, Holy, Holy!"})
    assert (edited["title"], edited["number"], edited["scripture_refs"], edited["theme"], edited["link"]) == (
        "Holy, Holy, Holy!", 1, "Isaiah 6:3", "Trinity", "https://hymnary.org/hymn/GG2013/1")
    cleared = hymn_library.update_hymn(world["church"], world["member"], hid,
                                       {"number": None, "scripture_refs": "", "theme": None, "link": " "})
    assert (cleared["number"], cleared["scripture_refs"], cleared["theme"], cleared["link"]) == (None, None, None, None)
    facts = hymn_library.update_hymn(world["church"], world["admin"], hid, {"text_year": 1826, "hymnal_count": 1322})
    assert (facts["text_year"], facts["hymnal_count"]) == (1826, 1322)
    unknown = hymn_library.update_hymn(world["church"], world["owner"], hid, {"text_year": None})
    assert (unknown["text_year"], unknown["hymnal_count"]) == (None, 1322)
    with session_scope() as s:
        assert s.get(Hymn, hid).audio_url == "https://example.org/holy.mp3"


def test_an_edit_checks_its_fields_the_hymnal_and_duplicates_but_not_itself(world):
    hid = _first(world)["id"]
    for changes, field, message in (({"title": None}, "title", "Hymn title is required."),
                                    ({"title": "  "}, "title", "Hymn title is required."),
                                    ({"hymnal": None}, "hymnal", "Choose one of your church's hymnals."),
                                    ({"hymnal": "PH1990"}, "hymnal", "Choose one of your church's hymnals."),
                                    ({"number": 100000}, "number", "Hymn number must be a whole number.")):
        _refused(lambda: hymn_library.update_hymn(world["church"], world["member"], hid, changes), field, message)
    with pytest.raises(Conflict) as taken:
        hymn_library.update_hymn(world["church"], world["member"], hid, {"title": "amazing grace", "number": 2})
    assert taken.value.message == "GG2013 already has #2 amazing grace."
    same = hymn_library.update_hymn(world["church"], world["member"], hid, {"title": "HOLY, HOLY,  HOLY"})
    assert same["title"] == "HOLY, HOLY, HOLY"                                 # itself: no conflict
    with session_scope() as s:
        s.add(Hymn(church_id=world["church"], hymnal="PH1990", title="Holy, Holy, Holy", number=1))
        s.add(Hymn(church_id=world["church"], hymnal="GG2013", title="Holy, Holy, Holy", number=1))   # an old twin
    moved = hymn_library.update_hymn(world["church"], world["member"], hid, {"hymnal": "PH1990", "number": 5})
    assert (moved["hymnal"], moved["number"]) == ("PH1990", 5)
    twin = hymn_library.update_hymn(world["church"], world["member"], hid, {"scripture_refs": "Revelation 4:8"})
    assert twin["scripture_refs"] == "Revelation 4:8"                          # no key change: no duplicate check


def test_an_edit_of_an_old_hymn_with_a_blank_title_is_never_a_duplicate(world):
    with session_scope() as s:
        blank = [Hymn(church_id=world["church"], hymnal="GG2013", title=title, number=n)
                 for n, title in ((5, None), (6, " "), (7, ""))]
        s.add_all(blank)
        s.flush()
        ids = [h.id for h in blank]
    for hid in ids[1:]:
        moved = hymn_library.update_hymn(world["church"], world["member"], hid, {"number": 5})
        assert (moved["number"], moved["title"]) == (5, "")
    assert sorted(h["Hymn Number"] for h in list_hymns(world["church"]) if not (h["Hymn Title"] or "").strip()) == [
        5, 5, 5]


def test_a_member_may_not_send_the_year_or_familiarity_even_as_null(world):
    hid = _first(world)["id"]
    for changes in ({"text_year": 1826}, {"text_year": None}, {"hymnal_count": None, "title": "Renamed"}):
        with pytest.raises(Forbidden) as denied:
            hymn_library.update_hymn(world["church"], world["member"], hid, changes)
        assert (denied.value.message, denied.value.details) == ("Only church admins can do this.", None)
    assert ("GG2013", 1, "Holy, Holy, Holy") in _rows(world)


def test_a_hand_entered_year_survives_the_backfill(world):
    hid = hymn_library.create_hymn(world["church"], world["admin"],
                                   _hymn(title=HOLY["title"], number=138, scripture_refs="Isaiah 6:3",
                                         text_year=1800))["id"]
    stats = hymnary_facts.run_backfill(FakeFetch({"Isaiah 6:3": {"Holy": HOLY}}))
    assert stats["updated"] == 1
    with session_scope() as s:
        holy = s.get(Hymn, hid)
        assert (holy.text_year, holy.hymnal_count) == (1800, 1322)


def test_only_admins_delete_a_hymn_and_an_unknown_or_another_churchs_is_not_found(world, make_church):
    hid = _first(world)["id"]
    with pytest.raises(Forbidden) as denied:
        hymn_library.delete_hymn(world["church"], world["member"], hid)
    assert denied.value.message == "Only church admins can do this."
    other = make_church(name="Other", owner_user_id=world["owner"])
    theirs = hymn_library.create_hymn(other, world["owner"], _hymn(title="Theirs"))["id"]
    for call in (lambda: hymn_library.delete_hymn(world["church"], world["owner"], theirs),
                 lambda: hymn_library.update_hymn(world["church"], world["owner"], theirs, {"text_year": 2000})):
        with pytest.raises(NotFound) as missing:
            call()
        assert missing.value.message == "Hymn not found."
    hymn_library.delete_hymn(world["church"], world["admin"], hid)
    with pytest.raises(NotFound):
        hymn_library.delete_hymn(world["church"], world["admin"], hid)
    assert _rows(world) == [("GG2013", 2, "Amazing Grace")]
    assert [h["Hymn Title"] for h in list_hymns(other)] == ["Theirs"]


def test_adding_ph1990_inserts_605_once_and_an_unknown_code_is_refused(world):
    assert hymn_library.add_hymnal(world["church"], world["admin"], "PH1990") == {
        "code": "PH1990", "label": "The Presbyterian Hymnal (1990)", "inserted": 605, "updated": 0}
    assert hymn_library.add_hymnal(world["church"], world["owner"], " PH1990 ")["inserted"] == 0
    assert [(h.code, h.hymn_count) for h in hymnal_summaries(world["church"])] == [("GG2013", 2), ("PH1990", 605)]
    _refused(lambda: hymn_library.add_hymnal(world["church"], world["owner"], "XX2000"), "code",
             "That hymnal isn't available to add.")


def test_catalog_hymnals_are_sources_and_present_follows_the_church(world, make_user, make_church):
    church_a = make_church(name="A", owner_user_id=world["owner"])
    with session_scope() as s:
        for n in (1, 2, 3):
            s.add(HymnCatalog(hymnal="GG2013", title=f"Catalog {n}", number=n, scripture_refs="Psalm 1",
                              text_year=1900 + n))
    church_b = churches.create_church(name="B", timezone="UTC", owner_user_id=make_user(email="b@example.com"))
    by_code = lambda church: {s["code"]: s for s in hymn_library.list_sources(church)}   # noqa: E731
    assert by_code(church_a)["GG2013"] == {"code": "GG2013", "label": "Glory to God (2013)", "hymn_count": 3,
                                           "has_scripture_refs": True, "present": False}
    assert by_code(church_a)["PH1990"] == {"code": "PH1990", "label": "The Presbyterian Hymnal (1990)",
                                           "hymn_count": 605, "has_scripture_refs": False, "present": False}
    assert by_code(church_b)["GG2013"]["present"] is True
    assert hymn_library.add_hymnal(church_a, world["owner"], "GG2013")["inserted"] == 3
    assert by_code(church_a)["GG2013"]["present"] is True
    assert sorted(h["Hymn Number"] for h in list_hymns(church_a)) == [1, 2, 3]


def test_a_source_is_present_only_once_the_church_has_as_many_hymns_in_it(world):
    """6a-2 build review M4: one hand-entered PH1990 hymn does not mark the whole bundled PH1990 added."""
    with session_scope() as s:
        s.add(Hymn(church_id=world["church"], hymnal="PH1990", title="Hand Entered", number=999))
    present = lambda: {s["code"]: s["present"] for s in hymn_library.list_sources(world["church"])}   # noqa: E731
    assert present()["PH1990"] is False
    assert hymn_library.add_hymnal(world["church"], world["owner"], "PH1990")["inserted"] == 605
    assert present()["PH1990"] is True


def test_removing_a_hymnal_deletes_only_its_hymns_but_never_the_only_or_the_default(world, make_church):
    other = make_church(name="Other", owner_user_id=world["owner"])
    hymn_library.add_hymnal(other, world["owner"], "PH1990")
    with pytest.raises(Conflict) as only:
        hymn_library.remove_hymnal(other, world["owner"], "PH1990")
    assert only.value.message == "You can't remove your only hymnal."
    hymn_library.add_hymnal(world["church"], world["owner"], "PH1990")
    with pytest.raises(Conflict) as default:
        hymn_library.remove_hymnal(world["church"], world["owner"], "GG2013")            # alphabetical first
    assert default.value.message == ("GG2013 is your default hymnal. Choose a different default in Church "
                                     "profile first.")
    churches.update_profile(world["church"], settings_patch={"default_hymnal": "PH1990"})
    with pytest.raises(Conflict):
        hymn_library.remove_hymnal(world["church"], world["owner"], "PH1990")
    churches.update_profile(world["church"], settings_patch={"default_hymnal": "GG2013"})
    with pytest.raises(NotFound) as missing:
        hymn_library.remove_hymnal(world["church"], world["owner"], "XX2000")
    assert missing.value.message == "Your church doesn't have that hymnal."
    assert hymn_library.remove_hymnal(world["church"], world["admin"], "PH1990") == 605
    assert [h.code for h in hymnal_summaries(world["church"])] == ["GG2013"]
    assert [(h.code, h.hymn_count) for h in hymnal_summaries(other)] == [("PH1990", 605)]


def test_a_member_a_demoted_admin_or_a_removed_member_writes_nothing(world):
    hymn_library.add_hymnal(world["church"], world["owner"], "PH1990")
    hid = _first(world)["id"]
    admin_writes = (lambda who: hymn_library.delete_hymn(world["church"], world[who], hid),
                    lambda who: hymn_library.add_hymnal(world["church"], world[who], "PH1990"),
                    lambda who: hymn_library.remove_hymnal(world["church"], world[who], "PH1990"),
                    lambda who: hymn_library.update_hymn(world["church"], world[who], hid, {"text_year": 1826}),
                    lambda who: _add(world, who=who, title="Facts", hymnal_count=5))
    set_role(world["admin"], world["church"], "member")            # after require_admin read "admin"
    for who in ("member", "admin"):
        for write in admin_writes:
            with pytest.raises(Forbidden) as denied:
                write(who)
            assert (denied.value.message, denied.value.details) == ("Only church admins can do this.", None)
    assert _add(world, who="admin", title="Still a member")["title"] == "Still a member"
    remove_membership(world["member"], world["church"])
    with pytest.raises(Forbidden) as removed:
        _add(world, title="Gone")
    assert removed.value.details == NO_ACCESS
    churches.soft_delete_church(world["church"])
    for write in (lambda: _add(world, who="owner", title="Deleted"),
                  lambda: hymn_library.update_hymn(world["church"], world["owner"], hid, {"title": "X"}),
                  lambda: hymn_library.remove_hymnal(world["church"], world["owner"], "PH1990")):
        with pytest.raises(Forbidden) as deleted:
            write()
        assert deleted.value.details == NO_ACCESS
    assert len(list_hymns(world["church"])) == 608


def test_each_write_reads_the_church_row_under_its_lock(world):
    hid = _first(world)["id"]
    for write in (lambda: _add(world, title="Locked"),
                  lambda: hymn_library.update_hymn(world["church"], world["member"], hid, {"title": "Locked 2"}),
                  lambda: hymn_library.add_hymnal(world["church"], world["owner"], "PH1990"),
                  lambda: hymn_library.remove_hymnal(world["church"], world["owner"], "PH1990"),
                  lambda: hymn_library.delete_hymn(world["church"], world["owner"], hid)):
        with _record_church_row_access() as (reads, _writes):
            write()
        assert reads and reads[0][1] is True, reads
        assert {session for session, _locked in reads} == {reads[0][0]}
