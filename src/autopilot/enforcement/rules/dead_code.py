"""Category 6 enforcement rule: Dead Code.

Detects unused imports (F401), unused variables (F841), and commented-out
code (ERA001) using ruff F and ERA rule families.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autopilot.core.models import CheckResult, ViolationSeverity
from autopilot.enforcement.rules.ruff_runner import run_ruff_check

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

_RUFF_CODES = ["F401", "F841", "ERA"]


class DeadCodeRule:
    """Enforcement rule for dead code detection.

    Satisfies the ``EnforcementRule`` protocol.
    """

    def __init__(
        self, *, severity: ViolationSeverity = ViolationSeverity.INFO
    ) -> None:
        self._severity = severity

    @property
    def category(self) -> str:
        return "dead_code"

    @property
    def name(self) -> str:
        return "unused-code-detection"

    def check(self, files: Sequence[Path]) -> CheckResult:
        return run_ruff_check(
            files,
            select_codes=_RUFF_CODES,
            category=self.category,
            rule_name=self.name,
            severity=self._severity,
        )
