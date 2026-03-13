"""Category 10 enforcement rule: Deprecated API Usage.

Checks for deprecated API usage and outdated patterns using ruff
TID251 (banned-api) and UP (pyupgrade) rule families.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autopilot.core.models import CheckResult, ViolationSeverity
from autopilot.enforcement.rules.ruff_runner import run_ruff_check

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

_RUFF_CODES = ["UP"]


class DeprecatedRule:
    """Enforcement rule for deprecated API detection.

    Satisfies the ``EnforcementRule`` protocol.
    """

    def __init__(self, *, severity: ViolationSeverity = ViolationSeverity.WARNING) -> None:
        self._severity = severity

    @property
    def category(self) -> str:
        return "deprecated"

    @property
    def name(self) -> str:
        return "deprecated-api-usage"

    def check(self, files: Sequence[Path]) -> CheckResult:
        return run_ruff_check(
            files,
            select_codes=_RUFF_CODES,
            category=self.category,
            rule_name=self.name,
            severity=self._severity,
        )
