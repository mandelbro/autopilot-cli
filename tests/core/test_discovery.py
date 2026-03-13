"""Tests for discovery-to-task conversion pipeline (Task 025)."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003 — used at runtime

import pytest

from autopilot.core.discovery import (
    DiscoveryDocument,
    DiscoveryParser,
    Phase,
    TaskFileWriter,
)
from autopilot.core.task import Task, TaskParser

# ---------------------------------------------------------------------------
# Sample discovery markdown
# ---------------------------------------------------------------------------

SAMPLE_DISCOVERY = """\
# My Project Discovery

**Date**: 2026-03-01
**Status**: Complete

A project for building things.

---

## Phase 1: Foundation

- Set up project structure
- Implement core module
- Write initial tests

Effort: small (6 points)

## Phase 2: Features

- Add authentication
- Add authorization
- Implement API endpoints
- Add caching layer

Effort: large (20 points)

## Phase 3: Polish

- Performance optimization
- Documentation

Effort: trivial
"""

MINIMAL_DISCOVERY = """\
# Tiny Project

Just a simple thing.

## Setup

- Initialize repo
- Add CI

Effort: small
"""


# ---------------------------------------------------------------------------
# Tests: DiscoveryParser.parse_discovery
# ---------------------------------------------------------------------------


class TestDiscoveryParser:
    def test_parses_title(self, tmp_path: Path) -> None:
        f = tmp_path / "discovery.md"
        f.write_text(SAMPLE_DISCOVERY, encoding="utf-8")
        doc = DiscoveryParser().parse_discovery(f)
        assert doc.title == "My Project Discovery"

    def test_parses_phases(self, tmp_path: Path) -> None:
        f = tmp_path / "discovery.md"
        f.write_text(SAMPLE_DISCOVERY, encoding="utf-8")
        doc = DiscoveryParser().parse_discovery(f)
        assert len(doc.phases) == 3

    def test_phase_names(self, tmp_path: Path) -> None:
        f = tmp_path / "discovery.md"
        f.write_text(SAMPLE_DISCOVERY, encoding="utf-8")
        doc = DiscoveryParser().parse_discovery(f)
        assert doc.phases[0].name == "Foundation"
        assert doc.phases[1].name == "Features"
        assert doc.phases[2].name == "Polish"

    def test_phase_deliverables(self, tmp_path: Path) -> None:
        f = tmp_path / "discovery.md"
        f.write_text(SAMPLE_DISCOVERY, encoding="utf-8")
        doc = DiscoveryParser().parse_discovery(f)
        assert len(doc.phases[0].deliverables) == 3
        assert "Set up project structure" in doc.phases[0].deliverables
        assert len(doc.phases[1].deliverables) == 4

    def test_phase_effort(self, tmp_path: Path) -> None:
        f = tmp_path / "discovery.md"
        f.write_text(SAMPLE_DISCOVERY, encoding="utf-8")
        doc = DiscoveryParser().parse_discovery(f)
        assert "small" in doc.phases[0].effort_estimate.lower()

    def test_minimal_discovery(self, tmp_path: Path) -> None:
        f = tmp_path / "discovery.md"
        f.write_text(MINIMAL_DISCOVERY, encoding="utf-8")
        doc = DiscoveryParser().parse_discovery(f)
        assert doc.title == "Tiny Project"
        assert len(doc.phases) == 1
        assert len(doc.phases[0].deliverables) == 2

    def test_description_extracted(self, tmp_path: Path) -> None:
        f = tmp_path / "discovery.md"
        f.write_text(SAMPLE_DISCOVERY, encoding="utf-8")
        doc = DiscoveryParser().parse_discovery(f)
        assert "building things" in doc.description


# ---------------------------------------------------------------------------
# Tests: DiscoveryParser.convert_to_tasks
# ---------------------------------------------------------------------------


class TestConvertToTasks:
    def test_correct_task_count(self, tmp_path: Path) -> None:
        f = tmp_path / "discovery.md"
        f.write_text(SAMPLE_DISCOVERY, encoding="utf-8")
        parser = DiscoveryParser()
        doc = parser.parse_discovery(f)
        tasks = parser.convert_to_tasks(doc)
        # 3 + 4 + 2 = 9 deliverables
        assert len(tasks) == 9

    def test_sequential_ids(self, tmp_path: Path) -> None:
        f = tmp_path / "discovery.md"
        f.write_text(SAMPLE_DISCOVERY, encoding="utf-8")
        parser = DiscoveryParser()
        doc = parser.parse_discovery(f)
        tasks = parser.convert_to_tasks(doc)
        ids = [t.id for t in tasks]
        assert ids == [f"{i:03d}" for i in range(1, 10)]

    def test_custom_start_id(self, tmp_path: Path) -> None:
        f = tmp_path / "discovery.md"
        f.write_text(SAMPLE_DISCOVERY, encoding="utf-8")
        parser = DiscoveryParser()
        doc = parser.parse_discovery(f)
        tasks = parser.convert_to_tasks(doc, start_id=50)
        assert tasks[0].id == "050"
        assert tasks[-1].id == "058"

    def test_tasks_have_user_stories(self, tmp_path: Path) -> None:
        f = tmp_path / "discovery.md"
        f.write_text(SAMPLE_DISCOVERY, encoding="utf-8")
        parser = DiscoveryParser()
        doc = parser.parse_discovery(f)
        tasks = parser.convert_to_tasks(doc)
        for task in tasks:
            assert task.user_story
            assert "As a developer" in task.user_story

    def test_tasks_have_prompts(self, tmp_path: Path) -> None:
        f = tmp_path / "discovery.md"
        f.write_text(SAMPLE_DISCOVERY, encoding="utf-8")
        parser = DiscoveryParser()
        doc = parser.parse_discovery(f)
        tasks = parser.convert_to_tasks(doc)
        for task in tasks:
            assert task.prompt
            assert "Objective" in task.prompt

    def test_sprint_points_are_fibonacci(self, tmp_path: Path) -> None:
        f = tmp_path / "discovery.md"
        f.write_text(SAMPLE_DISCOVERY, encoding="utf-8")
        parser = DiscoveryParser()
        doc = parser.parse_discovery(f)
        tasks = parser.convert_to_tasks(doc)
        valid_points = {1, 2, 3, 5, 8}
        for task in tasks:
            assert isinstance(task.sprint_points, int)
            assert task.sprint_points in valid_points


# ---------------------------------------------------------------------------
# Tests: Phase and DiscoveryDocument dataclasses
# ---------------------------------------------------------------------------


class TestDataModels:
    def test_phase_frozen(self) -> None:
        p = Phase(name="Test", deliverables=["A"])
        with pytest.raises(AttributeError):
            p.name = "Other"  # type: ignore[misc]

    def test_discovery_document_frozen(self) -> None:
        d = DiscoveryDocument(title="Test")
        with pytest.raises(AttributeError):
            d.title = "Other"  # type: ignore[misc]

    def test_phase_defaults(self) -> None:
        p = Phase(name="Test")
        assert p.deliverables == []
        assert p.effort_estimate == ""


# ---------------------------------------------------------------------------
# Tests: TaskFileWriter
# ---------------------------------------------------------------------------


class TestTaskFileWriter:
    def _make_tasks(self, count: int = 5) -> list[Task]:
        return [
            Task(
                id=f"{i + 1:03d}",
                title=f"Task {i + 1}",
                sprint_points=3,
                user_story=f"Story {i + 1}",
                outcome=f"Outcome {i + 1}",
                prompt=f"**Objective:** Task {i + 1}",
            )
            for i in range(count)
        ]

    def test_writes_index_file(self, tmp_path: Path) -> None:
        writer = TaskFileWriter()
        tasks = self._make_tasks(5)
        files = writer.write_task_files(tasks, tmp_path / "tasks")
        index_path = tmp_path / "tasks" / "tasks-index.md"
        assert index_path.exists()
        assert index_path in files

    def test_writes_task_file(self, tmp_path: Path) -> None:
        writer = TaskFileWriter()
        tasks = self._make_tasks(5)
        files = writer.write_task_files(tasks, tmp_path / "tasks")
        task_file = tmp_path / "tasks" / "tasks-1.md"
        assert task_file.exists()
        assert task_file in files

    def test_splits_at_max_tasks(self, tmp_path: Path) -> None:
        writer = TaskFileWriter()
        tasks = self._make_tasks(15)
        writer.write_task_files(tasks, tmp_path / "tasks")
        assert (tmp_path / "tasks" / "tasks-1.md").exists()
        assert (tmp_path / "tasks" / "tasks-2.md").exists()

    def test_index_summary_counts(self, tmp_path: Path) -> None:
        writer = TaskFileWriter()
        tasks = self._make_tasks(5)
        writer.write_task_files(tasks, tmp_path / "tasks")
        index_text = (tmp_path / "tasks" / "tasks-index.md").read_text()
        assert "**Total Tasks**: 5" in index_text
        assert "**Pending**: 5" in index_text
        assert "**Total Points**: 15" in index_text

    def test_task_file_parseable(self, tmp_path: Path) -> None:
        """Written task files should be parseable by TaskParser."""
        writer = TaskFileWriter()
        tasks = self._make_tasks(5)
        writer.write_task_files(tasks, tmp_path / "tasks")
        parser = TaskParser()
        parsed = parser.parse_task_file(tmp_path / "tasks" / "tasks-1.md")
        assert len(parsed) == 5
        assert parsed[0].id == "001"
        assert parsed[0].title == "Task 1"
        assert parsed[0].sprint_points == 3

    def test_merge_with_existing(self, tmp_path: Path) -> None:
        task_dir = tmp_path / "tasks"
        writer = TaskFileWriter()

        # Write initial tasks
        tasks1 = self._make_tasks(3)
        writer.write_task_files(tasks1, task_dir)

        # Merge new tasks
        new_tasks = [
            Task(id="001", title="New A", sprint_points=5, user_story="S", outcome="O"),
            Task(id="002", title="New B", sprint_points=3, user_story="S", outcome="O"),
        ]
        writer.write_task_files(new_tasks, task_dir, merge=True)

        # Verify index updated
        index_text = (task_dir / "tasks-index.md").read_text()
        assert "**Total Tasks**: 5" in index_text

        # Verify new file created with renumbered IDs
        assert (task_dir / "tasks-2.md").exists()
        parser = TaskParser()
        parsed = parser.parse_task_file(task_dir / "tasks-2.md")
        assert parsed[0].id == "004"
        assert parsed[1].id == "005"

    def test_id_sequencing(self, tmp_path: Path) -> None:
        writer = TaskFileWriter()
        tasks = self._make_tasks(12)
        writer.write_task_files(tasks, tmp_path / "tasks")
        parser = TaskParser()

        file1_tasks = parser.parse_task_file(tmp_path / "tasks" / "tasks-1.md")
        file2_tasks = parser.parse_task_file(tmp_path / "tasks" / "tasks-2.md")

        assert len(file1_tasks) == 10
        assert len(file2_tasks) == 2
        assert file1_tasks[-1].id == "010"
        assert file2_tasks[0].id == "011"
