"""Tests for cross-project quality reporting (Task 086)."""

from __future__ import annotations

import pytest

from autopilot.reporting.quality import (
    CrossProjectSummary,
    HealthReport,
    QualityReporter,
    TrendReport,
)
from autopilot.utils.db import Database

_PROJECT_A = "proj-a"
_PROJECT_B = "proj-b"


@pytest.fixture()
def db(tmp_path):
    db = Database(tmp_path / "test.db")
    db.insert_project(id=_PROJECT_A, name="Alpha", path="/tmp/alpha", type="python")
    db.insert_project(id=_PROJECT_B, name="Beta", path="/tmp/beta", type="python")
    return db


@pytest.fixture()
def reporter(db):
    return QualityReporter(db)


# ------------------------------------------------------------------
# record_violation
# ------------------------------------------------------------------


class TestRecordViolation:
    def test_inserts_and_counts(self, reporter: QualityReporter) -> None:
        reporter.record_violation(_PROJECT_A, "duplication", severity="warning")
        reporter.record_violation(_PROJECT_A, "security", severity="error")

        conn = reporter._db.get_connection()
        try:
            row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM enforcement_violations WHERE project_id = ?",
                (_PROJECT_A,),
            ).fetchone()
            assert row["cnt"] == 2
        finally:
            conn.close()

    def test_stores_all_fields(self, reporter: QualityReporter) -> None:
        reporter.record_violation(
            _PROJECT_A,
            "conventions",
            cycle_id="c-1",
            severity="error",
            file_path="src/foo.py",
            message="bad name",
        )

        conn = reporter._db.get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM enforcement_violations WHERE project_id = ?",
                (_PROJECT_A,),
            ).fetchone()
            assert row["category"] == "conventions"
            assert row["cycle_id"] == "c-1"
            assert row["severity"] == "error"
            assert row["file_path"] == "src/foo.py"
            assert row["message"] == "bad name"
        finally:
            conn.close()


# ------------------------------------------------------------------
# record_operational_event
# ------------------------------------------------------------------


class TestRecordOperationalEvent:
    def test_inserts_event(self, reporter: QualityReporter) -> None:
        reporter.record_operational_event(_PROJECT_A, "cycle_success")
        reporter.record_operational_event(_PROJECT_A, "cycle_failure", details="OOM")

        conn = reporter._db.get_connection()
        try:
            row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM operational_events WHERE project_id = ?",
                (_PROJECT_A,),
            ).fetchone()
            assert row["cnt"] == 2
        finally:
            conn.close()


# ------------------------------------------------------------------
# enforcement_trends
# ------------------------------------------------------------------


def _seed_violations_and_cycles(reporter: QualityReporter, project_id: str) -> None:
    """Seed sample violations and cycle events for trend testing."""
    conn = reporter._db.get_connection()
    try:
        # Day 1: 3 violations, 2 cycles
        for _ in range(3):
            conn.execute(
                "INSERT INTO enforcement_violations "
                "(project_id, category, recorded_at) VALUES (?, ?, ?)",
                (project_id, "duplication", "2026-03-01T10:00:00Z"),
            )
        for _ in range(2):
            conn.execute(
                "INSERT INTO operational_events "
                "(project_id, event_type, recorded_at) VALUES (?, ?, ?)",
                (project_id, "cycle_success", "2026-03-01T10:00:00Z"),
            )

        # Day 2: 1 violation, 3 cycles (improving)
        conn.execute(
            "INSERT INTO enforcement_violations "
            "(project_id, category, recorded_at) VALUES (?, ?, ?)",
            (project_id, "security", "2026-03-02T10:00:00Z"),
        )
        for _ in range(3):
            conn.execute(
                "INSERT INTO operational_events "
                "(project_id, event_type, recorded_at) VALUES (?, ?, ?)",
                (project_id, "cycle_success", "2026-03-02T10:00:00Z"),
            )
        conn.commit()
    finally:
        conn.close()


class TestEnforcementTrends:
    def test_empty_database(self, reporter: QualityReporter) -> None:
        result = reporter.enforcement_trends(_PROJECT_A)

        assert isinstance(result, TrendReport)
        assert result.total_violations == 0
        assert result.average_density == 0.0
        assert result.trend_direction == "stable"
        assert result.points == []

    def test_with_data(self, reporter: QualityReporter) -> None:
        _seed_violations_and_cycles(reporter, _PROJECT_A)
        result = reporter.enforcement_trends(_PROJECT_A, days=365)

        assert result.total_violations == 4
        assert len(result.points) == 2
        assert result.points[0].date == "2026-03-01"
        assert result.points[0].violation_count == 3
        # density = 3 violations / 2 cycles = 1.5
        assert result.points[0].violation_density == pytest.approx(1.5)

    def test_trend_direction_improving(self, reporter: QualityReporter) -> None:
        _seed_violations_and_cycles(reporter, _PROJECT_A)
        result = reporter.enforcement_trends(_PROJECT_A, days=365)

        # Day 1 density 1.5, Day 2 density ~0.33 => improving
        assert result.trend_direction == "improving"


# ------------------------------------------------------------------
# cross_project_summary
# ------------------------------------------------------------------


