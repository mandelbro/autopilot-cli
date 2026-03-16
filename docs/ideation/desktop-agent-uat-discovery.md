# Discovery: AI Desktop Agent for Slack Bot UAT Testing

**Date:** 2026-02-18
**Status:** Discovery Complete -- Ready for Task Planning
**Author:** Norwood (Discovery Agent)
**Source Research:** `docs/research/desktop-agent-uat-evaluation.md`
**Related:** `docs/testing/mvp-uat-test-plan.md`, `docs/testing/uat-flows-and-gap-analysis.md`

---

## Executive Summary

### The One-Liner

Add visual desktop testing to RepEngine's Slack bot UAT by using an LLM-orchestrated desktop agent that can screenshot, click, and type inside Slack Desktop -- validating Block Kit rendering, emoji, threading, and interactive workflows that API-only tests cannot see.

### The Problem

RepEngine's existing UAT infrastructure (`tests/uat/`) uses Slack Web API `curl` calls and `@claude-flow/browser` scripts to test Slack bot commands. These tools verify that the bot *responds* correctly at the API layer, but cannot verify:

1. **Block Kit visual rendering** -- do MEDDIC framework sections, risk badges, and confidence scores actually display correctly in Slack Desktop?
2. **Real user interaction patterns** -- mouse clicks, keyboard input, workspace navigation, thread expansion
3. **Cross-application workflows** -- Slack links opening in browser, Google Docs links working end-to-end
4. **Visual regression** -- emoji rendering, message threading UI, action button placement

The gap is not theoretical. API tests confirm `{"ok": true}` from Slack's servers, but a malformed Block Kit payload can render as a blank message, truncated text, or broken layout. Only a visual observer catches these failures.

### The Solution

A two-phase approach using LLM-orchestrated desktop agents:

- **Phase 1 (Prototype):** Install `computer-use-mcp` (MCP server + nut.js), enabling Claude Code to control the host macOS desktop directly. Zero infrastructure setup. Validates the concept within a single session.
- **Phase 2 (Production):** Deploy `Cua` framework with `Lume` macOS VMs. Sandboxed, reproducible, CI/CD-compatible. Runs 7 visual test scenarios inside an isolated macOS VM with Slack pre-installed.

### The Work

- **Phase 1 Effort:** 2-3 days (1 developer)
- **Phase 2 Effort:** 5-8 days (1 developer)
- **Ongoing Cost:** ~$2-15/week for Claude API usage during test runs
- **Infrastructure:** Lume VM (free/OSS), ~30GB disk per VM image

### The Risks

1. **Vision model accuracy** -- Claude's screenshot interpretation may misread Block Kit formatting (mitigated by using 1024x768 resolution and structured validation prompts)
2. **macOS Sequoia permissions** -- monthly screen recording re-authorization could break CI (mitigated by running in VM where permissions persist)
3. **Slack Desktop state drift** -- workspace login, notification popups, and update dialogs can derail agent navigation (mitigated by pre-flight VM snapshots and deterministic startup scripts)

---

## Research Quality Assessment

The source research document at `docs/research/desktop-agent-uat-evaluation.md` is solid but has specific gaps that this discovery addresses.

### Strengths

- **Comprehensive tool evaluation**: 15+ solutions evaluated across 3 tiers with clear verdict rationale. The elimination of OpenAI Operator (browser-only), Sikuli (abandoned), and traditional RPA (wrong paradigm) shows genuine investigation, not just Googling.
- **Practical prototype code**: The `slack_uat_runner.py` is production-quality Python with proper dataclasses, async patterns, and structured test results. It is not pseudocode.
- **Honest cost estimates**: The $0.10-0.30 per single command test and $0.70-2.10 per full suite are realistic for Claude Sonnet with 3 recent images and 1024x768 resolution.
- **Good decision log**: Captures the "why" behind each choice, not just the "what."

### Gaps and Corrections

| Area | Issue | Correction/Addition |
|------|-------|-------------------|
| **Command naming** | Tests reference `/repengine analyze`, `/repengine framework`, `/repengine draft`, `/repengine status` | These are actually correct as `/repengine` subcommands (e.g., `/repengine analyze <deal>`). The research's command format was close but missed the space-separated subcommand pattern. Separately, the agent-service commands (`/repengine-help`, `/email-draft`, `/framework`) are NOT in the Slack manifest and are unreachable. The `/rep-*` shortcuts in the manifest are broken (registered but unhandled). See "Slack Bot Commands" section for full analysis. |
| **Cua SDK API** | Uses `from computer import Computer` and `from agent import ComputerAgent` | The Cua Python SDK package names need verification. The import paths may be `from cua_computer import Computer` and `from cua_agent import ComputerAgent` per pip package names `cua-agent[anthropic]` and `cua-computer[lume]`. |
| **CI/CD feasibility** | Open question about Lume on GitHub Actions macOS runners | GitHub Actions macOS runners (M1) do support nested virtualization but with limitations. Lume requires Apple Silicon + macOS Ventura+. The `macos-14` and `macos-15` GitHub runners run on M1 and M4 Pro chips respectively and *should* support Lume, but this is unverified. Self-hosted runners are the safe fallback. |
| **Slack bot token in VM** | Flagged as open question | Solution: use `lume exec` to inject environment variables into the VM. Slack Desktop workspace login can be automated via deep links (`slack://open?team=T12345`) or by pre-authenticating in a VM snapshot. |
| **Missing integration with existing UAT** | Research mentions integrating with `tests/uat/run-tests.sh` but provides no concrete plan | This discovery provides the full integration plan below, including `just` targets, pytest markers, and report directory structure. |
| **Phase 1 human supervision** | States "human supervision during all sessions" but gives no guardrails | Phase 1 needs explicit safety controls: restricted screen area, application whitelist, abort-on-unexpected-dialog logic. |
| **Cost optimization gap** | Mentions local Ollama for OMNI loop but does not elaborate | For development iterations, running Llama 3.2 Vision via Ollama locally is free and sufficient for basic navigation. Reserve Claude Sonnet for validation runs. |

### Overall Verdict

The research is **8/10** -- strong evaluation, good prototype code, honest about limitations. The gaps are addressable and mostly relate to integration details rather than strategic misjudgments. The two-phase recommendation is sound.

---

## Current State Analysis

### Existing UAT Infrastructure

The project has a mature UAT testing framework at `tests/uat/`:

