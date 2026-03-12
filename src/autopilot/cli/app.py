"""Top-level Typer CLI application (RFC Appendix B).

Registers subcommand groups and top-level commands. When invoked
with no arguments, enters the REPL (Phase 2).
"""

from __future__ import annotations

import typer

from autopilot import __version__
from autopilot.cli.project import project_app

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
def watch() -> None:
    """Watch mode with live dashboard."""
    typer.echo("Not yet implemented: watch")


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


# -- Stub subcommands for Phase 2+ -------------------------------------------


@task_app.command("list")
def task_list() -> None:
    """List tasks in the current sprint."""
    typer.echo("Not yet implemented: task list")


@task_app.command("board")
def task_board() -> None:
    """Display the task board."""
    typer.echo("Not yet implemented: task board")


@session_app.command("start")
def session_start() -> None:
    """Start a new session."""
    typer.echo("Not yet implemented: session start")


@session_app.command("stop")
def session_stop() -> None:
    """Stop the current session."""
    typer.echo("Not yet implemented: session stop")


@session_app.command("list")
def session_list() -> None:
    """List sessions."""
    typer.echo("Not yet implemented: session list")


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
