"""Tests for core data models (Task 003)."""

from __future__ import annotations

import json
from datetime import datetime

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
        try:
            d.agent = "other"  # type: ignore[misc]
            raise AssertionError("Should be frozen")
        except AttributeError:
            pass


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
