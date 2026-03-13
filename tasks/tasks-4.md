## Summary (tasks-4.md)

- **Tasks in this file**: 10
- **Task IDs**: 031 - 040
- **Total Points**: 43

### Main Phase 3: Autonomous Execution -- Agent Invocation, Scheduling, Daemon, Hive-Mind

---

## Tasks

### Task ID: 031

- **Title**: Agent invoker with retry and model fallback
- **File**: src/autopilot/orchestration/agent_invoker.py
- **Complete**: [ ]
- **Sprint Points**: 5

- **User Story (business-facing)**: As a scheduler, I want reliable agent invocation with retry logic and model fallback, so that transient failures do not derail autonomous execution cycles.
- **Outcome (what this delivers)**: Agent invoker that calls Claude CLI with env sanitization, exponential backoff, model fallback chains, empty output detection, and structured result capture.

#### Prompt:

```markdown
**Objective:** Evolve RepEngine agent.py into a generalized agent invoker.

**File to Create/Modify:** `src/autopilot/orchestration/agent_invoker.py`

**Specification References:**
- RFC Section 3.3: Agent invocation in orchestration flow
- RFC Section 3.8: Error Recovery (exponential backoff, model fallback, empty output detection)
- Discovery: agent.py evolution (292 lines, Claude CLI subprocess with retry, env sanitization)

**Prerequisite Requirements:**
1. Tasks 002, 003, 004, 015 must be complete (config, models, subprocess utils, agent registry)
2. Write tests in `tests/orchestration/test_agent_invoker.py`

**Detailed Instructions:**
1. Implement `AgentInvoker` class:
   - `invoke(agent_name, prompt, project_config) -> AgentResult`
   - Load agent prompt from registry, inject project context
   - Call Claude CLI via subprocess with clean env, model, max_turns
   - Retry with exponential backoff (2 retries, 45s/90s from RepEngine)
   - Model fallback chain from config (opus -> opus 4.5 -> sonnet)
   - Empty output detection (exit 0, no output, < 8 seconds)
   - Timeout handling per agent role from config.agents.agent_timeouts
2. `AgentResult` captures: agent, action, output, duration, exit_code, model_used, retries
3. Sanitize all output through sanitizer before storing/displaying

**Acceptance Criteria:**
- [ ] Agent invocation calls Claude CLI with correct parameters
- [ ] Retry logic with exponential backoff works
- [ ] Model fallback chain is used on failure
- [ ] Empty output (exit 0, <8s, no content) detected as failure
- [ ] Per-agent timeout from config is respected
- [ ] Output is sanitized before return
- [ ] All tests pass with mocked subprocess
```

---

### Task ID: 032

- **Title**: Dispatch plan parser and validator
- **File**: src/autopilot/orchestration/dispatcher.py
- **Complete**: [ ]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a scheduler, I want robust dispatch plan parsing from PL agent output, so that even when the PL drifts from the contract, dispatches are correctly extracted and validated.
- **Outcome (what this delivers)**: Dispatch parser that handles code-fenced JSON, raw JSON, field name normalization, and validation against the dynamic agent registry.

#### Prompt:

```markdown
**Objective:** Port and evolve RepEngine dispatch.py for generalized dispatch parsing.

**File to Create/Modify:** `src/autopilot/orchestration/dispatcher.py`

**Specification References:**
- Discovery: dispatch.py description (133 lines, JSON extraction/validation)
- RFC Section 3.3: Dispatch plan in orchestration flow
- RFC Section 3.7: Validate against dynamic agent registry

**Prerequisite Requirements:**
1. Tasks 003, 015 must be complete (models, agent registry)
2. Write tests in `tests/orchestration/test_dispatcher.py`

**Detailed Instructions:**
1. Port RepEngine dispatch.py parsing logic:
   - Extract JSON from code-fenced blocks, raw JSON, or mixed text
   - Normalize field names (PL drifts: "reason" -> "rationale", etc.)
   - Handle single dispatch or list of dispatches
2. Validate dispatches against agent registry (reject unknown agents)
3. Resolve project_root from config for multi-project support
4. Return `DispatchPlan` with list of validated `Dispatch` objects

**Acceptance Criteria:**
- [ ] JSON extracted from code-fenced blocks
- [ ] Field name normalization handles known PL drift patterns
- [ ] Unknown agents are rejected with clear error
- [ ] Both single and list dispatch formats are handled
- [ ] All tests pass
```

