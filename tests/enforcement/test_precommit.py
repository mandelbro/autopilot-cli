"""Tests for the pre-commit hook setup (Task 061)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from autopilot.enforcement.precommit import PrecommitSetup


@pytest.fixture()
def setup() -> PrecommitSetup:
    return PrecommitSetup()


class TestGenerateConfig:
    def test_python_returns_dict(self, setup: PrecommitSetup) -> None:
        config = setup.generate_config("python")
        assert isinstance(config, dict)
        assert "pre-commit" in config

    def test_python_has_ruff_lint(self, setup: PrecommitSetup) -> None:
        config = setup.generate_config("python")
        commands = config["pre-commit"]["commands"]
        assert "lint" in commands
        assert "ruff" in commands["lint"]["run"]

    def test_python_has_ruff_format(self, setup: PrecommitSetup) -> None:
        config = setup.generate_config("python")
        commands = config["pre-commit"]["commands"]
        assert "format" in commands
        assert "ruff format" in commands["format"]["run"]

    def test_python_has_pyright(self, setup: PrecommitSetup) -> None:
        config = setup.generate_config("python")
        commands = config["pre-commit"]["commands"]
        assert "typecheck" in commands
        assert "pyright" in commands["typecheck"]["run"]

    def test_typescript_has_eslint(self, setup: PrecommitSetup) -> None:
        config = setup.generate_config("typescript")
        commands = config["pre-commit"]["commands"]
        assert "lint" in commands
        assert "eslint" in commands["lint"]["run"]

    def test_typescript_has_tsc(self, setup: PrecommitSetup) -> None:
        config = setup.generate_config("typescript")
        commands = config["pre-commit"]["commands"]
        assert "typecheck" in commands
        assert "tsc" in commands["typecheck"]["run"]

    def test_parallel_enabled(self, setup: PrecommitSetup) -> None:
        config = setup.generate_config("python")
        assert config["pre-commit"]["parallel"] is True

    def test_typescript_parallel_enabled(self, setup: PrecommitSetup) -> None:
        config = setup.generate_config("typescript")
        assert config["pre-commit"]["parallel"] is True


class TestAddBlockNoVerify:
    def test_adds_block_command(self, setup: PrecommitSetup) -> None:
        config = setup.generate_config("python")
        setup.add_block_no_verify(config)
        commands = config["pre-commit"]["commands"]
        assert "block-no-verify" in commands

    def test_block_command_exits_nonzero(self, setup: PrecommitSetup) -> None:
        config = setup.generate_config("python")
        setup.add_block_no_verify(config)
        cmd = config["pre-commit"]["commands"]["block-no-verify"]
        assert "exit 1" in cmd["run"]

    def test_block_command_disallows_skip(self, setup: PrecommitSetup) -> None:
        config = setup.generate_config("python")
        setup.add_block_no_verify(config)
        cmd = config["pre-commit"]["commands"]["block-no-verify"]
        assert cmd["env"]["LEFTHOOK_ALLOW_SKIP"] == "never"


class TestAddDetectSecrets:
    def test_adds_detect_secrets_hook(self, setup: PrecommitSetup) -> None:
        config = setup.generate_config("python")
        setup.add_detect_secrets(config)
        commands = config["pre-commit"]["commands"]
        assert "detect-secrets" in commands

    def test_detect_secrets_runs_hook(self, setup: PrecommitSetup) -> None:
        config = setup.generate_config("python")
        setup.add_detect_secrets(config)
        cmd = config["pre-commit"]["commands"]["detect-secrets"]
        assert "detect-secrets-hook" in cmd["run"]

    def test_detect_secrets_glob_all(self, setup: PrecommitSetup) -> None:
        config = setup.generate_config("python")
        setup.add_detect_secrets(config)
        cmd = config["pre-commit"]["commands"]["detect-secrets"]
        assert cmd["glob"] == "*"


class TestApply:
    def test_writes_lefthook_yml(self, setup: PrecommitSetup, tmp_path: Path) -> None:
        result = setup.apply(tmp_path, "python")
        lefthook_path = tmp_path / "lefthook.yml"
        assert lefthook_path.exists()
        assert result.success is True

    def test_result_contains_lefthook_path(self, setup: PrecommitSetup, tmp_path: Path) -> None:
        result = setup.apply(tmp_path, "python")
        assert any("lefthook.yml" in f for f in result.files_created)

    def test_result_contains_install_script(self, setup: PrecommitSetup, tmp_path: Path) -> None:
        result = setup.apply(tmp_path, "python")
        assert any("install-lefthook.sh" in f for f in result.files_created)

    def test_result_layer_is_precommit(self, setup: PrecommitSetup, tmp_path: Path) -> None:
        result = setup.apply(tmp_path, "python")
        assert result.layer == "precommit"

    def test_lefthook_yml_contains_parallel(
        self, setup: PrecommitSetup, tmp_path: Path
    ) -> None:
        setup.apply(tmp_path, "python")
        content = (tmp_path / "lefthook.yml").read_text()
        assert "parallel: true" in content

    def test_lefthook_yml_contains_detect_secrets(
        self, setup: PrecommitSetup, tmp_path: Path
    ) -> None:
        setup.apply(tmp_path, "python")
        content = (tmp_path / "lefthook.yml").read_text()
        assert "detect-secrets" in content

    def test_lefthook_yml_contains_block_no_verify(
        self, setup: PrecommitSetup, tmp_path: Path
    ) -> None:
        setup.apply(tmp_path, "python")
        content = (tmp_path / "lefthook.yml").read_text()
        assert "block-no-verify" in content


class TestInstallLefthook:
    def test_creates_install_script(self, setup: PrecommitSetup, tmp_path: Path) -> None:
        result = setup.install_lefthook(tmp_path)
        script = tmp_path / "scripts" / "install-lefthook.sh"
        assert script.exists()
        assert result.success is True

    def test_script_is_executable(self, setup: PrecommitSetup, tmp_path: Path) -> None:
        setup.install_lefthook(tmp_path)
        script = tmp_path / "scripts" / "install-lefthook.sh"
        assert script.stat().st_mode & 0o111
