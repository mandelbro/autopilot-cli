"""Sprint planning with velocity tracking (Tasks 024 + 027).

Provides VelocityTracker for SQLite-backed sprint metrics and SprintPlanner
for capacity-based sprint planning per RFC Section 6 Phase 2.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autopilot.core.task import Task
    from autopilot.utils.db import Database

from autopilot.core.models import SprintResult

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FIBONACCI_POINTS = frozenset({1, 2, 3, 5, 8})
_WARNING_SYMBOLS = frozenset({"⚠️", "⚠", "warning", "?"})
_DEFAULT_CAPACITY = 13
_MIN_SPRINTS_FOR_FORECAST = 3
_ROLLING_WINDOW = 5


# ---------------------------------------------------------------------------
# Sprint dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Sprint:
    """A sprint containing a set of tasks with capacity constraints."""

    id: str
    start_date: datetime
    end_date: datetime
    tasks: list[str] = field(default_factory=list)
    capacity: int = 0
    points_planned: int = 0
    status: str = "planned"

    def __hash__(self) -> int:  # pragma: no cover
        return hash(self.id)


# ---------------------------------------------------------------------------
# Fibonacci estimation (Task 027)
# ---------------------------------------------------------------------------


def validate_sprint_points(points: int | str) -> int:
    """Validate and return Fibonacci sprint points.

    Accepts integer values in {1, 2, 3, 5, 8} or a warning symbol
    (returned as 0).  Raises ``ValueError`` for invalid numeric values.
    """
    if isinstance(points, str):
        stripped = points.strip()
        if stripped in _WARNING_SYMBOLS or not stripped:
            return 0
        try:
            numeric = int(stripped)
        except ValueError:
            return 0
        points = numeric

    if points == 0:
        return 0

    if points not in FIBONACCI_POINTS:
        msg = f"Sprint points must be one of {sorted(FIBONACCI_POINTS)}, got {points}"
        raise ValueError(msg)
    return points


# ---------------------------------------------------------------------------
# VelocityTracker
# ---------------------------------------------------------------------------


class VelocityTracker:
    """Records and queries sprint velocity backed by SQLite."""

    def __init__(self, db: Database, project_id: str) -> None:
        self._db = db
        self._project_id = project_id

    # -- writes --

    def record_sprint(self, sprint: SprintResult) -> None:
        """Persist a sprint result to the velocity table."""
        self._db.insert_velocity(
            project_id=self._project_id,
            sprint_id=sprint.sprint_id,
            started_at=sprint.started_at.isoformat() if sprint.started_at else None,
            ended_at=sprint.ended_at.isoformat() if sprint.ended_at else None,
            points_planned=sprint.points_planned,
            points_completed=sprint.points_completed,
            tasks_completed=sprint.tasks_completed,
            tasks_carried_over=sprint.tasks_carried_over,
        )

    # -- reads --

    def get_history(self) -> list[SprintResult]:
        """Return all sprint results for this project, oldest first."""
        conn = self._db.get_connection()
        try:
            rows = conn.execute(
                "SELECT sprint_id, started_at, ended_at, points_planned, "
                "points_completed, tasks_completed, tasks_carried_over "
                "FROM velocity WHERE project_id = ? ORDER BY rowid ASC",
                (self._project_id,),
            ).fetchall()
        finally:
            conn.close()

        results: list[SprintResult] = []
        for row in rows:
            results.append(
                SprintResult(
                    sprint_id=row[0],
                    started_at=datetime.fromisoformat(row[1]) if row[1] else datetime.now(UTC),
                    ended_at=datetime.fromisoformat(row[2]) if row[2] else None,
                    points_planned=row[3],
                    points_completed=row[4],
                    tasks_completed=row[5],
                    tasks_carried_over=row[6],
                )
            )
        return results

    def get_average_velocity(self, sprints: int = _ROLLING_WINDOW) -> float:
        """Return the average points completed over the last *sprints* sprints."""
        history = self.get_history()
        if not history:
            return 0.0
        recent = history[-sprints:]
        return sum(s.points_completed for s in recent) / len(recent)

    def get_velocity_trend(self) -> list[tuple[str, int]]:
        """Return (sprint_id, points_completed) pairs for charting."""
        history = self.get_history()
        return [(s.sprint_id, s.points_completed) for s in history]

    def forecast_capacity(self, team_size: int = 1) -> int:
        """Forecast sprint capacity using rolling average velocity.

        Returns *_DEFAULT_CAPACITY * team_size* when fewer than
        *_MIN_SPRINTS_FOR_FORECAST* sprints are recorded.
        """
        history = self.get_history()
        if len(history) < _MIN_SPRINTS_FOR_FORECAST:
            return _DEFAULT_CAPACITY * team_size

        recent = history[-_ROLLING_WINDOW:]
        avg = sum(s.points_completed for s in recent) / len(recent)
        return int(avg * team_size)


# ---------------------------------------------------------------------------
# Batch estimation helpers (Task 027)
# ---------------------------------------------------------------------------


def find_unestimated_tasks(tasks: list[Task]) -> list[Task]:
    """Return tasks whose sprint_points are 0 or a warning symbol."""
    unestimated: list[Task] = []
    for t in tasks:
        if isinstance(t.sprint_points, str) or t.sprint_points == 0:
            unestimated.append(t)
    return unestimated


# ---------------------------------------------------------------------------
# SprintPlanner
# ---------------------------------------------------------------------------


class SprintPlanner:
    """Plans and closes sprints with capacity constraints."""

    def __init__(self, db: Database, project_id: str) -> None:
        self._db = db
        self._project_id = project_id
        self._tracker = VelocityTracker(db, project_id)

    # -- public API --

    def plan_sprint(
        self,
        tasks: list[Task],
        capacity: int,
        *,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> Sprint:
        """Select pending tasks up to *capacity* and create a sprint.

        Tasks are selected in list order until adding the next task
        would exceed *capacity*.
        """
        now = datetime.now(UTC)
        selected_ids: list[str] = []
        total_points = 0

        for task in tasks:
            if task.complete:
                continue
            pts = task.sprint_points if isinstance(task.sprint_points, int) else 0
            if pts == 0:
                continue
            if total_points + pts > capacity:
                continue
            selected_ids.append(task.id)
            total_points += pts

        sprint = Sprint(
            id=uuid.uuid4().hex[:12],
            start_date=start_date or now,
            end_date=end_date or now,
            tasks=selected_ids,
            capacity=capacity,
            points_planned=total_points,
            status="active",
        )
        self._persist_sprint(sprint)
        return sprint

    def close_sprint(
        self,
        sprint_id: str,
        completed_task_ids: list[str] | None = None,
        all_tasks: list[Task] | None = None,
    ) -> SprintResult:
        """Close a sprint, recording velocity and computing carryover.

        If *completed_task_ids* is provided, only those tasks count as done.
        Otherwise falls back to checking the *all_tasks* completion status.
        """
        sprint = self.active_sprint()
        if sprint is None or sprint.id != sprint_id:
            msg = f"No active sprint with id '{sprint_id}'"
            raise ValueError(msg)

        completed_ids = set(completed_task_ids or [])

        # If we have the actual task objects, use their completion status
        if not completed_ids and all_tasks:
            task_map = {t.id: t for t in all_tasks}
            completed_ids = {
                tid for tid in sprint.tasks if tid in task_map and task_map[tid].complete
            }

        points_completed = 0
        tasks_completed = 0
        task_map = {t.id: t for t in all_tasks} if all_tasks else {}
        for tid in sprint.tasks:
            if tid in completed_ids:
                tasks_completed += 1
                if tid in task_map:
                    pts = task_map[tid].sprint_points
                    points_completed += pts if isinstance(pts, int) else 0

        carried_over = len(sprint.tasks) - tasks_completed

        result = SprintResult(
            sprint_id=sprint.id,
            started_at=sprint.start_date,
            ended_at=datetime.now(UTC),
            points_planned=sprint.points_planned,
            points_completed=points_completed,
            tasks_completed=tasks_completed,
            tasks_carried_over=carried_over,
        )

        self._tracker.record_sprint(result)
        self._delete_sprint(sprint_id)
        return result

    def active_sprint(self) -> Sprint | None:
        """Return the current active sprint from SQLite, or None."""
        return self._load_active_sprint()

    # -- persistence helpers --

    def _persist_sprint(self, sprint: Sprint) -> None:
        """Save the sprint to SQLite."""
        conn = self._db.get_connection()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO sprints "
                "(id, project_id, start_date, end_date, tasks, capacity, points_planned, status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    sprint.id,
                    self._project_id,
                    sprint.start_date.isoformat(),
                    sprint.end_date.isoformat(),
                    json.dumps(sprint.tasks),
                    sprint.capacity,
                    sprint.points_planned,
                    sprint.status,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def _load_active_sprint(self) -> Sprint | None:
        """Load the active sprint from SQLite."""
        conn = self._db.get_connection()
        try:
            row = conn.execute(
                "SELECT id, start_date, end_date, tasks, capacity, points_planned, status "
                "FROM sprints WHERE project_id = ? AND status = 'active' LIMIT 1",
                (self._project_id,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        return Sprint(
            id=row[0],
            start_date=datetime.fromisoformat(row[1]),
            end_date=datetime.fromisoformat(row[2]) if row[2] else datetime.now(UTC),
            tasks=json.loads(row[3]),
            capacity=row[4],
            points_planned=row[5],
            status=row[6],
        )

    def _delete_sprint(self, sprint_id: str) -> None:
        """Remove a sprint from SQLite after closing."""
        conn = self._db.get_connection()
        try:
            conn.execute("DELETE FROM sprints WHERE id = ?", (sprint_id,))
            conn.commit()
        finally:
            conn.close()

    @property
    def velocity_tracker(self) -> VelocityTracker:
        """Access the underlying velocity tracker."""
        return self._tracker
