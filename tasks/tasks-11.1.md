## Summary (tasks-11.1.md)

- **Tasks in this file**: 5
- **Task IDs**: 095 - 099
- **Total Points**: 18

### Main Phase 8: Workspace Isolation -- Core Models and WorkspaceManager

Source: `docs/ideation/workspace-isolation-discovery.md`, `docs/ADR/ADR-011-workspace-isolation.md`

---

## Tasks

### Task ID: 095

- **Title**: WorkspaceConfig Pydantic model and WorkspaceInfo dataclass
- **File**: src/autopilot/core/config.py, src/autopilot/core/models.py
- **Complete**: [ ]
- **Sprint Points**: 2

- **User Story (business-facing)**: As a system operator, I want workspace isolation to be configurable via YAML, so that I can enable or disable isolated workspaces and control clone behavior without code changes.
- **Outcome (what this delivers)**: A frozen `WorkspaceConfig` Pydantic model added to `AutopilotConfig` with fields for `enabled`, `base_dir`, `cleanup_on_success`, `cleanup_on_failure`, `clone_depth`, and `max_workspaces`. A `WorkspaceInfo` dataclass in models.py for tracking workspace state at runtime.

#### Prompt:

```markdown
**Objective:** Add the `WorkspaceConfig` Pydantic model to the config hierarchy and the `WorkspaceInfo` dataclass for runtime workspace tracking.

**Files to Create/Modify:**
- `src/autopilot/core/config.py` (modify -- add WorkspaceConfig, add workspace field to AutopilotConfig)
- `src/autopilot/core/models.py` (modify -- add WorkspaceInfo dataclass, add WorkspaceStatus enum)
- `tests/core/test_config.py` (modify -- add tests for WorkspaceConfig defaults and YAML loading)
- `tests/core/test_models.py` (modify -- add tests for WorkspaceInfo)

**Prerequisite Requirements:**
1. Read `src/autopilot/core/config.py` to understand the frozen Pydantic model pattern
2. Read `src/autopilot/core/models.py` to understand the dataclass patterns used
3. Read `docs/ADR/ADR-011-workspace-isolation.md` for the configuration schema
4. Write tests first per TDD strategy

**Detailed Instructions:**
1. In `src/autopilot/core/config.py`, add a `WorkspaceConfig` model:
   ```python
   class WorkspaceConfig(BaseModel):
       model_config = ConfigDict(frozen=True)

       enabled: bool = False
       base_dir: str = "~/.autopilot/workspaces"
       cleanup_on_success: bool = True
       cleanup_on_failure: bool = False
       clone_depth: int = Field(default=0, ge=0)  # 0 = full clone
       max_workspaces: int = Field(default=5, gt=0)
   ```
2. Add `workspace: WorkspaceConfig = Field(default_factory=WorkspaceConfig)` to `AutopilotConfig`
3. In `src/autopilot/core/models.py`, add:
   ```python
   class WorkspaceStatus(StrEnum):
       CREATING = "creating"
       READY = "ready"
       ACTIVE = "active"
       CLEANING = "cleaning"
       CLEANED = "cleaned"
       FAILED = "failed"

   @dataclass  # NOTE: Not frozen -- status transitions require mutability (precedent: Session dataclass)
   class WorkspaceInfo:
       id: str
       project_name: str
       session_id: str
       workspace_dir: Path
       repository_url: str
       status: WorkspaceStatus
       created_at: datetime = field(default_factory=_utc_now)
       cleaned_at: datetime | None = None
       branch: str = ""
       clone_depth: int = 0
   ```
4. Ensure `WorkspaceConfig` defaults mean workspace isolation is OFF by default (backward compatible per ADR-011)

**Acceptance Criteria:**
- [ ] `WorkspaceConfig` model exists in config.py with all fields from ADR-011
- [ ] `AutopilotConfig` includes optional `workspace` field defaulting to disabled
- [ ] `WorkspaceInfo` dataclass exists in models.py with status tracking
- [ ] `WorkspaceStatus` enum covers full lifecycle
- [ ] Existing config YAML without workspace section still loads (backward compatible)
- [ ] All tests pass: `uv run pytest tests/core/test_config.py tests/core/test_models.py`
- [ ] `uv run ruff check src/autopilot/core/config.py src/autopilot/core/models.py` passes
- [ ] `uv run pyright src/autopilot/core/` passes
```

