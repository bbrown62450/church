"""integrations.openai_client (F §2.8 as refined by slice 3; S Backend 3.7,
Testing `test_openai_client.py`; AC5, AC6, AC18).

No test reaches OpenAI: the settings come from a dict, and the SDK client is
a stand-in whose chat.completions.create records each call and answers from a
script of replies and SDK exceptions (built with the SDK's own HTTP types).
"""
import inspect
import logging
from pathlib import Path

import openai
import pytest

from domain_errors import Busy
from integrations import openai_client as ai

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
