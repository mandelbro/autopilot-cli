# Autopilot CLI: Technical Discovery Document

**Date**: 2026-03-06
**Author**: Norwood (Technical Discovery Agent)
**Status**: Discovery Complete
**Effort Estimate**: 16-25 sprints (Fibonacci), ~215-368 story points

---

## The One-Liner

A standalone CLI tool that evolves the RepEngine autopilot from a project-specific daemon into a general-purpose autonomous development orchestrator -- think `claude-flow` meets `pm2` meets a really opinionated tech lead.

## The Problem

The RepEngine autopilot (`autopilot/`) works. It has survived hundreds of cycles, coordinated four agent roles (PL, EM, TA, PD) across four concurrent project checkouts, and produced real PRs that shipped. But it is welded to RepEngine. The scheduler, config, agent prompts, dispatch system, and board coordination are all hardcoded to one monorepo's conventions. Every new project that wants autonomous development needs to fork the entire `autopilot/` directory, adapt the config, rewrite the agent prompts, and hope nothing breaks.

Specific pain points:

1. **No project initialization story.** You cannot `autopilot init` in a new repo and get a working setup. Everything is manual: create `board/`, create `agents/`, write config.yaml, wire up justfile targets.

2. **No interactive mode.** The CLI is fire-and-forget: `plan`, `execute`, `status`. There is no REPL for exploring project state, managing sessions, or interactively dispatching agents. The human workflow is "edit YAML, run command, read log files."

3. **No discovery/task workflow integration.** Planning new work means opening a separate Claude Code session with the Norwood agent prompt, then manually creating task files following the tasks-workflow spec. Nothing connects discovery output to task creation to sprint planning to autonomous execution.

4. **Anti-pattern enforcement is config-level only.** The research identifies 11 enforcement categories and 5 enforcement layers, but the autopilot only implements one: the quality gate suffix appended to hive-mind objectives. There is no pre-commit hook management, no CI template generation, no real-time agent guardrails, no metrics collection.

5. **No cross-project orchestration intelligence.** The PL sees all projects, but there is no velocity tracking, no sprint planning, no capacity modeling. The PL just reads task indexes and dispatches work based on priority ordering.

6. **No deployment health monitoring.** There is zero automated monitoring between "PR merged" and "PD verifies on staging." On 2026-03-06, commit `e829056e` triggered two Render deployment failures that went completely undetected until a human manually checked the dashboard: one from an expired Git auth token (`build_failed`), another from broken imports (`update_failed` with `ModuleNotFoundError`). The PD and QA agents only check health endpoints when dispatched for feature verification -- they do not proactively monitor deploy outcomes. This means silent deployment failures accumulate, the PD agent wastes cycles trying to verify features that never deployed, and infrastructure issues have no automated detection path.

## The Solution

A Python CLI package called `autopilot-cli` (installed as `autopilot`) that provides:

- An **interactive REPL** for project management, session monitoring, and ad-hoc agent dispatch
- A **project scaffold** (`autopilot init`) that generates config, board, agent prompts, and enforcement infrastructure for any codebase
- **Discovery workflow integration** that spawns Norwood sessions and converts findings into structured task files
- **Task management** with Fibonacci estimation, sprint planning, and velocity tracking
- **Autonomous execution** via the proven scheduler/daemon architecture, generalized for any project
- **Layered anti-pattern enforcement** baked into every stage of the autonomous pipeline
- **Deployment health monitoring** via a DevOps Agent (DA) that checks Render deploy status, curls health endpoints, correlates failures with recent commits, and escalates issues
- **Pluggable agent roles** beyond the core five (PL, EM, TA, PD, DA)

---

## Current State Analysis

### What Exists (The Crime Scene)

The RepEngine autopilot at `/Users/montes/AI/RepEngine/rep-engine-service/autopilot/` is a well-tested Python package (954 lines of production code across 11 modules, 15 test files) with the following architecture:

| Module | Lines | Responsibility |
|--------|-------|----------------|
| `scheduler.py` | 691 | Cycle orchestration, dispatch execution, circuit breaker, locking |
| `cli.py` | 367 | Action commands (start/stop/pause/cycle/plan/execute) |
| `cli_display.py` | 285 | Read-only display commands (status/usage/history/questions/log) |
| `hive.py` | 353 | Hive-mind lifecycle: branch creation, init, spawn, record, shutdown |
| `agent.py` | 292 | Claude CLI subprocess invocation with retry, env sanitization |
| `config.py` | 158 | Pydantic config model with multi-project support |
| `models.py` | 108 | Shared data models (Dispatch, DispatchPlan, UsageState, AgentResult) |
| `usage.py` | 114 | Daily/weekly cycle-count tracking for Claude Max plan |
| `dispatch.py` | 133 | JSON extraction and validation from PL agent output |
| `reports.py` | 250 | Cycle reports, daily summary, decision log rotation |
| `sanitizer.py` | 32 | Regex-based secret redaction |
| `daemon.py` | 167 | Signal handling, PID file, interruptible sleep loop, log rotation |

**Dependencies** (from pyproject.toml): pydantic >= 2.10, pyyaml >= 6.0, structlog >= 24.0. Dev: pytest, pyright, ruff, freezegun.

**Key Observations:**

1. The codebase is clean. Pyright strict mode, ruff with a broad ruleset, 100% test file coverage per module. This is production-quality code that was successfully rewritten from 954 lines of bash.

2. The multi-project support is already abstracted. `config.resolved_projects()` returns `ProjectEntry` objects with name, task_dir, project_root, priority. The PL receives a formatted context block with absolute paths per project.

3. The hive-mind integration works but is tightly coupled. `hive.py` calls `npx claude-flow@alpha` directly with hardcoded init/spawn/shutdown sequences. The `_QUALITY_GATE_SUFFIX` is hardcoded to Python tooling (`uv run ruff`, `uv run pyright`, `uv run pytest`).

4. Agent prompts are markdown files in `agents/`. The system dynamically loads `agents/{agent-name}.md` at invocation time. This is already a plugin point -- drop a new `.md` file and add the agent name to `VALID_AGENTS`.

5. The dispatch parsing is surprisingly robust. It handles code-fenced JSON, raw JSON, field name normalization (the PL drifts from the contract), prompt synthesis from "reason" fields, and project_root resolution from config.

### Existing Components and Reuse Plan

**Will Reuse (directly or as fork-and-evolve):**

| Component | How | Why |
|-----------|-----|-----|
| `config.py` | Evolve | Pydantic config model is solid; extend for new features |
| `models.py` | Evolve | Core models (Dispatch, DispatchPlan, AgentResult) are general-purpose |
| `agent.py` | Evolve | Claude CLI invocation, env sanitization, retry logic are battle-tested |
| `dispatch.py` | Reuse as-is | JSON extraction/validation is agent-output-agnostic |
| `sanitizer.py` | Reuse as-is | Secret redaction is universal |
| `daemon.py` | Evolve | Signal handling, PID file, interruptible sleep are correct patterns |
| `scheduler.py` | Evolve | Cycle lock, circuit breaker, dispatch execution are reusable patterns |
| `usage.py` | Evolve | Usage tracking model works; extend with velocity metrics |
| `reports.py` | Evolve | Report generation patterns are reusable; parameterize for different projects |
| `hive.py` | Evolve | Core lifecycle is correct; remove hardcoded quality gates |

**Will Not Reuse:**

