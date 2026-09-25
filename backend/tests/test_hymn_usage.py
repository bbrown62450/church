from datetime import date, timedelta

from db import session_scope
from db.models import HymnUsage
from hymn_usage import (
    get_recently_used_identifiers,
    is_hymn_recently_used,
    record_usage,
)

RECENT = (date.today() - timedelta(days=7)).isoformat()


def test_usage_is_church_scoped(tmp_db, make_user, make_church):
    u = make_user(email="u@x.org")
    a = make_church(name="A", timezone="America/New_York", owner_user_id=u)
    b = make_church(name="B", timezone="America/New_York", owner_user_id=u)

    assert record_usage(a, RECENT, [{"number": 100, "title": "Holy, Holy, Holy"}]) is True

    a_set = get_recently_used_identifiers(a, weeks=12)
    b_set = get_recently_used_identifiers(b, weeks=12)
    assert (100, "holy, holy, holy") in a_set
    assert (100, "holy, holy, holy") not in b_set
    assert b_set == set()
    # is_hymn_recently_used consumes the church-scoped set.
    assert is_hymn_recently_used(100, "Holy, Holy, Holy", a_set) is True
    assert is_hymn_recently_used(100, "Holy, Holy, Holy", b_set) is False


def test_record_usage_is_idempotent(tmp_db, make_user, make_church):
    u = make_user(email="u2@x.org")
    a = make_church(name="A", timezone="America/New_York", owner_user_id=u)
    hymns = [{"number": 100, "title": "Holy, Holy, Holy"}]
    assert record_usage(a, RECENT, hymns) is True
    assert record_usage(a, RECENT, hymns) is True  # re-prepared bulletin

    with session_scope() as session:
        count = session.query(HymnUsage).filter(HymnUsage.church_id == a).count()
    assert count == 1


def test_record_usage_rejects_unparseable_date(tmp_db, make_user, make_church):
    u = make_user(email="u3@x.org")
    a = make_church(name="A", timezone="America/New_York", owner_user_id=u)
    assert record_usage(a, "not a date", [{"number": 1, "title": "X"}]) is False


def test_old_usage_excluded_from_window(tmp_db, make_user, make_church):
    u = make_user(email="u4@x.org")
    a = make_church(name="A", timezone="America/New_York", owner_user_id=u)
    old = (date.today() - timedelta(weeks=20)).isoformat()
    assert record_usage(a, old, [{"number": 55, "title": "Old Hymn"}]) is True
    assert (55, "old hymn") not in get_recently_used_identifiers(a, weeks=12)
