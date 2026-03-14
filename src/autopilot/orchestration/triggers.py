"""Event-driven scheduler triggers (Task 087).

Provides file change, git push, and manual triggers for the scheduler,
supporting interval, event, and hybrid scheduling strategies.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class TriggerEvent:
    """An event that should trigger a scheduler cycle."""

    trigger_type: str  # "file_change", "git_push", "manual", "interval"
    source: str  # path or description
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class Trigger(ABC):
    """Base class for scheduler triggers."""

    @abstractmethod
    def check(self) -> TriggerEvent | None:
        """Check if this trigger has fired. Returns event or None."""

    @abstractmethod
    def reset(self) -> None:
        """Reset the trigger after it has been consumed."""


class FileChangeTrigger(Trigger):
    """Watch directories for file changes using modification time polling.

    Monitors specified directories (e.g. tasks/, board/) for changes.
    Uses mtime comparison rather than filesystem events for portability.
    """

    def __init__(self, watch_dirs: list[Path]) -> None:
        self._watch_dirs = watch_dirs
        self._last_check: dict[str, float] = {}
        self._initialize_mtimes()

    def _initialize_mtimes(self) -> None:
        """Record initial modification times."""
        self._last_check.clear()
        for d in self._watch_dirs:
            if d.is_dir():
                for f in d.rglob("*"):
                    if f.is_file():
                        try:
                            self._last_check[str(f)] = f.stat().st_mtime
                        except OSError:
                            continue

    def check(self) -> TriggerEvent | None:
        """Check for file modifications since last check."""
        changed_files: list[str] = []
        for d in self._watch_dirs:
            if not d.is_dir():
                continue
            for f in d.rglob("*"):
                if not f.is_file():
                    continue
                path_str = str(f)
                try:
                    current_mtime = f.stat().st_mtime
                except OSError:
                    continue
                last_mtime = self._last_check.get(path_str, 0.0)
                if current_mtime > last_mtime:
                    changed_files.append(path_str)
                    self._last_check[path_str] = current_mtime

        if changed_files:
            return TriggerEvent(
                trigger_type="file_change",
                source=f"{len(changed_files)} file(s) changed",
            )
        return None

    def reset(self) -> None:
        """Re-record all mtimes."""
        self._initialize_mtimes()


class GitPushTrigger(Trigger):
    """Detect new commits on the current branch.

    Compares HEAD SHA to last known SHA to detect pushes or new commits.
    """

    def __init__(self, cwd: Path, branch: str = "main") -> None:
        self._cwd = cwd
        self._branch = branch
        self._last_sha = self._get_head_sha()

    def _get_head_sha(self) -> str:
        """Get current HEAD SHA."""
        from autopilot.utils.git import get_current_sha

        try:
            return get_current_sha(cwd=self._cwd)
        except Exception:
            return ""

    def check(self) -> TriggerEvent | None:
        """Check if HEAD has changed."""
        current = self._get_head_sha()
        if current and current != self._last_sha:
            self._last_sha = current
            return TriggerEvent(
                trigger_type="git_push",
                source=f"new commit {current[:8]}",
            )
        return None

    def reset(self) -> None:
        """Re-read the current HEAD SHA."""
        self._last_sha = self._get_head_sha()


class ManualTrigger(Trigger):
    """Always-available trigger for explicit cycle requests."""

    def __init__(self) -> None:
        self._fired = False

    def fire(self) -> None:
        """Fire the manual trigger."""
        self._fired = True

    def check(self) -> TriggerEvent | None:
        """Return an event if the trigger has been fired."""
        if self._fired:
            return TriggerEvent(trigger_type="manual", source="manual request")
        return None

    def reset(self) -> None:
        """Clear the fired state."""
        self._fired = False


class TriggerManager:
    """Manages multiple triggers with debouncing.

    Supports three strategies:
    - "interval": only time-based (no triggers checked)
    - "event": only triggers, no interval
    - "hybrid": triggers with minimum interval between cycles
    """

    def __init__(
        self,
        strategy: str = "interval",
        *,
        triggers: list[Trigger] | None = None,
        min_interval_seconds: float = 60.0,
        debounce_seconds: float = 5.0,
    ) -> None:
        self._strategy = strategy
        self._triggers = triggers or []
        self._min_interval = min_interval_seconds
        self._debounce = debounce_seconds
        self._last_cycle_time: float = 0.0
        self._last_event_time: float = 0.0

    @property
    def strategy(self) -> str:
        """Return the current scheduling strategy."""
        return self._strategy

    def add_trigger(self, trigger: Trigger) -> None:
        """Add a trigger to the manager."""
        self._triggers.append(trigger)

    def should_run_cycle(self) -> TriggerEvent | None:
        """Check all triggers and decide if a cycle should run.

        Returns the triggering event or None.
        Implements debouncing: rapid events within debounce window are collapsed.
        """
        now = time.monotonic()

        if self._strategy == "interval":
            # Pure interval mode -- no triggers to check
            return None

        # Check debounce
        if now - self._last_event_time < self._debounce:
            return None

        # Check minimum interval for hybrid mode
        if self._strategy == "hybrid" and now - self._last_cycle_time < self._min_interval:
            return None

        # Check all triggers
        for trigger in self._triggers:
            event = trigger.check()
            if event is not None:
                self._last_event_time = now
                return event

        return None

    def record_cycle_completed(self) -> None:
        """Record that a cycle has completed (for debouncing)."""
        self._last_cycle_time = time.monotonic()
        for trigger in self._triggers:
            trigger.reset()