```
tests/uat/
  RUNBOOK.md                     # AI agent execution guide
  run-tests.sh                   # Master test runner (8 suites)
  run-single-suite.sh            # Per-suite runner
  demo-email-testing.sh          # Interactive demo
  utils/
    slack-automation.sh           # Slack CLI wrappers (DM send/read/thread)
    test-data-generator.js        # Fixture generation (users, deals, contacts)
    assertions.js                 # Custom assertion helpers
  suites/
    01-onboarding/                # Magic link auth tests
    07-slack-integration/         # Slack command recognition tests
    08-email-integration/         # Gmail MCP integration
  fixtures/                      # Test data (users, deals, files)
  config/                        # Test configuration
```

**Key observations:**

1. **Slack testing is API-only**: `tests/uat/utils/slack-automation.sh` uses `slack-cli dm send` and `slack-cli dm read` -- it validates response *text content* but cannot see how it *renders*.
2. **Browser testing uses `@claude-flow/browser`**: The UAT plan references `createBrowserService()` for web UI testing (magic links, OAuth flows, file uploads) but this has no capability for native desktop apps like Slack Desktop.
3. **Report infrastructure exists**: Screenshots go to `tests/uat/reports/screenshots/`, JSON results to `tests/uat/reports/`. The desktop agent can integrate with this.
4. **`just` targets exist for testing**: `just test-all`, `just repengine-agent-test`, `just api-service-test` -- but no desktop UAT targets yet.

### Slack Bot Commands (Actual Implementation)

There are **two independent command routing paths** that are partially out of sync with the Slack manifest:

#### Path 1: Slack Manifest → API Service (`stg-api.repengine.co/integrations/slack/slash-command`)

The Slack app manifest (`infrastructure/slack-manifest.json`) registers these 5 commands, all routing to the api-service:

| Manifest Command | Description | API Service Handling |
|-----------------|-------------|---------------------|
| `/repengine [subcommand]` | General assistant | **WORKING** — SlashCommandRouter converts to `!subcommand` format |
| `/rep-analyze <deal>` | Analyze a deal | **BROKEN** — not in SlashCommandRouter.COMMAND_MAPPING, falls to unknown |
| `/rep-help [command]` | Get help | **BROKEN** — not in COMMAND_MAPPING, falls to unknown |
| `/rep-report [period]` | Generate reports | **BROKEN** — not in COMMAND_MAPPING, falls to unknown |
| `/rep-status [deal-id]` | Pipeline status | **BROKEN** — not in COMMAND_MAPPING, falls to unknown |

The api-service's `SlashCommandRouter` (`render/api-service/src/api_service/messaging/slack/slash_command_router.py`) only maps `/repengine`, `/handoff`, and `/prep`. The `/rep-*` shortcut commands are registered in Slack but not handled — they fall through to the unknown-command path, resulting in errors like: _"Bauch is not a recognized command. Type `/repengine help` to see all available commands"_

**Working `/repengine` subcommands** (via CommandProcessor `!command` patterns):

| Subcommand | Example | Routes To |
|-----------|---------|-----------|
| `analyze <deal>` | `/repengine analyze BigCorp` | repengine-agent |
| `framework <deal>` | `/repengine framework BigCorp` | Local handler |
| `help` | `/repengine help` | Local handler |
| `status <deal>` | `/repengine status BigCorp` | repengine-agent |
| `report [period]` | `/repengine report weekly` | Local handler |
| `draft <text>` | `/repengine draft follow-up for BigCorp` | repengine-agent |
| `handoff <deal>` | `/repengine handoff BigCorp to Jane` | repengine-agent |
| `settings` | `/repengine settings` | Local handler |
| `summary [text]` | `/repengine summary` | repengine-agent |
| `prep-doc <deal>` | `/repengine prep-doc BigCorp` | repengine-agent |

#### Path 2: Agent Service (`render/repengine-agent/api/slack_commands.py`)

The agent service handles these commands at `/slack/commands`, but **none are registered in the Slack manifest**:

| Command | Purpose | Status |
|---------|---------|--------|
| `/repengine-login <email>` | Magic link authentication | **UNREACHABLE** — not in manifest |
| `/email-draft <deal>` | Draft emails | **UNREACHABLE** — not in manifest |
| `/framework <deal>` | MEDDIC/BANT analysis | **UNREACHABLE** — not in manifest |
| `/repengine-help` | Display help | **UNREACHABLE** — not in manifest |

**Evidence from Slack:** `/framework` produces _"/framework is not a valid command"_ because Slack doesn't know about it.

#### Summary: What Actually Works Today

| Method | Example | Status |
|--------|---------|--------|
| `/repengine help` | Shows available commands | Working |
| `/repengine analyze BigCorp` | Analyzes a deal | Working |
| `/repengine framework BigCorp` | MEDDIC framework | Working |
| `/repengine status BigCorp` | Pipeline status | Working |
| `/repengine report weekly` | Sales reports | Working |
| `/repengine draft follow-up for BigCorp` | Draft messages | Working |
| Free-text DM to bot | "Analyze BigCorp" | Working |
| Thread replies | Context-aware follow-ups | Working |
| `/rep-status BigCorp` | Shortcut | **Broken** (manifest registered, not handled) |
| `/framework BigCorp` | Direct command | **Broken** (not in manifest) |

> **Note:** This command discrepancy is a pre-existing issue, not related to this discovery. However, the desktop agent UAT test scenarios MUST use the working command paths. A separate task should be filed to reconcile the manifest with the command handlers.

### What Cannot Be Tested Today

| Scenario | Current Coverage | Gap |
|----------|-----------------|-----|
| Block Kit section rendering | API validates JSON payload structure | Cannot verify visual layout in Slack Desktop |
| Emoji rendering in responses | API confirms emoji unicode in text | Cannot verify Slack renders them correctly |
| Thread expansion/collapse | API reads thread via `conversations.replies` | Cannot verify thread UI behavior |
| Action button placement | API confirms `actions` block exists | Cannot verify button position, size, clickability |
| Multi-message response flow | API reads latest message only | Cannot verify sequential message display |
| Error state visual treatment | API reads error text | Cannot verify visual prominence, color, icon |

---

## Target Architecture

### Phase 1: MCP Prototype (Host OS)

