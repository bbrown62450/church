"""One error shape for every API failure: {"error": {"code", "message"}}."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

_HTTP_CODES = {
    400: "bad_request",
    401: "unauthenticated",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
}


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def unauthenticated(message: str = "Please sign in.") -> ApiError:
    return ApiError(401, "unauthenticated", message)


def forbidden(message: str = "You don't have access to this church.") -> ApiError:
    return ApiError(403, "forbidden", message)


def auth_unavailable() -> ApiError:
    return ApiError(503, "auth_unavailable", "Sign-in is temporarily unavailable. Try again shortly.")


def _body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_request: Request, exc: ApiError):
        return JSONResponse(_body(exc.code, exc.message), status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def _invalid(_request: Request, _exc: RequestValidationError):
        return JSONResponse(_body("invalid_request", "The request was not valid."), status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_request: Request, exc: StarletteHTTPException):
        code = _HTTP_CODES.get(exc.status_code, "error")
        message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return JSONResponse(_body(code, message), status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, _exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(_body("internal_error", "Something went wrong."), status_code=500)
