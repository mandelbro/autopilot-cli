# Autopilot CLI: Product Requirements Document

**Version**: 1.0
**Date**: 2026-03-06
**Status**: Draft
**Authors**: Synthesized from technical discovery (Norwood) and UX design (Ive)

---

## 1. Executive Summary

Autopilot CLI is a standalone Python CLI tool that generalizes the RepEngine autopilot (a battle-tested, project-specific AI agent orchestration daemon) into a general-purpose autonomous development orchestrator. It lets technical architects define high-level`  ` vision and architectural decisions, then have long-running projects implemented autonomously by coordinated AI agent teams across multiple claude-flow/hive-mind sessions. The tool provides an interactive REPL, layered anti-pattern enforcement across 11 categories, sprint-based task management with velocity tracking, and multi-project orchestration with per-project daemons and global resource limits. Think `claude-flow` meets `pm2` meets a really opinionated tech lead.

---

## 2. Problem Statement

The RepEngine autopilot works. It has survived hundreds of cycles, coordinated four agent roles across four concurrent project checkouts, and shipped real PRs. But it is welded to RepEngine. Every new project that wants autonomous development needs to fork the entire `autopilot/` directory, adapt the config, rewrite the agent prompts, and hope nothing breaks.

### Specific Pain Points

**No project initialization story.** You cannot `autopilot init` in a new repo and get a working setup. Everything is manual: create `board/`, create `agents/`, write `config.yaml`, wire up justfile targets.

**No interactive mode.** The CLI is fire-and-forget: `plan`, `execute`, `status`. There is no REPL for exploring project state, managing sessions, or interactively dispatching agents. The human workflow is "edit YAML, run command, read log files."

**No discovery/task workflow integration.** Planning new work means opening a separate Claude Code session with the Norwood agent prompt, then manually creating task files following the tasks-workflow spec. Nothing connects discovery output to task creation to sprint planning to autonomous execution.

**Anti-pattern enforcement is config-level only.** Research identifies 11 enforcement categories and 5 enforcement layers, but the autopilot only implements one: the quality gate suffix appended to hive-mind objectives. There is no pre-commit hook management, no CI template generation, no real-time agent guardrails, no metrics collection.

**No cross-project orchestration intelligence.** The PL sees all projects, but there is no velocity tracking, no sprint planning, no capacity modeling. The PL reads task indexes and dispatches work based on priority ordering alone.

---

## 3. Vision & Goals

### Vision

A single command (`autopilot init`) transforms any codebase into an autonomously-managed project. The technical architect provides vision and makes architectural decisions. The tool handles everything else: planning, estimation, agent orchestration, quality enforcement, progress tracking, and reporting.

### Goals

| Goal | Measurable Outcome |
|------|-------------------|
| **Zero-to-autonomous in under 30 minutes** | From `autopilot init` to first completed autonomous cycle in < 30 min |
| **Project-agnostic** | Support Python, TypeScript, and hybrid projects via pluggable templates |
| **Maintain RepEngine cycle success rate** | >= 85% cycle success rate on new projects within 2 weeks of setup |
| **Reduce human intervention** | < 5 human interventions per 100 autonomous cycles (excluding architecture decisions) |
| **Enforce code quality at every layer** | All 11 anti-pattern categories covered across 5 enforcement layers |
| **Sprint-level predictability** | Velocity forecasting within 20% accuracy after 3 sprints |
| **Multi-project support** | Run 3+ projects concurrently with isolated daemons and shared resource limits |

### Non-Goals

- **IDE integration.** Autopilot is a CLI/REPL tool. Editor plugins are out of scope for v1.
- **Cloud hosting.** All execution is local. No SaaS component.
- **Non-Claude AI providers.** The orchestration layer assumes Claude CLI and claude-flow. Abstracting over multiple providers adds complexity without current demand.
- **Team collaboration.** v1 is single-user. Multi-user coordination (shared dashboards, role-based access) is deferred.

---

## 4. Target Users

### Primary: Technical Architects

Mid-to-senior engineers who own the technical vision for one or more projects. They make architecture decisions, review code at the design level, and want to delegate implementation to autonomous agents without losing control.

**Characteristics:**
- Comfortable with terminal-based tools (use `gh`, `kubectl`, `lazygit` daily)
- Have opinions about code quality and enforce them
- Work across multiple projects simultaneously
- Want to set direction, not micromanage individual tasks
- Trust automation when it is transparent and reversible

**Key workflow:** Define vision -> review discovery -> approve task plan -> start autonomous session -> answer agent questions -> review decisions -> merge PRs.

### Secondary: Engineering Managers

Managers who want visibility into autonomous development progress without needing to operate the tool directly.

**Characteristics:**
- Need sprint velocity and quality trend reports
- Want to understand capacity and forecast timelines
- Care about risk assessment (what is the agent success rate? where are the blockers?)

**Key workflow:** `autopilot report velocity` and `autopilot report quality` for sprint reviews.

---

## 5. User Journeys

### Journey 1: Initialize a New Project

**Actor:** Technical architect with an existing codebase.

```
1. $ cd ~/Projects/my-saas-app
2. $ autopilot init
3. Wizard auto-detects tech stack (TypeScript, React, PostgreSQL)
4. Architect confirms stack, names the project, selects quality standards
5. Tool creates .autopilot/ with config, agent prompts, board files
6. Tool updates project tooling (adds lint rules, pre-commit hooks)
7. Architect reviews .autopilot/config.yaml, adjusts agent count and models
8. Project registered in ~/.autopilot/projects.yaml
```

