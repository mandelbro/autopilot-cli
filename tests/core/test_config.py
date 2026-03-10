"""Tests for core configuration models (Task 002)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from autopilot.core.config import (
    AgentsConfig,
    AutopilotConfig,
    EnforcementConfig,
    GitConfig,
    ProjectConfig,
    SafetyConfig,
    SchedulerConfig,
    UsageLimitsConfig,
    _deep_merge,
)


class TestProjectConfig:
    def test_defaults(self) -> None:
        cfg = ProjectConfig(name="test")
        assert cfg.name == "test"
        assert cfg.type == "python"
        assert cfg.root == Path(".")

    def test_invalid_type_raises(self) -> None:
        with pytest.raises(ValidationError):
            ProjectConfig(name="test", type="ruby")  # type: ignore[arg-type]


class TestSchedulerConfig:
    def test_defaults(self) -> None:
        cfg = SchedulerConfig()
        assert cfg.strategy == "interval"
        assert cfg.interval_seconds == 1800
        assert cfg.cycle_timeout_seconds == 7200
        assert cfg.agent_timeout_seconds == 900
        assert cfg.consecutive_timeout_limit == 2
        assert cfg.agent_timeouts == {}


class TestUsageLimitsConfig:
    def test_defaults(self) -> None:
        cfg = UsageLimitsConfig()
        assert cfg.daily_cycle_limit == 200
        assert cfg.weekly_cycle_limit == 1400
        assert cfg.max_agent_invocations_per_cycle == 40


class TestAgentsConfig:
    def test_default_roles(self) -> None:
        cfg = AgentsConfig()
        assert len(cfg.roles) == 4
        assert "project-leader" in cfg.roles
        assert cfg.max_concurrent == 3


class TestEnforcementConfig:
    def test_all_11_categories(self) -> None:
        cfg = EnforcementConfig()
        assert len(cfg.categories) == 11
        assert "duplication" in cfg.categories
        assert "async_misuse" in cfg.categories


class TestSafetyConfig:
    def test_defaults(self) -> None:
        cfg = SafetyConfig()
        assert cfg.auto_merge is True
        assert cfg.require_tests is True
        assert cfg.max_files_per_commit == 100


class TestGitConfig:
    def test_defaults(self) -> None:
        cfg = GitConfig()
        assert cfg.base_branch == "main"
        assert cfg.branch_strategy == "batch"

    def test_invalid_strategy_raises(self) -> None:
        with pytest.raises(ValidationError):
            GitConfig(branch_strategy="yolo")  # type: ignore[arg-type]


class TestAutopilotConfig:
    def test_minimal_creation(self) -> None:
        cfg = AutopilotConfig(project=ProjectConfig(name="myproject"))
        assert cfg.project.name == "myproject"
        assert cfg.scheduler.strategy == "interval"

    def test_yaml_round_trip(self, tmp_path: Path) -> None:
        original = AutopilotConfig(
            project=ProjectConfig(name="roundtrip", type="typescript"),
            scheduler=SchedulerConfig(interval_seconds=600),
        )
        yaml_path = tmp_path / "config.yaml"
        original.to_yaml(yaml_path)
        loaded = AutopilotConfig.from_yaml(yaml_path)

        assert loaded.project.name == "roundtrip"
        assert loaded.project.type == "typescript"
        assert loaded.scheduler.interval_seconds == 600
        assert loaded.safety.auto_merge is True

    def test_yaml_preserves_all_values(self, tmp_path: Path) -> None:
        original = AutopilotConfig(
            project=ProjectConfig(name="full"),
            agents=AgentsConfig(max_concurrent=5),
            git=GitConfig(branch_strategy="per-task"),
        )
        yaml_path = tmp_path / "config.yaml"
        original.to_yaml(yaml_path)
        loaded = AutopilotConfig.from_yaml(yaml_path)

        assert loaded.agents.max_concurrent == 5
        assert loaded.git.branch_strategy == "per-task"

    def test_merge_project_overrides_global(self, tmp_path: Path) -> None:
        global_path = tmp_path / "global.yaml"
        project_path = tmp_path / "project.yaml"

        global_data = {
            "project": {"name": "global-default", "type": "python"},
            "scheduler": {"interval_seconds": 1800},
        }
        project_data = {
            "project": {"name": "myproject"},
            "scheduler": {"interval_seconds": 600},
        }

        with open(global_path, "w") as f:
            yaml.dump(global_data, f)
        with open(project_path, "w") as f:
            yaml.dump(project_data, f)

        merged = AutopilotConfig.merge(global_path, project_path)
        assert merged.project.name == "myproject"
        assert merged.scheduler.interval_seconds == 600

    def test_merge_missing_global(self, tmp_path: Path) -> None:
        project_path = tmp_path / "project.yaml"
        project_data = {"project": {"name": "solo"}}
        with open(project_path, "w") as f:
            yaml.dump(project_data, f)

        merged = AutopilotConfig.merge(tmp_path / "nonexistent.yaml", project_path)
        assert merged.project.name == "solo"

    def test_invalid_values_raise_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            AutopilotConfig(
                project=ProjectConfig(name="bad", type="ruby"),  # type: ignore[arg-type]
            )


class TestDeepMerge:
    def test_flat_merge(self) -> None:
        assert _deep_merge({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}

    def test_override(self) -> None:
        assert _deep_merge({"a": 1}, {"a": 2}) == {"a": 2}

    def test_nested_merge(self) -> None:
        base = {"x": {"a": 1, "b": 2}}
        override = {"x": {"b": 3, "c": 4}}
        assert _deep_merge(base, override) == {"x": {"a": 1, "b": 3, "c": 4}}
