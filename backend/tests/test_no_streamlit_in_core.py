"""The API imports auth and tenancy, and the API must run without Streamlit."""
import subprocess
import sys
from pathlib import Path

# The directory that holds tests/ — the repo root now, backend/ after the move.
CODE_DIR = Path(__file__).resolve().parents[1]


def test_auth_and_tenancy_do_not_import_streamlit():
    code = "import sys, auth, tenancy; sys.exit(1 if 'streamlit' in sys.modules else 0)"
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=CODE_DIR, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr or "streamlit was imported"


def test_usecases_package_imports_no_fastapi_or_streamlit():
    # usecases, domain_errors and db.ids are below the API layer (F §2.2).
    code = ("import sys, usecases, domain_errors, db.ids; "
            "bad = sorted({m.split('.')[0] for m in sys.modules} & {'fastapi', 'starlette', 'streamlit'}); "
            "print(bad); sys.exit(1 if bad else 0)")
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=CODE_DIR, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
