"""Tests for hive-mind integration with claude-flow (Task 037)."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from autopilot.core.config import (
    AutopilotConfig,
    ClaudeConfig,
    GitConfig,
    ProjectConfig,
    QualityGatesConfig,
)
from autopilot.orchestration.hive import HiveError, HiveMindManager, HiveSession

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def config() -> AutopilotConfig:
    return AutopilotConfig(
        project=ProjectConfig(name="test-project"),
        claude=ClaudeConfig(claude_flow_version="1.0.0"),
        git=GitConfig(branch_prefix="autopilot/", branch_strategy="batch"),
        quality_gates=QualityGatesConfig(
            pre_commit="ruff check",
            type_check="pyright",
            test="pytest",
        ),
    )


@pytest.fixture()
def manager(config: AutopilotConfig, tmp_path: Path) -> HiveMindManager:
    return HiveMindManager(config, cwd=tmp_path)


def _mock_run_result(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


class TestHealthCheck:
    @patch("autopilot.orchestration.hive.run_with_timeout")
    def test_healthy(self, mock_run: MagicMock, manager: HiveMindManager) -> None:
        mock_run.return_value = _mock_run_result(stdout="1.0.0")

        ok, version = manager.health_check()

        assert ok is True
        assert version == "1.0.0"

    @patch("autopilot.orchestration.hive.run_with_timeout")
    def test_unhealthy_nonzero(self, mock_run: MagicMock, manager: HiveMindManager) -> None:
        mock_run.return_value = _mock_run_result(returncode=1, stderr="not found")

        ok, msg = manager.health_check()

        assert ok is False
        assert "not found" in msg

    @patch("autopilot.orchestration.hive.run_with_timeout", side_effect=FileNotFoundError)
    def test_npx_not_found(self, _run: MagicMock, manager: HiveMindManager) -> None:
        ok, msg = manager.health_check()

        assert ok is False
        assert "npx not found" in msg

    @patch(
        "autopilot.orchestration.hive.run_with_timeout",
        side_effect=subprocess.TimeoutExpired(cmd="npx", timeout=30),
    )
    def test_timeout(self, _run: MagicMock, manager: HiveMindManager) -> None:
        ok, msg = manager.health_check()

        assert ok is False
        assert "timed out" in msg


class TestCreateBranch:
    @patch("autopilot.utils.git.create_branch")
    def test_single_task_per_task_strategy(
        self, mock_branch: MagicMock, config: AutopilotConfig, tmp_path: Path
    ) -> None:
        config = config.model_copy(
            update={"git": config.git.model_copy(update={"branch_strategy": "per-task"})}
        )
        mgr = HiveMindManager(config, cwd=tmp_path)

        branch = mgr.create_branch(["042"])

        assert branch == "autopilot/task-042"
        mock_branch.assert_called_once_with("autopilot/task-042", cwd=tmp_path)

    @patch("autopilot.utils.git.create_branch")
    def test_batch_strategy(self, mock_branch: MagicMock, manager: HiveMindManager) -> None:
        branch = manager.create_branch(["031", "032", "033"])

        assert branch == "autopilot/batch-031-032-033"

    @patch("autopilot.utils.git.create_branch")
    def test_batch_truncation(self, mock_branch: MagicMock, manager: HiveMindManager) -> None:
        branch = manager.create_branch(["031", "032", "033", "034", "035"])

        assert branch == "autopilot/batch-031-032-033-plus2"


class TestInitHive:
    @patch("autopilot.orchestration.hive.run_with_timeout")
    @patch("autopilot.orchestration.hive.build_clean_env", return_value={})
    def test_success(self, _env: MagicMock, mock_run: MagicMock, manager: HiveMindManager) -> None:
        mock_run.return_value = _mock_run_result()

        session = manager.init_hive("autopilot/batch-031", "Implement tasks")

        assert isinstance(session, HiveSession)
        assert session.branch == "autopilot/batch-031"
        assert session.objective == "Implement tasks"
        assert session.status == "active"

        # Verify command includes quality gates
        cmd = mock_run.call_args[0][0]
        assert "swarm" in cmd
        assert "init" in cmd

    @patch("autopilot.orchestration.hive.run_with_timeout")
    @patch("autopilot.orchestration.hive.build_clean_env", return_value={})
    def test_failure_raises(
        self, _env: MagicMock, mock_run: MagicMock, manager: HiveMindManager
    ) -> None:
        mock_run.return_value = _mock_run_result(returncode=1, stderr="swarm init failed")

        with pytest.raises(HiveError, match="Hive init failed"):
            manager.init_hive("branch", "objective")


class TestQualityGates:
    def test_builds_quality_gates_suffix(self, manager: HiveMindManager) -> None:
        suffix = manager._build_quality_gates()

        assert "pre-commit: ruff check" in suffix
        assert "type-check: pyright" in suffix
        assert "test: pytest" in suffix

    def test_empty_when_no_gates(self, tmp_path: Path) -> None:
        config = AutopilotConfig(
            project=ProjectConfig(name="test"),
            quality_gates=QualityGatesConfig(),
        )
        mgr = HiveMindManager(config, cwd=tmp_path)

        assert mgr._build_quality_gates() == ""


class TestSpawnWorkers:
    @patch("autopilot.orchestration.hive.run_with_timeout")
    @patch("autopilot.orchestration.hive.build_clean_env", return_value={})
    def test_spawns_requested_count(
        self, _env: MagicMock, mock_run: MagicMock, manager: HiveMindManager
    ) -> None:
        mock_run.return_value = _mock_run_result()
        session = HiveSession(id="s1", branch="b", objective="o")

        manager.spawn_workers(session, 3)

        assert mock_run.call_count == 3
        assert session.worker_count == 3

    @patch("autopilot.orchestration.hive.run_with_timeout")
    @patch("autopilot.orchestration.hive.build_clean_env", return_value={})
    def test_continues_on_spawn_failure(
        self, _env: MagicMock, mock_run: MagicMock, manager: HiveMindManager
    ) -> None:
        mock_run.return_value = _mock_run_result(returncode=1, stderr="spawn err")
        session = HiveSession(id="s1", branch="b", objective="o")

        # Should not raise — failures are logged as warnings
        manager.spawn_workers(session, 2)

        assert session.worker_count == 2
        assert mock_run.call_count == 2


class TestRecordSession:
    def test_marks_completed(self, manager: HiveMindManager) -> None:
        session = HiveSession(id="s1", branch="b", objective="o")

        manager.record_session(session, "success")

        assert session.status == "completed"
        assert session.ended_at is not None


class TestShutdown:
    @patch("autopilot.orchestration.hive.run_with_timeout")
    @patch("autopilot.orchestration.hive.build_clean_env", return_value={})
    def test_shutdown_success(
        self, _env: MagicMock, mock_run: MagicMock, manager: HiveMindManager
    ) -> None:
        mock_run.return_value = _mock_run_result()
        session = HiveSession(id="s1", branch="b", objective="o")

        manager.shutdown(session)

        assert session.status == "shutdown"

    @patch("autopilot.orchestration.hive.run_with_timeout")
    @patch("autopilot.orchestration.hive.build_clean_env", return_value={})
    def test_shutdown_failure_no_raise(
        self, _env: MagicMock, mock_run: MagicMock, manager: HiveMindManager
    ) -> None:
        mock_run.return_value = _mock_run_result(returncode=1, stderr="err")
        session = HiveSession(id="s1", branch="b", objective="o")

        # Should not raise
        manager.shutdown(session)

        assert session.status == "shutdown"
