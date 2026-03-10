# Discovery: Parallel UAT Framework for Autopilot CLI

**Date**: 2026-03-10
**Author**: Norwood (Technical Discovery Agent)
**Status**: Discovery Complete
**Effort Estimate**: 5-8 sprints (Fibonacci), ~55-90 story points

---

## The One-Liner

A parallel User Acceptance Testing framework, implemented as the `/autopilot-uat` Claude skill, that reviews completed tasks against the RFC, discovery, and UX design specifications -- running alongside development rather than gating it after the fact.

## The Problem

The Autopilot CLI project has a well-defined specification stack: an RFC (1,164 lines covering architecture, data model, enforcement engine, phased implementation), a technical discovery document (1,400+ lines with architecture, ADRs, and risk analysis), a UX design document (1,000+ lines covering REPL, dashboard, workflows, notifications), and a task workflow system that distributes implementation across numbered task files. These documents are detailed and cross-referenced.

But there is no systematic verification that what gets built matches what was specified.

Specific gaps:

1. **No specification traceability.** When Task 042 is marked complete, nothing verifies that it actually implements the RFC section it claims to address. The task prompt contains acceptance criteria, but those are self-assessed by the implementing agent. There is no second opinion.

2. **No cross-reference validation.** The RFC, discovery, and UX design documents make overlapping commitments. The RFC says the dashboard fits in 80x24. The UX design specifies a two-column layout at 72 characters. The discovery doc says Rich handles the rendering. Nobody checks that the implemented dashboard satisfies all three simultaneously.

3. **UAT happens too late.** Traditional UAT runs after development is "complete." In an autonomous agent pipeline where 200-320 story points are implemented across 14-22 sprints, waiting until the end means discovering specification drift when it is expensive to fix. A parallel UAT framework catches drift per-task, when the context is fresh and the fix is cheap.

4. **No quality gate between task completion and sprint tracking.** The task workflow system (tasks-workflow.md) defines a status flow: TO DO -> IN PROGRESS -> COMPLETE. But "COMPLETE" means the implementing agent self-assessed against its own acceptance criteria and ran tests. There is no independent verification against the source specifications before the task is counted toward velocity.

5. **The verification-quality skill is necessary but insufficient.** The existing `verification-quality` skill provides truth scoring (0.0-1.0 scale), code verification, and auto-rollback. These are code-level quality checks. They answer "is this code correct?" but not "does this code implement what the RFC specified?" UAT operates at a higher level: specification compliance, behavioral validation, and cross-document traceability.

## The Solution

A `/autopilot-uat` Claude skill that provides:

- **Task-level acceptance testing** triggered when tasks are marked complete, cross-referencing the task's deliverables against the RFC, discovery, and UX design specifications
- **Specification traceability matrix** mapping every task to the RFC sections, discovery requirements, and UX elements it implements
- **Parallel execution** via claude-flow swarm coordination, running UAT alongside development without blocking the implementation pipeline
- **Test generation** that produces pytest test cases from specification requirements, behavioral tests from user stories, and compliance checks from UX design constraints
- **Reporting and feedback loop** that feeds results back into the task workflow, with configurable quality gates that can block task completion on UAT failure

---

## Current State Analysis

### What Exists (The Crime Scene)

**Specification Stack:**

| Document | Location | Lines | Coverage |
|----------|----------|-------|----------|
| RFC | `docs/ideation/RFC.md` | ~1,165 | Architecture, data model, anti-patterns, implementation plan, risk analysis |
| Discovery | `docs/ideation/discovery.md` | ~1,400+ | Technical analysis, ADRs, reuse plan, risk register, implementation phases |
| UX Design | `docs/ideation/ux-design.md` | ~1,000+ | REPL, dashboard, workflows, notifications, progressive disclosure, errors |
| PRD | `docs/ideation/PRD.md` | (exists) | Product requirements |
| Task Workflow | `.claude/knowledge/workflows/tasks-workflow.md` | 320 | Task structure, sprint planning, velocity tracking |

**Task System:**

Tasks follow the workflow defined in `tasks-workflow.md`. Each task has: ID, Title, File, Complete status, Sprint Points, User Story, Outcome, and a detailed Prompt with acceptance criteria. The task index at `tasks/tasks-index.md` tracks overall project progress. Individual task files are at `tasks/tasks-N.md` with a max of 10 tasks per file.

Currently, no task files exist yet (`tasks/` directory is empty). This means we are designing the UAT framework before implementation begins -- the ideal time.

**Existing Verification Infrastructure:**

| Component | Location | What It Does | Gap for UAT |
|-----------|----------|--------------|-------------|
| verification-quality skill | `.claude/skills/verification-quality/SKILL.md` | Truth scoring (0.0-1.0), code verification, auto-rollback | Code-level only; no spec traceability |
| claude-flow verify | `npx claude-flow verify check` | Automated correctness, security, best practices | Generic checks; not RFC-aware |
| claude-flow truth | `npx claude-flow truth` | Reliability metrics with trends | Measures code quality, not spec compliance |
| claude-flow memory | `npx claude-flow memory store/search` | Persistent memory for patterns | Available for UAT pattern learning |
| claude-flow swarm | `npx claude-flow swarm init` | Multi-agent parallel execution | Available for parallel UAT execution |
| hooks intelligence | `npx claude-flow hooks intelligence` | Self-learning pattern recognition | Available for improving test generation |

**Existing Skills Ecosystem:**

The project has 30+ Claude skills under `.claude/skills/`. The most relevant to UAT:

- `verification-quality` -- Truth scoring and code-level verification (complement, not duplicate)
- `skill-builder` -- Defines the YAML frontmatter and progressive disclosure spec for new skills
- `swarm-orchestration` -- Multi-agent coordination patterns
- `hooks-automation` -- Event-driven automation hooks

### Existing Components and Reuse Plan

**Will Reuse:**

| Component | How | Why |
|-----------|-----|-----|
| verification-quality skill | Complement | UAT adds spec-level checks on top of code-level truth scoring |
| claude-flow verify/truth | Integrate | UAT triggers verify checks as part of its pipeline and records truth scores |
| claude-flow memory | Direct use | Store UAT patterns, test results, and traceability mappings |
| claude-flow swarm | Direct use | Parallel UAT execution across multiple completed tasks |
| claude-flow hooks | Direct use | Trigger UAT automatically on task completion events |
| Task workflow system | Read/extend | UAT reads task structure and extends it with UAT status fields |
| Specification documents | Read | UAT reads RFC, discovery, UX design as its acceptance criteria source |
| pytest infrastructure | Direct use | UAT generates pytest test cases that run in the project's test suite |

**Will Not Reuse:**

