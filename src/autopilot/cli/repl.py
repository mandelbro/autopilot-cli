"""Interactive REPL with prompt-toolkit (Tasks 013-014).

Provides an interactive shell for managing autopilot projects, sessions,
and agents. Uses prompt-toolkit for history, tab completion, and
context-sensitive prompts.
"""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory, InMemoryHistory

from autopilot.cli.display import console, notification

if TYPE_CHECKING:
    from pathlib import Path

    from prompt_toolkit.history import History

_log = logging.getLogger(__name__)


class ReplState(StrEnum):
    """REPL context state machine states."""

    NO_PROJECT = "no_project"
    PROJECT_SELECTED = "project_selected"
    SESSION_ACTIVE = "session_active"
    ATTENTION_NEEDED = "attention_needed"


class NotificationTier(StrEnum):
    """Notification urgency tiers per UX Design Section 6."""

    CRITICAL = "critical"
    IMPORTANT = "important"
    INFORMATIONAL = "informational"
    AMBIENT = "ambient"


class PendingNotification:
    """A notification waiting to be displayed."""

    __slots__ = ("message", "tier")

    def __init__(self, message: str, tier: NotificationTier) -> None:
        self.message = message
        self.tier = tier


class AutopilotREPL:
    """Interactive REPL for autopilot with context management.

    State machine: NO_PROJECT -> PROJECT_SELECTED -> SESSION_ACTIVE
    Any state can transition to ATTENTION_NEEDED when questions are pending.
    """

    def __init__(
        self,
        workspace: Path | None = None,
        *,
        history_path: Path | None = None,
    ) -> None:
        self._workspace = workspace
        self._state = ReplState.NO_PROJECT
        self._active_project: str = ""
        self._active_session: str = ""
        self._notifications: list[PendingNotification] = []
        self._running = False

        # Command registry: slash command -> handler
        self._commands: dict[str, _CommandHandler] = {
            "/help": self._cmd_help,
            "/quit": self._cmd_quit,
            "/exit": self._cmd_quit,
            "/projects": self._cmd_projects,
            "/sessions": self._cmd_sessions,
            "/status": self._cmd_status,
            "/notifications": self._cmd_notifications,
        }

        # Build completer from registered commands
        self._completer = WordCompleter(
            sorted(self._commands.keys()),
            ignore_case=True,
        )

        # History: file-based if path provided, otherwise in-memory
        history: History
        if history_path:
            history_path.parent.mkdir(parents=True, exist_ok=True)
            history = FileHistory(str(history_path))
        else:
            history = InMemoryHistory()

        self._session: PromptSession[str] = PromptSession(
            history=history,
            completer=self._completer,
        )

    @property
    def state(self) -> ReplState:
        """Current REPL state."""
        return self._state

    @property
    def active_project(self) -> str:
        """Currently selected project name."""
        return self._active_project

    def set_project(self, name: str) -> None:
        """Set the active project context."""
        self._active_project = name
        if name:
            self._state = ReplState.PROJECT_SELECTED
        else:
            self._state = ReplState.NO_PROJECT
            self._active_session = ""

    def set_session(self, session_id: str) -> None:
        """Set the active session."""
        self._active_session = session_id
        if session_id:
            self._state = ReplState.SESSION_ACTIVE
        elif self._active_project:
            self._state = ReplState.PROJECT_SELECTED

    def set_attention_needed(self) -> None:
        """Transition to ATTENTION_NEEDED state."""
        self._state = ReplState.ATTENTION_NEEDED

    def clear_attention(self) -> None:
        """Clear attention state, returning to previous context state."""
        if self._active_session:
            self._state = ReplState.SESSION_ACTIVE
        elif self._active_project:
            self._state = ReplState.PROJECT_SELECTED
        else:
            self._state = ReplState.NO_PROJECT

    def add_notification(self, message: str, tier: NotificationTier) -> None:
        """Queue a notification for display."""
        self._notifications.append(PendingNotification(message, tier))

    def get_prompt(self) -> str:
        """Build the context-sensitive prompt string."""
        if self._state == ReplState.ATTENTION_NEEDED:
            base = f"autopilot [{self._active_project}] !"
        elif self._state == ReplState.SESSION_ACTIVE:
            base = f"autopilot [{self._active_project}] *"
        elif self._state == ReplState.PROJECT_SELECTED:
            base = f"autopilot [{self._active_project}]"
        else:
            base = "autopilot"
        return f"{base} > "

    def flush_notifications(self) -> list[PendingNotification]:
        """Return and clear pending notifications (critical + important only).

        Informational and ambient notifications are kept for /notifications.
        """
        to_show: list[PendingNotification] = []
        remaining: list[PendingNotification] = []

        for n in self._notifications:
            if n.tier in (NotificationTier.CRITICAL, NotificationTier.IMPORTANT):
                to_show.append(n)
            else:
                remaining.append(n)

        self._notifications = remaining
        return to_show

    def run(self) -> None:
        """Run the REPL main loop. Blocks until /quit or EOF."""
        self._running = True
        notification("info", "Autopilot REPL started. Type /help for commands.")

        while self._running:
            try:
                # Show pending critical/important notifications
                for n in self.flush_notifications():
                    if n.tier == NotificationTier.CRITICAL:
                        notification("error", f"[CRITICAL] {n.message}")
                    else:
                        notification("info", n.message)

                text = self._session.prompt(self.get_prompt()).strip()
                if not text:
                    continue

                self._dispatch(text)

            except KeyboardInterrupt:
                console.print()  # newline after ^C
                continue
            except EOFError:
                self._running = False
                console.print("\nGoodbye.")

    def _dispatch(self, text: str) -> None:
        """Route input to command handlers."""
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        handler = self._commands.get(cmd)
        if handler:
            try:
                handler(args)
            except Exception as exc:
                notification("error", f"Command failed: {exc}")
                _log.debug("Command %s failed", cmd, exc_info=True)
        elif cmd.startswith("/"):
            notification("error", f"Unknown command: {cmd}. Type /help for available commands.")
        else:
            notification("info", f"Unknown input: {text}. Commands start with /")

    # -- Command handlers -------------------------------------------------------

    def _cmd_help(self, _args: str) -> None:
        """Show available commands."""
        console.print("[bold]Available commands:[/bold]")
        console.print("  /help          Show this help message")
        console.print("  /quit, /exit   Exit the REPL")
        console.print("  /projects      List registered projects")
        console.print("  /sessions      List active sessions")
        console.print("  /status        Show current REPL status")
        console.print("  /notifications Show queued notifications")

    def _cmd_quit(self, _args: str) -> None:
        """Exit the REPL."""
        self._running = False
        console.print("Goodbye.")

    def _cmd_projects(self, _args: str) -> None:
        """List registered projects."""
        try:
            from autopilot.core.project import ProjectRegistry  # type: ignore[attr-defined]

            registry = ProjectRegistry()
            projects = registry.load()
            if not projects:
                notification("info", "No projects registered.")
                return
            for p in projects:
                status = " (archived)" if p.archived else ""
                console.print(f"  {p.name} [{p.type}] {p.path}{status}")
        except Exception as exc:
            notification("error", f"Failed to list projects: {exc}")

    def _cmd_sessions(self, _args: str) -> None:
        """List active sessions."""
        notification("info", "Session listing not yet implemented.")

    def _cmd_status(self, _args: str) -> None:
        """Show REPL status."""
        console.print(f"[bold]State:[/bold] {self._state.value}")
        console.print(f"[bold]Project:[/bold] {self._active_project or '(none)'}")
        console.print(f"[bold]Session:[/bold] {self._active_session or '(none)'}")
        pending = len(self._notifications)
        console.print(f"[bold]Pending notifications:[/bold] {pending}")

    def _cmd_notifications(self, _args: str) -> None:
        """Show all queued notifications."""
        if not self._notifications:
            notification("info", "No pending notifications.")
            return
        for n in self._notifications:
            console.print(f"  [{n.tier.value}] {n.message}")


# Type alias for command handlers
type _CommandHandler = Any
