## Summary (tasks-2.1.md)

- **Tasks in this file**: 5
- **Task IDs**: 011 - 014-1
- **Total Points**: 13

### Phase 4a: CLI Integration + Phase 4b: Agent Integration

---

## Tasks

### Task ID: 011

- **Title**: CLI debug subcommand group -- run, list-tools, status
- **File**: src/autopilot/cli/debug.py
- **Complete**: [x]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a project operator, I want `autopilot debug run`, `autopilot debug list-tools`, and `autopilot debug status` commands, so that I can execute debugging runs and inspect the debugging pipeline state from the terminal.
- **Outcome (what this delivers)**: Typer subcommand group `debug` with `run`, `list-tools`, and `status` commands. Registered in the main CLI app.

#### Prompt:

```markdown
**Objective:** Create the `autopilot debug` CLI subcommand group with core operational commands.

**File to Create:** `src/autopilot/cli/debug.py`
**File to Modify:** CLI app registration (likely `src/autopilot/cli/app.py`)

**Context:**
Follow existing CLI subcommand patterns (e.g., `src/autopilot/cli/enforce.py`, `src/autopilot/cli/session.py`, `src/autopilot/cli/task.py`). Uses Typer + Rich. See discovery lines 734-753.

**Prerequisite Requirements:**
1. Tasks 001-006 must be complete (models, protocol, config, pipeline, loader)
2. Read existing CLI subcommand files for patterns

**Detailed Instructions:**

1. Create `src/autopilot/cli/debug.py` with Typer app: `debug_app = typer.Typer(name="debug", help="Debugging agent tools and pipeline management.")`

2. `@debug_app.command("run")`: Argument `task_file: Path`, options `--tool` (override), `--dry-run`. Load config, load task, check provisioned, invoke debugging agent (or validate in dry-run). Display results with Rich.

3. `@debug_app.command("list-tools")`: Load config, for each tool attempt load + check_provisioned, display Rich table (name, module.class, capabilities, status).

4. `@debug_app.command("status")`: Show debugging config, active tool provision status, recent run history.

5. Register `debug_app` in main CLI app.

**Acceptance Criteria:**
- [ ] `autopilot debug --help` shows all three commands
- [ ] `run` loads task and attempts execution; `--dry-run` validates only
- [ ] `list-tools` shows Rich table with registered tools and status
- [ ] `status` shows pipeline config and health
- [ ] `just all` passes
```

---

### Task ID: 012

- **Title**: CLI plugin management commands (add-tool, remove-tool, validate-tool, provision, deprovision)
- **File**: src/autopilot/cli/debug.py
- **Complete**: [x]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a project operator, I want CLI commands to register, validate, and provision debugging tool plugins, so that I can manage plugin lifecycle without editing YAML manually.
- **Outcome (what this delivers)**: Five additional commands in the `debug` group for plugin management, using load-modify-save config pattern (ADR-D05).

#### Prompt:

```markdown
**Objective:** Add plugin management commands to `autopilot debug` CLI group.

**File to Modify:** `src/autopilot/cli/debug.py`

**Context:**
Per ADR-D05, config mutation: load YAML → modify dict → validate via `AutopilotConfig.model_validate()` → write YAML. Per ADR-D01, `add-tool` validates protocol compliance at registration time. See discovery lines 164-206.

**Prerequisite Requirements:**
1. Task 011 must be complete

**Detailed Instructions:**

1. `add-tool`: Args `name`, `--module`, `--class`. Import module, validate protocol, add to config YAML, validate full config, write back. Reject invalid plugins.

2. `remove-tool`: Arg `name`. Remove from config, warn if removing active tool, validate, write.

3. `validate-tool`: Arg `name`. Load tool, run `validate_plugin_class()`, display results. Exit 0/1.

4. `provision`: Arg `name`. Load tool, call `tool.provision(settings)`, display `ProvisionResult`.

5. `deprovision`: Arg `name`. Load tool, confirm (unless `--force`), call `tool.deprovision()`.

6. Config mutation helper: `_load_modify_save_config(project_dir, modifier)` — load YAML dict, apply modifier, validate, write back.

**Acceptance Criteria:**
- [ ] `add-tool` validates protocol before writing config
- [ ] `add-tool` rejects non-compliant classes
- [ ] `remove-tool` warns when removing active tool
- [ ] Config mutation follows load-modify-save (ADR-D05)
- [ ] `provision` shows component status and manual steps
- [ ] `deprovision` requires confirmation or `--force`
- [ ] `just all` passes
```

