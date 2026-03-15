"""Git operations helper.

Provides clean/dirty state detection, branch management, and git state
validation per RFC Section 3.8.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class GitError(Exception):
    """Raised when a git operation fails."""


def _run_git(
    *args: str,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a git command and return the completed process."""
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=30,
    )
    return result


def is_clean(*, cwd: Path | None = None) -> bool:
    """Return True if the working tree has no uncommitted changes."""
    result = _run_git("status", "--porcelain", cwd=cwd)
    if result.returncode != 0:
        msg = f"git status failed: {result.stderr.strip()}"
        raise GitError(msg)
    return result.stdout.strip() == ""


def current_branch(*, cwd: Path | None = None) -> str:
    """Return the name of the current branch."""
    result = _run_git("rev-parse", "--abbrev-ref", "HEAD", cwd=cwd)
    if result.returncode != 0:
        msg = f"git rev-parse failed: {result.stderr.strip()}"
        raise GitError(msg)
    return result.stdout.strip()


def fetch_origin(*, cwd: Path | None = None) -> None:
    """Fetch from the origin remote."""
    result = _run_git("fetch", "origin", cwd=cwd)
    if result.returncode != 0:
        msg = f"git fetch failed: {result.stderr.strip()}"
        raise GitError(msg)


def create_branch(name: str, *, cwd: Path | None = None) -> None:
    """Create a new branch from the current HEAD."""
    result = _run_git("checkout", "-b", name, cwd=cwd)
    if result.returncode != 0:
        msg = f"git checkout -b failed: {result.stderr.strip()}"
        raise GitError(msg)


def checkout(branch: str, *, cwd: Path | None = None) -> None:
    """Switch to an existing branch."""
    result = _run_git("checkout", branch, cwd=cwd)
    if result.returncode != 0:
        msg = f"git checkout failed: {result.stderr.strip()}"
        raise GitError(msg)


def get_current_sha(*, cwd: Path | None = None) -> str:
    """Return the full SHA of the current HEAD commit."""
    result = _run_git("rev-parse", "HEAD", cwd=cwd)
    if result.returncode != 0:
        msg = f"git rev-parse HEAD failed: {result.stderr.strip()}"
        raise GitError(msg)
    return result.stdout.strip()


def validate_git_state(
    expected_branch: str,
    *,
    cwd: Path | None = None,
) -> list[str]:
    """Validate the current git state and return a list of issues.

    Checks:
    - Working tree is clean
    - Current branch matches *expected_branch*

    Returns an empty list when everything is valid.
    """
    issues: list[str] = []

    try:
        if not is_clean(cwd=cwd):
            issues.append("Working tree has uncommitted changes")
    except GitError as exc:
        issues.append(str(exc))

    try:
        branch = current_branch(cwd=cwd)
        if branch != expected_branch:
            issues.append(f"Expected branch '{expected_branch}', currently on '{branch}'")
    except GitError as exc:
        issues.append(str(exc))

    return issues


@dataclass(frozen=True)
class CloneResult:
    """Result from a git clone operation."""

    success: bool
    workspace_dir: Path
    error: str = ""
    duration_seconds: float = 0.0


def clone_repository(
    repository_url: str,
    target_dir: Path,
    *,
    branch: str = "",
    depth: int = 0,
    timeout_seconds: int = 120,
) -> CloneResult:
    """Clone a git repository into target_dir.

    Args:
        repository_url: The git URL or local path to clone from.
        target_dir: Where to clone into (must not exist).
        branch: Optional branch to clone (--branch flag).
        depth: Clone depth (0 = full clone, >0 = shallow).
        timeout_seconds: Maximum time for clone operation.
    """
    if not repository_url:
        return CloneResult(
            success=False, workspace_dir=target_dir, error="Repository URL must not be empty"
        )

    if target_dir.exists():
        return CloneResult(
            success=False,
            workspace_dir=target_dir,
            error=f"Target directory already exists: {target_dir}",
        )

    if depth < 0:
        return CloneResult(
            success=False, workspace_dir=target_dir, error="Clone depth must be >= 0"
        )

    if timeout_seconds <= 0:
        return CloneResult(success=False, workspace_dir=target_dir, error="Timeout must be > 0")

    cmd: list[str] = ["git", "clone", repository_url, str(target_dir)]
    if depth > 0:
        cmd.extend(["--depth", str(depth)])
    if branch:
        cmd.extend(["--branch", branch, "--single-branch"])

    start = time.monotonic()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - start
        return CloneResult(
            success=False,
            workspace_dir=target_dir,
            error=f"Clone timed out after {timeout_seconds}s",
            duration_seconds=elapsed,
        )
    except FileNotFoundError:
        return CloneResult(
            success=False,
            workspace_dir=target_dir,
            error="git is not installed or not found in PATH",
        )

    elapsed = time.monotonic() - start
    if result.returncode != 0:
        return CloneResult(
            success=False,
            workspace_dir=target_dir,
            error=result.stderr.strip(),
            duration_seconds=elapsed,
        )

    return CloneResult(
        success=True,
        workspace_dir=target_dir,
        duration_seconds=elapsed,
    )
