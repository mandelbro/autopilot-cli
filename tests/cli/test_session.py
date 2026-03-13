"""Tests for session CLI commands (Task 039)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from autopilot.cli.app import app

if TYPE_CHECKING:
    from pathlib import Path

runner = CliRunner()

_MOD = "autopilot.cli.session"


class TestSessionHelp:
    def test_session_help_shows_commands(self) -> None:
        result = runner.invoke(app, ["session", "--help"])
        assert result.exit_code == 0
        for cmd in ("start", "stop", "pause", "resume", "list", "attach", "log"):
            assert cmd in result.output


class TestSessionStart:
    @patch(f"{_MOD}.find_autopilot_dir", return_value=None)
    def test_no_autopilot_dir(self, _find: MagicMock) -> None:
        result = runner.invoke(app, ["session", "start"])
        assert result.exit_code == 1
        assert "No .autopilot directory" in result.output


class TestSessionStop:
    @patch(f"{_MOD}.find_autopilot_dir", return_value=None)
    def test_no_autopilot_dir(self, _find: MagicMock) -> None:
        result = runner.invoke(app, ["session", "stop"])
        assert result.exit_code == 1
        assert "No .autopilot directory" in result.output

    @patch(f"{_MOD}.stop_daemon", return_value=True)
    @patch(f"{_MOD}.find_autopilot_dir")
    def test_stop_success(self, mock_find: MagicMock, _stop: MagicMock, tmp_path: Path) -> None:
        mock_find.return_value = tmp_path
        result = runner.invoke(app, ["session", "stop"])
        assert result.exit_code == 0
        assert "stopped" in result.output

    @patch(f"{_MOD}.stop_daemon", return_value=False)
    @patch(f"{_MOD}.find_autopilot_dir")
    def test_stop_no_daemon(self, mock_find: MagicMock, _stop: MagicMock, tmp_path: Path) -> None:
        mock_find.return_value = tmp_path
        result = runner.invoke(app, ["session", "stop"])
        assert result.exit_code == 0
        assert "No running daemon" in result.output


class TestSessionPause:
    @patch(f"{_MOD}.find_autopilot_dir", return_value=None)
    def test_no_autopilot_dir(self, _find: MagicMock) -> None:
        result = runner.invoke(app, ["session", "pause", "abc123"])
        assert result.exit_code == 1

    @patch(f"{_MOD}.SessionManager")
    @patch(f"{_MOD}.Database")
    @patch(f"{_MOD}.find_autopilot_dir")
    def test_pause_not_found(
        self, mock_find: MagicMock, _db: MagicMock, mock_mgr_cls: MagicMock, tmp_path: Path
    ) -> None:
        mock_find.return_value = tmp_path
        mock_mgr_cls.return_value.get_session.return_value = None
        result = runner.invoke(app, ["session", "pause", "abc123"])
        assert result.exit_code == 1
        assert "not found" in result.output

    @patch(f"{_MOD}.SessionManager")
    @patch(f"{_MOD}.Database")
    @patch(f"{_MOD}.find_autopilot_dir")
    def test_pause_success(
        self, mock_find: MagicMock, _db: MagicMock, mock_mgr_cls: MagicMock, tmp_path: Path
    ) -> None:
        mock_find.return_value = tmp_path
        mock_mgr_cls.return_value.get_session.return_value = MagicMock()
        result = runner.invoke(app, ["session", "pause", "abc123"])
        assert result.exit_code == 0
        assert "paused" in result.output


class TestSessionResume:
    @patch(f"{_MOD}.SessionManager")
    @patch(f"{_MOD}.Database")
    @patch(f"{_MOD}.find_autopilot_dir")
    def test_resume_success(
        self, mock_find: MagicMock, _db: MagicMock, mock_mgr_cls: MagicMock, tmp_path: Path
    ) -> None:
        mock_find.return_value = tmp_path
        mock_mgr_cls.return_value.get_session.return_value = MagicMock()
        result = runner.invoke(app, ["session", "resume", "abc123"])
        assert result.exit_code == 0
        assert "resumed" in result.output


class TestSessionList:
    @patch(f"{_MOD}.find_autopilot_dir", return_value=None)
    def test_no_autopilot_dir(self, _find: MagicMock) -> None:
        result = runner.invoke(app, ["session", "list"])
        assert result.exit_code == 1

    @patch(f"{_MOD}.SessionManager")
    @patch(f"{_MOD}.Database")
    @patch(f"{_MOD}.find_autopilot_dir")
    def test_empty_list(
        self, mock_find: MagicMock, _db: MagicMock, mock_mgr_cls: MagicMock, tmp_path: Path
    ) -> None:
        mock_find.return_value = tmp_path
        mock_mgr_cls.return_value.list_sessions.return_value = []
        result = runner.invoke(app, ["session", "list"])
        assert result.exit_code == 0
        assert "No sessions found" in result.output


class TestSessionLog:
    @patch(f"{_MOD}.find_autopilot_dir", return_value=None)
    def test_no_autopilot_dir(self, _find: MagicMock) -> None:
        result = runner.invoke(app, ["session", "log", "abc123"])
        assert result.exit_code == 1

    @patch(f"{_MOD}.find_autopilot_dir")
    def test_no_log_file(self, mock_find: MagicMock, tmp_path: Path) -> None:
        mock_find.return_value = tmp_path
        result = runner.invoke(app, ["session", "log", "abc123"])
        assert result.exit_code == 1
        assert "No log file" in result.output

    @patch(f"{_MOD}.find_autopilot_dir")
    def test_shows_log_lines(self, mock_find: MagicMock, tmp_path: Path) -> None:
        mock_find.return_value = tmp_path
        log_dir = tmp_path / "logs"
        log_dir.mkdir(parents=True)
        log_file = log_dir / "daemon.log"
        log_file.write_text("line1\nline2\nline3\n")

        result = runner.invoke(app, ["session", "log", "abc123", "--lines", "2"])
        assert result.exit_code == 0
        assert "line2" in result.output
        assert "line3" in result.output


class TestSessionAttach:
    @patch(f"{_MOD}.find_autopilot_dir", return_value=None)
    def test_no_autopilot_dir(self, _find: MagicMock) -> None:
        result = runner.invoke(app, ["session", "attach", "abc123"])
        assert result.exit_code == 1

    @patch(f"{_MOD}.find_autopilot_dir")
    def test_no_log_file(self, mock_find: MagicMock, tmp_path: Path) -> None:
        mock_find.return_value = tmp_path
        result = runner.invoke(app, ["session", "attach", "abc123"])
        assert result.exit_code == 1
        assert "No log file" in result.output
