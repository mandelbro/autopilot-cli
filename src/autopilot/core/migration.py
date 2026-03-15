"""RepEngine layout migration engine (RFC Section 5, Task 082).

Migrates from the legacy RepEngine ``autopilot/`` sibling directory
layout to the modern ``.autopilot/`` dot-directory format. The
migration is non-destructive -- the original directory is preserved.
"""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path  # noqa: TC003 — used at runtime
from typing import Any

import yaml

from autopilot.utils.paths import ensure_dir_structure

_log = logging.getLogger(__name__)

_GITIGNORE_CONTENT = "# Autopilot runtime state (not version controlled)\nstate/\nlogs/\n"


@dataclass
class MigrationResult:
    """Result of a RepEngine migration."""

    success: bool
    source_dir: Path
    target_dir: Path
    files_copied: list[str] = field(default_factory=lambda: list[str]())
    config_mapped: bool = False
    state_converted: bool = False
    errors: list[str] = field(default_factory=lambda: list[str]())


class MigrationEngine:
    """Converts RepEngine autopilot/ layout to .autopilot/ format."""

    def detect_repengine_layout(self, project_root: Path) -> bool:
        """Check if *project_root* has a RepEngine ``autopilot/`` directory.

        Returns ``True`` when ``autopilot/`` exists as a plain directory
        **and** ``.autopilot/`` does not yet exist.
        """
        repengine_dir = project_root / "autopilot"
        return repengine_dir.is_dir() and not (project_root / ".autopilot").exists()

    def migrate(self, project_root: Path, *, dry_run: bool = False) -> MigrationResult:
        """Execute migration from RepEngine layout to ``.autopilot/`` format.

        Steps:
          1. Validate RepEngine layout exists
          2. Read existing config (YAML/JSON)
          3. Create ``.autopilot/`` directory structure
          4. Copy agent prompt files
          5. Copy board files
          6. Convert JSON state files to SQLite
          7. Register project in global registry
          8. Generate ``.gitignore``

        The original ``autopilot/`` directory is **preserved** (non-destructive).
        """
        source = project_root / "autopilot"
        target = project_root / ".autopilot"

        result = MigrationResult(success=False, source_dir=source, target_dir=target)

        # Guard: source must exist
        if not source.is_dir():
            result.errors.append(f"Source directory not found: {source}")
            return result

        # Guard: target must not exist
        if target.exists():
            result.errors.append(f"Target directory already exists: {target}")
            return result

        try:
            # Step 1 -- read existing config
            config = self._read_repengine_config(source)
            result.config_mapped = bool(config)

            if not dry_run:
                # Step 2 -- create directory structure
                ensure_dir_structure(target)

                # Step 3 -- write config if we read one
                if config:
                    config_path = target / "config.yaml"
                    config_path.write_text(yaml.dump(config, default_flow_style=False))
                    result.files_copied.append("config.yaml")

            # Step 4 -- copy agent files
            copied_agents = self._copy_agents(source, target, dry_run=dry_run)
            result.files_copied.extend(copied_agents)

            # Step 5 -- copy board files
            copied_board = self._copy_board(source, target, dry_run=dry_run)
            result.files_copied.extend(copied_board)

            # Step 6 -- convert state files
            result.state_converted = self._convert_state_files(source, target, dry_run=dry_run)

            # Step 7 -- register project in global registry
            if not dry_run:
                self._register_project(project_root, config)

            # Step 8 -- generate .gitignore
            if not dry_run:
                self._generate_gitignore(target, dry_run=dry_run)
                result.files_copied.append(".gitignore")

            result.success = True
        except Exception as exc:  # noqa: BLE001
            _log.exception("Migration failed")
            result.errors.append(str(exc))
            # Clean up partial migration on failure (only if we created it)
            if not dry_run and target.exists():
                shutil.rmtree(target, ignore_errors=True)

        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_repengine_config(self, repengine_dir: Path) -> dict[str, Any]:
        """Read config from RepEngine layout (YAML or JSON)."""
        # Try YAML first, then JSON
        for name in ("config.yaml", "config.yml", "config.json"):
            config_path = repengine_dir / name
            if config_path.exists():
                text = config_path.read_text()
                if name.endswith(".json"):
                    return dict(json.loads(text))
                return dict(yaml.safe_load(text) or {})
        return {}

    def _copy_agents(self, source: Path, target: Path, *, dry_run: bool) -> list[str]:
        """Copy agent markdown files from ``agents/`` subdirectory."""
        agents_src = source / "agents"
        if not agents_src.is_dir():
            return []

        agents_dst = target / "agents"
        copied: list[str] = []

        for md_file in sorted(agents_src.glob("*.md")):
            relative = f"agents/{md_file.name}"
            if not dry_run:
                agents_dst.mkdir(parents=True, exist_ok=True)
                shutil.copy2(md_file, agents_dst / md_file.name)
            copied.append(relative)

        return copied

    def _copy_board(self, source: Path, target: Path, *, dry_run: bool) -> list[str]:
        """Copy board markdown files from ``board/`` subdirectory."""
        board_src = source / "board"
        if not board_src.is_dir():
            return []

        board_dst = target / "board"
        copied: list[str] = []

        for md_file in sorted(board_src.glob("*.md")):
            relative = f"board/{md_file.name}"
            if not dry_run:
                board_dst.mkdir(parents=True, exist_ok=True)
                shutil.copy2(md_file, board_dst / md_file.name)
            copied.append(relative)

        return copied

    def _convert_state_files(self, source: Path, target: Path, *, dry_run: bool) -> bool:
        """Convert JSON state files to SQLite entries.

        Looks for ``usage-tracker.json`` and ``hive-sessions.json`` in the
        source directory and imports their data into the project SQLite db.
        """
        state_files = [
            source / "usage-tracker.json",
            source / "hive-sessions.json",
        ]
        found_any = any(f.exists() for f in state_files)
        if not found_any:
            return False

        if dry_run:
            return True

        try:
            from autopilot.utils.db import Database

            db = Database(target / "autopilot.db")

            for state_file in state_files:
                if not state_file.exists():
                    continue
                text = state_file.read_text()
                data: Any = json.loads(text) if text.strip() else {}

                # Store raw JSON data in a migration_state table
                conn = db.get_connection()
                try:
                    conn.execute(
                        "CREATE TABLE IF NOT EXISTS migration_state "
                        "(source_file TEXT PRIMARY KEY, data TEXT, migrated_at TEXT "
                        "DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')))"
                    )
                    conn.execute(
                        "INSERT OR REPLACE INTO migration_state (source_file, data) VALUES (?, ?)",
                        (state_file.name, json.dumps(data)),
                    )
                    conn.commit()
                finally:
                    conn.close()

            return True
        except Exception:  # noqa: BLE001
            _log.debug("State file conversion failed (non-critical)", exc_info=True)
            return False

    def _register_project(self, project_root: Path, config: dict[str, Any]) -> None:
        """Register the migrated project in the global registry."""
        try:
            from autopilot.core.project import ProjectRegistry

            name = config.get("project_name", project_root.name)
            project_type = config.get("project_type", "python")
            registry = ProjectRegistry()

            # Only register if not already registered
            existing = registry.find_by_path(str(project_root))
            if existing is None:
                existing_by_name = registry.find_by_name(name)
                if existing_by_name is None:
                    registry.register(name, str(project_root), project_type)
        except Exception:  # noqa: BLE001
            _log.debug("Global registry update failed (non-critical)", exc_info=True)

    def _generate_gitignore(self, autopilot_dir: Path, *, dry_run: bool) -> None:
        """Create ``.gitignore`` for runtime directories."""
        if dry_run:
            return
        gitignore_path = autopilot_dir / ".gitignore"
        gitignore_path.write_text(_GITIGNORE_CONTENT)