| Component | Why |
|-----------|-----|
| verification-quality rollback | UAT does not auto-rollback; it reports and blocks. Rollback is a code-level concern |
| CI/CD integration from verification-quality | UAT is a development-time tool, not a CI pipeline stage (for now) |

**Consolidation Opportunities:**

1. Truth scoring from `verification-quality` and UAT spec-compliance scoring should share a common reporting format. Both produce 0.0-1.0 scores with pass/fail thresholds. Design the UAT score to be composable with the truth score.
2. The hooks system could serve both verification-quality triggers and UAT triggers. Rather than each skill registering its own hooks, a shared "post-task-completion" hook chain would invoke both.

---

## UAT Framework Architecture

### High-Level Flow

```
  Task marked COMPLETE
         |
         v
  ┌──────────────────────┐
  │  UAT Trigger          │  Hook: post-task-complete
  │  (automatic or manual)│
  └──────┬───────────────┘
         |
         v
  ┌──────────────────────┐
  │  Task Context Loader  │  Reads: task file, user story, outcome, prompt
  │                       │  Reads: acceptance criteria from prompt
  └──────┬───────────────┘
         |
         v
  ┌──────────────────────┐
  │  Spec Cross-Reference │  Maps task to:
  │  Engine               │  - RFC sections (by keyword + explicit ref)
  │                       │  - Discovery requirements
  │                       │  - UX design elements
  └──────┬───────────────┘
         |
         v
  ┌──────────────────────┐
  │  Test Generator       │  Produces:
  │                       │  - pytest acceptance tests
  │                       │  - Behavioral tests (from user stories)
  │                       │  - Compliance checks (from UX spec)
  │                       │  - Anti-pattern enforcement checks
  └──────┬───────────────┘
         |
         v
  ┌──────────────────────┐
  │  Test Executor        │  Runs generated tests via pytest
  │                       │  Runs claude-flow verify for code checks
  │                       │  Collects results
  └──────┬───────────────┘
         |
         v
  ┌──────────────────────┐
  │  UAT Reporter         │  Produces:
  │                       │  - Per-task UAT report
  │                       │  - Traceability matrix update
  │                       │  - RFC coverage progress
  │                       │  - Pass/fail with feedback
  └──────┬───────────────┘
         |
         v
  ┌──────────────────────┐
  │  Feedback Loop        │  On pass: task stays COMPLETE
  │                       │  On fail: task reverts to IN PROGRESS
  │                       │           with UAT feedback attached
  └──────────────────────┘
```

### Component Deep Dive

#### 1. UAT Trigger System

The UAT pipeline activates in three modes:

**Automatic mode** -- A claude-flow `post-task` hook fires when a task's `Complete` field changes from `[ ]` to `[x]`. The hook reads the task ID and file path, then invokes the UAT pipeline.

```bash
# Hook registration
npx claude-flow hooks post-task --name "uat-trigger" \
  --condition "task.status == 'COMPLETE'" \
  --action "uat-pipeline --task-id ${task.id} --task-file ${task.file}"
```

**Manual mode** -- The user invokes UAT directly from the REPL:

```
autopilot [my-app] > /autopilot-uat 042
autopilot [my-app] > /autopilot-uat 040-050     # Range
autopilot [my-app] > /autopilot-uat --all        # All completed tasks
autopilot [my-app] > /autopilot-uat --sprint 3   # All tasks in sprint 3
```

**Batch mode** -- UAT runs across multiple completed tasks in parallel using claude-flow swarm:

```bash
npx claude-flow swarm init --topology hierarchical --max-agents 4 --strategy specialized
# Coordinator distributes UAT work across worker agents
```

#### 2. Task Context Loader

Reads a completed task and extracts all testable assertions:

```python
@dataclass
class TaskContext:
    task_id: str
    title: str
    file_path: str               # Target implementation file
    sprint_points: int
    user_story: str              # "As a <role>, I want..."
    outcome: str                 # What this task delivers
    acceptance_criteria: list[str]  # Extracted from prompt
    prompt_text: str             # Full implementation prompt
    spec_references: list[SpecReference]  # Cross-refs to RFC/discovery/UX

@dataclass
class SpecReference:
    document: str                # "RFC" | "Discovery" | "UX Design"
    section: str                 # e.g., "3.5 Anti-Pattern Enforcement Engine"
    requirement: str             # The specific requirement text
    verification_type: str       # "functional" | "behavioral" | "compliance"
```

The loader parses the task markdown format defined in `tasks-workflow.md`, extracting:
- User Story fields for behavioral test generation
- Acceptance Criteria checkboxes from the prompt section
- File path references for implementation verification
- Any explicit RFC/discovery/UX section references in the prompt text

#### 3. Specification Cross-Reference Engine

This is the core intelligence of the UAT framework. It maps tasks to specification requirements through three mechanisms:

**Explicit references** -- Task prompts that directly cite RFC sections:

```markdown
#### Prompt:
Implement the EnforcementEngine orchestrator as specified in RFC Section 3.5.
```

The engine parses these references using regex patterns for section numbers, document names, and requirement IDs.

**Keyword matching** -- Tasks that implement concepts defined in specifications without explicitly citing them:

```python
# The traceability engine maintains a keyword index of spec sections
SPEC_INDEX = {
    "circuit_breaker": [
        SpecReference("RFC", "3.8", "Circuit breaker: abort after N consecutive timeouts"),
        SpecReference("Discovery", "Error Recovery", "Circuit breaker extracted from scheduler"),
    ],
    "quality_gates": [
        SpecReference("RFC", "3.5.3", "Quality gates injected into hive-mind objectives"),
        SpecReference("RFC", "3.4.1", "QualityGatesConfig: pre_commit, type_check, test, all"),
        SpecReference("UX Design", "5.1", "Quality standards checkbox selector in init wizard"),
    ],
    # ... indexed from all three specification documents
}
```

**Structural mapping** -- The RFC's phased implementation plan (Section 6) maps directly to task groups. Phase 1 tasks map to RFC Section 6 Phase 1 deliverables. This structural correspondence is the highest-confidence mapping.

The engine produces a `TraceabilityMatrix`:

```python
@dataclass
class TraceabilityMatrix:
    task_id: str
    rfc_sections: list[SpecReference]
    discovery_requirements: list[SpecReference]
    ux_elements: list[SpecReference]
    coverage_score: float          # 0.0-1.0: how much of the mapped spec is covered
    unmapped_specs: list[str]      # Spec requirements with no task mapping
    unmapped_tasks: list[str]      # Tasks with no spec mapping (red flag)
```

#### 4. Test Generator

The test generator produces four categories of tests from the task context and specification references:

**Category A: Acceptance Tests (from task criteria)**

These are the most direct. Each acceptance criterion in the task prompt becomes a pytest test case:

```python
# Generated from Task 042 acceptance criteria:
# - [ ] All tests associated with this task are passing
# - [ ] Config model validates all fields per RFC Section 3.4.1

def test_task_042_config_model_validates_scheduler_fields():
    """UAT: RFC 3.4.1 - SchedulerConfig validates strategy field."""
    config = SchedulerConfig(strategy="interval")
    assert config.strategy == "interval"

    with pytest.raises(ValidationError):
        SchedulerConfig(strategy="invalid_strategy")

def test_task_042_config_model_default_values():
    """UAT: RFC 3.4.1 - SchedulerConfig defaults match RFC specification."""
    config = SchedulerConfig()
    assert config.interval_seconds == 1800
    assert config.cycle_timeout_seconds == 7200
    assert config.agent_timeout_seconds == 900
    assert config.consecutive_timeout_limit == 2
```

**Category B: Behavioral Tests (from user stories)**

Each user story in the task becomes a behavioral test:

```python
# Generated from: "As a technical architect, I want to initialize a project
# with autopilot init, so that I get a working .autopilot/ directory."

def test_user_story_project_init_creates_autopilot_dir(tmp_path):
    """UAT: User can initialize a project and get a working .autopilot/ directory."""
    result = runner.invoke(app, ["init", "--type", "python", "--name", "test", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / ".autopilot").is_dir()
    assert (tmp_path / ".autopilot" / "config.yaml").is_file()
    assert (tmp_path / ".autopilot" / "agents").is_dir()
    assert (tmp_path / ".autopilot" / "board").is_dir()
```

**Category C: Specification Compliance Tests (from RFC/Discovery)**

These verify that implementation details match the RFC's technical specifications:

```python
# Generated from RFC Section 3.4.2 - SQLite Schema

def test_rfc_342_sqlite_schema_has_required_tables():
    """UAT: RFC 3.4.2 - SQLite schema contains all specified tables."""
    conn = sqlite3.connect(db_path)
    tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    required = {"projects", "sessions", "cycles", "dispatches",
                "enforcement_metrics", "velocity"}
    assert required.issubset(tables), f"Missing tables: {required - tables}"

def test_rfc_342_sqlite_wal_mode():
    """UAT: RFC 3.4.2 - SQLite uses WAL mode for concurrent access."""
    conn = sqlite3.connect(db_path)
    journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert journal_mode == "wal"
```

**Category D: UX Compliance Tests (from UX Design)**

These verify that CLI output, REPL behavior, and user-facing interactions match the UX design spec:

```python
# Generated from UX Design Section 4.1 - Dashboard fits 80x24

def test_ux_41_dashboard_fits_80x24(mock_project_state):
    """UAT: UX 4.1 - Default dashboard renders within 80x24 terminal."""
    output = render_dashboard(mock_project_state, width=80, height=24)
    lines = output.split("\n")
    assert len(lines) <= 24, f"Dashboard has {len(lines)} lines, max is 24"
    assert all(len(line) <= 80 for line in lines), "Dashboard exceeds 80 columns"

# Generated from UX Design Section 3.3 - Context-sensitive prompt

def test_ux_33_prompt_shows_project_name(mock_repl):
    """UAT: UX 3.3 - REPL prompt includes active project name."""
    mock_repl.set_active_project("my-app")
    prompt = mock_repl.get_prompt()
    assert "my-app" in prompt

def test_ux_33_prompt_shows_running_agents(mock_repl):
    """UAT: UX 3.3 - REPL prompt includes running agent count."""
    mock_repl.set_running_agents(3)
    prompt = mock_repl.get_prompt()
    assert "3 running" in prompt
```

**Test file organization:**

```
tests/
  uat/
    __init__.py
    conftest.py                    # UAT-specific fixtures
    test_uat_task_001.py           # Tests for task 001
    test_uat_task_002.py           # Tests for task 002
    ...
    test_uat_rfc_compliance.py     # Cross-cutting RFC compliance tests
    test_uat_ux_compliance.py      # Cross-cutting UX compliance tests
    traceability/
      matrix.json                  # Current traceability matrix
      coverage.json                # Spec coverage metrics
```

#### 5. Test Executor

The executor runs the generated tests and collects results:

```python
@dataclass
class UATResult:
    task_id: str
    timestamp: str
    overall_pass: bool
    score: float                    # 0.0-1.0 composite score
    categories: dict[str, CategoryResult]
    traceability: TraceabilityMatrix
    duration_seconds: float
    test_count: int
    pass_count: int
    fail_count: int
    skip_count: int
    failures: list[TestFailure]

@dataclass
class CategoryResult:
    category: str                   # "acceptance" | "behavioral" | "compliance" | "ux"
    pass_rate: float
    tests: list[TestCaseResult]

@dataclass
class TestFailure:
    test_name: str
    category: str
    spec_reference: SpecReference
    expected: str
    actual: str
    suggestion: str                 # AI-generated fix suggestion
```

The executor:
1. Runs `pytest tests/uat/test_uat_task_{id}.py` with JSON output
2. Runs `npx claude-flow verify check --file {task.file_path}` for code-level verification
3. Records truth scores via `npx claude-flow truth`
4. Stores results in claude-flow memory for pattern learning

#### 6. UAT Reporter

Produces three levels of output:

**Per-task report** (shown immediately after UAT runs):

```
  UAT RESULTS: Task 042                                    Score: 0.92
  ─────────────────────────────────────────────────────────────────────

  ACCEPTANCE CRITERIA                                      4/5 PASS
    [PASS] Config model validates all fields per RFC 3.4.1
    [PASS] All tests associated with this task are passing
    [PASS] File complies with optimization guidelines
    [PASS] Pydantic models use strict validation
    [FAIL] Default values match RFC specification
           Expected: interval_seconds=1800
           Actual:   interval_seconds=900
           Ref: RFC Section 3.4.1, SchedulerConfig

  BEHAVIORAL                                               2/2 PASS
    [PASS] User can create config with defaults
    [PASS] Config rejects invalid strategy values

  SPECIFICATION COMPLIANCE                                 3/3 PASS
    [PASS] RFC 3.4.1: All config fields present
    [PASS] RFC 3.4.1: Type annotations match spec
    [PASS] Discovery ADR-5: YAML format supported

  UX COMPLIANCE                                            N/A
    No UX requirements mapped to this task.

  TRACEABILITY
    RFC sections covered: 3.4.1 (complete), 3.4.2 (partial)
    Discovery sections covered: Config, ADR-5
    UX sections covered: none (expected for backend task)

  RECOMMENDATION: Fix default value mismatch, then re-run UAT.
```

**Sprint-level report** (aggregated across all tasks in a sprint):

