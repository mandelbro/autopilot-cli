"""Tests for estimation agent (Task 080)."""

from __future__ import annotations

import pytest

from autopilot.core.estimation import (
    FIBONACCI_SCALE,
    EstimationAgent,
    EstimationResult,
    _nearest_fibonacci,
)
from autopilot.core.task import Task


class TestNearestFibonacci:
    def test_exact_values(self) -> None:
        for fib in FIBONACCI_SCALE:
            assert _nearest_fibonacci(float(fib)) == fib

    def test_rounds_up(self) -> None:
        assert _nearest_fibonacci(1.6) == 2

    def test_rounds_down(self) -> None:
        assert _nearest_fibonacci(2.2) == 2

    def test_midpoint(self) -> None:
        result = _nearest_fibonacci(4.0)
        assert result in (3, 5)


class TestEstimationResult:
    def test_frozen(self) -> None:
        r = EstimationResult(task_id="001", recommended_points=3, rationale="test")
        with pytest.raises(AttributeError):
            r.task_id = "002"  # type: ignore[misc]

    def test_defaults(self) -> None:
        r = EstimationResult(task_id="001", recommended_points=3, rationale="test")
        assert r.complexity_factors == []
        assert r.confidence == 0.0


class TestEstimationAgent:
    @pytest.fixture()
    def agent(self) -> EstimationAgent:
        return EstimationAgent()

    def test_simple_task_low_points(self, agent: EstimationAgent) -> None:
        task = Task(
            id="001",
            title="Update documentation readme",
            prompt="**Objective:** Update the README file",
        )
        result = agent.estimate_task(task)
        assert result.recommended_points in FIBONACCI_SCALE
        assert result.recommended_points <= 3

    def test_complex_task_high_points(self, agent: EstimationAgent) -> None:
        task = Task(
            id="002",
            title="Database migration and architecture refactor",
            prompt=(
                "**Objective:** Refactor the database schema and migrate "
                "all tables to new architecture with concurrent processing.\n\n"
                "**Acceptance Criteria:**\n"
                "- [ ] Schema migrated\n"
                "- [ ] Data integrity verified\n"
                "- [ ] Concurrent reads work\n"
                "- [ ] Rollback tested\n"
                "- [ ] Performance benchmarks pass\n"
                "- [ ] Integration tests updated\n"
            ),
            acceptance_criteria=[
                "Schema migrated",
                "Data integrity verified",
                "Concurrent reads work",
                "Rollback tested",
                "Performance benchmarks pass",
                "Integration tests updated",
            ],
        )
        result = agent.estimate_task(task)
        assert result.recommended_points >= 5

    def test_result_has_rationale(self, agent: EstimationAgent) -> None:
        task = Task(id="003", title="Add API endpoint", prompt="Build REST endpoint")
        result = agent.estimate_task(task)
        assert len(result.rationale) > 0
        assert "points" in result.rationale.lower()

    def test_result_has_complexity_factors(self, agent: EstimationAgent) -> None:
        task = Task(id="004", title="Security audit", prompt="Audit all security endpoints")
        result = agent.estimate_task(task)
        assert len(result.complexity_factors) > 0

    def test_confidence_is_bounded(self, agent: EstimationAgent) -> None:
        task = Task(id="005", title="Simple fix", prompt="Fix typo")
        result = agent.estimate_task(task)
        assert 0.0 <= result.confidence <= 1.0

    def test_result_in_fibonacci_scale(self, agent: EstimationAgent) -> None:
        task = Task(
            id="006",
            title="Complex integration with security",
            prompt="Build distributed concurrent system with database schema migration",
        )
        result = agent.estimate_task(task)
        assert result.recommended_points in FIBONACCI_SCALE

    def test_batch_estimate(self, agent: EstimationAgent) -> None:
        tasks = [
            Task(id="001", title="Doc update", prompt="Update docs"),
            Task(id="002", title="API endpoint", prompt="Build endpoint"),
            Task(id="003", title="Architecture refactor", prompt="Refactor arch"),
        ]
        results = agent.batch_estimate(tasks)
        assert len(results) == 3
        assert all(r.recommended_points in FIBONACCI_SCALE for r in results)
        assert all(r.task_id == tasks[i].id for i, r in enumerate(results))

    def test_batch_estimate_empty(self, agent: EstimationAgent) -> None:
        results = agent.batch_estimate([])
        assert results == []

    def test_spec_references_affect_complexity(self, agent: EstimationAgent) -> None:
        task_no_refs = Task(id="001", title="Build parser", prompt="Parse data")
        task_many_refs = Task(
            id="002",
            title="Build parser",
            prompt="Parse data",
            spec_references=["RFC 3.4", "Discovery Section 5", "UX Design 2.1"],
        )
        result_no = agent.estimate_task(task_no_refs)
        result_many = agent.estimate_task(task_many_refs)
        assert result_many.recommended_points >= result_no.recommended_points

    def test_file_path_depth_affects_complexity(self, agent: EstimationAgent) -> None:
        task_shallow = Task(
            id="001", title="Build module", prompt="Build it", file_path="src/mod.py"
        )
        task_deep = Task(
            id="002",
            title="Build module",
            prompt="Build it",
            file_path="src/deep/nested/path/mod.py",
        )
        result_shallow = agent.estimate_task(task_shallow)
        result_deep = agent.estimate_task(task_deep)
        assert result_deep.recommended_points >= result_shallow.recommended_points
