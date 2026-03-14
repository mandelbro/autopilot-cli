"""Tests for global resource broker (Task 084)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from autopilot.orchestration.resource_broker import ResourceBroker, ResourceStatus
from autopilot.utils.db import Database

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    return Database(tmp_path / "test.db")


@pytest.fixture()
def broker(db: Database) -> ResourceBroker:
    return ResourceBroker(db, max_concurrent_daemons=3, max_concurrent_agents=6)


class TestCanStartDaemon:
    @patch("autopilot.utils.process.is_running", return_value=True)
    def test_allows_within_limit(self, _mock: object, broker: ResourceBroker) -> None:
        allowed, reason = broker.can_start_daemon("proj-a")
        assert allowed is True
        assert reason == ""

    @patch("autopilot.utils.process.is_running", return_value=True)
    def test_blocks_duplicate_project(self, _mock: object, broker: ResourceBroker) -> None:
        broker.register_daemon("proj-a", 1000)

        allowed, reason = broker.can_start_daemon("proj-a")
        assert allowed is False
        assert "already running" in reason
        assert "proj-a" in reason

    @patch("autopilot.utils.process.is_running", return_value=True)
    def test_blocks_at_daemon_limit(self, _mock: object, broker: ResourceBroker) -> None:
        broker.register_daemon("proj-a", 1000)
        broker.register_daemon("proj-b", 1001)
        broker.register_daemon("proj-c", 1002)

        allowed, reason = broker.can_start_daemon("proj-d")
        assert allowed is False
        assert "Maximum" in reason
        assert "3/3" in reason

    @patch("autopilot.utils.process.is_running", return_value=True)
    def test_allows_different_projects_under_limit(
        self, _mock: object, broker: ResourceBroker
    ) -> None:
        broker.register_daemon("proj-a", 1000)
        broker.register_daemon("proj-b", 1001)

        allowed, reason = broker.can_start_daemon("proj-c")
        assert allowed is True


class TestCanSpawnAgent:
    def test_allows_within_limit(self, broker: ResourceBroker) -> None:
        allowed, reason = broker.can_spawn_agent("proj-a")
        assert allowed is True
        assert reason == ""

    def test_blocks_at_agent_limit(self, broker: ResourceBroker) -> None:
        for i in range(6):
            broker.register_agent("proj-a", f"agent-{i}")

        allowed, reason = broker.can_spawn_agent("proj-a")
        assert allowed is False
        assert "Maximum" in reason
        assert "6/6" in reason


class TestDaemonLifecycle:
    @patch("autopilot.utils.process.is_running", return_value=True)
    def test_register_and_release(self, _mock: object, broker: ResourceBroker) -> None:
        broker.register_daemon("proj-a", 1234)
        status = broker.get_resource_status()
        assert status.active_daemons == 1
        assert "proj-a" in status.daemon_projects

        broker.release_daemon("proj-a")
        status = broker.get_resource_status()
        assert status.active_daemons == 0
        assert status.daemon_projects == []

    @patch("autopilot.utils.process.is_running", return_value=True)
    def test_register_replaces_existing(self, _mock: object, broker: ResourceBroker) -> None:
        broker.register_daemon("proj-a", 1000)
        broker.register_daemon("proj-a", 2000)

        status = broker.get_resource_status()
        assert status.active_daemons == 1


class TestAgentLifecycle:
    def test_register_and_release(self, broker: ResourceBroker) -> None:
        agent_id = broker.register_agent("proj-a", "coder")
        assert agent_id > 0

        # Verify via can_spawn_agent count approaching limit
        for i in range(5):
            broker.register_agent("proj-a", f"agent-{i}")

        allowed, _ = broker.can_spawn_agent("proj-a")
        assert allowed is False

        broker.release_agent(agent_id)
        allowed, _ = broker.can_spawn_agent("proj-a")
        assert allowed is True


class TestResourceStatus:
    @patch("autopilot.utils.process.is_running", return_value=True)
    def test_returns_correct_counts(self, _mock: object, broker: ResourceBroker) -> None:
        broker.register_daemon("proj-a", 1000)
        broker.register_daemon("proj-b", 1001)
        broker.register_agent("proj-a", "coder")
        broker.register_agent("proj-a", "reviewer")
        broker.register_agent("proj-b", "tester")

        status = broker.get_resource_status()

        assert isinstance(status, ResourceStatus)
        assert status.active_daemons == 2
        assert status.max_daemons == 3
        assert status.active_agents == 3
        assert status.max_agents == 6
        assert sorted(status.daemon_projects) == ["proj-a", "proj-b"]
        assert status.agent_breakdown == {"proj-a": 2, "proj-b": 1}

    @patch("autopilot.utils.process.is_running", return_value=True)
    def test_empty_status(self, _mock: object, broker: ResourceBroker) -> None:
        status = broker.get_resource_status()
        assert status.active_daemons == 0
        assert status.active_agents == 0
        assert status.daemon_projects == []
        assert status.agent_breakdown == {}


class TestCleanupDeadDaemons:
    def test_removes_dead_pids(self, broker: ResourceBroker) -> None:
        broker.register_daemon("proj-dead", 99999)
        broker.register_agent("proj-dead", "orphan-agent")

        with patch("autopilot.utils.process.is_running", return_value=False):
            cleaned = broker.cleanup_dead_daemons()

        assert cleaned == ["proj-dead"]

        with patch("autopilot.utils.process.is_running", return_value=True):
            status = broker.get_resource_status()

        assert status.active_daemons == 0
        assert status.active_agents == 0

    def test_keeps_alive_daemons(self, broker: ResourceBroker) -> None:
        broker.register_daemon("proj-alive", 1000)

        with patch("autopilot.utils.process.is_running", return_value=True):
            cleaned = broker.cleanup_dead_daemons()

        assert cleaned == []

        with patch("autopilot.utils.process.is_running", return_value=True):
            status = broker.get_resource_status()

        assert status.active_daemons == 1

    def test_mixed_alive_and_dead(self, broker: ResourceBroker) -> None:
        broker.register_daemon("proj-alive", 1000)
        broker.register_daemon("proj-dead", 99999)

        def selective_is_running(pid: int) -> bool:
            return pid == 1000

        with patch(
            "autopilot.utils.process.is_running",
            side_effect=selective_is_running,
        ):
            cleaned = broker.cleanup_dead_daemons()

        assert cleaned == ["proj-dead"]

        with patch("autopilot.utils.process.is_running", return_value=True):
            status = broker.get_resource_status()

        assert status.active_daemons == 1
        assert "proj-alive" in status.daemon_projects


class TestPriorityWeights:
    def test_default_weight(self, broker: ResourceBroker) -> None:
        assert broker.get_priority_weight("any-project") == 1.0

    def test_custom_weights(self, db: Database) -> None:
        weights = {"critical-proj": 2.0, "low-proj": 0.5}
        broker = ResourceBroker(db, priority_weights=weights)

        assert broker.get_priority_weight("critical-proj") == 2.0
        assert broker.get_priority_weight("low-proj") == 0.5
        assert broker.get_priority_weight("unset-proj") == 1.0
