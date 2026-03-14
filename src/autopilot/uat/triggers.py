"""UAT automatic trigger hooks (Task 075).

Fires UAT automatically when tasks are marked complete, with configurable
auto-trigger, queue mechanism, and trivial task skipping.
"""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass
from pathlib import Path  # noqa: TC003 — used at runtime

import structlog

from autopilot.core.task import TaskParser
from autopilot.uat.pipeline import UATPipeline
from autopilot.uat.test_executor import UATResult  # noqa: TC001

logger = structlog.get_logger(__name__)

DEFAULT_SKIP_THRESHOLD = 1  # Skip tasks with <= this many sprint points


@dataclass
class TriggerConfig:
    """Configuration for UAT auto-trigger behavior."""

    enabled: bool = True
    skip_threshold: int = DEFAULT_SKIP_THRESHOLD
    timeout: int = 300
    max_tests_per_sp: int = 5


@dataclass(frozen=True)
class TriggerEvent:
    """Represents a task completion event for UAT triggering."""

    task_id: str
    project_dir: Path


class UATTrigger:
    """Automatic UAT trigger that fires on task completion."""

    def __init__(self, config: TriggerConfig | None = None) -> None:
        self._config = config or TriggerConfig()
        self._pipeline = UATPipeline(
            timeout=self._config.timeout,
            max_tests_per_sp=self._config.max_tests_per_sp,
        )
        self._queue: deque[TriggerEvent] = deque()
        self._running = False
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    @property
    def queue_size(self) -> int:
        return len(self._queue)

    @property
    def is_running(self) -> bool:
        return self._running

    def on_task_complete(self, task_id: str, project_dir: Path) -> UATResult | None:
        """Handle a task completion event.

        If auto-trigger is enabled and the task is not trivial, runs UAT.
        If UAT is already running, queues the event for later processing.

        Returns the UATResult if executed immediately, or None if queued/skipped.
        """
        if not self._config.enabled:
            logger.info("uat_trigger_disabled", task_id=task_id)
            return None

        # Check if task should be skipped (trivial)
        if self._should_skip(task_id, project_dir):
            logger.info("uat_trigger_skip_trivial", task_id=task_id)
            return None

        event = TriggerEvent(task_id=task_id, project_dir=project_dir)

        with self._lock:
            if self._running:
                self._queue.append(event)
                logger.info(
                    "uat_trigger_queued",
                    task_id=task_id,
                    queue_size=len(self._queue),
                )
                return None

            self._running = True

        try:
            result = self._run_uat(event)
            self._process_queue()
            return result
        finally:
            with self._lock:
                self._running = False

    def process_pending(self) -> list[tuple[str, UATResult]]:
        """Process all pending events in the queue.

        Returns a list of (task_id, result) tuples.
        """
        results: list[tuple[str, UATResult]] = []

        while self._queue:
            event = self._queue.popleft()
            result = self._run_uat(event)
            results.append((event.task_id, result))

        return results

    def _should_skip(self, task_id: str, project_dir: Path) -> bool:
        """Check if a task is trivial and should skip UAT."""
        task_dir = project_dir / "tasks"
        parser = TaskParser()
        task = parser.find_task_by_id(task_dir, task_id)

        if task is None:
            return False

        points = task.sprint_points
        return isinstance(points, int) and points <= self._config.skip_threshold

    def _run_uat(self, event: TriggerEvent) -> UATResult:
        """Execute UAT pipeline for a single trigger event."""
        logger.info("uat_trigger_fire", task_id=event.task_id)
        return self._pipeline.run(event.task_id, event.project_dir)

    def _process_queue(self) -> None:
        """Process queued events after current UAT completes."""
        while self._queue:
            event = self._queue.popleft()
            logger.info("uat_trigger_dequeue", task_id=event.task_id)
            self._run_uat(event)