| Component | Why |
|-----------|-----|
| `cli.py` (argparse) | Replace with `typer` for REPL support and richer UX |
| `cli_display.py` (print statements) | Replace with `rich` for tables, panels, progress bars |
| Agent prompt files | These are RepEngine-specific; new tool needs a template system |
| Board file format | Keep the concept; make the format configurable per project |
| Hardcoded `VALID_AGENTS` frozenset | Replace with dynamic agent registry from config |
| `_QUALITY_GATE_SUFFIX` | Replace with configurable quality gate per project type |

**Consolidation Opportunities:**

1. `_resolve_paths()` is duplicated between `cli.py` and `cli_display.py` -- consolidate into a shared utility.
2. `_build_clean_env()` is duplicated between `agent.py` and `hive.py` -- consolidate into a shared subprocess utility.
3. `_is_running()` is duplicated between `cli.py` and `cli_display.py` -- consolidate into process management utility.

---

## System Architecture

### Language Choice: Python

This is not a close call.

**Why Python, not TypeScript:**

1. **The existing codebase is Python.** 954 lines of tested, typed, production Python. Rewriting in TypeScript means throwing away battle-tested code for zero benefit.

2. **The runtime is Python.** The autopilot spawns `claude` CLI subprocesses, manages PID files, sends POSIX signals, rotates file descriptors for log rotation. Python's `subprocess`, `os`, and `signal` modules handle all of this natively. Node.js can do it, but the ergonomics are worse and the edge cases (PGID management, fd duplication) are more painful.

3. **The ecosystem is Python.** Pydantic for config/models, structlog for logging, ruff/pyright for quality, pytest for testing. All already configured and working.

4. **claude-flow is called via subprocess anyway.** The integration with claude-flow (`npx claude-flow@alpha ...`) is subprocess-based regardless of language. There is no library-level integration to leverage from TypeScript.

**Why Typer + Rich, not Click + manual formatting:**

The existing CLI uses `argparse` with `print()` statements. For a tool that aspires to be a daily-driver REPL, this is insufficient. Typer (built on Click) gives us:
- Automatic `--help` generation from type hints
- Subcommand groups (project, task, session, agent)
- Shell completion out of the box
- Easy REPL integration via `prompt_toolkit`

Rich gives us:
- Tables with proper alignment and color
- Progress bars for long-running operations
- Panels for status displays
- Markdown rendering in the terminal
- Tree views for project/task hierarchy

### Package Structure

```
autopilot-cli/
├── pyproject.toml
├── src/
│   └── autopilot/
│       ├── __init__.py
│       ├── __main__.py                # python -m autopilot
│       │
│       ├── cli/                       # Command layer
│       │   ├── __init__.py
│       │   ├── app.py                 # Typer app, top-level commands
│       │   ├── project.py             # project init/list/status/config
│       │   ├── task.py                # task create/list/estimate/assign/sprint
│       │   ├── session.py             # session list/start/stop/attach/logs
│       │   ├── agent.py               # agent list/invoke/roles
│       │   ├── discover.py            # discover start/status (Norwood integration)
│       │   ├── enforce.py             # enforce setup/check/report
│       │   ├── repl.py                # Interactive REPL mode
│       │   └── display.py             # Rich formatting helpers
│       │
│       ├── core/                      # Domain logic
│       │   ├── __init__.py
│       │   ├── config.py              # Evolved from RepEngine config.py
│       │   ├── models.py              # Evolved from RepEngine models.py
│       │   ├── project.py             # Project lifecycle (init, discover, validate)
│       │   ├── task.py                # Task CRUD, sprint planning, velocity
│       │   ├── agent_registry.py      # Dynamic agent role management
│       │   └── templates.py           # Project type templates (Python, TS, hybrid)
│       │
│       ├── orchestration/             # Execution engine
│       │   ├── __init__.py
│       │   ├── scheduler.py           # Evolved from RepEngine scheduler.py
│       │   ├── daemon.py              # Evolved from RepEngine daemon.py
│       │   ├── dispatcher.py          # Evolved from RepEngine dispatch.py
│       │   ├── agent_invoker.py       # Evolved from RepEngine agent.py
│       │   ├── hive.py                # Evolved from RepEngine hive.py
│       │   ├── circuit_breaker.py     # Extracted from scheduler for reuse
│       │   └── usage.py               # Evolved from RepEngine usage.py
│       │
│       ├── enforcement/               # Anti-pattern enforcement engine
│       │   ├── __init__.py
│       │   ├── engine.py              # Enforcement orchestration
│       │   ├── precommit.py           # Pre-commit hook generation/management
│       │   ├── ci.py                  # CI/CD pipeline template generation
│       │   ├── guardrails.py          # Real-time agent guardrails
│       │   ├── quality_gates.py       # Quality gate definitions per project type
│       │   ├── metrics.py             # Enforcement metrics collection
│       │   └── rules/                 # Rule definitions per category
│       │       ├── __init__.py
│       │       ├── infrastructure.py  # Category 1: Infrastructure duplication
│       │       ├── conventions.py     # Category 2: Ignored conventions
│       │       ├── complexity.py      # Category 3: Over-engineering
│       │       ├── security.py        # Category 4: Security vulnerabilities
│       │       └── ...                # Categories 5-11
│       │
│       ├── reporting/                 # Evolved from RepEngine reports.py
│       │   ├── __init__.py
│       │   ├── cycle_reports.py       # Per-cycle markdown reports
│       │   ├── daily_summary.py       # Aggregated daily view
│       │   ├── velocity.py            # Sprint velocity tracking and forecasting
│       │   ├── quality.py             # Enforcement trend analysis
│       │   └── decision_log.py        # Decision audit trail with rotation
│       │
│       ├── monitoring/                # Deployment health monitoring
│       │   ├── __init__.py
│       │   ├── render_registry.py     # Render service registry from config
│       │   ├── health_checker.py      # HTTP health endpoint checks
│       │   ├── deploy_status.py       # Deploy status board section writer
│       │   └── failure_patterns.py    # Known failure classification + remediation routing
│       │
│       ├── coordination/              # Document-mediated agent coordination
│       │   ├── __init__.py
│       │   ├── board.py               # Project board management
│       │   ├── questions.py           # Question queue (agent → human)
│       │   ├── announcements.py       # Human → agent broadcasts
│       │   └── decisions.py           # Decision log with archival
│       │
│       └── utils/                     # Shared utilities
│           ├── __init__.py
│           ├── subprocess.py          # Clean env builder, Claude CLI helpers
│           ├── process.py             # PID file, daemon detection
│           ├── sanitizer.py           # From RepEngine sanitizer.py
│           ├── paths.py               # Project/autopilot path resolution
│           └── git.py                 # Git operations (branch, fetch, status)
│
├── templates/                         # Project scaffolding templates
│   ├── python/
│   │   ├── agents/                    # Default agent prompts for Python projects
│   │   ├── board/                     # Initial board files
│   │   ├── config.yaml.j2            # Jinja2 config template
│   │   ├── pyproject-additions.toml   # Ruff/pyright additions
│   │   └── pre-commit-config.yaml     # Pre-commit hook config
│   ├── typescript/
│   │   ├── agents/
│   │   ├── board/
│   │   ├── config.yaml.j2
│   │   ├── eslint-additions.json
│   │   └── pre-commit-config.yaml
│   └── hybrid/
│       └── ...
│
└── tests/
    ├── conftest.py
    ├── cli/
    ├── core/
    ├── orchestration/
    ├── enforcement/
    ├── monitoring/
    ├── reporting/
    ├── coordination/
    └── utils/
```

### Dependency Strategy

