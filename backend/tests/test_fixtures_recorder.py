"""The upstream fixtures and their recorder agree (S Testing "Fixtures"; F §5).

backend/scripts/record_fixtures.py writes backend/tests/fixtures/; these
tests only read what it wrote. They never run the recorder's network code.
"""
import importlib.util
import json
from datetime import date
from pathlib import Path

from tests.upstream_fixtures import FIXTURE_DATES, FIXTURES_DIR, load

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "backend" / "scripts" / "record_fixtures.py"
ALWAYS_SYNTHETIC = {"lectio/html_200", "lectio/error_500", "esv/success", "esv/empty"}


def _load_recorder():
    """backend/scripts is not a package: load the script by path, as test_openapi_contract does."""
    spec = importlib.util.spec_from_file_location("record_fixtures_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _meta_files() -> list[Path]:
    return sorted(FIXTURES_DIR.glob("*/*.meta.json"))


def test_recorder_dates_match_fixture_files():
    recorder = _load_recorder()
    recorder_dates = {date.fromisoformat(d) for d in recorder.LECTIO_DATES}
    lectio_files = {date.fromisoformat(p.name.removesuffix(".meta.json"))
                    for p in (FIXTURES_DIR / "lectio").glob("*.meta.json") if p.name[:1].isdigit()}
    assert len(FIXTURE_DATES) == 13
    assert recorder_dates == lectio_files == set(FIXTURE_DATES)
    assert set(recorder.VANDERBILT_KEEP["2025-26"]) == set(recorder.LECTIO_DATES)
    not_found = {d for d in FIXTURE_DATES if load("lectio", d).status == 404}
    assert not_found == {date.fromisoformat(d) for d in recorder.LECTIO_404_DATES}
    assert sorted(recorder.all_names()) == sorted(
        f"{p.parent.name}/{p.name.removesuffix('.meta.json')}" for p in _meta_files())


def test_every_fixture_has_status_and_content_type():
    metas = _meta_files()
    assert metas, "no fixtures: run backend/scripts/record_fixtures.py (see backend/tests/fixtures/README.md)"
    readme = (FIXTURES_DIR / "README.md").read_text(encoding="utf-8")
    for meta_path in metas:
        kind, name = meta_path.parent.name, meta_path.name.removesuffix(".meta.json")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        assert set(meta) == {"status", "content_type", "url", "recorded_at", "synthetic"}, meta_path
        assert isinstance(meta["status"], int) and 100 <= meta["status"] <= 599, meta_path
        assert isinstance(meta["content_type"], str) and meta["content_type"].strip(), meta_path
        assert meta["url"].startswith("https://"), meta_path
        assert isinstance(meta["synthetic"], bool), meta_path
        if f"{kind}/{name}" in ALWAYS_SYNTHETIC:
            assert meta["synthetic"] is True, meta_path
        recorded = load(kind, name)
        assert (recorded.status, recorded.content_type) == (meta["status"], meta["content_type"])
        assert recorded.body, meta_path
        assert f"`{kind}/{name}`" in readme, f"README.md does not list {kind}/{name}"
    bodies = {p for p in FIXTURES_DIR.glob("*/*") if not p.name.endswith(".meta.json")
              and not p.name.startswith(".") and p.parent.name != "shared"}
    stems = {(p.parent.name, p.name.split(".", 1)[0]) for p in bodies}
    assert len(stems) == len(bodies) == len(metas), "a body file without a sidecar, or two bodies for one"
