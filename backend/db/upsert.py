"""Dialect-aware INSERT that supports ``.on_conflict_do_nothing()`` (F §2.4).

SQLAlchemy has no portable "insert or ignore": PostgreSQL and SQLite each have
their own ``insert()`` construct with ``on_conflict_do_nothing``. insert_ignore
picks the right one for the process engine, so callers write one statement:

    insert_ignore(User.__table__).values(...).on_conflict_do_nothing(index_elements=["email"])

Used by repos.users.ensure_user (ops); later by membership accept (slice 1)
and hymn usage recording (slice 5a).
"""
from typing import Optional, Union

from sqlalchemy import Table
from sqlalchemy.dialects import postgresql, sqlite

from db.engine import get_engine

_INSERTS = {"postgresql": postgresql.insert, "sqlite": sqlite.insert}


def insert_ignore(
    table: Union[Table, type], *, dialect_name: Optional[str] = None
) -> Union[postgresql.Insert, sqlite.Insert]:
    """Dialect insert() that supports .on_conflict_do_nothing(); postgresql or sqlite only.

    `table` is a Table or a mapped class. The dialect is the process engine's
    (get_engine(), the one SessionLocal is bound to); `dialect_name` overrides
    it only so tests can compile the Postgres form without connecting.
    """
    name = dialect_name or get_engine().dialect.name
    try:
        make_insert = _INSERTS[name]
    except KeyError:
        raise NotImplementedError(
            f"insert_ignore supports postgresql and sqlite, not {name!r}"
        ) from None
    return make_insert(table)