```
  UAT SPRINT REPORT: Sprint 2026-03-10 to 2026-04-07
  ─────────────────────────────────────────────────────────────────────

  OVERALL                                                  Score: 0.89
  Tasks assessed: 14/21 complete
  Tests generated: 187
  Tests passing: 168 (89.8%)

  RFC COVERAGE PROGRESS
  Section 3.1 Architecture      ████████████████████░  95%
  Section 3.2 Package Structure ████████████████░░░░░  80%
  Section 3.3 Orchestration     ██████░░░░░░░░░░░░░░░  30%
  Section 3.4 Data Model        ████████████████████░  95%
  Section 3.5 Enforcement       ░░░░░░░░░░░░░░░░░░░░░   0%  (Phase 4)
  Section 3.6 Inter-Agent       ██████████░░░░░░░░░░░  50%

  FAILING TASKS
  Task 042  Config defaults mismatch     RFC 3.4.1    0.92
  Task 047  Missing error recovery path  RFC 3.8      0.85

  SPEC GAPS (requirements with no implementing task)
  - RFC 3.8: Partial dispatch recovery (new in RFC, not in discovery tasks)
  - UX 8.3: Session recovery flow (no task covers this yet)
```

**Cumulative traceability matrix** (exportable as JSON or markdown):

```
  TRACEABILITY MATRIX
  ─────────────────────────────────────────────────────────────────────

  RFC Section              Task(s)         UAT Status    Coverage
  ──────────────────────── ─────────────── ───────────── ─────────
  3.1 Architecture         001-005         PASS          95%
  3.2 Package Structure    006-010         PASS          80%
  3.3 Orchestration Flow   025-035         PARTIAL       30%
  3.4.1 Config Schema      040-045         1 FAIL        92%
  3.4.2 SQLite Schema      046-048         PASS          100%
  3.4.3 Directory Layout   010-012         PASS          100%
  3.5 Enforcement Engine   (Phase 4)       NOT STARTED   0%
  3.6 Inter-Agent Comms    050-055         PARTIAL       50%
  3.7 Agent Registry       020-022         PASS          100%
  3.8 Error Recovery       060-065         1 FAIL        85%
```

#### 7. Feedback Loop

When UAT fails, the system can operate in two modes:

**Advisory mode** (default) -- UAT results are reported but do not block task completion. The task stays COMPLETE, and the UAT failure is logged as a known issue for the sprint retrospective.

**Gated mode** (opt-in) -- UAT failure reverts the task status from `[x]` back to `[ ]` and appends UAT feedback to the task file:

```markdown
### Task ID: 042

- **Title**: Implement SchedulerConfig model
- **File**: src/autopilot/core/config.py
- **Complete**: [ ]
- **Sprint Points**: 3
- **UAT Status**: FAIL (0.92) -- last run 2026-03-10

#### UAT Feedback (2026-03-10):

```
FAIL: Default value mismatch for interval_seconds
  Expected: 1800 (per RFC Section 3.4.1)
  Actual:   900
  Fix: Update default value in SchedulerConfig.interval_seconds
```
```

The mode is configured per-project:

```yaml
# .autopilot/config.yaml
uat:
  mode: "advisory"           # "advisory" | "gated"
  threshold: 0.90            # Minimum score to pass (gated mode)
  auto_trigger: true          # Run UAT on task completion
  parallel_workers: 4         # Max concurrent UAT agents
  categories:
    acceptance: true
    behavioral: true
    compliance: true
    ux: true
```

---

## Specification Traceability Matrix Design

### Matrix Structure

The traceability matrix is the persistent artifact that tracks what has been specified, what has been implemented, and what has been verified. It lives at `.autopilot/uat/traceability.json` and is updated every time UAT runs.

```python
@dataclass
class TraceabilityEntry:
    spec_id: str                   # "RFC-3.4.1" or "UX-4.1" or "DISC-ADR-5"
    spec_document: str             # "RFC" | "Discovery" | "UX Design"
    spec_section: str              # Section number or name
    requirement_text: str          # The actual requirement
    implementing_tasks: list[str]  # Task IDs that implement this
    uat_status: str                # "PASS" | "FAIL" | "PARTIAL" | "NOT_TESTED" | "NOT_STARTED"
    uat_score: float | None        # Latest UAT score
    last_tested: str | None        # ISO timestamp
    test_files: list[str]          # Generated test file paths
    notes: str                     # Human-readable notes

@dataclass
class TraceabilityMatrix:
    entries: list[TraceabilityEntry]
    generated_at: str
    total_requirements: int
    requirements_covered: int
    requirements_passing: int
    coverage_percentage: float
    pass_percentage: float
```

### Building the Initial Matrix

The matrix is bootstrapped from the three specification documents. This is a one-time operation that scans the specs and creates entries:

**From the RFC:**

The RFC has a clear hierarchical structure. Each numbered section (3.1, 3.2, ..., 3.8) with its subsections becomes a set of requirements. Key extraction points:

- Section 3.4.1: Every field in the Pydantic models is a testable requirement
- Section 3.4.2: Every SQL CREATE TABLE statement is a testable requirement
- Section 3.5: Each of the 11 anti-pattern categories and 5 enforcement layers is a testable requirement
- Section 6: Each phase's deliverables and exit criteria are testable requirements
- Section 10: Each success metric is a testable requirement
- Appendix B: Each command in the reference is a testable requirement

**From the Discovery:**

The discovery doc's structure maps to implementation requirements:

- "Existing Components and Reuse Plan" -- each "Will Reuse" entry implies an integration requirement
- "System Architecture" section -- package structure and module boundaries
- ADR decisions -- each decision implies implementation constraints
- Risk Register -- each mitigation implies defensive implementation requirements

**From the UX Design:**

The UX doc is the richest source of testable requirements:

- Section 3: REPL behavior (prompt format, input modes, output patterns)
- Section 4: Dashboard layout (character widths, information density, rendering targets)
- Section 5: Workflow UX (init wizard flow, planning pipeline, monitoring, Q&A, review)
- Section 6: Notification tiers and delivery mechanisms
- Section 7: Progressive disclosure levels
- Section 8: Error and edge case handling

### Estimated Matrix Size

| Source | Estimated Requirements | Testable |
|--------|----------------------|----------|
| RFC Sections 3.1-3.8 | ~80 | ~65 |
| RFC Section 6 (Phases) | ~40 | ~40 |
| RFC Section 10 (Metrics) | ~15 | ~15 |
| RFC Appendix B (Commands) | ~25 | ~25 |
| Discovery ADRs | ~10 | ~8 |
| Discovery Architecture | ~20 | ~15 |
| UX Design (all sections) | ~60 | ~50 |
| **Total** | **~250** | **~218** |

