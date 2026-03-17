## Summary (tasks-2.2.md)

- **Tasks in this file**: 5
- **Task IDs**: 015 - 019
- **Total Points**: 13

### Phase 5: Desktop Agent Plugin + Phase 6: Orchestration Integration + Documentation

---

## Tasks

### Task ID: 015

- **Title**: DesktopAgentTool skeleton, provisioning, and VM lifecycle
- **File**: src/autopilot/debugging/tools/desktop_agent.py
- **Complete**: [x]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a debugging agent testing a native desktop application (Slack, VS Code, etc.), I want a Desktop Agent plugin that manages VM lifecycle and provisioning, so that the heavy infrastructure (Lume, macOS image, models) can be set up and validated.
- **Outcome (what this delivers)**: `DesktopAgentTool` class skeleton implementing `DebuggingTool` protocol with provisioning, deprovisioning, health checks, setup/teardown lifecycle, and stub `execute_step`/diagnostics methods. Action execution is completed in Task 016.

#### Prompt:

```markdown
**Objective:** Implement the Desktop Agent plugin skeleton with provisioning and VM lifecycle (action execution in Task 016).

**File to Create:** `src/autopilot/debugging/tools/desktop_agent.py`

**Context:**
Wraps Cua SDK + Lume VM. Provisioning is heavy (~100GB). See discovery lines 417-457. Incorporate learnings about VM state drift, macOS permissions, and dual-model complexity.

**Prerequisite Requirements:**
1. Task 001 must be complete (protocol.py)
2. Read discovery lines 417-457 and `docs/ideation/desktop-agent-uat-discovery.md`

**Detailed Instructions:**

1. Class `DesktopAgentTool` with `protocol_version = 1`
2. Properties: `name` → `"desktop_agent"`, `capabilities` → `{INTERACTIVE_TEST, SCREENSHOT, UX_REVIEW}` (NO console/network capture)
3. `provision(settings)` — Multi-step: install Lume, pull macOS image, create VM, configure VM, download UI-TARS, install Ollama + validation model, create snapshot. Return `ProvisionResult` with `manual_steps`. Per-step try/except.
4. `deprovision()`: Stop VM, delete image, remove models.
5. `check_provisioned()`: Check Lume, VM, models. Return component-level `ProvisionStatus`.
6. `setup(settings)`: Start VM / restore snapshot, init ComputerAgent. Raise `ToolNotProvisionedError` if not provisioned.
7. `teardown()`: Save snapshot if configured, stop VM.
8. Stub methods: `execute_step()`, `capture_diagnostic_evidence()`, `capture_screenshot()`, `evaluate_ux()` — raise `NotImplementedError("Completed in Task 016")` to satisfy protocol.

**Implementation Notes:**
- Wrap async Cua SDK calls with `asyncio.run()` (ADR-D02)
- Guard `cua-computer` imports with try/except ImportError
- Missing SDK → reported in `check_provisioned()`

**Acceptance Criteria:**
- [ ] `isinstance(DesktopAgentTool(), DebuggingTool)` is `True`
- [ ] Capabilities exclude `CONSOLE_CAPTURE` and `NETWORK_CAPTURE`
- [ ] `provision()` handles each step independently with per-step error handling
- [ ] `setup()` raises `ToolNotProvisionedError` when not provisioned
- [ ] Missing Cua SDK handled gracefully (ImportError → degraded status)
- [ ] Async calls wrapped with `asyncio.run()` (ADR-D02)
- [ ] `just all` passes
```

---

### Task ID: 016

- **Title**: DesktopAgentTool action execution, retry logic, diagnostics, and dual-model config
- **File**: src/autopilot/debugging/tools/desktop_agent.py
- **Complete**: [x]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a debugging agent, I want reliable action execution on desktop applications with automatic retry for click accuracy issues, diagnostic capture, and dual-model support, so that desktop testing is robust despite UI-TARS limitations.
- **Outcome (what this delivers)**: Completed `DesktopAgentTool` with action mapping, click retry with position jitter, pre-flight dialog dismissal, diagnostic evidence capture, UX evaluation, and configurable dual-model architecture.