---

### Task ID: 033

- **Title**: Circuit breaker pattern
- **File**: src/autopilot/orchestration/circuit_breaker.py
- **Complete**: [ ]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a system operator, I want a circuit breaker that aborts remaining dispatches after consecutive failures, so that wasted cycles and costs are minimized during outages.
- **Outcome (what this delivers)**: Extracted circuit breaker from RepEngine scheduler with configurable threshold and state tracking.

#### Prompt:

```markdown
**Objective:** Extract and implement the circuit breaker pattern.

**File to Create/Modify:** `src/autopilot/orchestration/circuit_breaker.py`

**Specification References:**
- RFC Section 3.8: Circuit breaker (abort after N consecutive timeouts)
- Discovery: Circuit breaker extracted from scheduler for reuse

**Prerequisite Requirements:**
1. Task 003 must be complete (models)
2. Write tests in `tests/orchestration/test_circuit_breaker.py`

**Detailed Instructions:**
1. Implement `CircuitBreaker` class:
   - `__init__(consecutive_limit: int)` from config
   - `record_success()` resets consecutive failure count
   - `record_failure(error_type: str)` increments count
   - `is_tripped() -> bool` returns True when limit reached
   - `reset()` manually resets the breaker
   - `state() -> CircuitBreakerState` returns current state info
2. Track: consecutive_failures, total_failures, total_successes, last_failure_time
3. Emit structured log on trip

**Acceptance Criteria:**
- [ ] Circuit breaker trips after N consecutive failures
- [ ] Successful dispatch resets the counter
- [ ] State is queryable for monitoring
- [ ] All tests pass
```

---

### Task ID: 034

- **Title**: Usage tracking with per-project limits
- **File**: src/autopilot/orchestration/usage.py
- **Complete**: [x]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a system operator, I want usage tracking against Claude Max plan limits, so that autonomous execution stays within daily and weekly cycle budgets.
- **Outcome (what this delivers)**: Usage tracker evolved from RepEngine with daily/weekly cycle counts, per-project limits, and SQLite backing.

#### Prompt:

```markdown
**Objective:** Evolve RepEngine usage.py with per-project limits and SQLite backing.

**File to Create/Modify:** `src/autopilot/orchestration/usage.py`

**Specification References:**
- Discovery: usage.py evolution (114 lines, daily/weekly cycle-count tracking)
- RFC Section 3.4.1: UsageLimitsConfig (daily_cycle_limit, weekly_cycle_limit, max_agent_invocations_per_cycle)
- Discovery: Resource Management (per-project limits, priority weights)

**Prerequisite Requirements:**
1. Tasks 002, 006 must be complete (config, db)
2. Write tests in `tests/orchestration/test_usage.py`

**Detailed Instructions:**
1. Implement `UsageTracker` class:
   - `can_execute(project: str) -> tuple[bool, str]` checks all limits
   - `record_cycle(project: str)` increments daily/weekly counters
   - `record_agent_invocation(project: str, agent: str)`
   - `get_usage_summary(project: str | None) -> UsageSummary`
   - `reset_daily()` and `reset_weekly()` called on day/week boundaries
2. Support global limits and per-project overrides from config
3. Store usage data in SQLite (not flat JSON files as in RepEngine)
4. UsageSummary: daily_cycles, weekly_cycles, agent_invocations_today, limits, remaining

**Acceptance Criteria:**
- [ ] Usage limits prevent execution when exceeded
- [ ] Daily and weekly counters track correctly
- [ ] Per-project limits override global defaults
- [ ] Usage persists in SQLite
- [ ] All tests pass (use freezegun for time-based tests)
```

---

### Task ID: 035

