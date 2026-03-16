# Discovery: Debugging Agent with Plugin Architecture for autopilot-cli

**Date:** 2026-03-15
**Status:** Discovery Complete -- Post-Review Revision, Ready for Task Planning
**Author:** Norwood (Discovery Agent)
**Source:** `docs/ideation/autopilot-debugging-agent-discovery.md`, `docs/ideation/desktop-agent-uat-discovery.md`
**Reviewed by:** Zod (Principal Engineer Review, 2026-03-15)

---

## The One-Liner

Add an autonomous debugging agent to autopilot-cli that tests acceptance criteria against live environments, diagnoses failures, fixes code, drafts regression tests, and performs UX review -- with debugging tool backends shipped as plugins (browser MCP for web apps, desktop agent for native apps).

## The Problem

The autopilot-cli orchestration pipeline has a verification gap. Today, agents can plan work, implement features, review code, and monitor deployments. But nobody is actually *using* the feature after it ships to staging and checking whether it works from a real user's perspective.

The existing `uat/` module handles acceptance test generation and execution at the code level -- it generates pytest tests from task acceptance criteria and runs them. That is useful for structural verification. But it cannot:

1. **Interactively test a deployed application** -- navigate a browser, fill forms, click buttons, observe actual behavior on staging
2. **Diagnose root causes from live behavior** -- read console errors, inspect network waterfalls, trace state management bugs through a running application
3. **Fix issues autonomously** -- when a staging flow breaks, the current pipeline creates issues and waits for humans
4. **Validate UX quality** -- no agent evaluates whether a feature looks right and feels right, only whether the code compiles and tests pass
5. **Test non-browser applications** -- desktop apps, Slack bots, mobile apps require visual interaction that browser tools cannot provide

The critical insight: the *mechanism* for interacting with the application under test varies wildly (browser automation vs. desktop VM control vs. mobile device interaction), but the *workflow* is identical: test acceptance criteria, diagnose failures, fix code, verify fixes, draft regression tests, review UX. This separation is the basis for the plugin architecture.

## Source Discovery Assessment

### Strengths of the Original Discovery

The `autopilot-debugging-agent-discovery.md` document is well-structured. The 6-phase workflow (Interactive Testing, Diagnose & Fix, Verify Fix, Draft E2E Tests, Verify E2E Tests, UX Review) is sound and maps cleanly to a generic pipeline. The YAML task file schema is practical -- human-readable, machine-parseable, and properly scoped with `source_scope` constraints. The safety guardrails (3-strike rule, scope constraints, staging-only) are production-ready. The Mailpit sidecar strategy for email capture is clever and avoids the testing-code-in-production anti-pattern.

### Gaps Requiring Adaptation

**1. RepEngine-specific coupling.** The original is written for a specific product (RepEngine) with specific agents (PL, EM, TA, QA, PD, DA) and specific infrastructure (Render, SES, Slack bot). autopilot-cli is a generic orchestration framework -- it does not know what application it is orchestrating. The debugging agent must be project-agnostic.

**2. Hardcoded tool assumptions.** The original assumes Browser MCP (ruflo browser tools) is always available and Playwright is always the E2E framework. A generic framework must support different debugging tools and test frameworks through a plugin interface.

**3. Missing plugin boundary.** The original mentions a "tiered approach" (Playwright primary, Desktop UAT secondary) but does not define a formal interface between the debugging workflow and the tool backend. The tools are wired directly into the agent prompt. For autopilot-cli, this boundary must be explicit.

**4. Agent lifecycle gaps.** The original adds a debugging agent to a hardcoded `VALID_AGENTS` whitelist. autopilot-cli has a dynamic `AgentRegistry` that discovers agents from `.md` files. The debugging agent should leverage this existing pattern, not bypass it.

**5. No config model for debugging.** The original modifies `config.yaml` directly. autopilot-cli has a structured `AutopilotConfig` with frozen Pydantic models. The debugging agent needs proper config integration.

**6. Email strategy is project-specific.** Mailpit makes sense for a specific web app with magic link auth. For autopilot-cli, email capture should be one of potentially many "environment helpers" that plugins can provide, not a core debugging agent concern.

### Corrections for Adaptation

- **Remove all RepEngine references.** The debugging agent does not know about `stg-app.repengine.co`, `chris+repengine-uat-test@montesmakes.co`, or Render services. These are project-level configuration.
- **Remove Mailpit from core.** Email capture is an environment-specific concern. It belongs in the browser MCP plugin's configuration or as a project-level helper, not in the debugging agent core.
- **Generalize the agent roster.** The debugging agent does not know about PL, EM, QA, PD. It is dispatched by whatever planning agent the project configures. It reports results to the coordination board.
- **Replace YAML task file with Pydantic model.** The YAML schema is good, but autopilot-cli uses frozen dataclasses and Pydantic models, not raw YAML parsing. Define proper models.

---

## Existing Components & Reuse Plan

### What We Will Reuse

| Component | Location | How We Use It |
|-----------|----------|---------------|
| `AgentRegistry` | `src/autopilot/core/agent_registry.py` | Debugging agent registered as `.md` file in `.autopilot/agents/`, discovered automatically. No code changes to registry. |
| `AgentInvoker` | `src/autopilot/orchestration/agent_invoker.py` | Invokes the debugging agent with retry and model fallback. No changes needed -- `invoke()` works for any registered agent. |
| `Scheduler` | `src/autopilot/orchestration/scheduler.py` | Executes debugging dispatches as part of the cycle. The debugging agent is just another dispatch. |
| `Dispatch` / `DispatchPlan` | `src/autopilot/core/models.py` | Debugging agent receives dispatches through the standard model. No changes needed. |
| `CircuitBreaker` | `src/autopilot/orchestration/circuit_breaker.py` | Protects against debugging agent timeout loops. Already integrated with scheduler. |
| `HookRunner` | `src/autopilot/orchestration/hooks.py` | Can trigger debugging runs via `post_dispatch` hooks. Variable substitution supports `{agent}`, `{action}` context. |
| `EnforcementRule` protocol | `src/autopilot/enforcement/rules/base.py` | The `@runtime_checkable` Protocol pattern is the precedent for our plugin protocol. Same design: define a protocol, implementations satisfy it. |
| `UATPipeline` | `src/autopilot/uat/pipeline.py` | Reference for pipeline-stage orchestration pattern (load context, generate, execute, report). The debugging pipeline follows the same structure. |
| `TestExecutor` / `UATResult` | `src/autopilot/uat/test_executor.py` | Reuse `UATResult` data model for regression test execution results. Extend `TestExecutor` or compose with it for running generated regression tests. |
| `AutopilotConfig` | `src/autopilot/core/config.py` | Add `DebuggingConfig` as a new section following the frozen Pydantic model pattern (same as `WorkspaceConfig`, `EnforcementConfig`, etc.) |
| `coordination/board.py` | `src/autopilot/coordination/board.py` | Debugging agent posts findings and fix PRs to the coordination board. Uses existing announcement and decision-log patterns. |
| Frozen dataclass pattern | Throughout `src/autopilot/core/models.py` | All debugging models use `@dataclass(frozen=True)` consistent with `Dispatch`, `AgentResult`, `CycleResult`, etc. |

