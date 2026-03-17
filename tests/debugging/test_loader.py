"""Tests for debugging plugin loader."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import structlog.testing

from autopilot.core.config import DebuggingConfig, DebuggingToolConfig
from autopilot.debugging.loader import load_debugging_tool, validate_plugin_class
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


class _MockDebuggingTool:
    """A mock class satisfying the DebuggingTool protocol."""

    protocol_version: int = PROTOCOL_VERSION

    @property
    def name(self) -> str:
        return "mock-tool"

    @property
    def capabilities(self) -> frozenset[ToolCapability]:
        return frozenset(ToolCapability)

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


class _InvalidClass:
    """A class that does NOT satisfy the DebuggingTool protocol."""

    pass


class _WrongVersionTool(_MockDebuggingTool):
    """Mock tool with a mismatched protocol version."""

    protocol_version: int = 999


class _ProtocolVersionBlocker:
    """Descriptor that makes ``hasattr(cls, 'protocol_version')`` False."""

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name

    def __get__(self, obj: Any, objtype: type | None = None) -> int:
        raise AttributeError(self._name)


class _NoVersionTool(_MockDebuggingTool):
    """Mock tool satisfying the protocol but missing protocol_version.

    Inherits all methods from _MockDebuggingTool to avoid duplication.
    Uses a descriptor to block the inherited ``protocol_version``.
    """

    protocol_version = _ProtocolVersionBlocker()  # type: ignore[assignment]

    @property
    def name(self) -> str:
        return "no-version-tool"


def _make_config(
    tool_name: str = "browser_mcp",
    module: str = "autopilot.debugging.tools.browser_mcp",
    class_name: str = "BrowserMCPTool",
) -> DebuggingConfig:
    """Build a DebuggingConfig with a single tool entry."""
    return DebuggingConfig(
        enabled=True,
        tool=tool_name,
        tools={
            tool_name: DebuggingToolConfig(
                module=module,
                class_name=class_name,
            ),
        },
    )


# -- load_debugging_tool --


class TestLoadDebuggingTool:
    """Tests for load_debugging_tool."""

    def test_loads_valid_tool(self) -> None:
        mock_module = MagicMock()
        mock_module.BrowserMCPTool = _MockDebuggingTool

        config = _make_config()

        with patch("autopilot.debugging.loader.importlib.import_module", return_value=mock_module):
            tool = load_debugging_tool(config)

        assert isinstance(tool, DebuggingTool)
        assert tool.name == "mock-tool"

    def test_raises_on_unknown_tool_name(self) -> None:
        config = DebuggingConfig(
            enabled=True,
            tool="nonexistent",
            tools={},
        )

        with pytest.raises(ValueError, match="Unknown debugging tool 'nonexistent'"):
            load_debugging_tool(config)

    def test_raises_on_import_error(self) -> None:
        config = _make_config(module="no.such.module")

        with (
            patch(
                "autopilot.debugging.loader.importlib.import_module",
                side_effect=ModuleNotFoundError("No module named 'no.such.module'"),
            ),
            pytest.raises(ImportError, match="Could not import module"),
        ):
            load_debugging_tool(config)

    def test_raises_on_missing_class(self) -> None:
        mock_module = MagicMock(spec=[])  # Empty module — no attributes

        config = _make_config()

        with (
            patch("autopilot.debugging.loader.importlib.import_module", return_value=mock_module),
            pytest.raises(ImportError, match="Class 'BrowserMCPTool' not found"),
        ):
            load_debugging_tool(config)

    def test_raises_on_invalid_class(self) -> None:
        mock_module = MagicMock()
        mock_module.BrowserMCPTool = _InvalidClass

        config = _make_config()

        with (
            patch("autopilot.debugging.loader.importlib.import_module", return_value=mock_module),
            pytest.raises(TypeError, match="does not satisfy"),
        ):
            load_debugging_tool(config)

    def test_version_mismatch_logs_warning(self) -> None:
        mock_module = MagicMock()
        mock_module.BrowserMCPTool = _WrongVersionTool

        config = _make_config()

        with (
            structlog.testing.capture_logs() as captured,
            patch("autopilot.debugging.loader.importlib.import_module", return_value=mock_module),
        ):
            tool = load_debugging_tool(config)

        assert tool is not None
        events = [e["event"] for e in captured]
        assert "protocol_version_mismatch" in events

    def test_missing_version_logs_warning(self) -> None:
        mock_module = MagicMock()
        mock_module.BrowserMCPTool = _NoVersionTool

        config = _make_config()

        with (
            structlog.testing.capture_logs() as captured,
            patch("autopilot.debugging.loader.importlib.import_module", return_value=mock_module),
        ):
            tool = load_debugging_tool(config)

        assert tool is not None
        events = [e["event"] for e in captured]
        assert "missing_protocol_version" in events


# -- validate_plugin_class --


class TestValidatePluginClass:
    """Tests for validate_plugin_class."""

    def test_valid_class(self) -> None:
        valid, msg = validate_plugin_class(_MockDebuggingTool)
        assert valid is True
        assert msg == "Valid"

    def test_invalid_class_missing_methods(self) -> None:
        valid, msg = validate_plugin_class(_InvalidClass)
        assert valid is False
        assert "Missing required attributes" in msg

    def test_missing_protocol_version(self) -> None:
        valid, msg = validate_plugin_class(_NoVersionTool)
        assert valid is False
        assert "Missing 'protocol_version'" in msg

    def test_wrong_protocol_version(self) -> None:
        valid, msg = validate_plugin_class(_WrongVersionTool)
        assert valid is False
        assert "Protocol version mismatch" in msg
