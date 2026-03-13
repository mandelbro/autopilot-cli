"""Tests for sprint plan and close CLI commands (Task 026)."""

from __future__ import annotations

import typing

import pytest

if typing.TYPE_CHECKING:
    from pathlib import Path

from typer.testing import CliRunner

from autopilot.cli.app import app

runner = CliRunner()

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_INDEX_MD = """\
## Overall Project Task Summary

- **Total Tasks**: 4
- **Pending**: 3
- **Complete**: 1
- **Total Points**: 14
- **Points Complete**: 3

## Task File Index

- `tasks/tasks-1.md`: Contains Tasks 001 - 004 (4 tasks, 14 points)
"""

SAMPLE_TASKS_MD = """\
## Summary (tasks-1.md)

- **Tasks in this file**: 4
- **Task IDs**: 001 - 004
- **Total Points**: 14

---

## Tasks

### Task ID: 001

- **Title**: First task
- **File**: src/first.py
- **Complete**: [x]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a dev, I want feature A.
- **Outcome (what this delivers)**: Feature A works.

#### Prompt:

```markdown
**Objective:** Implement feature A.
```

---

### Task ID: 002

- **Title**: Second task
- **File**: src/second.py
- **Complete**: [ ]
- **Sprint Points**: 5

- **User Story (business-facing)**: As a dev, I want feature B.
- **Outcome (what this delivers)**: Feature B works.

#### Prompt:

```markdown
**Objective:** Implement feature B.
```

---

### Task ID: 003

- **Title**: Third task
- **File**: src/third.py
- **Complete**: [ ]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a dev, I want feature C.
- **Outcome (what this delivers)**: Feature C works.

#### Prompt:

```markdown
**Objective:** Implement feature C.
```

---

### Task ID: 004

- **Title**: Fourth task
- **File**: src/fourth.py
- **Complete**: [ ]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a dev, I want feature D.
- **Outcome (what this delivers)**: Feature D works.

#### Prompt:

```markdown
**Objective:** Implement feature D.
```
"""


