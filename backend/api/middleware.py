"""Request ids and CORS-safe 500s: pure ASGI middleware (F §2.5; ops slice).

RequestIdMiddleware gives every HTTP request an id: the inbound X-Request-Id
when it matches ^[A-Za-z0-9-]{8,64}$, else a new uuid4 hex. The id lives in a
contextvar while the request runs (anyio copies the context into the
threadpool, so sync routes and dependencies see it too), and every response
started inside the middleware carries it as X-Request-Id. Error bodies and log
lines read it through current_request_id().

Pure ASGI, not BaseHTTPMiddleware: nothing here buffers or re-wraps a response.
"""
import re
import uuid
from contextvars import ContextVar
from typing import Optional

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

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
