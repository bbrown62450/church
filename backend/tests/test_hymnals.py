from repos.hymns import (
    add_hymn, list_hymns, list_church_hymnals, import_hymns,
)


def test_default_hymnal_is_gg2013(tmp_db, make_user, make_church):
    owner = make_user(email="o@x.org")
    cid = make_church(name="C", timezone="UTC", owner_user_id=owner)
    h = add_hymn(cid, title="Amazing Grace", number=649)
    assert h["Hymnal"] == "GG2013"


def test_list_hymns_filters_by_hymnal(tmp_db, make_user, make_church):
    owner = make_user(email="o2@x.org")
    cid = make_church(name="C", timezone="UTC", owner_user_id=owner)
    add_hymn(cid, title="From GG", number=1, hymnal="GG2013")
    add_hymn(cid, title="From PH", number=1, hymnal="PH1990")
    assert {h["Hymn Title"] for h in list_hymns(cid)} == {"From GG", "From PH"}
    assert [h["Hymn Title"] for h in list_hymns(cid, hymnal="PH1990")] == ["From PH"]
    assert sorted(list_church_hymnals(cid)) == ["GG2013", "PH1990"]


def test_import_hymns_is_idempotent_and_enriches(tmp_db, make_user, make_church):
    owner = make_user(email="o3@x.org")
    cid = make_church(name="C", timezone="UTC", owner_user_id=owner)
    rows = [
        {"number": 1, "title": "Come, Thou Long-Expected Jesus"},
        {"number": 3, "title": "Comfort, Comfort You My People"},
    ]
    first = import_hymns(cid, "PH1990", rows)
    assert first == {"inserted": 2, "updated": 0, "total": 2}
    assert len(list_hymns(cid, hymnal="PH1990")) == 2

    # Re-run with enrichment added: no dupes, the matched row gains scripture refs.
    rows[0]["scripture_refs"] = "Isaiah 9:6"
    second = import_hymns(cid, "PH1990", rows)
    assert second["inserted"] == 0
    assert second["updated"] == 1
    ph = list_hymns(cid, hymnal="PH1990")
    assert len(ph) == 2   # still 2, not 4
    enriched = next(h for h in ph if h["Hymn Number"] == 1)
    assert enriched["Scripture References"] == "Isaiah 9:6"
