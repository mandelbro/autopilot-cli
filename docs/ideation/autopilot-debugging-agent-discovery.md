# Discovery: Autopilot Debugging Agent -- Autonomous Testing and Fix Cycle with E2E testing and UX features

## The One-Liner

Add an autonomous Debugging agent to the autopilot system that manually tests the application from acceptance criteria against staging, diagnoses and fixes failures in source code, re-runs until green, drafts E2E tests to protect against regressions, ensures the E2E tests run correctly, then performs a UX review pass and generates a report based on that review.

## The Problem

Today the autopilot pipeline has a gap between "code is merged" and "feature actually works for a user." The QA Tester agent does staging verification via curl and browser snapshots, but it cannot:

1. **Run real E2E tests** that exercise full user flows (magic link login, OAuth callbacks, multi-step wizards)
2. **Diagnose root causes** when a flow fails -- it can report "broken" but cannot read console errors, inspect network waterfalls, or trace state management bugs
3. **Fix issues autonomously** -- failures create GitHub issues and wait for human triage
4. **Validate UX quality** -- there is no agent that evaluates whether a feature *looks right* and *feels right*, only whether it *functions*

The immediate pain point: the magic link auth flow (`chris+repengine-uat-test@montesmakes.co`) completes the email round-trip but redirects back to login instead of dashboard. This has been the result of a manual process of over 10 rounds of attempting to sign into the web app (stg-app.repengine.co) with a magic link, encountering a failure, requesting assistance from the Hans subagent to review the error or Render logs, then provide a fix for the error, then try again.

This is exactly the kind of bug that a Debugging agent should catch, diagnose (is it a token parsing issue? a route guard race? a session persistence problem?), fix, verify, then add automated testing to protect against regressions.

## Current State Analysis

### Existing Autopilot Agents

| Agent | Can Test? | Can Fix Code? | Can Run Browser? |
|-------|-----------|---------------|------------------|
| PL    | No        | No            | No               |
| EM    | Indirectly (just all) | Yes | No         |
| TA    | No (reviews PRs) | No       | No               |
| QA    | Staging curl + browser MCP | No | Yes (MCP snapshots) |
| PD    | Staging curl + browser MCP | No | Yes (MCP snapshots) |
| DA    | Health checks only | No      | No               |

**Gap**: No agent can interactively test acceptance criteria against staging, read browser console output, inspect network requests, or iterate on code fixes based on interactive testing findings.

### Existing Test Infrastructure

**Playwright** (at `render/app-ui/`):
- `@playwright/test` v1.58.2 installed in devDependencies
- `playwright.config.ts` configured with multi-browser matrix (Chromium, Firefox, WebKit)
- `testDir: './tests/cross-browser'` -- contains 4 existing cross-browser specs (`core-rendering.spec.ts`, `performance-compat.spec.ts`, `responsive-layout.spec.ts`, `accessibility-compat.spec.ts`). The Debugging agent's E2E regression tests will go in a separate `tests/e2e/` directory to maintain a clear separation between cross-browser compatibility tests and feature-level E2E regression tests.
- `webServer` config starts Vite dev server automatically
- `PLAYWRIGHT_BASE_URL` env var supported for pointing at staging
- Scripts: `npm run test:e2e` and `npm run test:e2e:ui`

**Desktop Agent Debugging** (at `tests/uat/desktop-agent/`):
- UI-TARS 1.5 7B (via Cua SDK + MLX) for GUI automation inside Lume macOS VMs
- Gemma 3 12B (Ollama) for visual validation (screenshot PASS/FAIL verdicts)
- 123 unit tests passing, 7 visual tests (VIS-001 through VIS-007)
- Designed for Slack Desktop visual verification -- not web browser testing
- Requires Lume VM with 4 CPU / 8GB RAM / 64GB disk
- Framework is fully operational; Lume VM must be started before running visual tests (`lume start repengine-uat`)

**Frontend Auth Flow** (the immediate test target):
- `AuthCallback.tsx`: Extracts `?token=` and `?email=` from URL, calls `authClient.verifyOtp()`, fetches user data from PostgREST, routes to dashboard via `determineRedirectPath()`
- `auth-client.ts`: `AuthClient` class with magic link send, OTP verify, session refresh, localStorage persistence
- `auth.ts`: Wrapper functions with email validation, safe redirect URL handling
- Route: `/auth/callback` renders `AuthCallbackGuard` component
- Known bug: successful OTP verification redirects back to `/login` instead of `/dashboard`

### Existing Config & Models

