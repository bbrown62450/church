"""Domain errors and the error-code registry (F §1.5, §2.2 item 4; slice 1).

Usecases, repos and domain modules raise these; one handler in api/errors.py
turns each into the uniform body {"error": {"code", "message", "request_id",
"fields"?, "details"?}} with the class's HTTP status. This module imports no
FastAPI, Starlette or Streamlit, so every layer can use it.

ERROR_CODES is the one registry of server error codes and their statuses. The
frontend mirrors it as the ApiErrorCode union in frontend/src/lib/api/errors.ts
(test_error_registry.py keeps the two in step).
"""
import math
from typing import Any, ClassVar, Optional

ERROR_CODES: dict[str, int] = {
    # 400: a well-formed request the domain refuses; bad_request for framework 4xx
    "bad_request": 400,
    "invite_rejected": 400,
    "gmail_state_invalid": 400,
    "gmail_connect_failed": 400,
    # 401
    "unauthenticated": 401,
    # 403: a require_church 403 carries details.reason = "no_church_access"
    "forbidden": 403,
    # 404
    "not_found": 404,
    # 405: a known path called with the wrong method (framework)
    "method_not_allowed": 405,
    # 409
    "conflict": 409,
    "last_admin": 409,
    "owner_must_transfer": 409,
    "invite_exists": 409,
    "gmail_not_connected": 409,
    # 422
    "invalid_request": 422,
    "prompt_invalid": 422,
    "idempotency_mismatch": 422,
    "invalid_rubric": 422,
    # 429: always RateLimited
    "rate_limited": 429,
    # 500
    "internal_error": 500,
    # 502
    "upstream_error": 502,
    "ai_upstream_error": 502,
    "gmail_send_failed": 502,
    # 503
    "auth_unavailable": 503,
    "ai_not_configured": 503,
    "ai_busy": 503,
    "gmail_not_configured": 503,
    "db_unavailable": 503,
    # 504
    "upstream_timeout": 504,
    "ai_timeout": 504,
}


class DomainError(Exception):
    """Base class: a failure the user can be told about, with a registered code.

    `field` names the input the message is about (it becomes `fields[field]` on
    a 422); `details` is an optional, code-specific object (F §1.5).
    """

    status: ClassVar[int] = 500
    default_code: ClassVar[Optional[str]] = None

    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        field: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message)
        code = code or self.default_code
        if code is None:
            raise ValueError(f"{type(self).__name__} needs a code: it has no default code.")
        if ERROR_CODES.get(code) != self.status:
            raise ValueError(
                f"{type(self).__name__} is a {self.status}; code {code!r} is not registered "
                f"with that status in ERROR_CODES."
            )
        self.message = message
        self.code = code
        self.field = field
        self.details = details


class InvalidInput(DomainError):
    status = 422
    default_code = "invalid_request"


class NotFound(DomainError):
    status = 404
    default_code = "not_found"


class Forbidden(DomainError):
    status = 403
    default_code = "forbidden"


class Conflict(DomainError):
    status = 409
    default_code = "conflict"


class Rejected(DomainError):
    status = 400


class NotConfigured(DomainError):
    status = 503


class Busy(DomainError):
    status = 503


class UpstreamError(DomainError):
    status = 502


class UpstreamTimeout(DomainError):
    status = 504


class RateLimited(DomainError):
    """The only 429 (F §1.5, §2.2): the limiter and the church-create cap raise it.

    It always carries details.retry_after_seconds (a whole number of seconds,
    at least 1); the API handler copies it into the Retry-After header, and
    run_idempotent never stores it.
    """

    status = 429
    default_code = "rate_limited"

    def __init__(self, message: str, *, retry_after_seconds: float):
        seconds = max(1, math.ceil(retry_after_seconds))
        super().__init__(message, details={"retry_after_seconds": seconds})
        self.retry_after_seconds = seconds
