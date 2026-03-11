"""Project and autopilot path resolution utilities.

Consolidates _resolve_paths from RepEngine cli.py and cli_display.py
into a shared utility per Discovery Consolidation Opportunity 1.
"""

from __future__ import annotations

from pathlib import Path

_DOT_AUTOPILOT = ".autopilot"

# Standard subdirectories created inside .autopilot/ per RFC 3.4.3.
_STANDARD_SUBDIRS = (
    "agents",
    "board",
    "tasks",
    "state",
    "logs",
    "enforcement",
)


def find_autopilot_dir(start: Path | None = None) -> Path | None:
    """Walk up from *start* to find the nearest ``.autopilot/`` directory.

    Returns the absolute path to the directory, or ``None`` if not found.
    """
    current = (start or Path.cwd()).resolve()
    while True:
        candidate = current / _DOT_AUTOPILOT
        if candidate.is_dir():
            return candidate
        parent = current.parent
        if parent == current:
            return None
        current = parent


def resolve_project_root(autopilot_dir: Path) -> Path:
    """Derive the project root from a ``.autopilot/`` directory path."""
    return autopilot_dir.resolve().parent


def get_global_dir() -> Path:
    """Return the global autopilot directory (``~/.autopilot/``)."""
    return Path.home() / _DOT_AUTOPILOT


def ensure_dir_structure(autopilot_dir: Path) -> list[Path]:
    """Create the standard subdirectory structure inside *autopilot_dir*.

    Returns the list of directories that were created (already-existing
    directories are silently skipped).
    """
    created: list[Path] = []
    autopilot_dir.mkdir(parents=True, exist_ok=True)
    for name in _STANDARD_SUBDIRS:
        sub = autopilot_dir / name
        if not sub.exists():
            sub.mkdir()
            created.append(sub)
    return created
