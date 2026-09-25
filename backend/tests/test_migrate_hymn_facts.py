from sqlalchemy import create_engine, inspect, text

import migrate_add_hymn_facts


def _columns(engine, table):
    return {c["name"] for c in inspect(engine).get_columns(table)}


def test_adds_missing_columns_once(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with engine.begin() as conn:  # the pre-feature schema, trimmed to what matters
        conn.execute(text("CREATE TABLE hymns (id VARCHAR PRIMARY KEY, title VARCHAR)"))
        conn.execute(text("CREATE TABLE hymn_catalog (id VARCHAR PRIMARY KEY, title VARCHAR)"))

    added = migrate_add_hymn_facts.run(engine)
    assert sorted(added) == [
        "hymn_catalog.hymnal_count", "hymn_catalog.text_year",
        "hymns.hymnal_count", "hymns.text_year",
    ]
    for table in ("hymns", "hymn_catalog"):
        assert {"text_year", "hymnal_count"} <= _columns(engine, table)

    assert migrate_add_hymn_facts.run(engine) == []   # idempotent


def test_noop_on_a_current_database(tmp_db):
    assert migrate_add_hymn_facts.run(tmp_db) == []
