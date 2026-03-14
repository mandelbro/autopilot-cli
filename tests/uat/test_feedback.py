"""Tests for UAT feedback loop (Task 076)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from autopilot.uat.feedback import FeedbackLoop, FeedbackMode
from autopilot.uat.test_executor import TestFailure, UATResult


@pytest.fixture()
def project_dir(tmp_path: Path) -> Path:
    """Create a minimal project with a completed task."""
    task_dir = tmp_path / "tasks"
    task_dir.mkdir()

    index = (
        "## Overall Project Task Summary\n\n"
        "- **Total Tasks**: 1\n"
        "- **Pending**: 0\n"
        "- **Complete**: 1\n"
        "- **Total Points**: 3\n"
        "- **Points Complete**: 3\n\n"
        "## Task File Index\n\n"
        "- `tasks/tasks-1.md`: Contains Tasks 001 - 001 (1 tasks, 3 points)\n"
    )
    (task_dir / "tasks-index.md").write_text(index)

    tasks = (
        "## Summary (tasks-1.md)\n\n"
        "- **Tasks in this file**: 1\n"
        "- **Task IDs**: 001 - 001\n"
        "- **Total Points**: 3\n\n"
        "## Tasks\n\n"
        "### Task ID: 001\n\n"
        "- **Title**: Test feature\n"
        "- **File**: src/feature.py\n"
        "- **Complete**: [x]\n"
        "- **Sprint Points**: 3\n\n"
        "---\n"
    )
    (task_dir / "tasks-1.md").write_text(tasks)

    return tmp_path


class TestFeedbackMode:
    def test_advisory_constant(self) -> None:
        assert FeedbackMode.ADVISORY == "advisory"

    def test_gated_constant(self) -> None:
        assert FeedbackMode.GATED == "gated"


class TestFeedbackLoop:
    def test_default_mode_is_advisory(self) -> None:
        fb = FeedbackLoop()
        assert fb.mode == "advisory"
        assert fb.threshold == 0.90

    def test_invalid_mode_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid feedback mode"):
            FeedbackLoop(mode="unknown")

    def test_advisory_mode_logs_pass(self, project_dir: Path) -> None:
        fb = FeedbackLoop(mode="advisory")
        result = UATResult(overall_pass=True, score=1.0, test_count=5, passed=5)
        status = fb.process_result(result, "001", project_dir)
        assert status == "PASS"

    def test_advisory_mode_logs_fail_without_reverting(self, project_dir: Path) -> None:
        fb = FeedbackLoop(mode="advisory")
        result = UATResult(overall_pass=False, score=0.5, test_count=4, passed=2, failed=2)
        status = fb.process_result(result, "001", project_dir)
        assert status == "FAIL"

        # Task should still be marked complete
        task_file = project_dir / "tasks" / "tasks-1.md"
        content = task_file.read_text()
        assert "[x]" in content

    def test_gated_mode_reverts_on_fail(self, project_dir: Path) -> None:
        fb = FeedbackLoop(mode="gated", threshold=0.90)
        result = UATResult(
            overall_pass=False,
            score=0.5,
            test_count=4,
            passed=2,
            failed=2,
            failures=[
                TestFailure(
                    test_name="test_something",
                    suggestion="Fix the thing",
                )
            ],
        )
        status = fb.process_result(result, "001", project_dir)
        assert status == "FAIL"

        # Task should be reverted to incomplete
        task_file = project_dir / "tasks" / "tasks-1.md"
        content = task_file.read_text()
        assert "[ ]" in content

        # Index should be updated
        index_file = project_dir / "tasks" / "tasks-index.md"
        index_content = index_file.read_text()
        assert "**Pending**: 1" in index_content
        assert "**Complete**: 0" in index_content

    def test_gated_mode_pass_no_revert(self, project_dir: Path) -> None:
        fb = FeedbackLoop(mode="gated", threshold=0.90)
        result = UATResult(overall_pass=True, score=1.0, test_count=5, passed=5)
        status = fb.process_result(result, "001", project_dir)
        assert status == "PASS"

        # Task should remain complete
        task_file = project_dir / "tasks" / "tasks-1.md"
        content = task_file.read_text()
        assert "[x]" in content

    def test_partial_status_above_threshold(self, project_dir: Path) -> None:
        fb = FeedbackLoop(mode="advisory", threshold=0.80)
        result = UATResult(overall_pass=False, score=0.85, test_count=20, passed=17, failed=3)
        status = fb.process_result(result, "001", project_dir)
        assert status == "PARTIAL"

    def test_uat_status_written_to_task(self, project_dir: Path) -> None:
        fb = FeedbackLoop(mode="advisory")
        result = UATResult(overall_pass=True, score=1.0, test_count=1, passed=1)
        fb.process_result(result, "001", project_dir)

        task_file = project_dir / "tasks" / "tasks-1.md"
        content = task_file.read_text()
        assert "**UAT Status**: PASS" in content

    def test_feedback_section_appended_on_gated_fail(self, project_dir: Path) -> None:
        fb = FeedbackLoop(mode="gated", threshold=0.90)
        result = UATResult(
            overall_pass=False,
            score=0.4,
            test_count=5,
            passed=2,
            failed=3,
            failures=[
                TestFailure(test_name="test_a", suggestion="Fix A"),
                TestFailure(test_name="test_b", suggestion="Fix B"),
            ],
        )
        fb.process_result(result, "001", project_dir)

        task_file = project_dir / "tasks" / "tasks-1.md"
        content = task_file.read_text()
        assert "#### UAT Feedback" in content
        assert "test_a" in content
        assert "Fix A" in content

    def test_threshold_configurable(self) -> None:
        fb = FeedbackLoop(threshold=0.75)
        assert fb.threshold == 0.75
