"""Tests for debugging pipeline support functions."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import yaml

from autopilot.debugging.models import DebuggingResult, DebuggingTask
from autopilot.debugging.pipeline import (
    load_debugging_task,
    run_quality_gates,
    track_fix_iteration,
    validate_debugging_run,
    validate_source_scope,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


# -- load_debugging_task --


class TestLoadDebuggingTask:
    """Tests for load_debugging_task."""

    def test_loads_valid_yaml(self, tmp_path: Path) -> None:
        task_file = tmp_path / "task.yaml"
        task_file.write_text(
            yaml.dump(
                {
                    "task_id": "DBG-001",
                    "feature": "login",
                    "title": "Verify login flow",
                    "description": "End-to-end login test",
                    "staging_url": "http://staging.example.com",
                    "steps": [
                        {"action": "click", "target": "#login-btn"},
                        {"action": "fill", "target": "#email", "value": "test@x.com"},
                    ],
                    "acceptance_criteria": ["User sees dashboard"],
                    "source_scope": ["src/auth/"],
                }
            )
        )
        task = load_debugging_task(task_file)
        assert isinstance(task, DebuggingTask)
        assert task.task_id == "DBG-001"
        assert len(task.steps) == 2
        assert task.steps[0].action == "click"
        assert task.acceptance_criteria == ("User sees dashboard",)
        assert task.source_scope == ("src/auth/",)

    def test_raises_on_missing_required_field(self, tmp_path: Path) -> None:
        task_file = tmp_path / "task.yaml"
        task_file.write_text(
            yaml.dump(
                {
                    "task_id": "DBG-002",
                    "feature": "login",
                    # missing title, description, staging_url, steps, etc.
                }
            )
        )
        with pytest.raises(ValueError, match="Missing required field"):
            load_debugging_task(task_file)

    def test_raises_on_malformed_yaml(self, tmp_path: Path) -> None:
        task_file = tmp_path / "bad.yaml"
        task_file.write_text("key: [\ninvalid:\n  - {broken")
        with pytest.raises(ValueError, match="Failed to parse YAML"):
            load_debugging_task(task_file)

    def test_raises_on_non_dict_yaml(self, tmp_path: Path) -> None:
        task_file = tmp_path / "list.yaml"
        task_file.write_text(yaml.dump(["a", "b"]))
        with pytest.raises(ValueError, match="must be a YAML mapping"):
            load_debugging_task(task_file)

    def test_parses_step_defaults(self, tmp_path: Path) -> None:
        """Steps with only action/target get default values."""
        task_file = tmp_path / "task.yaml"
        task_file.write_text(
            yaml.dump(
                {
                    "task_id": "DBG-003",
                    "feature": "signup",
                    "title": "Verify signup",
                    "description": "Test signup flow",
                    "staging_url": "http://staging.example.com",
                    "steps": [{"action": "click", "target": "#btn"}],
                    "acceptance_criteria": ["Success"],
                    "source_scope": ["src/"],
                }
            )
        )
        task = load_debugging_task(task_file)
        step = task.steps[0]
        assert step.value == ""
        assert step.expect == ""
        assert step.timeout_seconds == 30

    def test_raises_on_non_list_steps(self, tmp_path: Path) -> None:
        task_file = tmp_path / "task.yaml"
        task_file.write_text(
            yaml.dump(
                {
                    "task_id": "DBG-005",
                    "feature": "login",
                    "title": "Test",
                    "description": "Desc",
                    "staging_url": "http://staging.example.com",
                    "steps": "not a list",
                    "acceptance_criteria": ["OK"],
                    "source_scope": ["src/"],
                }
            )
        )
        with pytest.raises(ValueError, match="must be a list"):
            load_debugging_task(task_file)

    def test_raises_on_null_acceptance_criteria(self, tmp_path: Path) -> None:
        task_file = tmp_path / "task.yaml"
        task_file.write_text(
            yaml.dump(
                {
                    "task_id": "DBG-006",
                    "feature": "login",
                    "title": "Test",
                    "description": "Desc",
                    "staging_url": "http://staging.example.com",
                    "steps": [{"action": "click", "target": "#btn"}],
                    "acceptance_criteria": None,
                    "source_scope": ["src/"],
                }
            )
        )
        with pytest.raises(ValueError, match="must be a list"):
            load_debugging_task(task_file)

    def test_optional_fields_default(self, tmp_path: Path) -> None:
        """Optional fields like ux_review_enabled default correctly."""
        task_file = tmp_path / "task.yaml"
        task_file.write_text(
            yaml.dump(
                {
                    "task_id": "DBG-004",
                    "feature": "profile",
                    "title": "Verify profile",
                    "description": "Test profile page",
                    "staging_url": "http://staging.example.com",
                    "steps": [{"action": "navigate", "target": "/profile"}],
                    "acceptance_criteria": ["Profile loads"],
                    "source_scope": ["src/profile/"],
                }
            )
        )
        task = load_debugging_task(task_file)
        assert task.ux_review_enabled is True
        assert task.ux_capture_states == ()


# -- validate_source_scope --


class TestValidateSourceScope:
    """Tests for validate_source_scope."""

    def test_all_files_within_scope(self) -> None:
        assert (
            validate_source_scope(
                modified_files=("src/auth/login.py", "src/auth/utils.py"),
                allowed_scope=("src/auth/",),
            )
            is True
        )

    def test_file_outside_scope(self) -> None:
        assert (
            validate_source_scope(
                modified_files=("src/auth/login.py", "src/billing/charge.py"),
                allowed_scope=("src/auth/",),
            )
            is False
        )

    def test_empty_modified_files(self) -> None:
        assert (
            validate_source_scope(
                modified_files=(),
                allowed_scope=("src/auth/",),
            )
            is True
        )

    def test_multiple_scopes(self) -> None:
        assert (
            validate_source_scope(
                modified_files=("src/auth/login.py", "tests/auth/test_login.py"),
                allowed_scope=("src/auth/", "tests/auth/"),
            )
            is True
        )

    def test_partial_prefix_no_match(self) -> None:
        """src/authorization/ should not match scope src/auth/ (uses path parts)."""
        assert (
            validate_source_scope(
                modified_files=("src/authorization/check.py",),
                allowed_scope=("src/auth/",),
            )
            is False
        )


# -- run_quality_gates --


class TestRunQualityGates:
    """Tests for run_quality_gates."""

    def test_success(self, tmp_path: Path) -> None:
        result = subprocess.CompletedProcess(
            args=["just", "all"], returncode=0, stdout="All checks passed", stderr=""
        )
        with patch("autopilot.debugging.pipeline.subprocess.run", return_value=result):
            passed, output = run_quality_gates(tmp_path)
        assert passed is True
        assert "All checks passed" in output

    def test_failure(self, tmp_path: Path) -> None:
        result = subprocess.CompletedProcess(
            args=["just", "all"], returncode=1, stdout="", stderr="Lint error"
        )
        with patch("autopilot.debugging.pipeline.subprocess.run", return_value=result):
            passed, output = run_quality_gates(tmp_path)
        assert passed is False
        assert "Lint error" in output

    def test_just_not_found(self, tmp_path: Path) -> None:
        with patch(
            "autopilot.debugging.pipeline.subprocess.run",
            side_effect=FileNotFoundError("just not found"),
        ):
            passed, output = run_quality_gates(tmp_path)
        assert passed is False
        assert "not found" in output

    def test_timeout(self, tmp_path: Path) -> None:
        with patch(
            "autopilot.debugging.pipeline.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="just all", timeout=60),
        ):
            passed, output = run_quality_gates(tmp_path, timeout_seconds=60)
        assert passed is False
        assert "timed out" in output


# -- track_fix_iteration --


class TestTrackFixIteration:
    """Tests for track_fix_iteration."""

    def test_within_limit(self) -> None:
        can_continue, msg = track_fix_iteration("DBG-001", attempt=1, max_iterations=3)
        assert can_continue is True
        assert "1/3" in msg

    def test_at_max(self) -> None:
        can_continue, msg = track_fix_iteration("DBG-001", attempt=3, max_iterations=3)
        assert can_continue is True
        assert "3/3" in msg

    def test_beyond_max(self) -> None:
        can_continue, msg = track_fix_iteration("DBG-001", attempt=4, max_iterations=3)
        assert can_continue is False
        assert "Escalating" in msg


# -- validate_debugging_run --


class TestValidateDebuggingRun:
    """Tests for validate_debugging_run."""

    def test_escalated_task(self, sample_debugging_task: Callable[..., DebuggingTask]) -> None:
        task = sample_debugging_task()
        result = DebuggingResult(task_id=task.task_id, escalated=True, escalation_reason="timeout")
        passed, msg = validate_debugging_run(task, result)
        assert passed is False
        assert "escalated" in msg

    def test_passing_task(self, sample_debugging_task: Callable[..., DebuggingTask]) -> None:
        task = sample_debugging_task()
        result = DebuggingResult(task_id=task.task_id, overall_pass=True)
        passed, msg = validate_debugging_run(task, result)
        assert passed is True
        assert "passed" in msg

    def test_failing_task(self, sample_debugging_task: Callable[..., DebuggingTask]) -> None:
        task = sample_debugging_task()
        result = DebuggingResult(task_id=task.task_id, overall_pass=False)
        passed, msg = validate_debugging_run(task, result)
        assert passed is False
        assert "did not pass" in msg
