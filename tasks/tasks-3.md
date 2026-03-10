## Summary (tasks-3.md)

- **Tasks in this file**: 10
- **Task IDs**: 021 - 030
- **Total Points**: 37

### Main Phase 2: Task Management + UAT Phase 1: Foundation Start

---

## Tasks

### Task ID: 021

- **Title**: Task file parser and data model
- **File**: src/autopilot/core/task.py
- **Complete**: [ ]
- **Sprint Points**: 5

- **User Story (business-facing)**: As a technical architect, I want the system to parse task files, so that tasks can be programmatically read, queried, and updated for sprint planning and autonomous dispatch.
- **Outcome (what this delivers)**: Markdown task file parser that reads the tasks-workflow.md format into structured data, supporting task queries, status updates, and index maintenance.

#### Prompt:

```markdown
**Objective:** Implement task file parsing and manipulation for the RepEngine-format task markdown.

**File to Create/Modify:** `src/autopilot/core/task.py`

**Specification References:**
- Task Workflow System (.claude/knowledge/workflows/tasks-workflow.md): Full task template
- Discovery: Task Management section (task file format, sprint planning)
- RFC Section 6 Phase 2: Task file parsing deliverables

**Prerequisite Requirements:**
1. Tasks 002, 003, 005 must be complete (config, models, paths)
2. Write tests in `tests/core/test_task.py`

**Detailed Instructions:**
1. Implement `TaskParser` class:
   - `parse_task_file(path: Path) -> list[Task]` parses tasks-N.md
   - `parse_task_index(path: Path) -> TaskIndex` parses tasks-index.md
   - `find_next_pending(task_dir: Path) -> Task | None` finds first incomplete task
   - `find_task_by_id(task_dir: Path, task_id: str) -> Task | None`
2. `Task` model: id, title, file_path, complete, sprint_points, user_story, outcome, prompt, acceptance_criteria, spec_references, uat_status
3. `TaskIndex` model: total_tasks, pending, complete, total_points, points_complete, file_index
4. Implement `update_task_status(task_dir: Path, task_id: str, complete: bool)` that updates both the task file and the index
5. Handle decimal task IDs (002-1, 002-2) for insertions

**Acceptance Criteria:**
- [ ] Parser correctly reads the tasks-workflow.md format
- [ ] All task fields are extracted including acceptance criteria
- [ ] Task status updates modify both task file and index
- [ ] next_pending correctly traverses files in order
- [ ] Decimal task IDs are handled
- [ ] All tests pass
```

---

### Task ID: 022

- **Title**: Interactive task creation command
- **File**: src/autopilot/cli/task.py
- **Complete**: [ ]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a technical architect, I want to create tasks interactively, so that I can quickly add new work items with proper structure and estimation.
- **Outcome (what this delivers)**: The `autopilot task create` command with interactive prompts for all task fields, generating properly formatted task markdown.

#### Prompt:

```markdown
**Objective:** Implement interactive task creation CLI command.

**File to Create/Modify:** `src/autopilot/cli/task.py`

**Specification References:**
- Task Workflow System: Task Creation Guidelines, Task Template
- Discovery: Task Management CLI commands
- UX Design Section 5.2: Planning Pipeline

**Prerequisite Requirements:**
1. Tasks 009, 021 must be complete (display, task parser)
2. Write tests in `tests/cli/test_task.py`

**Detailed Instructions:**
1. Implement `task create` command:
   - Interactive prompts for: title, file path, user story, outcome, sprint points (Fibonacci validation: 1,2,3,5,8)
   - Prompt text editor for detailed prompt content
   - Auto-assign next sequential task ID
   - Determine correct tasks-N.md file (create new if current is full at 10 tasks)
   - Update tasks-index.md with new task count and points
2. Support --title, --file, --points flags for non-interactive use
3. Validate sprint points against Fibonacci scale
4. Rich output showing created task summary

**Acceptance Criteria:**
- [ ] Interactive creation flow covers all task fields
- [ ] Task ID auto-increments correctly
- [ ] Sprint points validate against Fibonacci (1,2,3,5,8)
- [ ] Task file and index are both updated
- [ ] New task file created when current has 10 tasks
- [ ] All tests pass
```

