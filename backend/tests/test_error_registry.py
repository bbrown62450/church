"""The frontend error-code union mirrors domain_errors.ERROR_CODES (S Testing; ops handoff).

frontend/src/lib/api/errors.ts is read as text. Its ServerErrorCode union must
list exactly the registry's codes, and the client-only codes must never shadow
a server code, so a code added on one side fails CI until the other side has it.
"""
import re
from pathlib import Path

from domain_errors import ERROR_CODES

ERRORS_TS = Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "api" / "errors.ts"


def _union(name: str) -> list[str]:
    """The string literals of `export type <name> = ...;` in errors.ts, in order."""
    text = ERRORS_TS.read_text(encoding="utf-8")
    match = re.search(rf"export type {name} =(.*?);", text, re.DOTALL)
    assert match, f"errors.ts has no `export type {name} = ...;`"
    return re.findall(r'"([^"]*)"', match.group(1))


def test_frontend_union_lists_every_error_code():
    server = _union("ServerErrorCode")
    assert sorted(set(ERROR_CODES) - set(server)) == []
    assert "db_unavailable" in server   # the ops handoff code


def test_frontend_union_has_no_unregistered_server_codes():
    server = _union("ServerErrorCode")
    client = _union("ClientErrorCode")
    assert sorted(set(server) - set(ERROR_CODES)) == []
    assert len(server) == len(set(server)), "a code is listed twice"
    assert client == ["network_error", "timeout", "aborted", "unknown"]
    assert set(client).isdisjoint(ERROR_CODES)
    # ApiErrorCode is exactly ServerErrorCode | ClientErrorCode: no stray literal.
    assert _union("ApiErrorCode") == []
