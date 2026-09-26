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


def test_main_names_the_database_before_changing_it(tmp_path, monkeypatch, capsys):
    # A wrong DATABASE_URL (or a stray .env) whose schema is already current
    # prints the same "already present" as a correct run, so the target comes first.
    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE hymns (id VARCHAR PRIMARY KEY, title VARCHAR)"))
        conn.execute(text("CREATE TABLE hymn_catalog (id VARCHAR PRIMARY KEY, title VARCHAR)"))
    monkeypatch.setattr(migrate_add_hymn_facts, "get_engine", lambda: engine)

    migrate_add_hymn_facts.main()

    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == f"Database: sqlite:///{tmp_path / 'old.db'}"
    assert lines[1].startswith("Added: ")


def test_main_hides_the_database_password(monkeypatch, capsys):
    # create_engine does not connect, and run is replaced, so nothing is contacted.
    engine = create_engine("postgresql+psycopg2://app:s3cret@pooler.example.invalid:6543/postgres")
    monkeypatch.setattr(migrate_add_hymn_facts, "get_engine", lambda: engine)
    monkeypatch.setattr(migrate_add_hymn_facts, "run", lambda _engine: [])

    migrate_add_hymn_facts.main()

    out = capsys.readouterr().out
    assert out.splitlines()[0] == "Database: postgresql+psycopg2://app:***@pooler.example.invalid:6543/postgres"
    assert "s3cret" not in out