---

### Task ID: 023

- **Title**: Task list command with Rich display
- **File**: src/autopilot/cli/task.py
- **Complete**: [ ]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a technical architect, I want to view my task board with filtering and status colors, so that I can quickly assess project progress and find the next work item.
- **Outcome (what this delivers)**: The `autopilot task list` command showing a formatted task board with status, sprint points, and filtering by status/sprint.

#### Prompt:

```markdown
**Objective:** Implement the task list command with Rich table formatting.

**File to Create/Modify:** `src/autopilot/cli/task.py`

**Specification References:**
- Discovery: Task Management CLI (task list)
- UX Design Section 5.2: Task board display
- UX Design Section 7: Progressive Disclosure

**Prerequisite Requirements:**
1. Tasks 009, 021 must be complete (display, task parser)
2. Write tests in `tests/cli/test_task.py`

**Detailed Instructions:**
1. Implement `task list` command:
   - Parse all task files and display Rich table
   - Columns: ID, Title, File, Points, Status (color-coded), UAT Status
   - Filters: --status (pending/complete/all), --sprint, --project
   - Summary row: total tasks, pending, complete, points
2. Support --verbose flag for showing user stories
3. Highlight the "next" pending task
4. Show sprint progress bar when sprint is active

**Acceptance Criteria:**
- [ ] Task board displays all tasks with correct formatting
- [ ] Status filtering works (pending, complete, all)
- [ ] Next pending task is highlighted
- [ ] Summary statistics are accurate
- [ ] All tests pass
```

---

### Task ID: 024

- **Title**: Sprint planning with velocity tracking
- **File**: src/autopilot/core/task.py
- **Complete**: [ ]
- **Sprint Points**: 5

- **User Story (business-facing)**: As a technical architect, I want velocity-based sprint planning, so that I can plan realistic sprints based on historical throughput and forecast completion dates.
- **Outcome (what this delivers)**: Sprint planning engine with velocity tracking, capacity forecasting, and sprint lifecycle management backed by SQLite.

#### Prompt:

```markdown
**Objective:** Implement sprint planning with velocity tracking and forecasting.

**File to Create/Modify:** `src/autopilot/core/task.py`

**Specification References:**
- Discovery: VelocityTracker class (forecast_capacity using rolling average)
- Task Workflow System: Sprint Planning section (4-week cadence)
- Task Workflow System: Sprint Record Template Structure

**Prerequisite Requirements:**
1. Tasks 006, 021 must be complete (db, task parser)
2. Write tests in `tests/core/test_task.py`

**Detailed Instructions:**
1. Implement `VelocityTracker` class:
   - `record_sprint(sprint: SprintResult)` stores in SQLite velocity table
   - `forecast_capacity(team_size: int) -> int` using rolling average of last 5 sprints (default 13 if <3 sprints)
   - `get_history() -> list[SprintResult]` for velocity chart data
2. Implement `SprintPlanner` class:
   - `plan_sprint(tasks: list[Task], capacity: int) -> Sprint` selects tasks up to capacity
   - `close_sprint(sprint_id: str) -> SprintResult` calculates completed points, carries over incomplete
   - `active_sprint() -> Sprint | None` returns current sprint
3. Sprint record file generation at docs/project-management/sprints/
4. Velocity log maintenance at docs/project-management/velocity.md

**Acceptance Criteria:**
- [ ] Velocity tracking stores sprint results in SQLite
- [ ] Forecast uses rolling average with 13-point default
- [ ] Sprint planning respects capacity limits
- [ ] Sprint close records results and carries over tasks
- [ ] Sprint record files are generated
- [ ] All tests pass
```

---

### Task ID: 025

- **Title**: Discovery-to-task conversion pipeline
- **File**: src/autopilot/core/task.py
- **Complete**: [ ]
- **Sprint Points**: 5

