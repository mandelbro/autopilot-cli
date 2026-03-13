"""Tests for circuit breaker pattern (Task 033)."""

from __future__ import annotations

from autopilot.orchestration.circuit_breaker import CircuitBreaker


class TestCircuitBreakerTripping:
    def test_trips_after_consecutive_limit(self) -> None:
        cb = CircuitBreaker(consecutive_limit=2)
        assert cb.is_tripped() is False

        cb.record_failure("timeout")
        assert cb.is_tripped() is False

        cb.record_failure("timeout")
        assert cb.is_tripped() is True

    def test_does_not_trip_below_limit(self) -> None:
        cb = CircuitBreaker(consecutive_limit=3)
        cb.record_failure("error")
        cb.record_failure("error")
        assert cb.is_tripped() is False

    def test_trips_at_exactly_limit(self) -> None:
        cb = CircuitBreaker(consecutive_limit=1)
        cb.record_failure("error")
        assert cb.is_tripped() is True


class TestCircuitBreakerReset:
    def test_success_resets_consecutive_count(self) -> None:
        cb = CircuitBreaker(consecutive_limit=2)
        cb.record_failure("error")
        cb.record_success()
        cb.record_failure("error")
        assert cb.is_tripped() is False

    def test_manual_reset(self) -> None:
        cb = CircuitBreaker(consecutive_limit=2)
        cb.record_failure("error")
        cb.record_failure("error")
        assert cb.is_tripped() is True

        cb.reset()
        assert cb.is_tripped() is False


class TestCircuitBreakerState:
    def test_state_tracks_totals(self) -> None:
        cb = CircuitBreaker(consecutive_limit=3)
        cb.record_success()
        cb.record_success()
        cb.record_failure("timeout")
        cb.record_success()
        cb.record_failure("error")

        state = cb.state()
        assert state.total_successes == 3
        assert state.total_failures == 2
        assert state.consecutive_failures == 1
        assert state.is_tripped is False
        assert state.consecutive_limit == 3
        assert state.last_failure_error == "error"
        assert state.last_failure_time is not None

    def test_initial_state(self) -> None:
        cb = CircuitBreaker(consecutive_limit=2)
        state = cb.state()
        assert state.consecutive_failures == 0
        assert state.total_failures == 0
        assert state.total_successes == 0
        assert state.is_tripped is False
        assert state.last_failure_time is None
        assert state.last_failure_error == ""

    def test_state_after_reset_preserves_totals(self) -> None:
        cb = CircuitBreaker(consecutive_limit=2)
        cb.record_failure("error")
        cb.record_failure("error")
        cb.reset()

        state = cb.state()
        assert state.consecutive_failures == 0
        assert state.total_failures == 2  # totals preserved
        assert state.is_tripped is False
