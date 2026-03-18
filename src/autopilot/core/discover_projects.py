"""Discover external projects that use the Task Workflow System format.

Scans directories for ``tasks/tasks-index.md`` files and extracts project
metadata, enabling registration of external projects in the autopilot registry
without requiring a ``.autopilot/`` directory.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path  # noqa: TC003 — used at runtime

from autopilot.core.task import TaskParser

_DESCRIPTION_RE = re.compile(r"^\s*-\s+\*\*Description\*\*:\s*(.+)$")


@dataclass(frozen=True)
class DiscoverResult:
    """Metadata extracted from a discovered task project."""

    name: str
    path: str
    task_dir: str
    total_tasks: int = 0
    pending: int = 0
    complete: int = 0
    total_points: int = 0
    points_complete: int = 0
    description: str = ""


def _extract_description(text: str) -> str:
    """Extract the project description from the metadata section of tasks-index.md."""
    for line in text.split("\n"):
        # Stop searching once we hit the file index section
        if line.strip().startswith("## Task File Index"):
            break
        m = _DESCRIPTION_RE.match(line)
        if m:
            return m.group(1).strip()
    return ""


def discover_task_project(
    path: Path,
    *,
    name: str = "",
) -> DiscoverResult | None:
    """Discover a task project at *path*.

    Returns ``None`` if no ``tasks/tasks-index.md`` is found.
    """
    if not path.is_dir():
        return None

    task_dir = path / "tasks"
    index_path = task_dir / "tasks-index.md"

    if not index_path.exists():
        return None

    parser = TaskParser()
    index = parser.parse_task_index(index_path)
    description = _extract_description(index_path.read_text(encoding="utf-8"))

    return DiscoverResult(
        name=name or path.name,
        path=str(path.resolve()),
        task_dir=str(task_dir.resolve()),
        total_tasks=index.total_tasks,
        pending=index.pending,
        complete=index.complete,
        total_points=index.total_points,
        points_complete=index.points_complete,
        description=description,
    )


def scan_for_task_projects(
    search_path: Path,
    *,
    max_depth: int = 1,
) -> list[DiscoverResult]:
    """Scan immediate subdirectories of *search_path* for task projects.

    *max_depth* controls how many levels deep to search (1 = immediate children).
    """
    if not search_path.is_dir():
        return []

    results: list[DiscoverResult] = []

    def _scan(current: Path, depth: int) -> None:
        if depth > max_depth:
            return
        if not current.is_dir():
            return
        for child in sorted(current.iterdir()):
            if not child.is_dir() or child.name.startswith(".") or child.is_symlink():
                continue
            result = discover_task_project(child)
            if result is not None:
                results.append(result)
            elif depth < max_depth:
                _scan(child, depth + 1)

    _scan(search_path, 1)
    return results
