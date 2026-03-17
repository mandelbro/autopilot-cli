"""Tests for BrowserMCPTool plugin.

Task 010a: Core (protocol, actions, provisioning)
Task 010b: Diagnostics and UX evaluation
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from autopilot.debugging.models import ToolNotProvisionedError
from autopilot.debugging.tools._helpers import (
    classify_ux_criterion as _classify_ux_criterion,
)
from autopilot.debugging.tools._helpers import (
    ensure_screenshot_dir as _ensure_screenshot_dir,
)
from autopilot.debugging.tools.browser_mcp import (
    ACTION_MAP,
    BrowserMCPTool,
    _build_console_capture_js,
    _build_network_capture_js,
)
from autopilot.debugging.tools.protocol import (
    DebuggingTool,
    DiagnosticEvidence,
    ToolCapability,
    UXObservation,
)

if TYPE_CHECKING:
    from pathlib import Path


# ============================================================================
# Task 010a: Core — protocol, actions, provisioning
# ============================================================================


class TestBrowserMCPProtocol:
    """Protocol compliance tests."""

    def test_isinstance_debugging_tool(self) -> None:
        tool = BrowserMCPTool()
        assert isinstance(tool, DebuggingTool)

    def test_name_is_browser_mcp(self) -> None:
        assert BrowserMCPTool().name == "browser_mcp"

    def test_protocol_version(self) -> None:
        assert BrowserMCPTool.protocol_version == 1

    def test_all_five_capabilities(self) -> None:
        caps = BrowserMCPTool().capabilities
        assert caps == frozenset(ToolCapability)
        assert len(caps) == 5


class TestBrowserMCPActionMapping:
    """Action mapping tests."""

    def test_navigate_maps_correctly(self) -> None:
        assert ACTION_MAP["navigate"] == "browser_navigate"

    def test_click_maps_correctly(self) -> None:
        assert ACTION_MAP["click"] == "browser_click"

    def test_fill_maps_correctly(self) -> None:
        assert ACTION_MAP["fill"] == "browser_type"

    def test_wait_maps_correctly(self) -> None:
        assert ACTION_MAP["wait_for_navigation"] == "browser_wait"

    def test_assert_text_maps_to_snapshot(self) -> None:
        assert ACTION_MAP["assert_text"] == "browser_snapshot"

    def test_assert_visible_maps_to_snapshot(self) -> None:
        assert ACTION_MAP["assert_visible"] == "browser_snapshot"

    def test_screenshot_maps_correctly(self) -> None:
        assert ACTION_MAP["screenshot"] == "browser_screenshot"

    def test_unknown_action_returns_error(self) -> None:
        tool = BrowserMCPTool()
        result = tool.execute_step("nonexistent_action", "#target")
        assert result.success is False
        assert "Unknown action" in result.error

    def test_execute_navigate_succeeds(self) -> None:
        tool = BrowserMCPTool()
        result = tool.execute_step("navigate", "http://example.com")
        assert result.success is True
        assert "browser_navigate" in result.observation

    def test_execute_fill_succeeds(self) -> None:
        tool = BrowserMCPTool()
        result = tool.execute_step("fill", "#email", value="test@example.com")
        assert result.success is True
        assert "browser_type" in result.observation


class TestBrowserMCPProvisioning:
    """Provisioning and setup tests."""

    def test_provision_creates_mcp_config(self, tmp_path: Path) -> None:
        tool = BrowserMCPTool()
        result = tool.provision({"project_dir": str(tmp_path)})
        assert result.success is True
        assert "browsermcp" in result.components_installed

        config_file = tmp_path / ".mcp.json"
        assert config_file.exists()
        config = json.loads(config_file.read_text())
        assert "browsermcp" in config["mcpServers"]

    def test_provision_existing_config_adds_server(self, tmp_path: Path) -> None:
        config_file = tmp_path / ".mcp.json"
        config_file.write_text(json.dumps({"mcpServers": {"other": {}}}))

        tool = BrowserMCPTool()
        result = tool.provision({"project_dir": str(tmp_path)})
        assert result.success is True

        config = json.loads(config_file.read_text())
        assert "browsermcp" in config["mcpServers"]
        assert "other" in config["mcpServers"]

    def test_provision_already_registered_skips(self, tmp_path: Path) -> None:
        config_file = tmp_path / ".mcp.json"
        config_file.write_text(json.dumps({"mcpServers": {"browsermcp": {"command": "npx"}}}))

        tool = BrowserMCPTool()
        result = tool.provision({"project_dir": str(tmp_path)})
        assert result.success is True

    def test_check_provisioned_no_config(self, tmp_path: Path) -> None:
        tool = BrowserMCPTool()
        tool._project_dir = tmp_path
        status = tool.check_provisioned()
        assert status.provisioned is False
        assert "No .mcp.json" in status.message

    def test_check_provisioned_no_server(self, tmp_path: Path) -> None:
        config_file = tmp_path / ".mcp.json"
        config_file.write_text(json.dumps({"mcpServers": {}}))

        tool = BrowserMCPTool()
        tool._project_dir = tmp_path
        status = tool.check_provisioned()
        assert status.provisioned is False
        assert "not registered" in status.message

    def test_check_provisioned_healthy(self, tmp_path: Path) -> None:
        config_file = tmp_path / ".mcp.json"
        config_file.write_text(json.dumps({"mcpServers": {"browsermcp": {"command": "npx"}}}))

        tool = BrowserMCPTool()
        tool._project_dir = tmp_path
        status = tool.check_provisioned()
        assert status.provisioned is True
        assert status.ready is True

    def test_setup_raises_when_not_provisioned(self, tmp_path: Path) -> None:
        tool = BrowserMCPTool()
        with pytest.raises(ToolNotProvisionedError):
            tool.setup({"project_dir": str(tmp_path)})

    def test_setup_succeeds_when_provisioned(self, tmp_path: Path) -> None:
        config_file = tmp_path / ".mcp.json"
        config_file.write_text(json.dumps({"mcpServers": {"browsermcp": {"command": "npx"}}}))

        tool = BrowserMCPTool()
        tool.setup({"project_dir": str(tmp_path)})
        assert tool._provisioned is True

    def test_teardown_clears_settings(self) -> None:
        tool = BrowserMCPTool()
        tool._settings = {"key": "value"}
        tool.teardown()
        assert tool._settings == {}

    def test_deprovision_clears_state(self) -> None:
        tool = BrowserMCPTool()
        tool._provisioned = True
        tool._settings = {"key": "value"}
        tool.deprovision()
        assert tool._provisioned is False
        assert tool._settings == {}


# ============================================================================
# Task 010b: Diagnostics and UX evaluation
# ============================================================================


class TestBrowserMCPDiagnostics:
    """Diagnostic evidence capture tests."""

    def test_capture_diagnostic_evidence_returns_populated(self, tmp_path: Path) -> None:
        tool = BrowserMCPTool()
        tool._project_dir = tmp_path
        evidence = tool.capture_diagnostic_evidence()

        assert isinstance(evidence, DiagnosticEvidence)
        assert len(evidence.screenshots) > 0
        assert len(evidence.console_errors) > 0
        assert len(evidence.network_failures) > 0
        assert evidence.observations != ""

    def test_capture_screenshot_creates_directory(self, tmp_path: Path) -> None:
        tool = BrowserMCPTool()
        tool._project_dir = tmp_path
        path = tool.capture_screenshot("test_label")

        screenshot_dir = tmp_path / ".autopilot" / "debugging" / "screenshots"
        assert screenshot_dir.exists()
        assert "debug_test_label_" in path
        assert path.endswith(".png")

    def test_capture_screenshot_filename_format(self, tmp_path: Path) -> None:
        tool = BrowserMCPTool()
        tool._project_dir = tmp_path
        path = tool.capture_screenshot("my_label")

        # Format: debug_{label}_{timestamp}.png
        filename = path.split("/")[-1]
        assert filename.startswith("debug_my_label_")
        assert filename.endswith(".png")
        # Timestamp part should be 15 chars: YYYYMMDD_HHMMSS
        timestamp_part = filename[len("debug_my_label_") : -len(".png")]
        assert len(timestamp_part) == 15  # noqa: PLR2004


class TestBrowserMCPUXEvaluation:
    """UX evaluation tests."""

    def test_evaluate_ux_returns_observations(self, tmp_path: Path) -> None:
        tool = BrowserMCPTool()
        tool._project_dir = tmp_path
        observations = tool.evaluate_ux(
            criteria=("Check color contrast", "Verify form inputs"),
        )

        assert isinstance(observations, tuple)
        assert len(observations) == 2  # noqa: PLR2004
        assert all(isinstance(o, UXObservation) for o in observations)

    def test_evaluate_ux_categories(self, tmp_path: Path) -> None:
        tool = BrowserMCPTool()
        tool._project_dir = tmp_path
        observations = tool.evaluate_ux(
            criteria=("Check color contrast",),
        )

        assert observations[0].category == "visual_design"

    def test_evaluate_ux_severity(self, tmp_path: Path) -> None:
        tool = BrowserMCPTool()
        tool._project_dir = tmp_path
        observations = tool.evaluate_ux(criteria=("Something general",))

        assert observations[0].severity == "info"

    def test_evaluate_ux_screenshot_attached(self, tmp_path: Path) -> None:
        tool = BrowserMCPTool()
        tool._project_dir = tmp_path
        observations = tool.evaluate_ux(criteria=("Check nav links",))

        assert observations[0].screenshot_path != ""
        assert "ux_review" in observations[0].screenshot_path

    def test_evaluate_ux_empty_criteria(self, tmp_path: Path) -> None:
        tool = BrowserMCPTool()
        tool._project_dir = tmp_path
        observations = tool.evaluate_ux(criteria=())
        assert observations == ()


class TestBrowserMCPJSHelpers:
    """JavaScript helper tests."""

    def test_console_capture_js_returns_valid_js(self) -> None:
        js = _build_console_capture_js()
        assert isinstance(js, str)
        assert "console.error" in js
        assert "errors" in js

    def test_network_capture_js_returns_valid_js(self) -> None:
        js = _build_network_capture_js()
        assert isinstance(js, str)
        assert "fetch" in js
        assert "failures" in js


class TestBrowserMCPHelpers:
    """Helper function tests."""

    def test_ensure_screenshot_dir_creates(self, tmp_path: Path) -> None:
        result = _ensure_screenshot_dir(tmp_path)
        assert result.exists()
        assert result == tmp_path / ".autopilot" / "debugging" / "screenshots"

    def test_classify_ux_criterion_visual(self) -> None:
        assert _classify_ux_criterion("Check color contrast") == "visual_design"

    def test_classify_ux_criterion_navigation(self) -> None:
        assert _classify_ux_criterion("Verify nav links") == "navigation"

    def test_classify_ux_criterion_interaction(self) -> None:
        assert _classify_ux_criterion("Test form submission") == "interaction"

    def test_classify_ux_criterion_feedback(self) -> None:
        assert _classify_ux_criterion("Check error messages") == "feedback"

    def test_classify_ux_criterion_accessibility(self) -> None:
        assert _classify_ux_criterion("Verify aria labels") == "accessibility"

    def test_classify_ux_criterion_general(self) -> None:
        assert _classify_ux_criterion("Something else") == "general"
