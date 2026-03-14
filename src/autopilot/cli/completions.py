"""Shell completion helpers for dynamic argument values.

Provides completion callbacks that Typer can use for tab-completion
of project names, project types, and other dynamic CLI values.
These are consumed by bash, zsh, and fish via Typer's built-in
``--install-completion`` / ``--show-completion`` support.
"""

from __future__ import annotations


def complete_project_names(incomplete: str) -> list[str]:
    """Complete project names from the global registry.

    Filters out archived projects and returns only names that
    start with the typed prefix.
    """
    try:
        from autopilot.core.project import ProjectRegistry

        registry = ProjectRegistry()
        projects = registry.load()
        return [p.name for p in projects if p.name.startswith(incomplete) and not p.archived]
    except Exception:  # noqa: BLE001
        return []


def complete_project_types(incomplete: str) -> list[str]:
    """Complete project type values (python, typescript, hybrid)."""
    types = ["python", "typescript", "hybrid"]
    return [t for t in types if t.startswith(incomplete)]
