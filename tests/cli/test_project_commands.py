"""Tests for project CLI commands: list, show, switch, config, archive (Task 011)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import yaml
from typer.testing import CliRunner

from autopilot.cli.app import app
from autopilot.core.project import ProjectRegistry

if TYPE_CHECKING:
    from pathlib import Path

runner = CliRunner()


def _setup_registry(tmp_path: Path) -> ProjectRegistry:
    """Create a registry with a test project."""
    gd = tmp_path / "global"
    gd.mkdir()
    registry = ProjectRegistry(global_dir=gd)
    proj_dir = tmp_path / "myproject"
    proj_dir.mkdir()
    (proj_dir / ".autopilot").mkdir()
    registry.register("test-proj", str(proj_dir), "python")
    return registry


class TestProjectListCommand:
    def test_list_empty(self, tmp_path: Path) -> None:
        gd = tmp_path / "global"
        gd.mkdir()
        with patch("autopilot.cli.project.ProjectRegistry", lambda: ProjectRegistry(global_dir=gd)):
            result = runner.invoke(app, ["project", "list"])
            assert result.exit_code == 0
            assert "No projects" in result.output

    def test_list_shows_projects(self, tmp_path: Path) -> None:
        _setup_registry(tmp_path)
        gd = tmp_path / "global"
        with patch("autopilot.cli.project.ProjectRegistry", lambda: ProjectRegistry(global_dir=gd)):
            result = runner.invoke(app, ["project", "list"])
            assert result.exit_code == 0
            assert "test-proj" in result.output

    def test_list_hides_archived(self, tmp_path: Path) -> None:
        gd = tmp_path / "global"
        gd.mkdir()
        registry = ProjectRegistry(global_dir=gd)
        registry.register("visible", "/tmp/visible", "python")
        registry.register("hidden", "/tmp/hidden", "python")
        registry.archive("hidden")

        with patch("autopilot.cli.project.ProjectRegistry", lambda: ProjectRegistry(global_dir=gd)):
            result = runner.invoke(app, ["project", "list"])
            assert "visible" in result.output
            assert "hidden" not in result.output


class TestProjectShowCommand:
    def test_show_by_name(self, tmp_path: Path) -> None:
        _setup_registry(tmp_path)
        gd = tmp_path / "global"
        with patch("autopilot.cli.project.ProjectRegistry", lambda: ProjectRegistry(global_dir=gd)):
            result = runner.invoke(app, ["project", "show", "test-proj"])
            assert result.exit_code == 0
            assert "test-proj" in result.output
            assert "python" in result.output

    def test_show_missing_project(self, tmp_path: Path) -> None:
        gd = tmp_path / "global"
        gd.mkdir()
        with patch("autopilot.cli.project.ProjectRegistry", lambda: ProjectRegistry(global_dir=gd)):
            result = runner.invoke(app, ["project", "show", "nonexistent"])
            assert result.exit_code == 1

    def test_show_no_name_no_active(self, tmp_path: Path) -> None:
        gd = tmp_path / "global"
        gd.mkdir()
        with (
            patch("autopilot.cli.project.ProjectRegistry", lambda: ProjectRegistry(global_dir=gd)),
            patch("autopilot.cli.project._get_active_project", return_value=""),
        ):
            result = runner.invoke(app, ["project", "show"])
            assert result.exit_code == 1

    def test_show_uses_active_project(self, tmp_path: Path) -> None:
        _setup_registry(tmp_path)
        gd = tmp_path / "global"
        with (
            patch("autopilot.cli.project.ProjectRegistry", lambda: ProjectRegistry(global_dir=gd)),
            patch("autopilot.cli.project._get_active_project", return_value="test-proj"),
        ):
            result = runner.invoke(app, ["project", "show"])
            assert result.exit_code == 0
            assert "test-proj" in result.output


class TestProjectSwitchCommand:
    def test_switch_success(self, tmp_path: Path) -> None:
        _setup_registry(tmp_path)
        gd = tmp_path / "global"
        active_file = tmp_path / "active"
        with (
            patch("autopilot.cli.project.ProjectRegistry", lambda: ProjectRegistry(global_dir=gd)),
            patch("autopilot.cli.project._get_active_project_path", return_value=active_file),
        ):
            result = runner.invoke(app, ["project", "switch", "test-proj"])
            assert result.exit_code == 0
            assert "Switched" in result.output
            assert active_file.read_text().strip() == "test-proj"

    def test_switch_missing_project(self, tmp_path: Path) -> None:
        gd = tmp_path / "global"
        gd.mkdir()
        with patch("autopilot.cli.project.ProjectRegistry", lambda: ProjectRegistry(global_dir=gd)):
            result = runner.invoke(app, ["project", "switch", "nope"])
            assert result.exit_code == 1

    def test_switch_archived_project(self, tmp_path: Path) -> None:
        gd = tmp_path / "global"
        gd.mkdir()
        registry = ProjectRegistry(global_dir=gd)
        registry.register("archived", "/tmp/archived", "python")
        registry.archive("archived")
        with patch("autopilot.cli.project.ProjectRegistry", lambda: ProjectRegistry(global_dir=gd)):
            result = runner.invoke(app, ["project", "switch", "archived"])
            assert result.exit_code == 1


class TestProjectConfigCommand:
    def test_config_show_all(self, tmp_path: Path) -> None:
        gd = tmp_path / "global"
        gd.mkdir()
        registry = ProjectRegistry(global_dir=gd)
        proj_dir = tmp_path / "cfgproj"
        proj_dir.mkdir()
        ap_dir = proj_dir / ".autopilot"
        ap_dir.mkdir()
        (ap_dir / "config.yaml").write_text(yaml.dump({"project": {"name": "cfgproj"}}))
        registry.register("cfgproj", str(proj_dir), "python")

        with (
            patch("autopilot.cli.project.ProjectRegistry", lambda: ProjectRegistry(global_dir=gd)),
            patch("autopilot.cli.project._get_active_project", return_value="cfgproj"),
        ):
            result = runner.invoke(app, ["project", "config"])
            assert result.exit_code == 0

    def test_config_get_key(self, tmp_path: Path) -> None:
        gd = tmp_path / "global"
        gd.mkdir()
        registry = ProjectRegistry(global_dir=gd)
        proj_dir = tmp_path / "cfgproj2"
        proj_dir.mkdir()
        ap_dir = proj_dir / ".autopilot"
        ap_dir.mkdir()
        (ap_dir / "config.yaml").write_text(yaml.dump({"project": {"name": "cfgproj2"}}))
        registry.register("cfgproj2", str(proj_dir), "python")

        with (
            patch("autopilot.cli.project.ProjectRegistry", lambda: ProjectRegistry(global_dir=gd)),
            patch("autopilot.cli.project._get_active_project", return_value="cfgproj2"),
        ):
            result = runner.invoke(app, ["project", "config", "project.name"])
            assert result.exit_code == 0
            assert "cfgproj2" in result.output

    def test_config_no_active_project(self, tmp_path: Path) -> None:
        with patch("autopilot.cli.project._get_active_project", return_value=""):
            result = runner.invoke(app, ["project", "config"])
            assert result.exit_code == 1


class TestProjectArchiveCommand:
    def test_archive_success(self, tmp_path: Path) -> None:
        _setup_registry(tmp_path)
        gd = tmp_path / "global"
        with patch("autopilot.cli.project.ProjectRegistry", lambda: ProjectRegistry(global_dir=gd)):
            result = runner.invoke(app, ["project", "archive", "test-proj"])
            assert result.exit_code == 0
            assert "archived" in result.output

    def test_archive_missing_project(self, tmp_path: Path) -> None:
        gd = tmp_path / "global"
        gd.mkdir()
        with patch("autopilot.cli.project.ProjectRegistry", lambda: ProjectRegistry(global_dir=gd)):
            result = runner.invoke(app, ["project", "archive", "nope"])
            assert result.exit_code == 1
