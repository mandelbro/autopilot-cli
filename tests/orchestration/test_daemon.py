"""Tests for daemon with signal handling and log rotation (Task 036)."""

from __future__ import annotations

import os
import signal
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from autopilot.core.config import (
    AutopilotConfig,
    ProjectConfig,
    SchedulerConfig,
)
from autopilot.orchestration.daemon import (
    Daemon,
    DaemonState,
    stop_daemon,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def config() -> AutopilotConfig:
    return AutopilotConfig(
        project=ProjectConfig(name="test-project"),
        scheduler=SchedulerConfig(interval_seconds=1),
    )


@pytest.fixture()
def mock_scheduler() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def daemon(
    config: AutopilotConfig,
    mock_scheduler: MagicMock,
    tmp_path: Path,
) -> Daemon:
    return Daemon(
        config=config,
        scheduler=mock_scheduler,
        state_dir=tmp_path / "state",
        log_dir=tmp_path / "logs",
    )


class TestDaemonInit:
    def test_initial_state_is_stopped(self, daemon: Daemon) -> None:
        assert daemon._state == DaemonState.STOPPED

    def test_status_when_stopped(self, daemon: Daemon) -> None:
        status = daemon.status()
        assert status.state == DaemonState.STOPPED
        assert status.pid is None
        assert status.project == "test-project"
        assert status.uptime_seconds == 0.0
        assert status.cycles_completed == 0


class TestDaemonStartStop:
    @patch("autopilot.orchestration.daemon.find_orphaned_processes", return_value=[])
    def test_start_creates_directories(
        self, _orphans: MagicMock, daemon: Daemon, tmp_path: Path
    ) -> None:
        # Replace _run_loop to avoid blocking
        daemon._run_loop = lambda: None  # type: ignore[assignment]

        daemon.start()

        assert (tmp_path / "state").exists()
        assert (tmp_path / "logs").exists()

    @patch("autopilot.orchestration.daemon.find_orphaned_processes", return_value=[])
    def test_start_transitions_to_running(self, _orphans: MagicMock, daemon: Daemon) -> None:
        # Track state during loop
        observed_state: DaemonState | None = None

        def capture_state() -> None:
            nonlocal observed_state
            observed_state = daemon._state
            daemon._stop_event.set()
            # Don't call original — just stop

        daemon._run_loop = capture_state  # type: ignore[assignment]
        daemon.start()

        assert observed_state == DaemonState.RUNNING

    @patch("autopilot.orchestration.daemon.find_orphaned_processes", return_value=[])
    def test_start_releases_pid_on_finish(self, _orphans: MagicMock, daemon: Daemon) -> None:
        daemon._run_loop = lambda: None  # type: ignore[assignment]
        daemon.start()

        assert daemon._state == DaemonState.STOPPED
        assert not daemon._pid_file.is_alive()

    @patch("autopilot.orchestration.daemon.find_orphaned_processes", return_value=[])
    def test_double_start_raises(self, _orphans: MagicMock, daemon: Daemon) -> None:
        # Acquire PID file manually to simulate running daemon
        daemon._state_dir.mkdir(parents=True, exist_ok=True)
        daemon._pid_file.acquire()

        with pytest.raises(RuntimeError, match="already running"):
            daemon.start()

        daemon._pid_file.release()


class TestDaemonPauseResume:
    def test_pause_sets_paused(self, daemon: Daemon) -> None:
        daemon._state = DaemonState.RUNNING
        daemon.pause()
        assert daemon._state == DaemonState.PAUSED

    def test_resume_from_paused(self, daemon: Daemon) -> None:
        daemon._state = DaemonState.PAUSED
        daemon.resume()
        assert daemon._state == DaemonState.RUNNING

    def test_resume_noop_when_not_paused(self, daemon: Daemon) -> None:
        daemon._state = DaemonState.RUNNING
        daemon.resume()
        assert daemon._state == DaemonState.RUNNING


class TestDaemonStatus:
    def test_status_while_running(self, daemon: Daemon) -> None:
        daemon._state = DaemonState.RUNNING
        daemon._start_time = 0.0  # Will give large uptime via monotonic
        daemon._cycles_completed = 5

        status = daemon.status()
        assert status.state == DaemonState.RUNNING
        assert status.pid == os.getpid()
        assert status.cycles_completed == 5
        assert status.uptime_seconds > 0


class TestSignalHandlers:
    def test_sigterm_triggers_stop(self, daemon: Daemon, mock_scheduler: MagicMock) -> None:
        daemon._state = DaemonState.RUNNING
        daemon._handle_sigterm(signal.SIGTERM, None)

        assert daemon._state == DaemonState.STOPPING
        assert daemon._stop_event.is_set()
        mock_scheduler.stop.assert_called_once()

    def test_sighup_is_handled(self, daemon: Daemon) -> None:
        # SIGHUP should not crash — it's a config reload placeholder
        daemon._handle_sighup(signal.SIGHUP, None)


class TestLogRotation:
    def test_rotates_when_exceeds_max(self, daemon: Daemon, tmp_path: Path) -> None:
        log_dir = tmp_path / "logs"
        log_dir.mkdir(parents=True)
        log_file = log_dir / "daemon.log"
        # Set small max for testing
        daemon._log_max_bytes = 100
        log_file.write_text("x" * 200)

        daemon._rotate_log_if_needed()

        assert not log_file.exists() or log_file.stat().st_size == 0
        assert (log_dir / "daemon.log.1").exists()

    def test_no_rotation_when_small(self, daemon: Daemon, tmp_path: Path) -> None:
        log_dir = tmp_path / "logs"
        log_dir.mkdir(parents=True)
        log_file = log_dir / "daemon.log"
        daemon._log_max_bytes = 1000
        log_file.write_text("small log")

        daemon._rotate_log_if_needed()

        assert log_file.exists()
        assert not (log_dir / "daemon.log.1").exists()

    def test_no_crash_when_no_log(self, daemon: Daemon) -> None:
        # Log file doesn't exist — should not crash
        daemon._rotate_log_if_needed()


class TestOrphanCleanup:
    @patch("autopilot.orchestration.daemon.find_orphaned_processes", return_value=[123, 456])
    def test_logs_orphans(self, mock_find: MagicMock, daemon: Daemon) -> None:
        daemon._cleanup_orphans()
        mock_find.assert_called_once_with("claude.*--print")


class TestStopDaemon:
    def test_stop_running_daemon(self, tmp_path: Path) -> None:
        from autopilot.utils.process import PidFile

        state_dir = tmp_path / "state"
        state_dir.mkdir()
        pid_file = PidFile(state_dir / "daemon.pid")
        pid_file.acquire()

        with (
            patch("autopilot.orchestration.daemon.is_running", return_value=True),
            patch("autopilot.orchestration.daemon.os.kill") as mock_kill,
        ):
            result = stop_daemon(state_dir)

        assert result is True
        mock_kill.assert_called_once()
        pid_file.release()

    def test_stop_no_daemon(self, tmp_path: Path) -> None:
        result = stop_daemon(tmp_path / "state")
        assert result is False
