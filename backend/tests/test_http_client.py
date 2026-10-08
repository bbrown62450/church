"""integrations.http: the one outbound client (F §2.7; S New modules
"integrations/http.py", Testing "test_http_client.py"; 2a clarifications 24, 32).

Every test answers through httpx.MockTransport installed with
set_http_for_tests, so nothing leaves the process (the _no_network guard in
conftest.py stays active); the autouse _fresh_http_client fixture restores
the default client before the next test."""
import logging

import httpx
import pytest

from integrations import http


def _install(handler):
    """Answer get() with `handler` behind the module's own client settings;
    returns the list of requests the transport saw, in order."""
    seen = []

    def record(request):
        seen.append(request)
        return handler(request)

    http.set_http_for_tests(http.build_client(transport=httpx.MockTransport(record)))
    return seen


def test_user_agent_sent():
    seen = _install(lambda request: httpx.Response(200, text="ok"))
    r = http.get("https://api.example.test/v1/passage",
                 headers={"Authorization": "Token abc"}, read_timeout=10.0)
    assert r.status_code == 200 and r.text == "ok"
    assert http.USER_AGENT == "WorshipServiceBuilder/1.0"
    assert seen[0].headers["User-Agent"] == "WorshipServiceBuilder/1.0"
    assert seen[0].headers["Authorization"] == "Token abc"   # per-call headers are added


def test_plain_http_refused():
    seen = _install(lambda request: httpx.Response(200, text="should not be reached"))
    with pytest.raises(httpx.UnsupportedProtocol) as refused:
        http.get("http://api.example.test/v1/passage", params={"q": "John 3:16"},
                 read_timeout=10.0)
    assert seen == []                                   # refused before the transport
    assert isinstance(refused.value, httpx.HTTPError)   # fetchers catch HTTPError (clarification 24)
    assert "John" not in str(refused.value) and "api.example.test" not in str(refused.value)


def test_redirect_to_http_refused():
    def handler(request):
        return httpx.Response(302, headers={"Location": "http://api.example.test/plain"})

    seen = _install(handler)
    with pytest.raises(httpx.UnsupportedProtocol):
        http.get("https://api.example.test/start", read_timeout=10.0)
    assert [str(request.url) for request in seen] == ["https://api.example.test/start"]


def test_https_redirect_followed():
    def handler(request):
        if request.url.path == "/start":
            return httpx.Response(301, headers={"Location": "https://cdn.example.test/final"})
        return httpx.Response(200, text="done")

    seen = _install(handler)
    r = http.get("https://api.example.test/start", read_timeout=10.0)
    assert (r.status_code, r.text) == (200, "done")
    assert str(r.url) == "https://cdn.example.test/final"
    assert [str(request.url) for request in seen] == [
        "https://api.example.test/start", "https://cdn.example.test/final"]
    assert seen[1].headers["User-Agent"] == "WorshipServiceBuilder/1.0"


def test_per_call_read_timeout_connect_5s():
    seen = _install(lambda request: httpx.Response(200))
    http.get("https://lectio.example.test/day", read_timeout=15.0)
    http.get("https://lectio.example.test/day", read_timeout=10.0)
    assert [request.extensions["timeout"] for request in seen] == [
        {"connect": 5.0, "read": 15.0, "write": 15.0, "pool": 15.0},
        {"connect": 5.0, "read": 10.0, "write": 10.0, "pool": 10.0},
    ]
    assert http.DEFAULT_TIMEOUT == httpx.Timeout(10.0, connect=5.0)
    assert http.build_client().timeout == http.DEFAULT_TIMEOUT
    with pytest.raises(TypeError):
        http.get("https://lectio.example.test/day")     # read_timeout is required


def test_set_http_for_tests_swaps_and_none_restores():
    # A bare client (no https hook) makes the swap visible from outside.
    bare = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(204)))
    http.set_http_for_tests(bare)
    assert http.get("http://plain.example.test/", read_timeout=1.0).status_code == 204
    http.set_http_for_tests(None)
    with pytest.raises(httpx.UnsupportedProtocol):     # the default client's hook, before any I/O
        http.get("http://plain.example.test/", read_timeout=1.0)


def test_httpx_request_logs_silenced(caplog):
    caplog.set_level(logging.INFO)
    _install(lambda request: httpx.Response(200, json={"ok": True}))
    http.get("https://lectio.example.test/day", params={"date": "2026-03-29"}, read_timeout=10.0)
    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("httpcore").level == logging.WARNING
    leaked = [record for record in caplog.records
              if record.name.split(".")[0] in ("httpx", "httpcore")]
    assert leaked == []


def test_the_openai_sdk_logs_at_info_or_above_when_the_root_is_debug(caplog):
    """Slice 6a-3b: at DEBUG the OpenAI SDK logs each request's options, the
    prompt (and so the pastor's prayers) included; its logger stays at INFO."""
    caplog.set_level(logging.DEBUG)
    assert logging.getLogger().level == logging.DEBUG
    assert logging.getLogger("openai").level == logging.INFO
    assert logging.getLogger("openai._base_client").getEffectiveLevel() >= logging.INFO
    logging.getLogger("openai._base_client").debug("Request options: %s", "a private prayer")
    assert [r for r in caplog.records if r.name.startswith("openai")] == []


# --- slice 5b-2: post(), for Google's token, revoke and Gmail send endpoints ----------------------

def test_post_sends_a_form_or_json_with_its_own_timeout_and_the_user_agent():
    seen = _install(lambda request: httpx.Response(200, json={"ok": True}))
    r = http.post("https://oauth2.example.test/token", data={"grant_type": "refresh_token", "code": "c"},
                  timeout=httpx.Timeout(15.0, connect=5.0))
    assert r.json() == {"ok": True}
    http.post("https://gmail.example.test/send", json={"raw": "abc"}, headers={"Authorization": "Bearer t"},
              timeout=httpx.Timeout(30.0, connect=5.0))
    assert [request.method for request in seen] == ["POST", "POST"]
    assert seen[0].headers["Content-Type"] == "application/x-www-form-urlencoded"
    assert seen[0].content == b"grant_type=refresh_token&code=c"
    assert seen[1].headers["Content-Type"] == "application/json"
    assert seen[1].headers["Authorization"] == "Bearer t"
    assert seen[1].headers["User-Agent"] == "WorshipServiceBuilder/1.0"
    assert [request.extensions["timeout"] for request in seen] == [
        {"connect": 5.0, "read": 15.0, "write": 15.0, "pool": 15.0},
        {"connect": 5.0, "read": 30.0, "write": 30.0, "pool": 30.0},
    ]
    with pytest.raises(TypeError):
        http.post("https://oauth2.example.test/token", data={})          # timeout is required


def test_post_never_follows_a_redirect_and_refuses_plain_http():
    seen = _install(lambda request: httpx.Response(307, headers={"Location": "https://elsewhere.example.test/"}))
    r = http.post("https://oauth2.example.test/token", data={"a": "b"}, timeout=httpx.Timeout(5.0))
    assert r.status_code == 307                                          # returned, not replayed elsewhere
    assert [str(request.url) for request in seen] == ["https://oauth2.example.test/token"]
    with pytest.raises(httpx.UnsupportedProtocol):
        http.post("http://oauth2.example.test/token", data={"a": "b"}, timeout=httpx.Timeout(5.0))
    assert len(seen) == 1
