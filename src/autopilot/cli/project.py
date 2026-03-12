"""CLI commands for project management (UX Design Section 5.1)."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from autopilot.cli.display import console, notification
from autopilot.core.project import initialize_project

project_app = typer.Typer(name="project", help="Project lifecycle management.")


def run_init(*, name: str, project_type: str, root: str) -> None:
    """Shared init logic used by both ``autopilot init`` and ``autopilot project init``."""
    root_path = Path(root).resolve()

    try:
        result = initialize_project(
            name=name,
            project_type=project_type,
            root_path=root_path,
        )
    except (FileExistsError, ValueError) as exc:
        notification("error", str(exc))
        raise typer.Exit(code=1) from exc

    notification("success", f"Project '{result.project_name}' initialized!")
    console.print()

    # Show created files
    table = Table(title="Created Files", width=80)
    table.add_column("File", style="dim")
    for f in result.files_created:
        table.add_row(f)
    console.print(table)
    console.print()

    # Show next steps
    console.print("[bold]Next steps:[/bold]")
    for i, step in enumerate(result.next_steps, 1):
        console.print(f"  {i}. {step}")


@project_app.command("init")
def project_init(
    name: str = typer.Option(..., "--name", "-n", prompt="Project name", help="Project name."),
    project_type: str = typer.Option(
        "python",
        "--type",
        "-t",
        prompt="Project type (python/typescript/hybrid)",
        help="Project type.",
    ),
    root: str = typer.Option(
        ".",
        "--root",
        "-r",
        help="Project root directory.",
    ),
) -> None:
    """Initialize a new autopilot project with scaffolded .autopilot/ directory."""
    run_init(name=name, project_type=project_type, root=root)


@project_app.command("list")
def project_list_cmd() -> None:
    """List all registered projects."""
    typer.echo("Not yet implemented: project list")
