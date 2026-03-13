"""Tests for the FailureClassifier (Task 054)."""

from __future__ import annotations

import pytest

from autopilot.monitoring.failure_patterns import (
    FailureClassification,
    FailureClassifier,
    RemediationAction,
)


class TestFailureClassification:
    def test_frozen(self) -> None:
        fc = FailureClassification(
            pattern_name="test",
            matched_text="err",
            remediation=RemediationAction.EM_DISPATCH,
            confidence=0.9,
        )
        with pytest.raises(AttributeError):
            fc.pattern_name = "other"  # type: ignore[misc]


class TestRemediationAction:
    def test_values(self) -> None:
        assert RemediationAction.EM_DISPATCH == "em_dispatch"
        assert RemediationAction.HUMAN_ESCALATION == "human_escalation"
        assert RemediationAction.DA_RETRY == "da_retry"


class TestFailureClassifierBuiltins:
    def test_git_auth_expired(self) -> None:
        classifier = FailureClassifier()
        result = classifier.classify("fatal: Authentication failed for repo")
        assert result.pattern_name == "git_auth_expired"
        assert result.remediation == RemediationAction.HUMAN_ESCALATION
        assert result.confidence > 0

    def test_git_auth_403(self) -> None:
        classifier = FailureClassifier()
        result = classifier.classify("error: 403 Forbidden")
        assert result.pattern_name == "git_auth_expired"
        assert result.remediation == RemediationAction.HUMAN_ESCALATION

    def test_broken_imports(self) -> None:
        classifier = FailureClassifier()
        result = classifier.classify("ModuleNotFoundError: No module named 'foo'")
        assert result.pattern_name == "broken_imports"
        assert result.remediation == RemediationAction.EM_DISPATCH

    def test_import_error(self) -> None:
        classifier = FailureClassifier()
        result = classifier.classify("ImportError: cannot import name 'bar'")
        assert result.pattern_name == "broken_imports"
        assert result.remediation == RemediationAction.EM_DISPATCH

    def test_missing_dependency(self) -> None:
        classifier = FailureClassifier()
        result = classifier.classify("No matching distribution found for requests>=2.0")
        assert result.pattern_name == "missing_dependency"
        assert result.remediation == RemediationAction.EM_DISPATCH

    def test_crash_loop_oom(self) -> None:
        classifier = FailureClassifier()
        result = classifier.classify("Container was OOMKilled")
        assert result.pattern_name == "crash_loop"
        assert result.remediation == RemediationAction.EM_DISPATCH

    def test_crash_loop_exit_137(self) -> None:
        classifier = FailureClassifier()
        result = classifier.classify("Process exited with exit code 137")
        assert result.pattern_name == "crash_loop"

    def test_unknown_defaults_to_human_escalation(self) -> None:
        classifier = FailureClassifier()
        result = classifier.classify("Some completely novel error nobody expected")
        assert result.pattern_name == "unknown"
        assert result.remediation == RemediationAction.HUMAN_ESCALATION
        assert result.confidence == 0.0
        assert result.matched_text == ""

    def test_empty_input(self) -> None:
        classifier = FailureClassifier()
        result = classifier.classify("")
        assert result.pattern_name == "unknown"


class TestFailureClassifierCustomPatterns:
    def test_custom_pattern_match(self) -> None:
        classifier = FailureClassifier(custom_patterns={"db_timeout": r"database.*timeout"})
        result = classifier.classify("Error: database connection timeout after 30s")
        assert result.pattern_name == "db_timeout"
        assert result.remediation == RemediationAction.EM_DISPATCH
        assert result.confidence == 0.7

    def test_builtin_takes_precedence_over_custom(self) -> None:
        classifier = FailureClassifier(
            custom_patterns={"my_import": r"ImportError"}
        )
        result = classifier.classify("ImportError: no module named 'x'")
        assert result.pattern_name == "broken_imports"

    def test_custom_pattern_no_match_falls_through(self) -> None:
        classifier = FailureClassifier(custom_patterns={"nope": r"never_matches"})
        result = classifier.classify("random error text")
        assert result.pattern_name == "unknown"


class TestRouteRemediation:
    def test_routes_classification(self) -> None:
        classifier = FailureClassifier()
        classification = FailureClassification(
            pattern_name="test",
            matched_text="err",
            remediation=RemediationAction.DA_RETRY,
            confidence=0.5,
        )
        assert classifier.route_remediation(classification) == RemediationAction.DA_RETRY
