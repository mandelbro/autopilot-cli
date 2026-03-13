"""Tests for cycle reports generator (Task 040)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from autopilot.reporting.cycle_reports import (
    CycleReportData,
    CycleReportGenerator,
    DispatchOutcome,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def reports_dir(tmp_path: Path) -> Path:
    return tmp_path / "cycle-reports"


@pytest.fixture()
def generator(reports_dir: Path) -> CycleReportGenerator:
    return CycleReportGenerator(reports_dir=reports_dir)


@pytest.fixture()
def sample_data() -> CycleReportData:
    return CycleReportData(
        cycle_id="cycle-001",
        project_id="proj-a",
        status="COMPLETED",
        started_at=datetime(2026, 3, 13, 10, 0, 0, tzinfo=UTC),
        ended_at=datetime(2026, 3, 13, 10, 5, 30, tzinfo=UTC),
        duration_seconds=330.0,
        dispatches=(
            DispatchOutcome(
                agent="engineering-manager",
                action="Review PR #42",
                status="success",
                duration_seconds=120.5,
            ),
            DispatchOutcome(
                agent="technical-architect",
                action="Refactor auth module",
                status="failed",
                duration_seconds=200.0,
                error="Timeout after 200s",
            ),
        ),
    )


class TestCycleReportGenerator:
    def test_generates_markdown_file(
        self, generator: CycleReportGenerator, sample_data: CycleReportData
    ) -> None:
        path = generator.generate(sample_data)
        assert path.exists()
        assert path.suffix == ".md"

    def test_filename_contains_date(
        self, generator: CycleReportGenerator, sample_data: CycleReportData
    ) -> None:
        path = generator.generate(sample_data)
        assert "2026-03-13" in path.name

    def test_report_contains_cycle_id(
        self, generator: CycleReportGenerator, sample_data: CycleReportData
    ) -> None:
        path = generator.generate(sample_data)
        content = path.read_text()
        assert "cycle-001" in content

    def test_report_contains_dispatch_outcomes(
        self, generator: CycleReportGenerator, sample_data: CycleReportData
    ) -> None:
        path = generator.generate(sample_data)
        content = path.read_text()
        assert "engineering-manager" in content
        assert "technical-architect" in content
        assert "Review PR #42" in content

    def test_report_contains_summary_stats(
        self, generator: CycleReportGenerator, sample_data: CycleReportData
    ) -> None:
        path = generator.generate(sample_data)
        content = path.read_text()
        assert "Total Dispatches" in content
        assert "Succeeded" in content
        assert "Success Rate" in content

    def test_report_contains_errors_section(
        self, generator: CycleReportGenerator, sample_data: CycleReportData
    ) -> None:
        path = generator.generate(sample_data)
        content = path.read_text()
        assert "Errors" in content
        assert "Timeout after 200s" in content

    def test_sequence_increments(
        self, generator: CycleReportGenerator, sample_data: CycleReportData
    ) -> None:
        path1 = generator.generate(sample_data)
        path2 = generator.generate(sample_data)
        assert path1 != path2
        assert "001" in path1.name
        assert "002" in path2.name


class TestCycleReportNoDispatches:
    def test_report_with_no_dispatches(self, generator: CycleReportGenerator) -> None:
        data = CycleReportData(
            cycle_id="cycle-empty",
            project_id="proj-b",
            status="FAILED",
            started_at=datetime(2026, 3, 13, 10, 0, 0, tzinfo=UTC),
            ended_at=None,
            duration_seconds=0.5,
            dispatches=(),
        )
        path = generator.generate(data)
        content = path.read_text()
        assert "cycle-empty" in content
        assert "FAILED" in content
        # No dispatch table
        assert "| Agent" not in content
