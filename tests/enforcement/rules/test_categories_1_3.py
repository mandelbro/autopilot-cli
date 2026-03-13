"""Tests for enforcement rules Categories 1-3 (Task 057).

Category 1 (Duplication) is tested in test_duplication.py.
This file tests Categories 2 (Conventions) and 3 (Over-engineering).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autopilot.core.models import CheckResult, ViolationSeverity
from autopilot.enforcement.rules.base import EnforcementRule
from autopilot.enforcement.rules.conventions import ConventionsRule
from autopilot.enforcement.rules.overengineering import OverengineeringRule

if TYPE_CHECKING:
    from pathlib import Path


class TestConventionsRuleProtocol:
    def test_satisfies_protocol(self) -> None:
        rule = ConventionsRule()
        assert isinstance(rule, EnforcementRule)

    def test_category(self) -> None:
        assert ConventionsRule().category == "conventions"

    def test_name(self) -> None:
        assert ConventionsRule().name == "naming-import-conventions"

    def test_check_returns_check_result(self) -> None:
        result = ConventionsRule().check([])
        assert isinstance(result, CheckResult)
        assert result.category == "conventions"

    def test_custom_severity(self) -> None:
        rule = ConventionsRule(severity=ViolationSeverity.ERROR)
        assert rule._severity == ViolationSeverity.ERROR


class TestConventionsRuleWithRuff:
    def test_empty_file_list(self) -> None:
        result = ConventionsRule().check([])
        assert len(result.violations) == 0
        assert result.files_scanned == 0

    def test_nonexistent_file_skipped(self, tmp_path: Path) -> None:
        result = ConventionsRule().check([tmp_path / "missing.py"])
        assert len(result.violations) == 0

    def test_clean_file(self, tmp_path: Path) -> None:
        f = tmp_path / "clean.py"
        f.write_text("x = 1\n")
        result = ConventionsRule().check([f])
        assert isinstance(result, CheckResult)


class TestOverengineeringRuleProtocol:
    def test_satisfies_protocol(self) -> None:
        rule = OverengineeringRule()
        assert isinstance(rule, EnforcementRule)

    def test_category(self) -> None:
        assert OverengineeringRule().category == "overengineering"

    def test_name(self) -> None:
        assert OverengineeringRule().name == "complexity-simplification"

    def test_check_returns_check_result(self) -> None:
        result = OverengineeringRule().check([])
        assert isinstance(result, CheckResult)
        assert result.category == "overengineering"


class TestOverengineeringRuleWithRuff:
    def test_empty_file_list(self) -> None:
        result = OverengineeringRule().check([])
        assert len(result.violations) == 0

    def test_clean_file(self, tmp_path: Path) -> None:
        f = tmp_path / "simple.py"
        f.write_text("def add(a: int, b: int) -> int:\n    return a + b\n")
        result = OverengineeringRule().check([f])
        assert isinstance(result, CheckResult)
