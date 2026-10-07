"""A fake Google for the Gmail tests (slice 5b-2): an httpx.MockTransport behind
integrations.http.set_http_for_tests, so no test reaches the network (the
conftest guard stays on) and the autouse _fresh_http_client fixture puts the
real client back afterwards.

Each endpoint answers with what its attribute holds: an httpx.Response, an
exception to raise (an httpx error, as the transport would), or a function of
the request returning either. `requests` records every request in order;
`sent(...)` and friends filter it. The defaults are a successful connect and
send for owner@example.com.
"""
import base64
import json
from email import message_from_bytes, policy
from email.message import EmailMessage
from typing import Callable, Union
from urllib.parse import parse_qs

import httpx

import google_oauth
from integrations import http

Answer = Union[httpx.Response, Exception, Callable[[httpx.Request], Union[httpx.Response, Exception]]]

ACCESS_TOKEN = "access-token-1"
REFRESH_TOKEN = "refresh-token-1"
FRESH_ACCESS_TOKEN = "access-token-2"


def google_error(status: int, error: str) -> httpx.Response:
    """A token endpoint error ({"error": "invalid_grant", ...})."""
    return httpx.Response(status, json={"error": error, "error_description": "SECRET-GOOGLE-TEXT"})


# The Gmail API's error status for each HTTP status the tests use.
GMAIL_STATUS = {400: "INVALID_ARGUMENT", 401: "UNAUTHENTICATED", 403: "PERMISSION_DENIED", 429: "RESOURCE_EXHAUSTED"}


def gmail_error(status: int, reason: str, api_status: str | None = None) -> httpx.Response:
    """A Gmail API error with one reason (and its status name, by default the usual one for `status`)."""
    return httpx.Response(status, json={"error": {"code": status, "message": "SECRET-GOOGLE-TEXT",
                                                  "errors": [{"reason": reason, "message": "SECRET-GOOGLE-TEXT"}],
                                                  "status": api_status or GMAIL_STATUS.get(status, "UNKNOWN")}})


class FakeGoogle:
    def __init__(self, email: str = "owner@example.com"):
        self.exchange: Answer = httpx.Response(200, json={
            "access_token": ACCESS_TOKEN, "refresh_token": REFRESH_TOKEN, "expires_in": 3599,
            "scope": " ".join(google_oauth.SCOPES), "token_type": "Bearer"})
        self.userinfo: Answer = httpx.Response(200, json={"email": email, "verified_email": True})
        self.refresh: Answer = httpx.Response(200, json={"access_token": FRESH_ACCESS_TOKEN, "expires_in": 3599})
        self.send: Answer = httpx.Response(200, json={"id": "msg-1", "threadId": "thread-1", "labelIds": ["SENT"]})
        self.revoke: Answer = httpx.Response(200)
        self.requests: list[httpx.Request] = []

    def install(self) -> "FakeGoogle":
        http.set_http_for_tests(http.build_client(transport=httpx.MockTransport(self._handle)))
        return self

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        url = str(request.url).split("?")[0]
        if url == google_oauth.TOKEN_URI:
            form = parse_qs(request.content.decode())
            answer = self.exchange if form.get("grant_type") == ["authorization_code"] else self.refresh
        elif url == google_oauth.USERINFO_URI:
            answer = self.userinfo
        elif url == google_oauth.GMAIL_SEND_URI:
            answer = self.send
        elif url == google_oauth.REVOKE_URI:
            answer = self.revoke
        else:
            raise AssertionError(f"unexpected request to {url}")
        if callable(answer) and not isinstance(answer, (httpx.Response, Exception)):
            answer = answer(request)
        if isinstance(answer, Exception):
            raise answer
        return answer

    def calls(self, url: str, grant_type: str | None = None) -> list[httpx.Request]:
        found = [r for r in self.requests if str(r.url).split("?")[0] == url]
        if grant_type is not None:
            found = [r for r in found if parse_qs(r.content.decode()).get("grant_type") == [grant_type]]
        return found

    def form(self, request: httpx.Request) -> dict[str, str]:
        return {key: values[0] for key, values in parse_qs(request.content.decode()).items()}

    def sent(self) -> list[EmailMessage]:
        """Every message the Gmail send endpoint received, parsed."""
        messages = []
        for request in self.calls(google_oauth.GMAIL_SEND_URI):
            raw = base64.urlsafe_b64decode(json.loads(request.content)["raw"])
            messages.append(message_from_bytes(raw, policy=policy.default))
        return messages

