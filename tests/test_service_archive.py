from service_archive import (
    delete_service,
    get_service,
    list_saved_services,
    save_service,
    update_service,
)

_KW = dict(
    service_date="July 5, 2026",
    service_date_iso="2026-07-05",
    occasion="Ordinary",
    scriptures=["John 3:16"],
    hymns=[{"title": "Holy, Holy, Holy", "number": 1, "extra": "dropped"}],
    liturgy={"opening": "Call to worship"},
    sermon_title="Grace Abounds",
    selected_ot_ref="Ps 23",
    selected_nt_ref="John 3",
    include_communion=True,
)


def test_save_service_returns_snapshot(tmp_db, make_user, make_church):
    u = make_user(email="s@x.org")
    a = make_church(name="A", timezone="America/New_York", owner_user_id=u)
    saved = save_service(a, created_by=u, **_KW)
    assert saved["church_id"] == str(a)
    assert saved["created_by"] == str(u)
    assert saved["occasion"] == "Ordinary"
    # hymns are denormalized to title/number only.
    assert saved["hymns"] == [{"title": "Holy, Holy, Holy", "number": 1}]
    assert saved["include_communion"] is True
    assert saved["saved_at"]  # ISO timestamp present


def test_get_update_delete_are_church_scoped_idor(tmp_db, make_user, make_church):
    u = make_user(email="s2@x.org")
    a = make_church(name="A", timezone="America/New_York", owner_user_id=u)
    b = make_church(name="B", timezone="America/New_York", owner_user_id=u)
    sid = save_service(a, created_by=u, **_KW)["id"]

    # Same church can read it.
    assert get_service(sid, a) is not None
    # Church B cannot read/update/delete Church A's service.
    assert get_service(sid, b) is None
    assert update_service(sid, b, **{**_KW, "occasion": "HACKED"}) is None
    assert delete_service(sid, b) is False

    # Original untouched.
    still = get_service(sid, a)
    assert still["occasion"] == "Ordinary"

    # Correct church can update then delete.
    updated = update_service(sid, a, **{**_KW, "occasion": "Revised"})
    assert updated["occasion"] == "Revised"
    assert delete_service(sid, a) is True
    assert get_service(sid, a) is None


def test_list_saved_services_is_church_scoped(tmp_db, make_user, make_church):
    u = make_user(email="s3@x.org")
    a = make_church(name="A", timezone="America/New_York", owner_user_id=u)
    b = make_church(name="B", timezone="America/New_York", owner_user_id=u)
    save_service(a, created_by=u, **{**_KW, "occasion": "A1"})
    save_service(a, created_by=u, **{**_KW, "occasion": "A2"})
    save_service(b, created_by=u, **{**_KW, "occasion": "B1"})

    a_list = list_saved_services(a)
    b_list = list_saved_services(b)
    assert {s["occasion"] for s in a_list} == {"A1", "A2"}
    assert [s["occasion"] for s in b_list] == ["B1"]
