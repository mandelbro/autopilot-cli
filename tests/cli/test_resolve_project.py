"""Tests for _resolve_project external project resolution (PR #57)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

if TYPE_CHECKING:
    from pathlib import Path

import pytest

from autopilot.cli.app import _resolve_project
from autopilot.core.project import ProjectRegistry


def _register_external(global_dir: Path, project_root: Path, name: str = "ext-proj") -> None:
    """Register an external project in a temp global registry."""
    registry = ProjectRegistry(global_dir=global_dir)
    registry.register(
        name,
        str(project_root),
        "python",
        external=True,
        task_dir=str(project_root / "tasks"),
    )


class TestResolveProjectExternal:
    """_resolve_project should resolve external projects via the registry."""

    def test_returns_correct_ap_dir_and_name(self, tmp_path: Path) -> None:
        global_dir = tmp_path / "global"
        global_dir.mkdir()
        project_root = tmp_path / "my-external"
        project_root.mkdir()
        _register_external(global_dir, project_root, "my-external")

        with patch("autopilot.core.project.get_global_dir", return_value=global_dir):
            ap_dir, name = _resolve_project("my-external")

        assert name == "my-external"
        assert ap_dir == project_root / ".autopilot"
        assert ap_dir.is_dir()

    def test_creates_autopilot_dir_on_demand(self, tmp_path: Path) -> None:
        global_dir = tmp_path / "global"
        global_dir.mkdir()
        project_root = tmp_path / "fresh-ext"
        project_root.mkdir()
        _register_external(global_dir, project_root, "fresh-ext")

        assert not (project_root / ".autopilot").exists()

        with patch("autopilot.core.project.get_global_dir", return_value=global_dir):
            ap_dir, _ = _resolve_project("fresh-ext")

        assert ap_dir.is_dir()
        # ensure_dir_structure creates standard subdirs
        assert (ap_dir / "agents").is_dir()

    def test_reuses_existing_autopilot_dir(self, tmp_path: Path) -> None:
        global_dir = tmp_path / "global"
        global_dir.mkdir()
        project_root = tmp_path / "existing-ext"
        project_root.mkdir()
        existing_ap = project_root / ".autopilot"
        existing_ap.mkdir()
        marker = existing_ap / "marker.txt"
        marker.write_text("keep")
        _register_external(global_dir, project_root, "existing-ext")

        with patch("autopilot.core.project.get_global_dir", return_value=global_dir):
            ap_dir, _ = _resolve_project("existing-ext")

        assert ap_dir == existing_ap
        assert marker.read_text() == "keep"

    def test_stale_path_exits_with_error(self, tmp_path: Path) -> None:
        global_dir = tmp_path / "global"
        global_dir.mkdir()
        missing_root = tmp_path / "gone"
        # Don't create it — simulates a stale registry entry
        _register_external(global_dir, missing_root, "stale-proj")

        from click.exceptions import Exit

        with (
            patch("autopilot.core.project.get_global_dir", return_value=global_dir),
            pytest.raises(Exit),
        ):
            _resolve_project("stale-proj")
