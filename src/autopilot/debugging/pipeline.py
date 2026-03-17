"""Pipeline support functions for the debugging agent.

These are guardrail functions the LLM debugging agent invokes as tools.
They enforce constraints (source scope, iteration limits, quality gates)
but do NOT orchestrate the debugging workflow -- the LLM drives that.

See ADR-D03/D04 in the discovery document for rationale.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any, cast

import yaml

from autopilot.debugging.models import (
    DebuggingResult,
    DebuggingTask,
    FixCycleResults,
    InteractiveTestResults,
    RegressionTestResults,
    TestStep,
    UXReviewResults,
)

if TYPE_CHECKING:
    from autopilot.orchestration.agent_invoker import InvokeResult

_REQUIRED_FIELDS: tuple[str, ...] = (
    "task_id",
    "feature",
    "title",
    "description",
    "staging_url",
    "steps",
    "acceptance_criteria",
    "source_scope",
)


def load_debugging_task(task_path: Path) -> DebuggingTask:
    """Load a debugging task specification from a YAML file.

    Args:
        task_path: Path to the YAML task file.

    Returns:
        A validated ``DebuggingTask`` instance.

    Raises:
        ValueError: If the file is malformed YAML, not a mapping, or
            missing required fields.
    """
    raw_text = task_path.read_text(encoding="utf-8")

    try:
        data = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        msg = f"Failed to parse YAML from {task_path}: {exc}"
        raise ValueError(msg) from exc

    if not isinstance(data, dict):
        msg = f"Debugging task file must be a YAML mapping, got {type(data).__name__}"
        raise ValueError(msg)

    d = cast("dict[str, Any]", data)

    for field_name in _REQUIRED_FIELDS:
        if field_name not in d:
            msg = f"Missing required field '{field_name}' in {task_path}"
            raise ValueError(msg)

    for list_field in ("steps", "acceptance_criteria", "source_scope"):
        if not isinstance(d[list_field], list):
            msg = f"Field '{list_field}' must be a list in {task_path}, got {type(d[list_field]).__name__}"
            raise ValueError(msg)

    raw_steps: list[dict[str, Any]] = d["steps"]
    steps = tuple(
        TestStep(
            action=str(s["action"]),
            target=str(s["target"]),
            value=str(s.get("value", "")),
            expect=str(s.get("expect", "")),
            timeout_seconds=int(s.get("timeout_seconds", 30)),
        )
        for s in raw_steps
    )

    return DebuggingTask(
        task_id=str(d["task_id"]),
        feature=str(d["feature"]),
        title=str(d["title"]),
        description=str(d["description"]),
        staging_url=str(d["staging_url"]),
        steps=steps,
        acceptance_criteria=tuple(str(c) for c in d["acceptance_criteria"]),
        source_scope=tuple(str(s) for s in d["source_scope"]),
        ux_review_enabled=bool(d.get("ux_review_enabled", True)),
        ux_capture_states=tuple(str(s) for s in d.get("ux_capture_states", ())),
    )


def validate_source_scope(
    modified_files: tuple[str, ...],
    allowed_scope: tuple[str, ...],
) -> bool:
    """Check that all modified files fall within the allowed source scope.

    Uses ``PurePosixPath`` for prefix comparison so that
    ``src/authorization/`` does not accidentally match ``src/auth/``.

    Args:
        modified_files: Paths of files changed during a fix attempt.
        allowed_scope: Path prefixes that the debugging agent is allowed
            to modify.

    Returns:
        ``True`` if every modified file is within at least one allowed
        scope prefix, ``False`` otherwise.
    """
    if not modified_files:
        return True

    scope_parts = [PurePosixPath(s).parts for s in allowed_scope]

    for file_str in modified_files:
        file_parts = PurePosixPath(file_str).parts
        if not any(file_parts[: len(sp)] == sp for sp in scope_parts):
            return False

    return True


def run_quality_gates(
    project_dir: Path,
    timeout_seconds: int = 1800,
) -> tuple[bool, str]:
    """Run ``just all`` as the quality gate and report the result.

    Args:
        project_dir: Root directory of the project under test.
        timeout_seconds: Maximum seconds to wait for the command.

    Returns:
        A ``(passed, output)`` tuple.  *passed* is ``True`` when the
        process exits with code 0; *output* contains stdout on success
        or stderr (falling back to stdout) on failure.
    """
    try:
        proc = subprocess.run(
            ["just", "all"],
            capture_output=True,
            text=True,
            cwd=project_dir,
            timeout=timeout_seconds,
        )
    except FileNotFoundError:
        return (False, "quality gate runner 'just' not found")
    except subprocess.TimeoutExpired:
        return (False, f"quality gates timed out after {timeout_seconds}s")

    if proc.returncode == 0:
        return (True, proc.stdout)

    return (False, proc.stderr or proc.stdout)


def track_fix_iteration(
    task_id: str,
    attempt: int,
    max_iterations: int,
) -> tuple[bool, str]:
    """Decide whether the debugging agent may attempt another fix.

    Args:
        task_id: Identifier of the debugging task.
        attempt: Current 1-based attempt number.
        max_iterations: Maximum allowed iterations before escalation.

    Returns:
        A ``(can_continue, message)`` tuple.  *can_continue* is
        ``False`` when the iteration limit has been reached.
    """
    if attempt <= max_iterations:
        return (True, f"Attempt {attempt}/{max_iterations} for task {task_id}")

    return (
        False,
        f"Max iterations ({max_iterations}) reached for task {task_id}. Escalating.",
    )


def validate_debugging_run(
    task: DebuggingTask,
    result: DebuggingResult,
) -> tuple[bool, str]:
    """Validate the outcome of a complete debugging run.

    Args:
        task: The original debugging task specification.
        result: The composite result produced by the debugging agent.

    Returns:
        A ``(passed, message)`` tuple summarising whether the run
        succeeded.
    """
    if result.escalated:
        return (False, f"Task {task.task_id} was escalated: {result.escalation_reason}")

    if result.overall_pass:
        return (True, f"Task {task.task_id} passed all checks")

    return (False, f"Task {task.task_id} did not pass: overall_pass=False")


# -- Fenced-block JSON extraction pattern --
_JSON_FENCE = re.compile(r"```json\s*\n(.*?)\n\s*```", re.DOTALL)


def collect_debugging_result(
    task: DebuggingTask,
    agent_result: InvokeResult,
) -> DebuggingResult:
    """Parse the debugging agent's structured output into a :class:`DebuggingResult`.

    Extracts a JSON block from the agent output — either a fenced ``json``
    code block or raw JSON — and maps it to model dataclasses.  On parse
    failure, returns an escalated result rather than raising.

    Args:
        task: The original debugging task specification.
        agent_result: The invoke result from ``AgentInvoker``.

    Returns:
        A populated ``DebuggingResult``.
    """
    raw_output = agent_result.output.strip()

    if not raw_output:
        return DebuggingResult(
            task_id=task.task_id,
            escalated=True,
            escalation_reason="Failed to parse agent output: empty output",
        )

    parsed = _extract_json(raw_output)
    if parsed is None:
        return DebuggingResult(
            task_id=task.task_id,
            escalated=True,
            escalation_reason="Failed to parse agent output: no valid JSON found",
        )

    return _build_result(task.task_id, parsed)


def _extract_json(text: str) -> dict[str, Any] | None:
    """Extract a JSON object from agent output text.

    Tries fenced ``json`` block first, then raw JSON parsing.
    """
    # Try fenced code block
    match = _JSON_FENCE.search(text)
    if match:
        try:
            data = json.loads(match.group(1))
            if isinstance(data, dict):
                return cast("dict[str, Any]", data)
        except json.JSONDecodeError:
            pass

    # Try raw JSON
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return cast("dict[str, Any]", data)
    except json.JSONDecodeError:
        pass

    return None


def _build_result(task_id: str, data: dict[str, Any]) -> DebuggingResult:
    """Build a DebuggingResult from parsed JSON data."""
    test_results = _parse_test_results(data.get("test_results"))
    fix_results = _parse_fix_results(data.get("fix_results"))
    regression_results = _parse_regression_results(data.get("regression_results"))
    ux_results = _parse_ux_results(data.get("ux_results"))

    return DebuggingResult(
        task_id=str(data.get("task_id", task_id)),
        overall_pass=bool(data.get("overall_pass", False)),
        test_results=test_results,
        fix_results=fix_results,
        regression_results=regression_results,
        ux_results=ux_results,
        duration_seconds=float(data.get("duration_seconds", 0.0)),
        escalated=bool(data.get("escalated", False)),
        escalation_reason=str(data.get("escalation_reason", "")),
    )


def _parse_test_results(data: Any) -> InteractiveTestResults | None:
    if not isinstance(data, dict):
        return None
    d = cast("dict[str, Any]", data)
    return InteractiveTestResults(
        steps_total=int(d.get("steps_total", 0)),
        steps_passed=int(d.get("steps_passed", 0)),
        steps_failed=int(d.get("steps_failed", 0)),
        all_passed=bool(d.get("all_passed", False)),
        duration_seconds=float(d.get("duration_seconds", 0.0)),
    )


def _parse_fix_results(data: Any) -> FixCycleResults | None:
    if not isinstance(data, dict):
        return None
    d = cast("dict[str, Any]", data)
    return FixCycleResults(
        resolved=bool(d.get("resolved", False)),
        final_diagnosis=str(d.get("final_diagnosis", "")),
        duration_seconds=float(d.get("duration_seconds", 0.0)),
    )


def _parse_regression_results(data: Any) -> RegressionTestResults | None:
    if not isinstance(data, dict):
        return None
    d = cast("dict[str, Any]", data)
    return RegressionTestResults(
        tests_generated=int(d.get("tests_generated", 0)),
        tests_passed=int(d.get("tests_passed", 0)),
        tests_failed=int(d.get("tests_failed", 0)),
        test_file_path=str(d.get("test_file_path", "")),
        duration_seconds=float(d.get("duration_seconds", 0.0)),
    )


def _parse_ux_results(data: Any) -> UXReviewResults | None:
    if not isinstance(data, dict):
        return None
    d = cast("dict[str, Any]", data)
    return UXReviewResults(
        overall_pass=bool(d.get("overall_pass", False)),
        summary=str(d.get("summary", "")),
        duration_seconds=float(d.get("duration_seconds", 0.0)),
    )
