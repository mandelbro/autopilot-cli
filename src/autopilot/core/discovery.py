"""Discovery-to-task conversion pipeline (Tasks 025, 079).

Parses discovery markdown documents into structured phases and deliverables,
then converts them into Task objects and writes properly formatted task files.
Includes the end-to-end DiscoveryConverter pipeline (Task 079).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path  # noqa: TC003 — used at runtime

import structlog

from autopilot.core.task import Task

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

_EFFORT_MAP: dict[str, int] = {
    "trivial": 1,
    "small": 2,
    "medium": 3,
    "large": 5,
    "extra large": 8,
    "xl": 8,
}

MAX_TASKS_PER_FILE = 10


@dataclass(frozen=True)
class Phase:
    """A single phase extracted from a discovery document."""

    name: str
    deliverables: list[str] = field(default_factory=lambda: list[str]())
    effort_estimate: str = ""

    def __hash__(self) -> int:  # pragma: no cover
        return hash(self.name)


@dataclass(frozen=True)
class DiscoveryDocument:
    """Parsed representation of a discovery markdown document."""

    title: str
    description: str = ""
    phases: list[Phase] = field(default_factory=lambda: list[Phase]())

    def __hash__(self) -> int:  # pragma: no cover
        return hash(self.title)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

_PHASE_HEADER_RE = re.compile(
    r"^#{2,3}\s+(?:Phase\s+\d+[:\s]*|Implementation\s+Phase[:\s]*)?(.+)$",
    re.IGNORECASE,
)
_DELIVERABLE_RE = re.compile(r"^\s*[-*]\s+(.+)$")
_EFFORT_RE = re.compile(r"effort[:\s]*(.+)", re.IGNORECASE)
_TITLE_RE = re.compile(r"^#\s+(.+)$")


def _estimate_points(effort: str, num_deliverables: int) -> int:
    """Map an effort string to per-deliverable Fibonacci points."""
    effort_lower = effort.strip().lower()
    for key, pts in _EFFORT_MAP.items():
        if key in effort_lower:
            return pts

    # Try to extract a numeric sprint-point range
    numbers = re.findall(r"\d+", effort)
    if numbers:
        total = int(numbers[0])
        if num_deliverables > 0:
            per = max(1, total // num_deliverables)
            # Round to nearest Fibonacci
            for fib in (1, 2, 3, 5, 8):
                if per <= fib:
                    return fib
        return min(total, 8)

    return 3  # default medium


# ---------------------------------------------------------------------------
# DiscoveryParser
# ---------------------------------------------------------------------------


class DiscoveryParser:
    """Parses discovery markdown into structured data."""

    def parse_discovery(self, path: Path) -> DiscoveryDocument:
        """Extract title, description, phases, and deliverables from a discovery doc."""
        text = path.read_text(encoding="utf-8")
        lines = text.split("\n")

        title = ""
        description_lines: list[str] = []
        phases: list[Phase] = []
        current_phase_name: str | None = None
        current_deliverables: list[str] = []
        current_effort = ""
        in_header = True

        for line in lines:
            # Extract document title
            if not title:
                m = _TITLE_RE.match(line)
                if m:
                    title = m.group(1).strip()
                    in_header = True
                    continue

            # Detect phase headers
            if line.startswith("##"):
                # Save previous phase if any
                if current_phase_name and current_deliverables:
                    phases.append(
                        Phase(
                            name=current_phase_name,
                            deliverables=current_deliverables,
                            effort_estimate=current_effort,
                        )
                    )
                m = _PHASE_HEADER_RE.match(line)
                if m:
                    in_header = False
                    current_phase_name = m.group(1).strip()
                    current_deliverables = []
                    current_effort = ""
                else:
                    current_phase_name = None
                    current_deliverables = []
                    current_effort = ""
                continue

            # Collect description from top of document
            if in_header and title and not line.startswith("#"):
                stripped = line.strip()
                if stripped and not stripped.startswith("---"):
                    description_lines.append(stripped)
                continue

            # Within a phase: collect deliverables and effort
            if current_phase_name:
                m = _DELIVERABLE_RE.match(line)
                if m:
                    current_deliverables.append(m.group(1).strip())
                m_effort = _EFFORT_RE.search(line)
                if m_effort:
                    current_effort = m_effort.group(1).strip()

        # Save final phase
        if current_phase_name and current_deliverables:
            phases.append(
                Phase(
                    name=current_phase_name,
                    deliverables=current_deliverables,
                    effort_estimate=current_effort,
                )
            )

        description = " ".join(description_lines).strip()
        return DiscoveryDocument(title=title or path.stem, description=description, phases=phases)

    def convert_to_tasks(
        self,
        discovery: DiscoveryDocument,
        *,
        start_id: int = 1,
    ) -> list[Task]:
        """Convert a discovery document into a list of Task objects.

        Each phase deliverable becomes one task.  Sprint points are
        estimated from phase effort estimates distributed across deliverables.
        """
        tasks: list[Task] = []
        task_num = start_id

        for phase in discovery.phases:
            num_deliverables = len(phase.deliverables) or 1
            per_task_points = _estimate_points(phase.effort_estimate, num_deliverables)

            for deliverable in phase.deliverables:
                task_id = f"{task_num:03d}"
                tasks.append(
                    Task(
                        id=task_id,
                        title=deliverable,
                        sprint_points=per_task_points,
                        user_story=(
                            f"As a developer, I want {deliverable.lower()}, "
                            f"so that the {phase.name} phase is complete."
                        ),
                        outcome=f"Delivers: {deliverable}",
                        prompt=f"**Objective:** {deliverable}\n\n"
                        f"**Phase:** {phase.name}\n"
                        f"**Discovery:** {discovery.title}",
                    )
                )
                task_num += 1

        return tasks


# ---------------------------------------------------------------------------
# TaskFileWriter
# ---------------------------------------------------------------------------


class TaskFileWriter:
    """Writes Task objects into properly formatted task markdown files."""

    def write_task_files(
        self,
        tasks: list[Task],
        output_dir: Path,
        *,
        merge: bool = False,
    ) -> list[Path]:
        """Write tasks-index.md and tasks-N.md files.

        When *merge* is True and an existing tasks-index.md is present,
        new tasks are appended with continuing IDs.

        Returns the list of files created or modified.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        written_files: list[Path] = []

        existing_count = 0
        existing_points = 0
        existing_complete = 0

        if merge:
            existing_count, existing_points, existing_complete = self._read_existing_counts(
                output_dir
            )
            # Re-number tasks starting after existing
            renumbered: list[Task] = []
            for i, t in enumerate(tasks):
                new_id = f"{existing_count + i + 1:03d}"
                renumbered.append(
                    Task(
                        id=new_id,
                        title=t.title,
                        file_path=t.file_path,
                        complete=t.complete,
                        sprint_points=t.sprint_points,
                        user_story=t.user_story,
                        outcome=t.outcome,
                        prompt=t.prompt,
                    )
                )
            tasks = renumbered

        # Split tasks into chunks of MAX_TASKS_PER_FILE
        chunks: list[list[Task]] = []
        for i in range(0, len(tasks), MAX_TASKS_PER_FILE):
            chunks.append(tasks[i : i + MAX_TASKS_PER_FILE])

        # Determine starting file number
        start_file_num = 1
        if merge:
            existing_files = sorted(output_dir.glob("tasks-*.md"))
            existing_files = [f for f in existing_files if f.name != "tasks-index.md"]
            start_file_num = len(existing_files) + 1

        file_entries: list[tuple[str, str, str, int, int]] = []

        for chunk_idx, chunk in enumerate(chunks):
            file_num = start_file_num + chunk_idx
            file_name = f"tasks-{file_num}.md"
            file_path = output_dir / file_name
            content = self._render_task_file(file_name, chunk)
            file_path.write_text(content, encoding="utf-8")
            written_files.append(file_path)

            pts = sum(t.sprint_points for t in chunk if isinstance(t.sprint_points, int))
            file_entries.append((file_name, chunk[0].id, chunk[-1].id, len(chunk), pts))

        # Write or update index
        total_new_points = sum(t.sprint_points for t in tasks if isinstance(t.sprint_points, int))
        total_pending = sum(1 for t in tasks if not t.complete)
        total_complete_new = sum(1 for t in tasks if t.complete)

        index_path = output_dir / "tasks-index.md"
        index_content = self._render_index(
            total_tasks=existing_count + len(tasks),
            pending=total_pending + (existing_count - existing_complete),
            complete=existing_complete + total_complete_new,
            total_points=existing_points + total_new_points,
            points_complete=0,
            file_entries=file_entries,
            merge=merge,
            existing_index_path=index_path if merge and index_path.exists() else None,
        )
        index_path.write_text(index_content, encoding="utf-8")
        written_files.append(index_path)

        return written_files

    # -- internal helpers --

    @staticmethod
    def _read_existing_counts(output_dir: Path) -> tuple[int, int, int]:
        """Read existing task/point/complete counts from tasks-index.md."""
        index_path = output_dir / "tasks-index.md"
        if not index_path.exists():
            return 0, 0, 0

        text = index_path.read_text(encoding="utf-8")
        total = 0
        points = 0
        complete = 0
        for line in text.split("\n"):
            if m := re.match(r"^\s*-\s+\*\*Total Tasks\*\*:\s*(\d+)", line):
                total = int(m.group(1))
            elif m := re.match(r"^\s*-\s+\*\*Total Points\*\*:\s*(\d+)", line):
                points = int(m.group(1))
            elif (
                m := re.match(r"^\s*-\s+\*\*Complete\*\*:\s*(\d+)", line)
            ) and "Points" not in line:
                complete = int(m.group(1))
        return total, points, complete

    @staticmethod
    def _render_task_file(file_name: str, tasks: list[Task]) -> str:
        """Render a complete tasks-N.md file."""
        pts = sum(t.sprint_points for t in tasks if isinstance(t.sprint_points, int))
        lines = [
            f"## Summary ({file_name})",
            "",
            f"- **Tasks in this file**: {len(tasks)}",
            f"- **Task IDs**: {tasks[0].id} - {tasks[-1].id}",
            f"- **Total Points**: {pts}",
            "",
            "---",
            "",
            "## Tasks",
        ]

        for task in tasks:
            mark = "x" if task.complete else " "
            sp = task.sprint_points if isinstance(task.sprint_points, int) else "⚠️"
            lines.extend(
                [
                    "",
                    f"### Task ID: {task.id}",
                    "",
                    f"- **Title**: {task.title}",
                    f"- **File**: {task.file_path or 'TBD'}",
                    f"- **Complete**: [{mark}]",
                    f"- **Sprint Points**: {sp}",
                    "",
                    f"- **User Story (business-facing)**: {task.user_story}",
                    f"- **Outcome (what this delivers)**: {task.outcome}",
                    "",
                    "#### Prompt:",
                    "",
                    "```markdown",
                    task.prompt or f"**Objective:** {task.title}",
                    "```",
                    "",
                    "---",
                ]
            )

        return "\n".join(lines) + "\n"

    @staticmethod
    def _render_index(
        *,
        total_tasks: int,
        pending: int,
        complete: int,
        total_points: int,
        points_complete: int,
        file_entries: list[tuple[str, str, str, int, int]],
        merge: bool,
        existing_index_path: Path | None,
    ) -> str:
        """Render tasks-index.md content."""
        # If merging, preserve existing entries and append new ones
        existing_entries_text = ""
        if merge and existing_index_path and existing_index_path.exists():
            text = existing_index_path.read_text(encoding="utf-8")
            entry_lines: list[str] = []
            for line in text.split("\n"):
                if line.strip().startswith("- `tasks/tasks-"):
                    entry_lines.append(line)
            existing_entries_text = "\n".join(entry_lines)
            if existing_entries_text:
                existing_entries_text += "\n"

        new_entries: list[str] = []
        for fname, start_id, end_id, count, pts in file_entries:
            new_entries.append(
                f"- `tasks/{fname}`: Contains Tasks {start_id} - {end_id}"
                f" ({count} tasks, {pts} points)"
            )

        all_entries = existing_entries_text + "\n".join(new_entries)

        return (
            f"## Overall Project Task Summary\n"
            f"\n"
            f"- **Total Tasks**: {total_tasks}\n"
            f"- **Pending**: {pending}\n"
            f"- **Complete**: {complete}\n"
            f"- **Total Points**: {total_points}\n"
            f"- **Points Complete**: {points_complete}\n"
            f"\n"
            f"## Task File Index\n"
            f"\n"
            f"{all_entries}\n"
        )


