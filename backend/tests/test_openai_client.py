"""integrations.openai_client (F §2.8 as refined by slice 3; S Backend 3.7,
Testing `test_openai_client.py`; AC5, AC6, AC18).

No test reaches OpenAI: the settings come from a dict, and the SDK client is
a stand-in whose chat.completions.create records each call and answers from a
script of replies and SDK exceptions (built with the SDK's own HTTP types).
"""
import importlib
import inspect
import logging
from pathlib import Path
from types import SimpleNamespace

import openai
import pytest

from domain_errors import Busy, NotConfigured, UpstreamError, UpstreamTimeout
from integrations import openai_client as ai
from tests.conftest import FakeClock

# The HTTP library this SDK is built on (httpx in openai 1.x, httpx2 in 3.x), read
# from the SDK's own annotation of an error's `response`, so the tests build real
# SDK exceptions whichever version is installed.
SDK_HTTP = importlib.import_module(
    str(openai.APIStatusError.__init__.__annotations__["response"]).split(".")[0])
URL = "https://api.openai.com/v1/chat/completions"
REQUIREMENTS = Path(__file__).resolve().parents[1] / "requirements.txt"
MESSAGES = [{"role": "system", "content": "Reply with JSON only."},
            {"role": "user", "content": "Pick hymns."}]


def settings(**overrides) -> ai.AISettings:
    return ai.AISettings(**{"api_key": "sk-test", "model": "test-model", **overrides})


# --- T2: settings, availability, the startup line, the fake ---------------------------


def test_no_key_is_not_configured_with_a_warning(caplog):
    caplog.set_level(logging.INFO, logger="integrations.openai_client")
    loaded = ai.load_settings({"OPENAI_MODEL": "test-model", "OPENAI_API_KEY": "   "})
    assert loaded.api_key == "" and loaded.problem == "OPENAI_API_KEY missing"
    ai.configure_for_tests(settings=loaded)
    assert ai.ai_available() is False
    ai.ai_settings.cache_clear()
    with pytest.MonkeyPatch.context() as mp:
        mp.delenv("OPENAI_API_KEY", raising=False)
        mp.setenv("OPENAI_MODEL", "test-model")
        ai.log_startup_state()
    assert [(r.levelname, r.getMessage()) for r in caplog.records] == [
        ("WARNING", "AI: not configured (OPENAI_API_KEY missing)")]


def test_key_without_model_is_not_configured(caplog, monkeypatch):
    caplog.set_level(logging.INFO, logger="integrations.openai_client")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret-value")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    ai.reset_for_tests()
    assert ai.ai_available() is False
    ai.log_startup_state()
    assert [(r.levelname, r.getMessage()) for r in caplog.records] == [
        ("WARNING", "AI: not configured (OPENAI_MODEL missing)")]
    assert "sk-secret-value" not in caplog.text


def test_non_ascii_key_is_not_configured_and_never_logged(caplog, monkeypatch):
    caplog.set_level(logging.INFO, logger="integrations.openai_client")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-‑pasted key")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    ai.reset_for_tests()
    assert ai.ai_available() is False
    ai.log_startup_state()
    assert [(r.levelname, r.getMessage()) for r in caplog.records] == [
        ("ERROR", "AI: not configured (OPENAI_API_KEY is not ASCII)")]
    assert "pasted" not in caplog.text


def test_configured_logs_the_model_only(caplog, monkeypatch):
    caplog.set_level(logging.INFO, logger="integrations.openai_client")
    monkeypatch.setenv("OPENAI_API_KEY", "  sk-secret-value  ")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    ai.reset_for_tests()
    assert ai.ai_settings().api_key == "sk-secret-value"          # stripped
    assert ai.ai_available() is True
    ai.log_startup_state()
    assert [(r.levelname, r.getMessage()) for r in caplog.records] == [
        ("INFO", "AI: configured (model=test-model)")]
    assert "sk-secret" not in caplog.text


