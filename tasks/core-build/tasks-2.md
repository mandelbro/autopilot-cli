## Summary (tasks-2.md)

- **Tasks in this file**: 10
- **Task IDs**: 011 - 020
- **Total Points**: 30

### Main Phase 1: Foundation -- REPL, Agent Registry, Document-Mediated Coordination

---

## Tasks

### Task ID: 011

- **Title**: Project list, show, and switch commands
- **File**: src/autopilot/cli/project.py
- **Complete**: [x]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a technical architect managing multiple projects, I want to list, inspect, and switch between projects, so that I can monitor all my autonomous development work from one place.
- **Outcome (what this delivers)**: CLI commands for listing all registered projects with status, showing project details, and switching the active project context.

#### Prompt:

```markdown
**Objective:** Implement project listing, detail view, and context switching commands.

**File to Create/Modify:** `src/autopilot/cli/project.py`

**Specification References:**
- RFC Appendix B: project list|show|switch|config|archive commands
- UX Design Section 5.5: Monitoring Workflows (project overview)
- Discovery: Project registry (~/.autopilot/projects.yaml)

**Prerequisite Requirements:**
1. Tasks 006, 009, 010 must be complete (db, display, project init)
2. Write tests in `tests/cli/test_project.py`

**Detailed Instructions:**
1. `project list`: Query SQLite for all registered projects. Display Rich table with columns: Name, Type, Path, Status (running/stopped), Tasks (pending/complete), Last Activity
2. `project show [NAME]`: Show detailed project info including config summary, agent roster, active sessions, recent cycle history
3. `project switch NAME`: Set the active project context (stored in ~/.autopilot/active_project)
4. `project config [KEY] [VALUE]`: Get/set project config values
5. `project archive NAME`: Mark project as archived (soft delete from active list)

**Acceptance Criteria:**
- [ ] `autopilot project list` shows all registered projects in a table
- [ ] `autopilot project show` displays detailed project information
- [ ] `autopilot project switch` changes active project context
- [ ] All commands handle empty state gracefully (no projects registered)
- [ ] All tests pass
```

---

### Task ID: 012

- **Title**: Global project registry management
- **File**: src/autopilot/core/project.py
- **Complete**: [x]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a developer, I want a reliable registry of all autopilot-managed projects, so that the tool can discover and manage projects across the filesystem.
- **Outcome (what this delivers)**: YAML-based project registry at ~/.autopilot/projects.yaml with CRUD operations and path validation.

#### Prompt:

```markdown
**Objective:** Implement global project registry with CRUD operations.

**File to Create/Modify:** `src/autopilot/core/project.py`

**Specification References:**
- RFC ADR-3: ~/.autopilot/ for global state
- Discovery: Project registry format (projects.yaml)
- Discovery: Global config at ~/.autopilot/config.yaml

**Prerequisite Requirements:**
1. Tasks 002, 005 must be complete (config, paths)
2. Write tests in `tests/core/test_project.py`

**Detailed Instructions:**
1. Implement `ProjectRegistry` class:
   - `load() -> list[RegisteredProject]` from ~/.autopilot/projects.yaml
   - `register(name, path, project_type) -> RegisteredProject`
   - `unregister(name)` (removes from registry, does not delete .autopilot/)
   - `find_by_name(name) -> RegisteredProject | None`
   - `find_by_path(path) -> RegisteredProject | None`
   - `validate_all() -> list[RegistryIssue]` (checks paths still exist, configs valid)
2. `RegisteredProject` dataclass: name, path, type, registered_at, last_active, archived
3. Handle concurrent access (file locking for YAML writes)
4. Auto-create ~/.autopilot/ directory if it does not exist

**Acceptance Criteria:**
- [ ] Registry persists across CLI invocations
- [ ] Duplicate project names are rejected
- [ ] Invalid paths are detected during validation
- [ ] Registry file is created on first use
- [ ] All tests pass
```

---

### Task ID: 013

- **Title**: REPL skeleton with prompt-toolkit
- **File**: src/autopilot/cli/repl.py
- **Complete**: [x]
- **Sprint Points**: 5

- **User Story (business-facing)**: As a technical architect, I want an interactive REPL for managing projects, so that I can explore state, dispatch agents, and monitor sessions without leaving the terminal.
- **Outcome (what this delivers)**: Working REPL loop with prompt-toolkit providing history, basic tab completion, and slash command routing.

#### Prompt:

```markdown
**Objective:** Implement the core REPL loop with prompt-toolkit integration.

**File to Create/Modify:** `src/autopilot/cli/repl.py`

**Specification References:**
- RFC ADR-6: prompt-toolkit + Typer for REPL
- UX Design Section 3: REPL Experience (prompt format, input modes, output patterns)
- Discovery: REPL architecture (AutopilotREPL class)
- UX Design Section 3.1: Context-Sensitive Prompt

**Prerequisite Requirements:**
1. Tasks 008, 009, 012 must be complete (CLI app, display, registry)
2. Write tests in `tests/cli/test_repl.py`
3. Use context7 for prompt-toolkit patterns

**Detailed Instructions:**
1. Implement `AutopilotREPL` class:
   - `__init__(workspace)` with PromptSession, command registry, completer
   - `run()` async main loop with prompt_async
   - Command registry mapping slash commands to handlers
   - WordCompleter for available commands
   - History support (FileHistory at ~/.autopilot/repl_history)
2. Implement core slash commands: /help, /quit, /projects, /sessions, /status
3. Context-sensitive prompt showing: `autopilot [project-name] > ` or `autopilot > ` when no project selected
4. Error handling: catch exceptions in command handlers, display with Rich, continue REPL
5. Graceful exit on Ctrl+C and Ctrl+D

**Acceptance Criteria:**
- [ ] REPL launches with context-sensitive prompt
- [ ] Tab completion works for slash commands
- [ ] Command history persists between sessions
- [ ] Ctrl+C does not crash the REPL
- [ ] /help shows available commands
- [ ] /quit exits cleanly
- [ ] All tests pass
```

---

### Task ID: 014

- **Title**: REPL context management and notifications
- **File**: src/autopilot/cli/repl.py
- **Complete**: [x]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a technical architect, I want the REPL to show me relevant context and important notifications, so that I stay informed about project state without constant manual checking.
- **Outcome (what this delivers)**: REPL context state machine (no project -> project selected -> session active -> attention needed) and notification batching between outputs.

#### Prompt:

```markdown
**Objective:** Add context management and notification system to the REPL.

**File to Create/Modify:** `src/autopilot/cli/repl.py`

**Specification References:**
- UX Design Section 3.3: Context-Sensitive Prompt (state machine)
- UX Design Section 6: Notification and Alerting (4 tiers)
- UX Design Section 3.4: Output Patterns
- RFC Risk: REPL state management complexity

**Prerequisite Requirements:**
1. Task 013 must be complete
2. Write tests in `tests/cli/test_repl.py`

**Detailed Instructions:**
1. Implement REPL state machine:
   - States: NO_PROJECT, PROJECT_SELECTED, SESSION_ACTIVE, ATTENTION_NEEDED
   - Transitions based on project switch, session start/stop, question queue
   - Prompt format changes per state (UX Design Section 3.3)
2. Implement notification batching:
   - Notifications accumulate during command execution
   - Display batched notifications after command output completes
   - Never interrupt mid-typing (UX Design Section 6.3)
3. Implement 4 notification tiers per UX Design Section 6:
   - Critical: Inline, immediate (deployment failures, circuit breaker)
   - Important: Next prompt display (cycle complete, PR created)
   - Informational: Queryable via /notifications
   - Ambient: Prompt indicator changes

**Acceptance Criteria:**
- [ ] Prompt changes based on REPL state
- [ ] Notifications display at appropriate times
- [ ] Notification tiers work correctly
- [ ] State transitions are tested
- [ ] All tests pass
```

---

### Task ID: 015

