"""Ops workflows and their companion files (ops slice spec → Testing).

Built in ops-1 (backups, runbook, age recipients). ops-3 adds the keepalive.yml
and keep-awake.yml checks and deletes test_keepalive.py.
"""
import pathlib
import re
import subprocess

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]   # repo root
BACKUP_YML = ROOT / ".github" / "workflows" / "backup.yml"
CI_YML = ROOT / ".github" / "workflows" / "ci.yml"
NORMALIZE_SCRIPT = ".github/backup/normalize-pg-url.sh"   # relative: run exactly as backup.yml runs it

AGE_RECIPIENT = re.compile(r"^age1[02-9ac-hj-np-z]{58}$")
POSTGRES_IMAGE = re.compile(r"\bpostgres:(\d+)")


def _read(path):
    return path.read_text(encoding="utf-8")


def _pg_major():
    """PG_MAJOR from backup.yml, parsed as YAML (jobs.dump.env.PG_MAJOR)."""
    return str(yaml.safe_load(_read(BACKUP_YML))["jobs"]["dump"]["env"]["PG_MAJOR"])


# --- backup.yml -------------------------------------------------------------

BACKUP_MUST_CONTAIN = (
    "schedule:",
    "workflow_dispatch",
    "contents: read",
    "secrets.BACKUP_DATABASE_URL",
    "pipefail",
    "bash .github/backup/normalize-pg-url.sh",
    "--recipients-file .github/backup/age-recipients.txt",
    "postgresql-client-${PG_MAJOR}",
    "--schema=public",
    "--format=custom",
    ".dump.age",
    "retention-days: 30",
    # Exact copy from the ops spec's "Exact server messages" table.
    "::error::BACKUP_DATABASE_URL secret is not set",
    "::error::.github/backup/age-recipients.txt has no age recipient",
    "::error::Postgres server major is $major but PG_MAJOR is $PG_MAJOR; update PG_MAJOR in backup.yml",
)
BACKUP_MUST_NOT_CONTAIN = ("secrets.DATABASE_URL", ".sql.gz", ' -f "backup', "+psycopg2")


def test_backup_workflow_dumps_encrypts_and_uploads():
    text = _read(BACKUP_YML)
    assert [needle for needle in BACKUP_MUST_CONTAIN if needle not in text] == []


def test_backup_workflow_has_no_plaintext_dump_or_old_secret():
    text = _read(BACKUP_YML)
    assert [needle for needle in BACKUP_MUST_NOT_CONTAIN if needle in text] == []


def test_backup_workflow_checks_recipients_with_the_pattern_the_tests_use():
    assert AGE_RECIPIENT.pattern in _read(BACKUP_YML)


def test_backup_workflow_pins_pg_major_in_the_job_env():
    assert re.fullmatch(r"\d+", _pg_major())


# --- normalize-pg-url.sh ----------------------------------------------------

@pytest.mark.parametrize("raw, expected", [
    ("postgresql+psycopg2://u:p@h:5432/db", "postgresql://u:p@h:5432/db"),
    ("postgres://u:p@h/db", "postgresql://u:p@h/db"),
    ("postgresql://u:p@h/db", "postgresql://u:p@h/db"),
])
def test_normalize_pg_url(raw, expected):
    result = subprocess.run(
        ["bash", NORMALIZE_SCRIPT], input=raw, capture_output=True, text=True, cwd=ROOT,
    )
    assert result.returncode == 0
    assert result.stdout.rstrip("\n") == expected
    assert result.stderr == ""


# --- CI Postgres major (slice 1 adds the service container) ----------------

def _postgres_image_majors(text):
    return POSTGRES_IMAGE.findall(text)


def test_postgres_image_parser_finds_service_container_majors():
    sample = 'services:\n  db:\n    image: postgres:16-alpine\n  other:\n    image: "postgres:17"\n'
    assert _postgres_image_majors(sample) == ["16", "17"]


def test_ci_postgres_image_matches_pg_major():
    # Inert until slice 1 declares a postgres:<N> service container in ci.yml.
    # This is the only check of the CI Postgres major (ops spec, slice 1 row).
    majors = _postgres_image_majors(_read(CI_YML))
    assert [m for m in majors if m != _pg_major()] == []
