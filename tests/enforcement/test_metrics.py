"""Tests for EnforcementMetricsCollector (Task 066)."""

from __future__ import annotations

import sqlite3
import time
from typing import TYPE_CHECKING

from autopilot.core.models import CheckResult, Violation, ViolationSeverity
from autopilot.enforcement.metrics import (
    EnforcementMetricsCollector,
    MetricPoint,
    MetricsSummary,
)

if TYPE_CHECKING:
    from pathlib import Path


def _make_results(categories: dict[str, int], files_scanned: int = 10) -> list[CheckResult]:
    """Helper to create CheckResult list with N violations per category."""
    results: list[CheckResult] = []
    for cat, count in categories.items():
        violations = tuple(
            Violation(
                category=cat,
                rule="test-rule",
                file="test.py",
                message=f"violation {i}",
                severity=ViolationSeverity.WARNING,
            )
            for i in range(count)
        )
        results.append(
            CheckResult(
                category=cat,
                violations=violations,
                files_scanned=files_scanned,
                duration_seconds=0.5,
            )
        )
    return results


class TestDatabaseInit:
    def test_creates_table_on_init(self, tmp_path: Path) -> None:
        db = tmp_path / "metrics.db"
        EnforcementMetricsCollector(db)

        conn = sqlite3.connect(str(db))
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='enforcement_metrics'"
            )
            assert cursor.fetchone() is not None
        finally:
            conn.close()


class TestRecordCheck:
    def test_persists_data(self, tmp_path: Path) -> None:
        db = tmp_path / "metrics.db"
        collector = EnforcementMetricsCollector(db)
        results = _make_results({"security": 3, "dead_code": 1})

        collector.record_check("proj-1", results)

        conn = sqlite3.connect(str(db))
        try:
            cursor = conn.execute(
                "SELECT project_id, category, violations_count, files_scanned "
                "FROM enforcement_metrics ORDER BY category"
            )
            rows = cursor.fetchall()
            assert len(rows) == 2
            assert rows[0] == ("proj-1", "dead_code", 1, 10)
            assert rows[1] == ("proj-1", "security", 3, 10)
        finally:
            conn.close()


class TestGetTrend:
    def test_returns_metric_points(self, tmp_path: Path) -> None:
        db = tmp_path / "metrics.db"
        collector = EnforcementMetricsCollector(db)
        results = _make_results({"security": 2})

        collector.record_check("proj-1", results)

        trend = collector.get_trend("proj-1", "security", days=30)
        assert len(trend) == 1
        assert isinstance(trend[0], MetricPoint)
        assert trend[0].violation_count == 2
        assert trend[0].files_scanned == 10

    def test_filters_by_days(self, tmp_path: Path) -> None:
        db = tmp_path / "metrics.db"
        collector = EnforcementMetricsCollector(db)

        # Insert an old record manually (60 days ago)
        conn = sqlite3.connect(str(db))
        try:
            old_ts = "2020-01-01T00:00:00+00:00"
            conn.execute(
                """INSERT INTO enforcement_metrics
                (collected_at, project_id, category, violations_count,
                 files_scanned, duration_seconds)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (old_ts, "proj-1", "security", 5, 10, 0.5),
            )
            conn.commit()
        finally:
            conn.close()

        # Insert a recent record
        results = _make_results({"security": 2})
        collector.record_check("proj-1", results)

        trend = collector.get_trend("proj-1", "security", days=30)
        # Only the recent record should appear (old one is >30 days ago)
        assert len(trend) == 1
        assert trend[0].violation_count == 2


class TestGetSummary:
    def test_returns_correct_by_category(self, tmp_path: Path) -> None:
        db = tmp_path / "metrics.db"
        collector = EnforcementMetricsCollector(db)
        results = _make_results({"security": 3, "dead_code": 1, "duplication": 0})

        collector.record_check("proj-1", results)

        summary = collector.get_summary("proj-1")
        assert isinstance(summary, MetricsSummary)
        assert summary.by_category["security"] == 3
        assert summary.by_category["dead_code"] == 1
        assert summary.by_category["duplication"] == 0
        assert summary.total_violations == 4

    def test_trend_stable_for_first_check(self, tmp_path: Path) -> None:
        db = tmp_path / "metrics.db"
        collector = EnforcementMetricsCollector(db)
        results = _make_results({"security": 5})

        collector.record_check("proj-1", results)

        summary = collector.get_summary("proj-1")
        assert summary.trend_direction == "stable"

    def test_trend_improving_when_violations_decrease(self, tmp_path: Path) -> None:
        db = tmp_path / "metrics.db"
        collector = EnforcementMetricsCollector(db)

        # First check: 5 violations
        results_1 = _make_results({"security": 5})
        collector.record_check("proj-1", results_1)

        # Small delay to ensure distinct timestamps
        time.sleep(0.01)

        # Second check: 2 violations
        results_2 = _make_results({"security": 2})
        collector.record_check("proj-1", results_2)

        summary = collector.get_summary("proj-1")
        assert summary.trend_direction == "improving"

    def test_trend_degrading_when_violations_increase(self, tmp_path: Path) -> None:
        db = tmp_path / "metrics.db"
        collector = EnforcementMetricsCollector(db)

        results_1 = _make_results({"security": 1})
        collector.record_check("proj-1", results_1)

        time.sleep(0.01)

        results_2 = _make_results({"security": 5})
        collector.record_check("proj-1", results_2)

        summary = collector.get_summary("proj-1")
        assert summary.trend_direction == "degrading"

    def test_empty_project_returns_stable(self, tmp_path: Path) -> None:
        db = tmp_path / "metrics.db"
        collector = EnforcementMetricsCollector(db)

        summary = collector.get_summary("no-such-project")
        assert summary.total_violations == 0
        assert summary.trend_direction == "stable"
        assert summary.by_category == {}


class TestViolationDensity:
    def test_calculation_is_accurate(self, tmp_path: Path) -> None:
        db = tmp_path / "metrics.db"
        collector = EnforcementMetricsCollector(db)
        results = _make_results({"security": 5})

        collector.record_check("proj-1", results)

        density = collector.violation_density("proj-1", total_lines=1000)
        assert density == 5.0

    def test_returns_zero_for_zero_lines(self, tmp_path: Path) -> None:
        db = tmp_path / "metrics.db"
        collector = EnforcementMetricsCollector(db)
        results = _make_results({"security": 5})

        collector.record_check("proj-1", results)

        density = collector.violation_density("proj-1", total_lines=0)
        assert density == 0.0
