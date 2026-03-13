"""Tests for enforcement rules Categories 4-7 (Task 058)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from autopilot.core.models import CheckResult, ViolationSeverity
from autopilot.enforcement.rules.base import EnforcementRule
from autopilot.enforcement.rules.dead_code import DeadCodeRule
from autopilot.enforcement.rules.error_handling import ErrorHandlingRule
from autopilot.enforcement.rules.security import SecurityRule
from autopilot.enforcement.rules.type_safety import TypeSafetyRule

if TYPE_CHECKING:
    from pathlib import Path


class TestSecurityRule:
    def test_satisfies_protocol(self) -> None:
        assert isinstance(SecurityRule(), EnforcementRule)

    def test_category(self) -> None:
        assert SecurityRule().category == "security"

    def test_name(self) -> None:
        assert SecurityRule().name == "security-vulnerabilities"

    def test_default_severity_is_error(self) -> None:
        rule = SecurityRule()
        assert rule._severity == ViolationSeverity.ERROR

    def test_check_empty(self) -> None:
        result = SecurityRule().check([])
        assert isinstance(result, CheckResult)
        assert result.category == "security"

    def test_clean_file(self, tmp_path: Path) -> None:
        f = tmp_path / "safe.py"
        f.write_text("x = 1\n")
        result = SecurityRule().check([f])
        assert isinstance(result, CheckResult)


class TestErrorHandlingRule:
    def test_satisfies_protocol(self) -> None:
        assert isinstance(ErrorHandlingRule(), EnforcementRule)

    def test_category(self) -> None:
        assert ErrorHandlingRule().category == "error_handling"

    def test_name(self) -> None:
        assert ErrorHandlingRule().name == "error-handling-patterns"

    def test_check_empty(self) -> None:
        result = ErrorHandlingRule().check([])
        assert isinstance(result, CheckResult)

    def test_clean_file(self, tmp_path: Path) -> None:
        f = tmp_path / "handlers.py"
        f.write_text("x = 1\n")
        result = ErrorHandlingRule().check([f])
        assert isinstance(result, CheckResult)


class TestDeadCodeRule:
    def test_satisfies_protocol(self) -> None:
        assert isinstance(DeadCodeRule(), EnforcementRule)

    def test_category(self) -> None:
        assert DeadCodeRule().category == "dead_code"

    def test_name(self) -> None:
        assert DeadCodeRule().name == "unused-code-detection"

    def test_default_severity_is_info(self) -> None:
        rule = DeadCodeRule()
        assert rule._severity == ViolationSeverity.INFO

    def test_check_empty(self) -> None:
        result = DeadCodeRule().check([])
        assert isinstance(result, CheckResult)

    def test_clean_file(self, tmp_path: Path) -> None:
        f = tmp_path / "used.py"
        f.write_text("x = 1\n")
        result = DeadCodeRule().check([f])
        assert isinstance(result, CheckResult)


class TestTypeSafetyRule:
    def test_satisfies_protocol(self) -> None:
        assert isinstance(TypeSafetyRule(), EnforcementRule)

    def test_category(self) -> None:
        assert TypeSafetyRule().category == "type_safety"

    def test_name(self) -> None:
        assert TypeSafetyRule().name == "type-annotation-checks"

    def test_check_empty(self) -> None:
        result = TypeSafetyRule().check([])
        assert isinstance(result, CheckResult)

    def test_clean_file(self, tmp_path: Path) -> None:
        f = tmp_path / "typed.py"
        f.write_text("x: int = 1\n")
        result = TypeSafetyRule().check([f])
        assert isinstance(result, CheckResult)