```
+------------------+     +--------------------+     +-------------------+
| Claude Code      |     | computer-use-mcp   |     | Host macOS        |
| (Orchestrator)   |---->| (MCP Server)       |---->| Desktop           |
|                  |     |                    |     |                   |
| - Test prompts   |     | - nut.js bindings  |     | - Slack Desktop   |
| - Result parsing |     | - screenshot()     |     | - System UI       |
| - Pass/fail      |     | - click(x, y)      |     |                   |
+------------------+     | - type(text)       |     +-------------------+
                         | - press_key(key)   |
                         +--------------------+
```

**Characteristics:**
- Runs on developer's machine directly
- No VM, no container, no additional infra
- Human supervised (developer watches the screen)
- Good for: concept validation, ad-hoc visual checks, iterating on test prompts
- Bad for: CI/CD, reproducibility, parallel execution

### Phase 2: Cua + Lume Production (macOS VM)

```
+-------------------+     +-------------------+     +-------------------+
| pytest Runner     |     | Cua ComputerAgent |     | Lume macOS VM     |
| (tests/uat/       |---->| (Claude Sonnet)   |---->| (Sequoia)         |
|  desktop-agent/)  |     |                   |     |                   |
| - Test scenarios  |     | - Observe screen  |     | - Slack Desktop   |
| - Assertions      |     | - Decide action   |     | - 1024x768        |
| - JSON reports    |     | - Execute action   |     | - 8GB RAM, 4 CPU |
+-------------------+     | - Report findings |     +-------------------+
         ^                +-------------------+             |
         |                        |                         |
         |                        v                         v
         |                +-------------------+     +-------------------+
         +----------------|  Test Reports     |     | VM Snapshots      |
                          | - Screenshots     |     | - Clean state     |
                          | - Action logs     |     | - Pre-auth Slack  |
                          | - Pass/fail JSON  |     | - Permissions set |
                          +-------------------+     +-------------------+
```

**Characteristics:**
- Sandboxed macOS VM (no risk to host)
- Reproducible via VM snapshots
- Can run in CI on macOS Apple Silicon runners
- Supports parallel VMs for concurrent test suites
- Python-native integration with pytest

---

## Implementation Plan

### Phase 1: Prototype with computer-use-mcp

**Goal:** Validate that an LLM can reliably navigate Slack Desktop, send commands, and interpret bot responses. Determine accuracy, latency, and failure modes before investing in VM infrastructure.

**Duration:** 2-3 days

#### Task P1-001: Install and Configure computer-use-mcp

**Effort:** 2 hours

**Steps:**
1. Install MCP server: `claude mcp add --scope user --transport stdio computer-use -- npx -y computer-use-mcp`
2. Grant macOS permissions:
   - System Settings > Privacy & Security > Accessibility > Enable terminal app
   - System Settings > Privacy & Security > Screen Recording > Enable terminal app
3. Restart terminal application
4. Verify with basic test: "Take a screenshot and describe what you see"

**Acceptance Criteria:**
- [ ] MCP server responds to `screenshot`, `left_click`, `type`, `press_key` tools
- [ ] Screenshot returns a legible image of the desktop
- [ ] Click coordinates map correctly to on-screen elements

#### Task P1-002: Establish Safety Protocol for Host OS Testing

**Effort:** 1 hour

**Steps:**
1. Create a dedicated macOS user account `repengine-uat` (or use current account with restrictions)
2. Close all applications except Slack Desktop and the terminal
3. Set display resolution to 1440x900 or 1024x768
4. Disable macOS notifications (Do Not Disturb)
5. Position Slack window at a known location (full-screen or top-left anchored)
6. Document the exact window layout as a "starting position" reference

**Acceptance Criteria:**
- [ ] Desktop has no overlapping windows or notification badges
- [ ] Slack is open to the RepEngine bot DM channel
- [ ] Display resolution documented and fixed

#### Task P1-003: Execute Smoke Test (Single Command Validation)

**Effort:** 2 hours

**Steps:**
1. Using Claude Code with the MCP server active, prompt:
   ```
   Take a screenshot. Find the Slack application. Click on the DM conversation with RepEngine.
   Type "/repengine help" and press Enter.
   Wait 5 seconds and take another screenshot.
   Describe what the bot responded with. Does it list available commands?
   ```
2. Record: before/after screenshots, LLM interpretation, token usage, wall-clock time
3. Repeat 3 times to assess consistency

**Acceptance Criteria:**
- [ ] Agent successfully navigates to Slack DM
- [ ] Agent types the command and presses Enter
- [ ] Agent correctly identifies bot response content
- [ ] 3/3 runs produce consistent navigation behavior
- [ ] Latency < 2 minutes per complete test cycle

#### Task P1-004: Execute Full Test Suite (7 Scenarios)

**Effort:** 4 hours

**Steps:**
1. Adapt the 7 test scenarios from the research document to use **working commands** (see "What Actually Works Today"):
   - SLACK-001: `/repengine help` -- verify command list rendering (via `/repengine` subcommand)
   - SLACK-002: `/repengine analyze BigCorp Software License` -- verify analysis Block Kit
   - SLACK-003: `/repengine framework BigCorp Software License` -- verify MEDDIC sections
   - SLACK-004: `/repengine draft follow-up for BigCorp Software License` -- verify draft formatting
   - SLACK-005: Free-text "gibberish random text" -- verify error message display
   - SLACK-006: Thread context -- send message, reply in thread, verify context
   - SLACK-007: Response timing -- `/repengine help`, measure initial acknowledgment latency
2. Run each test manually via Claude Code MCP prompts
3. Capture structured results: test_id, passed, details, screenshots, duration, tokens

**Acceptance Criteria:**
- [ ] All 7 tests executed and results documented
- [ ] Pass rate >= 5/7 (accounting for expected vision model imprecision)
- [ ] Total suite duration < 15 minutes
- [ ] Total API cost < $5 for full run
- [ ] Failure modes documented with root cause analysis

#### Task P1-005: Document Phase 1 Findings

**Effort:** 2 hours

**Steps:**
1. Create `docs/testing/desktop-agent-phase1-results.md` with:
   - Test results table (7 scenarios, pass/fail, screenshots)
   - Accuracy analysis: what did the LLM get right/wrong?
   - Performance metrics: latency per test, token usage, cost
   - Failure mode catalog: what went wrong and why
   - Go/no-go recommendation for Phase 2
2. Update `docs/testing/README.md` to reference desktop agent testing

**Acceptance Criteria:**
- [ ] Results document created with all 7 test outcomes
- [ ] Clear go/no-go recommendation for Phase 2
- [ ] Cost projection for ongoing desktop agent testing