---

### Task ID: 096

- **Title**: ProjectRegistry repository_url extension
- **File**: src/autopilot/core/project.py
- **Complete**: [ ]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a system operator, I want autopilot to know each project's repository URL, so that workspace isolation can clone fresh copies without manual intervention.
- **Outcome (what this delivers)**: The `RegisteredProject` dataclass and `ProjectRegistry` methods updated to support an optional `repository_url` field, with backward-compatible loading of existing projects.yaml entries that lack the field.

#### Prompt:

```markdown
**Objective:** Extend `RegisteredProject` and `ProjectRegistry` to store and retrieve an optional `repository_url` field for each project.

**Files to Create/Modify:**
- `src/autopilot/core/project.py` (modify -- add repository_url to RegisteredProject, update register/find/serialization)
- `tests/core/test_project.py` (modify -- add tests for repository_url handling)

**Prerequisite Requirements:**
1. Read `src/autopilot/core/project.py` to understand the RegisteredProject dataclass and ProjectRegistry CRUD
2. Read `docs/ADR/ADR-011-workspace-isolation.md` for repository URL requirements
3. Write tests first per TDD strategy

**Detailed Instructions:**
1. Add `repository_url: str = ""` to the `RegisteredProject` dataclass
2. Update `ProjectRegistry.register()` to accept an optional `repository_url` parameter
3. Update `_dict_to_project()` to read `repository_url` from YAML (defaulting to `""` for existing entries)
4. Update `_project_to_dict()` to serialize `repository_url`
5. Add a `update_repository_url(name: str, url: str) -> None` method to `ProjectRegistry` for updating existing entries
6. Add validation: if `repository_url` is provided, it must be a plausible git URL (starts with `https://`, `git@`, `ssh://`, or is a local path). Use a simple check, not a full URL parser.
7. Update `validate_all()` to optionally warn if a project has workspace isolation enabled in its config but no `repository_url` set

**Key Backward Compatibility Concern:**
- Existing `projects.yaml` files will NOT have `repository_url`. The `_dict_to_project` method must default to `""` for missing fields.
- The `register()` method's new parameter must be optional with default `""`.

**Acceptance Criteria:**
- [ ] `RegisteredProject` has `repository_url: str = ""` field
- [ ] `ProjectRegistry.register()` accepts optional `repository_url`
- [ ] Existing projects.yaml without repository_url loads without error
- [ ] `update_repository_url()` method works for registered projects
- [ ] URL validation rejects obviously invalid URLs
- [ ] All tests pass: `uv run pytest tests/core/test_project.py`
- [ ] `uv run ruff check src/autopilot/core/project.py` passes
- [ ] `uv run pyright src/autopilot/core/project.py` passes
```

---

### Task ID: 097

- **Title**: WorkspaceManager core class with create, cleanup, and list
- **File**: src/autopilot/core/workspace.py
- **Complete**: [ ]
- **Sprint Points**: 5

- **User Story (business-facing)**: As a system operator, I want autopilot to automatically create isolated workspace clones for each session, so that agent work never conflicts with my local checkout.
- **Outcome (what this delivers)**: A `WorkspaceManager` class that creates fresh git clones in `~/.autopilot/workspaces/`, copies `.autopilot/` config into the clone, tracks workspace state, enforces `max_workspaces`, and cleans up completed workspaces.

#### Prompt:

```markdown
**Objective:** Implement the `WorkspaceManager` class that handles the full lifecycle of isolated workspace directories: creation (git clone), configuration, and cleanup.

**Files to Create/Modify:**
- `src/autopilot/core/workspace.py` (create)
- `tests/core/test_workspace.py` (create)

