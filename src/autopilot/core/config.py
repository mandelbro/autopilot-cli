"""Configuration models for Autopilot CLI (RFC Section 3.4.1).

Three-level hierarchy: global defaults (~/.autopilot/config.yaml)
-> project overrides (.autopilot/config.yaml) -> CLI flags.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


class ProjectConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    type: Literal["python", "typescript", "hybrid"] = "python"
    root: Path = Path(".")


class SchedulerConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    strategy: Literal["interval", "event", "hybrid"] = "interval"
    interval_seconds: int = Field(1800, gt=0)
    cycle_timeout_seconds: int = Field(7200, gt=0)
    agent_timeout_seconds: int = Field(900, gt=0)
    agent_timeouts: dict[str, int] = Field(default_factory=dict)
    consecutive_timeout_limit: int = Field(2, gt=0)


class UsageLimitsConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    daily_cycle_limit: int = Field(200, gt=0)
    weekly_cycle_limit: int = Field(1400, gt=0)
    max_agent_invocations_per_cycle: int = Field(40, gt=0)


class AgentsConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    roles: list[str] = Field(
        default_factory=lambda: [
            "project-leader",
            "engineering-manager",
            "technical-architect",
            "product-director",
        ]
    )
    models: dict[str, str] = Field(default_factory=dict)
    max_turns: dict[str, int] = Field(default_factory=dict)
    fallback_models: dict[str, list[str]] = Field(default_factory=dict)
    max_concurrent: int = Field(3, gt=0)


class QualityGatesConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    pre_commit: str = ""
    type_check: str = ""
    test: str = ""
    all: str = ""


class EnforcementConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    enabled: bool = True
    categories: list[str] = Field(
        default_factory=lambda: [
            "duplication",
            "conventions",
            "overengineering",
            "security",
            "error_handling",
            "dead_code",
            "type_safety",
            "test_quality",
            "comments",
            "deprecated",
            "async_misuse",
        ]
    )


class SafetyConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    auto_merge: bool = True
    require_ci_pass: bool = True
    require_review_approval: bool = True
    max_files_per_commit: int = Field(100, gt=0)
    require_tests: bool = True


class ApprovalConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    auto_approve_low_risk: bool = True
    auto_approve_medium_risk: bool = False
    require_approval_for_deletions: bool = True
    require_approval_for_schema_changes: bool = True


class ClaudeConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    extra_flags: str = "--dangerously-skip-permissions"
    mcp_config: str = ".mcp.json"
    claude_flow_version: str = "alpha"


class GitConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    base_branch: str = "main"
    branch_prefix: str = "feat/"
    branch_strategy: Literal["batch", "per-task"] = "batch"


class RenderServiceConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_key_env: str = "RENDER_API_KEY"
    poll_interval_seconds: int = Field(60, gt=0)
    deploy_timeout_seconds: int = Field(600, gt=0)


class DeploymentMonitoringConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    enabled: bool = False
    render: RenderServiceConfig = Field(default_factory=RenderServiceConfig)
    health_check_interval_seconds: int = Field(300, gt=0)


class AutopilotConfig(BaseModel):
    """Root configuration model."""

    model_config = ConfigDict(frozen=True)

    project: ProjectConfig
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    usage_limits: UsageLimitsConfig = Field(default_factory=UsageLimitsConfig)
    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    quality_gates: QualityGatesConfig = Field(default_factory=QualityGatesConfig)
    enforcement: EnforcementConfig = Field(default_factory=EnforcementConfig)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    approval: ApprovalConfig = Field(default_factory=ApprovalConfig)
    claude: ClaudeConfig = Field(default_factory=ClaudeConfig)
    git: GitConfig = Field(default_factory=GitConfig)
    deployment_monitoring: DeploymentMonitoringConfig = Field(
        default_factory=DeploymentMonitoringConfig
    )

    @classmethod
    def from_yaml(cls, path: Path) -> AutopilotConfig:
        """Load configuration from a YAML file."""
        if not path.exists():
            msg = (
                f"Configuration file not found: {path}\n"
                f"Create one with 'autopilot init' or see docs for the expected format."
            )
            raise FileNotFoundError(msg)
        try:
            with open(path) as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            msg = f"Invalid YAML in configuration file {path}: {exc}"
            raise ValueError(msg) from exc

        if data is None:
            msg = (
                f"Configuration file is empty: {path}\n"
                f"The file must contain at minimum a 'project' section with a 'name' field."
            )
            raise ValueError(msg)
        if not isinstance(data, dict):
            msg = f"Configuration file {path} must contain a YAML mapping, got {type(data).__name__}"
            raise ValueError(msg)
        return cls.model_validate(data)

    def to_yaml(self, path: Path) -> None:
        """Serialize configuration to a YAML file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            yaml.dump(
                self.model_dump(mode="json"),
                f,
                default_flow_style=False,
                sort_keys=False,
            )

    @classmethod
    def merge(cls, global_path: Path, project_path: Path) -> AutopilotConfig:
        """Merge global defaults with project overrides.

        Project values take precedence over global values.
        """
        global_data = _load_yaml_dict(global_path, label="global config")
        project_data = _load_yaml_dict(project_path, label="project config")
        merged = _deep_merge(global_data, project_data)
        return cls.model_validate(merged)


def _load_yaml_dict(path: Path, label: str) -> dict:
    """Load a YAML file and validate it contains a mapping."""
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        msg = f"Invalid YAML in {label} ({path}): {exc}"
        raise ValueError(msg) from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        msg = f"{label.capitalize()} ({path}) must contain a YAML mapping, got {type(data).__name__}"
        raise ValueError(msg)
    return data


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base, with override winning."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
