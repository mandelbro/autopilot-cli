"""Tests for dispatch plan parser and validator (Task 032)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from autopilot.core.models import DispatchPlan
from autopilot.orchestration.dispatcher import (
    DispatchParseError,
    DispatchValidationError,
    parse_dispatch_plan,
    validate_dispatch_plan,
)


class TestParseCodeFencedJSON:
    def test_code_fenced_json_list(self) -> None:
        raw = """Here is the plan:
```json
[
  {"agent": "engineering-manager", "action": "Review PR #42"}
]
```
"""
        plan = parse_dispatch_plan(raw)
        assert len(plan.dispatches) == 1
        assert plan.dispatches[0].agent == "engineering-manager"
        assert plan.dispatches[0].action == "Review PR #42"

    def test_code_fenced_json_object_with_dispatches(self) -> None:
        raw = """```json
{
  "dispatches": [
    {"agent": "technical-architect", "action": "Design module"},
    {"agent": "engineering-manager", "action": "Implement feature"}
  ],
  "summary": "Two-phase plan"
}
```"""
        plan = parse_dispatch_plan(raw)
        assert len(plan.dispatches) == 2
        assert plan.summary == "Two-phase plan"

    def test_code_fence_without_json_lang(self) -> None:
        raw = """```
{"agent": "project-leader", "action": "Plan sprint"}
```"""
        plan = parse_dispatch_plan(raw)
        assert len(plan.dispatches) == 1
        assert plan.dispatches[0].agent == "project-leader"


class TestParseRawJSON:
    def test_raw_json_object(self) -> None:
        raw = 'Some text {"agent": "engineering-manager", "action": "Fix bug"} more text'
        plan = parse_dispatch_plan(raw)
        assert len(plan.dispatches) == 1
        assert plan.dispatches[0].agent == "engineering-manager"

    def test_raw_json_array(self) -> None:
        raw = '[{"agent": "technical-architect", "action": "Refactor"}]'
        plan = parse_dispatch_plan(raw)
        assert len(plan.dispatches) == 1


class TestFieldNormalization:
    def test_reason_maps_to_action(self) -> None:
        raw = json.dumps({"agent": "project-leader", "reason": "Sprint planning"})
        plan = parse_dispatch_plan(raw)
        assert plan.dispatches[0].action == "Sprint planning"

    def test_rationale_maps_to_action(self) -> None:
        raw = json.dumps({"agent": "project-leader", "rationale": "Code review"})
        plan = parse_dispatch_plan(raw)
        assert plan.dispatches[0].action == "Code review"

    def test_name_maps_to_agent(self) -> None:
        raw = json.dumps({"name": "technical-architect", "action": "Design"})
        plan = parse_dispatch_plan(raw)
        assert plan.dispatches[0].agent == "technical-architect"

    def test_role_maps_to_agent(self) -> None:
        raw = json.dumps({"role": "engineering-manager", "action": "Review"})
        plan = parse_dispatch_plan(raw)
        assert plan.dispatches[0].agent == "engineering-manager"

    def test_project_maps_to_project_name(self) -> None:
        raw = json.dumps({"agent": "project-leader", "action": "Deploy", "project": "my-app"})
        plan = parse_dispatch_plan(raw)
        assert plan.dispatches[0].project_name == "my-app"

    def test_task_number_maps_to_task_id(self) -> None:
        raw = json.dumps({"agent": "project-leader", "action": "Fix", "task_number": "042"})
        plan = parse_dispatch_plan(raw)
        assert plan.dispatches[0].task_id == "042"


class TestParseSingleDispatch:
    def test_single_dispatch_object(self) -> None:
        raw = json.dumps({"agent": "project-leader", "action": "Plan"})
        plan = parse_dispatch_plan(raw)
        assert len(plan.dispatches) == 1

    def test_single_dispatch_in_dispatches_key(self) -> None:
        raw = json.dumps({"dispatches": [{"agent": "project-leader", "action": "Plan"}]})
        plan = parse_dispatch_plan(raw)
        assert len(plan.dispatches) == 1


class TestParseErrors:
    def test_empty_output_raises(self) -> None:
        with pytest.raises(DispatchParseError, match="Empty output"):
            parse_dispatch_plan("")

    def test_no_json_raises(self) -> None:
        with pytest.raises(DispatchParseError, match="No JSON found"):
            parse_dispatch_plan("Just some plain text without any JSON")

    def test_missing_agent_raises(self) -> None:
        raw = json.dumps({"action": "Do something"})
        with pytest.raises(DispatchParseError, match="missing 'agent'"):
            parse_dispatch_plan(raw)

    def test_missing_action_raises(self) -> None:
        raw = json.dumps({"agent": "project-leader"})
        with pytest.raises(DispatchParseError, match="missing 'action'"):
            parse_dispatch_plan(raw)

    def test_non_dict_entry_raises(self) -> None:
        raw = json.dumps(["not a dict"])
        with pytest.raises(DispatchParseError, match="must be a mapping"):
            parse_dispatch_plan(raw)

    def test_invalid_json_raises(self) -> None:
        raw = "```json\n{invalid json}\n```"
        with pytest.raises(DispatchParseError, match="Invalid JSON"):
            parse_dispatch_plan(raw)


class TestValidateDispatchPlan:
    def test_valid_plan_passes(self) -> None:
        plan = DispatchPlan(
            dispatches=(
                __import__("autopilot.core.models", fromlist=["Dispatch"]).Dispatch(
                    agent="project-leader", action="Plan"
                ),
            )
        )
        registry = MagicMock()
        registry.validate_dispatch.return_value = []
        result = validate_dispatch_plan(plan, registry)
        assert result is plan

    def test_unknown_agents_raises(self) -> None:
        plan = DispatchPlan(
            dispatches=(
                __import__("autopilot.core.models", fromlist=["Dispatch"]).Dispatch(
                    agent="unknown-agent", action="Do"
                ),
            )
        )
        registry = MagicMock()
        registry.validate_dispatch.return_value = ["unknown-agent"]
        registry.list_agents.return_value = ["project-leader"]
        with pytest.raises(DispatchValidationError, match="unknown-agent"):
            validate_dispatch_plan(plan, registry)
