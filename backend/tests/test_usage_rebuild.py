"""hymn_usage.rebuild_usage_for_date: a date's hymn use is the union of the
services saved for it (slice 5a spec, hymn_usage.py; owner answer 6,
2026-10-01; F §7.4). SQLite here; the concurrent case is in
test_services_postgres.py."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from db import session_scope
from db.models import HymnUsage, Service
from hymn_usage import rebuild_usage_for_date, record_usage

D = "2026-10-04"
T0 = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def church(make_church):
    return make_church(name="Grace")


def add_service(church_id, hymns, *, date_iso=D, minutes=0) -> uuid.UUID:
    """A services row as any writer left it (5a-2's 3 slots, Streamlit's compacted list, or junk)."""
    with session_scope() as s:
        row = Service(church_id=church_id, service_date_iso=date_iso, service_date_display="October 04, 2026",
                      occasion="", scriptures=[], hymns=hymns, liturgy={},
                      saved_at=T0 + timedelta(minutes=minutes))
        s.add(row)
        s.flush()
        return row.id


def usage(church_id, date_iso=D) -> list[tuple]:
    with session_scope() as s:
        return sorted(s.execute(select(HymnUsage.hymn_number, HymnUsage.hymn_title)
                                .where(HymnUsage.church_id == church_id, HymnUsage.date_iso == date_iso)).all(),
                      key=lambda r: (r[1], r[0] or 0))


def rebuild(church_id, date_iso=D) -> int:
    with session_scope() as s:
        return rebuild_usage_for_date(church_id, date_iso, session=s)


def slots(opening=None, response=None, closing=None) -> list[dict]:
    def entry(slot, hymn):
        title, number = hymn if hymn else ("", None)
        return {"slot": slot, "title": title, "number": number, "hymn_id": None, "hymnal": None}
    return [entry("opening", opening), entry("response", response), entry("closing", closing)]


def test_a_date_s_rows_are_the_union_of_its_saved_services(church):
    add_service(church, slots(("Holy, Holy, Holy", 138), None, ("Be Thou My Vision", 450)))
    add_service(church, slots(("Amazing Grace", 649)), minutes=5)      # an early service, same date
    assert rebuild(church) == 3
    assert usage(church) == [(649, "Amazing Grace"), (450, "Be Thou My Vision"), (138, "Holy, Holy, Holy")]


def test_rows_nothing_saved_backs_are_replaced(church):
    # Frozen Streamlit's Prepare (record_usage) and imported history wrote rows no saved service backs.
    assert record_usage(church, D, [{"title": "Prepared Only", "number": 1}])
    add_service(church, slots(("Holy, Holy, Holy", 138)))
    rebuild(church)
    assert usage(church) == [(138, "Holy, Holy, Holy")]


def test_a_date_with_no_service_left_has_no_rows(church):
    record_usage(church, D, [{"title": "Holy, Holy, Holy", "number": 138}])
    assert rebuild(church) == 0
    assert usage(church) == []


def test_titles_dedupe_by_the_usage_key_and_keep_the_first_saved(church):
    # usage_key is the title alone, punctuation, case and spacing ignored (3a amendment):
    # the same hymn from two hymnals, or typed twice, is one row.
    add_service(church, slots(("Holy, Holy, Holy", 138), ("Be Thou My Vision", None)))
    add_service(church, slots(("holy holy  holy", 4), ("Be Thou My Vision", None), ("Be Thou my vision!", 82)),
                minutes=5)
    assert rebuild(church) == 2
    assert usage(church) == [(None, "Be Thou My Vision"), (138, "Holy, Holy, Holy")]


def test_malformed_legacy_rows_are_skipped_not_raised(church):
    for junk in ("Holy", {"title": "x"}, [None, 42, {"title": 7}, {"title": "  "}], None):
        add_service(church, junk)
    # Streamlit's compacted list, a 4th entry included, and a Notion-era date with a time part.
    add_service(church, [{"title": "A", "number": 1}, {"title": "B"}, {"title": "C"}, {"title": "D", "number": "4"}],
                date_iso="2026-10-04T00:00:00.000Z")
    assert rebuild(church) == 4
    assert usage(church) == [(1, "A"), (None, "B"), (None, "C"), (4, "D")]


def test_only_that_date_and_that_church(church, make_church):
    other = make_church(name="Hope")
    add_service(church, slots(("Holy, Holy, Holy", 138)))
    add_service(church, slots(("Next Week", 2)), date_iso="2026-10-11")
    add_service(other, slots(("Their Hymn", 3)))
    record_usage(church, "2026-10-11", [{"title": "Kept", "number": 9}])
    record_usage(other, D, [{"title": "Their Prepared", "number": 8}])
    rebuild(church)
    assert usage(church) == [(138, "Holy, Holy, Holy")]
    assert usage(church, "2026-10-11") == [(9, "Kept")]                 # not rebuilt
    assert usage(other) == [(8, "Their Prepared")]                      # another church


def test_imported_rows_with_a_time_part_go_when_their_date_is_rebuilt(church):
    # Imported (Notion-era) history may store "2026-10-04T00:00:00.000Z": the rebuild
    # deletes by the date prefix, also when the last service on that date is deleted.
    def imported(title, number):
        with session_scope() as s:
            s.add(HymnUsage(church_id=church, date_iso=f"{D}T00:00:00.000Z", hymn_number=number, hymn_title=title))

    def every_row():
        with session_scope() as s:
            return sorted(s.execute(select(HymnUsage.date_iso, HymnUsage.hymn_number, HymnUsage.hymn_title)
                                    .where(HymnUsage.church_id == church)).all())

    imported("Imported", 7)
    sid = add_service(church, slots(("Holy, Holy, Holy", 138)))
    assert rebuild(church) == 1
    assert every_row() == [(D, 138, "Holy, Holy, Holy")]
    imported("Imported Again", 8)
    with session_scope() as s:
        s.delete(s.get(Service, sid))
    assert rebuild(church) == 0
    assert every_row() == []


@pytest.mark.parametrize("bad", [None, "", "2026-13-01", "2026-10-04T00:00:00", "October 04, 2026"])
def test_only_a_yyyy_mm_dd_date_is_accepted(church, bad):
    record_usage(church, D, [{"title": "Holy, Holy, Holy", "number": 138}])
    with pytest.raises(ValueError):
        rebuild(church, bad)
    assert usage(church) == [(138, "Holy, Holy, Holy")]
