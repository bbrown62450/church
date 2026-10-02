"""usecases.archive's saving, opening, listing and deleting (slice 5a spec,
Backend "usecases/archive.py", Testing `test_archive_usecase.py`; owner
answers 4 and 6, 2026-10-01). SQLite (`tmp_db`); the row lock and the
concurrent saves are in test_services_postgres.py."""
import logging
import re
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from db import session_scope
from db.models import Church, Hymn, HymnUsage, Service
from domain_errors import Conflict, InvalidInput, NotFound
from hymn_usage import record_usage
from repos.services import DATED_PREFIX
from service_output import CustomElement, normalize_date_iso
from usecases import archive
from usecases.liturgy import HymnRefData

GONE = "That service is no longer in the archive."
HYMN_GONE = "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step."
D = date(2026, 10, 4)


@pytest.fixture
def pastor(make_user):
    return make_user(email="pastor@example.com", name="Pastor Ann")


@pytest.fixture
def church(pastor, make_church):
    return make_church(name="Grace", owner_user_id=pastor)


def add_hymn(church_id, title="Holy, Holy, Holy", number=138, hymnal="GG2013"):
    with session_scope() as s:
        row = Hymn(church_id=church_id, hymnal=hymnal, title=title, number=number)
        s.add(row)
        s.flush()
        return row.id


def snapshot(title, number=None, hymnal=None):
    return HymnRefData(None, title, number, hymnal)


def service(**kw):
    base = dict(service_date=D, occasion=" World Communion Sunday ", scriptures=("Isaiah 5:1-7", " "),
                hymns={"opening": snapshot("Old Favorite", 12, "PH1990"), "response": None, "closing": None},
                liturgy={"call_to_worship": " Come. ", "opening_prayer": "  ",
                         "offertory_prayer": "[Error generating offertory_prayer: timeout]",
                         "benediction": "Go in peace."},
                sermon_title="Living Water", include_communion=True,
                custom_elements=(CustomElement("Anthem", "Choir", "sermon"),))
    return archive.ServiceInput(**{**base, **kw})


def stored(service_id):
    with session_scope() as s:
        row = s.get(Service, service_id)
        return None if row is None else {c: getattr(row, c) for c in (
            "service_date_iso", "service_date_display", "occasion", "scriptures", "hymns", "liturgy", "hymnal",
            "custom_elements", "include_communion", "created_by", "saved_at")}


def usage(church_id, date_iso="2026-10-04"):
    with session_scope() as s:
        return sorted(s.execute(select(HymnUsage.hymn_number, HymnUsage.hymn_title).where(
            HymnUsage.church_id == church_id, HymnUsage.date_iso == date_iso)).all(), key=lambda r: r[1])


def set_default_hymnal(church_id, code):
    with session_scope() as s:
        s.get(Church, church_id).settings = {"default_hymnal": code}


# --- create ---------------------------------------------------------------------

def test_create_writes_three_slots_the_display_date_and_the_8_sections(church, pastor):
    hymn_id = add_hymn(church)
    record = archive.create_service(church, pastor, service(hymns={
        "opening": HymnRefData(hymn_id, "Client's Copy", 1, None), "response": None,
        "closing": snapshot("Old Favorite", 12, "PH1990")}))
    row = stored(record.id)
    assert row["hymns"] == [
        {"slot": "opening", "title": "Holy, Holy, Holy", "number": 138, "hymn_id": str(hymn_id), "hymnal": "GG2013"},
        {"slot": "response", "title": "", "number": None, "hymn_id": None, "hymnal": None},
        {"slot": "closing", "title": "Old Favorite", "number": 12, "hymn_id": None, "hymnal": "PH1990"},
    ]
    assert (row["service_date_iso"], row["service_date_display"]) == ("2026-10-04", "October 04, 2026")
    assert row["occasion"] == "World Communion Sunday" and row["scriptures"] == ["Isaiah 5:1-7"]
    # Only non-blank sections, no error text; the Benediction and communion as sent (owner answer 4).
    assert row["liturgy"] == {"call_to_worship": "Come.", "benediction": "Go in peace."}
    assert row["include_communion"] is True
    assert row["custom_elements"] == [{"label": "Anthem", "text": "Choir", "insert_after": "sermon"}]
    assert row["created_by"] == pastor
    assert record.created_by == archive.Author(pastor, "Pastor Ann")
    assert record.hymns["opening"] == archive.ArchivedHymnData(hymn_id, "Holy, Holy, Holy", 138, "GG2013", True)
    assert record.hymns["closing"] == archive.ArchivedHymnData(None, "Old Favorite", 12, "PH1990", False)
    assert record.saved_at.endswith("+00:00")


