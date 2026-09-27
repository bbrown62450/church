"""Domain errors, the F §1.5 code registry, and (Task 3) their API mapping."""
import subprocess
import sys
from pathlib import Path

import pytest

from domain_errors import (
    ERROR_CODES,
    Busy,
    Conflict,
    DomainError,
    Forbidden,
    InvalidInput,
    NotConfigured,
    NotFound,
    RateLimited,
    Rejected,
    UpstreamError,
    UpstreamTimeout,
)

BACKEND = Path(__file__).resolve().parents[1]

# --- the classes and the registry (F §2.2 item 4, §1.5) ---------------------------


@pytest.mark.parametrize("make, status, code", [
    (lambda: InvalidInput("Church name is required."), 422, "invalid_request"),
    (lambda: NotFound("Not found."), 404, "not_found"),
    (lambda: Forbidden("Only the owner can do that."), 403, "forbidden"),
    (lambda: Conflict("Someone else changed this."), 409, "conflict"),
    (lambda: RateLimited("Slow down.", retry_after_seconds=30), 429, "rate_limited"),
], ids=["InvalidInput", "NotFound", "Forbidden", "Conflict", "RateLimited"])
def test_each_domain_error_has_its_status_and_default_code(make, status, code):
    exc = make()
    assert isinstance(exc, DomainError)
    assert (exc.status, exc.code) == (status, code)
    assert exc.message == str(exc)


@pytest.mark.parametrize("cls, code, status", [
    (Rejected, "invite_rejected", 400),
    (NotConfigured, "ai_not_configured", 503),
    (Busy, "ai_busy", 503),
    (UpstreamError, "ai_upstream_error", 502),
    (UpstreamTimeout, "ai_timeout", 504),
])
def test_per_case_classes_require_a_code(cls, code, status):
    with pytest.raises(ValueError, match="needs a code"):
        cls("Something failed.")
    exc = cls("Something failed.", code=code)
    assert (exc.status, exc.code) == (status, code)


def test_a_code_must_be_registered_with_the_class_status():
    with pytest.raises(ValueError, match="not registered"):
        Rejected("No.", code="not_a_code")
    with pytest.raises(ValueError, match="not registered"):
        Conflict("No.", code="not_found")                  # a 404 code on a 409 class
    assert InvalidInput("Bad rubric.", code="invalid_rubric").status == 422
    assert Conflict("Last admin.", code="last_admin").code == "last_admin"


def test_rate_limited_always_sets_retry_after_seconds():
    exc = RateLimited("You've created 5 churches in the last 24 hours. Try again later.",
                      retry_after_seconds=30)
    assert exc.retry_after_seconds == 30
    assert exc.details == {"retry_after_seconds": 30}
    assert exc.field is None
    assert RateLimited("Slow down.", retry_after_seconds=2.2).retry_after_seconds == 3   # rounded up
    assert RateLimited("Slow down.", retry_after_seconds=0).details == {"retry_after_seconds": 1}


def test_error_codes_is_the_f_1_5_registry():
    assert ERROR_CODES == {
        "bad_request": 400, "invite_rejected": 400, "gmail_state_invalid": 400,
        "gmail_connect_failed": 400,
        "unauthenticated": 401,
        "forbidden": 403,
        "not_found": 404,
        "method_not_allowed": 405,
        "conflict": 409, "last_admin": 409, "owner_must_transfer": 409, "invite_exists": 409,
        "gmail_not_connected": 409,
        "invalid_request": 422, "prompt_invalid": 422, "idempotency_mismatch": 422,
        "invalid_rubric": 422,
        "rate_limited": 429,
        "internal_error": 500,
        "upstream_error": 502, "ai_upstream_error": 502, "gmail_send_failed": 502,
        "auth_unavailable": 503, "ai_not_configured": 503, "ai_busy": 503,
        "gmail_not_configured": 503, "db_unavailable": 503,
        "upstream_timeout": 504, "ai_timeout": 504,
    }
    assert len(ERROR_CODES) == 29


def test_db_unavailable_is_503():
    assert ERROR_CODES["db_unavailable"] == 503


def test_domain_errors_imports_no_fastapi():
    code = ("import sys, domain_errors; "
            "bad = sorted({m.split('.')[0] for m in sys.modules} & {'fastapi', 'starlette', 'streamlit'}); "
            "print(bad); sys.exit(1 if bad else 0)")
    result = subprocess.run([sys.executable, "-c", code], cwd=BACKEND, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
