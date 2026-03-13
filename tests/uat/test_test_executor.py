"""Tests for UAT test executor."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from autopilot.uat.test_executor import (
    CategoryBreakdown,
    TestExecutor,
    TestFailure,
    UATResult,
    _classify_test,
)

# ---------------------------------------------------------------------------
# Data model tests
# ---------------------------------------------------------------------------


class TestUATResult:
    def test_frozen(self) -> None:
        r = UATResult()
        with pytest.raises(AttributeError):
            r.score = 0.5  # type: ignore[misc]

    def test_defaults(self) -> None:
        r = UATResult()
        assert r.overall_pass is False
        assert r.score == 0.0
        assert r.test_count == 0
        assert r.categories == []
        assert r.failures == []


class TestTestFailure:
    def test_frozen(self) -> None:
        f = TestFailure(test_name="test_x")
        with pytest.raises(AttributeError):
            f.test_name = "test_y"  # type: ignore[misc]

    def test_defaults(self) -> None:
        f = TestFailure(test_name="test_x")
        assert f.category == "acceptance"
        assert f.spec_reference == ""


class TestCategoryBreakdown:
    def test_frozen(self) -> None:
        c = CategoryBreakdown(category="acceptance")
        with pytest.raises(AttributeError):
            c.total = 5  # type: ignore[misc]

    def test_defaults(self) -> None:
        c = CategoryBreakdown(category="acceptance")
        assert c.total == 0
        assert c.passed == 0


# ---------------------------------------------------------------------------
# Helper tests
# ---------------------------------------------------------------------------


class TestClassifyTest:
    def test_acceptance_keyword(self) -> None:
        assert _classify_test("test_acceptance_login") == "acceptance"

    def test_behavioral_keyword(self) -> None:
        assert _classify_test("test_workflow_execution") == "behavioral"

    def test_compliance_keyword(self) -> None:
        assert _classify_test("test_rfc_compliance") == "compliance"

    def test_ux_keyword(self) -> None:
        assert _classify_test("test_display_output") == "ux"

    def test_default_is_acceptance(self) -> None:
        assert _classify_test("test_something_else") == "acceptance"


# ---------------------------------------------------------------------------
# TestExecutor tests
# ---------------------------------------------------------------------------


class TestTestExecutor:
    @pytest.fixture()
    def executor(self) -> TestExecutor:
        return TestExecutor(timeout=30)

    def test_missing_file_returns_result(self, executor: TestExecutor, tmp_path: Path) -> None:
        result = executor.run(tmp_path / "nonexistent.py")
        assert result.overall_pass is False
        assert "not found" in result.raw_output

    def test_run_passing_tests(self, executor: TestExecutor, tmp_path: Path) -> None:
        test_file = tmp_path / "test_pass.py"
        test_file.write_text(
            "def test_ok():\n    assert True\n",
            encoding="utf-8",
        )
        result = executor.run(test_file)
        # Should have at least parsed something
        assert isinstance(result, UATResult)
        assert result.raw_output != ""

    def test_run_failing_tests(self, executor: TestExecutor, tmp_path: Path) -> None:
        test_file = tmp_path / "test_fail.py"
        test_file.write_text(
            "def test_bad():\n    assert False\n",
            encoding="utf-8",
        )
        result = executor.run(test_file)
        assert isinstance(result, UATResult)

    def test_timeout_handling(self, tmp_path: Path) -> None:
        executor = TestExecutor(timeout=1)
        test_file = tmp_path / "test_slow.py"
        test_file.write_text(
            "import time\ndef test_slow():\n    time.sleep(10)\n",
            encoding="utf-8",
        )
        result = executor.run(test_file)
        assert isinstance(result, UATResult)

    def test_parse_stdout_fallback(self, executor: TestExecutor) -> None:
        raw = "3 passed, 1 failed, 2 skipped in 0.5s"
        result = executor._parse_stdout(raw)
        assert result.passed == 3
        assert result.failed == 1
        assert result.skipped == 2
        assert result.test_count == 6
        assert result.score == 0.5

    def test_parse_stdout_all_passed(self, executor: TestExecutor) -> None:
        raw = "5 passed in 0.3s"
        result = executor._parse_stdout(raw)
        assert result.passed == 5
        assert result.overall_pass is True
        assert result.score == 1.0

    def test_parse_stdout_empty(self, executor: TestExecutor) -> None:
        result = executor._parse_stdout("")
        assert result.test_count == 0
        assert result.score == 0.0
