"""Tests for UAT reporter."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from rich.console import Console

if TYPE_CHECKING:
    from pathlib import Path

from autopilot.uat.reporter import UATReporter
from autopilot.uat.test_executor import (
    CategoryBreakdown,
    TestFailure,
    UATResult,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def reporter() -> UATReporter:
    return UATReporter(console=Console(quiet=True))


@pytest.fixture()
def passing_result() -> UATResult:
    return UATResult(
        overall_pass=True,
        score=1.0,
        test_count=5,
        passed=5,
        failed=0,
        skipped=0,
        categories=[
            CategoryBreakdown(category="acceptance", total=5, passed=5),
        ],
    )


@pytest.fixture()
def failing_result() -> UATResult:
    return UATResult(
        overall_pass=False,
        score=0.6,
        test_count=5,
        passed=3,
        failed=1,
        skipped=1,
        categories=[
            CategoryBreakdown(category="acceptance", total=3, passed=2, failed=1),
            CategoryBreakdown(category="ux", total=2, passed=1, skipped=1),
        ],
        failures=[
            TestFailure(
                test_name="test_task_046_parser_works",
                category="acceptance",
                spec_reference="RFC Section 3.4",
                expected="valid output",
                actual="error occurred",
                suggestion="Check parser input format",
            ),
        ],
    )


@pytest.fixture()
def partial_result() -> UATResult:
    return UATResult(
        overall_pass=False,
        score=0.0,
        test_count=3,
        passed=0,
        failed=0,
        skipped=3,
    )


# ---------------------------------------------------------------------------
# Console rendering tests
# ---------------------------------------------------------------------------


class TestRenderTaskReport:
    def test_passing_report_contains_pass(
        self, reporter: UATReporter, passing_result: UATResult
    ) -> None:
        output = reporter.render_task_report(passing_result, task_id="046")
        assert "PASS" in output

    def test_failing_report_contains_fail(
        self, reporter: UATReporter, failing_result: UATResult
    ) -> None:
        output = reporter.render_task_report(failing_result, task_id="046")
        assert "FAIL" in output

    def test_report_contains_score(self, reporter: UATReporter, passing_result: UATResult) -> None:
        output = reporter.render_task_report(passing_result, task_id="046")
        assert "100%" in output

    def test_report_contains_task_id(
        self, reporter: UATReporter, passing_result: UATResult
    ) -> None:
        output = reporter.render_task_report(passing_result, task_id="046")
        assert "046" in output

    def test_report_without_task_id(self, reporter: UATReporter, passing_result: UATResult) -> None:
        output = reporter.render_task_report(passing_result)
        assert "UAT Report" in output

    def test_failure_details_shown(self, reporter: UATReporter, failing_result: UATResult) -> None:
        output = reporter.render_task_report(failing_result, task_id="046")
        assert "test_task_046_parser_works" in output
        assert "Check parser input format" in output

    def test_partial_report_shows_partial(
        self, reporter: UATReporter, partial_result: UATResult
    ) -> None:
        output = reporter.render_task_report(partial_result, task_id="099")
        assert "PARTIAL" in output


# ---------------------------------------------------------------------------
# Markdown rendering tests
# ---------------------------------------------------------------------------


class TestRenderToMarkdown:
    def test_markdown_has_title(self, reporter: UATReporter, passing_result: UATResult) -> None:
        md = reporter.render_to_markdown(passing_result, task_id="046")
        assert "# UAT Report - Task 046" in md

    def test_markdown_has_summary_table(
        self, reporter: UATReporter, passing_result: UATResult
    ) -> None:
        md = reporter.render_to_markdown(passing_result, task_id="046")
        assert "| Total | 5 |" in md
        assert "| Passed | 5 |" in md

    def test_markdown_has_categories(
        self, reporter: UATReporter, failing_result: UATResult
    ) -> None:
        md = reporter.render_to_markdown(failing_result, task_id="046")
        assert "## Categories" in md
        assert "acceptance" in md

    def test_markdown_has_failures(self, reporter: UATReporter, failing_result: UATResult) -> None:
        md = reporter.render_to_markdown(failing_result, task_id="046")
        assert "## Failures" in md
        assert "test_task_046_parser_works" in md

    def test_markdown_status_pass(self, reporter: UATReporter, passing_result: UATResult) -> None:
        md = reporter.render_to_markdown(passing_result)
        assert "**Status**: PASS" in md

    def test_markdown_status_fail(self, reporter: UATReporter, failing_result: UATResult) -> None:
        md = reporter.render_to_markdown(failing_result)
        assert "**Status**: FAIL" in md


# ---------------------------------------------------------------------------
# File saving tests
# ---------------------------------------------------------------------------


class TestSaveReport:
    def test_saves_to_standard_path(
        self, reporter: UATReporter, passing_result: UATResult, tmp_path: Path
    ) -> None:
        path = reporter.save_report(passing_result, task_id="046", project_dir=tmp_path)
        assert path.exists()
        assert path.name == "task-046-uat.md"
        assert ".autopilot/uat/reports" in str(path)

    def test_report_content_is_markdown(
        self, reporter: UATReporter, passing_result: UATResult, tmp_path: Path
    ) -> None:
        path = reporter.save_report(passing_result, task_id="046", project_dir=tmp_path)
        content = path.read_text(encoding="utf-8")
        assert content.startswith("# UAT Report")

    def test_creates_directory_if_missing(
        self, reporter: UATReporter, passing_result: UATResult, tmp_path: Path
    ) -> None:
        project = tmp_path / "new_project"
        path = reporter.save_report(passing_result, task_id="001", project_dir=project)
        assert path.exists()
