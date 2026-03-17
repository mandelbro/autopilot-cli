"""Tests for debugging orchestration integration (Task 018)."""

from __future__ import annotations

from unittest.mock import MagicMock

from autopilot.debugging.models import DebuggingResult, InteractiveTestResults
from autopilot.orchestration.debugging_hooks import (
    DebuggingHookConfig,
    DebuggingReportEntry,
    create_debugging_dispatch,
    format_debugging_result,
    get_debugging_timeout,
    make_debugging_dispatch_outcome,
    post_debugging_result_to_board,
    should_trigger_debugging,
)

# ============================================================================
# Hook trigger tests
# ============================================================================


class TestShouldTriggerDebugging:
    """Post-deploy hook trigger tests."""

    def test_disabled_by_default(self) -> None:
        config = DebuggingHookConfig()
        assert config.enabled is False

    def test_does_not_trigger_when_disabled(self) -> None:
        config = DebuggingHookConfig(enabled=False)
        assert should_trigger_debugging(config, "deploy-agent", "deploy to staging") is False

    def test_triggers_on_deploy_action(self) -> None:
        config = DebuggingHookConfig(enabled=True)
        assert should_trigger_debugging(config, "deploy-agent", "deploy to staging") is True

    def test_triggers_on_release_action(self) -> None:
        config = DebuggingHookConfig(enabled=True)
        assert should_trigger_debugging(config, "release-agent", "release v2.0") is True

    def test_does_not_trigger_on_non_deploy_action(self) -> None:
        config = DebuggingHookConfig(enabled=True)
        assert should_trigger_debugging(config, "coder", "implement feature") is False

    def test_case_insensitive_action_match(self) -> None:
        config = DebuggingHookConfig(enabled=True)
        assert should_trigger_debugging(config, "agent", "Deploy to Production") is True


class TestCreateDebuggingDispatch:
    """Debugging dispatch creation tests."""

    def test_creates_dispatch_with_config(self) -> None:
        config = DebuggingHookConfig(enabled=True, tool="desktop_agent", timeout_seconds=300)
        dispatch = create_debugging_dispatch(config, "task-001", "/project")

        assert dispatch.task_id == "task-001"
        assert dispatch.tool == "desktop_agent"
        assert dispatch.project_dir == "/project"
        assert dispatch.timeout_seconds == 300  # noqa: PLR2004


# ============================================================================
# Timeout configuration
# ============================================================================


class TestGetDebuggingTimeout:
    """Debugging timeout from scheduler config."""

    def test_returns_configured_timeout(self) -> None:
        timeouts = {"debugging": 600}
        assert get_debugging_timeout(timeouts) == 600  # noqa: PLR2004

    def test_returns_default_when_not_configured(self) -> None:
        timeouts = {"other-agent": 300}
        assert get_debugging_timeout(timeouts) == 900  # noqa: PLR2004

    def test_respects_custom_default(self) -> None:
        assert get_debugging_timeout({}, default_timeout=1200) == 1200  # noqa: PLR2004


# ============================================================================
# Result reporting
# ============================================================================


def _make_passing_result() -> DebuggingResult:
    return DebuggingResult(
        task_id="debug-001",
        overall_pass=True,
        test_results=InteractiveTestResults(
            steps_total=5,
            steps_passed=5,
            all_passed=True,
        ),
        duration_seconds=45.0,
    )


def _make_failing_result() -> DebuggingResult:
    return DebuggingResult(
        task_id="debug-002",
        overall_pass=False,
        test_results=InteractiveTestResults(
            steps_total=5,
            steps_passed=3,
            steps_failed=2,
        ),
        duration_seconds=60.0,
        escalated=True,
        escalation_reason="2 steps failed after max fix attempts",
    )


class TestFormatDebuggingResult:
    """Format debugging results for reporting."""

    def test_format_passing_result(self) -> None:
        entry = format_debugging_result(_make_passing_result())

        assert isinstance(entry, DebuggingReportEntry)
        assert entry.task_id == "debug-001"
        assert entry.overall_pass is True
        assert entry.steps_total == 5  # noqa: PLR2004
        assert entry.steps_passed == 5  # noqa: PLR2004

    def test_format_failing_result(self) -> None:
        entry = format_debugging_result(_make_failing_result())

        assert entry.overall_pass is False
        assert entry.escalated is True
        assert "failed" in entry.escalation_reason


class TestPostDebuggingResultToBoard:
    """Coordination board posting tests."""

    def test_passing_result_posts_announcement(self) -> None:
        announcement_log = MagicMock()
        decision_log = MagicMock()

        post_debugging_result_to_board(
            _make_passing_result(),
            announcement_log,
            decision_log,
        )

        announcement_log.post.assert_called_once()
        decision_log.record.assert_not_called()

    def test_failing_result_posts_decision_log(self) -> None:
        announcement_log = MagicMock()
        decision_log = MagicMock()

        post_debugging_result_to_board(
            _make_failing_result(),
            announcement_log,
            decision_log,
        )

        announcement_log.post.assert_not_called()
        decision_log.record.assert_called_once()


class TestMakeDebuggingDispatchOutcome:
    """Cycle report integration tests."""

    def test_passing_result_outcome(self) -> None:
        outcome = make_debugging_dispatch_outcome(_make_passing_result())

        assert outcome.agent == "debugging-agent"
        assert outcome.status == "success"
        assert outcome.error == ""

    def test_failing_result_outcome(self) -> None:
        outcome = make_debugging_dispatch_outcome(_make_failing_result())

        assert outcome.status == "failed"
        assert "failed" in outcome.error
