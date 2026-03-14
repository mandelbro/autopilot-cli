"""Tests for UAT reporter."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

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


# ---------------------------------------------------------------------------
# Helpers for coverage / gaps tests
# ---------------------------------------------------------------------------


def _make_fake_matrix(entries_data: list[dict]) -> MagicMock:
    """Build a mock TraceabilityMatrix with entries."""
    mock = MagicMock()
    entries = []
    for d in entries_data:
        entry = MagicMock()
        entry.spec_id = d.get("spec_id", "R001")
        entry.spec_document = d.get("spec_document", "RFC")
        entry.spec_section = d.get("spec_section", "Section 1")
        entry.requirement_text = d.get("requirement_text", "Must do X")
        entry.uat_status = d.get("uat_status", "untested")
        entries.append(entry)
    mock.entries = entries
    mock.total_requirements = len(entries)
    mock.requirements_covered = sum(1 for e in entries if e.uat_status != "untested")
    mock.coverage_percentage = (mock.requirements_covered / max(mock.total_requirements, 1)) * 100
    return mock


# ---------------------------------------------------------------------------
# Coverage rendering tests
# ---------------------------------------------------------------------------


class TestRenderCoverage:
    def test_returns_string_with_progress(self, reporter: UATReporter) -> None:
        matrix = _make_fake_matrix(
            [
                {"spec_document": "RFC", "uat_status": "passed"},
                {"spec_document": "RFC", "uat_status": "untested"},
            ]
        )
        output = reporter.render_coverage(matrix)
        assert isinstance(output, str)
        assert "50.0%" in output

    def test_shows_per_document_grouping(self, reporter: UATReporter) -> None:
        matrix = _make_fake_matrix(
            [
                {"spec_document": "RFC", "uat_status": "passed"},
                {"spec_document": "RFC", "uat_status": "passed"},
                {"spec_document": "Discovery", "uat_status": "untested"},
                {"spec_document": "Discovery", "uat_status": "passed"},
            ]
        )
        output = reporter.render_coverage(matrix)
        assert "RFC" in output
        assert "Discovery" in output

    def test_shows_total(self, reporter: UATReporter) -> None:
        matrix = _make_fake_matrix(
            [
                {"spec_document": "RFC", "uat_status": "passed"},
                {"spec_document": "RFC", "uat_status": "untested"},
                {"spec_document": "RFC", "uat_status": "untested"},
            ]
        )
        output = reporter.render_coverage(matrix)
        assert "Total:" in output
        assert "1/3" in output

    def test_shows_spec_coverage_heading(self, reporter: UATReporter) -> None:
        matrix = _make_fake_matrix([{"spec_document": "RFC", "uat_status": "passed"}])
        output = reporter.render_coverage(matrix)
        assert "Spec Coverage" in output


# ---------------------------------------------------------------------------
# Gaps rendering tests
# ---------------------------------------------------------------------------


class TestRenderGaps:
    def test_shows_untested_entries(self, reporter: UATReporter) -> None:
        matrix = _make_fake_matrix(
            [
                {"spec_id": "R001", "uat_status": "untested", "requirement_text": "Must do X"},
                {"spec_id": "R002", "uat_status": "passed", "requirement_text": "Must do Y"},
            ]
        )
        output = reporter.render_gaps(matrix)
        assert "R001" in output
        assert "R002" not in output

    def test_phase_filter_separates_current_and_future(self, reporter: UATReporter) -> None:
        matrix = _make_fake_matrix(
            [
                {
                    "spec_id": "R001",
                    "uat_status": "untested",
                    "spec_section": "Phase-1 Auth",
                },
                {
                    "spec_id": "R002",
                    "uat_status": "untested",
                    "spec_section": "Phase-2 Dashboard",
                },
            ]
        )
        output = reporter.render_gaps(matrix, phase="Phase-1")
        assert "Current Phase" in output
        assert "Future" in output

    def test_no_gaps_message(self, reporter: UATReporter) -> None:
        matrix = _make_fake_matrix(
            [
                {"spec_id": "R001", "uat_status": "passed"},
            ]
        )
        output = reporter.render_gaps(matrix)
        assert "No gaps" in output

    def test_truncates_long_requirement_text(self, reporter: UATReporter) -> None:
        long_text = "A" * 120
        matrix = _make_fake_matrix(
            [
                {"spec_id": "R001", "uat_status": "untested", "requirement_text": long_text},
            ]
        )
        output = reporter.render_gaps(matrix)
        # Should not contain the full 120-char string; Rich may use unicode ellipsis
        assert long_text not in output
        assert "..." in output or "\u2026" in output


# ---------------------------------------------------------------------------
# Sprint report tests
# ---------------------------------------------------------------------------


class TestRenderSprintReport:
    def test_aggregates_multiple_results(self, reporter: UATReporter) -> None:
        results = [
            UATResult(overall_pass=True, score=1.0, test_count=5, passed=5, failed=0, skipped=0),
            UATResult(overall_pass=False, score=0.6, test_count=10, passed=6, failed=3, skipped=1),
        ]
        matrix = _make_fake_matrix(
            [
                {"uat_status": "passed"},
                {"uat_status": "passed"},
                {"uat_status": "untested"},
            ]
        )
        output = reporter.render_sprint_report(results, matrix)
        assert "Sprint UAT Summary" in output
        assert "15" in output  # total tests
        assert "11" in output  # total passed

    def test_shows_pass_rate(self, reporter: UATReporter) -> None:
        results = [
            UATResult(overall_pass=True, score=1.0, test_count=10, passed=8, failed=2, skipped=0),
        ]
        matrix = _make_fake_matrix([{"uat_status": "passed"}])
        output = reporter.render_sprint_report(results, matrix)
        assert "80.0%" in output

    def test_shows_coverage_from_matrix(self, reporter: UATReporter) -> None:
        results = [
            UATResult(overall_pass=True, score=1.0, test_count=5, passed=5, failed=0, skipped=0),
        ]
        matrix = _make_fake_matrix(
            [
                {"uat_status": "passed"},
                {"uat_status": "passed"},
                {"uat_status": "untested"},
            ]
        )
        output = reporter.render_sprint_report(results, matrix)
        assert "2/3" in output
        assert "66.7%" in output