- **User Story (business-facing)**: As a technical architect, I want to convert discovery documents into structured tasks, so that findings automatically become actionable work items with proper estimation and ordering.
- **Outcome (what this delivers)**: The `task create --from-discovery` pipeline that parses discovery markdown and generates task files with proper IDs, structure, and phase ordering.

#### Prompt:

```markdown
**Objective:** Implement discovery-to-task conversion pipeline.

**File to Create/Modify:** `src/autopilot/core/task.py`

**Specification References:**
- Discovery: Discovery Workflow Integration (discover -> tasks create --from-discovery)
- Discovery: Task Management section (task create --from-discovery output)
- Task Workflow System: Task Creation Guidelines

**Prerequisite Requirements:**
1. Task 021 must be complete (task parser)
2. Write tests in `tests/core/test_task.py`

**Detailed Instructions:**
1. Implement `DiscoveryParser` class:
   - `parse_discovery(path: Path) -> DiscoveryDocument` extracts phases, deliverables, estimates
   - `convert_to_tasks(discovery: DiscoveryDocument) -> list[Task]` generates task list
   - Each implementation phase deliverable becomes a task
   - Sprint points estimated from phase effort estimates (distributed across deliverables)
2. Implement `TaskFileWriter` class:
   - `write_task_files(tasks: list[Task], output_dir: Path)` creates tasks-index.md and tasks-N.md files
   - Max 10 tasks per file
   - Proper ID sequencing
3. Support interactive confirmation before writing files
4. Handle merging with existing task files (append new tasks with continuing IDs)

**Acceptance Criteria:**
- [ ] Discovery documents parse into structured phases and deliverables
- [ ] Tasks are generated with all required template fields
- [ ] Task files respect 10-per-file limit
- [ ] Task IDs sequence correctly
- [ ] Index file is generated with correct summaries
- [ ] All tests pass
```

---

### Task ID: 026

- **Title**: Sprint plan and close CLI commands
- **File**: src/autopilot/cli/task.py
- **Complete**: [ ]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a technical architect, I want to plan and close sprints from the CLI, so that I can manage development cadence with velocity-informed capacity.
- **Outcome (what this delivers)**: The `autopilot task sprint plan` and `autopilot task sprint close` commands with interactive task selection and sprint record generation.

#### Prompt:

```markdown
**Objective:** Implement sprint planning and closing CLI commands.

**File to Create/Modify:** `src/autopilot/cli/task.py`

**Specification References:**
- Discovery: Task Management CLI (task sprint plan/close)
- Task Workflow System: Sprint Planning, Sprint Record Template
- UX Design Section 5.2: Planning Pipeline

**Prerequisite Requirements:**
1. Tasks 023, 024 must be complete (task list, sprint planner)
2. Write tests in `tests/cli/test_task.py`

**Detailed Instructions:**
1. `task sprint plan` command:
   - Show velocity forecast and recommended capacity
   - Display available pending tasks sorted by priority
   - Interactive task selection (checkbox-style with prompt-toolkit)
   - Validate total points against capacity (warn if over)
   - Generate sprint record file
2. `task sprint close` command:
   - Show sprint summary (planned vs completed)
   - Record velocity in SQLite
   - Carry over incomplete tasks
   - Generate retrospective template
   - Update velocity.md log

**Acceptance Criteria:**
- [ ] Sprint plan shows velocity forecast
- [ ] Task selection validates against capacity
- [ ] Sprint record file is generated
- [ ] Sprint close records velocity and handles carryover
- [ ] All tests pass
```

---

### Task ID: 027

- **Title**: Fibonacci estimation support and velocity storage
- **File**: src/autopilot/core/task.py
- **Complete**: [ ]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a technical architect, I want estimation support with Fibonacci validation, so that task sizing is consistent and velocity metrics are meaningful.
- **Outcome (what this delivers)**: Fibonacci validation, task estimation command integration, and SQLite-backed velocity persistence.

#### Prompt:

```markdown
**Objective:** Implement estimation validation and velocity storage.

**File to Create/Modify:** `src/autopilot/core/task.py`, `src/autopilot/cli/task.py`

**Specification References:**
- Task Workflow System: Sprint Points Scale (1,2,3,5,8)
- Discovery: Fibonacci estimation support
- Discovery: SQLite velocity storage

**Prerequisite Requirements:**
1. Tasks 006, 021 must be complete (db, task parser)
2. Write tests in `tests/core/test_task.py`

**Detailed Instructions:**
1. Implement Fibonacci validation: `validate_sprint_points(points: int | str) -> int` accepting 1,2,3,5,8 or warning symbol
2. `task estimate TASK_ID` command: prompt for sprint points, validate, update task file
3. Batch estimation: `task estimate --unestimated` finds all tasks with warning points
4. Velocity persistence: ensure all sprint results write to SQLite velocity table
5. Velocity queries: `get_average_velocity(sprints: int = 5) -> float`, `get_velocity_trend() -> list[tuple[str, int]]`

**Acceptance Criteria:**
- [ ] Only Fibonacci values (1,2,3,5,8) are accepted
- [ ] Unestimated tasks show warning symbol
- [ ] Velocity data persists in SQLite
- [ ] Velocity queries return correct averages
- [ ] All tests pass
```

---

### Task ID: 028

- **Title**: UAT skill directory structure and SKILL.md
- **File**: .claude/skills/autopilot-uat/SKILL.md
- **Complete**: [ ]
- **Sprint Points**: 2
- **Spec References**: UAT Discovery: /autopilot-uat Skill Architecture, YAML Frontmatter, Directory Structure

- **User Story (business-facing)**: As a developer, I want the UAT framework skill properly structured, so that it can be invoked as `/autopilot-uat` in Claude sessions with progressive disclosure documentation.
- **Outcome (what this delivers)**: Complete skill directory with SKILL.md, scripts/, resources/, and docs/ subdirectories following the skill-builder specification.

#### Prompt:

```markdown
**Objective:** Create the /autopilot-uat Claude skill directory structure.

**File to Create/Modify:**
- `.claude/skills/autopilot-uat/SKILL.md`
- `.claude/skills/autopilot-uat/scripts/` (empty placeholders)
- `.claude/skills/autopilot-uat/resources/templates/` (empty placeholders)
- `.claude/skills/autopilot-uat/resources/schemas/` (empty placeholders)

**Specification References:**
- UAT Discovery: /autopilot-uat Skill Architecture section
- UAT Discovery: YAML Frontmatter
- UAT Discovery: Directory Structure
- UAT Discovery: SKILL.md Structure (Progressive Disclosure levels 1-4)

**Prerequisite Requirements:**
1. No code dependencies (documentation-only task)

**Detailed Instructions:**
1. Create SKILL.md with YAML frontmatter (name, description per UAT Discovery)
2. Write 4 progressive disclosure levels:
   - Level 1: Overview (3 sentences, prerequisites, quick start)
   - Level 2: Quick Start (single task, sprint, matrix, coverage commands)
   - Level 3: Detailed Usage (config options, custom patterns, batch execution)
   - Level 4: Reference (schemas, API, troubleshooting)
3. Create placeholder directories per UAT Discovery skill architecture
4. Create JSON schemas for traceability matrix and UAT result per UAT Discovery

**UAT Acceptance Criteria:**
- [ ] SKILL.md follows skill-builder YAML frontmatter spec
- [ ] All 4 progressive disclosure levels are present
- [ ] Directory structure matches UAT Discovery specification
- [ ] JSON schemas are valid
- [ ] Skill can be referenced as /autopilot-uat
```

---

### Task ID: 029

- **Title**: UAT task context loader
- **File**: src/autopilot/uat/task_context.py
- **Complete**: [ ]
- **Sprint Points**: 3
- **Spec References**: UAT Discovery: Task Context Loader, TaskContext dataclass, SpecReference dataclass