### What We Will NOT Reuse

| Component | Reason |
|-----------|--------|
| `uat/spec_engine.py` (SpecCrossReferenceEngine) | The debugging agent does not cross-reference RFC/Discovery/UX specs. It tests live acceptance criteria from task files, not spec traceability. |
| `uat/traceability.py` | Same reason -- debugging is runtime verification, not spec compliance. |
| `uat/test_generator.py` | The debugging agent generates E2E tests for the *project's* test framework (Playwright, pytest, etc.), not autopilot's internal UAT tests. Generation is delegated to the LLM agent, not a template engine. |
| `monitoring/` health check pattern | The debugging agent does not poll health endpoints. It interactively tests full user flows. The monitoring module's concern is "is the service up?" while debugging's concern is "does the feature work?" |

### Consolidation Opportunities

1. **Result models.** `UATResult` and the proposed `DebuggingResult` share structural similarity (pass/fail/skip counts, category breakdowns, failure details). After implementation, if a third result type emerges, consolidate into a shared `VerificationResult` base. For now, two types is below the Rule of Three threshold -- keep them separate but structurally aligned so future consolidation is trivial.

2. **Support function patterns.** Both `UATPipeline.run()` and the proposed `pipeline.py` support functions follow: load context, validate, execute, report results, handle errors gracefully. If a third pipeline emerges, extract shared utilities. Same Rule of Three rationale.

3. **Config sections.** The pattern of `FooConfig(BaseModel)` with `ConfigDict(frozen=True)` added to `AutopilotConfig` is well-established (12 sections already). No consolidation needed -- this is a healthy pattern.

---

## Plugin Architecture Design

### Design Decision: Why Plugins?

The debugging agent's workflow is stable:
1. Load acceptance criteria
2. Test interactively against the live environment
3. Diagnose failures
4. Fix source code
5. Verify fixes
6. Draft regression tests
7. Review UX

But the *tool* for step 2 (and 3 and 7) varies by application type:
- **Web applications**: Browser MCP tools (navigate, click, fill, screenshot, read console)
- **Desktop applications**: Desktop agent (UI-TARS + Lume VM -- screenshot, click, type in native GUI)
- **API-only services**: HTTP client tools (curl, httpie -- no browser needed)
- **Mobile applications**: Future -- Appium, XCUITest, etc.

A plugin architecture lets us ship the workflow once and swap the tool backend.

### Architecture Decision: Plugin Protocol vs. Abstract Base Class

**Options:**

1. **`typing.Protocol` (structural typing)** -- Define a `DebuggingTool` protocol. Any class with the right methods satisfies it. No inheritance required.
   - Pro: Follows the `EnforcementRule` precedent in `enforcement/rules/base.py`
   - Pro: Third-party plugins do not need to import our base class
   - Pro: `@runtime_checkable` enables `isinstance()` validation
   - Con: No default method implementations

2. **Abstract Base Class** -- Define `BaseDebuggingTool(ABC)` with abstract methods and shared helpers.
   - Pro: Can provide default implementations (e.g., screenshot capture, result formatting)
   - Pro: Shared state management (session tracking, retry logic)
   - Con: Inheritance coupling -- third-party plugins must import and extend our class
   - Con: No precedent in this codebase (enforcement uses Protocol)

3. **Hybrid** -- Protocol for the interface contract, optional mixin/base class for shared utilities.
   - Pro: Best of both -- structural typing for the contract, concrete helpers for convenience
   - Con: Two concepts to understand
   - Con: Mixin-based reuse can get confusing

**Decision: Option 1 -- `typing.Protocol` with `@runtime_checkable`.**

This matches the established `EnforcementRule` pattern in the codebase. The debugging tool protocol defines the minimum contract. Shared utilities (retry logic, screenshot comparison, result formatting) go in a `utils` module that plugins can import optionally. No inheritance required.

### Architecture Decision: Plugin Discovery

**Options:**

1. **Directory-based discovery** (like `AgentRegistry`) -- Scan a directory for Python modules, import them, find classes satisfying the protocol.
   - Pro: Consistent with how agent prompts are discovered
   - Con: Requires import machinery, potential import errors

2. **Config-based registration** -- Plugins declared in `config.yaml` with module paths, loaded on demand.
   - Pro: Explicit, no magic
   - Pro: Consistent with enforcement's `categories` list in config
   - Con: Requires config changes to add a plugin

3. **Entry points** (setuptools/importlib.metadata) -- Plugins register via `[project.entry-points]` in `pyproject.toml`.
   - Pro: Standard Python packaging pattern
   - Pro: Third-party packages install and register automatically
   - Con: Over-engineered for the current scope (2 plugins, same repo)

**Decision: Option 2 -- Managed config-based registration.**

Plugins are declared in `config.yaml` under `debugging.tools`. Each entry maps a tool name to a Python module path. The debugging pipeline loads the configured tool at runtime. This is explicit, testable, and does not require import-time scanning. If third-party plugins become common (unlikely near-term), we can add entry-point support later without breaking changes.

The CLI provides management commands so users do not need to edit YAML manually:

```bash
# Register a plugin (validates protocol compliance, writes to config.yaml)
autopilot debug add-tool browser_mcp \
  --module autopilot.debugging.tools.browser_mcp \
  --class BrowserMCPTool

# List registered plugins with health/load status
autopilot debug list-tools
# Output:
#   browser_mcp    autopilot.debugging.tools.browser_mcp.BrowserMCPTool    ✓ loaded
#   desktop_agent  autopilot.debugging.tools.desktop_agent.DesktopAgentTool ✗ missing cua-computer

# Validate a plugin satisfies the protocol without registering it
autopilot debug validate-tool browser_mcp

# Remove a plugin from config
autopilot debug remove-tool desktop_agent
```

**Registration workflow:**
1. `add-tool` imports the module, instantiates the class, checks `isinstance(cls_instance, DebuggingTool)`, and rejects invalid plugins before writing to config
2. Built-in plugins (browser_mcp) are pre-registered when `autopilot init` creates a project config
3. `list-tools` shows what's available, what's healthy, what's broken
4. The YAML remains the source of truth -- CLI commands just manage it safely

```yaml
# .autopilot/config.yaml
debugging:
  enabled: true
  tool: "browser_mcp"  # active plugin for this project
  tools:
    browser_mcp:
      module: "autopilot.debugging.tools.browser_mcp"
      class: "BrowserMCPTool"
    desktop_agent:
      module: "autopilot.debugging.tools.desktop_agent"
      class: "DesktopAgentTool"
  max_fix_iterations: 3
  timeout_seconds: 1800
  regression_test_framework: "playwright"  # or "pytest", project-specific
```

### Plugin Protocol Definition

