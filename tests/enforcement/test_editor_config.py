"""Tests for the editor config generator (Task 060)."""

from __future__ import annotations

from autopilot.enforcement.editor_config import (
    generate_pyright_config,
    generate_ruff_config,
)


class TestGenerateRuffConfig:
    def test_returns_dict(self) -> None:
        config = generate_ruff_config()
        assert isinstance(config, dict)

    def test_contains_lint_select(self) -> None:
        config = generate_ruff_config()
        assert "lint" in config
        assert "select" in config["lint"]

    def test_covers_all_11_categories(self) -> None:
        config = generate_ruff_config()
        codes = config["lint"]["select"]
        expected_codes = {
            "I",
            "N",
            "C901",
            "SIM",
            "S",
            "BLE",
            "TRY",
            "ANN",
            "PT",
            "ERA",
            "UP",
            "ASYNC",
        }
        missing = expected_codes - set(codes)
        assert missing == set(), f"Missing ruff codes: {missing}"

    def test_ignores_self_annotation(self) -> None:
        config = generate_ruff_config()
        assert "ANN101" in config["lint"]["ignore"]

    def test_python_target_version(self) -> None:
        config = generate_ruff_config("python")
        assert config["target-version"] == "py312"

    def test_per_file_ignores_for_tests(self) -> None:
        config = generate_ruff_config()
        pfig = config.get("lint.per-file-ignores", {})
        assert "tests/**/*.py" in pfig

    def test_has_f401_and_f841(self) -> None:
        config = generate_ruff_config()
        codes = config["lint"]["select"]
        assert "F401" in codes
        assert "F841" in codes

    def test_has_tid251(self) -> None:
        config = generate_ruff_config()
        codes = config["lint"]["select"]
        assert "TID251" in codes


class TestGeneratePyrightConfig:
    def test_returns_dict(self) -> None:
        config = generate_pyright_config()
        assert isinstance(config, dict)

    def test_strict_mode(self) -> None:
        config = generate_pyright_config()
        assert config["typeCheckingMode"] == "strict"

    def test_python_version(self) -> None:
        config = generate_pyright_config("python")
        assert config["pythonVersion"] == "3.12"

    def test_report_missing_imports(self) -> None:
        config = generate_pyright_config()
        assert config["reportMissingImports"] is True
