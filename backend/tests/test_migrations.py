"""Alembic migrations: env.py, the revisions, offline SQL (F §3.1-§3.3; slice 1 spec)."""
import logging.config

import pytest
from alembic import command

from db.schema_check import ALEMBIC_INI, alembic_config


def _alembic(url: str, *args, **kw):
    """Run one Alembic command in-process on `url`; never reads DATABASE_URL, never touches logging."""
    return getattr(command, args[0])(alembic_config(url=url, configure_logger=False), *args[1:], **kw)


@pytest.fixture
def sqlite_url(tmp_path):
    return f"sqlite:///{tmp_path / 'migrations.db'}"


# --- env.py -------------------------------------------------------------------

@pytest.mark.parametrize("configure_logger", [True, False])
def test_env_py_configures_logging_only_when_asked(monkeypatch, sqlite_url, configure_logger):
    calls = []
    monkeypatch.setattr(logging.config, "fileConfig", lambda *a, **kw: calls.append((a, kw)))
    command.current(alembic_config(url=sqlite_url, configure_logger=configure_logger))
    expected = [((str(ALEMBIC_INI),), {"disable_existing_loggers": False})] if configure_logger else []
    assert calls == expected


def test_env_py_uses_the_configured_url_not_database_url(monkeypatch, capsys, sqlite_url, tmp_path):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@pooler.invalid:5432/postgres")
    _alembic(sqlite_url, "current")
    err = capsys.readouterr().err
    assert "Database: dialect=sqlite" in err
    assert "pooler.invalid" not in err
    assert (tmp_path / "migrations.db").exists()


def test_env_py_prints_the_database_line_to_stderr_only(capsys, sqlite_url, tmp_path):
    _alembic(sqlite_url, "current")
    out, err = capsys.readouterr()
    assert f"Database: dialect=sqlite driver=pysqlite host=- database={tmp_path / 'migrations.db'}\n" in err
    assert "Database:" not in out
