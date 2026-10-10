"""usecases.role_policy against tests/fixtures/shared/role_policy.json (6b spec,
Testing → "Pure policy"; F acceptance 19; slice 6b-1): the fixture holds
exactly the reachable states of the four checks, and every row's outcome,
code, message and field holds."""
import itertools
import json
import uuid
from pathlib import Path

import pytest

from domain_errors import Conflict, Forbidden, InvalidInput
from usecases import role_policy

FIXTURE = Path(__file__).parent / "fixtures" / "shared" / "role_policy.json"
ROWS = json.loads(FIXTURE.read_text(encoding="utf-8"))["rows"]
ROLES = ("owner", "admin", "member")
TARGETS = ("self", "owner", "admin", "member")
ACTOR, OTHER = uuid.UUID(int=1), uuid.UUID(int=2)


def _key(row: dict) -> tuple:
    return (row["action"], row["actor_role"], row.get("target"), row.get("new_role"), row.get("admin_count"))


def _reachable() -> set[tuple]:
    """Every state the database can hold: the owner acting on "owner" is self
    (one owner per church), and an owner or admin leaving counts themselves."""
    states = set()
    for actor, target in itertools.product(ROLES, TARGETS):
        if actor == "owner" and target == "owner":
            continue
        states |= {("change_role", actor, target, new_role, None) for new_role in ("member", "admin")}
        states |= {("remove", actor, target, None, None), ("transfer", actor, target, None, None)}
    for actor, count in itertools.product(ROLES, (0, 1, 2)):
        if not (count == 0 and actor in ("owner", "admin")):
            states.add(("leave", actor, None, None, count))
    return states


def test_the_fixture_holds_exactly_the_51_reachable_states():
    keys = [_key(row) for row in ROWS]
    assert len(keys) == len(set(keys)) == 51
    assert set(keys) == _reachable()


def _call(row: dict):
    target_id = ACTOR if row.get("target") == "self" else OTHER
    target_role = row["actor_role"] if row.get("target") == "self" else row.get("target")
    action = row["action"]
    if action == "change_role":
        return role_policy.check_role_change(actor_id=ACTOR, actor_role=row["actor_role"], target_id=target_id,
                                             target_role=target_role, new_role=row["new_role"])
    if action == "remove":
        return role_policy.check_remove(actor_id=ACTOR, actor_role=row["actor_role"], target_id=target_id,
                                        target_role=target_role)
    if action == "leave":
        return role_policy.check_leave(role=row["actor_role"], admin_count=row["admin_count"])
    return role_policy.check_transfer(actor_id=ACTOR, actor_role=row["actor_role"], target_id=target_id)


ERRORS = {"forbidden": (Forbidden, "forbidden"), "invalid": (InvalidInput, "invalid_request"),
          "owner_must_transfer": (Conflict, "owner_must_transfer"), "last_admin": (Conflict, "last_admin")}


@pytest.mark.parametrize("row", ROWS, ids=lambda row: "-".join(str(v) for v in _key(row) if v is not None))
def test_every_row_has_its_outcome(row):
    if row["expected"] in ("allow", "noop"):
        result = _call(row)
        expected = {"allow": "change" if row["action"] == "change_role" else None, "noop": "noop"}[row["expected"]]
        assert result == expected
        return
    kind, code = ERRORS[row["expected"]]
    with pytest.raises(kind) as raised:
        _call(row)
    assert (type(raised.value), raised.value.code, raised.value.message, raised.value.field, raised.value.details) == (
        kind, code, row["message"], row.get("field"), None)