- **User Story (business-facing)**: As a UAT agent, I want to load completed task context with all testable assertions, so that I can generate appropriate acceptance tests.
- **Outcome (what this delivers)**: Task context loader that extracts user stories, acceptance criteria, file paths, and spec references from completed task markdown.

#### Prompt:

```markdown
**Objective:** Implement the UAT task context loader per UAT Discovery specification.

**File to Create/Modify:** `src/autopilot/uat/task_context.py`

**Specification References:**
- UAT Discovery: Task Context Loader section
- UAT Discovery: TaskContext and SpecReference dataclasses
- Task Workflow System: Task template structure

**Prerequisite Requirements:**
1. Task 021 must be complete (task parser)
2. Write tests in `tests/uat/test_task_context.py`

**Detailed Instructions:**
1. Implement `TaskContext` dataclass per UAT Discovery:
   - task_id, title, file_path, sprint_points, user_story, outcome
   - acceptance_criteria: list[str] (extracted from prompt checkboxes)
   - prompt_text: str (full prompt content)
   - spec_references: list[SpecReference]
2. Implement `SpecReference` dataclass: document, section, requirement, verification_type
3. Implement `load_task_context(task_dir: Path, task_id: str) -> TaskContext`:
   - Parse task markdown to extract all fields
   - Extract acceptance criteria from `- [ ]` checkboxes in prompt
   - Extract spec references from `**Specification References:**` section
   - Parse `Spec References` field from task header

**UAT Acceptance Criteria:**
- [ ] TaskContext extracts all fields from task markdown
- [ ] Acceptance criteria checkboxes are parsed correctly
- [ ] Spec references are extracted from both header and prompt
- [ ] Missing fields produce clear warnings, not errors
- [ ] All tests pass
```

---

### Task ID: 030

- **Title**: UAT specification cross-reference engine (explicit references)
- **File**: src/autopilot/uat/spec_engine.py
- **Complete**: [ ]
- **Sprint Points**: 5
- **Spec References**: UAT Discovery: Spec Cross-Reference Engine, TraceabilityMatrix dataclass

- **User Story (business-facing)**: As a UAT agent, I want to map tasks to specification requirements, so that I can verify implementations against what was actually specified in the RFC, discovery, and UX design documents.
- **Outcome (what this delivers)**: Specification cross-reference engine supporting explicit reference parsing with regex patterns for section numbers and document names.

#### Prompt:

```markdown
**Objective:** Implement the spec cross-reference engine for explicit reference matching.

**File to Create/Modify:** `src/autopilot/uat/spec_engine.py`

**Specification References:**
- UAT Discovery: Specification Cross-Reference Engine section
- UAT Discovery: Explicit references (regex patterns for section numbers)
- UAT Discovery: TraceabilityMatrix dataclass

**Prerequisite Requirements:**
1. Task 029 must be complete (task context)
2. Write tests in `tests/uat/test_spec_engine.py`

**Detailed Instructions:**
1. Implement `SpecCrossReferenceEngine` class:
   - `match_explicit_references(context: TaskContext) -> list[SpecReference]`
   - Parse references like "RFC Section 3.4.1", "UX Design Section 4.1", "Discovery ADR-5"
   - Regex patterns for: "RFC (Section )?\d+(\.\d+)*", "UX Design Section \d+(\.\d+)*", "Discovery [\w-]+"
2. Implement `TraceabilityMatrix` dataclass per UAT Discovery:
   - task_id, rfc_sections, discovery_requirements, ux_elements
   - coverage_score (0.0-1.0), unmapped_specs, unmapped_tasks
3. Build initial reference mapping from task's spec_references field
4. Phase 1: Explicit references only (keyword matching deferred to Task 068)

**UAT Acceptance Criteria:**
- [ ] Explicit RFC section references are correctly parsed
- [ ] UX Design section references are correctly parsed
- [ ] Discovery references (ADR, section names) are correctly parsed
- [ ] TraceabilityMatrix correctly tracks coverage
- [ ] All tests pass
```
