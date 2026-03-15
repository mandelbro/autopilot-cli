"""Cross-project quality reporting and trend analysis (Task 086).

Provides enforcement quality trends, cross-project summaries,
and operational health metrics per RFC Section 10.
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3

    from autopilot.utils.db import Database

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class TrendPoint:
    """A single data point in a quality trend."""

    date: str
    violation_count: int
    violation_density: float  # violations per cycle


@dataclass(frozen=True)
class TrendReport:
    """Enforcement quality trend over time."""

    project_id: str
    days: int
    total_violations: int
    average_density: float
    trend_direction: str  # "improving", "degrading", "stable"
    points: list[TrendPoint] = field(default_factory=list[TrendPoint])


@dataclass(frozen=True)
class ProjectSummary:
    """Summary metrics for a single project."""

    project_id: str
    project_name: str
    velocity: float
    quality_score: float  # 0.0 to 1.0
    total_sessions: int
    active_sessions: int


@dataclass(frozen=True)
class CrossProjectSummary:
    """Aggregated summary across all projects."""

    total_projects: int
    total_sessions: int
    average_velocity: float
    average_quality: float
    projects: list[ProjectSummary] = field(default_factory=list[ProjectSummary])


@dataclass(frozen=True)
class HealthReport:
    """Operational health metrics for a project."""

    project_id: str
    cycle_success_rate: float
    total_cycles: int
    failed_cycles: int
    timeouts: int
    circuit_breaker_activations: int
    health_status: str  # "healthy", "degraded", "unhealthy"


class QualityReporter:
    """Cross-project quality reporting and trend analysis."""

    def __init__(self, db: Database) -> None:
        self._db = db
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        """Create quality tracking tables if they don't exist."""
        conn = self._db.get_connection()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS enforcement_violations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL,
                    cycle_id TEXT,
                    category TEXT NOT NULL,
                    severity TEXT NOT NULL DEFAULT 'warning',
                    file_path TEXT,
                    message TEXT,
                    recorded_at TEXT NOT NULL
                        DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
                );
                CREATE INDEX IF NOT EXISTS idx_violations_project_date
                    ON enforcement_violations(project_id, recorded_at);

                CREATE TABLE IF NOT EXISTS operational_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    details TEXT,
                    recorded_at TEXT NOT NULL
                        DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
                );
                CREATE INDEX IF NOT EXISTS idx_ops_events_project
                    ON operational_events(project_id, event_type);
            """)
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Write helpers
    # ------------------------------------------------------------------

    def record_violation(
        self,
        project_id: str,
        category: str,
        *,
        cycle_id: str = "",
        severity: str = "warning",
        file_path: str = "",
        message: str = "",
    ) -> None:
        """Record an enforcement violation."""
        conn = self._db.get_connection()
        try:
            conn.execute(
                "INSERT INTO enforcement_violations "
                "(project_id, cycle_id, category, severity, file_path, message) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (project_id, cycle_id, category, severity, file_path, message),
            )
            conn.commit()
        finally:
            conn.close()

    def record_operational_event(self, project_id: str, event_type: str, details: str = "") -> None:
        """Record an operational event.

        Recognised *event_type* values:
        ``cycle_success``, ``cycle_failure``, ``timeout``, ``circuit_breaker``.
        """
        conn = self._db.get_connection()
        try:
            conn.execute(
                "INSERT INTO operational_events (project_id, event_type, details) VALUES (?, ?, ?)",
                (project_id, event_type, details),
            )
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Trend analysis
    # ------------------------------------------------------------------

    def enforcement_trends(self, project_id: str, days: int = 30) -> TrendReport:
        """Get violation density trends over time for a project."""
        conn = self._db.get_connection()
        try:
            cutoff = f"-{days} days"

            # Violations grouped by date
            violation_rows = conn.execute(
                "SELECT date(recorded_at) AS d, COUNT(*) AS cnt "
                "FROM enforcement_violations "
                "WHERE project_id = ? "
                "  AND recorded_at >= datetime('now', ?) "
                "GROUP BY d ORDER BY d",
                (project_id, cutoff),
            ).fetchall()

            # Cycle counts per date (successes + failures)
            cycle_rows = conn.execute(
                "SELECT date(recorded_at) AS d, COUNT(*) AS cnt "
                "FROM operational_events "
                "WHERE project_id = ? "
                "  AND event_type IN ('cycle_success', 'cycle_failure') "
                "  AND recorded_at >= datetime('now', ?) "
                "GROUP BY d ORDER BY d",
                (project_id, cutoff),
            ).fetchall()

            violations_by_date: dict[str, int] = {row["d"]: row["cnt"] for row in violation_rows}
            cycles_by_date: dict[str, int] = {row["d"]: row["cnt"] for row in cycle_rows}

            all_dates = sorted(set(violations_by_date) | set(cycles_by_date))

            points: list[TrendPoint] = []
            for d in all_dates:
                v_count = violations_by_date.get(d, 0)
                c_count = max(cycles_by_date.get(d, 0), 1)
                density = v_count / c_count
                points.append(
                    TrendPoint(date=d, violation_count=v_count, violation_density=density)
                )

            total_violations = sum(p.violation_count for p in points)
            avg_density = sum(p.violation_density for p in points) / len(points) if points else 0.0
            direction = self._compute_trend_direction(points)

            return TrendReport(
                project_id=project_id,
                days=days,
                total_violations=total_violations,
                average_density=round(avg_density, 4),
                trend_direction=direction,
                points=points,
            )
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Cross-project summary
    # ------------------------------------------------------------------

    def cross_project_summary(self) -> CrossProjectSummary:
        """Get aggregated summary across all projects."""
        conn = self._db.get_connection()
        try:
            project_rows = conn.execute(
                "SELECT DISTINCT project_id FROM operational_events"
            ).fetchall()

            if not project_rows:
                return CrossProjectSummary(
                    total_projects=0,
                    total_sessions=0,
                    average_velocity=0.0,
                    average_quality=0.0,
                    projects=[],
                )

            summaries: list[ProjectSummary] = []
            for row in project_rows:
                pid = row["project_id"]
                summary = self._project_summary(conn, pid)
                summaries.append(summary)

            total_sessions = sum(s.total_sessions for s in summaries)
            avg_vel = sum(s.velocity for s in summaries) / len(summaries) if summaries else 0.0
            avg_qual = (
                sum(s.quality_score for s in summaries) / len(summaries) if summaries else 0.0
            )

            return CrossProjectSummary(
                total_projects=len(summaries),
                total_sessions=total_sessions,
                average_velocity=round(avg_vel, 2),
                average_quality=round(avg_qual, 4),
                projects=summaries,
            )
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Operational health
    # ------------------------------------------------------------------

    def operational_health(self, project_id: str) -> HealthReport:
        """Get operational health metrics for a project."""
        conn = self._db.get_connection()
        try:
            rows = conn.execute(
                "SELECT event_type, COUNT(*) AS cnt "
                "FROM operational_events "
                "WHERE project_id = ? "
                "GROUP BY event_type",
                (project_id,),
            ).fetchall()

            counts: dict[str, int] = {r["event_type"]: r["cnt"] for r in rows}
            successes = counts.get("cycle_success", 0)
            failures = counts.get("cycle_failure", 0)
            timeouts = counts.get("timeout", 0)
            cb_activations = counts.get("circuit_breaker", 0)
            total = successes + failures

            success_rate = successes / max(total, 1)
            status = self._health_status(success_rate)

            return HealthReport(
                project_id=project_id,
                cycle_success_rate=round(success_rate, 4),
                total_cycles=total,
                failed_cycles=failures,
                timeouts=timeouts,
                circuit_breaker_activations=cb_activations,
                health_status=status,
            )
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # CSV export
    # ------------------------------------------------------------------

    def export_csv(self, project_id: str | None = None, days: int = 30) -> str:
        """Export quality data as CSV string."""
        conn = self._db.get_connection()
        try:
            cutoff = f"-{days} days"
            if project_id:
                rows = conn.execute(
                    "SELECT project_id, cycle_id, category, severity, "
                    "file_path, message, recorded_at "
                    "FROM enforcement_violations "
                    "WHERE project_id = ? "
                    "  AND recorded_at >= datetime('now', ?) "
                    "ORDER BY recorded_at",
                    (project_id, cutoff),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT project_id, cycle_id, category, severity, "
                    "file_path, message, recorded_at "
                    "FROM enforcement_violations "
                    "WHERE recorded_at >= datetime('now', ?) "
                    "ORDER BY recorded_at",
                    (cutoff,),
                ).fetchall()

            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(
                [
                    "project_id",
                    "cycle_id",
                    "category",
                    "severity",
                    "file_path",
                    "message",
                    "recorded_at",
                ]
            )
            for r in rows:
                writer.writerow(
                    [
                        r["project_id"],
                        r["cycle_id"],
                        r["category"],
                        r["severity"],
                        r["file_path"],
                        r["message"],
                        r["recorded_at"],
                    ]
                )
            return buf.getvalue()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_trend_direction(points: list[TrendPoint]) -> str:
        """Compare first-half vs second-half density to determine trend."""
        if len(points) < 2:
            return "stable"

        mid = len(points) // 2
        first_half = points[:mid]
        second_half = points[mid:]

        avg_first = sum(p.violation_density for p in first_half) / len(first_half)
        avg_second = sum(p.violation_density for p in second_half) / len(second_half)

        threshold = max(avg_first * 0.1, 0.01)
        diff = avg_second - avg_first

        if diff < -threshold:
            return "improving"
        if diff > threshold:
            return "degrading"
        return "stable"

    def _project_summary(self, conn: sqlite3.Connection, project_id: str) -> ProjectSummary:
        """Build a ProjectSummary for one project from the open *conn*."""
        # Cycle counts
        cycle_row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM operational_events "
            "WHERE project_id = ? AND event_type IN ('cycle_success', 'cycle_failure')",
            (project_id,),
        ).fetchone()
        total_cycles = cycle_row["cnt"] if cycle_row else 0

        # Violation count
        viol_row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM enforcement_violations WHERE project_id = ?",
            (project_id,),
        ).fetchone()
        total_violations = viol_row["cnt"] if viol_row else 0

        quality_score = max(0.0, 1.0 - (total_violations / max(total_cycles, 1)))

        # Session counts (may not have a sessions table entry for every project)
        try:
            sess_row = conn.execute(
                "SELECT COUNT(*) AS total, "
                "SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) AS active "
                "FROM sessions WHERE project_id = ?",
                (project_id,),
            ).fetchone()
            total_sessions = sess_row["total"] if sess_row else 0
            active_sessions = sess_row["active"] if sess_row else 0
        except Exception:
            total_sessions = 0
            active_sessions = 0

        # Velocity: average points_completed from velocity table
        try:
            vel_row = conn.execute(
                "SELECT AVG(points_completed) AS avg_vel FROM velocity WHERE project_id = ?",
                (project_id,),
            ).fetchone()
            velocity = vel_row["avg_vel"] if vel_row and vel_row["avg_vel"] else 0.0
        except Exception:
            velocity = 0.0

        # Try to get project name
        try:
            proj_row = conn.execute(
                "SELECT name FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
            project_name = proj_row["name"] if proj_row else project_id
        except Exception:
            project_name = project_id

        return ProjectSummary(
            project_id=project_id,
            project_name=project_name,
            velocity=round(velocity, 2),
            quality_score=round(max(0.0, min(1.0, quality_score)), 4),
            total_sessions=total_sessions,
            active_sessions=active_sessions,
        )

    @staticmethod
    def _health_status(success_rate: float) -> str:
        """Map success rate to a health label."""
        if success_rate >= 0.9:
            return "healthy"
        if success_rate >= 0.7:
            return "degraded"
        return "unhealthy"
