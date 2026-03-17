## Summary (tasks-2.1.md)

- **Tasks in this file**: 6
- **Task IDs**: 008 - 013
- **Total Points**: 8

### Phase 3: HiveMindManager Evolution + Phase 4: CLI Commands + Phase 5a: Integration Wiring

---

## Tasks

### Task ID: 008

- **Title**: Add preflight checks and spawn_hive method to HiveMindManager
- **File**: src/autopilot/orchestration/hive.py
- **Complete**: [x]
- **Sprint Points**: 2

- **User Story (business-facing)**: As a hive-mind operator, I want a single `spawn_hive` method that validates preconditions and launches a hive-mind session via `hive-mind spawn`, so that I can replace the manual swarm-init-plus-spawn-workers workflow with one reliable call.
- **Outcome (what this delivers)**: `_preflight_checks()` method (clean git tree, no active namespace collision), `spawn_hive()` method using `subprocess.Popen` for `--claude` mode and `run_with_timeout` for non-claude mode, `_has_active_session()` helper. `HiveSession` extended with `metadata` dict field for PID storage.

#### Prompt:

```markdown
**Objective:** Add preflight validation and the new `spawn_hive` method to `HiveMindManager`, replacing the old `init_hive` + `spawn_workers` pattern.

**File to Modify:** `src/autopilot/orchestration/hive.py`

**Context:**
The discovery document (lines 500-616) specifies the new spawn pattern. With `--claude` mode, `hive-mind spawn` blocks for hours, so we use `subprocess.Popen` (non-blocking) and store the PID for monitoring/cancellation. Without `--claude`, it returns quickly and we use `run_with_timeout`. See discovery lines 159-206 for subprocess lifecycle details.

**Prerequisite Requirements:**
1. Task 001 must be complete (HiveMindConfig in config.py)
2. Read `src/autopilot/orchestration/hive.py` to understand current structure
3. Read `src/autopilot/utils/subprocess.py` for `run_with_timeout` and `build_clean_env`
4. Read discovery lines 500-616 for the spawn_hive implementation

**Detailed Instructions:**

1. Extend `HiveSession` dataclass to include a `metadata` dict:
   ```python
   @dataclass
   class HiveSession:
       id: str
       branch: str
       objective: str
       worker_count: int = 0
       started_at: float = field(default_factory=time.time)
       ended_at: float | None = None
       status: str = "active"
       metadata: dict[str, Any] = field(default_factory=dict)  # NEW
   ```
   Add the `Any` import from `typing`.

2. Add `_preflight_checks(self, namespace: str) -> None`:
   - Check `git status --porcelain` via `run_with_timeout` -- if stdout is non-empty, raise `HiveError` with message about dirty working tree
   - Check `_has_active_session(namespace)` -- if True, raise `HiveError` about active session on namespace

3. Add `_has_active_session(self, namespace: str) -> bool`:
   - Simple stub returning `False` for now (full session tracking is Phase 5a)
   - Add a docstring noting this is a placeholder

4. Add `spawn_hive(self, objective: str, *, namespace: str | None = None, use_claude: bool = True) -> HiveSession`:
   - Resolve namespace: `namespace or self._config.hive_mind.namespace or self._config.project.name`
   - Call `self._preflight_checks(ns)`
   - Create `HiveSession` with generated UUID, empty branch, and objective
   - Build command: `["npx", "ruflo@latest", "hive-mind", "spawn", objective, "--namespace", ns]`
   - If `use_claude`: append `"--claude"` and use `subprocess.Popen` with stdout/stderr PIPE, text=True, cwd, env. Store `process.pid` in `session.metadata["pid"]`. Set `session.status = "spawned"`. Store the `Popen` object in `self._active_processes[session.id]` (a `dict[str, subprocess.Popen[str]]` instance variable initialized in `__init__`) — do NOT store the Popen object in `session.metadata` as it is not serializable.
   - If not `use_claude`: use `run_with_timeout` with `spawn_timeout_seconds`. Check returncode, raise `HiveError` on failure. Set `session.status = "spawned"`.
   - Log spawn event
   - Return session

5. Add deprecation warnings to `init_hive()` and `spawn_workers()`:
   ```python
   import warnings
   warnings.warn("init_hive() is deprecated. Use spawn_hive() instead.", DeprecationWarning, stacklevel=2)
   ```

**Acceptance Criteria:**
- [ ] `HiveSession` has `metadata: dict[str, Any]` field
- [ ] `_preflight_checks` raises `HiveError` when git tree is dirty
- [ ] `_preflight_checks` raises `HiveError` when namespace has active session
- [ ] `spawn_hive` uses `subprocess.Popen` for `--claude` mode
- [ ] `spawn_hive` uses `run_with_timeout` for non-claude mode
- [ ] `spawn_hive` stores PID in `session.metadata["pid"]` for claude mode
- [ ] Popen object stored in `self._active_processes[session.id]`, NOT in `session.metadata` (non-serializable)
- [ ] Command uses `ruflo@latest` (not pinned version)
- [ ] `init_hive()` and `spawn_workers()` emit `DeprecationWarning`
- [ ] Existing tests still pass (old methods remain functional)
- [ ] `just all` passes
```

