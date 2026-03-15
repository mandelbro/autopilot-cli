"""Top-level Typer CLI application (RFC Appendix B).

Registers subcommand groups and top-level commands. When invoked
with no arguments, enters the REPL (Phase 2).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
    from pathlib import Path

    from autopilot.core.config import AutopilotConfig
    from autopilot.orchestration.scheduler import Scheduler

from autopilot import __version__
from autopilot.cli.completions import complete_project_names, complete_project_types
from autopilot.cli.discover import register_discover_commands
from autopilot.cli.enforce import register_enforce_commands
from autopilot.cli.project import project_app
from autopilot.cli.session import register_session_commands
from autopilot.cli.sprint import register_sprint_commands
from autopilot.cli.task import register_task_commands

app = typer.Typer(
    name="autopilot",
    help="Autonomous development orchestrator.",
    no_args_is_help=False,
    rich_markup_mode="rich",
)

# -- Subcommand groups --------------------------------------------------------

task_app = typer.Typer(name="task", help="Task management and sprint planning.")
session_app = typer.Typer(name="session", help="Session lifecycle management.")
plan_app = typer.Typer(name="plan", help="Dispatch planning and review.")
enforce_app = typer.Typer(name="enforce", help="Anti-pattern enforcement engine.")
agent_app = typer.Typer(name="agent", help="Agent registry and invocation.")
config_app = typer.Typer(name="config", help="Configuration management.")
report_app = typer.Typer(name="report", help="Reporting and analytics.")

app.add_typer(project_app)
app.add_typer(task_app)
app.add_typer(session_app)
app.add_typer(plan_app)
app.add_typer(enforce_app)
app.add_typer(agent_app)
app.add_typer(config_app)
app.add_typer(report_app)


# -- Callbacks ----------------------------------------------------------------


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"autopilot {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
    log_level: str = typer.Option(
        "INFO",
        "--log-level",
        help="Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).",
    ),
) -> None:
    """Autopilot CLI - autonomous development orchestrator."""
    from autopilot.logging import configure_logging

    configure_logging(level=log_level)

    if ctx.invoked_subcommand is None:
        from autopilot.cli.repl import AutopilotREPL
        from autopilot.utils.paths import get_global_dir

        repl = AutopilotREPL(history_path=get_global_dir() / "repl_history")
        repl.run()
        raise typer.Exit()


# -- Top-level commands -------------------------------------------------------


@app.command()
def init(
    name: str = typer.Option("", "--name", "-n", prompt="Project name", help="Project name."),
    project_type: str = typer.Option(
        "python",
        "--type",
        "-t",
        prompt="Project type (python/typescript/hybrid)",
        help="Project type.",
        autocompletion=complete_project_types,
    ),
    root: str = typer.Option(".", "--root", "-r", help="Project root directory."),
    repository_url: str = typer.Option(
        "",
        "--repository-url",
        help="Git repository URL for workspace isolation.",
    ),
) -> None:
    """Initialize a new autopilot project (delegates to ``project init``)."""
    from autopilot.cli.project import run_init

    run_init(name=name, project_type=project_type, root=root, repository_url=repository_url)


def _resolve_project(project: str = "") -> tuple[Path, str]:
    """Resolve autopilot dir and project name. Returns (ap_dir, project_name).

    Raises typer.Exit(1) if no .autopilot directory is found.
    """
    from autopilot.cli.display import console
    from autopilot.utils.paths import find_autopilot_dir

    ap_dir = find_autopilot_dir()
    if ap_dir is None:
        console.print("[error]No .autopilot directory found. Run 'autopilot init' first.[/error]")
        raise typer.Exit(code=1)
    project_name = project or ap_dir.parent.name
    return ap_dir, project_name


def _build_scheduler(ap_dir: Path, project_name: str) -> tuple[AutopilotConfig, Scheduler]:
    """Build Scheduler with all dependencies from an autopilot directory.

    Returns (config, scheduler).
    """
    from autopilot.core.config import AutopilotConfig, ProjectConfig
    from autopilot.orchestration.agent_invoker import AgentInvoker
    from autopilot.orchestration.scheduler import Scheduler
    from autopilot.orchestration.usage import UsageTracker
    from autopilot.utils.db import Database

    config = AutopilotConfig(project=ProjectConfig(name=project_name))
    state_dir = ap_dir / "state"
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
    return config, scheduler


@app.command()
def start(
    project: str = typer.Option(
        "", "--project", "-p", help="Project name.", autocompletion=complete_project_names
    ),
) -> None:
    """Start an autonomous session (alias for ``session start``)."""
    from autopilot.cli.display import console
    from autopilot.orchestration.daemon import Daemon

    ap_dir, project_name = _resolve_project(project)
    config, scheduler = _build_scheduler(ap_dir, project_name)

    daemon = Daemon(
        config=config,
        scheduler=scheduler,
        state_dir=ap_dir / "state",
        log_dir=ap_dir / "logs",
    )

    console.print(f"Starting session for project [bold]{project_name}[/bold]...")
    try:
        daemon.start()
    except RuntimeError as exc:
        console.print(f"[error]{exc}[/error]")
        raise typer.Exit(code=1) from None


@app.command()
def stop(
    project: str = typer.Option(
        "", "--project", "-p", help="Project name.", autocompletion=complete_project_names
    ),
) -> None:
    """Stop the running session (alias for ``session stop``)."""
    from autopilot.cli.display import console
    from autopilot.orchestration.daemon import stop_daemon

    ap_dir, _project_name = _resolve_project(project)
    state_dir = ap_dir / "state"
    if stop_daemon(state_dir):
        console.print("[success]Session daemon stopped.[/success]")
    else:
        console.print("[warning]No running daemon found.[/warning]")


@app.command()
def cycle(
    project: str = typer.Option(
        "", "--project", "-p", help="Project name.", autocompletion=complete_project_names
    ),
) -> None:
    """Run a single scheduler cycle inline (no daemon)."""
    from autopilot.cli.display import console
    from autopilot.orchestration.scheduler import SchedulerError

    ap_dir, project_name = _resolve_project(project)
    _config, scheduler = _build_scheduler(ap_dir, project_name)

    console.print(f"Running single cycle for [bold]{project_name}[/bold]...")
    try:
        from autopilot.orchestration.dispatcher import parse_dispatch_plan

        plan = parse_dispatch_plan("{}")
        result = scheduler.run_cycle(plan)
        console.print(
            f"[success]Cycle {result.id[:8]} completed: "
            f"{result.dispatches_succeeded}/{result.dispatches_planned} succeeded[/success]"
        )
    except SchedulerError as exc:
        console.print(f"[error]Cycle failed: {exc}[/error]")
        raise typer.Exit(code=1) from None


@app.command()
def watch(
    project: str = typer.Option(
        "", "--project", "-p", help="Project name.", autocompletion=complete_project_names
    ),
) -> None:
    """Watch mode with live dashboard."""
    from autopilot.cli.display import ProjectState, console, render_dashboard

    _ap_dir, project_name = _resolve_project(project)
    state = ProjectState(name=project_name, status="watching")
    output = render_dashboard(state)
    console.print(output)


@app.command()
def ask(question: str = typer.Argument(..., help="Question for the agent.")) -> None:
    """Ask a question to the AI agent."""
    typer.echo(f"Not yet implemented: ask {question}")


@app.command()
def review() -> None:
    """Review recent changes and agent output."""
    typer.echo("Not yet implemented: review")


@app.command()
def migrate(
    project_root: str = typer.Option(".", "--project-root", "-r", help="Project root directory."),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would change without modifying anything."
    ),
) -> None:
    """Migrate from RepEngine autopilot/ layout to .autopilot/ format."""
    from pathlib import Path

    from autopilot.cli.display import console, notification
    from autopilot.core.migration import MigrationEngine

    root = Path(project_root).resolve()
    engine = MigrationEngine()

    if not engine.detect_repengine_layout(root):
        notification("error", "No RepEngine autopilot/ directory found.")
        raise typer.Exit(code=1)

    if dry_run:
        console.print("[bold]Dry run mode[/bold] -- no changes will be made.\n")

    result = engine.migrate(root, dry_run=dry_run)

    if result.success:
        notification("success", f"Migration complete! {len(result.files_copied)} files processed.")
        if result.files_copied:
            for f in result.files_copied:
                console.print(f"  [dim]{f}[/dim]")
    else:
        notification("error", "Migration failed.")
        for err in result.errors:
            console.print(f"  [red]{err}[/red]")
        raise typer.Exit(code=1)


# -- Task commands (registered from task module) -----------------------------

register_task_commands(task_app)

# -- Sprint subcommands under task -------------------------------------------

sprint_sub = typer.Typer(name="sprint", help="Sprint planning and lifecycle.")
task_app.add_typer(sprint_sub)
register_sprint_commands(sprint_sub)

# -- Session commands (registered from session module) -------------------------

register_session_commands(session_app)

# -- Enforcement commands (registered from enforce module) ----------------------

register_enforce_commands(enforce_app)

# -- Discovery commands (registered from discover module) ----------------------

register_discover_commands(plan_app)

# -- Stub subcommands for Phase 2+ -------------------------------------------


@agent_app.command("list")
def agent_list() -> None:
    """List available agent roles."""
    typer.echo("Not yet implemented: agent list")


@config_app.command("show")
def config_show() -> None:
    """Show current configuration."""
    typer.echo("Not yet implemented: config show")


@config_app.command("edit")
def config_edit() -> None:
    """Edit configuration."""
    typer.echo("Not yet implemented: config edit")


@report_app.command("sprint")
def report_sprint() -> None:
    """Show sprint report."""
    typer.echo("Not yet implemented: report sprint")


@report_app.command("velocity")
def report_velocity() -> None:
    """Show velocity metrics."""
    typer.echo("Not yet implemented: report velocity")
