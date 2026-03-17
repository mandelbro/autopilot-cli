"""Tests for debugging CLI commands (Tasks 011-013)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from typer.testing import CliRunner

import autopilot.cli.debug as _debug_mod
from autopilot.cli.debug import debug_app
from autopilot.core.config import (
    AutopilotConfig,
    DebuggingConfig,
    DebuggingToolConfig,
    ProjectConfig,
)
from autopilot.debugging.tools.protocol import ProvisionResult, ProvisionStatus

runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_TOOL_CFG = DebuggingToolConfig(
    module="autopilot.debugging.tools.browser_mcp", class_name="BrowserMCPTool"
)

_DEBUG_CFG = DebuggingConfig(
    enabled=True,
    tool="browser_mcp",
    tools={"browser_mcp": _TOOL_CFG},
)


def _patch_resolve(
    cfg: DebuggingConfig = _DEBUG_CFG, root: Path | None = None, config: Path | None = None
):
    """Return a patch context manager for _resolve_debug_config."""
    r = root or Path("/tmp")
    c = config or Path("/tmp/config.yaml")
    return patch.object(_debug_mod, "_resolve_debug_config", return_value=(cfg, r, c))


@pytest.fixture()
def task_yaml(tmp_path: Path) -> Path:
    """Create a minimal debugging task YAML file."""
    task_data = {
        "task_id": "T001",
        "feature": "login",
        "title": "Test login flow",
        "description": "Verify login works",
        "staging_url": "http://localhost:3000",
        "steps": [{"action": "navigate", "target": "http://localhost:3000/login"}],
        "acceptance_criteria": ["Login page loads"],
        "source_scope": ["src/auth/"],
    }
    path = tmp_path / "task.yaml"
    path.write_text(yaml.dump(task_data), encoding="utf-8")
    return path


@pytest.fixture()
def config_dir(tmp_path: Path) -> Path:
    """Create a minimal .autopilot directory with config."""
    ap_dir = tmp_path / ".autopilot"
    ap_dir.mkdir()
    cfg = AutopilotConfig(
        project=ProjectConfig(name="test-proj"),
        debugging=_DEBUG_CFG,
    )
    config_path = ap_dir / "config.yaml"
    config_path.write_text(
        yaml.dump(cfg.model_dump(mode="json"), default_flow_style=False),
        encoding="utf-8",
    )
    return tmp_path


# ---------------------------------------------------------------------------
# Task 011: run command
# ---------------------------------------------------------------------------


class TestDebugRun:
    def test_run_missing_task_file(self) -> None:
        with _patch_resolve():
            result = runner.invoke(debug_app, ["run", "/nonexistent/task.yaml"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_run_dry_run(self, task_yaml: Path) -> None:
        with _patch_resolve():
            result = runner.invoke(debug_app, ["run", str(task_yaml), "--dry-run"])
        assert result.exit_code == 0
        assert "dry run" in result.output.lower()
        assert "T001" in result.output

    def test_run_tool_not_provisioned(self, task_yaml: Path) -> None:
        mock_tool = MagicMock()
        mock_tool.check_provisioned.return_value = ProvisionStatus(
            provisioned=False, ready=False, message="Not installed"
        )
        with (
            _patch_resolve(),
            patch("autopilot.debugging.loader.load_debugging_tool", return_value=mock_tool),
        ):
            result = runner.invoke(debug_app, ["run", str(task_yaml)])
        assert result.exit_code == 1
        assert "not provisioned" in result.output.lower()


# ---------------------------------------------------------------------------
# Task 011: list-tools command
# ---------------------------------------------------------------------------


class TestDebugListTools:
    def test_list_tools_empty(self) -> None:
        empty_cfg = DebuggingConfig(enabled=False, tools={})
        with _patch_resolve(cfg=empty_cfg):
            result = runner.invoke(debug_app, ["list-tools"])
        assert result.exit_code == 0
        assert "no debugging tools" in result.output.lower()

    def test_list_tools_shows_registered(self) -> None:
        mock_tool = MagicMock()
        mock_tool.check_provisioned.return_value = ProvisionStatus(provisioned=True, ready=True)
        mock_tool.capabilities = frozenset(["interactive_test"])
        with (
            _patch_resolve(),
            patch("autopilot.debugging.loader.load_debugging_tool", return_value=mock_tool),
        ):
            result = runner.invoke(debug_app, ["list-tools"])
        assert result.exit_code == 0
        assert "browser_mcp" in result.output


# ---------------------------------------------------------------------------
# Task 011: status command
# ---------------------------------------------------------------------------


class TestDebugStatus:
    def test_status_shows_config(self) -> None:
        with _patch_resolve():
            result = runner.invoke(debug_app, ["status"])
        assert result.exit_code == 0
        assert "browser_mcp" in result.output
        assert "True" in result.output  # enabled


# ---------------------------------------------------------------------------
# Task 012: add-tool command
# ---------------------------------------------------------------------------


class TestDebugAddTool:
    def test_add_tool_valid(self, config_dir: Path) -> None:
        config_path = config_dir / ".autopilot" / "config.yaml"

        mock_mod = MagicMock()
        mock_mod.FakeTool = MagicMock()

        with (
            _patch_resolve(root=config_dir, config=config_path),
            patch.object(_debug_mod, "importlib") as mock_imp,
            patch.object(_debug_mod, "_validate_plugin", return_value=(True, "Valid")),
            patch.object(_debug_mod, "_load_modify_save_config") as mock_save,
        ):
            mock_imp.import_module.return_value = mock_mod
            result = runner.invoke(
                debug_app,
                ["add-tool", "fake_tool", "--module", "fake.module", "--class", "FakeTool"],
            )
        assert result.exit_code == 0, f"output: {result.output}"
        assert "registered" in result.output.lower()
        mock_save.assert_called_once()

    def test_add_tool_invalid_protocol(self) -> None:
        mock_mod = MagicMock()
        mock_mod.BadTool = MagicMock()

        with (
            _patch_resolve(),
            patch.object(_debug_mod, "importlib") as mock_imp,
            patch.object(
                _debug_mod,
                "_validate_plugin",
                return_value=(False, "Missing required attributes: name"),
            ),
        ):
            mock_imp.import_module.return_value = mock_mod
            result = runner.invoke(
                debug_app,
                ["add-tool", "bad_tool", "--module", "fake.module", "--class", "BadTool"],
            )
        assert result.exit_code == 1
        assert "validation failed" in result.output.lower()


# ---------------------------------------------------------------------------
# Task 012: remove-tool command
# ---------------------------------------------------------------------------


class TestDebugRemoveTool:
    def test_remove_existing_tool(self, config_dir: Path) -> None:
        config_path = config_dir / ".autopilot" / "config.yaml"
        with (
            _patch_resolve(root=config_dir, config=config_path),
            patch.object(_debug_mod, "_load_modify_save_config"),
        ):
            result = runner.invoke(debug_app, ["remove-tool", "browser_mcp"])
        assert result.exit_code == 0
        assert "warning" in result.output.lower()  # active tool warning
        assert "removed" in result.output.lower()

    def test_remove_nonexistent_tool(self) -> None:
        with _patch_resolve():
            result = runner.invoke(debug_app, ["remove-tool", "nonexistent"])
        assert result.exit_code == 1
        assert "not registered" in result.output.lower()


# ---------------------------------------------------------------------------
# Task 012: validate-tool command
# ---------------------------------------------------------------------------


class TestDebugValidateTool:
    def test_validate_valid_tool(self) -> None:
        mock_mod = MagicMock()
        mock_mod.BrowserMCPTool = MagicMock()
        with (
            _patch_resolve(),
            patch.object(_debug_mod, "importlib") as mock_imp,
            patch.object(_debug_mod, "_validate_plugin", return_value=(True, "Valid")),
        ):
            mock_imp.import_module.return_value = mock_mod
            result = runner.invoke(debug_app, ["validate-tool", "browser_mcp"])
        assert result.exit_code == 0
        assert "valid" in result.output.lower()

    def test_validate_invalid_tool(self) -> None:
        mock_mod = MagicMock()
        mock_mod.BrowserMCPTool = MagicMock()
        with (
            _patch_resolve(),
            patch.object(_debug_mod, "importlib") as mock_imp,
            patch.object(_debug_mod, "_validate_plugin", return_value=(False, "Missing name")),
        ):
            mock_imp.import_module.return_value = mock_mod
            result = runner.invoke(debug_app, ["validate-tool", "browser_mcp"])
        assert result.exit_code == 1
        assert "invalid" in result.output.lower()


# ---------------------------------------------------------------------------
# Task 012: provision / deprovision commands
# ---------------------------------------------------------------------------


class TestDebugProvision:
    def test_provision_success(self) -> None:
        mock_tool = MagicMock()
        mock_tool.provision.return_value = ProvisionResult(
            success=True, components_installed=("playwright",)
        )
        with (
            _patch_resolve(),
            patch("autopilot.debugging.loader.load_debugging_tool", return_value=mock_tool),
        ):
            result = runner.invoke(debug_app, ["provision", "browser_mcp"])
        assert result.exit_code == 0
        assert "provisioned" in result.output.lower()

    def test_provision_unregistered_tool(self) -> None:
        with _patch_resolve():
            result = runner.invoke(debug_app, ["provision", "nonexistent"])
        assert result.exit_code == 1
        assert "not registered" in result.output.lower()


class TestDebugDeprovision:
    def test_deprovision_with_force(self) -> None:
        mock_tool = MagicMock()
        with (
            _patch_resolve(),
            patch("autopilot.debugging.loader.load_debugging_tool", return_value=mock_tool),
        ):
            result = runner.invoke(debug_app, ["deprovision", "browser_mcp", "--force"])
        assert result.exit_code == 0
        assert "deprovisioned" in result.output.lower()
        mock_tool.deprovision.assert_called_once()

    def test_deprovision_unregistered_tool(self) -> None:
        with _patch_resolve():
            result = runner.invoke(debug_app, ["deprovision", "nonexistent", "--force"])
        assert result.exit_code == 1
        assert "not registered" in result.output.lower()


# ---------------------------------------------------------------------------
# Task 013: Config mutation via add-tool writes valid YAML
# ---------------------------------------------------------------------------


class TestConfigMutation:
    def test_load_modify_save_roundtrip(self, tmp_path: Path) -> None:
        """YAML written by add-tool can be reloaded by AutopilotConfig.from_yaml()."""
        from autopilot.cli.debug import _load_modify_save_config

        config_path = tmp_path / "config.yaml"
        initial = {
            "project": {"name": "roundtrip-test"},
            "debugging": {"enabled": False, "tool": "browser_mcp", "tools": {}},
        }
        config_path.write_text(yaml.dump(initial), encoding="utf-8")

        def _add(raw: dict) -> None:
            raw["debugging"]["tools"]["new_tool"] = {
                "module": "some.module",
                "class": "SomeTool",
            }

        _load_modify_save_config(config_path, _add)

        # Verify YAML on disk uses 'class' alias, not 'class_name'
        yaml_text = config_path.read_text(encoding="utf-8")
        assert "class: SomeTool" in yaml_text
        assert "class_name" not in yaml_text

        # Verify roundtrip: re-load from disk
        reloaded = AutopilotConfig.from_yaml(config_path)
        assert "new_tool" in reloaded.debugging.tools
        assert reloaded.debugging.tools["new_tool"].module == "some.module"
        assert reloaded.debugging.tools["new_tool"].class_name == "SomeTool"

    def test_load_modify_save_creates_file(self, tmp_path: Path) -> None:
        """Config mutation creates config.yaml if it doesn't exist."""
        from autopilot.cli.debug import _load_modify_save_config

        config_path = tmp_path / "new_dir" / "config.yaml"

        def _add(raw: dict) -> None:
            raw["project"] = {"name": "new-proj"}
            raw.setdefault("debugging", {})["enabled"] = True

        result_cfg = _load_modify_save_config(config_path, _add)
        assert config_path.exists()
        assert result_cfg.debugging.enabled is True