```toml
[project]
name = "autopilot-cli"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    # Existing (proven in RepEngine)
    "pydantic>=2.10",
    "pyyaml>=6.0",
    "structlog>=24.0",
    # New: CLI UX
    "typer>=0.15",
    "rich>=13.0",
    "prompt-toolkit>=3.0",    # REPL / interactive prompts
    # New: Templating
    "jinja2>=3.1",            # Config/prompt template rendering
]

[project.scripts]
autopilot = "autopilot.cli.app:app"

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "freezegun>=1.4",
    "ruff>=0.9",
    "pyright>=1.1",
]
```

No new heavy dependencies. Typer, Rich, and prompt-toolkit are the standard Python CLI stack in 2026. Jinja2 is the standard for template rendering and is already a transitive dependency of many tools.

---

## Core Components

### 1. REPL / Interactive Shell

The REPL is the primary human interface for the Autopilot CLI. It provides a persistent session where the technical architect can manage projects, monitor autonomous sessions, and dispatch work.

**Implementation approach:** Typer for command routing, prompt-toolkit for the REPL loop, Rich for output formatting.

```python
# Simplified REPL architecture
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter

class AutopilotREPL:
    def __init__(self, workspace: Workspace):
        self.workspace = workspace
        self.session = PromptSession()
        self.commands = {
            "projects": self.cmd_projects,
            "sessions": self.cmd_sessions,
            "tasks": self.cmd_tasks,
            "discover": self.cmd_discover,
            "dispatch": self.cmd_dispatch,
            "status": self.cmd_status,
            "enforce": self.cmd_enforce,
        }
        self.completer = WordCompleter(list(self.commands.keys()))

    async def run(self):
        while True:
            text = await self.session.prompt_async(
                "autopilot> ",
                completer=self.completer,
            )
            cmd, *args = text.strip().split()
            if cmd in self.commands:
                await self.commands[cmd](args)
```

**Key interactions:**

| Command | Action |
|---------|--------|
| `projects` | List projects with status, velocity, task counts |
| `sessions` | Show running autonomous sessions with live progress |
| `tasks <project>` | Interactive task board (pending/active/done) |
| `discover <project>` | Launch Norwood discovery session in nested Claude instance |
| `dispatch <project>` | Manually trigger a PL cycle for one project |
| `enforce check` | Run full enforcement suite across all projects |
| `sprint plan` | Interactive sprint planning with velocity-based capacity |
| `agent invoke <role> <prompt>` | Ad-hoc single agent dispatch |

### 2. Project Management

**`autopilot init`** scaffolds a new project for autonomous development:

```
$ autopilot init --type python --name my-service
Initializing autopilot for 'my-service' (Python project)...

Created:
  .autopilot/
    config.yaml          # Scheduler, usage limits, claude config
    agents/
      project-leader.md  # PL prompt (Python-flavored)
      engineering-manager.md
      technical-architect.md
      product-director.md
    board/
      project-board.md   # Initial project board
      question-queue.md  # Empty queue
      decision-log.md    # Empty log
    state/               # Runtime state (gitignored)

Updated:
  pyproject.toml         # Added ruff rules for anti-pattern enforcement
  .pre-commit-config.yaml # Added enforcement hooks

Next steps:
  1. Review .autopilot/config.yaml and adjust for your project
  2. Create tasks: autopilot task create
  3. Run discovery: autopilot discover
  4. Start autonomous execution: autopilot start
```

The `.autopilot/` directory lives inside the project root (not a sibling like the current RepEngine layout). This makes it portable, versionable, and discoverable.

**Project registry:** A global config at `~/.autopilot/projects.yaml` tracks all initialized projects:

```yaml
projects:
  - name: my-service
    path: /Users/montes/Projects/my-service
    type: python
    registered_at: 2026-03-06T10:00:00
  - name: frontend-app
    path: /Users/montes/Projects/frontend-app
    type: typescript
    registered_at: 2026-03-06T11:00:00
```

This enables `autopilot projects` to list all managed projects without being inside any specific one.

### 3. Discovery Workflow Integration (Norwood Agent)

Discovery launches a nested Claude Code session with the Norwood agent system prompt, scoped to the target project:

```python
def start_discovery(
    project: ProjectConfig,
    topic: str,
    output_dir: Path,
) -> subprocess.Popen:
    """Spawn a Norwood discovery session as a background Claude instance."""
    norwood_prompt = load_agent_prompt("norwood-discovery")
    prompt = (
        f"{norwood_prompt}\n\n"
        f"## Discovery Context\n\n"
        f"Project: {project.name}\n"
        f"Root: {project.project_root}\n"
        f"Output: {output_dir}\n\n"
        f"## Topic\n\n{topic}\n\n"
        f"Write the discovery document to {output_dir}/discovery.md"
    )

    return subprocess.Popen(
        ["claude", "--dangerously-skip-permissions", "-p", prompt],
        cwd=str(project.project_root),
        env=build_clean_env(),
    )
```

The REPL can then monitor the discovery session, and when complete, offer to convert findings into tasks:

```
autopilot> discover my-service "Add OAuth2 provider adapter framework"
Starting Norwood discovery session...
Session running (PID: 12345)

autopilot> sessions
  [1] discovery/my-service  RUNNING  12m elapsed  PID: 12345

# ... later ...

autopilot> sessions
  [1] discovery/my-service  COMPLETED  47m  Output: .autopilot/discoveries/oauth-adapter/

autopilot> tasks create --from-discovery .autopilot/discoveries/oauth-adapter/discovery.md
Parsing discovery document...
Found 8 implementation phases with 23 work items.

Generate task files? [Y/n]: y
Created:
  tasks/oauth-adapter/tasks-index.md  (23 tasks, 89 story points)
  tasks/oauth-adapter/tasks-1.md      (tasks 001-010)
  tasks/oauth-adapter/tasks-2.md      (tasks 011-020)
  tasks/oauth-adapter/tasks-3.md      (tasks 021-023)
```

### 4. Task Management

The task system generalizes the RepEngine task workflow pattern:

**Task file format** (preserved from RepEngine convention):

```markdown
### Task 001: Implement base OAuth adapter interface
- **ID**: OAUTH-001
- **Sprint Points**: 3
- **Priority**: P1
- **Dependencies**: None
- **Complete**: [ ]

**Description**: Create the abstract base class for OAuth provider adapters...

**Acceptance Criteria**:
- [ ] Base adapter class with abstract methods
- [ ] Type definitions for OAuth flow parameters
- [ ] Unit tests for adapter contract validation
```

**Sprint planning with velocity tracking:**

```python
class VelocityTracker:
    """Track sprint velocity for capacity planning."""

    def __init__(self, project_dir: Path):
        self.history_file = project_dir / ".autopilot" / "state" / "velocity.json"

    def record_sprint(self, sprint: SprintResult) -> None:
        """Record completed sprint for velocity calculation."""
        ...

    def forecast_capacity(self, team_size: int = 1) -> int:
        """Forecast next sprint capacity using rolling average."""
        history = self._load_history()
        if len(history) < 3:
            return 13  # Default: 13 points (conservative)
        # Rolling average of last 5 sprints
        recent = [s.points_completed for s in history[-5:]]
        return int(sum(recent) / len(recent))
```

**CLI commands:**

```
autopilot task create                  # Interactive task creation
autopilot task create --from-discovery # Convert discovery to tasks
autopilot task list [--project NAME]   # Show task board
autopilot task estimate TASK_ID        # Launch Shelly for estimation
autopilot task sprint plan             # Plan next sprint (velocity-based)
autopilot task sprint close            # Close sprint, record velocity
```

### 5. Autopilot Daemon (Scheduler)

The daemon architecture is directly evolved from the RepEngine implementation, with these generalizations:

**Key changes from RepEngine:**

1. **Configurable quality gates.** Instead of hardcoded `_QUALITY_GATE_SUFFIX`, quality gates are defined per project type in config:

```yaml
quality_gates:
  python:
    pre_commit: "uv run ruff check --fix . && uv run ruff format ."
    type_check: "uv run pyright"
    test: "uv run pytest tests/ -x -q"
    all: "just all"
  typescript:
    pre_commit: "pnpm lint --fix"
    type_check: "pnpm typecheck"
    test: "pnpm test"
    all: "pnpm ci"
```

2. **Dynamic agent registry.** Instead of `VALID_AGENTS` frozenset, agents are loaded from the project's `.autopilot/agents/` directory:

```python
class AgentRegistry:
    def __init__(self, autopilot_dir: Path):
        self.agents_dir = autopilot_dir / "agents"

    def list_agents(self) -> list[str]:
        """Return all available agent names from .md files."""
        return [
            f.stem for f in self.agents_dir.glob("*.md")
            if not f.name.startswith("_")
        ]

    def validate_agent(self, name: str) -> bool:
        return (self.agents_dir / f"{name}.md").exists()
```

3. **Multi-daemon support.** Each project runs its own daemon (separate PID file, separate log directory). The global registry tracks which projects have active daemons.

4. **Configurable scheduler strategy.** The interval-based approach works but is wasteful. Add event-driven triggers:

```yaml
scheduler:
  strategy: "interval"          # or "event" or "hybrid"
  interval_seconds: 1800        # For interval/hybrid
  triggers:                     # For event/hybrid
    - type: "file_change"
      paths: ["tasks/", "board/"]
    - type: "git_push"
      branches: ["main"]
    - type: "manual"            # Always available
```

### 6. Anti-Pattern Enforcement Engine

This is the biggest net-new component. The research identifies 11 categories and 5 enforcement layers; the engine operationalizes all of them.

**Architecture:**

```
EnforcementEngine
├── Layer 1: Editor-time (configuration generation)
│   ├── Generate ruff config additions for Python
│   ├── Generate eslint config additions for TypeScript
│   └── Generate pyright/tsconfig strictness settings
│
├── Layer 2: Pre-commit hooks (lefthook/husky management)
│   ├── Install hook runner (lefthook preferred)
│   ├── Generate hook config from project type
│   ├── Add block-no-verify for Claude Code
│   └── Add detect-secrets for security scanning
│
├── Layer 3: CI/CD pipeline (template generation)
│   ├── GitHub Actions workflow templates
│   ├── Quality gate job definitions
│   └── Coverage/complexity thresholds
│
├── Layer 4: Real-time agent guardrails
│   ├── PreToolUse hook integration (block dangerous ops)
│   ├── PostToolUse hook integration (inject warnings)
│   └── AgentLint rule pack configuration
│
└── Layer 5: Protected code regions
    ├── Hash-based protection markers
    ├── Change detection in protected regions
    └── PR-level alerts for protected code changes
```

**Implementation approach:**

```python
class EnforcementEngine:
    def __init__(self, project: ProjectConfig):
        self.project = project
        self.rules = self._load_rules()

    def setup(self) -> SetupResult:
        """Full enforcement setup for a project."""
        results = []
        results.append(self._setup_editor_config())
        results.append(self._setup_precommit_hooks())
        results.append(self._setup_ci_pipeline())
        results.append(self._setup_agent_guardrails())
        return SetupResult(steps=results)

    def check(self) -> CheckResult:
        """Run all enforcement checks and return report."""
        violations = []
        for rule in self.rules:
            violations.extend(rule.check(self.project.root))
        return CheckResult(violations=violations)

    def report(self) -> EnforcementReport:
        """Generate trend analysis from historical metrics."""
        metrics = self._load_metrics_history()
        return EnforcementReport(
            violation_density=metrics.violation_density_trend(),
            top_categories=metrics.top_violation_categories(),
            improvement_rate=metrics.week_over_week_improvement(),
        )
```

**Quality gate injection into hive-mind objectives:**

Instead of the hardcoded `_QUALITY_GATE_SUFFIX`, the enforcement engine generates project-specific quality gate instructions:

```python
def build_quality_gate_prompt(self) -> str:
    """Build quality gate instructions for agent prompts."""
    gates = self.project.quality_gates
    lines = [
        "\n\nBefore reporting completion, every worker MUST run the quality gate:",
    ]
    for i, (name, cmd) in enumerate(gates.items(), 1):
        lines.append(f"({i}) {name}: `{cmd}`")
    lines.append(
        "Stage and commit any auto-fix changes. "
        "Do NOT leave unstaged formatting changes."
    )
    return " ".join(lines)
```

### 7. Session Management

Sessions are the runtime containers for autonomous work. Each session maps to one or more Claude CLI instances working on a specific project.

```python
@dataclass
class Session:
    id: str
    project: str
    type: SessionType      # "daemon", "cycle", "discovery", "manual"
    status: SessionStatus  # "running", "completed", "failed", "paused"
    pid: int | None
    started_at: datetime
    agent_name: str | None # For single-agent sessions
    cycle_id: str | None   # For cycle sessions
    log_file: Path
```

**Session persistence:** Sessions are tracked in `~/.autopilot/sessions.json` (global) with per-project detail in `.autopilot/state/sessions.json`.

**Key operations:**

```
autopilot session list                # All sessions across all projects
autopilot session list --project X    # Sessions for project X
autopilot session attach SESSION_ID   # Tail logs from a running session
autopilot session stop SESSION_ID     # Graceful shutdown
autopilot session logs SESSION_ID     # View full session logs
```

### 8. Reporting and Metrics

The reporting system evolves the RepEngine cycle reports into a comprehensive analytics layer:

**Velocity metrics:**
- Points completed per sprint (rolling average)
- Points completed per cycle
- Agent success rate (by role)
- Average cycle duration
- Throughput: tasks completed per week

**Quality metrics (from enforcement engine):**
- Lint violation density (issues per 1K lines)
- Hook bypass attempts (should be zero)
- Infrastructure duplication incidents
- Security findings per PR
- Type coverage percentage
- Cognitive complexity distribution (P50/P90/P99)

**Operational metrics:**
- Cycle success/failure/partial rates
- Agent timeout frequency
- Circuit breaker activations
- Usage against Claude Max limits
- Hive-mind session success rate

```
autopilot report velocity             # Sprint velocity chart
autopilot report quality              # Enforcement trend analysis
autopilot report operational          # System health dashboard
autopilot report --export csv         # Export for external analysis
```

---

## Agent Orchestration Strategy

### claude-flow / Hive-Mind Integration

The current integration pattern works and should be preserved:

1. **Scheduler (Python)** owns the lifecycle. It creates branches, initializes claude-flow, spawns hive-mind sessions, records outcomes, and shuts down.
2. **Hive-mind (Node.js via npx)** owns the implementation. Workers coordinate through the hive's consensus mechanism.
3. **EM agent (Claude CLI)** owns verification. Post-hive, the EM reviews, runs quality gates, commits, and creates PRs.

**What changes:**

- The `npx claude-flow@alpha` invocation should be version-pinned in config, not hardcoded
- The quality gate suffix is generated by the enforcement engine, not hardcoded
- Session recording uses the new session management system, not a standalone JSON file
- Branch naming strategy is configurable (currently hardcoded to `feat/batch-{ids}-{hash}`)

### Agent Lifecycle Management

