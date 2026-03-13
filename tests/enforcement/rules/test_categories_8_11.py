"""Tests for enforcement rules Categories 8-11 (Task 059)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from autopilot.core.models import CheckResult, ViolationSeverity
from autopilot.enforcement.rules.async_misuse import AsyncMisuseRule
from autopilot.enforcement.rules.base import EnforcementRule
from autopilot.enforcement.rules.comments import CommentsRule
from autopilot.enforcement.rules.deprecated import DeprecatedRule
from autopilot.enforcement.rules.test_quality import TestQualityRule

if TYPE_CHECKING:
    from pathlib import Path


class TestTestQualityRule:
    def test_satisfies_protocol(self) -> None:
        assert isinstance(TestQualityRule(), EnforcementRule)

    def test_category(self) -> None:
        assert TestQualityRule().category == "test_quality"

    def test_name(self) -> None:
        assert TestQualityRule().name == "test-anti-patterns"

    def test_check_empty(self) -> None:
        result = TestQualityRule().check([])
        assert isinstance(result, CheckResult)
        assert result.category == "test_quality"

    def test_clean_file(self, tmp_path: Path) -> None:
        f = tmp_path / "test_example.py"
        f.write_text("def test_add() -> None:\n    assert 1 + 1 == 2\n")
        result = TestQualityRule().check([f])
        assert isinstance(result, CheckResult)


class TestCommentsRule:
    def test_satisfies_protocol(self) -> None:
        assert isinstance(CommentsRule(), EnforcementRule)

    def test_category(self) -> None:
        assert CommentsRule().category == "comments"

    def test_name(self) -> None:
        assert CommentsRule().name == "excessive-comments"

    def test_default_severity_is_info(self) -> None:
        assert CommentsRule()._severity == ViolationSeverity.INFO

    def test_check_empty(self) -> None:
        result = CommentsRule().check([])
        assert isinstance(result, CheckResult)
        assert result.category == "comments"

    def test_normal_file_no_violations(self, tmp_path: Path) -> None:
        f = tmp_path / "normal.py"
        lines = ["x = 1\n"] * 20
        f.write_text("".join(lines))
        result = CommentsRule().check([f])
        assert len(result.violations) == 0

    def test_heavily_commented_file_flagged(self, tmp_path: Path) -> None:
        f = tmp_path / "comments.py"
        lines = ["# This is a comment\n"] * 15 + ["x = 1\n"] * 5
        f.write_text("".join(lines))
        result = CommentsRule().check([f])
        assert len(result.violations) >= 1
        assert "density" in result.violations[0].message.lower()

    def test_short_file_not_flagged(self, tmp_path: Path) -> None:
        f = tmp_path / "short.py"
        f.write_text("# comment\nx = 1\n")
        result = CommentsRule().check([f])
        assert len(result.violations) == 0

    def test_non_python_skipped(self, tmp_path: Path) -> None:
        f = tmp_path / "readme.md"
        f.write_text("# All comments\n" * 20)
        result = CommentsRule().check([f])
        assert result.files_scanned == 0


class TestDeprecatedRule:
    def test_satisfies_protocol(self) -> None:
        assert isinstance(DeprecatedRule(), EnforcementRule)

    def test_category(self) -> None:
        assert DeprecatedRule().category == "deprecated"

    def test_name(self) -> None:
        assert DeprecatedRule().name == "deprecated-api-usage"

    def test_check_empty(self) -> None:
        result = DeprecatedRule().check([])
        assert isinstance(result, CheckResult)

    def test_clean_file(self, tmp_path: Path) -> None:
        f = tmp_path / "modern.py"
        f.write_text("x = 1\n")
        result = DeprecatedRule().check([f])
        assert isinstance(result, CheckResult)


class TestAsyncMisuseRule:
    def test_satisfies_protocol(self) -> None:
        assert isinstance(AsyncMisuseRule(), EnforcementRule)

    def test_category(self) -> None:
        assert AsyncMisuseRule().category == "async_misuse"

    def test_name(self) -> None:
        assert AsyncMisuseRule().name == "async-misuse-detection"

    def test_check_empty(self) -> None:
        result = AsyncMisuseRule().check([])
        assert isinstance(result, CheckResult)
        assert result.category == "async_misuse"

    def test_clean_file(self, tmp_path: Path) -> None:
        f = tmp_path / "async_ok.py"
        f.write_text("import asyncio\n\nasync def main() -> None:\n    await asyncio.sleep(0)\n")
        result = AsyncMisuseRule().check([f])
        assert isinstance(result, CheckResult)
