"""Pipeline support functions for the debugging agent.

These are guardrail functions the LLM debugging agent invokes as tools.
They enforce constraints (source scope, iteration limits, quality gates)
but do NOT orchestrate the debugging workflow -- the LLM drives that.

See ADR-D03/D04 in the discovery document for rationale.
"""

from __future__ import annotations

import subprocess
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any, cast

import yaml

from autopilot.debugging.models import DebuggingTask, TestStep

if TYPE_CHECKING:
    from autopilot.debugging.models import DebuggingResult

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
