"""UAT reporter.

Renders UAT results as Rich-formatted console output and Markdown reports.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path  # noqa: TC003 — used at runtime

import structlog
from rich.console import Console
from rich.table import Table
from rich.text import Text

from autopilot.uat.test_executor import UATResult  # noqa: TC001

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Console reporter
# ---------------------------------------------------------------------------


class UATReporter:
    """Renders UAT results in Rich and Markdown formats."""

    def __init__(self, console: Console | None = None) -> None:
        self._console = console or Console()

    def render_task_report(self, result: UATResult, *, task_id: str = "") -> str:
        """Render a UAT result as Rich-formatted text.

        Returns the rendered string (also prints to console).
        Color coding: green for pass, red for fail, yellow for partial/skip.
        """
        buf = Console(record=True, width=100)

        # Header
        status = self._status_text(result)
        buf.print()
        title = "UAT Report"
        if task_id:
            title += f" — Task {task_id}"
        buf.print(f"[bold]{title}[/bold]")
        buf.print(status)
        buf.print()

        # Summary
        buf.print(f"  Score: {result.score:.0%}")
        buf.print(
            f"  Tests: {result.test_count} total, "
            f"[green]{result.passed} passed[/green], "
            f"[red]{result.failed} failed[/red], "
            f"[yellow]{result.skipped} skipped[/yellow]"
        )
        buf.print()

        # Category breakdown
        if result.categories:
            table = Table(title="Category Breakdown", show_lines=False)
            table.add_column("Category", style="bold")
            table.add_column("Total", justify="right")
            table.add_column("Passed", justify="right", style="green")
            table.add_column("Failed", justify="right", style="red")
            table.add_column("Skipped", justify="right", style="yellow")

            for cat in result.categories:
                table.add_row(
                    cat.category,
                    str(cat.total),
                    str(cat.passed),
                    str(cat.failed),
                    str(cat.skipped),
                )
            buf.print(table)
            buf.print()

        # Failures
        if result.failures:
            buf.print("[bold red]Failures:[/bold red]")
            for f in result.failures:
                buf.print(f"  [red]FAIL[/red] {f.test_name}")
                if f.category:
                    buf.print(f"    Category: {f.category}")
                if f.spec_reference:
                    buf.print(f"    Spec: {f.spec_reference}")
                if f.actual:
                    # Truncate long output
                    actual = f.actual[:200]
                    buf.print(f"    Details: {actual}")
                if f.suggestion:
                    buf.print(f"    Suggestion: {f.suggestion}")
                buf.print()

        output = buf.export_text()
        self._console.print(output, end="")
        return output

    def render_to_markdown(self, result: UATResult, *, task_id: str = "") -> str:
        """Render a UAT result as Markdown text."""
        lines: list[str] = []

        title = "UAT Report"
        if task_id:
            title += f" - Task {task_id}"
        lines.append(f"# {title}")
        lines.append("")
        lines.append(f"**Generated**: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}")
        lines.append("")

        # Status
        if result.overall_pass:
            status = "PASS"
        elif result.failed > 0:
            status = "FAIL"
        else:
            status = "PARTIAL"
        lines.append(f"**Status**: {status}")
        lines.append(f"**Score**: {result.score:.0%}")
        lines.append("")

        # Summary table
        lines.append("## Summary")
        lines.append("")
        lines.append("| Metric | Count |")
        lines.append("|--------|-------|")
        lines.append(f"| Total | {result.test_count} |")
        lines.append(f"| Passed | {result.passed} |")
        lines.append(f"| Failed | {result.failed} |")
        lines.append(f"| Skipped | {result.skipped} |")
        lines.append("")

        # Category breakdown
        if result.categories:
            lines.append("## Categories")
            lines.append("")
            lines.append("| Category | Total | Passed | Failed | Skipped |")
            lines.append("|----------|-------|--------|--------|---------|")
            for cat in result.categories:
                lines.append(
                    f"| {cat.category} | {cat.total} | "
                    f"{cat.passed} | {cat.failed} | {cat.skipped} |"
                )
            lines.append("")

        # Failures
        if result.failures:
            lines.append("## Failures")
            lines.append("")
            for f in result.failures:
                lines.append(f"### {f.test_name}")
                lines.append("")
                lines.append(f"- **Category**: {f.category}")
                if f.spec_reference:
                    lines.append(f"- **Spec**: {f.spec_reference}")
                if f.expected:
                    lines.append(f"- **Expected**: {f.expected}")
                if f.actual:
                    lines.append(f"- **Actual**: {f.actual[:300]}")
                if f.suggestion:
                    lines.append(f"- **Suggestion**: {f.suggestion}")
                lines.append("")

        return "\n".join(lines)

    def save_report(self, result: UATResult, *, task_id: str, project_dir: Path) -> Path:
        """Save a Markdown report to the standard location."""
        report_dir = project_dir / ".autopilot" / "uat" / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"task-{task_id}-uat.md"
        content = self.render_to_markdown(result, task_id=task_id)
        report_path.write_text(content, encoding="utf-8")
        logger.info("uat_report_saved", path=str(report_path))
        return report_path

    # -- private helpers ---------------------------------------------------

    def _status_text(self, result: UATResult) -> Text:
        """Build a coloured status label."""
        if result.overall_pass:
            return Text("  Status: PASS", style="bold green")
        if result.failed > 0:
            return Text("  Status: FAIL", style="bold red")
        return Text("  Status: PARTIAL", style="bold yellow")