```python
# src/autopilot/debugging/tools/protocol.py

from __future__ import annotations
from enum import StrEnum
from typing import Protocol, runtime_checkable
from dataclasses import dataclass, field

PROTOCOL_VERSION: int = 1
"""Module-level protocol version. Bumped on breaking changes."""

class ToolCapability(StrEnum):
    """Supported debugging tool capabilities."""
    INTERACTIVE_TEST = "interactive_test"
    CONSOLE_CAPTURE = "console_capture"
    NETWORK_CAPTURE = "network_capture"
    SCREENSHOT = "screenshot"
    UX_REVIEW = "ux_review"

@dataclass(frozen=True)
class InteractionResult:
    """Result of a single tool interaction with the application."""
    success: bool
    screenshot_path: str = ""
    console_output: str = ""
    network_log: str = ""
    observation: str = ""  # LLM-generated description of what was observed
    error: str = ""

@dataclass(frozen=True)
class DiagnosticEvidence:
    """Evidence collected during failure diagnosis."""
    screenshots: tuple[str, ...] = ()
    console_errors: tuple[str, ...] = ()
    network_failures: tuple[str, ...] = ()
    state_dumps: tuple[str, ...] = ()
    observations: str = ""

@dataclass(frozen=True)
class UXObservation:
    """A single UX review observation."""
    category: str  # layout, typography, color, spacing, interaction
    severity: str  # critical, suggestion, praise
    description: str
    screenshot_path: str = ""
    element_reference: str = ""

@dataclass(frozen=True)
class ProvisionResult:
    """Result of a one-time plugin provisioning operation."""
    success: bool
    components_installed: tuple[str, ...] = ()  # e.g., ("lume", "ui-tars-7b", "ollama")
    manual_steps: tuple[str, ...] = ()  # steps user must complete manually
    error: str = ""
    duration_seconds: float = 0.0

@dataclass(frozen=True)
class ProvisionStatus:
    """Health status of a plugin's provisioned infrastructure."""
    provisioned: bool  # has provision() been run?
    ready: bool  # is everything healthy and usable?
    components: dict[str, str] = field(default_factory=dict)
    # e.g., {"lume": "healthy", "ui-tars-7b": "healthy", "ollama": "not_found"}
    message: str = ""

@runtime_checkable
class DebuggingTool(Protocol):
    """Protocol for debugging tool plugins.

    Implementations provide the interactive testing, diagnosis,
    and UX review capabilities for a specific application type.

    The protocol is synchronous to match the codebase convention
    (EnforcementRule.check(), AgentInvoker.invoke(), Scheduler.run_cycle()
    are all sync). Plugins that wrap async backends (Browser MCP, Cua SDK)
    manage their own event loop internally via asyncio.run() or equivalent.
    This keeps the protocol compatible with isinstance() checks and avoids
    introducing asyncio as a dependency in the pipeline or test harness.
    """

    @property
    def name(self) -> str:
        """Tool identifier (e.g., 'browser_mcp', 'desktop_agent')."""
        ...

    @property
    def capabilities(self) -> frozenset[ToolCapability]:
        """Supported capabilities from ToolCapability enum."""
        ...

    def provision(self, settings: dict[str, object]) -> ProvisionResult:
        """One-time infrastructure setup for this tool.

        Called by `autopilot debug provision <tool-name>`. This is NOT called
        during normal pipeline runs -- it is a separate, potentially
        long-running, potentially interactive operation.

        The `settings` dict comes from `DebuggingToolConfig.settings` in
        config.yaml. Each plugin should define its own Pydantic model to
        validate these settings internally (e.g., `BrowserMCPSettings`).
        The loader calls `validate_settings()` at registration time if
        the plugin exposes it.

        Examples:
        - Browser MCP: register ruflo MCP server, verify browser binary
        - Desktop Agent: install Lume, pull macOS image, create VM,
          download UI-TARS model, install Ollama + validation model,
          configure VM permissions, create base snapshot

        Returns a ProvisionResult indicating success/failure and any
        manual steps the user must complete (e.g., granting macOS
        Accessibility permissions).
        """
        ...

    def deprovision(self) -> None:
        """Remove infrastructure installed by provision().

        Called by `autopilot debug deprovision <tool-name>`. Cleans up
        VMs, removes MCP server registrations, etc.
        """
        ...

    def check_provisioned(self) -> ProvisionStatus:
        """Check whether provision() has been run and infra is healthy.

        Called by `autopilot debug status` and at the start of `setup()`.
        Returns a status indicating whether the tool is ready, needs
        provisioning, or has a degraded component.
        """
        ...

    def setup(self, settings: dict[str, object]) -> None:
        """Per-session initialization (connect to browser, start VM, etc.).

        Called at the start of each debugging run. Should be fast (~seconds).
        Raises ToolNotProvisionedError if check_provisioned() indicates
        the tool is not ready.

        The `settings` dict comes from `DebuggingToolConfig.settings` in
        config.yaml. Plugins validate internally with their own Pydantic model.

        Async plugins wrap their initialization in asyncio.run() internally.
        """
        ...

    def teardown(self) -> None:
        """Per-session cleanup (close browser, stop VM, etc.)."""
        ...

    def execute_step(
        self,
        action: str,
        target: str,
        *,
        value: str = "",
        expect: str = "",
        timeout_seconds: int = 30,
    ) -> InteractionResult:
        """Execute a single test step (navigate, click, fill, etc.)."""
        ...

    def capture_diagnostic_evidence(self) -> DiagnosticEvidence:
        """Capture current application state for diagnosis."""
        ...

    def capture_screenshot(self, label: str) -> str:
        """Take a screenshot, return file path."""
        ...

    def evaluate_ux(
        self,
        criteria: tuple[str, ...],
        design_system_ref: str = "",
    ) -> tuple[UXObservation, ...]:
        """Perform UX review of current application state."""
        ...
```

### Browser MCP Plugin Design

The browser MCP plugin wraps ruflo browser tools for web application testing. It translates the generic `DebuggingTool` protocol into Browser MCP tool calls.

**Module:** `src/autopilot/debugging/tools/browser_mcp.py`

**Provisioning (`provision()`):**
- Registers the ruflo MCP server via `claude mcp add` (or verifies it is already registered)
- Verifies browser binary availability (Chromium for headless, or system browser for headed)
- Validates MCP server responds to a health check (e.g., `browser_snapshot` returns without error)
- Returns `ProvisionResult(manual_steps=())` -- fully automated, no manual steps required

**Provision check (`check_provisioned()`):**
- Checks MCP server is registered in `.mcp.json` or Claude config
- Checks MCP server process is reachable
- Returns component status: `{"ruflo_mcp": "healthy", "browser": "healthy"}`

