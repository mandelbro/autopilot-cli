## Summary (tasks-1.1.md)

- **Tasks in this file**: 5
- **Task IDs**: 001 - 005
- **Total Points**: 11

### Phase 1: Core Models & Plugin Protocol + Phase 2: Pipeline Support Functions (Start)

---

## Tasks

### Task ID: 001

- **Title**: Create debugging package structure and DebuggingTool Protocol
- **File**: src/autopilot/debugging/tools/protocol.py
- **Complete**: [ ]
- **Sprint Points**: 2

- **User Story (business-facing)**: As a plugin developer, I want a clearly defined Protocol for debugging tools, so that I can implement new tool backends (browser, desktop, API) that the debugging pipeline accepts without inheritance coupling.
- **Outcome (what this delivers)**: The `DebuggingTool` Protocol with `@runtime_checkable`, `ToolCapability` StrEnum, and all shared result frozen dataclasses (`InteractionResult`, `DiagnosticEvidence`, `UXObservation`, `ProvisionResult`, `ProvisionStatus`). Package `__init__.py` files for `src/autopilot/debugging/` and `src/autopilot/debugging/tools/`.

#### Prompt:

```markdown
**Objective:** Create the debugging package structure and the `DebuggingTool` Protocol that all tool plugins must satisfy.

**Files to Create:**
- `src/autopilot/debugging/__init__.py` (empty or minimal re-exports)
- `src/autopilot/debugging/tools/__init__.py` (empty or minimal re-exports)
- `src/autopilot/debugging/tools/protocol.py` (main deliverable)

**Context:**
This follows the `EnforcementRule` Protocol pattern in `src/autopilot/enforcement/rules/base.py` (line 53-54). The Protocol uses `typing.Protocol` with `@runtime_checkable` for structural typing. All result types use `@dataclass(frozen=True)` consistent with `src/autopilot/core/models.py`.

**Prerequisite Requirements:**
1. Read `src/autopilot/enforcement/rules/base.py` to understand the existing Protocol pattern
2. Read `src/autopilot/core/models.py` to understand frozen dataclass conventions (StrEnum, tuple for immutable sequences, field defaults)
3. Read the Protocol Definition section of `docs/ideation/debugging-agent-plugin-architecture-discovery.md` (lines 208-387)

**Detailed Instructions:**

1. Create `src/autopilot/debugging/__init__.py` and `src/autopilot/debugging/tools/__init__.py` as empty files (or with a module docstring only).

2. In `src/autopilot/debugging/tools/protocol.py`, implement:

   a. Module-level constant: `PROTOCOL_VERSION: int = 1`

   b. `ToolCapability(StrEnum)` with values:
      - `INTERACTIVE_TEST = "interactive_test"`
      - `CONSOLE_CAPTURE = "console_capture"`
      - `NETWORK_CAPTURE = "network_capture"`
      - `SCREENSHOT = "screenshot"`
      - `UX_REVIEW = "ux_review"`

   c. Frozen dataclasses (all fields with sensible defaults where appropriate):
      - `InteractionResult`: success (bool), screenshot_path (str), console_output (str), network_log (str), observation (str), error (str)
      - `DiagnosticEvidence`: screenshots (tuple[str, ...]), console_errors (tuple[str, ...]), network_failures (tuple[str, ...]), state_dumps (tuple[str, ...]), observations (str)
      - `UXObservation`: category (str), severity (str), description (str), screenshot_path (str), element_reference (str)
      - `ProvisionResult`: success (bool), components_installed (tuple[str, ...]), manual_steps (tuple[str, ...]), error (str), duration_seconds (float)
      - `ProvisionStatus`: provisioned (bool), ready (bool), components (dict[str, str] — use `field(default_factory=dict)`), message (str)

   d. `DebuggingTool(Protocol)` with `@runtime_checkable`:
      - Properties: `name -> str`, `capabilities -> frozenset[ToolCapability]`
      - Methods (all synchronous per ADR-D02):
        - `provision(settings: dict[str, object]) -> ProvisionResult`
        - `deprovision() -> None`
        - `check_provisioned() -> ProvisionStatus`
        - `setup(settings: dict[str, object]) -> None`
        - `teardown() -> None`
        - `execute_step(action: str, target: str, *, value: str = "", expect: str = "", timeout_seconds: int = 30) -> InteractionResult`
        - `capture_diagnostic_evidence() -> DiagnosticEvidence`
        - `capture_screenshot(label: str) -> str`
        - `evaluate_ux(criteria: tuple[str, ...], design_system_ref: str = "") -> tuple[UXObservation, ...]`

**Acceptance Criteria:**
- [ ] `from autopilot.debugging.tools.protocol import DebuggingTool, ToolCapability, InteractionResult` imports work
- [ ] `PROTOCOL_VERSION == 1`
- [ ] All dataclasses are frozen (raise `FrozenInstanceError` on attribute assignment)
- [ ] `isinstance(obj, DebuggingTool)` works with `@runtime_checkable`
- [ ] Uses `from __future__ import annotations` for forward references
- [ ] All tuple fields default to empty tuples `()`; dict fields use `field(default_factory=dict)`
- [ ] No async keywords anywhere — protocol is fully synchronous (ADR-D02)
- [ ] `just all` passes (lint, typecheck, test)
```

