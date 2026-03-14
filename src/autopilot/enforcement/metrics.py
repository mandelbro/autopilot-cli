"""Enforcement metrics collection and storage (Task 066, RFC Section 3.4.2).

Stores per-category violation counts in SQLite for trend analysis,
violation density calculation, and sprint-over-sprint tracking.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from autopilot.core.models import CheckResult


@dataclass(frozen=True)
class MetricPoint:
    """A single time-series data point for a metric."""

    timestamp: str
    violation_count: int
    files_scanned: int


@dataclass(frozen=True)
class MetricsSummary:
    """Aggregated metrics summary across categories."""

    by_category: dict[str, int]
    total_violations: int
    trend_direction: str  # "improving", "stable", "degrading"


class EnforcementMetricsCollector:
    """Collects and queries enforcement metrics from SQLite.

    Args:
        db_path: Path to the SQLite database file.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Create the enforcement_metrics_detail table if it does not exist."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._db_path))
        try:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS enforcement_metrics_detail (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    collected_at TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    violations_count INTEGER NOT NULL DEFAULT 0,
                    files_scanned INTEGER NOT NULL DEFAULT 0,
                    duration_seconds REAL NOT NULL DEFAULT 0.0
                )"""
            )
            conn.commit()
        finally:
            conn.close()

    def record_check(self, project_id: str, results: list[CheckResult]) -> None:
        """Insert one row per category for a check run.

        Args:
            project_id: Identifier of the project being checked.
            results: List of check results to record.
        """
        conn = sqlite3.connect(str(self._db_path))
        try:
            now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S")
            for r in results:
                conn.execute(
                    """INSERT INTO enforcement_metrics_detail
                    (collected_at, project_id, category, violations_count,
                     files_scanned, duration_seconds)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        now,
                        project_id,
                        r.category,
                        len(r.violations),
                        r.files_scanned,
                        r.duration_seconds,
                    ),
                )
            conn.commit()
        finally:
            conn.close()

    def get_trend(self, project_id: str, category: str, days: int = 30) -> list[MetricPoint]:
        """Query time-series data for a category within the last N days.

        Args:
            project_id: Project identifier.
            category: Enforcement category name.
            days: Number of days to look back (default 30).

        Returns:
            List of MetricPoint ordered by timestamp ascending.
        """
        conn = sqlite3.connect(str(self._db_path))
        try:
            cutoff = datetime.now(UTC) - timedelta(days=days)
            cutoff_str = cutoff.strftime("%Y-%m-%dT%H:%M:%S")
            cursor = conn.execute(
                """SELECT collected_at, violations_count, files_scanned
                FROM enforcement_metrics_detail
                WHERE project_id = ?
                  AND category = ?
                  AND collected_at >= ?
                ORDER BY collected_at ASC""",
                (project_id, category, cutoff_str),
            )
            return [
                MetricPoint(
                    timestamp=row[0],
                    violation_count=row[1],
                    files_scanned=row[2],
                )
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()

    def get_summary(self, project_id: str) -> MetricsSummary:
        """Get latest check's per-category counts, total, and trend direction.

        Trend direction compares the latest check run's total violations
        against the previous check run. If no previous data exists, returns
        ``"stable"``.

        Args:
            project_id: Project identifier.

        Returns:
            A MetricsSummary with per-category counts and trend.
        """
        conn = sqlite3.connect(str(self._db_path))
        try:
            # Find the two most recent distinct collected_at timestamps
            cursor = conn.execute(
                """SELECT DISTINCT collected_at
                FROM enforcement_metrics_detail
                WHERE project_id = ?
                ORDER BY collected_at DESC
                LIMIT 2""",
                (project_id,),
            )
            timestamps = [row[0] for row in cursor.fetchall()]

            if not timestamps:
                return MetricsSummary(by_category={}, total_violations=0, trend_direction="stable")

            latest_ts = timestamps[0]

            # Get per-category counts for latest
            cursor = conn.execute(
                """SELECT category, violations_count
                FROM enforcement_metrics_detail
                WHERE project_id = ? AND collected_at = ?""",
                (project_id, latest_ts),
            )
            by_category: dict[str, int] = {}
            for row in cursor.fetchall():
                by_category[row[0]] = row[1]
            latest_total = sum(by_category.values())

            # Determine trend direction
            if len(timestamps) < 2:
                trend = "stable"
            else:
                prev_ts = timestamps[1]
                cursor = conn.execute(
                    """SELECT SUM(violations_count)
                    FROM enforcement_metrics_detail
                    WHERE project_id = ? AND collected_at = ?""",
                    (project_id, prev_ts),
                )
                prev_total = cursor.fetchone()[0] or 0
                if latest_total < prev_total:
                    trend = "improving"
                elif latest_total > prev_total:
                    trend = "degrading"
                else:
                    trend = "stable"

            return MetricsSummary(
                by_category=by_category,
                total_violations=latest_total,
                trend_direction=trend,
            )
        finally:
            conn.close()

    def violation_density(self, project_id: str, total_lines: int) -> float:
        """Calculate violations per 1K lines of code.

        Args:
            project_id: Project identifier.
            total_lines: Total lines of code in the project.

        Returns:
            Violation density (violations per 1000 lines), or 0.0 if
            total_lines is zero.
        """
        if total_lines == 0:
            return 0.0
        summary = self.get_summary(project_id)
        return (summary.total_violations / total_lines) * 1000