**Outcome:** Project is ready for discovery and autonomous execution.
**Time:** Under 2 minutes.

### Journey 2: Plan a Feature

**Actor:** Technical architect with an initialized project.

```
1. $ autopilot (enters REPL)
2. /plan discover
3. Tool spawns Norwood discovery session, analyzes codebase
4. Discovery document saved to .autopilot/discoveries/
5. Architect reviews and edits discovery document
6. /plan tasks -- generates task breakdown from discovery
7. Architect reviews tasks, reorders priorities, removes irrelevant items
8. /plan estimate -- Shelly agent estimates complexity (Fibonacci points)
9. Architect reviews estimates, adjusts outliers
10. /plan enqueue -- moves approved tasks to execution queue
```

**Outcome:** Backlog of estimated, prioritized tasks ready for autonomous execution.
**Time:** 30-60 minutes (dominated by human review).

### Journey 3: Run Autonomous Execution

**Actor:** Technical architect with enqueued tasks.

```
1. /session start
2. Daemon launches, PL reads project state, generates dispatch plan
3. Agents execute in parallel (EM via hive-mind, TA/PD via Claude CLI)
4. REPL prompt updates with running agent count
5. Architect checks /dashboard periodically (or watches with /watch)
6. Agent asks a question -> architect answers via /ask <id>
7. Agent proposes high-risk decision -> architect reviews via /review <id>
8. Cycle completes, reports generated, next cycle begins
9. /session pause when architect needs to do manual work
10. /session resume to continue
```

**Outcome:** PRs created, tasks completed, velocity tracked.
**Time:** Hours to days (autonomous, with periodic human check-ins).

### Journey 4: Monitor and Review

**Actor:** Technical architect checking on a running session.

```
1. $ autopilot (enters REPL, sees session state in prompt)
2. Press Enter -> dashboard shows agents, tasks, attention items
3. /watch -> full-screen TUI with live agent activity streams
4. Press 1 -> focus on agent alpha, see timestamped activity log
5. Press a -> jump to question queue, answer pending question
6. Press q -> back to REPL
7. /report velocity -> sprint velocity chart with forecast
8. /report quality -> enforcement trend analysis
```

**Outcome:** Full visibility into autonomous work without disrupting agents.

### Journey 5: Multi-Project Orchestration

**Actor:** Technical architect managing 3 projects.

```
1. $ autopilot (enters REPL)
2. /project list -> see all projects with status, session state, attention items
3. /project switch frontend-app -> change active context
4. /session start -> second daemon launches within global resource limits
5. /project list -> both projects running, one flagged for attention
6. /report summary -> aggregated metrics across all projects
```

**Outcome:** Multiple projects running concurrently with isolated execution and unified visibility.

---

## 6. Product Requirements

### P0: Must Have for v1.0

#### 6.1 CLI Framework & REPL

| ID | Requirement | Details |
|----|------------|---------|
| P0-01 | Typer-based CLI with verb-noun command hierarchy | Consistent with `gh`, `kubectl` patterns. All subcommands work as both CLI calls and REPL slash commands. |
| P0-02 | Interactive REPL with prompt-toolkit | Persistent session with command history, tab completion, and context-sensitive prompt showing project name, agent count, and attention items. |
| P0-03 | Rich output formatting | Tables, panels, progress bars, markdown rendering via Rich library. No raw `print()` statements. |
| P0-04 | Three input modes | Slash commands (predictable, scriptable), natural language (exploration), quick actions (single-key responses in context). |
| P0-05 | Shell completions | Bash, zsh, and fish completions generated from Typer definitions. |

#### 6.2 Project Management

| ID | Requirement | Details |
|----|------------|---------|
| P0-06 | `autopilot init` wizard | Auto-detect tech stack, scaffold `.autopilot/` directory with config, agent prompts, board files. Support `--type` flag for Python/TypeScript/hybrid. |
| P0-07 | `.autopilot/` directory convention | All autopilot infrastructure lives in a dot-directory inside the project root. Portable, versionable, discoverable. |
| P0-08 | Global project registry | `~/.autopilot/projects.yaml` tracks all initialized projects. `autopilot project list` works from any directory. |
| P0-09 | Project scaffolding templates | Jinja2 templates for Python projects (agent prompts, config, board files, enforcement config). |
| P0-10 | `project list`, `show`, `switch`, `config` | Core project management commands. |

#### 6.3 Task Management

| ID | Requirement | Details |
|----|------------|---------|
| P0-11 | Task file parsing | Read and write RepEngine-format markdown task files (tasks-index.md + tasks-N.md). |
| P0-12 | `task create` | Interactive task creation with ID, description, priority, sprint points, dependencies, acceptance criteria. |
| P0-13 | `task list` | Task board display with filtering by status, priority, sprint. |
| P0-14 | Sprint planning | `task sprint plan` allocates tasks to sprints using velocity-based capacity. `task sprint close` records velocity. |
| P0-15 | Fibonacci estimation | Sprint points use Fibonacci sequence (1, 2, 3, 5, 8, 13, 21). |

#### 6.4 Daemon & Scheduler

