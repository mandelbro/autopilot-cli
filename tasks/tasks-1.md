## Summary (tasks-1.md)

- **Tasks in this file**: 10
- **Task IDs**: 001 - 010
- **Total Points**: 38

### Main Phase 1: Foundation -- Package Setup, Config, Models, Utilities, SQLite

---

## Tasks

### Task ID: 001

- **Title**: Package scaffolding and project structure
- **File**: pyproject.toml, src/autopilot/__init__.py, src/autopilot/__main__.py
- **Complete**: [x]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a developer, I want a properly structured Python package with all build configuration, so that the project can be installed, tested, and distributed via PyPI.
- **Outcome (what this delivers)**: A working Python package skeleton that can be installed with `uv pip install -e .` and run with `python -m autopilot`.

#### Prompt:

```markdown
**Objective:** Create the foundational package structure for autopilot-cli.

**File to Create/Modify:**
- `pyproject.toml`
- `src/autopilot/__init__.py`
- `src/autopilot/__main__.py`
- `tests/conftest.py`

**Specification References:**
- RFC Section 3.2: Package structure with src layout
- RFC Appendix A: Dependency table (pydantic>=2.10, pyyaml>=6.0, structlog>=24.0, typer>=0.15, rich>=13.0, prompt-toolkit>=3.0, jinja2>=3.1)
- Discovery: Dependency Strategy section
- RFC ADR-1: PyPI distribution with uv tool install

**Prerequisite Requirements:**
1. Use context7 for latest pyproject.toml best practices
2. Create test infrastructure with conftest.py

**Detailed Instructions:**
1. Create `pyproject.toml` with:
   - name: "autopilot-cli", requires-python: ">=3.12"
   - All production dependencies from RFC Appendix A
   - Dev dependencies: pytest>=8.0, pytest-cov>=5.0, freezegun>=1.4, ruff>=0.9, pyright>=1.1
   - Script entry point: autopilot = "autopilot.cli.app:app"
   - Ruff and pyright configuration sections
2. Create `src/autopilot/__init__.py` with version string
3. Create `src/autopilot/__main__.py` that imports and runs the CLI app
4. Create empty `__init__.py` files for all subpackages: cli/, core/, orchestration/, enforcement/, reporting/, monitoring/, coordination/, utils/
5. Create `tests/conftest.py` with basic fixtures (tmp_path for project dirs, mock config)

**Acceptance Criteria:**
- [ ] `uv pip install -e .` succeeds and `python -m autopilot --help` runs
- [ ] `uv run pytest` runs, `uv run ruff check .` and `uv run pyright` pass
- [ ] All subpackage __init__.py files exist

```

---

### Task ID: 002

- **Title**: Core configuration model with Pydantic
- **File**: src/autopilot/core/config.py
- **Complete**: [x]
- **Sprint Points**: 5

- **User Story (business-facing)**: As a technical architect, I want a validated configuration system, so that project settings are type-safe and documented with sensible defaults.
- **Outcome (what this delivers)**: Complete Pydantic configuration model covering all project, scheduler, agent, quality gate, enforcement, safety, and git settings with YAML loading.

#### Prompt:

```markdown
**Objective:** Implement the full configuration model hierarchy as specified in RFC Section 3.4.1.

**File to Create/Modify:** `src/autopilot/core/config.py`

**Specification References:**
- RFC Section 3.4.1: All Pydantic model definitions (ProjectConfig, SchedulerConfig, UsageLimitsConfig, AgentsConfig, QualityGatesConfig, EnforcementConfig, SafetyConfig, ApprovalConfig, ClaudeConfig, GitConfig, AutopilotConfig)
- RFC ADR-5: YAML configuration format
- Discovery: Configuration Format section

**Prerequisite Requirements:**
1. Task 001 must be complete (package structure)
2. Write tests first in `tests/core/test_config.py`
3. Use context7 for Pydantic v2 best practices

**Detailed Instructions:**
1. Implement all Pydantic models from RFC 3.4.1 with exact field names, types, and defaults
2. Add `AutopilotConfig.from_yaml(path: Path) -> AutopilotConfig` class method for YAML loading
3. Add `AutopilotConfig.to_yaml(path: Path) -> None` for serialization
4. Implement three-level config hierarchy: global defaults (~/.autopilot/config.yaml) -> project overrides (.autopilot/config.yaml) -> CLI flags
5. Add validation for enum fields (strategy, project type, branch_strategy)
6. Add `RenderServiceConfig` and `DeploymentMonitoringConfig` models per Discovery monitoring section

**Acceptance Criteria:**
- [ ] All 10+ Pydantic models from RFC 3.4.1 are implemented
- [ ] YAML round-trip preserves all values; defaults match RFC exactly
- [ ] Invalid values raise ValidationError with clear messages
- [ ] Config merging (global + project) works correctly
- [ ] All tests pass

```