def test_settings_defaults_overrides_and_bad_values(caplog):
    defaults = ai.load_settings({"OPENAI_API_KEY": "k", "OPENAI_MODEL": "m"})
    assert (defaults.timeout_seconds, defaults.max_retries, defaults.max_concurrency,
            defaults.temperature) == (30.0, 1, 4, None)
    custom = ai.load_settings({"OPENAI_API_KEY": "k", "OPENAI_MODEL": " m ",
                               "OPENAI_TIMEOUT_SECONDS": "20", "OPENAI_MAX_RETRIES": "0",
                               "OPENAI_MAX_CONCURRENCY": "2", "OPENAI_TEMPERATURE": "0.3"})
    assert (custom.model, custom.timeout_seconds, custom.max_retries, custom.max_concurrency,
            custom.temperature) == ("m", 20.0, 0, 2, 0.3)
    bad = ai.load_settings({"OPENAI_TIMEOUT_SECONDS": "soon", "OPENAI_MAX_RETRIES": "-1",
                            "OPENAI_MAX_CONCURRENCY": "0", "OPENAI_TEMPERATURE": "warm"})
    assert (bad.timeout_seconds, bad.max_retries, bad.max_concurrency, bad.temperature) == (
        30.0, 1, 4, None)
    assert caplog.text.count("is not valid") == 4
    # Non-finite numbers are not valid either, and the key never shows in the settings' repr.
    odd = ai.load_settings({"OPENAI_API_KEY": "sk-SECRET", "OPENAI_TIMEOUT_SECONDS": "nan",
                            "OPENAI_TEMPERATURE": "inf"})
    assert (odd.timeout_seconds, odd.temperature) == (30.0, None)
    assert "sk-SECRET" not in repr(odd)


def test_reasoning_effort_is_read_only_when_set(caplog):
    assert ai.load_settings({"OPENAI_API_KEY": "k", "OPENAI_MODEL": "m"}).reasoning_effort is None
    assert ai.load_settings({"OPENAI_REASONING_EFFORT": "  "}).reasoning_effort is None
    assert ai.load_settings({"OPENAI_REASONING_EFFORT": " Minimal "}).reasoning_effort == "minimal"
    assert ai.load_settings({"OPENAI_REASONING_EFFORT": "very high"}).reasoning_effort is None
    assert caplog.text.count("is not valid") == 1


def test_fake_ai_records_calls_and_takes_over_until_reset():
    fake = ai.FakeAI(reply='{"opening": []}', available=True)
    ai.set_ai_for_tests(fake)
    assert ai.ai_available() is True
    assert ai.complete(MESSAGES, max_completion_tokens=50, json_mode=True, deadline=12.5) == '{"opening": []}'
    assert fake.calls == [{"messages": MESSAGES, "max_completion_tokens": 50,
                           "json_mode": True, "deadline": 12.5}]
    ai.set_ai_for_tests(ai.FakeAI(available=False, error=Busy(ai.BUSY_MESSAGE, code="ai_busy")))
    assert ai.ai_available() is False
    with pytest.raises(Busy):
        ai.complete(MESSAGES, max_completion_tokens=50)
    ai.reset_for_tests()
    ai.configure_for_tests(settings=settings(api_key=""))
    assert ai.ai_available() is False                    # the real client again


def test_the_lifespan_logs_the_ai_state_once(tmp_db, caplog, monkeypatch):
    from fastapi.testclient import TestClient

    from api.main import create_app

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    ai.reset_for_tests()
    caplog.set_level(logging.INFO)
    with TestClient(create_app()):
        pass
    lines = [r.getMessage() for r in caplog.records if r.getMessage().startswith("AI:")]
    assert lines == ["AI: not configured (OPENAI_API_KEY missing)"]


def test_installed_sdk_takes_max_completion_tokens_and_requirements_pin():
    # openai>=1.58.0 is the first release whose create() takes both max_completion_tokens
    # and reasoning_effort; <4 keeps the next major release out until it is reviewed.
    create = openai.OpenAI(api_key="sk-test").chat.completions.create
    assert {"max_completion_tokens", "reasoning_effort"} <= set(inspect.signature(create).parameters)
    lines = [line.strip() for line in REQUIREMENTS.read_text().splitlines()]
    assert "openai>=1.58.0,<4" in lines


# --- T3: the call, error mapping, retries and the deadline ------------------------------


def _response(status: int, headers: dict | None = None):
    return SDK_HTTP.Response(status, headers=headers or {}, request=SDK_HTTP.Request("POST", URL))


def sdk_error(kind: str, **kw) -> Exception:
    """One SDK exception of each class F §2.8 maps."""
    request = SDK_HTTP.Request("POST", URL)
    if kind == "timeout":
        return openai.APITimeoutError(request=request)
    if kind == "connection":
        return openai.APIConnectionError(request=request)
    classes = {"rate_limit": (openai.RateLimitError, 429), "auth": (openai.AuthenticationError, 401),
               "permission": (openai.PermissionDeniedError, 403),
               "bad_request": (openai.BadRequestError, 400), "not_found": (openai.NotFoundError, 404),
               "server": (openai.InternalServerError, 500),
               "status_502": (openai.APIStatusError, 502)}
    cls, status = classes[kind]
    body = {"code": kw["code"]} if "code" in kw else None
    return cls(f"upstream said {kind}", response=_response(status, kw.get("headers")), body=body)


