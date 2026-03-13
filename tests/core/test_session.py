"""Tests for session management CRUD (Task 038)."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from autopilot.core.models import SessionStatus, SessionType
from autopilot.core.session import SessionManager
from autopilot.utils.db import Database

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    db = Database(tmp_path / "test.db")
    # Insert a project for foreign key constraint
    db.insert_project(
        id="proj-1",
        name="test-project",
        path="/tmp/test",
        type="python",
    )
    return db


@pytest.fixture()
def mgr(db: Database) -> SessionManager:
    return SessionManager(db=db)


class TestCreateSession:
    def test_creates_with_defaults(self, mgr: SessionManager) -> None:
        session = mgr.create_session("proj-1", SessionType.DAEMON)
        assert session.project == "proj-1"
        assert session.type == SessionType.DAEMON
        assert session.status == SessionStatus.RUNNING
        assert session.id  # UUID assigned

    def test_creates_with_agent_name(self, mgr: SessionManager) -> None:
        session = mgr.create_session("proj-1", SessionType.CYCLE, agent_name="project-leader")
        assert session.agent_name == "project-leader"

    def test_creates_with_pid(self, mgr: SessionManager) -> None:
        session = mgr.create_session("proj-1", SessionType.DAEMON, pid=12345)
        assert session.pid == 12345


class TestGetSession:
    def test_get_existing(self, mgr: SessionManager) -> None:
        created = mgr.create_session("proj-1", SessionType.MANUAL)
        fetched = mgr.get_session(created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.type == SessionType.MANUAL

    def test_get_nonexistent_returns_none(self, mgr: SessionManager) -> None:
        assert mgr.get_session("nonexistent-id") is None


class TestUpdateStatus:
    def test_updates_status(self, mgr: SessionManager) -> None:
        session = mgr.create_session("proj-1", SessionType.DAEMON)
        mgr.update_status(session.id, SessionStatus.PAUSED)
        fetched = mgr.get_session(session.id)
        assert fetched is not None
        assert fetched.status == SessionStatus.PAUSED


class TestEndSession:
    def test_end_sets_status_and_timestamp(self, mgr: SessionManager) -> None:
        session = mgr.create_session("proj-1", SessionType.CYCLE)
        mgr.end_session(session.id, SessionStatus.COMPLETED)
        fetched = mgr.get_session(session.id)
        assert fetched is not None
        assert fetched.status == SessionStatus.COMPLETED
        assert fetched.ended_at is not None


class TestListSessions:
    def test_list_all(self, mgr: SessionManager) -> None:
        mgr.create_session("proj-1", SessionType.DAEMON)
        mgr.create_session("proj-1", SessionType.CYCLE)
        sessions = mgr.list_sessions()
        assert len(sessions) == 2

    def test_list_by_project(self, mgr: SessionManager, db: Database) -> None:
        db.insert_project(id="proj-2", name="other-project", path="/tmp/other", type="python")
        mgr.create_session("proj-1", SessionType.DAEMON)
        mgr.create_session("proj-2", SessionType.CYCLE)
        sessions = mgr.list_sessions(project="proj-1")
        assert len(sessions) == 1
        assert sessions[0].project == "proj-1"

    def test_list_by_status(self, mgr: SessionManager) -> None:
        s1 = mgr.create_session("proj-1", SessionType.DAEMON)
        mgr.create_session("proj-1", SessionType.CYCLE)
        mgr.end_session(s1.id, SessionStatus.COMPLETED)
        sessions = mgr.list_sessions(status_filter=SessionStatus.RUNNING)
        assert len(sessions) == 1

    def test_list_by_type(self, mgr: SessionManager) -> None:
        mgr.create_session("proj-1", SessionType.DAEMON)
        mgr.create_session("proj-1", SessionType.CYCLE)
        sessions = mgr.list_sessions(type_filter=SessionType.DAEMON)
        assert len(sessions) == 1
        assert sessions[0].type == SessionType.DAEMON


class TestCleanupOrphaned:
    def test_cleans_dead_pid_sessions(self, mgr: SessionManager) -> None:
        session = mgr.create_session("proj-1", SessionType.DAEMON, pid=999999)
        with patch("autopilot.core.session.is_running", return_value=False):
            cleaned = mgr.cleanup_orphaned()
        assert session.id in cleaned
        fetched = mgr.get_session(session.id)
        assert fetched is not None
        assert fetched.status == SessionStatus.FAILED

    def test_skips_live_pid_sessions(self, mgr: SessionManager) -> None:
        mgr.create_session("proj-1", SessionType.DAEMON, pid=os.getpid())
        with patch("autopilot.core.session.is_running", return_value=True):
            cleaned = mgr.cleanup_orphaned()
        assert len(cleaned) == 0

    def test_skips_sessions_without_pid(self, mgr: SessionManager) -> None:
        mgr.create_session("proj-1", SessionType.MANUAL)
        cleaned = mgr.cleanup_orphaned()
        assert len(cleaned) == 0
