"""Tests for the CI/CD template generator (Task 062)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from pathlib import Path

from autopilot.enforcement.ci import CIPipelineGenerator


class TestGenerateWorkflow:
    def setup_method(self) -> None:
        self.gen = CIPipelineGenerator()

    def test_returns_valid_yaml_string(self) -> None:
        result = self.gen.generate_workflow("python")
        parsed = yaml.safe_load(result)
        assert isinstance(parsed, dict)

    def test_workflow_has_name(self) -> None:
        parsed = yaml.safe_load(self.gen.generate_workflow())
        assert parsed["name"] == "Quality Gates"

    def test_workflow_trigger_on_push_and_pr(self) -> None:
        parsed = yaml.safe_load(self.gen.generate_workflow())
        assert "push" in parsed[True]
        assert "pull_request" in parsed[True]

    def test_contains_lint_job(self) -> None:
        parsed = yaml.safe_load(self.gen.generate_workflow())
        assert "lint" in parsed["jobs"]
        steps = parsed["jobs"]["lint"]["steps"]
        run_steps = [s.get("run", "") for s in steps]
        assert any("ruff check src/ tests/" in r for r in run_steps)

    def test_contains_typecheck_job(self) -> None:
        parsed = yaml.safe_load(self.gen.generate_workflow())
        assert "typecheck" in parsed["jobs"]
        steps = parsed["jobs"]["typecheck"]["steps"]
        run_steps = [s.get("run", "") for s in steps]
        assert any("pyright" in r for r in run_steps)

    def test_contains_test_job(self) -> None:
        parsed = yaml.safe_load(self.gen.generate_workflow())
        assert "test" in parsed["jobs"]

    def test_contains_security_job(self) -> None:
        parsed = yaml.safe_load(self.gen.generate_workflow())
        assert "security" in parsed["jobs"]
        steps = parsed["jobs"]["security"]["steps"]
        run_steps = [s.get("run", "") for s in steps]
        assert any("detect-secrets scan" in r for r in run_steps)

    def test_all_four_jobs_present(self) -> None:
        parsed = yaml.safe_load(self.gen.generate_workflow())
        expected = {"lint", "typecheck", "test", "security"}
        assert set(parsed["jobs"].keys()) == expected

    def test_coverage_threshold_default(self) -> None:
        parsed = yaml.safe_load(self.gen.generate_workflow())
        test_steps = parsed["jobs"]["test"]["steps"]
        run_steps = [s.get("run", "") for s in test_steps]
        assert any("--cov-fail-under=90" in r for r in run_steps)

    def test_coverage_threshold_configurable(self) -> None:
        result = self.gen.generate_workflow(coverage_threshold=80)
        parsed = yaml.safe_load(result)
        test_steps = parsed["jobs"]["test"]["steps"]
        run_steps = [s.get("run", "") for s in test_steps]
        assert any("--cov-fail-under=80" in r for r in run_steps)

    def test_default_python_versions(self) -> None:
        parsed = yaml.safe_load(self.gen.generate_workflow())
        matrix = parsed["jobs"]["test"]["strategy"]["matrix"]
        assert matrix["python-version"] == ["3.12"]

    def test_custom_python_versions(self) -> None:
        result = self.gen.generate_workflow(python_versions=["3.11", "3.12"])
        parsed = yaml.safe_load(result)
        matrix = parsed["jobs"]["test"]["strategy"]["matrix"]
        assert matrix["python-version"] == ["3.11", "3.12"]

    def test_jobs_run_on_ubuntu(self) -> None:
        parsed = yaml.safe_load(self.gen.generate_workflow())
        for job_name, job in parsed["jobs"].items():
            assert job["runs-on"] == "ubuntu-latest", f"{job_name} not on ubuntu-latest"

    def test_jobs_use_checkout_v4(self) -> None:
        parsed = yaml.safe_load(self.gen.generate_workflow())
        for job_name, job in parsed["jobs"].items():
            uses = [s.get("uses", "") for s in job["steps"]]
            assert any("actions/checkout@v4" in u for u in uses), f"{job_name} missing checkout"

    def test_jobs_use_setup_python_v5(self) -> None:
        parsed = yaml.safe_load(self.gen.generate_workflow())
        for job_name, job in parsed["jobs"].items():
            uses = [s.get("uses", "") for s in job["steps"]]
            assert any("actions/setup-python@v5" in u for u in uses), (
                f"{job_name} missing setup-python"
            )


class TestWriteWorkflow:
    def setup_method(self) -> None:
        self.gen = CIPipelineGenerator()

    def test_creates_file_at_correct_path(self, tmp_path: Path) -> None:
        content = self.gen.generate_workflow()
        result_path = self.gen.write_workflow(tmp_path, content)
        expected = tmp_path / ".github" / "workflows" / "quality-gates.yml"
        assert result_path == expected
        assert result_path.exists()

    def test_file_content_matches(self, tmp_path: Path) -> None:
        content = self.gen.generate_workflow()
        result_path = self.gen.write_workflow(tmp_path, content)
        assert result_path.read_text() == content

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        content = self.gen.generate_workflow()
        result_path = self.gen.write_workflow(tmp_path, content)
        assert result_path.parent.is_dir()
