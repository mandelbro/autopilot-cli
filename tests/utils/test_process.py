"""Tests for autopilot.utils.process."""

from __future__ import annotations

import os
from pathlib import Path  # noqa: TC003

from autopilot.utils.process import PidFile, find_orphaned_processes, is_running


class TestIsRunning:
    def test_own_process(self) -> None:
        assert is_running(os.getpid()) is True

    def test_invalid_pid(self) -> None:
        assert is_running(0) is False
        assert is_running(-1) is False

    def test_dead_pid(self) -> None:
        # PID 99999999 is extremely unlikely to exist
        assert is_running(99999999) is False


class TestFindOrphanedProcesses:
    def test_no_match(self) -> None:
        result = find_orphaned_processes("__unlikely_pattern_xyzzy_99__")
        assert result == []

    def test_returns_list(self) -> None:
        # Just verify the function returns a list and doesn't crash
        result = find_orphaned_processes("python")
        assert isinstance(result, list)


class TestPidFile:
    def test_acquire_and_release(self, tmp_path: Path) -> None:
        pf = PidFile(tmp_path / "test.pid")
        assert pf.acquire() is True
        assert pf.path.exists()
        assert pf.is_alive() is True
        pf.release()
        assert not pf.path.exists()

    def test_acquire_blocks_when_alive(self, tmp_path: Path) -> None:
        pf = PidFile(tmp_path / "test.pid")
        pf.acquire(pid=os.getpid())

        pf2 = PidFile(tmp_path / "test.pid")
        assert pf2.acquire(pid=os.getpid() + 1) is False

    def test_acquire_recovers_dead_lock(self, tmp_path: Path) -> None:
        pid_file = tmp_path / "test.pid"
        pid_file.write_text("99999999")  # dead PID

        pf = PidFile(pid_file)
        assert pf.acquire() is True
        assert pf.read_pid() == os.getpid()

    def test_ttl_based_recovery(self, tmp_path: Path) -> None:
        pid_file = tmp_path / "test.pid"
        pid_file.write_text(str(os.getpid()))

        # Set mtime to the past
        old_time = os.path.getmtime(str(pid_file)) - 1000
        os.utime(str(pid_file), (old_time, old_time))

        pf = PidFile(pid_file, ttl_seconds=10)
        # Even though the PID is alive, the TTL is expired
        assert pf.acquire(pid=os.getpid()) is True

    def test_force_recover(self, tmp_path: Path) -> None:
        pid_file = tmp_path / "test.pid"
        pid_file.write_text(str(os.getpid()))

        pf = PidFile(pid_file)
        pf.force_recover()
        assert not pid_file.exists()

    def test_read_pid_missing_file(self, tmp_path: Path) -> None:
        pf = PidFile(tmp_path / "nonexistent.pid")
        assert pf.read_pid() is None

    def test_read_pid_invalid_content(self, tmp_path: Path) -> None:
        pid_file = tmp_path / "test.pid"
        pid_file.write_text("not-a-number")
        pf = PidFile(pid_file)
        assert pf.read_pid() is None

    def test_is_alive_no_file(self, tmp_path: Path) -> None:
        pf = PidFile(tmp_path / "nonexistent.pid")
        assert pf.is_alive() is False

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        pf = PidFile(tmp_path / "deep" / "nested" / "test.pid")
        assert pf.acquire() is True
        assert pf.path.exists()
