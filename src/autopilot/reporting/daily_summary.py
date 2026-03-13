"""Daily summary report aggregation for PL context (Task 041).

Aggregates cycle reports for a given date into a concise summary
optimized for PL prompt injection per RFC Section 3.6.
"""

from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass
from datetime import UTC, date
from typing import TYPE_CHECKING

from autopilot.reporting.cycle_reports import CycleReportData

if TYPE_CHECKING:
    from pathlib import Path

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class DailySummary:
    """Aggregated daily summary data."""

    date: date
    cycles_run: int
    total_dispatches: int
    succeeded: int
    failed: int
    agent_breakdown: dict[str, dict[str, int]]
    notable_errors: list[str]
    total_duration_seconds: float


class DailySummaryGenerator:
    """Generates daily summary reports aggregating cycle data for PL context."""

    def __init__(self, reports_dir: Path) -> None:
        self._reports_dir = reports_dir

    def aggregate(
        self, cycle_reports: list[CycleReportData], *, target_date: date | None = None
    ) -> DailySummary:
        """Aggregate cycle report data into a DailySummary."""
        if not cycle_reports:
            return DailySummary(
                date=target_date or date.today(),
                cycles_run=0,
                total_dispatches=0,
                succeeded=0,
                failed=0,
                agent_breakdown={},
                notable_errors=[],
                total_duration_seconds=0.0,
            )

        report_date = cycle_reports[0].started_at.date()
        total_dispatches = 0
        succeeded = 0
        failed = 0
        agent_breakdown: dict[str, dict[str, int]] = {}
        notable_errors: list[str] = []
        total_duration = 0.0

        for report in cycle_reports:
            total_duration += report.duration_seconds
            for d in report.dispatches:
                total_dispatches += 1
                if d.status == "success":
                    succeeded += 1
                else:
                    failed += 1
                    if d.error:
                        notable_errors.append(f"[{d.agent}] {d.error}")

                if d.agent not in agent_breakdown:
                    agent_breakdown[d.agent] = {"success": 0, "failed": 0}
                if d.status == "success":
                    agent_breakdown[d.agent]["success"] += 1
                else:
                    agent_breakdown[d.agent]["failed"] += 1

        return DailySummary(
            date=report_date,
            cycles_run=len(cycle_reports),
            total_dispatches=total_dispatches,
            succeeded=succeeded,
            failed=failed,
            agent_breakdown=agent_breakdown,
            notable_errors=notable_errors,
            total_duration_seconds=total_duration,
        )

    def generate(self, project_dir: Path, target_date: date) -> str:
        """Produce a concise daily summary markdown for PL prompt injection.

        Scans cycle report files for the given date and aggregates them.
        """
        reports = self._load_cycle_reports_for_date(project_dir, target_date)
        summary = self.aggregate(reports, target_date=target_date)
        return self._render(summary)

    def _load_cycle_reports_for_date(
        self, project_dir: Path, target_date: date
    ) -> list[CycleReportData]:
        """Load CycleReportData from markdown files for a specific date.

        Parses the cycle report markdown back into CycleReportData objects.
        Only returns reports matching the target date.
        """
        reports_dir = project_dir / ".autopilot" / "board" / "cycle-reports"
        if not reports_dir.exists():
            return []

        date_str = target_date.isoformat()
        pattern = f"cycle-{date_str}-*.md"
        report_files = sorted(reports_dir.glob(pattern))

        results: list[CycleReportData] = []
        for path in report_files:
            report = self._parse_cycle_report(path, target_date)
            if report is not None:
                results.append(report)

        return results

    def _parse_cycle_report(self, path: Path, target_date: date) -> CycleReportData | None:
        """Parse a cycle report markdown file back into CycleReportData."""
        from datetime import datetime

        from autopilot.reporting.cycle_reports import DispatchOutcome

        try:
            content = path.read_text()
        except OSError:
            _log.warning("failed_to_read_cycle_report: path=%s", path)
            return None

        lines = content.splitlines()
        cycle_id = ""
        project_id = ""
        status = ""
        started_at = datetime(target_date.year, target_date.month, target_date.day, tzinfo=UTC)
        ended_at: datetime | None = None
        duration_seconds = 0.0
        dispatches: list[DispatchOutcome] = []

        in_dispatches_table = False
        in_errors_section = False
        error_agent = ""
        errors_by_agent: dict[str, str] = {}

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("# Cycle Report:"):
                cycle_id = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("- **Project**:"):
                project_id = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("- **Status**:"):
                status = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("- **Started**:"):
                raw_dt = stripped.split(":", 1)[1].strip()
                with contextlib.suppress(ValueError):
                    started_at = datetime.fromisoformat(raw_dt)
            elif stripped.startswith("- **Ended**:"):
                raw_dt = stripped.split(":", 1)[1].strip()
                with contextlib.suppress(ValueError):
                    ended_at = datetime.fromisoformat(raw_dt)
            elif stripped.startswith("- **Duration**:"):
                raw_dur = stripped.split(":", 1)[1].strip().rstrip("s")
                with contextlib.suppress(ValueError):
                    duration_seconds = float(raw_dur)
            elif stripped == "## Dispatches" or stripped.startswith("## Dispatches "):
                in_dispatches_table = True
                in_errors_section = False
            elif stripped == "## Errors" or stripped.startswith("## Errors "):
                in_dispatches_table = False
                in_errors_section = True
            elif (
                stripped.startswith("## ")
                and not stripped.startswith("## Dispatches")
                and not stripped.startswith("## Errors")
            ):
                in_dispatches_table = False
                in_errors_section = False
            elif (
                in_dispatches_table and stripped.startswith("|") and not stripped.startswith("|--")
            ):
                parts = [p.strip() for p in stripped.split("|")]
                parts = [p for p in parts if p]
                if len(parts) >= 4 and parts[0] not in ("Agent",):
                    agent = parts[0]
                    action = parts[1]
                    d_status = "success" if parts[2] == "pass" else "failed"
                    d_dur = 0.0
                    with contextlib.suppress(ValueError):
                        d_dur = float(parts[3].rstrip("s"))
                    dispatches.append(
                        DispatchOutcome(
                            agent=agent,
                            action=action,
                            status=d_status,
                            duration_seconds=d_dur,
                        )
                    )
            elif in_errors_section:
                if stripped.startswith("### "):
                    error_agent = stripped[4:].strip()
                elif stripped.startswith("- **Error**:"):
                    error_msg = stripped.split(":", 1)[1].strip()
                    if error_agent:
                        errors_by_agent[error_agent] = error_msg

        # Attach errors to dispatches
        if errors_by_agent:
            enriched: list[DispatchOutcome] = []
            for d in dispatches:
                if d.agent in errors_by_agent and d.status != "success":
                    enriched.append(
                        DispatchOutcome(
                            agent=d.agent,
                            action=d.action,
                            status=d.status,
                            duration_seconds=d.duration_seconds,
                            error=errors_by_agent[d.agent],
                        )
                    )
                else:
                    enriched.append(d)
            dispatches = enriched

        return CycleReportData(
            cycle_id=cycle_id,
            project_id=project_id,
            status=status,
            started_at=started_at,
            ended_at=ended_at,
            duration_seconds=duration_seconds,
            dispatches=tuple(dispatches),
        )

    def _render(self, summary: DailySummary) -> str:
        """Render daily summary as concise markdown for PL prompt injection."""
        lines: list[str] = []
        lines.append(f"# Daily Summary: {summary.date.isoformat()}")
        lines.append("")
        lines.append(
            f"Cycles: {summary.cycles_run} | "
            f"Dispatches: {summary.total_dispatches} "
            f"({summary.succeeded} ok, {summary.failed} fail) | "
            f"Duration: {summary.total_duration_seconds:.0f}s"
        )
        lines.append("")

        if summary.agent_breakdown:
            lines.append("## Agents")
            lines.append("")
            lines.append("| Agent | OK | Fail |")
            lines.append("|-------|----|------|")
            for agent, counts in sorted(summary.agent_breakdown.items()):
                lines.append(f"| {agent} | {counts['success']} | {counts['failed']} |")
            lines.append("")

        if summary.notable_errors:
            lines.append("## Errors")
            lines.append("")
            for err in summary.notable_errors[:10]:
                lines.append(f"- {err}")
            lines.append("")

        return "\n".join(lines)