- **Title**: Scheduler core -- cycle orchestration
- **File**: src/autopilot/orchestration/scheduler.py
- **Complete**: [ ]
- **Sprint Points**: 8

- **User Story (business-facing)**: As a technical architect, I want a reliable cycle orchestrator, so that autonomous development runs in structured plan-execute-report cycles with proper locking and error recovery.
- **Outcome (what this delivers)**: The core scheduler that orchestrates the plan -> dispatch -> execute -> report cycle, evolved from RepEngine's 691-line scheduler.py.

#### Prompt:

```markdown
**Objective:** Implement the core scheduler with cycle orchestration per RFC Section 3.3.

**File to Create/Modify:** `src/autopilot/orchestration/scheduler.py`

**Specification References:**
- RFC Section 3.3: Agent Orchestration Flow (full sequence diagram)
- Discovery: scheduler.py evolution (691 lines, cycle lock, circuit breaker, dispatch execution)
- RFC Section 3.8: All error recovery patterns

**Prerequisite Requirements:**
1. Tasks 002-006, 015, 031-034 must be complete (all core, utils, agent invoker, dispatcher, circuit breaker, usage)
2. Write tests in `tests/orchestration/test_scheduler.py`

**Detailed Instructions:**
1. Implement `Scheduler` class with the three-phase cycle:
   - **Phase 1 Planning**: Acquire cycle lock, validate git state, check usage limits, invoke PL agent, parse dispatch plan
   - **Phase 2 Execution**: Execute dispatches (parallel where possible), apply circuit breaker, handle timeouts and failures
   - **Phase 3 Bookkeeping**: Generate cycle report, update daily summary, record cycle in SQLite, release lock
2. Cycle lock: PID file with TTL, liveness check, force-recovery for stale locks
3. Git state validation: clean tree, correct branch (from config.git.base_branch)
4. Support configurable scheduler strategy from config (interval only for now, event triggers in Phase 7)
5. `run_cycle() -> CycleResult` executes one full cycle
6. `run_loop(interval: int)` runs cycles on interval

**Acceptance Criteria:**
- [ ] Three-phase cycle executes correctly (plan, execute, report)
- [ ] Cycle lock prevents concurrent execution
- [ ] Git state validation runs before each cycle
- [ ] Usage limits are checked before execution
- [ ] Circuit breaker aborts on consecutive failures
- [ ] Stale locks are recovered
- [ ] CycleResult records all dispatch outcomes
- [ ] All tests pass with mocked agent invocations
```

---

### Task ID: 036

- **Title**: Daemon with signal handling and log rotation
- **File**: src/autopilot/orchestration/daemon.py
- **Complete**: [ ]
- **Sprint Points**: 5

- **User Story (business-facing)**: As a system operator, I want a robust daemon process, so that autonomous execution continues reliably in the background with proper signal handling and graceful shutdown.
- **Outcome (what this delivers)**: Background daemon evolved from RepEngine with PID file management, POSIX signal handling, interruptible sleep, log rotation, and orphan detection.

#### Prompt:

```markdown
**Objective:** Evolve RepEngine daemon.py for per-project background execution.

**File to Create/Modify:** `src/autopilot/orchestration/daemon.py`

**Specification References:**
- Discovery: daemon.py evolution (167 lines, signal handling, PID file, interruptible sleep, log rotation)
- RFC Section 3.8: Session recovery (detect orphaned Claude processes)
- Discovery: Multi-daemon support (separate PID file per project)

**Prerequisite Requirements:**
1. Tasks 004, 035 must be complete (process utils, scheduler)
2. Write tests in `tests/orchestration/test_daemon.py`

**Detailed Instructions:**
1. Implement `Daemon` class:
   - `start(project_config)` daemonizes, writes PID, starts scheduler loop
   - `stop()` sends SIGTERM, waits for graceful shutdown
   - `pause()` / `resume()` suspends/resumes cycle execution
   - Signal handlers: SIGTERM (graceful stop), SIGHUP (reload config), SIGINT (stop)
   - Interruptible sleep between cycles
2. Per-project isolation: PID file at .autopilot/state/daemon.pid, logs at .autopilot/logs/
3. Log rotation: rotate daemon.log at configurable size (default 10MB)
4. Orphan detection: on startup, find and clean up orphaned Claude processes
5. Record daemon sessions in SQLite

**Acceptance Criteria:**
- [ ] Daemon starts in background with PID file
- [ ] Signal handlers work correctly (SIGTERM, SIGHUP, SIGINT)
- [ ] Per-project PID isolation prevents conflicts
- [ ] Log rotation works at configured size
- [ ] Orphaned process detection works
- [ ] All tests pass
```