def test_a_null_hymnal_is_stored_as_the_church_s_effective_hymnal(church, pastor, make_church):
    add_hymn(church, hymnal="GG2013")
    add_hymn(church, title="Be Thou My Vision", number=339, hymnal="PH1990")
    assert stored(archive.create_service(church, pastor, service()).id)["hymnal"] == "GG2013"   # first code
    set_default_hymnal(church, "PH1990")
    assert stored(archive.create_service(church, pastor, service()).id)["hymnal"] == "PH1990"   # the default
    assert stored(archive.create_service(church, pastor, service(hymnal="  Mine ")).id)["hymnal"] == "Mine"
    empty = make_church(name="No Hymns", owner_user_id=pastor)
    assert stored(archive.create_service(empty, pastor, service()).id)["hymnal"] is None


def test_a_hymn_the_church_lacks_or_a_blank_label_writes_nothing(church, pastor, make_church):
    theirs = add_hymn(make_church(name="Hope"))
    for bad, error in (
        (service(hymns={"response": HymnRefData(theirs, "Theirs", 1, None)}), NotFound),
        (service(hymns={"response": HymnRefData(uuid.uuid4(), "Gone", 1, None)}), NotFound),
        (service(custom_elements=(CustomElement("A", "", "end"), CustomElement("  ", "x", "end"))), InvalidInput),
    ):
        with pytest.raises(error) as info:
            archive.create_service(church, pastor, bad)
        if error is NotFound:
            assert (info.value.message, info.value.details) == (HYMN_GONE, {"field": "hymns.response.hymn_id"})
        else:
            assert info.value.field == "custom_elements.1.label"
    with session_scope() as s:
        assert s.execute(select(func.count()).select_from(Service)).scalar_one() == 0


def test_a_failed_usage_rebuild_rolls_the_save_back(church, pastor, monkeypatch):
    record_usage(church, "2026-10-04", [{"title": "Prepared", "number": 1}])

    def broken(*_a, **_k):
        raise RuntimeError("rebuild failed")

    monkeypatch.setattr(archive, "rebuild_usage_for_date", broken)
    with pytest.raises(RuntimeError):
        archive.create_service(church, pastor, service())
    with session_scope() as s:
        assert s.execute(select(func.count()).select_from(Service)).scalar_one() == 0
    assert usage(church) == [(1, "Prepared")]


# --- hymn use (owner answer 6) ---------------------------------------------------

def test_saving_records_the_date_s_union_and_replaces_prepared_rows(church, pastor):
    record_usage(church, "2026-10-04", [{"title": "Prepared Only", "number": 1}])
    archive.create_service(church, pastor, service())
    assert usage(church) == [(12, "Old Favorite")]
    archive.create_service(church, pastor, service(hymns={"opening": snapshot("Early Hymn", 5)}))
    assert usage(church) == [(5, "Early Hymn"), (12, "Old Favorite")]


def test_deleting_recalculates_the_date_from_the_services_left(church, pastor):
    keep = archive.create_service(church, pastor, service())
    gone = archive.create_service(church, pastor, service(hymns={"opening": snapshot("Early Hymn", 5)}))
    archive.delete_service(church, gone.id)
    assert stored(gone.id) is None and stored(keep.id) is not None
    assert usage(church) == [(12, "Old Favorite")]
    archive.delete_service(church, keep.id)
    assert usage(church) == []


def test_deleting_an_undated_service_changes_no_hymn_use(church, pastor):
    record_usage(church, "2026-10-04", [{"title": "Kept", "number": 1}])
    with session_scope() as s:
        row = Service(church_id=church, service_date_iso="", service_date_display="", occasion="Old",
                      scriptures=[], hymns=[{"title": "Kept", "number": 1}], liturgy={})
        s.add(row)
        s.flush()
        undated = row.id
    archive.delete_service(church, undated)
    assert stored(undated) is None
    assert usage(church) == [(1, "Kept")]


def test_moving_a_service_to_another_date_rebuilds_both_dates(church, pastor):
    record = archive.create_service(church, pastor, service())
    moved = archive.replace_service(church, record.id, service(service_date=date(2026, 10, 11)),
                                    if_match=record.saved_at)
    assert moved.service_date_iso == "2026-10-11"
    assert usage(church) == []
    assert usage(church, "2026-10-11") == [(12, "Old Favorite")]


# --- replace (If-Match) ------------------------------------------------------------

