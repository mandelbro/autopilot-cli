"""Top-level Typer CLI application (RFC Appendix B).

Registers subcommand groups and top-level commands. When invoked
with no arguments, enters the REPL (Phase 2).
"""

from __future__ import annotations

import typer

from autopilot import __version__
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
) -> None:
    """Autopilot CLI - autonomous development orchestrator."""
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
    ),
    root: str = typer.Option(".", "--root", "-r", help="Project root directory."),
) -> None:
    """Initialize a new autopilot project (delegates to ``project init``)."""
    from autopilot.cli.project import run_init

    run_init(name=name, project_type=project_type, root=root)


@app.command()
def start(
    project: str = typer.Option("", "--project", "-p", help="Project name."),
) -> None:
    """Start an autonomous session (alias for ``session start``)."""
    from autopilot.cli.display import console
    from autopilot.core.config import AutopilotConfig, ProjectConfig
    from autopilot.orchestration.agent_invoker import AgentInvoker
    from autopilot.orchestration.daemon import Daemon
    from autopilot.orchestration.scheduler import Scheduler
    from autopilot.orchestration.usage import UsageTracker
    from autopilot.utils.db import Database
    from autopilot.utils.paths import find_autopilot_dir

    ap_dir = find_autopilot_dir()
    if ap_dir is None:
        console.print("[error]No .autopilot directory found. Run 'autopilot init' first.[/error]")
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
    daemon = Daemon(config=config, scheduler=scheduler, state_dir=state_dir, log_dir=log_dir)

    console.print(f"Starting session for project [bold]{project_name}[/bold]...")
    try:
        daemon.start()
    except RuntimeError as exc:
        console.print(f"[error]{exc}[/error]")
        raise typer.Exit(code=1) from None


@app.command()
def stop(
    project: str = typer.Option("", "--project", "-p", help="Project name."),
) -> None:
    """Stop the running session (alias for ``session stop``)."""
    from autopilot.cli.display import console
    from autopilot.orchestration.daemon import stop_daemon
    from autopilot.utils.paths import find_autopilot_dir

    ap_dir = find_autopilot_dir()
    if ap_dir is None:
        console.print("[error]No .autopilot directory found.[/error]")
        raise typer.Exit(code=1)

    state_dir = ap_dir / "state"
    if stop_daemon(state_dir):
        console.print("[success]Session daemon stopped.[/success]")
    else:
        console.print("[warning]No running daemon found.[/warning]")


@app.command()
def cycle(
    project: str = typer.Option("", "--project", "-p", help="Project name."),
) -> None:
    """Run a single scheduler cycle inline (no daemon)."""
    from autopilot.cli.display import console
    from autopilot.core.config import AutopilotConfig, ProjectConfig
    from autopilot.orchestration.agent_invoker import AgentInvoker
    from autopilot.orchestration.scheduler import Scheduler, SchedulerError
    from autopilot.orchestration.usage import UsageTracker
    from autopilot.utils.db import Database
    from autopilot.utils.paths import find_autopilot_dir

    ap_dir = find_autopilot_dir()
    if ap_dir is None:
        console.print("[error]No .autopilot directory found. Run 'autopilot init' first.[/error]")
        raise typer.Exit(code=1)

    project_name = project or ap_dir.parent.name
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
    project: str = typer.Option("", "--project", "-p", help="Project name."),
) -> None:
    """Watch mode with live dashboard."""
    from autopilot.cli.display import ProjectState, console, render_dashboard
    from autopilot.utils.paths import find_autopilot_dir

    ap_dir = find_autopilot_dir()
    if ap_dir is None:
        console.print("[error]No .autopilot directory found.[/error]")
        raise typer.Exit(code=1)

    project_name = project or ap_dir.parent.name
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
def migrate() -> None:
    """Migrate from RepEngine autopilot layout."""
    typer.echo("Not yet implemented: migrate")


# -- Task commands (registered from task module) -----------------------------

register_task_commands(task_app)

# -- Sprint subcommands under task -------------------------------------------

sprint_sub = typer.Typer(name="sprint", help="Sprint planning and lifecycle.")
task_app.add_typer(sprint_sub)
register_sprint_commands(sprint_sub)

# -- Session commands (registered from session module) -------------------------

register_session_commands(session_app)

# -- Stub subcommands for Phase 2+ -------------------------------------------


@enforce_app.command("run")
def enforce_run() -> None:
    """Run enforcement checks."""
    typer.echo("Not yet implemented: enforce run")


@enforce_app.command("report")
def enforce_report() -> None:
    """Show enforcement report."""
    typer.echo("Not yet implemented: enforce report")


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
