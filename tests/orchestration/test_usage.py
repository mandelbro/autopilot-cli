"""Tests for usage tracking with per-project limits (Task 034)."""

from __future__ import annotations

from typing import TYPE_CHECKING

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
            daily_cycle_limit=5,
            weekly_cycle_limit=20,
            max_agent_invocations_per_cycle=10,
        ),
    )


@pytest.fixture()
def tracker(db: Database, config: AutopilotConfig) -> UsageTracker:
    return UsageTracker(db=db, config=config)


class TestCanExecute:
    @freeze_time("2026-03-13 10:00:00+00:00")
    def test_allows_execution_under_limit(self, tracker: UsageTracker) -> None:
        allowed, reason = tracker.can_execute("proj-a")
        assert allowed is True
        assert reason == ""

    @freeze_time("2026-03-13 10:00:00+00:00")
    def test_blocks_when_daily_limit_reached(self, tracker: UsageTracker) -> None:
        for _ in range(5):
            tracker.record_cycle("proj-a")

        allowed, reason = tracker.can_execute("proj-a")
        assert allowed is False
        assert "Daily" in reason

    @freeze_time("2026-03-13 10:00:00+00:00")
    def test_blocks_when_weekly_limit_reached(self, tracker: UsageTracker) -> None:
        for _ in range(20):
            tracker.record_cycle("proj-a")

        allowed, reason = tracker.can_execute("proj-a")
        assert allowed is False
        assert "Daily" in reason or "Weekly" in reason


class TestRecordAndCount:
    @freeze_time("2026-03-13 10:00:00+00:00")
    def test_records_cycles(self, tracker: UsageTracker) -> None:
        tracker.record_cycle("proj-a")
        tracker.record_cycle("proj-a")
        summary = tracker.get_usage_summary("proj-a")
        assert summary.daily_cycles == 2
        assert summary.weekly_cycles == 2

    @freeze_time("2026-03-13 10:00:00+00:00")
    def test_records_agent_invocations(self, tracker: UsageTracker) -> None:
        tracker.record_agent_invocation("proj-a", "engineering-manager")
        tracker.record_agent_invocation("proj-a", "technical-architect")
        summary = tracker.get_usage_summary("proj-a")
        assert summary.agent_invocations_today == 2


class TestPerProjectLimits:
    @freeze_time("2026-03-13 10:00:00+00:00")
    def test_per_project_overrides_global(self, db: Database, config: AutopilotConfig) -> None:
        project_limits = UsageLimitsConfig(
            daily_cycle_limit=2,
            weekly_cycle_limit=10,
        )
        tracker = UsageTracker(
            db=db,
            config=config,
            per_project_limits={"proj-strict": project_limits},
        )
        tracker.record_cycle("proj-strict")
        tracker.record_cycle("proj-strict")

        allowed, reason = tracker.can_execute("proj-strict")
        assert allowed is False
        assert "Daily" in reason

        # Global project still has capacity
        allowed, reason = tracker.can_execute("proj-normal")
        assert allowed is True


class TestUsageSummary:
    @freeze_time("2026-03-13 10:00:00+00:00")
    def test_summary_includes_limits_and_remaining(self, tracker: UsageTracker) -> None:
        tracker.record_cycle("proj-a")
        summary = tracker.get_usage_summary("proj-a")
        assert summary.daily_cycle_limit == 5
        assert summary.weekly_cycle_limit == 20
        assert summary.daily_remaining == 4
        assert summary.weekly_remaining == 19

    @freeze_time("2026-03-13 10:00:00+00:00")
    def test_global_summary(self, tracker: UsageTracker) -> None:
        tracker.record_cycle("proj-a")
        tracker.record_cycle("proj-b")
        summary = tracker.get_usage_summary(None)
        assert summary.daily_cycles == 2


class TestResets:
    @freeze_time("2026-03-13 10:00:00+00:00")
    def test_reset_daily(self, tracker: UsageTracker) -> None:
        tracker.record_cycle("proj-a")
        tracker.record_cycle("proj-a")
        tracker.reset_daily("proj-a")
        summary = tracker.get_usage_summary("proj-a")
        assert summary.daily_cycles == 0

    @freeze_time("2026-03-13 10:00:00+00:00")
    def test_reset_weekly(self, tracker: UsageTracker) -> None:
        tracker.record_cycle("proj-a")
        tracker.reset_weekly("proj-a")
        summary = tracker.get_usage_summary("proj-a")
        assert summary.weekly_cycles == 0