---

### Phase 2: Production with Cua + Lume

**Goal:** Build a reproducible, sandboxed desktop UAT system that runs inside a macOS VM, integrates with pytest, and can eventually run in CI/CD.

**Duration:** 5-8 days

**Prerequisites:** Phase 1 must validate the concept (go decision)

#### Task P2-001: Install Lume and Provision macOS VM

**Effort:** 3 hours (includes ~80GB download)

**Steps:**
1. Install Lume:
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/trycua/cua/main/libs/lume/scripts/install.sh)"
   ```
2. Pull macOS Sequoia image:
   ```bash
   lume pull macos-sequoia-vanilla:latest
   ```
3. Create UAT VM with dedicated resources:
   ```bash
   lume run macos-sequoia-vanilla:latest --name repengine-uat --memory 8GB --cpu 4
   ```
4. Inside VM: configure for testing
   - Set display resolution to 1024x768
   - Disable screen saver, sleep, auto-update
   - Grant Accessibility and Screen Recording permissions to terminal
   - Install Homebrew, then `brew install --cask slack`
5. Sign into Slack staging workspace inside VM
6. Navigate to RepEngine bot DM channel
7. Create VM snapshot: `lume snapshot create repengine-uat clean-slate`

**Acceptance Criteria:**
- [ ] Lume installed and VM boots successfully
- [ ] Slack Desktop installed and authenticated in staging workspace
- [ ] VM snapshot created at clean starting state
- [ ] VM resolution is 1024x768

#### Task P2-002: Install Cua Python SDK and Verify Agent Loop

**Effort:** 2 hours

**Steps:**
1. In the host Python environment (project root or dedicated venv):
   ```bash
   uv pip install "cua-agent[anthropic]" "cua-computer[lume]"
   ```
2. Verify imports work:
   ```python
   from computer import Computer
   from agent import ComputerAgent
   ```
   (Adjust import paths if package structure differs from research document)
3. Write minimal verification script:
   ```python
   async with Computer(os_type="macos", provider_type="lume", display="1024x768") as computer:
       screenshot = await computer.screenshot()
       assert screenshot is not None
   ```
4. Verify Claude API key is available: `ANTHROPIC_API_KEY`

**Acceptance Criteria:**
- [ ] Cua SDK installed without dependency conflicts
- [ ] Agent can connect to Lume VM and take screenshots
- [ ] Correct import paths documented

#### Task P2-003: Create Desktop UAT Test Framework

**Effort:** 4 hours

**File:** `tests/uat/desktop-agent/conftest.py`

**Steps:**
1. Create `tests/uat/desktop-agent/` directory structure:
   ```
   tests/uat/desktop-agent/
     conftest.py           # pytest fixtures for Cua VM lifecycle
     test_slack_visual.py  # Visual Slack bot test scenarios
     helpers/
       __init__.py
       vm_manager.py       # VM snapshot restore, startup, teardown
       report_writer.py    # JSON/screenshot report generation
   ```
2. Implement conftest.py with:
   - `@pytest.fixture(scope="session")` for Lume VM lifecycle (start, restore snapshot, teardown)
   - `@pytest.fixture(scope="function")` for ComputerAgent per test
   - `@pytest.fixture` for report directory setup
   - pytest marker: `@pytest.mark.desktop_agent`
3. Implement `vm_manager.py`:
   - `restore_snapshot(vm_name, snapshot_name)` -- reset to clean Slack state
   - `start_vm(vm_name)` -- boot VM if not running
   - `stop_vm(vm_name)` -- graceful shutdown
4. Implement `report_writer.py`:
   - `save_screenshot(data, test_id, step_name)` -> saves to `tests/uat/reports/desktop-agent/screenshots/`
   - `save_test_result(result: TestResult)` -> appends to JSON report

**Acceptance Criteria:**
- [ ] pytest discovers tests with `--desktop-agent` marker
- [ ] VM lifecycle managed by session-scoped fixture
- [ ] Each test gets a fresh ComputerAgent instance
- [ ] Screenshots saved to report directory

#### Task P2-004: Implement Visual Test Scenarios

**Effort:** 6 hours

**File:** `tests/uat/desktop-agent/test_slack_visual.py`

**Steps:**
1. Implement 7 test functions, each as an independent pytest test:

   ```python
   @pytest.mark.desktop_agent
   @pytest.mark.asyncio
   async def test_help_command_display(agent, report):
       """SLACK-VIS-001: Verify /repengine help renders command list."""
       ...

   @pytest.mark.desktop_agent
   @pytest.mark.asyncio
   async def test_deal_analysis_block_kit(agent, report):
       """SLACK-VIS-002: Verify deal analysis Block Kit formatting."""
       ...
   ```

2. Each test follows the pattern:
   - Pre-flight: verify Slack is on the correct DM channel
   - Action: type command, press Enter
   - Wait: configurable delay (5-10s for bot response)
   - Observe: take screenshot, send to LLM for analysis
   - Validate: parse LLM response for pass/fail criteria
   - Report: save screenshot and structured result

3. Validation prompt engineering:
   ```
   You are a QA tester. The screenshot shows a Slack Desktop window.
   Look for the bot response to the command "{command}".
   Evaluate against these criteria:
   1. {criterion_1}
   2. {criterion_2}
   Report: PASS or FAIL with specific observations.
   ```

**Acceptance Criteria:**
- [ ] 7 visual test scenarios implemented
- [ ] Each test produces structured TestResult with pass/fail
- [ ] Screenshots captured before and after each action
- [ ] Tests are independent (can run in any order)

#### Task P2-005: Add just Targets and pytest Configuration

**Effort:** 2 hours

**Steps:**
1. Add pytest marker to `render/repengine-agent/pyproject.toml` (or root config):
   ```ini
   [tool.pytest.ini_options]
   markers = [
       "desktop_agent: visual desktop UAT tests (requires Lume VM)"
   ]
   ```
2. Add `just` targets to root justfile:
   ```just
   # Desktop Agent UAT (requires Lume VM + Cua SDK)
   desktop-uat:
     uv run pytest tests/uat/desktop-agent/ -m desktop_agent -v --tb=short

   desktop-uat-setup:
     lume snapshot restore repengine-uat clean-slate

   desktop-uat-report:
     cat tests/uat/reports/desktop-agent/latest.json | python -m json.tool
   ```
3. Exclude `desktop_agent` marker from default `just test-all` runs (since it requires VM):
   ```
   -m "not desktop_agent and not integration"
   ```

**Acceptance Criteria:**
- [ ] `just desktop-uat` runs the visual test suite
- [ ] `just desktop-uat-setup` restores VM to clean snapshot
- [ ] Desktop agent tests excluded from `just test-all`

#### Task P2-006: Integration with Existing UAT Report Pipeline

**Effort:** 2 hours

**Steps:**
1. Desktop agent test reports written to `tests/uat/reports/desktop-agent/`:
   ```
   tests/uat/reports/desktop-agent/
     slack-uat-YYYYMMDD-HHMMSS.json    # Structured results
     screenshots/
       SLACK-VIS-001-before-20260218-143022.png
       SLACK-VIS-001-after-20260218-143035.png
       ...
   ```
2. Report JSON schema matches existing UAT report format for consistency:
   ```json
   {
     "session": {"total": 7, "passed": 6, "failed": 1, "pass_rate": "85.7%"},
     "tests": [
       {"id": "SLACK-VIS-001", "name": "...", "passed": true, "duration_seconds": 45.2, "details": "..."}
     ]
   }
   ```
3. Update `tests/uat/run-tests.sh` to optionally include desktop-agent suite:
   ```bash
   if [[ "${INCLUDE_DESKTOP:-false}" == "true" ]]; then
     suites+=("desktop-agent")
   fi
   ```

**Acceptance Criteria:**
- [ ] Desktop agent reports in standard UAT report format
- [ ] Screenshots organized by test ID and timestamp
- [ ] Optionally included in master test runner

#### Task P2-007: CI/CD Integration Plan (Documentation Only)

**Effort:** 2 hours

This task produces documentation, not CI implementation. CI integration requires verified Lume support on GitHub Actions macOS runners, which is an open question.

**Steps:**
1. Document CI integration options in `docs/testing/desktop-agent-ci-integration.md`:
   - Option A: GitHub Actions `macos-14` runner with Lume (needs verification)
   - Option B: Self-hosted macOS runner with Lume pre-installed
   - Option C: Scheduled nightly run on developer machine via cron
2. Document VM image caching strategy (GitHub Actions cache or artifact storage)
3. Document secret management for `ANTHROPIC_API_KEY` and Slack workspace credentials
4. Provide a GitHub Actions workflow template (untested, for future implementation)

**Acceptance Criteria:**
- [ ] CI integration options documented with pros/cons
- [ ] VM caching strategy defined
- [ ] Secrets management approach documented
- [ ] Workflow template ready for future implementation

---

## Risk Analysis

### High Risk: Vision Model Interpretation Accuracy

**Probability:** Medium (Claude Sonnet is good at UI understanding but not perfect)
**Impact:** High (false passes/failures undermine test trustworthiness)
**Mitigation:**
- Use structured validation prompts with explicit criteria
- Set resolution to 1024x768 (optimal for vision models)
- Use `only_n_most_recent_images=3` to focus attention
- For critical assertions, combine visual verification with API cross-check (e.g., desktop agent sees "4 commands listed" AND API test confirms 4 commands in payload)
**Detection:** Track false positive/negative rates across runs. If accuracy drops below 85%, escalate to prompt engineering review.

### High Risk: macOS Permissions and OS-Level Interruptions

**Probability:** High (macOS Sequoia aggressively prompts for permissions)
**Impact:** Medium (test run fails, but no data loss)
**Mitigation:**
- Phase 1: human supervised, permissions pre-granted
- Phase 2: VM snapshot includes all permissions pre-authorized
- Implement "unexpected dialog detector" -- if agent sees a system dialog it does not expect, abort gracefully and report
**Detection:** Pre-flight check at start of each test run confirms permissions are active.

### Medium Risk: Slack Desktop State Drift

**Probability:** Medium (Slack updates, notification banners, "What's New" dialogs)
**Impact:** Medium (agent navigates to wrong area or gets stuck)
**Mitigation:**
- VM snapshot approach ensures clean starting state
- Pre-flight navigation sequence: close any open dialogs, verify correct channel
- Pin Slack version in VM (disable auto-update)
**Detection:** Pre-flight screenshot comparison against known-good reference image.

### Medium Risk: API Cost Escalation

**Probability:** Low (costs are well-bounded per the research)
**Impact:** Low (API costs are predictable, no surprise billing)
**Mitigation:**
- Use Claude Sonnet (not Opus) for agent loop -- 3x cheaper
- Limit to 3 recent screenshots per context window
- For development iterations, use local Ollama model (free)
- Set daily/weekly cost alerts on Anthropic dashboard
**Detection:** Token usage tracked per test run and included in reports.

### Low Risk: Cua/Lume Maturity

**Probability:** Low (Cua is actively maintained by trycua, Lume uses Apple's Virtualization.framework)
**Impact:** Medium (if Cua breaks, Phase 2 is blocked)
**Mitigation:**
- Phase 1 validates the concept without Cua dependency
- Cua is open source; we can fork if abandoned
- Fallback: use `computer-use-mcp` inside a VM (less elegant but functional)
**Detection:** Pin Cua SDK version in `pyproject.toml` and test against pinned version.

### Low Risk: CI/CD macOS Runner Compatibility

**Probability:** Medium (GitHub Actions macOS-14 is M1, virtualization support uncertain)
**Impact:** Low (self-hosted runner is viable alternative)
**Mitigation:**
- Phase 2 CI integration is documentation-only; actual CI deferred until runner compatibility verified
- Self-hosted M1 Mac Mini is ~$500 one-time cost if needed
**Detection:** Phase 2 Task P2-007 includes verification steps.

---

## Existing Components & Reuse Plan

### Services/Modules to Reuse

| Component | Location | Reuse Purpose |
|-----------|----------|---------------|
| UAT test fixtures | `tests/uat/fixtures/` | Deal data (DEAL-001 through DEAL-020), user data, contact data for test scenarios |
| Slack automation utilities | `tests/uat/utils/slack-automation.sh` | Reference implementation for send/read/thread patterns; desktop agent tests can cross-validate against API results |
| UAT report directory structure | `tests/uat/reports/` | Desktop agent reports follow same structure |
| Test configuration | `tests/uat/config/test-config.json` | Slack workspace, channel, bot name, timeouts |
| `just` task infrastructure | Root `justfile` | Add `desktop-uat` targets alongside existing test targets |
| pytest marker patterns | `render/api-service/pyproject.toml` | Follow `integration` marker pattern for `desktop_agent` marker |
| repengine-agent slash commands | `render/repengine-agent/src/repengine_agent/api/slack_commands.py` | Source of truth for what commands to test |

### Libraries Already Used Here

| Library | Version | Relevance |
|---------|---------|-----------|
| pytest | Current | Test runner for Phase 2 tests |
| pytest-asyncio | Current | Async test support for Cua agent loop |
| Anthropic Python SDK | Current | Claude API calls for agent loop |
| uv | Current | Package management for Cua SDK installation |
| just | Current | Task runner for new desktop UAT targets |

### What We Will Reuse

- **Test fixture data**: Existing deal fixtures provide realistic command targets ("BigCorp Software License" from `DEAL-001.json`)
- **Report directory convention**: `tests/uat/reports/desktop-agent/` follows existing `tests/uat/reports/` pattern
- **Slack configuration**: Bot name, channel IDs, workspace from `test-config.json`
- **`just` target patterns**: New targets follow `api-service-test` naming convention
- **pytest marker pattern**: `@pytest.mark.desktop_agent` follows `@pytest.mark.integration` pattern

### What We Will Not Reuse (Why)

- **`@claude-flow/browser`**: This is for web browser automation, not desktop app control. Cannot interact with Slack Desktop.
- **`slack-automation.sh` (execution layer)**: The shell script uses `slack-cli` for API-based send/read. Desktop agent tests use visual interaction instead. However, the test *scenarios* defined in the shell script are reused conceptually.
- **Jest/Node.js test runner**: Existing UAT suites (`tests/uat/suites/`) run on Jest. Desktop agent tests use pytest for consistency with the Python-based Cua SDK and the rest of the backend test suite.

### Consolidation Opportunities (Rule of Three)

- **Slack test scenarios**: There are now 3 implementations of "send command, verify response" logic: (1) `slack-automation.sh` shell tests, (2) `suites/07-slack-integration/command-recognition.test.js` Jest tests, (3) upcoming desktop agent pytest tests. After Phase 2, consolidate the *scenario definitions* (commands, expected responses, validation criteria) into a shared `tests/uat/scenarios/slack-commands.json` data file consumed by all three runners. This prevents scenario drift.
- **Test result reporting**: All three test approaches produce different report formats. After Phase 2, define a common `TestResult` schema used by shell, Jest, and pytest runners. This enables a single unified report generator.

---

## Cost Estimate

### Phase 1 (Prototype)

| Item | Cost | Notes |
|------|------|-------|
| Developer time | 2-3 days | 1 senior engineer |
| Claude API (development) | ~$5-10 | Multiple iterations of prompt tuning |
| Claude API (final validation run) | ~$2-3 | Single full 7-test suite |
| Infrastructure | $0 | Runs on developer's existing machine |
| **Total Phase 1** | **~$10-15 + 2-3 dev-days** | |

### Phase 2 (Production)

| Item | Cost | Notes |
|------|------|-------|
| Developer time | 5-8 days | 1 senior engineer |
| Claude API (development) | ~$15-25 | Multiple test iterations |
| Lume + VM image | $0 | Open source, one-time 80GB download |
| Disk space | 30GB sparse | Per VM image |
| Claude API (ongoing per week) | $2-15 | Depending on run frequency |
| CI runner (if self-hosted) | ~$500 one-time | Mac Mini M1 (optional) |
| **Total Phase 2** | **~$20-30 + 5-8 dev-days** | |

### Ongoing Operating Cost

| Scenario | Weekly Cost | Monthly Cost |
|----------|-------------|--------------|
| Daily regression (7 tests) | ~$14-15 | ~$60 |
| 3x/week regression | ~$6-9 | ~$25-40 |
| On-demand only | ~$2-4 | ~$8-16 |
| Development iterations (Ollama) | $0 | $0 |

---

## Success Metrics

### Phase 1 (Prototype)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Navigation accuracy | >= 90% | Agent reaches correct Slack DM in 9/10 attempts |
| Command execution accuracy | >= 85% | Agent types command correctly and presses Enter |
| Response interpretation accuracy | >= 80% | Agent correctly identifies pass/fail from screenshot |
| Single test latency | < 2 minutes | Wall-clock time from prompt to verdict |
| Full suite cost | < $5 | Total API cost for 7-test run |

### Phase 2 (Production)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Test suite pass rate (stable bot) | >= 85% | 6/7 tests pass when bot is working correctly |
| False positive rate | < 10% | Tests that pass when they should fail |
| False negative rate | < 15% | Tests that fail when they should pass |
| Full suite duration | < 15 minutes | From VM restore to report generation |
| VM boot-to-ready time | < 60 seconds | From snapshot restore to Slack DM visible |
| Report generation | 100% | Every run produces a structured JSON report |

---

## Open Questions Requiring Resolution

1. **Cua SDK import paths**: The research uses `from computer import Computer` and `from agent import ComputerAgent`. Need to verify against actual pip packages `cua-agent[anthropic]` and `cua-computer[lume]`. Resolution: verify during Task P2-002.

2. **Lume on GitHub Actions macOS-14**: Does `macos-14` (M1) support Lume's `Virtualization.framework` usage? Resolution: test during Task P2-007 or file a GitHub issue on the Lume repo.

3. **Slack Desktop version pinning in VM**: Can we prevent auto-updates inside the Lume VM? Resolution: disable `com.tinyspeck.slackmacgap.auto-update` plist key during VM setup in Task P2-001.

4. **Concurrent VM execution**: Can multiple Lume VMs run simultaneously for parallel test suites? Resolution: test during Phase 2 optimization (post-MVP).

5. **Hybrid validation strategy**: For each desktop agent test, should we also run the corresponding API test to cross-validate? Resolution: yes, implement in Phase 2 Task P2-004 as optional API cross-check fixtures.

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-18 | Two-phase approach (MCP prototype then Cua production) | Balance speed-to-validate with production safety |
| 2026-02-18 | Use `/repengine <subcommand>` format in test scenarios | Research format was close. Working commands use `/repengine analyze`, `/repengine framework`, etc. (space-separated subcommands via api-service CommandProcessor). Agent-service direct commands (`/framework`, `/email-draft`) are unreachable — not in Slack manifest. |
| 2026-02-18 | pytest for Phase 2 (not Jest) | Cua SDK is Python; aligns with backend test infrastructure |
| 2026-02-18 | Exclude desktop agent from `just test-all` | VM dependency makes it unsuitable for default test runs |
| 2026-02-18 | Defer CI/CD integration to documentation-only | Runner compatibility unverified; premature to implement |
| 2026-02-18 | Claude Sonnet for agent loop (not Opus) | 3x cheaper, sufficient for UI navigation tasks |
| 2026-02-18 | 1024x768 VM resolution | Optimal for vision model accuracy and token efficiency |
| 2026-02-18 | Consolidate scenario definitions after Phase 2 | Rule of Three: shell, Jest, and pytest all define similar scenarios |

---

## Next Steps

1. **Phase 1 kickoff**: Execute Tasks P1-001 through P1-005 (2-3 days)
2. **Go/no-go decision**: Based on Phase 1 results, decide whether to proceed with Phase 2
3. **Phase 2 execution**: If go, execute Tasks P2-001 through P2-007 (5-8 days)
4. **Task creation**: Convert the above implementation plan into the project's task workflow system (`tasks/desktop-agent-uat/`)

---

## Phase 2 Implementation Learnings (2026-02-19 through 2026-02-21)

**Status:** Prototype complete, end-to-end visual tests not yet passing. Restarting with fresh research and technical discovery.

### What Was Built

The Phase 2 framework was implemented with significant deviations from the original plan. Key deliverables:

| Component | File | Lines | Status |
|-----------|------|-------|--------|
| OpenCUA-7B server | `tests/uat/desktop-agent/opencua_server.py` | 327 | Working |
| Custom agent loop | `tests/uat/desktop-agent/helpers/opencua_loop.py` | 590 | Working but needs split |
| Test fixtures | `tests/uat/desktop-agent/conftest.py` | 187 | Working |
| Visual test suite | `tests/uat/desktop-agent/test_slack_visual.py` | 370 | 7 tests defined, not passing e2e |
| Visual validation | `tests/uat/desktop-agent/helpers/visual_validation.py` | 409 | Working |
| Ollama validator | `tests/uat/desktop-agent/helpers/ollama_validator.py` | 98 | Working |
| VNC screenshot helper | `tests/uat/desktop-agent/helpers/vnc_screenshot.py` | ~200 | Working |
| Agent runner | `tests/uat/desktop-agent/helpers/agent_runner.py` | ~100 | Working |
| OpenCUA loop unit tests | `tests/uat/desktop-agent/tests/test_opencua_loop.py` | ~400 | 36 tests passing |
| **Total unit tests** | Various `tests/` files | — | **156 passing** |
| **Total visual tests** | `test_slack_visual.py` | — | **7 defined (VIS-001–VIS-007)** |

### Architecture That Emerged: Dual-Model System

The original plan assumed a single model (Claude Sonnet) for both actions and validation. The actual implementation uses a **dual-model architecture**:

```
┌─────────────────────────────────────────────────────────┐
│                   Test Runner (pytest)                    │
│                                                          │
│  ┌──────────────────┐        ┌────────────────────────┐ │
│  │ OpenCUA-7B (8.3B) │        │ Gemma 3 12B (Ollama)   │ │
│  │ Port 8100 (local) │        │ Port 11434 (local)     │ │
│  │                    │        │                        │ │
│  │ PURPOSE: Actions   │        │ PURPOSE: Validation    │ │
│  │ - Click, type,     │        │ - Screenshot analysis  │ │
│  │   scroll, hotkey   │        │ - PASS/FAIL verdicts   │ │
│  │ - PyAutoGUI output │        │ - Text descriptions    │ │
│  │ - ~12-28s/image    │        │ - ~3-5s/image          │ │
│  │ - FREE (local)     │        │ - FREE (local)         │ │
│  └──────────────────┘        └────────────────────────┘ │
│           │                            │                 │
│           ▼                            ▼                 │
│  ┌──────────────────────────────────────────────────┐   │
│  │              Lume macOS VM (repengine-uat)         │   │
│  │  macOS Tahoe 26.3 | 1024x768 | Slack 4.48.94     │   │
│  │  VNC on port 5900 for screenshots                 │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