The autopilot uses Pydantic models for dispatch validation (`autopilot/src/autopilot/models.py`):
- `VALID_AGENTS` frozenset defines the agent whitelist -- currently 6 agents
- `AgentName` Literal type must match
- `Dispatch` model has `agent`, `action`, `prompt`, `task_id`, `pr_number`, `project_name`, `project_root`
- `config.yaml` has per-agent model selection, timeouts, and max turns

Adding a new agent requires changes to: `models.py` (type + whitelist), `config.yaml` (timeouts, model, max_turns), and a new `agents/<name>.md` system prompt.

## Target Architecture

### Architecture Decision: Agent Placement

**Options Considered:**

1. **New top-level agent (debugging-agent)**: Sits alongside EM/TA/QA/PD in the dispatch plan. PL dispatches it directly.
   - Pro: Clean separation of concerns; independent timeout/model config; PL can dispatch it when appropriate
   - Pro: Follows established agent pattern -- minimal scheduler changes
   - Con: Cannot modify source code AND run tests in the same invocation without scope-constraint violations
   - **Verdict: This is the one.**

2. **Sub-workflow of PL**: PL orchestrates a multi-step sequence (draft tests, run, diagnose, fix) within a single dispatch.
   - Pro: No new agent type needed
   - Con: PL is explicitly read-only; this would violate its core constraint
   - Con: Complex multi-tool workflow in a single agent prompt is brittle

3. **Extension of EM**: EM already writes code and runs tests. Add E2E capability to EM.
   - Pro: EM already has code-write permissions
   - Con: EM is already the most complex agent (580-line system prompt); adding E2E diagnosis bloats it further
   - Con: EM operates on feature branches pre-merge; Debugging runs post-merge on staging

**Decision: Option 1 -- New `debugging-agent` top-level agent.**

The Debugging agent is dispatched by PL after merge + deploy, similar to how QA and PD are dispatched. It has both code-read/write AND browser capabilities. Its scope is constrained to E2E test files and the specific source files implicated by debugging findings.

### Architecture Decision: Test Framework

**Options Considered:**

1. **Playwright only** (browser E2E): Fast, headless, CI-ready. Handles web flows natively. Cannot test Slack Desktop or native apps.
   - Effort: Low -- already installed, config exists
   - Speed: ~2-5s per test (headless Chromium)

2. **Desktop Debugging only** (UI-TARS + Lume VM): Can test anything visible on a desktop. Heavy setup, fragile VM state, 101s per test.
   - Effort: High -- VM management, model downloads, monkey-patches
   - Speed: ~60-120s per test

3. **Tiered approach**: Playwright for web flows (primary), Desktop Debugging for Slack/native visual validation (secondary, non-blocking).
   - Effort: Medium -- Playwright is primary, Desktop Debugging is opt-in
   - Speed: Playwright tests run every cycle; Desktop tests run on-demand

**Decision: Option 3 -- Tiered approach, Playwright as primary.**

