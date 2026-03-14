"""Tests for per-project usage limits and priority weights (Task 085)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from freezegun import freeze_time

from autopilot.core.config import AutopilotConfig, ProjectConfig, UsageLimitsConfig
from autopilot.orchestration.usage import UsageTracker
from autopilot.utils.db import Database

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    return Database(tmp_path / "test.db")


@pytest.fixture()
def config() -> AutopilotConfig:
    return AutopilotConfig(
        project=ProjectConfig(name="test"),
        usage_limits=UsageLimitsConfig(
            daily_cycle_limit=10,
            weekly_cycle_limit=50,
            max_agent_invocations_per_cycle=10,
        ),
    )


@pytest.fixture()
def tracker(db: Database, config: AutopilotConfig) -> UsageTracker:
    return UsageTracker(db=db, config=config)


class TestAllocateCycles:
    def test_equal_weights_distributes_evenly(self, tracker: UsageTracker) -> None:
        result = tracker.allocate_cycles(
            projects=["alpha", "beta", "gamma"],
            total_budget=90,
        )
        assert result["alpha"] == 30
        assert result["beta"] == 30
        assert result["gamma"] == 30
        assert sum(result.values()) == 90

    def test_different_weights_proportional(self, tracker: UsageTracker) -> None:
        result = tracker.allocate_cycles(
            projects=["high", "low"],
            total_budget=100,
            priority_weights={"high": 3.0, "low": 1.0},
        )
        assert result["high"] == 75
        assert result["low"] == 25
        assert sum(result.values()) == 100

    def test_zero_budget_returns_zeros(self, tracker: UsageTracker) -> None:
        result = tracker.allocate_cycles(
            projects=["alpha", "beta"],
            total_budget=0,
        )
        assert result == {"alpha": 0, "beta": 0}

    def test_remainder_goes_to_last_project(self, tracker: UsageTracker) -> None:
        """When budget doesn't divide evenly, the last project gets the remainder."""
        result = tracker.allocate_cycles(
            projects=["a", "b", "c"],
            total_budget=10,
        )
        # With equal weights (1.0 each), int(10 * 1/3) = 3 for first two
        # Last project gets remainder: 10 - 3 - 3 = 4
        assert sum(result.values()) == 10

    def test_single_project_gets_full_budget(self, tracker: UsageTracker) -> None:
        result = tracker.allocate_cycles(
            projects=["solo"],
            total_budget=100,
        )
        assert result == {"solo": 100}

    def test_partial_weights_default_to_one(self, tracker: UsageTracker) -> None:
        """Projects without explicit weight default to 1.0."""
        result = tracker.allocate_cycles(
            projects=["weighted", "default"],
            total_budget=100,
            priority_weights={"weighted": 3.0},
        )
        # weighted=3.0, default=1.0 => 75 + 25 = 100
        assert result["weighted"] == 75
        assert result["default"] == 25


class TestGetPerProjectUsage:
    @freeze_time("2026-03-13 10:00:00+00:00")
    def test_returns_correct_breakdown(self, tracker: UsageTracker) -> None:
        tracker.record_cycle("proj-a")
        tracker.record_cycle("proj-a")
        tracker.record_cycle("proj-b")
        tracker.record_agent_invocation("proj-a", "coder")
        tracker.record_agent_invocation("proj-a", "reviewer")
        tracker.record_agent_invocation("proj-b", "tester")

        usage = tracker.get_per_project_usage()

        assert "proj-a" in usage
        assert "proj-b" in usage
        assert usage["proj-a"]["daily_cycles"] == 2
        assert usage["proj-a"]["weekly_cycles"] == 2
        assert usage["proj-a"]["agents_today"] == 2
        assert usage["proj-b"]["daily_cycles"] == 1
        assert usage["proj-b"]["agents_today"] == 1

    @freeze_time("2026-03-13 10:00:00+00:00")
    def test_empty_when_no_usage(self, tracker: UsageTracker) -> None:
        usage = tracker.get_per_project_usage()
        assert usage == {}


class TestUsageReport:
    @freeze_time("2026-03-13 10:00:00+00:00")
    def test_report_includes_all_fields(self, tracker: UsageTracker) -> None:
        tracker.record_cycle("proj-a")
        tracker.record_cycle("proj-a")
        tracker.record_agent_invocation("proj-a", "coder")

        report = tracker.usage_report(projects=["proj-a"])

        assert len(report) == 1
        entry: dict[str, Any] = report[0]
        assert entry["project"] == "proj-a"
        assert entry["daily_cycles"] == 2
        assert entry["daily_limit"] == 10
        assert entry["daily_remaining"] == 8
        assert entry["weekly_cycles"] == 2
        assert entry["weekly_limit"] == 50
        assert entry["weekly_remaining"] == 48
        assert entry["agents_today"] == 1

    @freeze_time("2026-03-13 10:00:00+00:00")
    def test_report_for_unknown_project_shows_zeros(self, tracker: UsageTracker) -> None:
        report = tracker.usage_report(projects=["unknown"])

        assert len(report) == 1
        assert report[0]["daily_cycles"] == 0
        assert report[0]["weekly_cycles"] == 0
        assert report[0]["agents_today"] == 0

    @freeze_time("2026-03-13 10:00:00+00:00")
    def test_report_without_filter_includes_all(self, tracker: UsageTracker) -> None:
        tracker.record_cycle("proj-a")
        tracker.record_cycle("proj-b")

        report = tracker.usage_report()

        project_names = [r["project"] for r in report]
        assert "proj-a" in project_names
        assert "proj-b" in project_names


class TestPerProjectLimitsOverride:
    @freeze_time("2026-03-13 10:00:00+00:00")
    def test_per_project_limits_in_report(self, db: Database, config: AutopilotConfig) -> None:
        strict_limits = UsageLimitsConfig(
            daily_cycle_limit=3,
            weekly_cycle_limit=15,
        )
        tracker = UsageTracker(
            db=db,
            config=config,
            per_project_limits={"strict-proj": strict_limits},
        )
        tracker.record_cycle("strict-proj")
        tracker.record_cycle("strict-proj")

        report = tracker.usage_report(projects=["strict-proj"])

        assert report[0]["daily_limit"] == 3
        assert report[0]["weekly_limit"] == 15
        assert report[0]["daily_remaining"] == 1

    @freeze_time("2026-03-13 10:00:00+00:00")
    def test_global_project_uses_global_limits(self, db: Database, config: AutopilotConfig) -> None:
        strict_limits = UsageLimitsConfig(daily_cycle_limit=3, weekly_cycle_limit=15)
        tracker = UsageTracker(
            db=db,
            config=config,
            per_project_limits={"strict-proj": strict_limits},
        )
        tracker.record_cycle("normal-proj")

        report = tracker.usage_report(projects=["normal-proj"])

        assert report[0]["daily_limit"] == 10
        assert report[0]["weekly_limit"] == 50
