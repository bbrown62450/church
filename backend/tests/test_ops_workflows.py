"""Ops workflows and their companion files (ops slice spec → Testing).

Built in ops-1 (backups, runbook, age recipients). ops-3 adds the keepalive.yml
and keep-awake.yml checks and deletes test_keepalive.py.

backup.yml is checked as parsed YAML (PyYAML reads the bare key `on` as True),
and .github/backup/pg_env.py, which turns BACKUP_DATABASE_URL into libpq PG*
variables, is checked against SQLAlchemy's own URL parser and a real bash.
"""
import importlib.util
import os
import pathlib
import re
import subprocess
import sys

import pytest
import yaml
from sqlalchemy.engine import make_url

ROOT = pathlib.Path(__file__).resolve().parents[2]   # repo root
BACKUP_YML = ROOT / ".github" / "workflows" / "backup.yml"
CI_YML = ROOT / ".github" / "workflows" / "ci.yml"
PG_ENV_SCRIPT = ".github/backup/pg_env.py"   # relative: run exactly as backup.yml runs it
# The Supabase server major (17.6 on 2026-09-25). If Supabase upgrades, plan Task 11,
# Step 3 changes it together with PG_MAJOR in backup.yml and the runbook's major line.
SERVER_MAJOR = "17"

AGE_RECIPIENT = re.compile(r"^age1[02-9ac-hj-np-z]{58}$")
POSTGRES_IMAGE = re.compile(r"(?:\S*/)?postgres:(\d+)\S*")   # a whole image reference

DUMP_STEP = "Dump, compress and encrypt (plaintext never touches disk)"
SECRET_REF = "${{ secrets.BACKUP_DATABASE_URL }}"


def _read(path):
    return path.read_text(encoding="utf-8")


def _workflow(path=BACKUP_YML):
    return yaml.safe_load(_read(path))


def _pg_major():
    """PG_MAJOR from backup.yml, parsed as YAML (jobs.dump.env.PG_MAJOR)."""
    return str(_workflow()["jobs"]["dump"]["env"]["PG_MAJOR"])


def _dump_job():
    return _workflow()["jobs"]["dump"]


def _step(name):
    [step] = [s for s in _dump_job()["steps"] if s.get("name") == name]
    return step


def _action(name):
    [step] = [s for s in _dump_job()["steps"] if s.get("uses", "").split("@")[0] == name]
    return step


def _commands(run):
    """A run block's commands: continuation lines joined, blank and comment lines dropped."""
    joined = re.sub(r"\\\n\s*", " ", run)
    return [line.strip() for line in joined.splitlines()
            if line.strip() and not line.strip().startswith("#")]


