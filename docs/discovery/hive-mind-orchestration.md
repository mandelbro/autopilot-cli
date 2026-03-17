# Discovery: Hive-Mind Orchestration Integration

## The One-Liner

Replace autopilot's current swarm-init-plus-individual-spawn workflow with a single `hive-mind spawn` command that batches tasks, runs quality gates, creates PRs, and loops through code review autonomously.

## The Problem

The user has discovered a high-leverage workflow pattern using `npx ruflo@latest hive-mind spawn` that dramatically outperforms autopilot's current orchestration approach. The current `HiveMindManager` in `src/autopilot/orchestration/hive.py` does three things:

1. Initializes a swarm via `npx ruflo swarm init`
2. Spawns individual workers via `npx ruflo agent spawn` in a loop
3. Records and shuts down sessions

This maps to an older claude-flow/ruflo coordination model where autopilot managed the lifecycle externally. The winning pattern instead delegates the entire workflow to a single `hive-mind spawn` invocation with a carefully constructed objective prompt that includes batch grouping, quality gates, PR creation, and iterative code review. Autopilot's job becomes: build that objective prompt, fire the hive-mind, and track the outcome.

## The Solution

Evolve the orchestration layer to:

1. Add a new `HiveObjectiveBuilder` that constructs parameterized objective prompts using Jinja2 templates
2. Replace the `swarm init` + `agent spawn` loop with a single `hive-mind spawn` invocation
3. Add a new CLI command `autopilot hive` with subcommands for spawning, monitoring, and reviewing hive-mind sessions
4. Integrate the code review loop (PR creation, Claude review label, feedback loop, merge) into the objective template
5. Add configurable quality passes (duplication detection, cleanup, security, coverage) as template sections

## Current State Analysis

### Existing `HiveMindManager` (`src/autopilot/orchestration/hive.py`)

The current implementation manages a three-step lifecycle:

- `create_branch()` -- git branch creation with `per-task` or `batch` strategies
- `init_hive()` -- calls `npx ruflo swarm init --topology hierarchical --objective "..."` and appends quality gates from config
- `spawn_workers()` -- loops `npx ruflo agent spawn -t coder --name worker-{i}` N times
- `record_session()` / `shutdown()` -- bookkeeping

**Key limitation**: The objective prompt is a plain string concatenation with quality gates appended. There is no template system, no conditional sections, no support for the batch-group-implement-PR-review loop that has been proven effective.

### What the Winning Pattern Does Differently

The user's successful command:
```bash
npx ruflo@latest hive-mind spawn '<objective>' --namespace core-autopilot --claude
```

The objective prompt encodes the entire workflow:
1. Read task file, identify task IDs
2. Group related tasks into batches
3. For each batch: implement, run `just` (all quality checks), create PR, request code review via Claude, iterate on feedback, merge, move to next batch

This is fundamentally different from autopilot's current model where the scheduler manages individual dispatch cycles. The hive-mind approach is a single long-running invocation that manages its own lifecycle.

### Orchestration Module Inventory

| Component | File | Lines | Reuse Status |
|-----------|------|-------|--------------|
| `HiveMindManager` | `orchestration/hive.py` | 226 | **Evolve** -- keep `create_branch`, `record_session`, `shutdown`; replace `init_hive` + `spawn_workers` |
| `AgentInvoker` | `orchestration/agent_invoker.py` | 254 | **Keep** -- still needed for non-hive agent calls |
| `Scheduler` | `orchestration/scheduler.py` | 307 | **Keep** -- the daemon loop still uses this for interval/event cycles |
| `Dispatcher` | `orchestration/dispatcher.py` | 232 | **Keep** -- dispatch plan parsing still used by PL-driven cycles |
| `Daemon` | `orchestration/daemon.py` | 232 | **Keep** -- background process management unchanged |
| `CircuitBreaker` | `orchestration/circuit_breaker.py` | 86 | **Keep** -- can be used to gate hive-mind spawn failures |
| `UsageTracker` | `orchestration/usage.py` | 309 | **Keep** -- track hive-mind invocations against rate limits |
| `HookRunner` | `orchestration/hooks.py` | 197 | **Keep** -- pre/post hive hooks are a natural extension |
| `TriggerManager` | `orchestration/triggers.py` | 222 | **Keep** -- event triggers can initiate hive-mind sessions |
| `ResourceBroker` | `orchestration/resource_broker.py` | 210 | **Keep** -- enforce max concurrent hive-mind sessions |

