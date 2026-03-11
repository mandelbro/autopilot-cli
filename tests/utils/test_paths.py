"""Tests for autopilot.utils.paths."""

from __future__ import annotations

from pathlib import Path

from autopilot.utils.paths import (
    ensure_dir_structure,
    find_autopilot_dir,
    get_global_dir,
    resolve_project_root,
)


class TestFindAutopilotDir:
    def test_finds_in_current(self, tmp_path: Path) -> None:
        ap = tmp_path / ".autopilot"
        ap.mkdir()
        assert find_autopilot_dir(tmp_path) == ap

    def test_finds_in_parent(self, tmp_path: Path) -> None:
        ap = tmp_path / ".autopilot"
        ap.mkdir()
        child = tmp_path / "src" / "deep"
        child.mkdir(parents=True)
        assert find_autopilot_dir(child) == ap

    def test_returns_none_when_missing(self, tmp_path: Path) -> None:
        assert find_autopilot_dir(tmp_path) is None


class TestResolveProjectRoot:
    def test_resolves_parent(self, tmp_path: Path) -> None:
        ap = tmp_path / ".autopilot"
        ap.mkdir()
        assert resolve_project_root(ap) == tmp_path.resolve()


class TestGetGlobalDir:
    def test_returns_home_autopilot(self) -> None:
        result = get_global_dir()
        assert result == Path.home() / ".autopilot"


class TestEnsureDirStructure:
    def test_creates_standard_subdirs(self, tmp_path: Path) -> None:
        ap = tmp_path / ".autopilot"
        created = ensure_dir_structure(ap)
        assert ap.exists()
        expected = {"agents", "board", "tasks", "state", "logs", "enforcement"}
        actual = {p.name for p in created}
        assert actual == expected

    def test_idempotent(self, tmp_path: Path) -> None:
        ap = tmp_path / ".autopilot"
        ensure_dir_structure(ap)
        created = ensure_dir_structure(ap)
        assert created == []

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        ap = tmp_path / "deep" / "nested" / ".autopilot"
        ensure_dir_structure(ap)
        assert ap.exists()