@pytest.fixture()
def task_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Set up a temporary task directory with sample data."""
    task_dir = tmp_path / "tasks"
    task_dir.mkdir()
    (task_dir / "tasks-index.md").write_text(SAMPLE_INDEX_MD, encoding="utf-8")
    (task_dir / "tasks-1.md").write_text(SAMPLE_TASKS_MD, encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    # Pre-create the default project so FK constraints pass on velocity inserts
    from autopilot.utils.db import Database

    db = Database(tmp_path / "test.db")
    db.insert_project(id="default", name="default", path=str(tmp_path), type="python")

    return tmp_path


# ---------------------------------------------------------------------------
# sprint plan tests
# ---------------------------------------------------------------------------


class TestSprintPlan:
    """Tests for ``task sprint plan``."""

    def test_plan_shows_velocity_and_tasks(self, task_env: Path) -> None:
        db_path = str(task_env / "test.db")
        result = runner.invoke(
            app,
            ["task", "sprint", "plan", "--task-dir", "tasks", "--db-path", db_path],
        )
        assert result.exit_code == 0
        assert "Velocity Forecast" in result.output
        assert "Pending Tasks" in result.output
        assert "Selected Tasks" in result.output

    def test_plan_shows_capacity(self, task_env: Path) -> None:
        db_path = str(task_env / "test.db")
        result = runner.invoke(
            app,
            ["task", "sprint", "plan", "--task-dir", "tasks", "--db-path", db_path],
        )
        assert result.exit_code == 0
        # Default capacity is 13 (no history)
        assert "13" in result.output

    def test_plan_selects_tasks_up_to_capacity(self, task_env: Path) -> None:
        db_path = str(task_env / "test.db")
        result = runner.invoke(
            app,
            ["task", "sprint", "plan", "--task-dir", "tasks", "--db-path", db_path],
        )
        assert result.exit_code == 0
        # With capacity 13, tasks 002(5) + 003(3) + 004(3) = 11 should fit
        assert "Second task" in result.output
        assert "Third task" in result.output
        assert "Fourth task" in result.output

    def test_plan_missing_index(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        db_path = str(tmp_path / "test.db")
        result = runner.invoke(
            app,
            [
                "task",
                "sprint",
                "plan",
                "--task-dir",
                "nonexistent",
                "--db-path",
                db_path,
            ],
        )
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# sprint close tests
# ---------------------------------------------------------------------------


class TestSprintClose:
    """Tests for ``task sprint close``."""

    def test_close_no_active_sprint(self, task_env: Path) -> None:
        db_path = str(task_env / "test.db")
        result = runner.invoke(
            app,
            [
                "task",
                "sprint",
                "close",
                "--sprint-id",
                "nonexistent",
                "--task-dir",
                "tasks",
                "--db-path",
                db_path,
            ],
        )
        assert result.exit_code == 1
        assert "No active sprint" in result.output

    def test_plan_then_close(self, task_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Plan a sprint, then close it with some completed tasks."""
        from unittest.mock import patch

        from autopilot.core.sprint import SprintPlanner
        from autopilot.core.task import TaskParser
        from autopilot.utils.db import Database

        db_path = task_env / "test.db"
        db = Database(db_path)
        planner = SprintPlanner(db, "default")
        parser = TaskParser()

        task_dir = task_env / "tasks"
        index = parser.parse_task_index(task_dir / "tasks-index.md")
        all_tasks = []
        for entry in index.file_index:
            fp = task_dir / entry.file
            if fp.exists():
                all_tasks.extend(parser.parse_task_file(fp))

        pending = [t for t in all_tasks if not t.complete]
        sprint = planner.plan_sprint(pending, 13)

        # Patch SprintPlanner so the CLI's new instance shares the active sprint
        original_init = SprintPlanner.__init__

        def patched_init(self: SprintPlanner, *a: object, **kw: object) -> None:
            original_init(self, *a, **kw)  # type: ignore[arg-type]
            self._active = sprint

        with patch.object(SprintPlanner, "__init__", patched_init):
            result = runner.invoke(
                app,
                [
                    "task",
                    "sprint",
                    "close",
                    "--sprint-id",
                    sprint.id,
                    "--completed",
                    "002",
                    "--task-dir",
                    "tasks",
                    "--db-path",
                    str(db_path),
                ],
            )
        assert result.exit_code == 0
        assert "Sprint Summary" in result.output
        assert "Velocity recorded" in result.output

    def test_close_shows_carryover(self, task_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Closing with incomplete tasks shows carryover table."""
        from unittest.mock import patch

        from autopilot.core.sprint import SprintPlanner
        from autopilot.core.task import TaskParser
        from autopilot.utils.db import Database

        db_path = task_env / "test.db"
        db = Database(db_path)
        planner = SprintPlanner(db, "default")
        parser = TaskParser()

        task_dir = task_env / "tasks"
        index = parser.parse_task_index(task_dir / "tasks-index.md")
        all_tasks = []
        for entry in index.file_index:
            fp = task_dir / entry.file
            if fp.exists():
                all_tasks.extend(parser.parse_task_file(fp))

        pending = [t for t in all_tasks if not t.complete]
        sprint = planner.plan_sprint(pending, 13)

        original_init = SprintPlanner.__init__

        def patched_init(self: SprintPlanner, *a: object, **kw: object) -> None:
            original_init(self, *a, **kw)  # type: ignore[arg-type]
            self._active = sprint

        with patch.object(SprintPlanner, "__init__", patched_init):
            result = runner.invoke(
                app,
                [
                    "task",
                    "sprint",
                    "close",
                    "--sprint-id",
                    sprint.id,
                    "--completed",
                    "002",
                    "--task-dir",
                    "tasks",
                    "--db-path",
                    str(db_path),
                ],
            )
        assert result.exit_code == 0
        assert "Carried Over" in result.output