---

### Task ID: 009

- **Title**: Add stop_hive method to HiveMindManager
- **File**: src/autopilot/orchestration/hive.py
- **Complete**: [x]
- **Sprint Points**: 1

- **User Story (business-facing)**: As a hive-mind operator, I want to stop a running hive-mind session gracefully or forcefully, so that I can cancel long-running sessions or clean up orphaned processes.
- **Outcome (what this delivers)**: `stop_hive(session, force=False)` method that performs graceful shutdown via `hive-mind shutdown` followed by `os.kill(pid, SIGTERM)` fallback.

#### Prompt:

```markdown
**Objective:** Add the `stop_hive` method for stopping running hive-mind sessions.

**File to Modify:** `src/autopilot/orchestration/hive.py`

**Context:**
Discovery lines 594-616 define the stop logic. Graceful shutdown sends `hive-mind shutdown --namespace <ns>` to ruflo. Force mode skips this and goes straight to `os.kill`. Both paths terminate via SIGTERM on the stored PID.

**Prerequisite Requirements:**
1. Task 008 must be complete (spawn_hive and HiveSession with metadata)
2. Read discovery lines 594-616 for stop_hive specification

**Detailed Instructions:**

1. Add `stop_hive(self, session: HiveSession, *, force: bool = False) -> None`:

   ```python
   def stop_hive(self, session: HiveSession, *, force: bool = False) -> None:
       """Stop a running hive-mind session."""
       pid = session.metadata.get("pid")
       ns = session.metadata.get("namespace", "")

       if not force and ns:
           # Graceful: ask ruflo to shut down
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
           import os
           import signal
           try:
               os.kill(pid, signal.SIGTERM)
           except ProcessLookupError:
               pass  # already exited

       # Clean up the active process reference (Task 008 stores Popen in self._active_processes)
       self._active_processes.pop(session.id, None)

       session.status = "stopped"
       session.ended_at = time.time()
       _log.info("hive_stopped: session=%s force=%s", session.id, force)
   ```

2. Ensure `os` and `signal` imports are added at module level (move from inline).

**Acceptance Criteria:**
- [ ] `stop_hive(session)` calls graceful shutdown via ruflo then SIGTERM
- [ ] `stop_hive(session, force=True)` skips graceful shutdown, goes to SIGTERM
- [ ] `ProcessLookupError` is silently caught (process already exited)
- [ ] `subprocess.TimeoutExpired` during graceful shutdown is caught and logged
- [ ] Session status is set to `"stopped"` and `ended_at` is populated
- [ ] `just all` passes
```

---

### Task ID: 010

- **Title**: Create hive CLI command group with spawn and dry-run
- **File**: src/autopilot/cli/hive.py
- **Complete**: [x]
- **Sprint Points**: 2