**Why dual-model:** OpenCUA-7B outputs PyAutoGUI commands (e.g., `pyautogui.click(x=512, y=384)`), not natural language analysis. It cannot answer "does this screenshot show a help menu?" — it can only produce UI actions. Gemma 3 12B (via Ollama) handles screenshot analysis and produces PASS/FAIL verdicts with text explanations.

**Critical insight:** When Ollama is unavailable, the validation cascade falls back to the agent (OpenCUA), which outputs action commands instead of analysis — causing validation to always fail with nonsensical results.

### What Worked

1. **Test framework structure** — pytest with session-scoped VM fixtures, function-scoped agent fixtures, and `@pytest.mark.desktop_agent` marker. 156 unit tests pass without any VM.

2. **VNC screenshots** — The Cua SDK's `CGDisplayCreateImage()` returns stale frames inside Lume VMs. VNC screenshots via `vncdotool` produce accurate, real-time captures. This was the key workaround.

3. **OpenCUA server** — FastAPI wrapper serving HuggingFace transformers model with OpenAI-compatible API on port 8100. Inference works reliably on Apple MPS (M3 MacBook Pro).

4. **Custom agent loop** — `@register_agent(priority=2)` overrides the Cua SDK's built-in OpenCUA handler, parsing PyAutoGUI output via `ast.parse()` and converting to SDK response items.

