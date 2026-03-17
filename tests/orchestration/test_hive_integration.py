"""Tests for hive-mind integration wiring (Tasks 012-013).

Verifies ResourceBroker, UsageTracker, and SessionManager integration
with spawn_hive.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from autopilot.core.config import (
    AutopilotConfig,
    ClaudeConfig,
    GitConfig,
    HiveMindConfig,
    ProjectConfig,
    QualityGatesConfig,
)
from autopilot.orchestration.hive import HiveError, HiveMindManager

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def config() -> AutopilotConfig:
    return AutopilotConfig(
        project=ProjectConfig(name="test-project"),
        claude=ClaudeConfig(claude_flow_version="1.0.0"),
        git=GitConfig(branch_prefix="autopilot/", branch_strategy="batch"),
        quality_gates=QualityGatesConfig(),
        hive_mind=HiveMindConfig(namespace="test-ns", spawn_timeout_seconds=30),
    )


def _mock_run_result(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


class TestResourceBrokerIntegration:
    """Task 012: spawn_hive checks ResourceBroker before spawning."""

    @patch("autopilot.orchestration.hive.build_clean_env", return_value={})
    @patch("autopilot.orchestration.hive.run_with_timeout")
    def test_blocked_by_resource_broker(
        self,
        mock_run: MagicMock,
        _env: MagicMock,
        config: AutopilotConfig,
        tmp_path: Path,
    ) -> None:
        mock_run.return_value = _mock_run_result(stdout="")  # preflight
        broker = MagicMock()
        broker.can_spawn_agent.return_value = (False, "Maximum agents reached")

        manager = HiveMindManager(config, cwd=tmp_path, resource_broker=broker)

        with pytest.raises(HiveError, match="Maximum agents reached"):
            manager.spawn_hive("objective", use_claude=False)

        broker.can_spawn_agent.assert_called_once_with("test-project")

    @patch("autopilot.orchestration.hive.build_clean_env", return_value={})
    @patch("autopilot.orchestration.hive.run_with_timeout")
    def test_allowed_by_resource_broker(
        self,
        mock_run: MagicMock,
        _env: MagicMock,
        config: AutopilotConfig,
        tmp_path: Path,
    ) -> None:
        mock_run.side_effect = [
            _mock_run_result(stdout=""),  # preflight
            _mock_run_result(returncode=0),  # spawn
        ]
        broker = MagicMock()
        broker.can_spawn_agent.return_value = (True, "")

        manager = HiveMindManager(config, cwd=tmp_path, resource_broker=broker)
        session = manager.spawn_hive("objective", use_claude=False)

        assert session.status == "spawned"

    @patch("autopilot.orchestration.hive.build_clean_env", return_value={})
    @patch("autopilot.orchestration.hive.run_with_timeout")
    def test_register_agent_called_after_spawn(
        self,
        mock_run: MagicMock,
        _env: MagicMock,
        config: AutopilotConfig,
        tmp_path: Path,
    ) -> None:
        mock_run.side_effect = [
            _mock_run_result(stdout=""),
            _mock_run_result(returncode=0),
        ]
        broker = MagicMock()
        broker.can_spawn_agent.return_value = (True, "")

        manager = HiveMindManager(config, cwd=tmp_path, resource_broker=broker)
        manager.spawn_hive("objective", use_claude=False)

        broker.register_agent.assert_called_once_with("test-project", "hive-mind:test-ns")

    @patch("autopilot.orchestration.hive.build_clean_env", return_value={})
    @patch("autopilot.orchestration.hive.run_with_timeout")
    def test_no_broker_works_fine(
        self,
        mock_run: MagicMock,
        _env: MagicMock,
        config: AutopilotConfig,
        tmp_path: Path,
    ) -> None:
        mock_run.side_effect = [
            _mock_run_result(stdout=""),
            _mock_run_result(returncode=0),
        ]

        manager = HiveMindManager(config, cwd=tmp_path)
        session = manager.spawn_hive("objective", use_claude=False)

        assert session.status == "spawned"


class TestUsageTrackerIntegration:
    """Task 012: spawn_hive checks and records usage via UsageTracker."""

    @patch("autopilot.orchestration.hive.build_clean_env", return_value={})
    @patch("autopilot.orchestration.hive.run_with_timeout")
    def test_blocked_by_usage_quota(
        self,
        mock_run: MagicMock,
        _env: MagicMock,
        config: AutopilotConfig,
        tmp_path: Path,
    ) -> None:
        mock_run.return_value = _mock_run_result(stdout="")  # preflight
        tracker = MagicMock()
        tracker.can_execute.return_value = (False, "Daily cycle limit reached")

        manager = HiveMindManager(config, cwd=tmp_path, usage_tracker=tracker)

        with pytest.raises(HiveError, match="Daily cycle limit reached"):
            manager.spawn_hive("objective", use_claude=False)

        tracker.can_execute.assert_called_once_with("test-project")

    @patch("autopilot.orchestration.hive.build_clean_env", return_value={})
    @patch("autopilot.orchestration.hive.run_with_timeout")
    def test_records_cycle_after_spawn(
        self,
        mock_run: MagicMock,
        _env: MagicMock,
        config: AutopilotConfig,
        tmp_path: Path,
    ) -> None:
        mock_run.side_effect = [
            _mock_run_result(stdout=""),
            _mock_run_result(returncode=0),
        ]
        tracker = MagicMock()
        tracker.can_execute.return_value = (True, "")

        manager = HiveMindManager(config, cwd=tmp_path, usage_tracker=tracker)
        manager.spawn_hive("objective", use_claude=False)

        tracker.record_cycle.assert_called_once_with("test-project")

    @patch("autopilot.orchestration.hive.build_clean_env", return_value={})
    @patch("autopilot.orchestration.hive.run_with_timeout")
    def test_no_tracker_works_fine(
        self,
        mock_run: MagicMock,
        _env: MagicMock,
        config: AutopilotConfig,
        tmp_path: Path,
    ) -> None:
        mock_run.side_effect = [
            _mock_run_result(stdout=""),
            _mock_run_result(returncode=0),
        ]

        manager = HiveMindManager(config, cwd=tmp_path)
        session = manager.spawn_hive("objective", use_claude=False)

        assert session.status == "spawned"


class TestSessionManagerIntegration:
    """Task 013: spawn_hive creates session record via SessionManager."""

    @patch("autopilot.orchestration.hive.build_clean_env", return_value={})
    @patch("autopilot.orchestration.hive.subprocess.Popen")
    @patch("autopilot.orchestration.hive.run_with_timeout")
    def test_creates_session_record_claude_mode(
        self,
        mock_run: MagicMock,
        mock_popen: MagicMock,
        _env: MagicMock,
        config: AutopilotConfig,
        tmp_path: Path,
    ) -> None:
        mock_run.return_value = _mock_run_result(stdout="")
        mock_process = MagicMock()
        mock_process.pid = 42
        mock_popen.return_value = mock_process

        session_mgr = MagicMock()

        manager = HiveMindManager(config, cwd=tmp_path, session_manager=session_mgr)
        session = manager.spawn_hive("objective", use_claude=True)

        from autopilot.core.models import SessionType

        session_mgr.create_session.assert_called_once_with(
            project="test-project",
            session_type=SessionType.HIVE_MIND,
            agent_name="hive-mind:test-ns",
            pid=42,
            cycle_id=session.id,
        )

    @patch("autopilot.orchestration.hive.build_clean_env", return_value={})
    @patch("autopilot.orchestration.hive.run_with_timeout")
    def test_creates_session_record_non_claude(
        self,
        mock_run: MagicMock,
        _env: MagicMock,
        config: AutopilotConfig,
        tmp_path: Path,
    ) -> None:
        mock_run.side_effect = [
            _mock_run_result(stdout=""),
            _mock_run_result(returncode=0),
        ]
        session_mgr = MagicMock()

        manager = HiveMindManager(config, cwd=tmp_path, session_manager=session_mgr)
        session = manager.spawn_hive("objective", use_claude=False)

        from autopilot.core.models import SessionType

        session_mgr.create_session.assert_called_once_with(
            project="test-project",
            session_type=SessionType.HIVE_MIND,
            agent_name="hive-mind:test-ns",
            pid=None,
            cycle_id=session.id,
        )

    @patch("autopilot.orchestration.hive.build_clean_env", return_value={})
    @patch("autopilot.orchestration.hive.run_with_timeout")
    def test_no_session_manager_works_fine(
        self,
        mock_run: MagicMock,
        _env: MagicMock,
        config: AutopilotConfig,
        tmp_path: Path,
    ) -> None:
        mock_run.side_effect = [
            _mock_run_result(stdout=""),
            _mock_run_result(returncode=0),
        ]

        manager = HiveMindManager(config, cwd=tmp_path)
        session = manager.spawn_hive("objective", use_claude=False)

        assert session.status == "spawned"


class TestStopHivePermissionError:
    """Task 009: stop_hive catches PermissionError for cross-user processes."""

    @patch("os.kill", side_effect=PermissionError("Operation not permitted"))
    def test_permission_error_caught(
        self,
        _mock_kill: MagicMock,
        config: AutopilotConfig,
        tmp_path: Path,
    ) -> None:
        from autopilot.orchestration.hive import HiveSession

        manager = HiveMindManager(config, cwd=tmp_path)
        session = HiveSession(
            id="s1",
            branch="b",
            objective="o",
            metadata={"pid": 999, "namespace": "ns"},
        )

        # Should not raise
        manager.stop_hive(session, force=True)
        assert session.status == "stopped"


class TestSpawnHiveVersionPin:
    """Review fix: spawn_hive uses pinned version from config, not @latest."""

    @patch("autopilot.orchestration.hive.build_clean_env", return_value={})
    @patch("autopilot.orchestration.hive.run_with_timeout")
    def test_uses_pinned_version(
        self,
        mock_run: MagicMock,
        _env: MagicMock,
        config: AutopilotConfig,
        tmp_path: Path,
    ) -> None:
        mock_run.side_effect = [
            _mock_run_result(stdout=""),
            _mock_run_result(returncode=0),
        ]

        manager = HiveMindManager(config, cwd=tmp_path)
        manager.spawn_hive("objective", use_claude=False)

        spawn_cmd = mock_run.call_args_list[1][0][0]
        assert "ruflo@1.0.0" in " ".join(spawn_cmd)
        assert "ruflo@latest" not in " ".join(spawn_cmd)


class TestSpawnHiveMetadata:
    """Review fix: task_file and task_ids stored in session metadata."""

    @patch("autopilot.orchestration.hive.build_clean_env", return_value={})
    @patch("autopilot.orchestration.hive.run_with_timeout")
    def test_stores_task_file_and_ids(
        self,
        mock_run: MagicMock,
        _env: MagicMock,
        config: AutopilotConfig,
        tmp_path: Path,
    ) -> None:
        mock_run.side_effect = [
            _mock_run_result(stdout=""),
            _mock_run_result(returncode=0),
        ]

        manager = HiveMindManager(config, cwd=tmp_path)
        session = manager.spawn_hive(
            "objective",
            use_claude=False,
            task_file="tasks/tasks-1.md",
            task_ids=["001", "002"],
        )

        assert session.metadata["task_file"] == "tasks/tasks-1.md"
        assert session.metadata["task_ids"] == ["001", "002"]
