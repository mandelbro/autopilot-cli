"""Tests for autopilot.cli.project (Tasks 010, 104)."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003
from unittest.mock import MagicMock, patch

import yaml
from typer.testing import CliRunner

from autopilot.cli.app import app
from autopilot.cli.project import _detect_git_origin

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


class TestDetectGitOrigin:
    @patch("autopilot.cli.project.subprocess.run")
    def test_returns_url_on_success(self, mock_run: MagicMock, tmp_path: Path) -> None:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="https://github.com/test/repo.git\n"
        )
        result = _detect_git_origin(tmp_path)
        assert result == "https://github.com/test/repo.git"

    @patch("autopilot.cli.project.subprocess.run")
    def test_returns_empty_on_failure(self, mock_run: MagicMock, tmp_path: Path) -> None:
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        result = _detect_git_origin(tmp_path)
        assert result == ""

    @patch("autopilot.cli.project.subprocess.run", side_effect=FileNotFoundError)
    def test_returns_empty_when_git_not_found(self, _run: MagicMock, tmp_path: Path) -> None:
        result = _detect_git_origin(tmp_path)
        assert result == ""


class TestInitWithRepositoryUrl:
    def test_init_with_repository_url(self, tmp_path: Path) -> None:
        with patch("autopilot.core.project.get_global_dir", return_value=tmp_path / "global"):
            result = runner.invoke(
                app,
                [
                    "init",
                    "--name",
                    "url-proj",
                    "--type",
                    "python",
                    "--root",
                    str(tmp_path),
                    "--repository-url",
                    "https://github.com/t/t.git",
                ],
            )
            assert result.exit_code == 0
            projects_file = tmp_path / "global" / "projects.yaml"
            data = yaml.safe_load(projects_file.read_text())
            assert data[0]["repository_url"] == "https://github.com/t/t.git"

    def test_project_init_with_repository_url(self, tmp_path: Path) -> None:
        with patch("autopilot.core.project.get_global_dir", return_value=tmp_path / "global"):
            result = runner.invoke(
                app,
                [
                    "project",
                    "init",
                    "--name",
                    "url-proj2",
                    "--type",
                    "python",
                    "--root",
                    str(tmp_path),
                    "--repository-url",
                    "https://github.com/t/t.git",
                ],
            )
            assert result.exit_code == 0
            projects_file = tmp_path / "global" / "projects.yaml"
            data = yaml.safe_load(projects_file.read_text())
            assert data[0]["repository_url"] == "https://github.com/t/t.git"


class TestProjectListCommand:
    def test_project_list_stub(self) -> None:
        result = runner.invoke(app, ["project", "list"])
        assert result.exit_code == 0
