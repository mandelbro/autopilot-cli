"""Process management utilities.

Consolidates _is_running from RepEngine cli.py and cli_display.py
into a shared utility per Discovery Consolidation Opportunity 3.
"""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def is_running(pid: int) -> bool:
    """Check whether a process with the given PID is alive."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but we lack permission to signal it.
        return True
    return True


def find_orphaned_processes(pattern: str) -> list[int]:
    """Return PIDs of processes whose command line matches *pattern*.

    Uses ``pgrep -f`` on Unix systems. Returns an empty list on failure
    or if no matches are found.
    """
    import subprocess

    try:
        result = subprocess.run(
            ["pgrep", "-f", pattern],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return []
        return [int(line) for line in result.stdout.strip().splitlines() if line.strip()]
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        return []


class PidFile:
    """Manages a PID file for daemon-style process coordination.

    Supports acquire/release semantics, liveness checking, and
    TTL-based stale lock recovery.
    """

    def __init__(self, path: Path, *, ttl_seconds: int = 0) -> None:
        self.path = path
        self.ttl_seconds = ttl_seconds

    def acquire(self, pid: int | None = None) -> bool:
        """Attempt to acquire the PID file.

        Returns True if acquired, False if another live process holds it.
        Automatically recovers stale locks (dead process or expired TTL).
        Uses atomic exclusive-create to avoid TOCTOU races.
        """
        pid = pid if pid is not None else os.getpid()

        if self.path.exists():
            existing = self._read()
            if existing is not None and is_running(existing) and not self._is_expired():
                return False
            # Stale lock — reclaim.
            self.path.unlink(missing_ok=True)

        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(str(self.path), os.O_WRONLY | os.O_CREAT | os.O_EXCL)
            os.write(fd, str(pid).encode())
            os.close(fd)
        except FileExistsError:
            # Another process raced us — check if it's alive
            existing = self._read()
            if existing is not None and is_running(existing):
                return False
            # The other writer died; retry once
            self.path.unlink(missing_ok=True)
            try:
                fd = os.open(str(self.path), os.O_WRONLY | os.O_CREAT | os.O_EXCL)
                os.write(fd, str(pid).encode())
                os.close(fd)
            except FileExistsError:
                return False  # lost the second race; another live process owns it
        return True

    def release(self) -> None:
        """Release the PID file."""
        self.path.unlink(missing_ok=True)

    def is_alive(self) -> bool:
        """Return True if the PID file exists and the process is running."""
        existing = self._read()
        if existing is None:
            return False
        return is_running(existing)

    def force_recover(self) -> None:
        """Forcefully remove the PID file regardless of state."""
        self.path.unlink(missing_ok=True)

    def read_pid(self) -> int | None:
        """Read the PID from the file, or None if absent/invalid."""
        return self._read()

    def _read(self) -> int | None:
        try:
            return int(self.path.read_text().strip())
        except (FileNotFoundError, ValueError):
            return None

    def _is_expired(self) -> bool:
        """Check if the PID file has exceeded its TTL."""
        if self.ttl_seconds <= 0:
            return False
        try:
            mtime = self.path.stat().st_mtime
        except FileNotFoundError:
            return True
        return (time.time() - mtime) > self.ttl_seconds
