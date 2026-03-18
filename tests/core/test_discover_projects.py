"""Tests for autopilot.core.discover_projects — external task project discovery."""

from __future__ import annotations

from pathlib import Path

import pytest

from autopilot.core.discover_projects import (
    DiscoverResult,
    discover_task_project,
    scan_for_task_projects,
)


# ---------------------------------------------------------------------------
# Fixtures: create realistic task-workflow-system directories
# ---------------------------------------------------------------------------

SAMPLE_INDEX = """\
## Overall Project Task Summary

- **Total Tasks**: 10
- **Pending**: 7
- **Complete**: 3
- **Total Points**: 30
- **Points Complete**: 9

## Project: Sample Hooks Project

- Task Source File: `docs/discovery/discovery-hooks.md`
- **Description**: A sample project for testing discovery

## Task File Index

- `tasks/tasks-1.md`: Contains Tasks 000 - 004 (5 tasks, 15 points)
- `tasks/tasks-2.md`: Contains Tasks 005 - 009 (5 tasks, 15 points)
"""

SAMPLE_TASK_FILE = """\
## Summary (tasks-1.md)

- **Tasks in this file**: 5
- **Task IDs**: 000 - 004
- **Total Points**: 15

## Tasks

### Task ID: 000

- **Title**: Setup foundation
- **File**: src/foundation.py
- **Complete**: [x]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a developer, I want a foundation, so that I can build on it.
- **Outcome (what this delivers)**: Basic project structure.

#### Prompt:

```markdown
**Objective:** Create foundation module
```

### Task ID: 001

- **Title**: Add core logic
- **File**: src/core.py
- **Complete**: [ ]
- **Sprint Points**: 5

- **User Story (business-facing)**: As a developer, I want core logic, so that the app works.
- **Outcome (what this delivers)**: Working core module.

#### Prompt:

```markdown
**Objective:** Implement core logic
```
"""


@pytest.fixture
def external_project(tmp_path: Path) -> Path:
    """Create a realistic external project with tasks/ directory."""
    project = tmp_path / "my-external-project"
    project.mkdir()
    tasks_dir = project / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "tasks-index.md").write_text(SAMPLE_INDEX)
    (tasks_dir / "tasks-1.md").write_text(SAMPLE_TASK_FILE)
    return project


@pytest.fixture
def empty_project(tmp_path: Path) -> Path:
    """A project directory with no tasks."""
    project = tmp_path / "empty-project"
    project.mkdir()
    return project


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """A workspace with multiple projects, some with tasks."""
    ws = tmp_path / "workspace"
    ws.mkdir()

    # Project A — has tasks
    proj_a = ws / "project-a"
    proj_a.mkdir()
    tasks_a = proj_a / "tasks"
    tasks_a.mkdir()
    (tasks_a / "tasks-index.md").write_text(SAMPLE_INDEX)

    # Project B — no tasks
    proj_b = ws / "project-b"
    proj_b.mkdir()

    # Project C — has tasks
    proj_c = ws / "project-c"
    proj_c.mkdir()
    tasks_c = proj_c / "tasks"
    tasks_c.mkdir()
    (tasks_c / "tasks-index.md").write_text(SAMPLE_INDEX)

    return ws


# ---------------------------------------------------------------------------
# discover_task_project
# ---------------------------------------------------------------------------


class TestDiscoverTaskProject:
    def test_discovers_valid_project(self, external_project: Path) -> None:
        result = discover_task_project(external_project)
        assert result is not None
        assert result.name == "my-external-project"
        assert result.task_dir == str(external_project / "tasks")
        assert result.total_tasks == 10
        assert result.pending == 7
        assert result.complete == 3
        assert result.total_points == 30

    def test_returns_none_for_no_tasks(self, empty_project: Path) -> None:
        result = discover_task_project(empty_project)
        assert result is None

    def test_returns_none_for_missing_index(self, tmp_path: Path) -> None:
        project = tmp_path / "no-index"
        project.mkdir()
        (project / "tasks").mkdir()
        # tasks/ exists but no tasks-index.md
        result = discover_task_project(project)
        assert result is None

    def test_returns_none_for_nonexistent_path(self, tmp_path: Path) -> None:
        result = discover_task_project(tmp_path / "does-not-exist")
        assert result is None

    def test_custom_name_override(self, external_project: Path) -> None:
        result = discover_task_project(external_project, name="custom-name")
        assert result is not None
        assert result.name == "custom-name"

    def test_extracts_project_description(self, external_project: Path) -> None:
        result = discover_task_project(external_project)
        assert result is not None
        assert "sample project" in result.description.lower()


# ---------------------------------------------------------------------------
# scan_for_task_projects
# ---------------------------------------------------------------------------


class TestScanForTaskProjects:
    def test_finds_projects_in_workspace(self, workspace: Path) -> None:
        results = scan_for_task_projects(workspace)
        assert len(results) == 2
        names = {r.name for r in results}
        assert "project-a" in names
        assert "project-c" in names

    def test_returns_empty_for_no_projects(self, tmp_path: Path) -> None:
        results = scan_for_task_projects(tmp_path)
        assert results == []

    def test_max_depth_limits_search(self, workspace: Path) -> None:
        # Create a deeply nested project that should be skipped at depth=0
        deep = workspace / "nested" / "deep" / "project-d"
        deep.mkdir(parents=True)
        tasks = deep / "tasks"
        tasks.mkdir()
        (tasks / "tasks-index.md").write_text(SAMPLE_INDEX)

        # depth=1 should find only immediate children
        results = scan_for_task_projects(workspace, max_depth=1)
        names = {r.name for r in results}
        assert "project-d" not in names


# ---------------------------------------------------------------------------
# DiscoverResult
# ---------------------------------------------------------------------------


class TestDiscoverResult:
    def test_dataclass_fields(self) -> None:
        result = DiscoverResult(
            name="test",
            path="/tmp/test",
            task_dir="/tmp/test/tasks",
            total_tasks=5,
            pending=3,
            complete=2,
            total_points=15,
            points_complete=6,
            description="A test project",
        )
        assert result.name == "test"
        assert result.total_tasks == 5
        assert result.description == "A test project"
