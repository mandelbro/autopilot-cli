## Summary (tasks-2.2.md)

- **Tasks in this file**: 4
- **Task IDs**: 014 - 017
- **Total Points**: 4

### Phase 5b: Test Coverage

---

## Tasks

### Task ID: 014

- **Title**: Tests for spawn_hive and preflight checks
- **File**: tests/orchestration/test_hive.py
- **Complete**: [ ]
- **Sprint Points**: 1

- **User Story (business-facing)**: As a developer, I want tests for the new spawn_hive method and preflight checks, so that I can verify the Popen-based spawning, git validation, and error handling work correctly.
- **Outcome (what this delivers)**: New test classes in the existing `test_hive.py` covering `spawn_hive` (claude and non-claude modes), preflight checks (dirty git, active namespace), and `stop_hive` (graceful, force, missing PID).

#### Prompt:

```markdown
**Objective:** Extend the existing hive test file with tests for new Phase 3 methods.

**File to Modify:** `tests/orchestration/test_hive.py`

**Context:**
The existing test file has fixtures and mock patterns established. Add new test classes following the same patterns. Mock `subprocess.Popen` for claude-mode tests and `run_with_timeout` for non-claude tests.

**Prerequisite Requirements:**
1. Tasks 008-009 must be complete (spawn_hive, stop_hive)
2. Read `tests/orchestration/test_hive.py` for existing patterns

**Detailed Instructions:**

1. Update the `config` fixture to include `HiveMindConfig`:
   ```python
   from autopilot.core.config import HiveMindConfig
   # Add to fixture:
   hive_mind=HiveMindConfig(namespace="test-ns", spawn_timeout_seconds=10)
   ```

2. `TestPreflightChecks`:
   - Test dirty git tree raises `HiveError`
   - Test clean git tree passes
   - Mock `run_with_timeout` to return non-empty stdout for dirty case

3. `TestSpawnHive`:
   - Test claude mode: mock `subprocess.Popen`, verify PID in metadata, session status is "spawned"
   - Test non-claude mode: mock `run_with_timeout`, verify session status is "spawned"
   - Test non-claude failure: mock returncode=1, verify `HiveError` raised
   - Test namespace resolution: no namespace arg -> uses config namespace -> uses project name

4. `TestStopHive`:
   - Test graceful stop: verify `hive-mind shutdown` command is called, then SIGTERM
   - Test force stop: verify `hive-mind shutdown` is NOT called, SIGTERM sent
   - Test stop with already-exited process: `ProcessLookupError` is silently caught
   - Test stop with no PID: no `os.kill` call

5. `TestDeprecationWarnings`:
   - Test `init_hive()` emits `DeprecationWarning`
   - Test `spawn_workers()` emits `DeprecationWarning`

**Acceptance Criteria:**
- [ ] Preflight check tests cover dirty and clean git states
- [ ] Spawn tests cover both claude and non-claude modes
- [ ] Stop tests cover graceful, force, and error cases
- [ ] Deprecation warnings are tested with `pytest.warns(DeprecationWarning)`
- [ ] Existing tests are NOT modified (only new test classes added)
- [ ] `just all` passes
```

---

### Task ID: 015

- **Title**: Tests for ResourceBroker and UsageTracker integration
- **File**: tests/orchestration/test_hive.py
- **Complete**: [ ]
- **Sprint Points**: 1

- **User Story (business-facing)**: As a developer, I want tests verifying that resource limits and usage tracking are enforced during hive-mind spawning, so that production guardrails work correctly.
- **Outcome (what this delivers)**: Tests for `spawn_hive` with mocked `ResourceBroker` and `UsageTracker`, covering both allowed and denied scenarios.

#### Prompt:

```markdown
**Objective:** Add integration tests for ResourceBroker and UsageTracker wiring in spawn_hive.

**File to Modify:** `tests/orchestration/test_hive.py`

**Context:**
Task 012 added optional ResourceBroker and UsageTracker to HiveMindManager. These tests verify the wiring works correctly with mocked dependencies.

**Prerequisite Requirements:**
1. Task 012 must be complete

**Detailed Instructions:**

1. `TestResourceBrokerIntegration`:
   - Create manager with mocked `ResourceBroker` that returns `False` from `can_spawn_agent()`
   - Verify `spawn_hive` raises `HiveError` with resource-denied message
   - Create manager with mocked `ResourceBroker` that returns `True`
   - Verify spawn succeeds (mock Popen to prevent actual subprocess)

2. `TestUsageTrackerIntegration`:
   - Create manager with mocked `UsageTracker`
   - After successful spawn, verify `record_cycle()` was called once
   - After failed spawn (HiveError), verify `record_cycle()` was NOT called

3. Test that manager works correctly when both dependencies are `None` (the default case).

**Acceptance Criteria:**
- [ ] ResourceBroker denial raises HiveError
- [ ] UsageTracker.record_cycle() called on success only
- [ ] None dependencies work without errors
- [ ] `just all` passes
```