5. **Ollama for validation** — Gemma 3 12B provides reliable PASS/FAIL verdicts from screenshots with structured validation prompts. ~3-5s per analysis.

6. **Linting improvements** — Ruff/linter identified that OpenCUA works best with NO system prompt (empty string). Also improved code block extraction ordering in the PyAutoGUI parser.

### What Did NOT Work

1. **Lume VM state management is fragile**
   - No snapshot support in Lume v0.2.80 (contrary to original plan)
   - macOS keychain locks randomly, producing blocking dialogs
   - Slack loses authentication after keychain reset events
   - Slack process can become invisible (error -1712) requiring kill + relaunch
   - Each test run requires manual verification that VM is in a usable state

2. **OpenCUA-7B click grounding accuracy**
   - The model outputs pixel coordinates, but accuracy on complex UIs like Slack is inconsistent
   - Small UI targets (buttons, links) are frequently missed
   - ~12-28s inference latency per screenshot makes iterative correction slow
   - The model sometimes outputs malformed PyAutoGUI (missing parentheses, wrong function names)

3. **VM infrastructure reliability**
   - SSH connections close unexpectedly
   - `osascript` (AppleScript) via SSH hangs when targeting SecurityAgent
   - `lume ssh` works for CLI commands but cannot control GUI elements
   - VNC is the only reliable way to interact with the VM GUI, but VNC-based automation is brittle

