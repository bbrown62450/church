"""Slice 1 docs: the Alembic production runbook in backend/migrations/README.md,
the ops-runbook health-check lines, the README's Alembic notes, the manual
"Slice 1" checks (slice 1 spec → Production runbook, Local dev, Manual checks
items 1–11; F §3.3, §5.5) and slice 1b's foundations amendments (F §4.3
preview then Join, approved 2026-09-26, and the six docs-only fixes of the
slice 1b plan's owner answer 3).

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
SPECS = ROOT / "docs" / "superpowers" / "specs"
FOUNDATIONS = SPECS / "2026-09-25-migration-foundations-design.md"
SLICE_1_SPEC = SPECS / "2026-09-25-slice-1-onboarding-design.md"
JOIN_TAP_APPROVAL = (
    "Preview then Join approved by the owner on 2026-09-26 (amendment to decision 6)"
)

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
                   "Pre-deploy Command"):
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
    # Slices 2c and 3b append "## Slice 2" and "## Slice 3" after this section (their specs, Manual checks).
    headings = re.findall(r"^## .+$", text, re.MULTILINE)[-4:]
    assert headings == ["## Ops slice", "## Slice 1", "## Slice 2", "## Slice 3"]
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
        # Slice 1b: manual checks 2-11 (plan owner answers 2 and 7).
        "Slice 1b record",
        "claude/slice-1b-records",
        "Settings → Invites",
        "5 churches in 24 hours",
        "Join or create a church…",
        "Joined 1b Invite Test.",
        "This invite has already been used.",
        "Church name is required.",
        "Use a different Google account",
        "select_account",
        "You no longer have access to 1b Invite Test.",
        "This invite has been revoked.",
    ):
        assert needle in section, needle
    assert "liturgy-next" not in section
    assert section.count("- [ ] ") == 13
    assert section.count("- [ ] (after 1a) ") == 3
    assert section.count("- [ ] (after 1b) ") == 10
    assert "- [x]" not in section


def test_foundations_records_the_join_tap_amendment():
    # Slice 1b plan, owner answers 1 (behavior change 4 approved on 2026-09-26)
    # and 3 (six docs-only F fixes); the slice 1 spec closes its open items.
    text = _read(FOUNDATIONS)
    flat = _flat(text)
    d14 = _flat(next(line for line in text.splitlines() if line.startswith("| D14 |")))
    amendments = _section(text, "## Amendments from slice specs")
    rows_43 = [_flat(line) for line in amendments.splitlines() if line.startswith("| §4.3 |")]
    sign_in = _flat(_section(text, "### 4.3 Sign-in continuity"))
    assert JOIN_TAP_APPROVAL in d14
    assert len(rows_43) == 1 and JOIN_TAP_APPROVAL in rows_43[0]
    assert JOIN_TAP_APPROVAL in sign_in
    for gone in (
        "owner sign-off",
        "autoAccept",
        "Sign in with Google to join",
        "The root reads, clears and follows",
        "reason_code",
        "IntegrityError on the membership insert counts as success",
        "set to `/backend/railway.toml` by hand",
        "ping only `liturgy.streamlit.app`",
    ):
        assert gone not in flat, gone
    assert "Sign in with Google to see and accept your invite to Worship Service Builder." in sign_in
    assert "The `(signed-in)` layout reads the stored path, clears it, then follows it" in sign_in
    assert "The key scope has no church." in _flat(_section(text, "### 1.6 Idempotency"))
    assert "Config as Code is closed to this service" in _flat(
        _section(text, "### 3.3 How migrations run"))
    assert "https://liturgy-frozen.streamlit.app/" in _section(text, "### 6.1 The freeze (ops slice)")
    risks = _section(text, "### 7.4 Inventory §4 cross-cutting risks").splitlines()
    lookups = next(line for line in risks if line.startswith("| Global lookups exposed"))
    accept = next(line for line in risks if line.startswith("| Concurrent `accept_invite`"))
    assert "`already_member`" in lookups
    assert "`claim`" in accept and "`insert_ignore`" in accept
    slice_1 = _read(SLICE_1_SPEC)
    for gone in ("autoAccept", "behavior change 4 fallback", "If the owner declines", "Open, owner"):
        assert gone not in slice_1, gone
    assert "Resolved (owner, 2026-09-26)" in slice_1


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