**Prerequisite Requirements:**
1. Read `docs/ideation/workspace-isolation-discovery.md` for the architecture overview
2. Read `docs/ADR/ADR-011-workspace-isolation.md` for the workspace lifecycle
3. Read `src/autopilot/core/config.py` for `WorkspaceConfig` (Task 095)
4. Read `src/autopilot/core/models.py` for `WorkspaceInfo` and `WorkspaceStatus` (Task 095)
5. Read `src/autopilot/core/project.py` for `ProjectRegistry` with `repository_url` (Task 096)
6. Read `src/autopilot/utils/git.py` for `clone_repository()` and `CloneResult` (Task 098 — **must be implemented first**)
7. Read `src/autopilot/utils/subprocess.py` for the subprocess runner pattern
8. Write tests first per TDD strategy

**Detailed Instructions:**
1. Create `src/autopilot/core/workspace.py` with class `WorkspaceManager`:
   ```python
   class WorkspaceManager:
       def __init__(self, config: WorkspaceConfig, project_registry: ProjectRegistry) -> None:
           ...

       def create(self, project_name: str, session_id: str, *, branch: str = "") -> WorkspaceInfo:
           """Clone a fresh workspace for a session. Raises if max_workspaces exceeded."""
           # 1. Check max_workspaces limit
           # 2. Resolve repository_url from ProjectRegistry
           # 3. Create workspace dir: base_dir / f"{project_name}-{session_id[:8]}"
           # 4. Delegate to clone_repository() from utils/git.py (Task 098)
           # 5. Copy .autopilot/ config from source project into workspace
           # 6. Return WorkspaceInfo with status=READY

       def cleanup(self, workspace_id: str) -> None:
           """Remove a workspace directory and update tracking."""

       def list_workspaces(self, project_name: str | None = None) -> list[WorkspaceInfo]:
           """List all tracked workspaces, optionally filtered by project."""

       def get_workspace(self, workspace_id: str) -> WorkspaceInfo | None:
           """Get a specific workspace by ID."""
   ```
2. Workspace directory naming: `{base_dir}/{project_name}-{session_id[:8]}/`
   - **Note:** 8-char truncation of UUID4 = ~4 billion possibilities. Collision risk is negligible for practical use but should be documented in a code comment.
3. Git clone implementation:
   - **Delegate to `clone_repository()` from `src/autopilot/utils/git.py` (Task 098)** — do NOT inline subprocess calls
   - Pass `depth=self._config.clone_depth` and `branch=branch` through to the helper
   - Check `CloneResult.success` and raise `WorkspaceError` on failure
4. Config copying: after clone, copy the `.autopilot/` directory from the source project (looked up via `ProjectRegistry.find_by_name`) into the workspace root, EXCLUDING `state/` and `logs/` subdirectories
5. Workspace tracking: use a JSON manifest file at `{base_dir}/workspaces.json` to persist workspace metadata
   - **Use file locking** following the `ProjectRegistry._locked()` pattern to prevent races from concurrent workspace creation
6. Error handling:
   - If git clone fails, clean up partial directory and raise `WorkspaceError`
   - If max_workspaces exceeded, raise `WorkspaceError` with helpful message
   - If repository_url is missing from registry, raise `WorkspaceError`

**Key Design Decisions:**
- The manifest file (`workspaces.json`) is the source of truth for workspace inventory
- Workspace IDs are the session_id (1:1 mapping between session and workspace)
- Cleanup removes both the directory and the manifest entry

