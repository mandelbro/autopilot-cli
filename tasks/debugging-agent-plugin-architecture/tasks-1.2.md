## Summary (tasks-1.2.md)

- **Tasks in this file**: 6
- **Task IDs**: 006 - 010b
- **Total Points**: 12

### Phase 2: Plugin Loader + Phase 3a: Browser MCP Core + Phase 3b: Browser MCP Diagnostics & UX

---

## Tasks

### Task ID: 006

- **Title**: Plugin loader with config-based discovery
- **File**: src/autopilot/debugging/loader.py
- **Complete**: [x]
- **Sprint Points**: 2

- **User Story (business-facing)**: As a project operator, I want the debugging pipeline to automatically load the configured tool plugin from my `config.yaml`, so that I can switch between Browser MCP and Desktop Agent without code changes.
- **Outcome (what this delivers)**: `loader.py` with `load_debugging_tool()` that reads config, imports the module, validates protocol compliance and version, and returns a tool instance.

#### Prompt:

```markdown
**Objective:** Implement the plugin loader that discovers and validates debugging tool plugins from config.

**File to Create:** `src/autopilot/debugging/loader.py`

**Context:**
Per ADR-D01, plugins are declared in `config.yaml` under `debugging.tools`. The loader uses `importlib.import_module` to load the configured tool. Per ADR-D07, the loader checks `PROTOCOL_VERSION`. See discovery lines 142-206.

**Prerequisite Requirements:**
1. Tasks 001 and 003 must be complete (protocol + config)
2. Read `src/autopilot/core/config.py` for `DebuggingConfig` and `DebuggingToolConfig`

**Detailed Instructions:**

1. `load_debugging_tool(config: DebuggingConfig) -> DebuggingTool`:
   - Get active tool name from `config.tool`, look up in `config.tools`
   - Raise `ValueError` if tool name not found
   - `importlib.import_module(tool_config.module)` to load module
   - `getattr(module, tool_config.class_name)` to get class
   - Instantiate, validate `isinstance(instance, DebuggingTool)` — raise `TypeError` if fails
   - Check `protocol_version` class attribute — log warning if missing or mismatched
   - Return the instance

2. `validate_plugin_class(cls: type) -> tuple[bool, str]`:
   - Check if class satisfies `DebuggingTool` protocol without instantiation
   - Verify all required methods via `hasattr` checks
   - Check `protocol_version` class attribute
   - Return `(True, "Valid")` or `(False, reason)`

3. Error handling: Wrap imports in try/except, produce clear messages with tool name/module/class.

4. Use `structlog` for logging.

**Acceptance Criteria:**
- [ ] `load_debugging_tool` loads and returns a valid tool instance
- [ ] Raises `ValueError` for unknown tool name, `ImportError` for missing module, `TypeError` for invalid class
- [ ] Logs warning for version mismatch
- [ ] `validate_plugin_class` works without instantiation
- [ ] `just all` passes
```

---

### Task ID: 007

- **Title**: Unit tests for Phase 2 (pipeline and loader)
- **File**: tests/debugging/test_pipeline.py
- **Complete**: [x]
- **Sprint Points**: 2

- **User Story (business-facing)**: As a developer, I want tests for the pipeline support functions and plugin loader, so that guardrails are verified and plugin loading edge cases are covered.
- **Outcome (what this delivers)**: Test files for `pipeline.py` and `loader.py` covering happy paths, error cases, and edge cases.

#### Prompt:

