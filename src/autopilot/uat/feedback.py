"""UAT feedback loop with advisory and gated modes (Task 076).

Implements configurable feedback that either logs results (advisory)
or reverts task status on failure (gated), with threshold-based scoring.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path  # noqa: TC003 — used at runtime

import structlog

from autopilot.core.task import TaskParser, update_task_status
from autopilot.uat.test_executor import UATResult  # noqa: TC001

logger = structlog.get_logger(__name__)

DEFAULT_THRESHOLD = 0.90


class FeedbackMode:
    """Valid feedback mode constants."""

    ADVISORY = "advisory"
    GATED = "gated"


class FeedbackLoop:
    """Processes UAT results with configurable advisory or gated feedback."""

    def __init__(
        self,
        *,
        mode: str = FeedbackMode.ADVISORY,
        threshold: float = DEFAULT_THRESHOLD,
    ) -> None:
        if mode not in (FeedbackMode.ADVISORY, FeedbackMode.GATED):
            msg = f"Invalid feedback mode: {mode!r}. Use 'advisory' or 'gated'."
            raise ValueError(msg)
        self._mode = mode
        self._threshold = threshold

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def threshold(self) -> float:
        return self._threshold

    def process_result(
        self,
        result: UATResult,
        task_id: str,
        project_dir: Path,
    ) -> str:
        """Process a UAT result according to the configured mode.

        Returns the UAT status: "PASS", "FAIL", or "PARTIAL".
        """
        status = self._compute_status(result)

        logger.info(
            "uat_feedback",
            task_id=task_id,
            mode=self._mode,
            score=result.score,
            status=status,
        )

        # Update the task file with UAT status
        self._update_task_uat_status(task_id, status, project_dir)

        if self._mode == FeedbackMode.GATED and status == "FAIL":
            self._revert_task(task_id, result, project_dir)

        return status

    def _compute_status(self, result: UATResult) -> str:
        """Determine UAT status from result score and threshold."""
        if result.overall_pass:
            return "PASS"
        if result.score >= self._threshold:
            return "PARTIAL"
        return "FAIL"

    def _update_task_uat_status(
        self, task_id: str, status: str, project_dir: Path
    ) -> None:
        """Update the UAT Status field in the task file."""
        task_dir = project_dir / "tasks"
        parser = TaskParser()
        index_path = task_dir / "tasks-index.md"
        if not index_path.exists():
            return

        index = parser.parse_task_index(index_path)

        for entry in index.file_index:
            file_path = task_dir / entry.file
            if not file_path.exists():
                continue
            tasks = parser.parse_task_file(file_path)
            for task in tasks:
                normalized_task = task.id.strip().lstrip("0") or "0"
                normalized_search = task_id.strip().lstrip("0") or "0"
                if normalized_task == normalized_search:
                    self._write_uat_status(file_path, task_id, status)
                    return

    def _write_uat_status(
        self, file_path: Path, task_id: str, status: str
    ) -> None:
        """Write or update the UAT Status field in a task file."""
        text = file_path.read_text(encoding="utf-8")
        lines = text.split("\n")
        result_lines: list[str] = []

        normalized = task_id.strip().lstrip("0") or "0"
        in_target = False
        status_written = False
        task_header_re = re.compile(r"^###\s+Task\s+ID:\s*(.+)$", re.IGNORECASE)

        for line in lines:
            m = task_header_re.match(line)
            if m:
                tid = m.group(1).strip().lstrip("0") or "0"
                in_target = tid == normalized
                status_written = False

            # Update existing UAT Status line
            if in_target and re.match(r"^\s*-\s+\*\*UAT Status\*\*:", line):
                result_lines.append(f"- **UAT Status**: {status}")
                status_written = True
                continue

            # Insert UAT Status after Complete line if not already present
            if (
                in_target
                and not status_written
                and re.match(r"^\s*-\s+\*\*Sprint Points\*\*:", line)
            ):
                result_lines.append(line)
                result_lines.append(f"- **UAT Status**: {status}")
                status_written = True
                continue

            result_lines.append(line)

        file_path.write_text("\n".join(result_lines), encoding="utf-8")

    def _revert_task(
        self, task_id: str, result: UATResult, project_dir: Path
    ) -> None:
        """Revert task completion status and append UAT feedback section."""
        logger.warning(
            "uat_gated_revert",
            task_id=task_id,
            score=result.score,
            threshold=self._threshold,
        )

        task_dir = project_dir / "tasks"

        # Revert Complete: [x] -> [ ] and update index
        try:
            update_task_status(task_dir, task_id, complete=False)
        except (FileNotFoundError, ValueError) as exc:
            logger.error("uat_revert_failed", task_id=task_id, error=str(exc))
            return

        # Append UAT Feedback section to task file
        self._append_feedback_section(task_id, result, project_dir)

    def _append_feedback_section(
        self,
        task_id: str,
        result: UATResult,
        project_dir: Path,
    ) -> None:
        """Append a UAT Feedback section to the task in its task file."""
        task_dir = project_dir / "tasks"
        parser = TaskParser()
        index_path = task_dir / "tasks-index.md"
        if not index_path.exists():
            return

        index = parser.parse_task_index(index_path)
        normalized = task_id.strip().lstrip("0") or "0"

        for entry in index.file_index:
            file_path = task_dir / entry.file
            if not file_path.exists():
                continue
            tasks = parser.parse_task_file(file_path)
            for task in tasks:
                tid = task.id.strip().lstrip("0") or "0"
                if tid == normalized:
                    self._write_feedback(file_path, task_id, result)
                    return

    def _write_feedback(
        self, file_path: Path, task_id: str, result: UATResult
    ) -> None:
        """Insert UAT feedback section before the task's closing separator."""
        text = file_path.read_text(encoding="utf-8")
        lines = text.split("\n")
        result_lines: list[str] = []

        normalized = task_id.strip().lstrip("0") or "0"
        task_header_re = re.compile(r"^###\s+Task\s+ID:\s*(.+)$", re.IGNORECASE)
        in_target = False
        feedback_inserted = False

        date_str = datetime.now(UTC).strftime("%Y-%m-%d")

        feedback_lines = [
            "",
            f"#### UAT Feedback ({date_str}):",
            "",
            f"- **Score**: {result.score:.0%}",
            f"- **Tests**: {result.passed} passed, {result.failed} failed, "
            f"{result.skipped} skipped",
        ]

        if result.failures:
            feedback_lines.append("- **Failures**:")
            for f in result.failures[:5]:  # Limit to 5 failures
                feedback_lines.append(f"  - `{f.test_name}`: {f.suggestion}")

        feedback_lines.append("")

        for _i, line in enumerate(lines):
            m = task_header_re.match(line)
            if m:
                tid = m.group(1).strip().lstrip("0") or "0"
                if in_target and not feedback_inserted:
                    # Insert before next task header
                    result_lines.extend(feedback_lines)
                    feedback_inserted = True
                in_target = tid == normalized

            # Insert before separator (---) at end of target task
            if in_target and not feedback_inserted and line.strip() == "---":
                result_lines.extend(feedback_lines)
                feedback_inserted = True

            result_lines.append(line)

        # If task is the last one and no separator found
        if in_target and not feedback_inserted:
            result_lines.extend(feedback_lines)

        file_path.write_text("\n".join(result_lines), encoding="utf-8")
