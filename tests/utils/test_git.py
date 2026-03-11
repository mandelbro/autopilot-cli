"""Tests for autopilot.utils.git."""

from __future__ import annotations

import subprocess
from pathlib import Path  # noqa: TC003

import pytest

from autopilot.utils.git import (
    GitError,
    checkout,
    create_branch,
    current_branch,
    fetch_origin,
    is_clean,
    validate_git_state,
)


def _make_git_repo(tmp_path: Path) -> Path:
    """Initialize a minimal git repository for testing."""
    subprocess.run(["git", "init", str(tmp_path)], capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    # Create initial commit so HEAD exists
    (tmp_path / "README.md").write_text("init")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    return tmp_path


class TestIsClean:
    def test_clean_repo(self, tmp_path: Path) -> None:
        repo = _make_git_repo(tmp_path)
        assert is_clean(cwd=repo) is True

    def test_dirty_repo(self, tmp_path: Path) -> None:
        repo = _make_git_repo(tmp_path)
        (repo / "new_file.txt").write_text("dirty")
        assert is_clean(cwd=repo) is False


class TestCurrentBranch:
    def test_returns_branch_name(self, tmp_path: Path) -> None:
        repo = _make_git_repo(tmp_path)
        branch = current_branch(cwd=repo)
        assert branch in ("main", "master")


class TestFetchOrigin:
    def test_raises_on_no_remote(self, tmp_path: Path) -> None:
        repo = _make_git_repo(tmp_path)
        with pytest.raises(GitError):
            fetch_origin(cwd=repo)


class TestCreateBranch:
    def test_creates_and_switches(self, tmp_path: Path) -> None:
        repo = _make_git_repo(tmp_path)
        create_branch("feature/test", cwd=repo)
        assert current_branch(cwd=repo) == "feature/test"


class TestCheckout:
    def test_switch_branch(self, tmp_path: Path) -> None:
        repo = _make_git_repo(tmp_path)
        original = current_branch(cwd=repo)
        create_branch("other-branch", cwd=repo)
        checkout(original, cwd=repo)
        assert current_branch(cwd=repo) == original

    def test_nonexistent_branch(self, tmp_path: Path) -> None:
        repo = _make_git_repo(tmp_path)
        with pytest.raises(GitError):
            checkout("nonexistent-branch", cwd=repo)


class TestValidateGitState:
    def test_valid_state(self, tmp_path: Path) -> None:
        repo = _make_git_repo(tmp_path)
        branch = current_branch(cwd=repo)
        issues = validate_git_state(branch, cwd=repo)
        assert issues == []

    def test_wrong_branch(self, tmp_path: Path) -> None:
        repo = _make_git_repo(tmp_path)
        issues = validate_git_state("nonexistent", cwd=repo)
        assert len(issues) == 1
        assert "Expected branch" in issues[0]

    def test_dirty_and_wrong_branch(self, tmp_path: Path) -> None:
        repo = _make_git_repo(tmp_path)
        (repo / "new.txt").write_text("dirty")
        issues = validate_git_state("nonexistent", cwd=repo)
        assert len(issues) == 2