- **User Story (business-facing)**: As a developer, I want `autopilot hive spawn tasks/tasks-1.md --task-ids 001-008` to build an objective and launch a hive-mind session, so that I can orchestrate multi-task implementation from the CLI without constructing objective prompts manually.
- **Outcome (what this delivers)**: `hive_app` Typer group with `spawn` command (with `--dry-run` flag to preview objectives), `status`, `list`, and `stop` subcommands. Registered in `app.py`.

#### Prompt:

```markdown
**Objective:** Create the `autopilot hive` CLI command group with spawn, status, list, and stop subcommands.

**Files to Create/Modify:**
- `src/autopilot/cli/hive.py` (new)
- `src/autopilot/cli/app.py` (register the hive_app)

**Context:**
Follow the pattern of existing CLI command groups like `src/autopilot/cli/session.py` and `src/autopilot/cli/enforce.py`. The `spawn` command is the primary command -- it builds an objective via `HiveObjectiveBuilder`, then calls `HiveMindManager.spawn_hive()`. The `--dry-run` flag prints the objective without spawning. See discovery lines 622-655.

**Prerequisite Requirements:**
1. Tasks 001, 006, 008 must be complete (config, objective builder, spawn_hive)
2. Read `src/autopilot/cli/app.py` for how command groups are registered
3. Read `src/autopilot/cli/session.py` for Typer command patterns
4. Read discovery lines 622-655 for CLI command specifications

**Detailed Instructions:**

1. Create `src/autopilot/cli/hive.py` (~150 lines):

   a. `hive_app = typer.Typer(name="hive", help="Hive-mind orchestration.")`

   b. Helper `_parse_task_ids(task_ids_str: str) -> list[str]`:
      - Parse range format: `"001-008"` -> `["001", "002", ..., "008"]`
      - Parse comma format: `"001,003,005"` -> `["001", "003", "005"]`
      - Parse mixed: `"001-003,005"` -> `["001", "002", "003", "005"]`
      - Pad to 3 digits with leading zeros

   c. `spawn` command:
      - Arguments: `task_file` (required, path to task file)
      - Options: `--task-ids` (str), `--namespace` (str), `--template` (str, default "default"), `--dry-run` (bool)
      - Resolve project via existing `_resolve_project()` pattern from `app.py`
      - Build config via `AutopilotConfig` from project
      - Create `HiveObjectiveBuilder` and call `build()`
      - If `--dry-run`: print objective and exit
      - Otherwise: create `HiveMindManager` and call `spawn_hive()`
      - Display session ID and PID on success

   d. `status` command (stub):
      - `--namespace` option
      - Print "Not yet implemented" (future: query session store)

   e. `list` command (stub):
      - Print "Not yet implemented" (future: list recent sessions)

   f. `stop` command:
      - `--namespace` option, `--force` flag
      - Print "Not yet implemented" (future: find session by namespace and call stop_hive)

2. Register in `src/autopilot/cli/app.py`:
   - Add import: `from autopilot.cli.hive import hive_app`
   - Add registration: `app.add_typer(hive_app)` alongside other command groups

**Acceptance Criteria:**
- [ ] `autopilot hive spawn tasks/tasks-1.md --task-ids 001-008 --dry-run` prints the objective
- [ ] `_parse_task_ids("001-003")` returns `["001", "002", "003"]`
- [ ] `_parse_task_ids("001,003,005")` returns `["001", "003", "005"]`
- [ ] `hive_app` is registered in `app.py`
- [ ] `autopilot hive --help` shows spawn, status, list, stop subcommands
- [ ] `spawn` handles missing project gracefully (typer.Exit(1))
- [ ] `just all` passes
```

---

### Task ID: 011

- **Title**: Task ID parser unit tests
- **File**: tests/cli/test_hive_cli.py
- **Complete**: [x]
- **Sprint Points**: 1