This is a substantial but manageable matrix. At an average of 2-3 test cases per requirement, the UAT suite will generate approximately 500-650 test cases across the full project lifecycle.

---

## Parallel Execution Model

### How UAT Runs Alongside Development

The key design constraint: UAT must not slow down the implementation pipeline. It runs in parallel, on a separate concern, using separate compute resources.

```
  DEVELOPMENT PIPELINE              UAT PIPELINE
  ────────────────────              ────────────────────

  Task 040 → IN PROGRESS
  Task 041 → IN PROGRESS
  Task 042 → COMPLETE ─────────────→ UAT queued for 042
  Task 043 → IN PROGRESS             UAT running on 042
  Task 044 → IN PROGRESS             UAT complete: 042 PASS
  Task 045 → COMPLETE ─────────────→ UAT queued for 045
  Task 046 → IN PROGRESS             UAT running on 045
                                      UAT complete: 045 FAIL
                                      → feedback → 045 re-opened
```

### Swarm Coordination

UAT uses claude-flow swarm in a hierarchical topology:

```bash
npx claude-flow swarm init \
  --topology hierarchical \
  --max-agents 4 \
  --strategy specialized
```

**Agent roles in UAT swarm:**

| Role | Responsibility | Count |
|------|---------------|-------|
| UAT Coordinator | Receives completed tasks, distributes UAT work, aggregates results | 1 |
| Spec Analyzer | Reads specifications, builds cross-references, identifies requirements | 1 |
| Test Generator | Produces pytest test cases from requirements | 1 |
| Test Runner | Executes tests, collects results, generates reports | 1 |

For batch UAT (running against multiple completed tasks), the coordinator distributes tasks across multiple Test Generator + Test Runner pairs.

### Resource Isolation

UAT agents use separate resource allocation from development agents:

```yaml
# .autopilot/config.yaml
uat:
  parallel_workers: 4
  model: "sonnet"               # Use cheaper model for UAT (not opus)
  max_turns: 20                 # Limited turns per UAT run
  timeout_seconds: 300          # 5-minute timeout per task UAT
  resource_pool: "uat"          # Separate from development pool
```

Using sonnet for UAT is a deliberate cost optimization. UAT work is structured and pattern-based (read spec, generate test, run test, report result). It does not require the deep reasoning that implementation tasks demand. This keeps UAT costs low enough to run on every task completion without concern.

---

## Integration with Task Workflow System

### Proposed Changes to Task Template

Add UAT-specific fields to the task template in `tasks-workflow.md`:

```markdown
### Task ID: {ID}

- **Title**: Example title
- **File**: example/file/path
- **Complete**: [ ]
- **Sprint Points**: 3
- **UAT Status**: NOT_TESTED
- **Spec References**: RFC 3.4.1, UX 4.1

- **User Story (business-facing)**: As a <role>, I want <capability>, so that <business outcome>.
- **Outcome (what this delivers)**: Clear description of the feature enabled and business value.

#### Prompt:

```markdown
...existing prompt content...

**Specification References:**
- RFC Section 3.4.1: SchedulerConfig model
- UX Design Section 4.1: Dashboard layout constraints
- Discovery ADR-5: YAML configuration format

**UAT Acceptance Criteria (verified by /autopilot-uat):**
- [ ] All config fields from RFC 3.4.1 are present with correct types
- [ ] Default values match RFC specification
- [ ] YAML serialization/deserialization round-trips correctly
```
```

New fields:
- **UAT Status**: `NOT_TESTED` | `PASS` | `FAIL` | `PARTIAL` -- updated by the UAT pipeline
- **Spec References**: Explicit links to RFC/Discovery/UX sections -- used by the cross-reference engine
- **UAT Acceptance Criteria**: Separate from implementation acceptance criteria; these are verified by the UAT pipeline rather than self-assessed by the implementing agent

### Impact on Sprint Planning

UAT effort should be factored into sprint capacity but is not added to individual task point estimates. Instead:

- **UAT overhead**: Reserve 10-15% of sprint capacity for UAT execution and failure remediation
- **UAT velocity**: Track separately from implementation velocity to identify specification quality issues
- **Sprint retrospective**: UAT failure patterns inform future specification clarity

### Impact on Task Completion Workflow

The existing task completion workflow (Section 3 of tasks-workflow.md) gains an additional step:

```
Current: Run tests → Run linting → Optimize files → Mark complete → Update index

Proposed: Run tests → Run linting → Optimize files → Mark complete → UAT runs →
          If UAT passes: Update index, record velocity
          If UAT fails (gated mode): Revert to incomplete, attach feedback
          If UAT fails (advisory mode): Update index, log UAT issue
```

---

## ruflo/claude-flow Integration Plan

### Tool Mapping

| UAT Capability | claude-flow Tool | Usage |
|---------------|-----------------|-------|
| Task completion trigger | `hooks post-task` | Register hook to fire UAT on task completion |
| Parallel UAT execution | `swarm init`, `agent spawn` | Run multiple UAT agents for batch testing |
| Code verification | `verify check`, `verify batch` | Code-level quality checks as part of UAT |
| Truth scoring | `truth` | Record and track UAT scores alongside code truth scores |
| Test pattern memory | `memory store`, `memory search` | Store successful test patterns for reuse |
| Pattern learning | `hooks intelligence`, `agentdb pattern-store` | Learn which test patterns catch real bugs |
| Report generation | `verify report` | Generate UAT reports in multiple formats |
| Auto-rollback on failure | `verify rollback` | Optional: rollback task changes on UAT failure |
| Task orchestration | `task create`, `task status` | Track UAT tasks within claude-flow |

### Memory System for Test Pattern Learning

The UAT framework stores learned patterns in claude-flow memory:

```bash
# Store a successful test pattern
npx claude-flow memory store \
  --key "uat-pattern-config-validation" \
  --value "Pydantic models: test each field type, test defaults against spec, test validation errors" \
  --namespace "uat-patterns" \
  --tags "pydantic,config,rfc-3.4.1"

# Search for relevant patterns when generating tests for a new task
npx claude-flow memory search \
  --query "config model validation patterns" \
  --namespace "uat-patterns" \
  --limit 5
```

Over time, the memory system accumulates:
- **Test templates**: Reusable test patterns for common implementation types (Pydantic models, CLI commands, REPL behaviors, database schemas)
- **Failure patterns**: Common specification mismatches and their fixes
- **False positive patterns**: Tests that consistently fail due to test logic errors rather than implementation bugs

### Hooks Intelligence for Improving Test Generation

```bash
# Register UAT learning hook
npx claude-flow hooks intelligence learn \
  --pattern "uat-test-generation" \
  --input "task-context" \
  --output "test-quality-score" \
  --feedback "uat-pass-fail"
```

