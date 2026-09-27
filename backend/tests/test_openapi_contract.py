"""The committed OpenAPI snapshot matches the live API (F §1.11; S test_openapi_contract).

frontend/src/lib/api/openapi.json feeds `npm run gen:api` (schema.d.ts), so a
backend change that alters the API must regenerate it in the same PR. These
tests never write the committed file: they compare text, or write to tmp_path.
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "backend" / "scripts" / "export_openapi.py"
COMMITTED = REPO_ROOT / "frontend" / "src" / "lib" / "api" / "openapi.json"
REGENERATE = ".venv/bin/python backend/scripts/export_openapi.py"


def _load_export_openapi():
    """backend/scripts is not a package: load the script by path, as `python backend/scripts/…` does."""
    spec = importlib.util.spec_from_file_location("export_openapi_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_committed_openapi_matches_the_live_schema():
    live = _load_export_openapi().render_openapi()
    committed = COMMITTED.read_text(encoding="utf-8") if COMMITTED.exists() else ""
    assert committed == live, (
        f"{COMMITTED.relative_to(REPO_ROOT)} is stale. From the repo root run:\n"
        f"    {REGENERATE}\n"
        f"then `npm run gen:api` in frontend/, and commit both files."
    )


def test_write_openapi_writes_sorted_json_with_trailing_newline(tmp_path):
    module = _load_export_openapi()
    out = tmp_path / "nested" / "openapi.json"
    module.write_openapi(out)
    text = out.read_text(encoding="utf-8")
    assert text.endswith("}\n") and not text.endswith("\n\n")
    schema = json.loads(text)
    assert text == json.dumps(schema, sort_keys=True, indent=2) + "\n"
    assert schema["info"]["title"] == "Worship Service Builder API"
    assert {"/health", "/health/ready", "/me", "/church", "/rubric"} <= schema["paths"].keys()
    # T3's error_responses(...): every route documents the one error body.
    assert "ErrorBody" in schema["components"]["schemas"]
    assert "HTTPValidationError" not in schema["components"]["schemas"]


def test_export_script_runs_from_the_repo_root(tmp_path):
    """The regenerate command in the failure message works as printed:
    `python backend/scripts/export_openapi.py` puts backend/scripts on
    sys.path[0], and the script must still import api."""
    out = tmp_path / "openapi.json"
    result = subprocess.run([sys.executable, "backend/scripts/export_openapi.py", "--out", str(out)],
                            cwd=REPO_ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"Wrote {out}\n"
    assert out.read_text(encoding="utf-8") == _load_export_openapi().render_openapi()
