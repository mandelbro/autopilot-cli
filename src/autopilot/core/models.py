"""Core data models for Autopilot CLI.

Ports and evolves RepEngine models (Dispatch, DispatchPlan, AgentResult, UsageState)
and adds Session, CycleResult, SprintResult, and enforcement types per RFC Section 3.3.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

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


@dataclass(frozen=True)
class Dispatch:
    """A single agent dispatch instruction from the PL dispatch plan."""

    agent: str
    action: str
    project_name: str = ""
    task_id: str = ""


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
        data = json.loads(raw)
        dispatches = tuple(
            Dispatch(
                agent=d["agent"],
                action=d["action"],
                project_name=d.get("project_name", ""),
                task_id=d.get("task_id", ""),
            )
            for d in data.get("dispatches", [])
        )
        return cls(dispatches=dispatches, summary=data.get("summary", ""))


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
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: datetime | None = None
    agent_name: str | None = None
    cycle_id: str | None = None
    log_file: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

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
        data = json.loads(raw)
        return cls(
            id=data["id"],
            project=data["project"],
            type=SessionType(data["type"]),
            status=SessionStatus(data["status"]),
            pid=data.get("pid"),
            started_at=datetime.fromisoformat(data["started_at"]),
            ended_at=(
                datetime.fromisoformat(data["ended_at"]) if data.get("ended_at") else None
            ),
            agent_name=data.get("agent_name"),
            cycle_id=data.get("cycle_id"),
            log_file=data.get("log_file", ""),
            metadata=data.get("metadata", {}),
        )


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
    collected_at: datetime = field(default_factory=datetime.now)
    results: list[CheckResult] = field(default_factory=list)

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
