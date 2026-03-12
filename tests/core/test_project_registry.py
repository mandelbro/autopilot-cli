"""Tests for ProjectRegistry (Task 012)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from autopilot.core.project import (
    ProjectRegistry,
    RegisteredProject,
    RegistryIssue,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestProjectRegistry:
    def test_load_empty(self, tmp_path: Path) -> None:
        registry = ProjectRegistry(global_dir=tmp_path)
        assert registry.load() == []

    def test_register_and_load(self, tmp_path: Path) -> None:
        registry = ProjectRegistry(global_dir=tmp_path)
        result = registry.register("my-app", "/tmp/my-app", "python")
        assert isinstance(result, RegisteredProject)
        assert result.name == "my-app"
        assert result.path == "/tmp/my-app"
        assert result.type == "python"
        assert result.archived is False

        loaded = registry.load()
        assert len(loaded) == 1
        assert loaded[0].name == "my-app"

    def test_register_duplicate_raises(self, tmp_path: Path) -> None:
        registry = ProjectRegistry(global_dir=tmp_path)
        registry.register("dup", "/tmp/dup", "python")
        with pytest.raises(ValueError, match="already registered"):
            registry.register("dup", "/tmp/dup2", "python")

    def test_unregister(self, tmp_path: Path) -> None:
        registry = ProjectRegistry(global_dir=tmp_path)
        registry.register("to-remove", "/tmp/to-remove", "python")
        registry.unregister("to-remove")
        assert registry.load() == []

    def test_unregister_missing_raises(self, tmp_path: Path) -> None:
        registry = ProjectRegistry(global_dir=tmp_path)
        with pytest.raises(KeyError, match="not found"):
            registry.unregister("nonexistent")

    def test_find_by_name(self, tmp_path: Path) -> None:
        registry = ProjectRegistry(global_dir=tmp_path)
        registry.register("findme", "/tmp/findme", "typescript")
        result = registry.find_by_name("findme")
        assert result is not None
        assert result.type == "typescript"

    def test_find_by_name_missing(self, tmp_path: Path) -> None:
        registry = ProjectRegistry(global_dir=tmp_path)
        assert registry.find_by_name("nope") is None

    def test_find_by_path(self, tmp_path: Path) -> None:
        registry = ProjectRegistry(global_dir=tmp_path)
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        registry.register("bypath", str(project_dir), "python")
        result = registry.find_by_path(str(project_dir))
        assert result is not None
        assert result.name == "bypath"

    def test_find_by_path_missing(self, tmp_path: Path) -> None:
        registry = ProjectRegistry(global_dir=tmp_path)
        assert registry.find_by_path("/nonexistent") is None

    def test_update_last_active(self, tmp_path: Path) -> None:
        registry = ProjectRegistry(global_dir=tmp_path)
        registry.register("active-test", "/tmp/active", "python")
        registry.update_last_active("active-test")
        project = registry.find_by_name("active-test")
        assert project is not None
        assert project.last_active != ""

    def test_update_last_active_missing_raises(self, tmp_path: Path) -> None:
        registry = ProjectRegistry(global_dir=tmp_path)
        with pytest.raises(KeyError, match="not found"):
            registry.update_last_active("nope")

    def test_archive(self, tmp_path: Path) -> None:
        registry = ProjectRegistry(global_dir=tmp_path)
        registry.register("archiveme", "/tmp/archiveme", "python")
        registry.archive("archiveme")
        project = registry.find_by_name("archiveme")
        assert project is not None
        assert project.archived is True

    def test_archive_missing_raises(self, tmp_path: Path) -> None:
        registry = ProjectRegistry(global_dir=tmp_path)
        with pytest.raises(KeyError, match="not found"):
            registry.archive("nope")

    def test_validate_all_valid(self, tmp_path: Path) -> None:
        registry = ProjectRegistry(global_dir=tmp_path)
        project_dir = tmp_path / "valid_proj"
        project_dir.mkdir()
        (project_dir / ".autopilot").mkdir()
        registry.register("valid", str(project_dir), "python")
        issues = registry.validate_all()
        assert issues == []

    def test_validate_all_missing_path(self, tmp_path: Path) -> None:
        registry = ProjectRegistry(global_dir=tmp_path)
        registry.register("gone", "/nonexistent/path", "python")
        issues = registry.validate_all()
        assert len(issues) == 1
        assert isinstance(issues[0], RegistryIssue)
        assert "does not exist" in issues[0].issue

    def test_validate_all_missing_autopilot_dir(self, tmp_path: Path) -> None:
        registry = ProjectRegistry(global_dir=tmp_path)
        project_dir = tmp_path / "no_autopilot"
        project_dir.mkdir()
        registry.register("no-ap", str(project_dir), "python")
        issues = registry.validate_all()
        assert len(issues) == 1
        assert ".autopilot/" in issues[0].issue

    def test_persists_across_instances(self, tmp_path: Path) -> None:
        r1 = ProjectRegistry(global_dir=tmp_path)
        r1.register("persist", "/tmp/persist", "python")

        r2 = ProjectRegistry(global_dir=tmp_path)
        assert r2.find_by_name("persist") is not None

    def test_registry_file_created_on_first_use(self, tmp_path: Path) -> None:
        gd = tmp_path / "new_global"
        registry = ProjectRegistry(global_dir=gd)
        registry.register("first", "/tmp/first", "python")
        assert (gd / "projects.yaml").exists()

    def test_handles_corrupt_yaml(self, tmp_path: Path) -> None:
        registry = ProjectRegistry(global_dir=tmp_path)
        (tmp_path / "projects.yaml").write_text("not: a: list: {bad")
        # Should return empty rather than crash
        assert registry.load() == []

    def test_multiple_projects(self, tmp_path: Path) -> None:
        registry = ProjectRegistry(global_dir=tmp_path)
        registry.register("alpha", "/tmp/alpha", "python")
        registry.register("beta", "/tmp/beta", "typescript")
        registry.register("gamma", "/tmp/gamma", "hybrid")
        assert len(registry.load()) == 3


class TestRegisteredProject:
    def test_defaults(self) -> None:
        p = RegisteredProject(name="x", path="/tmp/x", type="python")
        assert p.archived is False
        assert p.registered_at != ""
        assert p.last_active == ""
