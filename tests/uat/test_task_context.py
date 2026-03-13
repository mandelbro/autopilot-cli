"""Tests for UAT task context loader."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from autopilot.uat.task_context import (
    SpecReference,
    TaskContext,
    _parse_spec_reference_line,
    _parse_spec_references_from_header,
    _parse_spec_references_from_prompt,
    load_task_context,
)

# ---------------------------------------------------------------------------
# SpecReference and TaskContext dataclass tests
# ---------------------------------------------------------------------------


class TestSpecReference:
    def test_frozen(self) -> None:
        ref = SpecReference(document="RFC", section="3.4.1")
        with pytest.raises(AttributeError):
            ref.document = "other"  # type: ignore[misc]

    def test_defaults(self) -> None:
        ref = SpecReference(document="RFC")
        assert ref.section == ""
        assert ref.requirement == ""
        assert ref.verification_type == "manual"


class TestTaskContext:
    def test_frozen(self) -> None:
        ctx = TaskContext(task_id="1", title="Test")
        with pytest.raises(AttributeError):
            ctx.title = "other"  # type: ignore[misc]

    def test_defaults(self) -> None:
        ctx = TaskContext(task_id="1", title="Test")
        assert ctx.file_path == ""
        assert ctx.acceptance_criteria == []
        assert ctx.spec_references == []
        assert ctx.prompt_text == ""


# ---------------------------------------------------------------------------
# Spec reference parsing helpers
# ---------------------------------------------------------------------------


class TestParseSpecReferenceLine:
    def test_rfc_section(self) -> None:
        ref = _parse_spec_reference_line("RFC Section 3.4.1: Task parsing")
        assert ref is not None
        assert ref.document == "RFC"
        assert ref.section == "3.4.1"
        assert ref.requirement == "Task parsing"

    def test_ux_design_section(self) -> None:
        ref = _parse_spec_reference_line("UX Design Section 5.2: Planning Pipeline")
        assert ref is not None
        assert ref.document == "UX Design"
        assert ref.section == "5.2"
        assert ref.verification_type == "visual"

    def test_plain_document(self) -> None:
        ref = _parse_spec_reference_line("Discovery: Task Management section")
        assert ref is not None
        assert ref.document == "Discovery"
        assert ref.requirement == "Task Management section"

    def test_empty_line(self) -> None:
        assert _parse_spec_reference_line("") is None
        assert _parse_spec_reference_line("   ") is None

    def test_with_list_prefix(self) -> None:
        ref = _parse_spec_reference_line("- RFC Section 6: Phase 2")
        assert ref is not None
        assert ref.document == "RFC"
        assert ref.section == "6"


class TestParseSpecReferencesFromPrompt:
    def test_extracts_from_spec_section(self) -> None:
        prompt = (
            "**Objective:** Do something\n"
            "\n"
            "**Specification References:**\n"
            "- RFC Section 3.4.1: Task parsing\n"
            "- UX Design Section 5.2: Planning Pipeline\n"
            "\n"
            "**Detailed Instructions:**\n"
            "1. Do stuff\n"
        )
        refs = _parse_spec_references_from_prompt(prompt)
        assert len(refs) == 2
        assert refs[0].document == "RFC"
        assert refs[0].section == "3.4.1"
        assert refs[1].document == "UX Design"

    def test_empty_prompt(self) -> None:
        assert _parse_spec_references_from_prompt("") == []

    def test_no_spec_section(self) -> None:
        prompt = "**Objective:** Do something\n**Instructions:** stuff\n"
        assert _parse_spec_references_from_prompt(prompt) == []


class TestParseSpecReferencesFromHeader:
    def test_parses_header_refs(self) -> None:
        raw = [
            "UAT Discovery: Task Context Loader",
            "RFC Section 6 Phase 2: Task file parsing deliverables",
        ]
        refs = _parse_spec_references_from_header(raw)
        assert len(refs) == 2
        assert refs[0].document == "UAT Discovery"
        assert refs[1].section == "6"


# ---------------------------------------------------------------------------
# load_task_context integration tests
# ---------------------------------------------------------------------------


class TestLoadTaskContext:
    @pytest.fixture()
    def task_dir(self, tmp_path: Path) -> Path:
        """Create a minimal task directory with index and task file."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()

        index = tasks_dir / "tasks-index.md"
        index.write_text(
            "## Overall Project Task Summary\n"
            "\n"
            "- **Total Tasks**: 2\n"
            "- **Pending**: 1\n"
            "- **Complete**: 1\n"
            "- **Total Points**: 8\n"
            "- **Points Complete**: 3\n"
            "\n"
            "## Task File Index\n"
            "\n"
            "- `tasks/tasks-1.md`: Contains Tasks 001 - 002 (2 tasks, 8 points)\n",
            encoding="utf-8",
        )

        task_file = tasks_dir / "tasks-1.md"
        task_file.write_text(
            "## Tasks\n"
            "\n"
            "### Task ID: 001\n"
            "\n"
            "- **Title**: Test task\n"
            "- **File**: src/example.py\n"
            "- **Complete**: [x]\n"
            "- **Sprint Points**: 3\n"
            "- **Spec References**: UAT Discovery: Context Loader, RFC Section 6: Phase 2\n"
            "\n"
            "- **User Story (business-facing)**: As a dev, I want tests, so that code works.\n"
            "- **Outcome (what this delivers)**: Working tests.\n"
            "\n"
            "#### Prompt:\n"
            "\n"
            "```markdown\n"
            "**Objective:** Build test task.\n"
            "\n"
            "**Specification References:**\n"
            "- Discovery: Task Management section\n"
            "- UX Design Section 7: Progressive Disclosure\n"
            "\n"
            "**Acceptance Criteria:**\n"
            "- [ ] Parser works correctly\n"
            "- [ ] All tests pass\n"
            "```\n"
            "\n"
            "---\n"
            "\n"
            "### Task ID: 002\n"
            "\n"
            "- **Title**: Another task\n"
            "- **File**: src/other.py\n"
            "- **Complete**: [ ]\n"
            "- **Sprint Points**: 5\n"
            "\n"
            "- **User Story (business-facing)**: As a dev, I want features.\n"
            "- **Outcome (what this delivers)**: Features.\n"
            "\n"
            "#### Prompt:\n"
            "\n"
            "```markdown\n"
            "**Objective:** Build features.\n"
            "```\n",
            encoding="utf-8",
        )

        return tasks_dir

    def test_loads_complete_task(self, task_dir: Path) -> None:
        ctx = load_task_context(task_dir, "001")
        assert ctx.task_id == "001"
        assert ctx.title == "Test task"
        assert ctx.file_path == "src/example.py"
        assert ctx.sprint_points == 3
        assert ctx.user_story == "As a dev, I want tests, so that code works."
        assert ctx.outcome == "Working tests."

    def test_acceptance_criteria_extracted(self, task_dir: Path) -> None:
        ctx = load_task_context(task_dir, "001")
        assert "Parser works correctly" in ctx.acceptance_criteria
        assert "All tests pass" in ctx.acceptance_criteria

    def test_spec_references_from_header_and_prompt(self, task_dir: Path) -> None:
        ctx = load_task_context(task_dir, "001")
        # Should have refs from header (2) and from prompt spec section (2)
        assert len(ctx.spec_references) >= 3
        docs = {r.document for r in ctx.spec_references}
        assert "UAT Discovery" in docs or "Discovery" in docs

    def test_missing_task_returns_placeholder(self, task_dir: Path) -> None:
        ctx = load_task_context(task_dir, "999")
        assert ctx.task_id == "999"
        assert "Unknown" in ctx.title

    def test_task_with_minimal_fields(self, task_dir: Path) -> None:
        ctx = load_task_context(task_dir, "002")
        assert ctx.task_id == "002"
        assert ctx.title == "Another task"
        # No spec_references in header or prompt for task 002
        assert ctx.spec_references == []