---

### Task ID: 037

- **Title**: Hive-mind integration with claude-flow
- **File**: src/autopilot/orchestration/hive.py
- **Complete**: [ ]
- **Sprint Points**: 5

- **User Story (business-facing)**: As a scheduler, I want to coordinate multi-agent implementation through hive-mind, so that complex tasks are broken into worker subtasks with quality gates enforced.
- **Outcome (what this delivers)**: Hive-mind lifecycle manager evolved from RepEngine that handles branch creation, claude-flow init, worker spawn, recording, and shutdown.

#### Prompt:

```markdown
**Objective:** Evolve RepEngine hive.py with configurable quality gates and version pinning.

**File to Create/Modify:** `src/autopilot/orchestration/hive.py`

**Specification References:**
- Discovery: hive.py evolution (353 lines, hive-mind lifecycle)
- RFC ADR-7: Subprocess-based claude-flow integration
- Discovery: Key changes (configurable quality gates, version-pinned claude-flow, session recording)

**Prerequisite Requirements:**
1. Tasks 002, 004, 005 must be complete (config, subprocess, git utils)
2. Write tests in `tests/orchestration/test_hive.py`

**Detailed Instructions:**
1. Implement `HiveMindManager` class:
   - `create_branch(task_ids: list[str], project_config) -> str` with configurable naming
   - `init_hive(branch: str, objective: str, project_config) -> HiveSession`
   - `spawn_workers(session: HiveSession, worker_count: int)`
   - `record_session(session: HiveSession, result)` stores in SQLite
   - `shutdown(session: HiveSession)`
2. Version-pin claude-flow from config.claude.claude_flow_version (not hardcoded @alpha)
3. Quality gates generated by enforcement engine, not hardcoded suffix
4. Branch naming from config.git.branch_prefix + configurable strategy
5. Health check at startup: verify claude-flow is installed and correct version

**Acceptance Criteria:**
- [ ] Hive-mind lifecycle (init, spawn, record, shutdown) works
- [ ] claude-flow version is pinned from config
- [ ] Quality gates are injected from config, not hardcoded
- [ ] Branch naming uses config strategy
- [ ] Startup health check validates claude-flow availability
- [ ] All tests pass with mocked npx calls
```

---

### Task ID: 038

- **Title**: Session management data model and CRUD
- **File**: src/autopilot/core/session.py
- **Complete**: [x]
- **Sprint Points**: 5

- **User Story (business-facing)**: As a technical architect, I want to track all autonomous sessions, so that I can monitor running work, review history, and debug issues.
- **Outcome (what this delivers)**: Session management layer with SQLite-backed CRUD for daemon, cycle, discovery, and manual sessions across all projects.

#### Prompt:

```markdown
**Objective:** Implement session lifecycle management with SQLite persistence.

**File to Create/Modify:** `src/autopilot/core/session.py`

**Specification References:**
- Discovery: Session Management section (Session dataclass, operations)
- RFC Section 3.4.2: sessions table in SQLite schema
- Discovery: Session persistence (global + per-project)

**Prerequisite Requirements:**
1. Tasks 003, 006 must be complete (models, db)
2. Write tests in `tests/core/test_session.py`

**Detailed Instructions:**
1. Implement `SessionManager` class:
   - `create_session(project, type, agent_name) -> Session` inserts into SQLite
   - `update_status(session_id, status)` updates session status
   - `end_session(session_id, status)` sets ended_at timestamp
   - `list_sessions(project, status_filter, type_filter) -> list[Session]`
   - `get_session(session_id) -> Session | None`
   - `cleanup_orphaned()` finds sessions with status=running but dead PIDs
2. Session types: daemon, cycle, discovery, manual
3. Track: id, project_id, type, status, pid, started_at, ended_at, agent_name, cycle_id, metadata
4. Support cross-project queries (list all running sessions globally)

**Acceptance Criteria:**
- [ ] Sessions persist in SQLite
- [ ] CRUD operations work correctly
- [ ] Orphaned session cleanup detects dead PIDs
- [ ] Cross-project queries work
- [ ] All tests pass
```