### Core Module Inventory

| Component | File | Lines | Reuse Status |
|-----------|------|-------|--------------|
| `AutopilotConfig` | `core/config.py` | 302 | **Extend** -- add `HiveMindConfig` section |
| `SessionManager` | `core/session.py` | 209 | **Extend** -- add `SessionType.HIVE_MIND` |
| `TemplateRenderer` | `core/templates.py` | 148 | **Reuse** -- Jinja2 rendering for objective templates |
| `models.py` | `core/models.py` | 387 | **Extend** -- add `HiveMindResult` model |

### CLI Module

| Component | File | Lines | Reuse Status |
|-----------|------|-------|--------------|
| `app.py` | `cli/app.py` | 356 | **Extend** -- register `hive_app` Typer group |
| `session.py` | `cli/session.py` | 401 | **Reuse** -- session list/attach/log already work for tracking |

## Existing Components and Reuse Plan

### What We Will Reuse

- **`TemplateRenderer`** from `core/templates.py` -- provides the Jinja2 infrastructure (loader, `StrictUndefined`, user-override paths, `_template.yaml` metadata). Note: `TemplateRenderer.render_to()` outputs to the filesystem, but `HiveObjectiveBuilder` needs string output. We will add a `render_to_string(template_name, context)` method to `TemplateRenderer` so the objective builder can reuse the same rendering infrastructure rather than building a parallel Jinja2 environment. We will create a new template type `hive-objective/` alongside existing `python/` and `typescript/` templates.
- **`HiveMindManager.create_branch()`** -- branch creation logic with batch naming is already solid.
- **`HiveMindManager.record_session()` / `shutdown()`** -- session lifecycle bookkeeping works.
- **`HiveSession` dataclass** -- extend it rather than replace it.
- **`QualityGatesConfig`** -- already captures the `just` / `pre-commit` / `type-check` / `test` commands.
- **`SessionManager`** -- track hive-mind sessions in the same SQLite database.
- **`UsageTracker`** -- count hive-mind invocations against daily/weekly limits.
- **`ResourceBroker`** -- enforce max concurrent hive-mind sessions.
- **`HookRunner`** -- run pre/post hooks around hive-mind lifecycle events.
- **`CircuitBreaker`** -- trip after consecutive hive-mind failures.

### What We Will Not Reuse

- **`HiveMindManager.init_hive()`** -- uses `swarm init` which is the wrong ruflo command. Replacing with `hive-mind spawn`.
- **`HiveMindManager.spawn_workers()`** -- the hive-mind manages its own workers internally. This method becomes unnecessary.
- **`Scheduler.run_cycle()` for hive-mind sessions** -- the hive-mind is a long-running invocation, not a scheduler cycle. The scheduler may *trigger* a hive-mind session but doesn't manage its execution.
- **`AgentInvoker`** -- hive-mind sessions don't go through the agent invoker. They're a direct subprocess call to ruflo.

### Consolidation Opportunities

There are currently two patterns for "run a subprocess against ruflo":
1. `HiveMindManager` calls `run_with_timeout` with `npx ruflo@{version}` commands
2. `AgentInvoker` calls `run_claude_cli` for individual agent invocations

Both share the pattern of: build command, run subprocess, check exit code, log result. The `run_with_timeout` and `build_clean_env` utilities in `utils/subprocess.py` are already shared. No consolidation needed -- the two patterns serve genuinely different purposes (long-running hive-mind vs. short-lived agent invocations).

## Architecture Decision: Hive-Mind Invocation Strategy

### The Situation

We need to decide how autopilot invokes and manages hive-mind sessions. The current approach (init swarm + spawn workers) is too granular. The winning approach (single `hive-mind spawn` with a rich objective) is proven. But we need to decide where the boundary falls between "what autopilot manages" and "what the hive-mind manages internally."

### Option 1: Thin Wrapper (Recommended)

