"""Subprocess and Claude CLI invocation utilities.

Consolidates _build_clean_env from RepEngine agent.py and hive.py
into a shared utility per Discovery Consolidation Opportunity 2.
"""

from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

# Environment variables stripped from child processes to avoid leaking secrets.
_SENSITIVE_ENV_PREFIXES = (
    "ANTHROPIC_",
    "OPENAI_",
    "AWS_SECRET",
    "GITHUB_TOKEN",
    "GH_TOKEN",
    "RENDER_API_KEY",
    "DATABASE_URL",
    "SECRET_",
    "TOKEN_",
    "API_KEY",
)

_SENSITIVE_ENV_EXACT = frozenset(
    {
        "PASSWORD",
        "PASSWD",
        "CREDENTIALS",
    }
)


def build_clean_env(*, extra: dict[str, str] | None = None) -> dict[str, str]:
    """Build a sanitized copy of the current environment.

    Strips environment variables whose names match known secret patterns
    so that child processes (especially Claude CLI) do not accidentally
    inherit API keys or tokens.
    """
    env: dict[str, str] = {}
    for key, value in os.environ.items():
        upper = key.upper()
        if upper in _SENSITIVE_ENV_EXACT:
            continue
        if any(upper.startswith(prefix) for prefix in _SENSITIVE_ENV_PREFIXES):
            continue
        env[key] = value
    if extra:
        env.update(extra)
    return env


def run_claude_cli(
    prompt: str,
    *,
    model: str = "sonnet",
    max_turns: int = 10,
    extra_flags: str = "",
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout_seconds: int = 900,
) -> subprocess.CompletedProcess[str]:
    """Invoke the Claude CLI with the given prompt and return the result.

    Uses a clean environment by default to prevent secret leakage.
    """
    cmd = ["claude", "--print", "--model", model, "--max-turns", str(max_turns)]
    if extra_flags:
        cmd.extend(extra_flags.split())
    cmd.extend(["--prompt", prompt])

    clean_env = env if env is not None else build_clean_env()

    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd,
        env=clean_env,
        timeout=timeout_seconds,
    )


def run_with_timeout(
    cmd: list[str],
    *,
    timeout_seconds: int = 120,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a command with a timeout, returning the completed process."""
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd,
        env=env,
        timeout=timeout_seconds,
    )