---

### Task ID: 039

- **Title**: Session CLI commands (start, stop, list, attach, logs)
- **File**: src/autopilot/cli/session.py
- **Complete**: [ ]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a technical architect, I want to manage autonomous sessions from the CLI, so that I can start daemons, monitor progress, and review logs without leaving the terminal.
- **Outcome (what this delivers)**: CLI commands for session lifecycle management: start, stop, pause, resume, list, attach (tail logs), and log viewing.

#### Prompt:

```markdown
**Objective:** Implement session management CLI commands.

**File to Create/Modify:** `src/autopilot/cli/session.py`

**Specification References:**
- RFC Appendix B: session start|pause|resume|stop|status|log commands
- Discovery: Session Management key operations
- UX Design Section 5.5: Monitoring Workflows

**Prerequisite Requirements:**
1. Tasks 036, 038 must be complete (daemon, session manager)
2. Write tests in `tests/cli/test_session.py`

**Detailed Instructions:**
1. `session start [--project NAME]`: Start daemon for project (or active project)
2. `session stop [SESSION_ID | --project NAME]`: Graceful shutdown
3. `session pause/resume SESSION_ID`: Suspend/resume execution
4. `session list [--project NAME] [--status STATUS]`: Rich table of sessions
5. `session attach SESSION_ID`: Tail log file in real-time
6. `session log SESSION_ID [--lines N]`: View session log file
7. All commands use Rich output with status colors

**Acceptance Criteria:**
- [ ] session start launches daemon in background
- [ ] session stop gracefully shuts down
- [ ] session list shows all sessions with status
- [ ] session attach tails logs in real-time
- [ ] All commands handle errors gracefully
- [ ] All tests pass
```

---

### Task ID: 040

- **Title**: Cycle reports generator
- **File**: src/autopilot/reporting/cycle_reports.py
- **Complete**: [x]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a technical architect, I want per-cycle markdown reports, so that I can review what each autonomous cycle accomplished, which agents ran, and what issues occurred.
- **Outcome (what this delivers)**: Cycle report generator that writes structured markdown reports to .autopilot/board/cycle-reports/ with dispatch outcomes, duration, and agent results.

#### Prompt:

```markdown
**Objective:** Implement per-cycle markdown report generation.

**File to Create/Modify:** `src/autopilot/reporting/cycle_reports.py`

**Specification References:**
- Discovery: reports.py evolution (250 lines, cycle reports)
- Discovery: Reporting and Metrics (per-cycle markdown)
- RFC Section 3.4.3: cycle-reports/ directory

**Prerequisite Requirements:**
1. Tasks 003, 005 must be complete (models, paths)
2. Write tests in `tests/reporting/test_cycle_reports.py`

**Detailed Instructions:**
1. Implement `CycleReportGenerator` class:
   - `generate(cycle_result: CycleResult) -> Path` writes markdown report
   - Report includes: cycle ID, timestamp, duration, dispatches (agent, action, status, duration), overall status, errors/warnings
   - File naming: cycle-{date}-{sequence}.md
   - Section for each dispatch with outcome details
2. Reports written to .autopilot/board/cycle-reports/
3. Include summary statistics: success rate, total duration, agent breakdown

**Acceptance Criteria:**
- [ ] Cycle reports contain all dispatch outcomes
- [ ] Reports are readable markdown with proper formatting
- [ ] File naming uses date and sequence number
- [ ] Summary statistics are accurate
- [ ] All tests pass
```
