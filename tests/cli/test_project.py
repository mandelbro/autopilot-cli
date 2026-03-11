"""Tests for autopilot.cli.project (Task 010)."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003
from unittest.mock import patch

from typer.testing import CliRunner

from autopilot.cli.app import app

runner = CliRunner()


class TestInitCommand:
    def test_init_creates_project(self, tmp_path: Path) -> None:
        with patch("autopilot.core.project.get_global_dir", return_value=tmp_path / "global"):
            result = runner.invoke(
                app,
                ["init", "--name", "test-proj", "--type", "python", "--root", str(tmp_path)],
            )
            assert result.exit_code == 0
            assert (tmp_path / ".autopilot").is_dir()
            assert (tmp_path / ".autopilot" / "config.yaml").exists()

    def test_init_shows_success(self, tmp_path: Path) -> None:
        with patch("autopilot.core.project.get_global_dir", return_value=tmp_path / "global"):
            result = runner.invoke(
                app,
                ["init", "--name", "my-app", "--type", "python", "--root", str(tmp_path)],
            )
            assert result.exit_code == 0
            assert "my-app" in result.output

    def test_init_fails_if_exists(self, tmp_path: Path) -> None:
        (tmp_path / ".autopilot").mkdir()
        result = runner.invoke(
            app,
            ["init", "--name", "test", "--type", "python", "--root", str(tmp_path)],
        )
        assert result.exit_code == 1

    def test_init_fails_for_bad_type(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app,
            ["init", "--name", "test", "--type", "ruby", "--root", str(tmp_path)],
        )
        assert result.exit_code == 1


class TestProjectListCommand:
    def test_project_list_stub(self) -> None:
        result = runner.invoke(app, ["project", "list"])
        assert result.exit_code == 0
