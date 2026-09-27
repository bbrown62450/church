"""The local-URL guard every Postgres-only test goes through (F §5.1)."""
import pytest

from tests.pg_helpers import require_local_test_url


@pytest.mark.parametrize("url", [
    "postgresql://postgres:ci-throwaway@localhost:5432/postgres",
    "postgresql+psycopg2://postgres:pw@127.0.0.1:5432/postgres",
    "postgres://postgres:pw@[::1]:5432/postgres",
], ids=["localhost", "127.0.0.1", "ipv6-loopback"])
def test_local_test_url_guard_accepts_loopback_postgres(url):
    assert require_local_test_url(url) == url


@pytest.mark.parametrize("url", [
    "postgresql://u:p@aws-0.pooler.supabase.com:5432/postgres",
    "sqlite:///x.db",
    "",
], ids=["supabase-pooler", "sqlite", "empty"])
def test_local_test_url_guard_rejects_remote_or_non_postgres(url):
    with pytest.raises(RuntimeError, match="TEST_DATABASE_URL must point at a local, throwaway Postgres."):
        require_local_test_url(url)
