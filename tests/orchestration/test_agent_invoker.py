"""Tests for agent invoker with retry and model fallback (Task 031)."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from autopilot.core.config import (
    AgentsConfig,
    AutopilotConfig,
    ClaudeConfig,
    ProjectConfig,
    SchedulerConfig,
)
from autopilot.core.models import DispatchStatus
from autopilot.orchestration.agent_invoker import AgentInvoker, _is_empty_output


@pytest.fixture()
def config() -> AutopilotConfig:
    return AutopilotConfig(
        project=ProjectConfig(name="test"),
        scheduler=SchedulerConfig(
            agent_timeout_seconds=60,
            agent_timeouts={"slow-agent": 120},
        ),
        agents=AgentsConfig(
            models={"custom-agent": "haiku"},
            max_turns={"custom-agent": 5},
            fallback_models={"custom-agent": ["haiku", "sonnet"]},
        ),
        claude=ClaudeConfig(extra_flags="--dangerously-skip-permissions"),
    )


@pytest.fixture()
def registry() -> MagicMock:
    reg = MagicMock()
    reg.load_prompt.return_value = "You are a test agent."
    return reg


@pytest.fixture()
def invoker(registry: MagicMock, config: AutopilotConfig) -> AgentInvoker:
    return AgentInvoker(registry=registry, config=config)


class TestAgentInvokerSuccess:
    def test_successful_invocation(self, invoker: AgentInvoker) -> None:
        completed = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="Agent output here", stderr=""
        )
        with patch(
            "autopilot.orchestration.agent_invoker.run_claude_cli",
            return_value=completed,
        ):
            result = invoker.invoke("project-leader", "Do something")

        assert result.status == DispatchStatus.SUCCESS
        assert result.output == "Agent output here"
        assert result.exit_code == 0
        assert result.model_used == "opus"

    def test_output_is_sanitized(self, invoker: AgentInvoker) -> None:
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="Token: sk-ant-AAAAAAAAAAAAAAAAAAAAAA leaked",
            stderr="",
        )
        with patch(
            "autopilot.orchestration.agent_invoker.run_claude_cli",
            return_value=completed,
        ):
            result = invoker.invoke("project-leader", "Check secrets")

        assert "sk-ant-" not in result.output
        assert "[REDACTED_API_KEY]" in result.output


class TestAgentInvokerRetry:
    def test_retries_on_failure_then_succeeds(self, invoker: AgentInvoker) -> None:
        fail = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="error")
        success = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="Success output", stderr=""
        )
        with (
            patch(
                "autopilot.orchestration.agent_invoker.run_claude_cli",
                side_effect=[fail, success],
            ),
            patch("autopilot.orchestration.agent_invoker.time.sleep"),
        ):
            result = invoker.invoke("project-leader", "Retry test")

        assert result.status == DispatchStatus.SUCCESS
        assert result.output == "Success output"
        assert result.retries == 1

    def test_retries_exhausted_falls_to_next_model(self, invoker: AgentInvoker) -> None:
        fail = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="error")
        success = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="Fallback success", stderr=""
        )
        with (
            patch(
                "autopilot.orchestration.agent_invoker.run_claude_cli",
                side_effect=[fail, fail, fail, success],
            ),
            patch("autopilot.orchestration.agent_invoker.time.sleep"),
        ):
            result = invoker.invoke("project-leader", "Fallback test")

        assert result.status == DispatchStatus.SUCCESS
        assert result.output == "Fallback success"


class TestAgentInvokerEmptyOutput:
    def test_empty_output_detected_as_failure(self, invoker: AgentInvoker) -> None:
        completed = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        call_count = 0

        def fake_monotonic() -> float:
            nonlocal call_count
            call_count += 1
            # Each invocation pair: start=N*100, end=start+3 (fast = empty)
            return float(call_count)

        with (
            patch(
                "autopilot.orchestration.agent_invoker.run_claude_cli",
                return_value=completed,
            ),
            patch(
                "autopilot.orchestration.agent_invoker.time.monotonic",
                side_effect=fake_monotonic,
            ),
            patch("autopilot.orchestration.agent_invoker.time.sleep"),
        ):
            result = invoker.invoke("project-leader", "Empty output")

        assert result.status != DispatchStatus.SUCCESS


class TestAgentInvokerTimeout:
    def test_timeout_handling(self, invoker: AgentInvoker) -> None:
        call_count = 0

        def fake_monotonic() -> float:
            nonlocal call_count
            call_count += 1
            return float(call_count * 60)

        with (
            patch(
                "autopilot.orchestration.agent_invoker.run_claude_cli",
                side_effect=TimeoutError("Timed out"),
            ),
            patch(
                "autopilot.orchestration.agent_invoker.time.monotonic",
                side_effect=fake_monotonic,
            ),
            patch("autopilot.orchestration.agent_invoker.time.sleep"),
        ):
            result = invoker.invoke("project-leader", "Timeout test")

        assert result.status == DispatchStatus.TIMEOUT


class TestAgentInvokerConfig:
    def test_per_agent_timeout(self, invoker: AgentInvoker) -> None:
        assert invoker._resolve_timeout("slow-agent") == 120
        assert invoker._resolve_timeout("unknown-agent") == 60

    def test_custom_fallback_chain(self, invoker: AgentInvoker) -> None:
        chain = invoker._resolve_fallback_chain("custom-agent")
        assert chain == ("haiku", "sonnet")

    def test_default_fallback_chain(self, invoker: AgentInvoker) -> None:
        chain = invoker._resolve_fallback_chain("unknown-agent")
        assert chain[0] == "opus"

    def test_per_agent_max_turns(self, invoker: AgentInvoker) -> None:
        assert invoker._resolve_max_turns("custom-agent") == 5
        assert invoker._resolve_max_turns("unknown-agent") == 10


class TestEmptyOutputDetection:
    def test_empty_and_fast_is_empty(self) -> None:
        assert _is_empty_output("", 3.0) is True

    def test_empty_but_slow_is_not_empty(self) -> None:
        assert _is_empty_output("", 10.0) is False

    def test_has_content_is_not_empty(self) -> None:
        assert _is_empty_output("some output", 3.0) is False
