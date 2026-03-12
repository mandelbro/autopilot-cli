"""Tests for QuestionQueue (Task 018)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from autopilot.coordination.questions import (
    QuestionPriority,
    QuestionQueue,
    QuestionStatus,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestQuestionQueue:
    def test_add_and_list_pending(self, tmp_path: Path) -> None:
        qq = QuestionQueue(tmp_path)
        q = qq.add_question("coder", "Should I use async?", "Performance concern")
        assert q.id.startswith("Q-")
        assert q.status == QuestionStatus.PENDING
        pending = qq.list_pending()
        assert len(pending) == 1
        assert pending[0].question == "Should I use async?"

    def test_priority_ordering(self, tmp_path: Path) -> None:
        qq = QuestionQueue(tmp_path)
        qq.add_question("a", "low q", priority="low")
        qq.add_question("b", "blocking q", priority="blocking")
        qq.add_question("c", "normal q", priority="normal")
        pending = qq.list_pending()
        assert pending[0].priority == QuestionPriority.BLOCKING
        assert pending[1].priority == QuestionPriority.NORMAL
        assert pending[2].priority == QuestionPriority.LOW

    def test_answer_question(self, tmp_path: Path) -> None:
        qq = QuestionQueue(tmp_path)
        q = qq.add_question("coder", "Use REST or GraphQL?")
        qq.answer(q.id, "Use REST", "architect")
        pending = qq.list_pending()
        assert len(pending) == 0

    def test_answer_missing_raises(self, tmp_path: Path) -> None:
        qq = QuestionQueue(tmp_path)
        with pytest.raises(KeyError, match="not found"):
            qq.answer("Q-nonexistent", "answer", "someone")

    def test_skip_question(self, tmp_path: Path) -> None:
        qq = QuestionQueue(tmp_path)
        q = qq.add_question("coder", "Skip me?")
        qq.skip(q.id, "Not relevant")
        pending = qq.list_pending()
        assert len(pending) == 0

    def test_skip_missing_raises(self, tmp_path: Path) -> None:
        qq = QuestionQueue(tmp_path)
        with pytest.raises(KeyError, match="not found"):
            qq.skip("Q-nonexistent", "reason")

    def test_has_blocking(self, tmp_path: Path) -> None:
        qq = QuestionQueue(tmp_path)
        assert qq.has_blocking() is False
        qq.add_question("coder", "Critical?", priority="blocking")
        assert qq.has_blocking() is True

    def test_persists_across_instances(self, tmp_path: Path) -> None:
        qq1 = QuestionQueue(tmp_path)
        qq1.add_question("coder", "Persist me")
        qq2 = QuestionQueue(tmp_path)
        assert len(qq2.list_pending()) == 1

    def test_file_created(self, tmp_path: Path) -> None:
        qq = QuestionQueue(tmp_path)
        qq.add_question("coder", "test")
        assert (tmp_path / "question-queue.md").exists()
