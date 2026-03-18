"""Tests for external project registration in ProjectRegistry."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from autopilot.core.project import ProjectRegistry, RegisteredProject


class TestRegisteredProjectExternalFields:
    def test_default_external_false(self) -> None:
        p = RegisteredProject(name="test", path="/tmp/test", type="python")
        assert p.external is False
        assert p.task_dir == ""

    def test_external_project_fields(self) -> None:
        p = RegisteredProject(
            name="ext",
            path="/tmp/ext",
            type="external",
            external=True,
            task_dir="/tmp/ext/tasks",
        )
        assert p.external is True
        assert p.task_dir == "/tmp/ext/tasks"


class TestProjectRegistryExternalProjects:
    def test_register_external_project(self, tmp_path: Path) -> None:
        registry = ProjectRegistry(global_dir=tmp_path)
        project = registry.register(
            "ext-proj",
            "/tmp/ext",
            "external",
            external=True,
            task_dir="/tmp/ext/tasks",
        )
        assert project.external is True
        assert project.task_dir == "/tmp/ext/tasks"

    def test_external_project_persists(self, tmp_path: Path) -> None:
        registry = ProjectRegistry(global_dir=tmp_path)
        registry.register(
            "ext-proj",
            "/tmp/ext",
            "external",
            external=True,
            task_dir="/tmp/ext/tasks",
        )
        # Load fresh
        registry2 = ProjectRegistry(global_dir=tmp_path)
        project = registry2.find_by_name("ext-proj")
        assert project is not None
        assert project.external is True
        assert project.task_dir == "/tmp/ext/tasks"

    def test_validate_all_skips_external_autopilot_check(self, tmp_path: Path) -> None:
        """External projects should not be flagged for missing .autopilot/ dir."""
        registry = ProjectRegistry(global_dir=tmp_path)
        ext_path = tmp_path / "ext-project"
        ext_path.mkdir()
        tasks_dir = ext_path / "tasks"
        tasks_dir.mkdir()

        registry.register(
            "ext",
            str(ext_path),
            "external",
            external=True,
            task_dir=str(tasks_dir),
        )
        issues = registry.validate_all()
        # Should not flag missing .autopilot/ for external projects
        autopilot_issues = [i for i in issues if ".autopilot" in i.issue]
        assert len(autopilot_issues) == 0

    def test_validate_all_flags_missing_task_dir_for_external(self, tmp_path: Path) -> None:
        """External projects with non-existent task_dir should be flagged."""
        registry = ProjectRegistry(global_dir=tmp_path)
        ext_path = tmp_path / "ext-project"
        ext_path.mkdir()

        registry.register(
            "ext",
            str(ext_path),
            "external",
            external=True,
            task_dir=str(ext_path / "nonexistent-tasks"),
        )
        issues = registry.validate_all()
        assert len(issues) == 1
        assert "task" in issues[0].issue.lower()

    def test_backward_compatible_load_no_external_field(self, tmp_path: Path) -> None:
        """Old projects.yaml without external/task_dir fields loads without error."""
        projects_file = tmp_path / "projects.yaml"
        data = [
            {
                "name": "old",
                "path": "/tmp/old",
                "type": "python",
                "registered_at": "2026-01-01",
                "last_active": "",
                "archived": False,
                "repository_url": "",
            }
        ]
        projects_file.write_text(yaml.dump(data))
        registry = ProjectRegistry(global_dir=tmp_path)
        projects = registry.load()
        assert len(projects) == 1
        assert projects[0].external is False
        assert projects[0].task_dir == ""
