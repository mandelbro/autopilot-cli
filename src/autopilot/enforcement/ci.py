"""Layer 3: CI/CD template generation for GitHub Actions (Task 062, RFC Section 3.5.2).

Generates GitHub Actions workflow YAML with quality gate jobs for lint,
typecheck, test, and security scanning.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from pathlib import Path


def _build_workflow(
    *,
    coverage_threshold: int,
    max_complexity: int,
    python_versions: list[str],
) -> dict[str | bool, Any]:
    """Build the workflow dict for GitHub Actions quality gates."""
    checkout_step: dict[str, str] = {"uses": "actions/checkout@v4"}

    def _setup_python(version_expr: str) -> dict[str, Any]:
        return {
            "uses": "actions/setup-python@v5",
            "with": {"python-version": version_expr},
        }

    install_step: dict[str, str] = {
        "name": "Install dependencies",
        "run": "pip install -e '.[dev]'",
    }

    lint_job: dict[str, Any] = {
        "runs-on": "ubuntu-latest",
        "steps": [
            checkout_step,
            _setup_python(python_versions[0]),
            install_step,
            {"name": "Lint", "run": "ruff check src/ tests/"},
        ],
    }

    typecheck_job: dict[str, Any] = {
        "runs-on": "ubuntu-latest",
        "steps": [
            checkout_step,
            _setup_python(python_versions[0]),
            install_step,
            {"name": "Typecheck", "run": "pyright"},
        ],
    }

    test_job: dict[str, Any] = {
        "runs-on": "ubuntu-latest",
        "strategy": {"matrix": {"python-version": python_versions}},
        "steps": [
            checkout_step,
            _setup_python("${{ matrix.python-version }}"),
            install_step,
            {
                "name": "Test",
                "run": f"pytest --cov --cov-fail-under={coverage_threshold}",
            },
        ],
    }

    security_job: dict[str, Any] = {
        "runs-on": "ubuntu-latest",
        "steps": [
            checkout_step,
            _setup_python(python_versions[0]),
            install_step,
            {"name": "Security scan", "run": "detect-secrets scan"},
        ],
    }

    return {
        "name": "Quality Gates",
        True: ["push", "pull_request"],  # yaml.dump renders True as 'on'
        "jobs": {
            "lint": lint_job,
            "typecheck": typecheck_job,
            "test": test_job,
            "security": security_job,
        },
    }


class CIPipelineGenerator:
    """Generate GitHub Actions CI workflow YAML for quality gates."""

    def generate_workflow(
        self,
        project_type: str = "python",
        *,
        coverage_threshold: int = 90,
        max_complexity: int = 10,
        python_versions: list[str] | None = None,
    ) -> str:
        """Return a GitHub Actions workflow YAML string.

        Parameters
        ----------
        project_type:
            Project type hint (currently only ``"python"`` is supported).
        coverage_threshold:
            Minimum test coverage percentage for the ``--cov-fail-under`` flag.
        max_complexity:
            Maximum cyclomatic complexity (reserved for future ruff integration).
        python_versions:
            Python versions to include in the test matrix.  Defaults to
            ``["3.12"]``.
        """
        if python_versions is None:
            python_versions = ["3.12"]

        workflow = _build_workflow(
            coverage_threshold=coverage_threshold,
            max_complexity=max_complexity,
            python_versions=python_versions,
        )

        return yaml.dump(workflow, default_flow_style=False, sort_keys=False)

    def write_workflow(self, project_root: Path, workflow_content: str) -> Path:
        """Write *workflow_content* to ``.github/workflows/quality-gates.yml``.

        Creates intermediate directories as needed and returns the path
        that was written.
        """
        target = project_root / ".github" / "workflows" / "quality-gates.yml"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(workflow_content)
        return target
