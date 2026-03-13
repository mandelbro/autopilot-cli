"""Category 11 enforcement rule: Async Misuse (2x human prevalence).

Detects async function misuse, blocking calls in async, and unawaited
coroutines using ruff ASYNC rule family.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autopilot.core.models import CheckResult, ViolationSeverity
from autopilot.enforcement.rules.ruff_runner import run_ruff_check

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

_RUFF_CODES = ["ASYNC"]


class AsyncMisuseRule:
    """Enforcement rule for async misuse detection.

    Satisfies the ``EnforcementRule`` protocol.
    """

    def __init__(
        self, *, severity: ViolationSeverity = ViolationSeverity.WARNING
    ) -> None:
        self._severity = severity

    @property
    def category(self) -> str:
        return "async_misuse"

    @property
    def name(self) -> str:
        return "async-misuse-detection"

    def check(self, files: Sequence[Path]) -> CheckResult:
        return run_ruff_check(
            files,
            select_codes=_RUFF_CODES,
            category=self.category,
            rule_name=self.name,
            severity=self._severity,
        )