```
                    ┌─────────────┐
                    │  Scheduler  │
                    │  (Python)   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │     PL      │  Phase 1: Planning
                    │ (claude CLI)│  - Read project state + deploy status
                    └──────┬──────┘  - Generate dispatch plan (incl. DA)
                           │
         ┌─────────────────┼─────────────────┐
         │            │            │          │
   ┌─────▼─────┐ ┌───▼───┐ ┌─────▼─────┐ ┌──▼──┐
   │    EM     │ │  TA   │ │    PD     │ │ DA  │  Phase 2: Execution
   │(hive-mind)│ │(claude)│ │ (claude)  │ │(son)│  - Parallel dispatch
   └─────┬─────┘ └───┬───┘ └─────┬─────┘ └──┬──┘  - Circuit breaker
         │            │            │          │
         └────────────┼────────────┘          │
                      │                       │
                      │    ┌──────────────────┘
                      │    │  DA writes deploy status to board
                      │    │  PL reads it next cycle to gate PD dispatch
                      ▼    ▼
                    ┌─────────────┐
                    │  Reporting  │  Phase 3: Bookkeeping
                    │  (Python)   │  - Cycle reports
                    └─────────────┘  - Metrics update
```

### Inter-Agent Communication

The document-mediated approach is the right one. Direct MCP-based inter-agent communication adds complexity without proportional benefit for the asynchronous, cycle-based workflow.

**Communication channels:**

| Channel | Direction | Medium | Purpose |
|---------|-----------|--------|---------|
| Project Board | PL ↔ All | Markdown file | Sprint status, active work, blockers |
| Deployment Status | DA → Board | Markdown section | Service deploy status table (read by PL to gate PD dispatch) |
| Question Queue | Agent → Human | Markdown file | Decisions requiring human input (DA posts infra escalations) |
| Decision Log | PL → All | Markdown file | Recorded decisions with rationale |
| Announcements | Human → All | Markdown file | Policy changes, priority shifts |
| Daily Summary | Scheduler → PL | Markdown file | Cycle history for PL context |
| Dispatch Plan | PL → Scheduler | JSON file | Structured agent instructions |
| GitHub Issues | DA → GitHub | GitHub API | Deploy failure diagnostics with full context |

This pattern scales because agents read fresh state at the start of each invocation. There is no stale cache, no message queue to maintain, no coordination protocol to debug.

### Error Recovery and Retry

The existing patterns are solid and should be preserved:

1. **Transient API errors:** Exponential backoff with configurable retry count (currently 2 retries, 45s/90s backoff)
2. **Agent timeouts:** Circuit breaker pattern -- abort remaining dispatches after N consecutive timeouts
3. **Model fallback:** PL and TA have fallback model chains (opus 4.6 → opus 4.5 → sonnet)
4. **Empty output detection:** Guard against Claude CLI short-circuiting (exit 0, no output, < 8 seconds)
5. **Stale lock recovery:** Cycle lock checks PID liveness and TTL before force-recovering

**New recovery mechanisms for Autopilot CLI:**

6. **Session recovery:** On daemon restart, detect orphaned Claude processes and clean them up
7. **Partial dispatch recovery:** If a cycle fails mid-dispatch, allow resuming from the last successful dispatch
8. **Git state recovery:** Before each cycle, validate that the working tree is clean and on the expected branch
9. **Deploy failure correlation:** DA correlates failed deploys with recent commits/PRs via `gh` and `git log`, classifies failure type (git auth, broken imports, missing deps, crash loop), and routes to appropriate remediation (EM dispatch for code issues, human escalation for infrastructure issues)

### Resource Management

**Token budgets:** The Claude Max plan uses weekly usage caps, not per-token billing. The existing cycle-count tracking model is the right abstraction. Extend with:

```yaml
usage_limits:
  daily_cycle_limit: 200
  weekly_cycle_limit: 1400
  max_agent_invocations_per_cycle: 40
  # New: per-project limits
  per_project:
    my-service:
      daily_cycle_limit: 100
      priority_weight: 2        # Gets 2x share in round-robin
    frontend-app:
      daily_cycle_limit: 50
      priority_weight: 1
```

**Concurrency limits:** One daemon per project, one cycle at a time per project (via cycle lock). Cross-project parallelism is controlled at the global level:

```yaml
global:
  max_concurrent_daemons: 3    # How many projects can run simultaneously
  max_concurrent_agents: 6     # Total Claude instances across all projects
```

---

## Data Architecture

### Hybrid Approach: Flat Files + SQLite

The RepEngine autopilot uses flat files exclusively (JSON for state, Markdown for reports/boards). This works for single-project operation but breaks down at scale.

**Decision: Flat files for human-readable coordination, SQLite for analytics.**

**Flat files (preserved):**
- Board files (project-board.md, question-queue.md, decision-log.md)
- Agent prompts (*.md in agents/)
- Cycle reports (markdown in cycle-reports/)
- Config (YAML)
- Task files (markdown in tasks/)

These must remain human-readable and git-versionable. Agents read and write them directly.

**SQLite (new, for analytics and session tracking):**

```sql
-- ~/.autopilot/autopilot.db

CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    type TEXT NOT NULL,        -- python, typescript, hybrid
    created_at TEXT NOT NULL,
    config_hash TEXT            -- detect config drift
);

CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    project_id TEXT REFERENCES projects(id),
    type TEXT NOT NULL,         -- daemon, cycle, discovery, manual
    status TEXT NOT NULL,       -- running, completed, failed, paused
    pid INTEGER,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    agent_name TEXT,
    cycle_id TEXT,
    metadata TEXT               -- JSON blob for session-specific data
);

CREATE TABLE cycles (
    id TEXT PRIMARY KEY,
    project_id TEXT REFERENCES projects(id),
    session_id TEXT REFERENCES sessions(id),
    status TEXT NOT NULL,       -- COMPLETED, PARTIAL, FAILED
    started_at TEXT NOT NULL,
    ended_at TEXT,
    dispatches_planned INTEGER,
    dispatches_succeeded INTEGER,
    dispatches_failed INTEGER,
    duration_seconds REAL
);

CREATE TABLE dispatches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_id TEXT REFERENCES cycles(id),
    agent TEXT NOT NULL,
    action TEXT,
    project_name TEXT,
    task_id TEXT,
    status TEXT NOT NULL,       -- success, failed, timeout
    duration_seconds REAL,
    exit_code INTEGER,
    error TEXT
);

CREATE TABLE enforcement_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT REFERENCES projects(id),
    collected_at TEXT NOT NULL,
    category TEXT NOT NULL,     -- One of the 11 anti-pattern categories
    violation_count INTEGER,
    files_scanned INTEGER,
    metadata TEXT               -- JSON: specific rule violations
);

CREATE TABLE velocity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT REFERENCES projects(id),
    sprint_id TEXT NOT NULL,
    started_at TEXT,
    ended_at TEXT,
    points_planned INTEGER,
    points_completed INTEGER,
    tasks_completed INTEGER,
    tasks_carried_over INTEGER
);
```

**Why SQLite and not just more JSON files:**

1. **Querying.** "Show me the timeout rate for the EM agent across all projects over the last 30 days" is trivial in SQL, painful with JSON files.
2. **Aggregation.** Velocity forecasting, trend analysis, and enforcement metrics all require time-series aggregation.
3. **Concurrency.** SQLite handles concurrent readers safely. Multiple daemon processes can write to the same database.
4. **Size.** After 1000 cycles with 4 dispatches each, the dispatches table has ~4000 rows. That is nothing for SQLite. The equivalent flat-file approach would be 4000 JSON files or one unwieldy mega-file.

