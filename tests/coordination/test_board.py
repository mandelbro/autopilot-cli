"""Tests for BoardManager (Task 017)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from autopilot.coordination.board import BoardManager, BoardState

if TYPE_CHECKING:
    from pathlib import Path


class TestBoardManager:
    def test_read_empty(self, tmp_path: Path) -> None:
        mgr = BoardManager(tmp_path)
        state = mgr.read_board()
        assert isinstance(state, BoardState)
        assert state.sprint_info == ""

    def test_write_and_read_round_trip(self, tmp_path: Path) -> None:
        mgr = BoardManager(tmp_path)
        mgr.update_section("Sprint Info", "Sprint 1: Jan-Feb")
        state = mgr.read_board()
        assert state.sprint_info == "Sprint 1: Jan-Feb"

    def test_update_preserves_other_sections(self, tmp_path: Path) -> None:
        mgr = BoardManager(tmp_path)
        mgr.update_section("Sprint Info", "sprint data")
        mgr.update_section("Blockers", "blocked on X")
        state = mgr.read_board()
        assert state.sprint_info == "sprint data"
        assert state.blockers == "blocked on X"

    def test_invalid_section_raises(self, tmp_path: Path) -> None:
        mgr = BoardManager(tmp_path)
        with pytest.raises(ValueError, match="Unknown section"):
            mgr.update_section("Bad Section", "content")

    def test_add_active_work(self, tmp_path: Path) -> None:
        mgr = BoardManager(tmp_path)
        mgr.add_active_work("T-001", "coder", "Implement feature X")
        mgr.add_active_work("T-002", "reviewer", "Review PR #5")
        state = mgr.read_board()
        assert "T-001" in state.active_work
        assert "T-002" in state.active_work
        assert "coder" in state.active_work

    def test_mark_blocker(self, tmp_path: Path) -> None:
        mgr = BoardManager(tmp_path)
        mgr.mark_blocker("API rate limit hit", "engineering-manager")
        state = mgr.read_board()
        assert "API rate limit" in state.blockers
        assert "engineering-manager" in state.blockers

    def test_update_sprint_progress(self, tmp_path: Path) -> None:
        mgr = BoardManager(tmp_path)
        mgr.update_sprint_progress(21, 13)
        state = mgr.read_board()
        assert "21" in state.sprint_info
        assert "13" in state.sprint_info

    def test_persists_to_file(self, tmp_path: Path) -> None:
        mgr = BoardManager(tmp_path)
        mgr.update_section("Active Work", "doing things")
        assert (tmp_path / "project-board.md").exists()

        # Read from new instance
        mgr2 = BoardManager(tmp_path)
        state = mgr2.read_board()
        assert state.active_work == "doing things"

    def test_all_sections_present(self, tmp_path: Path) -> None:
        mgr = BoardManager(tmp_path)
        mgr.update_section("Sprint Info", "s")
        mgr.update_section("Active Work", "a")
        mgr.update_section("Blockers", "b")
        mgr.update_section("Recent Decisions", "r")
        mgr.update_section("Deployment Status", "d")
        state = mgr.read_board()
        assert state.sprint_info == "s"
        assert state.active_work == "a"
        assert state.blockers == "b"
        assert state.recent_decisions == "r"
        assert state.deployment_status == "d"
