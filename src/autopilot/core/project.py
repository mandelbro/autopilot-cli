"""Project lifecycle management (RFC Section 3.4.3, ADR-2, ADR-3).

Handles project initialization, global registry CRUD, and
SQLite registration. The ``ProjectRegistry`` class provides
thread-safe access to ~/.autopilot/projects.yaml.
"""

from __future__ import annotations

import contextlib
import fcntl
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from collections.abc import Iterator

import yaml
from jinja2 import Environment, FileSystemLoader

from autopilot.utils.paths import ensure_dir_structure, get_global_dir

_log = logging.getLogger(__name__)

_VALID_PROJECT_TYPE = re.compile(r"^[a-zA-Z0-9_-]+$")

_TEMPLATES_DIR = Path(__file__).resolve().parents[3] / "templates"
_GITIGNORE_CONTENT = "# Autopilot runtime state (not version controlled)\nstate/\nlogs/\n"


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class ProjectInitResult:
    """Result of a project initialization."""

    project_name: str
    project_root: Path
    autopilot_dir: Path
    files_created: list[str] = field(default_factory=lambda: list[str]())
    next_steps: list[str] = field(default_factory=lambda: list[str]())


@dataclass
class RegisteredProject:
    """A project entry in the global registry."""

    name: str
    path: str
    type: str
    registered_at: str = field(default_factory=lambda: _utc_now().isoformat())
    last_active: str = ""
    archived: bool = False
    repository_url: str = ""


@dataclass
class RegistryIssue:
    """An issue found during registry validation."""

    project_name: str
    issue: str


class ProjectRegistry:
    """CRUD operations for ~/.autopilot/projects.yaml (Task 012).

    Uses file locking to handle concurrent access safely.
    """

    def __init__(self, global_dir: Path | None = None) -> None:
        self._global_dir = global_dir or get_global_dir()
        self._global_dir.mkdir(parents=True, exist_ok=True)
        self._projects_file = self._global_dir / "projects.yaml"
        self._lock_file = self._projects_file.with_suffix(".yaml.lock")

    @contextlib.contextmanager
    def _locked(self) -> Iterator[None]:
        """Hold an exclusive lock across a read-modify-write cycle."""
        self._lock_file.touch()
        with open(self._lock_file) as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lf, fcntl.LOCK_UN)

    def load(self) -> list[RegisteredProject]:
        """Load all registered projects."""
        raw = self._read_raw()
        return [self._dict_to_project(p) for p in raw]

    def register(
        self, name: str, path: str, project_type: str, *, repository_url: str = ""
    ) -> RegisteredProject:
        """Register a new project. Raises ValueError on duplicate name."""
        self._validate_repository_url(repository_url)
        with self._locked():
            raw = self._read_raw()
            for p in raw:
                if p.get("name") == name:
                    msg = f"Project '{name}' is already registered"
                    raise ValueError(msg)

            project = RegisteredProject(
                name=name, path=path, type=project_type, repository_url=repository_url
            )
            raw.append(self._project_to_dict(project))
            self._write_raw(raw)
        return project

    def unregister(self, name: str) -> None:
        """Remove a project from the registry (does not delete files)."""
        with self._locked():
            raw = self._read_raw()
            filtered = [p for p in raw if p.get("name") != name]
            if len(filtered) == len(raw):
                msg = f"Project '{name}' not found in registry"
                raise KeyError(msg)
            self._write_raw(filtered)

    def find_by_name(self, name: str) -> RegisteredProject | None:
        """Find a project by name."""
        for p in self._read_raw():
            if p.get("name") == name:
                return self._dict_to_project(p)
        return None

    def find_by_path(self, path: str) -> RegisteredProject | None:
        """Find a project by path."""
        resolved = str(Path(path).resolve())
        for p in self._read_raw():
            if str(Path(p.get("path", "")).resolve()) == resolved:
                return self._dict_to_project(p)
        return None

    def update_last_active(self, name: str) -> None:
        """Update the last_active timestamp for a project."""
        with self._locked():
            raw = self._read_raw()
            for p in raw:
                if p.get("name") == name:
                    p["last_active"] = _utc_now().isoformat()
                    self._write_raw(raw)
                    return
            msg = f"Project '{name}' not found in registry"
            raise KeyError(msg)

    def archive(self, name: str) -> None:
        """Mark a project as archived."""
        with self._locked():
            raw = self._read_raw()
            for p in raw:
                if p.get("name") == name:
                    p["archived"] = True
                    self._write_raw(raw)
                    return
            msg = f"Project '{name}' not found in registry"
            raise KeyError(msg)

    def update_repository_url(self, name: str, url: str) -> None:
        """Update the repository URL for a registered project."""
        self._validate_repository_url(url)
        with self._locked():
            raw = self._read_raw()
            for p in raw:
                if p.get("name") == name:
                    p["repository_url"] = url
                    self._write_raw(raw)
                    return
            msg = f"Project '{name}' not found in registry"
            raise KeyError(msg)

    @staticmethod
    def _validate_repository_url(url: str) -> None:
        """Validate that a URL is a plausible git URL."""
        if not url:
            return
        if url.startswith(("https://", "git@", "ssh://")) or url.startswith("/"):
            return
        msg = (
            f"Not a plausible git URL: {url!r}. "
            "Must start with https://, git@, ssh://, or be a local path"
        )
        raise ValueError(msg)

    def validate_all(self) -> list[RegistryIssue]:
        """Check all registered projects for issues."""
        issues: list[RegistryIssue] = []
        for p in self._read_raw():
            name = p.get("name", "<unknown>")
            path = p.get("path", "")
            if not path:
                issues.append(RegistryIssue(name, "missing path"))
                continue
            path_obj = Path(path)
            if not path_obj.exists():
                issues.append(RegistryIssue(name, f"path does not exist: {path}"))
            elif not (path_obj / ".autopilot").is_dir():
                issues.append(RegistryIssue(name, f"no .autopilot/ directory at {path}"))
        return issues

    def _read_raw(self) -> list[dict[str, Any]]:
        if not self._projects_file.exists():
            return []
        try:
            data = yaml.safe_load(self._projects_file.read_text())
        except yaml.YAMLError:
            _log.warning("Corrupt projects.yaml, returning empty list")
            return []
        if isinstance(data, list):
            return cast("list[dict[str, Any]]", data)
        return []

    def _write_raw(self, data: list[dict[str, Any]]) -> None:
        self._projects_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._projects_file.with_suffix(".yaml.tmp")
        content = yaml.dump(data, default_flow_style=False)
        tmp.write_text(content)
        tmp.replace(self._projects_file)

    @staticmethod
    def _dict_to_project(d: dict[str, str]) -> RegisteredProject:
        return RegisteredProject(
            name=d.get("name", ""),
            path=d.get("path", ""),
            type=d.get("type", ""),
            registered_at=d.get("registered_at", ""),
            last_active=d.get("last_active", ""),
            archived=bool(d.get("archived", False)),
            repository_url=d.get("repository_url", ""),
        )

    @staticmethod
    def _project_to_dict(p: RegisteredProject) -> dict[str, Any]:
        return {
            "name": p.name,
            "path": p.path,
            "type": p.type,
            "registered_at": p.registered_at,
            "last_active": p.last_active,
            "archived": p.archived,
            "repository_url": p.repository_url,
        }


