## Summary (tasks-5.md)

- **Tasks in this file**: 10
- **Task IDs**: 041 - 050
- **Total Points**: 36

### Main Phase 3: Reporting + UAT Phase 1 Completion / Phase 2 Start: Spec Coverage

---

## Tasks

### Task ID: 041

- **Title**: Daily summary report aggregation
- **File**: src/autopilot/reporting/daily_summary.py
- **Complete**: [ ]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a PL agent, I want a daily summary of all cycles, so that I have context about what was accomplished and what failed when planning the next cycle.
- **Outcome (what this delivers)**: Daily summary generator that aggregates cycle reports into a single PL-consumable context document.

#### Prompt:

```markdown
**Objective:** Implement daily summary report aggregation for PL context.

**File to Create/Modify:** `src/autopilot/reporting/daily_summary.py`

**Specification References:**
- Discovery: Reporting and Metrics (daily summary for PL context)
- RFC Section 3.6: Daily Summary (Scheduler -> PL)

**Prerequisite Requirements:**
1. Task 040 must be complete (cycle reports)
2. Write tests in `tests/reporting/test_daily_summary.py`

**Detailed Instructions:**
1. Implement `DailySummaryGenerator`:
   - `generate(project_dir: Path, date: date) -> str` produces summary markdown
   - Aggregate all cycle reports for the given date
   - Include: cycles run, total dispatches, success/failure counts, agent breakdown, notable errors
   - Format optimized for PL prompt injection (concise, structured)
2. Summary is regenerated each cycle for PL to read

**Acceptance Criteria:**
- [ ] Daily summary aggregates all cycle reports for a date
- [ ] Format is concise enough for agent prompt injection
- [ ] Summary includes actionable information (failures, blockers)
- [ ] All tests pass
```

---

### Task ID: 042

- **Title**: Velocity reporting and forecasting
- **File**: src/autopilot/reporting/velocity.py
- **Complete**: [ ]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a technical architect, I want velocity charts and forecasts, so that I can predict project completion timelines and adjust sprint capacity.
- **Outcome (what this delivers)**: Velocity reporting with sprint history, trend analysis, and completion forecasting from SQLite data.

#### Prompt:

```markdown
**Objective:** Implement velocity reporting with trend analysis and forecasting.

**File to Create/Modify:** `src/autopilot/reporting/velocity.py`

**Specification References:**
- Discovery: Reporting and Metrics (velocity metrics)
- Discovery: VelocityTracker (rolling average, forecast)
- RFC Section 10: Success Metrics

**Prerequisite Requirements:**
1. Tasks 006, 024 must be complete (db, velocity tracker)
2. Write tests in `tests/reporting/test_velocity.py`

**Detailed Instructions:**
1. Implement `VelocityReporter`:
   - `sprint_history(project_id, limit) -> list[SprintSummary]` from SQLite
   - `velocity_trend(project_id) -> VelocityTrend` with rolling averages
   - `forecast_completion(remaining_points, project_id) -> CompletionForecast`
   - `generate_report(project_id) -> str` produces Rich-formatted report
2. VelocityTrend: sprints, average, trend_direction, confidence
3. CompletionForecast: estimated_sprints, estimated_date, confidence_range

**Acceptance Criteria:**
- [ ] Sprint history queries SQLite correctly
- [ ] Rolling average velocity calculated correctly
- [ ] Completion forecast is reasonable
- [ ] Report renders with Rich formatting
- [ ] All tests pass
```

---

### Task ID: 043

- **Title**: Decision log reporting with rotation
- **File**: src/autopilot/reporting/decision_log.py
- **Complete**: [ ]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a technical architect, I want a searchable decision audit trail, so that I can understand why specific technical choices were made during autonomous execution.
- **Outcome (what this delivers)**: Decision log reporter integrated with the coordination decision log, providing search, filtering, and trend analysis.

#### Prompt:

```markdown
**Objective:** Implement decision log reporting with search and trend analysis.

**File to Create/Modify:** `src/autopilot/reporting/decision_log.py`

**Specification References:**
- Discovery: Decision log with rotation (from reports.py)
- RFC Section 3.6: Decision Log channel

**Prerequisite Requirements:**
1. Task 020 must be complete (coordination decisions)
2. Write tests in `tests/reporting/test_decision_log.py`

**Detailed Instructions:**
1. Implement `DecisionLogReporter`:
   - `recent_decisions(project_dir, limit) -> list[Decision]`
   - `decisions_by_agent(project_dir, agent) -> list[Decision]`
   - `search_decisions(project_dir, query) -> list[Decision]`
   - `decision_trend(project_dir) -> DecisionTrend` (decisions per cycle, by category)
   - `generate_report(project_dir) -> str` Rich-formatted summary
2. Integrate with rotation from coordination/decisions.py

**Acceptance Criteria:**
- [ ] Decision queries return correct results
- [ ] Search works across current and archived logs
- [ ] Trend analysis shows decision frequency patterns
- [ ] All tests pass
```

