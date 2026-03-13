"""Velocity reporting with trend analysis and forecasting (Task 042).

Provides sprint history, velocity trends, and completion forecasting
from SQLite data per RFC Section 10 success metrics.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autopilot.utils.db import Database


_ROLLING_WINDOW = 5
_MIN_SPRINTS_FOR_FORECAST = 3
_SPRINT_DURATION_WEEKS = 2


@dataclass(frozen=True)
class SprintSummary:
    """Single sprint summary for history display."""

    sprint_id: str
    started_at: str
    ended_at: str
    points_planned: int
    points_completed: int
    tasks_completed: int
    tasks_carried_over: int
    completion_rate: float


@dataclass(frozen=True)
class VelocityTrend:
    """Velocity trend analysis."""

    sprints: int
    average: float
    trend_direction: str  # "up", "down", "stable"
    confidence: float
    recent_velocities: list[int] = field(default_factory=list)


@dataclass(frozen=True)
class CompletionForecast:
    """Project completion estimate."""

    estimated_sprints: int
    estimated_date: date | None
    confidence_range: tuple[int, int]  # (min_sprints, max_sprints)
    average_velocity: float


class VelocityReporter:
    """Velocity reporting with trend analysis and completion forecasting."""

    def __init__(self, db: Database, project_id: str) -> None:
        self._db = db
        self._project_id = project_id

    def sprint_history(self, limit: int = 10) -> list[SprintSummary]:
        """Return up to *limit* most recent sprint summaries, oldest first."""
        from autopilot.core.sprint import VelocityTracker

        tracker = VelocityTracker(self._db, self._project_id)
        history = tracker.get_history()

        summaries: list[SprintSummary] = []
        for s in history[-limit:]:
            rate = s.points_completed / s.points_planned if s.points_planned > 0 else 0.0
            summaries.append(
                SprintSummary(
                    sprint_id=s.sprint_id,
                    started_at=s.started_at.isoformat() if s.started_at else "",
                    ended_at=s.ended_at.isoformat() if s.ended_at else "",
                    points_planned=s.points_planned,
                    points_completed=s.points_completed,
                    tasks_completed=s.tasks_completed,
                    tasks_carried_over=s.tasks_carried_over,
                    completion_rate=round(rate, 2),
                )
            )
        return summaries

    def velocity_trend(self) -> VelocityTrend:
        """Compute velocity trend with direction and confidence."""
        from autopilot.core.sprint import VelocityTracker

        tracker = VelocityTracker(self._db, self._project_id)
        history = tracker.get_history()

        if not history:
            return VelocityTrend(
                sprints=0,
                average=0.0,
                trend_direction="stable",
                confidence=0.0,
                recent_velocities=[],
            )

        recent = history[-_ROLLING_WINDOW:]
        velocities = [s.points_completed for s in recent]
        average = sum(velocities) / len(velocities)

        direction = self._compute_trend_direction(velocities)
        confidence = self._compute_confidence(velocities)

        return VelocityTrend(
            sprints=len(history),
            average=round(average, 1),
            trend_direction=direction,
            confidence=round(confidence, 2),
            recent_velocities=velocities,
        )

    def forecast_completion(self, remaining_points: int) -> CompletionForecast:
        """Forecast when remaining work will be completed."""
        from autopilot.core.sprint import VelocityTracker

        tracker = VelocityTracker(self._db, self._project_id)
        avg = tracker.get_average_velocity()

        if avg <= 0 or remaining_points <= 0:
            return CompletionForecast(
                estimated_sprints=0,
                estimated_date=None,
                confidence_range=(0, 0),
                average_velocity=avg,
            )

        estimated_sprints = math.ceil(remaining_points / avg)

        history = tracker.get_history()
        if len(history) >= _MIN_SPRINTS_FOR_FORECAST:
            recent = history[-_ROLLING_WINDOW:]
            velocities = [s.points_completed for s in recent]
            min_vel = min(velocities) if velocities else 1
            max_vel = max(velocities) if velocities else 1
            max_sprints = math.ceil(remaining_points / max(min_vel, 1))
            min_sprints = math.ceil(remaining_points / max(max_vel, 1))
        else:
            min_sprints = estimated_sprints
            max_sprints = estimated_sprints

        estimated_date = date.today() + timedelta(weeks=estimated_sprints * _SPRINT_DURATION_WEEKS)

        return CompletionForecast(
            estimated_sprints=estimated_sprints,
            estimated_date=estimated_date,
            confidence_range=(min_sprints, max_sprints),
            average_velocity=round(avg, 1),
        )

    def generate_report(self) -> str:
        """Produce a velocity report as formatted text."""
        trend = self.velocity_trend()
        history = self.sprint_history(limit=5)

        lines: list[str] = []
        lines.append("# Velocity Report")
        lines.append("")
        lines.append(
            f"Sprints tracked: {trend.sprints} | "
            f"Avg velocity: {trend.average} pts | "
            f"Trend: {trend.trend_direction} | "
            f"Confidence: {trend.confidence:.0%}"
        )
        lines.append("")

        if history:
            lines.append("## Recent Sprints")
            lines.append("")
            lines.append("| Sprint | Planned | Done | Rate |")
            lines.append("|--------|---------|------|------|")
            for s in reversed(history):
                lines.append(
                    f"| {s.sprint_id[:8]} | {s.points_planned} | "
                    f"{s.points_completed} | {s.completion_rate:.0%} |"
                )
            lines.append("")

        if trend.recent_velocities:
            lines.append("## Velocity Chart")
            lines.append("")
            max_vel = max(trend.recent_velocities) if trend.recent_velocities else 1
            for i, vel in enumerate(trend.recent_velocities):
                bar_len = int(vel / max(max_vel, 1) * 20)
                bar = "#" * bar_len
                lines.append(f"  S{i + 1}: {bar} {vel}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _compute_trend_direction(velocities: list[int]) -> str:
        """Determine trend direction from velocity series."""
        if len(velocities) < 2:
            return "stable"

        first_half = velocities[: len(velocities) // 2]
        second_half = velocities[len(velocities) // 2 :]

        avg_first = sum(first_half) / len(first_half) if first_half else 0
        avg_second = sum(second_half) / len(second_half) if second_half else 0

        diff = avg_second - avg_first
        threshold = max(avg_first * 0.1, 1)

        if diff > threshold:
            return "up"
        if diff < -threshold:
            return "down"
        return "stable"

    @staticmethod
    def _compute_confidence(velocities: list[int]) -> float:
        """Compute confidence based on velocity consistency (0.0 to 1.0)."""
        if len(velocities) < 2:
            return 0.0

        avg = sum(velocities) / len(velocities)
        if avg == 0:
            return 0.0

        variance = sum((v - avg) ** 2 for v in velocities) / len(velocities)
        std_dev = math.sqrt(variance)
        cv = std_dev / avg  # coefficient of variation

        # Lower CV = higher confidence
        confidence = max(0.0, 1.0 - cv)
        return min(1.0, confidence)
