"""The one outbound HTTP client (F §2.7; S New modules "integrations/http.py").

Every upstream call the new app makes (Lectio, Vanderbilt, bible-api, ESV,
and from slice 5b-2 Google's OAuth and Gmail endpoints) goes through get() or
post(). One module-level httpx.Client carries the settings F §2.7 fixes, so
no caller picks its own:
- User-Agent "WorshipServiceBuilder/1.0";
- follow_redirects=True, but only to https: a request event hook refuses any
  non-https URL, and httpx runs that hook for every redirect hop too;
- connect timeout 5 s; the read timeout is chosen per call (S Timeouts);
- post() never follows a redirect: a POST (a token exchange, an email send)
  is answered where it was sent or not at all, never replayed elsewhere.

A refused URL raises httpx.UnsupportedProtocol, an httpx.HTTPError, so a
fetcher that catches httpx.HTTPError reports it as an upstream failure rather
than a 500 (2a clarification 24). The message names the scheme only, never
the URL or its query string.

httpx logs every request's full URL, query string included, at INFO, and the
API's root logger runs at INFO (api/logging_config.py). Importing this module
sets the "httpx" and "httpcore" loggers to WARNING, so upstream URLs, dates
and ESV queries never reach the logs (F §2.5; 2a clarification 32). It also
holds the OpenAI SDK's "openai" logger at INFO: at DEBUG the SDK logs each
request's options, the prompt included, and a prompt can hold the pastor's
prayers (slice 6a-3b clarification 19), so even LOG_LEVEL=DEBUG keeps them out.

Tests swap the client with set_http_for_tests(build_client(transport=...));
set_http_for_tests(None) restores the default, and an autouse fixture in
tests/conftest.py does that before every test.

No FastAPI, no Streamlit (tests/test_no_streamlit_in_core.py).
"""
import logging
from typing import Mapping

import httpx

USER_AGENT = "WorshipServiceBuilder/1.0"
CONNECT_TIMEOUT = 5.0
DEFAULT_TIMEOUT = httpx.Timeout(10.0, connect=CONNECT_TIMEOUT)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.INFO)


def _require_https(request: httpx.Request) -> None:
    """Request event hook: refuse any URL that is not https, redirect hops included."""
    if request.url.scheme != "https":
        raise httpx.UnsupportedProtocol(
            f"Only https upstream URLs are allowed, not {request.url.scheme!r}.",
            request=request,
        )


def build_client(transport: httpx.BaseTransport | None = None) -> httpx.Client:
    """A client with this module's settings. `transport` is for tests
    (httpx.MockTransport); None uses httpx's real transport."""
    return httpx.Client(
        timeout=DEFAULT_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
        event_hooks={"request": [_require_https]},
        transport=transport,
    )


_DEFAULT_CLIENT = build_client()
_client = _DEFAULT_CLIENT


def get(url: str, *, params: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None, read_timeout: float) -> httpx.Response:
    """GET `url` with the shared client; `read_timeout` seconds to read, 5 s to connect.

    Raises httpx.HTTPError subclasses only for transport problems (a timeout,
    a refused URL, a connection error); a 4xx or 5xx is returned, not raised,
    so each fetcher decides what a status means."""
    return _client.get(
        url,
        params=params,
        headers=headers,
        timeout=httpx.Timeout(read_timeout, connect=CONNECT_TIMEOUT),
    )


def post(url: str, *, data: Mapping[str, str] | None = None, json: object = None,
         headers: Mapping[str, str] | None = None, timeout: httpx.Timeout) -> httpx.Response:
    """POST a form (`data`) or a JSON body (`json`) to `url` with the shared
    client and the given `timeout` (slice 5b-2: Google's token, revoke and
    Gmail send endpoints). A redirect is returned as it is, never followed.

    As get(): transport problems raise httpx.HTTPError subclasses, a 4xx or
    5xx is returned for the caller to classify."""
    return _client.post(url, data=data, json=json, headers=headers, timeout=timeout, follow_redirects=False)


def set_http_for_tests(client: httpx.Client | None) -> None:
    """Route get() through `client`; None restores the module's default client."""
    global _client
    _client = _DEFAULT_CLIENT if client is None else client
