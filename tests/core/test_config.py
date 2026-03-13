"""Tests for core configuration models (Task 002)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from autopilot.core.config import (
    AgentsConfig,
    AutopilotConfig,
    DeploymentMonitoringConfig,
    EnforcementConfig,
    GitConfig,
    GitHubIssuesConfig,
    MonitoredServiceConfig,
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

    def test_frozen(self) -> None:
        cfg = ProjectConfig(name="test")
        with pytest.raises(ValidationError):
            cfg.name = "other"  # type: ignore[misc]


class TestSchedulerConfig:
    def test_defaults(self) -> None:
        cfg = SchedulerConfig()
        assert cfg.strategy == "interval"
        assert cfg.interval_seconds == 1800
        assert cfg.cycle_timeout_seconds == 7200
        assert cfg.agent_timeout_seconds == 900
        assert cfg.consecutive_timeout_limit == 2
        assert cfg.agent_timeouts == {}

    def test_rejects_zero_interval(self) -> None:
        with pytest.raises(ValidationError, match="interval_seconds"):
            SchedulerConfig(interval_seconds=0)

    def test_rejects_negative_timeout(self) -> None:
        with pytest.raises(ValidationError, match="agent_timeout_seconds"):
            SchedulerConfig(agent_timeout_seconds=-1)


class TestUsageLimitsConfig:
    def test_defaults(self) -> None:
        cfg = UsageLimitsConfig()
        assert cfg.daily_cycle_limit == 200
        assert cfg.weekly_cycle_limit == 1400
        assert cfg.max_agent_invocations_per_cycle == 40

    def test_rejects_zero_limit(self) -> None:
        with pytest.raises(ValidationError, match="daily_cycle_limit"):
            UsageLimitsConfig(daily_cycle_limit=0)


class TestAgentsConfig:
    def test_default_roles(self) -> None:
        cfg = AgentsConfig()
        assert len(cfg.roles) == 4
        assert "project-leader" in cfg.roles
        assert cfg.max_concurrent == 3

    def test_rejects_zero_max_concurrent(self) -> None:
        with pytest.raises(ValidationError, match="max_concurrent"):
            AgentsConfig(max_concurrent=0)


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

    def test_rejects_zero_max_files(self) -> None:
        with pytest.raises(ValidationError, match="max_files_per_commit"):
            SafetyConfig(max_files_per_commit=0)


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

    def test_frozen(self) -> None:
        cfg = AutopilotConfig(project=ProjectConfig(name="test"))
        with pytest.raises(ValidationError):
            cfg.project = ProjectConfig(name="other")  # type: ignore[misc]

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

    def test_from_yaml_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="not found"):
            AutopilotConfig.from_yaml(tmp_path / "nonexistent.yaml")

    def test_from_yaml_empty_file(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty.yaml"
        empty.write_text("")
        with pytest.raises(ValueError, match="empty"):
            AutopilotConfig.from_yaml(empty)

    def test_from_yaml_invalid_yaml(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.yaml"
        bad.write_text(":\n  :\n  - [invalid")
        with pytest.raises(ValueError, match="Invalid YAML"):
            AutopilotConfig.from_yaml(bad)

    def test_from_yaml_non_dict(self, tmp_path: Path) -> None:
        bad = tmp_path / "list.yaml"
        bad.write_text("- item1\n- item2\n")
        with pytest.raises(ValueError, match="YAML mapping"):
            AutopilotConfig.from_yaml(bad)

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

    def test_merge_invalid_yaml_in_global(self, tmp_path: Path) -> None:
        global_path = tmp_path / "global.yaml"
        global_path.write_text(":\n  [invalid")
        project_path = tmp_path / "project.yaml"
        project_path.write_text("project:\n  name: test\n")

        with pytest.raises(ValueError, match="global config"):
            AutopilotConfig.merge(global_path, project_path)

    def test_merge_non_dict_yaml(self, tmp_path: Path) -> None:
        global_path = tmp_path / "global.yaml"
        global_path.write_text("- a list\n")
        project_path = tmp_path / "project.yaml"
        project_path.write_text("project:\n  name: test\n")

        with pytest.raises(ValueError, match="YAML mapping"):
            AutopilotConfig.merge(global_path, project_path)

    def test_invalid_values_raise_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            AutopilotConfig(
                project=ProjectConfig(name="bad", type="ruby"),  # type: ignore[arg-type]
            )


class TestMonitoredServiceConfig:
    def test_defaults(self) -> None:
        cfg = MonitoredServiceConfig()
        assert cfg.id == ""
        assert cfg.name == ""
        assert cfg.health_endpoints == []
        assert cfg.staging_url == ""

    def test_custom_values(self) -> None:
        cfg = MonitoredServiceConfig(
            id="svc-1",
            name="api",
            health_endpoints=["http://localhost/health"],
            staging_url="http://staging.example.com",
        )
        assert cfg.id == "svc-1"
        assert len(cfg.health_endpoints) == 1

    def test_frozen(self) -> None:
        cfg = MonitoredServiceConfig()
        with pytest.raises(ValidationError):
            cfg.name = "other"  # type: ignore[misc]


class TestGitHubIssuesConfig:
    def test_defaults(self) -> None:
        cfg = GitHubIssuesConfig()
        assert cfg.create_on_failure is True
        assert "deploy-failure" in cfg.labels
        assert "autopilot" in cfg.labels


class TestDeploymentMonitoringConfig:
    def test_defaults(self) -> None:
        cfg = DeploymentMonitoringConfig()
        assert cfg.enabled is False
        assert cfg.check_frequency == "every_cycle"
        assert cfg.health_check_timeout_seconds == 10
        assert cfg.failure_patterns == {}
        assert cfg.services == {}

    def test_with_services(self) -> None:
        cfg = DeploymentMonitoringConfig(
            services={
                "api": MonitoredServiceConfig(
                    id="svc-1",
                    name="api",
                    health_endpoints=["http://api/health"],
                ),
            }
        )
        assert "api" in cfg.services
        assert cfg.services["api"].name == "api"

    def test_with_failure_patterns(self) -> None:
        cfg = DeploymentMonitoringConfig(failure_patterns={"db_error": r"database.*timeout"})
        assert "db_error" in cfg.failure_patterns

    def test_yaml_round_trip(self, tmp_path: Path) -> None:
        original = AutopilotConfig(
            project=ProjectConfig(name="monitor-test"),
            deployment_monitoring=DeploymentMonitoringConfig(
                enabled=True,
                check_frequency="every_nth_cycle",
                services={
                    "web": MonitoredServiceConfig(
                        id="svc-web",
                        name="web",
                        health_endpoints=["http://web/health"],
                        staging_url="http://staging.web",
                    )
                },
                failure_patterns={"custom": r"pattern"},
            ),
        )
        yaml_path = tmp_path / "config.yaml"
        original.to_yaml(yaml_path)
        loaded = AutopilotConfig.from_yaml(yaml_path)

        assert loaded.deployment_monitoring.enabled is True
        assert loaded.deployment_monitoring.check_frequency == "every_nth_cycle"
        assert "web" in loaded.deployment_monitoring.services
        assert loaded.deployment_monitoring.services["web"].staging_url == "http://staging.web"
        assert "custom" in loaded.deployment_monitoring.failure_patterns


class TestDeepMerge:
    def test_flat_merge(self) -> None:
        assert _deep_merge({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}

    def test_override(self) -> None:
        assert _deep_merge({"a": 1}, {"a": 2}) == {"a": 2}

    def test_nested_merge(self) -> None:
        base = {"x": {"a": 1, "b": 2}}
        override = {"x": {"b": 3, "c": 4}}
        assert _deep_merge(base, override) == {"x": {"a": 1, "b": 3, "c": 4}}