**Per-session lifecycle:**
- `setup()` opens a browser session, navigates to the staging URL
- `teardown()` closes the browser session
- `execute_step()` maps actions to Browser MCP calls: `navigate` -> `browser_open`, `click` -> `browser_click`, `fill` -> `browser_fill`, etc.
- `capture_diagnostic_evidence()` captures console output via `browser_eval`, network state, and screenshots via `browser_screenshot`
- `evaluate_ux()` captures screenshots and sends them to the LLM with structured evaluation prompts
- Session management: maintains browser session across steps, supports login/logout flows
- **Does NOT embed Mailpit or email logic.** Email capture is configured per-project as an environment helper, not baked into the plugin.

**Capability set:** `frozenset({ToolCapability.INTERACTIVE_TEST, ToolCapability.CONSOLE_CAPTURE, ToolCapability.NETWORK_CAPTURE, ToolCapability.SCREENSHOT, ToolCapability.UX_REVIEW})`

### Desktop Agent Plugin Design

The desktop agent plugin wraps the Cua SDK + Lume VM infrastructure for native application testing (Slack Desktop, VS Code, mobile emulators, etc.).

**Module:** `src/autopilot/debugging/tools/desktop_agent.py`

**Provisioning (`provision()`) -- heavy, potentially interactive:**
1. **Install Lume** (if not present): Download and run Lume installer script
2. **Pull macOS image** (~80GB): `lume pull macos-sequoia-vanilla:latest`
3. **Create VM**: `lume run --name autopilot-uat --memory 8GB --cpu 4`
4. **Configure VM**: Set resolution to 1024x768, disable screen saver/sleep/auto-update, grant Accessibility and Screen Recording permissions
5. **Install target application** inside VM (e.g., `brew install --cask slack`)
6. **Download action model**: UI-TARS 1.5 7B via HuggingFace (~16GB)
7. **Install validation model**: Ollama + Gemma 3 12B (`ollama pull gemma3:12b`)
8. **Create base snapshot**: `lume snapshot create autopilot-uat clean-slate` (if Lume supports it) or document manual snapshot procedure
9. Returns `ProvisionResult(manual_steps=("Sign into Slack workspace inside VM", "Grant macOS Accessibility permission if prompted"))` -- some steps require manual intervention

**Provision check (`check_provisioned()`):**
- Checks Lume is installed and VM exists
- Checks VM can be started/connected to via VNC
- Checks action model (UI-TARS) is downloadable/loaded
- Checks Ollama is running and validation model is available
- Returns component status: `{"lume": "healthy", "vm_autopilot-uat": "healthy", "ui-tars-7b": "healthy", "ollama": "healthy", "gemma3-12b": "not_found"}`

**Per-session lifecycle:**
- `setup()` starts or restores VM snapshot, initializes ComputerAgent, runs pre-flight dialog dismissal
- `teardown()` saves VM snapshot if configured, stops VM
- `execute_step()` translates actions into Cua agent commands: `navigate` -> open application/URL, `click` -> coordinate-based click via UI-TARS, `fill` -> keyboard input via ComputerAgent
- `capture_diagnostic_evidence()` takes screenshots and sends to Gemma 3 12B for visual analysis (cannot capture console/network in desktop mode)
- `evaluate_ux()` captures screenshots and uses Gemma 3 12B or Claude for visual comparison against design references

**Capability set:** `frozenset({ToolCapability.INTERACTIVE_TEST, ToolCapability.SCREENSHOT, ToolCapability.UX_REVIEW})` (no `CONSOLE_CAPTURE` or `NETWORK_CAPTURE`)

**Critical learnings from the desktop-agent-uat-discovery to incorporate:**

1. **Click accuracy is unreliable.** UI-TARS 1.5 7B has approximately 70-80% click accuracy on desktop UIs. The plugin must implement retry logic with position jitter for failed clicks.
2. **VM state drift is real.** Slack auto-updates, notification banners, and "What's New" dialogs can derail the agent. The plugin must restore from a known-good VM snapshot before each test run and implement a pre-flight dialog dismissal sequence.
3. **Test execution is slow.** 60-120 seconds per test in desktop mode vs. 2-5 seconds for browser tests. The debugging pipeline must account for this in timeout configuration.
4. **macOS permissions are aggressive.** Sequoia prompts for accessibility, screen recording, and automation permissions. The VM snapshot must include all permissions pre-authorized.
5. **Dual-model architecture adds complexity.** UI-TARS for actions + Gemma/Claude for validation means two model configurations, two failure modes, and twice the debugging surface. Keep the model selection configurable per-plugin.

### Core Debugging Pipeline

**Module:** `src/autopilot/debugging/pipeline.py`

The debugging pipeline is **not a Python orchestrator** -- it is a set of support tools and validation functions that the LLM agent calls during its session. The LLM agent, running as a standard AgentInvoker session, IS the pipeline (see ADR-D03).

The pipeline module provides:

1. **Task loading**: Parse `DebuggingTask` from YAML task files. The LLM agent receives the task as part of its prompt.

2. **Guardrail tools** (exposed as callable functions the agent can invoke):
   - `validate_source_scope(modified_files, allowed_scope)` -- returns pass/fail
   - `run_quality_gates(project_dir)` -- runs `just all`, returns structured result
   - `track_fix_iteration(task_id, attempt)` -- increments counter, returns whether to continue or escalate

3. **Result collection**: After the agent session completes, `collect_debugging_result()` reads the agent's output, coordination board posts, and git history to assemble a `DebuggingResult`.

4. **Post-run validation**: `validate_debugging_run(task, result)` checks that acceptance criteria were addressed, source scope was respected, and quality gates passed.

```python
# Conceptual structure -- support functions, not an orchestrator

def load_debugging_task(task_path: Path) -> DebuggingTask:
    """Parse a YAML debugging task file into a typed model."""
    ...

def validate_source_scope(
    modified_files: tuple[str, ...],
    allowed_scope: tuple[str, ...],
) -> bool:
    """Check that all modified files are within the allowed source scope."""
    ...

def run_quality_gates(project_dir: Path) -> tuple[bool, str]:
    """Run `just all` and return (passed, output)."""
    ...

def track_fix_iteration(
    task_id: str,
    attempt: int,
    max_iterations: int,
) -> tuple[bool, str]:
    """Track fix attempt count. Returns (should_continue, message).

    Returns (False, "escalate") when max_iterations is reached.
    """
    ...

def collect_debugging_result(
    task: DebuggingTask,
    agent_result: InvokeResult,
) -> DebuggingResult:
    """Assemble a DebuggingResult from agent output and git history."""
    ...

def validate_debugging_run(
    task: DebuggingTask,
    result: DebuggingResult,
) -> tuple[bool, str]:
    """Post-run validation. Returns (passed, reason)."""
    ...
```

The agent's system prompt (`debugging-agent.md`) instructs the LLM to follow the 6-phase workflow:
1. **Interactive Testing**: Use the configured debugging tool (Browser MCP / Desktop Agent) to test each acceptance criterion
2. **Diagnose failures**: Capture diagnostic evidence, analyze console errors and network failures
3. **Fix source code**: Modify files within `source_scope`, call `validate_source_scope` to confirm
4. **Verify fix**: Re-test acceptance criteria, call `run_quality_gates`
5. **Draft regression tests**: Write E2E tests in the project's test framework
6. **UX Review**: Capture screenshots and evaluate against UX criteria

