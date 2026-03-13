"""Tests for UAT pipeline."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from autopilot.uat.pipeline import UATPipeline
from autopilot.uat.task_context import TaskContext
from autopilot.uat.test_executor import UATResult
from autopilot.uat.test_generator import GeneratedTestFile

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def pipeline() -> UATPipeline:
    return UATPipeline(timeout=30, max_tests_per_sp=5)


@pytest.fixture()
def project_dir(tmp_path: Path) -> Path:
    """Create a minimal project with task files."""
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()

    index = tasks_dir / "tasks-index.md"
    index.write_text(
        "## Overall Project Task Summary\n"
        "\n"
        "- **Total Tasks**: 1\n"
        "- **Pending**: 0\n"
        "- **Complete**: 1\n"
        "- **Total Points**: 3\n"
        "- **Points Complete**: 3\n"
        "\n"
        "## Task File Index\n"
        "\n"
        "- `tasks/tasks-1.md`: Contains Tasks 046 - 046 (1 tasks, 3 points)\n",
        encoding="utf-8",
    )

    task_file = tasks_dir / "tasks-1.md"
    task_file.write_text(
        "## Tasks\n"
        "\n"
        "### Task ID: 046\n"
        "\n"
        "- **Title**: Spec Index Builder\n"
        "- **File**: src/autopilot/uat/spec_index.py\n"
        "- **Complete**: [x]\n"
        "- **Sprint Points**: 3\n"
        "\n"
        "- **User Story (business-facing)**: As a dev, I want spec indexing.\n"
        "- **Outcome (what this delivers)**: Spec index.\n"
        "\n"
        "#### Prompt:\n"
        "\n"
        "```markdown\n"
        "**Objective:** Build spec index.\n"
        "\n"
        "**Acceptance Criteria:**\n"
        "- [ ] Parser extracts sections\n"
        "- [ ] Index is serializable\n"
        "```\n",
        encoding="utf-8",
    )

    return tmp_path


# ---------------------------------------------------------------------------
# Pipeline tests
# ---------------------------------------------------------------------------


class TestUATPipeline:
    def test_run_returns_uat_result(self, pipeline: UATPipeline, project_dir: Path) -> None:
        """Pipeline should return a UATResult even with generated stubs."""
        result = pipeline.run("046", project_dir)
        assert isinstance(result, UATResult)

    def test_run_nonexistent_task(self, pipeline: UATPipeline, tmp_path: Path) -> None:
        """Pipeline handles missing task gracefully."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        # Create minimal index
        (tasks_dir / "tasks-index.md").write_text(
            "## Overall Project Task Summary\n- **Total Tasks**: 0\n## Task File Index\n",
            encoding="utf-8",
        )
        result = pipeline.run("999", tmp_path)
        assert isinstance(result, UATResult)
        # No acceptance criteria means no tests generated
        assert "No acceptance criteria" in result.raw_output

    def test_run_handles_context_error(self, pipeline: UATPipeline, tmp_path: Path) -> None:
        """Pipeline handles errors in context loading."""
        # No tasks/ directory at all
        result = pipeline.run("001", tmp_path)
        assert isinstance(result, UATResult)
        assert result.overall_pass is False

    @patch("autopilot.uat.pipeline.TestExecutor")
    @patch("autopilot.uat.pipeline.TestGenerator")
    @patch("autopilot.uat.pipeline.load_task_context")
    def test_pipeline_calls_all_steps(
        self,
        mock_load: MagicMock,
        mock_gen_cls: MagicMock,
        mock_exec_cls: MagicMock,
        pipeline: UATPipeline,
        tmp_path: Path,
    ) -> None:
        """Verify pipeline calls context, generator, executor, and reporter."""
        mock_load.return_value = TaskContext(
            task_id="046",
            title="Test",
            sprint_points=3,
            acceptance_criteria=["Works"],
        )

        mock_gen = mock_gen_cls.return_value
        mock_gen.generate_acceptance_tests.return_value = GeneratedTestFile(
            file_path="tests/uat/test_task_046_uat.py",
            test_count=1,
            test_names=["test_task_046_works"],
            source_code="def test_task_046_works(): pass\n",
        )
        mock_gen.write_test_file.return_value = tmp_path / "tests" / "test_task_046_uat.py"

        mock_exec = mock_exec_cls.return_value
        mock_exec.run.return_value = UATResult(
            overall_pass=True,
            score=1.0,
            test_count=1,
            passed=1,
        )

        result = pipeline.run("046", tmp_path)

        mock_load.assert_called_once()
        mock_gen.generate_acceptance_tests.assert_called_once()
        mock_exec.run.assert_called_once()
        assert result.overall_pass is True

    @patch("autopilot.uat.pipeline.TestGenerator")
    @patch("autopilot.uat.pipeline.load_task_context")
    def test_pipeline_handles_generation_error(
        self,
        mock_load: MagicMock,
        mock_gen_cls: MagicMock,
        pipeline: UATPipeline,
        tmp_path: Path,
    ) -> None:
        """Pipeline returns error result when test generation fails."""
        mock_load.return_value = TaskContext(
            task_id="046",
            title="Test",
            acceptance_criteria=["Works"],
        )
        mock_gen = mock_gen_cls.return_value
        mock_gen.generate_acceptance_tests.side_effect = RuntimeError("gen failed")

        result = pipeline.run("046", tmp_path)
        assert result.overall_pass is False
        assert "gen failed" in result.raw_output

    @patch("autopilot.uat.pipeline.TestExecutor")
    @patch("autopilot.uat.pipeline.TestGenerator")
    @patch("autopilot.uat.pipeline.load_task_context")
    def test_pipeline_handles_execution_error(
        self,
        mock_load: MagicMock,
        mock_gen_cls: MagicMock,
        mock_exec_cls: MagicMock,
        pipeline: UATPipeline,
        tmp_path: Path,
    ) -> None:
        """Pipeline returns error result when test execution fails."""
        mock_load.return_value = TaskContext(
            task_id="046",
            title="Test",
            acceptance_criteria=["Works"],
        )
        mock_gen = mock_gen_cls.return_value
        mock_gen.generate_acceptance_tests.return_value = GeneratedTestFile(
            file_path="tests/uat/test_uat.py",
            test_count=1,
            test_names=["test_x"],
            source_code="pass\n",
        )
        mock_gen.write_test_file.return_value = tmp_path / "test.py"

        mock_exec = mock_exec_cls.return_value
        mock_exec.run.side_effect = RuntimeError("exec failed")

        result = pipeline.run("046", tmp_path)
        assert result.overall_pass is False
        assert "exec failed" in result.raw_output