| ID | Requirement | Details |
|----|------------|---------|
| P0-16 | Per-project daemon | Each project runs its own daemon with separate PID file and log directory. |
| P0-17 | Cycle orchestration | Scheduler runs planning-dispatch-execution-reporting cycles with configurable intervals. |
| P0-18 | Agent invocation | Spawn Claude CLI subprocesses with clean environment, retry logic, and timeout handling. Evolved from RepEngine `agent.py`. |
| P0-19 | Hive-mind integration | Initialize and manage claude-flow hive-mind sessions for EM agent. Version-pinned in config. |
| P0-20 | Circuit breaker | Abort remaining dispatches after N consecutive agent timeouts. |
| P0-21 | Usage tracking | Daily/weekly cycle counts against Claude Max plan limits. |
| P0-22 | Session management | `session start/stop/pause/resume/status/log`. Track sessions in SQLite. |
| P0-23 | `start/stop/pause/resume/cycle` | Core daemon lifecycle commands. |

#### 6.5 Coordination & Reporting

| ID | Requirement | Details |
|----|------------|---------|
| P0-24 | Document-mediated coordination | Board files (project-board.md, question-queue.md, decision-log.md) for agent-human and agent-agent communication. |
| P0-25 | Cycle reports | Per-cycle markdown reports with dispatch outcomes, duration, and agent results. |
| P0-26 | Daily summary | Aggregated daily view for PL context in subsequent cycles. |
| P0-27 | Decision log with rotation | Audit trail of all decisions (human and auto-approved) with archival. |

#### 6.6 Data Architecture

| ID | Requirement | Details |
|----|------------|---------|
| P0-28 | Hybrid storage | Flat files (markdown, YAML) for human-readable coordination. SQLite for analytics, session tracking, and metrics. |
| P0-29 | SQLite schema | Tables for projects, sessions, cycles, dispatches, enforcement_metrics, velocity. WAL mode for concurrent access. |
| P0-30 | YAML configuration | `.autopilot/config.yaml` per project, `~/.autopilot/config.yaml` for global defaults. Pydantic model validation. |

### P1: Should Have for v1.x

#### 6.7 Discovery Workflow

| ID | Requirement | Details |
|----|------------|---------|
| P1-01 | `plan discover` | Spawn Norwood discovery session as background Claude instance scoped to project. Stream progress in REPL. |
| P1-02 | `plan tasks` | Convert discovery document into structured task files with priorities and dependencies. |
| P1-03 | `plan estimate` | Launch Shelly estimation agent for Fibonacci point estimation with confidence and risk scoring. |
| P1-04 | `plan enqueue` | Move approved, estimated tasks into the execution queue. |
| P1-05 | Planning pipeline UX | Sequential Discover -> Tasks -> Estimate -> Enqueue flow with human review between each step. |

#### 6.8 Anti-Pattern Enforcement Engine

| ID | Requirement | Details |
|----|------------|---------|
| P1-06 | Enforcement engine architecture | Orchestration layer that coordinates all 5 enforcement layers. |
| P1-07 | Layer 1: Editor-time config | Generate ruff/eslint/pyright config additions for anti-pattern detection. |
| P1-08 | Layer 2: Pre-commit hooks | Install and configure lefthook/husky with enforcement rules. Include block-no-verify and detect-secrets. |
| P1-09 | Layer 3: CI/CD templates | Generate GitHub Actions workflow templates with quality gate jobs. |
| P1-10 | Layer 4: Agent guardrails | PreToolUse/PostToolUse hook integration for real-time agent behavior control. |
| P1-11 | Layer 5: Protected regions | Hash-based protection markers for critical code. Change detection and PR-level alerts. |
| P1-12 | 11-category rule coverage | Rules for: infrastructure duplication, ignored conventions, over-engineering, security vulnerabilities, error handling, dead code, type safety, test anti-patterns, excessive comments, deprecated APIs, async misuse. |
| P1-13 | `enforce setup/check/report` | Setup all layers, run checks with violation reporting, generate trend analysis. |
| P1-14 | Configurable quality gates | Per-project-type gate definitions (commands for lint, type check, test) injected into hive-mind objectives. |
| P1-15 | Enforcement metrics to SQLite | Track violation counts per category over time for trend analysis. |

#### 6.9 Sprint Planning & Velocity

| ID | Requirement | Details |
|----|------------|---------|
| P1-16 | Velocity tracking | Record points completed per sprint. Rolling average of last 5 sprints for capacity forecasting. |
| P1-17 | `report velocity` | Sprint velocity chart with historical data and forecast. |
| P1-18 | `report quality` | Enforcement trend analysis: violation density, top categories, week-over-week improvement. |

### P2: Nice to Have for v2.x

#### 6.10 Multi-Project Orchestration

| ID | Requirement | Details |
|----|------------|---------|
| P2-01 | Global resource broker | `max_concurrent_daemons` and `max_concurrent_agents` limits across all projects. |
| P2-02 | Per-project usage limits | Per-project daily cycle limits and priority weights for resource allocation. |
| P2-03 | Cross-project reporting | Aggregated velocity and quality metrics across all projects. |
| P2-04 | Multi-project dashboard | Overview showing all projects with status, session state, and attention items. |

#### 6.11 Watch Mode TUI

| ID | Requirement | Details |
|----|------------|---------|
| P2-05 | `/watch` full-screen TUI | Live-updating agent activity panels. Keyboard-driven navigation (Tab to cycle agents, 1-5 to focus, p to pause). |
| P2-06 | Focused agent view | Timestamped activity log for a single agent with search and decision history. |
| P2-07 | Watch mode shortcuts | Single-key actions: `a` for questions, `d` for decisions, `p` for pause, `q` for exit. |

