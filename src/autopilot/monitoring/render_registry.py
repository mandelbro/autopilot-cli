"""GitHub issue creation for deploy failures (Task 055).

Creates structured GitHub issues via the ``gh`` CLI when deployment
failures are detected, with deduplication to avoid flooding.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from autopilot.monitoring.failure_patterns import FailureClassification


@dataclass
class IssueContext:
    """Diagnostic context attached to a deploy failure issue."""

    service_name: str = ""
    error_output: str = ""
    recent_commits: str = ""
    deploy_timestamp: str = ""
    remediation_suggestion: str = ""


@dataclass
class GitHubIssueCreator:
    """Creates and deduplicates GitHub issues for deploy failures.

    Args:
        labels: Labels to apply to created issues.
        cwd: Working directory for ``gh`` commands.
    """

    labels: list[str] = field(default_factory=lambda: ["deploy-failure", "autopilot"])
    cwd: Path | None = None
    _runner: object | None = field(default=None, repr=False)

    def create_deploy_failure_issue(
        self,
        failure: FailureClassification,
        context: IssueContext,
    ) -> str:
        """Create a GitHub issue for a deploy failure.

        Returns the issue URL on success, or an empty string if a
        duplicate issue already exists or creation fails.
        """
        if self._has_duplicate(failure.pattern_name, context.service_name):
            return ""

        title = f"Deploy failure: {context.service_name} — {failure.pattern_name}"
        body = self._build_body(failure, context)
        label_str = ",".join(self.labels)

        result = self._run_gh(
            "issue",
            "create",
            "--title",
            title,
            "--body",
            body,
            "--label",
            label_str,
        )
        if result.returncode != 0:
            return ""

        return result.stdout.strip()

    def _has_duplicate(self, pattern_name: str, service_name: str) -> bool:
        """Check for an existing open issue with the same failure pattern."""
        search_query = f"Deploy failure: {service_name} — {pattern_name}"
        result = self._run_gh(
            "issue",
            "list",
            "--state",
            "open",
            "--search",
            search_query,
            "--json",
            "number",
            "--limit",
            "1",
        )
        if result.returncode != 0:
            return False
        output = result.stdout.strip()
        return output != "" and output != "[]"

    @staticmethod
    def _build_body(
        failure: FailureClassification,
        context: IssueContext,
    ) -> str:
        """Build the GitHub issue body with diagnostic context."""
        sections = [
            "## Deploy Failure Report\n",
            f"**Service**: {context.service_name}",
            f"**Failure Type**: {failure.pattern_name}",
            f"**Remediation**: {failure.remediation.value}",
            f"**Confidence**: {failure.confidence:.0%}",
            f"**Timestamp**: {context.deploy_timestamp}",
            "",
            "## Error Output",
            f"```\n{context.error_output}\n```"
            if context.error_output
            else "_No error output captured._",
            "",
            "## Recent Commits",
            f"```\n{context.recent_commits}\n```"
            if context.recent_commits
            else "_No commit data._",
            "",
            "## Remediation Suggestion",
            context.remediation_suggestion or "_See failure pattern documentation._",
        ]
        return "\n".join(sections)

    def _run_gh(self, *args: str) -> subprocess.CompletedProcess[str]:
        """Run a ``gh`` CLI command."""
        return subprocess.run(
            ["gh", *args],
            capture_output=True,
            text=True,
            cwd=self.cwd,
            timeout=30,
        )
