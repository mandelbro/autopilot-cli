"""Category 4 enforcement rule: Security (36-62% AI prevalence).

Checks for hardcoded secrets, credential patterns, and unsafe subprocess
usage using ruff S (flake8-bandit) rule family.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autopilot.core.models import CheckResult, ViolationSeverity
from autopilot.enforcement.rules.ruff_runner import run_ruff_check

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

_RUFF_CODES = ["S"]


class SecurityRule:
    """Enforcement rule for security vulnerability detection.

    Satisfies the ``EnforcementRule`` protocol.
    """

    def __init__(
        self, *, severity: ViolationSeverity = ViolationSeverity.ERROR
    ) -> None:
        self._severity = severity

    @property
    def category(self) -> str:
        return "security"

    @property
    def name(self) -> str:
        return "security-vulnerabilities"

    def check(self, files: Sequence[Path]) -> CheckResult:
        return run_ruff_check(
            files,
            select_codes=_RUFF_CODES,
            category=self.category,
            rule_name=self.name,
            severity=self._severity,
        )
