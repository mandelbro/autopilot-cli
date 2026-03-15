## Summary (tasks-11.2.md)

- **Tasks in this file**: 5
- **Task IDs**: 100 - 104
- **Total Points**: 18

### Main Phase 8: Workspace Isolation -- Pipeline Integration, CLI, and Operations

Source: `docs/ideation/workspace-isolation-discovery.md`, `docs/ADR/ADR-011-workspace-isolation.md`

---

## Tasks

### Task ID: 100

- **Title**: AgentInvoker workspace cwd propagation
- **File**: src/autopilot/orchestration/agent_invoker.py
- **Complete**: [x]
- **Sprint Points**: 2

- **User Story (business-facing)**: As a system operator, I want agents to run in the isolated workspace directory, so that all file operations and git commands target the clone instead of my checkout.
- **Outcome (what this delivers)**: Verification that `AgentInvoker.invoke()` correctly propagates the workspace `cwd` to the underlying `run_claude_cli()` call, plus a new `validate_workspace_cwd()` helper that confirms the target directory is a valid git repository before agent invocation.

#### Prompt:

```markdown
**Objective:** Ensure AgentInvoker correctly propagates workspace cwd and add a pre-invocation validation step.

**Files to Create/Modify:**
- `src/autopilot/orchestration/agent_invoker.py` (modify -- add workspace validation)
- `tests/orchestration/test_agent_invoker.py` (modify -- add workspace cwd tests)

**Prerequisite Requirements:**
1. Read `src/autopilot/orchestration/agent_invoker.py` to understand the existing cwd handling
2. Read `src/autopilot/utils/subprocess.py` to verify cwd is forwarded to subprocess
3. Write tests first per TDD strategy

**Detailed Instructions:**
1. The existing `invoke()` method already accepts `cwd: Path | None`. Verify this flows through `_invoke_with_retries()` to `run_claude_cli()` correctly (it does based on current code).
2. Add a `validate_cwd()` static method:
   ```python
   @staticmethod
   def validate_cwd(cwd: Path) -> list[str]:
       """Validate that cwd is a suitable workspace directory.

       Returns a list of issues (empty if valid).
       """
       issues = []
       if not cwd.exists():
           issues.append(f"Directory does not exist: {cwd}")
       elif not cwd.is_dir():
           issues.append(f"Path is not a directory: {cwd}")
       elif not (cwd / ".git").exists():
           issues.append(f"Not a git repository: {cwd}")
       return issues
   ```
3. In `invoke()`, if `cwd` is provided, call `validate_cwd()` and log warnings for any issues (but do not block invocation -- the git validation in Scheduler already covers this)
4. Add tests that verify:
   - `cwd` parameter flows through to `run_claude_cli()`
   - `validate_cwd()` catches missing directory, non-directory, and non-git-repo
   - Agent invocation with a valid workspace cwd succeeds

**Acceptance Criteria:**
- [ ] `validate_cwd()` static method exists and checks directory/git validity
- [ ] `invoke()` logs warnings from `validate_cwd()` when cwd is provided
- [ ] cwd propagation to subprocess is verified by tests
- [ ] All tests pass: `uv run pytest tests/orchestration/test_agent_invoker.py`
- [ ] `uv run ruff check src/autopilot/orchestration/agent_invoker.py` passes
- [ ] `uv run pyright src/autopilot/orchestration/agent_invoker.py` passes
```

---

### Task ID: 101

- **Title**: Daemon and SessionManager workspace lifecycle
- **File**: src/autopilot/orchestration/daemon.py, src/autopilot/core/session.py
- **Complete**: [ ]
- **Sprint Points**: 5

- **User Story (business-facing)**: As a system operator, I want the daemon to manage workspace creation per session and store workspace paths in session metadata, so that I can trace which workspace belongs to which session and workspaces are cleaned up when sessions end.
- **Outcome (what this delivers)**: The `Daemon` updated to create a `WorkspaceManager` at startup, pass it to the `Scheduler`, and store workspace paths in `Session.metadata`. `SessionManager.end_session()` extended to trigger workspace cleanup based on session outcome.

#### Prompt:

```markdown
**Objective:** Wire workspace lifecycle into the Daemon startup and SessionManager session-end flows.

**Files to Create/Modify:**
- `src/autopilot/orchestration/daemon.py` (modify -- create WorkspaceManager, pass to Scheduler)
- `src/autopilot/core/session.py` (modify -- add workspace cleanup on session end)
- `tests/orchestration/test_daemon.py` (modify -- add workspace lifecycle tests)
- `tests/core/test_session.py` (modify -- add workspace cleanup tests)

**Prerequisite Requirements:**
1. Read `src/autopilot/orchestration/daemon.py` to understand Daemon.start() and _run_loop()
2. Read `src/autopilot/core/session.py` to understand SessionManager.end_session()
3. Read `src/autopilot/core/workspace.py` for WorkspaceManager API (Task 097)
4. Read `src/autopilot/core/config.py` for WorkspaceConfig (Task 095)
5. Write tests first per TDD strategy

**Detailed Instructions:**

**Daemon changes:**
1. Add optional `workspace_manager: WorkspaceManager | None = None` to `Daemon.__init__()`
2. In `start()`, if `self._config.workspace.enabled`:
   - Create a `WorkspaceManager` if one was not injected (using config and project registry)
   - Pass it to `self._scheduler` (the Scheduler now accepts it per Task 099)
3. In `_run_loop()`, no changes needed -- the Scheduler handles per-cycle workspace creation

**SessionManager changes:**
1. Add a `set_workspace_path(session_id: str, workspace_dir: str) -> None` method that stores the workspace path in the session's metadata column
2. Add a `get_workspace_path(session_id: str) -> str | None` method that retrieves it
3. **Do NOT inject WorkspaceManager into SessionManager.end_session().** SessionManager is a pure data/persistence layer — workspace cleanup is an orchestration concern that belongs in the Daemon.

**Daemon cleanup orchestration (after end_session):**
1. After calling `self._session_manager.end_session()`, the Daemon checks workspace cleanup:
   - If status is COMPLETED and config says cleanup_on_success: call `workspace_manager.cleanup(session_id)`
   - If status is FAILED and config says cleanup_on_failure: call `workspace_manager.cleanup(session_id)`
   - Wrap cleanup in try/except to prevent cleanup failure from breaking the session-end flow
2. **Fix pre-existing bug:** `Daemon._run_loop()` currently passes a string to `Scheduler.run_cycle()` where a `DispatchPlan` is expected. Fix the call to construct a proper `DispatchPlan` or adjust the Scheduler's API.

**Key Design Decision:**
- Workspace path is stored in `Session.metadata["workspace_dir"]` rather than a new database column. This avoids a schema migration and uses the existing extensible metadata field.
- The Daemon owns the WorkspaceManager lifecycle AND cleanup orchestration. SessionManager stays a pure data layer.

**Acceptance Criteria:**
- [ ] Daemon creates WorkspaceManager when workspace.enabled is true
- [ ] Daemon passes WorkspaceManager to Scheduler
- [ ] SessionManager.set_workspace_path() stores path in metadata
- [ ] SessionManager.get_workspace_path() retrieves path from metadata
- [ ] Daemon triggers workspace cleanup after end_session based on status and config
- [ ] Workspace cleanup failure does not prevent session from ending
- [ ] When workspace.enabled=false, Daemon behavior is unchanged
- [ ] Pre-existing `_run_loop()` type mismatch is fixed
- [ ] All tests pass: `uv run pytest tests/orchestration/test_daemon.py tests/core/test_session.py`
- [ ] `uv run ruff check src/autopilot/orchestration/daemon.py src/autopilot/core/session.py` passes
- [ ] `uv run pyright src/autopilot/orchestration/daemon.py src/autopilot/core/session.py` passes
```

---

### Task ID: 102

- **Title**: CLI workspace list and cleanup commands
- **File**: src/autopilot/cli/session.py
- **Complete**: [ ]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a system operator, I want CLI commands to list active workspaces and manually clean up stale ones, so that I can monitor disk usage and recover from failed sessions without navigating the filesystem.
- **Outcome (what this delivers)**: Two new subcommands under a `session workspace` nested group: `session workspace list` and `session workspace cleanup`, with Rich table output showing workspace state, project, session, and disk usage. Uses a nested Typer sub-group to maintain consistency with the existing single-word command pattern (`start`, `stop`, `list`, etc.).

#### Prompt:

