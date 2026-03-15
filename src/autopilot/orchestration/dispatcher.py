"""Dispatch plan parser and validator (Task 032).

Ports and evolves RepEngine dispatch.py for generalized dispatch parsing.
Handles code-fenced JSON, raw JSON, field name normalization, and
validation against the dynamic agent registry per RFC Section 3.3.
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, cast

from autopilot.core.models import Dispatch, DispatchPlan

if TYPE_CHECKING:
    from autopilot.core.agent_registry import AgentRegistry

_log = logging.getLogger(__name__)

# Known PL field name drift patterns: PL output -> canonical field
_FIELD_NORMALIZATION: dict[str, str] = {
    "reason": "action",
    "rationale": "action",
    "task": "action",
    "description": "action",
    "name": "agent",
    "role": "agent",
    "agent_name": "agent",
    "project": "project_name",
    "repo": "project_name",
    "repository": "project_name",
    "task_number": "task_id",
    "issue": "task_id",
    "ticket": "task_id",
}

# Regex to extract JSON from code-fenced blocks
_CODE_FENCE_RE = re.compile(
    r"```(?:json)?\s*\n(.*?)```",
    re.DOTALL,
)

# Regex to find JSON arrays or objects in raw text
_JSON_BLOCK_RE = re.compile(
    r"(\[[\s\S]*?\]|\{[\s\S]*?\})",
)


class DispatchParseError(Exception):
    """Raised when dispatch plan parsing fails."""


class DispatchValidationError(Exception):
    """Raised when dispatch plan validation fails."""

    def __init__(self, unknown_agents: list[str], available: list[str]) -> None:
        self.unknown_agents = unknown_agents
        self.available = available
        agents = ", ".join(sorted(unknown_agents))
        valid = ", ".join(sorted(available)) if available else "(none)"
        super().__init__(f"Unknown agent(s) in dispatch plan: {agents}. Available: {valid}")


def parse_dispatch_plan(raw_output: str) -> DispatchPlan:
    """Parse a dispatch plan from PL agent output.

    Tries extraction in order:
    1. Code-fenced JSON blocks
    2. Raw JSON objects/arrays
    3. Falls back to error

    Handles both single dispatch objects and lists of dispatches.
    """
    if not raw_output.strip():
        msg = "Empty output — no dispatch plan found"
        raise DispatchParseError(msg)

    # Try code-fenced JSON first
    json_str = _extract_code_fenced_json(raw_output)
    if json_str is None:
        json_str = _extract_raw_json(raw_output)
    if json_str is None:
        msg = "No JSON found in PL output"
        raise DispatchParseError(msg)

    return _parse_json_to_plan(json_str)


def validate_dispatch_plan(
    plan: DispatchPlan,
    registry: AgentRegistry,
) -> DispatchPlan:
    """Validate all agents in the plan exist in the registry.

    Raises DispatchValidationError if any agents are unknown.
    """
    unknown = registry.validate_dispatch(plan)
    if unknown:
        raise DispatchValidationError(unknown, registry.list_agents())
    return plan


def _extract_code_fenced_json(text: str) -> str | None:
    """Extract JSON from the first code-fenced block."""
    match = _CODE_FENCE_RE.search(text)
    if match:
        return match.group(1).strip()
    return None


def _extract_raw_json(text: str) -> str | None:
    """Extract the first valid JSON object or array from raw text.

    Uses bracket-matching to handle nested structures that simple
    regex fails to capture.
    """
    for start_char, end_char in (("{", "}"), ("[", "]")):
        idx = text.find(start_char)
        while idx != -1:
            candidate = _extract_balanced(text, idx, start_char, end_char)
            if candidate is not None:
                try:
                    json.loads(candidate)
                    return candidate
                except json.JSONDecodeError:
                    pass
            idx = text.find(start_char, idx + 1)
    return None


def _extract_balanced(text: str, start: int, open_ch: str, close_ch: str) -> str | None:
    """Extract a balanced bracket substring from text."""
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _parse_json_to_plan(json_str: str) -> DispatchPlan:
    """Parse a JSON string into a DispatchPlan."""
    try:
        data: object = json.loads(json_str)
    except json.JSONDecodeError as exc:
        msg = f"Invalid JSON in dispatch plan: {exc}"
        raise DispatchParseError(msg) from exc

    dispatches: list[Dispatch] = []
    summary = ""

    if isinstance(data, list):
        # List of dispatch objects
        data_list = cast("list[object]", data)
        for i, item in enumerate(data_list):
            if not isinstance(item, dict):
                msg = f"Dispatch entry {i} must be a mapping, got {type(item).__name__}"
                raise DispatchParseError(msg)
            dispatches.append(_normalize_and_create_dispatch(cast("dict[str, object]", item), i))
    elif isinstance(data, dict):
        data_dict = cast("dict[str, object]", data)
        # Could be a single dispatch or a plan with "dispatches" key
        if "dispatches" in data_dict:
            raw_dispatches = data_dict["dispatches"]
            if not isinstance(raw_dispatches, list):
                msg = f"'dispatches' must be a list, got {type(raw_dispatches).__name__}"
                raise DispatchParseError(msg)
            items = cast("list[object]", raw_dispatches)
            for i, item in enumerate(items):
                if not isinstance(item, dict):
                    msg = f"Dispatch entry {i} must be a mapping, got {type(item).__name__}"
                    raise DispatchParseError(msg)
                dispatches.append(_normalize_and_create_dispatch(cast("dict[str, object]", item), i))
            raw_summary = data_dict.get("summary", "")
            summary = str(raw_summary) if raw_summary else ""
        else:
            # Single dispatch object
            dispatches.append(_normalize_and_create_dispatch(data_dict, 0))
    else:
        msg = f"Dispatch plan must be a list or mapping, got {type(data).__name__}"
        raise DispatchParseError(msg)

    return DispatchPlan(dispatches=tuple(dispatches), summary=summary)


def _normalize_and_create_dispatch(raw: dict[str, object], index: int) -> Dispatch:
    """Normalize field names and create a Dispatch object."""
    normalized: dict[str, str] = {}
    for key, value in raw.items():
        lower_key = str(key).lower()
        canonical = _FIELD_NORMALIZATION.get(lower_key, lower_key)
        if canonical not in normalized:
            normalized[canonical] = str(value) if value is not None else ""

    agent = normalized.get("agent", "")
    action = normalized.get("action", "")

    if not agent:
        msg = f"Dispatch entry {index} missing 'agent' field after normalization: {raw!r}"
        raise DispatchParseError(msg)
    if not action:
        msg = f"Dispatch entry {index} missing 'action' field after normalization: {raw!r}"
        raise DispatchParseError(msg)

    return Dispatch(
        agent=agent,
        action=action,
        project_name=normalized.get("project_name", ""),
        task_id=normalized.get("task_id", ""),
    )
