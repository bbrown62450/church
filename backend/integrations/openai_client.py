"""The one OpenAI client (F §2.8, with slice 3's refinements; S Backend 3.7).

- ai_settings(): OPENAI_API_KEY (stripped), OPENAI_MODEL (required, no
  default), OPENAI_TIMEOUT_SECONDS (30), OPENAI_MAX_RETRIES (1),
  OPENAI_MAX_CONCURRENCY (4), OPENAI_TEMPERATURE (unset),
  OPENAI_REASONING_EFFORT (unset). A missing key or model, or a key that is
  not ASCII, means "not configured".
- ai_available() and complete(messages, *, max_completion_tokens,
  json_mode=False, deadline=None) -> str. complete() always sends
  max_completion_tokens, sends response_format json_object in json_mode, and
  temperature and reasoning_effort only when they are set. It holds one of OPENAI_MAX_CONCURRENCY
  slots per call and retries itself (the SDK client has max_retries=0).
- log_startup_state(): the lifespan's one "AI: ..." line. The key is never
  logged, and no member ever sees configuration detail.
- FakeAI and set_ai_for_tests(): no test reaches OpenAI (F §5.3).

There is no hymn-specific code here. Callers that want their own wording for
ai_not_configured catch NotConfigured and raise their own (usecases.hymns).
No FastAPI, no Streamlit (tests/test_no_streamlit_in_core.py).
"""
from __future__ import annotations

import logging
import os
import re
import threading
import time
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Callable, Mapping, Optional, Sequence

import openai

from domain_errors import Busy, NotConfigured, UpstreamError, UpstreamTimeout

logger = logging.getLogger(__name__)

NOT_CONFIGURED_MESSAGE = "AI isn't set up on this app yet."
BUSY_MESSAGE = "The AI service is busy. Try again in a minute."
TIMEOUT_MESSAGE = "The AI took too long to answer. Try again."
UPSTREAM_MESSAGE = "The AI service had a problem. Try again."

SEMAPHORE_WAIT_SECONDS = 15.0      # F §2.8: waiting longer for a slot is ai_busy
DEADLINE_MARGIN_SECONDS = 5.0      # with a deadline: wait at most remaining - 5 s for a slot
MIN_RETRY_SECONDS = 5.0            # a retry starts only with at least this much time left
MAX_BACKOFF_SECONDS = 2.0          # min(Retry-After or 1 s, 2 s)
CONNECT_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True)
class AISettings:
    api_key: str = ""
    model: str = ""
    timeout_seconds: float = 30.0
    max_retries: int = 1
    max_concurrency: int = 4
    temperature: Optional[float] = None
    reasoning_effort: Optional[str] = None     # e.g. "minimal"; only for a reasoning model

    @property
    def problem(self) -> Optional[str]:
        """Why AI is not configured (for the startup log), or None when it is."""
        if not self.api_key:
            return "OPENAI_API_KEY missing"
        if not self.api_key.isascii():
            return "OPENAI_API_KEY is not ASCII"
        if not self.model:
            return "OPENAI_MODEL missing"
        return None


