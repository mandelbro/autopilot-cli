"""Plugin loader for debugging tool backends.

Discovers and validates debugging tool plugins from config, using
``importlib.import_module`` to load the configured tool class and checking
protocol compliance and version compatibility (ADR-D01, ADR-D07).
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

import structlog

from autopilot.debugging.tools.protocol import PROTOCOL_VERSION, DebuggingTool

if TYPE_CHECKING:
    from autopilot.core.config import DebuggingConfig

logger = structlog.get_logger(__name__)

_REQUIRED_METHODS: tuple[str, ...] = (
    "provision",
    "deprovision",
    "check_provisioned",
    "setup",
    "teardown",
    "execute_step",
    "capture_diagnostic_evidence",
    "capture_screenshot",
    "evaluate_ux",
)

_REQUIRED_PROPERTIES: tuple[str, ...] = ("name", "capabilities")


def load_debugging_tool(config: DebuggingConfig) -> DebuggingTool:
    """Load and return the active debugging tool plugin from config.

    Reads the active tool name from ``config.tool``, looks it up in
    ``config.tools``, dynamically imports the module, instantiates the
    class, and validates protocol compliance.

    Args:
        config: The debugging configuration section.

    Returns:
        A validated ``DebuggingTool`` instance.

    Raises:
        ValueError: If the active tool name is not found in ``config.tools``.
        ImportError: If the configured module cannot be imported.
        TypeError: If the loaded class does not satisfy ``DebuggingTool``.
    """
    tool_name = config.tool

    if tool_name not in config.tools:
        msg = (
            f"Unknown debugging tool '{tool_name}'. "
            f"Available tools: {', '.join(sorted(config.tools.keys())) or '(none)'}"
        )
        raise ValueError(msg)

    tool_config = config.tools[tool_name]
    module_path = tool_config.module
    class_name = tool_config.class_name

    log = logger.bind(tool=tool_name, module=module_path, class_name=class_name)
    log.info("loading_debugging_tool")

    try:
        module = importlib.import_module(module_path)
    except ModuleNotFoundError as exc:
        log.error("module_not_found", error=str(exc))
        msg = f"Could not import module '{module_path}' for tool '{tool_name}': {exc}"
        raise ImportError(msg) from exc

    cls = getattr(module, class_name, None)
    if cls is None:
        msg = f"Class '{class_name}' not found in module '{module_path}' for tool '{tool_name}'"
        raise ImportError(msg)

    try:
        instance = cls()
    except Exception as exc:
        msg = f"Failed to instantiate '{class_name}' for tool '{tool_name}': {exc}"
        raise TypeError(msg) from exc

    if not isinstance(instance, DebuggingTool):
        msg = (
            f"Class '{class_name}' from '{module_path}' does not satisfy "
            f"the DebuggingTool protocol for tool '{tool_name}'"
        )
        raise TypeError(msg)

    _check_protocol_version(cls, tool_name)

    log.info("debugging_tool_loaded", name=instance.name)
    return instance


def validate_plugin_class(cls: type) -> tuple[bool, str]:
    """Check whether a class satisfies the DebuggingTool protocol without instantiation.

    Verifies all required methods and properties exist as attributes on the
    class, and checks the ``protocol_version`` class attribute.

    Args:
        cls: The class to validate.

    Returns:
        A ``(valid, message)`` tuple.
    """
    missing: list[str] = []

    for attr in (*_REQUIRED_PROPERTIES, *_REQUIRED_METHODS):
        if not hasattr(cls, attr):
            missing.append(attr)

    if missing:
        return (False, f"Missing required attributes: {', '.join(missing)}")

    version = getattr(cls, "protocol_version", None)
    if version is None:
        return (False, "Missing 'protocol_version' class attribute")

    if version != PROTOCOL_VERSION:
        return (
            False,
            f"Protocol version mismatch: expected {PROTOCOL_VERSION}, got {version}",
        )

    return (True, "Valid")


def _check_protocol_version(cls: type, tool_name: str) -> None:
    """Log a warning if the class protocol_version is missing or mismatched."""
    version = getattr(cls, "protocol_version", None)

    if version is None:
        logger.warning(
            "missing_protocol_version",
            tool=tool_name,
            expected=PROTOCOL_VERSION,
        )
        return

    if version != PROTOCOL_VERSION:
        logger.warning(
            "protocol_version_mismatch",
            tool=tool_name,
            expected=PROTOCOL_VERSION,
            actual=version,
        )