**Migration path from RepEngine:** The `usage-tracker.json`, `hive-sessions.json`, and `daily-stats.json` state files are migrated into SQLite tables. Cycle reports remain as markdown files (human-readable, git-versionable).

### Configuration Format: YAML

Stay with YAML. The existing config is YAML, the Pydantic model for it is solid, and YAML supports comments (TOML does too, JSON does not). The only change is adding Jinja2 template support for the scaffolding flow.

```yaml
# .autopilot/config.yaml

# Project metadata
project:
  name: "my-service"
  type: "python"
  root: "."                    # Relative to .autopilot parent

# Scheduler configuration
scheduler:
  strategy: "interval"
  interval_seconds: 1800
  cycle_timeout_seconds: 7200
  agent_timeout_seconds: 900
  agent_timeouts:
    project_leader: 1800
    engineering_manager: 3600
    devops_agent: 900
  consecutive_timeout_limit: 2

# Usage limits
usage_limits:
  daily_cycle_limit: 200
  weekly_cycle_limit: 1400
  max_agent_invocations_per_cycle: 40

# Agent configuration
agents:
  roles:
    - project-leader
    - engineering-manager
    - technical-architect
    - product-director
    - devops-agent
  models:
    project_leader: "opus"
    engineering_manager: "opus"
    devops_agent: "sonnet"
  max_turns:
    project_leader: 30
    engineering_manager: 200
    devops_agent: 30
  fallback_models:
    project_leader: ["claude-opus-4-5-20250514", "sonnet"]

# Quality gates (per project type)
quality_gates:
  pre_commit: "uv run ruff check --fix . && uv run ruff format ."
  type_check: "uv run pyright"
  test: "uv run pytest tests/ -x -q"
  all: "just all"

# Enforcement
enforcement:
  enabled: true
  categories:
    - infrastructure_duplication
    - ignored_conventions
    - over_engineering
    - security_vulnerabilities
    - error_handling
    - dead_code
    - type_safety
    - test_anti_patterns
    - excessive_comments
    - deprecated_apis
    - async_misuse

# Safety (documented intent, enforced by prompts + branch protection)
safety:
  auto_merge: true
  require_ci_pass: true
  require_review_approval: true
  max_files_per_commit: 100
  require_tests: true

# Claude CLI
claude:
  extra_flags: "--dangerously-skip-permissions"
  mcp_config: ".mcp.json"
  claude_flow_version: "alpha"    # Pin claude-flow version

# Git
git:
  base_branch: "main"
  branch_prefix: "feat/"
  branch_strategy: "batch"       # batch (current) or per-task

# Render services (for DevOps Agent monitoring)
render_services:
  api_service:
    id: "srv-xxxxx"
    name: "my-service-api-staging"
    health_endpoints: ["/health", "/ready"]
    staging_url: "https://stg-api.example.com"
  app_ui:
    id: "srv-yyyyy"
    name: "my-service-app-staging"
    health_endpoints: ["/"]
    staging_url: "https://stg-app.example.com"

# Deployment monitoring
deployment_monitoring:
  enabled: true
  check_frequency: "every_cycle"   # every_cycle, every_nth_cycle, manual_only
  health_check_timeout_seconds: 10
  failure_patterns:                 # Known failure → remediation mapping
    git_auth_expired: "human_escalation"
    broken_imports: "em_dispatch"
    missing_dependency: "em_dispatch"
    crash_loop: "em_dispatch"
  github_issues:
    create_on_failure: true
    labels: ["deploy-failure", "autopilot"]

# Paths (relative to .autopilot/)
paths:
  board: "board"
  agents: "agents"
  state: "state"
  logs: "logs"
  discoveries: "discoveries"
  cycle_reports: "board/cycle-reports"
```

---

## Extension Points

### Custom Agent Roles

Any markdown file in `.autopilot/agents/` becomes an available agent role:

```
.autopilot/agents/
  project-leader.md        # Core role (from template)
  engineering-manager.md   # Core role
  technical-architect.md   # Core role
  product-director.md      # Core role
  devops-agent.md          # Core role (deployment health monitoring)
  security-reviewer.md     # Custom role
  performance-tester.md    # Custom role
  documentation-writer.md  # Custom role
```

The only requirement is that the PL's system prompt knows about available agents. The `autopilot agent list` command shows what is available, and the PL prompt is dynamically assembled with the current agent roster.

### Custom Enforcement Rules

Rules are Python classes following a simple protocol:

```python
class EnforcementRule(Protocol):
    category: str           # One of the 11 categories
    severity: str           # "error" | "warning" | "info"
    name: str

    def check(self, project_root: Path) -> list[Violation]: ...
    def fix(self, project_root: Path) -> list[Fix]: ...  # Optional auto-fix
```

Custom rules are loaded from `.autopilot/enforcement/rules/` using Python's import machinery. This allows project-specific rules (e.g., "never use httpx directly, use our BaseHTTPClient") without modifying the core tool.

### Project Type Templates

Templates live in the package's `templates/` directory and can be overridden by user-level templates at `~/.autopilot/templates/`:

```
~/.autopilot/templates/
  my-company-python/
    agents/
      project-leader.md    # Company-specific PL prompt
    config.yaml.j2         # Company-specific defaults
    enforcement/
      rules/
        internal_api_usage.py  # Custom rule
```

Register custom templates:

```yaml
# ~/.autopilot/config.yaml
templates:
  my-company-python:
    extends: "python"
    path: "~/.autopilot/templates/my-company-python"
```

### Workflow Customization

The cycle workflow (plan → dispatch → execute → report) can be customized with hooks:

```yaml
# .autopilot/config.yaml
hooks:
  pre_cycle:
    - "git fetch origin main"
    - "autopilot enforce check --quiet"
  post_cycle:
    - "autopilot report velocity --update"
  pre_dispatch:
    - "echo 'Dispatching {agent} for {action}'"
  post_dispatch:
    - "autopilot enforce metrics --record"
```

---

## Key Technical Decisions

### ADR-1: Package Distribution Strategy

**The Situation:** The tool needs to be installable on developer machines without requiring them to clone a monorepo.

**Options:**
1. **PyPI package** (`pip install autopilot-cli`) -- standard distribution, versioned releases
2. **pipx install from git** (`pipx install git+https://...`) -- no PyPI, always from source
3. **uv tool install** (`uv tool install autopilot-cli`) -- modern Python, isolated env

**Decision:** Distribute via PyPI with `uv tool install` as the recommended installation method. PyPI gives us versioned releases and dependency resolution. `uv tool install` gives us isolated environments. `pipx` works too.

```bash
# Recommended
uv tool install autopilot-cli

# Alternative
pipx install autopilot-cli

# From source
uv tool install git+https://github.com/org/autopilot-cli
```

**Trade-off:** PyPI publishing requires CI/CD setup and version management. Worth it for discoverability and reproducibility.

### ADR-2: `.autopilot/` vs Project-Root Layout

**The Situation:** The RepEngine autopilot lives as a sibling directory (`autopilot/`) to the service code. Should the new tool use a dot-directory inside the project?

**Decision:** Use `.autopilot/` inside the project root.

**Why:**
- Follows convention (`.github/`, `.vscode/`, `.claude/`)
- Clearly separates autopilot infrastructure from project code
- Allows multiple projects in a monorepo, each with its own `.autopilot/`
- The dot-prefix signals "tooling, not application code"

**Trade-off:** Existing RepEngine autopilot would need a one-time migration. Provide `autopilot migrate` command.

### ADR-3: Global State Location

**Decision:** `~/.autopilot/` for global config, project registry, and SQLite database.

