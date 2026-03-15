"""Daemon with signal handling and log rotation (Task 036).

Background daemon evolved from RepEngine with PID file management,
POSIX signal handling, interruptible sleep, log rotation, and orphan
detection per RFC Section 3.8.
"""

from __future__ import annotations

import logging
import os
import signal
import threading
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from autopilot.core.models import DispatchPlan
from autopilot.utils.process import PidFile, find_orphaned_processes, is_running

if TYPE_CHECKING:
    from pathlib import Path

    from autopilot.core.config import AutopilotConfig
    from autopilot.core.workspace import WorkspaceManager
    from autopilot.orchestration.scheduler import Scheduler

_log = logging.getLogger(__name__)

_DEFAULT_LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB


class DaemonState(StrEnum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"


@dataclass
class DaemonStatus:
    """Snapshot of daemon state for CLI display."""

    state: DaemonState
    pid: int | None
    project: str
    uptime_seconds: float = 0.0
    cycles_completed: int = 0


class Daemon:
    """Background daemon for per-project autonomous execution.

    Manages PID file, signal handlers, interruptible sleep,
    log rotation, and orphan cleanup.
    """

    def __init__(
        self,
        config: AutopilotConfig,
        scheduler: Scheduler,
        *,
        state_dir: Path,
        log_dir: Path,
        log_max_bytes: int = _DEFAULT_LOG_MAX_BYTES,
        workspace_manager: WorkspaceManager | None = None,
    ) -> None:
        self._config = config
        self._scheduler = scheduler
        self._state_dir = state_dir
        self._log_dir = log_dir
        self._log_max_bytes = log_max_bytes
        self._workspace_manager = workspace_manager

        self._pid_file = PidFile(state_dir / "daemon.pid", ttl_seconds=7200)
        self._state = DaemonState.STOPPED
        self._stop_event = threading.Event()
        self._start_time: float | None = None
        self._cycles_completed = 0

    def start(self) -> None:
        """Start the daemon, writing PID file and entering the scheduler loop."""
        self._cleanup_orphans()
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._log_dir.mkdir(parents=True, exist_ok=True)

        if not self._pid_file.acquire():
            existing_pid = self._pid_file.read_pid()
            msg = f"Daemon already running (PID {existing_pid})"
            raise RuntimeError(msg)

        # Forward workspace manager to scheduler if not already set
        if self._workspace_manager is not None and self._scheduler._workspace_manager is None:  # pyright: ignore[reportPrivateUsage]
            self._scheduler._workspace_manager = self._workspace_manager  # pyright: ignore[reportPrivateUsage]
        elif self._config.workspace.enabled and self._workspace_manager is None:
            _log.warning("daemon_workspace_enabled_but_no_manager")

        self._state = DaemonState.RUNNING
        self._start_time = time.monotonic()
        self._stop_event.clear()
        self._install_signal_handlers()

        _log.info(
            "daemon_started: project=%s pid=%d",
            self._config.project.name,
            os.getpid(),
        )

        try:
            self._run_loop()
        finally:
            self._state = DaemonState.STOPPED
            self._pid_file.release()
            _log.info("daemon_stopped: project=%s", self._config.project.name)

    def stop(self) -> None:
        """Signal the daemon to stop gracefully."""
        self._state = DaemonState.STOPPING
        self._stop_event.set()
        self._scheduler.stop()

    def pause(self) -> None:
        """Suspend cycle execution without stopping the daemon."""
        self._state = DaemonState.PAUSED
        _log.info("daemon_paused: project=%s", self._config.project.name)

    def resume(self) -> None:
        """Resume cycle execution after pause."""
        if self._state == DaemonState.PAUSED:
            self._state = DaemonState.RUNNING
            _log.info("daemon_resumed: project=%s", self._config.project.name)

    def status(self) -> DaemonStatus:
        """Return current daemon status."""
        uptime = 0.0
        if self._start_time is not None:
            uptime = time.monotonic() - self._start_time
        return DaemonStatus(
            state=self._state,
            pid=os.getpid() if self._state != DaemonState.STOPPED else None,
            project=self._config.project.name,
            uptime_seconds=uptime,
            cycles_completed=self._cycles_completed,
        )

    def _run_loop(self) -> None:
        """Main daemon loop with interruptible sleep."""
        interval = self._config.scheduler.interval_seconds

        while not self._stop_event.is_set():
            if self._state == DaemonState.PAUSED:
                self._stop_event.wait(timeout=5.0)
                continue

            self._rotate_log_if_needed()

            try:
                plan = DispatchPlan()
                self._scheduler.run_cycle(plan)
                self._cycles_completed += 1
            except Exception:
                _log.exception("daemon_cycle_error")

            # Interruptible sleep
            self._stop_event.wait(timeout=interval)

    def _install_signal_handlers(self) -> None:
        """Install POSIX signal handlers for daemon control."""
        signal.signal(signal.SIGTERM, self._handle_sigterm)
        signal.signal(signal.SIGINT, self._handle_sigterm)
        signal.signal(signal.SIGHUP, self._handle_sighup)

    def _handle_sigterm(self, signum: int, frame: object) -> None:
        """Handle SIGTERM/SIGINT for graceful shutdown."""
        _log.info("daemon_signal_received: signal=%d", signum)
        self.stop()

    def _handle_sighup(self, signum: int, frame: object) -> None:
        """Handle SIGHUP for config reload (placeholder)."""
        _log.info("daemon_sighup: config reload requested")

    def _rotate_log_if_needed(self) -> None:
        """Rotate daemon.log if it exceeds the configured size."""
        log_file = self._log_dir / "daemon.log"
        if not log_file.exists():
            return
        try:
            size = log_file.stat().st_size
        except OSError:
            return
        if size < self._log_max_bytes:
            return

        rotated = self._log_dir / "daemon.log.1"
        try:
            if rotated.exists():
                rotated.unlink()
            log_file.rename(rotated)
            _log.info("daemon_log_rotated: size=%d", size)
        except OSError:
            _log.warning("daemon_log_rotate_failed")

    def _cleanup_orphans(self) -> None:
        """Find and log orphaned Claude processes on startup."""
        orphans = find_orphaned_processes("claude.*--print")
        if orphans:
            _log.warning(
                "daemon_orphans_found: pids=%s",
                ",".join(str(p) for p in orphans),
            )


def stop_daemon(state_dir: Path) -> bool:
    """Send SIGTERM to a running daemon via its PID file.

    Returns True if the signal was sent, False if no daemon found.
    """
    pid_file = PidFile(state_dir / "daemon.pid")
    pid = pid_file.read_pid()
    if pid is None or not is_running(pid):
        return False
    try:
        os.kill(pid, signal.SIGTERM)
        return True
    except ProcessLookupError:
        return False
