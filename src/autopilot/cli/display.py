"""Rich display helpers for consistent CLI output (UX Design Sections 4, 7, 9).

Provides reusable formatting utilities for tables, panels, progress bars,
status indicators, and notifications. All output targets 80-column width.
"""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table
from rich.theme import Theme

# Color constants per UX Design Section 9
_THEME = Theme(
    {
        "success": "green",
        "warning": "yellow",
        "error": "red",
        "info": "blue",
        "muted": "dim",
        "points.low": "green",
        "points.mid": "yellow",
        "points.high": "red",
        "status.running": "blue",
        "status.completed": "green",
        "status.failed": "red",
        "status.paused": "yellow",
    }
)

# Singleton console with 80-column width constraint
console = Console(theme=_THEME, width=80)


def project_table(projects: list[dict[str, Any]]) -> Table:
    """Build a Rich table for project listing."""
    table = Table(title="Projects", width=80)
    table.add_column("Name", style="bold")
    table.add_column("Type")
    table.add_column("Path", style="dim")
    for p in projects:
        table.add_row(
            str(p.get("name", "")),
            str(p.get("type", "")),
            str(p.get("path", "")),
        )
    return table


def task_board(tasks: list[dict[str, Any]], *, filter_status: str = "") -> Table:
    """Build a Rich table for the task board display."""
    table = Table(title="Task Board", width=80)
    table.add_column("ID", width=6)
    table.add_column("Title", ratio=3)
    table.add_column("Status", width=12)
    table.add_column("Pts", width=4, justify="right")
    for t in tasks:
        status = str(t.get("status", ""))
        if filter_status and status.lower() != filter_status.lower():
            continue
        table.add_row(
            str(t.get("id", "")),
            str(t.get("title", "")),
            format_status(status),
            format_sprint_points(t.get("points", 0)),
        )
    return table


def status_panel(title: str, content: str, status: str = "info") -> Panel:
    """Build a Rich panel with status-appropriate styling."""
    style = f"status.{status}" if status in ("running", "completed", "failed", "paused") else status
    return Panel(content, title=title, border_style=style, width=80)


def progress_bar(description: str = "", total: int = 0) -> Progress:
    """Create a Rich progress bar and pre-add a task.

    Returns a ``Progress`` instance with one task already added. The caller
    should enter the context manager and call ``progress.update(task_id, advance=N)``.
    """
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    )
    progress.add_task(description, total=total)
    return progress


def format_sprint_points(points: int | Any) -> str:
    """Format sprint points with color coding."""
    try:
        pts = int(points)
    except (TypeError, ValueError):
        return "[muted]?[/muted]"
    if pts <= 2:
        return f"[points.low]{pts}[/points.low]"
    if pts <= 5:
        return f"[points.mid]{pts}[/points.mid]"
    return f"[points.high]{pts}[/points.high]"


def format_status(status: str) -> str:
    """Format a status string with appropriate colors."""
    lower = status.lower()
    style_map = {
        "running": "status.running",
        "completed": "status.completed",
        "complete": "status.completed",
        "failed": "status.failed",
        "paused": "status.paused",
        "pending": "warning",
        "todo": "muted",
        "to do": "muted",
    }
    style = style_map.get(lower, "")
    if style:
        return f"[{style}]{status}[/{style}]"
    return status


def notification(level: str, message: str) -> None:
    """Print a notification with level-appropriate styling."""
    style_map = {
        "success": "[success]",
        "warning": "[warning]",
        "error": "[error]",
        "info": "[info]",
    }
    prefix = style_map.get(level, "")
    close = f"[/{level}]" if prefix else ""
    icon_map = {
        "success": "OK",
        "warning": "WARN",
        "error": "ERR",
        "info": "INFO",
    }
    icon = icon_map.get(level, level.upper())
    console.print(f"{prefix}[{icon}]{close} {message}")
