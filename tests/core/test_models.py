"""Tests for core data models (Task 003)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from autopilot.core.models import (
    AgentName,
    AgentResult,
    CheckResult,
    CycleResult,
    CycleStatus,
    Dispatch,
    DispatchPlan,
    DispatchStatus,
    EnforcementReport,
    Fix,
    Session,
    SessionStatus,
    SessionType,
    SetupResult,
    SprintResult,
    UsageState,
    Violation,
    ViolationSeverity,
    WorkspaceInfo,
    WorkspaceStatus,
)


class TestEnums:
    def test_session_type_values(self) -> None:
        assert SessionType.DAEMON.value == "daemon"
        assert SessionType.CYCLE.value == "cycle"
        assert SessionType.DISCOVERY.value == "discovery"
        assert SessionType.MANUAL.value == "manual"

    def test_session_status_values(self) -> None:
        assert SessionStatus.RUNNING.value == "running"
        assert SessionStatus.COMPLETED.value == "completed"
        assert SessionStatus.FAILED.value == "failed"
        assert SessionStatus.PAUSED.value == "paused"

    def test_cycle_status_values(self) -> None:
        assert CycleStatus.COMPLETED.value == "COMPLETED"
        assert CycleStatus.PARTIAL.value == "PARTIAL"
        assert CycleStatus.FAILED.value == "FAILED"

    def test_agent_name_values(self) -> None:
        assert AgentName.PROJECT_LEADER.value == "project-leader"
        assert AgentName.ENGINEERING_MANAGER.value == "engineering-manager"

    def test_violation_severity(self) -> None:
        assert ViolationSeverity.ERROR.value == "error"


class TestDispatch:
    def test_creation(self) -> None:
        d = Dispatch(agent="project-leader", action="plan sprint")
        assert d.agent == "project-leader"
        assert d.action == "plan sprint"
        assert d.project_name == ""
        assert d.task_id == ""

    def test_frozen(self) -> None:
        d = Dispatch(agent="test", action="test")
        with pytest.raises(AttributeError):
            d.agent = "other"  # type: ignore[misc]

    def test_empty_agent_raises(self) -> None:
        with pytest.raises(ValueError, match="agent must not be empty"):
            Dispatch(agent="", action="do something")

    def test_empty_action_raises(self) -> None:
        with pytest.raises(ValueError, match="action must not be empty"):
            Dispatch(agent="test-agent", action="")


class TestDispatchPlan:
    def test_empty_plan(self) -> None:
        plan = DispatchPlan()
        assert len(plan.dispatches) == 0
        assert plan.summary == ""

    def test_json_round_trip(self) -> None:
        original = DispatchPlan(
            dispatches=(
                Dispatch(agent="project-leader", action="review", task_id="T-001"),
                Dispatch(agent="engineering-manager", action="implement"),
            ),
            summary="Sprint 1 work",
        )
        raw = original.to_json()
        restored = DispatchPlan.from_json(raw)

        assert len(restored.dispatches) == 2
        assert restored.dispatches[0].agent == "project-leader"
        assert restored.dispatches[0].task_id == "T-001"
        assert restored.dispatches[1].action == "implement"
        assert restored.summary == "Sprint 1 work"

    def test_from_json_missing_fields(self) -> None:
        raw = json.dumps({"dispatches": [{"agent": "a", "action": "b"}]})
        plan = DispatchPlan.from_json(raw)
        assert plan.dispatches[0].project_name == ""

    def test_from_json_invalid_json(self) -> None:
        with pytest.raises(ValueError, match="Invalid JSON"):
            DispatchPlan.from_json("not json")

    def test_from_json_non_dict(self) -> None:
        with pytest.raises(ValueError, match="must be a mapping"):
            DispatchPlan.from_json("[1, 2]")

    def test_from_json_missing_agent_key(self) -> None:
        raw = json.dumps({"dispatches": [{"action": "do"}]})
        with pytest.raises(ValueError, match="missing required"):
            DispatchPlan.from_json(raw)

    def test_from_json_non_dict_entry(self) -> None:
        raw = json.dumps({"dispatches": ["not a dict"]})
        with pytest.raises(ValueError, match="must be a mapping"):
            DispatchPlan.from_json(raw)


class TestAgentResult:
    def test_success_result(self) -> None:
        r = AgentResult(agent="tester", status=DispatchStatus.SUCCESS, exit_code=0)
        assert r.status == DispatchStatus.SUCCESS

    def test_failure_result(self) -> None:
        r = AgentResult(
            agent="builder",
            status=DispatchStatus.FAILED,
            exit_code=1,
            error="build failed",
        )
        assert r.error == "build failed"


class TestUsageState:
    def test_defaults(self) -> None:
        state = UsageState()
        assert state.daily_count == 0
        assert state.weekly_count == 0


class TestSession:
    def test_creation(self) -> None:
        s = Session(
            id="s-001",
            project="myproject",
            type=SessionType.DAEMON,
            status=SessionStatus.RUNNING,
            pid=1234,
        )
        assert s.id == "s-001"
        assert s.type == SessionType.DAEMON
        assert s.pid == 1234

    def test_default_started_at_is_utc(self) -> None:
        s = Session(
            id="s-utc",
            project="test",
            type=SessionType.MANUAL,
            status=SessionStatus.RUNNING,
        )
        assert s.started_at.tzinfo is not None

    def test_json_round_trip(self) -> None:
        now = datetime(2026, 3, 10, 12, 0, 0)
        original = Session(
            id="s-002",
            project="test",
            type=SessionType.CYCLE,
            status=SessionStatus.COMPLETED,
            started_at=now,
            ended_at=now,
            agent_name="project-leader",
            cycle_id="c-001",
            log_file="/tmp/test.log",
            metadata={"key": "value"},
        )
        raw = original.to_json()
        restored = Session.from_json(raw)

        assert restored.id == "s-002"
        assert restored.type == SessionType.CYCLE
        assert restored.status == SessionStatus.COMPLETED
        assert restored.agent_name == "project-leader"
        assert restored.metadata == {"key": "value"}

    def test_from_json_invalid_json(self) -> None:
        with pytest.raises(ValueError, match="Invalid JSON"):
            Session.from_json("not json")

    def test_from_json_non_dict(self) -> None:
        with pytest.raises(ValueError, match="must be a mapping"):
            Session.from_json("[1]")

    def test_from_json_missing_required(self) -> None:
        with pytest.raises(ValueError, match="missing required"):
            Session.from_json(json.dumps({"id": "s-1"}))

    def test_from_json_invalid_enum(self) -> None:
        raw = json.dumps(
            {
                "id": "s-1",
                "project": "p",
                "type": "invalid_type",
                "status": "running",
                "started_at": "2026-01-01T00:00:00",
            }
        )
        with pytest.raises(ValueError, match="Invalid session data"):
            Session.from_json(raw)


class TestCycleResult:
    def test_creation(self) -> None:
        now = datetime(2026, 3, 10, 12, 0, 0)
        r = CycleResult(
            id="c-001",
            project_id="p-001",
            status=CycleStatus.COMPLETED,
            started_at=now,
            dispatches_planned=3,
            dispatches_succeeded=2,
            dispatches_failed=1,
        )
        assert r.dispatches_planned == 3
        assert r.dispatches_failed == 1


class TestSprintResult:
    def test_creation(self) -> None:
        now = datetime(2026, 3, 10)
        r = SprintResult(
            sprint_id="sprint-1",
            started_at=now,
            points_planned=21,
            points_completed=18,
            tasks_completed=5,
            tasks_carried_over=1,
        )
        assert r.points_completed == 18
        assert r.tasks_carried_over == 1


class TestViolation:
    def test_creation(self) -> None:
        v = Violation(
            category="duplication",
            rule="no-duplicate-imports",
            file="src/app.py",
            line=42,
            message="Duplicate import detected",
            severity=ViolationSeverity.WARNING,
        )
        assert v.category == "duplication"
        assert v.line == 42


class TestFix:
    def test_creation(self) -> None:
        v = Violation(category="dead_code", rule="unused-var", file="a.py")
        f = Fix(violation=v, applied=True, diff="- x = 1\n")
        assert f.applied is True


class TestCheckResult:
    def test_creation(self) -> None:
        v = Violation(category="security", rule="hardcoded-key", file="config.py")
        r = CheckResult(category="security", violations=(v,), files_scanned=10)
        assert len(r.violations) == 1
        assert r.files_scanned == 10


class TestSetupResult:
    def test_creation(self) -> None:
        r = SetupResult(layer="precommit", success=True, files_created=(".lefthook.yml",))
        assert r.success is True


class TestEnforcementReport:
    def test_totals(self) -> None:
        v1 = Violation(category="security", rule="r1", file="a.py")
        v2 = Violation(category="security", rule="r2", file="b.py")
        v3 = Violation(category="dead_code", rule="r3", file="c.py")

        report = EnforcementReport(
            project_id="p-001",
            results=[
                CheckResult(category="security", violations=(v1, v2), files_scanned=5),
                CheckResult(category="dead_code", violations=(v3,), files_scanned=3),
            ],
        )
        assert report.total_violations == 3
        assert report.total_files_scanned == 8

    def test_json_serialization(self) -> None:
        report = EnforcementReport(project_id="p-001", results=[])
        raw = report.to_json()
        data = json.loads(raw)
        assert data["project_id"] == "p-001"
        assert data["total_violations"] == 0

    def test_default_collected_at_is_utc(self) -> None:
        report = EnforcementReport(project_id="p-001")
        assert report.collected_at.tzinfo is not None


class TestWorkspaceStatus:
    def test_all_values(self) -> None:
        assert WorkspaceStatus.CREATING.value == "creating"
        assert WorkspaceStatus.READY.value == "ready"
        assert WorkspaceStatus.ACTIVE.value == "active"
        assert WorkspaceStatus.CLEANING.value == "cleaning"
        assert WorkspaceStatus.CLEANED.value == "cleaned"
        assert WorkspaceStatus.FAILED.value == "failed"
        assert len(WorkspaceStatus) == 6


class TestWorkspaceInfo:
    def test_creation(self) -> None:
        info = WorkspaceInfo(
            id="ws-001",
            project_name="myproject",
            session_id="s-001",
            workspace_dir=Path("/tmp/ws"),
            repository_url="https://github.com/user/repo.git",
            status=WorkspaceStatus.READY,
            branch="feat/workspace",
            clone_depth=1,
        )
        assert info.id == "ws-001"
        assert info.project_name == "myproject"
        assert info.session_id == "s-001"
        assert info.workspace_dir == Path("/tmp/ws")
        assert info.repository_url == "https://github.com/user/repo.git"
        assert info.status == WorkspaceStatus.READY
        assert info.branch == "feat/workspace"
        assert info.clone_depth == 1

    def test_status_is_mutable(self) -> None:
        info = WorkspaceInfo(
            id="ws-002",
            project_name="test",
            session_id="s-002",
            workspace_dir=Path("/tmp/ws2"),
            repository_url="https://github.com/user/repo.git",
            status=WorkspaceStatus.CREATING,
        )
        info.status = WorkspaceStatus.READY
        assert info.status == WorkspaceStatus.READY

    def test_default_created_at_is_utc(self) -> None:
        info = WorkspaceInfo(
            id="ws-003",
            project_name="test",
            session_id="s-003",
            workspace_dir=Path("/tmp/ws3"),
            repository_url="https://github.com/user/repo.git",
            status=WorkspaceStatus.CREATING,
        )
        assert info.created_at.tzinfo is not None

    def test_cleaned_at_defaults_to_none(self) -> None:
        info = WorkspaceInfo(
            id="ws-004",
            project_name="test",
            session_id="s-004",
            workspace_dir=Path("/tmp/ws4"),
            repository_url="https://github.com/user/repo.git",
            status=WorkspaceStatus.ACTIVE,
        )
        assert info.cleaned_at is None