#### 6.12 Advanced Features

| ID | Requirement | Details |
|----|------------|---------|
| P2-08 | Natural language input | Parse natural language queries in REPL ("show me what agents are working on", "pause everything"). |
| P2-09 | Event-driven scheduler | Trigger cycles on file changes, git pushes, or manual dispatch (alongside interval-based). |
| P2-10 | Custom template support | User-level templates at `~/.autopilot/templates/` that extend built-in templates. |
| P2-11 | Workflow hooks | Pre/post cycle and dispatch hooks defined in config (shell commands). |
| P2-12 | TypeScript project template | Full template parity with Python (agent prompts, eslint config, pre-commit hooks). |
| P2-13 | Hybrid project template | Support for monorepos with mixed Python/TypeScript codebases. |
| P2-14 | `autopilot migrate` | Convert existing RepEngine autopilot layout to `.autopilot/` format. |
| P2-15 | Custom enforcement rules | Load project-specific Python rule classes from `.autopilot/enforcement/rules/`. |
| P2-16 | OS-level notifications | macOS/Linux notifications for critical and action-tier events when terminal is not in focus. |
| P2-17 | `--json` flag on all list commands | Scriptable output for CI/CD integration and external tooling. |
| P2-18 | `report --web` | Open browser-based dashboard for complex visualizations. |

---

## 7. UX Requirements

### Core Design Principle: Conversation, Not Operation

The user is a technical architect directing a team. The CLI should feel like talking to a capable tech lead, not like operating a control panel. Every interaction should reduce cognitive load, surface what matters, and stay out of the way when work is flowing.

### Design Values

| Value | What It Means in Practice |
|-------|--------------------------|
| **Trust through transparency** | Every agent action is traceable, explainable, and reversible. The architect never wonders "what just happened?" |
| **Attention is sacred** | Only interrupt for things that genuinely need human judgment. Default state: quiet competence. |
| **Speed to insight** | "How is my project doing?" answered in under 2 seconds from any state. |
| **Expert-friendly** | Support both guided flows (wizards) and direct commands (flags). Never force an expert through a wizard. |
| **Recoverable by default** | Every operation can be paused, resumed, undone, or abandoned. No one-way doors without explicit confirmation. |

### Information Hierarchy

Three levels of detail, accessible from any point in the application:

| Level | Name | Purpose | Trigger |
|-------|------|---------|---------|
| 0 | Prompt Line | What needs attention right now | Always visible |
| 1 | Dashboard | Project health at a glance | Enter on empty prompt, `/dashboard` |
| 2 | Detail Views | Deep inspection of any entity | `show` subcommands, `--verbose` flag |

### REPL Prompt Format

The prompt is context-sensitive and encodes real-time state:

```
autopilot >                                           # No project
autopilot [project-name] >                            # Project, no session
autopilot [project-name] (3 running) >                # Session healthy
autopilot [project-name] (3 running | ! 2 questions) > # Attention needed
autopilot [project-name] (paused) >                   # Session paused
```

Color coding: project name (cyan), running count (green), attention marker (yellow/amber), error state (red), paused (dim/gray).

### Dashboard Design

The default dashboard fits an 80x24 terminal with a two-column layout:

- **Left column:** Agent status (name, current task)
- **Right column:** Task progress (queued, in progress, done, blocked with bar charts)
- **Attention section:** Pending questions and reviews with direct action commands
- **Activity timeline:** 5 most recent events with timestamps
- **Metrics footer:** Quality stats (coverage, lint, types) and session stats (tasks completed, decisions, tokens)

Maximum content width: 72 characters.

### Notification Tiers

| Tier | Delivery | Examples |
|------|----------|---------|
| Critical | In-REPL + OS notification + terminal bell | Agent crashed, build broken, security vulnerability |
| Action | In-REPL + prompt badge | Question pending, review needed, decision blocked |
| Info | In-REPL (if idle), queryable via `/log` | Task completed, test passed, commit created |
| Silent | Queryable via `/log` only | Token usage, internal retries, routine operations |

Notifications batch between outputs. They never interrupt mid-typing and never scroll away user-requested output.

### Error Handling UX

- Long-running operations (> 2 seconds) show progress indicators with Ctrl+Z to background
- Agent failures show clear error messages, retry status, and multiple resolution paths
- Session recovery on restart: detect interrupted sessions, offer resume/fresh-start/report options
- Destructive operations require explicit confirmation (type project name)
- Connection failures auto-pause agents, save work-in-progress, auto-retry with backoff

### Accessibility

- All color-coded information has a non-color alternative (symbol, label, or position)
- Screen reader mode: plain text without box-drawing characters or animations
- High contrast mode: bold/normal weight instead of color
- All interactions keyboard-only (inherent in CLI)
- Timing is configurable: idle reminders and retry delays are not hardcoded

---

## 8. Technical Architecture

### Language & Stack

**Python 3.12+.** The existing RepEngine autopilot is 954 lines of tested, typed, production Python. The runtime manages subprocesses, PID files, and POSIX signals. Python's `subprocess`, `os`, and `signal` modules handle all of this natively. Rewriting in TypeScript would throw away battle-tested code for zero benefit.

**Core dependencies:**