class FakeSDK:
    """Stands in for openai.OpenAI: create() records kwargs and answers from `script`."""

    def __init__(self, *script):
        self.script = list(script) or ['{"ok": true}']
        self.calls: list[dict] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        item = self.script.pop(0) if len(self.script) > 1 else self.script[0]
        if isinstance(item, BaseException):
            raise item
        usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=item))],
                               usage=usage)


class RecordingSemaphore:
    def __init__(self, free: bool = True):
        self.free = free
        self.waits: list = []

    def acquire(self, blocking=True, timeout=None):
        self.waits.append(timeout if blocking else "no-wait")
        return self.free

    def release(self):
        pass


def setup(*script, clock=None, **settings_overrides):
    sdk, sleeps = FakeSDK(*script), []
    ai.configure_for_tests(settings=settings(**settings_overrides), sdk_client=sdk,
                           clock=clock or FakeClock().now, sleep=sleeps.append)
    return sdk, sleeps


def test_real_sdk_client_is_built_with_max_retries_zero():
    ai.configure_for_tests(settings=settings(timeout_seconds=30.0))
    client = ai._current().sdk_client
    assert isinstance(client, openai.OpenAI)
    assert client.max_retries == 0


def test_complete_sends_tokens_json_mode_and_temperature_only_when_set():
    sdk, _ = setup('{"opening": ["H1"]}')
    assert ai.complete(MESSAGES, max_completion_tokens=1200, json_mode=True) == '{"opening": ["H1"]}'
    (call,) = sdk.calls
    assert call["model"] == "test-model"
    assert call["messages"] == MESSAGES
    assert call["max_completion_tokens"] == 1200
    assert "max_tokens" not in call
    assert call["response_format"] == {"type": "json_object"}
    assert "temperature" not in call
    assert (call["timeout"].read, call["timeout"].connect) == (30.0, 5.0)

    sdk, _ = setup("plain", temperature=0.3)
    ai.complete(MESSAGES, max_completion_tokens=10)
    (call,) = sdk.calls
    assert call["temperature"] == 0.3
    assert "response_format" not in call


def test_complete_sends_reasoning_effort_only_when_set():
    sdk, _ = setup("plain")
    ai.complete(MESSAGES, max_completion_tokens=10)
    assert "reasoning_effort" not in sdk.calls[0]
    sdk, _ = setup("plain", reasoning_effort="minimal")
    ai.complete(MESSAGES, max_completion_tokens=10)
    assert sdk.calls[0]["reasoning_effort"] == "minimal"


def test_not_configured_raises_before_any_call():
    sdk, _ = setup("unused", model="")
    with pytest.raises(NotConfigured) as caught:
        ai.complete(MESSAGES, max_completion_tokens=10)
    assert (caught.value.code, caught.value.message) == ("ai_not_configured", ai.NOT_CONFIGURED_MESSAGE)
    assert sdk.calls == []


def test_every_sdk_error_class_maps_to_its_code():
    expected = {"timeout": (UpstreamTimeout, "ai_timeout", ai.TIMEOUT_MESSAGE),
                "rate_limit": (Busy, "ai_busy", ai.BUSY_MESSAGE),
                "auth": (NotConfigured, "ai_not_configured", ai.NOT_CONFIGURED_MESSAGE),
                "permission": (NotConfigured, "ai_not_configured", ai.NOT_CONFIGURED_MESSAGE),
                "bad_request": (UpstreamError, "ai_upstream_error", ai.UPSTREAM_MESSAGE),
                "connection": (UpstreamError, "ai_upstream_error", ai.UPSTREAM_MESSAGE),
                "server": (UpstreamError, "ai_upstream_error", ai.UPSTREAM_MESSAGE)}
    for kind, (cls, code, message) in expected.items():
        setup(sdk_error(kind), max_retries=0)
        with pytest.raises(cls) as caught:
            ai.complete(MESSAGES, max_completion_tokens=10)
        assert (caught.value.code, caught.value.message) == (code, message), kind
        assert "upstream said" not in caught.value.message            # never the SDK's text

    # A reply with no choices is the upstream's fault, not a 500.
    sdk, _ = setup(max_retries=0)
    sdk.chat.completions.create = lambda **kwargs: SimpleNamespace(choices=[], usage=None)
    with pytest.raises(UpstreamError) as caught:
        ai.complete(MESSAGES, max_completion_tokens=10)
    assert caught.value.code == "ai_upstream_error"


