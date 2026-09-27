"""Helpers for the Postgres-only tests (`@pytest.mark.postgres`; F §5.1).

Every Postgres URL a test uses passes require_local_test_url first, so a test
can never create roles, drop databases or TRUNCATE tables anywhere but a
local, throwaway Postgres (the same rule as pg_smoke.py).
"""
from urllib.parse import urlsplit

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
