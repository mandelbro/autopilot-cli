"""Circuit breaker pattern (Task 033).

Aborts remaining dispatches after consecutive failures to minimize
wasted cycles and costs during outages per RFC Section 3.8.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class CircuitBreakerState:
    """Snapshot of circuit breaker state for monitoring."""

    consecutive_failures: int
    total_failures: int
    total_successes: int
    is_tripped: bool
    consecutive_limit: int
    last_failure_time: float | None
    last_failure_error: str


@dataclass
class CircuitBreaker:
    """Circuit breaker that trips after N consecutive failures.

    When tripped, ``is_tripped()`` returns True, signaling the scheduler
    to abort remaining dispatches in the current cycle.
    """

    consecutive_limit: int = 2

    _consecutive_failures: int = field(default=0, init=False, repr=False)
    _total_failures: int = field(default=0, init=False, repr=False)
    _total_successes: int = field(default=0, init=False, repr=False)
    _last_failure_time: float | None = field(default=None, init=False, repr=False)
    _last_failure_error: str = field(default="", init=False, repr=False)

    def record_success(self) -> None:
        """Record a successful dispatch, resetting consecutive failure count."""
        self._consecutive_failures = 0
        self._total_successes += 1

    def record_failure(self, error_type: str = "") -> None:
        """Record a failed dispatch, incrementing consecutive count."""
        self._consecutive_failures += 1
        self._total_failures += 1
        self._last_failure_time = time.time()
        self._last_failure_error = error_type

        if self._consecutive_failures >= self.consecutive_limit:
            _log.warning(
                "circuit_breaker_tripped: consecutive=%d limit=%d error=%s",
                self._consecutive_failures,
                self.consecutive_limit,
                error_type,
            )

    def is_tripped(self) -> bool:
        """Return True when the consecutive failure limit has been reached."""
        return self._consecutive_failures >= self.consecutive_limit

    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        self._consecutive_failures = 0
        self._last_failure_time = None
        self._last_failure_error = ""

    def state(self) -> CircuitBreakerState:
        """Return the current circuit breaker state for monitoring."""
        return CircuitBreakerState(
            consecutive_failures=self._consecutive_failures,
            total_failures=self._total_failures,
            total_successes=self._total_successes,
            is_tripped=self.is_tripped(),
            consecutive_limit=self.consecutive_limit,
            last_failure_time=self._last_failure_time,
            last_failure_error=self._last_failure_error,
        )
