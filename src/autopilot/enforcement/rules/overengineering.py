"""Category 3 enforcement rule: Over-engineering (80-90% AI prevalence).

Checks cyclomatic complexity and unnecessary abstractions using ruff
C901 (complexity) and SIM (simplification) rule families.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autopilot.core.models import CheckResult, ViolationSeverity
from autopilot.enforcement.rules.ruff_runner import run_ruff_check

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

_RUFF_CODES = ["C901", "SIM"]


class OverengineeringRule:
    """Enforcement rule for over-engineering detection.

    Satisfies the ``EnforcementRule`` protocol.
    """

    def __init__(
        self, *, severity: ViolationSeverity = ViolationSeverity.WARNING
    ) -> None:
        self._severity = severity

    @property
    def category(self) -> str:
        return "overengineering"

    @property
    def name(self) -> str:
        return "complexity-simplification"

    def check(self, files: Sequence[Path]) -> CheckResult:
        return run_ruff_check(
            files,
            select_codes=_RUFF_CODES,
            category=self.category,
            rule_name=self.name,
            severity=self._severity,
        )
