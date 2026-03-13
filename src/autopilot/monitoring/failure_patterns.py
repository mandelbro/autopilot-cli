"""Failure pattern classification and remediation routing (Task 054).

Classifies deployment failures based on error output patterns and routes
them to appropriate remediation actions (EM dispatch, human escalation,
or DA retry).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum


class RemediationAction(StrEnum):
    """Possible remediation actions for classified failures."""

    EM_DISPATCH = "em_dispatch"
    HUMAN_ESCALATION = "human_escalation"
    DA_RETRY = "da_retry"


@dataclass(frozen=True)
class FailurePattern:
    """A known failure pattern with classification metadata."""

    name: str
    regex_patterns: tuple[str, ...] = ()
    remediation: RemediationAction = RemediationAction.HUMAN_ESCALATION
    severity: str = "high"


@dataclass(frozen=True)
class FailureClassification:
    """Result of classifying an error output."""

    pattern_name: str
    matched_text: str
    remediation: RemediationAction
    confidence: float


# Built-in failure pattern catalog
_BUILTIN_PATTERNS: tuple[FailurePattern, ...] = (
    FailurePattern(
        name="git_auth_expired",
        regex_patterns=(
            r"(?i)authentication failed",
            r"(?i)403 forbidden",
            r"(?i)could not read.*credentials",
            r"(?i)permission denied.*publickey",
        ),
        remediation=RemediationAction.HUMAN_ESCALATION,
        severity="critical",
    ),
    FailurePattern(
        name="broken_imports",
        regex_patterns=(
            r"ModuleNotFoundError",
            r"ImportError",
            r"(?i)cannot import name",
        ),
        remediation=RemediationAction.EM_DISPATCH,
        severity="high",
    ),
    FailurePattern(
        name="missing_dependency",
        regex_patterns=(
            r"(?i)no matching distribution",
            r"(?i)could not find a version",
            r"(?i)package .+ not found",
            r"(?i)requirements? .+ not satisfied",
        ),
        remediation=RemediationAction.EM_DISPATCH,
        severity="high",
    ),
    FailurePattern(
        name="crash_loop",
        regex_patterns=(
            r"(?i)oomkilled",
            r"(?i)exit code 137",
            r"(?i)segmentation fault",
            r"(?i)killed.*signal",
        ),
        remediation=RemediationAction.EM_DISPATCH,
        severity="critical",
    ),
)


@dataclass
class FailureClassifier:
    """Classifies deployment failure error output into known patterns.

    Combines built-in patterns with optional custom patterns loaded
    from project configuration.

    Args:
        custom_patterns: Extra pattern name -> regex mapping from config.
    """

    custom_patterns: dict[str, str] = field(default_factory=dict)

    def classify(self, error_output: str) -> FailureClassification:
        """Classify error output against known failure patterns.

        Returns the first matching pattern, or an "unknown" classification
        with human_escalation remediation if nothing matches.
        """
        for pattern in _BUILTIN_PATTERNS:
            matched = self._match_pattern(error_output, pattern.regex_patterns)
            if matched:
                return FailureClassification(
                    pattern_name=pattern.name,
                    matched_text=matched,
                    remediation=pattern.remediation,
                    confidence=0.9,
                )

        for name, regex in self.custom_patterns.items():
            match = re.search(regex, error_output)
            if match:
                return FailureClassification(
                    pattern_name=name,
                    matched_text=match.group(0),
                    remediation=RemediationAction.EM_DISPATCH,
                    confidence=0.7,
                )

        return FailureClassification(
            pattern_name="unknown",
            matched_text="",
            remediation=RemediationAction.HUMAN_ESCALATION,
            confidence=0.0,
        )

    def route_remediation(
        self, classification: FailureClassification
    ) -> RemediationAction:
        """Return the remediation action for a classification."""
        return classification.remediation

    @staticmethod
    def _match_pattern(
        text: str, patterns: tuple[str, ...]
    ) -> str:
        """Try each regex in *patterns* against *text*, return first match or ""."""
        for regex in patterns:
            match = re.search(regex, text)
            if match:
                return match.group(0)
        return ""
