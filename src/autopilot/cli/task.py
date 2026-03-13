"""Task management CLI commands (Tasks 022-023).

Provides ``task create`` (interactive task creation) and ``task list`` / ``task board``
commands with Rich table output, filtering, and summary statistics.
"""

from __future__ import annotations

import re
from pathlib import Path

import typer

from autopilot.cli.display import (
    console,
    format_sprint_points,
    format_status,
    notification,
)
from autopilot.core.task import Task, TaskIndex, TaskParser

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FIBONACCI_POINTS = {1, 2, 3, 5, 8}
MAX_TASKS_PER_FILE = 10


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_task_dir() -> Path:
    """Return the tasks/ directory relative to cwd."""
    return Path.cwd() / "tasks"


def validate_fibonacci(value: int) -> int:
    """Validate that sprint points are on the Fibonacci scale."""
    if value not in FIBONACCI_POINTS:
        msg = f"Sprint points must be one of {sorted(FIBONACCI_POINTS)}, got {value}"
        raise typer.BadParameter(msg)
    return value


def _get_all_tasks(parser: TaskParser, task_dir: Path) -> list[Task]:
    """Parse all task files referenced by the index and return a flat list."""
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


def _next_task_id(index: TaskIndex) -> str:
    """Compute the next sequential task ID (zero-padded to 3 digits)."""
    return f"{index.total_tasks + 1:03d}"


def _target_task_file(task_dir: Path, index: TaskIndex) -> tuple[Path, bool]:
    """Determine which task file to append to.

    Returns (path, is_new_file). Creates a new file when the last file has
    reached *MAX_TASKS_PER_FILE* tasks.
    """
    if not index.file_index:
        return task_dir / "tasks-1.md", True

    last_entry = index.file_index[-1]
    if last_entry.task_count >= MAX_TASKS_PER_FILE:
        # Derive new file number
        m = re.search(r"tasks-(\d+)", last_entry.file)
        next_num = (int(m.group(1)) + 1) if m else len(index.file_index) + 1
        return task_dir / f"tasks-{next_num}.md", True

    return task_dir / last_entry.file, False


def _render_task_markdown(
    task_id: str,
    title: str,
    file_path: str,
    user_story: str,
    outcome: str,
    sprint_points: int,
    prompt_text: str,
) -> str:
    """Render a single task block in the standard markdown format."""
    lines = [
        f"### Task ID: {task_id}",
        "",
        f"- **Title**: {title}",
        f"- **File**: {file_path}",
        "- **Complete**: [ ]",
        f"- **Sprint Points**: {sprint_points}",
        "",
        f"- **User Story (business-facing)**: {user_story}",
        f"- **Outcome (what this delivers)**: {outcome}",
        "",
        "#### Prompt:",
        "",
        "```markdown",
        prompt_text if prompt_text else f"**Objective:** {title}",
        "```",
    ]
    return "\n".join(lines)


def _new_task_file_header(file_name: str, task_id: str, points: int) -> str:
    """Generate the header for a brand-new tasks-N.md file."""
    return (
        f"## Summary ({file_name})\n"
        f"\n"
        f"- **Tasks in this file**: 1\n"
        f"- **Task IDs**: {task_id} - {task_id}\n"
        f"- **Total Points**: {points}\n"
        f"\n"
        f"---\n"
        f"\n"
        f"## Tasks\n"
    )


def _append_task_to_file(
    task_file: Path,
    is_new: bool,
    task_md: str,
    task_id: str,
    points: int,
) -> None:
    """Append a task to an existing or new task file, updating the local summary."""
    if is_new:
        content = _new_task_file_header(task_file.name, task_id, points)
        content += f"\n{task_md}\n"
        task_file.write_text(content, encoding="utf-8")
        return

    text = task_file.read_text(encoding="utf-8")

    # Update local summary counters
    text = re.sub(
        r"(\*\*Tasks in this file\*\*:\s*)(\d+)",
        lambda m: f"{m.group(1)}{int(m.group(2)) + 1}",
        text,
        count=1,
    )
    text = re.sub(
        r"(\*\*Task IDs\*\*:\s*\S+\s*-\s*)(\S+)",
        lambda m: f"{m.group(1)}{task_id}",
        text,
        count=1,
    )
    text = re.sub(
        r"(\*\*Total Points\*\*:\s*)(\d+)",
        lambda m: f"{m.group(1)}{int(m.group(2)) + points}",
        text,
        count=1,
    )

    # Append the task block
    if not text.endswith("\n"):
        text += "\n"
    text += f"\n---\n\n{task_md}\n"
    task_file.write_text(text, encoding="utf-8")