The hooks intelligence system tracks:
- Which test categories (acceptance, behavioral, compliance, UX) have the highest failure detection rates
- Which specification sections produce the most implementation drift
- Which task types (config, CLI, orchestration, enforcement) need the most UAT attention
- Optimal test count per task complexity level (1-point tasks need fewer tests than 8-point tasks)

---

## `/autopilot-uat` Skill Architecture

### YAML Frontmatter

```yaml
---
name: "Autopilot UAT"
description: "Parallel User Acceptance Testing framework that verifies completed tasks against RFC, discovery, and UX design specifications. Use when tasks are marked complete, when running sprint-level quality checks, or when checking specification coverage progress."
---
```

### Directory Structure

```
.claude/skills/autopilot-uat/
  SKILL.md                          # Main skill file (progressive disclosure)
  scripts/
    uat-pipeline.sh                 # Orchestrates the full UAT pipeline
    generate-tests.py               # Test generation from spec references
    build-matrix.py                 # Bootstrap traceability matrix from specs
    update-matrix.py                # Update matrix after UAT run
  resources/
    templates/
      test-acceptance.py.j2         # Jinja2 template for acceptance tests
      test-behavioral.py.j2         # Jinja2 template for behavioral tests
      test-compliance.py.j2         # Jinja2 template for compliance tests
      test-ux.py.j2                 # Jinja2 template for UX tests
      uat-report.md.j2              # Jinja2 template for UAT reports
    schemas/
      traceability.schema.json      # JSON schema for traceability matrix
      uat-result.schema.json        # JSON schema for UAT results
    spec-index/
      rfc-index.json                # Pre-built index of RFC requirements
      discovery-index.json          # Pre-built index of discovery requirements
      ux-index.json                 # Pre-built index of UX requirements
  docs/
    ADVANCED.md                     # Custom test patterns, matrix maintenance
    TROUBLESHOOTING.md              # Common UAT issues and resolutions
```

### SKILL.md Structure (Progressive Disclosure)

**Level 1: Overview**
- What the skill does (3 sentences)
- Prerequisites (pytest, claude-flow, specification documents)
- Quick start command

**Level 2: Quick Start**
- Run UAT on a single task: `/autopilot-uat 042`
- Run UAT on a sprint: `/autopilot-uat --sprint 3`
- View traceability matrix: `/autopilot-uat --matrix`
- View coverage: `/autopilot-uat --coverage`

**Level 3: Detailed Usage**
- Configuration options (mode, threshold, categories)
- Custom test patterns
- Integration with sprint planning
- Batch execution with swarm
- Hook registration for automatic triggering

**Level 4: Reference**
- Full schema documentation
- API reference for generated test patterns
- Troubleshooting guide
- Integration with verification-quality skill

### Relationship to verification-quality Skill

The two skills are complementary, not overlapping:

| Concern | verification-quality | autopilot-uat |
|---------|---------------------|---------------|
| Scope | Code correctness | Specification compliance |
| Trigger | Any code change | Task completion |
| Metric | Truth score (0.0-1.0) | UAT score (0.0-1.0) + coverage % |
| Tests | Generic (syntax, security, patterns) | Spec-derived (RFC, discovery, UX) |
| Rollback | Automatic on low truth score | Advisory or gated (configurable) |
| Memory | Code quality patterns | Spec compliance patterns |
| Output | Verification report | UAT report + traceability matrix |

Both scores can be composed into a combined quality metric:

```python
combined_score = (truth_score * 0.4) + (uat_score * 0.6)
```

The weighting reflects the priority: spec compliance matters more than code-level quality, because correct code that implements the wrong spec is still wrong.

---

## UX Design for `/autopilot-uat`

### REPL Integration

The `/autopilot-uat` command follows the same UX patterns established in the UX Design document (Sections 3-8):

**Single task UAT:**

```
autopilot [my-app] > /autopilot-uat 042

  Running UAT for Task 042: Implement SchedulerConfig model...

  Loading task context ........... done
  Cross-referencing specs ........ 3 RFC sections, 1 ADR, 0 UX elements
  Generating tests ............... 12 tests (4 acceptance, 2 behavioral, 6 compliance)
  Executing tests ................ done (2.3s)

  UAT RESULTS: Task 042                                    Score: 0.92
  ─────────────────────────────────────────────────────────────────────

  ACCEPTANCE CRITERIA                                      4/5 PASS
    [PASS] Config model validates all fields per RFC 3.4.1
    [PASS] All tests associated with this task are passing
    [PASS] File complies with optimization guidelines
    [PASS] Pydantic models use strict validation
    [FAIL] Default values match RFC specification
           interval_seconds: expected 1800, got 900
           Ref: RFC Section 3.4.1

  BEHAVIORAL                                               2/2 PASS
  SPECIFICATION COMPLIANCE                                 6/6 PASS

  Overall: 12/13 tests passing (92.3%)
  Recommendation: Fix interval_seconds default, re-run with /autopilot-uat 042

autopilot [my-app] >
```

**Sprint-level UAT:**

```
autopilot [my-app] > /autopilot-uat --sprint 3

  Running UAT for Sprint 3 (14 completed tasks)...

  Initializing UAT swarm (4 parallel workers)...
  [████████████████████████████████████████] 14/14 tasks  12.8s

  UAT SPRINT SUMMARY                                      Score: 0.89
  ─────────────────────────────────────────────────────────────────────

  Tasks assessed:  14        Tests generated:  187
  Tasks passing:   12        Tests passing:    168 (89.8%)
  Tasks failing:    2        Tests failing:     19

  FAILING TASKS
  042  Config defaults mismatch      RFC 3.4.1     0.92  (1 fix needed)
  047  Missing error recovery path   RFC 3.8       0.85  (2 fixes needed)

  RFC COVERAGE PROGRESS
  Phase 1 Foundation    ████████████████████░  95%  (38/40 requirements)
  Phase 2 Task Mgmt     ████████████░░░░░░░░  60%  (15/25 requirements)

  Full report: .autopilot/uat/reports/sprint-3-uat.md
  Matrix: /autopilot-uat --matrix

autopilot [my-app] >
```

**Coverage view:**

