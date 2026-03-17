"""Tests for collect_debugging_result (Task 014-1)."""

from __future__ import annotations

import json

from autopilot.core.models import DispatchStatus
from autopilot.debugging.models import DebuggingTask, TestStep
from autopilot.debugging.pipeline import collect_debugging_result
from autopilot.orchestration.agent_invoker import InvokeResult


def _make_task() -> DebuggingTask:
    return DebuggingTask(
        task_id="T001",
        feature="login",
        title="Test login",
        description="Verify login flow",
        staging_url="http://localhost:3000",
        steps=(TestStep(action="navigate", target="/login"),),
        acceptance_criteria=("Login page loads",),
        source_scope=("src/auth/",),
    )


def _make_invoke_result(output: str) -> InvokeResult:
    return InvokeResult(
        agent="debugging-agent",
        status=DispatchStatus.SUCCESS,
        exit_code=0,
        output=output,
    )


class TestCollectDebuggingResult:
    def test_valid_json_output(self) -> None:
        task = _make_task()
        agent_output = json.dumps(
            {
                "task_id": "T001",
                "overall_pass": True,
                "test_results": {
                    "steps_total": 1,
                    "steps_passed": 1,
                    "steps_failed": 0,
                    "all_passed": True,
                    "duration_seconds": 2.5,
                },
                "fix_results": None,
                "regression_results": None,
                "ux_results": None,
                "escalated": False,
                "escalation_reason": "",
            }
        )
        invoke_result = _make_invoke_result(agent_output)

        result = collect_debugging_result(task, invoke_result)

        assert result.task_id == "T001"
        assert result.overall_pass is True
        assert result.escalated is False
        assert result.test_results is not None
        assert result.test_results.steps_total == 1
        assert result.test_results.all_passed is True

    def test_valid_json_in_fenced_block(self) -> None:
        task = _make_task()
        json_block = json.dumps(
            {
                "task_id": "T001",
                "overall_pass": False,
                "escalated": True,
                "escalation_reason": "Max iterations reached",
            }
        )
        output = f"Here are the results:\n\n```json\n{json_block}\n```\n\nDone."
        invoke_result = _make_invoke_result(output)

        result = collect_debugging_result(task, invoke_result)

        assert result.task_id == "T001"
        assert result.overall_pass is False
        assert result.escalated is True
        assert result.escalation_reason == "Max iterations reached"

    def test_malformed_json_returns_escalated(self) -> None:
        task = _make_task()
        invoke_result = _make_invoke_result("This is not JSON at all")

        result = collect_debugging_result(task, invoke_result)

        assert result.task_id == "T001"
        assert result.escalated is True
        assert "parse" in result.escalation_reason.lower()

    def test_partial_output_missing_sub_results(self) -> None:
        task = _make_task()
        agent_output = json.dumps(
            {
                "task_id": "T001",
                "overall_pass": True,
            }
        )
        invoke_result = _make_invoke_result(agent_output)

        result = collect_debugging_result(task, invoke_result)

        assert result.task_id == "T001"
        assert result.overall_pass is True
        assert result.test_results is None
        assert result.fix_results is None
        assert result.regression_results is None
        assert result.ux_results is None

    def test_empty_output_returns_escalated(self) -> None:
        task = _make_task()
        invoke_result = _make_invoke_result("")

        result = collect_debugging_result(task, invoke_result)

        assert result.task_id == "T001"
        assert result.escalated is True