def _update_index_for_new_task(
    index_path: Path,
    task_file: Path,
    task_id: str,
    points: int,
    is_new_file: bool,
) -> None:
    """Update tasks-index.md after adding a new task."""
    text = index_path.read_text(encoding="utf-8")

    # Increment Total Tasks
    text = re.sub(
        r"(\*\*Total Tasks\*\*:\s*)(\d+)",
        lambda m: f"{m.group(1)}{int(m.group(2)) + 1}",
        text,
        count=1,
    )
    # Increment Pending
    text = re.sub(
        r"(\*\*Pending\*\*:\s*)(\d+)",
        lambda m: f"{m.group(1)}{int(m.group(2)) + 1}",
        text,
        count=1,
    )
    # Increment Total Points
    text = re.sub(
        r"(\*\*Total Points\*\*:\s*)(\d+)",
        lambda m: f"{m.group(1)}{int(m.group(2)) + points}",
        text,
        count=1,
    )

    if is_new_file:
        # Add a new entry to the file index
        new_entry = (
            f"- `tasks/{task_file.name}`: Contains Tasks {task_id} - {task_id}"
            f" (1 tasks, {points} points)"
        )
        # Insert before blank lines at end or after last index entry
        lines = text.split("\n")
        insert_idx = len(lines)
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip().startswith("- `tasks/tasks-"):
                insert_idx = i + 1
                break
        lines.insert(insert_idx, new_entry)
        text = "\n".join(lines)
    else:
        # Update the last file index entry's task count, end_id, and points
        file_name = task_file.name

        def _update_entry(m: re.Match[str]) -> str:
            old_count = int(m.group(2))
            old_points = int(m.group(3))
            return (
                f"- `tasks/{file_name}`: Contains Tasks {m.group(1)} - {task_id}"
                f" ({old_count + 1} tasks, {old_points + points} points)"
            )

        pattern = (
            rf"- `tasks/{re.escape(file_name)}`:\s*Contains\s+Tasks?\s+(\S+)\s*-\s*\S+"
            rf"\s*\((\d+)\s+tasks?,\s*(\d+)\s+points?\)"
        )
        text = re.sub(pattern, _update_entry, text, count=1)

    index_path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI Commands
# ---------------------------------------------------------------------------