**Acceptance Criteria:**
- [ ] `WorkspaceManager` class exists with create/cleanup/list/get methods
- [ ] `create()` delegates to `clone_repository()` from utils/git.py (not inline subprocess)
- [ ] `create()` copies .autopilot/ config (excluding state/ and logs/) into workspace
- [ ] `create()` enforces max_workspaces limit
- [ ] `cleanup()` removes workspace directory and manifest entry
- [ ] `list_workspaces()` reads from manifest file
- [ ] Manifest file uses file locking for concurrent access safety
- [ ] `WorkspaceError` exception class for all workspace failures
- [ ] All tests pass: `uv run pytest tests/core/test_workspace.py`
- [ ] File stays under 400 lines (Task 103 will extend this file with ~100 lines of stale detection)
- [ ] `uv run ruff check src/autopilot/core/workspace.py` passes
- [ ] `uv run pyright src/autopilot/core/workspace.py` passes
```

---

### Task ID: 098

- **Title**: Git clone subprocess helper with configuration
- **File**: src/autopilot/utils/git.py
- **Complete**: [ ]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a system operator, I want git clone operations to support shallow clones and branch targeting, so that workspace creation is fast for large repositories and agents work on the correct branch.
- **Outcome (what this delivers)**: A `clone_repository()` function in the git utils module that wraps `git clone` with configurable depth, branch, timeout, and structured error reporting.

#### Prompt:

```markdown
**Objective:** Add a `clone_repository()` function to the existing git utils module that WorkspaceManager delegates to for all clone operations.

**Files to Create/Modify:**
- `src/autopilot/utils/git.py` (modify -- add clone_repository function)
- `tests/utils/test_git.py` (modify -- add tests for clone_repository)

**Prerequisite Requirements:**
1. Read `src/autopilot/utils/git.py` to understand the existing git helper patterns
2. Read `src/autopilot/utils/subprocess.py` to understand the subprocess runner
3. Write tests first per TDD strategy
4. Use context7 for git clone subprocess best practices if needed

**Detailed Instructions:**
1. Add `clone_repository()` to `src/autopilot/utils/git.py`:
   ```python
   @dataclass(frozen=True)
   class CloneResult:
       success: bool
       workspace_dir: Path
       error: str = ""
       duration_seconds: float = 0.0

   def clone_repository(
       repository_url: str,
       target_dir: Path,
       *,
       branch: str = "",
       depth: int = 0,
       timeout_seconds: int = 120,
   ) -> CloneResult:
       """Clone a git repository into target_dir.

       Args:
           repository_url: The git URL to clone from.
           target_dir: Where to clone into (must not exist).
           branch: Optional branch to clone (--branch flag).
           depth: Clone depth (0 = full clone, >0 = shallow).
           timeout_seconds: Maximum time for clone operation.
       """
   ```
2. Build the git command: `["git", "clone", repository_url, str(target_dir)]`
   - Add `--depth {depth}` if depth > 0
   - Add `--branch {branch}` if branch is non-empty
   - Add `--single-branch` when branch is specified (avoids fetching all refs)
3. Use `subprocess.run()` with `capture_output=True`, `text=True`, `timeout=timeout_seconds`
4. Handle errors:
   - `subprocess.TimeoutExpired`: return CloneResult with error message
   - Non-zero exit code: return CloneResult with stderr
   - `FileNotFoundError` (git not installed): return CloneResult with helpful message
   - If target_dir already exists: return CloneResult with error before attempting clone
5. Validate inputs:
   - `repository_url` must not be empty
   - `target_dir` must not already exist
   - `depth` must be >= 0
   - `timeout_seconds` must be > 0

**Acceptance Criteria:**
- [ ] `clone_repository()` function exists in git.py
- [ ] `CloneResult` dataclass captures success, error, and timing
- [ ] Shallow clone works when depth > 0
- [ ] Branch targeting works when branch is specified
- [ ] Timeout handling returns structured error
- [ ] Input validation prevents empty URL, existing target dir
- [ ] All tests pass: `uv run pytest tests/utils/test_git.py`
- [ ] `uv run ruff check src/autopilot/utils/git.py` passes
- [ ] `uv run pyright src/autopilot/utils/git.py` passes
```

---

### Task ID: 099

- **Title**: Scheduler workspace integration
- **File**: src/autopilot/orchestration/scheduler.py
- **Complete**: [ ]
- **Sprint Points**: 5

- **User Story (business-facing)**: As a system operator, I want the scheduler to automatically create an isolated workspace before each cycle, so that agent execution never touches my working directory.
- **Outcome (what this delivers)**: The `Scheduler` updated to optionally create a workspace via `WorkspaceManager` before each cycle, pass the workspace path as `cwd` to dispatches, and clean up the workspace after the cycle completes (respecting cleanup policy).

#### Prompt:

```markdown
**Objective:** Integrate `WorkspaceManager` into `Scheduler.run_cycle()` so that when workspace isolation is enabled, each cycle executes in a fresh clone.

