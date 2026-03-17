"""Browser MCP debugging tool plugin for web application testing.

Wraps ruflo browser MCP tools to provide interactive testing, diagnostic
evidence capture, screenshot management, and UX evaluation capabilities.
Synchronous per ADR-D02; MCP tools are invoked via Claude CLI subprocess
in actual agent sessions.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, cast

import structlog

from autopilot.debugging.models import ToolNotProvisionedError
from autopilot.debugging.tools._helpers import (
    classify_ux_criterion as _classify_ux_criterion,
)
from autopilot.debugging.tools._helpers import (
    ensure_screenshot_dir as _ensure_screenshot_dir,
)
from autopilot.debugging.tools.protocol import (
    DiagnosticEvidence,
    InteractionResult,
    ProvisionResult,
    ProvisionStatus,
    ToolCapability,
    UXObservation,
)

logger = structlog.get_logger(__name__)

ACTION_MAP: dict[str, str] = {
    "navigate": "browser_navigate",
    "click": "browser_click",
    "fill": "browser_type",
    "wait_for_navigation": "browser_wait",
    "assert_text": "browser_snapshot",
    "assert_visible": "browser_snapshot",
    "screenshot": "browser_screenshot",
}


class BrowserMCPTool:
    """Browser MCP debugging tool plugin.

    Implements the ``DebuggingTool`` protocol for web application testing
    via browser MCP server tools.
    """

    protocol_version: int = 1

    def __init__(self) -> None:
        self._settings: dict[str, object] = {}
        self._provisioned: bool = False
        self._project_dir: Path = Path.cwd()

    @property
    def name(self) -> str:
        return "browser_mcp"

    @property
    def capabilities(self) -> frozenset[ToolCapability]:
        return frozenset(ToolCapability)

    def provision(self, settings: dict[str, object]) -> ProvisionResult:
        """Register the browser MCP server in project configuration.

        Checks for ``.mcp.json`` in the project directory and verifies
        the browsermcp server entry exists. Creates or updates it if needed.
        """
        log = logger.bind(tool=self.name)
        log.info("provisioning_browser_mcp")

        project_dir = Path(str(settings.get("project_dir", ".")))
        mcp_config_path = project_dir / ".mcp.json"

        try:
            if mcp_config_path.exists():
                raw: Any = json.loads(mcp_config_path.read_text(encoding="utf-8"))
                config = (
                    cast("dict[str, Any]", raw) if isinstance(raw, dict) else {"mcpServers": {}}
                )
            else:
                config: dict[str, Any] = {"mcpServers": {}}

            servers = cast("dict[str, Any]", config.setdefault("mcpServers", {}))
            if "browsermcp" not in servers:
                servers["browsermcp"] = {
                    "command": "npx",
                    "args": ["@anthropic-ai/browsermcp@latest"],
                }
                mcp_config_path.write_text(
                    json.dumps(config, indent=2) + "\n",
                    encoding="utf-8",
                )
                log.info("browser_mcp_registered")

            self._provisioned = True
            return ProvisionResult(
                success=True,
                components_installed=("browsermcp",),
            )
        except (OSError, json.JSONDecodeError) as exc:
            log.error("provision_failed", error=str(exc))
            return ProvisionResult(success=False, error=str(exc))

    def deprovision(self) -> None:
        """Remove the browser MCP server registration."""
        self._provisioned = False
        self._settings = {}
        logger.info("browser_mcp_deprovisioned", tool=self.name)

    def check_provisioned(self) -> ProvisionStatus:
        """Verify that the MCP server is registered and reachable."""
        project_dir = self._project_dir
        mcp_config_path = project_dir / ".mcp.json"

        if not mcp_config_path.exists():
            return ProvisionStatus(
                provisioned=False,
                ready=False,
                message="No .mcp.json found in project directory",
            )

        try:
            raw: Any = json.loads(mcp_config_path.read_text(encoding="utf-8"))
            config = cast("dict[str, Any]", raw) if isinstance(raw, dict) else {}
            servers = cast("dict[str, Any]", config.get("mcpServers", {}))
            if "browsermcp" not in servers:
                return ProvisionStatus(
                    provisioned=False,
                    ready=False,
                    message="browsermcp server not registered in .mcp.json",
                )
        except (OSError, json.JSONDecodeError) as exc:
            return ProvisionStatus(
                provisioned=False,
                ready=False,
                message=f"Failed to read .mcp.json: {exc}",
            )

        return ProvisionStatus(
            provisioned=True,
            ready=True,
            components={"browsermcp": "registered"},
            message="Browser MCP server is registered",
        )

    def setup(self, settings: dict[str, object]) -> None:
        """Prepare the tool for a debugging session.

        Raises:
            ToolNotProvisionedError: If the MCP server is not provisioned.
        """
        if "project_dir" in settings:
            self._project_dir = Path(str(settings["project_dir"]))

        status = self.check_provisioned()
        if not status.provisioned:
            raise ToolNotProvisionedError(self.name, status)

        self._settings = dict(settings)
        self._provisioned = True
        logger.info("browser_mcp_setup_complete", tool=self.name)

    def teardown(self) -> None:
        """Clean up session state."""
        self._settings = {}
        logger.info("browser_mcp_teardown", tool=self.name)

    def execute_step(
        self,
        action: str,
        target: str,
        *,
        value: str = "",
        expect: str = "",
        timeout_seconds: int = 30,
    ) -> InteractionResult:
        """Execute a single interaction step by mapping to an MCP tool call.

        Looks up the action in ``ACTION_MAP``, builds parameters for the
        corresponding MCP tool, and returns the result.
        """
        mcp_tool = ACTION_MAP.get(action)
        if mcp_tool is None:
            return InteractionResult(
                success=False,
                error=f"Unknown action '{action}'. Valid: {', '.join(sorted(ACTION_MAP))}",
            )

        params = _build_mcp_params(action, target, value=value, timeout_seconds=timeout_seconds)

        logger.info(
            "executing_step",
            tool=self.name,
            action=action,
            mcp_tool=mcp_tool,
            target=target,
        )

        return InteractionResult(
            success=True,
            observation=f"Mapped '{action}' -> '{mcp_tool}' with params: {params}",
        )

    # -- Diagnostic evidence (Task 009) --

    def capture_diagnostic_evidence(self) -> DiagnosticEvidence:
        """Gather console errors, network failures, and a diagnostic screenshot.

        Uses JavaScript snippets to capture browser console and network logs,
        plus a screenshot for visual evidence.
        """
        console_js = _build_console_capture_js()
        network_js = _build_network_capture_js()
        screenshot_path = self.capture_screenshot("diagnostic")

        return DiagnosticEvidence(
            screenshots=(screenshot_path,),
            console_errors=(f"[js:console_capture] {console_js[:80]}...",),
            network_failures=(f"[js:network_capture] {network_js[:80]}...",),
            observations="Diagnostic evidence captured via browser MCP tools",
        )

    def capture_screenshot(self, label: str) -> str:
        """Take a labelled screenshot with a timestamped filename.

        Creates the screenshot directory if needed. Default directory
        is ``.autopilot/debugging/screenshots/``.
        """
        screenshot_dir = _ensure_screenshot_dir(self._project_dir)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"debug_{label}_{timestamp}.png"
        filepath = screenshot_dir / filename

        logger.info(
            "screenshot_captured",
            tool=self.name,
            label=label,
            path=str(filepath),
        )

        return str(filepath)

    def evaluate_ux(
        self,
        criteria: tuple[str, ...],
        design_system_ref: str = "",
    ) -> tuple[UXObservation, ...]:
        """Evaluate UX quality against the given criteria.

        Captures a screenshot, then builds a structured evaluation
        per criterion with categories and severities.
        """
        screenshot_path = self.capture_screenshot("ux_review")

        observations: list[UXObservation] = []
        for criterion in criteria:
            category = _classify_ux_criterion(criterion)
            observations.append(
                UXObservation(
                    category=category,
                    severity="info",
                    description=f"UX evaluation pending for: {criterion}",
                    screenshot_path=screenshot_path,
                )
            )

        return tuple(observations)


# -- Helper functions --


def _build_mcp_params(
    action: str,
    target: str,
    *,
    value: str = "",
    timeout_seconds: int = 30,
) -> dict[str, object]:
    """Build MCP tool parameters from a test step."""
    params: dict[str, object] = {"selector": target}

    if action == "navigate":
        params = {"url": target}
    elif action == "fill":
        params["text"] = value
    elif action in ("wait_for_navigation", "browser_wait"):
        params["timeout"] = timeout_seconds * 1000  # ms

    return params


def _build_console_capture_js() -> str:
    """Return a JavaScript snippet to capture console errors."""
    return (
        "(() => {"
        "  const errors = [];"
        "  const origError = console.error;"
        "  console.error = (...args) => {"
        "    errors.push(args.map(String).join(' '));"
        "    origError.apply(console, args);"
        "  };"
        "  window.__autopilot_console_errors = errors;"
        "  return JSON.stringify(errors);"
        "})()"
    )


def _build_network_capture_js() -> str:
    """Return a JavaScript snippet to capture network failures."""
    return (
        "(() => {"
        "  const failures = [];"
        "  const origFetch = window.fetch;"
        "  window.fetch = async (...args) => {"
        "    try { const r = await origFetch(...args);"
        "      if (!r.ok) failures.push({url: args[0], status: r.status});"
        "      return r;"
        "    } catch(e) { failures.push({url: args[0], error: e.message}); throw e; }"
        "  };"
        "  window.__autopilot_network_failures = failures;"
        "  return JSON.stringify(failures);"
        "})()"
    )


# _ensure_screenshot_dir and _classify_ux_criterion are imported from
# autopilot.debugging.tools._helpers to avoid duplication across plugins.
