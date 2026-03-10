"""Configuration models for Autopilot CLI (RFC Section 3.4.1).

Three-level hierarchy: global defaults (~/.autopilot/config.yaml)
-> project overrides (.autopilot/config.yaml) -> CLI flags.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


class ProjectConfig(BaseModel):
    """Per-project configuration."""

    name: str
    type: Literal["python", "typescript", "hybrid"] = "python"
    root: Path = Path(".")


class SchedulerConfig(BaseModel):
    strategy: Literal["interval", "event", "hybrid"] = "interval"
    interval_seconds: int = 1800
    cycle_timeout_seconds: int = 7200
    agent_timeout_seconds: int = 900
    agent_timeouts: dict[str, int] = Field(default_factory=dict)
    consecutive_timeout_limit: int = 2


class UsageLimitsConfig(BaseModel):
    daily_cycle_limit: int = 200
    weekly_cycle_limit: int = 1400
    max_agent_invocations_per_cycle: int = 40


class AgentsConfig(BaseModel):
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
    max_concurrent: int = 3


class QualityGatesConfig(BaseModel):
    pre_commit: str = ""
    type_check: str = ""
    test: str = ""
    all: str = ""


class EnforcementConfig(BaseModel):
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
    auto_merge: bool = True
    require_ci_pass: bool = True
    require_review_approval: bool = True
    max_files_per_commit: int = 100
    require_tests: bool = True


class ApprovalConfig(BaseModel):
    auto_approve_low_risk: bool = True
    auto_approve_medium_risk: bool = False
    require_approval_for_deletions: bool = True
    require_approval_for_schema_changes: bool = True


class ClaudeConfig(BaseModel):
    extra_flags: str = "--dangerously-skip-permissions"
    mcp_config: str = ".mcp.json"
    claude_flow_version: str = "alpha"


class GitConfig(BaseModel):
    base_branch: str = "main"
    branch_prefix: str = "feat/"
    branch_strategy: Literal["batch", "per-task"] = "batch"


class RenderServiceConfig(BaseModel):
    api_key_env: str = "RENDER_API_KEY"
    poll_interval_seconds: int = 60
    deploy_timeout_seconds: int = 600


class DeploymentMonitoringConfig(BaseModel):
    enabled: bool = False
    render: RenderServiceConfig = Field(default_factory=RenderServiceConfig)
    health_check_interval_seconds: int = 300


class AutopilotConfig(BaseModel):
    """Root configuration model."""

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
        with open(path) as f:
            data = yaml.safe_load(f)
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
        global_data: dict = {}
        if global_path.exists():
            with open(global_path) as f:
                global_data = yaml.safe_load(f) or {}

        project_data: dict = {}
        if project_path.exists():
            with open(project_path) as f:
                project_data = yaml.safe_load(f) or {}

        merged = _deep_merge(global_data, project_data)
        return cls.model_validate(merged)


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base, with override winning."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
