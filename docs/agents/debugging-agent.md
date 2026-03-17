# Debugging Agent Usage Guide

## Overview

The debugging agent is an autonomous testing agent that validates acceptance criteria against live environments, diagnoses failures, fixes code, drafts regression tests, and performs UX review. It operates through a plugin architecture where tool backends (Browser MCP for web apps, Desktop Agent for native apps) implement a shared `DebuggingTool` protocol.

### 6-Phase Workflow

1. **Interactive Testing** -- Execute test steps against the target application
2. **Diagnosis** -- Capture diagnostic evidence (screenshots, console errors, network failures)
3. **Fix Attempt** -- Identify and apply code fixes with source scope enforcement
4. **Regression Testing** -- Generate and run regression tests for the fix
5. **UX Review** -- Evaluate UX quality against design criteria
6. **Escalation** -- Report results; escalate failures to the coordination board

### Plugin Architecture

Tool backends implement the `DebuggingTool` protocol (`src/autopilot/debugging/tools/protocol.py`). Each plugin advertises its capabilities via `ToolCapability` flags:

| Capability | Browser MCP | Desktop Agent |
|------------|:-----------:|:-------------:|
| `INTERACTIVE_TEST` | Yes | Yes |
| `CONSOLE_CAPTURE` | Yes | No |
| `NETWORK_CAPTURE` | Yes | No |
| `SCREENSHOT` | Yes | Yes |
| `UX_REVIEW` | Yes | Yes |

## Setup

### Enable debugging in configuration

Add the debugging section to your project's `autopilot.yml`:

```yaml
debugging:
  tool: browser_mcp  # or desktop_agent
  tools:
    browser_mcp:
      module: autopilot.debugging.tools.browser_mcp
      class_name: BrowserMCPTool
    desktop_agent:
      module: autopilot.debugging.tools.desktop_agent
      class_name: DesktopAgentTool
```

### Provision a tool

Before first use, provision the debugging tool:

```bash
# Browser MCP (lightweight -- registers MCP server in .mcp.json)
autopilot debug provision browser_mcp

# Desktop Agent (heavy -- downloads macOS VM, models, ~100GB)
autopilot debug provision desktop_agent
```

Check provisioning status:

```bash
autopilot debug status
```

## Usage

### Manual debugging runs

```bash
# Run a debugging task file
autopilot debug run tasks/debug-login.yml

# Run with a specific tool
autopilot debug run tasks/debug-login.yml --tool browser_mcp

# Dry-run validation (parse task, check tool, skip execution)
autopilot debug run tasks/debug-login.yml --dry-run

# Run with verbose output
autopilot debug run tasks/debug-login.yml --verbose
```

### Automated (hook-based) triggering

Enable post-deploy debugging triggers in your config:

```yaml
debugging:
  hooks:
    enabled: true
    tool: browser_mcp
    timeout_seconds: 900
```

When enabled, debugging runs trigger automatically after deploy-related dispatches (deploy, release, publish, ship actions). Disabled by default.

### Debugging timeout

The debugging agent timeout is configurable via the scheduler config:

```yaml
scheduler:
  agent_timeouts:
    debugging: 900  # 15 minutes (default)
```

Desktop agent tests take significantly longer (60-120s per step vs. 2-5s for browser), so increase the timeout when using the desktop agent.

## Task File Format

Debugging task files are YAML documents that specify what to test:

```yaml
# tasks/debug-login.yml
task_id: "login-001"
feature: "authentication"
title: "Verify login flow works end-to-end"
description: "Test that users can log in with valid credentials and see the dashboard"
staging_url: "https://staging.example.com"

steps:
  - action: navigate
    target: "https://staging.example.com/login"
  - action: fill
    target: "#email"
    value: "test@example.com"
  - action: fill
    target: "#password"
    value: "test-password"
  - action: click
    target: "#login-button"
  - action: assert_visible
    target: ".dashboard"
    expect: "Welcome"
    timeout_seconds: 10

acceptance_criteria:
  - "User can log in with valid credentials"
  - "Dashboard displays after successful login"

source_scope:
  - "src/auth/"
  - "src/pages/login/"

ux_review_enabled: true
ux_capture_states:
  - "login-form"
  - "dashboard-loaded"
```

### Action Reference

