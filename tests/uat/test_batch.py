"""Tests for UAT batch mode (Task 074)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from autopilot.uat.batch import BatchProgress, BatchResult, BatchUAT
from autopilot.uat.test_executor import UATResult

if TYPE_CHECKING:
    from pathlib import Path


class TestBatchProgress:
    def test_defaults(self) -> None:
        p = BatchProgress()
        assert p.remaining == 0
        assert p.percentage == 0.0

    def test_percentage_calculation(self) -> None:
        p = BatchProgress(total=10, completed=3)
        assert p.percentage == 30.0
        assert p.remaining == 7

    def test_zero_total_safe(self) -> None:
        p = BatchProgress(total=0, completed=0)
        assert p.percentage == 0.0


class TestBatchResult:
    def test_defaults(self) -> None:
        r = BatchResult()
        assert r.pass_rate == 0.0

    def test_pass_rate(self) -> None:
        r = BatchResult(total_tasks=10, tasks_passed=8, tasks_failed=2)
        assert r.pass_rate == 80.0


class TestBatchUAT:
    @pytest.fixture()
    def project_dir(self, tmp_path: Path) -> Path:
        """Create a minimal project structure with completed tasks."""
        task_dir = tmp_path / "tasks"
        task_dir.mkdir()

        # Create index
        index = (
            "## Overall Project Task Summary\n\n"
            "- **Total Tasks**: 3\n"
            "- **Pending**: 0\n"
            "- **Complete**: 3\n"
            "- **Total Points**: 9\n"
            "- **Points Complete**: 9\n\n"
            "## Task File Index\n\n"
            "- `tasks/tasks-1.md`: Contains Tasks 001 - 003 (3 tasks, 9 points)\n"
        )
        (task_dir / "tasks-index.md").write_text(index)

        tasks = (
            "## Summary (tasks-1.md)\n\n"
            "- **Tasks in this file**: 3\n"
            "- **Task IDs**: 001 - 003\n"
            "- **Total Points**: 9\n\n"
            "## Tasks\n\n"
            "### Task ID: 001\n\n"
            "- **Title**: Task one\n"
            "- **File**: src/one.py\n"
            "- **Complete**: [x]\n"
            "- **Sprint Points**: 3\n\n"
            "### Task ID: 002\n\n"
            "- **Title**: Task two\n"
            "- **File**: src/two.py\n"
            "- **Complete**: [x]\n"
            "- **Sprint Points**: 3\n\n"
            "### Task ID: 003\n\n"
            "- **Title**: Task three\n"
            "- **File**: src/three.py\n"
            "- **Complete**: [x]\n"
            "- **Sprint Points**: 3\n"
        )
        (task_dir / "tasks-1.md").write_text(tasks)

        return tmp_path

    @patch("autopilot.uat.batch.UATPipeline")
    def test_run_all_parallel(self, mock_pipeline_cls: MagicMock, project_dir: Path) -> None:
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = UATResult(overall_pass=True, score=1.0, test_count=1, passed=1)
        mock_pipeline_cls.return_value = mock_pipeline

        batch = BatchUAT(workers=2)
        batch._pipeline = mock_pipeline
        result = batch.run_all(project_dir)

        assert result.total_tasks == 3
        assert result.tasks_passed == 3
        assert result.tasks_failed == 0
        assert mock_pipeline.run.call_count == 3

    @patch("autopilot.uat.batch.UATPipeline")
    def test_run_range(self, mock_pipeline_cls: MagicMock, project_dir: Path) -> None:
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = UATResult(overall_pass=True, score=1.0, test_count=1, passed=1)
        mock_pipeline_cls.return_value = mock_pipeline

        batch = BatchUAT()
        batch._pipeline = mock_pipeline
        result = batch.run_range("001", "002", project_dir)

        assert result.total_tasks == 2

    def test_run_empty_project(self, tmp_path: Path) -> None:
        batch = BatchUAT()
        result = batch.run_all(tmp_path)
        assert result.total_tasks == 0

    @patch("autopilot.uat.batch.UATPipeline")
    def test_handles_task_error(self, mock_pipeline_cls: MagicMock, project_dir: Path) -> None:
        mock_pipeline = MagicMock()
        mock_pipeline.run.side_effect = RuntimeError("boom")
        mock_pipeline_cls.return_value = mock_pipeline

        batch = BatchUAT(workers=1)
        batch._pipeline = mock_pipeline
        result = batch.run_all(project_dir)

        assert result.total_tasks == 3
        assert result.tasks_failed == 3

    def test_worker_count_minimum(self) -> None:
        batch = BatchUAT(workers=0)
        assert batch._workers == 1
