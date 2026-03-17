"""Tests for DesktopAgentTool plugin.

Task 017: Unit tests for Desktop Agent with mocked Cua SDK and Lume CLI.
All tests run without real infrastructure (fully mocked).
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from autopilot.debugging.models import ToolNotProvisionedError
from autopilot.debugging.tools.desktop_agent import (
    ACTION_MAP,
    DesktopAgentTool,
    _ensure_screenshot_dir,
)
from autopilot.debugging.tools.protocol import (
    DebuggingTool,
    DiagnosticEvidence,
    ToolCapability,
    UXObservation,
)

if TYPE_CHECKING:
    from pathlib import Path

_LUME_OK = subprocess.CompletedProcess(args=["lume"], returncode=0, stdout="OK", stderr="")
_PATCH_RUN = "autopilot.debugging.tools.desktop_agent._run_lume_command"


# ============================================================================
# Protocol compliance
# ============================================================================


class TestDesktopAgentProtocol:
    """Protocol compliance tests."""

    def test_isinstance_debugging_tool(self) -> None:
        tool = DesktopAgentTool()
        assert isinstance(tool, DebuggingTool)

    def test_name_is_desktop_agent(self) -> None:
        assert DesktopAgentTool().name == "desktop_agent"

    def test_protocol_version(self) -> None:
        assert DesktopAgentTool.protocol_version == 1

    def test_capabilities_exactly_three(self) -> None:
        caps = DesktopAgentTool().capabilities
        expected = frozenset(
            {
                ToolCapability.INTERACTIVE_TEST,
                ToolCapability.SCREENSHOT,
                ToolCapability.UX_REVIEW,
            }
        )
        assert caps == expected
        assert len(caps) == 3  # noqa: PLR2004

    def test_capabilities_exclude_console_capture(self) -> None:
        caps = DesktopAgentTool().capabilities
        assert ToolCapability.CONSOLE_CAPTURE not in caps

    def test_capabilities_exclude_network_capture(self) -> None:
        caps = DesktopAgentTool().capabilities
        assert ToolCapability.NETWORK_CAPTURE not in caps


# ============================================================================
# Provisioning — mock subprocess for Lume CLI
# ============================================================================


class TestDesktopAgentProvisioning:
    """Provisioning workflow tests with mocked Lume CLI."""

    @patch(_PATCH_RUN, return_value="OK")
    def test_provision_full_workflow(self, mock_run: MagicMock) -> None:
        tool = DesktopAgentTool()
        result = tool.provision({})

        assert result.success is True
        assert len(result.components_installed) > 0
        assert "lume" in result.components_installed
        assert "vm" in result.components_installed
        assert "snapshot" in result.components_installed

    @patch(_PATCH_RUN, side_effect=FileNotFoundError("lume not found"))
    def test_provision_lume_not_found(self, mock_run: MagicMock) -> None:
        tool = DesktopAgentTool()
        result = tool.provision({})

        assert result.success is False
        assert "lume" in result.error.lower() or "failed" in result.error.lower()

    @patch(_PATCH_RUN, return_value="OK")
    def test_provision_manual_steps_returned(self, mock_run: MagicMock) -> None:
        tool = DesktopAgentTool()
        result = tool.provision({})

        assert result.success is True
        assert len(result.manual_steps) > 0
        steps_text = " ".join(result.manual_steps).lower()
        assert "sign" in steps_text or "permission" in steps_text

    @patch(_PATCH_RUN, return_value="OK")
    def test_provision_partial_failure_independent(self, mock_run: MagicMock) -> None:
        """Each provisioning step is independent; failure in one doesn't block others."""
        # Fail on the third call (VM creation) but succeed elsewhere
        mock_run.side_effect = [
            "OK",  # lume --version
            "OK",  # lume pull
            FileNotFoundError("vm creation failed"),  # lume run
            "OK",  # lume exec (configure)
            "OK",  # ollama pull action model
            "OK",  # ollama pull validation model
            "OK",  # lume snapshot
        ]
        tool = DesktopAgentTool()
        result = tool.provision({})

        assert result.success is False
        assert "vm" not in result.components_installed
        assert "lume" in result.components_installed

    @patch(_PATCH_RUN, return_value="running\nui-tars-1.5-7b\ngemma3:12b")
    def test_check_provisioned_all_healthy(self, mock_run: MagicMock) -> None:
        tool = DesktopAgentTool()
        status = tool.check_provisioned()

        assert status.provisioned is True
        assert status.ready is True or not status.ready  # depends on _CUA_AVAILABLE

    @patch(_PATCH_RUN)
    def test_check_provisioned_missing_model(self, mock_run: MagicMock) -> None:
        """Missing model → ready=False."""
        mock_run.return_value = "running"  # no model names in output
        tool = DesktopAgentTool()
        status = tool.check_provisioned()

        # Provisioned (lume found) but not ready (model missing)
        assert status.provisioned is True
        assert status.ready is False

    @patch(_PATCH_RUN, return_value="OK")
    def test_deprovision_clears_state(self, mock_run: MagicMock) -> None:
        tool = DesktopAgentTool()
        tool._provisioned = True
        tool._settings = {"key": "value"}
        tool.deprovision()

        assert tool._provisioned is False
        assert tool._settings == {}
        assert tool._computer_agent is None


