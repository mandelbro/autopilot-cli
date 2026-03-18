"""Tests for --project flag on task list/board commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from autopilot.cli.app import app
from autopilot.core.project import ProjectRegistry

runner = CliRunner()

SAMPLE_INDEX = """\
## Overall Project Task Summary

- **Total Tasks**: 3
- **Pending**: 2
- **Complete**: 1
- **Total Points**: 9
- **Points Complete**: 3

## Project: External Test

- **Description**: Test project

## Task File Index

- `tasks/tasks-1.md`: Contains Tasks 000 - 002 (3 tasks, 9 points)
"""

SAMPLE_TASKS = """\
## Summary (tasks-1.md)

- **Tasks in this file**: 3
- **Task IDs**: 000 - 002
- **Total Points**: 9

## Tasks

### Task ID: 000

- **Title**: Setup foundation
- **File**: src/foundation.py
- **Complete**: [x]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a dev, I want setup.
- **Outcome (what this delivers)**: Foundation.

#### Prompt:

```markdown
**Objective:** Create foundation
```

### Task ID: 001

- **Title**: Core logic
- **File**: src/core.py
- **Complete**: [ ]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a dev, I want core.
- **Outcome (what this delivers)**: Core module.

#### Prompt:

```markdown
**Objective:** Implement core
```

### Task ID: 002

- **Title**: Final polish
- **File**: src/polish.py
- **Complete**: [ ]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a dev, I want polish.
- **Outcome (what this delivers)**: Polish.

#### Prompt:

```markdown
**Objective:** Polish
```
"""


def _setup_external_project(tmp_path: Path) -> tuple[Path, Path]:
    """Create external project and register it. Returns (global_dir, project_path)."""
    global_dir = tmp_path / "global"
    global_dir.mkdir()

    project_path = tmp_path / "ext-project"
    project_path.mkdir()
    tasks_dir = project_path / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "tasks-index.md").write_text(SAMPLE_INDEX)
    (tasks_dir / "tasks-1.md").write_text(SAMPLE_TASKS)

    registry = ProjectRegistry(global_dir=global_dir)
    registry.register(
        "ext-project",
        str(project_path),
        "external",
        external=True,
        task_dir=str(tasks_dir),
    )
    return global_dir, project_path


class TestTaskListWithProjectFlag:
    def test_list_external_project_tasks(self, tmp_path: Path) -> None:
        global_dir, _project_path = _setup_external_project(tmp_path)

        with patch("autopilot.core.project.get_global_dir", return_value=global_dir):
            result = runner.invoke(
                app, ["task", "list", "--project", "ext-project"]
            )

        assert result.exit_code == 0
        assert "Setup foundation" in result.output
        assert "Core logic" in result.output
        assert "3 tasks" in result.output

    def test_list_unknown_project_fails(self, tmp_path: Path) -> None:
        global_dir = tmp_path / "global"
        global_dir.mkdir()

        with patch("autopilot.core.project.get_global_dir", return_value=global_dir):
            result = runner.invoke(
                app, ["task", "list", "--project", "nonexistent"]
            )

        assert result.exit_code != 0

    def test_board_with_project_flag(self, tmp_path: Path) -> None:
        global_dir, _project_path = _setup_external_project(tmp_path)

        with patch("autopilot.core.project.get_global_dir", return_value=global_dir):
            result = runner.invoke(
                app, ["task", "board", "--project", "ext-project"]
            )

        assert result.exit_code == 0
        assert "Setup foundation" in result.output


class TestProjectUnregister:
    def test_unregister_external_project(self, tmp_path: Path) -> None:
        global_dir, _project_path = _setup_external_project(tmp_path)

        with patch("autopilot.core.project.get_global_dir", return_value=global_dir):
            result = runner.invoke(
                app, ["project", "unregister", "ext-project"]
            )

        assert result.exit_code == 0
        registry = ProjectRegistry(global_dir=global_dir)
        assert registry.find_by_name("ext-project") is None

    def test_unregister_nonexistent_fails(self, tmp_path: Path) -> None:
        global_dir = tmp_path / "global"
        global_dir.mkdir()

        with patch("autopilot.core.project.get_global_dir", return_value=global_dir):
            result = runner.invoke(
                app, ["project", "unregister", "nonexistent"]
            )

        assert result.exit_code != 0