---

### Task ID: 003

- **Title**: Core data models
- **File**: src/autopilot/core/models.py
- **Complete**: [x]
- **Sprint Points**: 5

- **User Story (business-facing)**: As a developer, I want well-defined data models for all domain objects, so that data flows through the system with type safety and validation.
- **Outcome (what this delivers)**: Pydantic/dataclass models for Dispatch, DispatchPlan, AgentResult, Session, CycleResult, SprintResult, Violation, and all enforcement-related types.

#### Prompt:

```markdown
**Objective:** Implement all shared data models referenced across the system.

**File to Create/Modify:** `src/autopilot/core/models.py`

**Specification References:**
- RFC Section 3.3: AgentOrchestration flow models (DispatchPlan, Dispatch)
- RFC Section 3.7: AgentRegistry types
- RFC Section 3.8: Error recovery types
- Discovery: models.py evolution plan (Dispatch, DispatchPlan, UsageState, AgentResult)
- Discovery: Session dataclass definition

**Prerequisite Requirements:**
1. Task 001 must be complete
2. Write tests first in `tests/core/test_models.py`

**Detailed Instructions:**
1. Port and evolve RepEngine models: Dispatch, DispatchPlan, AgentResult, UsageState
2. Add Session model with fields: id, project, type (SessionType enum), status (SessionStatus enum), pid, started_at, agent_name, cycle_id, log_file
3. Add CycleResult model: id, project_id, status, started_at, ended_at, dispatches_planned/succeeded/failed, duration_seconds
4. Add SprintResult model: sprint_id, started_at, ended_at, points_planned, points_completed, tasks_completed, tasks_carried_over
5. Add enforcement types: Violation, Fix, CheckResult, SetupResult, EnforcementReport
6. Add enums: SessionType (daemon/cycle/discovery/manual), SessionStatus (running/completed/failed/paused), AgentName, CycleStatus
7. Use frozen dataclasses for immutable types, Pydantic for validated types

**Acceptance Criteria:**
- [ ] All models from RepEngine are ported with type annotations
- [ ] New models (Session, CycleResult, SprintResult) match Discovery specs
- [ ] Enums cover all valid states from RFC
- [ ] Serialization to/from JSON works for all models
- [ ] All tests pass

```

---

### Task ID: 004

- **Title**: Shared utilities -- subprocess and process management
- **File**: src/autopilot/utils/subprocess.py, src/autopilot/utils/process.py
- **Complete**: [ ]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a system operator, I want reliable subprocess and process management utilities, so that Claude CLI invocations and daemon processes are handled safely.
- **Outcome (what this delivers)**: Clean environment builder, Claude CLI helpers, PID file management, and daemon detection utilities.

#### Prompt:

```markdown
**Objective:** Consolidate and implement subprocess and process management utilities.

**File to Create/Modify:**
- `src/autopilot/utils/subprocess.py`
- `src/autopilot/utils/process.py`

**Specification References:**
- Discovery: Consolidation Opportunities 2 (_build_clean_env duplication)
- Discovery: Consolidation Opportunities 3 (_is_running duplication)
- RFC Section 3.3: Agent invocation subprocess management

**Prerequisite Requirements:**
1. Task 001 must be complete
2. Write tests first in `tests/utils/test_subprocess.py` and `tests/utils/test_process.py`

**Detailed Instructions:**
1. `subprocess.py`: Implement `build_clean_env()` that strips sensitive env vars (API keys, tokens), `run_claude_cli(prompt, model, max_turns, extra_flags, cwd, env)` helper, `run_with_timeout(cmd, timeout_seconds)` wrapper
2. `process.py`: Implement `PidFile` class with acquire/release/is_alive/force_recover, `is_running(pid)` check, `find_orphaned_processes(pattern)` for session recovery
3. Port the env sanitization logic from RepEngine agent.py and hive.py into the shared `build_clean_env()`

**Acceptance Criteria:**
- [ ] build_clean_env strips sensitive environment variables
- [ ] PidFile supports acquire, release, liveness check, and TTL-based recovery
- [ ] run_claude_cli properly invokes the claude CLI with all parameters
- [ ] All tests pass with mocked subprocess calls

```

