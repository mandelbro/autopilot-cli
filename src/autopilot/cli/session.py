"""Session lifecycle CLI commands (Task 039).

Commands: start, stop, pause, resume, list, attach, log.
All use Rich output with status-appropriate coloring.
"""

from __future__ import annotations

import signal
import sys
import time
from typing import Annotated

import typer

from autopilot.cli.display import console, format_status
from autopilot.core.models import SessionStatus
from autopilot.core.session import SessionManager
from autopilot.orchestration.daemon import stop_daemon
from autopilot.utils.db import Database
from autopilot.utils.paths import find_autopilot_dir


def register_session_commands(app: typer.Typer) -> None:
    """Register all session subcommands on the given Typer app."""

    @app.command("start")
    def session_start(
        project: Annotated[
            str | None,
            typer.Option("--project", "-p", help="Project name (defaults to active project)."),
        ] = None,
    ) -> None:
        """Start an autonomous session daemon for a project."""
        from autopilot.core.config import AutopilotConfig, ProjectConfig
        from autopilot.orchestration.agent_invoker import AgentInvoker
        from autopilot.orchestration.daemon import Daemon
        from autopilot.orchestration.scheduler import Scheduler
        from autopilot.orchestration.usage import UsageTracker

        ap_dir = find_autopilot_dir()
        if ap_dir is None:
            console.print(
                "[error]No .autopilot directory found. Run 'autopilot init' first.[/error]"
            )
            raise typer.Exit(code=1)

        project_name = project or ap_dir.parent.name
        config = AutopilotConfig(project=ProjectConfig(name=project_name))

        state_dir = ap_dir / "state"
        log_dir = ap_dir / "logs"

        db = Database(ap_dir / "autopilot.db")
        usage = UsageTracker(db=db, config=config)
        invoker = AgentInvoker(registry=None, config=config)  # type: ignore[arg-type]
        scheduler = Scheduler(
            config=config,
            invoker=invoker,
            usage_tracker=usage,
            lock_dir=state_dir,
            cwd=ap_dir.parent,
        )

        daemon = Daemon(
            config=config,
            scheduler=scheduler,
            state_dir=state_dir,
            log_dir=log_dir,
        )

        console.print(f"Starting session for project [bold]{project_name}[/bold]...")
        try:
            daemon.start()
        except RuntimeError as exc:
            console.print(f"[error]{exc}[/error]")
            raise typer.Exit(code=1) from None

    @app.command("stop")
    def session_stop(
        project: Annotated[
            str | None,
            typer.Option("--project", "-p", help="Project name."),
        ] = None,
    ) -> None:
        """Stop the running session daemon."""
        ap_dir = find_autopilot_dir()
        if ap_dir is None:
            console.print("[error]No .autopilot directory found.[/error]")
            raise typer.Exit(code=1)

        state_dir = ap_dir / "state"
        if stop_daemon(state_dir):
            console.print("[success]Session daemon stopped.[/success]")
        else:
            console.print("[warning]No running daemon found.[/warning]")

    @app.command("pause")
    def session_pause(
        session_id: Annotated[str, typer.Argument(help="Session ID to pause.")],
    ) -> None:
        """Pause execution of a running session."""
        ap_dir = find_autopilot_dir()
        if ap_dir is None:
            console.print("[error]No .autopilot directory found.[/error]")
            raise typer.Exit(code=1)

        db = Database(ap_dir / "autopilot.db")
        mgr = SessionManager(db)
        session = mgr.get_session(session_id)
        if session is None:
            console.print(f"[error]Session {session_id} not found.[/error]")
            raise typer.Exit(code=1)

        mgr.update_status(session_id, SessionStatus.PAUSED)
        console.print(f"Session [bold]{session_id}[/bold] paused.")

    @app.command("resume")
    def session_resume(
        session_id: Annotated[str, typer.Argument(help="Session ID to resume.")],
    ) -> None:
        """Resume a paused session."""
        ap_dir = find_autopilot_dir()
        if ap_dir is None:
            console.print("[error]No .autopilot directory found.[/error]")
            raise typer.Exit(code=1)

        db = Database(ap_dir / "autopilot.db")
        mgr = SessionManager(db)
        session = mgr.get_session(session_id)
        if session is None:
            console.print(f"[error]Session {session_id} not found.[/error]")
            raise typer.Exit(code=1)

        mgr.update_status(session_id, SessionStatus.RUNNING)
        console.print(f"Session [bold]{session_id}[/bold] resumed.")

    @app.command("list")
    def session_list(
        project: Annotated[
            str | None,
            typer.Option("--project", "-p", help="Filter by project."),
        ] = None,
        status: Annotated[
            str | None,
            typer.Option("--status", "-s", help="Filter by status."),
        ] = None,
    ) -> None:
        """List sessions with status."""
        from rich.table import Table

        ap_dir = find_autopilot_dir()
        if ap_dir is None:
            console.print("[error]No .autopilot directory found.[/error]")
            raise typer.Exit(code=1)

        db = Database(ap_dir / "autopilot.db")
        mgr = SessionManager(db)
        status_enum = SessionStatus(status) if status else None
        sessions = mgr.list_sessions(
            project=project or "",
            status_filter=status_enum,
        )

        if not sessions:
            console.print("[muted]No sessions found.[/muted]")
            return

        table = Table(title="Sessions", width=80)
        table.add_column("ID", width=10, no_wrap=True)
        table.add_column("Project")
        table.add_column("Type")
        table.add_column("Status", width=10)
        table.add_column("Agent")
        table.add_column("Started")

        for s in sessions:
            table.add_row(
                s.id[:8],
                s.project,
                s.type,
                format_status(s.status),
                s.agent_name or "-",
                s.started_at.strftime("%Y-%m-%d %H:%M") if s.started_at else "-",
            )

        console.print(table)

    @app.command("attach")
    def session_attach(
        session_id: Annotated[str, typer.Argument(help="Session ID to attach to.")],
    ) -> None:
        """Tail session logs in real-time."""
        ap_dir = find_autopilot_dir()
        if ap_dir is None:
            console.print("[error]No .autopilot directory found.[/error]")
            raise typer.Exit(code=1)

        log_file = ap_dir / "logs" / "daemon.log"
        if not log_file.exists():
            console.print("[warning]No log file found.[/warning]")
            raise typer.Exit(code=1)

        console.print(f"Attaching to session [bold]{session_id}[/bold]... (Ctrl+C to detach)")

        _interrupted = False

        def _handle_sigint(signum: int, frame: object) -> None:
            nonlocal _interrupted
            _interrupted = True

        old_handler = signal.signal(signal.SIGINT, _handle_sigint)
        try:
            with open(log_file) as fh:
                fh.seek(0, 2)  # Seek to end
                while not _interrupted:
                    line = fh.readline()
                    if line:
                        sys.stdout.write(line)
                    else:
                        time.sleep(0.5)
        finally:
            signal.signal(signal.SIGINT, old_handler)

        console.print("\n[muted]Detached.[/muted]")

    @app.command("log")
    def session_log(
        session_id: Annotated[str, typer.Argument(help="Session ID.")],
        lines: Annotated[
            int,
            typer.Option("--lines", "-n", help="Number of lines to show."),
        ] = 50,
    ) -> None:
        """View session log file."""
        from collections import deque

        ap_dir = find_autopilot_dir()
        if ap_dir is None:
            console.print("[error]No .autopilot directory found.[/error]")
            raise typer.Exit(code=1)

        log_file = ap_dir / "logs" / "daemon.log"
        if not log_file.exists():
            console.print("[warning]No log file found.[/warning]")
            raise typer.Exit(code=1)

        with open(log_file) as fh:
            tail = deque(fh, maxlen=lines)

        for line in tail:
            sys.stdout.write(line)
