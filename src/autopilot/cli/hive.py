"""Hive-mind orchestration CLI commands (Task 010).

Commands: spawn (with --dry-run), status, list, stop.
"""

from __future__ import annotations

from typing import Annotated

import typer

from autopilot.cli.display import console

hive_app = typer.Typer(name="hive", help="Hive-mind orchestration.")


def _parse_task_ids(task_ids_str: str) -> list[str]:
    """Parse task ID ranges and comma-separated values.

    Supports:
      - Range format: ``"001-008"``
      - Comma format: ``"001,003,005"``
      - Mixed format: ``"001-003,005,007-008"``
      - Single ID: ``"042"``

    Returns a deduplicated, sorted list of zero-padded (3-digit) task IDs.
    """
    if not task_ids_str.strip():
        return []

    result: set[int] = set()
    for part in task_ids_str.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            if "-" in part:
                start_str, end_str = part.split("-", 1)
                start, end = int(start_str), int(end_str)
                result.update(range(start, end + 1))
            else:
                result.add(int(part))
        except ValueError as exc:
            msg = f"Invalid task ID format '{part}': {exc}"
            raise ValueError(msg) from exc

    return [f"{n:03d}" for n in sorted(result)]


@hive_app.command("spawn")
def hive_spawn(
    task_file: Annotated[str, typer.Argument(help="Path to the task file.")],
    task_ids: Annotated[
        str,
        typer.Option("--task-ids", "-t", help="Task IDs (e.g. '001-008' or '001,003,005')."),
    ] = "",
    namespace: Annotated[
        str | None,
        typer.Option("--namespace", "-n", help="Hive-mind namespace."),
    ] = None,
    template: Annotated[
        str,
        typer.Option("--template", help="Objective template name."),
    ] = "default",
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview the objective without spawning."),
    ] = False,
) -> None:
    """Build an objective and launch a hive-mind session."""

    from autopilot.core.config import AutopilotConfig, ProjectConfig
    from autopilot.orchestration.hive import HiveError, HiveMindManager
    from autopilot.orchestration.objective_builder import HiveObjectiveBuilder
    from autopilot.utils.paths import find_autopilot_dir, get_global_dir

    ap_dir = find_autopilot_dir()
    if ap_dir is None:
        console.print("[error]No .autopilot directory found. Run 'autopilot init' first.[/error]")
        raise typer.Exit(code=1)

    project_name = ap_dir.parent.name
    global_config = get_global_dir() / "config.yaml"
    project_config = ap_dir / "config.yaml"
    if global_config.exists() or project_config.exists():
        config = AutopilotConfig.merge(global_config, project_config)
    else:
        config = AutopilotConfig(project=ProjectConfig(name=project_name))

    parsed_ids = _parse_task_ids(task_ids)
    if not parsed_ids:
        console.print("[error]No task IDs specified. Use --task-ids.[/error]")
        raise typer.Exit(code=1)

    builder = HiveObjectiveBuilder(config)
    objective = builder.build(task_file, parsed_ids, template_name=template)

    if dry_run:
        console.print("[bold]Objective preview:[/bold]\n")
        console.print(objective)
        return

    manager = HiveMindManager(config, cwd=ap_dir.parent)
    try:
        session = manager.spawn_hive(
            objective,
            namespace=namespace,
            use_claude=config.hive_mind.use_claude,
            task_file=task_file,
            task_ids=parsed_ids,
        )
    except HiveError as exc:
        console.print(f"[error]{exc}[/error]")
        raise typer.Exit(code=1) from None

    console.print(f"[success]Hive spawned: session={session.id[:8]}[/success]")
    pid = session.metadata.get("pid")
    if pid:
        console.print(f"  PID: {pid}")


@hive_app.command("status")
def hive_status(
    namespace: Annotated[
        str | None,
        typer.Option("--namespace", "-n", help="Hive-mind namespace."),
    ] = None,
) -> None:
    """Show hive-mind session status."""
    typer.echo("Not yet implemented")


@hive_app.command("list")
def hive_list() -> None:
    """List recent hive-mind sessions."""
    typer.echo("Not yet implemented")


@hive_app.command("stop")
def hive_stop(
    namespace: Annotated[
        str | None,
        typer.Option("--namespace", "-n", help="Hive-mind namespace."),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Force stop (skip graceful shutdown)."),
    ] = False,
) -> None:
    """Stop a running hive-mind session."""
    typer.echo("Not yet implemented")