Autopilot builds the objective prompt via Jinja2 templates, calls `hive-mind spawn` once, then monitors the process. The hive-mind handles batch grouping, PR creation, code review loops, and merging internally via the objective prompt instructions.

- **Why it works**: Proven pattern, minimal code to write, leverages ruflo's built-in orchestration
- **Why it might fail**: Less control over individual batches, harder to interrupt mid-batch
- **Effort**: 3-5 days

### Option 2: Thick Orchestrator

Autopilot parses the task file, groups batches itself, then spawns a separate hive-mind session per batch with a simpler objective. Autopilot manages the batch-to-batch transitions, PR creation, and review loop.

- **Why it works**: More control, better error handling per batch, easier to resume from failures
- **Why it might fail**: Reimplements what ruflo already does, more code to maintain, fights the tool
- **Effort**: 8-12 days

### Option 3: Hybrid

Autopilot groups batches and builds per-batch objectives, but delegates execution to hive-mind. Autopilot monitors completion and triggers the next batch.

- **Why it works**: Balance of control and delegation
- **Why it might fail**: Complex state machine, two systems managing batches
- **Effort**: 5-8 days

### What We're Going With

**Option 1: Thin Wrapper.** The evidence is clear -- the single-invocation pattern works. The objective prompt is the interface contract, and Jinja2 templates are how we parameterize it. We accept less granular control in exchange for proven reliability and dramatically less code.

### Trade-offs We're Accepting

- We give up per-batch error handling in exchange for simpler orchestration
- We give up interrupt-and-resume at batch boundaries in exchange for a single long-running session
- We depend on ruflo's internal batch management instead of building our own

### Future Enhancement: Supervised Mode

The Thin Wrapper is the right starting point, but a future iteration could add an optional "supervised mode" where autopilot polls `hive-mind status` between batches and can intervene on failures. This preserves initial simplicity while leaving the door open for more control without a rewrite.

## Subprocess Lifecycle