```
~/.autopilot/
  config.yaml          # Global defaults (models, usage limits)
  projects.yaml        # Project registry
  autopilot.db         # SQLite analytics database
  templates/           # Custom templates
  cache/               # Template cache, claude-flow cache
```

### ADR-4: Multi-Project Orchestration Model

**The Situation:** RepEngine's autopilot uses a single daemon that interleaves work across multiple project checkouts. Should Autopilot CLI do the same?

**Options:**
1. **Single orchestrator** (RepEngine model) -- one daemon reads all projects, PL decides allocation
2. **Per-project daemons** -- each project has its own daemon, global coordinator manages resources
3. **Hybrid** -- per-project daemons with a lightweight global resource broker

**Decision:** Per-project daemons with global resource limits (Option 2 with constraints from Option 3).

**Why:**
- **Isolation:** A stuck cycle in project A does not block project B
- **Simplicity:** Each daemon is self-contained, uses the same code as single-project mode
- **Resource management:** Global limits in `~/.autopilot/config.yaml` cap total concurrent daemons and agents
- **The PL gets simpler:** A PL that only manages one project produces better dispatch plans than one juggling four

**Trade-off:** No cross-project intelligence (e.g., "project A is blocked on a human answer, so give its cycles to project B"). This can be added later as a global scheduler layer without changing the per-project daemon architecture.

### ADR-5: Configuration Format

**Decision:** YAML for all configuration.

**Why not TOML:** The existing system uses YAML. The Pydantic config model parses YAML. Agent prompts reference YAML paths. Switching to TOML would require migrating existing users and rewriting the config layer for zero functional benefit. TOML is arguably nicer for flat configs, but autopilot config has deep nesting (agent_timeouts, per-project overrides, quality gates) where YAML is more natural.

### ADR-6: REPL Implementation

**Decision:** prompt-toolkit for the REPL loop, Typer for command parsing within the REPL.

**Why not just Typer:** Typer is designed for CLI commands, not persistent interactive sessions. It does not natively support a REPL loop with history, completion, and continuous state. prompt-toolkit handles the readline layer; Typer handles the command routing.

**Why not IPython/Jupyter:** Overkill. We need a command REPL, not a Python REPL. The interaction model is `autopilot> projects list`, not `>>> workspace.projects.list()`.

### ADR-7: claude-flow Integration Approach

**Decision:** Continue subprocess-based integration (`npx claude-flow@alpha ...`).

**Why not MCP-based:** The MCP tools (`mcp__claude-flow__*`) are available in the context of an MCP server session. The autopilot daemon runs as a standalone Python process, not inside a Claude session. Calling MCP tools would require either running an MCP client (complex) or wrapping the daemon in a Claude session (defeats the purpose).

**Why not library import:** claude-flow is a Node.js package. Importing it from Python requires a bridge (subprocess, FFI, or JSON-RPC), which is exactly what the current subprocess approach already does.

**Improvement:** Pin the claude-flow version in config instead of using `@alpha`. Add a health check at daemon startup that verifies claude-flow is available and the expected version.

---

## Risk Register

### HIGH: Agent Prompt Quality for New Projects

**Probability:** High (the RepEngine prompts are tuned over hundreds of cycles)
**Impact:** Major -- poor prompts lead to wasted cycles, bad code, infinite loops
**Mitigation:** Ship battle-tested prompt templates derived from the RepEngine originals. Include a "prompt tuning guide" in docs. Add a `autopilot agent test <role>` command that runs a dry-run dispatch and evaluates the output.
**Detection:** Track dispatch success rate per agent role. Alert when it drops below threshold.

### HIGH: claude-flow Version Compatibility

**Probability:** High (alpha software, breaking changes expected)
**Impact:** Hive-mind sessions fail silently or produce garbage
**Mitigation:** Version-pin claude-flow in config. Add startup health check. Maintain a compatibility matrix. Wrap all claude-flow calls with version-specific error handling.
**Detection:** Hive session failure rate spike.

### MEDIUM: SQLite Concurrency Under Multiple Daemons

**Probability:** Medium (SQLite handles concurrent reads well, concurrent writes less so)
**Impact:** Occasional write failures, lost metrics data
**Mitigation:** Use WAL mode (Write-Ahead Logging) for SQLite. Use retry-with-backoff for write operations. Keep write operations small and infrequent (once per cycle, not per dispatch).
**Detection:** SQLite busy errors in daemon logs.

### MEDIUM: Template Drift from Upstream Best Practices

**Probability:** Medium (ruff rules, eslint configs evolve monthly)
**Impact:** Templates generate outdated enforcement configs
**Mitigation:** Version templates. Add `autopilot enforce update` command that refreshes enforcement config from latest template. Include a "last-updated" field in generated configs.
**Detection:** Periodic comparison of generated configs against latest template.

### LOW: DA Consuming Too Many Cycles