The 3-strike escalation rule is enforced by the `track_fix_iteration` tool returning an escalation directive after `max_fix_iterations` attempts.

### Data Models

**Module:** `src/autopilot/debugging/models.py`

```python
@dataclass(frozen=True)
class DebuggingTask:
    """Input specification for a debugging run."""
    task_id: str
    feature: str
    title: str
    description: str
    staging_url: str
    steps: tuple[TestStep, ...]
    acceptance_criteria: tuple[str, ...]
    source_scope: tuple[str, ...]
    ux_review_enabled: bool = True
    ux_capture_states: tuple[str, ...] = ()

@dataclass(frozen=True)
class TestStep:
    """A single step in the interactive test plan."""
    action: str  # navigate, fill, click, wait, assert, wait_for_email, etc.
    target: str
    value: str = ""
    expect: str = ""
    timeout_seconds: int = 30

@dataclass(frozen=True)
class FixAttempt:
    """Record of a single fix iteration."""
    iteration: int
    diagnosis: str
    files_modified: tuple[str, ...]
    pr_url: str = ""
    tests_passed: bool = False
    error: str = ""

@dataclass(frozen=True)
class InteractiveTestResults:
    """Results from Phase 1: Interactive Testing."""
    steps_total: int = 0
    steps_passed: int = 0
    steps_failed: int = 0
    all_passed: bool = False
    step_results: tuple[InteractionResult, ...] = ()  # from protocol.py
    duration_seconds: float = 0.0

@dataclass(frozen=True)
class FixCycleResults:
    """Results from Phase 2-3: Diagnose & Fix cycle."""
    attempts: tuple[FixAttempt, ...] = ()
    resolved: bool = False
    final_diagnosis: str = ""
    duration_seconds: float = 0.0

@dataclass(frozen=True)
class RegressionTestResults:
    """Results from Phase 4-5: E2E regression test generation and execution."""
    tests_generated: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    test_file_path: str = ""
    duration_seconds: float = 0.0

@dataclass(frozen=True)
class UXReviewResults:
    """Results from Phase 6: UX Review."""
    observations: tuple[UXObservation, ...] = ()  # from protocol.py
    overall_pass: bool = False
    summary: str = ""
    duration_seconds: float = 0.0

@dataclass(frozen=True)
class DebuggingResult:
    """Complete output from a debugging pipeline run."""
    task_id: str
    overall_pass: bool = False
    test_results: InteractiveTestResults | None = None
    fix_results: FixCycleResults | None = None
    regression_results: RegressionTestResults | None = None
    ux_results: UXReviewResults | None = None
    duration_seconds: float = 0.0
    escalated: bool = False
    escalation_reason: str = ""

class ToolNotProvisionedError(RuntimeError):
    """Raised by setup() when a debugging tool is not provisioned."""

    def __init__(self, tool_name: str, status: ProvisionStatus) -> None:
        self.tool_name = tool_name
        self.status = status
        super().__init__(
            f"Tool '{tool_name}' is not provisioned. "
            f"Run 'autopilot debug provision {tool_name}' first. "
            f"Status: {status.message}"
        )
```

### Config Model

**Added to:** `src/autopilot/core/config.py`

```python
class DebuggingToolConfig(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    module: str = ""
    class_name: str = Field(default="", alias="class")
    settings: dict[str, object] = Field(default_factory=dict)
    # Plugin-specific settings passed to provision() and setup().
    # Each plugin validates these internally with its own Pydantic model.

class DebuggingConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    enabled: bool = False
    tool: str = "browser_mcp"
    tools: dict[str, DebuggingToolConfig] = Field(default_factory=dict)
    max_fix_iterations: int = Field(default=3, gt=0, le=5)
    timeout_seconds: int = Field(default=1800, gt=0)
    regression_test_framework: str = "pytest"
    ux_review_enabled: bool = True
```

Added to `AutopilotConfig`:
```python
debugging: DebuggingConfig = Field(default_factory=DebuggingConfig)
```

---

## Implementation Plan

### Phase 1: Core Models and Plugin Protocol (5 points)

**Goal:** Define the debugging data models, plugin protocol, and config integration. No runtime behavior yet -- this is the contract that everything else builds on.

**Deliverables:**
1. `src/autopilot/debugging/__init__.py` -- Package initialization
2. `src/autopilot/debugging/models.py` -- `DebuggingTask`, `TestStep`, `FixAttempt`, `DebuggingResult`, and related frozen dataclasses
3. `src/autopilot/debugging/tools/__init__.py` -- Tools subpackage
4. `src/autopilot/debugging/tools/protocol.py` -- `DebuggingTool` protocol, `InteractionResult`, `DiagnosticEvidence`, `UXObservation`
5. `src/autopilot/core/config.py` -- Add `DebuggingConfig`, `DebuggingToolConfig` to config hierarchy
6. `tests/debugging/` -- Unit tests for all models and config validation

**Success Criteria:**
- All models freeze correctly (immutable)
- Config loads from YAML with three-level merge
- `isinstance(obj, DebuggingTool)` works with `@runtime_checkable`
- `just all` passes

### Phase 2: Pipeline Support Functions and Plugin Loader (5 points)

**Goal:** The pipeline support functions (task loading, guardrails, result collection) and plugin loader work against a mock tool. No real browser or desktop interaction yet.

**Deliverables:**
1. `src/autopilot/debugging/pipeline.py` -- Support functions: `load_debugging_task()`, `validate_source_scope()`, `run_quality_gates()`, `track_fix_iteration()`, `collect_debugging_result()`, `validate_debugging_run()`
2. `src/autopilot/debugging/loader.py` -- Plugin loader: reads config, imports module, validates protocol compliance, checks `PROTOCOL_VERSION`
3. `tests/debugging/test_pipeline.py` -- Tests for all support functions with mock data
4. `tests/debugging/test_loader.py` -- Plugin loader tests with valid/invalid modules

**Success Criteria:**
- `load_debugging_task()` parses YAML into typed `DebuggingTask` model
- `validate_source_scope()` correctly accepts/rejects file paths
- `track_fix_iteration()` returns escalation directive after `max_fix_iterations`
- Plugin loader rejects classes that do not satisfy the protocol
- Plugin loader warns on version mismatch
- `just all` passes

### Phase 3a: Browser MCP Plugin -- Core (5 points)

**Goal:** Browser MCP plugin implementing the `DebuggingTool` protocol with action mapping and session management.

**Deliverables:**
1. `src/autopilot/debugging/tools/browser_mcp.py` -- `BrowserMCPTool` implementing `DebuggingTool` protocol
2. Action mapping: `navigate`, `click`, `fill`, `wait_for_navigation`, `assert_text`, `assert_visible`
3. Session management: login persistence, session validation
4. `tests/debugging/tools/test_browser_mcp.py` -- Tests with mocked MCP tool responses

