"""Decision log reporting with search and trend analysis (Task 043).

Integrates with coordination/decisions.py DecisionLog to provide
reporting, search across archived logs, and decision frequency analysis
per RFC Section 3.6.
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

from autopilot.coordination.decisions import Decision, DecisionLog

if TYPE_CHECKING:
    from pathlib import Path

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class DecisionTrend:
    """Decision frequency analysis."""

    total_decisions: int
    decisions_by_agent: dict[str, int]
    decisions_by_month: dict[str, int]
    most_active_agent: str


class DecisionLogReporter:
    """Reports on decision log data with search and trend analysis."""

    def __init__(self, board_dir: Path) -> None:
        self._board_dir = board_dir
        self._log = DecisionLog(board_dir)

    def recent_decisions(self, limit: int = 10) -> list[Decision]:
        """Return the most recent decisions."""
        return self._log.list_recent(limit)

    def decisions_by_agent(self, agent: str) -> list[Decision]:
        """Return decisions by a specific agent."""
        return [d for d in self._all_decisions() if d.agent == agent]

    def search_decisions(self, query: str) -> list[Decision]:
        """Search decisions across current and archived logs."""
        results: list[Decision] = []
        query_lower = query.lower()

        for d in self._all_decisions():
            if (
                query_lower in d.agent.lower()
                or query_lower in d.action.lower()
                or query_lower in d.rationale.lower()
            ):
                results.append(d)

        return results

    def decision_trend(self) -> DecisionTrend:
        """Analyze decision frequency patterns."""
        all_decisions = self._all_decisions()

        if not all_decisions:
            return DecisionTrend(
                total_decisions=0,
                decisions_by_agent={},
                decisions_by_month={},
                most_active_agent="",
            )

        agent_counts: Counter[str] = Counter()
        month_counts: Counter[str] = Counter()

        for d in all_decisions:
            agent_counts[d.agent] += 1
            month = d.timestamp[:7] if len(d.timestamp) >= 7 else "unknown"
            month_counts[month] += 1

        most_active = agent_counts.most_common(1)[0][0] if agent_counts else ""

        return DecisionTrend(
            total_decisions=len(all_decisions),
            decisions_by_agent=dict(agent_counts),
            decisions_by_month=dict(month_counts),
            most_active_agent=most_active,
        )

    def generate_report(self) -> str:
        """Generate a decision log summary report."""
        trend = self.decision_trend()
        recent = self.recent_decisions(limit=5)

        lines: list[str] = []
        lines.append("# Decision Log Report")
        lines.append("")
        lines.append(f"Total decisions: {trend.total_decisions}")
        if trend.most_active_agent:
            lines.append(f"Most active agent: {trend.most_active_agent}")
        lines.append("")

        if trend.decisions_by_agent:
            lines.append("## Decisions by Agent")
            lines.append("")
            lines.append("| Agent | Count |")
            lines.append("|-------|-------|")
            for agent, count in sorted(
                trend.decisions_by_agent.items(), key=lambda x: x[1], reverse=True
            ):
                lines.append(f"| {agent} | {count} |")
            lines.append("")

        if trend.decisions_by_month:
            lines.append("## Decisions by Month")
            lines.append("")
            lines.append("| Month | Count |")
            lines.append("|-------|-------|")
            for month, count in sorted(trend.decisions_by_month.items()):
                lines.append(f"| {month} | {count} |")
            lines.append("")

        if recent:
            lines.append("## Recent Decisions")
            lines.append("")
            for d in recent:
                lines.append(f"- **{d.id}** [{d.agent}] {d.action}")
                if d.rationale:
                    lines.append(f"  Rationale: {d.rationale}")
            lines.append("")

        return "\n".join(lines)

    def _all_decisions(self) -> list[Decision]:
        """Load all decisions from current log and archives."""
        decisions = self._log.list_all()

        archive_dir = self._board_dir / "decision-log-archive"
        if archive_dir.exists():
            for archive_file in sorted(archive_dir.glob("decision-log-*.md")):
                archived = self._log.load_from_file(archive_file)
                decisions = archived + decisions

        return decisions