def test_api_timeout_error_is_ai_timeout_not_its_base_class():
    # APITimeoutError subclasses APIConnectionError, which maps to ai_upstream_error.
    assert issubclass(openai.APITimeoutError, openai.APIConnectionError)
    setup(sdk_error("timeout"), sdk_error("timeout"))
    with pytest.raises(UpstreamTimeout) as caught:
        ai.complete(MESSAGES, max_completion_tokens=10)
    assert caught.value.code == "ai_timeout"


def test_insufficient_quota_is_not_configured_after_one_attempt(caplog):
    caplog.set_level(logging.INFO, logger="integrations.openai_client")
    sdk, sleeps = setup(sdk_error("rate_limit", code="insufficient_quota"), '{"ok": true}')
    with pytest.raises(NotConfigured) as caught:
        ai.complete(MESSAGES, max_completion_tokens=10)
    assert caught.value.code == "ai_not_configured"
    assert len(sdk.calls) == 1 and sleeps == []
    assert ("ERROR", "AI: quota exhausted (insufficient_quota)") in [
        (r.levelname, r.getMessage()) for r in caplog.records]


def test_a_model_openai_does_not_offer_is_not_configured(caplog):
    caplog.set_level(logging.INFO, logger="integrations.openai_client")
    for error in (sdk_error("not_found"), sdk_error("not_found", code="model_not_found"),
                  sdk_error("bad_request", code="model_not_found")):
        caplog.clear()
        sdk, sleeps = setup(error, '{"ok": true}', model="retired-model")
        with pytest.raises(NotConfigured) as caught:
            ai.complete(MESSAGES, max_completion_tokens=10)
        assert (caught.value.code, caught.value.message) == ("ai_not_configured", ai.NOT_CONFIGURED_MESSAGE)
        assert len(sdk.calls) == 1 and sleeps == []
        assert ("ERROR", "AI: model not available (OPENAI_MODEL=retired-model)") in [
            (r.levelname, r.getMessage()) for r in caplog.records]


def test_a_500_then_success_retries_once():
    sdk, sleeps = setup(sdk_error("server"), '{"ok": true}')
    assert ai.complete(MESSAGES, max_completion_tokens=10) == '{"ok": true}'
    assert len(sdk.calls) == 2
    assert sleeps == [1.0]                                       # no Retry-After: 1 s


def test_retry_after_60_waits_only_2_seconds():
    sdk, sleeps = setup(sdk_error("rate_limit", headers={"retry-after": "60"}), '{"ok": true}')
    assert ai.complete(MESSAGES, max_completion_tokens=10) == '{"ok": true}'
    assert sleeps == [2.0]


def test_bad_request_is_never_retried_and_retries_stop_at_the_maximum():
    sdk, sleeps = setup(sdk_error("bad_request"), '{"ok": true}')
    with pytest.raises(UpstreamError):
        ai.complete(MESSAGES, max_completion_tokens=10)
    assert len(sdk.calls) == 1 and sleeps == []

    sdk, sleeps = setup(sdk_error("status_502"), sdk_error("server"), '{"ok": true}')
    with pytest.raises(UpstreamError):
        ai.complete(MESSAGES, max_completion_tokens=10)
    assert len(sdk.calls) == 2 and sleeps == [1.0]               # OPENAI_MAX_RETRIES = 1


def test_the_deadline_shrinks_each_attempt_and_skips_a_late_retry():
    clock = FakeClock()
    sdk, sleeps = setup('{"ok": true}', clock=clock.now)
    ai.complete(MESSAGES, max_completion_tokens=10, deadline=clock.now() + 12.0)
    assert (sdk.calls[0]["timeout"].read, sdk.calls[0]["timeout"].connect) == (12.0, 5.0)

    def fail_late(**kwargs):            # the attempt uses up time until 4 s remain
        clock.advance(8.0)
        raise sdk_error("server")

    sdk, sleeps = setup(clock=clock.now)
    sdk.chat.completions.create = fail_late
    with pytest.raises(UpstreamError):
        ai.complete(MESSAGES, max_completion_tokens=10, deadline=clock.now() + 12.0)
    assert sleeps == []                                          # 4 s - 1 s backoff < 5 s: no retry


