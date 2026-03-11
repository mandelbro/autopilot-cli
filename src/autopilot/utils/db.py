"""SQLite database management with WAL mode (RFC Section 3.4.2).

Located at ~/.autopilot/autopilot.db. Provides schema creation,
connection management, retry-with-backoff for concurrent writes,
and convenience insert methods.
"""

from __future__ import annotations

import sqlite3
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

_SCHEMA_VERSION = 1

_SCHEMA_SQL = """\
-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- Core tables per RFC 3.4.2
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    path TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('python', 'typescript', 'hybrid')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    config_hash TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    type TEXT NOT NULL CHECK (type IN ('daemon', 'cycle', 'discovery', 'manual')),
    status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed', 'paused')),
    pid INTEGER,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    agent_name TEXT,
    cycle_id TEXT,
    metadata TEXT
);

CREATE TABLE IF NOT EXISTS cycles (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    session_id TEXT REFERENCES sessions(id),
    status TEXT NOT NULL CHECK (status IN ('COMPLETED', 'PARTIAL', 'FAILED')),
    started_at TEXT NOT NULL,
    ended_at TEXT,
    dispatches_planned INTEGER DEFAULT 0,
    dispatches_succeeded INTEGER DEFAULT 0,
    dispatches_failed INTEGER DEFAULT 0,
    duration_seconds REAL
);

CREATE TABLE IF NOT EXISTS dispatches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_id TEXT NOT NULL REFERENCES cycles(id),
    agent TEXT NOT NULL,
    action TEXT,
    project_name TEXT,
    task_id TEXT,
    status TEXT NOT NULL CHECK (status IN ('success', 'failed', 'timeout')),
    duration_seconds REAL,
    exit_code INTEGER,
    error TEXT
);

CREATE TABLE IF NOT EXISTS enforcement_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL REFERENCES projects(id),
    collected_at TEXT NOT NULL,
    category TEXT NOT NULL,
    violation_count INTEGER DEFAULT 0,
    files_scanned INTEGER DEFAULT 0,
    metadata TEXT
);

CREATE TABLE IF NOT EXISTS velocity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL REFERENCES projects(id),
    sprint_id TEXT NOT NULL,
    started_at TEXT,
    ended_at TEXT,
    points_planned INTEGER DEFAULT 0,
    points_completed INTEGER DEFAULT 0,
    tasks_completed INTEGER DEFAULT 0,
    tasks_carried_over INTEGER DEFAULT 0
);

-- Indices for common query patterns
CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project_id);
CREATE INDEX IF NOT EXISTS idx_cycles_project ON cycles(project_id);
CREATE INDEX IF NOT EXISTS idx_dispatches_cycle ON dispatches(cycle_id);
CREATE INDEX IF NOT EXISTS idx_dispatches_agent ON dispatches(agent);
CREATE INDEX IF NOT EXISTS idx_enforcement_project_date
    ON enforcement_metrics(project_id, collected_at);
CREATE INDEX IF NOT EXISTS idx_velocity_project ON velocity(project_id);
"""

# Retry configuration for SQLITE_BUSY
_MAX_RETRIES = 5
_BASE_DELAY = 0.05  # 50ms