Web flows (auth, integrations hub, dashboard, OAuth callbacks) use Playwright. Slack Desktop visual verification stays in the existing Desktop Debugging framework and is triggered optionally (same as PD's current opt-in desktop verification). The Debugging agent defaults to Playwright and only escalates to Desktop Debugging for features that cannot be browser-tested.

### Cycle Integration

```
Task Backlog -> EM Implements -> PR Created -> TA Reviews -> Merged -> DA Verifies Deploy
                                                                          |
                                                                   [Deploy Green]
                                                                          |
                                                              +-----> QA Verifies (acceptance criteria)
                                                              |
                                                              +-----> Debugging Agent (debugging cycle)
                                                              |
                                                              +-----> PD Verifies (product alignment)
```

**When Debugging Agent runs:**
- After merge + successful deploy (DA confirms deploy green)
- PL dispatches Debugging agent with: task ID, PR number, acceptance criteria, target staging URL
- **Execution order**: Debugging agent runs BEFORE QA and PD. Because the Debugging agent may modify source code and push fix PRs, QA and PD must verify against the final state of the code. If the Debugging agent pushes fixes, DA confirms the fix deploy is green before QA/PD are dispatched. If the Debugging agent finds no issues, QA and PD can run immediately (in parallel with each other).

**Debugging Agent Actions:**

| Action | Trigger | What It Does |
|--------|---------|-------------|
| `interactive_test` | New feature merged + deploy green | Uses browser MCP to test acceptance criteria interactively against staging |
| `diagnose_and_fix` | Interactive testing found failures | Traces failures found during interactive testing, reads console/network logs, fixes source code, creates PR |
| `verify_fix` | Fix applied in diagnose_and_fix | Re-tests interactively via browser MCP to confirm fixes work (max 3 iterations total) |
| `draft_e2e_tests` | Feature passes interactive testing | Drafts Playwright E2E tests as regression protection for the verified flow |
| `verify_e2e_tests` | E2E tests drafted | Runs Playwright suite to ensure E2E tests pass reliably |
| `ux_review` | Feature passes functional tests (MANDATORY) | Captures screenshots, evaluates UX against design system, generates review artifact |

### Debugging Agent Workflow (Single Dispatch)

```
Phase 1: Interactive Testing
  - Read task acceptance criteria from task file
  - Use browser MCP (ruflo browser tools) to interactively test each acceptance criterion against staging
  - Navigate flows, fill forms, click buttons, observe behavior -- conversational browser control
  - For flows requiring native interaction (e.g., Slack Desktop), use desktop UAT tools alongside browser MCP
  - Record findings: what passed, what failed, console errors, unexpected behavior

Phase 2: Diagnose & Fix (max 3 iterations)
  - If all acceptance criteria PASS in Phase 1: proceed to Phase 4
  - If any criteria FAIL:
    - Capture: console errors, network requests, screenshots from browser MCP
    - Diagnose: trace the failure to specific source code (within source_scope)
    - Fix: modify source code (scoped to relevant files only)
    - Run `just all` to verify no regressions
    - Commit fix, push to branch, create PR with `fix(module): resolve debugging failure` label

Phase 3: Verify Fix
  - Re-test interactively via browser MCP to confirm fixes work
  - If PASS: proceed to Phase 4
  - If FAIL: return to Phase 2 (up to 3 total iterations, then escalate to question-queue)

Phase 4: Draft E2E Regression Tests
  - AFTER the flow is debugged and verified working:
  - Draft Playwright E2E tests in render/app-ui/tests/e2e/<feature>/
  - Tests codify the acceptance criteria as repeatable, headless regression protection
  - Playwright is for CI/regression only -- browser MCP remains the primary interactive testing tool

Phase 5: Verify E2E Tests
  - Run Playwright suite against staging to ensure tests pass reliably
  - If tests flake: adjust timeouts, selectors, or retry logic
  - E2E tests should NOT exist until after the flow is debugged and verified

Phase 6: UX Review (MANDATORY)
  - Capture full-flow screenshots at key states
  - Evaluate layout, spacing, color, typography against design system
  - Generate UX review artifact at docs/ux-reviews/<feature>.md
  - Flag specific improvement suggestions
```

### Browser Interaction Modes

The Debugging agent uses two distinct modes of browser interaction:

- **Browser MCP** (ruflo browser tools): Interactive, conversational-style browser control for exploratory testing and debugging. This is the PRIMARY tool for testing acceptance criteria. The agent navigates pages, fills forms, clicks elements, reads content, and takes screenshots through MCP tool calls. Browser MCP enables real-time observation and ad-hoc investigation that scripted tests cannot provide.

- **Playwright**: Scripted, repeatable, headless browser automation for regression testing and CI. Playwright tests are drafted AFTER a flow is verified working via browser MCP. They codify acceptance criteria as automated checks that run in CI pipelines. Playwright is NOT used for initial testing or debugging -- it is regression protection only.

### Safety & Guardrails

**Code modification scope**: The Debugging agent CAN write code, but is constrained to:
- `render/app-ui/tests/e2e/**` -- E2E test files (always allowed)
- Source files directly implicated by debugging findings (requires diagnosis justification in decision log)
- **Never**: autopilot files, config files, database migrations, deployment config

**Fix cycle limits**:
- Max 3 fix iterations per dispatch (mirrors EM's Three-Strike Rule)
- If 3 iterations fail, escalate to question-queue and stop
- Each fix must pass `just all` before being pushed

**Staging interaction**:
- Read-only browser interaction unless testing a write endpoint
- Only staging URLs (stg-*.repengine.co) -- never production
- Authentication uses the designated test user (`chris+repengine-uat-test@montesmakes.co`)

**Out-of-scope root cause**: If diagnosis identifies a root cause in files outside `source_scope`, the agent escalates to question-queue with full diagnostic evidence (console errors, network traces, code path analysis). PL then dispatches EM with the diagnosis as context. The Debugging agent does NOT modify files outside its declared scope under any circumstances -- `source_scope` is a hard boundary, not advisory.

**Resource limits**:
- Playwright runs headless Chromium (no GPU, minimal memory)
- Timeout: 1800s (30 min) per dispatch -- enough for test authoring + 3 fix iterations
- Model: `opus` for diagnosis quality; `sonnet` acceptable for simple test runs

**Session management**:
- The Debugging agent maintains a persistent browser session for staging via Browser MCP. Before each test run, the agent checks for an active session (valid JWT in localStorage). If the session is active and the task is NOT testing the login flow, the agent skips authentication and proceeds directly.
- When testing the login flow specifically, the agent logs out first (clears session), then follows the full magic link flow using Mailpit to retrieve the OTP.
- If a persistent session has expired, the agent re-authenticates via the magic link flow before proceeding with non-auth tests.
- Auth flow instructions (login, logout, session recovery) are documented in the agent system prompt (`autopilot/agents/debugging-agent.md`).

## Task File Schema

The Debugging agent needs structured input describing what to test. Proposed schema for Debugging task files:

```yaml
# tasks/debugging/<feature-slug>.yaml
feature: "magic-link-login"
title: "Magic Link Authentication Flow"
description: >
  User requests magic link via email, receives link,
  clicks through to app, completes auth, lands on dashboard.

staging_url: "https://stg-app.repengine.co"
test_user:
  email: "chris+repengine-uat-test@montesmakes.co"
  role: "account_executive"

# Steps the E2E test should exercise
steps:
  - action: "navigate"
    target: "/login"
    expect: "Login page with email input visible"

  - action: "fill"
    target: "input[name=email]"
    value: "{{ test_user.email }}"

  - action: "click"
    target: "button[type=submit]"
    expect: "Confirmation screen shown"

  - action: "wait_for_email"
    provider: "mailpit"
    subject_contains: "Your RepEngine login code"
    timeout_seconds: 5

  - action: "extract_magic_link"
    source: "mailpit"
    expect: "Magic link URL extracted from captured email body"

  - action: "navigate"
    target: "{{ magic_link_url }}"
    expect: "Redirected to /auth/callback with token and email params"

  - action: "wait_for_navigation"
    target: "/dashboard"
    timeout_seconds: 10
    expect: "Dashboard page loaded, user name visible"

# Acceptance criteria (machine-checkable assertions)
acceptance_criteria:
  - "Login page renders without errors"
  - "Magic link email is captured by Mailpit within 5 seconds"
  - "Auth callback processes token without errors"
  - "User session is persisted in localStorage"
  - "Dashboard loads with user's first name displayed"
  - "No console errors during the entire flow"

# Source files involved (for scoped code fixes)
source_scope:
  - "render/app-ui/src/pages/AuthCallback.tsx"
  - "render/app-ui/src/lib/auth-client.ts"
  - "render/app-ui/src/lib/auth.ts"
  - "render/app-ui/src/features/Authentication/**"
  - "render/api-service/src/api_service/auth/**"

# Optional: UX review configuration
ux_review:
  enabled: true
  capture_states:
    - "login_page_initial"
    - "login_page_email_entered"
    - "confirmation_screen"
    - "auth_callback_loading"
    - "dashboard_loaded"
  design_system_ref: "render/app-ui/src/lib/design-tokens.ts"
```

This YAML format is both human-readable (a product manager can review it) and machine-parseable (the agent extracts steps and assertions). The `source_scope` field constrains which files the Debugging agent is allowed to modify during fix cycles.

## Email Integration Strategy

The magic link flow requires reading real emails during Debugging. This section documents the options evaluated, decisions made, and the rationale behind each.

### Options Evaluated

**Option A: Google Workspace MCP (Real Gmail Integration)**
- Use the installed `google_workspace` MCP server to read emails from `chris+repengine-uat-test@montesmakes.co` via Gmail API tools (`search_gmail_messages`, `get_gmail_message_content`)
- Pro: Tests the actual email delivery pipeline end-to-end (SES -> Gmail)
- Pro: Already installed and configured; delivery is essentially instant
- Con: **200 email/month limit** on the current plan -- Debugging runs could exhaust this quickly
- Con: Agent needs Gmail API access -- security surface increase
- **Status: Available for ad-hoc manual testing. Not suitable as primary Debugging strategy due to volume limit.**

**Option B: API Bypass (Direct Token) -- REMOVED**
- After sending the magic link, query the `auth_magic_links` table via PostgREST to get the OTP token directly
- Pro: Fast, deterministic, no email dependency
- Con: Doesn't test email delivery
- Con: **Requires production code that exists solely for testing** -- a fundamentally unsound development principle. Code that runs in production should serve production purposes.
- **Status: Tried and removed. Not a viable approach.**

**Option C: Mailpit SMTP Trap (Sidecar on api-service)**
- Run [Mailpit](https://github.com/axllent/mailpit) as a sidecar process inside the api-service Docker container
- Mailpit captures all outgoing SMTP emails and exposes them via a REST API
- Pro: Tests email sending and content without real delivery
- Pro: Unlimited volume -- no monthly email limits
- Pro: No production code changes -- the `SMTPEmailSender` in `email_sender.py` already supports SMTP on `localhost:1025`
- Pro: Mailpit REST API enables programmatic email retrieval for test assertions
- Con: Adds a second process to the api-service container (mitigated by lightweight binary and simple entrypoint)
- Con: Does not test real email delivery (SES -> inbox) -- but that's covered by Option A for spot-checks

### Decision: Option C (Mailpit Sidecar) as primary, Option A (Google Workspace MCP) for spot-checks.

Mailpit runs as a sidecar inside the staging api-service container. The api-service sends magic link emails to `localhost:1025` (SMTP), and the Debugging agent retrieves them from `localhost:8025` (Mailpit REST API) via a thin proxy route on the api-service. This tests email composition and sending without consuming external email quotas. For periodic end-to-end verification that real emails arrive in Gmail, Option A (Google Workspace MCP) can be used manually.

### Implementation: Mailpit Sidecar on api-service

#### Why Sidecar (Not Separate Service)

Render exposes one port per service, so Mailpit's API (port 8025) cannot be directly exposed alongside the FastAPI app (port 8000). A sidecar approach keeps Mailpit internal to the container and proxies API access through FastAPI. This avoids a separate Render service (~$7/mo) and keeps the email capture co-located with the email sender.

#### Infrastructure Changes

**1. Dockerfile addition** (`render/api-service/Dockerfile`):

Download the Mailpit binary in the build stage and include it in the final image. Mailpit is a single static Go binary (~15MB), no runtime dependencies.

```dockerfile
# In the build stage or a dedicated stage:
ARG MAILPIT_VERSION=v1.22.3
ADD https://github.com/axllent/mailpit/releases/download/${MAILPIT_VERSION}/mailpit-linux-amd64.tar.gz /tmp/mailpit.tar.gz
RUN tar -xzf /tmp/mailpit.tar.gz -C /usr/local/bin/ mailpit && chmod +x /usr/local/bin/mailpit
```

**2. Entrypoint script** (`render/api-service/scripts/entrypoint.sh`):

Start Mailpit in the background before launching the FastAPI app. Mailpit only starts when `AUTH_EMAIL_PROVIDER=smtp`.

```bash
#!/usr/bin/env bash
set -euo pipefail

# Start Mailpit sidecar only when using SMTP provider (staging/Debugging)
if [ "${AUTH_EMAIL_PROVIDER:-ses}" = "smtp" ]; then
  echo "[mailpit] Starting SMTP trap on :1025, API on :8025"
  mailpit --smtp 0.0.0.0:1025 --listen 127.0.0.1:8025 --max 500 &
  MAILPIT_PID=$!

  # Wait for Mailpit to be ready
  for i in $(seq 1 10); do
    if curl -sf http://127.0.0.1:8025/api/v1/info > /dev/null 2>&1; then
      echo "[mailpit] Ready (PID $MAILPIT_PID)"
      break
    fi
    sleep 0.5
  done
fi

# Start the FastAPI application (exec replaces shell, inherits signals)
exec uvicorn api_service.main:app --host 0.0.0.0 --port 8000 "$@"
```

**3. Environment variables** (staging only):

```
AUTH_EMAIL_PROVIDER=smtp
AUTH_EMAIL_SMTP_HOST=localhost
AUTH_EMAIL_SMTP_PORT=1025
```

Production continues using `AUTH_EMAIL_PROVIDER=ses` -- Mailpit is never started.

#### API Access: Proxy Route

A thin FastAPI route proxies requests to Mailpit's REST API. This route **only registers when `AUTH_EMAIL_PROVIDER=smtp`**, so it never exists in production.

**Route**: `GET /test/mailpit/messages`
**Purpose**: Debugging agent retrieves captured emails to extract magic link OTPs

Key Mailpit API endpoints to proxy:

| Mailpit API | Proxy Route | Purpose |
|-------------|-------------|---------|
| `GET /api/v1/messages` | `GET /test/mailpit/messages` | List captured emails |
| `GET /api/v1/message/{id}` | `GET /test/mailpit/messages/{id}` | Get email content (HTML/text) |
| `DELETE /api/v1/messages` | `DELETE /test/mailpit/messages` | Clear mailbox between test runs |
| `GET /api/v1/search?query=...` | `GET /test/mailpit/search?query=...` | Search by subject/recipient |

**Security**: The proxy route requires `SERVICE_API_KEY` authentication (same as inter-service calls), preventing unauthorized access. The route module is conditionally included at app startup -- it is not merely hidden behind an auth check, it does not exist in the production router at all.

#### Debugging Agent Email Retrieval Flow

```
1. Debugging agent triggers magic link request via Browser MCP (navigates to login, fills email, clicks submit)
2. api-service sends email via SMTPEmailSender -> localhost:1025
3. Mailpit captures the email
4. Debugging agent queries via curl: GET /test/mailpit/search?query=to:chris+repengine-uat-test@montesmakes.co
   (authenticated with SERVICE_API_KEY header, same pattern as QA/PD curl commands)
5. Debugging agent extracts OTP and magic link URL from the curl response (JSON)
6. Debugging agent navigates Browser MCP to the magic link URL
7. Auth callback flow completes in the browser
```

**Note on tool usage**: Browser MCP (ruflo browser tools) handles all DOM interaction -- navigating, filling forms, clicking, taking screenshots. Mailpit email retrieval uses `curl` with `SERVICE_API_KEY` authentication, following the same pattern established by QA Tester and PD agents for staging API calls. Browser MCP is never used to access the Mailpit proxy route.

#### Health Check Integration

The existing `/health/detailed` endpoint can include Mailpit status when `AUTH_EMAIL_PROVIDER=smtp`:

```json
{
  "modules": {
    "auth": { "status": "healthy" },
    "mailpit": { "status": "healthy", "messages": 42, "smtp_port": 1025 }
  }
}
```

#### Task File Schema Update

The `wait_for_email` step in Debugging task files should reference the Mailpit provider:

```yaml
  - action: "wait_for_email"
    provider: "mailpit"           # was: "gmail"
    subject_contains: "Your RepEngine login code"
    timeout_seconds: 5            # near-instant with local SMTP
```

#### Risks & Mitigations

| Risk | Probability | Mitigation |
|------|-------------|------------|
| Mailpit process crashes | Low (single binary, no deps) | Entrypoint script can add a health-check loop; Render restarts container on health failure |
| Port conflict | Very Low | Mailpit binds `127.0.0.1:8025` (API) and `0.0.0.0:1025` (SMTP) -- neither conflicts with FastAPI on `8000` |
| Resource contention | Very Low | Mailpit uses ~10MB RAM at idle, ~30MB under load. Negligible vs. FastAPI/uvicorn |
| Emails persist across test runs | Low | Debugging agent calls `DELETE /test/mailpit/messages` at start of each test run to clear state |

## Implementation Plan

### Phase 1: Foundation (Debugging Agent Scaffold + Interactive Testing Capability)
**Goal**: Working Debugging agent that can interactively test acceptance criteria against staging using browser MCP

**Deliverables**:
1. New agent: `autopilot/agents/debugging-agent.md` (system prompt with browser MCP as primary testing tool)
2. Model/config updates: `autopilot/src/autopilot/models.py` (add `debugging-agent` to VALID_AGENTS and AgentName)
3. Config updates: `autopilot/config.yaml` (add debugging_agent timeouts, model, max_turns)
4. Browser MCP integration: Agent system prompt includes ruflo browser tool usage patterns for interactive testing
5. Debugging task file: `tasks/debugging/magic-link-login.yaml` (first task definition with acceptance criteria)
6. Mailpit sidecar infrastructure: Dockerfile, entrypoint, proxy route (for email-dependent flows)
7. Mailpit test helpers: `render/app-ui/tests/e2e/helpers/mailpit.ts` (email retrieval for later E2E tests)

**Effort**: 8-13 Sprint Points

### Phase 2: Diagnosis & Fix Cycle + E2E Regression Tests
**Goal**: Debugging agent can diagnose interactive testing failures, fix source code, and draft E2E regression tests after fixes are verified

**Deliverables**:
1. Enhanced system prompt with diagnosis workflow (browser MCP findings, console log extraction, network analysis)
2. Fix-cycle protocol with Three-Strike Rule and escalation
3. PR creation with `debugging-fix` label for traceability
4. Integration with `just all` for regression checks
5. Playwright E2E test infrastructure: `render/app-ui/tests/e2e/` directory, config updates, first regression tests
6. Playwright trace/HAR capture configuration (for E2E regression suite)

**Effort**: 5-8 Sprint Points

### Phase 3: UX Review Pipeline (MANDATORY)
**Goal**: Debugging agent generates UX review artifacts with improvement suggestions -- this phase is mandatory for every debugging dispatch, not optional

**Deliverables**:
1. Screenshot capture at defined flow states (via browser MCP)
2. UX review document template at `docs/ux-reviews/<feature>.md`
3. Design system comparison logic (spacing, colors, typography)
4. Optional "Ive" persona integration for design expertise
5. Figma integration hooks (stretch -- export as design tokens diff)

**Effort**: 5-8 Sprint Points

### Phase 4: Autopilot Integration
**Goal**: PL dispatches Debugging agent as part of the standard cycle

**Deliverables**:
1. PL system prompt updates (dispatch rules for Debugging agent)
2. Debugging task file discovery (PL reads `tasks/debugging/` for available Debugging tasks)
3. Board updates for Debugging status tracking
4. Cycle report integration (Debugging results in cycle reports)

**Effort**: 3-5 Sprint Points

## Existing Components & Reuse Plan

### What We Will Reuse

| Component | Location | How We Use It |
|-----------|----------|---------------|
| Playwright config | `render/app-ui/playwright.config.ts` | Extend with E2E project; add staging base URL |
| ProxyApiClient | `render/app-ui/src/services/api/ProxyApiClient.ts` | NOT used directly -- Playwright has its own HTTP client. But tests mirror the same API patterns |
| SMTPEmailSender | `render/api-service/src/api_service/auth/email_sender.py` | Already supports SMTP on `localhost:1025` -- no code changes needed for Mailpit |
| AuthClient | `render/app-ui/src/lib/auth-client.ts` | Reference implementation -- E2E tests exercise this through the browser |
| Autopilot agent.py | `autopilot/src/autopilot/agent.py` | invoke_agent() works for any agent in VALID_AGENTS -- no changes needed |
| Autopilot dispatch.py | `autopilot/src/autopilot/dispatch.py` | Dispatch normalization already handles all field variations |
| Autopilot scheduler.py | `autopilot/src/autopilot/scheduler.py` | Cycle execution handles any dispatched agent generically |
| QA Tester prompt patterns | `autopilot/agents/qa-tester.md` | Reuse verification workflow structure, staging URL table, evidence-based reporting |
| Desktop Debugging conftest.py | `tests/uat/desktop-agent/conftest.py` | Reference for VM lifecycle patterns; NOT directly imported |

### What We Will NOT Reuse

| Component | Reason |
|-----------|--------|
| Desktop Debugging framework (UI-TARS + Lume) | Overkill for web E2E testing; Playwright is faster and more reliable for browser flows. Desktop Debugging remains for Slack Desktop visual testing only. |
| EM's hive-mind integration | Debugging agent is a single-agent workflow, not a multi-worker hive session. Fix cycles are sequential, not parallel. |
| PD's browser MCP tools | **REUSED** -- Browser MCP (ruflo browser tools) IS the primary interactive testing tool for the Debugging agent. PD uses it for simple page loads and snapshots; the Debugging agent uses the same tools for deeper interactive testing, form filling, navigation, and debugging. Playwright is used separately for scripted regression tests only. |

### Consolidation Opportunities

- **Staging URL constants**: Currently duplicated in QA Tester prompt, PD prompt, and config.yaml. Extract to a shared staging config block that all agents reference. (Rule of Three -- 3 current consumers + Debugging agent = 4)
- **Evidence capture patterns**: QA and PD both capture curl output and screenshots as evidence. Debugging agent adds Playwright traces and HAR files. Consider a shared "evidence artifact" format across all verification agents.
- **Board update boilerplate**: QA, PD, and Debugging all need to update decision-log and project-board after verification. Extract the update protocol to a shared section in the README or a template file.

## Risk Register

### HIGH RISK: Email Delivery Latency in E2E Tests

**Probability**: Low (mitigated by Mailpit sidecar -- email capture is local, near-instant)
**Impact**: Flaky tests, false negatives, wasted cycles
**Mitigation**: Mailpit sidecar captures emails locally on `localhost:1025` -- no network delivery latency. Debugging agent retrieves emails via Mailpit REST API with a 5-second timeout (vs. 30s for real email). Real Gmail delivery is only used for periodic spot-checks via Google Workspace MCP, not in automated Debugging runs.
**Detection**: Test timeout at the `wait_for_email` step; Mailpit health check in `/health/detailed`

### MEDIUM RISK: Debugging Agent Fix Cycle Creates Conflicts with EM

**Probability**: Medium (if Debugging agent pushes fixes to the same files EM is working on)
**Impact**: Merge conflicts, duplicated work
**Mitigation**: Debugging agent creates fix PRs on dedicated `uat-fix/<feature>` branches. PL coordinates so Debugging and EM don't target the same files simultaneously. Source scope in the task file constrains what the Debugging agent can modify.
**Detection**: Git merge conflict on push

### MEDIUM RISK: Playwright Tests Flake on Staging

**Probability**: Medium (staging is shared, deploys in progress, network latency)
**Impact**: False failures trigger unnecessary fix cycles
**Mitigation**: Built-in retry logic (Playwright config already has `retries: 2` for CI). Debugging agent distinguishes between deterministic failures (same error 3 times) and flakes (different errors or intermittent). Agent checks deploy status via DA before running.
**Detection**: Same test passes on retry, or error message changes between runs

### LOW RISK: Model Cost Overrun from Diagnosis Loops

**Probability**: Low (Claude Max flat rate, no per-token billing)
**Impact**: Wasted cycle budget, not monetary cost
**Mitigation**: Three-Strike Rule limits fix iterations to 3 per dispatch. Escalation to question-queue prevents infinite loops.
**Detection**: Consecutive timeout tracking in scheduler circuit breaker

## Dependencies

### Must Have Before Starting Phase 1
1. **Browser MCP (ruflo browser tools) accessible** -- the Debugging agent needs browser MCP tools for interactive testing
2. **Mailpit sidecar operational on staging** -- `AUTH_EMAIL_PROVIDER=smtp` configured, Mailpit binary in Dockerfile, entrypoint script starting Mailpit, proxy route registered (needed for email-dependent flows like magic link)
3. **Debugging agent registered in autopilot** -- models.py, config.yaml, system prompt

**NOT a Phase 1 dependency**: Desktop UAT (UI-TARS + Lume VM). The tiered approach defaults to Playwright and Browser MCP for all web flows. Desktop UAT is opt-in for Slack Desktop testing only and can be integrated independently by starting the Lume VM when needed.

### Must Have Before Phase 2 (E2E Regression Tests)
1. **Playwright browsers installed** -- `npx playwright install chromium` in the app-ui venv
2. **E2E test directory created** -- `render/app-ui/tests/e2e/` with base helpers
3. **At least one flow verified working via interactive testing** -- E2E tests are drafted after debugging, not before

### Must Have Before Phase 4 (Autopilot Integration)
1. **At least 3 working E2E regression tests** -- magic link flow, integrations hub load, OAuth callback
2. **Debugging agent system prompt tested manually** -- run it outside autopilot first to validate behavior
3. **PL prompt update reviewed** -- ensure dispatch rules don't conflict with existing QA/PD flows

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| E2E test count | 5+ tests covering critical flows | `npm run test:e2e -- --list` |
| Test reliability | >90% pass rate across 10 consecutive runs | Playwright test results over time |
| Fix cycle success | >50% of failures auto-fixed within 3 iterations | Debugging agent decision log entries |
| Time to first green | <15 min from dispatch to all tests passing | Cycle report duration |
| False positive rate | <10% of failures are flakes, not real bugs | Manual review of escalated failures |

## Appendix: Immediate Action -- Magic Link Auth Bug

While this discovery covers the full Debugging agent architecture, the magic link auth redirect bug can be investigated immediately using existing tools. The bug likely lives in one of:

1. **`AuthCallback.tsx` line 104**: `routeUser(userData)` calls `determineRedirectPath()` -- if this returns `/login` instead of `/dashboard`, the redirect fails. Check what `determineRedirectPath` does for the test user's role.

2. **`AuthCallbackGuard.tsx`**: This component wraps `AuthCallback` at the `/auth/callback` route. It may be checking session state and redirecting to login before `AuthCallback` has a chance to verify the OTP.

3. **`auth-client.ts` `verifyOtp()`**: The OTP verification may succeed server-side but fail to persist the session to localStorage, causing the `AuthenticatedRoute` guard on `/dashboard` to bounce the user back to login.

4. **Race condition**: The `AuthCallbackGuard` and `AuthenticatedRoute` may both be checking `authClient.getSession()` -- if the callback hasn't finished verifying the OTP before the route guard fires, the user gets bounced.

This is exactly the kind of bug a Playwright test with network interception and state assertions would catch in seconds.
