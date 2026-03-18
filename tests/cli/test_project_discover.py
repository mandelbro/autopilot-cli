"""Tests for project register and project discover CLI commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from autopilot.cli.app import app
from autopilot.core.project import ProjectRegistry

runner = CliRunner()

SAMPLE_INDEX = """\
## Overall Project Task Summary

- **Total Tasks**: 10
- **Pending**: 7
- **Complete**: 3
- **Total Points**: 30
- **Points Complete**: 9

## Project: Sample Project

- Task Source File: `docs/discovery/discovery.md`
- **Description**: A test project for discovery

## Task File Index

- `tasks/tasks-1.md`: Contains Tasks 000 - 009 (10 tasks, 30 points)
"""


def _make_task_project(base: Path, name: str) -> Path:
    """Create a minimal external project with tasks/tasks-index.md."""
    project = base / name
    project.mkdir(parents=True)
    tasks = project / "tasks"
    tasks.mkdir()
    (tasks / "tasks-index.md").write_text(SAMPLE_INDEX)
    return project


class TestProjectRegister:
    def test_register_external_project(self, tmp_path: Path) -> None:
        project_path = _make_task_project(tmp_path, "ext-project")
        global_dir = tmp_path / "global"

        with patch("autopilot.core.project.get_global_dir", return_value=global_dir):
            result = runner.invoke(
                app, ["project", "register", "--path", str(project_path)]
            )

        assert result.exit_code == 0
        assert "ext-project" in result.output

        registry = ProjectRegistry(global_dir=global_dir)
        proj = registry.find_by_name("ext-project")
        assert proj is not None
        assert proj.external is True

    def test_register_with_custom_name(self, tmp_path: Path) -> None:
        project_path = _make_task_project(tmp_path, "raw-dir")
        global_dir = tmp_path / "global"

        with patch("autopilot.core.project.get_global_dir", return_value=global_dir):
            result = runner.invoke(
                app,
                [
                    "project",
                    "register",
                    "--path",
                    str(project_path),
                    "--name",
                    "my-custom-name",
                ],
            )

        assert result.exit_code == 0
        registry = ProjectRegistry(global_dir=global_dir)
        proj = registry.find_by_name("my-custom-name")
        assert proj is not None

    def test_register_nonexistent_path(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app,
            ["project", "register", "--path", str(tmp_path / "nonexistent")],
        )
        assert result.exit_code != 0

    def test_register_no_tasks_dir(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()
        result = runner.invoke(
            app, ["project", "register", "--path", str(empty)]
        )
        assert result.exit_code != 0


class TestProjectDiscover:
    def test_discover_finds_projects(self, tmp_path: Path) -> None:
        _make_task_project(tmp_path, "proj-a")
        _make_task_project(tmp_path, "proj-b")
        (tmp_path / "not-a-project").mkdir()

        result = runner.invoke(
            app, ["project", "discover", "--path", str(tmp_path)]
        )
        assert result.exit_code == 0
        assert "proj-a" in result.output
        assert "proj-b" in result.output

    def test_discover_empty_workspace(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app, ["project", "discover", "--path", str(tmp_path)]
        )
        assert result.exit_code == 0
        assert "no task projects" in result.output.lower()

    def test_discover_and_register(self, tmp_path: Path) -> None:
        _make_task_project(tmp_path, "proj-x")
        global_dir = tmp_path / "global"

        with patch("autopilot.core.project.get_global_dir", return_value=global_dir):
            result = runner.invoke(
                app,
                [
                    "project",
                    "discover",
                    "--path",
                    str(tmp_path),
                    "--register",
                ],
            )

        assert result.exit_code == 0
        registry = ProjectRegistry(global_dir=global_dir)
        proj = registry.find_by_name("proj-x")
        assert proj is not None
        assert proj.external is True
