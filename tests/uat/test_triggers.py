"""Tests for UAT automatic triggers (Task 075)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from autopilot.uat.test_executor import UATResult
from autopilot.uat.triggers import TriggerConfig, TriggerEvent, UATTrigger

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def project_dir(tmp_path: Path) -> Path:
    """Create a minimal project with tasks."""
    task_dir = tmp_path / "tasks"
    task_dir.mkdir()

    index = (
        "## Overall Project Task Summary\n\n"
        "- **Total Tasks**: 2\n"
        "- **Pending**: 0\n"
        "- **Complete**: 2\n"
        "- **Total Points**: 4\n"
        "- **Points Complete**: 4\n\n"
        "## Task File Index\n\n"
        "- `tasks/tasks-1.md`: Contains Tasks 001 - 002 (2 tasks, 4 points)\n"
    )
    (task_dir / "tasks-index.md").write_text(index)

    tasks = (
        "## Summary (tasks-1.md)\n\n"
        "- **Tasks in this file**: 2\n"
        "- **Task IDs**: 001 - 002\n"
        "- **Total Points**: 4\n\n"
        "## Tasks\n\n"
        "### Task ID: 001\n\n"
        "- **Title**: Trivial doc update\n"
        "- **File**: docs/readme.md\n"
        "- **Complete**: [x]\n"
        "- **Sprint Points**: 1\n\n"
        "### Task ID: 002\n\n"
        "- **Title**: Real feature\n"
        "- **File**: src/feature.py\n"
        "- **Complete**: [x]\n"
        "- **Sprint Points**: 3\n"
    )
    (task_dir / "tasks-1.md").write_text(tasks)

    return tmp_path


class TestTriggerConfig:
    def test_defaults(self) -> None:
        config = TriggerConfig()
        assert config.enabled is True
        assert config.skip_threshold == 1

    def test_custom_values(self) -> None:
        config = TriggerConfig(enabled=False, skip_threshold=2)
        assert config.enabled is False
        assert config.skip_threshold == 2


class TestTriggerEvent:
    def test_frozen(self, tmp_path: Path) -> None:
        event = TriggerEvent(task_id="001", project_dir=tmp_path)
        assert event.task_id == "001"


class TestUATTrigger:
    def test_disabled_trigger_returns_none(self, project_dir: Path) -> None:
        config = TriggerConfig(enabled=False)
        trigger = UATTrigger(config=config)
        result = trigger.on_task_complete("002", project_dir)
        assert result is None

    def test_skips_trivial_task(self, project_dir: Path) -> None:
        config = TriggerConfig(enabled=True, skip_threshold=1)
        trigger = UATTrigger(config=config)
        result = trigger.on_task_complete("001", project_dir)
        assert result is None

    @patch("autopilot.uat.triggers.UATPipeline")
    def test_fires_for_non_trivial_task(
        self, mock_pipeline_cls: MagicMock, project_dir: Path
    ) -> None:
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = UATResult(
            overall_pass=True, score=1.0, test_count=1, passed=1
        )
        mock_pipeline_cls.return_value = mock_pipeline

        trigger = UATTrigger()
        trigger._pipeline = mock_pipeline
        result = trigger.on_task_complete("002", project_dir)

        assert result is not None
        assert result.overall_pass is True

    def test_enabled_property(self) -> None:
        trigger = UATTrigger(TriggerConfig(enabled=True))
        assert trigger.enabled is True

    def test_queue_size_starts_at_zero(self) -> None:
        trigger = UATTrigger()
        assert trigger.queue_size == 0

    def test_is_running_starts_false(self) -> None:
        trigger = UATTrigger()
        assert trigger.is_running is False

    @patch("autopilot.uat.triggers.UATPipeline")
    def test_process_pending_empty(self, mock_pipeline_cls: MagicMock) -> None:
        trigger = UATTrigger()
        results = trigger.process_pending()
        assert results == []
