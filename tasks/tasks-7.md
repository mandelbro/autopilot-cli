## Summary (tasks-7.md)

- **Tasks in this file**: 10
- **Task IDs**: 061 - 070
- **Total Points**: 40

### Main Phase 5: Enforcement Layers 2-5 + UAT Phase 2: Spec Coverage Completion

---

## Tasks

### Task ID: 061

- **Title**: Layer 2 -- Pre-commit hook setup
- **File**: src/autopilot/enforcement/precommit.py
- **Complete**: [x]
- **Sprint Points**: 5

- **User Story (business-facing)**: As a system operator, I want pre-commit hooks that block anti-patterns at commit time, so that enforcement catches issues before they enter the repository.
- **Outcome (what this delivers)**: Pre-commit hook generator using Lefthook with block-no-verify and detect-secrets integration.

#### Prompt:

```markdown
**Objective:** Implement Layer 2 pre-commit hook setup with Lefthook.

**File to Create/Modify:** `src/autopilot/enforcement/precommit.py`

**Specification References:**
- RFC Section 3.5.2: Layer 2 (Pre-Commit Hooks, <5s total)
- RFC Section 7.1: block-no-verify, detect-secrets
- Discovery: Pre-commit hook management

**Prerequisite Requirements:**
1. Task 056 must be complete (engine)
2. Write tests in `tests/enforcement/test_precommit.py`

**Detailed Instructions:**
1. Implement `PrecommitSetup`:
   - `install_lefthook(project_root: Path)` installs Lefthook runner
   - `generate_config(project_type: str) -> dict` creates lefthook.yml content
   - `add_block_no_verify(config: dict)` prevents AI --no-verify bypass
   - `add_detect_secrets(config: dict)` adds credential scanning
   - `apply(project_root: Path)` writes config and installs hooks
2. Hook config includes: ruff check+format, pyright, detect-secrets, block-no-verify
3. Target < 5 seconds total hook execution time
4. Support Python and TypeScript configurations

**Acceptance Criteria:**
- [ ] Lefthook config is generated correctly
- [ ] block-no-verify hook is included
- [ ] detect-secrets is configured
- [ ] Hook config targets < 5s execution
- [ ] All tests pass
```

---

### Task ID: 062

- **Title**: Layer 3 -- CI/CD template generation
- **File**: src/autopilot/enforcement/ci.py
- **Complete**: [x]
- **Sprint Points**: 5

- **User Story (business-facing)**: As a system operator, I want CI pipeline templates with quality gates, so that nothing merges without passing enforcement checks as a backstop.
- **Outcome (what this delivers)**: GitHub Actions workflow template generator with quality gate jobs, coverage thresholds, and complexity limits.

#### Prompt:

```markdown
**Objective:** Implement Layer 3 CI/CD template generation for GitHub Actions.

**File to Create/Modify:** `src/autopilot/enforcement/ci.py`

**Specification References:**
- RFC Section 3.5.2: Layer 3 (CI/CD Pipeline, backstop)
- Discovery: CI/CD template generation (GitHub Actions)

**Prerequisite Requirements:**
1. Task 056 must be complete (engine)
2. Write tests in `tests/enforcement/test_ci.py`

**Detailed Instructions:**
1. Implement `CIPipelineGenerator`:
   - `generate_workflow(project_type: str, config: EnforcementConfig) -> str` produces YAML
   - Jobs: lint (ruff), typecheck (pyright), test (pytest with coverage), security (detect-secrets)
   - Coverage threshold gate (configurable, default 90% for core)
   - Complexity threshold gate (max cyclomatic complexity)
2. Use Jinja2 templates for workflow generation
3. Place generated workflow at .github/workflows/quality-gates.yml
4. Support matrix strategy for multiple Python versions

**Acceptance Criteria:**
- [ ] GitHub Actions workflow YAML is valid
- [ ] All quality gate jobs are included
- [ ] Coverage thresholds are configurable
- [ ] Workflow supports Python matrix testing
- [ ] All tests pass
```

---

### Task ID: 063

- **Title**: Layer 4 -- Agent guardrails (PreToolUse/PostToolUse hooks)
- **File**: src/autopilot/enforcement/guardrails.py
- **Complete**: [x]
- **Sprint Points**: 5

- **User Story (business-facing)**: As a system operator, I want real-time guardrails during agent execution, so that dangerous operations like --no-verify or unauthorized dependencies are blocked before they happen.
- **Outcome (what this delivers)**: Agent guardrail configuration generator for PreToolUse/PostToolUse hooks with progressive trust and circuit breaker.

#### Prompt:

```markdown
**Objective:** Implement Layer 4 agent guardrails for Claude Code sessions.

**File to Create/Modify:** `src/autopilot/enforcement/guardrails.py`

**Specification References:**
- RFC Section 3.5.2: Layer 4 (Agent Guardrails, <10ms per evaluation)
- Discovery: Real-time agent guardrails (PreToolUse hooks)
- RFC Section 7.1: Hook bypass prevention

**Prerequisite Requirements:**
1. Task 056 must be complete (engine)
2. Write tests in `tests/enforcement/test_guardrails.py`

**Detailed Instructions:**
1. Implement `GuardrailsGenerator`:
   - `generate_pretooluse_rules(project: ProjectConfig) -> list[GuardrailRule]`
   - Block: git commit --no-verify, deleting protected files, installing unauthorized deps
   - `generate_posttooluse_rules(project: ProjectConfig) -> list[GuardrailRule]`
   - Warn: large file modifications, dependency additions
   - `generate_settings_json(rules: list) -> dict` for .claude/settings.json
2. Progressive trust model: errors -> warnings after N consecutive triggers (prevent agent lockup)
3. Security rules exempt from progressive trust (always error)
4. Target < 10ms evaluation per rule

**Acceptance Criteria:**
- [ ] PreToolUse rules block dangerous operations
- [ ] PostToolUse rules inject warnings
- [ ] Progressive trust prevents agent lockup
- [ ] Security rules are never downgraded
- [ ] Settings JSON is valid
- [ ] All tests pass
```

---

### Task ID: 064

- **Title**: Layer 5 -- Protected code regions
- **File**: src/autopilot/enforcement/protected.py
- **Complete**: [x]
- **Sprint Points**: 5

- **User Story (business-facing)**: As a system operator, I want to mark critical code regions as protected, so that AI agents cannot silently modify auth logic, payment processing, or data migrations without explicit review.
- **Outcome (what this delivers)**: Hash-based code protection system that detects changes to marked regions and alerts in PRs.

#### Prompt:

```markdown
**Objective:** Implement Layer 5 hash-based protected code regions.

**File to Create/Modify:** `src/autopilot/enforcement/protected.py`

**Specification References:**
- RFC Section 3.5.2: Layer 5 (Protected Regions)
- Discovery: Protected code regions (#@protected markers)

**Prerequisite Requirements:**
1. Task 056 must be complete (engine)
2. Write tests in `tests/enforcement/test_protected.py`

**Detailed Instructions:**
1. Implement `ProtectedRegionManager`:
   - `scan(file_path: Path) -> list[ProtectedRegion]` finds #@protected markers
   - `validate(file_path: Path) -> list[Violation]` checks hash matches current code
   - `protect(file_path: Path, start_line: int, line_count: int)` adds protection marker
   - `update_hash(file_path: Path, region_id: str)` updates hash after approved change
2. Marker format: `#@protected N HASH` where N is line count and HASH is sha256 of protected lines
3. Violation when hash mismatch detected (code was modified)
4. Integration with PR-level alerts (output for CI/CD to consume)

**Acceptance Criteria:**
- [ ] Protection markers are correctly parsed
- [ ] Hash validation detects code changes
- [ ] New protection can be added to existing files
- [ ] Hash updates work after approved changes
- [ ] All tests pass
```

---

### Task ID: 065

- **Title**: Quality gate prompt generation for hive-mind
- **File**: src/autopilot/enforcement/quality_gates.py
- **Complete**: [x]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a scheduler, I want quality gates injected into hive-mind objectives, so that every worker runs linting, type checking, and tests before reporting completion.
- **Outcome (what this delivers)**: Quality gate prompt generator that builds dynamic quality gate instructions from project config for injection into hive-mind objectives.

#### Prompt:

```markdown
**Objective:** Implement quality gate prompt generation per RFC Section 3.5.3.

**File to Create/Modify:** `src/autopilot/enforcement/quality_gates.py`

**Specification References:**
- RFC Section 3.5.3: Quality gate prompt generation
- Discovery: build_quality_gate_prompt() replacing hardcoded suffix

**Prerequisite Requirements:**
1. Task 002 must be complete (config with quality_gates)
2. Write tests in `tests/enforcement/test_quality_gates.py`

**Detailed Instructions:**
1. Implement `QualityGateBuilder`:
   - `build_prompt(config: QualityGatesConfig) -> str` generates agent instructions
   - Enumerate all gate commands with numbering
   - Include stage-and-commit instruction for auto-fixes
   - Support per-project-type gate definitions
2. Replace the RepEngine hardcoded `_QUALITY_GATE_SUFFIX`
3. Gate ordering: pre_commit -> type_check -> test -> all