def test_replace_is_a_full_replace_that_keeps_the_author_and_moves_saved_at(church, pastor):
    record = archive.create_service(church, pastor, service())
    again = archive.replace_service(church, record.id, service(
        occasion="Changed", liturgy={}, custom_elements=(), include_communion=False,
        hymns={"closing": snapshot("Closing Hymn", 3)}), if_match=record.saved_at)
    row = stored(record.id)
    assert (row["occasion"], row["liturgy"], row["custom_elements"], row["include_communion"]) == (
        "Changed", {}, [], False)
    assert [h["title"] for h in row["hymns"]] == ["", "", "Closing Hymn"]
    assert row["created_by"] == pastor and again.created_by == record.created_by
    assert again.saved_at > record.saved_at
    assert usage(church) == [(3, "Closing Hymn")]


@pytest.mark.parametrize("header", [
    lambda saved: saved,
    lambda saved: f'"{saved}"',
    lambda saved: f'W/"{saved}"',
    lambda saved: saved.replace("+00:00", "Z"),
    lambda saved: datetime.fromisoformat(saved).astimezone(timezone(timedelta(hours=-4))).isoformat(),
])
def test_if_match_accepts_the_saved_at_in_any_spelling(church, pastor, header):
    record = archive.create_service(church, pastor, service())
    assert archive.replace_service(church, record.id, service(), if_match=header(record.saved_at)).id == record.id


def test_the_check_order_is_404_then_422_then_409_then_the_input(church, pastor):
    record = archive.create_service(church, pastor, service())
    blank_label = service(custom_elements=(CustomElement(" ", "", "end"),))
    with pytest.raises(NotFound) as gone:
        archive.replace_service(church, uuid.uuid4(), blank_label, if_match=None)
    assert (gone.value.message, gone.value.details) == (GONE, None)
    for value, message in ((None, "If-Match is required."), ("  ", "If-Match is required."),
                           ("yesterday", "If-Match must be the service's saved_at timestamp.")):
        with pytest.raises(InvalidInput) as missing:
            archive.replace_service(church, record.id, blank_label, if_match=value)
        assert (missing.value.code, missing.value.message) == ("invalid_request", message)
    stale = (datetime.fromisoformat(record.saved_at) - timedelta(microseconds=1)).isoformat()
    with pytest.raises(Conflict) as conflict:
        archive.replace_service(church, record.id, blank_label, if_match=stale)
    assert conflict.value.message == "This service was changed by someone else. Reload it to see their changes."
    assert conflict.value.details == {"current_saved_at": record.saved_at}
    with pytest.raises(InvalidInput) as label:
        archive.replace_service(church, record.id, blank_label, if_match=record.saved_at)
    assert label.value.field == "custom_elements.0.label"
    assert stored(record.id)["occasion"] == "World Communion Sunday"        # nothing was written


def test_if_match_star_saves_over_any_version_and_a_list_is_unreadable(church, pastor):
    record = archive.create_service(church, pastor, service())
    archive.replace_service(church, record.id, service(), if_match=record.saved_at)     # record.saved_at is stale now
    for star in ("*", ' * '):
        assert archive.replace_service(church, record.id, service(), if_match=star).id == record.id
    with pytest.raises(NotFound):
        archive.replace_service(church, uuid.uuid4(), service(), if_match="*")          # "*" needs the row
    with pytest.raises(InvalidInput) as several:
        archive.replace_service(church, record.id, service(), if_match=f'"{record.saved_at}", "{record.saved_at}"')
    assert several.value.message == "If-Match must be the service's saved_at timestamp."


def test_another_church_s_service_is_not_found(church, pastor, make_church):
    record = archive.create_service(church, pastor, service())
    other = make_church(name="Hope")
    for call in (lambda: archive.get_service(other, record.id),
                 lambda: archive.replace_service(other, record.id, service(), if_match=record.saved_at),
                 lambda: archive.delete_service(other, record.id)):
        with pytest.raises(NotFound) as info:
            call()
        assert info.value.message == GONE
    assert stored(record.id) is not None
    assert archive.list_services(other, limit=20, offset=0).total == 0


# --- get: stored data normalized (5a spec, "Normalizing stored data") -------------

def legacy_row(church_id, **kw):
    base = dict(church_id=church_id, service_date_iso="2026-09-27", service_date_display="September 27, 2026",
                occasion="Pentecost 17", scriptures=["Psalm 25", 7], hymns=[], liturgy={}, sermon_title=None,
                selected_ot_ref=None, selected_nt_ref=None)
    with session_scope() as s:
        row = Service(**{**base, **kw})
        s.add(row)
        s.flush()
        return row.id


