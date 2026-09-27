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
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
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
