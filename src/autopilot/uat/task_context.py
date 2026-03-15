"""UAT task context loader.

Loads completed task context with all testable assertions, extracting
user stories, acceptance criteria, file paths, and spec references
from task markdown per UAT Discovery specification.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path  # noqa: TC003 — used at runtime

import structlog

from autopilot.core.task import TaskParser

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SpecReference:
    """A reference to a specification document section."""

    document: str
    section: str = ""
    requirement: str = ""
    verification_type: str = "manual"


@dataclass(frozen=True)
class TaskContext:
    """Full context for a task, ready for UAT test generation."""

    task_id: str
    title: str
    file_path: str = ""
    sprint_points: int | str = 0
    user_story: str = ""
    outcome: str = ""
    acceptance_criteria: list[str] = field(default_factory=list[str])
    prompt_text: str = ""
    spec_references: list[SpecReference] = field(default_factory=list[SpecReference])

    def __hash__(self) -> int:  # pragma: no cover
        return hash(self.task_id)


# ---------------------------------------------------------------------------
# Spec-reference parsing helpers
# ---------------------------------------------------------------------------

# Matches lines like "- RFC Section 3.4.1: Some requirement"
_SPEC_LINE_RE = re.compile(
    r"^\s*-\s+(.+?)(?::\s*(.+))?$",
)

# Matches the **Specification References:** header in prompt text
_SPEC_SECTION_RE = re.compile(
    r"\*\*Specification References?:?\*\*",
    re.IGNORECASE,
)


def _parse_spec_reference_line(line: str) -> SpecReference | None:
    """Parse a single spec reference line into a SpecReference."""
    line = line.strip()
    if not line:
        return None

    # Remove leading "- " if present
    if line.startswith("- "):
        line = line[2:].strip()

    if not line:
        return None

    # Try to split on ": " for document: requirement
    parts = line.split(":", 1)
    doc_part = parts[0].strip()
    requirement = parts[1].strip() if len(parts) > 1 else ""

    # Extract document and section
    # Patterns: "RFC Section 3.4.1", "UX Design Section 4.1",
    # "Discovery: Task Management", "Task Workflow System"
    section = ""
    document = doc_part

    # Check for "Section X.Y.Z" pattern
    section_match = re.search(r"[Ss]ection\s+([\d.]+)", doc_part)
    if section_match:
        section = section_match.group(1)
        # Document is everything before "Section"
        doc_name = re.sub(r"\s*[Ss]ection\s+[\d.]+.*", "", doc_part).strip()
        if doc_name:
            document = doc_name

    # Determine verification type from context
    verification_type = "manual"
    lower = line.lower()
    if any(kw in lower for kw in ("api", "endpoint", "interface", "function")):
        verification_type = "automated"
    elif any(kw in lower for kw in ("design", "ux", "layout")):
        verification_type = "visual"

    return SpecReference(
        document=document,
        section=section,
        requirement=requirement,
        verification_type=verification_type,
    )


def _parse_spec_references_from_prompt(prompt_text: str) -> list[SpecReference]:
    """Extract spec references from the **Specification References:** section in prompt text."""
    refs: list[SpecReference] = []
    lines = prompt_text.split("\n")
    in_spec_section = False

    for line in lines:
        # Detect start of spec references section
        if _SPEC_SECTION_RE.search(line):
            in_spec_section = True
            continue

        if in_spec_section:
            stripped = line.strip()
            # End of section: blank line or new section header
            if not stripped:
                in_spec_section = False
                continue
            if stripped.startswith("**") and stripped.endswith("**"):
                in_spec_section = False
                continue
            # Also end on non-list content (new section starting with **)
            if stripped.startswith("**"):
                in_spec_section = False
                continue

            # Parse the reference line
            ref = _parse_spec_reference_line(stripped)
            if ref:
                refs.append(ref)

    return refs


def _parse_spec_references_from_header(raw_refs: list[str]) -> list[SpecReference]:
    """Parse spec references from the task header's Spec References field."""
    refs: list[SpecReference] = []
    for raw in raw_refs:
        ref = _parse_spec_reference_line(raw)
        if ref:
            refs.append(ref)
    return refs


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_task_context(task_dir: Path, task_id: str) -> TaskContext:
    """Load a task's full context for UAT processing.

    Uses the existing ``TaskParser`` to locate and parse the task, then
    enriches the result with parsed spec references from both the task
    header and the prompt's Specification References section.

    Missing fields produce warnings via structlog, not errors.
    """
    parser = TaskParser()
    task = parser.find_task_by_id(task_dir, task_id)

    if task is None:
        logger.warning("task_not_found", task_id=task_id, task_dir=str(task_dir))
        return TaskContext(task_id=task_id, title=f"Unknown task {task_id}")

    # Warn on missing fields
    if not task.title:
        logger.warning("missing_field", task_id=task_id, field="title")
    if not task.user_story:
        logger.warning("missing_field", task_id=task_id, field="user_story")
    if not task.acceptance_criteria:
        logger.warning("missing_field", task_id=task_id, field="acceptance_criteria")

    # Collect spec references from both sources
    header_refs = _parse_spec_references_from_header(task.spec_references)
    prompt_refs = _parse_spec_references_from_prompt(task.prompt)
    all_refs = header_refs + prompt_refs

    return TaskContext(
        task_id=task.id,
        title=task.title,
        file_path=task.file_path,
        sprint_points=task.sprint_points,
        user_story=task.user_story,
        outcome=task.outcome,
        acceptance_criteria=task.acceptance_criteria,
        prompt_text=task.prompt,
        spec_references=all_refs,
    )