- **Title**: Dynamic agent registry
- **File**: src/autopilot/core/agent_registry.py
- **Complete**: [x]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a technical architect, I want to manage agent roles dynamically, so that I can add custom agents like security-reviewer without modifying any code.
- **Outcome (what this delivers)**: Dynamic agent registry that discovers roles from .autopilot/agents/*.md files with validation and prompt loading.

#### Prompt:

```markdown
**Objective:** Implement the dynamic agent registry per RFC Section 3.7.

**File to Create/Modify:** `src/autopilot/core/agent_registry.py`

**Specification References:**
- RFC Section 3.7: Dynamic Agent Registry (AgentRegistry class)
- RFC ADR-10: Dynamic agent registry
- Discovery: Agent Lifecycle Management
- Discovery: Custom Agent Roles (any .md in agents/ becomes a role)

**Prerequisite Requirements:**
1. Tasks 003, 005 must be complete (models, paths)
2. Write tests in `tests/core/test_agent_registry.py`

**Detailed Instructions:**
1. Implement `AgentRegistry` class per RFC Section 3.7:
   - `list_agents() -> list[str]` discovers .md files in agents/ dir
   - `load_prompt(name: str) -> str` loads agent prompt content
   - `validate_agent(name: str) -> bool` checks agent exists
   - `validate_dispatch(plan: DispatchPlan) -> list[str]` returns unknown agents
2. Add `AgentNotFoundError` with available agents in message
3. Skip files starting with underscore (_)
4. Support loading from both project-level (.autopilot/agents/) and global (~/.autopilot/agents/)

**Acceptance Criteria:**
- [ ] Registry discovers agents from .md files
- [ ] Unknown agent names raise descriptive errors
- [ ] Dispatch validation catches missing agents
- [ ] Underscore-prefixed files are excluded
- [ ] All tests pass
```

---

### Task ID: 016

- **Title**: Template rendering system with Jinja2
- **File**: src/autopilot/core/templates.py
- **Complete**: [x]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a developer, I want a template system for project scaffolding, so that new projects get correctly configured files based on their type and settings.
- **Outcome (what this delivers)**: Jinja2-based template renderer that processes templates from the package's templates/ directory and supports user-level template overrides.

#### Prompt:

```markdown
**Objective:** Implement the template rendering system for project scaffolding.

**File to Create/Modify:** `src/autopilot/core/templates.py`

**Specification References:**
- Discovery: Project Type Templates (package templates/, user ~/.autopilot/templates/)
- Discovery: Template system extension points
- RFC Section 3.4.3: Directory layout

**Prerequisite Requirements:**
1. Tasks 005, 007 must be complete (paths, Python templates)
2. Write tests in `tests/core/test_templates.py`

**Detailed Instructions:**
1. Implement `TemplateRenderer` class:
   - `__init__(project_type: str)` loads template directory
   - `render_to(output_dir: Path, context: dict)` renders all templates to output
   - Template lookup order: user override (~/.autopilot/templates/{type}/) then package default (templates/{type}/)
2. Implement `list_available_templates() -> list[str]` showing all registered types
3. Support template inheritance (`extends: "python"` in template config)
4. Add template validation (check all expected files are present)
5. Context variables: project_name, project_type, project_root, quality_gates, agent_roles

**Acceptance Criteria:**
- [ ] Templates render with Jinja2 variable substitution
- [ ] User templates override package defaults
- [ ] Template inheritance works
- [ ] Missing template variables raise clear errors
- [ ] All tests pass
```

---

### Task ID: 017

- **Title**: Board management for document-mediated coordination
- **File**: src/autopilot/coordination/board.py
- **Complete**: [x]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a project leader agent, I want a well-structured project board, so that I can read project state and write dispatch decisions through markdown files.
- **Outcome (what this delivers)**: Board manager that reads and writes project-board.md sections, tracks active work, blockers, and sprint progress.

#### Prompt:

```markdown
**Objective:** Implement the project board management for document-mediated agent coordination.

**File to Create/Modify:** `src/autopilot/coordination/board.py`

**Specification References:**
- RFC Section 3.6: Inter-Agent Communication Model
- Discovery: Inter-Agent Communication (board files, channels table)
- RFC Section 3.4.3: board/ directory structure

**Prerequisite Requirements:**
1. Tasks 003, 005 must be complete (models, paths)
2. Write tests in `tests/coordination/test_board.py`

**Detailed Instructions:**
1. Implement `BoardManager` class:
   - `read_board(project_dir: Path) -> BoardState` parses project-board.md into structured data
   - `update_section(section: str, content: str)` updates a specific board section
   - `add_active_work(task_id: str, agent: str, description: str)`
   - `mark_blocker(description: str, assigned_to: str)`
   - `update_sprint_progress(planned: int, completed: int)`
2. `BoardState` model: sprint_info, active_work, blockers, recent_decisions, deployment_status
3. Board file format: markdown with well-defined section headers that can be parsed reliably
4. Thread-safe file access (read-modify-write with file locking)

**Acceptance Criteria:**
- [ ] Board manager reads and writes project-board.md correctly
- [ ] Section updates preserve other sections
- [ ] Board state parses into structured data
- [ ] Concurrent writes are handled safely
- [ ] All tests pass
```

---

### Task ID: 018

- **Title**: Question queue for agent-to-human communication
- **File**: src/autopilot/coordination/questions.py
- **Complete**: [x]
- **Sprint Points**: 2

- **User Story (business-facing)**: As a technical architect, I want agents to post questions that need my judgment, so that autonomous work pauses appropriately on decisions I need to make.
- **Outcome (what this delivers)**: Question queue manager that handles agent questions with priority, status tracking, and REPL integration.

#### Prompt:

```markdown
**Objective:** Implement the question queue for agent-to-human decisions.

**File to Create/Modify:** `src/autopilot/coordination/questions.py`

**Specification References:**
- RFC Section 3.6: Question Queue (Agent -> Human)
- UX Design Section 5.4: Q&A Workflow
- Discovery: Question queue channel

**Prerequisite Requirements:**
1. Tasks 003, 005 must be complete
2. Write tests in `tests/coordination/test_questions.py`

**Detailed Instructions:**
1. Implement `QuestionQueue` class:
   - `add_question(agent: str, question: str, context: str, priority: str)` appends to question-queue.md
   - `list_pending() -> list[Question]` parses pending questions
   - `answer(question_id: str, answer: str, answered_by: str)` marks as answered
   - `skip(question_id: str, reason: str)` skips question
2. Question model: id, agent, question, context, priority (blocking/normal/low), status, timestamp
3. Blocking questions trigger ATTENTION_NEEDED REPL state

**Acceptance Criteria:**
- [ ] Questions persist in question-queue.md
- [ ] Pending/answered questions are correctly tracked
- [ ] Priority ordering works
- [ ] All tests pass
```

---

### Task ID: 019

- **Title**: Announcements channel for human-to-agent communication
- **File**: src/autopilot/coordination/announcements.py
- **Complete**: [x]
- **Sprint Points**: 2

- **User Story (business-facing)**: As a technical architect, I want to broadcast policy changes to all agents, so that priority shifts and new constraints are picked up in the next cycle.
- **Outcome (what this delivers)**: Announcement manager for human-to-agent broadcasts via announcements.md.

#### Prompt:

```markdown
**Objective:** Implement the announcements channel for human-to-agent broadcasts.

**File to Create/Modify:** `src/autopilot/coordination/announcements.py`

**Specification References:**
- RFC Section 3.6: Announcements (Human -> All)
- Discovery: Announcements channel

**Prerequisite Requirements:**
1. Tasks 003, 005 must be complete
2. Write tests in `tests/coordination/test_announcements.py`

**Detailed Instructions:**
1. Implement `AnnouncementManager` class:
   - `post(title: str, content: str, author: str)` adds announcement
   - `list_active() -> list[Announcement]` returns current announcements
   - `archive(announcement_id: str)` moves to archived section
   - `clear_all()` archives all current announcements
2. Announcement model: id, title, content, author, posted_at, archived
3. Announcements are read by agents at the start of every invocation

**Acceptance Criteria:**
- [ ] Announcements persist in announcements.md
- [ ] Active and archived sections are maintained
- [ ] Announcements are ordered by recency
- [ ] All tests pass
```

---

### Task ID: 020

- **Title**: Decision log with archival and rotation
- **File**: src/autopilot/coordination/decisions.py
- **Complete**: [x]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a technical architect, I want an audit trail of all PL decisions, so that I can review why specific agents were dispatched and what rationale drove the choices.
- **Outcome (what this delivers)**: Decision log manager with append, rotation, and archival for the decision-log.md file.

#### Prompt:

```markdown
**Objective:** Implement the decision log with rotation and archival.

**File to Create/Modify:** `src/autopilot/coordination/decisions.py`

**Specification References:**
- RFC Section 3.6: Decision Log (PL -> All)
- Discovery: Decision log with rotation (from reports.py evolution)
- Discovery: Reporting and Metrics section

**Prerequisite Requirements:**
1. Tasks 003, 005 must be complete
2. Write tests in `tests/coordination/test_decisions.py`

**Detailed Instructions:**
1. Implement `DecisionLog` class:
   - `record(agent: str, action: str, rationale: str, context: dict)` appends decision
   - `list_recent(limit: int) -> list[Decision]` returns latest decisions
   - `rotate(max_entries: int)` archives old entries to decision-log-archive/
   - `search(query: str) -> list[Decision]` searches decision history
2. Decision model: id, timestamp, agent, action, rationale, context, outcome
3. Rotation: when log exceeds max_entries (default 100), move oldest to archive
4. Archive files named by date: decision-log-2026-03.md

**Acceptance Criteria:**
- [ ] Decisions persist in decision-log.md
- [ ] Log rotation archives old entries
- [ ] Search finds decisions by keyword
- [ ] Archive files are properly named
- [ ] All tests pass
```
