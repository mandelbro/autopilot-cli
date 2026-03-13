"""Tests for scheduler core — cycle orchestration (Task 035)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from autopilot.core.config import (
    AutopilotConfig,
    GitConfig,
    ProjectConfig,
    SchedulerConfig,
    UsageLimitsConfig,
)
from autopilot.core.models import CycleStatus, Dispatch, DispatchPlan, DispatchStatus
from autopilot.orchestration.agent_invoker import InvokeResult
from autopilot.orchestration.scheduler import Scheduler, SchedulerError

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def config() -> AutopilotConfig:
    return AutopilotConfig(
        project=ProjectConfig(name="test-project"),
        scheduler=SchedulerConfig(
            consecutive_timeout_limit=2,
            agent_timeout_seconds=60,
        ),
        git=GitConfig(base_branch="main"),
        usage_limits=UsageLimitsConfig(
            daily_cycle_limit=100,
            weekly_cycle_limit=500,
        ),
    )


@pytest.fixture()
def invoker() -> MagicMock:
    mock = MagicMock()
    mock.invoke.return_value = InvokeResult(
        agent="test-agent",
        status=DispatchStatus.SUCCESS,
        exit_code=0,
        duration_seconds=10.0,
        output="Done",
        model_used="sonnet",
    )
    return mock


@pytest.fixture()
def usage() -> MagicMock:
    mock = MagicMock()
    mock.can_execute.return_value = (True, "")
    return mock


@pytest.fixture()
def scheduler(
    config: AutopilotConfig,
    invoker: MagicMock,
    usage: MagicMock,
    tmp_path: Path,
) -> Scheduler:
    return Scheduler(
        config=config,
        invoker=invoker,
        usage_tracker=usage,
        lock_dir=tmp_path,
        cwd=tmp_path,
    )


def _simple_plan(*agents: str) -> DispatchPlan:
    return DispatchPlan(
        dispatches=tuple(Dispatch(agent=a, action=f"Action for {a}") for a in agents),
        summary="Test plan",
    )


class TestThreePhase:
    @patch("autopilot.orchestration.scheduler.git.validate_git_state", return_value=[])
    def test_successful_cycle(self, _git: MagicMock, scheduler: Scheduler) -> None:
        plan = _simple_plan("engineering-manager", "technical-architect")
        result = scheduler.run_cycle(plan)

        assert result.status == CycleStatus.COMPLETED
        assert result.dispatches_planned == 2
        assert result.dispatches_succeeded == 2
        assert result.dispatches_failed == 0
        assert result.project_id == "test-project"

    @patch("autopilot.orchestration.scheduler.git.validate_git_state", return_value=[])
    def test_partial_cycle(
        self,
        _git: MagicMock,
        scheduler: Scheduler,
        invoker: MagicMock,
    ) -> None:
        success = InvokeResult(agent="a", status=DispatchStatus.SUCCESS, model_used="sonnet")
        failure = InvokeResult(
            agent="b", status=DispatchStatus.FAILED, error="Crash", model_used="sonnet"
        )
        invoker.invoke.side_effect = [success, failure]

        plan = _simple_plan("agent-a", "agent-b")
        result = scheduler.run_cycle(plan)

        assert result.status == CycleStatus.PARTIAL
        assert result.dispatches_succeeded == 1
        assert result.dispatches_failed == 1

    @patch("autopilot.orchestration.scheduler.git.validate_git_state", return_value=[])
    def test_failed_cycle(
        self,
        _git: MagicMock,
        scheduler: Scheduler,
        invoker: MagicMock,
    ) -> None:
        invoker.invoke.return_value = InvokeResult(
            agent="a", status=DispatchStatus.FAILED, error="Error", model_used="sonnet"
        )
        plan = _simple_plan("agent-a")
        result = scheduler.run_cycle(plan)

        assert result.status == CycleStatus.FAILED


class TestCycleLock:
    @patch("autopilot.orchestration.scheduler.git.validate_git_state", return_value=[])
    def test_lock_prevents_concurrent(
        self,
        _git: MagicMock,
        config: AutopilotConfig,
        invoker: MagicMock,
        usage: MagicMock,
        tmp_path: Path,
    ) -> None:
        s1 = Scheduler(
            config=config,
            invoker=invoker,
            usage_tracker=usage,
            lock_dir=tmp_path,
            cwd=tmp_path,
        )
        s2 = Scheduler(
            config=config,
            invoker=invoker,
            usage_tracker=usage,
            lock_dir=tmp_path,
            cwd=tmp_path,
        )
        # Acquire lock via s1's phase_plan
        s1._lock.acquire()
        try:
            with pytest.raises(SchedulerError, match="lock held"):
                s2.run_cycle(_simple_plan("agent-a"))
        finally:
            s1._lock.release()

    @patch("autopilot.orchestration.scheduler.git.validate_git_state", return_value=[])
    def test_lock_released_after_cycle(
        self, _git: MagicMock, scheduler: Scheduler, tmp_path: Path
    ) -> None:
        scheduler.run_cycle(_simple_plan("agent-a"))
        # Lock should be released
        assert not scheduler._lock.is_alive()


class TestGitValidation:
    def test_rejects_dirty_tree(self, scheduler: Scheduler) -> None:
        with (
            patch(
                "autopilot.orchestration.scheduler.git.validate_git_state",
                return_value=["Working tree has uncommitted changes"],
            ),
            pytest.raises(SchedulerError, match="Git state invalid"),
        ):
            scheduler.run_cycle(_simple_plan("agent-a"))


class TestUsageLimits:
    @patch("autopilot.orchestration.scheduler.git.validate_git_state", return_value=[])
    def test_blocks_when_limit_reached(
        self,
        _git: MagicMock,
        scheduler: Scheduler,
        usage: MagicMock,
    ) -> None:
        usage.can_execute.return_value = (False, "Daily limit reached")
        with pytest.raises(SchedulerError, match="Usage limit"):
            scheduler.run_cycle(_simple_plan("agent-a"))

    @patch("autopilot.orchestration.scheduler.git.validate_git_state", return_value=[])
    def test_records_cycle_and_invocations(
        self,
        _git: MagicMock,
        scheduler: Scheduler,
        usage: MagicMock,
    ) -> None:
        scheduler.run_cycle(_simple_plan("agent-a", "agent-b"))
        usage.record_cycle.assert_called_once_with("test-project")
        assert usage.record_agent_invocation.call_count == 2


class TestCircuitBreaker:
    @patch("autopilot.orchestration.scheduler.git.validate_git_state", return_value=[])
    def test_trips_after_consecutive_failures(
        self,
        _git: MagicMock,
        scheduler: Scheduler,
        invoker: MagicMock,
    ) -> None:
        invoker.invoke.return_value = InvokeResult(
            agent="a",
            status=DispatchStatus.TIMEOUT,
            error="Timeout",
            model_used="sonnet",
        )
        plan = _simple_plan("agent-a", "agent-b", "agent-c")
        result = scheduler.run_cycle(plan)

        # 2 actual failures + 1 skipped = 3 total
        assert result.dispatches_failed == 3
        assert result.dispatches_succeeded == 0


class TestRunLoop:
    @patch("autopilot.orchestration.scheduler.git.validate_git_state", return_value=[])
    def test_stop_halts_loop(
        self,
        _git: MagicMock,
        scheduler: Scheduler,
    ) -> None:
        call_count = 0

        def plan_fn() -> DispatchPlan | None:
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                scheduler.stop()
            return _simple_plan("agent-a")

        with patch("autopilot.orchestration.scheduler.time.sleep"):
            scheduler.run_loop(1, plan_fn=plan_fn)

        assert call_count >= 2

    def test_raises_without_plan_fn(self, scheduler: Scheduler) -> None:
        with pytest.raises(SchedulerError, match="plan_fn"):
            scheduler.run_loop(1)