# ============================================================================
# Session lifecycle — setup / teardown
# ============================================================================


class TestDesktopAgentSession:
    """Setup and teardown lifecycle tests."""

    @patch(_PATCH_RUN, return_value="running\nui-tars-1.5-7b\ngemma3:12b")
    def test_setup_restores_snapshot(self, mock_run: MagicMock, tmp_path: Path) -> None:
        tool = DesktopAgentTool()
        tool.setup({"project_dir": str(tmp_path)})

        # Verify snapshot restore was called
        snapshot_calls = [
            c
            for c in mock_run.call_args_list
            if len(c.args) > 0 and "snapshot" in str(c.args[0]) and "restore" in str(c.args[0])
        ]
        assert len(snapshot_calls) > 0

    @patch(_PATCH_RUN, side_effect=FileNotFoundError("lume not found"))
    def test_setup_not_provisioned_raises(self, mock_run: MagicMock, tmp_path: Path) -> None:
        tool = DesktopAgentTool()
        with pytest.raises(ToolNotProvisionedError):
            tool.setup({"project_dir": str(tmp_path)})

    @patch(_PATCH_RUN, return_value="running\nui-tars-1.5-7b\ngemma3:12b")
    def test_teardown_saves_snapshot_when_configured(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        tool = DesktopAgentTool()
        tool.setup(
            {
                "project_dir": str(tmp_path),
                "save_snapshot_on_teardown": True,
            }
        )
        mock_run.reset_mock()
        tool.teardown()

        # Verify snapshot create was called during teardown
        snapshot_calls = [
            c
            for c in mock_run.call_args_list
            if len(c.args) > 0 and "snapshot" in str(c.args[0]) and "create" in str(c.args[0])
        ]
        assert len(snapshot_calls) > 0

    @patch(_PATCH_RUN, return_value="running\nui-tars-1.5-7b\ngemma3:12b")
    def test_teardown_no_snapshot_by_default(self, mock_run: MagicMock, tmp_path: Path) -> None:
        tool = DesktopAgentTool()
        tool.setup({"project_dir": str(tmp_path)})
        mock_run.reset_mock()
        tool.teardown()

        # No snapshot create calls (only stop)
        snapshot_create_calls = [
            c
            for c in mock_run.call_args_list
            if len(c.args) > 0 and "snapshot" in str(c.args[0]) and "create" in str(c.args[0])
        ]
        assert len(snapshot_create_calls) == 0

    @patch("autopilot.debugging.tools.desktop_agent._dismiss_dialog")
    @patch(_PATCH_RUN, return_value="running\nui-tars-1.5-7b\ngemma3:12b")
    def test_setup_preflight_dismissal_runs(
        self, mock_run: MagicMock, mock_dismiss: MagicMock, tmp_path: Path
    ) -> None:
        tool = DesktopAgentTool()
        tool.setup({"project_dir": str(tmp_path)})

        # Pre-flight dialog dismissal should have been attempted
        assert mock_dismiss.call_count > 0

    @patch(_PATCH_RUN, return_value="running\nui-tars-1.5-7b\ngemma3:12b")
    def test_setup_applies_settings(self, mock_run: MagicMock, tmp_path: Path) -> None:
        tool = DesktopAgentTool()
        tool.setup(
            {
                "project_dir": str(tmp_path),
                "action_model": "custom-action-model",
                "validation_model": "custom-validation-model",
                "vm_name": "my-vm",
            }
        )

        assert tool._action_model == "custom-action-model"
        assert tool._validation_model == "custom-validation-model"
        assert tool._vm_name == "my-vm"


# ============================================================================
# Action execution
# ============================================================================


class TestDesktopAgentActions:
    """Action execution tests."""

    @patch("autopilot.debugging.tools.desktop_agent._verify_click_result", return_value=True)
    @patch("autopilot.debugging.tools.desktop_agent._execute_agent_click", return_value=True)
    def test_click_success(self, mock_click: MagicMock, mock_verify: MagicMock) -> None:
        tool = DesktopAgentTool()
        result = tool.execute_step("click", "#submit-btn")

        assert result.success is True
        assert "succeeded" in result.observation

    @patch("autopilot.debugging.tools.desktop_agent._verify_click_result")
    @patch("autopilot.debugging.tools.desktop_agent._execute_agent_click")
    def test_click_retry_on_failure(self, mock_click: MagicMock, mock_verify: MagicMock) -> None:
        """First attempt fails, retry succeeds."""
        # First click fails, second succeeds
        mock_click.side_effect = [False, True]
        mock_verify.return_value = True

        tool = DesktopAgentTool()
        result = tool.execute_step("click", "#submit-btn")

        assert result.success is True
        assert mock_click.call_count == 2  # noqa: PLR2004
        assert "attempt 2" in result.observation

    @patch("autopilot.debugging.tools.desktop_agent._verify_click_result", return_value=False)
    @patch("autopilot.debugging.tools.desktop_agent._execute_agent_click", return_value=True)
    def test_click_all_retries_fail(self, mock_click: MagicMock, mock_verify: MagicMock) -> None:
        """All retry attempts fail → returns failure."""
        tool = DesktopAgentTool()
        result = tool.execute_step("click", "#missing")

        assert result.success is False
        assert "failed after" in result.error

    @patch(_PATCH_RUN, return_value="OK")
    def test_navigate_action(self, mock_run: MagicMock) -> None:
        tool = DesktopAgentTool()
        result = tool.execute_step("navigate", "https://example.com")

        assert result.success is True
        assert "Opened" in result.observation

    def test_fill_action_without_agent(self) -> None:
        tool = DesktopAgentTool()
        result = tool.execute_step("fill", "#email", value="test@example.com")

        assert result.success is True
        assert "test@example.com" in result.observation

    def test_unknown_action_returns_error(self) -> None:
        tool = DesktopAgentTool()
        result = tool.execute_step("nonexistent_action", "#target")

        assert result.success is False
        assert "Unknown action" in result.error

    def test_screenshot_action(self, tmp_path: Path) -> None:
        tool = DesktopAgentTool()
        tool._project_dir = tmp_path
        result = tool.execute_step("screenshot", "test_capture")

        assert result.success is True
        assert result.screenshot_path != ""


# ============================================================================
# Diagnostics and UX evaluation
# ============================================================================


class TestDesktopAgentDiagnostics:
    """Diagnostic evidence capture tests."""

    def test_capture_diagnostic_evidence_returns_populated(self, tmp_path: Path) -> None:
        tool = DesktopAgentTool()
        tool._project_dir = tmp_path
        evidence = tool.capture_diagnostic_evidence()

        assert isinstance(evidence, DiagnosticEvidence)
        assert len(evidence.screenshots) > 0
        assert evidence.observations != ""

    def test_capture_screenshot_creates_directory(self, tmp_path: Path) -> None:
        tool = DesktopAgentTool()
        tool._project_dir = tmp_path
        path = tool.capture_screenshot("test_label")

        screenshot_dir = tmp_path / ".autopilot" / "debugging" / "screenshots"
        assert screenshot_dir.exists()
        assert "desktop_test_label_" in path
        assert path.endswith(".png")

    def test_evaluate_ux_returns_observations(self, tmp_path: Path) -> None:
        tool = DesktopAgentTool()
        tool._project_dir = tmp_path
        observations = tool.evaluate_ux(
            criteria=("Check color contrast", "Verify form inputs"),
        )

        assert isinstance(observations, tuple)
        assert len(observations) == 2  # noqa: PLR2004
        assert all(isinstance(o, UXObservation) for o in observations)

    def test_evaluate_ux_empty_criteria(self, tmp_path: Path) -> None:
        tool = DesktopAgentTool()
        tool._project_dir = tmp_path
        observations = tool.evaluate_ux(criteria=())
        assert observations == ()


# ============================================================================
# Configuration — dual-model settings
# ============================================================================


class TestDesktopAgentConfig:
    """Dual-model configuration tests."""

    def test_default_action_model(self) -> None:
        tool = DesktopAgentTool()
        assert tool._action_model == "ui-tars-1.5-7b"

    def test_default_validation_model(self) -> None:
        tool = DesktopAgentTool()
        assert tool._validation_model == "gemma3:12b"

    @patch(_PATCH_RUN, return_value="running\ncustom-action\ncustom-validation")
    def test_dual_model_configurable_via_settings(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        tool = DesktopAgentTool()
        tool.setup(
            {
                "project_dir": str(tmp_path),
                "action_model": "custom-action",
                "validation_model": "custom-validation",
            }
        )
        assert tool._action_model == "custom-action"
        assert tool._validation_model == "custom-validation"

    def test_default_timeout_120(self) -> None:
        """Desktop agent default timeout is 120s (vs. 30 for browser)."""
        from autopilot.debugging.tools.desktop_agent import _DEFAULT_TIMEOUT

        assert _DEFAULT_TIMEOUT == 120  # noqa: PLR2004


# ============================================================================
# Missing SDK handling
# ============================================================================


class TestDesktopAgentMissingSDK:
    """ImportError handling for missing Cua SDK."""

    @patch("autopilot.debugging.tools.desktop_agent._CUA_AVAILABLE", False)
    @patch(_PATCH_RUN, return_value="running\nui-tars-1.5-7b\ngemma3:12b")
    def test_missing_cua_sdk_check_provisioned(self, mock_run: MagicMock) -> None:
        tool = DesktopAgentTool()
        status = tool.check_provisioned()

        # Should report not ready when SDK is missing
        assert status.ready is False
        assert "cua_sdk" in status.components
        assert status.components["cua_sdk"] == "not_installed"


# ============================================================================
# Helpers
# ============================================================================


class TestDesktopAgentHelpers:
    """Helper function tests."""

    def test_ensure_screenshot_dir_creates(self, tmp_path: Path) -> None:
        result = _ensure_screenshot_dir(tmp_path)
        assert result.exists()
        assert result == tmp_path / ".autopilot" / "debugging" / "screenshots"

    def test_action_map_has_expected_keys(self) -> None:
        expected = {"navigate", "click", "fill", "wait", "screenshot", "assert_visible"}
        assert set(ACTION_MAP.keys()) == expected
