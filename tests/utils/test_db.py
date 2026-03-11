"""Tests for autopilot.utils.db."""

from __future__ import annotations

import sqlite3
from pathlib import Path  # noqa: TC003

from autopilot.utils.db import Database


class TestDatabaseInit:
    def test_creates_db_file(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        Database(db_path)
        assert db_path.exists()

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        db_path = tmp_path / "deep" / "nested" / "test.db"
        Database(db_path)
        assert db_path.exists()

    def test_wal_mode_enabled(self, tmp_path: Path) -> None:
        db = Database(tmp_path / "test.db")
        conn = db.get_connection()
        try:
            mode = conn.execute("PRAGMA journal_mode").fetchone()
            assert mode[0] == "wal"
        finally:
            conn.close()

    def test_foreign_keys_enabled(self, tmp_path: Path) -> None:
        db = Database(tmp_path / "test.db")
        conn = db.get_connection()
        try:
            fk = conn.execute("PRAGMA foreign_keys").fetchone()
            assert fk[0] == 1
        finally:
            conn.close()

    def test_schema_version_tracked(self, tmp_path: Path) -> None:
        db = Database(tmp_path / "test.db")
        assert db.schema_version == 1

    def test_idempotent_init(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        Database(db_path)
        Database(db_path)  # second init should not fail


class TestTables:
    def test_all_six_tables_exist(self, tmp_path: Path) -> None:
        db = Database(tmp_path / "test.db")
        conn = db.get_connection()
        try:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name NOT LIKE 'sqlite_%'"
                ).fetchall()
            }
            expected = {
                "schema_version",
                "projects",
                "sessions",
                "cycles",
                "dispatches",
                "enforcement_metrics",
                "velocity",
            }
            assert expected.issubset(tables)
        finally:
            conn.close()

    def test_all_six_indices_exist(self, tmp_path: Path) -> None:
        db = Database(tmp_path / "test.db")
        conn = db.get_connection()
        try:
            indices = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='index' "
                    "AND name NOT LIKE 'sqlite_%'"
                ).fetchall()
            }
            expected = {
                "idx_sessions_project",
                "idx_cycles_project",
                "idx_dispatches_cycle",
                "idx_dispatches_agent",
                "idx_enforcement_project_date",
                "idx_velocity_project",
            }
            assert expected.issubset(indices)
        finally:
            conn.close()


class TestInsertProject:
    def test_insert_and_query(self, tmp_path: Path) -> None:
        db = Database(tmp_path / "test.db")
        db.insert_project(
            id="proj-1", name="test", path="/tmp/test", type="python"
        )
        conn = db.get_connection()
        try:
            row = conn.execute("SELECT * FROM projects WHERE id = ?", ("proj-1",)).fetchone()
            assert row["name"] == "test"
            assert row["type"] == "python"
        finally:
            conn.close()

    def test_duplicate_name_raises(self, tmp_path: Path) -> None:
        db = Database(tmp_path / "test.db")
        db.insert_project(id="p1", name="dup", path="/a", type="python")
        try:
            db.insert_project(id="p2", name="dup", path="/b", type="python")
        except sqlite3.IntegrityError:
            pass
        else:
            msg = "Expected IntegrityError for duplicate name"
            raise AssertionError(msg)

    def test_invalid_type_raises(self, tmp_path: Path) -> None:
        db = Database(tmp_path / "test.db")
        try:
            db.insert_project(id="p1", name="bad", path="/a", type="ruby")
        except sqlite3.IntegrityError:
            pass
        else:
            msg = "Expected IntegrityError for invalid type"
            raise AssertionError(msg)


class TestInsertSession:
    def test_insert_with_project(self, tmp_path: Path) -> None:
        db = Database(tmp_path / "test.db")
        db.insert_project(id="proj-1", name="test", path="/tmp", type="python")
        db.insert_session(
            id="sess-1",
            project_id="proj-1",
            type="daemon",
            status="running",
            started_at="2024-01-01T00:00:00Z",
        )
        conn = db.get_connection()
        try:
            row = conn.execute("SELECT * FROM sessions WHERE id = ?", ("sess-1",)).fetchone()
            assert row["type"] == "daemon"
            assert row["status"] == "running"
        finally:
            conn.close()


class TestInsertCycle:
    def test_insert_with_project(self, tmp_path: Path) -> None:
        db = Database(tmp_path / "test.db")
        db.insert_project(id="proj-1", name="test", path="/tmp", type="python")
        db.insert_cycle(
            id="cyc-1",
            project_id="proj-1",
            status="COMPLETED",
            started_at="2024-01-01T00:00:00Z",
        )
        conn = db.get_connection()
        try:
            row = conn.execute("SELECT * FROM cycles WHERE id = ?", ("cyc-1",)).fetchone()
            assert row["status"] == "COMPLETED"
        finally:
            conn.close()


class TestInsertDispatch:
    def test_insert_with_cycle(self, tmp_path: Path) -> None:
        db = Database(tmp_path / "test.db")
        db.insert_project(id="proj-1", name="test", path="/tmp", type="python")
        db.insert_cycle(
            id="cyc-1", project_id="proj-1", status="COMPLETED",
            started_at="2024-01-01T00:00:00Z",
        )
        db.insert_dispatch(
            cycle_id="cyc-1", agent="engineering-manager", status="success",
        )
        conn = db.get_connection()
        try:
            row = conn.execute("SELECT * FROM dispatches WHERE cycle_id = ?", ("cyc-1",)).fetchone()
            assert row["agent"] == "engineering-manager"
        finally:
            conn.close()


class TestInsertEnforcementMetric:
    def test_insert(self, tmp_path: Path) -> None:
        db = Database(tmp_path / "test.db")
        db.insert_project(id="proj-1", name="test", path="/tmp", type="python")
        db.insert_enforcement_metric(
            project_id="proj-1",
            collected_at="2024-01-01T00:00:00Z",
            category="duplication",
            violation_count=3,
            files_scanned=10,
        )
        conn = db.get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM enforcement_metrics WHERE project_id = ?", ("proj-1",)
            ).fetchone()
            assert row["violation_count"] == 3
        finally:
            conn.close()


class TestInsertVelocity:
    def test_insert(self, tmp_path: Path) -> None:
        db = Database(tmp_path / "test.db")
        db.insert_project(id="proj-1", name="test", path="/tmp", type="python")
        db.insert_velocity(
            project_id="proj-1",
            sprint_id="sprint-1",
            points_planned=21,
            points_completed=18,
        )
        conn = db.get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM velocity WHERE project_id = ?", ("proj-1",)
            ).fetchone()
            assert row["points_planned"] == 21
            assert row["points_completed"] == 18
        finally:
            conn.close()


class TestForeignKeyConstraints:
    def test_session_requires_project(self, tmp_path: Path) -> None:
        db = Database(tmp_path / "test.db")
        try:
            db.insert_session(
                id="sess-1",
                project_id="nonexistent",
                type="daemon",
                status="running",
                started_at="2024-01-01T00:00:00Z",
            )
        except sqlite3.IntegrityError:
            pass
        else:
            msg = "Expected IntegrityError for missing project FK"
            raise AssertionError(msg)
