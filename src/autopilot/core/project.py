"""Project lifecycle management (RFC Section 3.4.3, ADR-2, ADR-3).

Handles project initialization: rendering Jinja2 templates from
templates/{type}/ to {root}/.autopilot/, global registry, and
SQLite registration.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

from autopilot.utils.paths import ensure_dir_structure, get_global_dir

_TEMPLATES_DIR = Path(__file__).resolve().parents[3] / "templates"
_GITIGNORE_CONTENT = "# Autopilot runtime state (not version controlled)\nstate/\nlogs/\n"


@dataclass
class ProjectInitResult:
    """Result of a project initialization."""

    project_name: str
    project_root: Path
    autopilot_dir: Path
    files_created: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)


def initialize_project(
    name: str,
    project_type: str = "python",
    root_path: Path | None = None,
    *,
    template_overrides: dict[str, str] | None = None,
) -> ProjectInitResult:
    """Initialize a new autopilot project.

    Creates the .autopilot/ directory structure, renders templates,
    registers the project globally in ~/.autopilot/projects.yaml,
    and optionally registers in the SQLite database.
    """
    root = (root_path or Path.cwd()).resolve()
    autopilot_dir = root / ".autopilot"

    if autopilot_dir.exists():
        msg = f"Project already initialized: {autopilot_dir}"
        raise FileExistsError(msg)

    # Create standard directory structure
    ensure_dir_structure(autopilot_dir)

    # Render templates
    template_dir = _TEMPLATES_DIR / project_type
    if not template_dir.exists():
        msg = f"No templates found for project type '{project_type}' at {template_dir}"
        raise ValueError(msg)

    files_created = _render_templates(
        template_dir=template_dir,
        autopilot_dir=autopilot_dir,
        context={
            "project_name": name,
            "project_root": str(root),
            "agent_roster": "",
            **(template_overrides or {}),
        },
    )

    # Create .gitignore for runtime directories
    gitignore_path = autopilot_dir / ".gitignore"
    gitignore_path.write_text(_GITIGNORE_CONTENT)
    files_created.append(str(gitignore_path.relative_to(root)))

    # Register in global projects.yaml
    _register_global(name=name, path=str(root), project_type=project_type)

    # Register in SQLite (best-effort)
    _register_sqlite(name=name, path=str(root), project_type=project_type)

    return ProjectInitResult(
        project_name=name,
        project_root=root,
        autopilot_dir=autopilot_dir,
        files_created=files_created,
        next_steps=[
            "Edit .autopilot/config.yaml to customize settings",
            "Review agent prompts in .autopilot/agents/",
            "Run 'autopilot session start' to begin autonomous development",
        ],
    )


def _render_templates(
    template_dir: Path,
    autopilot_dir: Path,
    context: dict[str, str],
) -> list[str]:
    """Render all templates from template_dir into autopilot_dir."""
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        keep_trailing_newline=True,
    )
    files_created: list[str] = []
    root = autopilot_dir.parent

    for template_name in env.list_templates():
        template = env.get_template(template_name)
        rendered = template.render(**context)

        # Strip .j2 extension for output
        output_name = template_name.removesuffix(".j2")
        output_path = autopilot_dir / output_name
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered)
        files_created.append(str(output_path.relative_to(root)))

    return files_created


def _register_global(*, name: str, path: str, project_type: str) -> None:
    """Register the project in ~/.autopilot/projects.yaml."""
    global_dir = get_global_dir()
    global_dir.mkdir(parents=True, exist_ok=True)
    projects_file = global_dir / "projects.yaml"

    projects: list[dict[str, str]] = []
    if projects_file.exists():
        data = yaml.safe_load(projects_file.read_text())
        if isinstance(data, list):
            projects = data

    # Avoid duplicates
    for p in projects:
        if p.get("name") == name:
            p["path"] = path
            p["type"] = project_type
            break
    else:
        projects.append({"name": name, "path": path, "type": project_type})

    projects_file.write_text(yaml.dump(projects, default_flow_style=False))


def _register_sqlite(*, name: str, path: str, project_type: str) -> None:
    """Register the project in the global SQLite database (best-effort)."""
    try:
        from autopilot.utils.db import Database

        db_path = get_global_dir() / "autopilot.db"
        db = Database(db_path)
        db.insert_project(
            id=str(uuid.uuid4()),
            name=name,
            path=path,
            type=project_type,
        )
    except Exception:  # noqa: BLE001
        # SQLite registration is non-critical; project works without it
        pass
