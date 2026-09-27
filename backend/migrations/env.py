"""Alembic environment (F §3.1; slice 1 spec, "Alembic setup").

URL: config.attributes["url"] when the caller set one (tests, the pg_db
fixture), else DATABASE_URL through db.engine._database_url() (the alembic
command line, Railway's pre-deploy command); always through
db.engine._normalize_url. No load_dotenv: a laptop run exports DATABASE_URL.

The "Database: ..." line goes to stderr, so `alembic upgrade ... --sql >
upgrade.sql` stays pure SQL. Logging comes from alembic.ini only when
config.attributes["configure_logger"] is not False.

Everything runs in ONE transaction (the default; no transaction_per_migration),
so a RAISE in 0003_lockdown rolls back 0002 to 0004 as well. On Postgres the
two timeouts run first, through context.execute inside that transaction.
Never call connection.execute() before context.configure(): SQLAlchemy 2.1
autobegins, Alembic then treats the transaction as external and does not
commit it, and closing the connection rolls every migration back while the
command still exits 0. Offline (--sql) the same code prints BEGIN;, the two
SET lines, the revisions and COMMIT;.
"""
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from api.startup import describe_database
from db.engine import _database_url, _normalize_url
from db.models import Base
from db.schema_check import include_object

config = context.config

if config.config_file_name and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata

POSTGRES_TIMEOUTS = ("SET LOCAL lock_timeout = '5s'", "SET LOCAL statement_timeout = '60s'")


def _configure_options(dialect_name: str) -> dict:
    return {
        "target_metadata": target_metadata,
        "include_object": include_object,
        "compare_type": True,
        "compare_server_default": False,
        # Batch mode affects autogenerate rendering only; hand-written ALTERs
        # on SQLite use op.batch_alter_table themselves (0004).
        "render_as_batch": dialect_name == "sqlite",
    }


def _run_in_one_transaction(dialect_name: str) -> None:
    with context.begin_transaction():
        if dialect_name == "postgresql":
            for statement in POSTGRES_TIMEOUTS:
                context.execute(statement)
        context.run_migrations()


def run_migrations_offline(url: str) -> None:
    dialect_name = make_url(url).get_backend_name()
    context.configure(
        url=url,
        literal_binds=True,
        # Named paramstyle: a literal % (0003's RAISE text) is not doubled.
        dialect_opts={"paramstyle": "named"},
        **_configure_options(dialect_name),
    )
    _run_in_one_transaction(dialect_name)


def run_migrations_online(url: str) -> None:
    engine = create_engine(url, poolclass=NullPool)
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, **_configure_options(connection.dialect.name))
            _run_in_one_transaction(connection.dialect.name)
    finally:
        engine.dispose()


database_url = _normalize_url(config.attributes.get("url") or _database_url())
print(f"Database: {describe_database(make_url(database_url))}", file=sys.stderr)

if context.is_offline_mode():
    run_migrations_offline(database_url)
else:
    run_migrations_online(database_url)
