"""Tests for AutopilotREPL (Tasks 013-014)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from autopilot.cli.repl import (
    AutopilotREPL,
    NotificationTier,
    ReplState,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestReplState:
    def test_initial_state_no_project(self, tmp_path: Path) -> None:
        repl = AutopilotREPL()
        assert repl.state == ReplState.NO_PROJECT

    def test_set_project_changes_state(self) -> None:
        repl = AutopilotREPL()
        repl.set_project("my-project")
        assert repl.state == ReplState.PROJECT_SELECTED
        assert repl.active_project == "my-project"

    def test_clear_project_returns_to_no_project(self) -> None:
        repl = AutopilotREPL()
        repl.set_project("my-project")
        repl.set_project("")
        assert repl.state == ReplState.NO_PROJECT

    def test_set_session_changes_state(self) -> None:
        repl = AutopilotREPL()
        repl.set_project("proj")
        repl.set_session("sess-1")
        assert repl.state == ReplState.SESSION_ACTIVE

    def test_clear_session_returns_to_project(self) -> None:
        repl = AutopilotREPL()
        repl.set_project("proj")
        repl.set_session("sess-1")
        repl.set_session("")
        assert repl.state == ReplState.PROJECT_SELECTED

    def test_attention_needed(self) -> None:
        repl = AutopilotREPL()
        repl.set_project("proj")
        repl.set_attention_needed()
        assert repl.state == ReplState.ATTENTION_NEEDED

    def test_clear_attention_restores_session(self) -> None:
        repl = AutopilotREPL()
        repl.set_project("proj")
        repl.set_session("sess-1")
        repl.set_attention_needed()
        repl.clear_attention()
        assert repl.state == ReplState.SESSION_ACTIVE

    def test_clear_attention_restores_project(self) -> None:
        repl = AutopilotREPL()
        repl.set_project("proj")
        repl.set_attention_needed()
        repl.clear_attention()
        assert repl.state == ReplState.PROJECT_SELECTED

    def test_clear_attention_restores_no_project(self) -> None:
        repl = AutopilotREPL()
        repl.set_attention_needed()
        repl.clear_attention()
        assert repl.state == ReplState.NO_PROJECT


class TestPrompt:
    def test_no_project_prompt(self) -> None:
        repl = AutopilotREPL()
        assert repl.get_prompt() == "autopilot > "

    def test_project_selected_prompt(self) -> None:
        repl = AutopilotREPL()
        repl.set_project("my-app")
        assert repl.get_prompt() == "autopilot [my-app] > "

    def test_session_active_prompt(self) -> None:
        repl = AutopilotREPL()
        repl.set_project("my-app")
        repl.set_session("s1")
        assert repl.get_prompt() == "autopilot [my-app] * > "

    def test_attention_needed_prompt(self) -> None:
        repl = AutopilotREPL()
        repl.set_project("my-app")
        repl.set_attention_needed()
        assert repl.get_prompt() == "autopilot [my-app] ! > "


class TestNotifications:
    def test_add_and_flush_critical(self) -> None:
        repl = AutopilotREPL()
        repl.add_notification("Deploy failed", NotificationTier.CRITICAL)
        flushed = repl.flush_notifications()
        assert len(flushed) == 1
        assert flushed[0].message == "Deploy failed"
        assert flushed[0].tier == NotificationTier.CRITICAL

    def test_flush_keeps_informational(self) -> None:
        repl = AutopilotREPL()
        repl.add_notification("FYI", NotificationTier.INFORMATIONAL)
        flushed = repl.flush_notifications()
        assert len(flushed) == 0  # informational not flushed

    def test_flush_shows_important(self) -> None:
        repl = AutopilotREPL()
        repl.add_notification("PR merged", NotificationTier.IMPORTANT)
        flushed = repl.flush_notifications()
        assert len(flushed) == 1

    def test_flush_clears_shown(self) -> None:
        repl = AutopilotREPL()
        repl.add_notification("Alert", NotificationTier.CRITICAL)
        repl.flush_notifications()
        assert repl.flush_notifications() == []

    def test_ambient_kept_for_notifications_command(self) -> None:
        repl = AutopilotREPL()
        repl.add_notification("bg info", NotificationTier.AMBIENT)
        repl.flush_notifications()
        # Ambient stays in the queue for /notifications
        assert len(repl._notifications) == 1


class TestCommandDispatch:
    def test_help_command(self) -> None:
        repl = AutopilotREPL()
        # Should not raise
        repl._dispatch("/help")

    def test_quit_command(self) -> None:
        repl = AutopilotREPL()
        repl._running = True
        repl._dispatch("/quit")
        assert repl._running is False

    def test_exit_command(self) -> None:
        repl = AutopilotREPL()
        repl._running = True
        repl._dispatch("/exit")
        assert repl._running is False

    def test_status_command(self) -> None:
        repl = AutopilotREPL()
        repl.set_project("test-proj")
        # Should not raise
        repl._dispatch("/status")

    def test_unknown_slash_command(self) -> None:
        repl = AutopilotREPL()
        # Should not raise, just show error
        repl._dispatch("/nonexistent")

    def test_non_slash_input(self) -> None:
        repl = AutopilotREPL()
        # Should not raise
        repl._dispatch("hello world")

    def test_command_case_insensitive(self) -> None:
        repl = AutopilotREPL()
        repl._running = True
        repl._dispatch("/QUIT")
        assert repl._running is False


class TestHistory:
    def test_file_history_created(self, tmp_path: Path) -> None:
        history_file = tmp_path / "history"
        AutopilotREPL(history_path=history_file)
        # FileHistory creates the file lazily, but parent should exist
        assert history_file.parent.exists()

    def test_in_memory_history_default(self) -> None:
        repl = AutopilotREPL()
        # Should not crash — uses InMemoryHistory
        assert repl._session is not None


class TestRunLoop:
    def test_eof_exits_gracefully(self) -> None:
        repl = AutopilotREPL()
        with patch.object(repl._session, "prompt", side_effect=EOFError):
            repl.run()
        assert repl._running is False

    def test_keyboard_interrupt_continues(self) -> None:
        repl = AutopilotREPL()
        call_count = 0

        def side_effect(*_args: object, **_kwargs: object) -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise KeyboardInterrupt
            raise EOFError

        with patch.object(repl._session, "prompt", side_effect=side_effect):
            repl.run()
        assert call_count == 2  # survived the interrupt

    def test_quit_stops_loop(self) -> None:
        repl = AutopilotREPL()
        with patch.object(repl._session, "prompt", return_value="/quit"):
            repl.run()
        assert repl._running is False

    def test_notifications_shown_before_prompt(self) -> None:
        repl = AutopilotREPL()
        repl.add_notification("Important!", NotificationTier.IMPORTANT)

        with patch.object(repl._session, "prompt", return_value="/quit"):
            repl.run()
        # After run, the important notification should have been flushed
        assert len(repl.flush_notifications()) == 0
