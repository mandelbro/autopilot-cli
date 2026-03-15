"""Global resource broker for multi-project daemon management (Task 084).

Enforces max_concurrent_daemons and max_concurrent_agents across all
active projects, with priority-weighted allocation and dead daemon cleanup.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autopilot.utils.db import Database

_log = logging.getLogger(__name__)

_BROKER_TABLE_SQL = """\
CREATE TABLE IF NOT EXISTS resource_daemons (
    project TEXT PRIMARY KEY,
    pid INTEGER NOT NULL,
    registered_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE TABLE IF NOT EXISTS resource_agents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    registered_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
"""


@dataclass(frozen=True)
class ResourceStatus:
    """Current resource allocation snapshot."""

    active_daemons: int
    max_daemons: int
    active_agents: int
    max_agents: int
    daemon_projects: list[str] = field(default_factory=lambda: list[str]())
    agent_breakdown: dict[str, int] = field(default_factory=lambda: dict[str, int]())


class ResourceBroker:
    """Global resource broker enforcing concurrent daemon and agent limits.

    Reads limits from ~/.autopilot/config.yaml:
      max_concurrent_daemons (default 3)
      max_concurrent_agents (default 6)

    Supports per-project priority weights for allocation decisions.
    Detects and cleans up dead daemons automatically.
    """

    def __init__(
        self,
        db: Database,
        *,
        max_concurrent_daemons: int = 3,
        max_concurrent_agents: int = 6,
        priority_weights: dict[str, float] | None = None,
    ) -> None:
        self._db = db
        self._max_daemons = max_concurrent_daemons
        self._max_agents = max_concurrent_agents
        self._priority_weights = priority_weights or {}
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        """Create resource tracking tables if they don't exist."""
        conn = self._db.get_connection()
        try:
            conn.executescript(_BROKER_TABLE_SQL)
            conn.commit()
        finally:
            conn.close()

    def can_start_daemon(self, project: str) -> tuple[bool, str]:
        """Check if a new daemon can start for the given project.

        Returns (True, "") if allowed, (False, reason) if blocked.
        """
        self.cleanup_dead_daemons()

        conn = self._db.get_connection()
        try:
            row = conn.execute(
                "SELECT pid FROM resource_daemons WHERE project = ?", (project,)
            ).fetchone()
            if row is not None:
                return False, f"Daemon already running for project '{project}' (PID {row[0]})"

            count = conn.execute("SELECT COUNT(*) FROM resource_daemons").fetchone()[0]
            if count >= self._max_daemons:
                return False, f"Maximum concurrent daemons reached ({count}/{self._max_daemons})"

            return True, ""
        finally:
            conn.close()

    def can_spawn_agent(self, project: str) -> tuple[bool, str]:
        """Check if a new agent can be spawned globally.

        Returns (True, "") if allowed, (False, reason) if blocked.
        """
        conn = self._db.get_connection()
        try:
            count = conn.execute("SELECT COUNT(*) FROM resource_agents").fetchone()[0]
            if count >= self._max_agents:
                return False, f"Maximum concurrent agents reached ({count}/{self._max_agents})"
            return True, ""
        finally:
            conn.close()

    def register_daemon(self, project: str, pid: int) -> None:
        """Register an active daemon for a project."""
        conn = self._db.get_connection()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO resource_daemons (project, pid) VALUES (?, ?)",
                (project, pid),
            )
            conn.commit()
        finally:
            conn.close()

    def release_daemon(self, project: str) -> None:
        """Release daemon registration for a project."""
        conn = self._db.get_connection()
        try:
            conn.execute("DELETE FROM resource_daemons WHERE project = ?", (project,))
            conn.commit()
        finally:
            conn.close()

    def register_agent(self, project: str, agent_name: str) -> int:
        """Register an active agent. Returns the registration ID."""
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                "INSERT INTO resource_agents (project, agent_name) VALUES (?, ?)",
                (project, agent_name),
            )
            conn.commit()
            return cursor.lastrowid or 0
        finally:
            conn.close()

    def release_agent(self, agent_id: int) -> None:
        """Release an agent registration by ID."""
        conn = self._db.get_connection()
        try:
            conn.execute("DELETE FROM resource_agents WHERE id = ?", (agent_id,))
            conn.commit()
        finally:
            conn.close()

    def get_resource_status(self) -> ResourceStatus:
        """Get current resource allocation status."""
        self.cleanup_dead_daemons()
        conn = self._db.get_connection()
        try:
            daemon_rows = conn.execute("SELECT project FROM resource_daemons").fetchall()
            daemon_projects = [r[0] for r in daemon_rows]

            agent_rows = conn.execute(
                "SELECT project, COUNT(*) FROM resource_agents GROUP BY project"
            ).fetchall()
            agent_breakdown = {r[0]: r[1] for r in agent_rows}
            total_agents = sum(agent_breakdown.values())

            return ResourceStatus(
                active_daemons=len(daemon_projects),
                max_daemons=self._max_daemons,
                active_agents=total_agents,
                max_agents=self._max_agents,
                daemon_projects=daemon_projects,
                agent_breakdown=agent_breakdown,
            )
        finally:
            conn.close()

    def cleanup_dead_daemons(self) -> list[str]:
        """Detect dead daemons and release their resources.

        Returns list of project names whose daemons were cleaned up.
        """
        from autopilot.utils.process import is_running

        cleaned: list[str] = []
        conn = self._db.get_connection()
        try:
            rows = conn.execute("SELECT project, pid FROM resource_daemons").fetchall()
            for project, pid in rows:
                if not is_running(pid):
                    conn.execute("DELETE FROM resource_daemons WHERE project = ?", (project,))
                    conn.execute("DELETE FROM resource_agents WHERE project = ?", (project,))
                    cleaned.append(project)
                    _log.info("cleaned_dead_daemon: project=%s pid=%d", project, pid)
            if cleaned:
                conn.commit()
        finally:
            conn.close()
        return cleaned

    def get_priority_weight(self, project: str) -> float:
        """Get the priority weight for a project (default 1.0)."""
        return self._priority_weights.get(project, 1.0)
