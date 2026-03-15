"""Tests for session CLI commands (Tasks 039, 045)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from autopilot.cli.app import app

if TYPE_CHECKING:
    from pathlib import Path

runner = CliRunner()

_MOD = "autopilot.cli.session"
_APP_MOD = "autopilot.cli.app"


class TestSessionHelp:
    def test_session_help_shows_commands(self) -> None:
        result = runner.invoke(app, ["session", "--help"])
        assert result.exit_code == 0
        for cmd in ("start", "stop", "pause", "resume", "list", "attach", "log", "workspace"):
            assert cmd in result.output


class TestSessionStart:
    @patch(f"{_MOD}.find_autopilot_dir", return_value=None)
    def test_no_autopilot_dir(self, _find: MagicMock) -> None:
        result = runner.invoke(app, ["session", "start"])
        assert result.exit_code == 1
        assert "No .autopilot directory" in result.output


class TestSessionStartNoWorkspaceFlag:
    def test_session_start_help_shows_no_workspace(self) -> None:
        result = runner.invoke(app, ["session", "start", "--help"])
        assert result.exit_code == 0
        assert "--no-workspace" in result.output

    @patch(f"{_MOD}.find_autopilot_dir", return_value=None)
    def test_no_workspace_flag_accepted(self, _find: MagicMock) -> None:
        """The --no-workspace flag is accepted without error (even if no .autopilot dir)."""
        result = runner.invoke(app, ["session", "start", "--no-workspace"])
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

    @patch(f"{_MOD}.SessionManager")
    @patch(f"{_MOD}.Database")
    @patch(f"{_MOD}.find_autopilot_dir")
    def test_resume_not_found(
        self, mock_find: MagicMock, _db: MagicMock, mock_mgr_cls: MagicMock, tmp_path: Path
    ) -> None:
        mock_find.return_value = tmp_path
        mock_mgr_cls.return_value.get_session.return_value = None
        result = runner.invoke(app, ["session", "resume", "abc123"])
        assert result.exit_code == 1
        assert "not found" in result.output


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

    @patch(f"{_MOD}.SessionManager")
    @patch(f"{_MOD}.Database")
    @patch(f"{_MOD}.find_autopilot_dir")
    def test_list_no_project_passes_none(
        self, mock_find: MagicMock, _db: MagicMock, mock_mgr_cls: MagicMock, tmp_path: Path
    ) -> None:
        """Regression: no --project must pass None, not empty string."""
        mock_find.return_value = tmp_path
        mock_mgr_cls.return_value.list_sessions.return_value = []
        runner.invoke(app, ["session", "list"])
        mock_mgr_cls.return_value.list_sessions.assert_called_once_with(
            project=None,
            status_filter=None,
        )

    @patch(f"{_MOD}.find_autopilot_dir")
    def test_list_invalid_status_exits_with_error(
        self, mock_find: MagicMock, tmp_path: Path
    ) -> None:
        """Regression: invalid --status must show error, not traceback."""
        mock_find.return_value = tmp_path
        result = runner.invoke(app, ["session", "list", "--status", "bogus"])
        assert result.exit_code == 1
        assert "Invalid status" in result.output


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


# -- Top-level convenience commands (Task 045) --------------------------------

_PATHS_MOD = "autopilot.utils.paths"
_DAEMON_MOD = "autopilot.orchestration.daemon"


class TestStartCommand:
    @patch(f"{_PATHS_MOD}.find_autopilot_dir", return_value=None)
    def test_no_autopilot_dir(self, _find: MagicMock) -> None:
        result = runner.invoke(app, ["start"])
        assert result.exit_code == 1
        assert "No .autopilot directory" in result.output

    @patch(f"{_DAEMON_MOD}.Daemon")
    @patch("autopilot.cli.app._build_scheduler")
    @patch(f"{_PATHS_MOD}.find_autopilot_dir")
    def test_start_happy_path(
        self,
        mock_find: MagicMock,
        mock_build: MagicMock,
        mock_daemon_cls: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_find.return_value = tmp_path
        mock_config = MagicMock()
        mock_scheduler = MagicMock()
        mock_build.return_value = (mock_config, mock_scheduler)
        mock_daemon_cls.return_value.start.return_value = None

        result = runner.invoke(app, ["start"])
        assert result.exit_code == 0
        assert "Starting session" in result.output
        mock_daemon_cls.return_value.start.assert_called_once()


class TestStopCommand:
    @patch(f"{_PATHS_MOD}.find_autopilot_dir", return_value=None)
    def test_no_autopilot_dir(self, _find: MagicMock) -> None:
        result = runner.invoke(app, ["stop"])
        assert result.exit_code == 1
        assert "No .autopilot directory" in result.output

    @patch(f"{_DAEMON_MOD}.stop_daemon", return_value=True)
    @patch(f"{_PATHS_MOD}.find_autopilot_dir")
    def test_stop_success(self, mock_find: MagicMock, _stop: MagicMock, tmp_path: Path) -> None:
        mock_find.return_value = tmp_path
        result = runner.invoke(app, ["stop"])
        assert result.exit_code == 0
        assert "stopped" in result.output

    @patch(f"{_DAEMON_MOD}.stop_daemon", return_value=False)
    @patch(f"{_PATHS_MOD}.find_autopilot_dir")
    def test_stop_no_daemon(self, mock_find: MagicMock, _stop: MagicMock, tmp_path: Path) -> None:
        mock_find.return_value = tmp_path
        result = runner.invoke(app, ["stop"])
        assert result.exit_code == 0
        assert "No running daemon" in result.output


class TestCycleCommand:
    @patch(f"{_PATHS_MOD}.find_autopilot_dir", return_value=None)
    def test_no_autopilot_dir(self, _find: MagicMock) -> None:
        result = runner.invoke(app, ["cycle"])
        assert result.exit_code == 1
        assert "No .autopilot directory" in result.output

    @patch("autopilot.orchestration.dispatcher.parse_dispatch_plan")
    @patch("autopilot.cli.app._build_scheduler")
    @patch(f"{_PATHS_MOD}.find_autopilot_dir")
    def test_cycle_happy_path(
        self,
        mock_find: MagicMock,
        mock_build: MagicMock,
        mock_parse: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_find.return_value = tmp_path
        mock_config = MagicMock()
        mock_scheduler = MagicMock()
        mock_result = MagicMock()
        mock_result.id = "cycle-test-123"
        mock_result.dispatches_succeeded = 2
        mock_result.dispatches_planned = 3
        mock_scheduler.run_cycle.return_value = mock_result
        mock_build.return_value = (mock_config, mock_scheduler)
        mock_parse.return_value = MagicMock()

        result = runner.invoke(app, ["cycle"])
        assert result.exit_code == 0
        assert "Running single cycle" in result.output
        mock_scheduler.run_cycle.assert_called_once()


class TestFormatSize:
    def test_bytes(self) -> None:
        from autopilot.cli.session import _format_size

        assert _format_size(512) == "512 B"

    def test_kilobytes(self) -> None:
        from autopilot.cli.session import _format_size

        assert "KB" in _format_size(2048)

    def test_megabytes(self) -> None:
        from autopilot.cli.session import _format_size

        assert "MB" in _format_size(2 * 1024 * 1024)

    def test_gigabytes(self) -> None:
        from autopilot.cli.session import _format_size

        assert "GB" in _format_size(2 * 1024 * 1024 * 1024)


class TestWorkspaceList:
    @patch(f"{_MOD}.find_autopilot_dir", return_value=None)
    def test_no_autopilot_dir(self, _find: MagicMock) -> None:
        result = runner.invoke(app, ["session", "workspace", "list"])
        assert result.exit_code == 1

    @patch("autopilot.core.workspace.WorkspaceManager.list_workspaces", return_value=[])
    @patch("autopilot.core.workspace.WorkspaceManager.__init__", return_value=None)
    @patch(f"{_MOD}.find_autopilot_dir")
    def test_empty_list(
        self,
        mock_find: MagicMock,
        _init: MagicMock,
        _list: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_find.return_value = tmp_path
        result = runner.invoke(app, ["session", "workspace", "list"])
        assert result.exit_code == 0
        assert "No workspaces found" in result.output


class TestWorkspaceCleanup:
    @patch(f"{_MOD}.find_autopilot_dir", return_value=None)
    def test_no_autopilot_dir(self, _find: MagicMock) -> None:
        result = runner.invoke(app, ["session", "workspace", "cleanup"])
        assert result.exit_code == 1

    def test_no_id_no_all_exits_error(self, tmp_path: Path) -> None:
        with patch(f"{_MOD}.find_autopilot_dir", return_value=tmp_path):
            result = runner.invoke(app, ["session", "workspace", "cleanup"])
        assert result.exit_code == 1
        assert "Specify a workspace ID" in result.output


class TestWatchCommand:
    @patch(f"{_PATHS_MOD}.find_autopilot_dir", return_value=None)
    def test_no_autopilot_dir(self, _find: MagicMock) -> None:
        result = runner.invoke(app, ["watch"])
        assert result.exit_code == 1
        assert "No .autopilot directory" in result.output

    @patch(f"{_PATHS_MOD}.find_autopilot_dir")
    def test_watch_renders_dashboard(self, mock_find: MagicMock, tmp_path: Path) -> None:
        mock_find.return_value = tmp_path
        result = runner.invoke(app, ["watch"])
        assert result.exit_code == 0