def test_a_compacted_streamlit_list_maps_by_position_and_resolves_by_title_and_number(church):
    gg = add_hymn(church, "Holy, Holy, Holy", 138, "GG2013")
    ph = add_hymn(church, "Holy, Holy, Holy", 138, "PH1990")
    add_hymn(church, "Be Thou My Vision", 450, "GG2013")
    sid = legacy_row(church, hymns=[{"title": "holy,  HOLY, holy", "number": 138}, {"title": "Unknown Hymn"},
                                    {"title": "Be Thou My Vision", "number": 999}, {"title": "Fourth"}])
    got = archive.get_service(church, sid)
    assert got.hymns["opening"] == archive.ArchivedHymnData(gg, "Holy, Holy, Holy", 138, "GG2013", True)
    assert got.hymns["response"] == archive.ArchivedHymnData(None, "Unknown Hymn", None, None, False)
    # The number must match when the entry has one.
    assert got.hymns["closing"] == archive.ArchivedHymnData(None, "Be Thou My Vision", 999, None, False)
    assert ph != gg                                  # GG2013 wins: the first code (no other preference)


def test_title_matches_prefer_the_entry_s_hymnal_then_the_service_s_then_the_church_s(church):
    gg = add_hymn(church, "Amazing Grace", 649, "GG2013")
    ph = add_hymn(church, "Amazing Grace", 280, "PH1990")
    el = add_hymn(church, "Amazing Grace", 779, "ELW")
    sid = legacy_row(church, hymnal="PH1990", hymns=[{"title": "Amazing Grace", "hymnal": "ELW"},
                                                     {"title": "Amazing Grace"}])
    got = archive.get_service(church, sid)
    assert (got.hymns["opening"].hymn_id, got.hymns["response"].hymn_id) == (el, ph)
    no_pref = archive.get_service(church, legacy_row(church, hymns=[{"title": "Amazing Grace"}]))
    assert no_pref.hymns["opening"].hymn_id == el                     # effective hymnal: the first code, "ELW"
    set_default_hymnal(church, "GG2013")
    assert archive.get_service(church, legacy_row(church, hymns=[{"title": "Amazing Grace"}])
                               ).hymns["opening"].hymn_id == gg


def test_duplicate_titles_resolve_the_same_way_every_time(church):
    ids = [add_hymn(church, "Doxology", n, "PH1990") for n in (593, 592, None)]
    sid = legacy_row(church, hymns=[{"title": "Doxology"}])
    picks = {archive.get_service(church, sid).hymns["opening"].hymn_id for _ in range(3)}
    assert picks == {ids[1]}                                           # the lowest number


def test_a_title_match_ignores_case_and_spacing_in_the_stored_title(church):
    # find_hymns_by_titles filters in Python with normalize_title: a SQL lower(title) IN (...)
    # would miss these stored titles (5a-2 plan, Risks).
    spaced = add_hymn(church, "Be\u00a0Thou  my Vision", 450, "GG2013")
    sid = legacy_row(church, hymns=[{"title": "be thou my vision", "number": 450}])
    assert archive.get_service(church, sid).hymns["opening"] == archive.ArchivedHymnData(
        spaced, "Be\u00a0Thou  my Vision", 450, "GG2013", True)


def test_a_stored_id_resolves_to_the_hymn_s_current_title(church, pastor):
    hymn_id = add_hymn(church, "Old Title", 1)
    record = archive.create_service(church, pastor, service(hymns={"opening": HymnRefData(hymn_id, "x", None, None)}))
    with session_scope() as s:
        s.get(Hymn, hymn_id).title = "New Title"
    assert archive.get_service(church, record.id).hymns["opening"].title == "New Title"
    with session_scope() as s:
        s.delete(s.get(Hymn, hymn_id))
    assert archive.get_service(church, record.id).hymns["opening"] == archive.ArchivedHymnData(
        None, "Old Title", 1, "GG2013", False)