```markdown
**Objective:** Write unit tests for pipeline support functions and plugin loader.

**Files to Create:**
- `tests/debugging/test_pipeline.py`
- `tests/debugging/test_loader.py`

**Context:**
Use `tmp_path` for file-based tests. Mock `subprocess.run` for `run_quality_gates`. Create a minimal mock class satisfying `DebuggingTool` for loader tests. Use `unittest.mock.patch` for `importlib.import_module`.

**Prerequisite Requirements:**
1. Tasks 005-006 must be complete

**Detailed Instructions:**

1. `tests/debugging/test_pipeline.py`:
   - `test_load_debugging_task_valid`: Write valid YAML to `tmp_path`, load, verify fields
   - `test_load_debugging_task_missing_required`: Missing fields → `ValueError`
   - `test_load_debugging_task_file_not_found`: Non-existent path
   - `test_validate_source_scope_all_in_scope`: Returns `True`
   - `test_validate_source_scope_out_of_scope`: Returns `False`
   - `test_validate_source_scope_empty_files`: Empty tuple returns `True`
   - `test_track_fix_iteration_continue`: Below max → `(True, ...)`
   - `test_track_fix_iteration_escalate`: At max → `(False, ...)`
   - `test_run_quality_gates_success`: Mock exit 0 → `(True, output)`
   - `test_run_quality_gates_failure`: Mock exit 1 → `(False, output)`
   - `test_validate_debugging_run_pass`: Pass case
   - `test_validate_debugging_run_escalated`: Escalated → failure
   - Note: `collect_debugging_result` is tested in Task 014-1, not here

2. `tests/debugging/test_loader.py`:
   - `_MockDebuggingTool` class satisfying protocol
   - `test_load_debugging_tool_success`: Patched import returns mock class
   - `test_load_debugging_tool_unknown_tool`: `ValueError`
   - `test_load_debugging_tool_import_error`: `ModuleNotFoundError`
   - `test_load_debugging_tool_invalid_class`: `TypeError`
   - `test_validate_plugin_class_valid` / `_invalid`
   - `test_load_debugging_tool_version_warning`: Wrong version logs warning (`caplog`)

**Acceptance Criteria:**
- [ ] Descriptive test names (`test_<function>_<scenario>`)
- [ ] YAML loading tested with real files via `tmp_path`
- [ ] Plugin loader tested with mocked imports
- [ ] Edge cases covered
- [ ] `just all` passes
```

---

### Task ID: 008

- **Title**: BrowserMCPTool core class with action mapping and session management
- **File**: src/autopilot/debugging/tools/browser_mcp.py
- **Complete**: [ ]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a debugging agent testing a web application, I want a Browser MCP tool plugin that translates generic test steps (navigate, click, fill) into Browser MCP tool calls, so that I can interactively test deployed web apps.
- **Outcome (what this delivers)**: `BrowserMCPTool` class implementing `DebuggingTool` protocol with action mapping, provisioning, and session lifecycle.

#### Prompt:

```markdown
**Objective:** Implement the Browser MCP debugging tool plugin for web application testing.

**File to Create:** `src/autopilot/debugging/tools/browser_mcp.py`

**Context:**
Wraps ruflo browser MCP tools. See discovery lines 389-416. Synchronous (ADR-D02). MCP tools are invoked via Claude CLI subprocess in actual agent sessions — this class provides provisioning/health interface and action mapping metadata.

**Prerequisite Requirements:**
1. Task 001 must be complete (protocol.py)
2. Read the Browser MCP Plugin Design section of the discovery (lines 389-416)

**Detailed Instructions:**

1. Class `BrowserMCPTool` with `protocol_version = 1`
2. Properties: `name` → `"browser_mcp"`, `capabilities` → all 5 capabilities
3. Action mapping dict: navigate→browser_navigate, click→browser_click, fill→browser_type, wait_for_navigation→browser_wait, assert_text→browser_snapshot, assert_visible→browser_snapshot, screenshot→browser_screenshot
4. `provision(settings)`: Check MCP server registration in `.mcp.json`. Return `ProvisionResult`.
5. `deprovision()`: Remove MCP server registration.
6. `check_provisioned()`: Verify MCP server registered and reachable. Return `ProvisionStatus`.
7. `setup(settings)`: Validate provisioned, store settings. Raise `ToolNotProvisionedError` if not provisioned.
8. `teardown()`: Clean up session state.
9. `execute_step()`: Look up action mapping, build MCP parameters, return `InteractionResult`.
10. `capture_diagnostic_evidence()`, `capture_screenshot()`, `evaluate_ux()`: Placeholder implementations.

**Acceptance Criteria:**
- [ ] `isinstance(BrowserMCPTool(), DebuggingTool)` is `True`
- [ ] `protocol_version == 1` class attribute
- [ ] All 5 capabilities declared
- [ ] Action mapping covers all specified actions
- [ ] `provision()` and `check_provisioned()` use subprocess for real MCP checks
- [ ] `setup()` raises `ToolNotProvisionedError` when not provisioned
- [ ] `just all` passes
```

---

### Task ID: 009

- **Title**: BrowserMCPTool diagnostics and UX evaluation capabilities
- **File**: src/autopilot/debugging/tools/browser_mcp.py
- **Complete**: [ ]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a debugging agent, I want the Browser MCP plugin to capture console errors, network failures, and screenshots for failure diagnosis, so that I can provide evidence-backed diagnoses to the fix cycle.
- **Outcome (what this delivers)**: Enhanced `BrowserMCPTool` with console capture via `browser_eval`, network log capture, screenshot management, and structured UX evaluation.

