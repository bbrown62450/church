"""Reuse the backend's database fixtures for the Streamlit-only tests."""
from tests.conftest import make_church, make_user, seed_catalog, tmp_db  # noqa: F401
