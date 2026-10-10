"""repos.integrity.find_violations and scripts/check_integrity.py (6b spec,
"Church integrity runbook" and Testing → Integrity; slice 6b-1): each kind is
found, soft-deleted churches are skipped, the output holds ids and counts
only, and the runbook's dedupe step leaves the newest pending invite."""
import importlib.util
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import select, text, update

from db import session_scope
from db.models import Church, Invite, Membership
from repos.integrity import find_violations
from repos.invites import create_invite
from repos.memberships import add_membership
from tests.invite_helpers import store_unchecked_role

BACKEND = Path(__file__).resolve().parents[1]
SCRIPT = BACKEND / "scripts" / "check_integrity.py"
README = BACKEND / "migrations" / "README.md"
NOW = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)


def _load_check_integrity():
    """backend/scripts is not a package: load the script by path, as `python scripts/…` does."""
    spec = importlib.util.spec_from_file_location("check_integrity_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def grace(make_user, make_church):
    owner = make_user(email="owner@example.com", name="Olive Owner")
    church = make_church(name="Grace", owner_user_id=owner)
    add_membership(make_user(email="admin@example.com"), church, "admin")
    return church, owner


def _set_roles(church, role, *, where_role):
    with session_scope() as s:
        s.execute(update(Membership).where(Membership.church_id == church, Membership.role == where_role)
                  .values(role=role))


def _pending(church, owner, email, *, created_at=NOW) -> uuid.UUID:
    invite_id = uuid.uuid4()
    with session_scope() as s:
        s.add(Invite(id=invite_id, church_id=church, code=uuid.uuid4().hex, email=email, role="member",
                     created_by=owner, created_at=created_at, expires_at=created_at + timedelta(days=7)))
    return invite_id


def test_a_clean_church_has_no_violations(grace):
    church, owner = grace
    create_invite(church_id=church, created_by=owner, email="new@example.com")
    assert find_violations() == []


def test_an_ownerless_church_and_one_with_no_admin_are_reported(grace, make_church, make_user):
    church, _ = grace
    _set_roles(church, "admin", where_role="owner")            # demoted directly in SQL: no owner
    lonely = make_church(name="Hope", owner_user_id=make_user(email="hope@example.com"))
    _set_roles(lonely, "member", where_role="owner")           # no owner and no admin
    gone = make_church(name="Gone", owner_user_id=make_user(email="gone@example.com"))
    _set_roles(gone, "member", where_role="owner")
    with session_scope() as s:                                  # soft-deleted: not checked
        s.execute(update(Church).where(Church.id == gone).values(deleted_at=NOW))
    found = find_violations()
    assert sorted((v["kind"], v["church_id"], v.get("owners")) for v in found) == sorted([
        ("owner_count", church, 0), ("owner_count", lonely, 0), ("no_admin", lonely, None)])


def test_two_owners_are_reported(grace):
    church, _ = grace
    with session_scope() as s:   # a row from before 0009 (or written by hand with the index gone)
        s.execute(text("DROP INDEX uq_memberships_one_owner"))
    _set_roles(church, "owner", where_role="admin")
    assert find_violations() == [{"kind": "owner_count", "church_id": church, "owners": 2}]


def test_an_invite_with_another_role_is_reported(grace):
    church, owner = grace
    code = create_invite(church_id=church, created_by=owner)
    store_unchecked_role(code, "owner")
    with session_scope() as s:
        invite_id = s.execute(select(Invite.id).where(Invite.code == code)).scalar_one()
    assert find_violations() == [{"kind": "invite_role", "church_id": church, "invite_id": invite_id}]


def test_duplicate_pending_invites_are_reported_and_the_runbook_step_keeps_the_newest(grace):
    church, owner = grace
    with session_scope() as s:                  # as a database from before 0008 could hold them
        s.execute(text("DROP INDEX uq_invites_pending_email"))
    older = _pending(church, owner, "dup@example.com")
    newer = _pending(church, owner, "DUP@example.com", created_at=NOW + timedelta(hours=1))
    _pending(church, owner, "other@example.com")
    assert find_violations() == [{"kind": "pending_duplicate", "church_id": church, "invites": 2}]
    step = re.search(r"\n2\. \*\*Duplicate pending email invites\*\*.*?```sql\n(.*?)```",
                     README.read_text(encoding="utf-8"), re.S).group(1)
    with session_scope() as s:
        s.execute(text(step))
    with session_scope() as s:
        revoked = dict(s.execute(select(Invite.id, Invite.revoked).where(Invite.id.in_([older, newer]))).all())
    assert revoked == {older: True, newer: False}
    assert find_violations() == []


def test_duplicate_pending_invites_in_a_soft_deleted_church_are_reported_too(grace):
    """0008's pre-check counts every church's invites, soft-deleted ones
    included, so the check must report them there too, or it says OK and the
    upgrade still refuses (6b-1 build review 3)."""
    church, owner = grace
    with session_scope() as s:                  # as a database from before 0008 could hold them
        s.execute(text("DROP INDEX uq_invites_pending_email"))
    _pending(church, owner, "dup@example.com")
    _pending(church, owner, "Dup@Example.com", created_at=NOW + timedelta(hours=1))
    with session_scope() as s:
        s.execute(update(Church).where(Church.id == church).values(deleted_at=NOW))
    assert find_violations() == [{"kind": "pending_duplicate", "church_id": church, "invites": 2}]


def test_the_script_prints_ids_and_counts_only_and_exits_1(grace, tmp_db, monkeypatch, capsys):
    church, owner = grace
    _set_roles(church, "admin", where_role="owner")
    code = create_invite(church_id=church, created_by=owner, email="secret@example.com")
    store_unchecked_role(code, "owner")
    monkeypatch.setenv("DATABASE_URL", str(tmp_db.url))
    assert _load_check_integrity().main([]) == 1
    out, err = capsys.readouterr()
    with session_scope() as s:
        invite_id = s.execute(select(Invite.id).where(Invite.code == code)).scalar_one()
    assert out.splitlines() == [f"owner_count church={church} owners=0", f"invite_role church={church} invite={invite_id}"]
    assert err.startswith("Database: dialect=sqlite")
    for secret in ("secret@example.com", "owner@example.com", "Olive", "Grace", code):
        assert secret not in out + err


def test_the_script_says_ok_and_exits_0_when_clean(grace, tmp_db, monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", str(tmp_db.url))
    assert _load_check_integrity().main([]) == 0
    assert capsys.readouterr().out == "OK: no integrity violations.\n"


def test_the_script_refuses_without_database_url(monkeypatch, capsys):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert _load_check_integrity().main([]) == 2
    assert capsys.readouterr().err == "DATABASE_URL is not set.\n"


@pytest.mark.postgres
def test_the_readme_query_counts_what_the_script_finds_on_postgres():
    """README "Before 0008_invites_integrity" step 2 (the SQL Editor's way) and
    find_violations (check_integrity.py's way) agree, on a database at 0007
    holding one problem of each kind (plus a second ownerless church)."""
    import os

    from alembic import command
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import NullPool

    from db.engine import _normalize_url
    from db.schema_check import alembic_config
    from tests.pg_helpers import require_local_test_url, throwaway_database

    url = os.environ.get("TEST_DATABASE_URL", "").strip()
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set (the backend-postgres CI job sets it)")
    readme = README.read_text(encoding="utf-8").split("\n## Before 0008_invites_integrity (slice 6b-1)\n", 1)[1]
    counts_sql = re.findall(r"```sql\n(.*?)```", readme, re.S)[0]
    with throwaway_database(require_local_test_url(url), role_bypassrls=True) as sandbox:
        command.upgrade(alembic_config(url=sandbox.role_url, configure_logger=False), "0007_bulletin_images")
        engine = create_engine(_normalize_url(sandbox.role_url), poolclass=NullPool)
        try:
            with Session(engine) as s, s.begin():
                user, grace, hope, joy = uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
                s.execute(text("INSERT INTO users (id, email, created_at) VALUES (:u, 'p@example.com', now())"),
                          {"u": user})
                for church in (grace, hope, joy):
                    s.execute(text("INSERT INTO churches (id, name, timezone, settings, created_at) "
                                   "VALUES (:c, 'C', 'UTC', '{}', now())"), {"c": church})
                s.execute(text("INSERT INTO memberships (church_id, user_id, role, created_at) VALUES "
                               "(:g, :u, 'owner', now()), (:h, :u, 'admin', now()), (:j, :u, 'member', now())"),
                          {"g": grace, "h": hope, "j": joy, "u": user})
                for email, role in (("dup@example.com", "member"), ("Dup@example.com", "member"),
                                    (None, "owner")):
                    s.execute(text(
                        "INSERT INTO invites (id, church_id, code, email, role, created_by, created_at, expires_at, "
                        "revoked, reusable) VALUES (:id, :c, :code, :email, :role, :u, now(), now() + interval '7 days', "
                        "false, false)"),
                        {"id": uuid.uuid4(), "c": grace, "code": uuid.uuid4().hex, "email": email, "role": role,
                         "u": user})
            with Session(engine) as s:
                kinds = [v["kind"] for v in find_violations(session=s)]
                counts = dict(s.execute(text(counts_sql)).mappings().one())
        finally:
            engine.dispose()
    assert kinds == ["owner_count", "owner_count", "no_admin", "invite_role", "pending_duplicate"]
    assert (counts["churches_without_one_owner"], counts["churches_without_admin"], counts["other_role_invites"],
            counts["duplicate_pending_pairs"]) == (2, 1, 1, 1)