| Package | Version | Purpose |
|---------|---------|---------|
| pydantic | >= 2.10 | Config and data model validation |
| pyyaml | >= 6.0 | YAML config parsing |
| structlog | >= 24.0 | Structured logging |
| typer | >= 0.15 | CLI command routing with auto-generated help |
| rich | >= 13.0 | Terminal output formatting (tables, panels, progress) |
| prompt-toolkit | >= 3.0 | REPL loop with history, completion, keybindings |
| jinja2 | >= 3.1 | Config and prompt template rendering |

No heavy frameworks. These are the standard Python CLI stack in 2026.

### Package Structure

```
autopilot-cli/
  src/autopilot/
    cli/              # Command layer (app, project, task, session, agent,
                      #   discover, enforce, repl, display)
    core/             # Domain logic (config, models, project, task,
                      #   agent_registry, templates)
    orchestration/    # Execution engine (scheduler, daemon, dispatcher,
                      #   agent_invoker, hive, circuit_breaker, usage)
    enforcement/      # Anti-pattern engine (engine, precommit, ci,
                      #   guardrails, quality_gates, metrics, rules/)
    reporting/        # Analytics (cycle_reports, daily_summary, velocity,
                      #   quality, decision_log)
    coordination/     # Agent communication (board, questions,
                      #   announcements, decisions)
    utils/            # Shared (subprocess, process, sanitizer, paths, git)
  templates/          # Project scaffolding (python/, typescript/, hybrid/)
  tests/              # Mirror of src/ structure
```

### Agent Orchestration Flow

```
Scheduler (Python) --> PL (Claude CLI) --> Dispatch Plan (JSON)
                                              |
                            +-----------------+-----------------+
                            |                 |                 |
                         EM (hive-mind)    TA (Claude CLI)   PD (Claude CLI)
                            |                 |                 |
                            +-----------------+-----------------+
                                              |
                                     Reporting (Python)
```

1. **Scheduler** owns the lifecycle: creates branches, manages cycles, enforces limits.
2. **PL (Project Leader)** reads project state and generates a structured dispatch plan.
3. **EM (Engineering Manager)** executes implementation via claude-flow hive-mind with worker agents.
4. **TA (Technical Architect)** handles architecture review and design tasks.
5. **PD (Product Director)** handles product-level decisions and documentation.
6. **Reporting** generates cycle reports, updates metrics, and rotates logs.

### Dynamic Agent Registry

Any `.md` file placed in `.autopilot/agents/` becomes an available agent role. The PL prompt is dynamically assembled with the current agent roster. Custom roles (security-reviewer, performance-tester, documentation-writer) require no code changes.

### Inter-Agent Communication

Document-mediated via flat files. Agents read fresh state at the start of each invocation. No message queues, no coordination protocols, no stale caches.

| Channel | Direction | Medium | Purpose |
|---------|-----------|--------|---------|
| Project Board | PL <-> All | Markdown | Sprint status, active work, blockers |
| Question Queue | Agent -> Human | Markdown | Decisions requiring human input |
| Decision Log | PL -> All | Markdown | Recorded decisions with rationale |
| Announcements | Human -> All | Markdown | Policy changes, priority shifts |
| Daily Summary | Scheduler -> PL | Markdown | Cycle history for PL context |
| Dispatch Plan | PL -> Scheduler | JSON | Structured agent instructions |

### Error Recovery

Preserved from RepEngine (battle-tested):
- Transient API errors: exponential backoff (2 retries, 45s/90s)
- Agent timeouts: circuit breaker pattern
- Model fallback: opus 4.6 -> opus 4.5 -> sonnet
- Empty output detection: guard against Claude CLI short-circuiting
- Stale lock recovery: PID liveness + TTL check

New for Autopilot CLI:
- Session recovery: detect orphaned Claude processes on daemon restart
- Partial dispatch recovery: resume from last successful dispatch
- Git state recovery: validate clean working tree and correct branch before each cycle

### Distribution

```bash
# Recommended
uv tool install autopilot-cli

# Alternative
pipx install autopilot-cli

# From source
uv tool install git+https://github.com/org/autopilot-cli
```

Published to PyPI with versioned releases.

---

## 9. Anti-Pattern Enforcement

### The Problem

Research shows AI coding agents produce specific, measurable anti-patterns at significantly higher rates than human developers. Infrastructure duplication occurs in 80-90% of agent sessions. Convention violations approach 100%. Security vulnerabilities appear at 36-62% rates. Test anti-patterns in 40-70% of generated tests. These are not edge cases; they are the default behavior.

### The 11 Categories

| # | Category | Agent Prevalence | Detection Method |
|---|----------|-----------------|-----------------|
| 1 | Infrastructure duplication | 80-90% | AST analysis, import graph |
| 2 | Ignored conventions | 90-100% | Linter rules, naming regex |
| 3 | Over-engineering | 80-90% | Cognitive complexity, abstraction depth |
| 4 | Security vulnerabilities | 36-62% | SAST tools, detect-secrets |
| 5 | Error handling gaps | ~2x human rate | Pattern matching, coverage analysis |
| 6 | Dead code | Variable | Tree-shaking analysis, import tracing |
| 7 | Type safety violations | Variable | Strict type checker (pyright/tsc) |
| 8 | Test anti-patterns | 40-70% | Test structure analysis, assertion quality |
| 9 | Excessive comments | 90-100% | Comment density analysis, content heuristics |
| 10 | Deprecated APIs | Variable | API version checking, deprecation warnings |
| 11 | Async misuse | 2x human | Async pattern analysis, event loop inspection |

### The 5 Enforcement Layers

Each layer catches different problems at different points in the development pipeline:

**Layer 1: Editor-time configuration.** Generate ruff/eslint/pyright config additions that catch anti-patterns during agent code generation. This is the cheapest enforcement point. Most issues are flagged before any commit.

**Layer 2: Pre-commit hooks.** Install lefthook with enforcement rules. Include `block-no-verify` (prevent agents from bypassing hooks) and `detect-secrets` for credential scanning. This catches anything that slips past the editor.

**Layer 3: CI/CD pipeline.** Generate GitHub Actions workflow templates with quality gate jobs, coverage thresholds, and complexity limits. This is the backstop: nothing merges without passing.

**Layer 4: Real-time agent guardrails.** PreToolUse/PostToolUse hook integration that blocks dangerous operations (deleting protected files, installing unauthorized dependencies) and injects warnings during agent execution.

**Layer 5: Protected code regions.** Hash-based protection markers in critical code (auth logic, payment processing, data migration). Change detection triggers PR-level alerts and requires explicit human approval.

### Integration with Autonomous Pipeline

The enforcement engine is not a separate tool to run manually. It is baked into the autonomous pipeline:

1. **At init:** `autopilot init` configures all 5 layers for the detected project type.
2. **At planning:** Discovery documents include enforcement baseline analysis.
3. **At execution:** Quality gates are injected into every hive-mind objective. Agent prompts include enforcement context.
4. **At reporting:** Enforcement metrics are collected per cycle and stored in SQLite for trend analysis.
5. **On demand:** `autopilot enforce check` runs the full suite. `autopilot enforce report` shows trends.

---

## 10. Data Architecture

### Design Decision: Flat Files + SQLite

Flat files for things agents and humans read directly. SQLite for things the tool queries and aggregates.

### Flat Files (Human-Readable, Git-Versionable)

| File Type | Location | Purpose |
|-----------|----------|---------|
| Board files | `.autopilot/board/` | project-board.md, question-queue.md, decision-log.md |
| Agent prompts | `.autopilot/agents/` | One `.md` per agent role |
| Task files | `.autopilot/tasks/` | tasks-index.md + tasks-N.md (RepEngine format) |
| Cycle reports | `.autopilot/board/cycle-reports/` | Per-cycle markdown |
| Config | `.autopilot/config.yaml` | Project configuration |
| Discoveries | `.autopilot/discoveries/` | Discovery documents |

These files must remain human-readable. Agents read and write them directly. They are committed to version control (except `state/` which is gitignored).

### SQLite (Analytics, Session Tracking, Metrics)

Located at `~/.autopilot/autopilot.db` (global). WAL mode enabled for concurrent access from multiple daemons.

**Tables:**

| Table | Purpose | Write Frequency |
|-------|---------|----------------|
| `projects` | Project registry with config hash | On init/config change |
| `sessions` | Session lifecycle tracking | On session start/stop |
| `cycles` | Cycle outcomes (status, duration, dispatch counts) | Once per cycle |
| `dispatches` | Per-dispatch results (agent, action, status, duration) | Per dispatch |
| `enforcement_metrics` | Violation counts per category over time | Per enforcement check |
| `velocity` | Sprint points planned vs. completed | Per sprint close |

**Why SQLite, not more JSON files:** "Show me the timeout rate for the EM agent across all projects over the last 30 days" is one SQL query. With JSON files, it is a script. After 1,000 cycles with 4 dispatches each, the dispatches table has ~4,000 rows. That is nothing for SQLite. The equivalent flat-file approach would be 4,000 JSON files or one unwieldy mega-file.

### Configuration Hierarchy

```
~/.autopilot/config.yaml     # Global defaults (models, usage limits, display)
.autopilot/config.yaml        # Project-specific (overrides global)
CLI flags                      # Per-invocation (overrides project)
```

---

## 11. Success Metrics

### Technical Health

| Metric | Target | Measurement |
|--------|--------|-------------|
| Cycle success rate | >= 85% | `cycles` table: COMPLETED / total |
| Agent timeout rate | <= 10% | `dispatches` table: timeout / total |
| SQLite write failures | 0 | Daemon log monitoring |
| Dispatch plan parse success | >= 95% | `dispatches` table: parsed / attempted |
| Hive-mind session success rate | >= 80% | Session records |

### Code Quality (of Autopilot CLI itself)

| Metric | Target | Tool |
|--------|--------|------|
| Pyright strict mode | Zero errors | pyright |
| Ruff extended ruleset | Zero warnings | ruff |
| Test coverage (core/, orchestration/) | >= 90% | pytest-cov |
| Test coverage (cli/) | >= 80% | pytest-cov |

### User Experience

| Metric | Target | Measurement |
|--------|--------|-------------|
| Time from `init` to working setup | < 2 minutes | Manual testing |
| Time from `init` to first autonomous cycle | < 30 minutes | End-to-end test |
| Migration from RepEngine layout | < 5 minutes | Manual testing |
| Dashboard render time | < 2 seconds | Profiling |
| Human interventions per 100 cycles | < 5 (excl. architecture decisions) | Decision log analysis |

### Velocity Accuracy

| Metric | Target | Measurement |
|--------|--------|-------------|
| Forecast accuracy (after 3 sprints) | Within 20% of actual | `velocity` table comparison |
| Points completed per sprint trend | Increasing or stable | `velocity` table |
| Task carry-over rate | < 20% per sprint | Sprint close data |

---

## 12. Implementation Phases

### Phase 1: Foundation (3-5 sprints, ~40-65 story points)

