"""Category 8 enforcement rule: Test Anti-Patterns (40-70% AI prevalence).

Checks for assertion-free tests, over-mocking, and test naming conventions
using ruff PT (flake8-pytest-style) rule family.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autopilot.core.models import CheckResult, ViolationSeverity
from autopilot.enforcement.rules.ruff_runner import run_ruff_check

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

_RUFF_CODES = ["PT"]


class TestQualityRule:
    """Enforcement rule for test anti-pattern detection.

    Satisfies the ``EnforcementRule`` protocol.
    """

    def __init__(self, *, severity: ViolationSeverity = ViolationSeverity.WARNING) -> None:
        self._severity = severity

    @property
    def category(self) -> str:
        return "test_quality"

    @property
    def name(self) -> str:
        return "test-anti-patterns"

    def check(self, files: Sequence[Path]) -> CheckResult:
        return run_ruff_check(
            files,
            select_codes=_RUFF_CODES,
            category=self.category,
            rule_name=self.name,
            severity=self._severity,
        )