---

### Task ID: 002

- **Title**: Create debugging data models
- **File**: src/autopilot/debugging/models.py
- **Complete**: [ ]
- **Sprint Points**: 2

- **User Story (business-facing)**: As a debugging pipeline operator, I want typed, immutable data models for debugging tasks and results, so that the pipeline has a clear contract for inputs and outputs.
- **Outcome (what this delivers)**: All debugging-specific frozen dataclasses: `DebuggingTask`, `TestStep`, `FixAttempt`, `InteractiveTestResults`, `FixCycleResults`, `RegressionTestResults`, `UXReviewResults`, `DebuggingResult`, and `ToolNotProvisionedError`.

#### Prompt:

```markdown
**Objective:** Create the debugging data models that define the input/output contract for the debugging pipeline.

**File to Create:** `src/autopilot/debugging/models.py`

**Context:**
All models follow the frozen dataclass pattern from `src/autopilot/core/models.py`. The discovery document (lines 531-628) defines these models precisely. Some types reference `InteractionResult` and `UXObservation` from `protocol.py` (Task 001).

**Prerequisite Requirements:**
1. Task 001 must be complete (protocol.py provides `InteractionResult`, `UXObservation`, `ProvisionStatus`)
2. Read `src/autopilot/core/models.py` for frozen dataclass conventions
3. Read the Data Models section of the discovery (lines 531-628)

**Detailed Instructions:**

1. Create `src/autopilot/debugging/models.py` with `from __future__ import annotations`.

2. Implement these frozen dataclasses:

   a. `TestStep`: action (str), target (str), value (str = ""), expect (str = ""), timeout_seconds (int = 30)
   b. `DebuggingTask`: task_id (str), feature (str), title (str), description (str), staging_url (str), steps (tuple[TestStep, ...]), acceptance_criteria (tuple[str, ...]), source_scope (tuple[str, ...]), ux_review_enabled (bool = True), ux_capture_states (tuple[str, ...] = ())
   c. `FixAttempt`: iteration (int), diagnosis (str), files_modified (tuple[str, ...]), pr_url (str = ""), tests_passed (bool = False), error (str = "")
   d. `InteractiveTestResults`: steps_total (int = 0), steps_passed (int = 0), steps_failed (int = 0), all_passed (bool = False), step_results (tuple[InteractionResult, ...] = ()), duration_seconds (float = 0.0)
   e. `FixCycleResults`: attempts (tuple[FixAttempt, ...] = ()), resolved (bool = False), final_diagnosis (str = ""), duration_seconds (float = 0.0)
   f. `RegressionTestResults`: tests_generated (int = 0), tests_passed (int = 0), tests_failed (int = 0), test_file_path (str = ""), duration_seconds (float = 0.0)
   g. `UXReviewResults`: observations (tuple[UXObservation, ...] = ()), overall_pass (bool = False), summary (str = ""), duration_seconds (float = 0.0)
   h. `DebuggingResult`: task_id (str), overall_pass (bool = False), test_results (InteractiveTestResults | None = None), fix_results (FixCycleResults | None = None), regression_results (RegressionTestResults | None = None), ux_results (UXReviewResults | None = None), duration_seconds (float = 0.0), escalated (bool = False), escalation_reason (str = "")

3. Create `ToolNotProvisionedError(RuntimeError)`:
   - `__init__(self, tool_name: str, status: ProvisionStatus) -> None`
   - Stores `tool_name` and `status` as instance attributes
   - Message: `f"Tool '{tool_name}' is not provisioned. Run 'autopilot debug provision {tool_name}' first. Status: {status.message}"`

**Acceptance Criteria:**
- [ ] All dataclasses are frozen (immutable)
- [ ] `DebuggingTask` requires all non-defaulted fields (task_id, feature, title, description, staging_url, steps, acceptance_criteria, source_scope)
- [ ] `ToolNotProvisionedError` stores `tool_name` and `status` attributes and produces the correct message
- [ ] Import of `InteractionResult` and `UXObservation` from `.tools.protocol` works correctly
- [ ] `just all` passes
```

