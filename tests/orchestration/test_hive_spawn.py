"""Tests for spawn_hive and stop_hive methods (Tasks 008-009)."""

from __future__ import annotations

import subprocess
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
        hive_mind=HiveMindConfig(namespace="test-ns", spawn_timeout_seconds=30),
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


class TestHiveSessionMetadata:
    """Task 008: HiveSession has metadata dict field."""

    def test_metadata_default_empty_dict(self) -> None:
        session = HiveSession(id="s1", branch="b", objective="o")
        assert session.metadata == {}
        assert isinstance(session.metadata, dict)

    def test_metadata_stores_arbitrary_data(self) -> None:
        session = HiveSession(id="s1", branch="b", objective="o", metadata={"pid": 1234})
        assert session.metadata["pid"] == 1234


class TestPreflightChecks:
    """Task 008: _preflight_checks raises HiveError on dirty tree or active session."""

    @patch("autopilot.orchestration.hive.run_with_timeout")
    def test_dirty_git_tree_raises(self, mock_run: MagicMock, manager: HiveMindManager) -> None:
        mock_run.return_value = _mock_run_result(stdout="M src/foo.py\n")

        with pytest.raises(HiveError, match="dirty"):
            manager._preflight_checks("test-ns")

    @patch("autopilot.orchestration.hive.run_with_timeout")
    def test_clean_git_tree_passes(self, mock_run: MagicMock, manager: HiveMindManager) -> None:
        mock_run.return_value = _mock_run_result(stdout="")

        # Should not raise
        manager._preflight_checks("test-ns")

    @patch("autopilot.orchestration.hive.run_with_timeout")
    def test_active_session_raises(self, mock_run: MagicMock, manager: HiveMindManager) -> None:
        mock_run.return_value = _mock_run_result(stdout="")
        # Simulate active session by patching _has_active_session
        with (
            patch.object(manager, "_has_active_session", return_value=True),
            pytest.raises(HiveError, match="active session"),
        ):
            manager._preflight_checks("test-ns")


class TestHasActiveSession:
    """Task 008: _has_active_session is a placeholder returning False."""

    def test_returns_false_placeholder(self, manager: HiveMindManager) -> None:
        assert manager._has_active_session("any-ns") is False


class TestSpawnHive:
    """Task 008: spawn_hive using Popen for claude mode and run_with_timeout for non-claude."""

    @patch("autopilot.orchestration.hive.build_clean_env", return_value={})
    @patch("autopilot.orchestration.hive.subprocess.Popen")
    @patch("autopilot.orchestration.hive.run_with_timeout")
    def test_claude_mode_uses_popen(
        self,
        mock_run: MagicMock,
        mock_popen: MagicMock,
        _env: MagicMock,
        manager: HiveMindManager,
    ) -> None:
        # Preflight: clean git tree
        mock_run.return_value = _mock_run_result(stdout="")
        mock_process = MagicMock()
        mock_process.pid = 42
        mock_popen.return_value = mock_process

        session = manager.spawn_hive("Implement tasks", use_claude=True)

        assert session.status == "spawned"
        assert session.metadata["pid"] == 42
        assert session.id in manager._active_processes
        assert manager._active_processes[session.id] is mock_process
        # Verify --claude in command
        cmd = mock_popen.call_args[0][0]
        assert "--claude" in cmd
        assert "ruflo@latest" in " ".join(cmd)

    @patch("autopilot.orchestration.hive.build_clean_env", return_value={})
    @patch("autopilot.orchestration.hive.run_with_timeout")
    def test_non_claude_mode_uses_run_with_timeout(
        self,
        mock_run: MagicMock,
        _env: MagicMock,
        manager: HiveMindManager,
    ) -> None:
        # First call = preflight git check, second = spawn
        mock_run.side_effect = [
            _mock_run_result(stdout=""),  # preflight
            _mock_run_result(returncode=0),  # spawn
        ]

        session = manager.spawn_hive("Implement tasks", use_claude=False)

        assert session.status == "spawned"
        # Second call is spawn
        spawn_cmd = mock_run.call_args_list[1][0][0]
        assert "--claude" not in spawn_cmd

    @patch("autopilot.orchestration.hive.build_clean_env", return_value={})
    @patch("autopilot.orchestration.hive.run_with_timeout")
    def test_non_claude_failure_raises(
        self,
        mock_run: MagicMock,
        _env: MagicMock,
        manager: HiveMindManager,
    ) -> None:
        mock_run.side_effect = [
            _mock_run_result(stdout=""),  # preflight
            _mock_run_result(returncode=1, stderr="spawn failed"),  # spawn
        ]

        with pytest.raises(HiveError, match="spawn failed"):
            manager.spawn_hive("Implement tasks", use_claude=False)

    @patch("autopilot.orchestration.hive.build_clean_env", return_value={})
    @patch("autopilot.orchestration.hive.run_with_timeout")
    def test_namespace_resolution_from_config(
        self,
        mock_run: MagicMock,
        _env: MagicMock,
        manager: HiveMindManager,
    ) -> None:
        # Preflight clean
        mock_run.side_effect = [
            _mock_run_result(stdout=""),
            _mock_run_result(returncode=0),
        ]

        manager.spawn_hive("obj", use_claude=False)

        # Namespace should come from config.hive_mind.namespace = "test-ns"
        spawn_cmd = mock_run.call_args_list[1][0][0]
        assert "--namespace" in spawn_cmd
        ns_idx = spawn_cmd.index("--namespace")
        assert spawn_cmd[ns_idx + 1] == "test-ns"

    @patch("autopilot.orchestration.hive.build_clean_env", return_value={})
    @patch("autopilot.orchestration.hive.run_with_timeout")
    def test_explicit_namespace_overrides_config(
        self,
        mock_run: MagicMock,
        _env: MagicMock,
        manager: HiveMindManager,
    ) -> None:
        mock_run.side_effect = [
            _mock_run_result(stdout=""),
            _mock_run_result(returncode=0),
        ]

        manager.spawn_hive("obj", namespace="custom-ns", use_claude=False)

        spawn_cmd = mock_run.call_args_list[1][0][0]
        ns_idx = spawn_cmd.index("--namespace")
        assert spawn_cmd[ns_idx + 1] == "custom-ns"


