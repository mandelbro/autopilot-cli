"""Tests for autopilot.core.workspace (Task 097)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from autopilot.core.config import WorkspaceConfig
from autopilot.core.models import WorkspaceStatus
from autopilot.core.project import ProjectRegistry
from autopilot.core.workspace import WorkspaceError, WorkspaceManager


def _make_git_repo(path: Path) -> Path:
    """Initialize a minimal git repository for testing."""
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", str(path)], capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=path,
        capture_output=True,
        check=True,
    )
    (path / "README.md").write_text("init")
    subprocess.run(["git", "add", "."], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, capture_output=True, check=True)
    return path


@pytest.fixture()
def workspace_setup(tmp_path: Path) -> tuple[WorkspaceConfig, ProjectRegistry, Path]:
    """Set up a workspace manager test environment."""
    base_dir = tmp_path / "workspaces"
    config = WorkspaceConfig(enabled=True, base_dir=str(base_dir), max_workspaces=3)

    # Create a source repo
    source_repo = _make_git_repo(tmp_path / "source-repo")

    # Set up .autopilot/ in source project
    autopilot_dir = source_repo / ".autopilot"
    autopilot_dir.mkdir()
    (autopilot_dir / "config.yaml").write_text("project:\n  name: test\n")
    (autopilot_dir / "agents").mkdir()
    (autopilot_dir / "agents" / "test.md").write_text("agent prompt")
    # These should be excluded from copy
    (autopilot_dir / "state").mkdir()
    (autopilot_dir / "state" / "data.json").write_text("{}")
    (autopilot_dir / "logs").mkdir()
    (autopilot_dir / "logs" / "session.log").write_text("log")

    registry = ProjectRegistry(global_dir=tmp_path / "global")
    registry.register("test-project", str(source_repo), "python", repository_url=str(source_repo))

    return config, registry, base_dir


class TestWorkspaceError:
    def test_is_exception(self) -> None:
        err = WorkspaceError("test error")
        assert isinstance(err, Exception)
        assert str(err) == "test error"


class TestWorkspaceManagerCreate:
    def test_creates_workspace(
        self, workspace_setup: tuple[WorkspaceConfig, ProjectRegistry, Path]
    ) -> None:
        config, registry, base_dir = workspace_setup
        mgr = WorkspaceManager(config, registry)
        info = mgr.create("test-project", "session-12345678-abcd")

        assert info.status == WorkspaceStatus.READY
        assert info.project_name == "test-project"
        assert info.session_id == "session-12345678-abcd"
        assert info.workspace_dir.exists()
        assert (info.workspace_dir / "README.md").exists()

    def test_workspace_dir_naming(
        self, workspace_setup: tuple[WorkspaceConfig, ProjectRegistry, Path]
    ) -> None:
        config, registry, base_dir = workspace_setup
        mgr = WorkspaceManager(config, registry)
        info = mgr.create("test-project", "session-12345678-abcd")
        # First 8 chars of "session-12345678-abcd" is "session-"
        assert info.workspace_dir.name == "test-project-session-"

    def test_copies_autopilot_config(
        self, workspace_setup: tuple[WorkspaceConfig, ProjectRegistry, Path]
    ) -> None:
        config, registry, base_dir = workspace_setup
        mgr = WorkspaceManager(config, registry)
        info = mgr.create("test-project", "session-12345678-abcd")

        ws_autopilot = info.workspace_dir / ".autopilot"
        assert ws_autopilot.exists()
        assert (ws_autopilot / "config.yaml").exists()
        assert (ws_autopilot / "agents" / "test.md").exists()

    def test_excludes_state_and_logs(
        self, workspace_setup: tuple[WorkspaceConfig, ProjectRegistry, Path]
    ) -> None:
        config, registry, base_dir = workspace_setup
        mgr = WorkspaceManager(config, registry)
        info = mgr.create("test-project", "session-12345678-abcd")

        ws_autopilot = info.workspace_dir / ".autopilot"
        assert not (ws_autopilot / "state").exists()
        assert not (ws_autopilot / "logs").exists()

    def test_max_workspaces_enforced(
        self, workspace_setup: tuple[WorkspaceConfig, ProjectRegistry, Path]
    ) -> None:
        config, registry, base_dir = workspace_setup  # max_workspaces=3
        mgr = WorkspaceManager(config, registry)
        mgr.create("test-project", "aaaaaaaa-0001")
        mgr.create("test-project", "bbbbbbbb-0002")
        mgr.create("test-project", "cccccccc-0003")

        with pytest.raises(WorkspaceError, match="max_workspaces"):
            mgr.create("test-project", "dddddddd-0004")

    def test_missing_repository_url_raises(self, tmp_path: Path) -> None:
        config = WorkspaceConfig(enabled=True, base_dir=str(tmp_path / "ws"))
        registry = ProjectRegistry(global_dir=tmp_path / "global")
        registry.register("no-url", "/tmp/no-url", "python")
        mgr = WorkspaceManager(config, registry)

        with pytest.raises(WorkspaceError, match="repository_url"):
            mgr.create("no-url", "session-00000001")

    def test_unregistered_project_raises(
        self, workspace_setup: tuple[WorkspaceConfig, ProjectRegistry, Path]
    ) -> None:
        config, registry, base_dir = workspace_setup
        mgr = WorkspaceManager(config, registry)

        with pytest.raises(WorkspaceError, match="not found"):
            mgr.create("nonexistent-project", "session-00000001")

    def test_creates_with_branch(
        self, workspace_setup: tuple[WorkspaceConfig, ProjectRegistry, Path]
    ) -> None:
        config, registry, base_dir = workspace_setup
        # Detect the actual default branch name (main or master)
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=registry.find_by_name("test-project").path,  # type: ignore[union-attr]
            capture_output=True,
            text=True,
            check=True,
        )
        branch = result.stdout.strip()
        mgr = WorkspaceManager(config, registry)
        info = mgr.create("test-project", "session-12345678", branch=branch)
        assert info.branch == branch
        assert info.status == WorkspaceStatus.READY

    def test_clone_failure_cleans_partial_dir_and_skips_manifest(
        self, workspace_setup: tuple[WorkspaceConfig, ProjectRegistry, Path]
    ) -> None:
        """When clone fails, partial directory is removed and manifest is not updated."""
        config, registry, base_dir = workspace_setup
        mgr = WorkspaceManager(config, registry)

        # Register a project with a valid-looking but nonexistent repo path to trigger clone failure
        registry.register(
            "bad-project", "/tmp/bad", "python", repository_url="/nonexistent/repo/path"
        )

        with pytest.raises(WorkspaceError, match="Git clone failed"):
            mgr.create("bad-project", "session-12345678")

        # Verify no workspace directory left behind
        expected_dir = base_dir / "bad-project-session-"
        assert not expected_dir.exists()

        # Verify manifest was not updated
        assert mgr.list_workspaces() == []

    def test_no_autopilot_dir_in_source_skips_copy(self, tmp_path: Path) -> None:
        """When source project has no .autopilot/ dir, workspace is still created."""
        base_dir = tmp_path / "workspaces"
        config = WorkspaceConfig(enabled=True, base_dir=str(base_dir))

        # Create a source repo WITHOUT .autopilot/
        source = _make_git_repo(tmp_path / "no-autopilot-repo")

        registry = ProjectRegistry(global_dir=tmp_path / "global")
        registry.register("no-ap", str(source), "python", repository_url=str(source))

        mgr = WorkspaceManager(config, registry)
        info = mgr.create("no-ap", "session-12345678")

        assert info.status == WorkspaceStatus.READY
        assert (info.workspace_dir / "README.md").exists()
        # .autopilot/ should not exist in workspace since source doesn't have it
        assert not (info.workspace_dir / ".autopilot").exists()


class TestWorkspaceManagerCleanup:
    def test_cleanup_removes_directory(
        self, workspace_setup: tuple[WorkspaceConfig, ProjectRegistry, Path]
    ) -> None:
        config, registry, base_dir = workspace_setup
        mgr = WorkspaceManager(config, registry)
        info = mgr.create("test-project", "session-12345678")
        assert info.workspace_dir.exists()

        mgr.cleanup(info.id)
        assert not info.workspace_dir.exists()

    def test_cleanup_removes_from_manifest(
        self, workspace_setup: tuple[WorkspaceConfig, ProjectRegistry, Path]
    ) -> None:
        config, registry, base_dir = workspace_setup
        mgr = WorkspaceManager(config, registry)
        info = mgr.create("test-project", "session-12345678")
        mgr.cleanup(info.id)

        assert mgr.get_workspace(info.id) is None

    def test_cleanup_nonexistent_raises(
        self, workspace_setup: tuple[WorkspaceConfig, ProjectRegistry, Path]
    ) -> None:
        config, registry, base_dir = workspace_setup
        mgr = WorkspaceManager(config, registry)

        with pytest.raises(WorkspaceError, match="not found"):
            mgr.cleanup("nonexistent-id")


class TestWorkspaceManagerList:
    def test_list_empty(
        self, workspace_setup: tuple[WorkspaceConfig, ProjectRegistry, Path]
    ) -> None:
        config, registry, base_dir = workspace_setup
        mgr = WorkspaceManager(config, registry)
        assert mgr.list_workspaces() == []

    def test_list_all(self, workspace_setup: tuple[WorkspaceConfig, ProjectRegistry, Path]) -> None:
        config, registry, base_dir = workspace_setup
        mgr = WorkspaceManager(config, registry)
        mgr.create("test-project", "eeeeeeee-0001")
        mgr.create("test-project", "ffffffff-0002")

        workspaces = mgr.list_workspaces()
        assert len(workspaces) == 2

    def test_list_filtered_by_project(
        self, workspace_setup: tuple[WorkspaceConfig, ProjectRegistry, Path]
    ) -> None:
        config, registry, base_dir = workspace_setup
        # Register a second project
        source2 = _make_git_repo(Path(str(base_dir)).parent / "source2")
        registry.register("other-project", str(source2), "python", repository_url=str(source2))

        mgr = WorkspaceManager(config, registry)
        mgr.create("test-project", "gggggggg-0001")
        mgr.create("other-project", "hhhhhhhh-0002")

        filtered = mgr.list_workspaces(project_name="test-project")
        assert len(filtered) == 1
        assert filtered[0].project_name == "test-project"


class TestWorkspaceManagerGet:
    def test_get_existing(
        self, workspace_setup: tuple[WorkspaceConfig, ProjectRegistry, Path]
    ) -> None:
        config, registry, base_dir = workspace_setup
        mgr = WorkspaceManager(config, registry)
        created = mgr.create("test-project", "session-12345678")

        found = mgr.get_workspace(created.id)
        assert found is not None
        assert found.id == created.id

    def test_get_nonexistent(
        self, workspace_setup: tuple[WorkspaceConfig, ProjectRegistry, Path]
    ) -> None:
        config, registry, base_dir = workspace_setup
        mgr = WorkspaceManager(config, registry)
        assert mgr.get_workspace("nonexistent") is None


class TestWorkspaceManifest:
    def test_manifest_file_created(
        self, workspace_setup: tuple[WorkspaceConfig, ProjectRegistry, Path]
    ) -> None:
        config, registry, base_dir = workspace_setup
        mgr = WorkspaceManager(config, registry)
        mgr.create("test-project", "session-12345678")

        manifest = base_dir / "workspaces.json"
        assert manifest.exists()
        data = json.loads(manifest.read_text())
        assert len(data) == 1

    def test_manifest_persists_across_instances(
        self, workspace_setup: tuple[WorkspaceConfig, ProjectRegistry, Path]
    ) -> None:
        config, registry, base_dir = workspace_setup
        mgr1 = WorkspaceManager(config, registry)
        mgr1.create("test-project", "session-12345678")

        mgr2 = WorkspaceManager(config, registry)
        workspaces = mgr2.list_workspaces()
        assert len(workspaces) == 1
