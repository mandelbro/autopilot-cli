"""Quality gate prompt generation for hive-mind objectives (Task 065, RFC Section 3.5.3).

Builds dynamic quality gate instructions from project configuration for
injection into hive-mind agent objectives, replacing hardcoded suffixes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autopilot.core.config import QualityGatesConfig

_PYTHON_DEFAULTS: dict[str, str] = {
    "pre_commit": "ruff check --fix . && ruff format .",
    "type_check": "pyright",
    "test": "pytest",
}

_TYPESCRIPT_DEFAULTS: dict[str, str] = {
    "pre_commit": "eslint --fix . && prettier --write .",
    "type_check": "tsc --noEmit",
    "test": "npm test",
}

_DEFAULTS_BY_PROJECT_TYPE: dict[str, dict[str, str]] = {
    "python": _PYTHON_DEFAULTS,
    "typescript": _TYPESCRIPT_DEFAULTS,
}

_GATE_ORDERING: list[str] = ["pre_commit", "type_check", "test"]

_GATE_LABELS: dict[str, str] = {
    "pre_commit": "Pre-commit checks",
    "type_check": "Type checking",
    "test": "Tests",
}


class QualityGateBuilder:
    """Builds quality gate prompts from project configuration."""

    @staticmethod
    def gate_ordering() -> list[str]:
        """Return the fixed gate ordering.

        Returns
        -------
        list[str]
            Gate names in execution order: pre_commit, type_check, test.
        """
        return list(_GATE_ORDERING)

    @staticmethod
    def get_gates(
        config: QualityGatesConfig,
        *,
        project_type: str = "python",
    ) -> list[tuple[str, str]]:
        """Return resolved (gate_name, command) tuples in execution order.

        Uses config values when non-empty, otherwise falls back to defaults
        for the given *project_type*.

        Parameters
        ----------
        config:
            Quality gates configuration from the project.
        project_type:
            Either ``"python"`` or ``"typescript"``.

        Returns
        -------
        list[tuple[str, str]]
            Ordered list of ``(gate_name, command)`` pairs.
        """
        defaults = _DEFAULTS_BY_PROJECT_TYPE.get(project_type, _PYTHON_DEFAULTS)
        gates: list[tuple[str, str]] = []
        for gate_name in _GATE_ORDERING:
            config_value = getattr(config, gate_name, "")
            command = config_value if config_value else defaults[gate_name]
            gates.append((gate_name, command))
        return gates

    @staticmethod
    def build_prompt(
        config: QualityGatesConfig,
        *,
        project_type: str = "python",
    ) -> str:
        """Generate a numbered quality gate prompt for agent objectives.

        Parameters
        ----------
        config:
            Quality gates configuration from the project.
        project_type:
            Either ``"python"`` or ``"typescript"``.

        Returns
        -------
        str
            Markdown-formatted quality gate instructions.
        """
        gates = QualityGateBuilder.get_gates(config, project_type=project_type)

        lines: list[str] = [
            "## Quality Gates",
            "",
            "Before reporting task completion, run these checks in order:",
            "",
        ]

        for idx, (gate_name, command) in enumerate(gates, start=1):
            label = _GATE_LABELS[gate_name]
            lines.append(f"{idx}. **{label}**: `{command}`")

        lines.append("")
        lines.append("If any gate fails, fix the issues and re-run. Stage and commit auto-fixes.")

        return "\n".join(lines)
