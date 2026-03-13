"""UAT test executor.

Runs generated pytest test files and collects structured results with
pass/fail/skip counts, category breakdowns, and failure details.
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path  # noqa: TC003 — used at runtime

import structlog

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

# Category keywords used to classify test names
_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "acceptance": ["acceptance", "ac_", "criterion", "criteria"],
    "behavioral": ["behavior", "behaviour", "workflow", "flow", "process"],
    "compliance": ["compliance", "spec", "rfc", "standard", "requirement"],
    "ux": ["ux", "display", "render", "layout", "ui", "visual"],
}


@dataclass(frozen=True)
class TestFailure:
    """Details about a single test failure."""

    test_name: str
    category: str = "acceptance"
    spec_reference: str = ""
    expected: str = ""
    actual: str = ""
    suggestion: str = ""


@dataclass(frozen=True)
class CategoryBreakdown:
    """Pass/fail/skip counts for a single test category."""

    category: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0


@dataclass(frozen=True)
class UATResult:
    """Aggregated result from a UAT test run."""

    overall_pass: bool = False
    score: float = 0.0
    test_count: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    categories: list[CategoryBreakdown] = field(default_factory=list)
    failures: list[TestFailure] = field(default_factory=list)
    raw_output: str = ""


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------


def _classify_test(test_name: str) -> str:
    """Classify a test into a category based on its name."""
    lower = test_name.lower()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return category
    return "acceptance"


class TestExecutor:
    """Executes pytest test files and collects UAT results."""

    def __init__(self, *, timeout: int = 300) -> None:
        self._timeout = timeout

    def run(self, test_file: Path) -> UATResult:
        """Execute a pytest test file and return structured results.

        Uses ``pytest --tb=short -q`` with JSON report output for
        machine-readable result parsing.
        """
        if not test_file.exists():
            logger.warning("test_file_not_found", path=str(test_file))
            return UATResult(raw_output=f"Test file not found: {test_file}")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            json_path = Path(tmp.name)

        try:
            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "pytest",
                    str(test_file),
                    f"--json-report-file={json_path}",
                    "--json-report",
                    "--tb=short",
                    "-q",
                    "--no-header",
                ],
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
            raw_output = result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            logger.warning("test_timeout", path=str(test_file), timeout=self._timeout)
            return UATResult(raw_output=f"Test execution timed out after {self._timeout}s")
        except FileNotFoundError:
            # uv not available, try plain pytest
            try:
                result = subprocess.run(
                    [
                        "python",
                        "-m",
                        "pytest",
                        str(test_file),
                        f"--json-report-file={json_path}",
                        "--json-report",
                        "--tb=short",
                        "-q",
                        "--no-header",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=self._timeout,
                )
                raw_output = result.stdout + result.stderr
            except (subprocess.TimeoutExpired, FileNotFoundError):
                return UATResult(raw_output="Could not execute pytest")

        # Parse JSON report if available
        if json_path.exists():
            try:
                return self._parse_json_report(json_path, raw_output)
            except (json.JSONDecodeError, KeyError):
                logger.warning("json_report_parse_failed", path=str(json_path))
            finally:
                json_path.unlink(missing_ok=True)

        # Fallback: parse stdout
        return self._parse_stdout(raw_output)

    def _parse_json_report(self, json_path: Path, raw_output: str) -> UATResult:
        """Parse pytest-json-report output into UATResult."""
        data = json.loads(json_path.read_text(encoding="utf-8"))
        tests = data.get("tests", [])

        passed = 0
        failed = 0
        skipped = 0
        failures: list[TestFailure] = []
        category_counts: dict[str, dict[str, int]] = {}

        for test in tests:
            nodeid = test.get("nodeid", "")
            test_name = nodeid.split("::")[-1] if "::" in nodeid else nodeid
            outcome = test.get("outcome", "")
            category = _classify_test(test_name)

            if category not in category_counts:
                category_counts[category] = {"total": 0, "passed": 0, "failed": 0, "skipped": 0}
            category_counts[category]["total"] += 1

            if outcome == "passed":
                passed += 1
                category_counts[category]["passed"] += 1
            elif outcome == "failed":
                failed += 1
                category_counts[category]["failed"] += 1
                # Extract failure details
                call_info = test.get("call", {})
                longrepr = call_info.get("longrepr", "")
                failures.append(
                    TestFailure(
                        test_name=test_name,
                        category=category,
                        actual=str(longrepr)[:500] if longrepr else "",
                        suggestion="Review the failing acceptance criterion.",
                    )
                )
            else:
                skipped += 1
                category_counts[category]["skipped"] += 1

        total = passed + failed + skipped
        score = round(passed / total, 2) if total > 0 else 0.0
        overall_pass = failed == 0 and total > 0

        categories = [
            CategoryBreakdown(category=cat, **counts)
            for cat, counts in sorted(category_counts.items())
        ]

        return UATResult(
            overall_pass=overall_pass,
            score=score,
            test_count=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            categories=categories,
            failures=failures,
            raw_output=raw_output,
        )

    def _parse_stdout(self, raw_output: str) -> UATResult:
        """Fallback parser that extracts counts from pytest stdout."""
        passed = failed = skipped = 0
        for line in raw_output.split("\n"):
            lower = line.lower()
            if "passed" in lower or "failed" in lower or "skipped" in lower:
                for m in re.finditer(r"(\d+)\s+(passed|failed|skipped)", lower):
                    count = int(m.group(1))
                    kind = m.group(2)
                    if kind == "passed":
                        passed = count
                    elif kind == "failed":
                        failed = count
                    elif kind == "skipped":
                        skipped = count

        total = passed + failed + skipped
        score = round(passed / total, 2) if total > 0 else 0.0

        return UATResult(
            overall_pass=failed == 0 and total > 0,
            score=score,
            test_count=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            raw_output=raw_output,
        )
