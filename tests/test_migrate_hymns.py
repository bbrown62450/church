import uuid

from migrate_to_db import parse_hymn_page, import_hymn_catalog, run_migration
from db import session_scope
from repos.churches import list_user_churches
from repos.hymns import list_hymns


def _hymn_page(number, title, scripture=""):
    props = {
        "Hymn Title": {"type": "title", "title": [{"plain_text": title}]},
        "Hymn Number": {"type": "number", "number": number},
    }
    if scripture:
        props["Scripture References"] = {
            "type": "rich_text",
            "rich_text": [{"plain_text": scripture}],
        }
    return {"id": f"page-{number}", "properties": props}


def test_parse_hymn_page_flattens_notion_keys():
    parsed = parse_hymn_page(_hymn_page(43, "Holy, Holy, Holy", "Revelation 4:8"))
    assert parsed["number"] == 43
    assert parsed["title"] == "Holy, Holy, Holy"
    assert parsed["props"]["Hymn Title"] == "Holy, Holy, Holy"
    assert parsed["props"]["Scripture References"] == "Revelation 4:8"


def test_import_hymn_catalog_is_idempotent(tmp_db):
    pages = [
        _hymn_page(43, "Holy, Holy, Holy", "Revelation 4:8"),
        _hymn_page(649, "Amazing Grace", "John 9:25"),
    ]
    with session_scope() as session:
        first = import_hymn_catalog(session, pages)
    assert first == {"inserted": 2, "updated": 0, "total": 2}
    with session_scope() as session:
        second = import_hymn_catalog(session, pages)
    assert second["inserted"] == 0
    assert second["updated"] == 2


def test_run_migration_creates_owner_church_and_seeds(tmp_db):
    pages = [
        _hymn_page(43, "Holy, Holy, Holy", "Revelation 4:8"),
        _hymn_page(649, "Amazing Grace", "John 9:25"),
    ]
    report = run_migration(
        founder_email="Beau@Example.com",
        church_name="Conner Presbyterian",
        timezone="America/New_York",
        hymn_pages=pages,
    )
    user_id = uuid.UUID(report["founder_user_id"])
    owned = [c for c in list_user_churches(user_id) if c["role"] == "owner"]
    assert any(c["name"] == "Conner Presbyterian" for c in owned)

    church_id = uuid.UUID(report["church_id"])
    hymns = list_hymns(church_id)
    assert len(hymns) == 2
    assert {"Holy, Holy, Holy", "Amazing Grace"} <= {h.get("Hymn Title") for h in hymns}


def test_run_migration_is_idempotent(tmp_db):
    pages = [_hymn_page(1, "Come Thou Fount", "1 Samuel 7:12")]
    first = run_migration(
        founder_email="beau@example.com",
        church_name="Conner Presbyterian",
        timezone="America/New_York",
        hymn_pages=pages,
    )
    second = run_migration(
        founder_email="beau@example.com",
        church_name="Conner Presbyterian",
        timezone="America/New_York",
        hymn_pages=pages,
    )
    assert second["church_id"] == first["church_id"]
    user_id = uuid.UUID(second["founder_user_id"])
    named = [c for c in list_user_churches(user_id) if c["name"] == "Conner Presbyterian"]
    assert len(named) == 1
    assert len(list_hymns(uuid.UUID(second["church_id"]))) == 1
