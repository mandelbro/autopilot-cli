"""Tests for velocity reporting and forecasting (Task 042)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from autopilot.core.models import SprintResult
from autopilot.reporting.velocity import VelocityReporter
from autopilot.utils.db import Database

_PROJECT_ID = "proj-1"


@pytest.fixture()
def db(tmp_path):
    db = Database(tmp_path / "test.db")
    # Insert dummy project for FK constraint on velocity table
    db.insert_project(id=_PROJECT_ID, name="test", path="/tmp/test", type="python")
    return db


@pytest.fixture()
def reporter(db):
    return VelocityReporter(db, _PROJECT_ID)


def _record_sprints(db: Database, project_id: str, velocities: list[int]) -> None:
    """Helper to insert sprint results with given point velocities."""
    from autopilot.core.sprint import VelocityTracker

    tracker = VelocityTracker(db, project_id)
    for i, pts in enumerate(velocities):
        result = SprintResult(
            sprint_id=f"sprint-{i + 1:03d}",
            started_at=datetime(2026, 1 + i % 12, 1, tzinfo=UTC),
            ended_at=datetime(2026, 1 + i % 12, 14, tzinfo=UTC),
            points_planned=pts + 2,
            points_completed=pts,
            tasks_completed=pts // 2,
            tasks_carried_over=1,
        )
        tracker.record_sprint(result)


class TestSprintHistory:
    def test_empty_history(self, reporter: VelocityReporter) -> None:
        result = reporter.sprint_history()
        assert result == []

    def test_history_with_data(self, db, reporter: VelocityReporter) -> None:
        _record_sprints(db, _PROJECT_ID, [10, 12, 8])
        result = reporter.sprint_history()

        assert len(result) == 3
        assert result[0].sprint_id == "sprint-001"
        assert result[0].points_completed == 10
        assert result[0].completion_rate > 0

    def test_history_limit(self, db, reporter: VelocityReporter) -> None:
        _record_sprints(db, _PROJECT_ID, [10, 12, 8, 15, 11])
        result = reporter.sprint_history(limit=3)

        assert len(result) == 3


class TestVelocityTrend:
    def test_empty_trend(self, reporter: VelocityReporter) -> None:
        trend = reporter.velocity_trend()

        assert trend.sprints == 0
        assert trend.average == 0.0
        assert trend.trend_direction == "stable"
        assert trend.confidence == 0.0

    def test_stable_trend(self, db, reporter: VelocityReporter) -> None:
        _record_sprints(db, _PROJECT_ID, [10, 10, 10, 10])
        trend = reporter.velocity_trend()

        assert trend.sprints == 4
        assert trend.average == 10.0
        assert trend.trend_direction == "stable"
        assert trend.confidence > 0.5

    def test_upward_trend(self, db, reporter: VelocityReporter) -> None:
        _record_sprints(db, _PROJECT_ID, [5, 6, 10, 15])
        trend = reporter.velocity_trend()

        assert trend.trend_direction == "up"

    def test_downward_trend(self, db, reporter: VelocityReporter) -> None:
        _record_sprints(db, _PROJECT_ID, [15, 14, 8, 5])
        trend = reporter.velocity_trend()

        assert trend.trend_direction == "down"


class TestCompletionForecast:
    def test_no_history(self, reporter: VelocityReporter) -> None:
        forecast = reporter.forecast_completion(remaining_points=50)

        assert forecast.estimated_sprints == 0
        assert forecast.estimated_date is None

    def test_with_history(self, db, reporter: VelocityReporter) -> None:
        _record_sprints(db, _PROJECT_ID, [10, 12, 8, 10, 11])
        forecast = reporter.forecast_completion(remaining_points=50)

        assert forecast.estimated_sprints > 0
        assert forecast.estimated_date is not None
        assert forecast.average_velocity > 0
        assert forecast.confidence_range[0] <= forecast.estimated_sprints
        assert forecast.confidence_range[1] >= forecast.estimated_sprints

    def test_zero_remaining(self, db, reporter: VelocityReporter) -> None:
        _record_sprints(db, _PROJECT_ID, [10, 12])
        forecast = reporter.forecast_completion(remaining_points=0)

        assert forecast.estimated_sprints == 0


class TestGenerateReport:
    def test_empty_report(self, reporter: VelocityReporter) -> None:
        report = reporter.generate_report()

        assert "Velocity Report" in report
        assert "Sprints tracked: 0" in report

    def test_report_with_data(self, db, reporter: VelocityReporter) -> None:
        _record_sprints(db, _PROJECT_ID, [10, 12, 8, 15, 11])
        report = reporter.generate_report()

        assert "Velocity Report" in report
        assert "Recent Sprints" in report
        assert "Velocity Chart" in report
        assert "sprint-" in report


class TestTrendHelpers:
    def test_trend_single_value(self) -> None:
        assert VelocityReporter._compute_trend_direction([10]) == "stable"

    def test_confidence_single_value(self) -> None:
        assert VelocityReporter._compute_confidence([10]) == 0.0

    def test_confidence_identical(self) -> None:
        assert VelocityReporter._compute_confidence([10, 10, 10]) == 1.0

    def test_confidence_varied(self) -> None:
        c = VelocityReporter._compute_confidence([5, 15, 5, 15])
        assert 0.0 < c < 1.0
