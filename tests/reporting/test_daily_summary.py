"""Tests for daily summary report aggregation (Task 041)."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from autopilot.reporting.cycle_reports import CycleReportData, DispatchOutcome
from autopilot.reporting.daily_summary import DailySummary, DailySummaryGenerator


@pytest.fixture()
def reports_dir(tmp_path):
    d = tmp_path / "cycle-reports"
    d.mkdir()
    return d


@pytest.fixture()
def generator(reports_dir):
    return DailySummaryGenerator(reports_dir)


def _make_report(
    cycle_id: str = "c1",
    project: str = "proj",
    status: str = "COMPLETED",
    dispatches: tuple[DispatchOutcome, ...] = (),
) -> CycleReportData:
    return CycleReportData(
        cycle_id=cycle_id,
        project_id=project,
        status=status,
        started_at=datetime(2026, 3, 13, 10, 0, tzinfo=UTC),
        ended_at=datetime(2026, 3, 13, 10, 5, tzinfo=UTC),
        duration_seconds=300.0,
        dispatches=dispatches,
    )


class TestAggregate:
    def test_empty_reports(self, generator: DailySummaryGenerator) -> None:
        summary = generator.aggregate([])
        assert summary.cycles_run == 0
        assert summary.total_dispatches == 0

    def test_single_cycle(self, generator: DailySummaryGenerator) -> None:
        dispatches = (
            DispatchOutcome(agent="coder", action="write", status="success", duration_seconds=10.0),
            DispatchOutcome(
                agent="tester", action="test", status="failed", duration_seconds=5.0, error="boom"
            ),
        )
        report = _make_report(dispatches=dispatches)
        summary = generator.aggregate([report])

        assert summary.cycles_run == 1
        assert summary.total_dispatches == 2
        assert summary.succeeded == 1
        assert summary.failed == 1
        assert summary.date == date(2026, 3, 13)
        assert "coder" in summary.agent_breakdown
        assert summary.agent_breakdown["coder"]["success"] == 1
        assert len(summary.notable_errors) == 1

    def test_multiple_cycles(self, generator: DailySummaryGenerator) -> None:
        d1 = (
            DispatchOutcome(agent="coder", action="write", status="success", duration_seconds=10.0),
        )
        d2 = (
            DispatchOutcome(agent="coder", action="fix", status="success", duration_seconds=8.0),
            DispatchOutcome(
                agent="reviewer", action="review", status="success", duration_seconds=3.0
            ),
        )
        reports = [
            _make_report(cycle_id="c1", dispatches=d1),
            _make_report(cycle_id="c2", dispatches=d2),
        ]
        summary = generator.aggregate(reports)

        assert summary.cycles_run == 2
        assert summary.total_dispatches == 3
        assert summary.succeeded == 3
        assert summary.failed == 0
        assert summary.agent_breakdown["coder"]["success"] == 2


class TestGenerate:
    def test_generate_from_project_dir(self, tmp_path, generator: DailySummaryGenerator) -> None:
        """Generate from actual cycle report files in the project directory."""
        # Create .autopilot/board/cycle-reports/ with a report file
        reports_dir = tmp_path / ".autopilot" / "board" / "cycle-reports"
        reports_dir.mkdir(parents=True)

        report_content = """# Cycle Report: cycle-001

- **Project**: myproject
- **Status**: COMPLETED
- **Started**: 2026-03-13T10:00:00+00:00
- **Ended**: 2026-03-13T10:05:00+00:00
- **Duration**: 300.0s

## Summary

- **Total Dispatches**: 2
- **Succeeded**: 1
- **Failed**: 1
- **Success Rate**: 50%
- **Total Dispatch Time**: 15.0s

## Dispatches

| Agent | Action | Status | Duration |
|-------|--------|--------|----------|
| coder | write | pass | 10.0s |
| tester | test | FAIL | 5.0s |
"""
        (reports_dir / "cycle-2026-03-13-001.md").write_text(report_content)

        result = generator.generate(tmp_path, date(2026, 3, 13))

        assert "Daily Summary: 2026-03-13" in result
        assert "Cycles: 1" in result
        assert "coder" in result

    def test_generate_no_reports(self, tmp_path, generator: DailySummaryGenerator) -> None:
        result = generator.generate(tmp_path, date(2026, 3, 13))
        assert "Cycles: 0" in result


class TestRender:
    def test_render_with_errors(self, generator: DailySummaryGenerator) -> None:
        summary = DailySummary(
            date=date(2026, 3, 13),
            cycles_run=2,
            total_dispatches=5,
            succeeded=3,
            failed=2,
            agent_breakdown={
                "coder": {"success": 2, "failed": 1},
                "tester": {"success": 1, "failed": 1},
            },
            notable_errors=["[coder] compile error", "[tester] timeout"],
            total_duration_seconds=600.0,
        )
        result = generator._render(summary)

        assert "2026-03-13" in result
        assert "Cycles: 2" in result
        assert "5" in result  # total dispatches
        assert "## Agents" in result
        assert "## Errors" in result
        assert "compile error" in result

    def test_render_empty(self, generator: DailySummaryGenerator) -> None:
        summary = DailySummary(
            date=date(2026, 3, 13),
            cycles_run=0,
            total_dispatches=0,
            succeeded=0,
            failed=0,
            agent_breakdown={},
            notable_errors=[],
            total_duration_seconds=0.0,
        )
        result = generator._render(summary)

        assert "Cycles: 0" in result
        assert "## Agents" not in result
        assert "## Errors" not in result
