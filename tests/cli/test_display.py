"""Tests for autopilot.cli.display (Task 009)."""

from __future__ import annotations

from io import StringIO

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from autopilot.cli.display import (
    console,
    format_sprint_points,
    format_status,
    notification,
    progress_bar,
    project_table,
    status_panel,
    task_board,
)


class TestConsole:
    def test_width_is_80(self) -> None:
        assert console.width == 80


class TestProjectTable:
    def test_returns_table(self) -> None:
        result = project_table([])
        assert isinstance(result, Table)

    def test_renders_projects(self) -> None:
        projects = [
            {"name": "foo", "type": "python", "path": "/tmp/foo"},
            {"name": "bar", "type": "typescript", "path": "/tmp/bar"},
        ]
        table = project_table(projects)
        buf = StringIO()
        Console(file=buf, width=80).print(table)
        output = buf.getvalue()
        assert "foo" in output
        assert "bar" in output

    def test_handles_empty_list(self) -> None:
        table = project_table([])
        buf = StringIO()
        Console(file=buf, width=80).print(table)
        assert "Projects" in buf.getvalue()


class TestTaskBoard:
    def test_returns_table(self) -> None:
        result = task_board([])
        assert isinstance(result, Table)

    def test_renders_tasks(self) -> None:
        tasks = [
            {"id": "001", "title": "Setup", "status": "completed", "points": 3},
        ]
        table = task_board(tasks)
        buf = StringIO()
        Console(file=buf, width=80).print(table)
        output = buf.getvalue()
        assert "001" in output
        assert "Setup" in output

    def test_filter_status(self) -> None:
        tasks = [
            {"id": "001", "title": "Done", "status": "completed", "points": 3},
            {"id": "002", "title": "Pending", "status": "todo", "points": 5},
        ]
        table = task_board(tasks, filter_status="completed")
        buf = StringIO()
        Console(file=buf, width=80).print(table)
        output = buf.getvalue()
        assert "Done" in output
        assert "Pending" not in output


class TestStatusPanel:
    def test_returns_panel(self) -> None:
        result = status_panel("Test", "content")
        assert isinstance(result, Panel)

    def test_panel_title(self) -> None:
        panel = status_panel("My Title", "body text", "running")
        assert panel.title == "My Title"


class TestProgressBar:
    def test_creates_progress(self) -> None:
        p = progress_bar("Working...", 100)
        assert p is not None

    def test_pre_adds_task(self) -> None:
        p = progress_bar("Processing", 50)
        assert len(p.tasks) == 1
        assert p.tasks[0].total == 50


class TestFormatSprintPoints:
    def test_low_points(self) -> None:
        result = format_sprint_points(1)
        assert "1" in result
        assert "points.low" in result

    def test_mid_points(self) -> None:
        result = format_sprint_points(3)
        assert "3" in result
        assert "points.mid" in result

    def test_high_points(self) -> None:
        result = format_sprint_points(8)
        assert "8" in result
        assert "points.high" in result

    def test_invalid_points(self) -> None:
        result = format_sprint_points(None)
        assert "?" in result


class TestFormatStatus:
    def test_running(self) -> None:
        result = format_status("running")
        assert "status.running" in result

    def test_completed(self) -> None:
        result = format_status("completed")
        assert "status.completed" in result

    def test_failed(self) -> None:
        result = format_status("failed")
        assert "status.failed" in result

    def test_unknown_status(self) -> None:
        result = format_status("custom")
        assert result == "custom"


class TestNotification:
    def test_info_notification(self) -> None:
        buf = StringIO()
        test_console = Console(file=buf, width=80)
        # Monkey-patch console temporarily
        import autopilot.cli.display as display_mod

        orig = display_mod.console
        display_mod.console = test_console
        try:
            notification("info", "Test message")
            output = buf.getvalue()
            assert "INFO" in output
            assert "Test message" in output
        finally:
            display_mod.console = orig

    def test_error_notification(self) -> None:
        buf = StringIO()
        test_console = Console(file=buf, width=80)
        import autopilot.cli.display as display_mod

        orig = display_mod.console
        display_mod.console = test_console
        try:
            notification("error", "Something failed")
            output = buf.getvalue()
            assert "ERR" in output
        finally:
            display_mod.console = orig
