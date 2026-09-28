"""Slice 1a docs: the Alembic production runbook in backend/migrations/README.md,
the ops-runbook health-check lines, the README's Alembic notes and the manual
"Slice 1" checks (slice 1 spec → Production runbook, Local dev, Manual checks
item 1; F §3.3, §5.5).

Text is compared whitespace-collapsed (`_flat`), so rewrapping a paragraph
never breaks a test; fenced output blocks are compared exactly.
"""
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]   # repo root
MIGRATIONS_README = ROOT / "backend" / "migrations" / "README.md"
RUNBOOK = ROOT / "docs" / "ops-runbook.md"
README = ROOT / "README.md"
MANUAL_VERIFICATION = ROOT / "docs" / "manual-verification.md"
BACKUP_YML = ROOT / ".github" / "workflows" / "backup.yml"

RUNBOOK_STEPS = (
    "### Step 0: RLS precondition",
    "### Step 1: Backup",
    "### Step 2: Server version",
    "### Step 3: Nothing is stamped yet",
    "### Step 4: Stamp the baseline",
    "### Step 5: Read the SQL the upgrade will run",
    "### Step 6: Drift check",
    "### Step 7: Railway settings, immediately before merging",
    "### Step 8: Merge and watch the deploy",
    "### Step 9: Confirm head",
    "### Step 10: Streamlit smoke check",
)
OWNER_COMMANDS = (
    "../.venv/bin/pip install -r ../requirements-dev.txt",
    "IFS= read -rs DATABASE_URL && export DATABASE_URL",
    "../.venv/bin/alembic current",
    "../.venv/bin/alembic stamp 0001_baseline",
    "../.venv/bin/alembic upgrade 0001_baseline:head --sql > upgrade.sql",
    "../.venv/bin/python scripts/schema_drift.py",
    "../.venv/bin/alembic check",
    "../.venv/bin/alembic upgrade head",
    "unset DATABASE_URL",
)
# schema_drift.py's stdout on production right after stamping (sorted lines;
# db.schema_check.format_diff). "add_index ix_hymns_church_hymnal" follows only
# if production lacks that index.
DRIFT_AT_BASELINE = (
    "revision: 0001_baseline head: 0004_invites_reusable state: behind\n"
    "add_column invites.accepted_by\n"
    "add_column invites.reusable\n"
    "add_fk fk_invites_accepted_by_users\n"
)
DRIFT_AT_HEAD = "revision: 0004_invites_reusable head: 0004_invites_reusable state: current\n"
LOCKDOWN_REFUSAL = (
    "0003_lockdown: role % has no BYPASSRLS and does not own: %. Enabling RLS would hide "
    'their rows from the app. See migrations/README.md "RLS precondition".'
)


def _read(path):
    return path.read_text(encoding="utf-8")


def _flat(text):
    """The text with every run of whitespace collapsed to one space."""
    return " ".join(text.split())


def _section(text, heading):
    """The body of `heading` up to the next heading of the same level."""
    level = heading.split(" ", 1)[0]
    return text.split(f"\n{heading}\n", 1)[1].split(f"\n{level} ", 1)[0]


def test_migrations_readme_has_the_production_runbook_steps():
    text = _read(MIGRATIONS_README)
    runbook = _section(text, "## Production runbook (slice 1a)")
    assert re.findall(r"^### Step \d+: .+$", runbook, re.MULTILINE) == list(RUNBOOK_STEPS)
    for command in OWNER_COMMANDS:
        assert command in runbook, command
    assert DRIFT_AT_BASELINE in runbook
    assert DRIFT_AT_HEAD in runbook
    flat = _flat(runbook)
    for needle in (
        "add_index ix_hymns_church_hymnal",
        "`/backend/railway.toml`",
        "Healthcheck Path",
        "`/health/ready`",
        '"reason": "schema_behind"',
        "No new upgrade operations detected.",
        "0004_invites_reusable (head)",
        "Target database is not up to date.",
        "BEGIN;",
        "SET LOCAL lock_timeout = '5s';",
        "SET LOCAL statement_timeout = '60s';",
        "COMMIT;",
        "gh workflow run db-backup --ref main",
        "https://liturgy-frozen.streamlit.app/",
        "Create invite",
        "relation",
        "already exists",
        '"Alembic stamping record (slice 1a)", never a URL or a password.',
    ):
        assert needle in flat, needle
    assert "liturgy-next" not in text


