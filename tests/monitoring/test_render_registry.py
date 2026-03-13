"""Tests for the GitHubIssueCreator (Task 055)."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

from autopilot.monitoring.failure_patterns import (
    FailureClassification,
    RemediationAction,
)
from autopilot.monitoring.render_registry import (
    GitHubIssueCreator,
    IssueContext,
)


def _make_failure(
    pattern: str = "broken_imports",
    remediation: RemediationAction = RemediationAction.EM_DISPATCH,
) -> FailureClassification:
    return FailureClassification(
        pattern_name=pattern,
        matched_text="ImportError",
        remediation=remediation,
        confidence=0.9,
    )


def _make_context(service: str = "api") -> IssueContext:
    return IssueContext(
        service_name=service,
        error_output="ImportError: no module named foo",
        recent_commits="abc1234 fix: stuff",
        deploy_timestamp="2026-03-13T00:00:00Z",
        remediation_suggestion="Fix the imports",
    )


def _gh_result(
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=["gh"], returncode=returncode, stdout=stdout, stderr=stderr
    )


class TestGitHubIssueCreator:
    def test_creates_issue_on_success(self) -> None:
        creator = GitHubIssueCreator()

        with patch.object(creator, "_run_gh") as mock_gh:
            # First call: duplicate check returns empty list
            # Second call: issue create returns URL
            mock_gh.side_effect = [
                _gh_result(stdout="[]"),
                _gh_result(stdout="https://github.com/org/repo/issues/42\n"),
            ]
            url = creator.create_deploy_failure_issue(_make_failure(), _make_context())

        assert url == "https://github.com/org/repo/issues/42"
        assert mock_gh.call_count == 2

    def test_skips_duplicate_issue(self) -> None:
        creator = GitHubIssueCreator()

        with patch.object(creator, "_run_gh") as mock_gh:
            mock_gh.return_value = _gh_result(stdout='[{"number": 10}]')
            url = creator.create_deploy_failure_issue(_make_failure(), _make_context())

        assert url == ""
        assert mock_gh.call_count == 1

    def test_returns_empty_on_create_failure(self) -> None:
        creator = GitHubIssueCreator()

        with patch.object(creator, "_run_gh") as mock_gh:
            mock_gh.side_effect = [
                _gh_result(stdout="[]"),
                _gh_result(returncode=1, stderr="gh: not authenticated"),
            ]
            url = creator.create_deploy_failure_issue(_make_failure(), _make_context())

        assert url == ""

    def test_duplicate_check_failure_allows_creation(self) -> None:
        creator = GitHubIssueCreator()

        with patch.object(creator, "_run_gh") as mock_gh:
            mock_gh.side_effect = [
                _gh_result(returncode=1),
                _gh_result(stdout="https://github.com/org/repo/issues/99\n"),
            ]
            url = creator.create_deploy_failure_issue(_make_failure(), _make_context())

        assert url == "https://github.com/org/repo/issues/99"

    def test_custom_labels(self) -> None:
        creator = GitHubIssueCreator(labels=["urgent", "deploy"])

        with patch.object(creator, "_run_gh") as mock_gh:
            mock_gh.side_effect = [
                _gh_result(stdout="[]"),
                _gh_result(stdout="https://github.com/org/repo/issues/1\n"),
            ]
            creator.create_deploy_failure_issue(_make_failure(), _make_context())

        create_call = mock_gh.call_args_list[1]
        args = create_call[0]
        label_idx = list(args).index("--label")
        assert args[label_idx + 1] == "urgent,deploy"


class TestIssueBody:
    def test_body_contains_service_name(self) -> None:
        body = GitHubIssueCreator._build_body(_make_failure(), _make_context("web-api"))
        assert "web-api" in body

    def test_body_contains_failure_type(self) -> None:
        body = GitHubIssueCreator._build_body(_make_failure("crash_loop"), _make_context())
        assert "crash_loop" in body

    def test_body_contains_error_output(self) -> None:
        ctx = _make_context()
        body = GitHubIssueCreator._build_body(_make_failure(), ctx)
        assert "ImportError" in body

    def test_body_contains_commits(self) -> None:
        ctx = _make_context()
        body = GitHubIssueCreator._build_body(_make_failure(), ctx)
        assert "abc1234" in body

    def test_body_handles_empty_context(self) -> None:
        ctx = IssueContext(service_name="svc")
        body = GitHubIssueCreator._build_body(_make_failure(), ctx)
        assert "svc" in body
        assert "No error output" in body