---

### Task ID: 044

- **Title**: Dashboard -- 80x24 two-column layout
- **File**: src/autopilot/cli/display.py
- **Complete**: [ ]
- **Sprint Points**: 5

- **User Story (business-facing)**: As a technical architect, I want a compact dashboard that shows project health at a glance, so that I can assess status in under 2 seconds from any state.
- **Outcome (what this delivers)**: Rich-rendered dashboard fitting 80x24 with project status, active sessions, recent cycles, and task progress in a two-column layout.

#### Prompt:

```markdown
**Objective:** Implement the compact dashboard per UX Design Section 4.

**File to Create/Modify:** `src/autopilot/cli/display.py`

**Specification References:**
- UX Design Section 4: Dashboard Design (80x24, two-column layout)
- UX Design Section 4.1: Default View (project health, active work, recent activity)
- UX Design Section 4.2: Expanded View (detailed metrics)
- RFC Section 7.2: Dashboard render time < 2 seconds

**Prerequisite Requirements:**
1. Tasks 009, 038 must be complete (display helpers, session manager)
2. Write tests in `tests/cli/test_display.py`

**Detailed Instructions:**
1. Implement `render_dashboard(project_state, width=80, height=24) -> str`:
   - Left column: Project name, status, active sessions count, current sprint progress bar
   - Right column: Recent cycle outcomes (last 5), task board summary (pending/active/done)
   - Bottom: Notifications/alerts strip
2. Rich Layout with two columns at 72 characters total (UX Design)
3. Support `--expand` for detailed view with velocity chart
4. Handle edge cases: no project selected, no sessions, no cycles

**Acceptance Criteria:**
- [ ] Dashboard fits within 80x24 terminal
- [ ] Two-column layout renders correctly
- [ ] All data sections are populated from real state
- [ ] Render time < 2 seconds
- [ ] Empty states show helpful messages
- [ ] All tests pass

**UAT Acceptance Criteria:**
- [ ] UX 4.1: Default dashboard renders within 80x24
- [ ] UX 4.2: Expanded view shows additional metrics
```

---

### Task ID: 045

- **Title**: CLI commands -- start, stop, pause, resume, cycle
- **File**: src/autopilot/cli/session.py
- **Complete**: [ ]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a technical architect, I want top-level commands for controlling autonomous execution, so that starting and stopping the autopilot is as simple as `autopilot start`.
- **Outcome (what this delivers)**: Convenience commands that wrap session management for common operations: start daemon, stop daemon, single cycle execution.

#### Prompt:

```markdown
**Objective:** Add convenience commands for common session operations.

**File to Create/Modify:** `src/autopilot/cli/app.py`, `src/autopilot/cli/session.py`

**Specification References:**
- RFC Appendix B: Top-level start, watch commands
- Discovery: autopilot start/stop/pause/resume/cycle/plan/execute

**Prerequisite Requirements:**
1. Task 039 must be complete (session CLI)
2. Write tests in `tests/cli/test_session.py`

**Detailed Instructions:**
1. Register top-level aliases in app.py:
   - `autopilot start` -> `session start` for active project
   - `autopilot stop` -> `session stop` for active project
   - `autopilot cycle` -> run single cycle without daemon
   - `autopilot watch` -> attach to running session with live dashboard
2. `cycle` command: runs one scheduler cycle directly (not as daemon)
3. `watch` command: combines session attach with dashboard updates
4. All commands infer project from active context or --project flag

**Acceptance Criteria:**
- [ ] `autopilot start` starts daemon for active project
- [ ] `autopilot stop` stops running daemon
- [ ] `autopilot cycle` executes single cycle inline
- [ ] All tests pass
```

---

### Task ID: 046

- **Title**: UAT spec index builder for RFC document
- **File**: src/autopilot/uat/spec_index.py
- **Complete**: [ ]
- **Sprint Points**: 5
- **Spec References**: UAT Discovery: Building the Initial Matrix, Estimated Matrix Size

- **User Story (business-facing)**: As a UAT agent, I want a structured index of all RFC requirements, so that I can map tasks to specific testable requirements for coverage tracking.
- **Outcome (what this delivers)**: RFC spec index builder that parses the RFC document sections into a structured index of testable requirements stored as JSON.

#### Prompt:

```markdown
**Objective:** Build the specification index for the RFC document.

**File to Create/Modify:** `src/autopilot/uat/spec_index.py`

**Specification References:**
- UAT Discovery: Building the Initial Matrix (RFC extraction points)
- UAT Discovery: Estimated Matrix Size (~80 RFC sections, ~65 testable)
- UAT Discovery: Spec index stored at .autopilot/uat/traceability.json

**Prerequisite Requirements:**
1. Task 030 must be complete (spec engine)
2. Write tests in `tests/uat/test_spec_index.py`

**Detailed Instructions:**
1. Implement `SpecIndexBuilder` class:
   - `build_rfc_index(rfc_path: Path) -> SpecIndex` parses RFC markdown
   - Extract sections by heading hierarchy (##, ###)
   - Identify testable requirements from: config fields (3.4.1), SQL tables (3.4.2), enforcement categories (3.5), commands (Appendix B), success metrics (Section 10)
   - Each requirement gets: spec_id, document, section, requirement_text, verification_type
2. `SpecIndex` model: entries list, generated_at, total_requirements, testable_count
3. Store index at `.autopilot/uat/spec-index/rfc-index.json`
4. Support incremental rebuild (only changed sections)

**UAT Acceptance Criteria:**
- [ ] RFC sections are correctly parsed and indexed
- [ ] Testable requirements are identified from config, SQL, and commands
- [ ] Index stores as valid JSON
- [ ] Rebuild detects spec changes
- [ ] All tests pass

**Session Awareness Instructions:**
1. Store index format for Discovery and UX index builders
```

---

### Task ID: 047

- **Title**: UAT basic test generator -- acceptance tests
- **File**: src/autopilot/uat/test_generator.py
- **Complete**: [ ]
- **Sprint Points**: 5
- **Spec References**: UAT Discovery: Test Generator, Category A: Acceptance Tests

- **User Story (business-facing)**: As a UAT agent, I want to generate pytest test cases from task acceptance criteria, so that each completed task's claims are independently verified.
- **Outcome (what this delivers)**: Test generator that converts task acceptance criteria into executable pytest test files using Jinja2 templates.

#### Prompt:

```markdown
**Objective:** Implement acceptance test generation from task criteria.

**File to Create/Modify:** `src/autopilot/uat/test_generator.py`

**Specification References:**
- UAT Discovery: Test Generator, Category A (Acceptance Tests)
- UAT Discovery: Test file organization (tests/uat/test_uat_task_{id}.py)

**Prerequisite Requirements:**
1. Task 029 must be complete (task context loader)
2. Write tests in `tests/uat/test_test_generator.py`

**Detailed Instructions:**
1. Implement `TestGenerator` class:
   - `generate_acceptance_tests(context: TaskContext) -> GeneratedTestFile`
   - Each acceptance criterion becomes a pytest test function
   - Test name format: `test_task_{id}_{criterion_slug}`
   - Docstring includes spec reference if available
   - Use Jinja2 templates from .claude/skills/autopilot-uat/resources/templates/
2. `GeneratedTestFile` model: file_path, test_count, test_names, source_code
3. Create Jinja2 template `test-acceptance.py.j2` for test file structure
4. Tests output to `tests/uat/test_uat_task_{id}.py`
5. Cap test generation at 5 tests per story point

**UAT Acceptance Criteria:**
- [ ] Acceptance criteria are converted to pytest functions
- [ ] Generated tests have descriptive names and docstrings
- [ ] Tests reference source spec sections
- [ ] Test count respects story point cap
- [ ] Generated test files are valid Python
- [ ] All tests pass

**Session Awareness Instructions:**
1. Store test generation patterns for behavioral and compliance generators
```

---

### Task ID: 048

- **Title**: UAT test executor with pytest runner
- **File**: src/autopilot/uat/test_executor.py
- **Complete**: [ ]
- **Sprint Points**: 3
- **Spec References**: UAT Discovery: Test Executor, UATResult dataclass

- **User Story (business-facing)**: As a UAT agent, I want to execute generated tests and collect structured results, so that I can produce pass/fail reports with actionable feedback.
- **Outcome (what this delivers)**: Test executor that runs pytest with JSON output and collects UATResult with category-level breakdowns.

#### Prompt:

```markdown
**Objective:** Implement UAT test executor with structured result collection.

**File to Create/Modify:** `src/autopilot/uat/test_executor.py`

**Specification References:**
- UAT Discovery: Test Executor section
- UAT Discovery: UATResult, CategoryResult, TestFailure dataclasses

**Prerequisite Requirements:**
1. Task 047 must be complete (test generator)
2. Write tests in `tests/uat/test_test_executor.py`

**Detailed Instructions:**
1. Implement `TestExecutor` class:
   - `run(test_file: Path) -> UATResult` executes pytest with JSON output
   - Collect: overall_pass, score (0.0-1.0), test_count, pass/fail/skip counts
   - Category breakdown: acceptance, behavioral, compliance, ux
   - TestFailure details: test_name, category, spec_reference, expected, actual, suggestion
2. `UATResult` dataclass per UAT Discovery specification
3. Score calculation: pass_count / test_count
4. Timeout support: abort test execution after configurable limit (default 300s)

**UAT Acceptance Criteria:**
- [ ] Pytest runs and results are collected as UATResult
- [ ] Category breakdown is accurate
- [ ] Failures include actionable details
- [ ] Score calculation is correct
- [ ] Timeout aborts long-running tests
- [ ] All tests pass

**Session Awareness Instructions:**
1. Store result format for reporter integration
```

---

### Task ID: 049

- **Title**: UAT per-task reporter
- **File**: src/autopilot/uat/reporter.py
- **Complete**: [ ]
- **Sprint Points**: 3
- **Spec References**: UAT Discovery: UAT Reporter, Per-task report format

- **User Story (business-facing)**: As a technical architect, I want clear UAT reports for each task, so that I can see what passed, what failed, and exactly what needs fixing.
- **Outcome (what this delivers)**: Per-task UAT reporter that renders structured results as Rich terminal output matching the UAT Discovery report format.

#### Prompt:

```markdown
**Objective:** Implement per-task UAT report rendering.

**File to Create/Modify:** `src/autopilot/uat/reporter.py`

**Specification References:**
- UAT Discovery: UAT Reporter, Per-task report format
- UAT Discovery: UX Design for /autopilot-uat (terminal output format)

**Prerequisite Requirements:**
1. Tasks 009, 048 must be complete (display helpers, test executor)
2. Write tests in `tests/uat/test_reporter.py`

**Detailed Instructions:**
1. Implement `UATReporter` class:
   - `render_task_report(result: UATResult) -> str` produces Rich-formatted output
   - Sections: header with score, each test category with pass/fail, traceability, recommendation
   - Match the exact output format from UAT Discovery UX section
   - Color coding: green for pass, red for fail, yellow for partial
2. `render_to_markdown(result: UATResult) -> str` for file-based reports
3. Store reports at .autopilot/uat/reports/task-{id}-uat.md

**UAT Acceptance Criteria:**
- [ ] Report format matches UAT Discovery specification
- [ ] Pass/fail colors are correct
- [ ] Recommendations are actionable
- [ ] Markdown reports are stored for history
- [ ] All tests pass

**Session Awareness Instructions:**
1. Store report format for sprint-level aggregation
```

---

### Task ID: 050

- **Title**: UAT pipeline orchestration and /autopilot-uat command
- **File**: src/autopilot/uat/pipeline.py
- **Complete**: [ ]
- **Sprint Points**: 3
- **Spec References**: UAT Discovery: High-Level Flow, /autopilot-uat command integration

- **User Story (business-facing)**: As a technical architect, I want to run UAT on completed tasks with a single command, so that specification compliance is verified without manual test writing.
- **Outcome (what this delivers)**: End-to-end UAT pipeline that orchestrates context loading, spec cross-referencing, test generation, execution, and reporting for a single task.

#### Prompt:

```markdown
**Objective:** Implement the end-to-end UAT pipeline for single-task verification.

**File to Create/Modify:** `src/autopilot/uat/pipeline.py`

**Specification References:**
- UAT Discovery: High-Level Flow diagram
- UAT Discovery: /autopilot-uat {task_id} command
- UAT Discovery: UAT config schema (mode, threshold, categories)

**Prerequisite Requirements:**
1. Tasks 029, 030, 047, 048, 049 must be complete (context, spec engine, generator, executor, reporter)
2. Write tests in `tests/uat/test_pipeline.py`

**Detailed Instructions:**
1. Implement `UATPipeline` class:
   - `run(task_id: str, project_dir: Path) -> UATResult`
   - Steps: load context -> cross-reference specs -> generate tests -> execute -> report
   - Progress output during each step
   - Handle errors gracefully (UAT errors never block implementation)
2. Implement `/autopilot-uat` CLI integration:
   - `autopilot-uat TASK_ID` runs pipeline for single task
   - Rich progress display during execution
   - Final report output
3. UAT config from .autopilot/config.yaml uat section

**UAT Acceptance Criteria:**
- [ ] Full pipeline executes: context -> specs -> tests -> run -> report
- [ ] Errors in UAT pipeline do not block development
- [ ] Progress is displayed during execution
- [ ] Final report matches UAT Discovery format
- [ ] All tests pass

**Session Awareness Instructions:**
1. Store pipeline interface for batch mode and automatic triggers
```
