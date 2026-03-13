"""Deploy status board writer (Task 053).

Writes deployment health results to the Deployment Status section of
project-board.md so the PL can gate feature verification on deploy health.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from autopilot.monitoring.health_checker import HealthCheckResult


class DeployStatusWriter:
    """Writes health check results to the board's Deployment Status section."""

    def update_board(self, board_path: Path, results: list[HealthCheckResult]) -> None:
        """Update the Deployment Status section in project-board.md.

        If the board file does not exist it is created with only the
        Deployment Status section.  If it already exists, the section
        is replaced in-place while preserving other content.
        """
        table = self._build_table(results)

        if not board_path.exists():
            board_path.parent.mkdir(parents=True, exist_ok=True)
            board_path.write_text(f"# Project Board\n\n## Deployment Status\n\n{table}\n")
            return

        content = board_path.read_text()
        new_content = self._replace_section(content, table)
        board_path.write_text(new_content)

    def _build_table(self, results: list[HealthCheckResult]) -> str:
        """Build a markdown table from health check results."""
        now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
        lines = [
            "| Service | Status | Last Check | Health Endpoints | Notes |",
            "|---------|--------|------------|------------------|-------|",
        ]

        by_service: dict[str, list[HealthCheckResult]] = {}
        for r in results:
            by_service.setdefault(r.service_name, []).append(r)

        for svc_name, svc_results in sorted(by_service.items()):
            all_healthy = all(r.healthy for r in svc_results)
            status = "healthy" if all_healthy else "unhealthy"
            endpoints = ", ".join(r.endpoint for r in svc_results)
            notes = "; ".join(r.error for r in svc_results if r.error)
            lines.append(f"| {svc_name} | {status} | {now} | {endpoints} | {notes} |")

        return "\n".join(lines)

    @staticmethod
    def _replace_section(content: str, table: str) -> str:
        """Replace the Deployment Status section, preserving other content."""
        marker = "## Deployment Status"
        if marker not in content:
            return f"{content.rstrip()}\n\n{marker}\n\n{table}\n"

        before, rest = content.split(marker, 1)
        # Find next section header or end of file
        lines = rest.split("\n")
        after_lines: list[str] = []
        found_next = False
        for line in lines[1:]:  # skip the marker line itself
            if line.startswith("## ") and not found_next:
                found_next = True
            if found_next:
                after_lines.append(line)

        after = "\n".join(after_lines) if after_lines else ""
        result = f"{before}{marker}\n\n{table}\n"
        if after:
            result = f"{result}\n{after}"
        return result