#### Prompt:

```markdown
**Objective:** Complete the Desktop Agent with action execution, retry logic, diagnostics, and dual-model config.

**File to Modify:** `src/autopilot/debugging/tools/desktop_agent.py`

**Context:**
Critical learnings from discovery: click accuracy ~70-80% needs retry+jitter, VM state drift needs snapshot restore, 60-120s per test needs higher timeouts, dual-model (UI-TARS for actions, Gemma/Claude for validation).

**Prerequisite Requirements:**
1. Task 015 must be complete (skeleton with stubs exists)

**Detailed Instructions:**

1. Replace `execute_step()` stub with full implementation:
   - Action mapping: navigate→open app/URL, click→coordinate-based via UI-TARS, fill→keyboard input, wait→duration, screenshot→VM capture, assert_visible→screenshot+validation model
   - Click retry: configurable max retries (default 3), position jitter +/-5px, verification after click via validation model, failure after all retries

2. Replace `capture_diagnostic_evidence()` stub: Screenshots + validation model analysis. Return populated `DiagnosticEvidence`.

3. Replace `capture_screenshot()` stub: VM screenshot via Cua SDK, timestamped filename.

4. Replace `evaluate_ux()` stub: Screenshots to validation model for structured `UXObservation` evaluation.

5. Pre-flight dialog dismissal in `setup()`: After VM restore, dismiss "What's New" popups, update notifications, permission prompts. Configurable patterns.

6. Dual-model config: `action_model` (default UI-TARS 1.5 7B), `validation_model` (default Gemma 3 12B via Ollama). Both configurable via `settings`.

7. Default `timeout_seconds` for desktop: 120 (vs. 30 for browser).

**Acceptance Criteria:**
- [ ] All action types mapped
- [ ] Click retry with +/-5px jitter
- [ ] Click verification uses validation model
- [ ] Pre-flight dialog dismissal in `setup()`
- [ ] `capture_diagnostic_evidence()` returns populated `DiagnosticEvidence`
- [ ] `evaluate_ux()` returns structured `UXObservation` tuples
- [ ] Dual-model configurable via settings
- [ ] Default timeout 120 seconds
- [ ] `just all` passes
```

---

### Task ID: 017

- **Title**: Unit tests for Desktop Agent plugin
- **File**: tests/debugging/tools/test_desktop_agent.py
- **Complete**: [x]
- **Sprint Points**: 2

- **User Story (business-facing)**: As a developer, I want comprehensive tests for the Desktop Agent plugin, so that VM lifecycle, retry logic, and dual-model configuration are verified without requiring actual infrastructure.
- **Outcome (what this delivers)**: Test file with mocked Cua SDK covering protocol compliance, provisioning, action execution, retry logic, and configuration.

#### Prompt:

```markdown
**Objective:** Write unit tests for DesktopAgentTool with mocked Cua SDK and Lume CLI.

**File to Create:** `tests/debugging/tools/test_desktop_agent.py`

**Context:**
All tests work without Cua SDK or Lume. Mock subprocess and imports. Integration tests guarded by `AUTOPILOT_INTEGRATION_TESTS` env var (ADR-D06).

**Prerequisite Requirements:**
1. Tasks 015-016 must be complete

**Detailed Instructions:**

1. Protocol: isinstance check, name, capabilities (3 only), protocol_version
2. Provisioning (mock subprocess): full workflow, lume not found, manual steps, all healthy, missing model, deprovision stops VM
3. Session: setup restores snapshot, not provisioned raises, teardown saves snapshot, preflight runs
4. Actions: click success, click retry (first fail → retry succeeds), all retries fail, fill, unknown action
5. Config: dual-model configurable, default timeout 120
6. Missing SDK: ImportError → reported in check_provisioned

**Acceptance Criteria:**
- [ ] All tests pass without Cua SDK or Lume (fully mocked)
- [ ] Click retry with jitter verified
- [ ] Provisioning steps tested independently
- [ ] No integration tests by default
- [ ] `just all` passes
```

