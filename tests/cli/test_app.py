"""Tests for autopilot.cli.app (Task 008)."""

from __future__ import annotations

from typer.testing import CliRunner

from autopilot.cli.app import app

runner = CliRunner()


class TestVersionFlag:
    def test_version_shows_version(self) -> None:
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "autopilot" in result.output
        assert "0.1.0" in result.output

    def test_version_short_flag(self) -> None:
        result = runner.invoke(app, ["-V"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output


class TestHelp:
    def test_help_shows_all_groups(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        for group in ("project", "task", "session", "enforce", "agent", "config", "report"):
            assert group in result.output

    def test_help_shows_top_level_commands(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        for cmd in ("init", "watch", "ask", "review", "migrate"):
            assert cmd in result.output


class TestSubcommandGroupHelp:
    def test_project_help(self) -> None:
        result = runner.invoke(app, ["project", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output

    def test_task_help(self) -> None:
        result = runner.invoke(app, ["task", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output

    def test_session_help(self) -> None:
        result = runner.invoke(app, ["session", "--help"])
        assert result.exit_code == 0
        assert "start" in result.output

    def test_enforce_help(self) -> None:
        result = runner.invoke(app, ["enforce", "--help"])
        assert result.exit_code == 0
        assert "check" in result.output

    def test_agent_help(self) -> None:
        result = runner.invoke(app, ["agent", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output

    def test_config_help(self) -> None:
        result = runner.invoke(app, ["config", "--help"])
        assert result.exit_code == 0
        assert "show" in result.output

    def test_report_help(self) -> None:
        result = runner.invoke(app, ["report", "--help"])
        assert result.exit_code == 0
        assert "sprint" in result.output


class TestNoArgsEntersRepl:
    def test_no_args_shows_repl_or_help(self) -> None:
        result = runner.invoke(app, [])
        # With invoke_without_command=True, no subcommand triggers REPL stub
        assert result.exit_code == 0 or "Usage" in result.output


class TestStubCommands:
    def test_init_help(self) -> None:
        result = runner.invoke(app, ["init", "--help"])
        assert result.exit_code == 0
        assert "init" in result.output.lower()

    def test_watch_stub(self) -> None:
        result = runner.invoke(app, ["watch"])
        assert result.exit_code == 0

    def test_review_stub(self) -> None:
        result = runner.invoke(app, ["review"])
        assert result.exit_code == 0

    def test_migrate_no_repengine_layout(self) -> None:
        """Migrate exits with code 1 when no RepEngine layout is found."""
        result = runner.invoke(app, ["migrate"])
        assert result.exit_code == 1
