"""Schema checks shared by migrations/env.py, the API's startup check, the
drift script and the tests (F §3.1, §2.6; slice 1 spec, "Modules added").

- alembic_config: the Alembic Config, built from alembic.ini's absolute
  path (never the working directory). `url` reaches env.py through
  cfg.attributes["url"]; configure_logger=False keeps env.py from
  reconfiguring logging (every in-process caller passes it).
- include_object: autogenerate never looks at reflected tables that the
  models do not declare (alembic_version, anything else in the schema), so
  it never proposes dropping them.
- schema_diff: compare_metadata between a live connection and the models,
  with the same options env.py uses. It does not run env.py.

Imports no FastAPI and nothing from api/ (layering, F §2.2).
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from alembic.util import CommandError
from sqlalchemy.engine import Connection

from db.engine import Base

ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"


def alembic_config(*, url: str | None = None, configure_logger: bool = True) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    if url is not None:
        cfg.attributes["url"] = url
    cfg.attributes["configure_logger"] = configure_logger
    return cfg


def include_object(obj, name, type_, reflected, compare_to) -> bool:
    """False only for a table that exists in the database but not in the models."""
    return not (type_ == "table" and reflected and compare_to is None)


def schema_diff(conn: Connection) -> list:
    """Differences between the database behind `conn` and the models ([] = none)."""
    from db import models  # noqa: F401  (registers every table on Base.metadata)

    context = MigrationContext.configure(conn, opts={
        "compare_type": True,
        "compare_server_default": False,
        "include_object": include_object,
    })
    return compare_metadata(context, Base.metadata)


@dataclass(frozen=True)
class RevisionState:
    """Where a database stands against this release's migration scripts.

    state: "current" (at head), "behind" (no alembic_version row, or a revision
    these scripts know that is not head), "ahead" (a revision these scripts do
    not know: a newer release ran, then was rolled back) or "unknown" (the
    check itself failed; only run_startup_checks returns it).
    """
    current: str | None
    head: str | None
    state: Literal["current", "behind", "ahead", "unknown"]


def revision_state(conn: Connection) -> RevisionState:
    """Compare the database's alembic_version with this release's head.

    Reads the scripts through ScriptDirectory, so env.py never runs here (no
    logging reconfiguration, no Database: line). Raises what the database
    raises; callers that must not fail wrap it (run_startup_checks).
    """
    script = ScriptDirectory.from_config(alembic_config(configure_logger=False))
    head = script.get_current_head()
    current = MigrationContext.configure(conn).get_current_revision()
    if current == head:
        return RevisionState(current, head, "current")
    if current is None:
        return RevisionState(current, head, "behind")
    try:
        script.get_revision(current)
    except CommandError:                               # not one of this release's revisions
        return RevisionState(current, head, "ahead")
    return RevisionState(current, head, "behind")


def _name(obj) -> str:
    """An index's or constraint's name; `<table>(<cols>)` when it has none."""
    if isinstance(obj.name, str) and obj.name:
        return obj.name
    table = getattr(obj, "table", None)
    columns = ",".join(column.name for column in getattr(obj, "columns", ()))
    return f"{table.name if table is not None else '?'}({columns})"


def _type(value) -> str:
    try:
        return str(value)
    except Exception:  # noqa: BLE001 - a type that only compiles on its own dialect
        return repr(value)


def _entry_lines(entry) -> list[str]:
    if isinstance(entry, list):                        # compare_metadata nests modify_* entries
        return [line for item in entry for line in _entry_lines(item)]
    kind = entry[0] if isinstance(entry, tuple) and entry else None
    if kind in ("add_table", "remove_table"):
        return [f"{kind} {entry[1].name}"]
    if kind in ("add_column", "remove_column"):        # (kind, schema, table, Column)
        return [f"{kind} {entry[2]}.{entry[3].name}"]
    if kind in ("add_index", "remove_index", "add_constraint", "remove_constraint",
                "add_fk", "remove_fk"):
        return [f"{kind} {_name(entry[1])}"]
    if kind == "modify_nullable":                      # (kind, schema, table, column, kw, old, new)
        return [f"modify_nullable {entry[2]}.{entry[3]} {entry[5]} -> {entry[6]}"]
    if kind == "modify_type":
        return [f"modify_type {entry[2]}.{entry[3]} {_type(entry[5])} -> {_type(entry[6])}"]
    if kind == "modify_default":
        return [f"modify_default {entry[2]}.{entry[3]}"]
    return [repr(entry)]


def format_diff(diff: list) -> list[str]:
    """schema_diff() as sorted text lines, one per difference (runbook step 6)."""
    return sorted(line for entry in diff for line in _entry_lines(entry))
