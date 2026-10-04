"""Request ids and CORS-safe 500s: pure ASGI middleware (F §2.5; ops slice).

RequestIdMiddleware gives every HTTP request an id: the inbound X-Request-Id
when it matches ^[A-Za-z0-9-]{8,64}$, else a new uuid4 hex. The id lives in a
contextvar while the request runs (anyio copies the context into the
threadpool, so sync routes and dependencies see it too), and every response
started inside the middleware carries it as X-Request-Id. Error bodies and log
lines read it through current_request_id().

UnhandledErrorMiddleware turns an unexpected exception into the uniform 500
body from inside CORSMiddleware and RequestIdMiddleware, so the browser gets a
readable 500 with CORS headers and X-Request-Id instead of a network error.

UploadSizeMiddleware (printed bulletin PR 3a) refuses a cover picture over
10 MB from its Content-Length, before the body is read into memory (the
route would read it all first), and one sent without a length.

Pure ASGI, not BaseHTTPMiddleware: nothing here buffers or re-wraps a response.
"""
import logging
import re
import uuid
from contextvars import ContextVar
from typing import Optional

from starlette.datastructures import MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-Id"

_VALID_REQUEST_ID = re.compile(r"[A-Za-z0-9-]{8,64}")
_request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def current_request_id() -> Optional[str]:
    """The id of the request being handled; None outside RequestIdMiddleware."""
    return _request_id.get()


def _inbound_request_id(scope: Scope) -> Optional[str]:
    """The caller's X-Request-Id if it is well formed, else None."""
    for name, value in scope.get("headers", []):
        if name == b"x-request-id":
            candidate = value.decode("latin-1")
            return candidate if _VALID_REQUEST_ID.fullmatch(candidate) else None
    return None


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = _inbound_request_id(scope) or uuid.uuid4().hex
        token = _request_id.set(request_id)

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                message.setdefault("headers", [])
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            _request_id.reset(token)


class UnhandledErrorMiddleware:
    """Log an unexpected exception and answer 500 `internal_error`.

    If the response has already started, a second one must never start: the
    error is logged and re-raised. Otherwise it is logged, the 500 is sent and
    nothing is re-raised. The exception text never reaches the client.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = False

        async def send_wrapper(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            # The path only, never the query string: it can carry codes or tokens.
            logger.exception("Unhandled error on %s %s", scope["method"], scope["path"])
            if started:
                raise
            from api.errors import error_body   # deferred: api.errors imports this module

            response = JSONResponse(error_body("internal_error", "Something went wrong."), status_code=500)
            await response(scope, receive, send)


class UploadSizeMiddleware:
    """POST /bulletin-images: a 422 naming "image" when the body's
    Content-Length is over bulletin_image.MAX_UPLOAD_BYTES or missing (a
    chunked body), before any of it is read. Every other request passes."""

    PATH = "/bulletin-images"
    NO_LENGTH_MESSAGE = "Send the picture with its size (Content-Length)."

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] != "POST" or scope["path"] != self.PATH:
            await self.app(scope, receive, send)
            return
        from api.errors import error_body           # deferred, as UnhandledErrorMiddleware
        from bulletin_image import MAX_UPLOAD_BYTES, TOO_LARGE_MESSAGE

        lengths = [value for name, value in scope.get("headers", []) if name == b"content-length"]
        message = None
        if len(lengths) != 1 or not lengths[0].isdigit():
            message = self.NO_LENGTH_MESSAGE
        elif int(lengths[0]) > MAX_UPLOAD_BYTES:
            message = TOO_LARGE_MESSAGE
        if message is None:
            await self.app(scope, receive, send)
            return
        response = JSONResponse(error_body("invalid_request", message, fields={"image": message}), status_code=422)
        await response(scope, receive, send)