```
autopilot [my-app] > /autopilot-uat --coverage

  SPECIFICATION COVERAGE                         Updated: 2026-03-10
  ─────────────────────────────────────────────────────────────────────

  RFC                                                    Covered  Total
  Section 3.1 Architecture Overview         ████████████  12/12   100%
  Section 3.2 Package Structure             ████████░░░░   8/12    67%
  Section 3.3 Orchestration Flow            ██░░░░░░░░░░   2/15    13%
  Section 3.4 Data Model                    ██████████░░  20/24    83%
  Section 3.5 Enforcement Engine            ░░░░░░░░░░░░   0/30     0%
  Section 3.6 Inter-Agent Communication     ████░░░░░░░░   4/10    40%
  Section 3.7 Agent Registry                ████████████   6/6    100%
  Section 3.8 Error Recovery                ██████░░░░░░   6/12    50%

  Discovery                                              28/35    80%
  UX Design                                              15/50    30%

  Overall: 101/218 requirements covered (46.3%)

  Gaps: /autopilot-uat --gaps  (show uncovered requirements)

autopilot [my-app] >
```

**Gaps view:**

```
autopilot [my-app] > /autopilot-uat --gaps

  UNCOVERED REQUIREMENTS                                  117 remaining
  ─────────────────────────────────────────────────────────────────────

  HIGH PRIORITY (in current implementation phase)
  RFC 3.3.1  Cycle lock acquisition with PID + TTL        No task assigned
  RFC 3.3.1  Git state validation before each cycle       Task 033, not started
  RFC 3.8    Partial dispatch recovery                    No task assigned

  FUTURE PHASES (expected to be covered later)
  RFC 3.5.*  All enforcement engine requirements          Phase 4
  UX 5.3     Watch mode TUI                               Phase 6
  UX 8.3     Session recovery flow                        Phase 6

  /autopilot-uat --gaps --phase 1   (show only current phase gaps)

autopilot [my-app] >
```

### Integration with Existing Commands

| Existing Command | UAT Integration |
|-----------------|-----------------|
| `/watch` | UAT status appears in the watch TUI when UAT is running on a task |
| `/report summary` | Includes UAT pass rate and coverage percentage |
| `/report quality` | Includes UAT scores alongside enforcement metrics |
| `/dashboard` | Shows UAT status for recently completed tasks |
| `/plan show` | Shows UAT status column next to task completion status |

### Error Presentation

When UAT encounters errors (not test failures, but UAT pipeline errors):

```
  UAT ERROR: Task 042
  ─────────────────────────────────────────────────────────────────────

  Could not generate tests: specification reference "RFC 3.4.1" not found
  in spec index.

  This usually means:
  1. The spec index is outdated -- run /autopilot-uat --rebuild-index
  2. The task's spec reference is incorrect -- check tasks/tasks-5.md

  UAT skipped for this task. Implementation is not affected.

autopilot [my-app] >
```

Design notes:
- UAT errors never block implementation. If UAT itself is broken, development continues.
- Clear diagnostic with actionable next steps.
- The distinction between "UAT failed" (tests ran but found issues) and "UAT errored" (UAT pipeline itself broke) is always explicit.

---

## Risk Analysis

### HIGH: Specification Index Accuracy

**Probability:** High (natural language specs are ambiguous, keyword matching has false positives)
**Impact:** Major -- inaccurate traceability matrix undermines trust in the entire framework
**Mitigation:** Start with explicit spec references in task prompts (humans write them). Keyword matching is supplementary. False positive/negative tracking in memory system refines matching over time. Manual matrix corrections are first-class operations.
**Detection:** Regular human review of traceability matrix. Track "UAT overrides" (human corrections to auto-generated mappings).

### HIGH: Test Generation Quality

**Probability:** High (generating meaningful tests from natural language spec text is hard)
**Impact:** Major -- bad tests either miss real drift (false negatives) or flag correct code (false positives)
**Mitigation:** Start with template-based generation (Jinja2 templates for common patterns: Pydantic models, CLI commands, SQLite schemas). Hand-written tests for complex requirements. AI-generated tests for behavioral and UX categories, reviewed by human before first run.
**Detection:** Track false positive rate (tests that fail on correct code) and false negative rate (spec drift that UAT misses). Both should decrease over time as patterns are learned.

### MEDIUM: UAT Pipeline Overhead

**Probability:** Medium (running 12+ tests per task adds time and cost)
**Impact:** Reduced development velocity if UAT becomes a bottleneck
**Mitigation:** Use sonnet model (not opus) for UAT agents. Set tight timeout (5 minutes per task). Run UAT in parallel with development, never blocking the implementation pipeline in advisory mode. Skip UAT for trivial tasks (1-point documentation updates).
**Detection:** Track UAT duration per task. Alert if average exceeds 5 minutes. Compare implementation velocity with and without UAT.

### MEDIUM: Specification Drift in Specs Themselves

**Probability:** Medium (the RFC and discovery docs will evolve as implementation reveals new insights)
**Impact:** UAT tests become outdated when specs change
**Mitigation:** Spec index rebuild is a first-class operation (`/autopilot-uat --rebuild-index`). When specs change, the diff triggers a targeted UAT re-run on affected tasks. Version the spec index alongside the spec documents.
**Detection:** Git diff on spec documents triggers spec index staleness warning.

### LOW: Over-Testing

**Probability:** Low-Medium (enthusiasm for UAT could lead to excessive test generation)
**Impact:** Test suite becomes slow, noisy, and ignored
**Mitigation:** Cap test generation at 5 tests per story point (a 3-point task gets max 15 tests). Focus on high-value requirements (RFC data model, UX behavioral constraints) over low-value ones (code comment style). Regularly prune tests that have never caught a real issue.
**Detection:** Track test-to-failure ratio. Tests that pass 100% of the time for 3+ sprints are candidates for removal or promotion to the standard test suite.

### LOW: Gated Mode Friction

**Probability:** Low (gated mode is opt-in)
**Impact:** Developers ignore or disable UAT if it blocks too often
**Mitigation:** Default to advisory mode. Gated mode requires explicit opt-in. Gated threshold is configurable (default 0.90, not 1.0). Clear feedback on what failed and how to fix it.
**Detection:** Track UAT disable/re-enable frequency. If teams frequently disable gated mode, the threshold is too aggressive.

---

## Implementation Plan

### Phase 1: Foundation (2 sprints, ~15-20 story points)

**Goal:** Core UAT pipeline working for manual invocation on single tasks.

**Deliverables:**
- [ ] Skill directory structure (`.claude/skills/autopilot-uat/`)
- [ ] SKILL.md with progressive disclosure structure
- [ ] Task context loader (parses task markdown format)
- [ ] Spec cross-reference engine (explicit references only, no keyword matching)
- [ ] Spec index builder for RFC (manual bootstrap)
- [ ] Basic test generator (acceptance tests from task criteria)
- [ ] Test executor (pytest runner with JSON output)
- [ ] Per-task UAT reporter (terminal output)
- [ ] UAT config schema (mode, threshold, categories)
- [ ] `/autopilot-uat {task_id}` command

**Exit criteria:** `/autopilot-uat 042` reads a completed task, generates acceptance tests from its criteria, runs them, and reports results with RFC section references.

