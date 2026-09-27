import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
CI_YML = ROOT / ".github" / "workflows" / "ci.yml"
# The backend-postgres service container: throwaway, local to the runner, never a real database.
THROWAWAY_URL = "postgresql://postgres:ci-throwaway@localhost:5432/postgres"
# Slice 1a (S Backend 1a, F §5.4): the Alembic cycle on the empty container, then
# ops-2's smoke on the fresh head schema (its user count assumes empty tables),
# then the @pytest.mark.postgres tests (pg_db empties the tables before each).
POSTGRES_JOB_RUNS = [
    "alembic upgrade head",
    "alembic check",
    "alembic downgrade base",
    "alembic upgrade head",
    "python backend/tests/pg_smoke.py",
    "python -m pytest -m postgres -q",
]


def _ci():
    import yaml

    return yaml.safe_load(CI_YML.read_text(encoding="utf-8"))


def test_ci_runs_backend_tests_and_frontend_checks_on_prs():
    text = CI_YML.read_text(encoding="utf-8")
    assert "pull_request" in text
    assert "python -m pytest" in text
    for script in ("npm run lint", "npm run typecheck", "npm test", "npm run build"):
        assert script in text


def test_ci_postgres_job_runs_the_alembic_cycle_then_postgres_tests():
    """Upgrade an empty database to head, check the models match, downgrade every
    revision, upgrade again, then the ops-2 smoke and the Postgres-only tests.
    The alembic steps run in backend/ (alembic.ini's home); the rest from the
    repo root. The Postgres major is checked only by test_ops_workflows (ops spec)."""
    steps = _ci()["jobs"]["backend-postgres"]["steps"]
    runs = [step.get("run", "") for step in steps]
    assert runs[-len(POSTGRES_JOB_RUNS):] == POSTGRES_JOB_RUNS     # in this order, last, nothing between
    assert runs.index("pip install -r requirements-dev.txt") < runs.index("alembic upgrade head")
    for step in steps:
        if step.get("run", "").startswith("alembic "):
            assert step.get("working-directory") == "backend", step
        elif step.get("run", "").startswith("python "):
            assert "working-directory" not in step, step
    assert (ROOT / "backend" / "alembic.ini").is_file()
    assert (ROOT / "backend" / "tests" / "pg_smoke.py").is_file()


def test_ci_postgres_job_points_both_urls_at_the_throwaway_container():
    import yaml

    from tests.pg_helpers import require_local_test_url

    ci = _ci()
    job = ci["jobs"]["backend-postgres"]
    assert job["env"]["DATABASE_URL"] == THROWAWAY_URL
    assert job["env"]["TEST_DATABASE_URL"] == THROWAWAY_URL
    assert require_local_test_url(job["env"]["TEST_DATABASE_URL"]) == THROWAWAY_URL
    service = job["services"]["postgres"]
    assert f":{service['env']['POSTGRES_PASSWORD']}@localhost:5432/" in THROWAWAY_URL
    assert service["ports"] == ["5432:5432"]
    assert "secrets." not in yaml.safe_dump(job)                   # the job never reads a real database
    assert "TEST_DATABASE_URL" not in (ci["jobs"]["backend"].get("env") or {})   # there they skip


def test_ci_postgres_service_image_is_a_bare_postgres_major():
    """test_ops_workflows.test_ci_postgres_service_matches_pg_major is the only check
    of the CI Postgres major, and it passes on an empty list. Pinning the one
    service to the bare postgres:<N> shape keeps that check reading a real image."""
    services = _ci()["jobs"]["backend-postgres"]["services"]
    assert list(services) == ["postgres"]
    assert re.fullmatch(r"postgres:\d+", services["postgres"]["image"]), services["postgres"]["image"]
