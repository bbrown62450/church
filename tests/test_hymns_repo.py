from db import session_scope
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
