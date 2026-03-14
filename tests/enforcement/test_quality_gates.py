"""Tests for quality gate prompt generation (Task 065)."""

from __future__ import annotations

from autopilot.core.config import QualityGatesConfig
from autopilot.enforcement.quality_gates import QualityGateBuilder


class TestBuildPromptDefaults:
    """build_prompt with default (empty) config."""

    def setup_method(self) -> None:
        self.config = QualityGatesConfig()
        self.prompt = QualityGateBuilder.build_prompt(self.config)

    def test_includes_all_three_gates(self) -> None:
        assert "Pre-commit checks" in self.prompt
        assert "Type checking" in self.prompt
        assert "Tests" in self.prompt

    def test_contains_quality_gates_header(self) -> None:
        assert "## Quality Gates" in self.prompt

    def test_contains_numbered_steps(self) -> None:
        assert "1. **Pre-commit checks**" in self.prompt
        assert "2. **Type checking**" in self.prompt
        assert "3. **Tests**" in self.prompt

    def test_python_defaults_ruff(self) -> None:
        assert "ruff check --fix . && ruff format ." in self.prompt

    def test_python_defaults_pyright(self) -> None:
        assert "pyright" in self.prompt

    def test_python_defaults_pytest(self) -> None:
        assert "pytest" in self.prompt

    def test_contains_failure_instruction(self) -> None:
        assert "If any gate fails" in self.prompt


class TestBuildPromptCustomConfig:
    """build_prompt uses custom commands from config."""

    def test_uses_custom_pre_commit(self) -> None:
        config = QualityGatesConfig(pre_commit="black . && isort .")
        prompt = QualityGateBuilder.build_prompt(config)
        assert "black . && isort ." in prompt
        assert "ruff" not in prompt

    def test_uses_custom_type_check(self) -> None:
        config = QualityGatesConfig(type_check="mypy src/")
        prompt = QualityGateBuilder.build_prompt(config)
        assert "mypy src/" in prompt
        assert "pyright" not in prompt

    def test_uses_custom_test(self) -> None:
        config = QualityGatesConfig(test="pytest -x --tb=short")
        prompt = QualityGateBuilder.build_prompt(config)
        assert "pytest -x --tb=short" in prompt

    def test_mixed_custom_and_defaults(self) -> None:
        config = QualityGatesConfig(pre_commit="custom-lint")
        prompt = QualityGateBuilder.build_prompt(config)
        assert "custom-lint" in prompt
        # Other gates should still use defaults
        assert "pyright" in prompt
        assert "pytest" in prompt


class TestBuildPromptTypescript:
    """build_prompt for TypeScript project type."""

    def setup_method(self) -> None:
        self.config = QualityGatesConfig()
        self.prompt = QualityGateBuilder.build_prompt(self.config, project_type="typescript")

    def test_uses_eslint(self) -> None:
        assert "eslint --fix . && prettier --write ." in self.prompt

    def test_uses_tsc(self) -> None:
        assert "tsc --noEmit" in self.prompt

    def test_uses_npm_test(self) -> None:
        assert "npm test" in self.prompt


class TestGetGates:
    """get_gates returns correct tuples."""

    def test_python_defaults(self) -> None:
        config = QualityGatesConfig()
        gates = QualityGateBuilder.get_gates(config)
        assert len(gates) == 3
        assert gates[0] == ("pre_commit", "ruff check --fix . && ruff format .")
        assert gates[1] == ("type_check", "pyright")
        assert gates[2] == ("test", "pytest")

    def test_typescript_defaults(self) -> None:
        config = QualityGatesConfig()
        gates = QualityGateBuilder.get_gates(config, project_type="typescript")
        assert gates[0] == (
            "pre_commit",
            "eslint --fix . && prettier --write .",
        )
        assert gates[1] == ("type_check", "tsc --noEmit")
        assert gates[2] == ("test", "npm test")

    def test_uses_config_values_when_provided(self) -> None:
        config = QualityGatesConfig(
            pre_commit="my-lint",
            type_check="my-typecheck",
            test="my-test",
        )
        gates = QualityGateBuilder.get_gates(config)
        assert gates[0] == ("pre_commit", "my-lint")
        assert gates[1] == ("type_check", "my-typecheck")
        assert gates[2] == ("test", "my-test")

    def test_partial_config_mixes_custom_and_defaults(self) -> None:
        config = QualityGatesConfig(type_check="mypy .")
        gates = QualityGateBuilder.get_gates(config)
        assert gates[0][1] == "ruff check --fix . && ruff format ."
        assert gates[1][1] == "mypy ."
        assert gates[2][1] == "pytest"


class TestGateOrdering:
    """gate_ordering returns the fixed execution order."""

    def test_returns_correct_order(self) -> None:
        ordering = QualityGateBuilder.gate_ordering()
        assert ordering == ["pre_commit", "type_check", "test"]

    def test_returns_new_list_each_call(self) -> None:
        a = QualityGateBuilder.gate_ordering()
        b = QualityGateBuilder.gate_ordering()
        assert a is not b
