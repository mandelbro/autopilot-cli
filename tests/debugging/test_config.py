"""Tests for debugging configuration models (Task 004).

Validates DebuggingConfig and DebuggingToolConfig defaults, alias handling,
AutopilotConfig integration, and YAML round-trip behaviour.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path
import yaml
from pydantic import ValidationError

from autopilot.core.config import (
    AutopilotConfig,
    DebuggingConfig,
    DebuggingToolConfig,
    ProjectConfig,
)


class TestDebuggingToolConfig:
    def test_defaults(self) -> None:
        cfg = DebuggingToolConfig()
        assert cfg.module == ""
        assert cfg.class_name == ""
        assert cfg.settings == {}

    def test_alias_class(self) -> None:
        cfg = DebuggingToolConfig.model_validate(
            {"class": "BrowserMCP", "module": "autopilot.debugging.tools.browser_mcp"}
        )
        assert cfg.class_name == "BrowserMCP"
        assert cfg.module == "autopilot.debugging.tools.browser_mcp"

    def test_populate_by_name(self) -> None:
        cfg = DebuggingToolConfig(class_name="DesktopAgent", module="tools.desktop")
        assert cfg.class_name == "DesktopAgent"

    def test_frozen(self) -> None:
        cfg = DebuggingToolConfig()
        with pytest.raises(ValidationError):
            cfg.module = "changed"  # type: ignore[misc]

    def test_settings_dict(self) -> None:
        cfg = DebuggingToolConfig(settings={"headless": True, "port": 9222})
        assert cfg.settings["headless"] is True


class TestDebuggingConfig:
    def test_defaults(self) -> None:
        cfg = DebuggingConfig()
        assert cfg.enabled is False
        assert cfg.tool == "browser_mcp"
        assert cfg.tools == {}
        assert cfg.max_fix_iterations == 3
        assert cfg.timeout_seconds == 1800
        assert cfg.regression_test_framework == "pytest"
        assert cfg.ux_review_enabled is True

    def test_frozen(self) -> None:
        cfg = DebuggingConfig()
        with pytest.raises(ValidationError):
            cfg.enabled = True  # type: ignore[misc]

    def test_rejects_zero_max_fix_iterations(self) -> None:
        with pytest.raises(ValidationError, match="max_fix_iterations"):
            DebuggingConfig(max_fix_iterations=0)

    def test_rejects_six_max_fix_iterations(self) -> None:
        with pytest.raises(ValidationError, match="max_fix_iterations"):
            DebuggingConfig(max_fix_iterations=6)

    def test_accepts_boundary_max_fix_iterations(self) -> None:
        cfg_low = DebuggingConfig(max_fix_iterations=1)
        cfg_high = DebuggingConfig(max_fix_iterations=5)
        assert cfg_low.max_fix_iterations == 1
        assert cfg_high.max_fix_iterations == 5

    def test_rejects_zero_timeout(self) -> None:
        with pytest.raises(ValidationError, match="timeout_seconds"):
            DebuggingConfig(timeout_seconds=0)

    def test_with_tool_entries(self) -> None:
        cfg = DebuggingConfig(
            tools={
                "browser_mcp": DebuggingToolConfig(
                    module="autopilot.debugging.tools.browser_mcp",
                    class_name="BrowserMCPTool",
                ),
            }
        )
        assert "browser_mcp" in cfg.tools
        assert cfg.tools["browser_mcp"].class_name == "BrowserMCPTool"


class TestDebuggingConfigInAutopilotConfig:
    def test_autopilot_config_includes_debugging(self) -> None:
        cfg = AutopilotConfig(project=ProjectConfig(name="test"))
        assert isinstance(cfg.debugging, DebuggingConfig)
        assert cfg.debugging.enabled is False

    def test_yaml_without_debugging_section(self, tmp_path: Path) -> None:
        yaml_path = tmp_path / "config.yaml"
        yaml_path.write_text("project:\n  name: no-debugging\n")
        loaded = AutopilotConfig.from_yaml(yaml_path)
        assert loaded.debugging.enabled is False
        assert loaded.debugging.tool == "browser_mcp"

    def test_yaml_round_trip(self, tmp_path: Path) -> None:
        original = AutopilotConfig(
            project=ProjectConfig(name="debug-test"),
            debugging=DebuggingConfig(
                enabled=True,
                tool="desktop_agent",
                max_fix_iterations=5,
                tools={
                    "desktop_agent": DebuggingToolConfig(
                        module="autopilot.debugging.tools.desktop_agent",
                        class_name="DesktopAgentTool",
                        settings={"vm_name": "autopilot-uat"},
                    ),
                },
            ),
        )
        yaml_path = tmp_path / "config.yaml"
        original.to_yaml(yaml_path)
        loaded = AutopilotConfig.from_yaml(yaml_path)

        assert loaded.debugging.enabled is True
        assert loaded.debugging.tool == "desktop_agent"
        assert loaded.debugging.max_fix_iterations == 5
        assert "desktop_agent" in loaded.debugging.tools
        assert loaded.debugging.tools["desktop_agent"].class_name == "DesktopAgentTool"

    def test_yaml_serializes_class_alias(self, tmp_path: Path) -> None:
        """Verify that to_yaml uses by_alias so 'class_name' writes as 'class'."""
        original = AutopilotConfig(
            project=ProjectConfig(name="alias-test"),
            debugging=DebuggingConfig(
                tools={
                    "browser_mcp": DebuggingToolConfig(
                        module="tools.browser", class_name="BrowserMCP"
                    ),
                }
            ),
        )
        yaml_path = tmp_path / "config.yaml"
        original.to_yaml(yaml_path)

        with open(yaml_path) as f:
            raw = yaml.safe_load(f)

        tool_data = raw["debugging"]["tools"]["browser_mcp"]
        assert "class" in tool_data
        assert tool_data["class"] == "BrowserMCP"
        assert "class_name" not in tool_data
