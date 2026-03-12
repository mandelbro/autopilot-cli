"""Decision log with archival and rotation (Task 020).

Append-only decision log in decision-log.md with rotation to
dated archive files when the log exceeds max_entries.
"""

from __future__ import annotations

import fcntl
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

_log = logging.getLogger(__name__)

_LOG_FILENAME = "decision-log.md"
_ARCHIVE_DIR = "decision-log-archive"
_DEFAULT_MAX_ENTRIES = 100


@dataclass
class Decision:
    """A single PL decision record."""

    id: str
    timestamp: str
    agent: str
    action: str
    rationale: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    outcome: str = ""


class DecisionLog:
    """Manages decision-log.md with append, rotation, and search."""

    def __init__(self, board_dir: Path, *, max_entries: int = _DEFAULT_MAX_ENTRIES) -> None:
        self._board_dir = board_dir
        self._log_file = board_dir / _LOG_FILENAME
        self._archive_dir = board_dir / _ARCHIVE_DIR
        self._max_entries = max_entries

    def record(
        self,
        agent: str,
        action: str,
        rationale: str = "",
        context: dict[str, Any] | None = None,
    ) -> Decision:
        """Append a decision to the log."""
        decision = Decision(
            id=f"D-{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now(UTC).isoformat(),
            agent=agent,
            action=action,
            rationale=rationale,
            context=context or {},
        )
        decisions = self._load()
        decisions.append(decision)
        self._save(decisions)
        return decision

    def list_recent(self, limit: int = 10) -> list[Decision]:
        """Return the most recent decisions."""
        decisions = self._load()
        return decisions[-limit:]

    def rotate(self, max_entries: int | None = None) -> int:
        """Archive old entries. Returns count of archived entries."""
        limit = max_entries or self._max_entries
        decisions = self._load()
        if len(decisions) <= limit:
            return 0

        to_archive = decisions[:-limit]
        to_keep = decisions[-limit:]

        # Group by year-month for archive files
        by_month: dict[str, list[Decision]] = {}
        for d in to_archive:
            month = d.timestamp[:7] if len(d.timestamp) >= 7 else "unknown"
            by_month.setdefault(month, []).append(d)

        self._archive_dir.mkdir(parents=True, exist_ok=True)
        for month, entries in by_month.items():
            archive_file = self._archive_dir / f"decision-log-{month}.md"
            existing = self._load_from(archive_file) if archive_file.exists() else []
            existing.extend(entries)
            self._save_to(archive_file, existing)

        self._save(to_keep)
        return len(to_archive)

    def search(self, query: str) -> list[Decision]:
        """Search decisions by keyword in agent, action, or rationale."""
        query_lower = query.lower()
        results: list[Decision] = []
        for d in self._load():
            if (
                query_lower in d.agent.lower()
                or query_lower in d.action.lower()
                or query_lower in d.rationale.lower()
            ):
                results.append(d)
        return results

    def _load(self) -> list[Decision]:
        return self._load_from(self._log_file)

    def _save(self, decisions: list[Decision]) -> None:
        self._board_dir.mkdir(parents=True, exist_ok=True)
        self._save_to(self._log_file, decisions)

    def _load_from(self, path: Path) -> list[Decision]:
        """Parse a decision log file."""
        if not path.exists():
            return []

        decisions: list[Decision] = []
        content = path.read_text()
        current: dict[str, str] = {}

        for line in content.splitlines():
            if line.startswith("### D-"):
                if current.get("id"):
                    decisions.append(self._dict_to_decision(current))
                current = {"id": line[4:].strip()}
            elif line.startswith("- **"):
                key, _, value = line[4:].partition(":**")
                key = key.strip().lower()
                value = value.strip()
                current[key] = value

        if current.get("id"):
            decisions.append(self._dict_to_decision(current))
        return decisions

    def _save_to(self, path: Path, decisions: list[Decision]) -> None:
        """Write decisions to a file."""
        lines = ["# Decision Log", ""]
        for d in decisions:
            lines.append(f"### {d.id}")
            lines.append("")
            lines.append(f"- **Timestamp:** {d.timestamp}")
            lines.append(f"- **Agent:** {d.agent}")
            lines.append(f"- **Action:** {d.action}")
            if d.rationale:
                lines.append(f"- **Rationale:** {d.rationale}")
            if d.outcome:
                lines.append(f"- **Outcome:** {d.outcome}")
            lines.append("")

        self._write_locked(path, "\n".join(lines))

    @staticmethod
    def _dict_to_decision(d: dict[str, str]) -> Decision:
        return Decision(
            id=d.get("id", ""),
            timestamp=d.get("timestamp", ""),
            agent=d.get("agent", ""),
            action=d.get("action", ""),
            rationale=d.get("rationale", ""),
            outcome=d.get("outcome", ""),
        )

    @staticmethod
    def _write_locked(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".md.tmp")
        with open(tmp, "w") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                f.write(content)
                f.flush()
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
        tmp.replace(path)
