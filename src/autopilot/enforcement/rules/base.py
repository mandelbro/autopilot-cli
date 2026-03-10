"""Base protocol and configuration for enforcement rules.

All enforcement rules must implement the EnforcementRule protocol so that the
enforcement engine (Task 056) can discover and invoke them uniformly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from autopilot.core.models import CheckResult, ViolationSeverity


class RuleConfig(BaseModel):
    """Shared configuration for enforcement rules.

    Attributes:
        min_lines: Minimum block length (in lines) to consider for analysis.
        similarity_threshold: Minimum structural similarity ratio [0.0, 1.0]
            required before a pair is flagged as duplicate.
        severity: Default violation severity emitted by the rule.
    """

    model_config = ConfigDict(frozen=True)

    min_lines: int = Field(default=6, gt=0, description="Minimum lines to analyse")
    similarity_threshold: float = Field(
        default=0.80,
        ge=0.0,
        le=1.0,
        description="Structural similarity ratio threshold",
    )
    severity: ViolationSeverity = Field(
        default=ViolationSeverity.WARNING,
        description="Severity level for emitted violations",
    )

    @field_validator("similarity_threshold")
    @classmethod
    def _validate_threshold(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            msg = f"similarity_threshold must be in [0.0, 1.0], got {v}"
            raise ValueError(msg)
        return v


@runtime_checkable
class EnforcementRule(Protocol):
    """Protocol that every enforcement rule must satisfy.

    The enforcement engine (Task 056) loads rules by checking isinstance(obj,
    EnforcementRule), so this protocol is marked @runtime_checkable.
    """

    @property
    def category(self) -> str:
        """Enforcement category (e.g. 'duplication', 'conventions')."""
        ...

    @property
    def name(self) -> str:
        """Unique rule identifier within its category."""
        ...

    def check(self, files: Sequence[Path]) -> CheckResult:
        """Analyse the given files and return a CheckResult.

        Args:
            files: Source files to analyse.  Non-existent or unparseable
                files must be silently skipped.

        Returns:
            A CheckResult whose ``category`` matches ``self.category``.
        """
        ...
