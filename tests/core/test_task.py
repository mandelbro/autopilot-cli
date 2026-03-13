"""Tests for task file parser and data model."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003 — used at runtime

import pytest

from autopilot.core.task import (
    Task,
    TaskParser,
    update_task_status,
)

# ---------------------------------------------------------------------------
# Sample markdown fixtures
# ---------------------------------------------------------------------------

SAMPLE_INDEX = """\
## Overall Project Task Summary

- **Total Tasks**: 4
- **Pending**: 3
- **Complete**: 1
- **Total Points**: 14
- **Points Complete**: 3

## Task File Index

- `tasks/tasks-1.md`: Contains Tasks 001 - 002 (2 tasks, 8 points)
- `tasks/tasks-2.md`: Contains Tasks 003 - 004 (2 tasks, 6 points)
"""

SAMPLE_TASK_FILE = """\
## Summary (tasks-1.md)

- **Tasks in this file**: 2
- **Task IDs**: 001 - 002

---

## Tasks

### Task ID: 001

- **Title**: First task
- **File**: src/foo.py
- **Complete**: [x]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a dev, I want X, so that Y.
- **Outcome (what this delivers)**: Delivers X.

#### Prompt:

```markdown
**Objective:** Do something.

**Acceptance Criteria:**
- [ ] Criterion A
- [ ] Criterion B
```

---

### Task ID: 002

- **Title**: Second task
- **File**: src/bar.py
- **Complete**: [ ]
- **Sprint Points**: 5

- **User Story (business-facing)**: As a dev, I want A, so that B.
- **Outcome (what this delivers)**: Delivers A.

#### Prompt:

```markdown
**Objective:** Do another thing.

**Acceptance Criteria:**
- [ ] Criterion C
```
"""

SAMPLE_TASK_FILE_2 = """\
## Tasks

### Task ID: 003

- **Title**: Third task
- **File**: src/baz.py
- **Complete**: [ ]
- **Sprint Points**: 3

- **User Story (business-facing)**: Story 3.
- **Outcome (what this delivers)**: Outcome 3.

#### Prompt:

```markdown
**Objective:** Third objective.
```

---

### Task ID: 004

- **Title**: Fourth task
- **File**: src/qux.py
- **Complete**: [ ]
- **Sprint Points**: 3

- **User Story (business-facing)**: Story 4.
- **Outcome (what this delivers)**: Outcome 4.

#### Prompt:

```markdown
**Objective:** Fourth objective.
```
"""

SAMPLE_DECIMAL_TASK_FILE = """\
## Tasks

### Task ID: 002-1

- **Title**: Inserted task
- **File**: src/insert.py
- **Complete**: [ ]
- **Sprint Points**: 2

- **User Story (business-facing)**: Inserted story.
- **Outcome (what this delivers)**: Inserted outcome.

#### Prompt:

```markdown
**Objective:** Inserted objective.
```
"""

SAMPLE_SPEC_REFS_TASK = """\
## Tasks

### Task ID: 028

- **Title**: UAT skill directory
- **File**: .claude/skills/autopilot-uat/SKILL.md
- **Complete**: [ ]
- **Sprint Points**: 2
- **Spec References**: UAT Discovery: /autopilot-uat Skill Architecture, YAML Frontmatter

- **User Story (business-facing)**: Story.
- **Outcome (what this delivers)**: Outcome.

#### Prompt:

```markdown
**Objective:** Create it.
```
"""

SAMPLE_WARNING_POINTS = """\
## Tasks

### Task ID: 099

- **Title**: Unestimated task
- **File**: src/unknown.py
- **Complete**: [ ]
- **Sprint Points**: ⚠️

- **User Story (business-facing)**: Story.
- **Outcome (what this delivers)**: Outcome.

#### Prompt:

