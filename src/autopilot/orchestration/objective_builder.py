"""Hive-mind objective prompt builder.

Constructs parameterized objective prompts from Jinja2 templates
using project configuration to drive template context.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from autopilot.core.templates import TemplateRenderer

if TYPE_CHECKING:
    from autopilot.core.config import AutopilotConfig, QualityGatesConfig

_log = logging.getLogger(__name__)

_PACKAGE_TEMPLATES = Path(__file__).resolve().parents[3] / "templates"


class HiveObjectiveBuilder:
    """Builds parameterized hive-mind objective prompts from Jinja2 templates."""

    def __init__(self, config: AutopilotConfig) -> None:
        self._config = config
        self._renderer = TemplateRenderer(
            "hive-objective",
            package_templates_dir=_PACKAGE_TEMPLATES,
        )

    def build(
        self,
        task_file: str,
        task_ids: list[str],
        *,
        template_name: str = "default",
    ) -> str:
        """Render the objective template with config-driven context."""
        context = self._build_context(task_file, task_ids)
        rendered = self._renderer.render_to_string(f"{template_name}.j2", context)
        if len(rendered) > 4000:
            _log.warning("Objective length %d exceeds 4000 characters", len(rendered))
        return rendered

    def _build_context(self, task_file: str, task_ids: list[str]) -> dict[str, Any]:
        """Build template context from config."""
        hive = self._config.hive_mind
        gates = self._config.quality_gates
        return {
            "task_ids": task_ids,
            "task_file": task_file,
            "quality_command": gates.all or "just",
            "format_command": hive.format_command,
            "code_review_enabled": hive.code_review_enabled,
            "max_review_rounds": hive.max_review_rounds,
            "auto_merge": hive.auto_merge,
            "duplication_check": hive.duplication_check,
            "cleanup_pass": hive.cleanup_pass,
            "security_scan": hive.security_scan,
            "coverage_check": hive.coverage_check,
            "file_size_check": hive.file_size_check,
            "quality_gates": self._format_quality_gates(gates),
            "sprint_record": "",
        }

    @staticmethod
    def _format_quality_gates(gates: QualityGatesConfig) -> str:
        """Format quality gates as a bulleted list."""
        parts: list[str] = []
        if gates.pre_commit:
            parts.append(f"pre-commit: {gates.pre_commit}")
        if gates.type_check:
            parts.append(f"type-check: {gates.type_check}")
        if gates.test:
            parts.append(f"test: {gates.test}")
        if gates.all:
            parts.append(f"all: {gates.all}")

        if not parts:
            return ""
        return "\n".join(f"- {p}" for p in parts)
