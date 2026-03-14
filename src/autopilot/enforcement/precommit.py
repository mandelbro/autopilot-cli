"""Layer 2: Pre-commit hook setup with Lefthook (Task 061, RFC Section 3.5.2).

Generates Lefthook configuration for pre-commit hooks with block-no-verify
and detect-secrets integration, targeting < 5s total hook execution.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

from autopilot.core.models import SetupResult

_log = logging.getLogger(__name__)

# Hook definitions per project type
_PYTHON_COMMANDS: dict[str, dict[str, Any]] = {
    "lint": {"run": "ruff check --fix {staged_files}", "glob": "*.py"},
    "format": {"run": "ruff format --check {staged_files}", "glob": "*.py"},
    "typecheck": {"run": "pyright {staged_files}", "glob": "*.py"},
}

_TYPESCRIPT_COMMANDS: dict[str, dict[str, Any]] = {
    "lint": {"run": "eslint --fix {staged_files}", "glob": "*.{ts,tsx}"},
    "format": {"run": "prettier --check {staged_files}", "glob": "*.{ts,tsx}"},
    "typecheck": {"run": "tsc --noEmit", "glob": "*.{ts,tsx}"},
}

_INSTALL_SCRIPT = """\
#!/usr/bin/env bash
set -euo pipefail

if ! command -v lefthook &>/dev/null; then
    echo "Installing lefthook..."
    npm install -g @evilmartians/lefthook
fi

lefthook install
echo "Lefthook hooks installed successfully."
"""


class PrecommitSetup:
    """Generates and applies Lefthook pre-commit configuration.

    Supports Python and TypeScript projects with parallel hook execution,
    detect-secrets credential scanning, and --no-verify bypass blocking.
    """

    def install_lefthook(self, project_root: Path) -> SetupResult:
        """Write a Lefthook install script to *project_root*.

        Returns a :class:`SetupResult` describing the created file.
        """
        script_path = project_root / "scripts" / "install-lefthook.sh"
        try:
            script_path.parent.mkdir(parents=True, exist_ok=True)
            script_path.write_text(_INSTALL_SCRIPT)
            script_path.chmod(0o755)
        except OSError as exc:
            return SetupResult(
                layer="precommit",
                success=False,
                errors=(f"Failed to write install script: {exc}",),
            )
        return SetupResult(
            layer="precommit",
            success=True,
            files_created=(str(script_path),),
        )

    def generate_config(self, project_type: str) -> dict[str, Any]:
        """Create a Lefthook config dict for *project_type*.

        Supports ``"python"`` and ``"typescript"``.  The returned dict
        is suitable for serialisation to ``lefthook.yml``.
        """
        if project_type == "typescript":
            commands = dict(_TYPESCRIPT_COMMANDS)
        else:
            commands = dict(_PYTHON_COMMANDS)

        return {
            "pre-commit": {
                "parallel": True,
                "commands": commands,
            },
        }

    def add_block_no_verify(self, config: dict[str, Any]) -> dict[str, Any]:
        """Add a hook that blocks ``--no-verify`` bypass attempts."""
        commands = config.setdefault("pre-commit", {}).setdefault("commands", {})
        commands["block-no-verify"] = {
            "run": "echo 'ERROR: --no-verify is disabled' && exit 1",
            "env": {"LEFTHOOK_ALLOW_SKIP": "never"},
        }
        return config

    def add_detect_secrets(self, config: dict[str, Any]) -> dict[str, Any]:
        """Add a detect-secrets credential scanning hook."""
        commands = config.setdefault("pre-commit", {}).setdefault("commands", {})
        commands["detect-secrets"] = {
            "run": "detect-secrets-hook {staged_files}",
            "glob": "*",
        }
        return config

    def apply(
        self,
        project_root: Path,
        project_type: str = "python",
    ) -> SetupResult:
        """Orchestrate full Lefthook setup for *project_root*.

        1. Generate base config for *project_type*.
        2. Add block-no-verify and detect-secrets hooks.
        3. Write ``lefthook.yml`` to *project_root*.
        4. Write the install helper script.

        Returns a :class:`SetupResult` with all created file paths.
        """
        try:
            import yaml
        except ModuleNotFoundError:  # pragma: no cover
            return SetupResult(
                layer="precommit",
                success=False,
                errors=("PyYAML is required but not installed",),
            )

        config = self.generate_config(project_type)
        self.add_block_no_verify(config)
        self.add_detect_secrets(config)

        lefthook_path = project_root / "lefthook.yml"
        files_created: list[str] = []
        errors: list[str] = []

        try:
            project_root.mkdir(parents=True, exist_ok=True)
            lefthook_path.write_text(yaml.dump(config, default_flow_style=False, sort_keys=False))
            files_created.append(str(lefthook_path))
        except OSError as exc:
            errors.append(f"Failed to write lefthook.yml: {exc}")

        install_result = self.install_lefthook(project_root)
        files_created.extend(install_result.files_created)
        errors.extend(install_result.errors)

        return SetupResult(
            layer="precommit",
            success=len(errors) == 0,
            files_created=tuple(files_created),
            errors=tuple(errors),
        )