---

### Task ID: 018

- **Title**: Orchestration integration (hooks, scheduler, result reporting)
- **File**: src/autopilot/orchestration/debugging_hooks.py
- **Complete**: [x]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a project operator, I want debugging runs to trigger automatically after deployments and results to appear in cycle reports, so that the debugging pipeline is fully integrated with the autopilot orchestration lifecycle.
- **Outcome (what this delivers)**: Post-deploy hook trigger, scheduler integration, debugging results in cycle reports, and escalation to coordination board.

#### Prompt:

```markdown
**Objective:** Integrate the debugging agent into the autopilot orchestration lifecycle.

**Files to Modify:**
- `src/autopilot/orchestration/hooks.py` — post-deploy debugging trigger
- `src/autopilot/reporting/` — debugging results in cycle reports

**Context:**
Debugging agent dispatched like any other agent via `DispatchPlan`. Scheduler uses existing infrastructure. See discovery lines 790-805.

**Prerequisite Requirements:**
1. Tasks 001-014-1 must be complete

**Detailed Instructions:**

1. Hook configuration: `post_dispatch` hook pattern triggers debugging after deploy actions. Configurable, disabled by default.

2. Scheduler: Debugging dispatches processed normally. Debugging timeout from config respected via `AgentsConfig.agent_timeouts`.

3. Result reporting: Post summary to coordination board (announcement for pass, decision-log for fail). Include in cycle reports.

**Acceptance Criteria:**
- [ ] Post-deploy hook configurable, disabled by default
- [ ] Debugging timeout respected by scheduler
- [ ] Results posted to coordination board
- [ ] Results in cycle reports when applicable
- [ ] `just all` passes
```

---

### Task ID: 019

- **Title**: Debugging agent usage guide documentation
- **File**: docs/agents/debugging-agent.md
- **Complete**: [ ]
- **Sprint Points**: 2

- **User Story (business-facing)**: As a project operator, I want comprehensive documentation for the debugging agent, so that I can set up, configure, and troubleshoot debugging runs without reading source code.
- **Outcome (what this delivers)**: Usage guide covering overview, setup, usage (manual + hooks), task file format, plugin management, provisioning, and troubleshooting.

#### Prompt:

```markdown
**Objective:** Create the debugging agent usage guide documentation.

**File to Create:** `docs/agents/debugging-agent.md`

**Prerequisite Requirements:**
1. Tasks 001-018 must be complete (all code is implemented)

**Detailed Instructions:**

1. **Overview**: What the debugging agent does, the 6-phase workflow, the plugin architecture concept.

2. **Setup**: How to enable debugging in config, how to provision a tool (`autopilot debug provision browser_mcp`).

3. **Usage**:
   - Manual: `autopilot debug run <task-file>` with options
   - Automated: Hook-based triggering after deploys
   - Dry-run validation

4. **Task File Format**: YAML schema for debugging task files with annotated example.

5. **Plugin Management**: `list-tools`, `add-tool`, `remove-tool`, `validate-tool`, `provision`, `deprovision` commands.

6. **Troubleshooting**: Common issues (tool not provisioned, MCP server unreachable, desktop agent click failures, escalation reasons).

7. **Architecture**: Plugin protocol, pipeline support functions, agent prompt, ADR references.

**Acceptance Criteria:**
- [ ] Covers all 7 sections listed above
- [ ] Includes at least one YAML task file example
- [ ] References all CLI commands with usage examples
- [ ] Troubleshooting covers top 5 expected failure modes
- [ ] `just all` passes (no broken doc references)
```