> **Status**: Confirmed via research (Issues #955, #368, #578)

### Confirmed Behavior

**`hive-mind spawn --claude` blocks the calling process** for the entire Claude Code session (potentially hours). The `--claude` flag launches an interactive Claude Code process that receives a coordination prompt and uses MCP tools for multi-agent work. No actual parallel subprocesses are spawned — Claude Code receives the objective and manages the work internally.

**Without `--claude`, the spawn exits quickly** — it registers workers and returns immediately.

Since autopilot always uses `--claude` mode, the subprocess strategy is:

### Implementation: `subprocess.Popen` (non-blocking)

```python
# --claude mode: long-running blocking process → use Popen
process = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    cwd=self._cwd,
    env=build_clean_env(),
)
session.pid = process.pid  # Essential for monitoring/cleanup/cancellation
```

**Key implications:**
- `spawn_timeout_seconds` is **irrelevant** for `--claude` mode — the process runs for hours. This config field should be repurposed as the timeout for the Popen launch confirmation (process starts successfully).
- `session_timeout_seconds` (default 4 hours) governs the Popen kill timeout — after this duration, the process is forcefully terminated.
- PID tracking is **essential** — stored in `HiveSession.metadata["pid"]` for cleanup, orphan detection, and `hive stop`.
- The existing `run_with_timeout` utility in `utils/subprocess.py` uses `subprocess.run` (blocking) — a new `run_async` or `popen_with_monitoring` utility is needed.

### Available ruflo hive-mind subcommands

```
hive-mind init, spawn, status, task, join, leave,
consensus, broadcast, memory, optimize-memory, shutdown
```

Note: `hive-mind spawn --help` does not document spawn-specific flags (known limitation, Issue #345). The `--claude` and `--namespace` flags are confirmed working via user testing.

### Pre-flight checks before spawning

1. Validate git working tree is clean (`git status --porcelain`) — the hive-mind creates branches, PRs, and merges; a dirty tree causes conflicts
2. Validate ruflo availability: `npx ruflo@latest hive-mind --help` succeeds
3. Validate namespace is not already in use by an active session
4. Log objective length (warn if > 4000 characters)

### Sources

- [Issue #955](https://github.com/ruvnet/ruflo/issues/955): `--claude` flag was documented but not implemented; fixed in v3.0.0-alpha.124
- [Issue #368](https://github.com/ruvnet/ruflo/issues/368): Confirmed no actual parallel subprocesses — Claude Code receives coordination prompt
- [Issue #578](https://github.com/ruvnet/ruflo/issues/578): `--claude` and `--non-interactive` flag implementation

## Result Collection Strategy

> **Status**: Confirmed via research — ruflo does **not** expose structured JSON results.

### Confirmed: No Structured Output

ruflo's `hive-mind spawn` produces multi-stage plaintext output (swarm summary, config, coordination prompt). There is no `--format json` flag on `spawn` or `status`. The `hive-mind status` subcommand exists but returns plaintext only — treat it as informational/display-only.

MCP tools (`memory_usage`, `task_orchestrate`, `consensus_vote`) provide runtime state *during* a session but not post-session result extraction.

### Strategy: Git-Derived Results + Exit Code

After the Popen process completes, autopilot collects results from observable state:

1. **Exit code** — `process.returncode` (0 = success, non-zero = failure). Always available.
2. **Raw output** — capture `stdout` and `stderr` from Popen pipes for logging/debugging.
3. **PRs created/merged** — query GitHub via `gh pr list --author @me --search "created:>={session_start_time}"` or filter by branch naming convention.
4. **Tasks completed** — re-read the task file and count `Complete: [x]` markers, comparing before/after counts.
5. **Batches completed** — infer from merged PR count (each batch = one PR).

### `HiveMindResult` Design

Result fields that cannot be reliably detected are `Optional[int] = None`:

```python
@dataclass(frozen=True)
class HiveMindResult:
    session_id: str
    namespace: str
    task_file: str
    task_ids: tuple[str, ...]
    exit_code: int = 0
    duration_seconds: float = 0.0
    output: str = ""                    # raw stdout
    error: str = ""                     # raw stderr
    # Git-derived (populated post-session via _collect_results)
    tasks_completed: int | None = None  # count of [x] markers added
    prs_created: int | None = None
    prs_merged: int | None = None
    batches_completed: int | None = None  # inferred from prs_merged
```

### Sources

- [Issue #1036](https://github.com/ruvnet/ruflo/issues/1036): CLI commands reference non-existent MCP tools — status APIs may be incomplete
- Existing `test_hive.py` mocks subprocess output as empty strings, confirming no structured parsing exists today

## Implementation Plan

### Phase 1: Configuration and Models (3 points)

**Goal**: Add config and data models for hive-mind orchestration.

**Changes**:

1. **`src/autopilot/core/config.py`** -- Add `HiveMindConfig` to `AutopilotConfig`:

```python
class HiveMindConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    enabled: bool = False
    namespace: str = ""  # defaults to project name if empty
    worker_count: int = Field(default=4, gt=0, le=15)
    use_claude: bool = True  # --claude flag
    batch_strategy: Literal["auto", "manual"] = "auto"
    objective_template: str = "default"  # template name in hive-objective/
    # Quality pass toggles
    duplication_check: bool = True
    cleanup_pass: bool = True
    security_scan: bool = True
    coverage_check: bool = True
    file_size_check: bool = True
    # Review loop
    code_review_enabled: bool = True
    code_review_label: str = "claude-review"
    max_review_rounds: int = Field(default=3, gt=0, le=10)
    auto_merge: bool = True
    # Commands (config-driven, no hardcoding)
    format_command: str = "just format"
    # Timeouts
    spawn_timeout_seconds: int = Field(default=60, gt=0)
    session_timeout_seconds: int = Field(default=14400, gt=0)  # 4 hours
```

Add to `AutopilotConfig`:
```python
class AutopilotConfig(BaseModel):
    # ... existing fields ...
    hive_mind: HiveMindConfig = Field(default_factory=HiveMindConfig)
```

YAML config example:
```yaml
hive_mind:
  enabled: true
  namespace: "core-autopilot"
  worker_count: 4
  use_claude: true
  code_review_enabled: true
  max_review_rounds: 3
  auto_merge: true
  format_command: "just format"
```

2. **`src/autopilot/core/models.py`** -- Add `SessionType.HIVE_MIND` enum value and `HiveMindResult` dataclass:

> **Note**: Grep all `SessionType` usages in the codebase to verify no switch/match statements need updating for the new `HIVE_MIND` value.

```python
class SessionType(StrEnum):
    DAEMON = "daemon"
    CYCLE = "cycle"
    DISCOVERY = "discovery"
    MANUAL = "manual"
    HIVE_MIND = "hive_mind"  # new

@dataclass(frozen=True)
class HiveMindResult:
    session_id: str
    namespace: str
    task_file: str
    task_ids: tuple[str, ...]  # tuple for immutability on frozen dataclass
    batches_completed: int | None = None  # populated via result collection strategy
    prs_created: int | None = None
    prs_merged: int | None = None
    exit_code: int = 0
    duration_seconds: float = 0.0
    output: str = ""
    error: str = ""
```

### Phase 2: Objective Template System (5 points)

**Goal**: Create a Jinja2-based objective template that encodes the full hive-mind workflow.

**Changes**:

1. **`templates/hive-objective/default.j2`** -- The core objective template:

```jinja2
Review Task IDs: {{ task_ids | join(', ') }} from @{{ task_file }}, group any related tasks into batches, then implement the work following the Task Workflow System guidelines.

For each batch, once it is implemented and all code quality checks are passing ({{ quality_command }}):
{% if code_review_enabled %}
- Create a PR with a description of each task in the batch
- Request a code review from Claude Code (@.github/workflows/claude-code-review.yml)
- Make sure all CI checks pass
- Make any changes requested in code review
- Loop until Claude approves the PR (max {{ max_review_rounds }} rounds)
{% if auto_merge %}
- Merge the PR
{% endif %}
- Move on to the next batch
{% else %}
- Create a PR with a description of each task in the batch
- Move on to the next batch
{% endif %}

{% if duplication_check %}
## Duplication Detection
After implementing each batch and before creating the PR, scan the affected files for:
- Duplicate function/method implementations across modules
- Copy-pasted code blocks that should be extracted to shared utilities
- Similar patterns that appear 3+ times (Rule of Three) -- consolidate into shared abstractions
- Redundant imports or re-exports
{% endif %}

{% if cleanup_pass %}
## Cleanup Pass
Before creating the PR, run a cleanup pass on all modified files:
- Remove dead code, unused imports, and unreachable branches
- Apply consistent formatting ({{ format_command }})
- Remove TODO/FIXME comments that have been addressed
- Ensure docstrings are present on public APIs
{% endif %}

{% if security_scan %}
## Security Analysis
Before creating the PR, verify:
- No secrets, API keys, or credentials in source files
- No hardcoded passwords or tokens
- Input validation at system boundaries
- File path sanitization where applicable
- No use of eval() or equivalent unsafe patterns
{% endif %}

{% if coverage_check %}
## Test Coverage
Ensure each batch:
- Has test coverage for new/modified public APIs
- All existing tests pass after changes
- Test files follow project naming conventions
{% endif %}

{% if file_size_check %}
## File Size Optimization
After implementation, check that:
- No file exceeds 500 lines without architectural justification
- Files approaching 400 lines are evaluated for splitting
- Each file has a single clear responsibility
{% endif %}

## Task Status Updates
After each batch is complete and merged:
- Mark completed tasks as `Complete: [x]` in the task file
- Update the task index file with new completion counts
{% if sprint_record %}
- Update the sprint record at {{ sprint_record }}
{% endif %}

## Quality Gates
{{ quality_gates }}
```

2. **`templates/hive-objective/_template.yaml`** -- Template metadata:

```yaml
expected_files:
  - default.j2
# All template variables — user-provided marked with (required)
variables:
  - task_ids              # (required) CLI argument
  - task_file             # (required) CLI argument
  - quality_command       # from quality_gates.all or "just"
  - format_command        # from hive_mind.format_command
  - code_review_enabled   # from hive_mind config
  - max_review_rounds     # from hive_mind config
  - auto_merge            # from hive_mind config
  - duplication_check     # from hive_mind config
  - cleanup_pass          # from hive_mind config
  - security_scan         # from hive_mind config
  - coverage_check        # from hive_mind config
  - file_size_check       # from hive_mind config
  - quality_gates         # built from QualityGatesConfig
  - sprint_record         # from active sprint config (optional)
```

3. **`src/autopilot/orchestration/objective_builder.py`** -- New module (~120 lines):

```python
class HiveObjectiveBuilder:
    """Builds parameterized hive-mind objective prompts from Jinja2 templates."""

    def __init__(self, config: AutopilotConfig) -> None:
        self._config = config
        self._renderer = TemplateRenderer(
            "hive-objective",
            package_templates_dir=_PACKAGE_TEMPLATES,
        )

    def build(
        self,
        task_file: str,
        task_ids: list[str],
        *,
        template_name: str = "default",
    ) -> str:
        """Render the objective template with config-driven context."""
        context = self._build_context(task_file, task_ids)
        rendered = self._renderer.render_to_string(f"{template_name}.j2", context)
        if len(rendered) > 4000:
            log.warning("objective_length_warning", length=len(rendered))
        return rendered

    def _build_context(self, task_file: str, task_ids: list[str]) -> dict:
        hive = self._config.hive_mind
        gates = self._config.quality_gates
        return {
            "task_ids": task_ids,
            "task_file": task_file,
            "quality_command": gates.all or "just",
            "format_command": hive.format_command,
            "code_review_enabled": hive.code_review_enabled,
            "max_review_rounds": hive.max_review_rounds,
            "auto_merge": hive.auto_merge,
            "duplication_check": hive.duplication_check,
            "cleanup_pass": hive.cleanup_pass,
            "security_scan": hive.security_scan,
            "coverage_check": hive.coverage_check,
            "file_size_check": hive.file_size_check,
            "quality_gates": self._format_quality_gates(gates),
            "sprint_record": "",  # populated from sprint config if active
        }
```

### Phase 3: Hive-Mind Manager Evolution (3 points)

**Goal**: Replace `init_hive` + `spawn_workers` with a single `spawn_hive` method.

**Changes to `src/autopilot/orchestration/hive.py`**:

```python
class HiveMindManager:
    def _preflight_checks(self, namespace: str) -> None:
        """Validate preconditions before spawning a hive-mind session."""
        # 1. Clean git working tree
        result = run_with_timeout(
            ["git", "status", "--porcelain"],
            timeout_seconds=10,
            cwd=self._cwd,
        )
        if result.stdout.strip():
            msg = "Git working tree is dirty. Commit or stash changes before spawning."
            raise HiveError(msg)

        # 2. Check for active session on this namespace
        if self._has_active_session(namespace):
            msg = f"Namespace '{namespace}' already has an active hive-mind session."
            raise HiveError(msg)

    def spawn_hive(
        self,
        objective: str,
        *,
        namespace: str | None = None,
        use_claude: bool = True,
    ) -> HiveSession:
        """Spawn a hive-mind session with the given objective.

        Uses `npx ruflo@latest hive-mind spawn` instead of the older
        swarm init + agent spawn pattern. Uses @latest to ensure
        hive-mind spawn subcommand is always available.

        With --claude (default), the process blocks for the entire
        Claude Code session. We use subprocess.Popen for non-blocking
        invocation and store the PID for monitoring/cancellation.
        """
        hive_config = self._config.hive_mind
        ns = namespace or hive_config.namespace or self._config.project.name

        self._preflight_checks(ns)

        session = HiveSession(
            id=str(uuid.uuid4()),
            branch="",  # hive-mind manages its own branches
            objective=objective,
        )

        cmd = [
            "npx",
            "ruflo@latest",
            "hive-mind",
            "spawn",
            objective,
            "--namespace",
            ns,
        ]
        if use_claude:
            cmd.append("--claude")

        if use_claude:
            # --claude mode: long-running process, use Popen
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self._cwd,
                env=build_clean_env(),
            )
            session.metadata["pid"] = process.pid
            session.metadata["process"] = process  # for wait/poll
            session.status = "spawned"
            log.info("hive_spawned", pid=process.pid, namespace=ns)
        else:
            # Non-claude mode: quick return
            result = run_with_timeout(
                cmd,
                timeout_seconds=hive_config.spawn_timeout_seconds,
                cwd=self._cwd,
                env=build_clean_env(),
            )
            if result.returncode != 0:
                msg = f"Hive-mind spawn failed: {result.stderr.strip()}"
                raise HiveError(msg)
            session.status = "spawned"

        return session

    def stop_hive(self, session: HiveSession, *, force: bool = False) -> None:
        """Stop a running hive-mind session."""
        pid = session.metadata.get("pid")
        ns = session.metadata.get("namespace", "")

        if not force and ns:
            # Graceful: ask ruflo to shut down
            run_with_timeout(
                ["npx", "ruflo@latest", "hive-mind", "shutdown", "--namespace", ns],
                timeout_seconds=30,
                cwd=self._cwd,
                env=build_clean_env(),
            )

        if pid:
            import signal
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass  # already exited

        session.status = "stopped"
```

The existing `init_hive()` and `spawn_workers()` methods remain for backward compatibility but are marked as deprecated with a log warning.

> **Note on `npx ruflo@latest`**: We use `@latest` instead of pinning to `claude_flow_version` to ensure the `hive-mind spawn` subcommand is always available. The config field `claude_flow_version` (named for historical reasons when the package was `@claude-flow/cli`) should be considered tech debt for a future rename to `ruflo_version`.

### Phase 4: CLI Commands (3 points)

**Goal**: Add `autopilot hive` command group.

**New file `src/autopilot/cli/hive.py`** (~200 lines):

```python
hive_app = typer.Typer(name="hive", help="Hive-mind orchestration.")

@hive_app.command("spawn")
def hive_spawn(
    task_file: str = typer.Argument(..., help="Task file path relative to project root."),
    task_ids: str = typer.Option("", help="Task IDs to process (e.g., '001-008' or '001,003,005')."),
    namespace: str = typer.Option("", help="Hive-mind namespace."),
    template: str = typer.Option("default", help="Objective template name."),
    dry_run: bool = typer.Option(False, help="Print the objective without spawning."),
) -> None:
    """Spawn a hive-mind session for a batch of tasks."""

@hive_app.command("status")
def hive_status(namespace: str = typer.Option("", help="Namespace to check.")) -> None:
    """Check hive-mind session status."""

@hive_app.command("list")
def hive_list() -> None:
    """List recent hive-mind sessions."""

@hive_app.command("stop")
def hive_stop(
    namespace: str = typer.Option("", help="Namespace of session to stop."),
    force: bool = typer.Option(False, help="Force kill without graceful shutdown."),
) -> None:
    """Stop a running hive-mind session."""
```

Register in `app.py`:
```python
from autopilot.cli.hive import hive_app
app.add_typer(hive_app)
```

### Phase 5a: Integration Wiring (3 points)

**Goal**: Wire hive-mind into existing orchestration infrastructure.

1. **Integration with existing orchestration**:
   - `ResourceBroker.can_spawn_agent()` gates hive-mind spawns
   - `UsageTracker.record_cycle()` counts hive-mind invocations
   - `HookRunner.run_hooks("pre_hive" / "post_hive")` -- add two new hook points
   - `CircuitBreaker` tracks consecutive hive-mind failures

2. **Session tracking**:
   - `SessionManager.create_session(type=SessionType.HIVE_MIND)` for each spawn
   - Store namespace, task_file, task_ids, PID in session metadata

3. **Cancellation support**:
   - `hive stop` kills the subprocess via stored PID
   - Graceful shutdown via `npx ruflo@latest hive-mind shutdown --namespace <ns>`
   - Force kill fallback via `os.kill(pid, signal.SIGTERM)`

### Phase 5b: Test Coverage (5 points)

**Goal**: Comprehensive test coverage for all new components.

1. **Test files**:
   - `tests/orchestration/test_objective_builder.py` -- template rendering with various config combinations
   - `tests/orchestration/test_hive.py` -- extend existing tests for `spawn_hive`, pre-flight checks, cancellation
   - `tests/cli/test_hive.py` -- CLI command smoke tests with mocked subprocess (spawn, status, list, stop)
   - `tests/core/test_config.py` -- extend for `HiveMindConfig` serialization/deserialization

## Risk Register

### HIGH: Objective Prompt Exceeds Token Limits

**Probability**: Medium -- with all quality passes enabled, the objective could get large.
**Impact**: ruflo silently truncates or fails.
**Mitigation**: The template should produce objectives under 4000 characters. Add a length check in `HiveObjectiveBuilder.build()` with a warning.
**Detection**: Log the objective length on every spawn.

### MEDIUM: Hive-Mind Session Timeout / Orphaned Processes

**Probability**: Medium -- large task batches (8+ tasks) can run for hours. With `Popen`, the process runs independently.
**Impact**: Session hangs, no PR created, tasks not marked complete. Orphaned `npx` process consumes resources.
**Mitigation**: `session_timeout_seconds` config (default 4 hours). Background monitoring thread polls `process.poll()` and kills after timeout. PID stored in session metadata for cleanup via `hive stop`.
**Detection**: Session duration check in `SessionManager.cleanup_orphaned()`. Periodic PID liveness check.

### MEDIUM: Dirty Git State During Hive-Mind Execution

**Probability**: Medium -- user may make local changes while a hive-mind session is running in the background.
**Impact**: Merge conflicts when the hive-mind tries to create PRs or merge.
**Mitigation**: Pre-flight check validates clean working tree. Document that users should not modify the repository while a hive-mind session is active.
**Detection**: Pre-flight `git status --porcelain` check before spawn.

### LOW: Template Rendering Errors

**Probability**: Low -- Jinja2 with `StrictUndefined` catches missing variables.
**Impact**: Spawn fails before anything runs.
**Mitigation**: `HiveObjectiveBuilder` validates all required context variables before rendering. `--dry-run` flag lets users preview the objective.
**Detection**: Validation errors are surfaced immediately in the CLI.

### LOW: Backward Compatibility with Existing Hive Sessions

**Probability**: Low -- few existing sessions use the old pattern.
**Impact**: Existing session records might not display correctly.
**Mitigation**: The new `SessionType.HIVE_MIND` is additive. Old sessions retain their `SessionType.DAEMON` or `SessionType.MANUAL` types.

## Success Metrics

- **Technical**: Hive-mind sessions complete end-to-end (batch, implement, PR, review, merge) without manual intervention
- **Delivery**: Implementation across 5 phases, each independently testable
- **Quality**: All quality passes (duplication, cleanup, security, coverage, file size) execute as part of the objective
- **Adoption**: Users can switch from manual `npx ruflo hive-mind spawn '...'` to `autopilot hive spawn tasks/project/tasks-1.md --task-ids 001-008` with equivalent results

## Total Estimated Effort

| Phase | Points | Description |
|-------|--------|-------------|
| 1 | 3 | Config models and data types |
| 2 | 5 | Objective template system |
| 3 | 3 | HiveMindManager evolution |
| 4 | 3 | CLI commands (spawn, status, list, stop) |
| 5a | 3 | Integration wiring (ResourceBroker, hooks, cancellation) |
| 5b | 5 | Test coverage (4 test files, config/builder/hive/cli) |
| **Total** | **22** | **~2 sprints at current velocity** |

## Appendix: Full Objective Template Variables

| Variable | Source | Description |
|----------|--------|-------------|
| `task_ids` | CLI argument | List of task IDs to process |
| `task_file` | CLI argument | Relative path to task file |
| `quality_command` | `quality_gates.all` or `"just"` | Command to run all quality checks |
| `format_command` | `hive_mind.format_command` | Code formatting command (default: `"just format"`) |
| `code_review_enabled` | `hive_mind.code_review_enabled` | Whether to include PR review loop |
| `max_review_rounds` | `hive_mind.max_review_rounds` | Max iterations on review feedback |
| `auto_merge` | `hive_mind.auto_merge` | Whether to merge after approval |
| `duplication_check` | `hive_mind.duplication_check` | Include duplication detection pass |
| `cleanup_pass` | `hive_mind.cleanup_pass` | Include dead code/formatting cleanup |
| `security_scan` | `hive_mind.security_scan` | Include security analysis pass |
| `coverage_check` | `hive_mind.coverage_check` | Include test coverage verification |
| `file_size_check` | `hive_mind.file_size_check` | Include file size optimization check |
| `quality_gates` | Built from `QualityGatesConfig` | Formatted quality gate commands |
| `sprint_record` | Sprint config if active | Path to sprint record for status updates |