### Phase 2: Specification Coverage (1-2 sprints, ~12-18 story points)

**Goal:** Full traceability matrix and coverage reporting.

**Deliverables:**
- [ ] Spec index builder for Discovery and UX Design documents
- [ ] Keyword-based cross-reference matching (supplementary to explicit refs)
- [ ] Traceability matrix data model and JSON storage
- [ ] Matrix update pipeline (runs after every UAT)
- [ ] Coverage reporter (overall and per-spec-section)
- [ ] Gaps reporter (uncovered requirements)
- [ ] Behavioral test generator (from user stories)
- [ ] Compliance test generator (from RFC technical specs)
- [ ] UX compliance test generator (from UX design constraints)
- [ ] `/autopilot-uat --coverage` and `/autopilot-uat --gaps` commands

**Exit criteria:** Traceability matrix tracks all ~218 requirements. Coverage and gaps reports show which specs are implemented and verified.

### Phase 3: Parallel Execution and Automation (1-2 sprints, ~13-22 story points)

**Goal:** UAT runs automatically on task completion and in parallel for batch operations.

**Deliverables:**
- [ ] claude-flow hook registration for post-task-completion trigger
- [ ] Swarm configuration for parallel UAT execution
- [ ] Batch UAT mode (`/autopilot-uat --sprint N`)
- [ ] Sprint-level UAT reporter
- [ ] Feedback loop implementation (advisory and gated modes)
- [ ] Task template updates with UAT-specific fields
- [ ] Integration with `/watch`, `/report`, `/dashboard` commands
- [ ] UAT score composition with truth score from verification-quality

**Exit criteria:** Tasks trigger UAT automatically on completion. Sprint-level batch UAT runs across all completed tasks in parallel. Results appear in existing reporting commands.

### Phase 4: Learning and Optimization (1-2 sprints, ~15-30 story points)

**Goal:** UAT improves over time through pattern learning.

**Deliverables:**
- [ ] claude-flow memory integration for test patterns
- [ ] Hooks intelligence integration for test generation improvement
- [ ] False positive/negative tracking and mitigation
- [ ] Test pruning based on value metrics
- [ ] Spec index auto-refresh on specification document changes
- [ ] Custom test pattern support (user-defined Jinja2 templates)
- [ ] UAT results export (JSON, CSV, HTML)
- [ ] Historical trend analysis

**Exit criteria:** Test generation quality improves measurably over 3+ sprints. False positive rate decreases. Pattern memory contains reusable test templates for all major implementation types.

### Effort Summary

| Phase | Sprints | Story Points | Outcome |
|-------|---------|-------------|---------|
| 1: Foundation | 2 | 15-20 | Manual single-task UAT with acceptance tests |
| 2: Coverage | 1-2 | 12-18 | Full traceability matrix and spec coverage |
| 3: Parallel | 1-2 | 13-22 | Automatic triggering, batch execution, integration |
| 4: Learning | 1-2 | 15-30 | Pattern learning, optimization, advanced features |
| **Total** | **5-8** | **55-90** | |

### Dependency on Main Project Phases

UAT development should track the main project implementation:

- **UAT Phase 1** can begin alongside **Project Phase 1** (Foundation). The UAT framework needs tasks to test, and Phase 1 produces the first batch.
- **UAT Phase 2** should be ready before **Project Phase 3** (Autonomous Execution). By the time agents are implementing autonomously, UAT should have full coverage tracking.
- **UAT Phase 3** (parallel execution) aligns with **Project Phase 3**, when the swarm infrastructure is available.
- **UAT Phase 4** (learning) can run continuously from **Project Phase 4** onward.

---

## Planning Process Update Recommendations

### 1. Task Template Updates

**Recommendation:** Add three fields to the task template in `tasks-workflow.md`:

- `UAT Status`: Track UAT results per task
- `Spec References`: Explicit links to specification sections
- `UAT Acceptance Criteria`: Separate section for spec-derived criteria that UAT verifies independently

**Impact:** Moderate. Every task prompt needs these fields. Best to add them before task creation begins.

### 2. Sprint Planning Adjustments

**Recommendation:** Reserve 10-15% of sprint capacity for UAT overhead.

For a sprint with 40 planned points:
- 34-36 points for implementation tasks
- 4-6 points reserved for UAT execution, failure remediation, and spec gap resolution

**Impact:** Low. This is a planning adjustment, not a process change.

### 3. Task Prompt Specification References

**Recommendation:** Every task prompt should include explicit `Spec References` listing the RFC sections, discovery requirements, and UX elements it implements. This is the highest-value change because it makes the traceability matrix accurate from day one rather than relying on keyword matching.

**Impact:** Moderate. Requires task authors to identify which spec sections each task addresses. This is valuable independent of UAT because it improves task clarity and reduces specification drift.

### 4. Sprint Retrospective UAT Review

**Recommendation:** Add a UAT section to the sprint retrospective template:

```markdown
## UAT Summary
- UAT pass rate: {percentage}
- Spec coverage progress: {percentage}
- Most common failure category: {category}
- Spec gaps discovered: {count}
- Lessons learned: {notes}
```

**Impact:** Low. Adds one section to an existing template.

---

## Open Questions

| # | Question | Options | Current Leaning |
|---|----------|---------|-----------------|
| 1 | Should UAT tests be committed to the repo or generated on-the-fly? | (a) Committed (persistent, reviewable, version-controlled), (b) Generated each time (always fresh, no maintenance), (c) Hybrid (templates committed, instances generated) | (c) Hybrid -- templates in the skill's resources/, generated tests in `.autopilot/uat/` (gitignored) |
| 2 | Should the traceability matrix be human-editable? | (a) Machine-only (auto-generated from specs), (b) Human-editable with merge logic, (c) Human-override with audit trail | (c) Human-override -- auto-generated base with human corrections tracked |
| 3 | What happens when a spec document changes mid-sprint? | (a) Invalidate all affected UAT results, (b) Flag as stale but keep passing, (c) Re-run affected UAT tests automatically | (b) Flag as stale -- re-running is expensive and the spec change may be minor |
| 4 | Should UAT score affect velocity tracking? | (a) No -- velocity counts completed tasks regardless, (b) Yes -- only UAT-passing tasks count toward velocity, (c) Separate metrics (implementation velocity vs. quality-adjusted velocity) | (c) Separate metrics -- implementation velocity for sprint planning, quality-adjusted velocity for project health |
| 5 | How should UAT handle tasks that span multiple spec sections? | (a) Generate tests for all referenced sections, (b) Generate tests only for the primary section, (c) Split into sub-UAT-runs per section | (a) All sections -- a task that claims to implement 3 spec sections should be tested against all 3 |

---

*End of Discovery*
