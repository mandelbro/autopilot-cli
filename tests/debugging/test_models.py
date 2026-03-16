"""Tests for debugging pipeline data models (Task 004)."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

from autopilot.debugging.models import (
    DebuggingResult,
    DebuggingTask,
    FixAttempt,
    FixCycleResults,
    InteractiveTestResults,
    RegressionTestResults,
    TestStep,
    ToolNotProvisionedError,
    UXReviewResults,
)
from autopilot.debugging.tools.protocol import (
    InteractionResult,
    ProvisionStatus,
    UXObservation,
)


class TestTestStep:
    def test_construction_with_required_fields(self) -> None:
        step = TestStep(action="click", target="#submit")
        assert step.action == "click"
        assert step.target == "#submit"
        assert step.value == ""
        assert step.expect == ""
        assert step.timeout_seconds == 30

    def test_construction_with_all_fields(self) -> None:
        step = TestStep(
            action="fill",
            target="#email",
            value="user@example.com",
            expect="input populated",
            timeout_seconds=10,
        )
        assert step.value == "user@example.com"
        assert step.timeout_seconds == 10

    def test_frozen_immutability(self) -> None:
        step = TestStep(action="click", target="#btn")
        with pytest.raises(dataclasses.FrozenInstanceError):
            step.action = "hover"  # type: ignore[misc]


class TestDebuggingTask:
    def test_construction_with_required_fields(
        self, sample_debugging_task: Callable[..., DebuggingTask]
    ) -> None:
        task = sample_debugging_task()
        assert task.task_id == "DBG-001"
        assert task.feature == "login"
        assert task.title == "Verify login flow"
        assert task.description == "End-to-end login test"
        assert task.staging_url == "http://staging.example.com"
        assert len(task.steps) == 1
        assert len(task.acceptance_criteria) == 1
        assert len(task.source_scope) == 1

    def test_default_optional_fields(
        self, sample_debugging_task: Callable[..., DebuggingTask]
    ) -> None:
        task = sample_debugging_task()
        assert task.ux_review_enabled is True
        assert task.ux_capture_states == ()

    def test_override_optional_fields(
        self, sample_debugging_task: Callable[..., DebuggingTask]
    ) -> None:
        task = sample_debugging_task(
            ux_review_enabled=False,
            ux_capture_states=("logged_in", "dashboard"),
        )
        assert task.ux_review_enabled is False
        assert task.ux_capture_states == ("logged_in", "dashboard")

    def test_frozen_immutability(self, sample_debugging_task: Callable[..., DebuggingTask]) -> None:
        task = sample_debugging_task()
        with pytest.raises(dataclasses.FrozenInstanceError):
            task.task_id = "DBG-999"  # type: ignore[misc]


class TestFixAttempt:
    def test_construction(self) -> None:
        attempt = FixAttempt(
            iteration=1,
            diagnosis="Missing null check",
            files_modified=("src/auth.py",),
        )
        assert attempt.iteration == 1
        assert attempt.diagnosis == "Missing null check"
        assert attempt.files_modified == ("src/auth.py",)
        assert attempt.pr_url == ""
        assert attempt.tests_passed is False
        assert attempt.error == ""

    def test_with_all_fields(self) -> None:
        attempt = FixAttempt(
            iteration=2,
            diagnosis="Race condition",
            files_modified=("src/auth.py", "src/session.py"),
            pr_url="https://github.com/org/repo/pull/42",
            tests_passed=True,
            error="",
        )
        assert attempt.tests_passed is True
        assert attempt.pr_url == "https://github.com/org/repo/pull/42"

    def test_frozen_immutability(self) -> None:
        attempt = FixAttempt(iteration=1, diagnosis="d", files_modified=())
        with pytest.raises(dataclasses.FrozenInstanceError):
            attempt.iteration = 2  # type: ignore[misc]


class TestInteractiveTestResults:
    def test_default_construction(self) -> None:
        results = InteractiveTestResults()
        assert results.steps_total == 0
        assert results.steps_passed == 0
        assert results.steps_failed == 0
        assert results.all_passed is False
        assert results.step_results == ()
        assert results.duration_seconds == 0.0

    def test_with_step_results(self) -> None:
        step_result = InteractionResult(success=True)
        results = InteractiveTestResults(
            steps_total=1,
            steps_passed=1,
            all_passed=True,
            step_results=(step_result,),
            duration_seconds=1.5,
        )
        assert results.steps_total == 1
        assert len(results.step_results) == 1


class TestFixCycleResults:
    def test_default_construction(self) -> None:
        results = FixCycleResults()
        assert results.attempts == ()
        assert results.resolved is False
        assert results.final_diagnosis == ""
        assert results.duration_seconds == 0.0


class TestRegressionTestResults:
    def test_default_construction(self) -> None:
        results = RegressionTestResults()
        assert results.tests_generated == 0
        assert results.tests_passed == 0
        assert results.tests_failed == 0
        assert results.test_file_path == ""
        assert results.duration_seconds == 0.0


class TestUXReviewResults:
    def test_default_construction(self) -> None:
        results = UXReviewResults()
        assert results.observations == ()
        assert results.overall_pass is False
        assert results.summary == ""
        assert results.duration_seconds == 0.0

    def test_with_observations(self) -> None:
        obs = UXObservation(
            category="contrast",
            severity="error",
            description="Low contrast text",
        )
        results = UXReviewResults(
            observations=(obs,),
            overall_pass=False,
            summary="1 issue found",
        )
        assert len(results.observations) == 1
        assert results.observations[0].category == "contrast"


class TestDebuggingResult:
    def test_minimal_construction(self) -> None:
        result = DebuggingResult(task_id="DBG-001")
        assert result.task_id == "DBG-001"
        assert result.overall_pass is False
        assert result.test_results is None
        assert result.fix_results is None
        assert result.regression_results is None
        assert result.ux_results is None
        assert result.duration_seconds == 0.0
        assert result.escalated is False
        assert result.escalation_reason == ""

    def test_with_populated_sub_results(self) -> None:
        test_res = InteractiveTestResults(steps_total=3, steps_passed=3, all_passed=True)
        fix_res = FixCycleResults(resolved=True, final_diagnosis="Fixed null check")
        regression_res = RegressionTestResults(tests_generated=5, tests_passed=5)
        ux_res = UXReviewResults(overall_pass=True, summary="All clear")

        result = DebuggingResult(
            task_id="DBG-002",
            overall_pass=True,
            test_results=test_res,
            fix_results=fix_res,
            regression_results=regression_res,
            ux_results=ux_res,
            duration_seconds=120.5,
        )
        assert result.overall_pass is True
        assert result.test_results is not None
        assert result.test_results.all_passed is True
        assert result.fix_results is not None
        assert result.fix_results.resolved is True
        assert result.regression_results is not None
        assert result.regression_results.tests_generated == 5
        assert result.ux_results is not None
        assert result.ux_results.overall_pass is True

    def test_frozen_immutability(self) -> None:
        result = DebuggingResult(task_id="DBG-001")
        with pytest.raises(dataclasses.FrozenInstanceError):
            result.task_id = "DBG-999"  # type: ignore[misc]

    def test_with_escalation(self) -> None:
        result = DebuggingResult(
            task_id="DBG-003",
            escalated=True,
            escalation_reason="Max fix iterations exceeded",
        )
        assert result.escalated is True
        assert result.escalation_reason == "Max fix iterations exceeded"


class TestToolNotProvisionedError:
    def test_message_contains_tool_name(self) -> None:
        status = ProvisionStatus(provisioned=False, ready=False, message="Not installed")
        error = ToolNotProvisionedError(tool_name="browser_mcp", status=status)

        assert "browser_mcp" in str(error)
        assert "not provisioned" in str(error).lower()
        assert "Not installed" in str(error)

    def test_tool_name_attribute(self) -> None:
        status = ProvisionStatus(provisioned=False, ready=False)
        error = ToolNotProvisionedError(tool_name="playwright", status=status)
        assert error.tool_name == "playwright"

    def test_status_attribute(self) -> None:
        status = ProvisionStatus(provisioned=False, ready=False, message="Missing deps")
        error = ToolNotProvisionedError(tool_name="test-tool", status=status)
        assert error.status is status
        assert error.status.message == "Missing deps"

    def test_is_runtime_error(self) -> None:
        status = ProvisionStatus(provisioned=False, ready=False)
        error = ToolNotProvisionedError(tool_name="t", status=status)
        assert isinstance(error, RuntimeError)

    def test_provision_command_in_message(self) -> None:
        status = ProvisionStatus(provisioned=False, ready=False)
        error = ToolNotProvisionedError(tool_name="browser_mcp", status=status)
        assert "autopilot debug provision browser_mcp" in str(error)