class TestDeprecationWarnings:
    """Task 008: init_hive and spawn_workers emit DeprecationWarning."""

    @patch("autopilot.orchestration.hive.run_with_timeout")
    @patch("autopilot.orchestration.hive.build_clean_env", return_value={})
    def test_init_hive_warns(
        self, _env: MagicMock, mock_run: MagicMock, manager: HiveMindManager
    ) -> None:
        mock_run.return_value = _mock_run_result()
        with pytest.warns(DeprecationWarning, match="spawn_hive"):
            manager.init_hive("branch", "objective")

    @patch("autopilot.orchestration.hive.run_with_timeout")
    @patch("autopilot.orchestration.hive.build_clean_env", return_value={})
    def test_spawn_workers_warns(
        self, _env: MagicMock, mock_run: MagicMock, manager: HiveMindManager
    ) -> None:
        mock_run.return_value = _mock_run_result()
        session = HiveSession(id="s1", branch="b", objective="o")
        with pytest.warns(DeprecationWarning, match="spawn_hive"):
            manager.spawn_workers(session, 1)


class TestStopHive:
    """Task 009: stop_hive with graceful and force modes."""

    @patch("autopilot.orchestration.hive.build_clean_env", return_value={})
    @patch("autopilot.orchestration.hive.run_with_timeout")
    @patch("os.kill")
    def test_graceful_shutdown(
        self,
        mock_kill: MagicMock,
        mock_run: MagicMock,
        _env: MagicMock,
        manager: HiveMindManager,
    ) -> None:
        mock_run.return_value = _mock_run_result()
        session = HiveSession(
            id="s1",
            branch="b",
            objective="o",
            metadata={"pid": 123, "namespace": "test-ns"},
        )

        manager.stop_hive(session)

        # Graceful shutdown was called
        cmd = mock_run.call_args[0][0]
        assert "shutdown" in cmd
        assert "--namespace" in cmd
        # SIGTERM was sent
        mock_kill.assert_called_once()
        assert session.status == "stopped"
        assert session.ended_at is not None

    @patch("os.kill")
    def test_force_skips_graceful(
        self,
        mock_kill: MagicMock,
        manager: HiveMindManager,
    ) -> None:
        session = HiveSession(
            id="s1",
            branch="b",
            objective="o",
            metadata={"pid": 123, "namespace": "test-ns"},
        )

        with patch("autopilot.orchestration.hive.run_with_timeout") as mock_run:
            manager.stop_hive(session, force=True)
            # Graceful shutdown should NOT be called
            mock_run.assert_not_called()

        mock_kill.assert_called_once()
        assert session.status == "stopped"

    @patch("os.kill", side_effect=ProcessLookupError)
    def test_process_already_exited(
        self,
        mock_kill: MagicMock,
        manager: HiveMindManager,
    ) -> None:
        session = HiveSession(
            id="s1",
            branch="b",
            objective="o",
            metadata={"pid": 999, "namespace": "test-ns"},
        )

        # Should not raise
        manager.stop_hive(session, force=True)
        assert session.status == "stopped"

    @patch("autopilot.orchestration.hive.build_clean_env", return_value={})
    @patch(
        "autopilot.orchestration.hive.run_with_timeout",
        side_effect=subprocess.TimeoutExpired(cmd="npx", timeout=30),
    )
    @patch("os.kill")
    def test_graceful_timeout_caught(
        self,
        mock_kill: MagicMock,
        mock_run: MagicMock,
        _env: MagicMock,
        manager: HiveMindManager,
    ) -> None:
        session = HiveSession(
            id="s1",
            branch="b",
            objective="o",
            metadata={"pid": 123, "namespace": "test-ns"},
        )

        # Should not raise -- timeout is caught, then falls through to SIGTERM
        manager.stop_hive(session)
        mock_kill.assert_called_once()
        assert session.status == "stopped"

    def test_cleans_active_processes(self, manager: HiveMindManager) -> None:
        mock_proc = MagicMock()
        manager._active_processes["s1"] = mock_proc
        session = HiveSession(
            id="s1",
            branch="b",
            objective="o",
            metadata={"namespace": "ns"},
        )

        manager.stop_hive(session, force=True)

        assert "s1" not in manager._active_processes
