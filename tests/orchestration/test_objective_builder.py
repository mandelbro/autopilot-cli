"""Tests for HiveObjectiveBuilder (Task 007)."""

from __future__ import annotations

import logging

import pytest

from autopilot.core.config import (
    AutopilotConfig,
    HiveMindConfig,
    ProjectConfig,
    QualityGatesConfig,
)
from autopilot.orchestration.objective_builder import HiveObjectiveBuilder


@pytest.fixture
def hive_config() -> AutopilotConfig:
    return AutopilotConfig(
        project=ProjectConfig(name="test"),
        quality_gates=QualityGatesConfig(
            pre_commit="ruff check",
            type_check="pyright",
            test="pytest",
            all="just",
        ),
    )


class TestBuild:
    def test_returns_non_empty(self, hive_config: AutopilotConfig) -> None:
        builder = HiveObjectiveBuilder(hive_config)
        result = builder.build("tasks/tasks-1.md", ["001", "002"])
        assert len(result) > 0

    def test_contains_task_ids(self, hive_config: AutopilotConfig) -> None:
        builder = HiveObjectiveBuilder(hive_config)
        result = builder.build("tasks/tasks-1.md", ["001", "002"])
        assert "001, 002" in result

    def test_contains_task_file(self, hive_config: AutopilotConfig) -> None:
        builder = HiveObjectiveBuilder(hive_config)
        result = builder.build("tasks/tasks-1.md", ["001"])
        assert "tasks/tasks-1.md" in result

    def test_code_review_disabled(self) -> None:
        config = AutopilotConfig(
            project=ProjectConfig(name="test"),
            hive_mind=HiveMindConfig(code_review_enabled=False),
        )
        builder = HiveObjectiveBuilder(config)
        result = builder.build("t.md", ["001"])
        assert "code review" not in result.lower() or "Request a code review" not in result

    def test_quality_passes_disabled(self) -> None:
        config = AutopilotConfig(
            project=ProjectConfig(name="test"),
            hive_mind=HiveMindConfig(
                duplication_check=False,
                cleanup_pass=False,
                security_scan=False,
                coverage_check=False,
                file_size_check=False,
            ),
        )
        builder = HiveObjectiveBuilder(config)
        result = builder.build("t.md", ["001"])
        assert "Duplication Detection" not in result
        assert "Cleanup Pass" not in result
        assert "Security Analysis" not in result
        assert "Test Coverage" not in result
        assert "File Size Optimization" not in result

    def test_all_quality_passes_present_by_default(self, hive_config: AutopilotConfig) -> None:
        builder = HiveObjectiveBuilder(hive_config)
        result = builder.build("t.md", ["001"])
        assert "Duplication Detection" in result
        assert "Cleanup Pass" in result
        assert "Security Analysis" in result
        assert "Test Coverage" in result
        assert "File Size Optimization" in result


class TestFormatQualityGates:
    def test_with_gates(self) -> None:
        gates = QualityGatesConfig(
            pre_commit="ruff check",
            type_check="pyright",
            test="pytest",
        )
        result = HiveObjectiveBuilder._format_quality_gates(gates)
        assert "- pre-commit: ruff check" in result
        assert "- type-check: pyright" in result
        assert "- test: pytest" in result

    def test_empty_gates(self) -> None:
        gates = QualityGatesConfig()
        result = HiveObjectiveBuilder._format_quality_gates(gates)
        assert result == ""

    def test_with_all_gate(self) -> None:
        gates = QualityGatesConfig(all="just")
        result = HiveObjectiveBuilder._format_quality_gates(gates)
        assert "- all: just" in result


class TestLengthWarning:
    def test_warns_on_long_objective(
        self, hive_config: AutopilotConfig, caplog: pytest.LogCaptureFixture
    ) -> None:
        builder = HiveObjectiveBuilder(hive_config)
        with caplog.at_level(logging.WARNING):
            result = builder.build("t.md", [f"{i:03d}" for i in range(200)])
        if len(result) > 4000:
            assert "4000" in caplog.text


class TestTemplateName:
    def test_default_template(self, hive_config: AutopilotConfig) -> None:
        builder = HiveObjectiveBuilder(hive_config)
        result = builder.build("t.md", ["001"], template_name="default")
        assert len(result) > 0
