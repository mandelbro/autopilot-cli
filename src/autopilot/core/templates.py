"""Template rendering system with Jinja2 (Task 016).

Renders project scaffolding from templates/{type}/ with user-level
overrides from ~/.autopilot/templates/{type}/. Supports template
inheritance via an ``extends`` key in template config.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound

from autopilot.utils.paths import get_global_dir

_log = logging.getLogger(__name__)

_PACKAGE_TEMPLATES = Path(__file__).resolve().parents[3] / "templates"


def list_available_templates() -> list[str]:
    """Return all registered template type names."""
    types: set[str] = set()
    if _PACKAGE_TEMPLATES.is_dir():
        for d in _PACKAGE_TEMPLATES.iterdir():
            if d.is_dir():
                types.add(d.name)
    user_dir = get_global_dir() / "templates"
    if user_dir.is_dir():
        for d in user_dir.iterdir():
            if d.is_dir():
                types.add(d.name)
    return sorted(types)


class TemplateRenderer:
    """Renders Jinja2 templates for a given project type.

    Lookup order: user override (~/.autopilot/templates/{type}/) then
    package default (templates/{type}/). Template inheritance is
    supported via ``extends: "base_type"`` in a ``_template.yaml``
    config file.
    """

    def __init__(
        self,
        project_type: str,
        *,
        package_templates_dir: Path | None = None,
        user_templates_dir: Path | None = None,
    ) -> None:
        self._project_type = project_type
        self._package_dir = (package_templates_dir or _PACKAGE_TEMPLATES) / project_type
        self._user_dir = (user_templates_dir or get_global_dir() / "templates") / project_type
        self._template_config = self._load_template_config()

    def render_to(self, output_dir: Path, context: dict[str, Any]) -> list[str]:
        """Render all templates to output_dir, returning relative paths of created files."""
        files_created: list[str] = []

        # Render parent templates first if inheritance is used
        parent_type = self._template_config.get("extends")
        if parent_type and isinstance(parent_type, str):
            parent = TemplateRenderer(
                parent_type,
                package_templates_dir=self._package_dir.parent,
                user_templates_dir=self._user_dir.parent,
            )
            files_created.extend(parent.render_to(output_dir, context))

        # Build search paths: user override first, then package
        search_paths: list[str] = []
        if self._user_dir.is_dir():
            search_paths.append(str(self._user_dir))
        if self._package_dir.is_dir():
            search_paths.append(str(self._package_dir))

        if not search_paths:
            msg = f"No templates found for project type '{self._project_type}'"
            raise ValueError(msg)

        env = Environment(
            loader=FileSystemLoader(search_paths),
            keep_trailing_newline=True,
            undefined=StrictUndefined,
        )

        for template_name in env.list_templates():
            if template_name.startswith("_"):
                continue
            try:
                template = env.get_template(template_name)
            except TemplateNotFound:
                _log.warning("Template not found: %s", template_name)
                continue

            rendered = template.render(**context)
            output_name = template_name.removesuffix(".j2")
            output_path = output_dir / output_name
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered)
            rel = str(output_path.relative_to(output_dir))
            if rel not in files_created:
                files_created.append(rel)

        return files_created

    def validate(self) -> list[str]:
        """Check that all expected template files are present. Returns issues."""
        issues: list[str] = []
        expected = self._template_config.get("expected_files", [])
        if not isinstance(expected, list):
            return issues

        search_paths = []
        if self._user_dir.is_dir():
            search_paths.append(self._user_dir)
        if self._package_dir.is_dir():
            search_paths.append(self._package_dir)

        for fname in expected:
            found = False
            for sp in search_paths:
                if (sp / fname).exists() or (sp / f"{fname}.j2").exists():
                    found = True
                    break
            if not found:
                issues.append(f"Missing expected template: {fname}")
        return issues

    def _load_template_config(self) -> dict[str, Any]:
        """Load _template.yaml config if it exists."""
        for d in (self._user_dir, self._package_dir):
            config_path = d / "_template.yaml"
            if config_path.is_file():
                try:
                    data = yaml.safe_load(config_path.read_text())
                    if isinstance(data, dict):
                        return data
                except yaml.YAMLError:
                    _log.warning("Invalid _template.yaml in %s", d)
        return {}
