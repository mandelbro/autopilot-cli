"""Tests for sprint planning and velocity tracking (Tasks 024 + 027)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path  # noqa: TC003 — used at runtime

import pytest

from autopilot.core.models import SprintResult
from autopilot.core.sprint import (
    Sprint,
    SprintPlanner,
    VelocityTracker,
    find_unestimated_tasks,
    validate_sprint_points,
)
from autopilot.core.task import Task
from autopilot.utils.db import Database

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    """Create a fresh in-tmp database."""
    db = Database(tmp_path / "test.db")
    # Insert a dummy project (FK constraint)
    db.insert_project(id="proj-1", name="test", path="/tmp/test", type="python")
    return db


@pytest.fixture()
def tracker(db: Database) -> VelocityTracker:
    return VelocityTracker(db, "proj-1")


@pytest.fixture()
def planner(db: Database) -> SprintPlanner:
    return SprintPlanner(db, "proj-1")


def _make_sprint_result(
    sprint_id: str = "s1",
    points_planned: int = 13,
    points_completed: int = 10,
    tasks_completed: int = 3,
    tasks_carried_over: int = 1,
) -> SprintResult:
    return SprintResult(
        sprint_id=sprint_id,
        started_at=datetime.now(UTC),
        ended_at=datetime.now(UTC),
        points_planned=points_planned,
        points_completed=points_completed,
        tasks_completed=tasks_completed,
        tasks_carried_over=tasks_carried_over,
    )


def _sample_tasks() -> list[Task]:
    """Return a list of sample tasks for planning tests."""
    return [
        Task(id="001", title="Task A", sprint_points=3, complete=False),
        Task(id="002", title="Task B", sprint_points=5, complete=False),
        Task(id="003", title="Task C", sprint_points=2, complete=False),
        Task(id="004", title="Task D", sprint_points=8, complete=False),
        Task(id="005", title="Task E", sprint_points=1, complete=True),
    ]


# ---------------------------------------------------------------------------
# Tests: validate_sprint_points (Task 027)
# ---------------------------------------------------------------------------


class TestValidateSprintPoints:
    @pytest.mark.parametrize("pts", [1, 2, 3, 5, 8])
    def test_valid_fibonacci(self, pts: int) -> None:
        assert validate_sprint_points(pts) == pts

    def test_zero_is_valid(self) -> None:
        assert validate_sprint_points(0) == 0

    @pytest.mark.parametrize("pts", [4, 6, 7, 10, 13])
    def test_invalid_raises(self, pts: int) -> None:
        with pytest.raises(ValueError, match="Sprint points must be"):
            validate_sprint_points(pts)

    def test_warning_symbol_returns_zero(self) -> None:
        assert validate_sprint_points("⚠️") == 0

    def test_warning_text_returns_zero(self) -> None:
        assert validate_sprint_points("warning") == 0

    def test_string_numeric_valid(self) -> None:
        assert validate_sprint_points("5") == 5

    def test_string_numeric_invalid(self) -> None:
        with pytest.raises(ValueError, match="Sprint points must be"):
            validate_sprint_points("4")

    def test_empty_string_returns_zero(self) -> None:
        assert validate_sprint_points("") == 0


# ---------------------------------------------------------------------------
# Tests: find_unestimated_tasks (Task 027)
# ---------------------------------------------------------------------------


class TestFindUnestimatedTasks:
    def test_finds_zero_point_tasks(self) -> None:
        tasks = [
            Task(id="1", title="A", sprint_points=3),
            Task(id="2", title="B", sprint_points=0),
            Task(id="3", title="C", sprint_points="⚠️"),
        ]
        unest = find_unestimated_tasks(tasks)
        assert len(unest) == 2
        assert unest[0].id == "2"
        assert unest[1].id == "3"

    def test_all_estimated(self) -> None:
        tasks = [
            Task(id="1", title="A", sprint_points=3),
            Task(id="2", title="B", sprint_points=5),
        ]
        assert find_unestimated_tasks(tasks) == []


# ---------------------------------------------------------------------------
# Tests: Sprint dataclass
# ---------------------------------------------------------------------------


class TestSprintModel:
    def test_defaults(self) -> None:
        now = datetime.now(UTC)
        s = Sprint(id="s1", start_date=now, end_date=now)
        assert s.status == "planned"
        assert s.tasks == []
        assert s.capacity == 0

    def test_frozen(self) -> None:
        now = datetime.now(UTC)
        s = Sprint(id="s1", start_date=now, end_date=now)
        with pytest.raises(AttributeError):
            s.id = "s2"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Tests: VelocityTracker
# ---------------------------------------------------------------------------


class TestVelocityTracker:
    def test_record_and_retrieve(self, tracker: VelocityTracker) -> None:
        tracker.record_sprint(_make_sprint_result("s1", points_completed=10))
        history = tracker.get_history()
        assert len(history) == 1
        assert history[0].sprint_id == "s1"
        assert history[0].points_completed == 10

    def test_get_average_velocity(self, tracker: VelocityTracker) -> None:
        for i, pts in enumerate([8, 10, 12, 14, 16]):
            tracker.record_sprint(_make_sprint_result(f"s{i}", points_completed=pts))
        avg = tracker.get_average_velocity()
        assert avg == 12.0

    def test_get_average_velocity_empty(self, tracker: VelocityTracker) -> None:
        assert tracker.get_average_velocity() == 0.0

    def test_get_average_velocity_subset(self, tracker: VelocityTracker) -> None:
        for i, pts in enumerate([5, 10, 15, 20]):
            tracker.record_sprint(_make_sprint_result(f"s{i}", points_completed=pts))
        # Last 2 sprints: 15, 20 -> avg 17.5
        assert tracker.get_average_velocity(sprints=2) == 17.5

    def test_velocity_trend(self, tracker: VelocityTracker) -> None:
        tracker.record_sprint(_make_sprint_result("s1", points_completed=8))
        tracker.record_sprint(_make_sprint_result("s2", points_completed=13))
        trend = tracker.get_velocity_trend()
        assert trend == [("s1", 8), ("s2", 13)]

    def test_forecast_default_when_few_sprints(self, tracker: VelocityTracker) -> None:
        tracker.record_sprint(_make_sprint_result("s1", points_completed=10))
        assert tracker.forecast_capacity() == 13  # default

    def test_forecast_default_team_size(self, tracker: VelocityTracker) -> None:
        tracker.record_sprint(_make_sprint_result("s1", points_completed=10))
        assert tracker.forecast_capacity(team_size=2) == 26

    def test_forecast_with_enough_data(self, tracker: VelocityTracker) -> None:
        for i in range(5):
            tracker.record_sprint(_make_sprint_result(f"s{i}", points_completed=10))
        assert tracker.forecast_capacity() == 10

    def test_forecast_rounds_down(self, tracker: VelocityTracker) -> None:
        # 2 sprints is below the 3-sprint minimum
        for i, pts in enumerate([9, 11]):
            tracker.record_sprint(_make_sprint_result(f"s{i}", points_completed=pts))
        assert tracker.forecast_capacity() == 13  # <3 sprints, uses default

    def test_forecast_with_three_sprints(self, tracker: VelocityTracker) -> None:
        for i, pts in enumerate([9, 10, 11]):
            tracker.record_sprint(_make_sprint_result(f"s{i}", points_completed=pts))
        # 3 sprints = exactly min threshold, so forecast is used
        assert tracker.forecast_capacity() == 10  # int(avg of 9,10,11) = 10


# ---------------------------------------------------------------------------
# Tests: SprintPlanner
# ---------------------------------------------------------------------------


class TestSprintPlanner:
    def test_plan_sprint_respects_capacity(self, planner: SprintPlanner) -> None:
        tasks = _sample_tasks()
        sprint = planner.plan_sprint(tasks, capacity=10)
        assert sprint.points_planned <= 10
        assert sprint.status == "active"
        assert len(sprint.tasks) > 0

    def test_plan_sprint_selects_correct_tasks(self, planner: SprintPlanner) -> None:
        tasks = _sample_tasks()
        sprint = planner.plan_sprint(tasks, capacity=10)
        # Task A (3) + Task B (5) + Task C (2) = 10, Task D (8) skipped, Task E complete
        assert "001" in sprint.tasks
        assert "002" in sprint.tasks
        assert "003" in sprint.tasks
        assert "005" not in sprint.tasks  # complete, skipped

    def test_plan_sprint_skips_complete_tasks(self, planner: SprintPlanner) -> None:
        tasks = _sample_tasks()
        sprint = planner.plan_sprint(tasks, capacity=100)
        assert "005" not in sprint.tasks

    def test_plan_sprint_skips_zero_point_tasks(self, planner: SprintPlanner) -> None:
        tasks = [Task(id="001", title="No points", sprint_points=0)]
        sprint = planner.plan_sprint(tasks, capacity=10)
        assert sprint.tasks == []
        assert sprint.points_planned == 0

    def test_active_sprint(self, planner: SprintPlanner) -> None:
        assert planner.active_sprint() is None
        tasks = _sample_tasks()
        sprint = planner.plan_sprint(tasks, capacity=10)
        assert planner.active_sprint() is not None
        assert planner.active_sprint() == sprint

    def test_close_sprint(self, planner: SprintPlanner) -> None:
        tasks = _sample_tasks()
        sprint = planner.plan_sprint(tasks, capacity=10)

        # Mark task A as complete
        completed_tasks = [
            Task(id="001", title="Task A", sprint_points=3, complete=True),
            Task(id="002", title="Task B", sprint_points=5, complete=False),
            Task(id="003", title="Task C", sprint_points=2, complete=False),
        ]

        result = planner.close_sprint(
            sprint.id,
            completed_task_ids=["001"],
            all_tasks=completed_tasks,
        )

        assert result.points_completed == 3
        assert result.tasks_completed == 1
        assert result.tasks_carried_over == 2
        assert planner.active_sprint() is None

    def test_close_sprint_records_velocity(self, planner: SprintPlanner) -> None:
        tasks = _sample_tasks()
        sprint = planner.plan_sprint(tasks, capacity=10)

        completed_tasks = [
            Task(id="001", title="Task A", sprint_points=3, complete=True),
            Task(id="002", title="Task B", sprint_points=5, complete=True),
            Task(id="003", title="Task C", sprint_points=2, complete=True),
        ]
        planner.close_sprint(
            sprint.id,
            completed_task_ids=["001", "002", "003"],
            all_tasks=completed_tasks,
        )

        history = planner.velocity_tracker.get_history()
        assert len(history) == 1
        assert history[0].points_completed == 10

    def test_close_nonexistent_sprint_raises(self, planner: SprintPlanner) -> None:
        with pytest.raises(ValueError, match="No active sprint"):
            planner.close_sprint("nonexistent")

    def test_close_sprint_with_ids_only(self, planner: SprintPlanner) -> None:
        """Closing with completed_task_ids but no all_tasks must still count correctly."""
        tasks = _sample_tasks()
        sprint = planner.plan_sprint(tasks, capacity=10)

        # Pass only IDs, no task objects
        result = planner.close_sprint(sprint.id, completed_task_ids=["001", "003"])
        assert result.tasks_completed == 2
        assert result.tasks_carried_over == 1
        # Points unknown without task objects, so 0 is acceptable
        assert result.points_completed == 0

    def test_close_sprint_auto_detects_completion(self, planner: SprintPlanner) -> None:
        tasks = _sample_tasks()
        sprint = planner.plan_sprint(tasks, capacity=10)

        # Pass all_tasks with completion status, no explicit completed_task_ids
        completed_tasks = [
            Task(id="001", title="Task A", sprint_points=3, complete=True),
            Task(id="002", title="Task B", sprint_points=5, complete=True),
            Task(id="003", title="Task C", sprint_points=2, complete=False),
        ]
        result = planner.close_sprint(sprint.id, all_tasks=completed_tasks)
        assert result.points_completed == 8
        assert result.tasks_completed == 2
        assert result.tasks_carried_over == 1
