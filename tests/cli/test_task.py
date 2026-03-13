"""Tests for autopilot.cli.task (Tasks 022-023)."""

from __future__ import annotations

import typing

import pytest

if typing.TYPE_CHECKING:
    from pathlib import Path
from typer.testing import CliRunner

from autopilot.cli.task import (
    FIBONACCI_POINTS,
    _get_all_tasks,
    _new_task_file_header,
    _next_task_id,
    _render_task_markdown,
    _target_task_file,
    validate_fibonacci,
)
from autopilot.core.task import TaskFileEntry, TaskIndex, TaskParser

runner = CliRunner()

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_INDEX_MD = """\
## Overall Project Task Summary

- **Total Tasks**: 2
- **Pending**: 1
- **Complete**: 1
- **Total Points**: 8
- **Points Complete**: 3

## Task File Index

- `tasks/tasks-1.md`: Contains Tasks 001 - 002 (2 tasks, 8 points)
"""

SAMPLE_TASKS_MD = """\
## Summary (tasks-1.md)

- **Tasks in this file**: 2
- **Task IDs**: 001 - 002
- **Total Points**: 8

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
"""


@pytest.fixture()
def task_dir(tmp_path: Path) -> Path:
    """Create a temporary task directory with sample files."""
    td = tmp_path / "tasks"
    td.mkdir()
    (td / "tasks-index.md").write_text(SAMPLE_INDEX_MD, encoding="utf-8")
    (td / "tasks-1.md").write_text(SAMPLE_TASKS_MD, encoding="utf-8")
    return td


# ---------------------------------------------------------------------------
# Unit tests: helpers
# ---------------------------------------------------------------------------


class TestValidateFibonacci:
    def test_valid_points(self) -> None:
        for p in FIBONACCI_POINTS:
            assert validate_fibonacci(p) == p

    def test_invalid_points_raises(self) -> None:
        import typer

        with pytest.raises(typer.BadParameter):
            validate_fibonacci(4)

    def test_zero_raises(self) -> None:
        import typer

        with pytest.raises(typer.BadParameter):
            validate_fibonacci(0)


class TestNextTaskId:
    def test_sequential(self) -> None:
        index = TaskIndex(total_tasks=9)
        assert _next_task_id(index) == "010"

    def test_triple_digits(self) -> None:
        index = TaskIndex(total_tasks=99)
        assert _next_task_id(index) == "100"


class TestTargetTaskFile:
    def test_empty_index(self, tmp_path: Path) -> None:
        index = TaskIndex(file_index=[])
        path, is_new = _target_task_file(tmp_path, index)
        assert path == tmp_path / "tasks-1.md"
        assert is_new is True

    def test_existing_file_not_full(self, tmp_path: Path) -> None:
        index = TaskIndex(file_index=[TaskFileEntry("tasks-1.md", "001", "005", 5, 15)])
        path, is_new = _target_task_file(tmp_path, index)
        assert path == tmp_path / "tasks-1.md"
        assert is_new is False

    def test_full_file_creates_new(self, tmp_path: Path) -> None:
        index = TaskIndex(file_index=[TaskFileEntry("tasks-1.md", "001", "010", 10, 30)])
        path, is_new = _target_task_file(tmp_path, index)
        assert path == tmp_path / "tasks-2.md"
        assert is_new is True


class TestRenderTaskMarkdown:
    def test_contains_id_and_title(self) -> None:
        md = _render_task_markdown(
            task_id="042",
            title="My Task",
            file_path="src/foo.py",
            user_story="As a dev, I want X.",
            outcome="X works.",
            sprint_points=3,
            prompt_text="Do the thing.",
        )
        assert "### Task ID: 042" in md
        assert "- **Title**: My Task" in md
        assert "- **Complete**: [ ]" in md
        assert "- **Sprint Points**: 3" in md

    def test_default_prompt_when_empty(self) -> None:
        md = _render_task_markdown(
            task_id="001",
            title="Setup",
            file_path="src/a.py",
            user_story="story",
            outcome="result",
            sprint_points=1,
            prompt_text="",
        )
        assert "**Objective:** Setup" in md


class TestNewTaskFileHeader:
    def test_header_format(self) -> None:
        header = _new_task_file_header("tasks-3.md", "021", 5)
        assert "## Summary (tasks-3.md)" in header
        assert "- **Tasks in this file**: 1" in header
        assert "- **Task IDs**: 021 - 021" in header


class TestGetAllTasks:
    def test_returns_all_tasks(self, task_dir: Path) -> None:
        parser = TaskParser()
        tasks = _get_all_tasks(parser, task_dir)
        assert len(tasks) == 2
        assert tasks[0].id == "001"
        assert tasks[1].id == "002"

    def test_empty_dir(self, tmp_path: Path) -> None:
        parser = TaskParser()
        tasks = _get_all_tasks(parser, tmp_path)
        assert tasks == []


# ---------------------------------------------------------------------------
# Integration tests: CLI commands via typer test runner
# ---------------------------------------------------------------------------


