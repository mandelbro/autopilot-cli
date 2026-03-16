"""Shared fixtures for debugging subsystem tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

from autopilot.core.config import DebuggingConfig, DebuggingToolConfig
from autopilot.debugging.models import DebuggingTask, TestStep
from autopilot.debugging.tools.protocol import (
    DiagnosticEvidence,
    InteractionResult,
    ProvisionResult,
    ProvisionStatus,
    ToolCapability,
    UXObservation,
)


class _MinimalDebuggingTool:
    """A minimal implementation satisfying the DebuggingTool protocol."""

    @property
    def name(self) -> str:
        return "mock-tool"

    @property
    def capabilities(self) -> frozenset[ToolCapability]:
        return frozenset({ToolCapability.INTERACTIVE_TEST})

    def provision(self, settings: dict[str, object]) -> ProvisionResult:
        return ProvisionResult(success=True)

    def deprovision(self) -> None:
        return None

    def check_provisioned(self) -> ProvisionStatus:
        return ProvisionStatus(provisioned=True, ready=True)

    def setup(self, settings: dict[str, object]) -> None:
        return None

    def teardown(self) -> None:
        return None

    def execute_step(
        self,
        action: str,
        target: str,
        *,
        value: str = "",
        expect: str = "",
        timeout_seconds: int = 30,
    ) -> InteractionResult:
        return InteractionResult(success=True)

    def capture_diagnostic_evidence(self) -> DiagnosticEvidence:
        return DiagnosticEvidence()

    def capture_screenshot(self, label: str) -> str:
        return f"/tmp/{label}.png"

    def evaluate_ux(
        self,
        criteria: tuple[str, ...],
        design_system_ref: str = "",
    ) -> tuple[UXObservation, ...]:
        return ()


@pytest.fixture
def mock_debugging_tool() -> _MinimalDebuggingTool:
    """A minimal class satisfying the DebuggingTool protocol."""
    return _MinimalDebuggingTool()


@pytest.fixture
def sample_debugging_task() -> Callable[..., DebuggingTask]:
    """Factory fixture returning a DebuggingTask with valid defaults."""

    def _factory(**overrides: object) -> DebuggingTask:
        defaults: dict[str, object] = {
            "task_id": "DBG-001",
            "feature": "login",
            "title": "Verify login flow",
            "description": "End-to-end login test",
            "staging_url": "http://staging.example.com",
            "steps": (TestStep(action="click", target="#login-btn"),),
            "acceptance_criteria": ("User is redirected to dashboard",),
            "source_scope": ("src/auth/",),
        }
        defaults.update(overrides)
        return DebuggingTask(**defaults)  # type: ignore[arg-type]

    return _factory


@pytest.fixture
def debugging_config() -> DebuggingConfig:
    """A DebuggingConfig with a mock browser_mcp tool entry."""
    return DebuggingConfig(
        enabled=True,
        tool="browser_mcp",
        tools={
            "browser_mcp": DebuggingToolConfig(
                module="autopilot.debugging.tools.browser_mcp",
                class_name="BrowserMCPTool",
                settings={"headless": True},
            ),
        },
    )