**Goal:** Working CLI with project init and basic REPL. No autonomous execution.

**Deliverables:**
- Package scaffolding (pyproject.toml, src layout, test infrastructure)
- Core config model (evolved from RepEngine config.py)
- Core data models (evolved from RepEngine models.py)
- `autopilot init` with Python project template
- `autopilot project list/show/switch/config`
- REPL skeleton with prompt-toolkit (context-sensitive prompt, slash commands, tab completion)
- Rich display helpers (tables, panels, progress)
- SQLite schema and migration infrastructure
- Shared utilities (subprocess, process, sanitizer, paths, git)

**Exit criteria:** `autopilot init --type python --name test-project` creates a valid `.autopilot/` directory. `autopilot` launches a REPL with context-sensitive prompt. `autopilot project list` shows registered projects.

### Phase 2: Task Management (2-3 sprints, ~25-40 story points)

**Goal:** Full task lifecycle, manual execution only.

**Deliverables:**
- Task file parsing (RepEngine markdown format)
- `task create`, `task list`, `task create --from-discovery`
- Sprint planning with velocity tracking
- `task sprint plan/close`
- Fibonacci estimation support
- SQLite velocity storage

**Exit criteria:** Full task create -> estimate -> sprint plan -> track lifecycle. Tasks are valid RepEngine-format markdown.

### Phase 3: Autonomous Execution (3-5 sprints, ~50-80 story points)

**Goal:** The daemon runs cycles, dispatches agents, and produces PRs.

**Deliverables:**
- Agent invoker (evolved from RepEngine agent.py)
- Dispatch parser (reuse RepEngine dispatch.py)
- Scheduler with cycle orchestration (evolved from RepEngine scheduler.py)
- Daemon with signal handling (evolved from RepEngine daemon.py)
- Hive-mind integration (evolved from RepEngine hive.py)
- Circuit breaker and usage tracking
- Session management (start/stop/pause/resume/list/attach)
- Cycle reports, daily summary, decision log
- Dashboard (80x24 two-column layout)
- `start/stop/pause/resume/cycle/plan/execute`

**Exit criteria:** `autopilot start` launches a daemon that runs cycles. Dispatches produce real Claude CLI invocations. Cycle reports are written. Dashboard shows live session state.

### Phase 4: Enforcement Engine (2-3 sprints, ~30-45 story points)

**Goal:** All 5 enforcement layers operational.

**Deliverables:**
- Enforcement engine architecture
- Layer 1: Editor config generation (ruff, eslint, pyright)
- Layer 2: Pre-commit hook setup (lefthook, block-no-verify)
- Layer 3: CI/CD template generation (GitHub Actions)
- Layer 4: Agent guardrail integration (PreToolUse hooks)
- Layer 5: Protected code region support
- `enforce setup/check/report`
- Metrics collection to SQLite
- Quality gate prompt generation for hive-mind

**Exit criteria:** `autopilot enforce setup` configures all 5 layers for Python projects. `autopilot enforce check` reports violations by category. Quality gates are injected into hive-mind objectives.

### Phase 5: Discovery & Polish (2-3 sprints, ~25-40 story points)

**Goal:** End-to-end workflow from discovery to autonomous execution.

**Deliverables:**
- Norwood discovery agent prompt template
- `plan discover`, `plan tasks`, `plan estimate`, `plan enqueue`
- Discovery-to-task conversion pipeline
- Shelly estimation agent integration
- TypeScript project template
- `autopilot migrate` (RepEngine layout conversion)
- Shell completions (bash, zsh, fish)
- Documentation

**Exit criteria:** `plan discover` -> discovery doc -> `plan tasks` -> task files -> `session start` -> autonomous execution produces PRs.

### Phase 6: Multi-Project & Advanced (2-3 sprints, ~30-50 story points)

**Goal:** Production-ready multi-project orchestration.

**Deliverables:**
- Global resource broker (concurrent daemon/agent limits)
- Per-project usage limits and priority weights
- Cross-project reporting dashboard
- Watch mode TUI (`/watch`)
- Event-driven scheduler triggers
- Custom template support
- Workflow hooks (pre/post cycle/dispatch)
- Hybrid project template

**Exit criteria:** Multiple projects run concurrent daemons within global resource limits. Watch mode displays live agent activity. Velocity and quality metrics aggregate across projects.

### Total Estimate

| Phases | Sprints | Story Points |
|--------|---------|-------------|
| 1-3 (working autonomous CLI) | 8-13 | 115-185 |
| 4-6 (full feature set) | 6-9 | 85-135 |
| **Total** | **14-22** | **200-320** |

---

## 13. Risks & Mitigations

### High Risk

| Risk | Probability | Impact | Mitigation | Detection |
|------|------------|--------|------------|-----------|
| **Agent prompt quality for new projects** | High | Major: poor prompts waste cycles, produce bad code | Ship battle-tested templates from RepEngine. Include prompt tuning guide. Add `agent test <role>` for dry-run dispatch evaluation. | Dispatch success rate per agent role drops below threshold. |
| **claude-flow version compatibility** | High | Major: hive-mind sessions fail silently or produce garbage | Version-pin in config. Startup health check. Compatibility matrix. Version-specific error handling. | Hive session failure rate spike. |

### Medium Risk

