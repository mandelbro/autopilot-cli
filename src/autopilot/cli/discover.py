"""Discovery workflow CLI commands (Task 078).

Implements ``plan discover``, ``plan tasks``, ``plan estimate``, and
``plan show`` subcommands for launching Norwood discovery sessions
and converting findings to tasks.
"""

from __future__ import annotations

from pathlib import Path

import structlog
import typer

from autopilot.cli.display import console

logger = structlog.get_logger(__name__)


def register_discover_commands(plan_app: typer.Typer) -> None:
    """Register discovery-related commands on the plan Typer group."""

    @plan_app.command("discover")
    def plan_discover(
        project: str = typer.Argument(..., help="Project name for discovery."),
        topic: str = typer.Argument(..., help="Topic or area to analyze."),
        wait: bool = typer.Option(False, "--wait", "-w", help="Block until discovery completes."),
        output: str = typer.Option(
            "", "--output", "-o", help="Output directory for discovery document."
        ),
    ) -> None:
        """Launch a Norwood discovery session for technical analysis."""
        from autopilot.utils.paths import find_autopilot_dir

        ap_dir = find_autopilot_dir()
        if ap_dir is None:
            console.print(
                "[error]No .autopilot directory found. Run 'autopilot init' first.[/error]"
            )
            raise typer.Exit(code=1)

        project_dir = ap_dir.parent
        output_path = Path(output) if output else project_dir / ".autopilot" / "discoveries"
        output_path.mkdir(parents=True, exist_ok=True)

        discovery_file = output_path / f"{_slugify(topic)}-discovery.md"

        console.print("[bold]Starting discovery session[/bold]")
        console.print(f"  Project: {project}")
        console.print(f"  Topic: {topic}")
        console.print(f"  Output: {discovery_file}")

        # Load the Norwood prompt template
        template_content = _load_discovery_template(ap_dir, project, project_dir)

        if wait:
            console.print("[dim]Running discovery (--wait mode)...[/dim]")
            _run_discovery_sync(template_content, topic, discovery_file)
            console.print(f"[success]Discovery complete: {discovery_file}[/success]")
        else:
            console.print(
                "[dim]Discovery session registered. Use --wait to block until complete.[/dim]"
            )
            # Write a placeholder discovery document
            _write_placeholder(discovery_file, project, topic)
            console.print(f"[success]Placeholder created: {discovery_file}[/success]")

    @plan_app.command("tasks")
    def plan_tasks(
        from_discovery: str = typer.Option(
            ..., "--from-discovery", help="Path to discovery document."
        ),
        output_dir: str = typer.Option(
            "tasks", "--output", "-o", help="Output directory for task files."
        ),
        merge: bool = typer.Option(False, "--merge", help="Merge with existing task files."),
    ) -> None:
        """Convert a discovery document into task files."""
        from autopilot.core.discovery import DiscoveryParser, TaskFileWriter

        discovery_path = Path(from_discovery)
        if not discovery_path.exists():
            console.print(f"[error]Discovery file not found: {discovery_path}[/error]")
            raise typer.Exit(code=1)

        out_dir = Path(output_dir)

        parser = DiscoveryParser()
        doc = parser.parse_discovery(discovery_path)

        console.print(f"[bold]Parsed discovery: {doc.title}[/bold]")
        console.print(f"  Phases: {len(doc.phases)}")
        total_deliverables = sum(len(p.deliverables) for p in doc.phases)
        console.print(f"  Deliverables: {total_deliverables}")

        # Show phase summary
        for phase in doc.phases:
            console.print(f"  - {phase.name}: {len(phase.deliverables)} deliverables")

        # Convert to tasks — TaskFileWriter handles merge renumbering internally,
        # so we always generate with start_id=1 and let write_task_files adjust.
        tasks = parser.convert_to_tasks(doc, start_id=1)
        console.print(f"\n  Generated {len(tasks)} tasks")

        # Write task files (merge=True renumbers and appends internally)
        writer = TaskFileWriter()
        files = writer.write_task_files(tasks, out_dir, merge=merge)

        console.print("[success]Task files written:[/success]")
        for f in files:
            console.print(f"  {f}")

    @plan_app.command("estimate")
    def plan_estimate(
        task_file: str = typer.Option(
            "", "--file", "-f", help="Task file to estimate (defaults to all)."
        ),
    ) -> None:
        """Launch estimation agent for batch task pointing."""
        console.print("[bold]Estimation agent[/bold]")
        console.print(
            "[dim]Launches Shelly for batch estimation. "
            "Not yet fully integrated — estimate manually or use 'autopilot task estimate'.[/dim]"
        )
        if task_file:
            console.print(f"  File: {task_file}")
        console.print("[warning]Estimation agent integration pending (Task 080).[/warning]")

    @plan_app.command("show")
    def plan_show() -> None:
        """Display current planning state (discovery + tasks + sprint)."""
        from autopilot.utils.paths import find_autopilot_dir

        ap_dir = find_autopilot_dir()
        if ap_dir is None:
            console.print(
                "[error]No .autopilot directory found. Run 'autopilot init' first.[/error]"
            )
            raise typer.Exit(code=1)

        project_dir = ap_dir.parent
        task_dir = project_dir / "tasks"
        discovery_dir = project_dir / ".autopilot" / "discoveries"

        console.print("[bold]Planning State[/bold]")
        console.print()

        # Show discoveries
        if discovery_dir.exists():
            discoveries = sorted(discovery_dir.glob("*.md"))
            if discoveries:
                console.print(f"  [bold]Discoveries[/bold]: {len(discoveries)}")
                for d in discoveries[:5]:
                    console.print(f"    - {d.name}")
            else:
                console.print("  [dim]No discoveries found.[/dim]")
        else:
            console.print("  [dim]No discoveries directory.[/dim]")

        console.print()

        # Show task summary
        if task_dir.exists():
            index_path = task_dir / "tasks-index.md"
            if index_path.exists():
                from autopilot.core.task import TaskParser

                parser = TaskParser()
                index = parser.parse_task_index(index_path)
                console.print("  [bold]Tasks[/bold]:")
                console.print(f"    Total: {index.total_tasks}")
                console.print(f"    Complete: {index.complete}")
                console.print(f"    Pending: {index.pending}")
                console.print(f"    Points: {index.points_complete}/{index.total_points}")
            else:
                console.print("  [dim]No task index found.[/dim]")
        else:
            console.print("  [dim]No tasks directory.[/dim]")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _slugify(text: str) -> str:
    """Convert text to a filename-safe slug."""
    import re

    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


