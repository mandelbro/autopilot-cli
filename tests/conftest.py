"""Shared test fixtures for autopilot-cli."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """A temporary directory simulating a project root."""
    return tmp_path


@pytest.fixture
def autopilot_dir(project_dir: Path) -> Path:
    """A temporary .autopilot directory with standard structure."""
    ap = project_dir / ".autopilot"
    ap.mkdir()
    for subdir in ("agents", "board", "tasks", "state", "logs", "enforcement"):
        (ap / subdir).mkdir()
    return ap


@pytest.fixture
def global_dir(tmp_path: Path) -> Path:
    """A temporary ~/.autopilot global directory."""
    gd = tmp_path / "global_autopilot"
    gd.mkdir()
    return gd
