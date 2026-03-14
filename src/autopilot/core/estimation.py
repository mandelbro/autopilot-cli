"""Estimation agent integration for task pointing (Task 080).

Analyzes task complexity and suggests Fibonacci sprint points using
structured heuristics (with optional LLM-based estimation).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from autopilot.core.task import Task

logger = structlog.get_logger(__name__)

# Fibonacci scale for sprint points
FIBONACCI_SCALE = (1, 2, 3, 5, 8)

# Complexity indicators and their point contributions
_COMPLEXITY_KEYWORDS: dict[str, list[str]] = {
    "high": [
        "architecture",
        "migration",
        "refactor",
        "integration",
        "security",
        "concurrent",
        "parallel",
        "distributed",
        "database schema",
    ],
    "medium": [
        "api",
        "endpoint",
        "cli command",
        "configuration",
        "template",
        "generator",
        "parser",
        "validation",
    ],
    "low": [
        "documentation",
        "readme",
        "comment",
        "rename",
        "format",
        "type annotation",
        "stub",
        "placeholder",
    ],
}


@dataclass(frozen=True)
class EstimationResult:
    """Result from estimating a single task's complexity."""

    task_id: str
    recommended_points: int
    rationale: str
    complexity_factors: list[str] = field(default_factory=list)
    confidence: float = 0.0

    def __hash__(self) -> int:  # pragma: no cover
        return hash(self.task_id)


def _nearest_fibonacci(value: float) -> int:
    """Round a float to the nearest Fibonacci number in the scale."""
    best = FIBONACCI_SCALE[0]
    best_dist = abs(value - best)
    for fib in FIBONACCI_SCALE[1:]:
        dist = abs(value - fib)
        if dist < best_dist:
            best = fib
            best_dist = dist
    return best


def _count_acceptance_criteria(task: Task) -> int:
    """Count acceptance criteria from the task's prompt text."""
    count = len(task.acceptance_criteria)
    if not count and task.prompt:
        # Count checkbox items in prompt
        count = len(re.findall(r"^\s*-\s+\[.\]", task.prompt, re.MULTILINE))
    return count


class EstimationAgent:
    """Estimates task complexity and suggests Fibonacci sprint points.

    Uses heuristic analysis of task content (title, prompt, acceptance
    criteria, dependencies) to compute a complexity score, then maps
    it to the nearest Fibonacci number.
    """

    def estimate_task(
        self,
        task: Task,
        project_context: str = "",
    ) -> EstimationResult:
        """Estimate a single task's sprint points.

        Parameters
        ----------
        task:
            The task to estimate.
        project_context:
            Optional project description for additional context.

        Returns
        -------
        EstimationResult
            Contains recommended_points, rationale, and complexity factors.
        """
        factors: list[str] = []
        score = 0.0

        # Factor 1: Title and prompt complexity keywords
        text = f"{task.title} {task.prompt} {task.user_story}".lower()

        high_matches = [kw for kw in _COMPLEXITY_KEYWORDS["high"] if kw in text]
        medium_matches = [kw for kw in _COMPLEXITY_KEYWORDS["medium"] if kw in text]
        low_matches = [kw for kw in _COMPLEXITY_KEYWORDS["low"] if kw in text]

        if high_matches:
            score += 2.0
            factors.append(f"High complexity keywords: {', '.join(high_matches[:3])}")
        if medium_matches:
            score += 1.0
            factors.append(f"Medium complexity keywords: {', '.join(medium_matches[:3])}")
        if low_matches:
            score -= 0.5
            factors.append(f"Low complexity indicators: {', '.join(low_matches[:3])}")

        # Factor 2: Acceptance criteria count
        ac_count = _count_acceptance_criteria(task)
        if ac_count > 5:
            score += 1.5
            factors.append(f"Many acceptance criteria ({ac_count})")
        elif ac_count > 3:
            score += 0.5
            factors.append(f"Moderate acceptance criteria ({ac_count})")
        elif ac_count > 0:
            factors.append(f"Few acceptance criteria ({ac_count})")

        # Factor 3: Prompt length (more detailed = potentially more complex)
        prompt_len = len(task.prompt)
        if prompt_len > 1000:
            score += 1.0
            factors.append(f"Detailed prompt ({prompt_len} chars)")
        elif prompt_len > 500:
            score += 0.5
            factors.append(f"Moderate prompt ({prompt_len} chars)")

        # Factor 4: Spec references (more refs = more integration work)
        ref_count = len(task.spec_references)
        if ref_count > 2:
            score += 0.5
            factors.append(f"Multiple spec references ({ref_count})")

        # Factor 5: File path complexity
        if task.file_path:
            depth = task.file_path.count("/")
            if depth > 3:
                score += 0.5
                factors.append(f"Deep file path ({depth} levels)")

        # Map to Fibonacci
        base_points = max(1.0, score + 2.0)  # Base of 2 (small task)
        recommended = _nearest_fibonacci(base_points)

        # Build rationale
        if not factors:
            factors.append("No significant complexity indicators found")

        confidence = min(0.95, 0.5 + (len(factors) * 0.1))
        rationale = (
            f"Estimated at {recommended} points based on: "
            + "; ".join(factors[:5])
        )

        logger.info(
            "task_estimated",
            task_id=task.id,
            points=recommended,
            confidence=confidence,
        )

        return EstimationResult(
            task_id=task.id,
            recommended_points=recommended,
            rationale=rationale,
            complexity_factors=factors,
            confidence=round(confidence, 2),
        )

    def batch_estimate(
        self,
        tasks: list[Task],
        project_context: str = "",
    ) -> list[EstimationResult]:
        """Estimate sprint points for multiple tasks.

        Returns a list of EstimationResult in the same order as input tasks.
        """
        logger.info("batch_estimate_start", count=len(tasks))
        results = [
            self.estimate_task(task, project_context) for task in tasks
        ]
        logger.info(
            "batch_estimate_complete",
            count=len(results),
            total_points=sum(r.recommended_points for r in results),
        )
        return results
