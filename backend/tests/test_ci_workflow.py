import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_ci_runs_backend_tests_and_frontend_checks_on_prs():
    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "pull_request" in text
    assert "python -m pytest" in text
    for script in ("npm run lint", "npm run typecheck", "npm test", "npm run build"):
        assert script in text
