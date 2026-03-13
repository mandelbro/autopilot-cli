"""Task file parser and data model.

Parses the tasks-workflow.md format (tasks-index.md and tasks-N.md files)
into structured data, supporting task queries, status updates, and index
maintenance per RFC Section 6 Phase 2.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path  # noqa: TC003 — used at runtime

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Task:
    """A single task parsed from a tasks-N.md file."""

    id: str
    title: str
    file_path: str = ""
    complete: bool = False
    sprint_points: int | str = 0
    user_story: str = ""
    outcome: str = ""
    prompt: str = ""
    acceptance_criteria: list[str] = field(default_factory=list)
    spec_references: list[str] = field(default_factory=list)
    uat_status: str = ""

    # frozen=True + list defaults require hash=False override
    def __hash__(self) -> int:  # pragma: no cover
        return hash(self.id)


@dataclass(frozen=True)
class TaskFileEntry:
    """A single entry in the task-file index."""

    file: str
    start_id: str
    end_id: str
    task_count: int
    points: int


@dataclass(frozen=True)
class TaskIndex:
    """Parsed representation of tasks-index.md."""

    total_tasks: int = 0
    pending: int = 0
    complete: int = 0
    total_points: int = 0
    points_complete: int = 0
    file_index: list[TaskFileEntry] = field(default_factory=list)

    def __hash__(self) -> int:  # pragma: no cover
        return id(self)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

_TASK_HEADER_RE = re.compile(r"^###\s+Task\s+ID:\s*(.+)$", re.IGNORECASE)
_TITLE_RE = re.compile(r"^\s*-\s+\*\*Title\*\*:\s*(.+)$")
_FILE_RE = re.compile(r"^\s*-\s+\*\*File\*\*:\s*(.+)$")
_COMPLETE_RE = re.compile(r"^\s*-\s+\*\*Complete\*\*:\s*\[(.)\]")
_POINTS_RE = re.compile(r"^\s*-\s+\*\*Sprint Points\*\*:\s*(.+)$")
_USER_STORY_RE = re.compile(r"^\s*-\s+\*\*User Story \(business-facing\)\*\*:\s*(.+)$")
_OUTCOME_RE = re.compile(r"^\s*-\s+\*\*Outcome \(what this delivers\)\*\*:\s*(.+)$")
_SPEC_REFS_RE = re.compile(r"^\s*-\s+\*\*Spec References?\*\*:\s*(.+)$", re.IGNORECASE)
_UAT_STATUS_RE = re.compile(r"^\s*-\s+\*\*UAT Status\*\*:\s*(.+)$", re.IGNORECASE)
_CHECKBOX_RE = re.compile(r"^\s*-\s+\[.\]\s+(.+)$")

# Index-level patterns
_STAT_RE = re.compile(r"^\s*-\s+\*\*(.+?)\*\*:\s*(\d+)$")
_FILE_INDEX_RE = re.compile(
    r"^\s*-\s+`tasks/(tasks-[\w.]+\.md)`.*Tasks?\s+(\S+)\s*-\s*(\S+)"
    r"\s*\((\d+)\s+tasks?,\s*(\d+)\s+points?\)"
)


def _parse_sprint_points(raw: str) -> int | str:
    """Return an int for numeric points, or the raw string (e.g. warning symbol)."""
    raw = raw.strip()
    try:
        return int(raw)
    except ValueError:
        return raw


# ---------------------------------------------------------------------------
# TaskParser
# ---------------------------------------------------------------------------


class TaskParser:
    """Parses task markdown files into structured data."""

    # -- public API --

    def parse_task_file(self, path: Path) -> list[Task]:
        """Parse a tasks-N.md file and return all tasks found."""
        text = path.read_text(encoding="utf-8")
        return self._extract_tasks(text)

    def parse_task_index(self, path: Path) -> TaskIndex:
        """Parse tasks-index.md and return a TaskIndex."""
        text = path.read_text(encoding="utf-8")
        return self._extract_index(text)

    def find_next_pending(self, task_dir: Path) -> Task | None:
        """Find the first incomplete task across all task files in order."""
        index_path = task_dir / "tasks-index.md"
        if not index_path.exists():
            return None
        index = self.parse_task_index(index_path)
        for entry in index.file_index:
            file_path = task_dir / entry.file
            if not file_path.exists():
                continue
            tasks = self.parse_task_file(file_path)
            for task in tasks:
                if not task.complete:
                    return task
        return None

    def find_task_by_id(self, task_dir: Path, task_id: str) -> Task | None:
        """Locate a task by its ID across all task files."""
        normalized = task_id.strip().lstrip("0") or "0"
        index_path = task_dir / "tasks-index.md"
        if not index_path.exists():
            return None
        index = self.parse_task_index(index_path)
        for entry in index.file_index:
            if self._id_in_range(normalized, entry.start_id, entry.end_id):
                file_path = task_dir / entry.file
                if not file_path.exists():
                    continue
                tasks = self.parse_task_file(file_path)
                for task in tasks:
                    if self._normalize_id(task.id) == normalized:
                        return task
        # Fallback: scan all files (handles decimal IDs outside range)
        for entry in index.file_index:
            file_path = task_dir / entry.file
            if not file_path.exists():
                continue
            tasks = self.parse_task_file(file_path)
            for task in tasks:
                if self._normalize_id(task.id) == normalized:
                    return task
        return None

    # -- internal helpers --

    @staticmethod
    def _normalize_id(raw: str) -> str:
        """Normalize a task ID: strip leading zeros but preserve decimal suffixes."""
        raw = raw.strip()
        # Handle decimal IDs like 002-1
        if "-" in raw:
            base, suffix = raw.split("-", 1)
            return (base.lstrip("0") or "0") + "-" + suffix
        return raw.lstrip("0") or "0"

    @staticmethod
    def _id_in_range(normalized_id: str, start_id: str, end_id: str) -> bool:
        """Check if a normalized ID falls within the range of a file entry."""
        # Decimal IDs (e.g. 2-1) belong in the same file as their base
        base_id = normalized_id.split("-")[0]
        try:
            num = int(base_id)
            s = int(start_id.lstrip("0") or "0")
            e = int(end_id.lstrip("0") or "0")
            return s <= num <= e
        except ValueError:
            return False

    def _extract_tasks(self, text: str) -> list[Task]:
        """Extract all tasks from markdown text."""
        lines = text.split("\n")
        tasks: list[Task] = []
        i = 0
        while i < len(lines):
            m = _TASK_HEADER_RE.match(lines[i])
            if m:
                task, i = self._parse_single_task(lines, i, m.group(1).strip())
                tasks.append(task)
            else:
                i += 1
        return tasks

    def _parse_single_task(self, lines: list[str], start: int, task_id: str) -> tuple[Task, int]:
        """Parse a single task block starting at *start*. Returns (Task, next_line)."""
        title = ""
        file_path = ""
        complete = False
        sprint_points: int | str = 0
        user_story = ""
        outcome = ""
        prompt = ""
        acceptance_criteria: list[str] = []
        spec_references: list[str] = []
        uat_status = ""

        i = start + 1
        in_prompt = False
        prompt_lines: list[str] = []
        fence_count = 0

        while i < len(lines):
            line = lines[i]

            # Detect next task header -> stop
            if _TASK_HEADER_RE.match(line):
                break

            # Track fenced code blocks for prompt extraction
            if line.strip().startswith("```"):
                if not in_prompt and fence_count == 0:
                    # Opening fence (e.g. ```markdown) -> start capturing
                    fence_count = 1
                    in_prompt = True
                    i += 1
                    continue
                if in_prompt:
                    # Closing fence -> stop capturing
                    in_prompt = False
                    fence_count = 0
                    i += 1
                    continue

            if in_prompt:
                prompt_lines.append(line)
                # Extract acceptance criteria from prompt checkboxes
                cm = _CHECKBOX_RE.match(line)
                if cm:
                    acceptance_criteria.append(cm.group(1).strip())
                i += 1
                continue

            # Field extraction (outside prompt)
            if m := _TITLE_RE.match(line):
                title = m.group(1).strip()
            elif m := _FILE_RE.match(line):
                file_path = m.group(1).strip()
            elif m := _COMPLETE_RE.match(line):
                complete = m.group(1).lower() == "x"
            elif m := _POINTS_RE.match(line):
                sprint_points = _parse_sprint_points(m.group(1))
            elif m := _USER_STORY_RE.match(line):
                user_story = m.group(1).strip()
            elif m := _OUTCOME_RE.match(line):
                outcome = m.group(1).strip()
            elif m := _SPEC_REFS_RE.match(line):
                spec_references = [r.strip() for r in m.group(1).split(",") if r.strip()]
            elif m := _UAT_STATUS_RE.match(line):
                uat_status = m.group(1).strip()

            i += 1

        prompt = "\n".join(prompt_lines).strip()

        return (
            Task(
                id=task_id,
                title=title,
                file_path=file_path,
                complete=complete,
                sprint_points=sprint_points,
                user_story=user_story,
                outcome=outcome,
                prompt=prompt,
                acceptance_criteria=acceptance_criteria,
                spec_references=spec_references,
                uat_status=uat_status,
            ),
            i,
        )

    def _extract_index(self, text: str) -> TaskIndex:
        """Extract task index data from tasks-index.md content."""
        stats: dict[str, int] = {}
        file_entries: list[TaskFileEntry] = []

        for line in text.split("\n"):
            if m := _STAT_RE.match(line):
                key = m.group(1).strip().lower().replace(" ", "_")
                stats[key] = int(m.group(2))
            if m := _FILE_INDEX_RE.match(line):
                file_entries.append(
                    TaskFileEntry(
                        file=m.group(1),
                        start_id=m.group(2),
                        end_id=m.group(3),
                        task_count=int(m.group(4)),
                        points=int(m.group(5)),
                    )
                )

        return TaskIndex(
            total_tasks=stats.get("total_tasks", 0),
            pending=stats.get("pending", 0),
            complete=stats.get("complete", 0),
            total_points=stats.get("total_points", 0),
            points_complete=stats.get("points_complete", 0),
            file_index=file_entries,
        )


# ---------------------------------------------------------------------------
# Status update
# ---------------------------------------------------------------------------


def update_task_status(task_dir: Path, task_id: str, complete: bool) -> None:
    """Update a task's completion status in both its task file and the index.

    Raises ``FileNotFoundError`` if the task directory or index is missing.
    Raises ``ValueError`` if the task ID is not found.
    """
    parser = TaskParser()
    index_path = task_dir / "tasks-index.md"
    if not index_path.exists():
        msg = f"Task index not found: {index_path}"
        raise FileNotFoundError(msg)

    index = parser.parse_task_index(index_path)
    normalized = TaskParser._normalize_id(task_id)

    # Locate the task file containing this ID
    target_file: Path | None = None
    for entry in index.file_index:
        file_path = task_dir / entry.file
        if not file_path.exists():
            continue
        tasks = parser.parse_task_file(file_path)
        for task in tasks:
            if TaskParser._normalize_id(task.id) == normalized:
                target_file = file_path
                break
        if target_file:
            break

    if target_file is None:
        msg = f"Task ID '{task_id}' not found in any task file"
        raise ValueError(msg)

    # 1. Update the task file
    _update_task_file(target_file, task_id, complete)

    # 2. Update the index summary
    _update_index_file(index_path, task_id, complete, index)


def _update_task_file(path: Path, task_id: str, complete: bool) -> None:
    """Rewrite the task file toggling the Complete checkbox for *task_id*."""
    text = path.read_text(encoding="utf-8")
    normalized = TaskParser._normalize_id(task_id)
    lines = text.split("\n")
    result: list[str] = []
    in_target_task = False

    for line in lines:
        m = _TASK_HEADER_RE.match(line)
        if m:
            tid = m.group(1).strip()
            in_target_task = TaskParser._normalize_id(tid) == normalized

        if in_target_task and _COMPLETE_RE.match(line):
            mark = "x" if complete else " "
            line = re.sub(r"\[.\]", f"[{mark}]", line, count=1)
            in_target_task = False  # only update once

        result.append(line)

    path.write_text("\n".join(result), encoding="utf-8")


def _update_index_file(path: Path, task_id: str, complete: bool, index: TaskIndex) -> None:
    """Adjust Pending / Complete / Points Complete in tasks-index.md."""
    # Find the task to get its sprint points
    parser = TaskParser()
    task_dir = path.parent
    task = parser.find_task_by_id(task_dir, task_id)
    points = 0
    if task is not None and isinstance(task.sprint_points, int):
        points = task.sprint_points

    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    result: list[str] = []

    pending_delta = -1 if complete else 1
    complete_delta = 1 if complete else -1

    for line in lines:
        if re.match(r"^\s*-\s+\*\*Pending\*\*:\s*\d+", line):
            new_val = max(0, index.pending + pending_delta)
            line = f"- **Pending**: {new_val}"
        elif re.match(r"^\s*-\s+\*\*Complete\*\*:\s*\d+", line) and "Points" not in line:
            new_val = max(0, index.complete + complete_delta)
            line = f"- **Complete**: {new_val}"
        elif re.match(r"^\s*-\s+\*\*Points Complete\*\*:\s*\d+", line):
            new_val = max(0, index.points_complete + (points * complete_delta))
            line = f"- **Points Complete**: {new_val}"
        result.append(line)

    path.write_text("\n".join(result), encoding="utf-8")
