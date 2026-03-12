"""Question queue for agent-to-human communication (Task 018).

Manages agent questions with priority, status tracking, and
persistence in question-queue.md.
"""

from __future__ import annotations

import fcntl
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_log = logging.getLogger(__name__)

_QUEUE_FILENAME = "question-queue.md"


class QuestionPriority(StrEnum):
    BLOCKING = "blocking"
    NORMAL = "normal"
    LOW = "low"


class QuestionStatus(StrEnum):
    PENDING = "pending"
    ANSWERED = "answered"
    SKIPPED = "skipped"


@dataclass
class Question:
    """A question posted by an agent."""

    id: str
    agent: str
    question: str
    context: str = ""
    priority: QuestionPriority = QuestionPriority.NORMAL
    status: QuestionStatus = QuestionStatus.PENDING
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    answer: str = ""
    answered_by: str = ""
    skip_reason: str = ""


class QuestionQueue:
    """Manages the question-queue.md file for agent-to-human decisions."""

    def __init__(self, board_dir: Path) -> None:
        self._board_dir = board_dir
        self._queue_file = board_dir / _QUEUE_FILENAME

    def add_question(
        self,
        agent: str,
        question: str,
        context: str = "",
        priority: str = "normal",
    ) -> Question:
        """Append a question to the queue. Returns the created question."""
        q = Question(
            id=f"Q-{uuid.uuid4().hex[:8]}",
            agent=agent,
            question=question,
            context=context,
            priority=QuestionPriority(priority),
        )
        questions = self._load()
        questions.append(q)
        self._save(questions)
        return q

    def list_pending(self) -> list[Question]:
        """Return all pending questions, ordered by priority."""
        priority_order = {
            QuestionPriority.BLOCKING: 0,
            QuestionPriority.NORMAL: 1,
            QuestionPriority.LOW: 2,
        }
        pending = [q for q in self._load() if q.status == QuestionStatus.PENDING]
        return sorted(pending, key=lambda q: priority_order.get(q.priority, 1))

    def answer(self, question_id: str, answer: str, answered_by: str) -> None:
        """Mark a question as answered."""
        questions = self._load()
        for q in questions:
            if q.id == question_id:
                q.status = QuestionStatus.ANSWERED
                q.answer = answer
                q.answered_by = answered_by
                self._save(questions)
                return
        msg = f"Question '{question_id}' not found"
        raise KeyError(msg)

    def skip(self, question_id: str, reason: str) -> None:
        """Skip a question with a reason."""
        questions = self._load()
        for q in questions:
            if q.id == question_id:
                q.status = QuestionStatus.SKIPPED
                q.skip_reason = reason
                self._save(questions)
                return
        msg = f"Question '{question_id}' not found"
        raise KeyError(msg)

    def has_blocking(self) -> bool:
        """Check if there are any blocking pending questions."""
        return any(q.priority == QuestionPriority.BLOCKING for q in self.list_pending())

    def _load(self) -> list[Question]:
        """Parse question-queue.md into structured questions."""
        if not self._queue_file.exists():
            return []

        questions: list[Question] = []
        content = self._queue_file.read_text()
        current: dict[str, str] = {}

        for line in content.splitlines():
            if line.startswith("### Q-"):
                if current.get("id"):
                    questions.append(self._dict_to_question(current))
                current = {"id": line[4:].strip()}
            elif line.startswith("- **"):
                key, _, value = line[4:].partition(":**")
                key = key.strip().lower()
                value = value.strip()
                current[key] = value

        if current.get("id"):
            questions.append(self._dict_to_question(current))
        return questions

    def _save(self, questions: list[Question]) -> None:
        """Write all questions to question-queue.md."""
        lines = ["# Question Queue", ""]
        for q in questions:
            lines.append(f"### {q.id}")
            lines.append("")
            lines.append(f"- **Agent:** {q.agent}")
            lines.append(f"- **Question:** {q.question}")
            if q.context:
                lines.append(f"- **Context:** {q.context}")
            lines.append(f"- **Priority:** {q.priority.value}")
            lines.append(f"- **Status:** {q.status.value}")
            lines.append(f"- **Timestamp:** {q.timestamp}")
            if q.answer:
                lines.append(f"- **Answer:** {q.answer}")
            if q.answered_by:
                lines.append(f"- **Answered_by:** {q.answered_by}")
            if q.skip_reason:
                lines.append(f"- **Skip_reason:** {q.skip_reason}")
            lines.append("")

        self._board_dir.mkdir(parents=True, exist_ok=True)
        self._write_locked(self._queue_file, "\n".join(lines))

    @staticmethod
    def _dict_to_question(d: dict[str, str]) -> Question:
        return Question(
            id=d.get("id", ""),
            agent=d.get("agent", ""),
            question=d.get("question", ""),
            context=d.get("context", ""),
            priority=QuestionPriority(d.get("priority", "normal")),
            status=QuestionStatus(d.get("status", "pending")),
            timestamp=d.get("timestamp", ""),
            answer=d.get("answer", ""),
            answered_by=d.get("answered_by", ""),
            skip_reason=d.get("skip_reason", ""),
        )

    @staticmethod
    def _write_locked(path: Path, content: str) -> None:
        tmp = path.with_suffix(".md.tmp")
        with open(tmp, "w") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                f.write(content)
                f.flush()
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
        tmp.replace(path)