| Risk | Probability | Impact | Mitigation | Detection |
|------|------------|--------|------------|-----------|
| **SQLite concurrency under multiple daemons** | Medium | Data loss: lost metrics, corrupted sessions | WAL mode. Retry-with-backoff for writes. Small, infrequent write operations (per-cycle, not per-dispatch). | SQLite busy errors in daemon logs. |
| **Template drift from upstream** | Medium | Outdated enforcement configs for new projects | Version templates. `enforce update` command refreshes from latest. "Last-updated" field in generated configs. | Periodic comparison against latest template. |
| **Scope creep in enforcement engine** | Medium | Delayed delivery of Phases 4-5 | Start with Layer 1 (editor config) and Layer 2 (pre-commit) only. Layers 3-5 are P1 stretch. | Phase 4 exceeds 3 sprint estimate. |

### Low Risk

| Risk | Probability | Impact | Mitigation | Detection |
|------|------------|--------|------------|-----------|
| **Adoption resistance from RepEngine workflow** | Low | Wasted development effort | `autopilot migrate` command. Backward compatibility for first releases. | Usage metrics after launch. |
| **REPL complexity exceeding prompt-toolkit capabilities** | Low | UX degradation for advanced features | Natural language input and watch mode are P2. Core REPL (slash commands + tab completion) is well within prompt-toolkit's capabilities. | User feedback during Phase 1 testing. |

---

## 14. Open Questions

### Architecture Decisions Pending

| # | Question | Options | Leaning | Depends On |
|---|----------|---------|---------|------------|
| 1 | **How should natural language input be processed?** | (a) Local intent parsing with regex/keyword matching, (b) Route to Claude for interpretation, (c) Hybrid: common patterns parsed locally, complex queries to Claude | (c) Hybrid | P2 scope. Defer until REPL usage patterns are clear. |
| 2 | **Should the watch mode TUI use Textual or raw Rich Live?** | (a) Textual (full TUI framework), (b) Rich Live Display with custom keybindings | (b) Rich Live | Textual adds a heavy dependency. Rich Live covers the 80% case. |
| 3 | **How should cross-project intelligence work?** | (a) Global scheduler layer that reallocates resources, (b) Per-project daemons with no cross-project awareness, (c) Shared context in PL prompts | (b) for v1, (a) for v2 | Multi-project usage patterns. |
| 4 | **Should we support non-Claude agents?** | (a) Abstract the agent invoker for multiple providers, (b) Claude-only | (b) Claude-only for v1 | Market demand for multi-provider. |
| 5 | **How should the planning pipeline handle large codebases (>100K lines)?** | (a) Incremental discovery (directory-by-directory), (b) Pre-filter with lightweight analysis, (c) Increase context window budget | Unknown | Testing with large repos in Phase 5. |

### Product Decisions Pending

| # | Question | Context |
|---|----------|---------|
| 6 | **Should autopilot have an `--approve-all` mode for fully unattended execution?** | Some users want zero human intervention. This conflicts with the "trust through transparency" design value but could be gated behind explicit opt-in. |
| 7 | **How aggressive should auto-approval policies be by default?** | Currently proposed: auto-approve low-risk decisions (formatting, renaming, test fixes). Should structural refactoring or dependency additions also auto-approve? |
| 8 | **Should there be a public plugin registry for custom agent roles?** | The dynamic agent registry makes sharing agent prompts trivial. A community registry could accelerate adoption but adds maintenance burden. |
| 9 | **What is the upgrade story for config schema changes between versions?** | As the tool evolves, `.autopilot/config.yaml` schema will change. Need a migration strategy (versioned configs, auto-migration, or manual). |

---

## 15. Appendices

### Source Documents

| Document | Location | Author | Content |
|----------|----------|--------|---------|
| Technical Discovery | `./discovery.md` | Norwood | Architecture, implementation plan, ADRs, risk register, package structure, code analysis |
| UX Design | `./ux-design.md` | Ive | Design philosophy, REPL experience, dashboard design, workflow UX, notifications, accessibility |

### Research References

| Document | Location |
|----------|----------|
| Anti-pattern enforcement research | `/Users/montes/Library/Mobile Documents/com~apple~CloudDocs/Projects/AI_Projects/Research/ai-agent-anti-patterns-enforcement.md` |
| Anti-pattern field guide | `/Users/montes/Library/Mobile Documents/com~apple~CloudDocs/Projects/AI_Projects/Research/ai-agent-anti-patterns-field-guide.md` |
| RepEngine autopilot source | `/Users/montes/AI/RepEngine/rep-engine-service/autopilot/` |
| Python rewrite discovery | `/Users/montes/AI/RepEngine/rep-engine-service/docs/discovery/autopilot-python-rewrite-discovery.md` |

### Key Architecture Decision Records (from Discovery)

| ADR | Decision | Rationale |
|-----|----------|-----------|
| ADR-1 | Distribute via PyPI | Versioned releases, dependency resolution, `uv tool install` recommended |
| ADR-2 | `.autopilot/` inside project root | Follows `.github/`, `.vscode/` convention. Portable, versionable. |
| ADR-3 | `~/.autopilot/` for global state | Global config, project registry, SQLite database |
| ADR-4 | Per-project daemons | Isolation over cross-project intelligence. Stuck project A does not block project B. |
| ADR-5 | YAML configuration | Existing system uses YAML. Deep nesting is more natural than TOML. Supports comments. |
| ADR-6 | prompt-toolkit + Typer for REPL | prompt-toolkit for readline layer, Typer for command routing |
| ADR-7 | Subprocess-based claude-flow integration | No library-level integration to leverage. MCP tools require running inside a Claude session. |