4. **Keychain dialog blocking** (critical operational issue)
   - "Slack wants to use your confidential information stored in 'Slack Safe Storage'" dialog appears unpredictably
   - Requires precise VNC coordinate targeting to dismiss: password field at (570, 275), type "lume", click "Always Allow" at (410, 305)
   - Even after `security unlock-keychain -p lume` + `security set-keychain-settings`, the dialog can reappear after VM restart

5. **Slack re-authentication flow**
   - After keychain reset, Slack shows "Sign In to Worldwide Global" screen
   - Requires: click sign-in button → Safari opens → click "Allow" → Slack loads
   - This multi-app flow is extremely difficult to automate reliably

### Model Comparison Table

| Feature | OpenCUA-7B | Gemma 3 12B | Claude Sonnet |
|---------|------------|-------------|---------------|
| **Size** | 8.3B params | 12B params | Cloud API |
| **Cost** | Free (local) | Free (local) | ~$0.10-0.30/test |
| **Inference (1024x768)** | ~12-28s (MPS) | ~3-5s (Ollama) | ~2-3s (API) |
| **UI action output** | PyAutoGUI commands | Text only | Structured JSON |
| **Screenshot analysis** | No (action-only) | Yes (PASS/FAIL) | Yes (detailed) |
| **Click accuracy** | Low-Medium | N/A | High |
| **Setup complexity** | High (3 patches, custom server) | Low (ollama pull) | None |
| **Offline capable** | Yes | Yes | No |