class TestTaskListCommand:
    def _make_app(self, task_dir: Path) -> typing.Any:
        """Build a Typer app with task commands pointing at the fixture dir."""
        import typer as _typer

        from autopilot.cli import task as task_mod

        app = _typer.Typer()
        original_resolve = task_mod._resolve_task_dir
        task_mod._resolve_task_dir = lambda: task_dir  # type: ignore[assignment]

        from autopilot.cli.task import register_task_commands

        register_task_commands(app)
        # Restore after registration (commands capture closure)
        # We need the monkey-patch to persist for invocation, so we don't restore
        self._cleanup = lambda: setattr(  # noqa: B010
            task_mod, "_resolve_task_dir", original_resolve
        )
        return app

    def test_list_all(self, task_dir: Path) -> None:
        app = self._make_app(task_dir)
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "First task" in result.output
        assert "Second task" in result.output
        assert "Summary" in result.output
        self._cleanup()

    def test_list_pending(self, task_dir: Path) -> None:
        app = self._make_app(task_dir)
        result = runner.invoke(app, ["list", "--status", "pending"])
        assert result.exit_code == 0
        assert "Second task" in result.output
        # First task is complete, should not appear in table rows
        # (but may appear in summary count)
        self._cleanup()

    def test_list_complete(self, task_dir: Path) -> None:
        app = self._make_app(task_dir)
        result = runner.invoke(app, ["list", "--status", "complete"])
        assert result.exit_code == 0
        assert "First task" in result.output
        self._cleanup()

    def test_list_verbose(self, task_dir: Path) -> None:
        app = self._make_app(task_dir)
        result = runner.invoke(app, ["list", "--verbose"])
        assert result.exit_code == 0
        # verbose shows user stories
        assert "feature" in result.output.lower() or "dev" in result.output.lower()
        self._cleanup()

    def test_board_alias(self, task_dir: Path) -> None:
        app = self._make_app(task_dir)
        result = runner.invoke(app, ["board"])
        assert result.exit_code == 0
        assert "Task Board" in result.output
        self._cleanup()

    def test_no_index_exits(self, tmp_path: Path) -> None:
        app = self._make_app(tmp_path)
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 1
        self._cleanup()


class TestTaskCreateCommand:
    def _make_app(self, task_dir: Path) -> typing.Any:
        import typer as _typer

        from autopilot.cli import task as task_mod

        app = _typer.Typer()
        original_resolve = task_mod._resolve_task_dir
        task_mod._resolve_task_dir = lambda: task_dir  # type: ignore[assignment]

        from autopilot.cli.task import register_task_commands

        register_task_commands(app)
        self._cleanup = lambda: setattr(  # noqa: B010
            task_mod, "_resolve_task_dir", original_resolve
        )
        return app

    def test_create_non_interactive(self, task_dir: Path) -> None:
        app = self._make_app(task_dir)
        result = runner.invoke(
            app,
            [
                "create",
                "--title",
                "New Feature",
                "--file",
                "src/new.py",
                "--points",
                "3",
                "--user-story",
                "As a dev, I want new feature.",
                "--outcome",
                "New feature works.",
                "--prompt",
                "Build the new feature.",
            ],
        )
        assert result.exit_code == 0
        assert "003" in result.output
        assert "New Feature" in result.output

        # Verify file was updated
        task_file = task_dir / "tasks-1.md"
        content = task_file.read_text()
        assert "### Task ID: 003" in content
        assert "New Feature" in content

        # Verify index was updated
        index_content = (task_dir / "tasks-index.md").read_text()
        assert "**Total Tasks**: 3" in index_content
        assert "**Pending**: 2" in index_content
        self._cleanup()

    def test_create_invalid_points(self, task_dir: Path) -> None:
        app = self._make_app(task_dir)
        result = runner.invoke(
            app,
            [
                "create",
                "--title",
                "Bad",
                "--file",
                "src/x.py",
                "--points",
                "4",
                "--user-story",
                "story",
                "--outcome",
                "out",
            ],
        )
        assert result.exit_code != 0
        self._cleanup()

    def test_create_triggers_new_file(self, task_dir: Path) -> None:
        """When the current file has 10 tasks, a new file should be created."""
        # Rewrite the index to say the file has 10 tasks
        index_md = """\
## Overall Project Task Summary

- **Total Tasks**: 10
- **Pending**: 5
- **Complete**: 5
- **Total Points**: 30
- **Points Complete**: 15

## Task File Index

- `tasks/tasks-1.md`: Contains Tasks 001 - 010 (10 tasks, 30 points)
"""
        (task_dir / "tasks-index.md").write_text(index_md, encoding="utf-8")

        app = self._make_app(task_dir)
        result = runner.invoke(
            app,
            [
                "create",
                "--title",
                "Overflow",
                "--file",
                "src/overflow.py",
                "--points",
                "2",
                "--user-story",
                "story",
                "--outcome",
                "result",
                "--prompt",
                "Do overflow.",
            ],
        )
        assert result.exit_code == 0
        assert (task_dir / "tasks-2.md").exists()

        new_content = (task_dir / "tasks-2.md").read_text()
        assert "### Task ID: 011" in new_content
        self._cleanup()

    def test_create_no_index(self, tmp_path: Path) -> None:
        app = self._make_app(tmp_path)
        result = runner.invoke(
            app,
            ["create", "--title", "X", "--file", "f", "--points", "1"],
        )
        assert result.exit_code == 1
        self._cleanup()