---

### Task ID: 016

- **Title**: CLI smoke tests for hive commands
- **File**: tests/cli/test_hive_cli.py
- **Complete**: [ ]
- **Sprint Points**: 1

- **User Story (business-facing)**: As a developer, I want CLI smoke tests for the hive command group, so that I can verify commands are registered, help text works, and basic argument parsing is correct.
- **Outcome (what this delivers)**: Tests using `typer.testing.CliRunner` for `hive spawn --dry-run`, `hive --help`, `hive status`, `hive list`, and `hive stop`.

#### Prompt:

```markdown
**Objective:** Add CLI smoke tests for the hive command group.

**File to Modify:** `tests/cli/test_hive_cli.py` (extend the file from Task 011)

**Context:**
Follow CLI test patterns from `tests/cli/test_session_cli.py` or similar. Use `typer.testing.CliRunner` to invoke commands. Mock subprocess calls to prevent actual process spawning.

**Prerequisite Requirements:**
1. Tasks 010-011 must be complete (hive CLI + parser tests)
2. Read existing CLI test files for patterns

**Detailed Instructions:**

1. Add `TestHiveCLI` class:

   a. Test `autopilot hive --help` returns exit code 0 and shows subcommands
   b. Test `autopilot hive spawn --help` returns exit code 0 and shows options
   c. Test `autopilot hive spawn tasks/file.md --dry-run` with mocked config prints objective
   d. Test `autopilot hive status` returns exit code 0 (stub response)
   e. Test `autopilot hive list` returns exit code 0 (stub response)
   f. Test `autopilot hive stop` returns exit code 0 (stub response)

2. Use `CliRunner` from `typer.testing`:
   ```python
   from typer.testing import CliRunner
   from autopilot.cli.app import app

   runner = CliRunner()
   result = runner.invoke(app, ["hive", "--help"])
   assert result.exit_code == 0
   ```

3. For the dry-run test, mock the config loading and `HiveObjectiveBuilder` to return a known string.

**Acceptance Criteria:**
- [ ] All hive subcommands are reachable via the CLI runner
- [ ] Help text includes "spawn", "status", "list", "stop"
- [ ] Dry-run test verifies objective is printed to stdout
- [ ] No actual subprocesses are spawned in any test
- [ ] `just all` passes
```

---

### Task ID: 017

- **Title**: Config integration tests for HiveMindConfig with merge
- **File**: tests/core/test_hive_config.py
- **Complete**: [ ]
- **Sprint Points**: 1

- **User Story (business-facing)**: As a developer, I want tests for the three-level config merge with hive-mind settings, so that global defaults, project overrides, and CLI flags work correctly for hive-mind configuration.
- **Outcome (what this delivers)**: Tests for `AutopilotConfig.merge()` with hive-mind sections in both global and project configs, verifying that project values override global defaults for hive-mind fields.

#### Prompt:

```markdown
**Objective:** Add integration tests for HiveMindConfig in the three-level config merge system.

**File to Modify:** `tests/core/test_hive_config.py` (extend the file from Task 003)

**Context:**
The `AutopilotConfig.merge(global_path, project_path)` method merges global defaults with project overrides. HiveMindConfig should follow the same merge semantics as other config sections. See `tests/core/test_config.py` for existing merge tests.

**Prerequisite Requirements:**
1. Task 003 must be complete (basic HiveMindConfig tests)
2. Read `tests/core/test_config.py` for merge test patterns

**Detailed Instructions:**

1. `TestHiveMindConfigMerge`:

   a. Test global hive_mind config applied when project has no hive_mind section:
      - Write global YAML with `hive_mind: {enabled: true, namespace: "global-ns"}`
      - Write project YAML with only `project: {name: "test"}`
      - `AutopilotConfig.merge()` should have `enabled=True, namespace="global-ns"`

   b. Test project overrides global hive_mind values:
      - Global: `hive_mind: {enabled: false, namespace: "global"}`
      - Project: `hive_mind: {enabled: true, namespace: "project-ns"}`
      - Merged should have `enabled=True, namespace="project-ns"`

   c. Test partial override (project overrides only some fields):
      - Global: `hive_mind: {enabled: true, worker_count: 8, namespace: "global"}`
      - Project: `hive_mind: {namespace: "project-ns"}`
      - Merged should have `enabled=True, worker_count=8, namespace="project-ns"` (deep merge)

   d. Test default values when neither global nor project specify hive_mind:
      - Both files have only `project: {name: "test"}`
      - `hive_mind.enabled` should be `False`, `worker_count` should be `4`

2. Use `tmp_path` to write YAML files for each test case.

**Acceptance Criteria:**
- [ ] Global-only, project-override, partial-override, and no-config cases tested
- [ ] Deep merge preserves unoverridden fields within hive_mind section
- [ ] Tests use `tmp_path` and real YAML files (not dict construction)
- [ ] `just all` passes
```
