"""Tests for debugging tool protocol and supporting data models (Task 004)."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

import pytest

from autopilot.debugging.tools.protocol import (
    PROTOCOL_VERSION,
    DebuggingTool,
    DiagnosticEvidence,
    InteractionResult,
    ProvisionResult,
    ProvisionStatus,
    ToolCapability,
    UXObservation,
)

if TYPE_CHECKING:
    from tests.debugging.conftest import _MinimalDebuggingTool


class TestToolCapability:
    def test_has_five_members(self) -> None:
        assert len(ToolCapability) == 5

    def test_interactive_test_value(self) -> None:
        assert ToolCapability.INTERACTIVE_TEST == "interactive_test"

    def test_console_capture_value(self) -> None:
        assert ToolCapability.CONSOLE_CAPTURE == "console_capture"

    def test_network_capture_value(self) -> None:
        assert ToolCapability.NETWORK_CAPTURE == "network_capture"

    def test_screenshot_value(self) -> None:
        assert ToolCapability.SCREENSHOT == "screenshot"

    def test_ux_review_value(self) -> None:
        assert ToolCapability.UX_REVIEW == "ux_review"

    def test_string_representation(self) -> None:
        assert str(ToolCapability.INTERACTIVE_TEST) == "interactive_test"
        assert f"{ToolCapability.UX_REVIEW}" == "ux_review"


class TestInteractionResult:
    def test_default_construction(self) -> None:
        result = InteractionResult(success=True)
        assert result.success is True
        assert result.screenshot_path == ""
        assert result.console_output == ""
        assert result.network_log == ""
        assert result.observation == ""
        assert result.error == ""

    def test_full_construction(self) -> None:
        result = InteractionResult(
            success=False,
            screenshot_path="/tmp/shot.png",
            console_output="TypeError",
            network_log="GET /api 500",
            observation="Button did not respond",
            error="click failed",
        )
        assert result.success is False
        assert result.screenshot_path == "/tmp/shot.png"
        assert result.error == "click failed"

    def test_frozen_immutability(self) -> None:
        result = InteractionResult(success=True)
        with pytest.raises(dataclasses.FrozenInstanceError):
            result.success = False  # type: ignore[misc]


class TestDiagnosticEvidence:
    def test_default_construction(self) -> None:
        evidence = DiagnosticEvidence()
        assert evidence.screenshots == ()
        assert evidence.console_errors == ()
        assert evidence.network_failures == ()
        assert evidence.state_dumps == ()
        assert evidence.observations == ""

    def test_frozen_immutability(self) -> None:
        evidence = DiagnosticEvidence()
        with pytest.raises(dataclasses.FrozenInstanceError):
            evidence.observations = "changed"  # type: ignore[misc]


class TestUXObservation:
    def test_required_fields(self) -> None:
        obs = UXObservation(
            category="layout",
            severity="warning",
            description="Button overlap",
        )
        assert obs.category == "layout"
        assert obs.severity == "warning"
        assert obs.description == "Button overlap"
        assert obs.screenshot_path == ""
        assert obs.element_reference == ""

    def test_frozen_immutability(self) -> None:
        obs = UXObservation(category="a", severity="b", description="c")
        with pytest.raises(dataclasses.FrozenInstanceError):
            obs.category = "other"  # type: ignore[misc]


class TestProvisionResult:
    def test_default_construction(self) -> None:
        result = ProvisionResult(success=True)
        assert result.success is True
        assert result.components_installed == ()
        assert result.manual_steps == ()
        assert result.error == ""
        assert result.duration_seconds == 0.0

    def test_frozen_immutability(self) -> None:
        result = ProvisionResult(success=False)
        with pytest.raises(dataclasses.FrozenInstanceError):
            result.success = True  # type: ignore[misc]


class TestProvisionStatus:
    def test_default_construction(self) -> None:
        status = ProvisionStatus(provisioned=True, ready=False)
        assert status.provisioned is True
        assert status.ready is False
        assert status.components == {}
        assert status.message == ""

    def test_frozen_immutability(self) -> None:
        status = ProvisionStatus(provisioned=True, ready=True)
        with pytest.raises(dataclasses.FrozenInstanceError):
            status.provisioned = False  # type: ignore[misc]


class TestDebuggingToolProtocol:
    def test_minimal_class_satisfies_protocol(
        self, mock_debugging_tool: _MinimalDebuggingTool
    ) -> None:
        assert isinstance(mock_debugging_tool, DebuggingTool)

    def test_class_missing_method_fails_isinstance(self) -> None:
        class IncompleteToolMissingExecuteStep:
            @property
            def name(self) -> str:
                return "incomplete"

            @property
            def capabilities(self) -> frozenset[ToolCapability]:
                return frozenset()

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

            # Missing: execute_step, capture_diagnostic_evidence,
            #          capture_screenshot, evaluate_ux

        incomplete = IncompleteToolMissingExecuteStep()
        assert not isinstance(incomplete, DebuggingTool)


class TestProtocolVersion:
    def test_protocol_version_is_one(self) -> None:
        assert PROTOCOL_VERSION == 1
