"""Tests for autopilot.core.project (Task 010)."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003
from unittest.mock import patch

import pytest
import yaml

from autopilot.core.project import ProjectInitResult, initialize_project


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


class TestProjectInitResult:
    def test_defaults(self) -> None:
        result = ProjectInitResult(
            project_name="test",
            project_root=Path("/tmp"),
            autopilot_dir=Path("/tmp/.autopilot"),
        )
        assert result.files_created == []
        assert result.next_steps == []