- **User Story (business-facing)**: As a developer, I want tests for the task ID parsing logic, so that range and comma-separated formats are verified before integration testing.
- **Outcome (what this delivers)**: Tests for `_parse_task_ids` covering range format, comma format, mixed format, single ID, and zero-padded output.

#### Prompt:

```markdown
**Objective:** Write unit tests for the task ID parser in the hive CLI module.

**File to Create:** `tests/cli/test_hive_cli.py`

**Context:**
The `_parse_task_ids` function is a pure utility function that can be tested without any CLI or subprocess mocking. Test it directly.

**Prerequisite Requirements:**
1. Task 010 must be complete (hive.py with _parse_task_ids)

**Detailed Instructions:**

1. Import `_parse_task_ids` from `autopilot.cli.hive`.

2. Test cases:
   - `"001-005"` -> `["001", "002", "003", "004", "005"]`
   - `"001,003,005"` -> `["001", "003", "005"]`
   - `"001-003,005,007-008"` -> `["001", "002", "003", "005", "007", "008"]`
   - `"042"` -> `["042"]`
   - `"1-3"` -> `["001", "002", "003"]` (zero-padded)
   - `""` -> `[]` (empty input)

3. Test that the function returns deduplicated, sorted results when ranges overlap.

**Acceptance Criteria:**
- [ ] All format variations tested (range, comma, mixed, single, empty)
- [ ] Zero-padding to 3 digits is verified
- [ ] `just all` passes
```

---

### Task ID: 012

- **Title**: Wire hive-mind into ResourceBroker and UsageTracker
- **File**: src/autopilot/orchestration/hive.py
- **Complete**: [x]
- **Sprint Points**: 1

- **User Story (business-facing)**: As the orchestration system, I want hive-mind spawns gated by resource limits and counted against usage quotas, so that runaway automation cannot exceed configured concurrency or daily invocation limits.
- **Outcome (what this delivers)**: `spawn_hive` checks `ResourceBroker.can_spawn_agent()` before spawning and records the invocation via `UsageTracker.record_cycle()` after spawning. Optional dependencies injected via constructor.

#### Prompt:

```markdown
**Objective:** Integrate hive-mind spawning with the existing ResourceBroker and UsageTracker infrastructure.

**File to Modify:** `src/autopilot/orchestration/hive.py`

**Context:**
The `ResourceBroker` (in `orchestration/resource_broker.py`) gates concurrent agent spawns. The `UsageTracker` (in `orchestration/usage.py`) counts invocations against daily/weekly limits. Both are optional dependencies -- hive-mind should work without them but respect them when present. See discovery lines 663-671.

**Prerequisite Requirements:**
1. Task 008 must be complete (spawn_hive method)
2. Read `src/autopilot/orchestration/resource_broker.py` for `ResourceBroker.can_spawn_agent()` API
3. Read `src/autopilot/orchestration/usage.py` for `UsageTracker` API

**Detailed Instructions:**

1. Extend `HiveMindManager.__init__` to accept optional dependencies:
   ```python
   def __init__(
       self,
       config: AutopilotConfig,
       *,
       cwd: Path | None = None,
       resource_broker: ResourceBroker | None = None,
       usage_tracker: UsageTracker | None = None,
   ) -> None:
       self._config = config
       self._cwd = cwd
       self._resource_broker = resource_broker
       self._usage_tracker = usage_tracker
   ```
   Use `TYPE_CHECKING` imports for `ResourceBroker` and `UsageTracker`.

2. In `spawn_hive`, add resource check before spawning. Note: `can_spawn_agent(project)` requires a `project: str` argument and returns `tuple[bool, str]` (not a bare `bool`):
   ```python
   if self._resource_broker:
       allowed, reason = self._resource_broker.can_spawn_agent(self._config.project.name)
       if not allowed:
           raise HiveError(reason)
   ```

3. After successful spawn, record usage. Note: `record_cycle(project)` requires a `project: str` argument:
   ```python
   if self._usage_tracker:
       self._usage_tracker.record_cycle(self._config.project.name)
   ```

4. Ensure existing tests still pass by keeping the new parameters optional with `None` defaults.

**Acceptance Criteria:**
- [ ] `ResourceBroker` check raises `HiveError` with the broker's reason string when `can_spawn_agent(project)` returns `(False, reason)`
- [ ] `UsageTracker.record_cycle(project)` is called with `self._config.project.name` after successful spawn
- [ ] Both dependencies are optional (None default) -- spawn works without them
- [ ] Existing `test_hive.py` tests pass without modification (constructor compatible)
- [ ] `just all` passes
```

