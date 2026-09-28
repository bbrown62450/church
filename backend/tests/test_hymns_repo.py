from sqlalchemy import event, select

from db import session_scope
from db.models import Hymn, HymnCatalog
from repos.hymns import (
    add_hymn,
    delete_hymn,
    list_hymns,
    seed_church_from_catalog,
    update_hymn,
)


def test_add_hymn_maps_to_flat_notion_keys(tmp_db, make_user, make_church):
    owner = make_user(email="owner@grace.org")
    # Catalog is empty here, so the church is created with 0 hymns.
    cid = make_church(name="Grace", timezone="America/New_York", owner_user_id=owner)
    assert list_hymns(cid) == []

    created = add_hymn(
        cid,
        title="Amazing Grace",
        number=378,
        scripture_refs="Eph 2:8",
        theme="Grace",
        hymnary_link="https://hymnary.org/text/amazing_grace",
    )
    assert created["Hymn Title"] == "Amazing Grace"
    assert "id" in created

    hymns = list_hymns(cid)
    assert len(hymns) == 1
    h = hymns[0]
    assert set(h) >= {
        "id",
        "Hymn Title",
        "Hymn Number",
        "Scripture References",
        "Theme",
        "Hymnary.org Link",
        "Audio",
    }
    assert h["Hymn Title"] == "Amazing Grace"
    assert h["Hymn Number"] == 378
    assert h["Scripture References"] == "Eph 2:8"
    assert h["Theme"] == "Grace"
    assert h["Hymnary.org Link"] == "https://hymnary.org/text/amazing_grace"


def test_update_hymn_is_church_scoped_idor_safe(tmp_db, make_user, make_church):
    owner = make_user(email="owner2@grace.org")
    a = make_church(name="A", timezone="America/New_York", owner_user_id=owner)
    b = make_church(name="B", timezone="America/New_York", owner_user_id=owner)
    created = add_hymn(a, title="Holy, Holy, Holy", number=1)
    hid = created["id"]

    # Church B cannot touch Church A's hymn.
    assert update_hymn(hid, b, title="HACKED", number=999) is None
    unchanged = list_hymns(a)[0]
    assert unchanged["Hymn Title"] == "Holy, Holy, Holy"
    assert unchanged["Hymn Number"] == 1

    # Correct church can update.
    updated = update_hymn(hid, a, title="Holy, Holy, Holy!", number=2, theme="Trinity")
    assert updated is not None
    assert updated["Hymn Title"] == "Holy, Holy, Holy!"
    assert updated["Hymn Number"] == 2
    assert updated["Theme"] == "Trinity"


def test_delete_hymn_is_church_scoped_idor_safe(tmp_db, make_user, make_church):
    owner = make_user(email="owner3@grace.org")
    a = make_church(name="A", timezone="America/New_York", owner_user_id=owner)
    b = make_church(name="B", timezone="America/New_York", owner_user_id=owner)
    hid = add_hymn(a, title="For All the Saints", number=326)["id"]

    # Cross-church delete is a no-op.
    assert delete_hymn(hid, b) is False
    assert len(list_hymns(a)) == 1

    # Same-church delete works.
    assert delete_hymn(hid, a) is True
    assert list_hymns(a) == []


def test_seed_church_from_catalog_returns_count_and_copies_rows(
    tmp_db, make_user, make_church, seed_catalog
):
    owner = make_user(email="seed@grace.org")
    # Created against an empty catalog -> 0 hymns to start.
    cid = make_church(name="Seeded", timezone="America/New_York", owner_user_id=owner)
    assert list_hymns(cid) == []

    seed_catalog(3)
    with session_scope() as session:
        n = seed_church_from_catalog(cid, session)
    assert n == 3
    assert len(list_hymns(cid)) == 3


def test_hymn_dicts_expose_year_and_familiarity(tmp_db, make_user, make_church):
    cid = make_church(owner_user_id=make_user(email="facts@grace.org"))
    created = add_hymn(cid, title="Holy, Holy, Holy", number=138)
    assert created["Text Year"] is None
    assert created["Hymnal Count"] is None


def test_seed_copies_year_and_familiarity(tmp_db, make_user, make_church):
    from db.models import HymnCatalog

    cid = make_church(owner_user_id=make_user(email="seedfacts@grace.org"))
    with session_scope() as session:
        session.add(HymnCatalog(title="Holy, Holy, Holy", number=138, text_year=1826, hymnal_count=1322))
    with session_scope() as session:
        seed_church_from_catalog(cid, session)
    [hymn] = list_hymns(cid)
    assert hymn["Text Year"] == 1826
    assert hymn["Hymnal Count"] == 1322


SEEDED_COLUMNS = ("hymnal", "title", "number", "scripture_refs", "theme",
                  "hymnary_link", "audio_url", "text_year", "hymnal_count")


def _watch_hymn_inserts(engine) -> list:
    """Record each cursor execution that inserts into hymns (an executemany is one)."""
    seen = []

    @event.listens_for(engine, "before_cursor_execute")
    def _record(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("INSERT INTO HYMNS "):
            seen.append(statement)

    return seen


def test_seed_copies_every_catalog_column_in_bulk(tmp_db, make_user, make_church):
    cid = make_church(owner_user_id=make_user(email="bulk@grace.org"))
    with session_scope() as session:
        session.add_all([
            HymnCatalog(hymnal="GG2013", title="Holy, Holy, Holy", number=138,
                        scripture_refs="Revelation 4:8", theme="trinity, praise",
                        hymnary_link="https://hymnary.org/text/holy_holy_holy",
                        audio_url="https://example.org/138.mp3", text_year=1826,
                        hymnal_count=1322),
            HymnCatalog(hymnal="PH1990", title="Be Thou My Vision", number=339),
        ])
    inserts = _watch_hymn_inserts(tmp_db)
    built = []

    def _count_hymn_objects(target, args, kwargs):
        built.append(1)

    event.listen(Hymn, "init", _count_hymn_objects)
    try:
        with session_scope() as session:
            assert seed_church_from_catalog(cid, session) == 2
    finally:
        event.remove(Hymn, "init", _count_hymn_objects)
    # One INSERT for the whole catalog, and no Hymn object built per row.
    assert len(inserts) == 1
    assert built == []

    with session_scope() as session:
        catalog = session.execute(
            select(HymnCatalog).order_by(HymnCatalog.number)
        ).scalars().all()
        hymns = session.execute(
            select(Hymn).where(Hymn.church_id == cid).order_by(Hymn.number)
        ).scalars().all()
    assert [tuple(getattr(h, col) for col in SEEDED_COLUMNS) for h in hymns] == [
        tuple(getattr(c, col) for col in SEEDED_COLUMNS) for c in catalog
    ]
    assert len({h.id for h in hymns}) == 2
    assert not {h.id for h in hymns} & {c.id for c in catalog}  # fresh ids, not the catalog's


def test_seed_with_empty_catalog_inserts_nothing(tmp_db, make_user, make_church):
    cid = make_church(owner_user_id=make_user(email="empty@grace.org"))
    inserts = _watch_hymn_inserts(tmp_db)
    with session_scope() as session:
        # An empty parameter list would INSERT one all-defaults row (IntegrityError
        # on hymns.church_id), so the seed must skip the statement entirely.
        assert seed_church_from_catalog(cid, session) == 0
    assert inserts == []
    assert list_hymns(cid) == []
