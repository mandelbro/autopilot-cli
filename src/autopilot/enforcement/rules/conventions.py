"""Category 2 enforcement rule: Ignored Conventions (90-100% AI prevalence).

Checks naming conventions, import ordering, and file organization
using ruff I (isort) and N (pep8-naming) rule families.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autopilot.core.models import CheckResult, ViolationSeverity
from autopilot.enforcement.rules.ruff_runner import run_ruff_check

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

_RUFF_CODES = ["I", "N"]


class ConventionsRule:
    """Enforcement rule for naming and import convention violations.

    Satisfies the ``EnforcementRule`` protocol.
    """

    def __init__(
        self, *, severity: ViolationSeverity = ViolationSeverity.WARNING
    ) -> None:
        self._severity = severity

    @property
    def category(self) -> str:
        return "conventions"

    @property
    def name(self) -> str:
        return "naming-import-conventions"

    def check(self, files: Sequence[Path]) -> CheckResult:
        return run_ruff_check(
            files,
            select_codes=_RUFF_CODES,
            category=self.category,
            rule_name=self.name,
            severity=self._severity,
        )
