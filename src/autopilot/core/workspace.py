"""Workspace isolation manager (ADR-011, Task 097).

Creates and manages isolated git clones for agent sessions,
preventing working tree contamination in the developer's checkout.
"""

from __future__ import annotations

import fcntl
import json
import logging
import shutil
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from autopilot.core.models import SessionStatus, WorkspaceInfo, WorkspaceStatus
from autopilot.utils.git import clone_repository

if TYPE_CHECKING:
    from autopilot.core.config import WorkspaceConfig
    from autopilot.core.project import ProjectRegistry

# Type alias for session status lookup — avoids importing SessionManager
SessionStatusLookup = Callable[[str], SessionStatus | None]

_log = logging.getLogger(__name__)

# Directories to exclude when copying .autopilot/ config into workspace
_EXCLUDED_SUBDIRS = {"state", "logs"}


class WorkspaceError(Exception):
    """Raised when a workspace operation fails."""


class WorkspaceManager:
    """Manages isolated workspace clones for agent sessions.

    Workspaces are tracked via a JSON manifest at {base_dir}/workspaces.json.
    File locking prevents races from concurrent workspace creation.
    """

    def __init__(self, config: WorkspaceConfig, project_registry: ProjectRegistry) -> None:
        self._config = config
        self._registry = project_registry
        self._base_dir = Path(config.base_dir).expanduser()
        self._manifest_path = self._base_dir / "workspaces.json"
        self._lock_path = self._base_dir / "workspaces.json.lock"

    def create(
        self,
        project_name: str,
        session_id: str,
        *,
        branch: str = "",
    ) -> WorkspaceInfo:
        """Clone a fresh workspace for a session.

        Args:
            project_name: Name of the registered project.
            session_id: Session identifier (used as workspace ID).
            branch: Optional branch to clone.

        Raises:
            WorkspaceError: If max_workspaces exceeded, project not found,
                repository_url missing, or clone fails.
        """
        project = self._registry.find_by_name(project_name)
        if project is None:
            msg = f"Project '{project_name}' not found in registry"
            raise WorkspaceError(msg)

        if not project.repository_url:
            msg = (
                f"Project '{project_name}' has no repository_url set. "
                f"Use 'autopilot project update-url' to configure it."
            )
            raise WorkspaceError(msg)

        with self._locked():
            manifest = self._read_manifest()

            if len(manifest) >= self._config.max_workspaces:
                msg = (
                    f"max_workspaces limit reached ({self._config.max_workspaces}). "
                    f"Clean up existing workspaces before creating new ones."
                )
                raise WorkspaceError(msg)

            # 8-char truncation of session_id for directory naming
            short_id = session_id[:8]
            workspace_dir = self._base_dir / f"{project_name}-{short_id}"

            result = clone_repository(
                project.repository_url,
                workspace_dir,
                branch=branch,
                depth=self._config.clone_depth,
            )

            if not result.success:
                if workspace_dir.exists():
                    shutil.rmtree(workspace_dir, ignore_errors=True)
                msg = f"Git clone failed: {result.error}"
                raise WorkspaceError(msg)

            # Copy .autopilot/ config from source project into workspace
            source_path = Path(project.path)
            self._copy_autopilot_config(source_path, workspace_dir)

            info = WorkspaceInfo(
                id=session_id,
                project_name=project_name,
                session_id=session_id,
                workspace_dir=workspace_dir,
                repository_url=project.repository_url,
                status=WorkspaceStatus.READY,
                branch=branch,
                clone_depth=self._config.clone_depth,
            )

            manifest[session_id] = self._info_to_dict(info)
            self._write_manifest(manifest)

        _log.info("Created workspace for %s at %s", project_name, workspace_dir)
        return info

    def cleanup(self, workspace_id: str) -> None:
        """Remove a workspace directory and manifest entry.

        Raises:
            WorkspaceError: If workspace not found.
        """
        with self._locked():
            manifest = self._read_manifest()
            if workspace_id not in manifest:
                msg = f"Workspace '{workspace_id}' not found in manifest"
                raise WorkspaceError(msg)

            entry = manifest[workspace_id]
            workspace_dir = Path(entry["workspace_dir"])

            if workspace_dir.exists():
                shutil.rmtree(workspace_dir)
                _log.info("Removed workspace directory: %s", workspace_dir)

            del manifest[workspace_id]
            self._write_manifest(manifest)

    def list_workspaces(self, project_name: str | None = None) -> list[WorkspaceInfo]:
        """List all tracked workspaces, optionally filtered by project."""
        manifest = self._read_manifest()
        workspaces = [self._dict_to_info(v) for v in manifest.values()]
        if project_name is not None:
            workspaces = [w for w in workspaces if w.project_name == project_name]
        return workspaces

    def get_workspace(self, workspace_id: str) -> WorkspaceInfo | None:
        """Get a specific workspace by ID."""
        manifest = self._read_manifest()
        entry = manifest.get(workspace_id)
        if entry is None:
            return None
        return self._dict_to_info(entry)

    def detect_stale(self, get_session_status: SessionStatusLookup) -> list[WorkspaceInfo]:
        """Detect workspaces whose sessions have ended, failed, or been deleted.

        Also scans the filesystem for orphaned directories not tracked in the manifest.

        Args:
            get_session_status: Callback that returns session status for a session ID,
                or None if the session no longer exists.
        """
        manifest = self._read_manifest()
        stale: list[WorkspaceInfo] = []

        for entry in manifest.values():
            info = self._dict_to_info(entry)
            status = get_session_status(info.session_id)
            if status is None or status in (SessionStatus.COMPLETED, SessionStatus.FAILED):
                stale.append(info)

        # Scan for orphaned directories not in the manifest
        if self._base_dir.is_dir():
            tracked_dirs = {Path(e["workspace_dir"]).resolve() for e in manifest.values()}
            for child in self._base_dir.iterdir():
                if not child.is_dir():
                    continue
                # Skip manifest/lock files and non-workspace directories
                if child.resolve() in tracked_dirs:
                    continue
                if child.name.startswith("."):
                    continue
                # Check if it looks like a workspace (has .git)
                if (child / ".git").exists():
                    orphan = WorkspaceInfo(
                        id=f"orphan-{child.name}",
                        project_name="unknown",
                        session_id="unknown",
                        workspace_dir=child,
                        repository_url="",
                        status=WorkspaceStatus.FAILED,
                    )
                    stale.append(orphan)

        return stale

    def disk_usage(self, workspace_id: str | None = None) -> dict[str, Any]:
        """Report disk usage for workspaces.

        Args:
            workspace_id: If provided, report for a single workspace.
                If None, report total and per-workspace breakdown.

        Returns:
            Dict with ``total_bytes`` and ``workspaces`` keys.
        """
        if workspace_id is not None:
            manifest = self._read_manifest()
            entry = manifest.get(workspace_id)
            if entry is None:
                return {"total_bytes": 0, "workspaces": {workspace_id: 0}}
            ws_dir = Path(entry["workspace_dir"])
            size = self._dir_size(ws_dir)
            return {"total_bytes": size, "workspaces": {workspace_id: size}}

        manifest = self._read_manifest()
        per_workspace: dict[str, int] = {}
        total = 0
        for wid, entry in manifest.items():
            ws_dir = Path(entry["workspace_dir"])
            size = self._dir_size(ws_dir)
            per_workspace[wid] = size
            total += size
        return {"total_bytes": total, "workspaces": per_workspace}

    def cleanup_stale(self, get_session_status: SessionStatusLookup) -> list[str]:
        """Detect and clean up all stale workspaces.

        Removes stale workspace directories and prunes manifest entries
        whose directories no longer exist.

        Returns:
            List of cleaned workspace IDs.
        """
        stale = self.detect_stale(get_session_status)
        cleaned: list[str] = []

        for info in stale:
            wid = info.id
            if wid.startswith("orphan-"):
                # Orphaned directory not in manifest — just remove the directory
                if info.workspace_dir.exists():
                    shutil.rmtree(info.workspace_dir, ignore_errors=True)
                    _log.info("Removed orphaned workspace directory: %s", info.workspace_dir)
                cleaned.append(wid)
            else:
                try:
                    self.cleanup(wid)
                    _log.info("Cleaned stale workspace: %s", wid)
                    cleaned.append(wid)
                except (WorkspaceError, OSError):
                    _log.warning("Failed to clean workspace %s, pruning manifest", wid)
                    cleaned.append(wid)

        # Prune any remaining stale manifest entries
        pruned = self._prune_stale_manifest_entries()
        for pid in pruned:
            if pid not in cleaned:
                cleaned.append(pid)

        return cleaned

    def _prune_stale_manifest_entries(self) -> list[str]:
        """Remove manifest entries whose directories no longer exist.

        Returns:
            List of pruned workspace IDs.
        """
        pruned: list[str] = []
        with self._locked():
            manifest = self._read_manifest()
            to_remove: list[str] = []
            for wid, entry in manifest.items():
                ws_dir = Path(entry["workspace_dir"])
                if not ws_dir.exists():
                    to_remove.append(wid)
            for wid in to_remove:
                del manifest[wid]
                pruned.append(wid)
                _log.info("Pruned stale manifest entry: %s", wid)
            if pruned:
                self._write_manifest(manifest)
        return pruned

    @staticmethod
    def _dir_size(path: Path) -> int:
        """Calculate total size of all files in a directory tree."""
        if not path.is_dir():
            return 0
        return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())

    # -- Private helpers --

    @contextmanager
    def _locked(self) -> Iterator[None]:
        """Hold an exclusive lock for manifest read-modify-write."""
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._lock_path.touch()
        with open(self._lock_path) as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lf, fcntl.LOCK_UN)

    def _read_manifest(self) -> dict[str, dict[str, Any]]:
        if not self._manifest_path.exists():
            return {}
        try:
            data = json.loads(self._manifest_path.read_text())
        except (json.JSONDecodeError, OSError):
            _log.warning("Corrupt workspaces.json, returning empty manifest")
            return {}
        if isinstance(data, dict):
            return cast("dict[str, dict[str, Any]]", data)
        return {}

    def _write_manifest(self, data: dict[str, dict[str, Any]]) -> None:
        self._base_dir.mkdir(parents=True, exist_ok=True)
        tmp = self._manifest_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2, default=str))
        tmp.replace(self._manifest_path)

    @staticmethod
    def _copy_autopilot_config(source_project: Path, workspace_dir: Path) -> None:
        """Copy .autopilot/ config into workspace, excluding state/ and logs/."""
        source_ap = source_project / ".autopilot"
        if not source_ap.is_dir():
            return

        target_ap = workspace_dir / ".autopilot"
        target_ap.mkdir(exist_ok=True)

        for item in source_ap.iterdir():
            if item.name in _EXCLUDED_SUBDIRS:
                continue
            if item.is_dir():
                shutil.copytree(item, target_ap / item.name, dirs_exist_ok=True)
            else:
                shutil.copy2(item, target_ap / item.name)

    @staticmethod
    def _info_to_dict(info: WorkspaceInfo) -> dict[str, Any]:
        return {
            "id": info.id,
            "project_name": info.project_name,
            "session_id": info.session_id,
            "workspace_dir": str(info.workspace_dir),
            "repository_url": info.repository_url,
            "status": info.status.value,
            "created_at": info.created_at.isoformat(),
            "cleaned_at": info.cleaned_at.isoformat() if info.cleaned_at else None,
            "branch": info.branch,
            "clone_depth": info.clone_depth,
        }

    @staticmethod
    def _dict_to_info(d: dict[str, Any]) -> WorkspaceInfo:
        return WorkspaceInfo(
            id=d["id"],
            project_name=d["project_name"],
            session_id=d["session_id"],
            workspace_dir=Path(d["workspace_dir"]),
            repository_url=d["repository_url"],
            status=WorkspaceStatus(d["status"]),
            created_at=datetime.fromisoformat(d["created_at"]),
            cleaned_at=(datetime.fromisoformat(d["cleaned_at"]) if d.get("cleaned_at") else None),
            branch=d.get("branch", ""),
            clone_depth=d.get("clone_depth", 0),
        )