def _strings(node, path=()):
    """Every string in a parsed YAML tree, with its path of keys and indexes."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _strings(value, path + (key,))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _strings(value, path + (index,))
    elif isinstance(node, str):
        yield path, node


# --- backup.yml: triggers, job, secret scope --------------------------------

def test_backup_workflow_triggers_and_permissions():
    workflow = _workflow()
    triggers = workflow[True]   # the bare key `on`, as PyYAML reads it
    assert set(triggers) == {"schedule", "workflow_dispatch"}
    assert triggers["schedule"] == [{"cron": "37 8 * * *"}]
    assert workflow["permissions"] == {"contents": "read"}
    assert "env" not in workflow
    assert list(workflow["jobs"]) == ["dump"]


def test_backup_job_runner_timeout_environment_and_pg_major():
    job = _dump_job()
    assert job["runs-on"] == "ubuntu-24.04"
    assert job["timeout-minutes"] == 20
    # The owner stores BACKUP_DATABASE_URL in the `backup` environment, whose
    # deployment-branch policy admits only main (plan Task 11).
    assert job["environment"] == "backup"
    assert job["env"] == {"PG_MAJOR": SERVER_MAJOR}   # a quoted string, never the secret
    assert "permissions" not in job


def test_backup_secret_is_only_in_the_steps_that_need_it():
    workflow = _workflow()
    secret_paths = [path for path, value in _strings(workflow) if "secrets." in value]
    steps = workflow["jobs"]["dump"]["steps"]
    assert all(path[:3] == ("jobs", "dump", "steps") and path[4:] == ("env", "BACKUP_DATABASE_URL")
               for path in secret_paths), secret_paths
    assert sorted(steps[path[3]]["name"] for path in secret_paths) == ["Check prerequisites", DUMP_STEP]
    assert all(steps[path[3]]["env"]["BACKUP_DATABASE_URL"] == SECRET_REF for path in secret_paths)
    # The prerequisites step only tests that the secret is set; it never prints it.
    uses = [c for c in _commands(_step("Check prerequisites")["run"]) if "BACKUP_DATABASE_URL" in c]
    assert [c.startswith('test -n "$BACKUP_DATABASE_URL"') for c in uses] == [True]


def test_backup_actions_are_pinned_to_commit_shas():
    steps = [s for s in _dump_job()["steps"] if "uses" in s]
    assert [s["uses"].split("@")[0] for s in steps] == ["actions/checkout", "actions/upload-artifact"]
    assert [s["uses"] for s in steps if not re.fullmatch(r"actions/[a-z-]+@[0-9a-f]{40}", s["uses"])] == []
    # Each pin carries the release it came from, e.g. `@<sha> # v4.4.0`.
    commented = re.findall(r"^\s*- uses: (\S+) # v\d+\.\d+\.\d+$", _read(BACKUP_YML), re.MULTILINE)
    assert commented == [s["uses"] for s in steps]
    assert _action("actions/checkout")["with"] == {"persist-credentials": False}


def test_backup_artifact_settings():
    assert _action("actions/upload-artifact")["with"] == {
        "name": "db-backup",
        "path": "backup-*.dump.age",
        "retention-days": 30,
        "if-no-files-found": "error",
        "compression-level": 0,
    }


# --- backup.yml: the dump step ------------------------------------------------

def test_dump_step_masks_the_url_parts_before_anything_else():
    commands = _commands(_step(DUMP_STEP)["run"])
    assert commands[:2] == [
        "set -euo pipefail",
        'python3 .github/backup/pg_env.py --mask <<<"$BACKUP_DATABASE_URL"',
    ]

    def first(needle):
        return next(i for i, c in enumerate(commands) if needle in c)

    assert first("--mask") < first("--exports") < first("eval ") < first("/psql") < first("/pg_dump")


#  Matches $BACKUP_DATABASE_URL, "$BACKUP_DATABASE_URL" and ${BACKUP_DATABASE_URL} alike, so a
#  braced reference (e.g. `psql "${BACKUP_DATABASE_URL}" ...`) cannot slip past this test the
#  way a literal '"$BACKUP_DATABASE_URL"' substring check would.
URL_TOKEN = re.compile(r"\bBACKUP_DATABASE_URL\b")
# A word-boundary match, not a "/psql"/"/pg_dump" substring check: it also catches a bare
# `psql ...` or `pg_dump ...` invocation with no "$bin/" prefix.
COMMAND_WORD = re.compile(r"\b(?:psql|pg_dump)\b")
POSTGRES_URL_SCHEME = re.compile(r"postgres(?:ql)?://")


def test_dump_step_gives_psql_and_pg_dump_no_url():
    step = _step(DUMP_STEP)
    commands = _commands(step["run"])
    assert step["env"] == {"BACKUP_DATABASE_URL": SECRET_REF, "PGSSLMODE": "require"}
    assert "PGSSLMODE" not in step["run"]   # nothing weakens it
    # The URL reaches only pg_env.py, on stdin, and is unset right after: libpq gets PG*
    # variables. Exactly these three lines may name the token, in any shell form.
    assert [c for c in commands if URL_TOKEN.search(c)] == [
        'python3 .github/backup/pg_env.py --mask <<<"$BACKUP_DATABASE_URL"',
        'pg_env=$(python3 .github/backup/pg_env.py --exports <<<"$BACKUP_DATABASE_URL")',
        "unset pg_env BACKUP_DATABASE_URL",
    ]
    assert 'eval "$pg_env"' in commands
    assert 'bin="/usr/lib/postgresql/${PG_MAJOR}/bin"' in commands
    command_lines = [c for c in commands if COMMAND_WORD.search(c)]
    [psql] = [c for c in command_lines if "psql" in c]
    [pg_dump] = [c for c in command_lines if "pg_dump" in c]
    assert psql == """server=$("$bin/psql" -X -Atc 'show server_version_num')"""
    assert pg_dump.startswith('"$bin/pg_dump" --schema=public ')
    # No psql/pg_dump command line, in any form, ever sees the secret token or a raw URL.
    assert len(command_lines) == 2
    for command in command_lines:
        assert not URL_TOKEN.search(command)
        assert not POSTGRES_URL_SCHEME.search(command)
        assert "url" not in command.lower()


def test_dump_step_has_no_shell_tracing():
    # Tracing would echo every expanded command, including the masked-but-still-live
    # $BACKUP_DATABASE_URL, to the public run log. The only `set` command allowed is the
    # one at the top of the step; no `set -x`/`-v`, `set -o xtrace`/`verbose` variant.
    step = _step(DUMP_STEP)
    commands = _commands(step["run"])
    set_commands = [c for c in commands if re.match(r"^set\b", c)]
    assert set_commands == ["set -euo pipefail"]
    # Nothing anywhere in the workflow enables tracing another way (e.g. an env-var toggle).
    text = _read(BACKUP_YML)
    for forbidden in ("xtrace", "BASH_XTRACEFD", "SHELLOPTS"):
        assert forbidden not in text, forbidden


def test_dump_step_streams_pg_dump_into_age_with_no_plaintext_file():
    run = _step(DUMP_STEP)["run"]
    [pg_dump] = [c for c in _commands(run) if "/pg_dump" in c]
    producer, pipe, consumer = pg_dump.partition(" | ")
    assert pipe
    assert producer.split() == ['"$bin/pg_dump"', "--schema=public", "--no-owner", "--no-privileges",
                                "--format=custom"]
    assert consumer == ('age --encrypt --recipients-file .github/backup/age-recipients.txt '
                        '--output "backup-$ts.dump.age"')
    assert ">" not in run   # no redirection anywhere in the step: age --output writes the only file


BACKUP_MUST_CONTAIN = (
    "postgresql-client-${PG_MAJOR}",
    # Exact copy from the ops spec's "Exact server messages" table.
    "::error::BACKUP_DATABASE_URL secret is not set",
    "::error::.github/backup/age-recipients.txt has no age recipient",
    "::error::Postgres server major is $major but PG_MAJOR is $PG_MAJOR; update PG_MAJOR in backup.yml",
    "::error::Encrypted backup is unexpectedly small",
)
# "::add-mask::$" — a shell-expanded mask is neither escaped nor split into parts.
BACKUP_MUST_NOT_CONTAIN = ("secrets.DATABASE_URL", ".sql.gz", ' -f "backup', "+psycopg2",
                           "normalize-pg-url", "::add-mask::$")


def test_backup_workflow_contains_the_exact_messages():
    text = _read(BACKUP_YML)
    assert [needle for needle in BACKUP_MUST_CONTAIN if needle not in text] == []


def test_backup_workflow_has_no_plaintext_dump_old_secret_or_shell_mask():
    text = _read(BACKUP_YML)
    assert [needle for needle in BACKUP_MUST_NOT_CONTAIN if needle in text] == []


def test_backup_workflow_checks_recipients_with_the_pattern_the_tests_use():
    assert AGE_RECIPIENT.pattern in _read(BACKUP_YML)


# --- .github/backup/pg_env.py -------------------------------------------------

SUPABASE_USER = "postgres.abcdefghijklmnopqrst"
SUPABASE_HOST = "aws-0-us-east-1.pooler.supabase.com"

# (password as written in the URL, the password SQLAlchemy — and so the app — uses)
TRICKY_PASSWORDS = [
    ("SeCrEt/PW", "SeCrEt/PW"),              # libpq: invalid integer value "SeCrEt" for ... "port"
    ("SeCrEt%zzPW", "SeCrEt%zzPW"),          # libpq: invalid percent-encoded token: "SeCrEt%zzPW"
    ("50%25off", "50%off"),                  # encoded percent
    ("me%40home", "me@home"),                # encoded @
    ("a:b:c", "a:b:c"),                      # colons
    ("it's\"q", "it's\"q"),                  # both quotes
    ("x$(id)`id`;z", "x$(id)`id`;z"),        # shell syntax
    ("line%0Abreak%0D", "line\nbreak\r"),    # newline and CR: workflow commands must escape them
    ("p#q?r", "p#q?r"),                      # characters urllib.parse.urlsplit would cut at
]


@pytest.fixture(scope="module")
def pg_env():
    spec = importlib.util.spec_from_file_location("pg_env", ROOT / PG_ENV_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _url(raw_password, scheme="postgresql+psycopg2"):
    return f"{scheme}://{SUPABASE_USER}:{raw_password}@{SUPABASE_HOST}:5432/postgres"


def _run_pg_env(args, url):
    # A trailing newline, as bash's <<< adds. Bytes, so nothing is translated.
    return subprocess.run([sys.executable, PG_ENV_SCRIPT, *args], input=(url + "\n").encode(),
                          capture_output=True, cwd=ROOT)


def _command_escape(value):
    """Workflow-command data escaping (@actions/core escapeData): the runner undoes it."""
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


@pytest.mark.parametrize("raw, password", TRICKY_PASSWORDS)
def test_pg_env_decodes_the_url_like_sqlalchemy(pg_env, raw, password):
    url = _url(raw)
    parts = pg_env.parse(url)
    assert parts == {"host": SUPABASE_HOST, "port": "5432", "user": SUPABASE_USER,
                     "password": password, "dbname": "postgres"}
    app = make_url(url)
    assert (app.username, app.password, app.host, app.port, app.database) == (
        parts["user"], parts["password"], parts["host"], int(parts["port"]), parts["dbname"])


@pytest.mark.parametrize("raw, password", TRICKY_PASSWORDS)
def test_pg_env_mask_prints_an_escaped_mask_for_each_part(raw, password):
    url = _url(raw)
    result = _run_pg_env(["--mask"], url)
    assert (result.returncode, result.stderr) == (0, b"")
    lines = result.stdout.decode().split("\n")
    assert lines.pop() == ""
    assert [line for line in lines if not line.startswith("::add-mask::")] == []
    for value in (password, SUPABASE_USER, SUPABASE_HOST, url):
        assert "::add-mask::" + _command_escape(value) in lines, value


def test_pg_env_mask_escapes_percent_cr_and_newline_for_the_runner():
    url = "postgresql://u:50%25off%0Anext%0D@db.example.com/postgres"
    lines = _run_pg_env(["--mask"], url).stdout.decode().split("\n")
    assert "::add-mask::50%25off%0Anext%0D" in lines   # the password, 50%off<LF>next<CR>
    assert "::add-mask::postgresql://u:50%2525off%250Anext%250D@db.example.com/postgres" in lines


@pytest.mark.parametrize("raw, password", TRICKY_PASSWORDS)
def test_pg_env_exports_survive_eval_in_bash(raw, password):
    script = ('eval "$("$PYTHON" .github/backup/pg_env.py --exports <<<"$BACKUP_DATABASE_URL")"; '
              'printf "%s\\0" "$PGHOST" "$PGPORT" "$PGUSER" "$PGPASSWORD" "$PGDATABASE"')
    env = {"PATH": os.environ["PATH"], "PYTHON": sys.executable, "BACKUP_DATABASE_URL": _url(raw)}
    result = subprocess.run(["bash", "-c", script], env=env, capture_output=True, cwd=ROOT)
    assert (result.returncode, result.stderr) == (0, b"")
    assert result.stdout.split(b"\0")[:-1] == [
        value.encode() for value in (SUPABASE_HOST, "5432", SUPABASE_USER, password, "postgres")]


def test_pg_env_exports_only_the_five_libpq_variables():
    lines = _run_pg_env(["--exports"], _url("pw")).stdout.decode().splitlines()
    assert [line.split("=", 1)[0] for line in lines] == [
        "export PGHOST", "export PGPORT", "export PGUSER", "export PGPASSWORD", "export PGDATABASE"]


@pytest.mark.parametrize("scheme", ["postgresql+psycopg2", "postgresql+psycopg", "postgresql", "postgres"])
def test_pg_env_accepts_the_scheme_forms(pg_env, scheme):
    assert pg_env.parse(f"{scheme}://u:pw@db.example.com/postgres") == {
        "host": "db.example.com", "port": "5432", "user": "u", "password": "pw", "dbname": "postgres"}


@pytest.mark.parametrize("url", [
    "mysql://u:SeCrEtPW@db.example.com/postgres",                 # not Postgres
    "postgresql://u:SeCrEt%zzPW@db.example.com:SeCrEt/postgres",  # port is not a number
    "postgresql://u:SeCrEtPW@db.example.com:99999/postgres",      # port out of range
    "postgresql://u:SeCrEtPW@/postgres",                          # no host
    "postgresql://u:SeCrEtPW@db.example.com",                     # no database
    "postgresql://SeCrEtUser@db.example.com/postgres",            # no password
    "postgresql://u:SeCrEt%00PW@db.example.com/postgres",         # NUL byte
    "SeCrEtPW",                                                   # not a URL
])
def test_pg_env_rejects_a_malformed_url_without_echoing_it(pg_env, url):
    for mode in ("--mask", "--exports"):
        result = _run_pg_env([mode], url)
        assert result.returncode != 0
        assert result.stdout == b""
        assert result.stderr.decode() == pg_env.ERROR + "\n"
        assert b"SeCrEt" not in result.stderr


@pytest.mark.parametrize("args", [[], ["--bogus"], ["--mask", "--exports"]])
def test_pg_env_rejects_bad_arguments(args):
    result = _run_pg_env(args, _url("SeCrEtPW"))
    assert result.returncode != 0
    assert result.stdout == b""
    assert b"SeCrEt" not in result.stderr


# --- CI Postgres major (slice 1 adds the service container) ----------------

def _postgres_service_majors(workflow):
    """Majors of the postgres:<N> images in jobs.*.services.*.image of a parsed workflow."""
    majors = []
    for job in (workflow.get("jobs") or {}).values():
        for service in ((job or {}).get("services") or {}).values():
            image = service.get("image", "") if isinstance(service, dict) else str(service)
            match = POSTGRES_IMAGE.fullmatch(image)
            if match:
                majors.append(match.group(1))
    return majors


def test_postgres_service_parser_reads_service_images():
    sample = yaml.safe_load(
        "jobs:\n"
        "  a:\n"
        "    services:\n"
        "      db: {image: 'postgres:16-alpine'}\n"
        "      cache: {image: 'redis:7'}\n"
        "  b:\n"
        "    services:\n"
        "      db: {image: 'docker.io/library/postgres:17'}\n"
        "  c:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps: [{run: 'docker run postgres:15'}]\n"   # not a service: ignored
    )
    assert _postgres_service_majors(sample) == ["16", "17"]


def test_ci_postgres_service_matches_pg_major():
    # Inert until slice 1 declares a postgres:<N> service container in ci.yml.
    # This is the only check of the CI Postgres major (ops spec, slice 1 row).
    majors = _postgres_service_majors(_workflow(CI_YML))
    assert [m for m in majors if m != _pg_major()] == []


# --- docs/ops-runbook.md and README ------------------------------------------

RUNBOOK = ROOT / "docs" / "ops-runbook.md"
README = ROOT / "README.md"
PG_MAJOR_LINE = re.compile(r"^- Postgres server major: (\d+)\s*$", re.MULTILINE)
OPS1_RUNBOOK_SECTIONS = (
    "## Supabase lockdown record",
    "## Backups",
    "## Streamlit freeze",
    "## Platform limits",
    "## Incident response",
)
TRIAGE_ROWS = ("D5", "A7", "E6", "E4", "D6", "F6", "F7", "F10", "D3", "G7", "F4", "B2", "C1", "G5")


def test_runbook_postgres_server_major_matches_pg_major():
    majors = PG_MAJOR_LINE.findall(_read(RUNBOOK))
    assert len(majors) == 1, f"want exactly one '- Postgres server major: <N>' line, found {majors}"
    assert majors[0] == _pg_major()


def test_runbook_has_the_ops1_sections():
    headings = set(re.findall(r"^## .+$", _read(RUNBOOK), re.MULTILINE))
    assert [s for s in OPS1_RUNBOOK_SECTIONS if s not in headings] == []


def test_runbook_records_the_streamlit_bug_triage_and_d5_recovery():
    text = _read(RUNBOOK)
    assert "### Streamlit bug triage" in text
    assert [row for row in TRIAGE_ROWS if f"\n| {row}" not in text] == []
    assert "jsonb_array_length(hymns::jsonb) = 0" in text   # the D5 recovery query


def test_readme_backups_paragraph_describes_encrypted_backups():
    section = _read(README).split("### Backups (required)", 1)[1].split("\n### ", 1)[0]
    # "`age`" with backticks: a bare "age" is already a substring of "storage" in the old text.
    for needle in ("BACKUP_DATABASE_URL", "`age`", ".dump.age", "docs/ops-runbook.md"):
        assert needle in section, needle
    assert "compressed dump" not in section
