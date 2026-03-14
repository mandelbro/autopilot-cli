"""Tests for discovery CLI commands (Task 078)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from typer.testing import CliRunner

from autopilot.cli.app import app

if TYPE_CHECKING:
    from pathlib import Path

runner = CliRunner()


class TestPlanDiscover:
    def test_discover_runs_or_fails_gracefully(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app, ["plan", "discover", "myproject", "auth"], catch_exceptions=False
        )
        # Either succeeds (if .autopilot exists in cwd) or fails with error
        if result.exit_code != 0:
            assert "No .autopilot" in result.output

    def test_discover_help(self) -> None:
        result = runner.invoke(app, ["plan", "discover", "--help"])
        assert result.exit_code == 0
        assert "discover" in result.output.lower()


class TestPlanTasks:
    def test_tasks_missing_discovery_file(self) -> None:
        result = runner.invoke(
            app,
            ["plan", "tasks", "--from-discovery", "/nonexistent/file.md"],
            catch_exceptions=False,
        )
        assert result.exit_code == 1

    def test_tasks_from_discovery(self, tmp_path: Path) -> None:
        # Create a minimal discovery document
        discovery_file = tmp_path / "test-discovery.md"
        discovery_file.write_text(
            "# Test Discovery\n\n"
            "Some description.\n\n"
            "## Phase 1: Foundation\n\n"
            "- Build core module\n"
            "- Add configuration\n\n"
            "## Phase 2: Features\n\n"
            "- Implement feature A\n"
            "- Implement feature B\n"
        )
        output_dir = tmp_path / "tasks"
        result = runner.invoke(
            app,
            [
                "plan",
                "tasks",
                "--from-discovery",
                str(discovery_file),
                "--output",
                str(output_dir),
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "Generated 4 tasks" in result.output
        assert (output_dir / "tasks-index.md").exists()

    def test_tasks_help(self) -> None:
        result = runner.invoke(app, ["plan", "tasks", "--help"])
        assert result.exit_code == 0
        # Rich may inject ANSI escapes into option names; check for key parts
        assert "discovery" in result.output.lower()


class TestPlanEstimate:
    def test_estimate_command(self) -> None:
        result = runner.invoke(app, ["plan", "estimate"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "Estimation" in result.output

    def test_estimate_help(self) -> None:
        result = runner.invoke(app, ["plan", "estimate", "--help"])
        assert result.exit_code == 0


class TestPlanShow:
    def test_show_runs_or_fails_gracefully(self) -> None:
        result = runner.invoke(app, ["plan", "show"], catch_exceptions=False)
        # Either shows planning state or fails with no .autopilot error
        if result.exit_code != 0:
            assert "No .autopilot" in result.output
        else:
            assert "Planning State" in result.output

    def test_show_help(self) -> None:
        result = runner.invoke(app, ["plan", "show", "--help"])
        assert result.exit_code == 0
