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
