"""Hive-mind integration with claude-flow (Task 037).

Hive-mind lifecycle manager evolved from RepEngine that handles branch
creation, claude-flow init, worker spawn, recording, and shutdown per
RFC ADR-7.
"""

from __future__ import annotations

import logging
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from autopilot.utils.subprocess import build_clean_env, run_with_timeout

if TYPE_CHECKING:
    from pathlib import Path

    from autopilot.core.config import AutopilotConfig

_log = logging.getLogger(__name__)


@dataclass
class HiveSession:
    """Active hive-mind session context."""

    id: str
    branch: str
    objective: str
    worker_count: int = 0
    started_at: float = field(default_factory=time.time)
    ended_at: float | None = None
    status: str = "active"


class HiveError(Exception):
    """Raised when a hive-mind operation fails."""


class HiveMindManager:
    """Manages the hive-mind lifecycle for multi-agent implementation.

    Handles branch creation, claude-flow init, worker spawn,
    session recording, and shutdown.
    """

    def __init__(
        self,
        config: AutopilotConfig,
        *,
        cwd: Path | None = None,
    ) -> None:
        self._config = config
        self._cwd = cwd

    def health_check(self) -> tuple[bool, str]:
        """Verify claude-flow is installed and correct version."""
        expected = self._config.claude.claude_flow_version
        try:
            result = run_with_timeout(
                ["npx", f"ruflo@{expected}", "--version"],
                timeout_seconds=30,
                cwd=self._cwd,
            )
            if result.returncode != 0:
                return False, f"claude-flow check failed: {result.stderr.strip()}"
            version = result.stdout.strip()
            _log.info("hive_health_check: version=%s", version)
            return True, version
        except FileNotFoundError:
            return False, "npx not found — Node.js is required"
        except subprocess.TimeoutExpired:
            return False, "claude-flow health check timed out"

    def create_branch(
        self,
        task_ids: list[str],
    ) -> str:
        """Create a git branch for hive-mind work."""
        from autopilot.utils import git

        prefix = self._config.git.branch_prefix
        strategy = self._config.git.branch_strategy

        if strategy == "per-task" and len(task_ids) == 1:
            branch_name = f"{prefix}task-{task_ids[0]}"
        else:
            batch_id = "-".join(task_ids[:3])
            if len(task_ids) > 3:
                batch_id += f"-plus{len(task_ids) - 3}"
            branch_name = f"{prefix}batch-{batch_id}"

        git.create_branch(branch_name, cwd=self._cwd)
        _log.info("hive_branch_created: branch=%s", branch_name)
        return branch_name

    def init_hive(
        self,
        branch: str,
        objective: str,
    ) -> HiveSession:
        """Initialize a hive-mind session using claude-flow."""
        session = HiveSession(
            id=str(uuid.uuid4()),
            branch=branch,
            objective=objective,
        )

        version = self._config.claude.claude_flow_version
        quality_gates = self._build_quality_gates()

        cmd = [
            "npx",
            f"ruflo@{version}",
            "swarm",
            "init",
            "--topology",
            "hierarchical",
            "--objective",
            f"{objective}{quality_gates}",
        ]

        result = run_with_timeout(
            cmd,
            timeout_seconds=60,
            cwd=self._cwd,
            env=build_clean_env(),
        )
        if result.returncode != 0:
            msg = f"Hive init failed: {result.stderr.strip()}"
            raise HiveError(msg)

        _log.info("hive_initialized: session=%s branch=%s", session.id, branch)
        return session

    def spawn_workers(
        self,
        session: HiveSession,
        worker_count: int,
    ) -> None:
        """Spawn worker agents in the hive."""
        version = self._config.claude.claude_flow_version

        for i in range(worker_count):
            cmd = [
                "npx",
                f"ruflo@{version}",
                "agent",
                "spawn",
                "-t",
                "coder",
                "--name",
                f"worker-{i}",
            ]
            result = run_with_timeout(
                cmd,
                timeout_seconds=30,
                cwd=self._cwd,
                env=build_clean_env(),
            )
            if result.returncode != 0:
                _log.warning(
                    "hive_worker_spawn_failed: worker=%d error=%s",
                    i,
                    result.stderr.strip(),
                )

        session.worker_count = worker_count
        _log.info(
            "hive_workers_spawned: session=%s count=%d",
            session.id,
            worker_count,
        )

    def record_session(self, session: HiveSession, result: str) -> None:
        """Record the hive session outcome."""
        session.ended_at = time.time()
        session.status = "completed"
        _log.info(
            "hive_session_recorded: session=%s duration=%.1fs",
            session.id,
            (session.ended_at - session.started_at),
        )

    def shutdown(self, session: HiveSession) -> None:
        """Shut down the hive-mind session."""
        version = self._config.claude.claude_flow_version
        cmd = [
            "npx",
            f"ruflo@{version}",
            "swarm",
            "shutdown",
        ]
        result = run_with_timeout(
            cmd,
            timeout_seconds=30,
            cwd=self._cwd,
            env=build_clean_env(),
        )
        if result.returncode != 0:
            _log.warning("hive_shutdown_failed: %s", result.stderr.strip())

        session.status = "shutdown"
        _log.info("hive_shutdown: session=%s", session.id)

    def _build_quality_gates(self) -> str:
        """Build quality gates suffix from config."""
        gates = self._config.quality_gates
        parts: list[str] = []
        if gates.pre_commit:
            parts.append(f"pre-commit: {gates.pre_commit}")
        if gates.type_check:
            parts.append(f"type-check: {gates.type_check}")
        if gates.test:
            parts.append(f"test: {gates.test}")
        if gates.all:
            parts.append(f"all: {gates.all}")

        if not parts:
            return ""
        return "\n\nQuality Gates:\n" + "\n".join(f"- {p}" for p in parts)
