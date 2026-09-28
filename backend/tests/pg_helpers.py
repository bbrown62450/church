"""Helpers for the Postgres-only tests (`@pytest.mark.postgres`; F §5.1).

Every Postgres URL a test uses passes require_local_test_url first, so a test
can never create roles, drop databases or TRUNCATE tables anywhere but a
local, throwaway Postgres (the same rule as pg_smoke.py).

throwaway_database and supabase_roles (Task 8) create cluster-wide roles and
a whole database on that local Postgres, and drop them again on the way out.
"""
import secrets
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator
from urllib.parse import urlsplit

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.pool import NullPool

from db.engine import _normalize_url

LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1")


def require_local_test_url(url: str) -> str:
    """Return `url` if it is a Postgres URL on this machine, else raise RuntimeError."""
    try:
        parts = urlsplit(url or "")
        host = parts.hostname
    except ValueError:              # e.g. an unbalanced "[" in the host
        parts, host = None, None
    if parts is None or not parts.scheme.startswith("postgres") or host not in LOCAL_HOSTS:
        raise RuntimeError("TEST_DATABASE_URL must point at a local, throwaway Postgres.")
    return url


@dataclass(frozen=True)
class ThrowawayDb:
    name: str           # the database, wsb_lockdown_<hex>
    role: str           # LOGIN role wsb_t_<hex>: owns the database, runs the migrations
    role_url: str       # the database, connected as `role`
    admin_db_url: str   # the database, connected as the admin (superuser) role
    other_role: str     # NOLOGIN role wsb_o_<hex>: owns tables `role` must not own


def _admin_engine(admin_url: str) -> Engine:
    # CREATE DATABASE and DROP DATABASE cannot run inside a transaction.
    return create_engine(_normalize_url(admin_url), isolation_level="AUTOCOMMIT", poolclass=NullPool)


@contextmanager
def throwaway_database(admin_url: str, *, role_bypassrls: bool = False) -> Iterator[ThrowawayDb]:
    """A new database owned by a new LOGIN role, both dropped on exit.

    `admin_url` is TEST_DATABASE_URL (CI's superuser, which may grant
    BYPASSRLS). The role owns the database, so it has CREATE on its `public`
    schema (since Postgres 15 only the database owner has it) and 0001 runs
    as it; it is not a superuser, so 0003's ownership rules apply to it.
    """
    admin_url = require_local_test_url(admin_url)
    suffix = secrets.token_hex(4)
    name, role, other_role = f"wsb_lockdown_{suffix}", f"wsb_t_{suffix}", f"wsb_o_{suffix}"
    password = secrets.token_hex(16)
    rls = "BYPASSRLS" if role_bypassrls else "NOBYPASSRLS"
    base = make_url(admin_url)
    admin = _admin_engine(admin_url)
    try:
        with admin.connect() as conn:
            conn.exec_driver_sql(f"CREATE ROLE {role} LOGIN {rls} PASSWORD '{password}'")
            conn.exec_driver_sql(f"CREATE ROLE {other_role} NOLOGIN")
            conn.exec_driver_sql(f"CREATE DATABASE {name} OWNER {role}")
        yield ThrowawayDb(
            name=name,
            role=role,
            role_url=base.set(username=role, password=password, database=name)
                         .render_as_string(hide_password=False),
            admin_db_url=base.set(database=name).render_as_string(hide_password=False),
            other_role=other_role,
        )
    finally:
        with admin.connect() as conn:
            conn.exec_driver_sql(f"DROP DATABASE IF EXISTS {name} WITH (FORCE)")
            conn.exec_driver_sql(f"DROP ROLE IF EXISTS {role}")
            conn.exec_driver_sql(f"DROP ROLE IF EXISTS {other_role}")
        admin.dispose()


@contextmanager
def supabase_roles(admin_url: str) -> Iterator[None]:
    """Make sure the NOLOGIN roles anon and authenticated exist, as on Supabase.

    Drops on exit only the ones it created. Enter it BEFORE throwaway_database,
    so the database (and every grant to these roles inside it) is gone before
    the roles are dropped.
    """
    admin = _admin_engine(require_local_test_url(admin_url))
    created = []
    try:
        with admin.connect() as conn:
            for name in ("anon", "authenticated"):
                exists = conn.execute(
                    text("SELECT 1 FROM pg_roles WHERE rolname = :name"), {"name": name}).first()
                if exists is None:
                    conn.exec_driver_sql(f"CREATE ROLE {name} NOLOGIN")
                    created.append(name)
        yield
    finally:
        with admin.connect() as conn:
            for name in created:
                conn.exec_driver_sql(f"DROP ROLE IF EXISTS {name}")
        admin.dispose()
