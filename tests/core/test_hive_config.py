"""Tests for HiveMindConfig and HiveMindResult (Task 003)."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

if TYPE_CHECKING:
    from pathlib import Path

from autopilot.core.config import AutopilotConfig, HiveMindConfig, ProjectConfig
from autopilot.core.models import HiveMindResult, SessionType


class TestHiveMindConfig:
    def test_defaults(self) -> None:
        cfg = HiveMindConfig()
        assert cfg.enabled is False
        assert cfg.namespace == ""
        assert cfg.worker_count == 4
        assert cfg.use_claude is True
        assert cfg.batch_strategy == "auto"
        assert cfg.objective_template == "default"
        assert cfg.duplication_check is True
        assert cfg.cleanup_pass is True
        assert cfg.security_scan is True
        assert cfg.coverage_check is True
        assert cfg.file_size_check is True
        assert cfg.code_review_enabled is True
        assert cfg.code_review_label == "claude-review"
        assert cfg.max_review_rounds == 3
        assert cfg.auto_merge is True
        assert cfg.format_command == "just format"
        assert cfg.spawn_timeout_seconds == 60
        assert cfg.session_timeout_seconds == 14400

    def test_frozen(self) -> None:
        cfg = HiveMindConfig()
        with pytest.raises(ValidationError):
            cfg.enabled = True  # type: ignore[misc]

    def test_worker_count_rejects_zero(self) -> None:
        with pytest.raises(ValidationError, match="worker_count"):
            HiveMindConfig(worker_count=0)

    def test_worker_count_accepts_max(self) -> None:
        cfg = HiveMindConfig(worker_count=15)
        assert cfg.worker_count == 15

    def test_worker_count_rejects_above_max(self) -> None:
        with pytest.raises(ValidationError, match="worker_count"):
            HiveMindConfig(worker_count=16)

    def test_max_review_rounds_rejects_zero(self) -> None:
        with pytest.raises(ValidationError, match="max_review_rounds"):
            HiveMindConfig(max_review_rounds=0)

    def test_max_review_rounds_accepts_max(self) -> None:
        cfg = HiveMindConfig(max_review_rounds=10)
        assert cfg.max_review_rounds == 10

    def test_max_review_rounds_rejects_above_max(self) -> None:
        with pytest.raises(ValidationError, match="max_review_rounds"):
            HiveMindConfig(max_review_rounds=11)

    def test_spawn_timeout_rejects_zero(self) -> None:
        with pytest.raises(ValidationError, match="spawn_timeout_seconds"):
            HiveMindConfig(spawn_timeout_seconds=0)

    def test_session_timeout_rejects_zero(self) -> None:
        with pytest.raises(ValidationError, match="session_timeout_seconds"):
            HiveMindConfig(session_timeout_seconds=0)

    def test_yaml_round_trip(self, tmp_path: Path) -> None:
        original = AutopilotConfig(
            project=ProjectConfig(name="hive-test"),
            hive_mind=HiveMindConfig(
                enabled=True,
                namespace="test-ns",
                worker_count=8,
                code_review_enabled=False,
                max_review_rounds=5,
            ),
        )
        yaml_path = tmp_path / "config.yaml"
        original.to_yaml(yaml_path)
        loaded = AutopilotConfig.from_yaml(yaml_path)

        assert loaded.hive_mind.enabled is True
        assert loaded.hive_mind.namespace == "test-ns"
        assert loaded.hive_mind.worker_count == 8
        assert loaded.hive_mind.code_review_enabled is False
        assert loaded.hive_mind.max_review_rounds == 5

    def test_yaml_without_hive_mind_section(self, tmp_path: Path) -> None:
        yaml_path = tmp_path / "config.yaml"
        yaml_path.write_text("project:\n  name: no-hive\n")
        loaded = AutopilotConfig.from_yaml(yaml_path)
        assert loaded.hive_mind.enabled is False
        assert loaded.hive_mind.worker_count == 4

    def test_autopilot_config_has_hive_mind_field(self) -> None:
        cfg = AutopilotConfig(project=ProjectConfig(name="test"))
        assert isinstance(cfg.hive_mind, HiveMindConfig)


class TestHiveMindResult:
    def test_construction(self) -> None:
        result = HiveMindResult(
            session_id="sess-1",
            namespace="ns",
            task_file="tasks/tasks-1.md",
            task_ids=("001", "002"),
        )
        assert result.session_id == "sess-1"
        assert result.namespace == "ns"
        assert result.task_file == "tasks/tasks-1.md"
        assert result.task_ids == ("001", "002")

    def test_frozen_immutability(self) -> None:
        result = HiveMindResult(session_id="s", namespace="n", task_file="t", task_ids=("001",))
        with pytest.raises(FrozenInstanceError):
            result.exit_code = 1  # type: ignore[misc]

    def test_task_ids_is_tuple(self) -> None:
        result = HiveMindResult(session_id="s", namespace="n", task_file="t", task_ids=("001",))
        assert isinstance(result.task_ids, tuple)

    def test_git_derived_fields_default_none(self) -> None:
        result = HiveMindResult(session_id="s", namespace="n", task_file="t", task_ids=())
        assert result.tasks_completed is None
        assert result.prs_created is None
        assert result.prs_merged is None
        assert result.batches_completed is None

    def test_default_values(self) -> None:
        result = HiveMindResult(session_id="s", namespace="n", task_file="t", task_ids=())
        assert result.exit_code == 0
        assert result.duration_seconds == 0.0
        assert result.output == ""
        assert result.error == ""


class TestSessionTypeHiveMind:
    def test_hive_mind_value(self) -> None:
        assert SessionType.HIVE_MIND == "hive_mind"

    def test_round_trip(self) -> None:
        assert SessionType("hive_mind") is SessionType.HIVE_MIND