---

### Task ID: 003

- **Title**: Add DebuggingConfig and DebuggingToolConfig to AutopilotConfig
- **File**: src/autopilot/core/config.py
- **Complete**: [ ]
- **Sprint Points**: 2

- **User Story (business-facing)**: As a project operator, I want debugging configuration in my project's `config.yaml`, so that I can enable/disable debugging, select a tool plugin, and tune pipeline parameters without code changes.
- **Outcome (what this delivers)**: `DebuggingToolConfig` and `DebuggingConfig` Pydantic models added to `config.py`, with `debugging` field added to `AutopilotConfig`. Existing configs without a `debugging` section continue to work (defaults to `enabled: False`).

#### Prompt:

```markdown
**Objective:** Add debugging configuration models to the existing AutopilotConfig hierarchy.

**File to Modify:** `src/autopilot/core/config.py`

**Context:**
The discovery document (lines 631-659) defines the config models. Follow the exact same pattern as existing config sections (e.g., `WorkspaceConfig`, `EnforcementConfig`): frozen Pydantic BaseModel with `ConfigDict(frozen=True)`.

**Prerequisite Requirements:**
1. Read `src/autopilot/core/config.py` to understand the existing config pattern
2. Read the Config Model section of the discovery (lines 631-659)

**Detailed Instructions:**

1. Add `DebuggingToolConfig(BaseModel)` with:
   - `model_config = ConfigDict(frozen=True, populate_by_name=True)`
   - `module: str = ""`
   - `class_name: str = Field(default="", alias="class")`
   - `settings: dict[str, object] = Field(default_factory=dict)`

2. Add `DebuggingConfig(BaseModel)` with:
   - `model_config = ConfigDict(frozen=True)`
   - `enabled: bool = False`
   - `tool: str = "browser_mcp"`
   - `tools: dict[str, DebuggingToolConfig] = Field(default_factory=dict)`
   - `max_fix_iterations: int = Field(default=3, gt=0, le=5)`
   - `timeout_seconds: int = Field(default=1800, gt=0)`
   - `regression_test_framework: str = "pytest"`
   - `ux_review_enabled: bool = True`

3. Add to `AutopilotConfig`:
   - `debugging: DebuggingConfig = Field(default_factory=DebuggingConfig)`

**Acceptance Criteria:**
- [ ] `DebuggingToolConfig` uses `populate_by_name=True` so both `class` (YAML) and `class_name` (Python) work
- [ ] `DebuggingConfig` has all fields with correct defaults and validators (`gt=0`, `le=5`)
- [ ] `AutopilotConfig` includes `debugging` field with `DebuggingConfig` default
- [ ] Existing config YAML files without `debugging` section load without error (Pydantic defaults apply)
- [ ] Config round-trip: `AutopilotConfig.from_yaml()` -> `to_yaml()` preserves debugging section (verify `to_yaml()` uses `by_alias=True` for the `class` alias on `DebuggingToolConfig`)
- [ ] `just all` passes
```

---

### Task ID: 004

- **Title**: Unit tests for Phase 1 (protocol, models, config)
- **File**: tests/debugging/test_models.py
- **Complete**: [ ]
- **Sprint Points**: 2

- **User Story (business-facing)**: As a developer, I want comprehensive tests for the debugging data models and protocol, so that I can refactor confidently knowing the contracts are verified.
- **Outcome (what this delivers)**: Test files covering frozen immutability, `isinstance` protocol checks, config loading/validation, and default value correctness.

#### Prompt:

```markdown
**Objective:** Write unit tests for all Phase 1 deliverables: protocol types, data models, and config integration.

**Files to Create:**
- `tests/debugging/__init__.py`
- `tests/debugging/conftest.py` (shared fixtures: `mock_debugging_tool`, `sample_debugging_task`, `debugging_config`)
- `tests/debugging/test_protocol.py`
- `tests/debugging/test_models.py`
- `tests/debugging/test_config.py`

**Context:**
Follow test patterns from `tests/conftest.py` (fixtures: `project_dir`, `autopilot_dir`, `global_dir`). The codebase uses plain pytest with `tmp_path` fixtures. No `pytest.mark.skipif` — use runtime env var checks for integration tests (ADR-D06). No pytest-asyncio needed (ADR-D02).

**Prerequisite Requirements:**
1. Tasks 001-003 must be complete
2. Read `tests/conftest.py` for fixture patterns
3. Read existing tests (e.g., `tests/core/test_config.py`) for style conventions

**Detailed Instructions:**

1. `tests/debugging/conftest.py` — shared fixtures reused by all debugging test files:
   - `mock_debugging_tool`: A minimal class satisfying `DebuggingTool` protocol (reused in test_protocol, test_loader, test_pipeline)
   - `sample_debugging_task`: A factory fixture returning a `DebuggingTask` with valid defaults
   - `debugging_config`: A `DebuggingConfig` with a mock `browser_mcp` tool entry

2. `tests/debugging/test_protocol.py`:
   - Test `ToolCapability` StrEnum has all 5 values and string representation
   - Test each frozen dataclass for default construction and frozen immutability
   - Test `@runtime_checkable` with a minimal class satisfying `DebuggingTool`
   - Test that a class missing a method fails `isinstance` check
   - Test `PROTOCOL_VERSION == 1`

3. `tests/debugging/test_models.py`:
   - Test construction of `TestStep`, `DebuggingTask` (all required fields), `FixAttempt`
   - Test result types default construction
   - Test `DebuggingResult` with `None` and populated sub-results
   - Test `ToolNotProvisionedError` message, `tool_name` and `status` attributes
   - Test frozen immutability on `DebuggingTask` and `DebuggingResult`

4. `tests/debugging/test_config.py`:
   - Test `DebuggingConfig` default values
   - Test `DebuggingToolConfig` with `class` alias
   - Test `AutopilotConfig` includes `debugging` field
   - Test config YAML without `debugging` section loads successfully
   - Test validation: `max_fix_iterations=0` and `max_fix_iterations=6` raise `ValidationError`

**Acceptance Criteria:**
- [ ] All test files created with descriptive test names
- [ ] Protocol isinstance check tests pass (positive and negative cases)
- [ ] Config alias test confirms `class` YAML key maps to `class_name` attribute
- [ ] Frozen immutability tested on at least one instance per module
- [ ] `just all` passes
```

---

### Task ID: 005

- **Title**: Pipeline support functions
- **File**: src/autopilot/debugging/pipeline.py
- **Complete**: [ ]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a debugging agent, I want guardrail functions to validate my actions (source scope, fix iteration limits, quality gates), so that I stay within project constraints during autonomous debugging runs.
- **Outcome (what this delivers)**: `pipeline.py` with `load_debugging_task()`, `validate_source_scope()`, `run_quality_gates()`, `track_fix_iteration()`, `collect_debugging_result()`, and `validate_debugging_run()`.

#### Prompt:

```markdown
**Objective:** Implement the pipeline support functions that the LLM debugging agent calls as guardrail tools.

**File to Create:** `src/autopilot/debugging/pipeline.py`

**Context:**
Per ADR-D03/D04, the debugging pipeline is NOT a Python orchestrator — it is a set of support functions the LLM agent invokes. The LLM drives the workflow; these functions enforce constraints. See discovery lines 458-519.

**Prerequisite Requirements:**
1. Tasks 001-002 must be complete (models and protocol)
2. Read the Core Debugging Pipeline section of the discovery (lines 458-519)
3. Read `src/autopilot/orchestration/agent_invoker.py` to understand `InvokeResult` type

**Detailed Instructions:**

1. `load_debugging_task(task_path: Path) -> DebuggingTask`: Read YAML, parse into model, validate required fields, raise `ValueError` for malformed files.

2. `validate_source_scope(modified_files: tuple[str, ...], allowed_scope: tuple[str, ...]) -> bool`: Check each file path starts with at least one allowed scope prefix. Use `PurePosixPath`.

3. `run_quality_gates(project_dir: Path) -> tuple[bool, str]`: Run `just all` via `subprocess.run`, capture output, handle `FileNotFoundError` gracefully.

4. `track_fix_iteration(task_id: str, attempt: int, max_iterations: int) -> tuple[bool, str]`: Return continue/escalate based on attempt count.

5. `validate_debugging_run(task: DebuggingTask, result: DebuggingResult) -> tuple[bool, str]`: Check overall_pass and escalated status.

> **Note:** `collect_debugging_result()` is deferred to Task 014-1 (after the agent prompt defines the output format). Do NOT implement it here.

**Acceptance Criteria:**
- [ ] `load_debugging_task` parses valid YAML and raises `ValueError` for missing fields
- [ ] `validate_source_scope` correctly accepts/rejects file paths
- [ ] `track_fix_iteration` returns escalation after max iterations
- [ ] `run_quality_gates` handles missing `just` binary gracefully
- [ ] `validate_debugging_run` checks overall_pass and escalated status
- [ ] `collect_debugging_result` is NOT in this file (deferred to Task 014-1)
- [ ] All functions have type annotations and docstrings
- [ ] `just all` passes
```
