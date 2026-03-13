"""Tests for the HealthChecker (Task 053)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from urllib.error import URLError

import pytest

from autopilot.core.config import MonitoredServiceConfig
from autopilot.monitoring.health_checker import HealthChecker, HealthCheckResult


class TestHealthCheckResult:
    def test_frozen(self) -> None:
        r = HealthCheckResult(
            service_name="api",
            endpoint="http://localhost/health",
            status_code=200,
            response_time=0.1,
            healthy=True,
        )
        with pytest.raises(AttributeError):
            r.healthy = False  # type: ignore[misc]

    def test_defaults(self) -> None:
        r = HealthCheckResult(
            service_name="api",
            endpoint="http://localhost/health",
            status_code=200,
            response_time=0.1,
            healthy=True,
        )
        assert r.error == ""


class TestHealthCheckerInterface:
    def test_check_service_returns_list(self) -> None:
        svc = MonitoredServiceConfig(id="svc-1", name="api", health_endpoints=[], staging_url="")
        checker = HealthChecker(timeout=5)
        results = checker.check_service(svc)
        assert isinstance(results, list)
        assert len(results) == 0

    def test_check_all_returns_list(self) -> None:
        checker = HealthChecker(timeout=5)
        results = checker.check_all({})
        assert isinstance(results, list)
        assert len(results) == 0


class TestHealthCheckerWithMockedHTTP:
    def test_healthy_endpoint(self) -> None:
        svc = MonitoredServiceConfig(
            id="svc-1",
            name="web",
            health_endpoints=["http://localhost:8000/health"],
        )
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("autopilot.monitoring.health_checker.urlopen", return_value=mock_resp):
            checker = HealthChecker(timeout=5)
            results = checker.check_service(svc)

        assert len(results) == 1
        assert results[0].healthy is True
        assert results[0].status_code == 200
        assert results[0].service_name == "web"
        assert results[0].endpoint == "http://localhost:8000/health"
        assert results[0].response_time >= 0

    def test_unhealthy_endpoint_500(self) -> None:
        svc = MonitoredServiceConfig(
            id="svc-1",
            name="api",
            health_endpoints=["http://localhost:8000/health"],
        )
        mock_resp = MagicMock()
        mock_resp.status = 500
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("autopilot.monitoring.health_checker.urlopen", return_value=mock_resp):
            checker = HealthChecker(timeout=5)
            results = checker.check_service(svc)

        assert len(results) == 1
        assert results[0].healthy is False
        assert results[0].status_code == 500

    def test_connection_error(self) -> None:
        svc = MonitoredServiceConfig(
            id="svc-1",
            name="api",
            health_endpoints=["http://localhost:9999/health"],
        )

        with patch(
            "autopilot.monitoring.health_checker.urlopen",
            side_effect=URLError("Connection refused"),
        ):
            checker = HealthChecker(timeout=5)
            results = checker.check_service(svc)

        assert len(results) == 1
        assert results[0].healthy is False
        assert results[0].status_code == 0
        assert "Connection refused" in results[0].error

    def test_timeout_error(self) -> None:
        svc = MonitoredServiceConfig(
            id="svc-1",
            name="api",
            health_endpoints=["http://localhost:9999/health"],
        )

        with patch(
            "autopilot.monitoring.health_checker.urlopen",
            side_effect=TimeoutError("timed out"),
        ):
            checker = HealthChecker(timeout=1)
            results = checker.check_service(svc)

        assert len(results) == 1
        assert results[0].healthy is False
        assert "timed out" in results[0].error

    def test_multiple_endpoints(self) -> None:
        svc = MonitoredServiceConfig(
            id="svc-1",
            name="api",
            health_endpoints=[
                "http://localhost:8000/health",
                "http://localhost:8000/ready",
            ],
        )
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("autopilot.monitoring.health_checker.urlopen", return_value=mock_resp):
            checker = HealthChecker(timeout=5)
            results = checker.check_service(svc)

        assert len(results) == 2

    def test_check_all_aggregates(self) -> None:
        services = {
            "web": MonitoredServiceConfig(
                id="svc-1",
                name="web",
                health_endpoints=["http://localhost:8000/health"],
            ),
            "api": MonitoredServiceConfig(
                id="svc-2",
                name="api",
                health_endpoints=["http://localhost:9000/health"],
            ),
        }
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("autopilot.monitoring.health_checker.urlopen", return_value=mock_resp):
            checker = HealthChecker(timeout=5)
            results = checker.check_all(services)

        assert len(results) == 2
        names = {r.service_name for r in results}
        assert names == {"web", "api"}
