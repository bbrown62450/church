import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_ci_runs_backend_tests_and_frontend_checks_on_prs():
    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "pull_request" in text
    assert "python -m pytest" in text
    for script in ("npm run lint", "npm run typecheck", "npm test", "npm run build"):
        assert script in text


def test_ci_runs_the_postgres_smoke_on_a_throwaway_postgres_17():
    """ops-2: ON CONFLICT (email), the 3 + 3 pool and the Streamlit multi-tab race
    only exist on Postgres, so CI runs backend/tests/pg_smoke.py against a
    postgres:17 service container (the major matches PG_MAJOR; see
    test_ops_workflows.test_ci_postgres_service_matches_pg_major)."""
    import yaml

    ci = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))
    job = ci["jobs"]["backend-postgres"]
    assert job["services"]["postgres"]["image"] == "postgres:17"
    url = job["env"]["DATABASE_URL"]
    assert url.startswith("postgresql://") and "@localhost:5432/" in url   # never a real database
    runs = [step.get("run", "") for step in job["steps"]]
    assert "python backend/tests/pg_smoke.py" in runs
    assert (ROOT / "backend" / "tests" / "pg_smoke.py").is_file()
