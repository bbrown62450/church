"""The archive on real Postgres (slice 5a spec, Testing "Postgres"; acceptance
criteria 7 and 8): concurrent saves on one date record the full union of
their hymns, two PUTs with the same If-Match give one 200 and one 409, the
list's NULLS LAST order, and the owner's read-only counts before 0005
(backend/migrations/README.md).

Skipped without TEST_DATABASE_URL; CI's backend-postgres job runs them. The
SQLite fixtures cannot be used here: users and churches come from the repos
on pg_db's engine. Forcing the race: a barrier inside the function the
usecase calls through a module attribute holds each save until both have
written their row (or both are about to lock it), so the advisory lock and
the row lock are what decide the outcome. A save that never reaches the
barrier breaks it after 10 s, and the test errors instead of passing vacuously.
"""
import re
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError

import repos.services
from db import SessionLocal, session_scope
from db.models import HymnUsage, Service
from domain_errors import Conflict
from hymn_usage import rebuild_usage_for_date
from repos.churches import create_church
from repos.users import ensure_user
from usecases import archive
from usecases.liturgy import HymnRefData

README = Path(__file__).resolve().parents[1] / "migrations" / "README.md"


@pytest.fixture
def world(pg_db):
    user = ensure_user("pastor@example.com", "Pastor").id
    return user, create_church(name="Grace", timezone="America/New_York", owner_user_id=user)


def hymn(title, number):
    return HymnRefData(None, title, number, None)


def service(day, opening, response, closing):
    return archive.ServiceInput(service_date=day, occasion="", hymns={
        "opening": opening, "response": response, "closing": closing})


def used(church_id, day) -> set[str]:
    with session_scope() as s:
        return set(s.execute(select(HymnUsage.hymn_title).where(
            HymnUsage.church_id == church_id, HymnUsage.date_iso == day.isoformat())).scalars().all())


def together(monkeypatch, module, name):
    """Patch module.name so two callers wait for each other before the real call."""
    real = getattr(module, name)
    barrier = threading.Barrier(2)

    def wrapped(*args, **kwargs):
        barrier.wait(timeout=10)
        return real(*args, **kwargs)

    monkeypatch.setattr(module, name, wrapped)


@pytest.mark.postgres
def test_concurrent_saves_on_one_date_record_the_full_union(world, monkeypatch):
    user, church = world
    together(monkeypatch, archive, "rebuild_usage_for_date")
    for round_ in range(20):
        day = date(2026, 1, 4) + timedelta(weeks=round_)
        early = service(day, hymn("Holy, Holy, Holy", 138), hymn("Be Thou My Vision", 450), hymn("Early", 1))
        late = service(day, hymn("Be Thou My Vision", 450), hymn("Holy, Holy, Holy", 138), hymn("Late", 2))
        with ThreadPoolExecutor(max_workers=2) as pool:
            records = list(pool.map(lambda data: archive.create_service(church, user, data), (early, late)))
        assert len({r.id for r in records}) == 2
        assert used(church, day) == {"Holy, Holy, Holy", "Be Thou My Vision", "Early", "Late"}, round_


@pytest.mark.postgres
def test_a_rebuild_waits_for_another_on_the_same_date_only(world):
    """The advisory lock, deterministically: while one transaction has rebuilt
    a date, a second one's rebuild of that date waits (here it gives up after
    200 ms), and a rebuild of another date does not."""
    _user, church = world
    first = SessionLocal()
    try:
        rebuild_usage_for_date(church, "2026-10-04", session=first)       # holds the lock until it ends
        for date_iso, waits in (("2026-10-04", True), ("2026-10-11", False)):
            second = SessionLocal()
            try:
                second.execute(text("SET LOCAL lock_timeout = '200ms'"))
                if waits:
                    with pytest.raises(OperationalError, match="lock timeout"):
                        rebuild_usage_for_date(church, date_iso, session=second)
                else:
                    assert rebuild_usage_for_date(church, date_iso, session=second) == 0
            finally:
                second.rollback()
                second.close()
    finally:
        first.rollback()
        first.close()


@pytest.mark.postgres
def test_two_puts_with_the_same_if_match_give_one_save_and_one_conflict(world, monkeypatch):
    user, church = world
    record = archive.create_service(church, user, service(date(2026, 10, 4), hymn("Holy, Holy, Holy", 138),
                                                          None, None))
    together(monkeypatch, repos.services, "get_service")

    def put(occasion):
        data = archive.ServiceInput(service_date=date(2026, 10, 4), occasion=occasion)
        try:
            return archive.replace_service(church, record.id, data, if_match=record.saved_at)
        except Conflict as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(put, ("Mine", "Theirs")))
    saved = [r for r in results if isinstance(r, archive.ServiceRecord)]
    conflicts = [r for r in results if isinstance(r, Conflict)]
    assert (len(saved), len(conflicts)) == (1, 1)
    assert conflicts[0].details == {"current_saved_at": saved[0].saved_at}
    monkeypatch.undo()                                   # one more read, without the barrier
    assert archive.get_service(church, record.id).occasion == saved[0].occasion


@pytest.mark.postgres
def test_the_list_puts_blank_and_missing_dates_last_as_on_sqlite(world):
    user, church = world
    base = datetime(2026, 9, 1, tzinfo=timezone.utc)
    with session_scope() as s:
        for minutes, (name, date_iso) in enumerate((("old", "2026-09-27"), ("blank", ""), ("new", "2026-10-11"),
                                                    ("none", None), ("same-day-later", "2026-10-11"))):
            s.add(Service(church_id=church, created_by=user, service_date_iso=date_iso, occasion=name,
                          hymns=[], liturgy={}, scriptures=[], saved_at=base + timedelta(minutes=minutes)))
    page = archive.list_services(church, limit=20, offset=0)
    assert [i.occasion for i in page.items] == ["same-day-later", "new", "old", "none", "blank"]


def readme_sql(n: int) -> str:
    """The n-th ```sql block of README "Before 0005_services_extras": 0 is step 2's counts, 1 step 4's check."""
    section = README.read_text(encoding="utf-8").split("\n## Before 0005_services_extras (slice 5a-2)\n", 1)[1]
    return re.findall(r"```sql\n(.*?)```", section, re.S)[n]


@pytest.mark.postgres
def test_the_owner_s_read_only_queries_count_as_the_api_reads(world):
    user, church = world
    archive.create_service(church, user, service(date(2026, 10, 4), hymn("Holy, Holy, Holy", 138), None, None))
    with session_scope() as s:
        for date_iso, hymns in (("2026-09-27", [{"title": "A", "number": 1}]),     # Streamlit's list
                                ("", [{"title": "B"}]), (None, None),                   # undated
                                ("2026-09-20T00:00:00.000Z", []), ("Sept 13", "junk")):
            s.add(Service(church_id=church, service_date_iso=date_iso, occasion="", hymns=hymns, liturgy={},
                          scriptures=[]))
    with session_scope() as s:
        counts = dict(s.execute(text(readme_sql(0))).mappings().one())
        applied = dict(s.execute(text(readme_sql(1))).mappings().one())
    # The 5a-2 save has 3 slots; the other five are old-style; "", NULL and "Sept 13" are undated.
    assert counts == {"version": "0005_services_extras", "services": 6, "undated": 3, "old_style_hymn_lists": 5}
    assert applied == {"version": "0005_services_extras", "new_columns": 2, "new_index": 1}
