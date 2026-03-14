"""Tests for event-driven scheduler triggers (Task 087)."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

import pytest

from autopilot.orchestration.triggers import (
    FileChangeTrigger,
    GitPushTrigger,
    ManualTrigger,
    TriggerEvent,
    TriggerManager,
)


class TestFileChangeTrigger:
    def test_returns_none_when_no_changes(self, tmp_path: Path) -> None:
        watch_dir = tmp_path / "tasks"
        watch_dir.mkdir()
        (watch_dir / "task.md").write_text("initial")

        trigger = FileChangeTrigger([watch_dir])

        assert trigger.check() is None

    def test_detects_modified_file(self, tmp_path: Path) -> None:
        watch_dir = tmp_path / "tasks"
        watch_dir.mkdir()
        task_file = watch_dir / "task.md"
        task_file.write_text("initial")

        trigger = FileChangeTrigger([watch_dir])

        # Ensure mtime changes
        time.sleep(0.05)
        task_file.write_text("modified")

        event = trigger.check()
        assert event is not None
        assert event.trigger_type == "file_change"
        assert "1 file(s) changed" in event.source

    def test_detects_new_file(self, tmp_path: Path) -> None:
        watch_dir = tmp_path / "tasks"
        watch_dir.mkdir()

        trigger = FileChangeTrigger([watch_dir])

        (watch_dir / "new_file.md").write_text("new content")

        event = trigger.check()
        assert event is not None
        assert event.trigger_type == "file_change"

    def test_returns_none_after_reset(self, tmp_path: Path) -> None:
        watch_dir = tmp_path / "tasks"
        watch_dir.mkdir()
        task_file = watch_dir / "task.md"
        task_file.write_text("initial")

        trigger = FileChangeTrigger([watch_dir])

        time.sleep(0.05)
        task_file.write_text("modified")

        assert trigger.check() is not None

        trigger.reset()
        assert trigger.check() is None

    def test_ignores_nonexistent_watch_dir(self, tmp_path: Path) -> None:
        nonexistent = tmp_path / "does_not_exist"
        trigger = FileChangeTrigger([nonexistent])
        assert trigger.check() is None

    def test_handles_multiple_watch_dirs(self, tmp_path: Path) -> None:
        dir_a = tmp_path / "tasks"
        dir_b = tmp_path / "board"
        dir_a.mkdir()
        dir_b.mkdir()

        trigger = FileChangeTrigger([dir_a, dir_b])

        (dir_b / "note.md").write_text("new")

        event = trigger.check()
        assert event is not None
        assert event.trigger_type == "file_change"


class TestGitPushTrigger:
    @patch("autopilot.orchestration.triggers.GitPushTrigger._get_head_sha")
    def test_returns_none_when_sha_unchanged(self, mock_sha: object) -> None:
        mock_sha.return_value = "abc123"  # type: ignore[attr-defined]
        trigger = GitPushTrigger(Path("/fake"), branch="main")
        assert trigger.check() is None

    @patch("autopilot.orchestration.triggers.GitPushTrigger._get_head_sha")
    def test_detects_sha_change(self, mock_sha: object) -> None:
        mock_sha.return_value = "abc123"  # type: ignore[attr-defined]
        trigger = GitPushTrigger(Path("/fake"), branch="main")

        mock_sha.return_value = "def456"  # type: ignore[attr-defined]
        event = trigger.check()
        assert event is not None
        assert event.trigger_type == "git_push"
        assert "def456" in event.source

    @patch("autopilot.orchestration.triggers.GitPushTrigger._get_head_sha")
    def test_returns_none_after_consuming_change(self, mock_sha: object) -> None:
        mock_sha.return_value = "abc123"  # type: ignore[attr-defined]
        trigger = GitPushTrigger(Path("/fake"), branch="main")

        mock_sha.return_value = "def456"  # type: ignore[attr-defined]
        assert trigger.check() is not None
        # Same SHA now stored, so no new event
        assert trigger.check() is None

    @patch("autopilot.orchestration.triggers.GitPushTrigger._get_head_sha")
    def test_reset_updates_last_sha(self, mock_sha: object) -> None:
        mock_sha.return_value = "abc123"  # type: ignore[attr-defined]
        trigger = GitPushTrigger(Path("/fake"), branch="main")

        mock_sha.return_value = "def456"  # type: ignore[attr-defined]
        trigger.reset()
        # After reset, sha is updated so no event
        assert trigger.check() is None

    @patch("autopilot.orchestration.triggers.GitPushTrigger._get_head_sha")
    def test_handles_empty_sha(self, mock_sha: object) -> None:
        mock_sha.return_value = ""  # type: ignore[attr-defined]
        trigger = GitPushTrigger(Path("/fake"), branch="main")
        assert trigger.check() is None


class TestManualTrigger:
    def test_returns_none_when_not_fired(self) -> None:
        trigger = ManualTrigger()
        assert trigger.check() is None

    def test_returns_event_when_fired(self) -> None:
        trigger = ManualTrigger()
        trigger.fire()

        event = trigger.check()
        assert event is not None
        assert event.trigger_type == "manual"
        assert event.source == "manual request"

    def test_reset_clears_fired_state(self) -> None:
        trigger = ManualTrigger()
        trigger.fire()
        assert trigger.check() is not None

        trigger.reset()
        assert trigger.check() is None

    def test_remains_fired_until_reset(self) -> None:
        trigger = ManualTrigger()
        trigger.fire()
        assert trigger.check() is not None
        assert trigger.check() is not None  # still fired


class TestTriggerEvent:
    def test_frozen_dataclass(self) -> None:
        event = TriggerEvent(trigger_type="manual", source="test")
        assert event.trigger_type == "manual"
        assert event.source == "test"
        assert event.timestamp is not None

        with pytest.raises(AttributeError):
            event.trigger_type = "other"  # type: ignore[misc]


class TestTriggerManagerInterval:
    def test_interval_strategy_always_returns_none(self) -> None:
        manual = ManualTrigger()
        manual.fire()

        manager = TriggerManager(strategy="interval", triggers=[manual])
        assert manager.should_run_cycle() is None

    def test_strategy_property(self) -> None:
        manager = TriggerManager(strategy="hybrid")
        assert manager.strategy == "hybrid"


class TestTriggerManagerEvent:
    def test_event_strategy_checks_triggers(self) -> None:
        manual = ManualTrigger()
        manager = TriggerManager(
            strategy="event",
            triggers=[manual],
            debounce_seconds=0.0,
        )

        assert manager.should_run_cycle() is None

        manual.fire()
        event = manager.should_run_cycle()
        assert event is not None
        assert event.trigger_type == "manual"

    def test_event_strategy_returns_first_trigger(self) -> None:
        m1 = ManualTrigger()
        m2 = ManualTrigger()
        manager = TriggerManager(
            strategy="event",
            triggers=[m1, m2],
            debounce_seconds=0.0,
        )

        m1.fire()
        m2.fire()
        event = manager.should_run_cycle()
        assert event is not None
        assert event.trigger_type == "manual"


class TestTriggerManagerHybrid:
    def test_hybrid_respects_min_interval(self) -> None:
        manual = ManualTrigger()
        manager = TriggerManager(
            strategy="hybrid",
            triggers=[manual],
            min_interval_seconds=1000.0,
            debounce_seconds=0.0,
        )

        # Record a recent cycle
        manager.record_cycle_completed()

        manual.fire()
        # Should be suppressed because min_interval hasn't elapsed
        assert manager.should_run_cycle() is None

    def test_hybrid_allows_after_interval(self) -> None:
        manual = ManualTrigger()
        manager = TriggerManager(
            strategy="hybrid",
            triggers=[manual],
            min_interval_seconds=0.0,
            debounce_seconds=0.0,
        )

        manual.fire()
        event = manager.should_run_cycle()
        assert event is not None


class TestTriggerManagerDebounce:
    def test_debouncing_prevents_rapid_fire(self) -> None:
        manual = ManualTrigger()
        manager = TriggerManager(
            strategy="event",
            triggers=[manual],
            debounce_seconds=1000.0,
        )

        manual.fire()
        # First call records an event time
        event = manager.should_run_cycle()
        assert event is not None

        # Immediately after, debounce should suppress
        manual.fire()
        assert manager.should_run_cycle() is None

    def test_debounce_allows_after_window(self) -> None:
        manual = ManualTrigger()
        manager = TriggerManager(
            strategy="event",
            triggers=[manual],
            debounce_seconds=0.0,
        )

        manual.fire()
        event = manager.should_run_cycle()
        assert event is not None

        manual.fire()
        event = manager.should_run_cycle()
        assert event is not None


class TestTriggerManagerRecordCycle:
    def test_record_cycle_resets_triggers(self) -> None:
        manual = ManualTrigger()
        manager = TriggerManager(
            strategy="event",
            triggers=[manual],
            debounce_seconds=0.0,
        )

        manual.fire()
        assert manager.should_run_cycle() is not None

        manager.record_cycle_completed()
        # Manual trigger should be reset
        assert manager.should_run_cycle() is None

    def test_add_trigger(self) -> None:
        manager = TriggerManager(strategy="event", debounce_seconds=0.0)
        manual = ManualTrigger()
        manager.add_trigger(manual)

        manual.fire()
        assert manager.should_run_cycle() is not None
