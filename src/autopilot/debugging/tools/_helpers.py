"""Shared helper functions for debugging tool plugins.

Extracted from browser_mcp.py and desktop_agent.py to avoid duplication
across plugin implementations.
"""

from __future__ import annotations

from pathlib import Path  # noqa: TCH003 — used at runtime in ensure_screenshot_dir

_DEFAULT_SCREENSHOT_DIR = ".autopilot/debugging/screenshots"


def ensure_screenshot_dir(project_dir: Path) -> Path:
    """Create the screenshot directory if it does not exist."""
    screenshot_dir = project_dir / _DEFAULT_SCREENSHOT_DIR
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    return screenshot_dir


def classify_ux_criterion(criterion: str) -> str:
    """Classify a UX criterion into a category based on keywords."""
    criterion_lower = criterion.lower()
    if any(kw in criterion_lower for kw in ("color", "contrast", "font", "style", "visual")):
        return "visual_design"
    if any(kw in criterion_lower for kw in ("nav", "menu", "link", "route", "breadcrumb")):
        return "navigation"
    if any(kw in criterion_lower for kw in ("form", "input", "button", "submit", "field")):
        return "interaction"
    if any(kw in criterion_lower for kw in ("error", "message", "feedback", "toast", "alert")):
        return "feedback"
    if any(kw in criterion_lower for kw in ("access", "aria", "screen reader", "keyboard")):
        return "accessibility"
    return "general"