---

### Task ID: 005

- **Title**: Shared utilities -- sanitizer, paths, git
- **File**: src/autopilot/utils/sanitizer.py, src/autopilot/utils/paths.py, src/autopilot/utils/git.py
- **Complete**: [ ]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a developer, I want shared path resolution, secret redaction, and git operation utilities, so that common operations are consistent and secure across the codebase.
- **Outcome (what this delivers)**: Secret sanitizer (regex-based), project/autopilot path resolver, and git operations helper (branch, fetch, status, clean check).

#### Prompt:

```markdown
**Objective:** Implement remaining shared utilities for path resolution, secret redaction, and git operations.

**File to Create/Modify:**
- `src/autopilot/utils/sanitizer.py`
- `src/autopilot/utils/paths.py`
- `src/autopilot/utils/git.py`

**Specification References:**
- Discovery: sanitizer.py (direct port, 32 lines)
- Discovery: Consolidation Opportunity 1 (_resolve_paths duplication)
- RFC Section 3.4.3: Directory layout per project
- RFC Section 3.8: Git state recovery (validate clean tree, correct branch)

**Prerequisite Requirements:**
1. Task 001 must be complete
2. Write tests in `tests/utils/test_sanitizer.py`, `tests/utils/test_paths.py`, `tests/utils/test_git.py`

**Detailed Instructions:**
1. `sanitizer.py`: Port RepEngine sanitizer -- regex patterns for API keys, tokens, passwords; `sanitize(text: str) -> str` function
2. `paths.py`: Implement `find_autopilot_dir(start: Path) -> Path | None` (walks up to find .autopilot/), `resolve_project_root(autopilot_dir: Path) -> Path`, `get_global_dir() -> Path` (returns ~/.autopilot/), `ensure_dir_structure(autopilot_dir: Path)` that creates standard subdirectories per RFC 3.4.3
3. `git.py`: Implement `is_clean() -> bool`, `current_branch() -> str`, `fetch_origin()`, `create_branch(name: str)`, `checkout(branch: str)`, `validate_git_state(expected_branch: str) -> list[str]` (returns list of issues)

**Acceptance Criteria:**
- [ ] Sanitizer redacts API keys, bearer tokens, and passwords
- [ ] Path resolver correctly finds .autopilot/ directories
- [ ] Git utilities handle clean/dirty state detection
- [ ] All tests pass

```

---

### Task ID: 006

- **Title**: SQLite schema and database management
- **File**: src/autopilot/utils/db.py
- **Complete**: [x]
- **Sprint Points**: 5

- **User Story (business-facing)**: As a system operator, I want reliable analytics storage, so that cycle history, velocity metrics, and enforcement data are queryable and persistent.
- **Outcome (what this delivers)**: SQLite database management with WAL mode, schema creation, connection pooling, and migration support at ~/.autopilot/autopilot.db.

#### Prompt:

```markdown
**Objective:** Implement SQLite database management with the full schema from RFC 3.4.2.

**File to Create/Modify:** `src/autopilot/utils/db.py`

**Specification References:**
- RFC Section 3.4.2: Complete SQLite schema (6 tables, 6 indices)
- Discovery: Hybrid Approach section (flat files for coordination, SQLite for analytics)
- Discovery: Risk Register -- SQLite concurrency (WAL mode, retry-with-backoff)

**Prerequisite Requirements:**
1. Task 001 must be complete
2. Write tests in `tests/utils/test_db.py`

**Detailed Instructions:**
1. Implement `Database` class with:
   - `__init__(db_path: Path)` that creates the database with WAL mode enabled
   - `initialize_schema()` that creates all 6 tables and 6 indices from RFC 3.4.2
   - `get_connection() -> sqlite3.Connection` with WAL mode and foreign keys enabled
   - Retry-with-backoff wrapper for write operations (handles SQLITE_BUSY)
2. Create all tables: projects, sessions, cycles, dispatches, enforcement_metrics, velocity
3. Create all indices from RFC 3.4.2
4. Add schema version tracking (for future migrations)
5. Add convenience methods: `insert_project()`, `insert_session()`, `insert_cycle()`, `insert_dispatch()`, `insert_enforcement_metric()`, `insert_velocity()`
6. Default database path: `~/.autopilot/autopilot.db`

**Acceptance Criteria:**
- [ ] Database creates with WAL mode enabled
- [ ] All 6 tables match RFC 3.4.2 schema exactly
- [ ] All 6 indices are created
- [ ] Foreign key constraints are enforced
- [ ] Retry-with-backoff handles concurrent write contention
- [ ] Schema version is tracked for migrations
- [ ] All tests pass

```

