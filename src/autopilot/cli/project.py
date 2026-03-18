"""CLI commands for project management (UX Design Section 5.1, Tasks 010-011)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, cast

import typer
from rich.table import Table

from autopilot.cli.display import console, format_status, notification
from autopilot.core.project import ProjectRegistry, initialize_project
from autopilot.utils.paths import get_global_dir

project_app = typer.Typer(name="project", help="Project lifecycle management.")


def _get_active_project_path() -> Path:
    """Return the path to the active project marker file."""
    return get_global_dir() / "active_project"


def _get_active_project() -> str:
    """Read the currently active project name, or empty string."""
    path = _get_active_project_path()
    if path.exists():
        return path.read_text().strip()
    return ""


def _set_active_project(name: str) -> None:
    """Write the active project name."""
    path = _get_active_project_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(name)


def _detect_git_origin(root: Path) -> str:
    """Try to detect the git remote origin URL. Returns empty string on failure."""
    try:
        proc = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return ""


def run_init(*, name: str, project_type: str, root: str, repository_url: str = "") -> None:
    """Shared init logic used by both ``autopilot init`` and ``autopilot project init``."""
    root_path = Path(root).resolve()

    # Auto-detect repository URL if not provided
    if not repository_url:
        repository_url = _detect_git_origin(root_path)

    try:
        result = initialize_project(
            name=name,
            project_type=project_type,
            root_path=root_path,
            repository_url=repository_url,
        )
    except (FileExistsError, ValueError) as exc:
        notification("error", str(exc))
        raise typer.Exit(code=1) from exc

    notification("success", f"Project '{result.project_name}' initialized!")
    console.print()

    table = Table(title="Created Files", width=80)
    table.add_column("File", style="dim")
    for f in result.files_created:
        table.add_row(f)
    console.print(table)
    console.print()

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
    repository_url: str = typer.Option(
        "",
        "--repository-url",
        help="Git repository URL for workspace isolation.",
    ),
) -> None:
    """Initialize a new autopilot project with scaffolded .autopilot/ directory."""
    run_init(name=name, project_type=project_type, root=root, repository_url=repository_url)


@project_app.command("list")
def project_list_cmd() -> None:
    """List all registered projects."""
    registry = ProjectRegistry()
    projects = registry.load()

    if not projects:
        notification("info", "No projects registered. Run 'autopilot init' to create one.")
        return

    table = Table(title="Projects", width=80)
    table.add_column("Name", style="bold")
    table.add_column("Type")
    table.add_column("Path", style="dim")
    table.add_column("Status", width=10)

    active = _get_active_project()
    for p in projects:
        if p.archived:
            continue
        status = "active" if p.name == active else ""
        table.add_row(p.name, p.type, p.path, format_status(status) if status else "")
    console.print(table)


@project_app.command("show")
def project_show(
    name: str = typer.Argument(default="", help="Project name (default: active project)."),
) -> None:
    """Show detailed project information."""
    if not name:
        name = _get_active_project()
    if not name:
        notification("error", "No project specified and no active project set.")
        raise typer.Exit(code=1)

    registry = ProjectRegistry()
    project = registry.find_by_name(name)
    if project is None:
        notification("error", f"Project '{name}' not found in registry.")
        raise typer.Exit(code=1)

    console.print(f"[bold]Project:[/bold] {project.name}")
    console.print(f"[bold]Type:[/bold] {project.type}")
    console.print(f"[bold]Path:[/bold] {project.path}")
    console.print(f"[bold]Registered:[/bold] {project.registered_at}")
    if project.last_active:
        console.print(f"[bold]Last Active:[/bold] {project.last_active}")
    console.print(f"[bold]Archived:[/bold] {project.archived}")

    project_path = Path(project.path)
    config_path = project_path / ".autopilot" / "config.yaml"
    if config_path.exists():
        console.print(f"[bold]Config:[/bold] {config_path}")
    agents_dir = project_path / ".autopilot" / "agents"
    if agents_dir.is_dir():
        agents = [f.stem for f in agents_dir.iterdir() if f.suffix == ".md"]
        if agents:
            console.print(f"[bold]Agents:[/bold] {', '.join(sorted(agents))}")


@project_app.command("switch")
def project_switch(
    name: str = typer.Argument(..., help="Project name to switch to."),
) -> None:
    """Set the active project context."""
    registry = ProjectRegistry()
    project = registry.find_by_name(name)
    if project is None:
        notification("error", f"Project '{name}' not found in registry.")
        raise typer.Exit(code=1)
    if project.archived:
        notification("error", f"Project '{name}' is archived.")
        raise typer.Exit(code=1)

    _set_active_project(name)
    registry.update_last_active(name)
    notification("success", f"Switched to project '{name}'.")


@project_app.command("config")
def project_config(
    key: str = typer.Argument(default="", help="Config key to get/set."),
    value: str = typer.Argument(default="", help="Value to set (omit to get)."),
) -> None:
    """Get or set project config values."""
    import yaml as _yaml

    name = _get_active_project()
    if not name:
        notification("error", "No active project. Use 'autopilot project switch' first.")
        raise typer.Exit(code=1)

    registry = ProjectRegistry()
    project = registry.find_by_name(name)
    if project is None:
        notification("error", f"Project '{name}' not found.")
        raise typer.Exit(code=1)

    config_path = Path(project.path) / ".autopilot" / "config.yaml"
    if not config_path.exists():
        notification("error", f"Config file not found: {config_path}")
        raise typer.Exit(code=1)

    data: dict[str, Any] = _yaml.safe_load(config_path.read_text()) or {}

    if not key:
        console.print_json(data=data)
        return

    if not value:
        # Get a key using dot notation
        parts = key.split(".")
        current_val: Any = data
        for part in parts:
            if isinstance(current_val, dict) and part in current_val:
                current_val = cast("Any", current_val[part])
            else:
                notification("error", f"Key '{key}' not found.")
                raise typer.Exit(code=1)
        console.print(f"{key} = {current_val}")
        return

    # Set a key using dot notation
    parts = key.split(".")
    current_dict: dict[str, Any] = data
    for part in parts[:-1]:
        if part not in current_dict or not isinstance(current_dict[part], dict):
            current_dict[part] = {}
        current_dict = current_dict[part]
    current_dict[parts[-1]] = value
    config_path.write_text(_yaml.dump(data, default_flow_style=False))
    notification("success", f"Set {key} = {value}")


@project_app.command("archive")
def project_archive(
    name: str = typer.Argument(..., help="Project name to archive."),
) -> None:
    """Mark a project as archived (soft delete from active list)."""
    registry = ProjectRegistry()
    project = registry.find_by_name(name)
    if project is None:
        notification("error", f"Project '{name}' not found in registry.")
        raise typer.Exit(code=1)

    registry.archive(name)
    notification("success", f"Project '{name}' archived.")


@project_app.command("unregister")
def project_unregister(
    name: str = typer.Argument(..., help="Project name to unregister."),
) -> None:
    """Remove a project from the registry (does not delete files)."""
    registry = ProjectRegistry()
    try:
        registry.unregister(name)
    except KeyError:
        notification("error", f"Project '{name}' not found in registry.")
        raise typer.Exit(code=1) from None
    notification("success", f"Unregistered project '{name}'.")


@project_app.command("register")
def project_register(
    path: str = typer.Option(
        ..., "--path", "-p", help="Path to an external project with tasks/ directory."
    ),
    name: str = typer.Option(
        "", "--name", "-n", help="Custom project name (defaults to dir name)."
    ),
) -> None:
    """Register an external project that has a tasks/ directory."""
    from autopilot.core.discover_projects import discover_task_project

    project_path = Path(path).resolve()
    if not project_path.is_dir():
        notification("error", f"Path does not exist: {project_path}")
        raise typer.Exit(code=1)

    result = discover_task_project(project_path, name=name if name else "")
    if result is None:
        notification("error", f"No tasks/tasks-index.md found at {project_path}")
        raise typer.Exit(code=1)

    registry = ProjectRegistry()
    try:
        project = registry.register(
            result.name,
            result.path,
            "external",
            external=True,
            task_dir=result.task_dir,
        )
    except ValueError as exc:
        notification("error", str(exc))
        raise typer.Exit(code=1) from exc

    notification("success", f"Registered external project '{project.name}'")
    console.print(f"  [bold]Path:[/bold] {project.path}")
    console.print(f"  [bold]Tasks:[/bold] {result.total_tasks} ({result.pending} pending)")
    console.print(
        f"  [bold]Points:[/bold] {result.total_points} ({result.points_complete} complete)"
    )
    if result.description:
        console.print(f"  [bold]Description:[/bold] {result.description}")


@project_app.command("discover")
def project_discover(
    path: str = typer.Option(
        ".", "--path", "-p", help="Workspace directory to scan for task projects."
    ),
    register: bool = typer.Option(
        False, "--register", "-r", help="Auto-register discovered projects."
    ),
    max_depth: int = typer.Option(1, "--depth", "-d", help="Max directory depth to scan (1-5)."),
) -> None:
    """Scan a directory for projects with Task Workflow System files."""
    from autopilot.core.discover_projects import scan_for_task_projects

    if max_depth < 1 or max_depth > 5:
        notification("error", "Depth must be between 1 and 5.")
        raise typer.Exit(code=1)

    search_path = Path(path).resolve()
    results = scan_for_task_projects(search_path, max_depth=max_depth)

    if not results:
        notification("info", f"No task projects found under {search_path}")
        return

    table = Table(title=f"Discovered Task Projects ({len(results)})", width=90)
    table.add_column("Name", style="bold")
    table.add_column("Tasks", justify="right")
    table.add_column("Pending", justify="right")
    table.add_column("Points", justify="right")
    table.add_column("Path", style="dim")

    for r in results:
        table.add_row(r.name, str(r.total_tasks), str(r.pending), str(r.total_points), r.path)

    console.print(table)

    if register:
        registry = ProjectRegistry()
        registered_count = 0
        for r in results:
            existing = registry.find_by_name(r.name)
            if existing is not None:
                console.print(f"  [dim]Skipping '{r.name}' (already registered)[/dim]")
                continue
            try:
                registry.register(
                    r.name,
                    r.path,
                    "external",
                    external=True,
                    task_dir=r.task_dir,
                )
                registered_count += 1
            except ValueError as exc:
                console.print(f"  [dim]Skipping '{r.name}': {exc}[/dim]")
        notification("success", f"Registered {registered_count} new project(s).")
