from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_requirements_pins_runtime_and_migration_deps():
    text = (ROOT / "requirements.txt").read_text()
    assert "streamlit[auth]>=1.45.0" in text
    assert "SQLAlchemy>=2.0" in text
    assert "psycopg2-binary" in text
    # notion-client is kept ONLY for the one-time migration script.
    assert "notion-client" in text
    assert "migration only" in text.lower()
    # The old shared-password-era bare streamlit pin must be gone.
    assert "\nstreamlit>=1.28.0" not in text


def test_gitignore_covers_local_db_and_secrets():
    text = (ROOT / ".gitignore").read_text()
    assert "data/*.db" in text
    assert ".streamlit/secrets.toml" in text