# ---------------------------------------------------------------------------
# DiscoveryConverter — end-to-end pipeline (Task 079)
# ---------------------------------------------------------------------------

# Patterns for extracting spec references from discovery context
_SPEC_REF_RE = re.compile(
    r"(?:RFC|Discovery|UX Design)\s+(?:Section\s+)?[\d.]+",
    re.IGNORECASE,
)


class DiscoveryConverter:
    """End-to-end pipeline: parse discovery -> extract phases -> generate tasks -> write files.

    Wraps DiscoveryParser and TaskFileWriter with additional spec reference
    extraction and proportional point distribution.
    """

    def __init__(self) -> None:
        self._parser = DiscoveryParser()
        self._writer = TaskFileWriter()

    def parse(self, path: Path) -> DiscoveryDocument:
        """Parse a discovery markdown file into a structured document."""
        logger.info("discovery_parse", path=str(path))
        return self._parser.parse_discovery(path)

    def extract_phases(self, doc: DiscoveryDocument) -> list[Phase]:
        """Extract implementation phases from a parsed discovery document."""
        return list(doc.phases)

    def generate_tasks(
        self,
        phases: list[Phase],
        *,
        project_title: str = "",
        start_id: int = 1,
    ) -> list[Task]:
        """Create tasks from phases with spec references and proportional points.

        Each deliverable in each phase becomes a task. Spec references are
        extracted from the phase context text. Points are distributed
        proportionally from phase effort estimates.
        """
        tasks: list[Task] = []
        task_num = start_id

        for phase in phases:
            num_deliverables = len(phase.deliverables) or 1
            per_task_points = _estimate_points(phase.effort_estimate, num_deliverables)

            # Extract any spec references from the phase name and effort
            phase_context = f"{phase.name} {phase.effort_estimate}"
            spec_refs = _SPEC_REF_RE.findall(phase_context)

            for deliverable in phase.deliverables:
                task_id = f"{task_num:03d}"

                # Also check deliverable text for spec references
                deliverable_refs = _SPEC_REF_RE.findall(deliverable)
                all_refs = spec_refs + deliverable_refs
                combined_refs = ", ".join(dict.fromkeys(all_refs)) if all_refs else ""

                prompt = f"**Objective:** {deliverable}\n\n**Phase:** {phase.name}\n"
                if project_title:
                    prompt += f"**Discovery:** {project_title}\n"
                if combined_refs:
                    prompt += f"\n**Specification References:**\n- {combined_refs}\n"

                tasks.append(
                    Task(
                        id=task_id,
                        title=deliverable,
                        sprint_points=per_task_points,
                        user_story=(
                            f"As a developer, I want {deliverable.lower()}, "
                            f"so that the {phase.name} phase is complete."
                        ),
                        outcome=f"Delivers: {deliverable}",
                        prompt=prompt,
                        spec_references=[combined_refs] if combined_refs else [],
                    )
                )
                task_num += 1

        logger.info("discovery_tasks_generated", count=len(tasks))
        return tasks

    def write_files(
        self,
        tasks: list[Task],
        output_dir: Path,
        *,
        merge: bool = False,
    ) -> list[Path]:
        """Write tasks to task files, optionally merging with existing files."""
        logger.info(
            "discovery_write_files",
            count=len(tasks),
            output=str(output_dir),
            merge=merge,
        )
        return self._writer.write_task_files(tasks, output_dir, merge=merge)

    def convert(
        self,
        discovery_path: Path,
        output_dir: Path,
        *,
        merge: bool = False,
    ) -> list[Path]:
        """Full end-to-end conversion: parse -> extract -> generate -> write.

        Convenience method that chains all pipeline steps.
        """
        doc = self.parse(discovery_path)
        phases = self.extract_phases(doc)

        start_id = 1
        if merge:
            existing_count, _, _ = TaskFileWriter._read_existing_counts(output_dir)  # pyright: ignore[reportPrivateUsage]
            start_id = existing_count + 1

        tasks = self.generate_tasks(
            phases,
            project_title=doc.title,
            start_id=start_id,
        )
        return self.write_files(tasks, output_dir, merge=merge)