#### Prompt:

```markdown
**Objective:** Add diagnostic evidence collection and UX review capabilities to BrowserMCPTool.

**File to Modify:** `src/autopilot/debugging/tools/browser_mcp.py`

**Prerequisite Requirements:**
1. Task 008 must be complete

**Detailed Instructions:**

1. Enhanced `capture_diagnostic_evidence()`: JavaScript snippets for console errors and network failures, diagnostic screenshot. Return populated `DiagnosticEvidence`.

2. Enhanced `capture_screenshot(label)`: Timestamped filename `debug_{label}_{timestamp}.png`, configurable directory (default `.autopilot/debugging/screenshots/`), create dir if needed.

3. Enhanced `evaluate_ux(criteria, design_system_ref)`: Capture screenshots, build structured evaluation per criterion, return `tuple[UXObservation, ...]` with categories and severities.

4. Helper methods: `_build_console_capture_js()`, `_build_network_capture_js()`, `_ensure_screenshot_dir(project_dir)`.

**Acceptance Criteria:**
- [ ] `capture_diagnostic_evidence()` returns populated `DiagnosticEvidence`
- [ ] `capture_screenshot()` generates timestamped filenames, ensures directory exists
- [ ] `evaluate_ux()` returns structured `UXObservation` tuples
- [ ] JavaScript helpers return valid JS snippets
- [ ] `just all` passes
```

---

### Task ID: 010a

- **Title**: Unit tests for Browser MCP plugin -- core (protocol, actions, provisioning)
- **File**: tests/debugging/tools/test_browser_mcp.py
- **Complete**: [ ]
- **Sprint Points**: 1

- **User Story (business-facing)**: As a developer, I want tests for the Browser MCP plugin's core functionality (protocol compliance, action mapping, provisioning), so that I can validate Task 008's implementation before building diagnostics.
- **Outcome (what this delivers)**: Test file and package init covering protocol satisfaction, action mapping, and provisioning with mocked MCP responses.

#### Prompt:

```markdown
**Objective:** Write unit tests for BrowserMCPTool core functionality (Task 008 deliverables).

**Files to Create:**
- `tests/debugging/tools/__init__.py`
- `tests/debugging/tools/test_browser_mcp.py`

**Prerequisite Requirements:**
1. Task 008 must be complete

**Detailed Instructions:**

1. Protocol compliance: isinstance check, name, capabilities, protocol_version
2. Action mapping: navigate, click, fill map correctly; unknown action handled gracefully
3. Provisioning (mock subprocess): healthy, not registered, setup raises when not provisioned

**Acceptance Criteria:**
- [ ] All tests pass with mocked subprocess
- [ ] No actual browser or MCP server required
- [ ] Protocol compliance verified (isinstance, capabilities)
- [ ] `just all` passes
```

---

### Task ID: 010b

- **Title**: Unit tests for Browser MCP plugin -- diagnostics and UX
- **File**: tests/debugging/tools/test_browser_mcp.py
- **Complete**: [ ]
- **Sprint Points**: 1

- **User Story (business-facing)**: As a developer, I want tests for the Browser MCP plugin's diagnostic and UX capabilities, so that console capture, screenshots, and UX evaluation are verified without a running browser.
- **Outcome (what this delivers)**: Additional tests in the Browser MCP test file covering diagnostics, screenshot management, and UX evaluation.

#### Prompt:

```markdown
**Objective:** Write unit tests for BrowserMCPTool diagnostics and UX capabilities (Task 009 deliverables).

**File to Modify:** `tests/debugging/tools/test_browser_mcp.py`

**Prerequisite Requirements:**
1. Task 009 must be complete
2. Task 010a must be complete (test file exists)

**Detailed Instructions:**

1. Diagnostics: evidence populated with console errors and network failures, screenshot creates directory, filename format matches `debug_{label}_{timestamp}.png`
2. UX evaluation: returns tuple of `UXObservation`, valid categories and severities
3. JavaScript helpers: `_build_console_capture_js()` and `_build_network_capture_js()` return valid JS

**Acceptance Criteria:**
- [ ] Diagnostic evidence fully populated in tests
- [ ] Screenshot directory creation verified
- [ ] UX observations have valid structure
- [ ] `just all` passes
```
