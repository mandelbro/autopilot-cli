"""Cycle reports generator (Task 040).

Generates per-cycle markdown reports to .autopilot/board/cycle-reports/
with dispatch outcomes, duration, and agent results per RFC Section 3.4.3.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class DispatchOutcome:
    """Individual dispatch result for report generation."""

    agent: str
    action: str
    status: str
    duration_seconds: float
    error: str = ""


@dataclass(frozen=True)
class CycleReportData:
    """Data container for cycle report generation."""

    cycle_id: str
    project_id: str
    status: str
    started_at: datetime
    ended_at: datetime | None
    duration_seconds: float
    dispatches: tuple[DispatchOutcome, ...]


class CycleReportGenerator:
    """Generates per-cycle markdown reports."""

    def __init__(self, reports_dir: Path) -> None:
        self._reports_dir = reports_dir

    def generate(self, data: CycleReportData) -> Path:
        """Write a markdown report for a cycle and return the file path."""
        self._reports_dir.mkdir(parents=True, exist_ok=True)

        filename = self._build_filename(data.started_at)
        path = self._reports_dir / filename

        content = self._render(data)
        path.write_text(content)

        _log.info("cycle_report_written: path=%s", path)
        return path

    def _build_filename(self, started_at: datetime) -> str:
        """Build filename: cycle-{date}-{sequence}.md."""
        date_str = started_at.strftime("%Y-%m-%d")
        sequence = self._next_sequence(date_str)
        return f"cycle-{date_str}-{sequence:03d}.md"

    def _next_sequence(self, date_str: str) -> int:
        """Find the next sequence number for a given date."""
        if not self._reports_dir.exists():
            return 1
        existing = sorted(self._reports_dir.glob(f"cycle-{date_str}-*.md"))
        if not existing:
            return 1
        last = existing[-1].stem
        try:
            seq = int(last.rsplit("-", 1)[-1])
            return seq + 1
        except ValueError:
            return 1

    def _render(self, data: CycleReportData) -> str:
        """Render the cycle report as markdown."""
        lines: list[str] = []
        lines.append(f"# Cycle Report: {data.cycle_id}")
        lines.append("")
        lines.append(f"- **Project**: {data.project_id}")
        lines.append(f"- **Status**: {data.status}")
        lines.append(f"- **Started**: {data.started_at.isoformat()}")
        if data.ended_at:
            lines.append(f"- **Ended**: {data.ended_at.isoformat()}")
        lines.append(f"- **Duration**: {data.duration_seconds:.1f}s")
        lines.append("")

        # Summary statistics
        total = len(data.dispatches)
        succeeded = sum(1 for d in data.dispatches if d.status == "success")
        failed = sum(1 for d in data.dispatches if d.status != "success")
        total_dispatch_time = sum(d.duration_seconds for d in data.dispatches)

        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Total Dispatches**: {total}")
        lines.append(f"- **Succeeded**: {succeeded}")
        lines.append(f"- **Failed**: {failed}")
        if total > 0:
            lines.append(f"- **Success Rate**: {succeeded / total * 100:.0f}%")
        lines.append(f"- **Total Dispatch Time**: {total_dispatch_time:.1f}s")
        lines.append("")

        # Agent breakdown
        if data.dispatches:
            lines.append("## Dispatches")
            lines.append("")
            lines.append("| Agent | Action | Status | Duration |")
            lines.append("|-------|--------|--------|----------|")
            for d in data.dispatches:
                status_icon = "pass" if d.status == "success" else "FAIL"
                lines.append(
                    f"| {d.agent} | {d.action} | {status_icon} | {d.duration_seconds:.1f}s |"
                )
            lines.append("")

        # Errors section
        errors = [d for d in data.dispatches if d.error]
        if errors:
            lines.append("## Errors")
            lines.append("")
            for d in errors:
                lines.append(f"### {d.agent}")
                lines.append(f"- **Action**: {d.action}")
                lines.append(f"- **Error**: {d.error}")
                lines.append("")

        return "\n".join(lines)
