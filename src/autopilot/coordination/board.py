"""Board management for document-mediated coordination (Task 017).

Reads and writes project-board.md sections, tracks active work,
blockers, and sprint progress with thread-safe file access.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from autopilot.coordination.utils import file_lock, write_atomic

if TYPE_CHECKING:
    from pathlib import Path

_log = logging.getLogger(__name__)

_BOARD_FILENAME = "project-board.md"

# Section headers used for parsing and writing
_SECTIONS = (
    "Sprint Info",
    "Active Work",
    "Blockers",
    "Recent Decisions",
    "Deployment Status",
)


@dataclass
class BoardState:
    """Parsed project board state."""

    sprint_info: str = ""
    active_work: str = ""
    blockers: str = ""
    recent_decisions: str = ""
    deployment_status: str = ""


class BoardManager:
    """Reads and writes project-board.md for agent coordination.

    The board file uses markdown with well-defined ``## Section`` headers.
    """

    def __init__(self, board_dir: Path) -> None:
        self._board_dir = board_dir
        self._board_file = board_dir / _BOARD_FILENAME

    def read_board(self) -> BoardState:
        """Parse project-board.md into structured data."""
        if not self._board_file.exists():
            return BoardState()

        content = self._board_file.read_text()
        sections = self._parse_sections(content)
        return BoardState(
            sprint_info=sections.get("Sprint Info", ""),
            active_work=sections.get("Active Work", ""),
            blockers=sections.get("Blockers", ""),
            recent_decisions=sections.get("Recent Decisions", ""),
            deployment_status=sections.get("Deployment Status", ""),
        )

    def update_section(self, section: str, content: str) -> None:
        """Update a specific board section, preserving other sections."""
        if section not in _SECTIONS:
            msg = f"Unknown section '{section}'. Valid: {', '.join(_SECTIONS)}"
            raise ValueError(msg)

        state = self.read_board()
        field_map = {
            "Sprint Info": "sprint_info",
            "Active Work": "active_work",
            "Blockers": "blockers",
            "Recent Decisions": "recent_decisions",
            "Deployment Status": "deployment_status",
        }
        setattr(state, field_map[section], content)
        self._write_board(state)

    def add_active_work(self, task_id: str, agent: str, description: str) -> None:
        """Add an entry to the Active Work section."""
        state = self.read_board()
        entry = f"- **{task_id}** ({agent}): {description}"
        if state.active_work:
            state.active_work = f"{state.active_work}\n{entry}"
        else:
            state.active_work = entry
        self._write_board(state)

    def mark_blocker(self, description: str, assigned_to: str) -> None:
        """Add a blocker to the Blockers section."""
        state = self.read_board()
        entry = f"- [{assigned_to}] {description}"
        if state.blockers:
            state.blockers = f"{state.blockers}\n{entry}"
        else:
            state.blockers = entry
        self._write_board(state)

    def update_sprint_progress(self, planned: int, completed: int) -> None:
        """Update sprint progress in the Sprint Info section."""
        state = self.read_board()
        state.sprint_info = f"Planned: {planned} | Completed: {completed}"
        self._write_board(state)

    def _write_board(self, state: BoardState) -> None:
        """Write the full board state to file with locking."""
        lines = ["# Project Board", ""]
        for section in _SECTIONS:
            field_map = {
                "Sprint Info": "sprint_info",
                "Active Work": "active_work",
                "Blockers": "blockers",
                "Recent Decisions": "recent_decisions",
                "Deployment Status": "deployment_status",
            }
            content = getattr(state, field_map[section])
            lines.append(f"## {section}")
            lines.append("")
            if content:
                lines.append(content)
            lines.append("")

        self._board_dir.mkdir(parents=True, exist_ok=True)
        with file_lock(self._board_file):
            write_atomic(self._board_file, "\n".join(lines))

    @staticmethod
    def _parse_sections(content: str) -> dict[str, str]:
        """Parse markdown content into section name -> content mapping."""
        sections: dict[str, str] = {}
        current_section: str | None = None
        current_lines: list[str] = []

        for line in content.splitlines():
            if line.startswith("## "):
                if current_section is not None:
                    sections[current_section] = "\n".join(current_lines).strip()
                current_section = line[3:].strip()
                current_lines = []
            elif current_section is not None:
                current_lines.append(line)

        if current_section is not None:
            sections[current_section] = "\n".join(current_lines).strip()

        return sections