**Acceptance Criteria:**
- [ ] Quality gate prompt includes all configured gates
- [ ] Prompt format matches Discovery specification
- [ ] Per-project-type gates work (Python vs TypeScript)
- [ ] All tests pass
```

---

### Task ID: 066

- **Title**: Enforcement metrics collection to SQLite
- **File**: src/autopilot/enforcement/metrics.py
- **Complete**: [x]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a technical architect, I want enforcement metrics tracked over time, so that I can see whether code quality is improving sprint over sprint.
- **Outcome (what this delivers)**: Metrics collector that stores per-category violation counts in SQLite for trend analysis.

#### Prompt:

```markdown
**Objective:** Implement enforcement metrics collection and storage.

**File to Create/Modify:** `src/autopilot/enforcement/metrics.py`

**Specification References:**
- RFC Section 3.4.2: enforcement_metrics table
- RFC Section 3.5.3: Metrics collection at reporting step
- Discovery: Quality metrics (violation density, hook bypass attempts)

**Prerequisite Requirements:**
1. Tasks 006, 056 must be complete (db, engine)
2. Write tests in `tests/enforcement/test_metrics.py`

**Detailed Instructions:**
1. Implement `EnforcementMetricsCollector`:
   - `record_check(project_id: str, results: CheckResult)` stores in SQLite
   - One row per category per check run
   - `get_trend(project_id, category, days) -> list[MetricPoint]`
   - `get_summary(project_id) -> MetricsSummary` with per-category counts
   - `violation_density(project_id) -> float` violations per 1K lines
2. MetricPoint: timestamp, violation_count, files_scanned
3. MetricsSummary: by_category, total_violations, trend_direction

**Acceptance Criteria:**
- [ ] Metrics persist in SQLite enforcement_metrics table
- [ ] Trend queries return correct time-series data
- [ ] Violation density calculation is accurate
- [ ] All tests pass
```

---

### Task ID: 067

- **Title**: Enforce CLI commands (setup, check, report)
- **File**: src/autopilot/cli/enforce.py
- **Complete**: [x]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a technical architect, I want CLI commands for enforcement setup, checking, and reporting, so that I can manage anti-pattern enforcement from the terminal.
- **Outcome (what this delivers)**: The `autopilot enforce` subcommand group with setup, check, report, and update commands.

#### Prompt:

```markdown
**Objective:** Implement enforcement CLI commands.

**File to Create/Modify:** `src/autopilot/cli/enforce.py`

**Specification References:**
- RFC Appendix B: enforce setup|check|report [--update]
- RFC Section 3.5.3: Integration with autonomous pipeline

**Prerequisite Requirements:**
1. Tasks 009, 056, 066 must be complete (display, engine, metrics)
2. Write tests in `tests/cli/test_enforce.py`

**Detailed Instructions:**
1. `enforce setup [--project NAME]`: Configure all 5 enforcement layers
2. `enforce check [--category CAT] [--fix]`: Run checks, optionally auto-fix
3. `enforce report [--category CAT] [--days N]`: Show trend analysis with Rich tables
4. `enforce update`: Refresh enforcement config from latest template
5. All commands use Rich for output formatting

**Acceptance Criteria:**
- [ ] enforce setup configures all layers
- [ ] enforce check shows violations by category
- [ ] enforce report shows trends with charts
- [ ] --fix flag applies auto-fixes
- [ ] All tests pass
```

---

### Task ID: 068

- **Title**: UAT spec index for Discovery and UX Design documents
- **File**: src/autopilot/uat/spec_index.py
- **Complete**: [ ]
- **Sprint Points**: 3
- **Spec References**: UAT Discovery: Building the Initial Matrix (Discovery and UX extraction)

- **User Story (business-facing)**: As a UAT agent, I want spec indices for the Discovery and UX Design documents, so that traceability covers all three specification sources.
- **Outcome (what this delivers)**: Spec index builders for Discovery document (ADRs, architecture, risk register) and UX Design document (REPL, dashboard, workflows, errors).

#### Prompt:

```markdown
**Objective:** Extend spec index builder for Discovery and UX Design documents.

**File to Create/Modify:** `src/autopilot/uat/spec_index.py`

**Specification References:**
- UAT Discovery: Building the Initial Matrix (Discovery and UX extraction points)
- UAT Discovery: Estimated Matrix Size (~20 Discovery, ~60 UX requirements)

**Prerequisite Requirements:**
1. Task 046 must be complete (RFC index builder)
2. Write tests in `tests/uat/test_spec_index.py`

**Detailed Instructions:**
1. Add `build_discovery_index(path: Path) -> SpecIndex`:
   - Extract ADR decisions as constraints
   - Extract architecture requirements from package structure
   - Extract risk mitigations as defensive requirements