def test_migrations_readme_records_the_rls_precondition_and_pg_major():
    text = _read(MIGRATIONS_README)
    section = _flat(_section(text, "## RLS precondition"))
    for needle in (
        "select tablename, tableowner from pg_tables where schemaname = 'public' order by 1;",
        "select current_user, rolbypassrls from pg_roles where rolname = current_user;",
        "owner of every `public` table: `postgres`",
        "`current_user`, `rolbypassrls`: `postgres`, `true`",
        "2026-09-25",
        "ALTER TABLE public.<t> OWNER TO <app role>;",
        "CREATE POLICY app_all ON public.<t> TO <app role> USING (true) WITH CHECK (true);",
        LOCKDOWN_REFUSAL,
    ):
        assert needle in section, needle
    reverting = _flat(_section(text, "## Reverting"))
    for needle in ("Never downgrade production below `0003_lockdown`",
                   "../.venv/bin/alembic downgrade 0003_lockdown",
                   "Config-as-code"):
        assert needle in reverting, needle
    majors = re.findall(r"^Server major recorded for slice 1a: (\d+) ", text, re.MULTILINE)
    pg_major = str(yaml.safe_load(_read(BACKUP_YML))["jobs"]["dump"]["env"]["PG_MAJOR"])
    assert majors == [pg_major]


def test_ops_runbook_health_check_lines_name_health_ready():
    text = _read(RUNBOOK)
    environments = _flat(_section(text, "## Environments and variables"))
    for needle in ("`/backend/railway.toml`", "Healthcheck Path", "`/health/ready`",
                   "alembic upgrade head", "backend/migrations/README.md"):
        assert needle in environments, needle
    keep_alive = _flat(_section(text, "## Keep-alive"))
    for needle in ("deploy health check", "`schema_behind`", "backend/migrations/README.md"):
        assert needle in keep_alive, needle
    flat = _flat(text)
    for stale in ("(slice 1 moves it to `/health/ready`)",
                  "slice 1 moves the deploy check to `/health/ready`"):
        assert stale not in flat, stale
    # Dated records are history: slice 1a edits none of them in place.
    for record in (
        "Checked against Railway → the API service → Variables (names only) and "
        "Settings → Deploy → Healthcheck Path:",
        "Healthcheck Path `/health` (already set).",
        "-- Defense in depth; slice 1's 0003_lockdown repeats this idempotently.",
        "slice 1 decides between transferring table ownership and adding policies",
    ):
        assert record in flat, record


def test_manual_verification_has_the_slice_1_section():
    text = _read(MANUAL_VERIFICATION)
    assert re.findall(r"^## .+$", text, re.MULTILINE)[-2:] == ["## Ops slice", "## Slice 1"]
    section = _flat(_section(text, "## Slice 1"))
    for needle in (
        "https://worship-service-builder.vercel.app",
        "375 px",
        "step 0",
        "`/backend/railway.toml`",
        "pre-deploy",
        "alembic upgrade head",
        "`/health/ready`",
        "0004_invites_reusable (head)",
        "No new upgrade operations detected.",
        "`/welcome`",
        "No church yet",
        "not a 404",
        "Log out",
        "https://liturgy-frozen.streamlit.app",
        "Create invite",
    ):
        assert needle in section, needle
    assert "liturgy-next" not in section
    assert section.count("- [ ] ") == 3
    assert "- [x]" not in section


def test_readme_documents_alembic_for_local_dev():
    text = _read(README)
    database = _flat(_section(text, "## Database"))
    for needle in (
        "../.venv/bin/alembic upgrade head",
        "../.venv/bin/alembic stamp 0001_baseline && ../.venv/bin/alembic upgrade head",
        "sqlite:///../data/app.db",
        "TEST_DATABASE_URL",
        "pytest -m postgres",
        "backend/migrations/README.md",
        "backend/railway.toml",
    ):
        assert needle in database, needle
    deploying = _flat(text.split("**Deploying:**", 1)[1].split("\n## ", 1)[0])
    for needle in ("`/backend/railway.toml`", "`/health/ready`", "alembic upgrade head"):
        assert needle in deploying, needle
    assert "health check `/health`)" not in deploying
