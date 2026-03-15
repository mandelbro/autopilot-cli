"""Core data models for Autopilot CLI.

Ports and evolves RepEngine models (Dispatch, DispatchPlan, AgentResult, UsageState)
and adds Session, CycleResult, SprintResult, and enforcement types per RFC Section 3.3.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, cast

# -- Enums --


class SessionType(StrEnum):
    DAEMON = "daemon"
    CYCLE = "cycle"
    DISCOVERY = "discovery"
    MANUAL = "manual"


class SessionStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class CycleStatus(StrEnum):
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class DispatchStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


class AgentName(StrEnum):
    PROJECT_LEADER = "project-leader"
    ENGINEERING_MANAGER = "engineering-manager"
    TECHNICAL_ARCHITECT = "technical-architect"
    PRODUCT_DIRECTOR = "product-director"


class ViolationSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


# -- Core orchestration models (evolved from RepEngine) --


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class Dispatch:
    """A single agent dispatch instruction from the PL dispatch plan."""

    agent: str
    action: str
    project_name: str = ""
    task_id: str = ""

    def __post_init__(self) -> None:
        if not self.agent:
            msg = "Dispatch.agent must not be empty"
            raise ValueError(msg)
        if not self.action:
            msg = "Dispatch.action must not be empty"
            raise ValueError(msg)


@dataclass(frozen=True)
class DispatchPlan:
    """Structured agent dispatch plan parsed from PL output."""

    dispatches: tuple[Dispatch, ...] = ()
    summary: str = ""

    def to_json(self) -> str:
        return json.dumps(
            {
                "dispatches": [
                    {
                        "agent": d.agent,
                        "action": d.action,
                        "project_name": d.project_name,
                        "task_id": d.task_id,
                    }
                    for d in self.dispatches
                ],
                "summary": self.summary,
            }
        )

    @classmethod
    def from_json(cls, raw: str) -> DispatchPlan:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            msg = f"Invalid JSON in dispatch plan: {exc}"
            raise ValueError(msg) from exc

        if not isinstance(parsed, dict):
            msg = f"Dispatch plan JSON must be a mapping, got {type(parsed).__name__}"
            raise ValueError(msg)

        data = cast("dict[str, Any]", parsed)
        dispatches: list[Dispatch] = []
        for i, raw_d in enumerate(data.get("dispatches", [])):
            if not isinstance(raw_d, dict):
                msg = f"Dispatch entry {i} must be a mapping, got {type(raw_d).__name__}"
                raise ValueError(msg)
            d = cast("dict[str, Any]", raw_d)
            if "agent" not in d or "action" not in d:
                msg = f"Dispatch entry {i} missing required 'agent' and/or 'action' fields: {d!r}"
                raise ValueError(msg)
            dispatches.append(
                Dispatch(
                    agent=str(d["agent"]),
                    action=str(d["action"]),
                    project_name=str(d.get("project_name", "")),
                    task_id=str(d.get("task_id", "")),
                )
            )
        return cls(dispatches=tuple(dispatches), summary=str(data.get("summary", "")))


@dataclass(frozen=True)
class AgentResult:
    """Result from a single agent invocation."""

    agent: str
    status: DispatchStatus
    exit_code: int = 0
    duration_seconds: float = 0.0
    output: str = ""
    error: str = ""


@dataclass(frozen=True)
class UsageState:
    """Tracks daily/weekly cycle counts for rate limiting."""

    daily_count: int = 0
    weekly_count: int = 0
    last_cycle_date: str = ""
    last_week_start: str = ""


# -- Session and cycle models --


@dataclass
class Session:
    """Runtime session container for autonomous work."""

    id: str
    project: str
    type: SessionType
    status: SessionStatus
    pid: int | None = None
    started_at: datetime = field(default_factory=_utc_now)
    ended_at: datetime | None = None
    agent_name: str | None = None
    cycle_id: str | None = None
    log_file: str = ""
    metadata: dict[str, Any] = field(default_factory=lambda: dict[str, Any]())

    def to_json(self) -> str:
        return json.dumps(
            {
                "id": self.id,
                "project": self.project,
                "type": self.type.value,
                "status": self.status.value,
                "pid": self.pid,
                "started_at": self.started_at.isoformat(),
                "ended_at": self.ended_at.isoformat() if self.ended_at else None,
                "agent_name": self.agent_name,
                "cycle_id": self.cycle_id,
                "log_file": self.log_file,
                "metadata": self.metadata,
            }
        )

    @classmethod
    def from_json(cls, raw: str) -> Session:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            msg = f"Invalid JSON in session data: {exc}"
            raise ValueError(msg) from exc

        if not isinstance(parsed, dict):
            msg = f"Session JSON must be a mapping, got {type(parsed).__name__}"
            raise ValueError(msg)

        data = cast("dict[str, Any]", parsed)
        required = ("id", "project", "type", "status", "started_at")
        missing = [k for k in required if k not in data]
        if missing:
            msg = f"Session JSON missing required fields: {missing}"
            raise ValueError(msg)

        try:
            ended_at_raw = data.get("ended_at")
            metadata_raw = data.get("metadata", {})
            return cls(
                id=str(data["id"]),
                project=str(data["project"]),
                type=SessionType(str(data["type"])),
                status=SessionStatus(str(data["status"])),
                pid=int(data["pid"]) if data.get("pid") is not None else None,
                started_at=datetime.fromisoformat(str(data["started_at"])),
                ended_at=(
                    datetime.fromisoformat(str(ended_at_raw)) if ended_at_raw else None
                ),
                agent_name=str(data["agent_name"]) if data.get("agent_name") is not None else None,
                cycle_id=str(data["cycle_id"]) if data.get("cycle_id") is not None else None,
                log_file=str(data.get("log_file", "")),
                metadata=cast("dict[str, Any]", metadata_raw) if isinstance(metadata_raw, dict) else {},
            )
        except (ValueError, TypeError) as exc:
            msg = f"Invalid session data (id={data.get('id', '?')}): {exc}"
            raise ValueError(msg) from exc


@dataclass(frozen=True)
class CycleResult:
    """Outcome of a single orchestration cycle."""

    id: str
    project_id: str
    status: CycleStatus
    started_at: datetime
    ended_at: datetime | None = None
    dispatches_planned: int = 0
    dispatches_succeeded: int = 0
    dispatches_failed: int = 0
    duration_seconds: float = 0.0


@dataclass(frozen=True)
class SprintResult:
    """Sprint velocity record."""

    sprint_id: str
    started_at: datetime
    ended_at: datetime | None = None
    points_planned: int = 0
    points_completed: int = 0
    tasks_completed: int = 0
    tasks_carried_over: int = 0


# -- Enforcement types --


@dataclass(frozen=True)
class Violation:
    """A single enforcement rule violation."""

    category: str
    rule: str
    file: str
    line: int = 0
    message: str = ""
    severity: ViolationSeverity = ViolationSeverity.WARNING
    suggestion: str = ""


@dataclass(frozen=True)
class Fix:
    """An applied fix for a violation."""

    violation: Violation
    applied: bool = False
    diff: str = ""


@dataclass(frozen=True)
class CheckResult:
    """Result from an enforcement check run."""

    category: str
    violations: tuple[Violation, ...] = ()
    files_scanned: int = 0
    duration_seconds: float = 0.0


@dataclass(frozen=True)
class SetupResult:
    """Result from enforcement layer setup."""

    layer: str
    success: bool = True
    files_created: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


@dataclass
class EnforcementReport:
    """Aggregated enforcement report across categories."""

    project_id: str
    collected_at: datetime = field(default_factory=_utc_now)
    results: list[CheckResult] = field(default_factory=lambda: list[CheckResult]())

    @property
    def total_violations(self) -> int:
        return sum(len(r.violations) for r in self.results)

    @property
    def total_files_scanned(self) -> int:
        return sum(r.files_scanned for r in self.results)

    def to_json(self) -> str:
        return json.dumps(
            {
                "project_id": self.project_id,
                "collected_at": self.collected_at.isoformat(),
                "total_violations": self.total_violations,
                "total_files_scanned": self.total_files_scanned,
                "results": [
                    {
                        "category": r.category,
                        "violations": [
                            {
                                "category": v.category,
                                "rule": v.rule,
                                "file": v.file,
                                "line": v.line,
                                "message": v.message,
                                "severity": v.severity.value,
                                "suggestion": v.suggestion,
                            }
                            for v in r.violations
                        ],
                        "files_scanned": r.files_scanned,
                        "duration_seconds": r.duration_seconds,
                    }
                    for r in self.results
                ],
            }
        )