---

### Task ID: 007

- **Title**: Python project template with Jinja2
- **File**: templates/python/
- **Complete**: [x]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a technical architect, I want project scaffolding templates, so that `autopilot init` generates a complete .autopilot/ directory with sensible defaults for Python projects.
- **Outcome (what this delivers)**: Jinja2 templates for config.yaml, agent prompt files (PL, EM, TA, PD), board files, and enforcement configs for Python projects.

#### Prompt:

```markdown
**Objective:** Create the Python project template for autopilot init scaffolding.

**File to Create/Modify:**
- `templates/python/config.yaml.j2`
- `templates/python/agents/project-leader.md`
- `templates/python/agents/engineering-manager.md`
- `templates/python/agents/technical-architect.md`
- `templates/python/agents/product-director.md`
- `templates/python/board/project-board.md`
- `templates/python/board/question-queue.md`
- `templates/python/board/decision-log.md`
- `templates/python/board/announcements.md`

**Specification References:**
- RFC Section 3.4.3: Directory layout per project
- RFC Section 3.4.1: Default config values for all fields
- Discovery: Project Management section (.autopilot/ directory contents)
- Discovery: Quality gates for Python (uv run ruff, pyright, pytest)

**Prerequisite Requirements:**
1. Task 001 must be complete
2. Review existing RepEngine agent prompts for reference patterns

**Detailed Instructions:**
1. Create `config.yaml.j2` with Jinja2 variables for project name, type, root path. Include all config sections from RFC 3.4.1 with Python-specific quality gates
2. Create agent prompt templates based on RepEngine patterns but generalized for any Python project. Each prompt should include: role description, available tools, project context injection points, quality gate instructions placeholder
3. Create initial board files with standard headers and empty content sections
4. Ensure all templates use the directory structure from RFC 3.4.3

**Acceptance Criteria:**
- [ ] config.yaml.j2 renders valid YAML with all RFC 3.4.1 sections
- [ ] All 4 agent prompt templates are complete and project-agnostic
- [ ] Board files have correct structure for document-mediated coordination
- [ ] Templates render correctly with Jinja2 given project name and type
- [ ] Quality gates default to Python toolchain (ruff, pyright, pytest)

```

---

### Task ID: 008

- **Title**: Typer CLI application skeleton
- **File**: src/autopilot/cli/app.py
- **Complete**: [ ]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a user, I want a well-organized CLI with subcommand groups and auto-generated help, so that I can discover and use all autopilot capabilities from the terminal.
- **Outcome (what this delivers)**: Top-level Typer application with registered subcommand groups (project, task, session, enforce, agent, config) and the REPL entry point.

#### Prompt:

```markdown
**Objective:** Create the top-level Typer CLI application with command group registration.

**File to Create/Modify:** `src/autopilot/cli/app.py`

**Specification References:**
- RFC Appendix B: Full command reference (all top-level commands and subcommands)
- UX Design Section 2: Information Architecture (command taxonomy)
- Discovery: CLI layer description

**Prerequisite Requirements:**
1. Task 001 must be complete
2. Write tests in `tests/cli/test_app.py`
3. Use context7 for Typer best practices

**Detailed Instructions:**
1. Create main Typer app with callback that enters REPL when no command is provided
2. Register subcommand groups as Typer sub-applications: project, task, session, plan, enforce, agent, config, report
3. Add top-level commands: init, watch, ask, review, migrate
4. Add `--version` flag
5. Implement stub commands that print "Not yet implemented" for Phase 2+ features
6. Configure Rich as the default console for all Typer output

**Acceptance Criteria:**
- [ ] `autopilot --help` shows all command groups
- [ ] `autopilot --version` prints the version
- [ ] `autopilot` with no arguments attempts to enter REPL
- [ ] All subcommand groups are registered and show help
- [ ] All tests pass

```