def test_liturgy_custom_elements_and_dates_are_normalized(church):
    sid = legacy_row(church, service_date_iso="2026-10-04T00:00:00.000Z", liturgy={
        "call_to_worship": " Come. ", "opening_prayer": "", "notion_era_key": "x", "benediction": 5,
        "offertory_prayer": "[Configure OPENAI_API_KEY to generate offertory_prayer.]"},
        custom_elements=[{"label": "Anthem", "text": "Choir", "insert_after": "sermon"},
                         {"label": "Bogus", "text": "x", "insert_after": "bogus"}, {"label": 3}, "junk"])
    got = archive.get_service(church, sid)
    assert got.service_date_iso == "2026-10-04"
    assert got.liturgy == {"call_to_worship": "Come."}
    assert got.custom_elements == [CustomElement("Anthem", "Choir", "sermon"), CustomElement("Bogus", "x", "end"),
                                   CustomElement("", "", "end")]
    assert got.scriptures == ["Psalm 25"]
    assert (got.sermon_title, got.selected_ot_ref, got.created_by, got.hymnal) == ("", "", None, None)
    assert got.hymns == {"opening": None, "response": None, "closing": None}
    assert archive.get_service(church, legacy_row(church, service_date_iso="Oct 4", custom_elements=None)
                               ).service_date_iso is None


def test_an_element_with_an_unknown_place_survives_open_then_save(church, pastor):
    sid = legacy_row(church, custom_elements=[{"label": "Bogus", "text": "x", "insert_after": "bogus"}])
    opened = archive.get_service(church, sid)
    archive.replace_service(church, sid, service(custom_elements=tuple(opened.custom_elements)),
                            if_match=opened.saved_at)
    assert stored(sid)["custom_elements"] == [{"label": "Bogus", "text": "x", "insert_after": "end"}]


# --- list --------------------------------------------------------------------------

def test_the_list_is_newest_service_date_first_with_undated_last(church, pastor, make_user):
    base = datetime(2026, 9, 1, tzinfo=timezone.utc)
    gone_author = make_user(email="gone@example.com", name="  ")
    ids = {}
    for name, date_iso, minutes, author in (("old", "2026-09-27", 0, pastor), ("blank", "", 1, None),
                                            ("new", "2026-10-11", 2, gone_author), ("none", None, 3, None),
                                            ("notion", "2026-10-11T00:00:00.000Z", 4, None),
                                            ("same-day-later", "2026-10-11", 5, pastor),
                                            ("words", "Sept 13", 6, None), ("impossible", "2026-02-30", 7, None)):
        ids[name] = legacy_row(church, service_date_iso=date_iso, occasion=name, created_by=author,
                               saved_at=base + timedelta(minutes=minutes))
    page = archive.list_services(church, limit=20, offset=0)
    # A time part sorts by its date; "Sept 13" and an impossible date are undated, as the API reports them.
    assert [i.occasion for i in page.items] == ["same-day-later", "notion", "new", "old",
                                                "impossible", "words", "none", "blank"]
    assert (page.total, page.limit, page.offset) == (8, 20, 0)
    new = page.items[2]
    assert new.created_by == archive.Author(gone_author, "gone@example.com")     # a blank name: the email
    assert (new.service_date_iso, new.saved_at) == ("2026-10-11", "2026-09-01T00:02:00+00:00")
    assert page.items[1].service_date_iso == "2026-10-11"
    assert all(i.service_date_iso is None for i in page.items[4:]) and page.items[6].created_by is None
    window = archive.list_services(church, limit=2, offset=3)
    assert [i.occasion for i in window.items] == ["old", "impossible"] and window.total == 8


def test_the_list_sort_reads_the_same_dates_as_normalize_date_iso():
    """repos.services.DATED_PREFIX (the SQL sort) and normalize_date_iso (the API) agree."""
    samples = [f"{y:04d}-{m:02d}-{d:02d}" for y in (0, 1, 4, 100, 400, 1900, 2000, 2024, 2026, 2100, 9999)
               for m in range(14) for d in range(33)]
    samples += ["", "Sept 13", "October 4", "2026-10-04T00:00:00.000Z", " 2026-10-04", "\uff12\uff10\uff12\uff16-10-04",
                "26-10-04", "2026-10-4", "2026-10-04x"]
    for raw in samples:
        assert (re.search(DATED_PREFIX, raw) is not None) == (normalize_date_iso(raw) is not None), raw


def test_saving_logs_ids_and_counts_never_text(church, pastor, caplog):
    with caplog.at_level(logging.INFO, logger="usecases.archive"):
        record = archive.create_service(church, pastor, service())
        archive.delete_service(church, record.id)
    lines = [r.getMessage() for r in caplog.records if r.name == "usecases.archive"]
    assert lines[0].startswith(f"archive.create church={church} service={record.id} usage_rows=1 ms=")
    assert lines[1].startswith(f"archive.delete church={church} service={record.id} usage_rows=0 ms=")
    assert not any("Communion" in line or "Old Favorite" in line for line in lines)
