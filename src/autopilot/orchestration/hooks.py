"""Workflow hooks for cycle and dispatch boundaries (Task 088).

Executes configurable shell commands at pre_cycle, post_cycle,
pre_dispatch, and post_dispatch lifecycle points.
"""

from __future__ import annotations

import logging
import subprocess
import time
from dataclasses import dataclass
from typing import Any

_log = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 30  # seconds

_VALID_HOOK_POINTS = frozenset({"pre_cycle", "post_cycle", "pre_dispatch", "post_dispatch"})


@dataclass(frozen=True)
class HookResult:
    """Result of a single hook execution."""

    hook_point: str  # pre_cycle, post_cycle, pre_dispatch, post_dispatch
    command: str
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = 0.0
    timed_out: bool = False


@dataclass(frozen=True)
class HookConfig:
    """Configuration for a single hook."""

    hook_point: str
    command: str
    timeout: int = _DEFAULT_TIMEOUT
    abort_on_failure: bool = False  # If True + exit code 2, abort cycle


class HookRunner:
    """Executes lifecycle hooks at cycle and dispatch boundaries.

    Hook points:
    - pre_cycle: Before a cycle starts
    - post_cycle: After a cycle completes
    - pre_dispatch: Before each agent dispatch
    - post_dispatch: After each agent dispatch

    Variable substitution in commands:
    - {agent}: Agent name (dispatch hooks only)
    - {action}: Action description (dispatch hooks only)
    - {project}: Project name
    - {cycle_id}: Current cycle ID

    Failure handling:
    - Exit code 0: success
    - Exit code 1: warning logged, cycle continues
    - Exit code 2 with abort_on_failure=True: abort cycle
    - Timeout: warning logged, cycle continues
    """

    def __init__(self, hooks: list[HookConfig] | None = None) -> None:
        self._hooks = hooks or []

    @classmethod
    def from_config(cls, hooks_config: list[dict[str, Any]]) -> HookRunner:
        """Create HookRunner from config dict list.

        Expected format:
        [
            {"hook_point": "pre_cycle", "command": "git fetch", "timeout": 30},
            {"hook_point": "post_dispatch", "command": "echo {agent} done"},
        ]
        """
        hooks: list[HookConfig] = []
        for h in hooks_config:
            hook_point: str = str(h.get("hook_point", ""))
            command: str = str(h.get("command", ""))
            timeout_val = h.get("timeout", _DEFAULT_TIMEOUT)
            timeout: int = (
                int(timeout_val) if isinstance(timeout_val, (int, float)) else _DEFAULT_TIMEOUT
            )
            abort_val = h.get("abort_on_failure", False)
            abort_on_failure: bool = bool(abort_val)
            hooks.append(
                HookConfig(
                    hook_point=hook_point,
                    command=command,
                    timeout=timeout,
                    abort_on_failure=abort_on_failure,
                )
            )
        return cls(hooks)

    def run_hooks(
        self,
        hook_point: str,
        context: dict[str, str] | None = None,
    ) -> list[HookResult]:
        """Execute all hooks registered for the given hook point.

        Args:
            hook_point: One of pre_cycle, post_cycle, pre_dispatch, post_dispatch
            context: Variable substitution context (agent, action, project, cycle_id)

        Returns:
            List of HookResult for each executed hook
        """
        ctx = context or {}
        results: list[HookResult] = []

        matching_hooks = [h for h in self._hooks if h.hook_point == hook_point]

        for hook in matching_hooks:
            command = self._substitute(hook.command, ctx)
            result = self._execute(hook_point, command, hook.timeout)
            results.append(result)

            if result.exit_code != 0:
                _log.warning(
                    "hook_failed: point=%s command=%s exit_code=%d",
                    hook_point,
                    command,
                    result.exit_code,
                )
                if hook.abort_on_failure and result.exit_code == 2:
                    _log.error("hook_abort: point=%s — aborting cycle", hook_point)
                    break

        return results

    def should_abort(self, results: list[HookResult]) -> bool:
        """Check if any hook result should abort the cycle."""
        for result in results:
            matching = [
                h
                for h in self._hooks
                if h.hook_point == result.hook_point and h.command in result.command
            ]
            for hook in matching:
                if hook.abort_on_failure and result.exit_code == 2:
                    return True
        return False

    def _substitute(self, command: str, context: dict[str, str]) -> str:
        """Substitute {variables} in command string."""
        result = command
        for key, value in context.items():
            result = result.replace(f"{{{key}}}", value)
        return result

    def _execute(self, hook_point: str, command: str, timeout: int) -> HookResult:
        """Execute a single hook command via subprocess."""
        start = time.monotonic()
        try:
            proc = subprocess.run(
                command,
                shell=True,  # noqa: S602 — hooks are user-configured commands
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            duration = time.monotonic() - start
            return HookResult(
                hook_point=hook_point,
                command=command,
                exit_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                duration_seconds=round(duration, 3),
            )
        except subprocess.TimeoutExpired:
            duration = time.monotonic() - start
            _log.warning("hook_timeout: command=%s timeout=%d", command, timeout)
            return HookResult(
                hook_point=hook_point,
                command=command,
                exit_code=-1,
                stderr=f"Timed out after {timeout}s",
                duration_seconds=round(duration, 3),
                timed_out=True,
            )
        except Exception as exc:
            duration = time.monotonic() - start
            return HookResult(
                hook_point=hook_point,
                command=command,
                exit_code=-1,
                stderr=str(exc),
                duration_seconds=round(duration, 3),
            )