---

### Task ID: 009

- **Title**: Rich display helpers
- **File**: src/autopilot/cli/display.py
- **Complete**: [ ]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a user, I want beautiful, consistent terminal output, so that project status, task boards, and reports are easy to read and visually organized.
- **Outcome (what this delivers)**: Reusable Rich formatting utilities for tables, panels, progress bars, status indicators, and the 80x24 dashboard layout.

#### Prompt:

```markdown
**Objective:** Implement Rich display helpers for consistent CLI output formatting.

**File to Create/Modify:** `src/autopilot/cli/display.py`

**Specification References:**
- UX Design Section 4: Dashboard Design (80x24, two-column layout)
- UX Design Section 9: Visual Language (color scheme, typography, status indicators)
- UX Design Section 7: Progressive Disclosure levels
- Discovery: Rich formatting replacement for print statements

**Prerequisite Requirements:**
1. Task 001 must be complete
2. Write tests in `tests/cli/test_display.py`
3. Use context7 for Rich library patterns

**Detailed Instructions:**
1. Create `Console` singleton with configured theme matching UX Design Section 9
2. Implement helper functions:
   - `project_table(projects: list) -> Table` for project listing
   - `task_board(tasks: list, filter: str) -> Table` for task board display
   - `status_panel(title: str, content: str, status: str) -> Panel` for status displays
   - `progress_bar(description: str, total: int) -> Progress` for long operations
   - `format_sprint_points(points: int) -> str` with color coding
   - `format_status(status: str) -> str` with status-appropriate colors
   - `notification(level: str, message: str)` for user notifications
3. Define color constants per UX Design Section 9 (green=success, yellow=warning, red=error, blue=info)
4. Ensure all output fits within 80-column default width

**Acceptance Criteria:**
- [ ] All display helpers produce valid Rich renderables
- [ ] Output respects 80-column width constraint
- [ ] Status colors follow UX Design Section 9 visual language
- [ ] Display helpers handle empty data gracefully
- [ ] All tests pass

```

---

### Task ID: 010

- **Title**: Project initialization command and core logic
- **File**: src/autopilot/core/project.py, src/autopilot/cli/project.py
- **Complete**: [ ]
- **Sprint Points**: 5

- **User Story (business-facing)**: As a technical architect, I want to initialize a project with `autopilot init`, so that I get a working .autopilot/ directory with config, agent prompts, and board files ready for autonomous development.
- **Outcome (what this delivers)**: The `autopilot init` command that scaffolds .autopilot/ from templates, registers the project globally, and provides clear next-steps guidance.

#### Prompt:

```markdown
**Objective:** Implement project initialization with template rendering and global registration.

**File to Create/Modify:**
- `src/autopilot/core/project.py`
- `src/autopilot/cli/project.py`

**Specification References:**
- RFC Section 3.4.3: Directory layout per project
- RFC ADR-2: .autopilot/ inside project root
- RFC ADR-3: ~/.autopilot/ for global state
- Discovery: Project Management section (autopilot init output)
- UX Design Section 5.1: Init Wizard flow

**Prerequisite Requirements:**
1. Tasks 001, 002, 006, 007 must be complete (package, config, db, templates)
2. Write tests in `tests/core/test_project.py` and `tests/cli/test_project.py`

**Detailed Instructions:**
1. `core/project.py`:
   - `initialize_project(name, project_type, root_path, template_overrides) -> ProjectInitResult`
   - Renders Jinja2 templates from templates/{type}/ to {root}/.autopilot/
   - Creates state/ and logs/ directories (gitignored)
   - Registers project in ~/.autopilot/projects.yaml
   - Registers project in SQLite database
   - Returns ProjectInitResult with list of created files and next steps
2. `cli/project.py`:
   - `init` command with --type (python/typescript/hybrid), --name, --root options
   - Interactive prompts when options are missing (UX Design Section 5.1)
   - Rich output showing created files and next steps
   - `project list` command (stub for Task 011)

**Acceptance Criteria:**
- [ ] `autopilot init --type python --name test` creates valid .autopilot/ directory
- [ ] All template files rendered with correct project name
- [ ] Project registered in ~/.autopilot/projects.yaml and SQLite
- [ ] state/ and logs/ directories are created with .gitignore entries
- [ ] Rich output shows created files and next steps
- [ ] All tests pass
```
