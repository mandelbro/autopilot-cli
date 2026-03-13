"""Health endpoint checker for monitored services (Task 053).

Performs HTTP GET requests against configured health endpoints and
returns structured results for board reporting.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.error import URLError
from urllib.request import Request, urlopen

if TYPE_CHECKING:
    from autopilot.core.config import MonitoredServiceConfig


@dataclass(frozen=True)
class HealthCheckResult:
    """Result of a single health endpoint check."""

    service_name: str
    endpoint: str
    status_code: int
    response_time: float
    healthy: bool
    error: str = ""


class HealthChecker:
    """Checks HTTP health endpoints for monitored services.

    Args:
        timeout: HTTP request timeout in seconds.
    """

    def __init__(self, timeout: int = 10) -> None:
        self._timeout = timeout

    def check_service(
        self, service: MonitoredServiceConfig
    ) -> list[HealthCheckResult]:
        """Check all health endpoints for a single service."""
        results: list[HealthCheckResult] = []
        for endpoint in service.health_endpoints:
            results.append(self._check_endpoint(service.name, endpoint))
        return results

    def check_all(
        self, services: dict[str, MonitoredServiceConfig]
    ) -> list[HealthCheckResult]:
        """Check all endpoints across all monitored services."""
        results: list[HealthCheckResult] = []
        for service in services.values():
            results.extend(self.check_service(service))
        return results

    def _check_endpoint(self, name: str, endpoint: str) -> HealthCheckResult:
        """Perform an HTTP GET to a single health endpoint."""
        start = time.monotonic()
        try:
            req = Request(endpoint, method="GET")  # noqa: S310
            with urlopen(req, timeout=self._timeout) as resp:  # noqa: S310
                status_code = resp.status
                elapsed = time.monotonic() - start
                return HealthCheckResult(
                    service_name=name,
                    endpoint=endpoint,
                    status_code=status_code,
                    response_time=elapsed,
                    healthy=200 <= status_code < 400,
                )
        except URLError as exc:
            elapsed = time.monotonic() - start
            return HealthCheckResult(
                service_name=name,
                endpoint=endpoint,
                status_code=0,
                response_time=elapsed,
                healthy=False,
                error=str(exc.reason),
            )
        except (TimeoutError, OSError) as exc:
            elapsed = time.monotonic() - start
            return HealthCheckResult(
                service_name=name,
                endpoint=endpoint,
                status_code=0,
                response_time=elapsed,
                healthy=False,
                error=str(exc),
            )
