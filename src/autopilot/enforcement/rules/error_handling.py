"""Category 5 enforcement rule: Error Handling (~2x human prevalence).

Checks for bare except, swallowed errors, and missing error types using
ruff BLE (blind-except) and TRY (tryceratops) rule families.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autopilot.core.models import CheckResult, ViolationSeverity
from autopilot.enforcement.rules.ruff_runner import run_ruff_check

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

_RUFF_CODES = ["BLE", "TRY"]


class ErrorHandlingRule:
    """Enforcement rule for error handling anti-pattern detection.

    Satisfies the ``EnforcementRule`` protocol.
    """

    def __init__(
        self, *, severity: ViolationSeverity = ViolationSeverity.WARNING
    ) -> None:
        self._severity = severity

    @property
    def category(self) -> str:
        return "error_handling"

    @property
    def name(self) -> str:
        return "error-handling-patterns"

    def check(self, files: Sequence[Path]) -> CheckResult:
        return run_ruff_check(
            files,
            select_codes=_RUFF_CODES,
            category=self.category,
            rule_name=self.name,
            severity=self._severity,
        )
