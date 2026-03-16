## Summary (tasks-8.md)

- **Tasks in this file**: 10
- **Task IDs**: 071 - 080
- **Total Points**: 38

### UAT Phase 3: Test Generators + Parallel Execution | Main Phase 6: Discovery Integration

---

## Tasks

### Task ID: 071

- **Title**: UAT behavioral test generator (from user stories)
- **File**: src/autopilot/uat/test_generator.py
- **Complete**: [x]
- **Sprint Points**: 3
- **Spec References**: UAT Discovery: Test Generator Category B (Behavioral Tests)

- **User Story (business-facing)**: As a UAT agent, I want to generate behavioral tests from user stories, so that the system verifies not just acceptance criteria but end-to-end user workflows.
- **Outcome (what this delivers)**: Behavioral test generator that converts user story "As a... I want... so that..." into executable pytest scenarios.

#### Prompt:

```markdown
**Objective:** Implement behavioral test generation from user stories.

**File to Create/Modify:** `src/autopilot/uat/test_generator.py`

**Specification References:**
- UAT Discovery: Test Generator Category B (Behavioral Tests)
- UAT Discovery: User story test examples

**Prerequisite Requirements:**
1. Task 047 must be complete (acceptance test generator)
2. Write tests in `tests/uat/test_test_generator.py`

**Detailed Instructions:**
1. Add `generate_behavioral_tests(context: TaskContext) -> GeneratedTestFile`:
   - Parse user story into Given-When-Then structure
   - "As a <role>" -> test context/fixture setup
   - "I want <action>" -> test action
   - "so that <outcome>" -> assertion
   - Generate pytest function with descriptive name
2. Create Jinja2 template `test-behavioral.py.j2`
3. Test names: `test_user_story_{task_id}_{action_slug}`

**UAT Acceptance Criteria:**
- [ ] User stories are parsed into testable components
- [ ] Generated tests follow Given-When-Then structure
- [ ] Test names are descriptive and unique
- [ ] Generated tests are valid Python
- [ ] All tests pass
```

---

### Task ID: 072

- **Title**: UAT compliance test generator (from RFC specs)
- **File**: src/autopilot/uat/test_generator.py
- **Complete**: [x]
- **Sprint Points**: 3
- **Spec References**: UAT Discovery: Test Generator Category C (Specification Compliance Tests)

- **User Story (business-facing)**: As a UAT agent, I want to generate compliance tests from RFC specifications, so that implementation details are verified against the technical specification.
- **Outcome (what this delivers)**: Compliance test generator that creates pytest tests from RFC requirements (config fields, SQL schemas, command interfaces).

#### Prompt:

```markdown
**Objective:** Implement specification compliance test generation.

**File to Create/Modify:** `src/autopilot/uat/test_generator.py`

**Specification References:**
- UAT Discovery: Test Generator Category C (Specification Compliance Tests)
- UAT Discovery: RFC compliance test examples (SQLite schema, config fields)

**Prerequisite Requirements:**
1. Tasks 046, 047 must be complete (spec index, acceptance generator)
2. Write tests in `tests/uat/test_test_generator.py`

**Detailed Instructions:**
1. Add `generate_compliance_tests(context: TaskContext, spec_index: SpecIndex) -> GeneratedTestFile`:
   - For config fields (RFC 3.4.1): test field existence, types, defaults
   - For SQL tables (RFC 3.4.2): test table existence, column names, constraints
   - For commands (Appendix B): test command registration and help output
   - For success metrics (Section 10): test measurement infrastructure exists
2. Create Jinja2 template `test-compliance.py.j2`
3. Test names: `test_rfc_{section}_{requirement_slug}`

**UAT Acceptance Criteria:**
- [ ] Config field compliance tests verify types and defaults
- [ ] SQL schema tests verify tables and columns
- [ ] Command tests verify CLI registration
- [ ] All generated tests are valid Python
- [ ] All tests pass
```

---

### Task ID: 073

- **Title**: UAT UX compliance test generator
- **File**: src/autopilot/uat/test_generator.py
- **Complete**: [x]
- **Sprint Points**: 3
- **Spec References**: UAT Discovery: Test Generator Category D (UX Compliance Tests)

- **User Story (business-facing)**: As a UAT agent, I want to generate UX compliance tests, so that CLI output, REPL behavior, and terminal dimensions are verified against the UX design spec.
- **Outcome (what this delivers)**: UX compliance test generator that creates tests for dashboard dimensions, prompt format, keyboard shortcuts, and output patterns.

#### Prompt:

```markdown
**Objective:** Implement UX compliance test generation.

**File to Create/Modify:** `src/autopilot/uat/test_generator.py`

**Specification References:**
- UAT Discovery: Test Generator Category D (UX Compliance Tests)
- UAT Discovery: UX compliance test examples (80x24 dashboard, prompt format)

**Prerequisite Requirements:**
1. Tasks 047, 068 must be complete (acceptance generator, UX index)
2. Write tests in `tests/uat/test_test_generator.py`

**Detailed Instructions:**
1. Add `generate_ux_tests(context: TaskContext, ux_index: SpecIndex) -> GeneratedTestFile`:
   - Dashboard constraints: fits 80x24, correct column widths
   - Prompt format: shows project name, running agent count
   - Output patterns: error formatting, progress indicators
   - Notification tiers: correct delivery mechanism per tier
2. Create Jinja2 template `test-ux.py.j2`
3. Test names: `test_ux_{section}_{requirement_slug}`

**UAT Acceptance Criteria:**
- [ ] Dashboard dimension tests are generated
- [ ] Prompt format tests verify UX spec
- [ ] Output pattern tests check formatting
- [ ] All generated tests are valid Python
- [ ] All tests pass
```

---

### Task ID: 074

- **Title**: UAT batch mode with swarm coordination
- **File**: src/autopilot/uat/batch.py
- **Complete**: [x]
- **Sprint Points**: 5
- **Spec References**: UAT Discovery: Parallel Execution Model, Swarm Coordination

- **User Story (business-facing)**: As a technical architect, I want to run UAT across an entire sprint's completed tasks in parallel, so that specification compliance is verified efficiently without sequential bottlenecks.
- **Outcome (what this delivers)**: Batch UAT mode using claude-flow swarm for parallel execution across multiple completed tasks.

#### Prompt:

```markdown
**Objective:** Implement batch UAT with parallel execution.

**File to Create/Modify:** `src/autopilot/uat/batch.py`

**Specification References:**
- UAT Discovery: Parallel Execution Model
- UAT Discovery: Swarm Coordination (hierarchical, 4 workers)
- UAT Discovery: Resource Isolation (sonnet model, 20 max turns)

**Prerequisite Requirements:**
1. Task 050 must be complete (single-task pipeline)
2. Write tests in `tests/uat/test_batch.py`

**Detailed Instructions:**
1. Implement `BatchUAT`:
   - `run_sprint(sprint_id: str, project_dir: Path) -> list[UATResult]`
   - Find all completed tasks in sprint
   - Run UAT pipeline for each in parallel (configurable worker count)
   - Aggregate results
   - `run_range(start_id: str, end_id: str, project_dir) -> list[UATResult]`
   - `run_all(project_dir) -> list[UATResult]` all completed tasks
2. Parallel execution using concurrent.futures.ThreadPoolExecutor
3. Optional: claude-flow swarm integration for larger batches
4. Progress tracking: show overall progress bar
5. Add `--sprint N`, `--all`, range (040-050) flags to UAT CLI

**UAT Acceptance Criteria:**
- [ ] Batch UAT runs multiple tasks in parallel
- [ ] Progress bar shows overall progress
- [ ] Results are correctly aggregated
- [ ] Worker count is configurable
- [ ] All tests pass
```

---

### Task ID: 075

- **Title**: UAT automatic trigger hooks (post-task-complete)
- **File**: src/autopilot/uat/triggers.py
- **Complete**: [x]
- **Sprint Points**: 3
- **Spec References**: UAT Discovery: UAT Trigger System, Automatic mode

- **User Story (business-facing)**: As a system operator, I want UAT to run automatically when tasks are completed, so that specification drift is caught immediately without manual intervention.
- **Outcome (what this delivers)**: Automatic UAT trigger that fires when task status changes from incomplete to complete, using file watching or hook registration.

#### Prompt:

```markdown
**Objective:** Implement automatic UAT triggering on task completion.

**File to Create/Modify:** `src/autopilot/uat/triggers.py`

**Specification References:**
- UAT Discovery: UAT Trigger System (automatic, manual, batch modes)
- UAT Discovery: claude-flow hooks post-task integration

**Prerequisite Requirements:**
1. Tasks 021, 050 must be complete (task parser, UAT pipeline)
2. Write tests in `tests/uat/test_triggers.py`

**Detailed Instructions:**
1. Implement `UATTrigger`:
   - `register_hook(project_dir: Path)` sets up post-task-complete trigger
   - `on_task_complete(task_id: str, project_dir: Path)` runs UAT pipeline
   - Trigger detection: monitor task file changes (Complete: [ ] -> [x])
2. Support disabling auto-trigger via config: uat.auto_trigger: false
3. Queue mechanism: if UAT is already running, queue next task
4. Integrate with session management to track UAT sessions
5. Skip UAT for trivial tasks (1-point documentation updates, configurable)

**UAT Acceptance Criteria:**
- [ ] UAT triggers automatically on task completion
- [ ] Auto-trigger is configurable (on/off)
- [ ] Queue prevents concurrent UAT conflicts
- [ ] Trivial task skipping works
- [ ] All tests pass
```

