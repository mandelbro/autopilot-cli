"""Tests for enforcement CLI commands (Task 067)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    from pathlib import Path

import typer
from typer.testing import CliRunner

from autopilot.core.models import (
    CheckResult,
    EnforcementReport,
    SetupResult,
    Violation,
    ViolationSeverity,
)

runner = CliRunner()

_MOD = "autopilot.cli.enforce"


def _make_app() -> typer.Typer:
    """Build a test Typer app with enforce commands registered."""
    app = typer.Typer()
    from autopilot.cli.enforce import register_enforce_commands

    register_enforce_commands(app)
    return app


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _mock_engine(
    *,
    setup_result: SetupResult | None = None,
    check_results: list[CheckResult] | None = None,
    report: EnforcementReport | None = None,
) -> MagicMock:
    """Create a mock EnforcementEngine with configurable return values."""
    engine = MagicMock()
    engine.setup.return_value = setup_result or SetupResult(
        layer="enforcement-engine", success=True
    )
    engine.check.return_value = check_results if check_results is not None else []
    engine.report.return_value = report or EnforcementReport(project_id="test")
    return engine


def _patch_resolve(engine: MagicMock, tmp_path: Path, project_name: str = "test-proj"):
    """Patch ``_resolve_enforcement`` to return the given engine."""
    return patch(
        f"{_MOD}._resolve_enforcement",
        return_value=(engine, tmp_path, project_name),
    )


# ---------------------------------------------------------------------------
# Tests: setup
# ---------------------------------------------------------------------------


class TestEnforceSetup:
    def test_setup_success(self, tmp_path: Path) -> None:
        engine = _mock_engine()
        app = _make_app()
        with _patch_resolve(engine, tmp_path):
            result = runner.invoke(app, ["setup"])
        assert result.exit_code == 0
        assert "setup complete" in result.output.lower()

    def test_setup_with_project_flag(self, tmp_path: Path) -> None:
        engine = _mock_engine()
        app = _make_app()
        with _patch_resolve(engine, tmp_path, "my-proj"):
            result = runner.invoke(app, ["setup", "--project", "my-proj"])
        assert result.exit_code == 0
        assert "my-proj" in result.output

    def test_setup_failure(self, tmp_path: Path) -> None:
        engine = _mock_engine(
            setup_result=SetupResult(
                layer="enforcement-engine",
                success=False,
                errors=("DB init failed",),
            )
        )
        app = _make_app()
        with _patch_resolve(engine, tmp_path):
            result = runner.invoke(app, ["setup"])
        assert result.exit_code == 1
        assert "failed" in result.output.lower()


# ---------------------------------------------------------------------------
# Tests: check
# ---------------------------------------------------------------------------


class TestEnforceCheck:
    def test_check_no_violations(self, tmp_path: Path) -> None:
        engine = _mock_engine(check_results=[])
        app = _make_app()
        with _patch_resolve(engine, tmp_path):
            result = runner.invoke(app, ["check"])
        assert result.exit_code == 0
        assert "no violations" in result.output.lower()

    def test_check_with_violations_warning_only(self, tmp_path: Path) -> None:
        violations = (
            Violation(
                category="security",
                rule="no-eval",
                file="src/app.py",
                line=10,
                message="eval() usage",
                severity=ViolationSeverity.WARNING,
            ),
        )
        engine = _mock_engine(
            check_results=[CheckResult(category="security", violations=violations, files_scanned=5)]
        )
        app = _make_app()
        with _patch_resolve(engine, tmp_path):
            result = runner.invoke(app, ["check"])
        # Warnings should not cause exit code 1
        assert result.exit_code == 0
        assert "security" in result.output
        assert "eval() usage" in result.output

    def test_check_with_error_violations_exits_1(self, tmp_path: Path) -> None:
        violations = (
            Violation(
                category="security",
                rule="hardcoded-secret",
                file="src/config.py",
                line=3,
                message="Hardcoded secret detected",
                severity=ViolationSeverity.ERROR,
            ),
        )
        engine = _mock_engine(
            check_results=[CheckResult(category="security", violations=violations, files_scanned=2)]
        )
        app = _make_app()
        with _patch_resolve(engine, tmp_path):
            result = runner.invoke(app, ["check"])
        assert result.exit_code == 1

    def test_check_category_filter(self, tmp_path: Path) -> None:
        sec_violation = Violation(
            category="security",
            rule="no-eval",
            file="src/a.py",
            line=1,
            message="eval",
            severity=ViolationSeverity.WARNING,
        )
        dup_violation = Violation(
            category="duplication",
            rule="dup-block",
            file="src/b.py",
            line=5,
            message="duplicate block",
            severity=ViolationSeverity.WARNING,
        )
        engine = _mock_engine(
            check_results=[
                CheckResult(category="security", violations=(sec_violation,), files_scanned=1),
                CheckResult(category="duplication", violations=(dup_violation,), files_scanned=1),
            ]
        )
        app = _make_app()
        with _patch_resolve(engine, tmp_path):
            result = runner.invoke(app, ["check", "--category", "security"])
        assert result.exit_code == 0
        assert "eval" in result.output
        assert "duplicate block" not in result.output

    def test_check_fix_flag_placeholder(self, tmp_path: Path) -> None:
        violations = (
            Violation(
                category="conventions",
                rule="naming",
                file="src/x.py",
                line=1,
                message="bad name",
                severity=ViolationSeverity.INFO,
            ),
        )
        engine = _mock_engine(
            check_results=[
                CheckResult(category="conventions", violations=violations, files_scanned=1)
            ]
        )
        app = _make_app()
        with _patch_resolve(engine, tmp_path):
            result = runner.invoke(app, ["check", "--fix"])
        assert result.exit_code == 0
        assert "not yet implemented" in result.output.lower()


# ---------------------------------------------------------------------------
# Tests: report
# ---------------------------------------------------------------------------


class TestEnforceReport:
    def test_report_empty(self, tmp_path: Path) -> None:
        engine = _mock_engine()
        app = _make_app()
        with _patch_resolve(engine, tmp_path):
            result = runner.invoke(app, ["report"])
        assert result.exit_code == 0
        assert "no enforcement data" in result.output.lower()

    def test_report_with_data(self, tmp_path: Path) -> None:
        report_obj = EnforcementReport(
            project_id="test",
            results=[
                CheckResult(category="security", files_scanned=10, duration_seconds=1.23),
                CheckResult(
                    category="duplication",
                    violations=(
                        Violation(
                            category="duplication",
                            rule="dup",
                            file="a.py",
                            message="dup",
                        ),
                    ),
                    files_scanned=8,
                    duration_seconds=0.5,
                ),
            ],
        )
        engine = _mock_engine(report=report_obj)
        app = _make_app()
        with _patch_resolve(engine, tmp_path):
            result = runner.invoke(app, ["report"])
        assert result.exit_code == 0
        assert "security" in result.output
        assert "duplication" in result.output

    def test_report_category_filter(self, tmp_path: Path) -> None:
        report_obj = EnforcementReport(
            project_id="test",
            results=[
                CheckResult(category="security", files_scanned=10),
                CheckResult(category="duplication", files_scanned=8),
            ],
        )
        engine = _mock_engine(report=report_obj)
        app = _make_app()
        with _patch_resolve(engine, tmp_path):
            result = runner.invoke(app, ["report", "--category", "security"])
        assert result.exit_code == 0
        assert "security" in result.output

    def test_report_days_option(self, tmp_path: Path) -> None:
        report_obj = EnforcementReport(
            project_id="test",
            results=[
                CheckResult(category="security", files_scanned=5, duration_seconds=0.1),
            ],
        )
        engine = _mock_engine(report=report_obj)
        app = _make_app()
        with _patch_resolve(engine, tmp_path):
            result = runner.invoke(app, ["report", "--days", "7"])
        assert result.exit_code == 0
        assert "Enforcement Report" in result.output


# ---------------------------------------------------------------------------
# Tests: update
# ---------------------------------------------------------------------------


class TestEnforceUpdate:
    def test_update_prints_message(self) -> None:
        app = _make_app()
        result = runner.invoke(app, ["update"])
        assert result.exit_code == 0
        assert "updated" in result.output.lower()
