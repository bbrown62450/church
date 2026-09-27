"""One error shape for every API failure (F §1.5):
{"error": {"code", "message", "request_id", "fields"?, "details"?}}.

Code below the API raises domain_errors.DomainError subclasses; one handler
here maps them. ApiError stays for API-layer failures only: authentication and
the /health/ready probe's db_unavailable (F §2.2). Every code comes from
domain_errors.ERROR_CODES.
"""
import logging
import uuid
from typing import Any, Optional, Sequence

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.middleware import current_request_id
from domain_errors import DomainError, RateLimited

logger = logging.getLogger(__name__)

# Framework (Starlette) HTTP errors. Any other status keeps its number and gets
# bad_request (4xx) or internal_error (5xx): every code is in ERROR_CODES.
_HTTP_CODES = {
    400: "bad_request",
    401: "unauthenticated",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
}

# Leading parts of a Pydantic error location that name where the value came from.
_LOCATION_PREFIXES = ("body", "query", "header", "path")


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, *,
                 details: Optional[dict[str, Any]] = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details


def unauthenticated(message: str = "Please sign in.") -> ApiError:
    return ApiError(401, "unauthenticated", message)


def forbidden(message: str = "You don't have access to this church.", *,
              details: Optional[dict[str, Any]] = None) -> ApiError:
    return ApiError(403, "forbidden", message, details=details)


def auth_unavailable() -> ApiError:
    return ApiError(503, "auth_unavailable", "Sign-in is temporarily unavailable. Try again shortly.")


def db_unavailable() -> ApiError:
    """503 from GET /health/ready only (F §1.5 registry; the recorded F §2.2 exception)."""
    return ApiError(503, "db_unavailable", "The database is not reachable.")


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str
    fields: Optional[dict[str, str]] = None
    details: Optional[dict[str, Any]] = None


class ErrorBody(BaseModel):
    """Every error response's body (F §1.5). `fields` and `details` are left out when absent."""

    error: ErrorDetail


def error_responses(*statuses: int) -> dict[int, dict[str, Any]]:
    """`responses=` for a route decorator: each status documents ErrorBody in OpenAPI."""
    return {status: {"model": ErrorBody} for status in statuses}


def _body(code: str, message: str, *, fields: Optional[dict[str, str]] = None,
          details: Optional[dict[str, Any]] = None) -> dict:
    """The uniform error body (F §1.5).

    `request_id` is the X-Request-Id of the request. The uuid4 fallback only
    fires outside RequestIdMiddleware, in the last-resort handler below.
    `fields` and `details` appear only when they are non-empty.
    """
    error: dict[str, Any] = {
        "code": code,
        "message": message,
        "request_id": current_request_id() or uuid.uuid4().hex,
    }
    if fields:
        error["fields"] = fields
    if details:
        error["details"] = details
    return {"error": error}


# Public name for UnhandledErrorMiddleware (api/middleware.py).
error_body = _body


def _field_message(error: dict) -> str:
    kind = error.get("type")
    if kind == "missing":
        return "Required."
    if kind == "string_too_long":
        return f"Too long (max {(error.get('ctx') or {}).get('max_length')} characters)."
    return "Not a valid value."


def validation_fields(errors: Sequence[dict]) -> dict[str, str]:
    """Pydantic errors as {"dotted.location": short message} (F §1.5).

    The leading body/query/header/path part is dropped, so
    ("body", "hymns", "opening", "title") becomes "hymns.opening.title". An
    error about the whole body (location ("body",)) or about unparseable JSON
    names no field and is left out. The first error for a location wins.
    """
    fields: dict[str, str] = {}
    for error in errors:
        if error.get("type") == "json_invalid":      # its location is a character offset
            continue
        location = [str(part) for part in error.get("loc", ())]
        if location and location[0] in _LOCATION_PREFIXES:
            location = location[1:]
        key = ".".join(location)
        if key and key not in fields:
            fields[key] = _field_message(error)
    return fields


def domain_error_response(exc: DomainError) -> JSONResponse:
    """The response for a DomainError: the app's handler, and run_idempotent (api/idempotency.py)."""
    fields = {exc.field: exc.message} if exc.field and exc.status == 422 else None
    headers = {"Retry-After": str(exc.retry_after_seconds)} if isinstance(exc, RateLimited) else None
    return JSONResponse(_body(exc.code, exc.message, fields=fields, details=exc.details),
                        status_code=exc.status, headers=headers)


def _http_code(status: int) -> str:
    if status in _HTTP_CODES:
        return _HTTP_CODES[status]
    return "internal_error" if status >= 500 else "bad_request"


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_request: Request, exc: ApiError):
        return JSONResponse(_body(exc.code, exc.message, details=exc.details), status_code=exc.status)

    @app.exception_handler(DomainError)
    async def _domain_error(_request: Request, exc: DomainError):
        return domain_error_response(exc)

    @app.exception_handler(RequestValidationError)
    async def _invalid(_request: Request, exc: RequestValidationError):
        return JSONResponse(
            _body("invalid_request", "The request was not valid.", fields=validation_fields(exc.errors())),
            status_code=422,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_request: Request, exc: StarletteHTTPException):
        if exc.status_code >= 500:
            message = "Something went wrong."          # never framework or upstream text
        else:
            message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return JSONResponse(_body(_http_code(exc.status_code), message), status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, _exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(_body("internal_error", "Something went wrong."), status_code=500)
