import json
import re
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


# --- ops slice (ops-1): dead code and configuration drift (inv H8, H10, H11, H12) ---

# Spelled in parts so that the ops spec's whole-word grep (acceptance criterion 6),
# which must find nothing under backend/, does not match this test.
DELETED_DEAD_MODULES = tuple("_".join(parts) + ".py" for parts in (
    ("email", "send"),
    ("notion", "archive"),
    ("notion", "usage"),
    ("select", "sunday", "hymns"),
    ("add", "hymnary", "links"),
    ("fix", "hymn", "titles"),
))


def test_dead_modules_are_deleted():
    found = [str(p.relative_to(ROOT)) for name in DELETED_DEAD_MODULES
             for p in (ROOT / "backend").rglob(name)]
    assert found == []


def test_backend_env_example_lists_the_ops_settings():
    text = (ROOT / "backend" / ".env.example").read_text()
    missing = [key for key in ("APP_ENV", "LOG_LEVEL", "DB_POOL_SIZE", "DB_MAX_OVERFLOW", "ESV_API_KEY")
               if not re.search(rf"^{key}=", text, re.MULTILINE)]
    assert missing == []
    # Supavisor Pool Size is 15 (Nano): 2 x (3 + 3) + 2 = 14 <= 15 (owner, 2026-09-25).
    assert re.search(r"^DB_POOL_SIZE=3$", text, re.MULTILINE)
    assert re.search(r"^DB_MAX_OVERFLOW=3$", text, re.MULTILINE)


def test_shadcn_is_a_dev_dependency_only():
    package = json.loads((ROOT / "frontend" / "package.json").read_text())
    assert "shadcn" in package["devDependencies"]
    assert "shadcn" not in package["dependencies"]