2. Add `build_ux_index(path: Path) -> SpecIndex`:
   - Extract REPL behavior requirements (Section 3)
   - Extract dashboard layout constraints (Section 4)
   - Extract workflow UX requirements (Section 5)
   - Extract error handling requirements (Section 8)
3. Merge all indices into a combined spec index
4. Store at .autopilot/uat/spec-index/discovery-index.json and ux-index.json

**UAT Acceptance Criteria:**
- [ ] Discovery ADRs and architecture are indexed
- [ ] UX Design sections are indexed
- [ ] Combined index contains all three sources
- [ ] All tests pass
```

---

### Task ID: 069

- **Title**: UAT traceability matrix data model and storage
- **File**: src/autopilot/uat/traceability.py
- **Complete**: [ ]
- **Sprint Points**: 5
- **Spec References**: UAT Discovery: Specification Traceability Matrix Design, TraceabilityEntry dataclass

- **User Story (business-facing)**: As a UAT agent, I want a persistent traceability matrix, so that spec coverage is tracked across all UAT runs and requirements are mapped to implementing tasks.
- **Outcome (what this delivers)**: Traceability matrix data model with JSON persistence, CRUD operations, coverage calculation, and gap detection.

#### Prompt:

```markdown
**Objective:** Implement the traceability matrix per UAT Discovery specification.

**File to Create/Modify:** `src/autopilot/uat/traceability.py`

**Specification References:**
- UAT Discovery: Specification Traceability Matrix Design
- UAT Discovery: TraceabilityEntry and TraceabilityMatrix dataclasses
- UAT Discovery: Matrix Structure section

**Prerequisite Requirements:**
1. Tasks 030, 046, 068 must be complete (spec engine, all indices)
2. Write tests in `tests/uat/test_traceability.py`

**Detailed Instructions:**
1. Implement `TraceabilityEntry` per UAT Discovery:
   - spec_id, spec_document, spec_section, requirement_text
   - implementing_tasks, uat_status, uat_score, last_tested, test_files, notes
2. Implement `TraceabilityMatrix` per UAT Discovery:
   - entries, generated_at, total_requirements, requirements_covered, requirements_passing
   - coverage_percentage, pass_percentage
3. CRUD operations:
   - `initialize_matrix(spec_indices: list[SpecIndex]) -> TraceabilityMatrix`
   - `update_entry(task_id, uat_result)` updates status after UAT run
   - `get_coverage() -> CoverageReport`
   - `get_gaps() -> list[TraceabilityEntry]` uncovered requirements
4. Store at .autopilot/uat/traceability.json
5. Support human overrides with audit trail

**UAT Acceptance Criteria:**
- [ ] Matrix contains entries from all three spec documents
- [ ] Coverage calculation is accurate
- [ ] Gaps correctly identify uncovered requirements
- [ ] Human overrides are tracked
- [ ] JSON persistence works correctly
- [ ] All tests pass
```

---

### Task ID: 070

- **Title**: UAT coverage and gaps reporters
- **File**: src/autopilot/uat/reporter.py
- **Complete**: [ ]
- **Sprint Points**: 3
- **Spec References**: UAT Discovery: Coverage view, Gaps view output formats

- **User Story (business-facing)**: As a technical architect, I want to see spec coverage progress and requirement gaps, so that I know which specifications are verified and which need attention.
- **Outcome (what this delivers)**: Coverage and gaps reporters that render traceability matrix data as Rich terminal output with progress bars per spec section.

#### Prompt:

```markdown
**Objective:** Implement coverage and gaps reporters for the traceability matrix.

**File to Create/Modify:** `src/autopilot/uat/reporter.py`

**Specification References:**
- UAT Discovery: /autopilot-uat --coverage output format
- UAT Discovery: /autopilot-uat --gaps output format

**Prerequisite Requirements:**
1. Tasks 049, 069 must be complete (reporter base, traceability matrix)
2. Write tests in `tests/uat/test_reporter.py`

**Detailed Instructions:**
1. Add to `UATReporter`:
   - `render_coverage(matrix: TraceabilityMatrix) -> str` coverage view with progress bars per section
   - `render_gaps(matrix: TraceabilityMatrix, phase: str | None) -> str` uncovered requirements
   - `render_sprint_report(results: list[UATResult], matrix: TraceabilityMatrix) -> str` sprint-level aggregation
2. Coverage output matches UAT Discovery format (section name, progress bar, percentage)
3. Gaps output separates high priority (current phase) from future phases
4. Add `--coverage` and `--gaps` flags to UAT pipeline CLI

**UAT Acceptance Criteria:**
- [ ] Coverage view shows progress bars per spec section
- [ ] Gaps view separates current phase from future
- [ ] Sprint report aggregates multiple task results
- [ ] Output matches UAT Discovery UX specification
- [ ] All tests pass
```
