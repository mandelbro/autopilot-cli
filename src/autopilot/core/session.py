"""Session management data model and CRUD (Task 038).

SQLite-backed CRUD for daemon, cycle, discovery, and manual sessions
across all projects per RFC Section 3.4.2.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from autopilot.core.models import Session, SessionStatus, SessionType
from autopilot.utils.process import is_running

if TYPE_CHECKING:
    from autopilot.utils.db import Database

_log = logging.getLogger(__name__)


class SessionManager:
    """CRUD operations for autonomous sessions with SQLite persistence."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def create_session(
        self,
        project: str,
        session_type: SessionType,
        agent_name: str | None = None,
        *,
        pid: int | None = None,
        cycle_id: str | None = None,
    ) -> Session:
        """Create and persist a new session."""
        session = Session(
            id=str(uuid.uuid4()),
            project=project,
            type=session_type,
            status=SessionStatus.RUNNING,
            pid=pid,
            started_at=datetime.now(UTC),
            agent_name=agent_name,
            cycle_id=cycle_id,
        )
        self._db.insert_session(
            id=session.id,
            project_id=session.project,
            type=session.type.value,
            status=session.status.value,
            started_at=session.started_at.isoformat(),
            pid=session.pid,
            agent_name=session.agent_name,
            cycle_id=session.cycle_id,
        )
        return session

    def update_status(self, session_id: str, status: SessionStatus) -> None:
        """Update the status of an existing session."""
        conn = self._db.get_connection()
        try:
            conn.execute(
                "UPDATE sessions SET status = ? WHERE id = ?",
                (status.value, session_id),
            )
            conn.commit()
        finally:
            conn.close()

    def end_session(self, session_id: str, status: SessionStatus) -> None:
        """Mark a session as ended with a timestamp."""
        now = datetime.now(UTC).isoformat()
        conn = self._db.get_connection()
        try:
            conn.execute(
                "UPDATE sessions SET status = ?, ended_at = ? WHERE id = ?",
                (status.value, now, session_id),
            )
            conn.commit()
        finally:
            conn.close()

    def list_sessions(
        self,
        project: str | None = None,
        status_filter: SessionStatus | None = None,
        type_filter: SessionType | None = None,
    ) -> list[Session]:
        """List sessions with optional filters."""
        query = "SELECT * FROM sessions WHERE 1=1"
        params: list[str] = []

        if project is not None:
            query += " AND project_id = ?"
            params.append(project)
        if status_filter is not None:
            query += " AND status = ?"
            params.append(status_filter.value)
        if type_filter is not None:
            query += " AND type = ?"
            params.append(type_filter.value)

        query += " ORDER BY started_at DESC"

        conn = self._db.get_connection()
        try:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_session(row) for row in rows]
        finally:
            conn.close()

    def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID."""
        conn = self._db.get_connection()
        try:
            row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
            return self._row_to_session(row) if row else None
        finally:
            conn.close()

    def cleanup_orphaned(self) -> list[str]:
        """Find and mark sessions with status=running but dead PIDs.

        Returns a list of session IDs that were cleaned up.
        """
        running = self.list_sessions(status_filter=SessionStatus.RUNNING)
        cleaned: list[str] = []

        for session in running:
            if session.pid is not None and not is_running(session.pid):
                self.end_session(session.id, SessionStatus.FAILED)
                cleaned.append(session.id)
                _log.warning(
                    "session_orphan_cleaned: id=%s pid=%d project=%s",
                    session.id,
                    session.pid,
                    session.project,
                )

        return cleaned

    @staticmethod
    def _row_to_session(row: object) -> Session:
        """Convert a sqlite3.Row to a Session model."""
        # sqlite3.Row supports index and key access
        r: dict[str, object] = dict(
            zip(row.keys(), tuple(row), strict=False)  # type: ignore[union-attr]
        )
        started_at_raw = r.get("started_at")
        ended_at_raw = r.get("ended_at")
        return Session(
            id=str(r["id"]),
            project=str(r["project_id"]),
            type=SessionType(str(r["type"])),
            status=SessionStatus(str(r["status"])),
            pid=int(str(r["pid"])) if r.get("pid") is not None else None,
            started_at=(
                datetime.fromisoformat(str(started_at_raw))
                if started_at_raw
                else datetime.now(UTC)
            ),
            ended_at=(
                datetime.fromisoformat(str(ended_at_raw))
                if ended_at_raw
                else None
            ),
            agent_name=str(r["agent_name"]) if r.get("agent_name") else None,
            cycle_id=str(r["cycle_id"]) if r.get("cycle_id") else None,
        )
