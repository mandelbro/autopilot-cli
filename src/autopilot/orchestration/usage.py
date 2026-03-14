"""Usage tracking with per-project limits (Task 034).

Tracks daily/weekly cycle counts against Claude Max plan limits,
with per-project overrides and SQLite backing per RFC Section 3.4.1.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from autopilot.core.config import AutopilotConfig, UsageLimitsConfig
    from autopilot.utils.db import Database

_log = logging.getLogger(__name__)

_USAGE_TABLE_SQL = """\
CREATE TABLE IF NOT EXISTS usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('cycle', 'agent_invocation')),
    agent_name TEXT,
    recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_usage_project_date ON usage(project_id, recorded_at);
"""


@dataclass(frozen=True)
class UsageSummary:
    """Summary of usage for a project or globally."""

    daily_cycles: int
    weekly_cycles: int
    agent_invocations_today: int
    daily_cycle_limit: int
    weekly_cycle_limit: int
    max_agent_invocations_per_cycle: int
    daily_remaining: int
    weekly_remaining: int


class UsageTracker:
    """Tracks daily/weekly cycle counts against configurable limits.

    Stores usage data in SQLite instead of flat JSON files.
    Supports global limits and per-project overrides from config.
    """

    def __init__(
        self,
        db: Database,
        config: AutopilotConfig,
        *,
        per_project_limits: dict[str, UsageLimitsConfig] | None = None,
    ) -> None:
        self._db = db
        self._global_limits = config.usage_limits
        self._per_project_limits = per_project_limits or {}
        self._ensure_table()

    def _ensure_table(self) -> None:
        conn = self._db.get_connection()
        try:
            conn.executescript(_USAGE_TABLE_SQL)
            conn.commit()
        finally:
            conn.close()

    def can_execute(self, project: str) -> tuple[bool, str]:
        """Check all usage limits for a project.

        Returns (True, "") if execution is allowed, or (False, reason) if blocked.
        """
        limits = self._resolve_limits(project)
        now = datetime.now(UTC)

        daily = self._count_cycles(project, _start_of_day(now))
        if daily >= limits.daily_cycle_limit:
            return False, f"Daily cycle limit reached ({daily}/{limits.daily_cycle_limit})"

        weekly = self._count_cycles(project, _start_of_week(now))
        if weekly >= limits.weekly_cycle_limit:
            return False, f"Weekly cycle limit reached ({weekly}/{limits.weekly_cycle_limit})"

        return True, ""

    def record_cycle(self, project: str) -> None:
        """Record a cycle execution for the project."""
        self._insert_usage(project, "cycle")

    def record_agent_invocation(self, project: str, agent: str) -> None:
        """Record an agent invocation within a cycle."""
        self._insert_usage(project, "agent_invocation", agent_name=agent)

    def get_usage_summary(self, project: str | None = None) -> UsageSummary:
        """Get usage summary for a project, or global if None."""
        now = datetime.now(UTC)
        day_start = _start_of_day(now)
        week_start = _start_of_week(now)

        if project is not None:
            limits = self._resolve_limits(project)
            daily = self._count_cycles(project, day_start)
            weekly = self._count_cycles(project, week_start)
            agents_today = self._count_agent_invocations(project, day_start)
        else:
            limits = self._global_limits
            daily = self._count_all_cycles(day_start)
            weekly = self._count_all_cycles(week_start)
            agents_today = self._count_all_agent_invocations(day_start)

        return UsageSummary(
            daily_cycles=daily,
            weekly_cycles=weekly,
            agent_invocations_today=agents_today,
            daily_cycle_limit=limits.daily_cycle_limit,
            weekly_cycle_limit=limits.weekly_cycle_limit,
            max_agent_invocations_per_cycle=limits.max_agent_invocations_per_cycle,
            daily_remaining=max(0, limits.daily_cycle_limit - daily),
            weekly_remaining=max(0, limits.weekly_cycle_limit - weekly),
        )

    def reset_daily(self, project: str) -> None:
        """Delete daily usage records for a project (for boundary resets)."""
        now = datetime.now(UTC)
        day_start = _start_of_day(now)
        conn = self._db.get_connection()
        try:
            conn.execute(
                "DELETE FROM usage WHERE project_id = ? AND recorded_at >= ?",
                (project, day_start.isoformat()),
            )
            conn.commit()
        finally:
            conn.close()

    def reset_weekly(self, project: str) -> None:
        """Delete weekly usage records for a project (for boundary resets)."""
        now = datetime.now(UTC)
        week_start = _start_of_week(now)
        conn = self._db.get_connection()
        try:
            conn.execute(
                "DELETE FROM usage WHERE project_id = ? AND recorded_at >= ?",
                (project, week_start.isoformat()),
            )
            conn.commit()
        finally:
            conn.close()

    def allocate_cycles(
        self,
        projects: list[str],
        total_budget: int,
        priority_weights: dict[str, float] | None = None,
    ) -> dict[str, int]:
        """Allocate cycle budget across projects proportional to priority weights.

        Higher weight = more cycles. Default weight is 1.0.
        Returns dict mapping project name to allocated cycles.
        """
        weights = priority_weights or {}
        project_weights = {p: weights.get(p, 1.0) for p in projects}
        total_weight = sum(project_weights.values())

        if total_weight <= 0 or total_budget <= 0:
            return {p: 0 for p in projects}

        allocation: dict[str, int] = {}
        allocated = 0
        sorted_projects = sorted(projects, key=lambda p: project_weights[p], reverse=True)

        for i, project in enumerate(sorted_projects):
            if i == len(sorted_projects) - 1:
                allocation[project] = total_budget - allocated
            else:
                share = int(total_budget * project_weights[project] / total_weight)
                allocation[project] = share
                allocated += share

        return allocation

    def get_per_project_usage(self) -> dict[str, dict[str, int]]:
        """Get usage breakdown per project.

        Returns dict mapping project_id to {daily_cycles, weekly_cycles, agents_today}.
        """
        now = datetime.now(UTC)
        day_start = _start_of_day(now)
        week_start = _start_of_week(now)

        conn = self._db.get_connection()
        try:
            project_rows = conn.execute("SELECT DISTINCT project_id FROM usage").fetchall()

            result: dict[str, dict[str, int]] = {}
            for row in project_rows:
                project_id = row[0]
                daily = self._count(project_id, "cycle", day_start)
                weekly = self._count(project_id, "cycle", week_start)
                agents = self._count(project_id, "agent_invocation", day_start)
                result[project_id] = {
                    "daily_cycles": daily,
                    "weekly_cycles": weekly,
                    "agents_today": agents,
                }
            return result
        finally:
            conn.close()

    def usage_report(self, projects: list[str] | None = None) -> list[dict[str, Any]]:
        """Generate usage report with per-project breakdown.

        Returns list of dicts with project, usage, limits, and allocation info.
        """
        per_project = self.get_per_project_usage()
        report_projects = projects or list(per_project.keys())

        report: list[dict[str, Any]] = []
        for project in report_projects:
            limits = self._resolve_limits(project)
            usage = per_project.get(
                project,
                {"daily_cycles": 0, "weekly_cycles": 0, "agents_today": 0},
            )
            report.append(
                {
                    "project": project,
                    "daily_cycles": usage["daily_cycles"],
                    "daily_limit": limits.daily_cycle_limit,
                    "daily_remaining": max(0, limits.daily_cycle_limit - usage["daily_cycles"]),
                    "weekly_cycles": usage["weekly_cycles"],
                    "weekly_limit": limits.weekly_cycle_limit,
                    "weekly_remaining": max(0, limits.weekly_cycle_limit - usage["weekly_cycles"]),
                    "agents_today": usage["agents_today"],
                }
            )
        return report

    def _resolve_limits(self, project: str) -> UsageLimitsConfig:
        return self._per_project_limits.get(project, self._global_limits)

    def _insert_usage(
        self,
        project: str,
        usage_type: str,
        agent_name: str | None = None,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        conn = self._db.get_connection()
        try:
            conn.execute(
                "INSERT INTO usage (project_id, type, agent_name, recorded_at) VALUES (?, ?, ?, ?)",
                (project, usage_type, agent_name, now),
            )
            conn.commit()
        finally:
            conn.close()

    def _count_cycles(self, project: str, since: datetime) -> int:
        return self._count(project, "cycle", since)

    def _count_agent_invocations(self, project: str, since: datetime) -> int:
        return self._count(project, "agent_invocation", since)

    def _count_all_cycles(self, since: datetime) -> int:
        return self._count_all("cycle", since)

    def _count_all_agent_invocations(self, since: datetime) -> int:
        return self._count_all("agent_invocation", since)

    def _count(self, project: str, usage_type: str, since: datetime) -> int:
        conn = self._db.get_connection()
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM usage WHERE project_id = ? AND type = ? AND recorded_at >= ?",
                (project, usage_type, since.isoformat()),
            ).fetchone()
            return row[0] if row else 0
        finally:
            conn.close()

    def _count_all(self, usage_type: str, since: datetime) -> int:
        conn = self._db.get_connection()
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM usage WHERE type = ? AND recorded_at >= ?",
                (usage_type, since.isoformat()),
            ).fetchone()
            return row[0] if row else 0
        finally:
            conn.close()


def _start_of_day(dt: datetime) -> datetime:
    """Return the start of the UTC day for the given datetime."""
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def _start_of_week(dt: datetime) -> datetime:
    """Return the start of the ISO week (Monday) for the given datetime."""
    day_of_week = dt.weekday()  # Monday=0
    start = dt - timedelta(days=day_of_week)
    return start.replace(hour=0, minute=0, second=0, microsecond=0)