**Success Criteria:**
- Plugin satisfies `DebuggingTool` protocol (`isinstance` check passes)
- Action mapping translates all step types to MCP tool calls
- Session persists across test steps within a single run
- `just all` passes

### Phase 3b: Browser MCP Plugin -- Diagnostics & UX (5 points)

**Goal:** Console capture, network capture, screenshot capture, and UX review capabilities for the browser MCP plugin.

**Deliverables:**
1. Console capture via `browser_eval` for diagnostic evidence
2. Network log capture for failure diagnosis
3. Screenshot capture at each step and for UX review
4. UX evaluation: capture screenshots, send to LLM with structured prompts
5. Additional tests for diagnostic and UX capabilities

**Success Criteria:**
- Console errors captured and included in diagnostic evidence
- Screenshots saved with labeled file paths
- UX evaluation returns structured `UXObservation` results
- `just all` passes

### Phase 4a: CLI Integration -- Commands (5 points)

**Goal:** `autopilot debug` CLI command group with plugin management and run command.

**Deliverables:**
1. `src/autopilot/cli/debug.py` -- Typer subcommand group:
   - `autopilot debug run <task-file>` -- Load task, check provisioned, initialize plugin, invoke debugging agent, report results
   - `autopilot debug list-tools` -- Show registered plugins with provision/health status
   - `autopilot debug add-tool <name> --module <mod> --class <cls>` -- Validate protocol compliance, write to config via load-modify-save (ADR-D05)
   - `autopilot debug remove-tool <name>` -- Remove plugin from config
   - `autopilot debug validate-tool <name>` -- Check plugin satisfies protocol without registering
   - `autopilot debug provision <name>` -- Run one-time infrastructure setup for a plugin
   - `autopilot debug deprovision <name>` -- Remove infrastructure installed by provision
   - `autopilot debug status` -- Show debugging pipeline health, active tool provision status, component health

**Success Criteria:**
- `autopilot debug add-tool` validates protocol compliance and rejects invalid plugins
- `autopilot debug list-tools` shows configured plugins, their capabilities, and load status
- Config mutation follows load-modify-save pattern (ADR-D05) -- no in-place mutation of frozen models
- `just all` passes

### Phase 4b: Agent Integration (3 points)

**Goal:** Debugging agent registered in AgentRegistry, integrated with coordination board and orchestration cycle.

**Deliverables:**
1. Agent prompt template: `.autopilot/agents/debugging-agent.md` (system prompt defining the 6-phase workflow, 3-strike escalation rule, scope constraints)
2. Integration with `AgentRegistry` -- debugging agent auto-discovered from `.md` file
3. Integration with coordination board -- debugging results posted as announcements/decisions
4. `autopilot init` updated to pre-register browser_mcp tool in default config

**Success Criteria:**
- Debugging agent appears in `autopilot agent list`
- Agent prompt defines complete 6-phase workflow with guardrail tool usage
- Results posted to coordination board
- `just all` passes

### Phase 5: Desktop Agent Plugin (5 points)

**Goal:** Desktop agent plugin for testing non-browser applications, incorporating learnings from the desktop-agent-uat-discovery.

**Deliverables:**
1. `src/autopilot/debugging/tools/desktop_agent.py` -- `DesktopAgentTool` implementing `DebuggingTool` protocol
2. Cua SDK integration: VM lifecycle (start, restore snapshot, teardown)
3. Action mapping with retry logic for click accuracy issues
4. Pre-flight dialog dismissal sequence
5. Dual-model configuration: UI-TARS for actions, configurable validation model
6. `tests/debugging/tools/test_desktop_agent.py` -- Tests with mocked Cua SDK

**Success Criteria:**
- Plugin satisfies `DebuggingTool` protocol
- VM snapshot restore works in tests
- Click retry logic handles UI-TARS accuracy issues
- Capability set correctly excludes `console_capture` and `network_capture`
- `just all` passes (desktop integration tests guarded by `AUTOPILOT_INTEGRATION_TESTS=1` env var, per ADR-D06)

### Phase 6: Orchestration Integration (3 points)

**Goal:** The debugging agent runs as part of the standard autopilot cycle, dispatched after deploy verification.

**Deliverables:**
1. Hook configuration for post-deploy debugging triggers
2. Scheduler integration: debugging dispatches processed like any other agent
3. Result reporting: debugging results included in cycle reports
4. Documentation: `docs/agents/debugging-agent.md` usage guide

**Success Criteria:**
- Debugging agent dispatched via standard `DispatchPlan`
- Cycle reports include debugging results
- Failed debugging runs trigger escalation to coordination board
- `just all` passes

---

## Risk Register

### HIGH RISK: Browser MCP Tool Availability

**Probability:** Medium (depends on ruflo MCP server being reachable)
**Impact:** High (debugging pipeline cannot run without a tool)
**Mitigation:** Plugin `check_provisioned()` validates infrastructure health before `setup()` runs. `autopilot debug provision <tool>` handles one-time setup (MCP server registration, model downloads, VM creation). Pipeline returns a clear `DebuggingResult` with `escalated=True` and reason if the tool is not provisioned or unavailable. The plugin loader validates at config load time that the configured module exists and the class satisfies the protocol.
**Detection:** `check_provisioned()` returns degraded status; `autopilot debug status` shows component-level health; `setup()` raises if not provisioned.

### HIGH RISK: Plugin Protocol Stability

**Probability:** Medium (protocol may need changes as we learn from real usage)
**Impact:** Medium (breaking changes require updating all plugins)
**Mitigation:** Keep the protocol minimal. Only require methods that all tool backends genuinely need. Put tool-specific methods in tool-specific interfaces. Use `capabilities` property so the pipeline can gracefully degrade when a tool lacks a feature (e.g., skip console capture for desktop agent). Version the protocol if breaking changes are unavoidable.
**Detection:** Type checker catches protocol violations at development time; `@runtime_checkable` catches them at load time.

### LOW RISK: Plugin Internal Async Management

**Probability:** Low (well-understood pattern: `asyncio.run()` within sync methods)
**Impact:** Low (isolated to plugin internals, not visible to pipeline or tests)
**Mitigation:** The `DebuggingTool` protocol is synchronous (ADR-D02). Plugins that wrap async backends (Browser MCP, Cua SDK) manage their own event loop internally. This is a standard Python pattern. The pipeline, tests, and config layer never see `async`. If a plugin has event loop issues, it is a plugin bug, not a framework bug.
**Detection:** Plugin-level unit tests; `autopilot debug validate-tool` checks protocol compliance including method signatures.

### MEDIUM RISK: Desktop Agent Reliability