class Database:
    """SQLite database with WAL mode, schema management, and retry logic."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _initialize(self) -> None:
        conn = self.get_connection()
        try:
            conn.executescript(_SCHEMA_SQL)
            # Record schema version if not already present
            existing = conn.execute(
                "SELECT version FROM schema_version WHERE version = ?",
                (_SCHEMA_VERSION,),
            ).fetchone()
            if existing is None:
                conn.execute(
                    "INSERT INTO schema_version (version) VALUES (?)",
                    (_SCHEMA_VERSION,),
                )
            conn.commit()
        finally:
            conn.close()

    def get_connection(self) -> sqlite3.Connection:
        """Return a new connection with WAL mode and foreign keys enabled."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        return conn

    def _retry_write(
        self,
        sql: str,
        params: tuple[Any, ...] = (),
    ) -> None:
        """Execute a write with exponential backoff on SQLITE_BUSY."""
        conn = self.get_connection()
        try:
            for attempt in range(_MAX_RETRIES):
                try:
                    conn.execute(sql, params)
                    conn.commit()
                    return
                except sqlite3.OperationalError as exc:
                    if "database is locked" not in str(exc):
                        raise
                    if attempt == _MAX_RETRIES - 1:
                        raise
                    time.sleep(_BASE_DELAY * (2**attempt))
        finally:
            conn.close()

    def insert_project(
        self,
        *,
        id: str,
        name: str,
        path: str,
        type: str,
        config_hash: str = "",
    ) -> None:
        self._retry_write(
            "INSERT INTO projects (id, name, path, type, config_hash) VALUES (?, ?, ?, ?, ?)",
            (id, name, path, type, config_hash),
        )

    def insert_session(
        self,
        *,
        id: str,
        project_id: str,
        type: str,
        status: str,
        started_at: str,
        pid: int | None = None,
        agent_name: str | None = None,
        cycle_id: str | None = None,
        metadata: str | None = None,
    ) -> None:
        self._retry_write(
            "INSERT INTO sessions (id, project_id, type, status, pid, started_at, "
            "agent_name, cycle_id, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (id, project_id, type, status, pid, started_at, agent_name, cycle_id, metadata),
        )

    def insert_cycle(
        self,
        *,
        id: str,
        project_id: str,
        session_id: str | None = None,
        status: str,
        started_at: str,
        ended_at: str | None = None,
        dispatches_planned: int = 0,
        dispatches_succeeded: int = 0,
        dispatches_failed: int = 0,
        duration_seconds: float = 0.0,
    ) -> None:
        self._retry_write(
            "INSERT INTO cycles (id, project_id, session_id, status, started_at, ended_at, "
            "dispatches_planned, dispatches_succeeded, dispatches_failed, duration_seconds) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                id,
                project_id,
                session_id,
                status,
                started_at,
                ended_at,
                dispatches_planned,
                dispatches_succeeded,
                dispatches_failed,
                duration_seconds,
            ),
        )

    def insert_dispatch(
        self,
        *,
        cycle_id: str,
        agent: str,
        status: str,
        action: str | None = None,
        project_name: str | None = None,
        task_id: str | None = None,
        duration_seconds: float = 0.0,
        exit_code: int = 0,
        error: str | None = None,
    ) -> None:
        self._retry_write(
            "INSERT INTO dispatches (cycle_id, agent, action, project_name, task_id, "
            "status, duration_seconds, exit_code, error) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                cycle_id,
                agent,
                action,
                project_name,
                task_id,
                status,
                duration_seconds,
                exit_code,
                error,
            ),
        )

    def insert_enforcement_metric(
        self,
        *,
        project_id: str,
        collected_at: str,
        category: str,
        violation_count: int = 0,
        files_scanned: int = 0,
        metadata: str | None = None,
    ) -> None:
        self._retry_write(
            "INSERT INTO enforcement_metrics (project_id, collected_at, category, "
            "violation_count, files_scanned, metadata) VALUES (?, ?, ?, ?, ?, ?)",
            (project_id, collected_at, category, violation_count, files_scanned, metadata),
        )

    def insert_velocity(
        self,
        *,
        project_id: str,
        sprint_id: str,
        started_at: str | None = None,
        ended_at: str | None = None,
        points_planned: int = 0,
        points_completed: int = 0,
        tasks_completed: int = 0,
        tasks_carried_over: int = 0,
    ) -> None:
        self._retry_write(
            "INSERT INTO velocity (project_id, sprint_id, started_at, ended_at, "
            "points_planned, points_completed, tasks_completed, tasks_carried_over) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                project_id,
                sprint_id,
                started_at,
                ended_at,
                points_planned,
                points_completed,
                tasks_completed,
                tasks_carried_over,
            ),
        )

    @property
    def schema_version(self) -> int:
        """Return the current schema version."""
        conn = self.get_connection()
        try:
            row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
            return row[0] if row and row[0] is not None else 0
        except sqlite3.OperationalError:
            return 0
        finally:
            conn.close()
