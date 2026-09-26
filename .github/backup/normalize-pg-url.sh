#!/usr/bin/env bash
# Reads one Postgres URL on stdin and writes a libpq-compatible URL on stdout.
# Strips a SQLAlchemy driver suffix (postgresql+psycopg2:// -> postgresql://),
# which pg_dump and psql reject (inventory H5), and turns postgres:// into
# postgresql://. Never writes to stderr: the URL holds the database password.
# backup.yml and backend/tests/test_ops_workflows.py both run it as
# `bash .github/backup/normalize-pg-url.sh`, so its file mode does not matter.
set -euo pipefail
sed -E 's#^postgres(ql)?(\+[A-Za-z0-9_]+)?://#postgresql://#'
