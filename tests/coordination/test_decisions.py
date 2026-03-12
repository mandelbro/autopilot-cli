"""Tests for DecisionLog (Task 020)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from autopilot.coordination.decisions import DecisionLog

if TYPE_CHECKING:
    from pathlib import Path


class TestDecisionLog:
    def test_record_and_list_recent(self, tmp_path: Path) -> None:
        log = DecisionLog(tmp_path)
        d = log.record("coder", "implement auth", rationale="Security requirement")
        assert d.id.startswith("D-")
        assert d.agent == "coder"
        recent = log.list_recent()
        assert len(recent) == 1
        assert recent[0].action == "implement auth"

    def test_list_recent_limit(self, tmp_path: Path) -> None:
        log = DecisionLog(tmp_path)
        for i in range(5):
            log.record("agent", f"action-{i}")
        recent = log.list_recent(limit=3)
        assert len(recent) == 3
        assert recent[-1].action == "action-4"

    def test_search_by_agent(self, tmp_path: Path) -> None:
        log = DecisionLog(tmp_path)
        log.record("coder", "write code")
        log.record("reviewer", "review PR")
        log.record("coder", "fix bug")
        results = log.search("coder")
        assert len(results) == 2

    def test_search_by_action(self, tmp_path: Path) -> None:
        log = DecisionLog(tmp_path)
        log.record("coder", "implement authentication")
        log.record("coder", "add tests")
        results = log.search("authentication")
        assert len(results) == 1

    def test_search_by_rationale(self, tmp_path: Path) -> None:
        log = DecisionLog(tmp_path)
        log.record("coder", "action", rationale="performance optimization")
        results = log.search("performance")
        assert len(results) == 1

    def test_search_no_results(self, tmp_path: Path) -> None:
        log = DecisionLog(tmp_path)
        log.record("coder", "action")
        assert log.search("nonexistent") == []

    def test_rotate_archives_old(self, tmp_path: Path) -> None:
        log = DecisionLog(tmp_path, max_entries=3)
        for i in range(5):
            log.record("agent", f"action-{i}")
        archived = log.rotate()
        assert archived == 2
        remaining = log.list_recent(limit=100)
        assert len(remaining) == 3

    def test_rotate_creates_archive_files(self, tmp_path: Path) -> None:
        log = DecisionLog(tmp_path, max_entries=2)
        for i in range(4):
            log.record("agent", f"action-{i}")
        log.rotate()
        archive_dir = tmp_path / "decision-log-archive"
        assert archive_dir.is_dir()
        archive_files = list(archive_dir.iterdir())
        assert len(archive_files) > 0

    def test_rotate_no_op_under_limit(self, tmp_path: Path) -> None:
        log = DecisionLog(tmp_path, max_entries=10)
        log.record("agent", "action")
        archived = log.rotate()
        assert archived == 0

    def test_persists_across_instances(self, tmp_path: Path) -> None:
        log1 = DecisionLog(tmp_path)
        log1.record("agent", "persistent action")
        log2 = DecisionLog(tmp_path)
        assert len(log2.list_recent()) == 1

    def test_file_created(self, tmp_path: Path) -> None:
        log = DecisionLog(tmp_path)
        log.record("agent", "action")
        assert (tmp_path / "decision-log.md").exists()

    def test_context_parameter(self, tmp_path: Path) -> None:
        log = DecisionLog(tmp_path)
        d = log.record("agent", "action", context={"key": "value"})
        assert d.context == {"key": "value"}
