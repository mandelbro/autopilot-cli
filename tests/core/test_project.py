"""Tests for autopilot.core.project (Task 010)."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003
from unittest.mock import patch

import pytest
import yaml

from autopilot.core.project import (
    ProjectInitResult,
    ProjectRegistry,
    RegisteredProject,
    initialize_project,
)


class TestInitializeProject:
    def test_creates_autopilot_dir(self, tmp_path: Path) -> None:
        result = initialize_project("test", root_path=tmp_path)
        assert (tmp_path / ".autopilot").is_dir()
        assert isinstance(result, ProjectInitResult)

    def test_creates_standard_subdirs(self, tmp_path: Path) -> None:
        initialize_project("test", root_path=tmp_path)
        ap = tmp_path / ".autopilot"
        for subdir in ("agents", "board", "tasks", "state", "logs", "enforcement"):
            assert (ap / subdir).is_dir()

    def test_renders_config_yaml(self, tmp_path: Path) -> None:
        initialize_project("my-project", root_path=tmp_path)
        config_path = tmp_path / ".autopilot" / "config.yaml"
        assert config_path.exists()
        data = yaml.safe_load(config_path.read_text())
        assert data["project"]["name"] == "my-project"
        assert data["project"]["type"] == "python"

    def test_renders_agent_prompts(self, tmp_path: Path) -> None:
        initialize_project("test", root_path=tmp_path)
        agents_dir = tmp_path / ".autopilot" / "agents"
        expected = {
            "project-leader.md",
            "engineering-manager.md",
            "technical-architect.md",
            "product-director.md",
            "devops-agent.md",
            "norwood-discovery.md",
            "debugging-agent.md",
        }
        actual = {f.name for f in agents_dir.iterdir() if f.suffix == ".md"}
        assert expected == actual

    def test_renders_board_files(self, tmp_path: Path) -> None:
        initialize_project("test", root_path=tmp_path)
        board_dir = tmp_path / ".autopilot" / "board"
        expected = {
            "project-board.md",
            "question-queue.md",
            "decision-log.md",
            "announcements.md",
        }
        actual = {f.name for f in board_dir.iterdir() if f.suffix == ".md"}
        assert expected == actual

    def test_creates_gitignore(self, tmp_path: Path) -> None:
        initialize_project("test", root_path=tmp_path)
        gitignore = tmp_path / ".autopilot" / ".gitignore"
        assert gitignore.exists()
        content = gitignore.read_text()
        assert "state/" in content
        assert "logs/" in content

    def test_returns_files_created(self, tmp_path: Path) -> None:
        result = initialize_project("test", root_path=tmp_path)
        assert len(result.files_created) > 0
        assert any("config.yaml" in f for f in result.files_created)

    def test_returns_next_steps(self, tmp_path: Path) -> None:
        result = initialize_project("test", root_path=tmp_path)
        assert len(result.next_steps) > 0

    def test_registers_in_global_projects_yaml(self, tmp_path: Path) -> None:
        with patch("autopilot.core.project.get_global_dir", return_value=tmp_path / "global"):
            initialize_project("test", root_path=tmp_path)
            projects_file = tmp_path / "global" / "projects.yaml"
            assert projects_file.exists()
            data = yaml.safe_load(projects_file.read_text())
            assert isinstance(data, list)
            assert data[0]["name"] == "test"

    def test_raises_if_already_initialized(self, tmp_path: Path) -> None:
        (tmp_path / ".autopilot").mkdir()
        with pytest.raises(FileExistsError, match="already initialized"):
            initialize_project("test", root_path=tmp_path)

    def test_raises_for_invalid_project_type(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="No templates found"):
            initialize_project("test", project_type="ruby", root_path=tmp_path)

    def test_rejects_path_traversal_type(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Invalid project type"):
            initialize_project("test", project_type="../../../etc", root_path=tmp_path)

    def test_rejects_slash_in_type(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Invalid project type"):
            initialize_project("test", project_type="foo/bar", root_path=tmp_path)

    def test_rejects_dot_dot_in_type(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Invalid project type"):
            initialize_project("test", project_type="..", root_path=tmp_path)

    def test_idempotent_global_registration(self, tmp_path: Path) -> None:
        root1 = tmp_path / "proj1"
        root1.mkdir()
        root2 = tmp_path / "proj2"
        root2.mkdir()

        with patch("autopilot.core.project.get_global_dir", return_value=tmp_path / "global"):
            initialize_project("proj-a", root_path=root1)
            initialize_project("proj-b", root_path=root2)
            projects_file = tmp_path / "global" / "projects.yaml"
            data = yaml.safe_load(projects_file.read_text())
            names = [p["name"] for p in data]
            assert "proj-a" in names
            assert "proj-b" in names


class TestRegisteredProject:
    def test_default_repository_url(self) -> None:
        p = RegisteredProject(name="test", path="/tmp/test", type="python")
        assert p.repository_url == ""

    def test_custom_repository_url(self) -> None:
        p = RegisteredProject(
            name="test",
            path="/tmp/test",
            type="python",
            repository_url="https://github.com/test/test.git",
        )
        assert p.repository_url == "https://github.com/test/test.git"


class TestProjectRegistryRepositoryUrl:
    def test_register_with_repository_url(self, tmp_path: Path) -> None:
        registry = ProjectRegistry(global_dir=tmp_path)
        project = registry.register(
            "test", "/tmp/test", "python", repository_url="https://github.com/t/t.git"
        )
        assert project.repository_url == "https://github.com/t/t.git"

    def test_register_without_repository_url(self, tmp_path: Path) -> None:
        registry = ProjectRegistry(global_dir=tmp_path)
        project = registry.register("test", "/tmp/test", "python")
        assert project.repository_url == ""

    def test_backward_compatible_load(self, tmp_path: Path) -> None:
        """Existing projects.yaml without repository_url loads without error."""
        projects_file = tmp_path / "projects.yaml"
        data = [
            {
                "name": "old",
                "path": "/tmp/old",
                "type": "python",
                "registered_at": "2026-01-01",
                "last_active": "",
                "archived": False,
            }
        ]
        projects_file.write_text(yaml.dump(data))
        registry = ProjectRegistry(global_dir=tmp_path)
        projects = registry.load()
        assert len(projects) == 1
        assert projects[0].repository_url == ""

    def test_update_repository_url(self, tmp_path: Path) -> None:
        registry = ProjectRegistry(global_dir=tmp_path)
        registry.register("test", "/tmp/test", "python")
        registry.update_repository_url("test", "https://github.com/t/t.git")
        project = registry.find_by_name("test")
        assert project is not None
        assert project.repository_url == "https://github.com/t/t.git"

    def test_update_repository_url_not_found(self, tmp_path: Path) -> None:
        registry = ProjectRegistry(global_dir=tmp_path)
        with pytest.raises(KeyError, match="not found"):
            registry.update_repository_url("nonexistent", "https://example.com")

    def test_update_repository_url_validates(self, tmp_path: Path) -> None:
        registry = ProjectRegistry(global_dir=tmp_path)
        registry.register("test", "/tmp/test", "python")
        with pytest.raises(ValueError, match="plausible git URL"):
            registry.update_repository_url("test", "ftp://invalid-scheme")

    def test_valid_urls_accepted(self, tmp_path: Path) -> None:
        registry = ProjectRegistry(global_dir=tmp_path)
        valid_urls = [
            "https://github.com/test/repo.git",
            "git@github.com:test/repo.git",
            "ssh://git@github.com/test/repo.git",
            "/local/path/to/repo",
        ]
        for i, url in enumerate(valid_urls):
            name = f"test-{i}"
            registry.register(name, f"/tmp/{name}", "python", repository_url=url)
            project = registry.find_by_name(name)
            assert project is not None
            assert project.repository_url == url

    def test_repository_url_persists_through_serialization(self, tmp_path: Path) -> None:
        registry = ProjectRegistry(global_dir=tmp_path)
        registry.register(
            "test", "/tmp/test", "python", repository_url="https://github.com/t/t.git"
        )
        # Load fresh
        registry2 = ProjectRegistry(global_dir=tmp_path)
        project = registry2.find_by_name("test")
        assert project is not None
        assert project.repository_url == "https://github.com/t/t.git"


class TestInitializeProjectWithRepositoryUrl:
    def test_repository_url_passed_to_registry(self, tmp_path: Path) -> None:
        with patch("autopilot.core.project.get_global_dir", return_value=tmp_path / "global"):
            initialize_project(
                "url-test",
                root_path=tmp_path,
                repository_url="https://github.com/test/repo.git",
            )
            projects_file = tmp_path / "global" / "projects.yaml"
            data = yaml.safe_load(projects_file.read_text())
            assert data[0]["repository_url"] == "https://github.com/test/repo.git"

    def test_empty_repository_url_by_default(self, tmp_path: Path) -> None:
        with patch("autopilot.core.project.get_global_dir", return_value=tmp_path / "global"):
            initialize_project("no-url-test", root_path=tmp_path)
            projects_file = tmp_path / "global" / "projects.yaml"
            data = yaml.safe_load(projects_file.read_text())
            assert data[0]["repository_url"] == ""

    def test_next_steps_include_workspace_hint(self, tmp_path: Path) -> None:
        with patch("autopilot.core.project.get_global_dir", return_value=tmp_path / "global"):
            result = initialize_project("hint-test", root_path=tmp_path / "hint-proj")
            assert any("workspace" in step.lower() for step in result.next_steps)


class TestProjectInitResult:
    def test_defaults(self) -> None:
        result = ProjectInitResult(
            project_name="test",
            project_root=Path("/tmp"),
            autopilot_dir=Path("/tmp/.autopilot"),
        )
        assert result.files_created == []
        assert result.next_steps == []
