"""hymn_usage.usage_near: the recent-use window around the service date
(slice 3 spec, Backend 3.4; Testing `test_hymn_usage_window.py`; AC4 window
half; owner answer Q2 of 2026-09-29: the key is the normalized title alone)."""
import logging
import uuid
from datetime import date

import pytest

from db import session_scope
from db.models import Church, HymnUsage, User
from hymn_usage import RECENT_WEEKS, usage_near

D = date(2026, 10, 4)                     # a Sunday; D - 84 = 2026-07-12, D + 84 = 2026-12-27


def _use(church_id, date_iso, title="Holy, Holy, Holy", number=1):
    with session_scope() as s:
        s.add(HymnUsage(church_id=church_id, date_iso=date_iso, hymn_number=number, hymn_title=title))


def test_window_is_84_days_each_side_inclusive_and_excludes_the_service_date(tmp_db, make_church):
    cid = make_church()
    assert RECENT_WEEKS == 12
    _use(cid, "2026-07-12", "Edge before")
    _use(cid, "2026-12-27", "Edge after")
    _use(cid, "2026-07-11", "Too early")
    _use(cid, "2026-12-28", "Too late")
    _use(cid, "2026-10-04", "Same day")
    assert usage_near(cid, D) == {"edge before": date(2026, 7, 12), "edge after": date(2026, 12, 27)}
    # Owner decision 1: the window is clamped at date.min and date.max, not an OverflowError.
    _use(cid, "9999-12-30", "Last days")
    _use(cid, "0001-01-02", "First days")
    assert usage_near(cid, date.max) == {"last days": date(9999, 12, 30)}
    assert usage_near(cid, date.min) == {"first days": date(1, 1, 2)}


def test_nearest_date_wins_and_ties_go_to_the_earlier_date(tmp_db, make_church):
    cid = make_church()
    _use(cid, "2026-08-02", "A")
    _use(cid, "2026-09-20", "A")
    _use(cid, "2026-10-18", "A")          # 14 days after; 2026-09-20 is 14 days before
    _use(cid, "2026-11-01", "B")
    _use(cid, "2026-10-11", "B")
    assert usage_near(cid, D) == {"a": date(2026, 9, 20), "b": date(2026, 10, 11)}


def test_the_key_is_the_title_alone_across_numbers_and_hymnals(tmp_db, make_church):
    """Owner answer Q2: a hymn sung as GG2013 #403 is recent when picked as PH1990 #138."""
    cid = make_church()
    _use(cid, "2026-09-27", "Come, Thou Almighty King", number=403)
    _use(cid, "2026-09-13", "Nameless", number=None)
    near = usage_near(cid, D)
    assert near["come thou almighty king"] == date(2026, 9, 27)
    assert near["nameless"] == date(2026, 9, 13)


def test_title_whitespace_and_case_are_tolerated(tmp_db, make_church):
    cid = make_church()
    _use(cid, "2026-09-27", "  Come,  Thou ALMIGHTY King ")
    _use(cid, "2026-09-20", "")
    _use(cid, "2026-09-20", None)
    assert usage_near(cid, D) == {"come thou almighty king": date(2026, 9, 27)}


def test_usage_is_church_scoped(tmp_db, make_church):
    a, b = make_church(name="A"), make_church(name="B")
    _use(b, "2026-09-27", "Only in B")
    assert usage_near(a, D) == {}
    assert usage_near(b, D) == {"only in b": date(2026, 9, 27)}


def test_null_and_blank_dates_are_ignored(tmp_db, make_church):
    cid = make_church()
    _use(cid, None, "Null date")
    _use(cid, "", "Blank date")
    assert usage_near(cid, D) == {}


def test_datetime_shaped_dates_count_as_their_day(tmp_db, make_church):
    cid = make_church()
    _use(cid, "2026-08-02T10:00:00.000-05:00", "Inside")
    _use(cid, "2026-12-27T10:00:00.000-05:00", "On the last day")
    _use(cid, "2026-10-04T10:00:00.000-05:00", "On the service date")
    assert usage_near(cid, D) == {"inside": date(2026, 8, 2), "on the last day": date(2026, 12, 27)}


def test_malformed_dates_are_skipped_and_counted_at_debug(tmp_db, make_church, caplog):
    cid = make_church()
    _use(cid, "2026-8-2", "Unpadded")             # sorts after "2026-12-28": SQL drops it
    _use(cid, "2026-10-1", "Malformed")           # inside the SQL range, then fails to parse
    _use(cid, "2026-09-3x", "Also malformed")
    _use(cid, "2026-09-27", "Good")
    caplog.set_level(logging.DEBUG, logger="hymn_usage")
    assert usage_near(cid, D) == {"good": date(2026, 9, 27)}
    assert "usage_near skipped 2 usage rows" in caplog.text


@pytest.mark.postgres
def test_usage_near_on_postgres(pg_db):
    """The string range and the datetime-shaped value on Postgres (S Testing "postgres")."""
    user_id, church_id = uuid.uuid4(), uuid.uuid4()
    with session_scope() as s:
        s.add(User(id=user_id, email="pg@example.com"))
        s.add(Church(id=church_id, name="PG", timezone="America/New_York", settings={}))
    _use(church_id, "2026-12-27T10:00:00.000-05:00", "Last day")
    _use(church_id, "2026-12-28", "Too late")
    _use(church_id, "2026-8-2", "Malformed")
    _use(church_id, "2026-10-04", "Same day")
    _use(church_id, "2026-07-12", "First day")
    assert usage_near(church_id, D) == {"last day": date(2026, 12, 27),
                                        "first day": date(2026, 7, 12)}