```markdown
Placeholder.
```
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_task_dir(tmp_path: Path) -> Path:
    """Create a minimal task directory with index + two task files."""
    task_dir = tmp_path / "tasks"
    task_dir.mkdir()
    (task_dir / "tasks-index.md").write_text(SAMPLE_INDEX, encoding="utf-8")
    (task_dir / "tasks-1.md").write_text(SAMPLE_TASK_FILE, encoding="utf-8")
    (task_dir / "tasks-2.md").write_text(SAMPLE_TASK_FILE_2, encoding="utf-8")
    return task_dir


# ---------------------------------------------------------------------------
# Tests: Task dataclass
# ---------------------------------------------------------------------------


class TestTaskModel:
    def test_defaults(self) -> None:
        t = Task(id="001", title="Test")
        assert t.id == "001"
        assert t.title == "Test"
        assert t.complete is False
        assert t.sprint_points == 0
        assert t.acceptance_criteria == []

    def test_frozen_raises_on_assign(self) -> None:
        t = Task(id="001", title="Test")
        with pytest.raises(AttributeError):
            t.id = "002"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Tests: TaskParser.parse_task_file
# ---------------------------------------------------------------------------


class TestParseTaskFile:
    def test_extracts_all_tasks(self, tmp_path: Path) -> None:
        f = tmp_path / "tasks-1.md"
        f.write_text(SAMPLE_TASK_FILE, encoding="utf-8")
        parser = TaskParser()
        tasks = parser.parse_task_file(f)
        assert len(tasks) == 2

    def test_first_task_fields(self, tmp_path: Path) -> None:
        f = tmp_path / "tasks-1.md"
        f.write_text(SAMPLE_TASK_FILE, encoding="utf-8")
        t = TaskParser().parse_task_file(f)[0]
        assert t.id == "001"
        assert t.title == "First task"
        assert t.file_path == "src/foo.py"
        assert t.complete is True
        assert t.sprint_points == 3
        assert "As a dev" in t.user_story
        assert "Delivers X" in t.outcome

    def test_acceptance_criteria_extracted(self, tmp_path: Path) -> None:
        f = tmp_path / "tasks-1.md"
        f.write_text(SAMPLE_TASK_FILE, encoding="utf-8")
        t = TaskParser().parse_task_file(f)[0]
        assert len(t.acceptance_criteria) == 2
        assert "Criterion A" in t.acceptance_criteria[0]

    def test_second_task_pending(self, tmp_path: Path) -> None:
        f = tmp_path / "tasks-1.md"
        f.write_text(SAMPLE_TASK_FILE, encoding="utf-8")
        t = TaskParser().parse_task_file(f)[1]
        assert t.id == "002"
        assert t.complete is False
        assert t.sprint_points == 5

    def test_spec_references_parsed(self, tmp_path: Path) -> None:
        f = tmp_path / "task.md"
        f.write_text(SAMPLE_SPEC_REFS_TASK, encoding="utf-8")
        t = TaskParser().parse_task_file(f)[0]
        assert len(t.spec_references) == 2
        assert "YAML Frontmatter" in t.spec_references[1]

    def test_warning_sprint_points(self, tmp_path: Path) -> None:
        f = tmp_path / "task.md"
        f.write_text(SAMPLE_WARNING_POINTS, encoding="utf-8")
        t = TaskParser().parse_task_file(f)[0]
        assert isinstance(t.sprint_points, str)

    def test_decimal_task_id(self, tmp_path: Path) -> None:
        f = tmp_path / "task.md"
        f.write_text(SAMPLE_DECIMAL_TASK_FILE, encoding="utf-8")
        t = TaskParser().parse_task_file(f)[0]
        assert t.id == "002-1"
        assert t.sprint_points == 2


# ---------------------------------------------------------------------------
# Tests: TaskParser.parse_task_index
# ---------------------------------------------------------------------------


