"""Top-level Typer CLI application."""

import typer

from autopilot import __version__

app = typer.Typer(
    name="autopilot",
    help="Autonomous development orchestrator.",
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"autopilot {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-V", help="Show version and exit.", callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """Autopilot CLI - autonomous development orchestrator."""
