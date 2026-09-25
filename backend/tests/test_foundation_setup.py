from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]   # repo root (this file is backend/tests/...)


def test_backend_requirements_pin_runtime_and_migration_deps():
    text = (ROOT / "backend" / "requirements.txt").read_text()
    assert "SQLAlchemy>=2.0" in text
    assert "psycopg2-binary" in text
    # notion-client is kept ONLY for the one-time migration script.
    assert "notion-client" in text
    assert "migration only" in text.lower()
    # The API must not depend on Streamlit.
    assert "streamlit" not in text.lower()


def test_root_requirements_add_streamlit_on_top_of_backend():
    text = (ROOT / "requirements.txt").read_text()
    assert "-r backend/requirements.txt" in text
    assert "streamlit[auth]>=1.45.0" in text
    # The old shared-password-era bare streamlit pin must be gone.
    assert "\nstreamlit>=1.28.0" not in text


def test_gitignore_covers_local_db_and_secrets():
    text = (ROOT / ".gitignore").read_text()
    assert "data/*.db" in text
    assert ".streamlit/secrets.toml" in text


def test_backend_deploy_files_run_uvicorn_on_python_311():
    procfile = (ROOT / "backend" / "Procfile").read_text()
    assert "uvicorn api.main:app" in procfile
    assert "$PORT" in procfile
    assert (ROOT / "backend" / ".python-version").read_text().strip() == "3.11"