**Probability:** High (documented in desktop-agent-uat-discovery: click accuracy 70-80%, VM state drift)
**Impact:** Medium (false failures waste fix cycles; false passes miss real bugs)
**Mitigation:** Implement retry logic with position jitter for clicks. Restore VM snapshot before each run. Add pre-flight validation sequence. Mark desktop plugin as "experimental" in initial release. Set higher tolerance thresholds for desktop UX review.
**Detection:** Track false positive/negative rates. If accuracy drops below 80%, escalate to prompt engineering review.

### LOW RISK: Config Migration for Existing Projects

**Probability:** High (existing configs do not have `debugging` section)
**Impact:** Low (Pydantic defaults handle missing sections gracefully)
**Mitigation:** `DebuggingConfig` has `enabled: bool = False` as default. Existing configs work unchanged. Projects opt in by adding `debugging.enabled: true` to their config.
**Detection:** Integration tests with config files that lack the debugging section.

### LOW RISK: Plugin Module Import Failures

**Probability:** Low (plugins are in-tree, not third-party)
**Impact:** Low (clear error message, debugging disabled)
**Mitigation:** Plugin loader wraps `importlib.import_module` in try/except, logs the full traceback, and returns a clear error. `autopilot debug list-tools` shows which plugins loaded and which failed.
**Detection:** `autopilot debug status` reports plugin health.

---

## Architecture Decision Records

### ADR-D01: Debugging Tool Plugin Protocol with Managed Config Registration

**Context:** The debugging agent needs to interact with different types of applications (web, desktop, mobile). The interaction mechanism varies but the workflow is constant.

**Decision:** Use `typing.Protocol` with `@runtime_checkable` to define the `DebuggingTool` interface. Plugins are registered in `config.yaml` (source of truth) and loaded via `importlib`. The CLI provides managed commands (`add-tool`, `remove-tool`, `validate-tool`, `list-tools`) so users do not edit YAML manually. `add-tool` validates protocol compliance at registration time.

**Rationale:** Matches the `EnforcementRule` precedent for the protocol. Config-based registration is explicit and testable. CLI management adds validation and discoverability without introducing magic (no directory scanning, no entry points). Built-in plugins are pre-registered by `autopilot init`.

**Trade-offs:** No default method implementations (plugins must implement everything). Acceptable because the protocol is small (10 methods) and the two initial plugins have very different implementations. Adding a plugin requires a CLI command or config edit, not just dropping a file -- this is intentional (explicit > implicit).

### ADR-D02: Synchronous Plugin Protocol with Internal Async

**Context:** Browser MCP and Cua SDK are both async. The debugging pipeline needs to call them. The rest of the codebase (`EnforcementRule.check()`, `AgentInvoker.invoke()`, `Scheduler.run_cycle()`) is entirely synchronous.

**Decision:** The `DebuggingTool` protocol methods are **synchronous**. Plugins that wrap async backends (Browser MCP, Cua SDK) manage their own event loop internally via `asyncio.run()` or equivalent within each method call.

**Rationale:**
1. A sync class cannot satisfy an async protocol without `async def` stubs, which defeats the structural typing benefit of `@runtime_checkable` Protocols
2. Every other Protocol/interface in the codebase is sync -- consistency reduces cognitive load
3. Tests do not need `pytest-asyncio` or `@pytest.mark.asyncio`
4. Simple tool implementations (e.g., an HTTP-based debugging tool using `requests`) should not be forced into async
5. The agent subprocess boundary (`AgentInvoker` → `run_claude_cli()`) already isolates the debugging pipeline from the scheduler -- there is no need for async at the protocol level to avoid blocking

**Trade-offs:** Each async plugin must manage its own event loop (call `asyncio.run()` or maintain a running loop). This is slightly more boilerplate in async plugins but keeps the protocol, pipeline, and tests simple. The boilerplate is isolated to the 2 async plugins, while the simplicity benefits everything else.

### ADR-D03: Debugging Agent as LLM-Orchestrated Standard Agent

**Context:** The debugging agent could run as (A) a Python-orchestrated pipeline that calls the LLM for specific decisions, or (B) an LLM agent session where the LLM drives the full workflow with tool-level guardrails.

**Decision:** Option B -- The debugging agent is a standard agent with a `.md` system prompt, discovered by `AgentRegistry`, dispatched by the scheduler, invoked by `AgentInvoker`. The LLM agent session IS the debugging pipeline. The agent's system prompt defines the 6-phase workflow. Debugging tool plugins (Browser MCP, Desktop Agent) are available as MCP tools within the Claude CLI session via `.mcp.json`.

**Rationale:**
1. This matches how `AgentInvoker` already works: it launches a Claude CLI subprocess with a system prompt + task prompt, and the LLM executes using available MCP tools.
2. Browser MCP tools are accessed via the Claude CLI session's native MCP integration, not via Python code calling the tools directly.
3. The debugging agent gets retry logic, model fallback, circuit breaker protection, and usage tracking from AgentInvoker for free.
4. The LLM can adapt to unexpected situations (novel error messages, unexpected UI states) better than a rigid scripted pipeline.

**Trade-offs:** Less deterministic than a code-driven pipeline. The LLM may deviate from the intended phase ordering. Mitigated by guardrails enforced at the tool response level (see ADR-D04).

### ADR-D04: Guardrails via Tool Responses and System Prompt

**Context:** With the LLM as the outer loop (ADR-D03), guardrails cannot be enforced by Python code controlling phase ordering. Instead, guardrails must be enforced at the boundaries the system does control: tool responses, system prompt instructions, and post-run validation.

**Decision:** Guardrails are enforced through three mechanisms:

1. **System prompt instructions**: The debugging agent's `.md` system prompt defines the 6-phase workflow ordering, the 3-strike escalation rule, and source scope constraints. The prompt is the primary control mechanism.

2. **Tool-level validation**: Support functions in `pipeline.py` validate inputs and return structured pass/fail responses:
   - `validate_source_scope(modified_files, allowed_scope)` checks that proposed file modifications are within `source_scope` before allowing edits
   - `run_quality_gates(project_dir)` runs `just all` and returns pass/fail
   - `track_fix_iteration(task_id, attempt, max_iterations)` tracks fix attempt count and returns an escalation directive when the limit is reached

3. **Post-run validation**: After the agent session completes, `validate_debugging_run()` checks the output: did acceptance criteria pass? Were only in-scope files modified? Did quality gates pass? If validation fails, the result is marked `escalated=True` with a reason.

**Rationale:**
- vs. code-driven pipeline (original ADR-D04): The LLM-as-outer-loop model from ADR-D03 means Python code does not control phase ordering. Guardrails must operate at the tool boundary instead.
- Tool-level validation is enforceable by code (the function checks constraints before returning), while prompt-level instructions are best-effort.
- Post-run validation catches anything the tool-level checks missed.

**Trade-offs:** The 3-strike rule is enforced by a tool that tracks state, not by a Python loop. If the LLM ignores the tool's escalation directive, the post-run validation catches it. This is less strict than a code-controlled loop but compatible with the LLM-as-agent execution model.

### ADR-D05: Config Mutation via Load-Modify-Save

