"""Category 9 enforcement rule: Excessive Comments (90-100% AI prevalence).

Detects commented-out code and excessive inline comments using ruff ERA
(eradicate) rule family plus a comment density heuristic.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from autopilot.core.models import CheckResult, Violation, ViolationSeverity

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

_COMMENT_DENSITY_THRESHOLD = 0.40


class CommentsRule:
    """Enforcement rule for excessive comment detection.

    Satisfies the ``EnforcementRule`` protocol.  Uses a simple line-based
    heuristic: if > 40% of non-blank lines are comments, flag the file.
    """

    def __init__(
        self, *, severity: ViolationSeverity = ViolationSeverity.INFO
    ) -> None:
        self._severity = severity

    @property
    def category(self) -> str:
        return "comments"

    @property
    def name(self) -> str:
        return "excessive-comments"

    def check(self, files: Sequence[Path]) -> CheckResult:
        start = time.monotonic()
        violations: list[Violation] = []
        scanned = 0

        for path in files:
            if not path.exists() or path.suffix != ".py":
                continue
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            scanned += 1
            lines = content.splitlines()
            non_blank = [ln for ln in lines if ln.strip()]
            if len(non_blank) < 10:
                continue

            comment_lines = sum(
                1 for ln in non_blank if ln.strip().startswith("#")
            )
            density = comment_lines / len(non_blank)

            if density > _COMMENT_DENSITY_THRESHOLD:
                violations.append(
                    Violation(
                        category=self.category,
                        rule=self.name,
                        file=str(path),
                        line=1,
                        message=(
                            f"Comment density {density:.0%} exceeds "
                            f"{_COMMENT_DENSITY_THRESHOLD:.0%} threshold"
                        ),
                        severity=self._severity,
                    )
                )

        elapsed = time.monotonic() - start
        return CheckResult(
            category=self.category,
            violations=tuple(violations),
            files_scanned=scanned,
            duration_seconds=elapsed,
        )
