"""db.upsert.insert_ignore: INSERT … ON CONFLICT DO NOTHING on SQLite and Postgres."""
import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.dialects import postgresql, sqlite

from db import session_scope
from db.models import User
from db.upsert import insert_ignore


def _insert_user(target, email="dup@example.com"):
    return (
        insert_ignore(target)
        .values(id=uuid.uuid4(), email=email)
        .on_conflict_do_nothing(index_elements=["email"])
    )


def _user_count():
    with session_scope() as s:
        return s.execute(select(func.count()).select_from(User)).scalar_one()


def test_insert_ignore_inserts_once_and_ignores_the_duplicate(tmp_db):
    stmt = _insert_user(User.__table__)
    assert isinstance(stmt, sqlite.Insert)          # dialect taken from the process engine
    with session_scope() as s:
        s.execute(stmt)
    with session_scope() as s:
        s.execute(_insert_user(User.__table__))     # same email, new id: ignored, no IntegrityError
    assert _user_count() == 1


def test_insert_ignore_accepts_a_mapped_class(tmp_db):
    with session_scope() as s:
        s.execute(_insert_user(User))
        s.execute(_insert_user(User))
    assert _user_count() == 1


def test_insert_ignore_rejects_other_dialects():
    with pytest.raises(NotImplementedError):
        insert_ignore(User.__table__, dialect_name="mysql")


def test_insert_ignore_compiles_on_conflict_do_nothing_for_postgres():
    stmt = (
        insert_ignore(User.__table__, dialect_name="postgresql")
        .values(id=uuid.uuid4(), email="dup@example.com")
        .on_conflict_do_nothing(index_elements=["email"])
    )
    assert isinstance(stmt, postgresql.Insert)
    sql = str(stmt.compile(dialect=postgresql.dialect()))   # compiles without connecting
    assert "ON CONFLICT (email) DO NOTHING" in sql
