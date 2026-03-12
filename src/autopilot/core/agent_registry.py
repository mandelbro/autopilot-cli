"""Dynamic agent registry (RFC Section 3.7, ADR-10, Task 015).

Discovers agent roles from .md files in .autopilot/agents/ directories.
Supports both project-level and global (~/.autopilot/agents/) agents.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from autopilot.utils.paths import get_global_dir

if TYPE_CHECKING:
    from pathlib import Path

    from autopilot.core.models import DispatchPlan

_log = logging.getLogger(__name__)
_VALID_AGENT_NAME = re.compile(r"^[a-zA-Z0-9_-]+$")


class AgentNotFoundError(Exception):
    """Raised when a requested agent is not in the registry."""

    def __init__(self, name: str, available: list[str]) -> None:
        self.name = name
        self.available = available
        agents = ", ".join(sorted(available)) if available else "(none)"
        super().__init__(f"Agent '{name}' not found. Available: {agents}")


class AgentRegistry:
    """Discovers and loads agent prompts from .autopilot/agents/ directories.

    Lookup order: project-level agents override global agents.
    Files starting with underscore are excluded.
    """

    def __init__(
        self,
        project_agents_dir: Path | None = None,
        global_agents_dir: Path | None = None,
    ) -> None:
        self._project_dir = project_agents_dir
        self._global_dir = global_agents_dir or (get_global_dir() / "agents")

    def list_agents(self) -> list[str]:
        """Discover all available agent names from .md files."""
        agents: dict[str, Path] = {}
        # Global agents first (lower priority)
        for name, path in self._scan_dir(self._global_dir):
            agents[name] = path
        # Project agents override globals
        if self._project_dir:
            for name, path in self._scan_dir(self._project_dir):
                agents[name] = path
        return sorted(agents.keys())

    def load_prompt(self, name: str) -> str:
        """Load the prompt content for a named agent.

        Raises AgentNotFoundError if the agent does not exist.
        """
        path = self._resolve_path(name)
        if path is None:
            raise AgentNotFoundError(name, self.list_agents())
        return path.read_text()

    def validate_agent(self, name: str) -> bool:
        """Check whether an agent exists in the registry."""
        return self._resolve_path(name) is not None

    def validate_dispatch(self, plan: DispatchPlan) -> list[str]:
        """Return names of agents in the plan that are not registered."""
        available = set(self.list_agents())
        return [d.agent for d in plan.dispatches if d.agent not in available]

    def _resolve_path(self, name: str) -> Path | None:
        """Find the .md file for an agent, project-level first.

        Validates that the name is safe to prevent path traversal.
        """
        if not _VALID_AGENT_NAME.match(name):
            return None
        if self._project_dir:
            candidate = self._project_dir / f"{name}.md"
            if candidate.is_file():
                return candidate
        candidate = self._global_dir / f"{name}.md"
        if candidate.is_file():
            return candidate
        return None

    @staticmethod
    def _scan_dir(directory: Path) -> list[tuple[str, Path]]:
        """Scan a directory for agent .md files, excluding underscore-prefixed."""
        if not directory.is_dir():
            return []
        results: list[tuple[str, Path]] = []
        for f in sorted(directory.iterdir()):
            if f.suffix == ".md" and not f.name.startswith("_") and f.is_file():
                results.append((f.stem, f))
        return results
