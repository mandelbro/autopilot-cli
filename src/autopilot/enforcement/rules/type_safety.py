"""Category 7 enforcement rule: Type Safety.

Checks for Any abuse (ANN401), missing type annotations, and unsafe
casts using ruff ANN rule family.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autopilot.core.models import CheckResult, ViolationSeverity
from autopilot.enforcement.rules.ruff_runner import run_ruff_check

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

_RUFF_CODES = ["ANN"]


class TypeSafetyRule:
    """Enforcement rule for type safety verification.

    Satisfies the ``EnforcementRule`` protocol.
    """

    def __init__(self, *, severity: ViolationSeverity = ViolationSeverity.WARNING) -> None:
        self._severity = severity

    @property
    def category(self) -> str:
        return "type_safety"

    @property
    def name(self) -> str:
        return "type-annotation-checks"

    def check(self, files: Sequence[Path]) -> CheckResult:
        return run_ruff_check(
            files,
            select_codes=_RUFF_CODES,
            category=self.category,
            rule_name=self.name,
            severity=self._severity,
        )
