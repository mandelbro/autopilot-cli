"""Debugging agent orchestration integration (Task 018).

Post-deploy hook trigger, debugging timeout configuration, and result
reporting to the coordination board and cycle reports.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autopilot.coordination.announcements import AnnouncementManager
    from autopilot.coordination.decisions import DecisionLog
    from autopilot.debugging.models import DebuggingResult
    from autopilot.reporting.cycle_reports import DispatchOutcome

_log = logging.getLogger(__name__)

_DEFAULT_DEBUGGING_TIMEOUT = 900  # 15 minutes


@dataclass(frozen=True)
class DebuggingHookConfig:
    """Configuration for post-deploy debugging triggers.

    Disabled by default. Set ``enabled=True`` to trigger debugging runs
    after deploy dispatches complete.
    """

    enabled: bool = False
    tool: str = "browser_mcp"
    task_dir: str = ".autopilot/debugging/tasks"
    timeout_seconds: int = _DEFAULT_DEBUGGING_TIMEOUT


@dataclass(frozen=True)
class DebuggingDispatch:
    """A debugging dispatch triggered by a post-deploy hook."""

    task_id: str
    tool: str
    project_dir: str
    timeout_seconds: int = _DEFAULT_DEBUGGING_TIMEOUT


def should_trigger_debugging(
    hook_config: DebuggingHookConfig,
    dispatch_agent: str,
    dispatch_action: str,
) -> bool:
    """Check whether a debugging run should be triggered after a dispatch.

    Returns True if debugging hooks are enabled and the dispatch was a
    deploy-related action.
    """
    if not hook_config.enabled:
        return False

    deploy_keywords = ("deploy", "release", "publish", "ship")
    action_lower = dispatch_action.lower()
    return any(kw in action_lower for kw in deploy_keywords)


def create_debugging_dispatch(
    hook_config: DebuggingHookConfig,
    task_id: str,
    project_dir: str,
) -> DebuggingDispatch:
    """Create a debugging dispatch from hook config and task info."""
    return DebuggingDispatch(
        task_id=task_id,
        tool=hook_config.tool,
        project_dir=project_dir,
        timeout_seconds=hook_config.timeout_seconds,
    )


def get_debugging_timeout(
    agent_timeouts: dict[str, int],
    default_timeout: int = _DEFAULT_DEBUGGING_TIMEOUT,
) -> int:
    """Get the debugging agent timeout from scheduler config.

    Checks ``agent_timeouts`` for a ``debugging`` key, falling back
    to the provided default.
    """
    return agent_timeouts.get("debugging", default_timeout)


# -- Result reporting --


@dataclass(frozen=True)
class DebuggingReportEntry:
    """A debugging result formatted for reporting."""

    task_id: str
    overall_pass: bool
    steps_total: int = 0
    steps_passed: int = 0
    duration_seconds: float = 0.0
    escalated: bool = False
    escalation_reason: str = ""


def format_debugging_result(result: DebuggingResult) -> DebuggingReportEntry:
    """Convert a DebuggingResult into a report-friendly entry."""
    steps_total = 0
    steps_passed = 0
    if result.test_results is not None:
        steps_total = result.test_results.steps_total
        steps_passed = result.test_results.steps_passed

    return DebuggingReportEntry(
        task_id=result.task_id,
        overall_pass=result.overall_pass,
        steps_total=steps_total,
        steps_passed=steps_passed,
        duration_seconds=result.duration_seconds,
        escalated=result.escalated,
        escalation_reason=result.escalation_reason,
    )


def post_debugging_result_to_board(
    result: DebuggingResult,
    announcement_log: AnnouncementManager,
    decision_log: DecisionLog,
) -> None:
    """Post debugging results to the coordination board.

    Pass results go to announcements; fail results go to the decision log
    for escalation review.
    """
    entry = format_debugging_result(result)

    if entry.overall_pass:
        announcement_log.post(
            title=f"Debugging passed: {entry.task_id}",
            content=(
                f"Task {entry.task_id} passed all checks. "
                f"{entry.steps_passed}/{entry.steps_total} steps passed "
                f"in {entry.duration_seconds:.1f}s."
            ),
            author="debugging-agent",
        )
        _log.info("debugging_result_posted_announcement: task_id=%s", entry.task_id)
    else:
        decision_log.record(
            agent="debugging-agent",
            action=f"Debugging failed: {entry.task_id}",
            rationale=(
                f"Task {entry.task_id} failed. "
                f"{entry.steps_passed}/{entry.steps_total} steps passed. "
                f"Duration: {entry.duration_seconds:.1f}s."
                + (f" Escalated: {entry.escalation_reason}" if entry.escalated else "")
            ),
        )
        _log.info("debugging_result_posted_decision_log: task_id=%s", entry.task_id)


def make_debugging_dispatch_outcome(
    result: DebuggingResult,
) -> DispatchOutcome:
    """Create a DispatchOutcome from a DebuggingResult for cycle reports."""
    from autopilot.reporting.cycle_reports import DispatchOutcome

    entry = format_debugging_result(result)
    status = "success" if entry.overall_pass else "failed"
    error = entry.escalation_reason if entry.escalated else ""

    return DispatchOutcome(
        agent="debugging-agent",
        action=f"debug-{entry.task_id}",
        status=status,
        duration_seconds=entry.duration_seconds,
        error=error,
    )