---

### Task ID: 013

- **Title**: Unit tests for CLI debug commands
- **File**: tests/cli/test_debug.py
- **Complete**: [x]
- **Sprint Points**: 2

- **User Story (business-facing)**: As a developer, I want tests for all `autopilot debug` CLI commands, so that plugin management and pipeline execution are verified.
- **Outcome (what this delivers)**: Test file using Typer's `CliRunner` to test all 8 debug subcommands.

#### Prompt:

```markdown
**Objective:** Write unit tests for the `autopilot debug` CLI subcommand group.

**File to Create:** `tests/cli/test_debug.py`

**Prerequisite Requirements:**
1. Tasks 011-012 must be complete

**Detailed Instructions:**

1. Setup: `CliRunner()` fixture, config fixture with `debugging` section in `tmp_path`
2. Test `run`: valid task (mock loader+pipeline), dry-run, missing task file
3. Test `list-tools`: registered tools shown, empty config
4. Test `status`: config values displayed
5. Test `add-tool`: valid plugin (mock), invalid protocol (rejection)
6. Test `remove-tool`: existing tool, active tool warning
7. Test `validate-tool`: valid exit 0, invalid exit 1
8. Test `provision`/`deprovision`: success mock, force flag

**Acceptance Criteria:**
- [ ] All 8 commands have at least one test
- [ ] `CliRunner` for all invocations
- [ ] Config mutation tested (YAML written correctly after add-tool)
- [ ] YAML written by `add-tool` can be re-loaded by `AutopilotConfig.from_yaml()` without error, and the debugging tool config (including `class` alias) is preserved
- [ ] Error cases covered
- [ ] `just all` passes
```

---

### Task ID: 014

- **Title**: Debugging agent system prompt, AgentRegistry integration, and init defaults
- **File**: .autopilot/agents/debugging-agent.md, src/autopilot/cli/app.py (init command)
- **Complete**: [ ]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a project operator, I want the debugging agent to appear in `autopilot agent list` and be dispatchable like any other agent, so that debugging runs integrate seamlessly with the existing orchestration pipeline.
- **Outcome (what this delivers)**: Agent prompt template defining the 6-phase workflow, auto-discovered by `AgentRegistry`, coordination board integration, and `autopilot init` pre-registers `browser_mcp`.

#### Prompt:

```markdown
**Objective:** Create the debugging agent's system prompt and integrate with agent infrastructure.

**Files to Create/Modify:**
- Create: `.autopilot/agents/debugging-agent.md` (agent prompt)
- Modify: `src/autopilot/cli/app.py` (the `init` command at line ~99) to pre-register `browser_mcp` in default config

**Context:**
Per ADR-D03, debugging agent is standard agent discovered from `.md` file by `AgentRegistry`. The LLM session IS the pipeline. See discovery lines 521-528 and 755-769.

**Prerequisite Requirements:**
1. Tasks 001-006 must be complete
2. Read `src/autopilot/core/agent_registry.py` for discovery pattern
3. Read existing agent prompts in `.autopilot/agents/`
4. Read `src/autopilot/coordination/board.py`

**Detailed Instructions:**

1. Create `.autopilot/agents/debugging-agent.md` defining:
   - Phase 1 — Interactive Testing: Use debugging tool to test acceptance criteria
   - Phase 2 — Diagnose Failures: Capture diagnostic evidence, analyze root cause
   - Phase 3 — Fix Source Code: Modify files within `source_scope`, call `validate_source_scope()`, run `run_quality_gates()`, 3-strike escalation via `track_fix_iteration()`
   - Phase 4 — Verify Fix: Re-test failed criteria
   - Phase 5 — Draft Regression Tests: E2E tests in project framework
   - Phase 6 — UX Review: Screenshots + evaluation
   - Tool usage instructions, 3-strike rule, source scope constraints, reporting format

2. Modify `autopilot init` to include default debugging config:
   ```yaml
   debugging:
     enabled: false
     tool: "browser_mcp"
     tools:
       browser_mcp:
         module: "autopilot.debugging.tools.browser_mcp"
         class: "BrowserMCPTool"
   ```

3. Coordination board integration: results as announcements, failures as decision-log entries.

**Acceptance Criteria:**
- [ ] `debugging-agent.md` defines complete 6-phase workflow
- [ ] Agent discovered by `AgentRegistry`
- [ ] Prompt references guardrail tools
- [ ] 3-strike escalation rule defined
- [ ] `autopilot init` pre-registers `browser_mcp`
- [ ] `just all` passes
```

---

### Task ID: 014-1

- **Title**: Implement `collect_debugging_result` with agent output schema
- **File**: src/autopilot/debugging/pipeline.py
- **Complete**: [ ]
- **Sprint Points**: 2

- **User Story (business-facing)**: As a debugging pipeline operator, I want the agent's output to be parsed into a structured `DebuggingResult`, so that orchestration can process and report debugging outcomes programmatically.
- **Outcome (what this delivers)**: `collect_debugging_result()` function in `pipeline.py` that accepts an `InvokeResult` from `AgentInvoker` and parses the agent's structured JSON output into a `DebuggingResult`. Also defines the expected agent output JSON schema that the debugging agent prompt (Task 014) must produce.

#### Prompt:

```markdown
**Objective:** Implement `collect_debugging_result` now that the agent output format is defined by the debugging agent prompt (Task 014).

**File to Modify:** `src/autopilot/debugging/pipeline.py`
**Test File to Create:** `tests/debugging/test_collect_result.py`

**Context:**
This function was deferred from Task 005 because it depends on the agent's output format, which is defined by the debugging agent prompt in Task 014. Per the discovery (line 509), the signature uses `InvokeResult` from `src/autopilot/orchestration/agent_invoker.py`.

**Prerequisite Requirements:**
1. Task 005 must be complete (pipeline.py exists)
2. Task 014 must be complete (agent prompt defines the output format)
3. Read `src/autopilot/orchestration/agent_invoker.py` for `InvokeResult` (line 34)

**Detailed Instructions:**

1. Define the expected agent output JSON schema as a module-level docstring or constant:
   - `task_id`, `overall_pass`, `test_results`, `fix_results`, `regression_results`, `ux_results`, `escalated`, `escalation_reason`

2. `collect_debugging_result(task: DebuggingTask, agent_result: InvokeResult) -> DebuggingResult`:
   - Extract agent output text from `agent_result`
   - Parse structured JSON block from agent output (look for ```json fenced block or raw JSON)
   - Map parsed JSON to `DebuggingResult` and sub-result models
   - On parse failure: return `DebuggingResult(task_id=task.task_id, escalated=True, escalation_reason="Failed to parse agent output")`

3. Write tests in `tests/debugging/test_collect_result.py`:
   - `test_collect_result_valid_json`: Well-formed output → populated result
   - `test_collect_result_malformed_json`: Bad output → escalated result
   - `test_collect_result_partial_output`: Missing sub-results → None fields

**Acceptance Criteria:**
- [ ] Signature: `collect_debugging_result(task: DebuggingTask, agent_result: InvokeResult) -> DebuggingResult`
- [ ] Parses structured JSON from agent output
- [ ] Returns escalated result on parse failure (no exceptions)
- [ ] Tests cover valid, malformed, and partial output
- [ ] `just all` passes
```