| Action | Description | Browser MCP | Desktop Agent |
|--------|-------------|:-----------:|:-------------:|
| `navigate` | Open URL or application | URL | App/URL |
| `click` | Click element | CSS selector | Coordinate-based (UI-TARS) |
| `fill` | Type text into field | CSS selector + value | Keyboard input |
| `wait` | Wait for duration | Duration (ms) | Duration (s) |
| `screenshot` | Capture screenshot | Via MCP | Via VM |
| `assert_visible` | Verify element/text visible | CSS selector + snapshot | Screenshot + validation model |
| `assert_text` | Verify text content | CSS selector + snapshot | N/A |
| `wait_for_navigation` | Wait for page load | Via MCP | N/A |

## Plugin Management

### List available tools

```bash
autopilot debug list-tools
```

### Add a custom tool

```bash
autopilot debug add-tool my_tool --module my_project.tools.custom --class MyCustomTool
```

### Remove a tool

```bash
autopilot debug remove-tool my_tool
```

### Validate a tool

```bash
autopilot debug validate-tool browser_mcp
```

### Provision / deprovision

```bash
# Provision (install dependencies, configure infrastructure)
autopilot debug provision browser_mcp

# Deprovision (remove infrastructure, clean up)
autopilot debug deprovision desktop_agent
```

## Troubleshooting

### Tool not provisioned

```
ToolNotProvisionedError: Tool 'browser_mcp' is not provisioned.
Run 'autopilot debug provision browser_mcp' first.
```

**Fix:** Run `autopilot debug provision <tool>` to set up the required infrastructure.

### MCP server unreachable

```
browsermcp server not registered in .mcp.json
```

**Fix:** Re-provision the browser MCP tool: `autopilot debug provision browser_mcp`. Verify `.mcp.json` exists in the project root with a `browsermcp` server entry.

### Desktop agent click failures

Click accuracy with UI-TARS is ~70-80%. The desktop agent automatically retries with +/-5px position jitter (up to 3 attempts by default).

**Tuning options:**
- Increase retries: `click_max_retries: 5` in settings
- Ensure VM snapshot has all permissions pre-authorized
- Run pre-flight dialog dismissal to clear popups

### VM state drift (Desktop Agent)

Slack auto-updates, notification banners, and "What's New" dialogs can derail tests.

**Fix:** The desktop agent restores from a known-good VM snapshot before each test run. If issues persist, recreate the snapshot: `autopilot debug provision desktop_agent`.

### Escalation: max fix attempts exceeded

```
escalation_reason: "Max fix iterations (3) reached without passing all tests"
```

**Fix:** Review the debugging result in the coordination board decision log. The agent could not fix the failing tests automatically. Manual investigation is needed.

## Architecture

### Protocol (`src/autopilot/debugging/tools/protocol.py`)

The `DebuggingTool` protocol (ADR-D01) defines the interface all plugins must satisfy:
- `@runtime_checkable` for dynamic isinstance checks
- `protocol_version` class attribute for compatibility (ADR-D07)
- Synchronous methods; async plugins wrap with `asyncio.run()` internally (ADR-D02)

### Pipeline (`src/autopilot/debugging/pipeline.py`)

Support functions for the LLM agent session (ADR-D03, ADR-D04):
- `load_debugging_task()` -- Parse YAML task files
- `validate_source_scope()` -- Enforce file modification boundaries
- `run_quality_gates()` -- Run `just all` for quality checks
- `collect_debugging_result()` -- Assemble results post-session

### Plugin loader (`src/autopilot/debugging/loader.py`)

Dynamic plugin loading with protocol validation (ADR-D01):
- `load_debugging_tool()` -- Import, instantiate, validate
- `validate_plugin_class()` -- Pre-instantiation protocol check

### Orchestration (`src/autopilot/orchestration/debugging_hooks.py`)

Post-deploy integration:
- `should_trigger_debugging()` -- Check if deploy action should trigger debugging
- `post_debugging_result_to_board()` -- Announcement (pass) or decision log (fail)
- `make_debugging_dispatch_outcome()` -- Include in cycle reports

### ADR References

| ADR | Summary |
|-----|---------|
| ADR-D01 | `typing.Protocol` with `@runtime_checkable`; config-based plugin registration |
| ADR-D02 | Synchronous protocol; async internals via `asyncio.run()` |
| ADR-D03 | LLM-orchestrated agent (standard `AgentInvoker` session) |
| ADR-D04 | Guardrails via tool responses + system prompt |
| ADR-D05 | Config mutation via load-modify-save |
| ADR-D06 | Two-tier tests (unit always, integration guarded by env var) |
| ADR-D07 | Protocol versioning via `PROTOCOL_VERSION` constant |
