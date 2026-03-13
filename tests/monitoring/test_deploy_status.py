"""Tests for the DeployStatusWriter (Task 053)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from autopilot.monitoring.deploy_status import DeployStatusWriter
from autopilot.monitoring.health_checker import HealthCheckResult


def _healthy_result(
    name: str = "api", endpoint: str = "http://localhost/health"
) -> HealthCheckResult:
    return HealthCheckResult(
        service_name=name,
        endpoint=endpoint,
        status_code=200,
        response_time=0.05,
        healthy=True,
    )


def _unhealthy_result(name: str = "api", error: str = "Connection refused") -> HealthCheckResult:
    return HealthCheckResult(
        service_name=name,
        endpoint="http://localhost/health",
        status_code=0,
        response_time=0.0,
        healthy=False,
        error=error,
    )


class TestDeployStatusWriter:
    def test_creates_board_file_if_missing(self, tmp_path: Path) -> None:
        board = tmp_path / "project-board.md"
        writer = DeployStatusWriter()
        writer.update_board(board, [_healthy_result()])

        assert board.exists()
        content = board.read_text()
        assert "## Deployment Status" in content
        assert "| api |" in content

    def test_table_contains_healthy_status(self, tmp_path: Path) -> None:
        board = tmp_path / "project-board.md"
        writer = DeployStatusWriter()
        writer.update_board(board, [_healthy_result()])

        content = board.read_text()
        assert "healthy" in content

    def test_table_contains_unhealthy_status(self, tmp_path: Path) -> None:
        board = tmp_path / "project-board.md"
        writer = DeployStatusWriter()
        writer.update_board(board, [_unhealthy_result()])

        content = board.read_text()
        assert "unhealthy" in content
        assert "Connection refused" in content

    def test_replaces_existing_section(self, tmp_path: Path) -> None:
        board = tmp_path / "project-board.md"
        board.write_text(
            "# Project Board\n\n## Sprint Info\n\nSprint 1\n\n"
            "## Deployment Status\n\nOLD DATA\n\n## Active Work\n\nTasks\n"
        )
        writer = DeployStatusWriter()
        writer.update_board(board, [_healthy_result("web")])

        content = board.read_text()
        assert "OLD DATA" not in content
        assert "| web |" in content
        assert "## Sprint Info" in content
        assert "## Active Work" in content

    def test_appends_section_if_missing(self, tmp_path: Path) -> None:
        board = tmp_path / "project-board.md"
        board.write_text("# Project Board\n\n## Sprint Info\n\nSprint 1\n")

        writer = DeployStatusWriter()
        writer.update_board(board, [_healthy_result()])

        content = board.read_text()
        assert "## Sprint Info" in content
        assert "## Deployment Status" in content

    def test_multiple_services_in_table(self, tmp_path: Path) -> None:
        board = tmp_path / "project-board.md"
        results = [
            _healthy_result("web", "http://web/health"),
            _unhealthy_result("api", "timeout"),
        ]
        writer = DeployStatusWriter()
        writer.update_board(board, results)

        content = board.read_text()
        assert "| web |" in content
        assert "| api |" in content
        assert "healthy" in content
        assert "unhealthy" in content

    def test_empty_results_still_writes_headers(self, tmp_path: Path) -> None:
        board = tmp_path / "project-board.md"
        writer = DeployStatusWriter()
        writer.update_board(board, [])

        content = board.read_text()
        assert "## Deployment Status" in content
        assert "| Service |" in content

    def test_groups_endpoints_by_service(self, tmp_path: Path) -> None:
        board = tmp_path / "project-board.md"
        results = [
            _healthy_result("api", "http://api/health"),
            _healthy_result("api", "http://api/ready"),
        ]
        writer = DeployStatusWriter()
        writer.update_board(board, results)

        content = board.read_text()
        lines = [line for line in content.splitlines() if "| api |" in line]
        assert len(lines) == 1
        assert "http://api/health" in lines[0]
        assert "http://api/ready" in lines[0]
