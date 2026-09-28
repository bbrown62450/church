"""integrations.budget: process-wide upstream budgets (S "Upstream budgets", Testing; AC13; slice 2a).

Every test runs on the `budget_clock` FakeClock (conftest.py), which never
moves unless a test advances it.
"""
import threading
import time

import pytest

from integrations import budget


def _acquired_at_pace(clock, seconds_between: float, attempts: int) -> int:
    """How many ESV acquires succeed, one every `seconds_between`, before the first refusal."""
    for count in range(attempts):
        if not budget.try_acquire("esv"):
            return count
        clock.advance(seconds_between)
    return attempts


def test_bible_api_fifteen_then_sixteenth_fails_then_refills(budget_clock):
    assert [budget.try_acquire("bible_api") for _ in range(16)] == [True] * 15 + [False]
    budget_clock.advance(1)                      # half a token: one takes 2 s (30 s / 15)
    assert budget.try_acquire("bible_api") is False
    budget_clock.advance(1)
    assert budget.try_acquire("bible_api") is True
    assert budget.try_acquire("bible_api") is False
    budget_clock.advance(30)
    assert [budget.try_acquire("bible_api") for _ in range(16)] == [True] * 15 + [False]
    budget.set_clock_for_tests(budget_clock.now)         # the hook forgets the spent budget
    assert all(budget.try_acquire("bible_api") for _ in range(15))
    budget.reset_for_tests()                             # ...and reset restores the real clock
    assert budget._clock is time.monotonic


def test_esv_minute_rule(budget_clock):
    assert [budget.try_acquire("esv") for _ in range(61)] == [True] * 60 + [False]
    budget_clock.advance(1)                      # 60 per minute: one token a second
    assert budget.try_acquire("esv") is True
    assert budget.try_acquire("esv") is False


def test_esv_hour_rule(budget_clock):
    # One a second never runs out the minute rule (it refills one a second), so
    # the hour rule stops it: before call m it holds 1000 - (m - 1) * (1 - 1000/3600).
    assert _acquired_at_pace(budget_clock, 1.0, 5_000) == 1_384
    budget_clock.advance(3.6)                    # one hour token: 3 600 s / 1 000
    assert budget.try_acquire("esv") is True


def test_esv_day_rule(budget_clock):
    # One every 4 s never runs out the minute or the hour rule, so the day rule
    # stops it: before call m it holds 5000 - (m - 1) * (1 - 4 * 5000/86400).
    assert _acquired_at_pace(budget_clock, 4.0, 10_000) == 6_505
    budget_clock.advance(17.28)                  # one day token: 86 400 s / 5 000
    assert budget.try_acquire("esv") is True


def test_failed_acquire_takes_nothing(budget_clock):
    assert all(budget.try_acquire("esv") for _ in range(60))
    assert not any(budget.try_acquire("esv") for _ in range(1_000))   # the minute rule refuses...
    budget_clock.advance(60)
    assert all(budget.try_acquire("esv") for _ in range(60))        # ...and the hour rule lost nothing


def test_threads_get_exactly_fifteen(budget_clock):
    start = threading.Barrier(32)
    results: list[bool] = []
    results_lock = threading.Lock()

    def acquire() -> None:
        start.wait(timeout=10)
        got = budget.try_acquire("bible_api")
        with results_lock:
            results.append(got)

    threads = [threading.Thread(target=acquire) for _ in range(32)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    assert len(results) == 32
    assert results.count(True) == 15


def test_unknown_upstream_raises(budget_clock):
    assert budget.BUDGETS == {                           # S "Upstream budgets"
        "bible_api": ((15, 30.0),),
        "esv": ((60, 60.0), (1_000, 3_600.0), (5_000, 86_400.0)),
    }
    with pytest.raises(KeyError):
        budget.try_acquire("openai")