```markdown
**Objective:** Add workspace management CLI commands for listing and cleaning up workspaces.

**Files to Create/Modify:**
- `src/autopilot/cli/session.py` (modify -- add workspace-list and workspace-cleanup commands)
- `tests/cli/test_session.py` (modify -- add tests for new commands)

**Prerequisite Requirements:**
1. Read `src/autopilot/cli/session.py` to understand the command registration pattern
2. Read `src/autopilot/core/workspace.py` for WorkspaceManager API (Task 097)
3. Read `src/autopilot/cli/display.py` for Rich output patterns
4. Write tests first per TDD strategy

**Detailed Instructions:**
1. Create a nested Typer sub-group for workspace commands (consistent with existing single-word patterns):
   ```python
   workspace_app = typer.Typer(help="Workspace management commands.")
   app.add_typer(workspace_app, name="workspace")

   @workspace_app.command("list")
   def workspace_list(
       project: str | None = typer.Option(None, "--project", "-p"),
   ) -> None:
       """List all workspace directories with status and disk usage."""
   ```
   - Instantiate WorkspaceManager from config
   - Call `list_workspaces(project_name=project)`
   - Display Rich table with columns: ID (short), Project, Session, Status, Path, Size, Created
   - Calculate directory size using `shutil.disk_usage()` or walk
   - Show total disk usage at bottom

2. Add `cleanup` command to the workspace sub-group:
   ```python
   @workspace_app.command("cleanup")
   def workspace_cleanup(
       workspace_id: str | None = typer.Argument(None),
       all_workspaces: bool = typer.Option(False, "--all"),
       stale: bool = typer.Option(False, "--stale"),
       force: bool = typer.Option(False, "--force"),
   ) -> None:
       """Clean up workspace directories."""
   ```
   - If `workspace_id` is provided: clean up that specific workspace
   - If `--all`: clean up all workspaces (with confirmation unless --force)
   - If `--stale`: clean up only workspaces whose sessions are no longer running
   - Show summary of cleaned workspaces and disk space reclaimed

3. Use `typer.confirm()` for destructive operations unless `--force` is passed

**Acceptance Criteria:**
- [ ] `session workspace list` command shows all workspaces in a Rich table
- [ ] `session workspace list` supports --project filter
- [ ] `session workspace cleanup` supports single workspace, --all, and --stale modes
- [ ] Destructive cleanup requires confirmation (unless --force)
- [ ] Commands handle missing .autopilot dir gracefully
- [ ] All tests pass: `uv run pytest tests/cli/test_session.py`
- [ ] `uv run ruff check src/autopilot/cli/session.py` passes
- [ ] `uv run pyright src/autopilot/cli/session.py` passes
```

---

### Task ID: 103

- **Title**: Stale workspace detection and disk usage reporting
- **File**: src/autopilot/core/workspace.py
- **Complete**: [x]
- **Sprint Points**: 5

- **User Story (business-facing)**: As a system operator, I want autopilot to detect orphaned workspaces from crashed sessions, so that disk space is not wasted by workspace directories that no one is using.
- **Outcome (what this delivers)**: A `detect_stale()` method on `WorkspaceManager` that cross-references workspace manifest entries against a session status lookup callback to find workspaces whose sessions have ended or crashed, plus a `disk_usage()` method for reporting.

#### Prompt:

```markdown
**Objective:** Add stale workspace detection and disk usage reporting to WorkspaceManager.

**Files to Create/Modify:**
- `src/autopilot/core/workspace.py` (modify -- add detect_stale and disk_usage methods)
- `tests/core/test_workspace.py` (modify -- add stale detection and disk usage tests)

**Prerequisite Requirements:**
1. Read `src/autopilot/core/workspace.py` for existing WorkspaceManager (Task 097)
2. Read `src/autopilot/core/session.py` for SessionManager.get_session() (for session status lookup)
3. Write tests first per TDD strategy

**Detailed Instructions:**

**Important: Avoid bidirectional dependency.** WorkspaceManager (core/) must NOT import SessionManager directly. Instead, use a callback protocol to decouple the modules:

```python
from collections.abc import Callable
from autopilot.core.models import SessionStatus

