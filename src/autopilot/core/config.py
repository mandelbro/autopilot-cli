"""Configuration models for Autopilot CLI (RFC Section 3.4.1).

Three-level hierarchy: global defaults (~/.autopilot/config.yaml)
-> project overrides (.autopilot/config.yaml) -> CLI flags.
"""

from pathlib import Path
from typing import Any, Literal, Self, cast

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
    interval_seconds: int = Field(default=1800, gt=0)
    cycle_timeout_seconds: int = Field(default=7200, gt=0)
    agent_timeout_seconds: int = Field(default=900, gt=0)
    agent_timeouts: dict[str, int] = Field(default_factory=dict)
    consecutive_timeout_limit: int = Field(default=2, gt=0)


class UsageLimitsConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    daily_cycle_limit: int = Field(default=200, gt=0)
    weekly_cycle_limit: int = Field(default=1400, gt=0)
    max_agent_invocations_per_cycle: int = Field(default=40, gt=0)


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
    max_concurrent: int = Field(default=3, gt=0)


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
    max_files_per_commit: int = Field(default=100, gt=0)
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


class MonitoredServiceConfig(BaseModel):
    """Per-service monitoring configuration with health endpoints."""

    model_config = ConfigDict(frozen=True)

    id: str = ""
    name: str = ""
    health_endpoints: list[str] = Field(default_factory=lambda: list[str]())
    staging_url: str = ""


class RenderServiceConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_key_env: str = "RENDER_API_KEY"
    poll_interval_seconds: int = Field(default=60, gt=0)
    deploy_timeout_seconds: int = Field(default=600, gt=0)


class GitHubIssuesConfig(BaseModel):
    """GitHub issue creation settings for deploy failures."""

    model_config = ConfigDict(frozen=True)

    create_on_failure: bool = True
    labels: list[str] = Field(default_factory=lambda: ["deploy-failure", "autopilot"])


class DeploymentMonitoringConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    enabled: bool = False
    check_frequency: Literal["every_cycle", "every_nth_cycle", "manual_only"] = "every_cycle"
    health_check_timeout_seconds: int = Field(default=10, gt=0)
    failure_patterns: dict[str, str] = Field(default_factory=dict)
    github_issues: GitHubIssuesConfig = Field(default_factory=GitHubIssuesConfig)
    render: RenderServiceConfig = Field(default_factory=RenderServiceConfig)
    services: dict[str, MonitoredServiceConfig] = Field(default_factory=dict)


class WorkspaceConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    enabled: bool = False
    base_dir: str = "~/.autopilot/workspaces"
    cleanup_on_success: bool = True
    cleanup_on_failure: bool = False
    clone_depth: int = Field(default=0, ge=0)
    max_workspaces: int = Field(default=5, gt=0)


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
    workspace: WorkspaceConfig = Field(default_factory=WorkspaceConfig)

    @classmethod
    def from_yaml(cls, path: Path) -> Self:
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
            msg = (
                f"Configuration file {path} must contain a YAML mapping, got {type(data).__name__}"
            )
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
    def merge(cls, global_path: Path, project_path: Path) -> Self:
        """Merge global defaults with project overrides.

        Project values take precedence over global values.
        """
        global_data = _load_yaml_dict(global_path, label="global config")
        project_data = _load_yaml_dict(project_path, label="project config")
        merged = _deep_merge(global_data, project_data)
        return cls.model_validate(merged)


def _load_yaml_dict(path: Path, label: str) -> dict[str, Any]:
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
        msg = (
            f"{label.capitalize()} ({path}) must contain a YAML mapping, got {type(data).__name__}"
        )
        raise ValueError(msg)
    return cast("dict[str, Any]", data)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge override into base, with override winning."""
    result: dict[str, Any] = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(
                cast("dict[str, Any]", result[key]), cast("dict[str, Any]", value)
            )
        else:
            result[key] = value
    return result