class TestCrossProjectSummary:
    def test_empty_database(self, reporter: QualityReporter) -> None:
        result = reporter.cross_project_summary()

        assert isinstance(result, CrossProjectSummary)
        assert result.total_projects == 0
        assert result.total_sessions == 0
        assert result.average_velocity == 0.0
        assert result.average_quality == 0.0

    def test_multiple_projects(self, reporter: QualityReporter) -> None:
        # Seed project A: 2 successes, 1 violation
        reporter.record_operational_event(_PROJECT_A, "cycle_success")
        reporter.record_operational_event(_PROJECT_A, "cycle_success")
        reporter.record_violation(_PROJECT_A, "duplication")

        # Seed project B: 1 success, 0 violations
        reporter.record_operational_event(_PROJECT_B, "cycle_success")

        result = reporter.cross_project_summary()

        assert result.total_projects == 2
        assert len(result.projects) == 2

        proj_a = next(p for p in result.projects if p.project_id == _PROJECT_A)
        proj_b = next(p for p in result.projects if p.project_id == _PROJECT_B)

        assert proj_a.project_name == "Alpha"
        assert proj_b.project_name == "Beta"
        # Project A quality: 1 - (1 violation / 2 cycles) = 0.5
        assert proj_a.quality_score == pytest.approx(0.5)
        # Project B quality: 1 - (0 / 1) = 1.0
        assert proj_b.quality_score == pytest.approx(1.0)
        assert result.average_quality == pytest.approx(0.75)


# ------------------------------------------------------------------
# operational_health
# ------------------------------------------------------------------


class TestOperationalHealth:
    def test_empty_database(self, reporter: QualityReporter) -> None:
        result = reporter.operational_health(_PROJECT_A)

        assert isinstance(result, HealthReport)
        assert result.total_cycles == 0
        assert result.health_status == "unhealthy"
        assert result.cycle_success_rate == 0.0

    def test_healthy_project(self, reporter: QualityReporter) -> None:
        for _ in range(9):
            reporter.record_operational_event(_PROJECT_A, "cycle_success")
        reporter.record_operational_event(_PROJECT_A, "cycle_failure")

        result = reporter.operational_health(_PROJECT_A)

        assert result.total_cycles == 10
        assert result.failed_cycles == 1
        assert result.cycle_success_rate == pytest.approx(0.9)
        assert result.health_status == "healthy"

    def test_degraded_project(self, reporter: QualityReporter) -> None:
        for _ in range(7):
            reporter.record_operational_event(_PROJECT_A, "cycle_success")
        for _ in range(3):
            reporter.record_operational_event(_PROJECT_A, "cycle_failure")

        result = reporter.operational_health(_PROJECT_A)

        assert result.cycle_success_rate == pytest.approx(0.7)
        assert result.health_status == "degraded"

    def test_unhealthy_project(self, reporter: QualityReporter) -> None:
        for _ in range(3):
            reporter.record_operational_event(_PROJECT_A, "cycle_success")
        for _ in range(7):
            reporter.record_operational_event(_PROJECT_A, "cycle_failure")

        result = reporter.operational_health(_PROJECT_A)

        assert result.cycle_success_rate == pytest.approx(0.3)
        assert result.health_status == "unhealthy"

    def test_counts_timeouts_and_circuit_breaker(self, reporter: QualityReporter) -> None:
        reporter.record_operational_event(_PROJECT_A, "cycle_success")
        reporter.record_operational_event(_PROJECT_A, "timeout")
        reporter.record_operational_event(_PROJECT_A, "timeout")
        reporter.record_operational_event(_PROJECT_A, "circuit_breaker")

        result = reporter.operational_health(_PROJECT_A)

        assert result.timeouts == 2
        assert result.circuit_breaker_activations == 1
        # timeouts and circuit_breaker don't count as cycles
        assert result.total_cycles == 1


# ------------------------------------------------------------------
# export_csv
# ------------------------------------------------------------------


class TestExportCsv:
    def test_empty_database(self, reporter: QualityReporter) -> None:
        csv_str = reporter.export_csv()

        lines = csv_str.strip().split("\n")
        assert len(lines) == 1  # header only
        assert "project_id" in lines[0]
        assert "category" in lines[0]

    def test_with_data(self, reporter: QualityReporter) -> None:
        reporter.record_violation(_PROJECT_A, "duplication", message="dup found")
        reporter.record_violation(_PROJECT_B, "security", message="leak")

        csv_str = reporter.export_csv(days=365)

        lines = csv_str.strip().split("\n")
        assert len(lines) == 3  # header + 2 rows

    def test_filter_by_project(self, reporter: QualityReporter) -> None:
        reporter.record_violation(_PROJECT_A, "duplication")
        reporter.record_violation(_PROJECT_B, "security")

        csv_str = reporter.export_csv(project_id=_PROJECT_A, days=365)

        lines = csv_str.strip().split("\n")
        assert len(lines) == 2  # header + 1 row
        assert _PROJECT_A in lines[1]

    def test_csv_parseable(self, reporter: QualityReporter) -> None:
        """Verify output is valid CSV."""
        import csv as csv_mod
        import io

        reporter.record_violation(_PROJECT_A, "conventions", message="comma, in message")

        csv_str = reporter.export_csv(days=365)

        reader = csv_mod.reader(io.StringIO(csv_str))
        rows = list(reader)
        assert len(rows) == 2
        assert rows[1][5] == "comma, in message"
