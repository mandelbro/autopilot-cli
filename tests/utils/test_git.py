"""Tests for autopilot.utils.git."""

from __future__ import annotations

import subprocess
from pathlib import Path  # noqa: TC003

import pytest

from autopilot.utils.git import (
    CloneResult,
    GitError,
    checkout,
    clone_repository,
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


class TestCloneResult:
    def test_creation(self) -> None:
        r = CloneResult(success=True, workspace_dir=Path("/tmp/ws"))
        assert r.success is True
        assert r.workspace_dir == Path("/tmp/ws")
        assert r.error == ""
        assert r.duration_seconds == 0.0

    def test_frozen(self) -> None:
        r = CloneResult(success=True, workspace_dir=Path("/tmp"))
        with pytest.raises(AttributeError):
            r.success = False  # type: ignore[misc]


class TestCloneRepository:
    def test_successful_clone(self, tmp_path: Path) -> None:
        source = _make_git_repo(tmp_path / "source")
        target = tmp_path / "target"
        result = clone_repository(str(source), target)
        assert result.success is True
        assert result.workspace_dir == target
        assert result.error == ""
        assert result.duration_seconds > 0
        assert (target / "README.md").exists()

    def test_shallow_clone(self, tmp_path: Path) -> None:
        source = _make_git_repo(tmp_path / "source")
        target = tmp_path / "target"
        result = clone_repository(str(source), target, depth=1)
        assert result.success is True
        assert (target / "README.md").exists()

    def test_branch_clone(self, tmp_path: Path) -> None:
        source = _make_git_repo(tmp_path / "source")
        subprocess.run(
            ["git", "checkout", "-b", "feature"],
            cwd=source,
            capture_output=True,
            check=True,
        )
        (source / "feature.txt").write_text("feature")
        subprocess.run(["git", "add", "."], cwd=source, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "feature commit"],
            cwd=source,
            capture_output=True,
            check=True,
        )

        target = tmp_path / "target"
        result = clone_repository(str(source), target, branch="feature")
        assert result.success is True
        assert (target / "feature.txt").exists()

    def test_empty_url_returns_error(self, tmp_path: Path) -> None:
        result = clone_repository("", tmp_path / "target")
        assert result.success is False
        assert "empty" in result.error.lower() or "url" in result.error.lower()

    def test_target_exists_returns_error(self, tmp_path: Path) -> None:
        existing = tmp_path / "existing"
        existing.mkdir()
        result = clone_repository("https://example.com/repo.git", existing)
        assert result.success is False
        assert "exist" in result.error.lower()

    def test_invalid_url_returns_error(self, tmp_path: Path) -> None:
        result = clone_repository("not-a-valid-repo-url", tmp_path / "target")
        assert result.success is False
        assert result.error != ""

    def test_negative_depth_returns_error(self, tmp_path: Path) -> None:
        result = clone_repository(
            "https://example.com/repo.git", tmp_path / "target", depth=-1
        )
        assert result.success is False

    def test_zero_timeout_returns_error(self, tmp_path: Path) -> None:
        result = clone_repository(
            "https://example.com/repo.git", tmp_path / "target", timeout_seconds=0
        )
        assert result.success is False
