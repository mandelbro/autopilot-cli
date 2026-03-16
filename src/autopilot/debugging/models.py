"""Debugging pipeline data models.

Defines the input/output contracts for debugging tasks, fix attempts,
test results, and the composite DebuggingResult.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autopilot.debugging.tools.protocol import (
        InteractionResult,
        ProvisionStatus,
        UXObservation,
    )


@dataclass(frozen=True)
class TestStep:
    """A single step in an interactive test plan."""

    action: str
    target: str
    value: str = ""
    expect: str = ""
    timeout_seconds: int = 30


@dataclass(frozen=True)
class DebuggingTask:
    """Input specification for a debugging run."""

    task_id: str
    feature: str
    title: str
    description: str
    staging_url: str
    steps: tuple[TestStep, ...]
    acceptance_criteria: tuple[str, ...]
    source_scope: tuple[str, ...]
    ux_review_enabled: bool = True
    ux_capture_states: tuple[str, ...] = ()


@dataclass(frozen=True)
class FixAttempt:
    """Record of a single fix iteration."""

    iteration: int
    diagnosis: str
    files_modified: tuple[str, ...]
    pr_url: str = ""
    tests_passed: bool = False
    error: str = ""


@dataclass(frozen=True)
class InteractiveTestResults:
    """Results from interactive testing phase."""

    steps_total: int = 0
    steps_passed: int = 0
    steps_failed: int = 0
    all_passed: bool = False
    step_results: tuple[InteractionResult, ...] = ()
    duration_seconds: float = 0.0


@dataclass(frozen=True)
class FixCycleResults:
    """Results from the diagnose-and-fix cycle."""

    attempts: tuple[FixAttempt, ...] = ()
    resolved: bool = False
    final_diagnosis: str = ""
    duration_seconds: float = 0.0


@dataclass(frozen=True)
class RegressionTestResults:
    """Results from regression test generation and execution."""

    tests_generated: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    test_file_path: str = ""
    duration_seconds: float = 0.0


@dataclass(frozen=True)
class UXReviewResults:
    """Results from UX review phase."""

    observations: tuple[UXObservation, ...] = ()
    overall_pass: bool = False
    summary: str = ""
    duration_seconds: float = 0.0


@dataclass(frozen=True)
class DebuggingResult:
    """Complete output from a debugging pipeline run."""

    task_id: str
    overall_pass: bool = False
    test_results: InteractiveTestResults | None = None
    fix_results: FixCycleResults | None = None
    regression_results: RegressionTestResults | None = None
    ux_results: UXReviewResults | None = None
    duration_seconds: float = 0.0
    escalated: bool = False
    escalation_reason: str = ""


class ToolNotProvisionedError(RuntimeError):
    """Raised when a debugging tool has not been provisioned."""

    def __init__(self, tool_name: str, status: ProvisionStatus) -> None:
        self.tool_name = tool_name
        self.status = status
        super().__init__(
            f"Tool '{tool_name}' is not provisioned. "
            f"Run 'autopilot debug provision {tool_name}' first. "
            f"Status: {status.message}"
        )