def _number(environ: Mapping[str, str], name: str, default, cast, minimum):
    raw = (environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        value = cast(raw)
    except ValueError:
        value = None
    if value is None or value < minimum:
        logger.warning("AI: %s=%r is not valid; using %s", name, raw, default)
        return default
    return value


def _reasoning_effort(environ: Mapping[str, str]) -> Optional[str]:
    raw = (environ.get("OPENAI_REASONING_EFFORT") or "").strip()
    if not raw:
        return None
    if not re.fullmatch(r"[a-z]+", raw.lower()):
        logger.warning("AI: %s=%r is not valid; using %s", "OPENAI_REASONING_EFFORT", raw, None)
        return None
    return raw.lower()


def load_settings(environ: Mapping[str, str] = os.environ) -> AISettings:
    temperature = _number(environ, "OPENAI_TEMPERATURE", None, float, 0.0)
    return AISettings(
        api_key=(environ.get("OPENAI_API_KEY") or "").strip(),
        model=(environ.get("OPENAI_MODEL") or "").strip(),
        timeout_seconds=_number(environ, "OPENAI_TIMEOUT_SECONDS", 30.0, float, 1.0),
        max_retries=_number(environ, "OPENAI_MAX_RETRIES", 1, int, 0),
        max_concurrency=_number(environ, "OPENAI_MAX_CONCURRENCY", 4, int, 1),
        temperature=temperature,
        reasoning_effort=_reasoning_effort(environ),
    )


@lru_cache
def ai_settings() -> AISettings:
    """The settings, read once per process (reset_for_tests clears them)."""
    return load_settings()


def log_startup_state() -> None:
    """Exactly one line (S Backend 3.7). Never the key."""
    settings = ai_settings()
    problem = settings.problem
    if problem is None:
        logger.info("AI: configured (model=%s)", settings.model)
    elif problem == "OPENAI_API_KEY is not ASCII":
        logger.error("AI: not configured (%s)", problem)
    else:
        logger.warning("AI: not configured (%s)", problem)


# --- the fake (tests) ----------------------------------------------------------


@dataclass
class FakeAI:
    """complete() records each call and returns `reply` (a str, or a callable
    taking the messages), or raises `error`. ai_available() returns `available`."""

    reply: Any = "{}"
    available: bool = True
    error: Optional[BaseException] = None
    calls: list[dict] = field(default_factory=list)

    def ai_available(self) -> bool:
        return self.available

    def complete(self, messages, *, max_completion_tokens: int, json_mode: bool = False,
                 deadline: Optional[float] = None) -> str:
        self.calls.append({"messages": [dict(m) for m in messages],
                           "max_completion_tokens": max_completion_tokens,
                           "json_mode": json_mode, "deadline": deadline})
        if self.error is not None:
            raise self.error
        return self.reply(messages) if callable(self.reply) else self.reply


_override: Optional[FakeAI] = None


def set_ai_for_tests(fake: Optional[FakeAI]) -> None:
    """Tests: route ai_available() and complete() to `fake` (None restores the real client)."""
    global _override
    _override = fake


# --- the real client -------------------------------------------------------------


class _State:
    """The SDK client, the concurrency slots, the clock and the sleep, for the current settings."""

    def __init__(self, settings: AISettings, *, sdk_client: Any = None, semaphore: Any = None,
                 clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep):
        self.settings = settings
        self._sdk_client = sdk_client
        self.semaphore = semaphore or threading.BoundedSemaphore(settings.max_concurrency)
        self.clock = clock
        self.sleep = sleep

    @property
    def sdk_client(self):
        if self._sdk_client is None:
            # max_retries=0: complete() retries itself (the SDK honors Retry-After
            # for up to 60 s while holding a slot; S Backend 3.7).
            self._sdk_client = openai.OpenAI(
                api_key=self.settings.api_key, max_retries=0,
                timeout=openai.Timeout(self.settings.timeout_seconds,
                                       connect=CONNECT_TIMEOUT_SECONDS))
        return self._sdk_client


_state: Optional[_State] = None
_state_lock = threading.Lock()


def _current() -> _State:
    global _state
    with _state_lock:
        if _state is None:
            _state = _State(ai_settings())
        return _state


def configure_for_tests(*, settings: Optional[AISettings] = None, sdk_client: Any = None,
                        semaphore: Any = None, clock: Optional[Callable[[], float]] = None,
                        sleep: Optional[Callable[[float], None]] = None) -> None:
    """Tests: the real complete() over a fake SDK client, clock, sleep and semaphore."""
    global _state
    with _state_lock:
        _state = _State(settings or ai_settings(), sdk_client=sdk_client, semaphore=semaphore,
                        clock=clock or time.monotonic, sleep=sleep or time.sleep)


def reset_for_tests() -> None:
    """Tests: no fake, settings read again from the environment, a new client and slots."""
    global _state, _override
    ai_settings.cache_clear()
    with _state_lock:
        _state = None
    _override = None


def ai_available() -> bool:
    if _override is not None:
        return _override.ai_available()
    return _current().settings.problem is None


def complete(messages: Sequence[Mapping[str, str]], *, max_completion_tokens: int,
             json_mode: bool = False, deadline: Optional[float] = None) -> str:
    """The reply's text. Raises NotConfigured, Busy, UpstreamTimeout or
    UpstreamError (F §2.8's codes, this module's messages); never an SDK error."""
    if _override is not None:
        return _override.complete(messages, max_completion_tokens=max_completion_tokens,
                                  json_mode=json_mode, deadline=deadline)
    return _complete(_current(), messages, max_completion_tokens, json_mode, deadline)



def _complete(state: _State, messages, max_completion_tokens: int, json_mode: bool,
              deadline: Optional[float]) -> str:
    """Task 3 replaces this with the call, the error mapping, the retries and the deadline."""
    raise NotConfigured(NOT_CONFIGURED_MESSAGE, code="ai_not_configured")