---

### Task ID: 013

- **Title**: Add session tracking to spawn_hive via SessionManager
- **File**: src/autopilot/orchestration/hive.py
- **Complete**: [x]
- **Sprint Points**: 1

- **User Story (business-facing)**: As the session management system, I want hive-mind sessions tracked in the session store with `SessionType.HIVE_MIND`, so that `autopilot session list` shows hive-mind sessions alongside daemon and manual sessions.
- **Outcome (what this delivers)**: `spawn_hive` creates a `Session` record with `SessionType.HIVE_MIND`, stores namespace, task_file, and task_ids in session metadata. PID is recorded for process monitoring.

#### Prompt:

```markdown
**Objective:** Integrate session tracking into the hive-mind spawn lifecycle.

**File to Modify:** `src/autopilot/orchestration/hive.py`

**Context:**
The `Session` model (in `core/models.py`) and `SessionManager` (in `core/session.py`) track all sessions. Task 002 added `SessionType.HIVE_MIND`. The session metadata dict is the right place for hive-specific data (namespace, task_file, task_ids, PID). See discovery lines 673-676.

**Prerequisite Requirements:**
1. Tasks 002, 008 must be complete (SessionType.HIVE_MIND, spawn_hive)
2. Read `src/autopilot/core/models.py` for `Session` and `SessionType`
3. Read `src/autopilot/core/session.py` for `SessionManager` API

**Detailed Instructions:**

1. Add `session_manager` as an optional dependency on `HiveMindManager.__init__`:
   ```python
   session_manager: SessionManager | None = None,
   ```

2. In `spawn_hive`, after successful Popen/run, create and store a session. Note: `SessionManager.create_session()` takes individual parameters (not a pre-built `Session` object). Its signature is `create_session(project, session_type, agent_name, *, pid, cycle_id) -> Session`:
   ```python
   if self._session_manager:
       from autopilot.core.models import SessionType
       self._session_manager.create_session(
           project=self._config.project.name,
           session_type=SessionType.HIVE_MIND,
           agent_name=f"hive-mind:{ns}",
           pid=session.metadata.get("pid"),
           cycle_id=session.id,
       )
   ```
   Note: The current `SessionManager.create_session()` does not support a `metadata` dict. Storing namespace, task_file, and task_ids in session metadata requires extending the `create_session` API — this is deferred. For now, encode key context in `agent_name` (e.g., `"hive-mind:{namespace}"`) and `cycle_id` (the HiveSession UUID).

3. Update `spawn_hive` signature to accept `task_file` and `task_ids` for session metadata:
   ```python
   def spawn_hive(
       self,
       objective: str,
       *,
       namespace: str | None = None,
       use_claude: bool = True,
       task_file: str = "",
       task_ids: list[str] | None = None,
   ) -> HiveSession:
   ```

4. Store namespace in `session.metadata["namespace"]` for use by `stop_hive`.

**Acceptance Criteria:**
- [ ] `spawn_hive` calls `session_manager.create_session(project, SessionType.HIVE_MIND, agent_name, pid=..., cycle_id=...)` when `session_manager` is provided
- [ ] `agent_name` encodes the namespace (e.g., `"hive-mind:{ns}"`)
- [ ] `cycle_id` is set to the `HiveSession.id` UUID
- [ ] Session PID matches the Popen process PID
- [ ] `session_manager` is optional (spawn works without it)
- [ ] Existing tests pass without modification
- [ ] `just all` passes
```
