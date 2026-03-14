"""UAT batch mode with parallel execution (Task 074).

Runs UAT across multiple completed tasks in parallel using
ThreadPoolExecutor, with configurable worker count and progress tracking.
"""

from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass, field
from pathlib import Path  # noqa: TC003 — used at runtime

import structlog

from autopilot.core.task import TaskParser
from autopilot.uat.pipeline import UATPipeline
from autopilot.uat.test_executor import UATResult

logger = structlog.get_logger(__name__)

DEFAULT_WORKERS = 4
DEFAULT_TIMEOUT = 300


@dataclass(frozen=True)
class BatchProgress:
    """Progress state for a batch UAT run."""

    total: int = 0
    completed: int = 0
    passed: int = 0
    failed: int = 0

    @property
    def remaining(self) -> int:
        return self.total - self.completed

    @property
    def percentage(self) -> float:
        return (self.completed / max(self.total, 1)) * 100


@dataclass(frozen=True)
class BatchResult:
    """Aggregated result from a batch UAT run."""

    results: list[tuple[str, UATResult]] = field(default_factory=list)
    total_tasks: int = 0
    tasks_passed: int = 0
    tasks_failed: int = 0

    @property
    def pass_rate(self) -> float:
        return (self.tasks_passed / max(self.total_tasks, 1)) * 100


class BatchUAT:
    """Runs UAT across multiple tasks in parallel."""

    def __init__(
        self,
        *,
        workers: int = DEFAULT_WORKERS,
        timeout: int = DEFAULT_TIMEOUT,
        max_tests_per_sp: int = 5,
    ) -> None:
        self._workers = max(1, workers)
        self._timeout = timeout
        self._max_tests_per_sp = max_tests_per_sp
        self._pipeline = UATPipeline(timeout=timeout, max_tests_per_sp=max_tests_per_sp)

    def run_sprint(self, sprint_id: str, project_dir: Path) -> BatchResult:
        """Run UAT for all completed tasks in a sprint.

        Scans task files for completed tasks and runs UAT in parallel.
        The *sprint_id* is currently used for logging; task filtering
        is based on completion status.
        """
        logger.info("batch_uat_sprint_start", sprint_id=sprint_id)
        task_ids = self._find_completed_task_ids(project_dir)
        return self._run_batch(task_ids, project_dir)

    def run_range(self, start_id: str, end_id: str, project_dir: Path) -> BatchResult:
        """Run UAT for a range of completed tasks (e.g. '040' to '050')."""
        logger.info("batch_uat_range", start=start_id, end=end_id)
        all_ids = self._find_completed_task_ids(project_dir)

        start_num = int(start_id.lstrip("0") or "0")
        end_num = int(end_id.lstrip("0") or "0")
        filtered = []
        for tid in all_ids:
            try:
                num = int(tid.lstrip("0") or "0")
                if start_num <= num <= end_num:
                    filtered.append(tid)
            except ValueError:
                continue

        return self._run_batch(filtered, project_dir)

    def run_all(self, project_dir: Path) -> BatchResult:
        """Run UAT for all completed tasks in the project."""
        logger.info("batch_uat_all")
        task_ids = self._find_completed_task_ids(project_dir)
        return self._run_batch(task_ids, project_dir)

    def run_tasks(self, task_ids: list[str], project_dir: Path) -> BatchResult:
        """Run UAT for a specific list of task IDs."""
        return self._run_batch(task_ids, project_dir)

    # -- internal ---------------------------------------------------------

    def _find_completed_task_ids(self, project_dir: Path) -> list[str]:
        """Find all completed task IDs across task files."""
        task_dir = project_dir / "tasks"
        if not task_dir.exists():
            return []

        parser = TaskParser()
        index_path = task_dir / "tasks-index.md"
        if not index_path.exists():
            return []

        index = parser.parse_task_index(index_path)
        completed: list[str] = []

        for entry in index.file_index:
            file_path = task_dir / entry.file
            if not file_path.exists():
                continue
            tasks = parser.parse_task_file(file_path)
            for task in tasks:
                if task.complete:
                    completed.append(task.id)

        return completed

    def _run_batch(self, task_ids: list[str], project_dir: Path) -> BatchResult:
        """Execute UAT pipeline for multiple tasks in parallel."""
        if not task_ids:
            logger.warning("batch_uat_no_tasks")
            return BatchResult()

        total = len(task_ids)
        logger.info("batch_uat_start", total=total, workers=self._workers)

        results: list[tuple[str, UATResult]] = []
        passed = 0
        failed = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=self._workers) as executor:
            future_to_id = {
                executor.submit(self._pipeline.run, tid, project_dir): tid for tid in task_ids
            }

            for future in concurrent.futures.as_completed(future_to_id):
                tid = future_to_id[future]
                try:
                    result = future.result()
                except Exception as exc:
                    logger.error("batch_uat_task_error", task_id=tid, error=str(exc))
                    result = UATResult(raw_output=f"Error: {exc}")

                results.append((tid, result))
                if result.overall_pass:
                    passed += 1
                else:
                    failed += 1

                completed = passed + failed
                logger.info(
                    "batch_uat_progress",
                    completed=completed,
                    total=total,
                    pct=round(completed / total * 100, 1),
                )

        logger.info(
            "batch_uat_complete",
            total=total,
            passed=passed,
            failed=failed,
        )

        return BatchResult(
            results=results,
            total_tasks=total,
            tasks_passed=passed,
            tasks_failed=failed,
        )