**Context:** The `autopilot debug add-tool` command needs to modify `config.yaml` to register a plugin. All config models use `ConfigDict(frozen=True)` -- no in-place mutation is possible.

**Decision:** Use the load-modify-save pattern:
1. Load YAML file into a plain dict via `yaml.safe_load()`
2. Modify the dict (e.g., add/remove tool entry under `debugging.tools`)
3. Validate the modified dict via `AutopilotConfig.model_validate(dict)` to catch errors before writing
4. Serialize back to YAML via `yaml.dump()` and write to file

This is the same round-trip pattern used by `from_yaml()` / `to_yaml()` on `AutopilotConfig`. The frozen Pydantic models are never mutated -- a new model is instantiated from the modified dict for validation only.

**Rationale:** Consistent with existing `to_yaml()` pattern in `config.py` (`model_dump(mode="json")` then `yaml.dump()`). No need for a separate config mutation API. The plain-dict approach is explicit and testable.

**Trade-offs:** The intermediate dict is untyped. Mitigated by the `model_validate()` step catching errors before the write.

### ADR-D06: Provisioning Test Strategy

**Context:** Plugin provisioning (`provision()`, `check_provisioned()`) interacts with external infrastructure (MCP server registration, VM lifecycle, model downloads). Tests must cover this without requiring real infrastructure on every test run.

**Decision:** Two-tier test strategy:

1. **Unit tests (always run):** Mock `subprocess.run` / `importlib.import_module` calls. Validate that:
   - `provision()` calls the correct commands in the correct order
   - `check_provisioned()` returns correct status for healthy/degraded/missing components
   - Error handling works for all failure modes (command not found, timeout, partial failure)
   - `ProvisionResult` and `ProvisionStatus` models are populated correctly

2. **Integration tests (opt-in via environment variable):** Guarded by `os.environ.get("AUTOPILOT_INTEGRATION_TESTS")` check at the top of the test function (not `pytest.mark.skipif`, matching existing codebase pattern where no skipif decorators are used). These tests:
   - Actually register/unregister an MCP server
   - Actually validate protocol compliance of a real plugin class
   - Run against a local test fixture (not production infrastructure)

**Rationale:** The codebase has no `pytest.mark.skipif` usage anywhere. Environment variable checks at runtime are the established pattern. Real subprocess fixtures (SQLite, filesystem) are used throughout existing tests.

**Trade-offs:** Integration tests require manual setup to run. Acceptable because provisioning is a one-time operation and the unit tests cover the logic paths.

### ADR-D07: Protocol Versioning Strategy

**Context:** The `DebuggingTool` protocol may need to evolve as we learn from real usage. Breaking changes would require updating all plugins simultaneously.

**Decision:** Lightweight versioning:
1. A `PROTOCOL_VERSION: int = 1` module-level constant in `protocol.py`
2. The plugin loader logs a warning if a loaded plugin class does not expose a `protocol_version` class attribute or if it does not match the current `PROTOCOL_VERSION`
3. Breaking changes (if ever needed) bump `PROTOCOL_VERSION` and the loader rejects plugins with mismatched versions

**Rationale:** The protocol is small (10 methods) with only 2 in-tree plugins. Formal versioning (semver, deprecation cycles) is premature. The version constant plus loader warning gives sufficient protection without over-engineering.

**Trade-offs:** No automated migration path for plugins. Acceptable given the small plugin count and in-tree ownership.

---

## File Structure Summary

```
src/autopilot/
  debugging/
    __init__.py
    models.py               # DebuggingTask, TestStep, DebuggingResult, etc.
    pipeline.py              # Support functions: task loading, guardrails, result collection
    loader.py                # Plugin discovery and loading
    tools/
      __init__.py
      protocol.py            # DebuggingTool Protocol, shared result types
      browser_mcp.py         # Browser MCP plugin (web apps)
      desktop_agent.py       # Desktop agent plugin (native apps)
  core/
    config.py                # Add DebuggingConfig, DebuggingToolConfig
  cli/
    debug.py                 # Typer subcommand group

tests/
  debugging/
    __init__.py
    test_models.py
    test_pipeline.py
    test_loader.py
    tools/
      __init__.py
      test_browser_mcp.py
      test_desktop_agent.py
```

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Plugin protocol stability | Zero breaking changes after Phase 2 | Protocol method count and signature tracking |
| Pipeline completion rate | >90% of runs complete all 6 phases | Pipeline result analysis |
| Fix cycle success rate | >50% of failures auto-fixed within 3 iterations | `FixAttempt` outcome tracking |
| Browser MCP reliability | >95% step execution success | `InteractionResult.success` rate |
| Desktop agent reliability | >80% step execution success (lower due to known accuracy issues) | `InteractionResult.success` rate |
| Config backward compatibility | 100% of existing configs load without error | CI tests with legacy config fixtures |
| Test coverage | >80% line coverage for `debugging/` package | `just coverage` |

---

## Immediate Next Steps

1. ~~**Review this discovery** with the project maintainer.~~ **DONE.** Key decisions validated:
   - **Sync protocol** (ADR-D02): Protocol is synchronous; async plugins manage their own event loop internally
   - **Managed config-based registration** (ADR-D01): CLI commands for add/remove/validate, YAML is source of truth
   - **LLM-as-outer-loop** (ADR-D03): Debugging agent is a standard AgentInvoker session; LLM drives the workflow
   - **Tool-level guardrails** (ADR-D04): Guardrails via tool responses and post-run validation, not code-controlled pipeline
2. ~~**Principal engineer review (Zod).**~~ **DONE.** All critical, important, and suggested issues resolved:
   - ADR-D03/D04 rewritten to resolve execution model contradiction (LLM-as-outer-loop with tool-level guardrails)
   - Four missing result types defined (`InteractiveTestResults`, `FixCycleResults`, `RegressionTestResults`, `UXReviewResults`)
   - `dict[str, object]` tool_config replaced with `DebuggingToolConfig.settings` + plugin-internal Pydantic validation
   - Missing `field` import added to protocol snippet
   - `DebuggingToolConfig` gets `populate_by_name=True`
   - Phase 3 split into 3a/3b (5+5pts), Phase 4 split into 4a/4b (5+3pts). Total: 36 points (was 31)
   - New ADRs: D05 (config mutation via load-modify-save), D06 (provisioning test strategy), D07 (protocol versioning)
   - `ToolCapability` StrEnum, tuple return types, `ToolNotProvisionedError` added per suggestions
3. **Create task file** for Phase 1 (models + protocol). Estimated 5 story points. This can begin immediately with no external dependencies.
4. **Validate Browser MCP availability.** Confirm that ruflo browser tools are accessible from agent subprocesses via Claude CLI's `.mcp.json` integration. This is a Phase 3a dependency but should be verified early.
5. **Decide on desktop agent priority.** Phase 5 (desktop plugin) is independent of Phases 3-4. If desktop testing is not an immediate need, it can be deferred without blocking the core debugging capability.
