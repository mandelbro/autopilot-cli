"""Tests for AgentRegistry (Task 015)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from autopilot.core.agent_registry import AgentNotFoundError, AgentRegistry
from autopilot.core.models import Dispatch, DispatchPlan

if TYPE_CHECKING:
    from pathlib import Path


class TestAgentRegistry:
    def test_list_agents_empty(self, tmp_path: Path) -> None:
        registry = AgentRegistry(
            project_agents_dir=tmp_path / "proj_agents",
            global_agents_dir=tmp_path / "global_agents",
        )
        assert registry.list_agents() == []

    def test_list_agents_discovers_md_files(self, tmp_path: Path) -> None:
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "coder.md").write_text("You are a coder.")
        (agents_dir / "reviewer.md").write_text("You are a reviewer.")
        registry = AgentRegistry(project_agents_dir=agents_dir)
        assert registry.list_agents() == ["coder", "reviewer"]

    def test_excludes_underscore_prefixed(self, tmp_path: Path) -> None:
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "coder.md").write_text("prompt")
        (agents_dir / "_draft.md").write_text("draft prompt")
        registry = AgentRegistry(project_agents_dir=agents_dir)
        assert registry.list_agents() == ["coder"]

    def test_excludes_non_md_files(self, tmp_path: Path) -> None:
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "coder.md").write_text("prompt")
        (agents_dir / "notes.txt").write_text("notes")
        registry = AgentRegistry(project_agents_dir=agents_dir)
        assert registry.list_agents() == ["coder"]

    def test_project_overrides_global(self, tmp_path: Path) -> None:
        global_dir = tmp_path / "global"
        global_dir.mkdir()
        (global_dir / "coder.md").write_text("global coder")
        (global_dir / "reviewer.md").write_text("global reviewer")

        proj_dir = tmp_path / "project"
        proj_dir.mkdir()
        (proj_dir / "coder.md").write_text("project coder")

        registry = AgentRegistry(project_agents_dir=proj_dir, global_agents_dir=global_dir)
        agents = registry.list_agents()
        assert "coder" in agents
        assert "reviewer" in agents
        # Project-level should win
        assert registry.load_prompt("coder") == "project coder"
        assert registry.load_prompt("reviewer") == "global reviewer"


class TestPathTraversalProtection:
    def test_rejects_slash_in_name(self, tmp_path: Path) -> None:
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        registry = AgentRegistry(project_agents_dir=agents_dir)
        assert registry.validate_agent("../../etc/passwd") is False

    def test_rejects_dotdot_in_name(self, tmp_path: Path) -> None:
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        registry = AgentRegistry(project_agents_dir=agents_dir)
        assert registry.validate_agent("..") is False

    def test_rejects_dot_prefix(self, tmp_path: Path) -> None:
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        registry = AgentRegistry(project_agents_dir=agents_dir)
        assert registry.validate_agent(".hidden") is False

    def test_load_prompt_rejects_traversal(self, tmp_path: Path) -> None:
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "coder.md").write_text("prompt")
        registry = AgentRegistry(project_agents_dir=agents_dir)
        with pytest.raises(AgentNotFoundError):
            registry.load_prompt("../secrets")


class TestLoadPrompt:
    def test_load_prompt_success(self, tmp_path: Path) -> None:
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "coder.md").write_text("You are a coder agent.")
        registry = AgentRegistry(project_agents_dir=agents_dir)
        assert registry.load_prompt("coder") == "You are a coder agent."

    def test_load_prompt_not_found_raises(self, tmp_path: Path) -> None:
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "coder.md").write_text("prompt")
        registry = AgentRegistry(project_agents_dir=agents_dir)
        with pytest.raises(AgentNotFoundError, match="nope") as exc_info:
            registry.load_prompt("nope")
        assert "coder" in str(exc_info.value)

    def test_agent_not_found_error_attributes(self) -> None:
        err = AgentNotFoundError("x", ["a", "b"])
        assert err.name == "x"
        assert err.available == ["a", "b"]


class TestValidateAgent:
    def test_validate_existing(self, tmp_path: Path) -> None:
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "coder.md").write_text("prompt")
        registry = AgentRegistry(project_agents_dir=agents_dir)
        assert registry.validate_agent("coder") is True

    def test_validate_missing(self, tmp_path: Path) -> None:
        registry = AgentRegistry(
            project_agents_dir=tmp_path / "empty",
            global_agents_dir=tmp_path / "empty2",
        )
        assert registry.validate_agent("nope") is False


class TestValidateDispatch:
    def test_all_valid(self, tmp_path: Path) -> None:
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "coder.md").write_text("prompt")
        (agents_dir / "reviewer.md").write_text("prompt")
        registry = AgentRegistry(project_agents_dir=agents_dir)
        plan = DispatchPlan(
            dispatches=(
                Dispatch(agent="coder", action="code"),
                Dispatch(agent="reviewer", action="review"),
            )
        )
        assert registry.validate_dispatch(plan) == []

    def test_returns_unknown_agents(self, tmp_path: Path) -> None:
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "coder.md").write_text("prompt")
        registry = AgentRegistry(project_agents_dir=agents_dir)
        plan = DispatchPlan(
            dispatches=(
                Dispatch(agent="coder", action="code"),
                Dispatch(agent="unknown-agent", action="do"),
            )
        )
        unknown = registry.validate_dispatch(plan)
        assert unknown == ["unknown-agent"]

    def test_empty_plan(self, tmp_path: Path) -> None:
        registry = AgentRegistry(project_agents_dir=tmp_path)
        plan = DispatchPlan()
        assert registry.validate_dispatch(plan) == []