# Type alias for session status lookup — avoids importing SessionManager
SessionStatusLookup = Callable[[str], SessionStatus | None]
```

1. Add `detect_stale(get_session_status: SessionStatusLookup) -> list[WorkspaceInfo]`:
   - For each workspace in the manifest:
     - Look up the session status by calling `get_session_status(workspace.session_id)`
     - If result is None (session deleted), mark workspace as stale
     - If status is COMPLETED or FAILED, mark workspace as stale
   - Return list of stale workspaces
   - **Callers** (CLI, Daemon) pass `lambda sid: session_manager.get_session(sid).status` as the callback

2. Add `disk_usage(workspace_id: str | None = None) -> dict[str, int]`:
   - If workspace_id is provided: return size of that workspace directory
   - If None: return total size of all workspaces plus per-workspace breakdown
   - Use `shutil.disk_usage()` for the base_dir, and `sum(f.stat().st_size for f in dir.rglob('*'))` for per-workspace sizes
   - Return dict like: `{"total_bytes": N, "workspaces": {"id1": N1, "id2": N2}}`

3. Add `cleanup_stale(get_session_status: SessionStatusLookup) -> list[str]`:
   - Calls `detect_stale()`, then `cleanup()` for each stale workspace
   - Returns list of cleaned workspace IDs
   - Logs each cleanup operation

**Edge Cases:**
- Workspace directory exists on disk but not in manifest (orphaned filesystem entry)
- Manifest entry exists but directory is already gone (stale manifest entry)
- Handle both cases gracefully: scan filesystem for untracked workspace dirs, prune stale manifest entries

**File Size Note:** After adding these methods, `workspace.py` may approach 400 lines. If it exceeds 400 lines, extract `detect_stale()`, `disk_usage()`, and `cleanup_stale()` into a separate `workspace_ops.py` module.

**Acceptance Criteria:**
- [ ] `detect_stale()` accepts a `SessionStatusLookup` callback (not SessionManager directly)
- [ ] `detect_stale()` identifies workspaces whose sessions are ended or crashed
- [ ] `disk_usage()` reports per-workspace and total byte counts
- [ ] `cleanup_stale()` removes stale workspaces and returns cleaned IDs
- [ ] Orphaned filesystem directories (not in manifest) are detected
- [ ] Stale manifest entries (directory gone) are pruned
- [ ] File stays under 500 lines (extract to workspace_ops.py if needed)
- [ ] All tests pass: `uv run pytest tests/core/test_workspace.py`
- [ ] `uv run ruff check src/autopilot/core/workspace.py` passes
- [ ] `uv run pyright src/autopilot/core/workspace.py` passes
```

---

### Task ID: 104

- **Title**: Update init command for repository URL and session start workspace flag
- **File**: src/autopilot/cli/app.py, src/autopilot/cli/project.py, src/autopilot/core/project.py, src/autopilot/cli/session.py
- **Complete**: [ ]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a developer setting up a new project, I want `autopilot init` to optionally capture the repository URL, so that workspace isolation works out of the box without additional configuration.
- **Outcome (what this delivers)**: The `init` command updated to accept an optional `--repository-url` flag that stores the URL in the project registry. The `session start` command updated to pass workspace configuration through to the daemon.

#### Prompt:

```markdown
**Objective:** Update the init and session-start CLI commands to support workspace isolation configuration.

**Files to Create/Modify:**
- `src/autopilot/cli/app.py` (modify -- update `init()` command to accept --repository-url flag)
- `src/autopilot/cli/project.py` (modify -- update `run_init()` to pass repository_url to registry)
- `src/autopilot/core/project.py` (modify -- update `initialize_project()` to accept repository_url)
- `src/autopilot/cli/session.py` (modify -- update session_start to wire WorkspaceManager)
- `tests/cli/test_init.py` (modify -- add repository URL tests)
- `tests/cli/test_session.py` (modify -- add workspace wiring tests)

**Prerequisite Requirements:**
1. Read the init command source to understand current parameter handling
2. Read `src/autopilot/core/project.py` for `ProjectRegistry.register()` with `repository_url` (Task 096)
3. Read `src/autopilot/cli/session.py` for `session_start` command (current implementation)
4. Write tests first per TDD strategy

**Detailed Instructions:**

**Init command changes:**
1. Add `--repository-url` / `-r` option (default empty string)
2. If provided, pass `repository_url` to `ProjectRegistry.register()`
3. If not provided but the current directory is a git repo, attempt to auto-detect:
   - Run `git remote get-url origin` and use the result if available
   - If auto-detection fails, skip silently (not required)
4. Add to the `next_steps` output: "Set repository URL with 'autopilot config set workspace.repository_url <url>' for workspace isolation"

**Session start changes:**
1. In `session_start()`, after creating the Scheduler:
   - If `config.workspace.enabled` is True:
     - Create a `WorkspaceManager` from config and project registry
     - Pass it to the Scheduler (which now accepts it per Task 099)
   - If workspace.enabled is False: no change to current behavior
2. Add `--no-workspace` flag that overrides `workspace.enabled` to False for this session

**Acceptance Criteria:**
- [ ] `autopilot init --repository-url <url>` stores URL in project registry
- [ ] Auto-detection of origin URL works when --repository-url is not provided
- [ ] `session start` creates WorkspaceManager when workspace.enabled is true
- [ ] `session start --no-workspace` disables workspace isolation for that session
- [ ] All tests pass for modified test files
- [ ] `uv run ruff check` passes for modified files
- [ ] `uv run pyright` passes for modified files
```

---
