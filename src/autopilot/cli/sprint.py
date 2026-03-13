"""Sprint planning and closing CLI commands (Task 026).

Provides ``task sprint plan`` and ``task sprint close`` subcommands
using the core SprintPlanner/VelocityTracker from sprint.py.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from autopilot.cli.display import (
    console,
    format_sprint_points,
    format_status,
    notification,
)
from autopilot.core.sprint import SprintPlanner, VelocityTracker
from autopilot.core.task import Task, TaskParser
from autopilot.utils.db import Database

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DEFAULT_TASK_DIR = "tasks"
_DEFAULT_DB_PATH = ".autopilot/autopilot.db"
_DEFAULT_PROJECT_ID = "default"


def _get_pending_tasks(parser: TaskParser, task_dir: Path) -> list[Task]:
    """Return all pending tasks with valid sprint points, in file order."""
    index_path = task_dir / "tasks-index.md"
    if not index_path.exists():
        return []
    index = parser.parse_task_index(index_path)
    pending: list[Task] = []
    for entry in index.file_index:
        file_path = task_dir / entry.file
        if file_path.exists():
            for t in parser.parse_task_file(file_path):
                if not t.complete:
                    pending.append(t)
    return pending


def _get_all_tasks(parser: TaskParser, task_dir: Path) -> list[Task]:
    """Return all tasks from all task files."""
    index_path = task_dir / "tasks-index.md"
    if not index_path.exists():
        return []
    index = parser.parse_task_index(index_path)
    all_tasks: list[Task] = []
    for entry in index.file_index:
        file_path = task_dir / entry.file
        if file_path.exists():
            all_tasks.extend(parser.parse_task_file(file_path))
    return all_tasks


# ---------------------------------------------------------------------------
# CLI Registration
# ---------------------------------------------------------------------------


def register_sprint_commands(sprint_app: typer.Typer) -> None:
    """Register sprint plan/close subcommands on the given Typer app."""

    @sprint_app.command("plan")
    def sprint_plan(
        task_dir: str = typer.Option(
            _DEFAULT_TASK_DIR, "--task-dir", help="Path to tasks directory."
        ),
        db_path: str = typer.Option(_DEFAULT_DB_PATH, "--db-path", help="Path to SQLite database."),
        project_id: str = typer.Option(
            _DEFAULT_PROJECT_ID, "--project-id", help="Project identifier."
        ),
    ) -> None:
        """Plan a new sprint based on velocity forecast."""
        task_path = Path(task_dir)
        index_path = task_path / "tasks-index.md"
        if not index_path.exists():
            notification("error", f"Task index not found: {index_path}")
            raise typer.Exit(code=1)

        db = Database(Path(db_path))
        tracker = VelocityTracker(db, project_id)
        planner = SprintPlanner(db, project_id)
        parser = TaskParser()

        # Velocity forecast
        capacity = tracker.forecast_capacity()
        avg_velocity = tracker.get_average_velocity()

        console.print("\n[bold]Sprint Planning[/bold]\n")

        # Show velocity info
        info_table = Table(title="Velocity Forecast", width=80)
        info_table.add_column("Metric", style="bold", width=30)
        info_table.add_column("Value", width=20)
        info_table.add_row("Average Velocity", f"{avg_velocity:.1f} pts/sprint")
        info_table.add_row("Recommended Capacity", f"{capacity} points")
        console.print(info_table)

        # Get pending tasks
        pending = _get_pending_tasks(parser, task_path)
        if not pending:
            notification("warning", "No pending tasks found.")
            raise typer.Exit()

        # Show pending tasks
        console.print("\n[bold]Available Pending Tasks[/bold]\n")
        pending_table = Table(title="Pending Tasks", width=80)
        pending_table.add_column("ID", width=6)
        pending_table.add_column("Title", ratio=3)
        pending_table.add_column("File", ratio=2, style="dim")
        pending_table.add_column("Pts", width=4, justify="right")
        pending_table.add_column("Status", width=10)

        for task in pending:
            pending_table.add_row(
                task.id,
                task.title,
                task.file_path,
                format_sprint_points(task.sprint_points),
                format_status("Pending"),
            )
        console.print(pending_table)

        # Auto-select tasks up to capacity
        sprint = planner.plan_sprint(pending, capacity)

        # Display selected tasks
        console.print(f"\n[bold]Sprint Plan (capacity: {capacity} pts)[/bold]\n")
        selected_table = Table(title="Selected Tasks", width=80)
        selected_table.add_column("ID", width=6)
        selected_table.add_column("Title", ratio=3)
        selected_table.add_column("Pts", width=4, justify="right")

        task_map = {t.id: t for t in pending}
        for tid in sprint.tasks:
            t = task_map.get(tid)
            if t:
                selected_table.add_row(
                    t.id,
                    t.title,
                    format_sprint_points(t.sprint_points),
                )
        console.print(selected_table)

        # Capacity warning
        if sprint.points_planned > capacity:
            notification(
                "warning",
                f"Sprint is over capacity: {sprint.points_planned}/{capacity} points",
            )
        else:
            notification(
                "success",
                f"Sprint planned: {sprint.points_planned}/{capacity} points, "
                f"{len(sprint.tasks)} tasks (ID: {sprint.id})",
            )

    @sprint_app.command("close")
    def sprint_close(
        sprint_id: str = typer.Option(..., "--sprint-id", help="Sprint ID to close."),
        completed: str = typer.Option(
            "",
            "--completed",
            help="Comma-separated task IDs that were completed.",
        ),
        task_dir: str = typer.Option(
            _DEFAULT_TASK_DIR, "--task-dir", help="Path to tasks directory."
        ),
        db_path: str = typer.Option(_DEFAULT_DB_PATH, "--db-path", help="Path to SQLite database."),
        project_id: str = typer.Option(
            _DEFAULT_PROJECT_ID, "--project-id", help="Project identifier."
        ),
    ) -> None:
        """Close a sprint and record velocity."""
        task_path = Path(task_dir)
        db = Database(Path(db_path))
        planner = SprintPlanner(db, project_id)
        parser = TaskParser()

        # Check for active sprint
        active = planner.active_sprint()
        if active is None or active.id != sprint_id:
            notification("error", f"No active sprint with ID '{sprint_id}'.")
            raise typer.Exit(code=1)

        # Parse completed task IDs
        completed_ids = [c.strip() for c in completed.split(",") if c.strip()]

        # Get all tasks for point calculations
        all_tasks = _get_all_tasks(parser, task_path)

        # Close the sprint
        result = planner.close_sprint(
            sprint_id,
            completed_task_ids=completed_ids if completed_ids else None,
            all_tasks=all_tasks,
        )

        # Display summary
        console.print("\n[bold]Sprint Summary[/bold]\n")
        summary_table = Table(title=f"Sprint {sprint_id}", width=80)
        summary_table.add_column("Metric", style="bold", width=30)
        summary_table.add_column("Value", width=20)
        summary_table.add_row("Points Planned", str(result.points_planned))
        summary_table.add_row("Points Completed", str(result.points_completed))
        summary_table.add_row("Tasks Completed", str(result.tasks_completed))
        summary_table.add_row("Tasks Carried Over", str(result.tasks_carried_over))
        console.print(summary_table)

        # Show carryover tasks
        if result.tasks_carried_over > 0:
            completed_set = set(completed_ids)
            carryover = [tid for tid in active.tasks if tid not in completed_set]
            if carryover:
                console.print("\n[bold]Carryover Tasks[/bold]\n")
                task_map = {t.id: t for t in all_tasks}
                carry_table = Table(title="Carried Over", width=80)
                carry_table.add_column("ID", width=6)
                carry_table.add_column("Title", ratio=3)
                carry_table.add_column("Pts", width=4, justify="right")
                for tid in carryover:
                    t = task_map.get(tid)
                    if t:
                        carry_table.add_row(
                            t.id,
                            t.title,
                            format_sprint_points(t.sprint_points),
                        )
                console.print(carry_table)

        notification(
            "success",
            f"Sprint {sprint_id} closed. Velocity recorded: "
            f"{result.points_completed}/{result.points_planned} points.",
        )
