"""Tests for RepEngine layout migration engine (Task 082)."""

from __future__ import annotations

import json
from pathlib import Path  # noqa: TC003 — used at runtime

import pytest
import yaml

from autopilot.core.migration import MigrationEngine


@pytest.fixture
def engine() -> MigrationEngine:
    return MigrationEngine()


def _make_repengine_layout(root: Path) -> Path:
    """Create a minimal RepEngine autopilot/ directory structure."""
    ap = root / "autopilot"
    ap.mkdir()

    # Config
    config = {"project_name": "test-project", "project_type": "python"}
    (ap / "config.yaml").write_text(yaml.dump(config))

    # Agents
    agents = ap / "agents"
    agents.mkdir()
    (agents / "coder.md").write_text("# Coder Agent\nPrompt content.")
    (agents / "reviewer.md").write_text("# Reviewer Agent\nReview prompt.")

    # Board
    board = ap / "board"
    board.mkdir()
    (board / "decisions.md").write_text("# Decisions\n- Decision 1")

    # State files
    (ap / "usage-tracker.json").write_text(json.dumps({"total_tokens": 1000}))
    (ap / "hive-sessions.json").write_text(json.dumps({"sessions": []}))

    return ap


class TestDetectRepengineLayout:
    def test_detects_valid_repengine_layout(self, tmp_path: Path, engine: MigrationEngine) -> None:
        _make_repengine_layout(tmp_path)
        assert engine.detect_repengine_layout(tmp_path) is True

    def test_rejects_when_no_autopilot_dir(self, tmp_path: Path, engine: MigrationEngine) -> None:
        assert engine.detect_repengine_layout(tmp_path) is False

    def test_rejects_when_dot_autopilot_exists(
        self, tmp_path: Path, engine: MigrationEngine
    ) -> None:
        (tmp_path / "autopilot").mkdir()
        (tmp_path / ".autopilot").mkdir()
        assert engine.detect_repengine_layout(tmp_path) is False

    def test_rejects_when_autopilot_is_file(self, tmp_path: Path, engine: MigrationEngine) -> None:
        (tmp_path / "autopilot").write_text("not a directory")
        assert engine.detect_repengine_layout(tmp_path) is False


class TestMigrate:
    def test_creates_dot_autopilot_structure(self, tmp_path: Path, engine: MigrationEngine) -> None:
        _make_repengine_layout(tmp_path)
        result = engine.migrate(tmp_path)

        assert result.success is True
        assert (tmp_path / ".autopilot").is_dir()
        assert (tmp_path / ".autopilot" / "agents").is_dir()
        assert (tmp_path / ".autopilot" / "board").is_dir()
        assert (tmp_path / ".autopilot" / "state").is_dir()
        assert (tmp_path / ".autopilot" / "logs").is_dir()

    def test_copies_agent_files(self, tmp_path: Path, engine: MigrationEngine) -> None:
        _make_repengine_layout(tmp_path)
        result = engine.migrate(tmp_path)

        assert result.success is True
        assert (tmp_path / ".autopilot" / "agents" / "coder.md").exists()
        assert (tmp_path / ".autopilot" / "agents" / "reviewer.md").exists()
        assert "agents/coder.md" in result.files_copied
        assert "agents/reviewer.md" in result.files_copied

    def test_copies_board_files(self, tmp_path: Path, engine: MigrationEngine) -> None:
        _make_repengine_layout(tmp_path)
        result = engine.migrate(tmp_path)

        assert result.success is True
        assert (tmp_path / ".autopilot" / "board" / "decisions.md").exists()
        assert "board/decisions.md" in result.files_copied

    def test_maps_config(self, tmp_path: Path, engine: MigrationEngine) -> None:
        _make_repengine_layout(tmp_path)
        result = engine.migrate(tmp_path)

        assert result.success is True
        assert result.config_mapped is True
        config_path = tmp_path / ".autopilot" / "config.yaml"
        assert config_path.exists()
        config = yaml.safe_load(config_path.read_text())
        assert config["project_name"] == "test-project"

    def test_converts_state_files(self, tmp_path: Path, engine: MigrationEngine) -> None:
        _make_repengine_layout(tmp_path)
        result = engine.migrate(tmp_path)

        assert result.success is True
        assert result.state_converted is True
        assert (tmp_path / ".autopilot" / "autopilot.db").exists()

    def test_preserves_original_directory(self, tmp_path: Path, engine: MigrationEngine) -> None:
        _make_repengine_layout(tmp_path)
        engine.migrate(tmp_path)

        # Original directory must still exist with all files
        assert (tmp_path / "autopilot").is_dir()
        assert (tmp_path / "autopilot" / "agents" / "coder.md").exists()
        assert (tmp_path / "autopilot" / "config.yaml").exists()

    def test_generates_gitignore(self, tmp_path: Path, engine: MigrationEngine) -> None:
        _make_repengine_layout(tmp_path)
        result = engine.migrate(tmp_path)

        assert result.success is True
        gitignore = tmp_path / ".autopilot" / ".gitignore"
        assert gitignore.exists()
        content = gitignore.read_text()
        assert "state/" in content
        assert "logs/" in content

    def test_dry_run_makes_no_changes(self, tmp_path: Path, engine: MigrationEngine) -> None:
        _make_repengine_layout(tmp_path)
        result = engine.migrate(tmp_path, dry_run=True)

        assert result.success is True
        assert not (tmp_path / ".autopilot").exists()
        # Should still report what would be copied
        assert len(result.files_copied) > 0

    def test_fails_when_target_exists(self, tmp_path: Path, engine: MigrationEngine) -> None:
        _make_repengine_layout(tmp_path)
        (tmp_path / ".autopilot").mkdir()

        result = engine.migrate(tmp_path)

        assert result.success is False
        assert any("already exists" in e for e in result.errors)

    def test_fails_when_source_missing(self, tmp_path: Path, engine: MigrationEngine) -> None:
        result = engine.migrate(tmp_path)

        assert result.success is False
        assert any("not found" in e for e in result.errors)

    def test_handles_missing_agents_dir(self, tmp_path: Path, engine: MigrationEngine) -> None:
        ap = tmp_path / "autopilot"
        ap.mkdir()
        (ap / "config.yaml").write_text(yaml.dump({"project_name": "bare"}))

        result = engine.migrate(tmp_path)

        assert result.success is True
        assert not any("agents/" in f for f in result.files_copied)

    def test_handles_json_config(self, tmp_path: Path, engine: MigrationEngine) -> None:
        ap = tmp_path / "autopilot"
        ap.mkdir()
        (ap / "config.json").write_text(json.dumps({"project_name": "json-proj"}))

        result = engine.migrate(tmp_path)

        assert result.success is True
        assert result.config_mapped is True

    def test_handles_no_config(self, tmp_path: Path, engine: MigrationEngine) -> None:
        ap = tmp_path / "autopilot"
        ap.mkdir()

        result = engine.migrate(tmp_path)

        assert result.success is True
        assert result.config_mapped is False

    def test_handles_no_state_files(self, tmp_path: Path, engine: MigrationEngine) -> None:
        ap = tmp_path / "autopilot"
        ap.mkdir()

        result = engine.migrate(tmp_path)

        assert result.success is True
        assert result.state_converted is False