**Files to Create/Modify:**
- `src/autopilot/orchestration/scheduler.py` (modify)
- `tests/orchestration/test_scheduler.py` (modify -- add workspace integration tests)

**Prerequisite Requirements:**
1. Read `src/autopilot/orchestration/scheduler.py` to understand the three-phase cycle
2. Read `src/autopilot/core/workspace.py` for `WorkspaceManager` API (Task 097)
3. Read `src/autopilot/core/config.py` for `WorkspaceConfig` (Task 095)
4. Write tests first per TDD strategy

**Detailed Instructions:**
1. Add an optional `workspace_manager: WorkspaceManager | None = None` parameter to `Scheduler.__init__()`
2. In `run_cycle()`, before Phase 1 (planning):
   - If `self._workspace_manager` is not None and `self._config.workspace.enabled` is True:
     - Call `workspace_manager.create(project_name, cycle_id, branch=self._config.git.base_branch)`
     - Store the `WorkspaceInfo` for later cleanup
     - Override `self._cwd` with `workspace_info.workspace_dir` for this cycle
3. In `_phase_plan()`:
   - Git validation must use the workspace cwd (already uses `self._cwd`, but verify the override applies)
4. In `_execute_dispatch()`:
   - The `cwd` passed to `self._invoker.invoke()` must be the workspace path
5. After Phase 3 (bookkeeping), add workspace cleanup:
   - If cycle succeeded and `cleanup_on_success` is True: call `workspace_manager.cleanup()`
   - If cycle failed and `cleanup_on_failure` is True: call `workspace_manager.cleanup()`
   - If preserving workspace on failure: log the workspace path for debugging
6. Ensure the workspace cwd override is LOCAL to the cycle (do not mutate self._cwd permanently):
   ```python
   original_cwd = self._cwd
   try:
       if workspace_enabled:
           self._cwd = workspace_info.workspace_dir
       # ... run cycle phases ...
   finally:
       self._cwd = original_cwd
       # ... cleanup workspace ...
   ```
7. When workspace is disabled (`workspace.enabled = false`), behavior must be identical to current code (zero behavior change)

**Critical Complexity Notes:**
- The `_phase_plan` method validates git state on `self._cwd`. When workspace is enabled, this MUST validate the workspace (the fresh clone), not the developer's checkout. The current code already uses `self._cwd` for this, so the override approach works.
- If workspace creation fails, the cycle must NOT proceed. Raise `SchedulerError`.
- If workspace cleanup fails, log the error but do NOT fail the cycle result.
- **Thread-safety note:** The `self._cwd` override pattern is safe because `run_cycle()` is guarded by `self._lock`. If the lock is ever removed, this pattern would need revisiting.
- **Pre-existing bug:** `Daemon._run_loop()` passes a string to `run_cycle()` where a `DispatchPlan` is expected. Task 101 must address this when wiring the Daemon.

**Acceptance Criteria:**
- [ ] Scheduler accepts optional WorkspaceManager in constructor
- [ ] When workspace.enabled=true, a workspace is created before each cycle
- [ ] Dispatches execute in the workspace directory
- [ ] Workspace cleanup respects config (cleanup_on_success, cleanup_on_failure)
- [ ] Workspace cwd override is scoped to the cycle (not permanent)
- [ ] When workspace.enabled=false, behavior is unchanged from current code
- [ ] Workspace creation failure raises SchedulerError (cycle does not proceed)
- [ ] Workspace cleanup failure is logged but does not fail the cycle
- [ ] All tests pass: `uv run pytest tests/orchestration/test_scheduler.py`
- [ ] `uv run ruff check src/autopilot/orchestration/scheduler.py` passes
- [ ] `uv run pyright src/autopilot/orchestration/scheduler.py` passes
```

---