---

### Task ID: 076

- **Title**: UAT feedback loop (advisory and gated modes)
- **File**: src/autopilot/uat/feedback.py
- **Complete**: [x]
- **Sprint Points**: 5
- **Spec References**: UAT Discovery: Feedback Loop, Advisory mode, Gated mode

- **User Story (business-facing)**: As a technical architect, I want configurable UAT feedback modes, so that I can choose between advisory reporting and strict gating that reverts failed tasks.
- **Outcome (what this delivers)**: Feedback loop implementing both advisory mode (log and continue) and gated mode (revert task status on failure) with configurable threshold.

#### Prompt:

```markdown
**Objective:** Implement UAT feedback loop with advisory and gated modes.

**File to Create/Modify:** `src/autopilot/uat/feedback.py`

**Specification References:**
- UAT Discovery: Feedback Loop section
- UAT Discovery: Advisory mode vs Gated mode
- UAT Discovery: UAT config schema (mode, threshold)
- UAT Discovery: Task template updates with UAT-specific fields

**Prerequisite Requirements:**
1. Tasks 021, 048 must be complete (task parser, test executor)
2. Write tests in `tests/uat/test_feedback.py`

**Detailed Instructions:**
1. Implement `FeedbackLoop`:
   - `process_result(result: UATResult, mode: str, threshold: float)`
   - Advisory mode: log result, update UAT Status field in task, continue
   - Gated mode: if score < threshold, revert Complete to [ ], append UAT feedback section
   - Update task file with UAT Status (PASS/FAIL/PARTIAL)
2. UAT feedback section format per UAT Discovery specification:
   - "#### UAT Feedback ({date}):" with failure details and fix suggestions
3. Integrate with task index updates (adjust points complete if task reverted)
4. Score composition: optional integration with verification-quality truth score
5. Config: mode (advisory/gated), threshold (default 0.90)

**UAT Acceptance Criteria:**
- [ ] Advisory mode logs without blocking
- [ ] Gated mode reverts task status on failure
- [ ] UAT feedback is appended to task file
- [ ] Task index is updated when tasks are reverted
- [ ] Threshold is configurable
- [ ] All tests pass
```

---

### Task ID: 077

- **Title**: Norwood discovery agent prompt template
- **File**: templates/python/agents/norwood-discovery.md
- **Complete**: [x]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a technical architect, I want a discovery agent template, so that `autopilot discover` launches a properly configured Norwood session for technical analysis.
- **Outcome (what this delivers)**: Norwood discovery agent prompt template that produces structured discovery documents with phases, ADRs, and implementation plans.

#### Prompt:

```markdown
**Objective:** Create the Norwood discovery agent prompt template.

**File to Create/Modify:** `templates/python/agents/norwood-discovery.md`

**Specification References:**
- Discovery: Discovery Workflow Integration section
- Discovery: start_discovery() function signature
- RFC Section 6 Phase 5: Norwood discovery agent prompt template

**Prerequisite Requirements:**
1. Task 007 must be complete (template structure)
2. Review existing Norwood prompt patterns from RepEngine

**Detailed Instructions:**
1. Write Norwood system prompt with sections:
   - Role: Technical discovery agent for codebase analysis
   - Output format: Standard discovery document structure (problem, solution, architecture, ADRs, phases, risks)
   - Tool usage: File reading, code analysis, dependency scanning
   - Context injection points: project name, root, type, existing architecture
2. Template variables for project-specific context
3. Discovery document output format matching the project's actual discovery.md structure
4. Include instruction to write discovery to specified output path

**Acceptance Criteria:**
- [ ] Prompt produces structured discovery documents
- [ ] Template variables allow project customization
- [ ] Output format matches existing discovery document patterns
- [ ] Prompt is model-agnostic (works with opus and sonnet)
```

---

### Task ID: 078

- **Title**: Discover CLI commands
- **File**: src/autopilot/cli/discover.py
- **Complete**: [x]
- **Sprint Points**: 5

- **User Story (business-facing)**: As a technical architect, I want to launch and monitor discovery sessions from the CLI, so that technical analysis happens within the autopilot workflow and feeds into task creation.
- **Outcome (what this delivers)**: The `autopilot plan discover` and `autopilot plan tasks` commands for launching Norwood sessions and converting findings to tasks.

#### Prompt:

```markdown
**Objective:** Implement discovery workflow CLI commands.

**File to Create/Modify:** `src/autopilot/cli/discover.py`

**Specification References:**
- RFC Appendix B: plan discover|tasks|estimate|enqueue|show
- Discovery: Discovery Workflow Integration (start_discovery, session monitoring)
- UX Design Section 5.2: Planning Pipeline

**Prerequisite Requirements:**
1. Tasks 004, 025, 038 must be complete (subprocess, discovery-to-task, sessions)
2. Write tests in `tests/cli/test_discover.py`

**Detailed Instructions:**
1. `plan discover PROJECT TOPIC` command:
   - Launch Norwood discovery session as background Claude instance
   - Register as discovery session in session manager
   - Show session ID and PID
   - `--wait` flag to block until discovery completes
2. `plan tasks --from-discovery PATH` command:
   - Parse discovery document
   - Interactive confirmation of phases and tasks
   - Generate task files
3. `plan estimate` command: launch Shelly for batch estimation
4. `plan show` command: display current plan (discovery + tasks + sprint status)
5. All commands track progress via session management

**Acceptance Criteria:**
- [ ] plan discover launches background Claude session
- [ ] Discovery session is tracked in session manager
- [ ] plan tasks converts discovery to task files
- [ ] plan show displays current planning state
- [ ] All tests pass
```

---

### Task ID: 079

- **Title**: Discovery-to-task conversion pipeline (end-to-end)
- **File**: src/autopilot/core/discovery.py
- **Complete**: [x]
- **Sprint Points**: 5

- **User Story (business-facing)**: As a technical architect, I want automated conversion from discovery documents to structured tasks, so that the entire planning pipeline flows seamlessly from analysis to execution.
- **Outcome (what this delivers)**: End-to-end pipeline that reads discovery documents, extracts deliverables per phase, generates tasks with spec references, and writes properly formatted task files.

#### Prompt:

```markdown
**Objective:** Implement the complete discovery-to-task conversion pipeline.

**File to Create/Modify:** `src/autopilot/core/discovery.py`

**Specification References:**
- Discovery: Discovery Workflow Integration (conversion flow)
- Discovery: Task create --from-discovery output example
- Task Workflow System: Task Creation Guidelines

**Prerequisite Requirements:**
1. Tasks 021, 025 must be complete (task parser, basic conversion)
2. Write tests in `tests/core/test_discovery.py`

**Detailed Instructions:**
1. Implement `DiscoveryConverter`:
   - `parse(path: Path) -> DiscoveryDocument` parses discovery markdown
   - `extract_phases(doc: DiscoveryDocument) -> list[Phase]` identifies implementation phases
   - `generate_tasks(phases: list[Phase], project_config) -> list[Task]` creates tasks
   - `write_files(tasks: list[Task], output_dir: Path) -> list[Path]` writes task files
2. Phase extraction: identify "Phase N:" sections, extract deliverable checkboxes
3. Task generation: one task per deliverable, with spec references extracted from phase context
4. Sprint point estimation: distribute phase estimate across deliverables proportionally
5. Support merging into existing task files (continuing IDs)

**Acceptance Criteria:**
- [ ] Discovery documents parse into phases and deliverables
- [ ] Tasks include spec references from discovery context
- [ ] Sprint points are distributed proportionally
- [ ] Merge with existing tasks works correctly
- [ ] All tests pass
```

---

### Task ID: 080

- **Title**: Shelly estimation agent integration
- **File**: src/autopilot/core/estimation.py
- **Complete**: [x]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a technical architect, I want AI-assisted task estimation, so that sprint points are consistently assessed based on complexity analysis rather than gut feeling.
- **Outcome (what this delivers)**: Integration with a Shelly-style estimation agent that analyzes task complexity and suggests Fibonacci sprint points.

#### Prompt:

```markdown
**Objective:** Implement estimation agent integration for task pointing.

**File to Create/Modify:** `src/autopilot/core/estimation.py`

**Specification References:**
- Task Workflow System: Sprint Points Scale (Fibonacci)
- Discovery: Shelly estimation agent integration
- RFC Section 6 Phase 5: Shelly estimation agent

**Prerequisite Requirements:**
1. Tasks 021, 031 must be complete (task parser, agent invoker)
2. Write tests in `tests/core/test_estimation.py`

**Detailed Instructions:**
1. Implement `EstimationAgent`:
   - `estimate_task(task: Task, project_context: str) -> EstimationResult`
   - Invoke Claude with estimation prompt (complexity analysis, dependency assessment)
   - Parse result into Fibonacci point recommendation with rationale
   - `batch_estimate(tasks: list[Task]) -> list[EstimationResult]`
2. EstimationResult: task_id, recommended_points, rationale, complexity_factors, confidence
3. Estimation prompt includes: task description, file path, dependencies, project type
4. Validate output against Fibonacci scale (1,2,3,5,8)
5. Store estimation rationale for sprint planning context

**Acceptance Criteria:**
- [ ] Estimation agent produces Fibonacci-valid suggestions
- [ ] Rationale explains complexity factors
- [ ] Batch estimation works for multiple tasks
- [ ] All tests pass with mocked agent calls
```