def initialize_project(
    name: str,
    project_type: str = "python",
    root_path: Path | None = None,
    *,
    template_overrides: dict[str, str] | None = None,
    repository_url: str = "",
) -> ProjectInitResult:
    """Initialize a new autopilot project.

    Creates the .autopilot/ directory structure, renders templates,
    registers the project globally in ~/.autopilot/projects.yaml,
    and optionally registers in the SQLite database.
    """
    # Validate project_type to prevent path traversal
    if not _VALID_PROJECT_TYPE.match(project_type):
        msg = f"Invalid project type '{project_type}': must contain only alphanumeric characters, hyphens, and underscores"
        raise ValueError(msg)

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
    _register_global(
        name=name, path=str(root), project_type=project_type, repository_url=repository_url
    )

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
            "Set repository URL with 'autopilot project config workspace.repository_url <url>' for workspace isolation",
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


def _register_global(*, name: str, path: str, project_type: str, repository_url: str = "") -> None:
    """Register the project in ~/.autopilot/projects.yaml."""
    registry = ProjectRegistry()
    existing = registry.find_by_name(name)
    if existing is None:
        registry.register(name, path, project_type, repository_url=repository_url)
    else:
        # Update existing entry via raw rewrite (idempotent)
        raw = registry._read_raw()  # pyright: ignore[reportPrivateUsage]
        for p in raw:
            if p.get("name") == name:
                p["path"] = path
                p["type"] = project_type
                if repository_url:
                    p["repository_url"] = repository_url
                break
        registry._write_raw(raw)  # pyright: ignore[reportPrivateUsage]


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
        _log.debug("SQLite registration failed (non-critical)", exc_info=True)
