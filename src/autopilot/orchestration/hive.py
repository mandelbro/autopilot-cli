"""Hive-mind integration with claude-flow (Task 037).

Hive-mind lifecycle manager evolved from RepEngine that handles branch
creation, claude-flow init, worker spawn, recording, and shutdown per
RFC ADR-7.
"""

from __future__ import annotations

import contextlib
import logging
import os
import signal
import subprocess
import time
import uuid
import warnings
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from autopilot.utils.subprocess import build_clean_env, run_with_timeout

if TYPE_CHECKING:
    from pathlib import Path

    from autopilot.core.config import AutopilotConfig
    from autopilot.core.session import SessionManager
    from autopilot.orchestration.resource_broker import ResourceBroker
    from autopilot.orchestration.usage import UsageTracker

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
    metadata: dict[str, Any] = field(default_factory=lambda: dict[str, Any]())


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
        resource_broker: ResourceBroker | None = None,
        usage_tracker: UsageTracker | None = None,
        session_manager: SessionManager | None = None,
    ) -> None:
        self._config = config
        self._cwd = cwd
        self._resource_broker = resource_broker
        self._usage_tracker = usage_tracker
        self._session_manager = session_manager
        self._active_processes: dict[str, subprocess.Popen[str]] = {}

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
        """Initialize a hive-mind session using claude-flow.

        .. deprecated:: Use :meth:`spawn_hive` instead.
        """
        warnings.warn(
            "init_hive() is deprecated. Use spawn_hive() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
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
        """Spawn worker agents in the hive.

        .. deprecated:: Use :meth:`spawn_hive` instead.
        """
        warnings.warn(
            "spawn_workers() is deprecated. Use spawn_hive() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
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

    def spawn_hive(
        self,
        objective: str,
        *,
        namespace: str | None = None,
        use_claude: bool = True,
        task_file: str = "",
        task_ids: list[str] | None = None,
    ) -> HiveSession:
        """Spawn a hive-mind session via ``hive-mind spawn``.

        With ``use_claude=True`` (default), the process blocks for hours so
        we use ``subprocess.Popen`` and store the PID for monitoring. Without
        ``--claude``, it returns quickly via ``run_with_timeout``.
        """
        ns = namespace or self._config.hive_mind.namespace or self._config.project.name
        self._preflight_checks(ns)

        if self._resource_broker:
            allowed, reason = self._resource_broker.can_spawn_agent(self._config.project.name)
            if not allowed:
                raise HiveError(reason)

        session = HiveSession(
            id=str(uuid.uuid4()),
            branch="",
            objective=objective,
            metadata={"namespace": ns},
        )

        cmd = ["npx", "ruflo@latest", "hive-mind", "spawn", objective, "--namespace", ns]

        if use_claude:
            cmd.append("--claude")
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self._cwd,
                env=build_clean_env(),
            )
            session.metadata["pid"] = process.pid
            session.status = "spawned"
            self._active_processes[session.id] = process
        else:
            result = run_with_timeout(
                cmd,
                timeout_seconds=self._config.hive_mind.spawn_timeout_seconds,
                cwd=self._cwd,
                env=build_clean_env(),
            )
            if result.returncode != 0:
                msg = f"Hive spawn failed: {result.stderr.strip()}"
                raise HiveError(msg)
            session.status = "spawned"

        if self._usage_tracker:
            self._usage_tracker.record_cycle(self._config.project.name)

        if self._session_manager:
            from autopilot.core.models import SessionType

            self._session_manager.create_session(
                project=self._config.project.name,
                session_type=SessionType.HIVE_MIND,
                agent_name=f"hive-mind:{ns}",
                pid=session.metadata.get("pid"),
                cycle_id=session.id,
            )

        _log.info("hive_spawned: session=%s namespace=%s claude=%s", session.id, ns, use_claude)
        return session

    def stop_hive(self, session: HiveSession, *, force: bool = False) -> None:
        """Stop a running hive-mind session."""
        pid = session.metadata.get("pid")
        ns = session.metadata.get("namespace", "")

        if not force and ns:
            try:
                run_with_timeout(
                    ["npx", "ruflo@latest", "hive-mind", "shutdown", "--namespace", ns],
                    timeout_seconds=30,
                    cwd=self._cwd,
                    env=build_clean_env(),
                )
            except subprocess.TimeoutExpired:
                _log.warning("hive_graceful_shutdown_timeout: namespace=%s", ns)

        if pid:
            with contextlib.suppress(ProcessLookupError):
                os.kill(pid, signal.SIGTERM)

        self._active_processes.pop(session.id, None)

        session.status = "stopped"
        session.ended_at = time.time()
        _log.info("hive_stopped: session=%s force=%s", session.id, force)

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

    def _preflight_checks(self, namespace: str) -> None:
        """Validate preconditions before spawning a hive-mind session."""
        result = run_with_timeout(
            ["git", "status", "--porcelain"],
            timeout_seconds=10,
            cwd=self._cwd,
        )
        if result.stdout.strip():
            msg = "Cannot spawn hive: dirty working tree. Commit or stash changes first."
            raise HiveError(msg)

        if self._has_active_session(namespace):
            msg = f"Cannot spawn hive: active session already exists on namespace '{namespace}'."
            raise HiveError(msg)

    def _has_active_session(self, namespace: str) -> bool:
        """Check if there is an active session on the given namespace.

        Placeholder — full session tracking is deferred to Phase 5a.
        """
        return False

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
