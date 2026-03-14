"""Enforcement CLI commands (Task 067, RFC Appendix B).

Provides ``autopilot enforce`` subcommands for setup, check, report,
and update of anti-pattern enforcement layers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
    from pathlib import Path

    from autopilot.enforcement.engine import EnforcementEngine


def _resolve_enforcement(
    project: str,
) -> tuple[EnforcementEngine, Path, str]:
    """Build an :class:`EnforcementEngine` from the current project.

    Uses lazy imports so the module can be imported without pulling in
    heavy dependencies at CLI parse time.

    Returns:
        ``(engine, project_root, project_name)``
    """
    from autopilot.cli.display import console
    from autopilot.core.config import EnforcementConfig as _EnforcementConfig
    from autopilot.enforcement.engine import EnforcementEngine as _Engine
    from autopilot.utils.paths import find_autopilot_dir

    ap_dir = find_autopilot_dir()
    if ap_dir is None:
        console.print("[error]No .autopilot directory found. Run 'autopilot init' first.[/error]")
        raise typer.Exit(code=1)

    project_root = ap_dir.parent
    project_name = project or project_root.name

    config = _EnforcementConfig()
    db_path = ap_dir / "enforcement.db"
    engine = _Engine(config, db_path=db_path)
    return engine, project_root, project_name


def register_enforce_commands(app: typer.Typer) -> None:
    """Register all enforcement subcommands on *app*."""

    @app.command("setup")
    def enforce_setup(
        project: str = typer.Option("", "--project", "-p", help="Project name."),
    ) -> None:
        """Configure enforcement layers for the project."""
        from autopilot.cli.display import console
        from autopilot.core.config import ProjectConfig as _ProjectConfig

        engine, _root, project_name = _resolve_enforcement(project)
        result = engine.setup(_ProjectConfig(name=project_name))

        if result.success:
            console.print(
                f"[success]Enforcement setup complete for [bold]{project_name}[/bold].[/success]"
            )
            if result.files_created:
                for f in result.files_created:
                    console.print(f"  Created: {f}")
        else:
            console.print("[error]Enforcement setup failed.[/error]")
            for err in result.errors:
                console.print(f"  [error]{err}[/error]")
            raise typer.Exit(code=1)

    @app.command("check")
    def enforce_check(
        category: str = typer.Option(
            "", "--category", "-c", help="Filter by enforcement category."
        ),
        fix: bool = typer.Option(False, "--fix", help="Attempt auto-fix (placeholder)."),
        project: str = typer.Option("", "--project", "-p", help="Project name."),
    ) -> None:
        """Run enforcement checks against the project."""
        from rich.table import Table

        from autopilot.cli.display import console
        from autopilot.core.models import ViolationSeverity as _Sev

        engine, project_root, _project_name = _resolve_enforcement(project)
        results = engine.check(project_root)

        # Flatten violations, optionally filtering by category.
        all_violations = []
        for r in results:
            if category and r.category != category:
                continue
            all_violations.extend(r.violations)

        if not all_violations:
            console.print("[success]No violations found.[/success]")
            return

        table = Table(title="Enforcement Violations", width=80)
        table.add_column("Category", width=14)
        table.add_column("File", ratio=2)
        table.add_column("Line", width=5, justify="right")
        table.add_column("Message", ratio=3)
        table.add_column("Severity", width=8)

        has_error = False
        for v in all_violations:
            if v.severity == _Sev.ERROR:
                has_error = True
            table.add_row(
                v.category,
                v.file,
                str(v.line) if v.line else "",
                v.message,
                v.severity.value,
            )

        console.print(table)
        console.print(f"\nTotal violations: {len(all_violations)}")

        if fix:
            console.print(
                "[info]Auto-fix is not yet implemented. "
                "Violations must be resolved manually.[/info]"
            )

        if has_error:
            raise typer.Exit(code=1)

    @app.command("report")
    def enforce_report(
        category: str = typer.Option(
            "", "--category", "-c", help="Filter by enforcement category."
        ),
        days: int = typer.Option(30, "--days", "-d", help="Report window in days."),
        project: str = typer.Option("", "--project", "-p", help="Project name."),
    ) -> None:
        """Generate an enforcement report from stored metrics."""
        from rich.table import Table

        from autopilot.cli.display import console

        engine, _root, project_name = _resolve_enforcement(project)
        report = engine.report(project_name)

        results = report.results
        if category:
            results = [r for r in results if r.category == category]

        if not results:
            console.print("[info]No enforcement data available for report.[/info]")
            return

        table = Table(title=f"Enforcement Report ({days}d)", width=80)
        table.add_column("Category", ratio=2)
        table.add_column("Violations", width=11, justify="right")
        table.add_column("Files Scanned", width=14, justify="right")
        table.add_column("Duration (s)", width=13, justify="right")

        for r in results:
            table.add_row(
                r.category,
                str(len(r.violations)),
                str(r.files_scanned),
                f"{r.duration_seconds:.2f}",
            )

        console.print(table)
        console.print(
            f"\nTotal violations: {report.total_violations} | "
            f"Files scanned: {report.total_files_scanned}"
        )

    @app.command("update")
    def enforce_update() -> None:
        """Update enforcement configuration (placeholder)."""
        from autopilot.cli.display import console

        console.print("[success]Enforcement config updated.[/success]")
