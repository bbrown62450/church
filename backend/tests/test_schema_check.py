"""db.schema_check: the Alembic config, include_object and schema_diff (F §3.1, §2.6)."""
import subprocess
import sys
from pathlib import Path

from alembic.script import ScriptDirectory
from sqlalchemy import Column, Integer, MetaData, Table

from db.engine import Base
from db.schema_check import ALEMBIC_INI, alembic_config, include_object, schema_diff

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"


def test_alembic_config_finds_the_scripts_from_the_repo_root(monkeypatch):
    monkeypatch.chdir(ROOT)
    script = ScriptDirectory.from_config(alembic_config(configure_logger=False))
    assert Path(script.dir).resolve() == (BACKEND / "migrations").resolve()
    assert (Path(script.dir) / "env.py").is_file()


def test_alembic_config_finds_the_scripts_from_backend():
    code = ("from alembic.script import ScriptDirectory; from db.schema_check import alembic_config; "
            "print(ScriptDirectory.from_config(alembic_config(configure_logger=False)).dir)")
    result = subprocess.run([sys.executable, "-c", code], cwd=BACKEND, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert Path(result.stdout.strip()).resolve() == (BACKEND / "migrations").resolve()


def test_alembic_config_sets_the_url_and_logger_attributes():
    assert ALEMBIC_INI == BACKEND.resolve() / "alembic.ini"
    cfg = alembic_config(url="sqlite:///x.db", configure_logger=False)
    assert cfg.config_file_name == str(ALEMBIC_INI)
    assert cfg.attributes == {"url": "sqlite:///x.db", "configure_logger": False}
    assert alembic_config().attributes == {"configure_logger": True}


def test_include_object_skips_reflected_tables_not_in_the_models(tmp_db):
    users = Base.metadata.tables["users"]
    assert include_object(None, "alembic_version", "table", True, None) is False
    assert include_object(users, "users", "table", True, users) is True
    assert include_object(users, "users", "table", False, None) is True      # missing: reported
    assert include_object(None, "ix_legacy", "index", True, None) is True
    Table("legacy_notes", MetaData(), Column("id", Integer, primary_key=True)).create(tmp_db)
    Base.metadata.tables["contacts"].drop(tmp_db)
    with tmp_db.connect() as conn:
        diff = schema_diff(conn)
    assert sorted((entry[0], entry[1].name) for entry in diff) == [
        ("add_index", "ix_contacts_church_id"), ("add_table", "contacts")]


def test_schema_diff_is_empty_for_a_create_all_database(tmp_db):
    with tmp_db.connect() as conn:
        assert schema_diff(conn) == []


# --- Task 10: revision_state, format_diff and scripts/schema_drift.py ---------
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from db.schema_check import (
    RevisionState,
    alembic_config,
    format_diff,
    revision_state,
    schema_diff,
)

EXPECTED_HEAD = "0008_invites_integrity"
# What a database stamped at 0001_baseline lacks (runbook step 6, sorted):
# 0004's invites changes, then 0005's and 0006's services changes (slice 5a-2,
# printed bulletin PR 2b), then 0007's table (printed bulletin PR 3a), then
# 0008's removed constraint (slice 6b-1; SQLite reflects no expression index,
# so its new uq_invites_pending_email is not listed here; Postgres lists it).
BASELINE_DRIFT = [
    "add_column invites.accepted_by",
    "add_column invites.reusable",
    "add_column services.bulletin",
    "add_column services.custom_elements",
    "add_column services.hymnal",
    "add_fk fk_invites_accepted_by_users",
    "add_index ix_bulletin_images_church_created",
    "add_index ix_services_church_date",
    "add_table bulletin_images",
    "remove_constraint uq_invites_church_email",
]
BACKEND_DIR = Path(__file__).resolve().parents[1]
SCHEMA_DRIFT = BACKEND_DIR / "scripts" / "schema_drift.py"


def _sqlite_file_url(tmp_path, name="drift.db"):
    return f"sqlite:///{tmp_path / name}"


def _upgrade_to(url, revision):
    """In-process `alembic upgrade`, with the URL passed explicitly (never DATABASE_URL)."""
    command.upgrade(alembic_config(url=url, configure_logger=False), revision)


def _state_of(url):
    engine = create_engine(url, poolclass=NullPool)
    try:
        with engine.connect() as conn:
            return revision_state(conn)
    finally:
        engine.dispose()


def _load_schema_drift():
    """backend/scripts is not a package: load the script by path, as `python scripts/…` does."""
    spec = importlib.util.spec_from_file_location("schema_drift_under_test", SCHEMA_DRIFT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_head_is_0008_invites_integrity():
    script = ScriptDirectory.from_config(alembic_config(configure_logger=False))
    assert script.get_current_head() == EXPECTED_HEAD


def test_revision_state_on_an_empty_database_is_behind(tmp_path):
    assert _state_of(_sqlite_file_url(tmp_path)) == RevisionState(None, EXPECTED_HEAD, "behind")


def test_revision_state_at_head_is_current(tmp_path):
    url = _sqlite_file_url(tmp_path)
    _upgrade_to(url, "head")
    assert _state_of(url) == RevisionState(EXPECTED_HEAD, EXPECTED_HEAD, "current")


def test_revision_state_at_baseline_is_behind(tmp_path):
    url = _sqlite_file_url(tmp_path)
    _upgrade_to(url, "0001_baseline")
    assert _state_of(url) == RevisionState("0001_baseline", EXPECTED_HEAD, "behind")


def test_an_unknown_revision_is_ahead(tmp_path):
    """A database migrated by a newer release that was then rolled back."""
    url = _sqlite_file_url(tmp_path)
    _upgrade_to(url, "head")
    engine = create_engine(url, poolclass=NullPool)
    try:
        with engine.begin() as conn:
            conn.execute(text("UPDATE alembic_version SET version_num = '0005_from_the_future'"))
    finally:
        engine.dispose()
    assert _state_of(url) == RevisionState("0005_from_the_future", EXPECTED_HEAD, "ahead")


def test_schema_diff_at_baseline_lists_exactly_the_0004_to_0008_changes(tmp_path):
    """0001_baseline stands in for production after `alembic stamp 0001_baseline`."""
    url = _sqlite_file_url(tmp_path)
    _upgrade_to(url, "0001_baseline")
    engine = create_engine(url, poolclass=NullPool)
    try:
        with engine.connect() as conn:
            assert format_diff(schema_diff(conn)) == BASELINE_DRIFT
    finally:
        engine.dispose()


def test_format_diff_renders_each_entry_kind():
    md = sa.MetaData()
    users = sa.Table("users", md, sa.Column("id", sa.Integer, primary_key=True))
    things = sa.Table(
        "things", md,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer),
        sa.Column("label", sa.String(20)),
    )
    fk = sa.ForeignKeyConstraint(["user_id"], [users.c.id], name="fk_things_user")
    things.append_constraint(fk)
    unique = sa.UniqueConstraint(things.c.label, name="uq_things_label")
    things.append_constraint(unique)
    index = sa.Index("ix_things_label", things.c.label)
    diff = [
        ("add_table", things),
        ("remove_table", users),
        ("add_column", None, "things", things.c.label),
        ("remove_column", None, "things", sa.Column("old", sa.Integer)),
        ("add_index", index),
        ("remove_index", sa.Index("ix_gone", things.c.user_id)),
        ("add_constraint", unique),
        ("remove_constraint", sa.UniqueConstraint(things.c.user_id, name="uq_gone")),
        ("add_fk", fk),
        ("remove_fk", sa.ForeignKeyConstraint(["user_id"], [users.c.id], name="fk_gone")),
        [                                              # compare_metadata nests modify_* entries
            ("modify_nullable", None, "things", "label", {}, True, False),
            ("modify_type", None, "things", "label", {}, sa.String(10), sa.String(20)),
            ("modify_default", None, "things", "label", {}, None, "x"),
        ],
        ("add_table_comment", things),                 # a kind format_diff does not know
    ]
    assert format_diff(diff) == sorted([
        "add_table things",
        "remove_table users",
        "add_column things.label",
        "remove_column things.old",
        "add_index ix_things_label",
        "remove_index ix_gone",
        "add_constraint uq_things_label",
        "remove_constraint uq_gone",
        "add_fk fk_things_user",
        "remove_fk fk_gone",
        "modify_nullable things.label True -> False",
        "modify_type things.label VARCHAR(10) -> VARCHAR(20)",
        "modify_default things.label",
        repr(("add_table_comment", things)),
    ])


def test_schema_drift_exits_1_at_baseline_and_prints_the_diff(tmp_path, monkeypatch, capsys):
    url = _sqlite_file_url(tmp_path)
    _upgrade_to(url, "0001_baseline")
    capsys.readouterr()                                   # drop env.py's own Database: line
    monkeypatch.setenv("DATABASE_URL", url)
    assert _load_schema_drift().main([]) == 1
    out, err = capsys.readouterr()
    assert out.splitlines() == [
        f"revision: 0001_baseline head: {EXPECTED_HEAD} state: behind",
        *BASELINE_DRIFT,
    ]
    assert err.startswith("Database: dialect=sqlite driver=pysqlite host=- database=")


def test_schema_drift_exits_0_at_head(tmp_path, monkeypatch, capsys):
    url = _sqlite_file_url(tmp_path)
    _upgrade_to(url, "head")
    capsys.readouterr()
    monkeypatch.setenv("DATABASE_URL", url)
    assert _load_schema_drift().main([]) == 0
    out, _err = capsys.readouterr()
    assert out.splitlines() == [f"revision: {EXPECTED_HEAD} head: {EXPECTED_HEAD} state: current"]


def test_schema_drift_refuses_without_database_url(monkeypatch, capsys):
    """Never falls back to the local SQLite default: the owner must export the URL."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert _load_schema_drift().main([]) == 2
    out, err = capsys.readouterr()
    assert (out, err) == ("", "DATABASE_URL is not set.\n")


def test_schema_drift_script_runs_from_backend(tmp_path):
    """Runbook step 6 runs `python scripts/schema_drift.py` from backend/, where
    sys.path[0] is backend/scripts; the script must still import db and api."""
    url = _sqlite_file_url(tmp_path)
    _upgrade_to(url, "head")
    env = {**os.environ, "DATABASE_URL": url}
    result = subprocess.run([sys.executable, "scripts/schema_drift.py"], cwd=BACKEND_DIR, env=env,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"revision: {EXPECTED_HEAD} head: {EXPECTED_HEAD} state: current\n"
    assert "Database: dialect=sqlite" in result.stderr