class TestParseTaskIndex:
    def test_summary_stats(self, tmp_path: Path) -> None:
        f = tmp_path / "tasks-index.md"
        f.write_text(SAMPLE_INDEX, encoding="utf-8")
        idx = TaskParser().parse_task_index(f)
        assert idx.total_tasks == 4
        assert idx.pending == 3
        assert idx.complete == 1
        assert idx.total_points == 14
        assert idx.points_complete == 3

    def test_file_index_entries(self, tmp_path: Path) -> None:
        f = tmp_path / "tasks-index.md"
        f.write_text(SAMPLE_INDEX, encoding="utf-8")
        idx = TaskParser().parse_task_index(f)
        assert len(idx.file_index) == 2
        e = idx.file_index[0]
        assert e.file == "tasks-1.md"
        assert e.start_id == "001"
        assert e.end_id == "002"
        assert e.task_count == 2
        assert e.points == 8


# ---------------------------------------------------------------------------
# Tests: find_next_pending / find_task_by_id
# ---------------------------------------------------------------------------


class TestFindTasks:
    def test_find_next_pending_skips_complete(self, tmp_path: Path) -> None:
        task_dir = _write_task_dir(tmp_path)
        t = TaskParser().find_next_pending(task_dir)
        assert t is not None
        assert t.id == "002"

    def test_find_next_pending_no_index(self, tmp_path: Path) -> None:
        assert TaskParser().find_next_pending(tmp_path) is None

    def test_find_task_by_id_found(self, tmp_path: Path) -> None:
        task_dir = _write_task_dir(tmp_path)
        t = TaskParser().find_task_by_id(task_dir, "003")
        assert t is not None
        assert t.title == "Third task"

    def test_find_task_by_id_leading_zeros(self, tmp_path: Path) -> None:
        task_dir = _write_task_dir(tmp_path)
        t = TaskParser().find_task_by_id(task_dir, "001")
        assert t is not None
        assert t.title == "First task"

    def test_find_task_by_id_not_found(self, tmp_path: Path) -> None:
        task_dir = _write_task_dir(tmp_path)
        assert TaskParser().find_task_by_id(task_dir, "999") is None

    def test_find_decimal_task_id(self, tmp_path: Path) -> None:
        """Decimal IDs like 002-1 should be locatable."""
        task_dir = _write_task_dir(tmp_path)
        # Add the decimal task to tasks-1.md
        content = (task_dir / "tasks-1.md").read_text()
        content += "\n" + SAMPLE_DECIMAL_TASK_FILE
        (task_dir / "tasks-1.md").write_text(content, encoding="utf-8")
        t = TaskParser().find_task_by_id(task_dir, "002-1")
        assert t is not None
        assert t.title == "Inserted task"


# ---------------------------------------------------------------------------
# Tests: update_task_status
# ---------------------------------------------------------------------------


class TestUpdateTaskStatus:
    def test_mark_complete(self, tmp_path: Path) -> None:
        task_dir = _write_task_dir(tmp_path)
        update_task_status(task_dir, "002", complete=True)

        # Verify task file updated
        tasks = TaskParser().parse_task_file(task_dir / "tasks-1.md")
        t = [t for t in tasks if t.id == "002"][0]
        assert t.complete is True

        # Verify index updated
        idx = TaskParser().parse_task_index(task_dir / "tasks-index.md")
        assert idx.pending == 2
        assert idx.complete == 2
        assert idx.points_complete == 8  # was 3, +5

    def test_mark_incomplete(self, tmp_path: Path) -> None:
        task_dir = _write_task_dir(tmp_path)
        update_task_status(task_dir, "001", complete=False)

        tasks = TaskParser().parse_task_file(task_dir / "tasks-1.md")
        t = [t for t in tasks if t.id == "001"][0]
        assert t.complete is False

        idx = TaskParser().parse_task_index(task_dir / "tasks-index.md")
        assert idx.pending == 4
        assert idx.complete == 0
        assert idx.points_complete == 0

    def test_missing_index_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            update_task_status(tmp_path, "001", complete=True)

    def test_unknown_task_raises(self, tmp_path: Path) -> None:
        task_dir = _write_task_dir(tmp_path)
        with pytest.raises(ValueError, match="not found"):
            update_task_status(task_dir, "999", complete=True)
