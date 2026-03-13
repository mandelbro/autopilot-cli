"""Tests for sprint plan and close CLI commands (Task 026)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
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

    def test_plan_then_close(self, task_env: Path) -> None:
        """Plan a sprint via CLI, then close it — no monkey-patching needed."""
        db_path = str(task_env / "test.db")

        # Step 1: Plan a sprint
        plan_result = runner.invoke(
            app,
            ["task", "sprint", "plan", "--task-dir", "tasks", "--db-path", db_path],
        )
        assert plan_result.exit_code == 0

        # Extract the sprint ID from the plan output
        import re

        m = re.search(r"ID:\s*(\w+)", plan_result.output)
        assert m is not None, f"Could not find sprint ID in output: {plan_result.output}"
        sprint_id = m.group(1)

        # Step 2: Close the sprint (separate CLI invocation, fresh process)
        close_result = runner.invoke(
            app,
            [
                "task",
                "sprint",
                "close",
                "--sprint-id",
                sprint_id,
                "--completed",
                "002",
                "--task-dir",
                "tasks",
                "--db-path",
                db_path,
            ],
        )
        assert close_result.exit_code == 0
        assert "Sprint Summary" in close_result.output
        assert "Velocity recorded" in close_result.output

    def test_close_shows_carryover(self, task_env: Path) -> None:
        """Closing with incomplete tasks shows carryover table."""
        db_path = str(task_env / "test.db")

        # Plan a sprint first
        plan_result = runner.invoke(
            app,
            ["task", "sprint", "plan", "--task-dir", "tasks", "--db-path", db_path],
        )
        assert plan_result.exit_code == 0

        import re

        m = re.search(r"ID:\s*(\w+)", plan_result.output)
        assert m is not None
        sprint_id = m.group(1)

        # Close with only 1 of 3 tasks completed — should show carryover
        close_result = runner.invoke(
            app,
            [
                "task",
                "sprint",
                "close",
                "--sprint-id",
                sprint_id,
                "--completed",
                "002",
                "--task-dir",
                "tasks",
                "--db-path",
                db_path,
            ],
        )
        assert close_result.exit_code == 0
        assert "Carried Over" in close_result.output
