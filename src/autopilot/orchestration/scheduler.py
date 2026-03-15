"""Scheduler core — cycle orchestration (Task 035).

Orchestrates the plan -> dispatch -> execute -> report cycle
per RFC Section 3.3, evolved from RepEngine's 691-line scheduler.py.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from autopilot.core.models import CycleResult, CycleStatus, DispatchStatus
from autopilot.orchestration.circuit_breaker import CircuitBreaker
from autopilot.utils import git
from autopilot.utils.process import PidFile

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from autopilot.core.config import AutopilotConfig
    from autopilot.orchestration.agent_invoker import AgentInvoker, InvokeResult
    from autopilot.orchestration.dispatcher import DispatchPlan
    from autopilot.orchestration.usage import UsageTracker

    PlanFn = Callable[[], DispatchPlan | None]

_log = logging.getLogger(__name__)

_CYCLE_LOCK_TTL = 7200  # 2 hours


@dataclass(frozen=True)
class DispatchOutcome:
    """Outcome of a single dispatch execution."""

    agent: str
    action: str
    status: DispatchStatus
    duration_seconds: float = 0.0
    exit_code: int = 0
    output: str = ""
    error: str = ""
    model_used: str = ""


@dataclass
class CycleContext:
    """Runtime context for a single cycle execution."""

    cycle_id: str
    project_id: str
    started_at: datetime
    outcomes: list[DispatchOutcome] = field(default_factory=lambda: list[DispatchOutcome]())


class SchedulerError(Exception):
    """Raised when the scheduler encounters a blocking error."""


class Scheduler:
    """Core scheduler orchestrating the three-phase execution cycle.

    Phase 1 (Planning): Acquire lock, validate git, check usage, invoke PL
    Phase 2 (Execution): Execute dispatches, apply circuit breaker
    Phase 3 (Bookkeeping): Generate report, record cycle, release lock
    """

    def __init__(
        self,
        config: AutopilotConfig,
        invoker: AgentInvoker,
        usage_tracker: UsageTracker,
        *,
        lock_dir: Path | None = None,
        cwd: Path | None = None,
    ) -> None:
        self._config = config
        self._invoker = invoker
        self._usage = usage_tracker
        self._cwd = cwd
        self._circuit_breaker = CircuitBreaker(
            consecutive_limit=config.scheduler.consecutive_timeout_limit
        )

        lock_path = (lock_dir or (cwd or _default_lock_dir())) / "cycle.lock"
        self._lock = PidFile(lock_path, ttl_seconds=_CYCLE_LOCK_TTL)
        self._running = False

    def run_cycle(
        self,
        dispatch_plan: DispatchPlan,
    ) -> CycleResult:
        """Execute one full plan -> execute -> report cycle."""
        project_id = self._config.project.name
        ctx = CycleContext(
            cycle_id=str(uuid.uuid4()),
            project_id=project_id,
            started_at=datetime.now(UTC),
        )

        # Phase 1: Planning
        self._phase_plan(project_id)

        # Phase 2: Execution
        try:
            self._phase_execute(ctx, dispatch_plan)
        finally:
            # Phase 3: Bookkeeping (always runs, lock always released)
            try:
                result = self._phase_bookkeep(ctx)
            finally:
                self._lock.release()

        return result

    def run_loop(self, interval: int, *, plan_fn: PlanFn | None = None) -> None:
        """Run cycles on an interval until stopped.

        ``plan_fn`` is called each iteration to produce the dispatch plan.
        If None, raises SchedulerError.
        """
        if plan_fn is None:
            msg = "plan_fn is required for run_loop"
            raise SchedulerError(msg)

        self._running = True
        while self._running:
            try:
                plan = plan_fn()
                if plan and plan.dispatches:
                    self.run_cycle(plan)
            except SchedulerError:
                _log.exception("scheduler_cycle_error")
            if self._running:
                time.sleep(interval)

    def stop(self) -> None:
        """Signal the scheduler loop to stop after the current cycle."""
        self._running = False

    def _phase_plan(self, project_id: str) -> None:
        """Phase 1: Acquire lock, validate state, check limits."""
        if not self._lock.acquire():
            msg = "Another cycle is already running (lock held)"
            raise SchedulerError(msg)

        # Validate git state
        issues = git.validate_git_state(self._config.git.base_branch, cwd=self._cwd)
        if issues:
            self._lock.release()
            msg = f"Git state invalid: {'; '.join(issues)}"
            raise SchedulerError(msg)

        # Check usage limits
        allowed, reason = self._usage.can_execute(project_id)
        if not allowed:
            self._lock.release()
            msg = f"Usage limit reached: {reason}"
            raise SchedulerError(msg)

    def _phase_execute(
        self,
        ctx: CycleContext,
        dispatch_plan: DispatchPlan,
    ) -> None:
        """Phase 2: Execute dispatches with circuit breaker."""
        self._circuit_breaker.reset()

        for dispatch in dispatch_plan.dispatches:
            if self._circuit_breaker.is_tripped():
                _log.warning("scheduler_circuit_breaker_tripped: skipping remaining dispatches")
                ctx.outcomes.append(
                    DispatchOutcome(
                        agent=dispatch.agent,
                        action=dispatch.action,
                        status=DispatchStatus.FAILED,
                        error="Skipped: circuit breaker tripped",
                    )
                )
                continue

            outcome = self._execute_dispatch(dispatch.agent, dispatch.action)
            ctx.outcomes.append(outcome)

            if outcome.status == DispatchStatus.SUCCESS:
                self._circuit_breaker.record_success()
            else:
                self._circuit_breaker.record_failure(outcome.error)

    def _execute_dispatch(self, agent: str, action: str) -> DispatchOutcome:
        """Execute a single dispatch and return the outcome."""
        self._usage.record_agent_invocation(self._config.project.name, agent)

        result: InvokeResult = self._invoker.invoke(agent, action, cwd=self._cwd)

        return DispatchOutcome(
            agent=agent,
            action=action,
            status=result.status,
            duration_seconds=result.duration_seconds,
            exit_code=result.exit_code,
            output=result.output,
            error=result.error,
            model_used=result.model_used,
        )

    def _phase_bookkeep(self, ctx: CycleContext) -> CycleResult:
        """Phase 3: Record cycle, update usage."""
        ended_at = datetime.now(UTC)
        duration = (ended_at - ctx.started_at).total_seconds()

        succeeded = sum(1 for o in ctx.outcomes if o.status == DispatchStatus.SUCCESS)
        failed = len(ctx.outcomes) - succeeded

        if failed == 0 and succeeded > 0:
            status = CycleStatus.COMPLETED
        elif succeeded > 0:
            status = CycleStatus.PARTIAL
        else:
            status = CycleStatus.FAILED

        self._usage.record_cycle(ctx.project_id)

        return CycleResult(
            id=ctx.cycle_id,
            project_id=ctx.project_id,
            status=status,
            started_at=ctx.started_at,
            ended_at=ended_at,
            dispatches_planned=len(ctx.outcomes),
            dispatches_succeeded=succeeded,
            dispatches_failed=failed,
            duration_seconds=duration,
        )


def _default_lock_dir() -> Path:
    from pathlib import Path

    from autopilot.utils.paths import find_autopilot_dir

    ap = find_autopilot_dir()
    if ap is not None:
        return ap / "state"
    return Path.home() / ".autopilot" / "state"
