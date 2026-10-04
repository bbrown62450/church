import configparser
import json
import re
from pathlib import Path

import pytest

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


# --- ops slice (ops-3): the frontend error union gets db_unavailable (slice 1) ---

FRONTEND_ERROR_UNION = ROOT / "frontend" / "src" / "lib" / "api" / "errors.ts"


def _missing_error_codes(path, codes=("db_unavailable",)):
    """Codes the frontend error union lacks; [] while the file does not exist.

    Slice 1 creates src/lib/api/errors.ts (F §4.11). Until then this check is
    inert; from then on it fails slice 1's CI if the union lacks a code that
    ops added to the backend."""
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    return [code for code in codes if not re.search(rf"""["']{code}["']""", text)]


def test_frontend_error_union_lists_db_unavailable_once_it_exists():
    assert _missing_error_codes(FRONTEND_ERROR_UNION) == []


@pytest.mark.parametrize("content, missing", [
    (None, []),
    ('export type ErrorCode = "not_found" | "internal_error";\n', ["db_unavailable"]),
    ('export type ErrorCode = "not_found" | "db_unavailable";\n', []),
], ids=["no-file-yet", "code-missing", "code-present"])
def test_missing_error_codes_reads_the_union(tmp_path, content, missing):
    path = tmp_path / "errors.ts"
    if content is not None:
        path.write_text(content, encoding="utf-8")
    assert _missing_error_codes(path) == missing


# --- slice 1a: Alembic, tzdata, exact minor pins and the postgres marker (S Backend 1a) ---

def test_backend_requirements_add_alembic_tzdata_and_exact_minor_pins():
    lines = {line.strip() for line in (ROOT / "backend" / "requirements.txt").read_text().splitlines()}
    assert {"alembic>=1.20", "tzdata>=2026.4", "fastapi==0.141.*", "pydantic==2.13.*"} <= lines
    assert "fastapi>=0.115" not in lines          # replaced by the exact minor pin


def test_pytest_ini_declares_the_postgres_marker():
    ini = configparser.ConfigParser()
    ini.read(ROOT / "pytest.ini")
    markers = [line.strip() for line in ini["pytest"]["markers"].splitlines() if line.strip()]
    assert markers == ["postgres: needs TEST_DATABASE_URL (runs in the backend-postgres CI job)"]


# --- slice 1a: Alembic (F §3.1; slice 1 spec, "Alembic setup") ---

def test_alembic_ini_uses_here_paths_and_has_logging_sections():
    ini = configparser.RawConfigParser()
    assert ini.read(ROOT / "backend" / "alembic.ini", encoding="utf-8")
    assert ini.get("alembic", "script_location") == "%(here)s/migrations"
    assert ini.get("alembic", "prepend_sys_path") == "%(here)s"
    assert ini.get("alembic", "path_separator") == "os"
    assert not ini.has_option("alembic", "sqlalchemy.url")    # env.py owns the URL
    for section in ("loggers", "handlers", "formatters", "logger_root", "logger_sqlalchemy",
                    "logger_alembic", "handler_console", "formatter_generic"):
        assert ini.has_section(section), section
    assert ini.get("handler_console", "args") == "(sys.stderr,)"


# --- slice 1a: the one-off schema scripts give way to Alembic (F §3.2; S amendment 2026-09-26) ---

def test_one_off_schema_scripts_are_deleted():
    backend = ROOT / "backend"
    for gone in ("migrate_add_hymnal.py", "migrate_add_hymn_facts.py", "tests/test_migrate_hymn_facts.py"):
        assert not (backend / gone).exists(), gone
    # The data backfill stays as an ops CLI (data, not schema) and now points at Alembic.
    backfill = (backend / "backfill_hymn_facts.py").read_text(encoding="utf-8")
    assert "Run after `alembic upgrade head`" in backfill
    assert "migrate_add_hymn_facts" not in backfill
    assert (backend / "hymnary_facts.py").is_file()


def test_readme_says_hymn_facts_columns_come_from_alembic():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    section = readme.split("### Service rubric: hymn year and familiarity", 1)[1].split("\n## ", 1)[0]
    assert "1. The columns come from the Alembic migrations (`alembic upgrade head`)." in section
    assert "backfill_hymn_facts.py --dry-run" in section            # steps 2 and 3 unchanged
    assert "migrate_add_hymn_facts" not in readme
    assert "migrate_add_hymnal" not in readme


# --- slice 1a: Railway deploy settings (S backend/railway.toml, F §3.3) --------
# Railway does not read backend/railway.toml for this service (Config as Code
# is closed to it): the pre-deploy command and the health check path live in
# Railway → the API service → Settings → Deploy. The file records those values.

def test_railway_toml_runs_migrations_and_checks_readiness():
    import tomllib

    config = tomllib.loads((ROOT / "backend" / "railway.toml").read_text(encoding="utf-8"))
    # Exactly the two values set in the Railway UI (Pre-deploy Command,
    # Healthcheck Path): the start command stays in backend/Procfile.
    assert config == {"deploy": {
        "preDeployCommand": ["alembic upgrade head"],
        "healthcheckPath": "/health/ready",
    }}


# --- printed bulletin PR 3a build review M5: Pillow's limits were measured on 12.3 ---

def test_backend_requirements_pin_pillow_to_the_measured_minor():
    from importlib.metadata import version

    lines = {line.strip() for line in (ROOT / "backend" / "requirements.txt").read_text().splitlines()}
    assert "pillow>=12.3,<13" in lines
    major, minor = (int(part) for part in version("pillow").split(".")[:2])
    assert major == 12 and minor >= 3                                    # what this machine and CI install
