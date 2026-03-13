"""Agent invoker with retry and model fallback (Task 031).

Generalizes RepEngine agent.py into a reliable agent invocation layer
with exponential backoff, model fallback chains, empty output detection,
and structured result capture per RFC Section 3.3 and 3.8.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from autopilot.core.models import AgentResult, DispatchStatus
from autopilot.utils.sanitizer import sanitize
from autopilot.utils.subprocess import run_claude_cli

if TYPE_CHECKING:
    from pathlib import Path

    from autopilot.core.agent_registry import AgentRegistry
    from autopilot.core.config import AutopilotConfig

_log = logging.getLogger(__name__)

# Thresholds for empty output detection (from RepEngine)
_EMPTY_OUTPUT_MIN_DURATION = 8.0  # seconds
_DEFAULT_RETRY_DELAYS = (45, 90)  # exponential backoff delays
_DEFAULT_FALLBACK_CHAIN = ("opus", "claude-opus-4-5-20250514", "sonnet")


@dataclass(frozen=True)
class InvokeResult:
    """Result from agent invocation including retry metadata."""

    agent: str
    status: DispatchStatus
    exit_code: int = 0
    duration_seconds: float = 0.0
    output: str = ""
    error: str = ""
    model_used: str = ""
    retries: int = 0

    def to_agent_result(self) -> AgentResult:
        return AgentResult(
            agent=self.agent,
            status=self.status,
            exit_code=self.exit_code,
            duration_seconds=self.duration_seconds,
            output=self.output,
            error=self.error,
        )


class AgentInvoker:
    """Invokes Claude CLI agents with retry logic and model fallback.

    Loads agent prompts from the registry, injects project context,
    and calls Claude CLI with clean env, configurable model/timeouts,
    and structured result capture.
    """

    def __init__(
        self,
        registry: AgentRegistry,
        config: AutopilotConfig,
    ) -> None:
        self._registry = registry
        self._config = config

    def invoke(
        self,
        agent_name: str,
        prompt: str,
        *,
        cwd: Path | None = None,
    ) -> InvokeResult:
        """Invoke an agent with retry and model fallback.

        Loads the agent prompt from the registry, appends the caller-supplied
        prompt, and tries each model in the fallback chain until one succeeds.
        """
        agent_prompt = self._registry.load_prompt(agent_name)
        full_prompt = f"{agent_prompt}\n\n---\n\n{prompt}"

        fallback_chain = self._resolve_fallback_chain(agent_name)
        timeout = self._resolve_timeout(agent_name)
        extra_flags = self._config.claude.extra_flags

        last_result: InvokeResult | None = None

        for model in fallback_chain:
            result = self._invoke_with_retries(
                agent_name=agent_name,
                prompt=full_prompt,
                model=model,
                timeout=timeout,
                extra_flags=extra_flags,
                cwd=cwd,
            )
            if result.status == DispatchStatus.SUCCESS:
                return result
            last_result = result
            _log.warning(
                "agent_invoke_model_failed: agent=%s model=%s status=%s",
                agent_name,
                model,
                result.status,
            )

        if last_result is not None:
            return last_result
        return InvokeResult(
            agent=agent_name,
            status=DispatchStatus.FAILED,
            error="No models available in fallback chain",
        )

    def _invoke_with_retries(
        self,
        *,
        agent_name: str,
        prompt: str,
        model: str,
        timeout: int,
        extra_flags: str,
        cwd: Path | None,
    ) -> InvokeResult:
        """Try invoking the agent with exponential backoff retries."""
        retry_delays = _DEFAULT_RETRY_DELAYS
        last_error = ""
        last_exit_code = 0
        last_duration = 0.0

        for attempt in range(1 + len(retry_delays)):
            if attempt > 0:
                delay = retry_delays[attempt - 1]
                _log.info(
                    "agent_invoke_retry: agent=%s model=%s attempt=%d delay=%d",
                    agent_name,
                    model,
                    attempt + 1,
                    delay,
                )
                time.sleep(delay)

            start = time.monotonic()
            try:
                result = run_claude_cli(
                    prompt,
                    model=model,
                    max_turns=self._resolve_max_turns(agent_name),
                    extra_flags=extra_flags,
                    cwd=cwd,
                    timeout_seconds=timeout,
                )
                duration = time.monotonic() - start
                last_duration = duration
                output = sanitize(result.stdout.strip())
                last_exit_code = result.returncode

                if result.returncode == 0 and not _is_empty_output(output, duration):
                    return InvokeResult(
                        agent=agent_name,
                        status=DispatchStatus.SUCCESS,
                        exit_code=result.returncode,
                        duration_seconds=duration,
                        output=output,
                        model_used=model,
                        retries=attempt,
                    )

                if _is_empty_output(output, duration):
                    last_error = (
                        f"Empty output detected (exit 0, {duration:.1f}s, {len(output)} chars)"
                    )
                    _log.warning(
                        "agent_invoke_empty_output: agent=%s model=%s duration=%.1f",
                        agent_name,
                        model,
                        duration,
                    )
                else:
                    last_error = sanitize(result.stderr.strip()) or f"exit code {result.returncode}"

            except TimeoutError:
                last_duration = time.monotonic() - start
                last_error = f"Timeout after {timeout}s"
                last_exit_code = -1
                _log.warning(
                    "agent_invoke_timeout: agent=%s model=%s timeout=%d",
                    agent_name,
                    model,
                    timeout,
                )

        return InvokeResult(
            agent=agent_name,
            status=DispatchStatus.TIMEOUT if "Timeout" in last_error else DispatchStatus.FAILED,
            exit_code=last_exit_code,
            duration_seconds=last_duration,
            error=last_error,
            model_used=model,
            retries=len(retry_delays),
        )

    def _resolve_fallback_chain(self, agent_name: str) -> tuple[str, ...]:
        """Get the model fallback chain for an agent."""
        agent_fallbacks = self._config.agents.fallback_models.get(agent_name)
        if agent_fallbacks:
            return tuple(agent_fallbacks)
        agent_model = self._config.agents.models.get(agent_name)
        if agent_model:
            return (agent_model, *_DEFAULT_FALLBACK_CHAIN[1:])
        return _DEFAULT_FALLBACK_CHAIN

    def _resolve_timeout(self, agent_name: str) -> int:
        """Get the timeout for an agent from config."""
        return self._config.scheduler.agent_timeouts.get(
            agent_name,
            self._config.scheduler.agent_timeout_seconds,
        )

    def _resolve_max_turns(self, agent_name: str) -> int:
        """Get the max turns for an agent from config."""
        return self._config.agents.max_turns.get(agent_name, 10)


def _is_empty_output(output: str, duration: float) -> bool:
    """Detect empty output: exit 0 with no content and fast completion."""
    return len(output) == 0 and duration < _EMPTY_OUTPUT_MIN_DURATION