def register_task_commands(task_app: typer.Typer) -> None:
    """Register all task subcommands on the given Typer app."""

    @task_app.command("create")
    def task_create(
        title: str | None = typer.Option(None, "--title", "-t", help="Task title."),
        file: str | None = typer.Option(None, "--file", "-f", help="Target file path."),
        points: int | None = typer.Option(
            None, "--points", "-p", help="Sprint points (1,2,3,5,8)."
        ),
        user_story: str | None = typer.Option(None, "--user-story", help="User story text."),
        outcome: str | None = typer.Option(None, "--outcome", help="Outcome description."),
        prompt_text: str | None = typer.Option(None, "--prompt", help="Task prompt text."),
    ) -> None:
        """Create a new task interactively or via flags."""
        task_dir = _resolve_task_dir()
        index_path = task_dir / "tasks-index.md"

        if not index_path.exists():
            notification("error", f"Task index not found: {index_path}")
            raise typer.Exit(code=1)

        parser = TaskParser()
        index = parser.parse_task_index(index_path)

        # Collect fields — prompt interactively when not provided via flags
        final_title = title or typer.prompt("Task title")
        final_file = file or typer.prompt("Target file path")
        final_user_story = user_story or typer.prompt("User story")
        final_outcome = outcome or typer.prompt("Outcome")
        final_prompt = prompt_text or typer.prompt("Prompt text (brief objective)", default="")

        if points is not None:
            final_points = validate_fibonacci(points)
        else:
            raw_points = typer.prompt("Sprint points (1,2,3,5,8)", type=int, default=3)
            final_points = validate_fibonacci(raw_points)

        # Determine task ID and target file
        task_id = _next_task_id(index)
        target_file, is_new = _target_task_file(task_dir, index)

        # Render and write
        task_md = _render_task_markdown(
            task_id=task_id,
            title=final_title,
            file_path=final_file,
            user_story=final_user_story,
            outcome=final_outcome,
            sprint_points=final_points,
            prompt_text=final_prompt,
        )

        _append_task_to_file(target_file, is_new, task_md, task_id, final_points)
        _update_index_for_new_task(index_path, target_file, task_id, final_points, is_new)

        # Summary output
        notification("success", f"Created Task {task_id}: {final_title}")
        from rich.table import Table

        summary = Table(title=f"Task {task_id}", width=80)
        summary.add_column("Field", style="bold", width=16)
        summary.add_column("Value")
        summary.add_row("ID", task_id)
        summary.add_row("Title", final_title)
        summary.add_row("File", final_file)
        summary.add_row("Points", format_sprint_points(final_points))
        summary.add_row("User Story", final_user_story)
        summary.add_row("Outcome", final_outcome)
        summary.add_row("Task File", target_file.name)
        console.print(summary)

    @task_app.command("list")
    def task_list(
        status: str = typer.Option(
            "all",
            "--status",
            "-s",
            help="Filter by status: pending, complete, all.",
        ),
        verbose: bool = typer.Option(False, "--verbose", "-v", help="Show user stories."),
    ) -> None:
        """List tasks with Rich table display."""
        _render_task_list(status=status, verbose=verbose)

    @task_app.command("board")
    def task_board_cmd(
        status: str = typer.Option(
            "all",
            "--status",
            "-s",
            help="Filter by status: pending, complete, all.",
        ),
        verbose: bool = typer.Option(False, "--verbose", "-v", help="Show user stories."),
    ) -> None:
        """Display the task board (alias for list)."""
        _render_task_list(status=status, verbose=verbose)


def _render_task_list(*, status: str, verbose: bool) -> None:
    """Shared implementation for task list and task board commands."""
    from rich.table import Table

    task_dir = _resolve_task_dir()
    index_path = task_dir / "tasks-index.md"

    if not index_path.exists():
        notification("error", f"Task index not found: {index_path}")
        raise typer.Exit(code=1)

    parser = TaskParser()
    index = parser.parse_task_index(index_path)
    all_tasks = _get_all_tasks(parser, task_dir)
    next_pending = parser.find_next_pending(task_dir)

    # Apply status filter
    if status.lower() == "pending":
        filtered = [t for t in all_tasks if not t.complete]
    elif status.lower() == "complete":
        filtered = [t for t in all_tasks if t.complete]
    else:
        filtered = all_tasks

    # Build table
    table = Table(title="Task Board", width=80)
    table.add_column("ID", width=6)
    table.add_column("Title", ratio=3)
    table.add_column("File", ratio=2, style="dim")
    table.add_column("Pts", width=4, justify="right")
    table.add_column("Status", width=10)
    if verbose:
        table.add_column("User Story", ratio=3)

    for task in filtered:
        task_status = "Complete" if task.complete else "Pending"
        is_next = next_pending is not None and task.id == next_pending.id
        style = "bold cyan" if is_next else ""
        id_display = f">{task.id}" if is_next else task.id

        row: list[str] = [
            id_display,
            task.title,
            task.file_path,
            format_sprint_points(task.sprint_points),
            format_status(task_status),
        ]
        if verbose:
            row.append(task.user_story or "")

        table.add_row(*row, style=style)

    console.print(table)

    # Summary line
    total = len(all_tasks)
    complete_count = sum(1 for t in all_tasks if t.complete)
    pending_count = total - complete_count
    console.print(
        f"\n[bold]Summary:[/bold] {total} tasks, "
        f"[success]{complete_count} complete[/success], "
        f"[warning]{pending_count} pending[/warning], "
        f"{index.total_points} total points, "
        f"{index.points_complete} points complete"
    )

    # Progress bar (simple text-based)
    if total > 0:
        pct = complete_count / total * 100
        bar_len = 40
        filled = int(bar_len * complete_count / total)
        bar = "#" * filled + "-" * (bar_len - filled)
        console.print(f"Progress: [{bar}] {pct:.0f}%")