**Probability:** Low-Medium (DA's work is primarily read-only: Render API calls + curl + git log)
**Impact:** Reduced capacity for feature development
**Mitigation:** Use `sonnet` model (cheaper/faster than `opus`), cap at 30 max turns, 900s timeout. Monitor cycle reports for DA duration. If DA consistently takes > 2 minutes, consider downgrading specific checks to a scheduler Python hook.
**Detection:** Daily summary shows DA duration per cycle.

### LOW: PL Forgets to Dispatch DA

**Probability:** Low (given explicit prompt instructions)
**Impact:** Deployment monitoring gaps
**Mitigation:** If this happens consistently (3+ cycles without DA dispatch), upgrade to scheduler-injected DA -- the scheduler automatically prepends a DA dispatch at the start of every cycle, before invoking PL.
**Detection:** Cycle reports show whether DA was included in dispatch plan.

### LOW: Adoption Resistance from Existing RepEngine Workflow

**Probability:** Low (single user/team context currently)
**Impact:** Wasted development effort
**Mitigation:** Provide `autopilot migrate` command that converts existing RepEngine autopilot layout to `.autopilot/` format. Maintain backward compatibility for the first few releases.

---

## Implementation Plan

### Phase 1: Foundation (3-5 sprints)

**Goal:** Working CLI with project init and basic REPL -- no autonomous execution yet.

**Deliverables:**
- [ ] Package scaffolding (pyproject.toml, src layout, test infrastructure)
- [ ] Core config model (evolved from RepEngine config.py)
- [ ] Core data models (evolved from RepEngine models.py)
- [ ] `autopilot init` -- project scaffolding from templates
- [ ] `autopilot projects list/status` -- global project registry
- [ ] REPL skeleton with prompt-toolkit
- [ ] Rich display helpers (tables, panels, progress)
- [ ] SQLite schema and migration infrastructure
- [ ] Shared utilities (subprocess, process, sanitizer, paths, git)
- [ ] Template system (Python project type only)

**Success criteria:** `autopilot init --type python --name test-project` creates a valid `.autopilot/` directory. `autopilot` launches a REPL. `autopilot projects` lists registered projects.

### Phase 2: Task Management (2-3 sprints)

**Goal:** Full task lifecycle without autonomous execution.

**Deliverables:**
- [ ] Task file parsing (markdown format from RepEngine convention)
- [ ] `autopilot task create` -- interactive task creation
- [ ] `autopilot task list` -- task board display
- [ ] `autopilot task create --from-discovery` -- discovery-to-task conversion
- [ ] Sprint planning with velocity tracking
- [ ] `autopilot task sprint plan/close`
- [ ] Fibonacci estimation support
- [ ] SQLite velocity storage

**Success criteria:** Full task create → estimate → plan → track lifecycle works manually. Tasks are valid RepEngine-format markdown.

### Phase 3: Autonomous Execution (3-5 sprints)

**Goal:** The daemon runs cycles, dispatches agents, and produces PRs.

**Deliverables:**
- [ ] Agent invoker (evolved from RepEngine agent.py)
- [ ] Dispatch parser (reuse RepEngine dispatch.py)
- [ ] Scheduler with cycle orchestration (evolved from RepEngine scheduler.py)
- [ ] Daemon with signal handling (evolved from RepEngine daemon.py)
- [ ] Hive-mind integration (evolved from RepEngine hive.py)
- [ ] Circuit breaker and usage tracking
- [ ] Session management (start/stop/list/attach)
- [ ] Cycle reports and daily summary
- [ ] Decision log with rotation
- [ ] `autopilot start/stop/pause/resume/cycle/plan/execute`

**Success criteria:** `autopilot start` launches a daemon that runs cycles. Dispatches produce real Claude CLI invocations. Cycle reports are written.

### Phase 4: DevOps Agent -- Deployment Monitoring (2-3 sprints)

**Goal:** Automated deployment health monitoring integrated into every cycle.

**Deliverables:**
- [ ] DA system prompt (`devops-agent.md`) with monitoring workflows (check_deploys, verify_deploy, investigate_failure)
- [ ] Render service registry in config (service IDs, health endpoints, staging URLs)
- [ ] DA added to `AgentName`, `VALID_AGENTS`, config models, and dispatch normalization
- [ ] PL prompt updated with DA dispatch logic (every cycle: check_deploys; after merges: verify_deploy)
- [ ] Deployment Status section added to project board template
- [ ] Known failure pattern catalog (git auth expired → human escalation, broken imports → EM dispatch, missing deps → EM dispatch, crash loop → EM dispatch)
- [ ] GitHub issue creation for deploy failures with structured diagnostics
- [ ] `fix_deploy` action added as recognized EM action in PL prompt
- [ ] Manual-action escalation via question-queue.md for infrastructure failures

**Success criteria:** DA runs every cycle via PL dispatch. Deploy failures are detected within one cycle (~30 min). Failed deploys produce GitHub issues with diagnostic context. PL reads deployment status before dispatching PD for feature verification. Known code-level failures (broken imports, missing deps) trigger EM remediation dispatches.

**Effort estimate:** 15-18 story points across 9 tasks. Phases 1-3 (foundation + registry + board: 7-10 SP) deliver core monitoring. Phases 4-5 (failure investigation + remediation: 8 SP) add intelligence.

### Phase 5: Enforcement Engine (2-3 sprints)

**Goal:** All 5 enforcement layers are operational.

**Deliverables:**
- [ ] Enforcement engine architecture
- [ ] Layer 1: Editor config generation (ruff, eslint, pyright)
- [ ] Layer 2: Pre-commit hook setup (lefthook, block-no-verify)
- [ ] Layer 3: CI/CD template generation (GitHub Actions)
- [ ] Layer 4: Agent guardrail integration (PreToolUse hooks)
- [ ] Layer 5: Protected code region support
- [ ] `autopilot enforce setup/check/report`
- [ ] Metrics collection to SQLite
- [ ] Quality gate prompt generation for hive-mind

**Success criteria:** `autopilot enforce setup` configures all 5 layers for a Python project. `autopilot enforce check` runs all checks and reports violations by category. Quality gates are injected into hive-mind objectives.

### Phase 6: Discovery Integration and Polish (2-3 sprints)

**Goal:** End-to-end workflow from discovery to autonomous execution.

**Deliverables:**
- [ ] Norwood discovery agent prompt template
- [ ] `autopilot discover` -- launch and monitor discovery sessions
- [ ] Discovery-to-task conversion pipeline
- [ ] Shelly estimation agent integration
- [ ] TypeScript project type template
- [ ] `autopilot migrate` -- RepEngine layout migration
- [ ] Comprehensive documentation
- [ ] Shell completions (bash, zsh, fish)

**Success criteria:** `autopilot discover "Build OAuth adapter"` → produces discovery doc → `autopilot task create --from-discovery` → creates tasks → `autopilot start` → autonomous execution produces PRs.

### Phase 7: Multi-Project and Advanced Features (2-3 sprints)

**Goal:** Production-ready multi-project orchestration.

**Deliverables:**
- [ ] Global resource broker (concurrent daemon limits)
- [ ] Per-project usage limits
- [ ] Cross-project reporting dashboard
- [ ] Event-driven scheduler triggers
- [ ] Custom template support (`~/.autopilot/templates/`)
- [ ] Hybrid project type template
- [ ] Workflow hooks (pre/post cycle/dispatch)
- [ ] Export/import for project configs

**Success criteria:** Multiple projects run concurrent daemons within global resource limits. Velocity and quality metrics aggregate across projects.

---

## Success Metrics

### Technical
- All 11 anti-pattern categories have enforcement rules
- Cycle success rate >= 85% (matching RepEngine baseline)
- Agent timeout rate <= 10%
- Zero data loss from SQLite concurrency issues
- Deploy failure detection latency < 30 minutes (within one DA cycle)
- 100% of deploy failures produce GitHub issues with diagnostic context
- Zero PD cycles wasted on undeployed features (PL gates on DA status)

### Delivery
- Phase 1-3 (working autonomous CLI): 8-13 sprints
- Phase 4 (deployment monitoring): additional 2-3 sprints
- Phase 5-7 (enforcement, discovery, multi-project): additional 6-9 sprints
- Total: 16-25 sprints

### Quality
- Pyright strict mode, zero errors
- Ruff with extended ruleset, zero warnings
- Test coverage >= 90% for core/ and orchestration/
- Test coverage >= 80% for cli/ (integration tests)

### Adoption
- `autopilot init` produces a working setup in under 2 minutes
- First autonomous cycle runs within 30 minutes of init
- Migration from RepEngine layout takes under 5 minutes

---

## Appendix: RepEngine Autopilot Source Files Referenced

All source analysis is based on the following files at `/Users/montes/AI/RepEngine/rep-engine-service/autopilot/`:

- `src/autopilot/cli.py` -- CLI action commands
- `src/autopilot/cli_display.py` -- Display commands
- `src/autopilot/config.py` -- Pydantic config model
- `src/autopilot/models.py` -- Shared data models
- `src/autopilot/scheduler.py` -- Cycle orchestration
- `src/autopilot/daemon.py` -- Daemon lifecycle
- `src/autopilot/agent.py` -- Claude CLI invocation
- `src/autopilot/dispatch.py` -- Dispatch plan parsing
- `src/autopilot/hive.py` -- Hive-mind integration
- `src/autopilot/usage.py` -- Usage tracking
- `src/autopilot/reports.py` -- Reporting and log rotation
- `src/autopilot/sanitizer.py` -- Secret redaction
- `config.yaml` -- Production configuration
- `pyproject.toml` -- Package configuration

Anti-pattern enforcement research at:
- `/Users/montes/Library/Mobile Documents/com~apple~CloudDocs/Projects/AI_Projects/Research/ai-agent-anti-patterns-enforcement.md`
- `/Users/montes/Library/Mobile Documents/com~apple~CloudDocs/Projects/AI_Projects/Research/ai-agent-anti-patterns-field-guide.md`

DevOps Agent discovery at:
- `/Users/montes/Library/Mobile Documents/com~apple~CloudDocs/Projects/AI_Projects/autopilot-cli/docs/ideation/devops-agent-discovery.md`

Original Python rewrite discovery at:
- `/Users/montes/AI/RepEngine/rep-engine-service/docs/discovery/autopilot-python-rewrite-discovery.md`