### Technical Debt Inventory

1. **`opencua_loop.py` at 590 lines** — exceeds 500-line file size target. Should be split into parser, action converter, and agent loop modules.
2. **Venv patches lost on reinstall** — `qwen_vl_utils` stub and `agent.py` Ollama image guard disable are manual patches not tracked in version control.
3. **No VM state persistence** — No automated way to restore VM to known-good state before each test run.
4. **Hardcoded VNC coordinates** — Keychain dialog dismissal uses hardcoded pixel coordinates that break with any resolution or dialog layout change.
5. **Two venvs required** — `.venv` (test runner with Cua SDK) and `.venv-vllm` (OpenCUA server with PyTorch) must both be maintained separately.
6. **OpenCUA model patches** — 3 patches to `modeling_opencua.py` (tie_weights, pooler_output, DynamicCache) and `config.media_placeholder_token_id` override are fragile.

### Open Questions (Updated)

| # | Original Question | Resolution |
|---|-------------------|------------|
| 1 | Cua SDK import paths | **Resolved**: `from computer import Computer`, `from agent import ComputerAgent` (Option A) |
| 2 | Lume on GitHub Actions macOS-14 | **Still open**: Not tested |
| 3 | Slack Desktop version pinning | **Partially resolved**: Slack 4.48.94 installed, auto-update not explicitly disabled |
| 4 | Concurrent VM execution | **Still open**: Not tested |
| 5 | Hybrid validation strategy | **Resolved**: Dual-model — OpenCUA for actions, Ollama/Gemma 3 for validation |

**New open questions:**

6. **Is OpenCUA-7B the right action model?** — Click accuracy is low, inference is slow, setup is complex. Newer models (Qwen2.5-VL-72B, UI-TARS) may perform better but require more compute.
7. **Should we use Claude API instead of local models?** — Claude Sonnet has much higher click accuracy and lower latency, but costs ~$0.10-0.30 per test step.
8. **Can VM state management be automated?** — Lume has no snapshots. Options: custom disk image cloning, or a "VM reset script" that programmatically clears keychain, verifies Slack auth, and sets known-good state.
9. **Is the Cua SDK the right framework?** — The SDK requires significant workarounds (custom agent loop, VNC patches). A simpler approach using direct VNC + model API calls might be more maintainable.

### Decision Log (Updated)

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-19 | Use OpenCUA-7B as default action model (replacing Claude Sonnet) | Free local inference, no API costs during development |
| 2026-02-19 | Custom FastAPI server for OpenCUA (not mlx-vlm) | mlx-vlm uses M-RoPE incompatible with OpenCUA's 1D RoPE |
| 2026-02-19 | HuggingFace transformers (not vLLM) for inference | vLLM doesn't support MPS; transformers works on Apple Silicon |
| 2026-02-19 | Dual-model architecture (OpenCUA + Gemma 3) | OpenCUA outputs actions only; validation requires a separate text analysis model |
| 2026-02-20 | VNC screenshots as primary method | Cua SDK's CGDisplayCreateImage returns stale frames in Lume VMs |
| 2026-02-20 | Empty system prompt for OpenCUA | Linter analysis confirmed model works best without system prompt injection |
| 2026-02-20 | `ast.parse()` for PyAutoGUI parsing (not regex) | More reliable extraction of function calls and arguments |
| 2026-02-21 | Pause and restart with fresh discovery | Too many workarounds accumulated; need to re-evaluate approach |

### Recommendations for Next Iteration

**Option A: Fix VM State + Keep OpenCUA**
- Create a "VM reset script" that unlocks keychain, verifies Slack auth, and kills stale processes
- Improve OpenCUA click accuracy with prompt engineering or fine-tuning
- Split opencua_loop.py into smaller modules
- Effort: 3-5 days

**Option B: Switch to Claude API for Actions**
- Replace OpenCUA-7B with Claude Sonnet 4 for UI actions
- Keep Ollama/Gemma 3 for validation (cost savings)
- Higher accuracy, lower latency, simpler setup
- Ongoing cost: ~$2-15/week
- Effort: 2-3 days

**Option C: Hybrid VNC + Direct Model API**
- Drop Cua SDK entirely
- Use VNC for screenshots and input (vncdotool)
- Use Claude or OpenCUA via direct API calls
- Simpler architecture, fewer moving parts
- Effort: 3-5 days

**Option D: Evaluate Newer Open-Source VLMs**
- Research UI-TARS, Qwen2.5-VL variants, and other models released since OpenCUA
- Some may have better UI grounding accuracy with less setup
- Effort: 1-2 days (research), then 2-3 days (implementation)