def _load_discovery_template(ap_dir: Path, project: str, project_dir: Path) -> str:
    """Load and render the Norwood discovery prompt template."""
    from jinja2 import Environment, FileSystemLoader

    # Look for the template in the package templates directory
    from autopilot.core.templates import PACKAGE_TEMPLATES

    package_templates = PACKAGE_TEMPLATES / "python"

    if not package_templates.is_dir():
        logger.warning("templates_dir_not_found", path=str(package_templates))
        return f"# Discovery: {project}\n\nTemplate directory not found."

    try:
        env = Environment(
            loader=FileSystemLoader(str(package_templates)),
            keep_trailing_newline=True,
        )
        template = env.get_template("agents/norwood-discovery.md")
        content = template.render(
            project_name=project,
            project_root=str(project_dir),
            project_type="python",
        )
    except Exception as exc:
        logger.warning("discovery_template_render_failed", error=str(exc))
        content = f"# Discovery: {project}\n\nTemplate render failed: {exc}"

    return content


def _run_discovery_sync(template_content: str, topic: str, output_path: Path) -> None:
    """Run discovery synchronously using the rendered template.

    Writes the rendered Norwood prompt template as a discovery document
    with the topic injected as context. Full agent integration is pending;
    this writes the template as-is for manual review or agent consumption.
    """
    header = f"# Discovery: {topic}\n\n"
    content = header + template_content
    output_path.write_text(content, encoding="utf-8")


def _write_placeholder(output_path: Path, project: str, topic: str) -> None:
    """Write a placeholder discovery document."""
    content = (
        f"# Discovery: {topic}\n\n"
        f"**Project**: {project}\n"
        f"**Status**: Pending\n\n"
        f"Run with `--wait` to execute discovery, "
        f"or launch a Norwood agent session manually.\n"
    )
    output_path.write_text(content, encoding="utf-8")