def test_a_deadline_already_passed_times_out_with_one_log_line(caplog):
    clock = FakeClock()
    sdk, _ = setup('{"ok": true}', clock=clock.now)
    with pytest.raises(UpstreamTimeout):
        ai.complete(MESSAGES, max_completion_tokens=10, deadline=clock.now() - 1.0)
    assert sdk.calls == []
    assert "outcome=ai_timeout" in caplog.text


def test_the_slot_wait_is_bounded_by_the_deadline():
    clock = FakeClock()
    busy = RecordingSemaphore(free=False)
    sdk = FakeSDK()
    ai.configure_for_tests(settings=settings(), sdk_client=sdk, semaphore=busy, clock=clock.now)
    with pytest.raises(Busy) as caught:
        ai.complete(MESSAGES, max_completion_tokens=10, deadline=clock.now() + 5.5)
    assert (caught.value.code, caught.value.message) == ("ai_busy", ai.BUSY_MESSAGE)
    assert busy.waits == [pytest.approx(0.5)]                   # min(15, remaining - 5)
    with pytest.raises(Busy):
        ai.complete(MESSAGES, max_completion_tokens=10)         # no deadline: 15 s
    with pytest.raises(Busy):
        ai.complete(MESSAGES, max_completion_tokens=10, deadline=clock.now() + 3.0)
    assert busy.waits[1:] == [15.0, "no-wait"]
    assert sdk.calls == []


def test_a_real_semaphore_times_out_as_ai_busy():
    import threading

    slots = threading.BoundedSemaphore(1)
    slots.acquire()                                              # the one slot is taken
    clock = FakeClock()
    ai.configure_for_tests(settings=settings(), sdk_client=FakeSDK(), semaphore=slots, clock=clock.now)
    with pytest.raises(Busy):
        ai.complete(MESSAGES, max_completion_tokens=10, deadline=clock.now() + 5.05)
    slots.release()


# --- slice 4a: a per-call attempt timeout (slice 4 spec, Risks 1) ------------------------


def test_a_call_can_set_its_own_attempt_timeout_inside_the_deadline():
    """Prayers of the People: 60 s attempts inside /liturgy/generate's 80 s deadline."""
    clock = FakeClock()
    sdk, sleeps = setup(sdk_error("server"), '{"ok": true}', clock=clock.now)
    assert ai.complete(MESSAGES, max_completion_tokens=10, timeout_seconds=60.0,
                       deadline=clock.now() + 80.0) == '{"ok": true}'
    assert [(c["timeout"].read, c["timeout"].connect) for c in sdk.calls] == [(60.0, 5.0), (60.0, 5.0)]
    assert sleeps == [1.0]                                       # a quick failure is retried
    reads = []

    def time_out(**kwargs):                                     # each attempt runs to its timeout
        reads.append(kwargs["timeout"].read)
        clock.advance(kwargs["timeout"].read)
        raise sdk_error("timeout")

    # After a 15 s slot wait, a 60 s timeout leaves 5 s: no retry. Straight
    # away, it leaves 20 s: one retry, capped by the deadline.
    for waited, expected in ((15.0, [60.0]), (0.0, [60.0, 20.0])):
        sdk, _ = setup(clock=clock.now)
        sdk.chat.completions.create = time_out
        reads.clear()
        deadline = clock.now() + 80.0
        clock.advance(waited)
        with pytest.raises(UpstreamTimeout):
            ai.complete(MESSAGES, max_completion_tokens=10, timeout_seconds=60.0, deadline=deadline)
        assert reads == expected, waited
    sdk, _ = setup('{"ok": true}')
    ai.complete(MESSAGES, max_completion_tokens=10)
    assert sdk.calls[0]["timeout"].read == 30.0                  # without it: the setting
    for bad in (0, -1.0):
        with pytest.raises(ValueError):
            ai.complete(MESSAGES, max_completion_tokens=10, timeout_seconds=bad)
    fake = ai.FakeAI(reply="ok")
    ai.set_ai_for_tests(fake)
    ai.complete(MESSAGES, max_completion_tokens=10, timeout_seconds=60.0)
    ai.complete(MESSAGES, max_completion_tokens=10)
    assert fake.calls[0]["timeout_seconds"] == 60.0 and "timeout_seconds" not in fake.calls[1]
