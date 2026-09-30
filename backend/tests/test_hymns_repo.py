import uuid

import pytest
from sqlalchemy import event, select

from db import session_scope
from db.models import Hymn, HymnCatalog
from domain_errors import NotFound
from repos.hymns import (
    HymnalSummary,
    HymnRecord,
    add_hymn,
    delete_hymn,
    hymnal_summaries,
    list_hymnal_records,
    list_hymns,
    query_hymns,
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


# --- slice 3a: typed reads (S Backend 1 "repos/hymns.py"; F §1.4) -------------------

def _hymn(church_id, hymnal, title, number=None, refs=None, **extra):
    with session_scope() as s:
        row = Hymn(church_id=church_id, hymnal=hymnal, title=title, number=number,
                   scripture_refs=refs, **extra)
        s.add(row)
        s.flush()
        return row.id


def _titles(records):
    return [(r.hymnal, r.number, r.title) for r in records]


def test_query_hymns_maps_records_and_orders_nulls_last(tmp_db, make_church):
    cid = make_church()
    _hymn(cid, "PH1990", "Zion", 5)
    _hymn(cid, "GG2013", "no number b")
    _hymn(cid, "GG2013", "Holy", 2, refs="Isaiah 6:3", theme="Praise",
          hymnary_link="https://hymnary.org/hymn/GG2013/2", text_year=1826, hymnal_count=1322)
    _hymn(cid, "GG2013", "No number A")
    _hymn(cid, "GG2013", "Abide", 10)
    records, total = query_hymns(cid, limit=2000)
    assert total == 5
    assert _titles(records) == [("GG2013", 2, "Holy"), ("GG2013", 10, "Abide"),
                                ("GG2013", None, "No number A"), ("GG2013", None, "no number b"),
                                ("PH1990", 5, "Zion")]
    holy = records[0]
    assert isinstance(holy, HymnRecord) and isinstance(holy.id, uuid.UUID)
    assert (holy.link, holy.scripture_refs, holy.theme, holy.text_year, holy.hymnal_count) == (
        "https://hymnary.org/hymn/GG2013/2", "Isaiah 6:3", "Praise", 1826, 1322)


def test_query_hymns_filters_by_hymnal_number_and_escaped_title(tmp_db, make_church):
    cid = make_church()
    _hymn(cid, "GG2013", "Joy to the World", 134)
    _hymn(cid, "GG2013", "Psalm 134", 999)
    _hymn(cid, "GG2013", "100% Sure", 1)
    _hymn(cid, "GG2013", "100 Sure", 2)
    _hymn(cid, "GG2013", "snake_case", 3)
    _hymn(cid, "GG2013", "snakeXcase", 4)
    _hymn(cid, "PH1990", "Joy to the World", 40)
    assert _titles(query_hymns(cid, hymnal="PH1990")[0]) == [("PH1990", 40, "Joy to the World")]
    assert query_hymns(cid, hymnal="NOPE") == ([], 0)
    assert {r.number for r in query_hymns(cid, q="134")[0]} == {134, 999}     # number or title
    assert [r.title for r in query_hymns(cid, q=" JOY ", hymnal="GG2013")[0]] == ["Joy to the World"]
    assert [r.title for r in query_hymns(cid, q="100%")[0]] == ["100% Sure"]
    assert [r.title for r in query_hymns(cid, q="e_c")[0]] == ["snake_case"]
    assert query_hymns(cid, q="   ")[1] == 7                                     # blank q: no filter


def test_long_digit_q_uses_the_title_branch_only(tmp_db, make_church):
    cid = make_church()
    _hymn(cid, "GG2013", "Hymn 123456", 123456)
    _hymn(cid, "GG2013", "Other", 7)
    assert [r.number for r in query_hymns(cid, q="123456")[0]] == [123456]    # 6 digits: number too
    assert query_hymns(cid, q="9" * 30) == ([], 0)                             # no OverflowError
    assert [r.number for r in query_hymns(cid, q="1234567")[0]] == []


def test_query_hymns_pages_counts_blank_titles_and_is_church_scoped(tmp_db, make_church):
    a, b = make_church(name="A"), make_church(name="B")
    for n in range(1, 6):
        _hymn(a, "GG2013", f"Hymn {n}", n)
    _hymn(a, "GG2013", None, 6)
    _hymn(a, "GG2013", "  ", 7)
    _hymn(b, "GG2013", "Church B only", 1)
    page, total = query_hymns(a, limit=2, offset=2)
    assert total == 7
    assert [r.number for r in page] == [3, 4]
    assert [r.number for r in query_hymns(a, limit=10, offset=5)[0]] == [6, 7]
    assert "Church B only" not in [r.title for r in query_hymns(a, limit=100)[0]]
    with pytest.raises(NotFound):
        query_hymns("not-a-uuid")


def test_hymnal_summaries_count_hymns_and_scripture_refs(tmp_db, make_church):
    cid, other = make_church(name="A"), make_church(name="B")
    _hymn(cid, "PH1990", "One", 1)
    _hymn(cid, "GG2013", "Two", 2, refs="John 3:16")
    _hymn(cid, "GG2013", "Three", 3, refs="   ")
    _hymn(cid, "GG2013", "Four", 4)
    _hymn(cid, "", "Blank code", 5)
    _hymn(other, "ZZ", "Other church", 1)
    assert hymnal_summaries(cid) == [HymnalSummary("GG2013", 3, 1), HymnalSummary("PH1990", 1, 0)]
    assert hymnal_summaries(make_church(name="Empty")) == []
    # Codepoint order, as Streamlit's sorted() (owner decision 1): upper case before lower.
    _hymn(cid, "ab", "Lower", 1)
    _hymn(cid, "Zz", "Upper", 1)
    assert [h.code for h in hymnal_summaries(cid)] == ["GG2013", "PH1990", "Zz", "ab"]


def test_list_hymnal_records_in_hymnal_order_in_the_callers_session(tmp_db, make_church):
    cid = make_church()
    _hymn(cid, "GG2013", "B", 2)
    _hymn(cid, "GG2013", "A", None)
    _hymn(cid, "GG2013", "C", 1)
    _hymn(cid, "PH1990", "D", 1)
    with session_scope() as s:
        records = list_hymnal_records(cid, "GG2013", session=s)
        assert [r.title for r in records] == ["C", "B", "A"]
        assert hymnal_summaries(cid, session=s)[0].code == "GG2013"


# --- slice 4a: the liturgy request's picks (S Backend 6 "repos/hymns.py") ---

def _no_own_scope():
    raise AssertionError("opened its own session_scope instead of using session=")


def test_get_hymns_by_ids_is_church_scoped_and_skips_what_it_cannot_find(tmp_db, make_church, monkeypatch):
    import repos.hymns
    from repos.hymns import get_hymns_by_ids

    mine, other = make_church(), make_church(name="Other")
    a = _hymn(mine, "GG2013", "Holy, Holy, Holy", 1, text_year=1826)
    b = _hymn(mine, "PH1990", "Be Thou My Vision", None)
    theirs = _hymn(other, "GG2013", "Not Mine", 2)
    found = get_hymns_by_ids(mine, [a, str(b), theirs, uuid.uuid4(), "not-a-uuid", None])
    assert set(found) == {a, b}
    assert (found[a].title, found[a].number, found[a].hymnal, found[a].text_year) == (
        "Holy, Holy, Holy", 1, "GG2013", 1826)
    assert found[b].number is None
    assert get_hymns_by_ids(mine, []) == {}
    with session_scope() as s:
        s.get(Hymn, a).title = "Uncommitted"
        s.flush()                                       # seen only through s
        with monkeypatch.context() as m:
            m.setattr(repos.hymns, "session_scope", _no_own_scope)
            found_in_s = get_hymns_by_ids(mine, [a], session=s)
        assert set(found_in_s) == {a} and found_in_s[a].title == "Uncommitted"
        s.rollback()
    with pytest.raises(NotFound):
        get_hymns_by_ids("not-a-church", [a])
