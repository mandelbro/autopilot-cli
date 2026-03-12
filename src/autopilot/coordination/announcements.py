"""Announcements channel for human-to-agent communication (Task 019).

Manages broadcasts via announcements.md with active/archived sections.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from autopilot.coordination.utils import file_lock, write_atomic

if TYPE_CHECKING:
    from pathlib import Path

_log = logging.getLogger(__name__)

_ANNOUNCEMENTS_FILENAME = "announcements.md"


@dataclass
class Announcement:
    """A human-to-agent broadcast announcement."""

    id: str
    title: str
    content: str
    author: str
    posted_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    archived: bool = False


class AnnouncementManager:
    """Manages announcements.md for human-to-agent broadcasts."""

    def __init__(self, board_dir: Path) -> None:
        self._board_dir = board_dir
        self._file = board_dir / _ANNOUNCEMENTS_FILENAME

    def post(self, title: str, content: str, author: str) -> Announcement:
        """Add a new announcement."""
        a = Announcement(
            id=f"ANN-{uuid.uuid4().hex[:8]}",
            title=title,
            content=content,
            author=author,
        )
        announcements = self._load()
        announcements.append(a)
        self._save(announcements)
        return a

    def list_active(self) -> list[Announcement]:
        """Return current (non-archived) announcements, newest first."""
        active = [a for a in self._load() if not a.archived]
        return sorted(active, key=lambda a: a.posted_at, reverse=True)

    def archive(self, announcement_id: str) -> None:
        """Move an announcement to archived."""
        announcements = self._load()
        for a in announcements:
            if a.id == announcement_id:
                a.archived = True
                self._save(announcements)
                return
        msg = f"Announcement '{announcement_id}' not found"
        raise KeyError(msg)

    def clear_all(self) -> None:
        """Archive all current announcements."""
        announcements = self._load()
        changed = False
        for a in announcements:
            if not a.archived:
                a.archived = True
                changed = True
        if changed:
            self._save(announcements)

    def _load(self) -> list[Announcement]:
        """Parse announcements.md."""
        if not self._file.exists():
            return []

        announcements: list[Announcement] = []
        content = self._file.read_text()
        current: dict[str, str] = {}

        for line in content.splitlines():
            if line.startswith("### ANN-"):
                if current.get("id"):
                    announcements.append(self._dict_to_announcement(current))
                current = {"id": line[4:].strip()}
            elif line.startswith("- **"):
                key, _, value = line[4:].partition(":**")
                key = key.strip().lower()
                value = value.strip()
                current[key] = value

        if current.get("id"):
            announcements.append(self._dict_to_announcement(current))
        return announcements

    def _save(self, announcements: list[Announcement]) -> None:
        """Write announcements to file."""
        active = [a for a in announcements if not a.archived]
        archived = [a for a in announcements if a.archived]

        lines = ["# Announcements", ""]
        lines.append("## Active")
        lines.append("")
        for a in active:
            self._append_entry(lines, a)

        lines.append("## Archived")
        lines.append("")
        for a in archived:
            self._append_entry(lines, a)

        self._board_dir.mkdir(parents=True, exist_ok=True)
        with file_lock(self._file):
            write_atomic(self._file, "\n".join(lines))

    @staticmethod
    def _append_entry(lines: list[str], a: Announcement) -> None:
        lines.append(f"### {a.id}")
        lines.append("")
        lines.append(f"- **Title:** {a.title}")
        lines.append(f"- **Content:** {a.content}")
        lines.append(f"- **Author:** {a.author}")
        lines.append(f"- **Posted_at:** {a.posted_at}")
        lines.append(f"- **Archived:** {a.archived}")
        lines.append("")

    @staticmethod
    def _dict_to_announcement(d: dict[str, str]) -> Announcement:
        return Announcement(
            id=d.get("id", ""),
            title=d.get("title", ""),
            content=d.get("content", ""),
            author=d.get("author", ""),
            posted_at=d.get("posted_at", ""),
            archived=d.get("archived", "").lower() == "true",
        )
