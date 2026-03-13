"""Tests for decision log reporting (Task 043)."""

from __future__ import annotations

import pytest

from autopilot.coordination.decisions import DecisionLog
from autopilot.reporting.decision_log import DecisionLogReporter


@pytest.fixture()
def board_dir(tmp_path):
    d = tmp_path / "board"
    d.mkdir()
    return d


@pytest.fixture()
def reporter(board_dir):
    return DecisionLogReporter(board_dir)


def _seed_decisions(board_dir, count: int = 5, agent: str = "coder") -> None:
    """Seed the decision log with test decisions."""
    log = DecisionLog(board_dir)
    for i in range(count):
        log.record(
            agent=agent if i % 2 == 0 else "reviewer",
            action=f"action-{i}",
            rationale=f"rationale for action {i}",
        )


class TestRecentDecisions:
    def test_empty(self, reporter: DecisionLogReporter) -> None:
        assert reporter.recent_decisions() == []

    def test_returns_recent(self, board_dir, reporter: DecisionLogReporter) -> None:
        _seed_decisions(board_dir, count=5)
        recent = reporter.recent_decisions(limit=3)

        assert len(recent) == 3
        assert recent[-1].action == "action-4"


class TestDecisionsByAgent:
    def test_filter_by_agent(self, board_dir, reporter: DecisionLogReporter) -> None:
        _seed_decisions(board_dir, count=6)
        coder_decisions = reporter.decisions_by_agent("coder")

        assert all(d.agent == "coder" for d in coder_decisions)
        assert len(coder_decisions) == 3  # indices 0, 2, 4

    def test_nonexistent_agent(self, board_dir, reporter: DecisionLogReporter) -> None:
        _seed_decisions(board_dir, count=3)
        assert reporter.decisions_by_agent("nonexistent") == []


class TestSearchDecisions:
    def test_search_by_action(self, board_dir, reporter: DecisionLogReporter) -> None:
        _seed_decisions(board_dir, count=5)
        results = reporter.search_decisions("action-2")

        assert len(results) == 1
        assert results[0].action == "action-2"

    def test_search_by_rationale(self, board_dir, reporter: DecisionLogReporter) -> None:
        _seed_decisions(board_dir, count=5)
        results = reporter.search_decisions("rationale")

        assert len(results) == 5

    def test_search_across_archives(self, board_dir, reporter: DecisionLogReporter) -> None:
        """Search should include archived decisions."""
        log = DecisionLog(board_dir, max_entries=3)
        for i in range(6):
            log.record(agent="coder", action=f"action-{i}", rationale=f"reason-{i}")
        log.rotate()

        results = reporter.search_decisions("action-")
        assert len(results) == 6

    def test_search_no_match(self, board_dir, reporter: DecisionLogReporter) -> None:
        _seed_decisions(board_dir, count=3)
        assert reporter.search_decisions("nonexistent_xyz") == []


class TestDecisionTrend:
    def test_empty_trend(self, reporter: DecisionLogReporter) -> None:
        trend = reporter.decision_trend()

        assert trend.total_decisions == 0
        assert trend.most_active_agent == ""

    def test_trend_with_data(self, board_dir, reporter: DecisionLogReporter) -> None:
        _seed_decisions(board_dir, count=6)
        trend = reporter.decision_trend()

        assert trend.total_decisions == 6
        assert "coder" in trend.decisions_by_agent
        assert "reviewer" in trend.decisions_by_agent
        assert trend.most_active_agent in ("coder", "reviewer")
        assert len(trend.decisions_by_month) > 0


class TestGenerateReport:
    def test_empty_report(self, reporter: DecisionLogReporter) -> None:
        report = reporter.generate_report()

        assert "Decision Log Report" in report
        assert "Total decisions: 0" in report

    def test_report_with_data(self, board_dir, reporter: DecisionLogReporter) -> None:
        _seed_decisions(board_dir, count=5)
        report = reporter.generate_report()

        assert "Decision Log Report" in report
        assert "Decisions by Agent" in report
        assert "Recent Decisions" in report
        assert "coder" in report


class TestAllDecisions:
    def test_includes_archives(self, board_dir, reporter: DecisionLogReporter) -> None:
        """_all_decisions should include both current and archived entries."""
        log = DecisionLog(board_dir, max_entries=2)
        for i in range(5):
            log.record(agent="coder", action=f"action-{i}", rationale="test")
        log.rotate()

        all_decisions = reporter._all_decisions()
        assert len(all_decisions) == 5
