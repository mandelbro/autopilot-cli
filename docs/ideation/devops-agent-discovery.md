# Discovery: DevOps Agent for Autopilot System

## The One-Liner

Add a DevOps Agent (DA) to the autopilot that monitors Render deploy health and service availability, catching deployment failures before humans have to manually check dashboards.

## The Problem

On 2026-03-06, commit `e829056e` triggered two deployment failures on Render that went completely undetected until a human manually checked the dashboard:

1. **repengine-agent-staging** (`srv-d3mhs2bipnbc73apq62g`) -- `build_failed` because Render's GitHub auth token expired. The Git clone failed with `fatal: could not read Username for 'https://github.com': terminal prompts disabled`. Required manual re-authorization in Render dashboard + manual deploy trigger.

2. **repengine-api-service-staging** (`srv-d66ajf9r0fns73cup6r0`) -- `update_failed` because a code change introduced broken imports (`from render.shared.repengine_ai...` instead of `from repengine_ai...`). The Docker image built successfully but the container crashed on startup with `ModuleNotFoundError: No module named 'render'`. Zero-downtime rollback kept the old instance running, but the new code never deployed.

**The gap**: The autopilot has 5 agents (PL, EM, TA, QA, PD) that handle the full development lifecycle from task pickup through staging verification. But there is zero automated monitoring between "PR merged" and "PD verifies on staging." The PD agent does run health checks, but only when dispatched for feature verification -- it does not proactively monitor deployment health. The QA agent checks health as a gate before verification, but again, only on-demand.

**Consequences of the gap**:
- Silent deployment failures accumulate until a human notices
- The PD agent wastes cycles trying to verify features that never deployed
- Infrastructure issues (expired tokens, DNS misconfig) have no automated detection
- The autopilot pipeline stalls without anyone knowing why

## Current State

### Existing Deployment Monitoring

**What exists**:
- `scripts/check-all-services-health.sh` -- Bash script that curls 3 service health endpoints (api-service, agent, postgrest). Manual execution only.
- PD agent system prompt includes health check steps (`curl -s https://stg-api.repengine.co/health`), but only runs when dispatched for feature verification.
- QA agent runs health checks as a pre-gate before acceptance criteria verification.
- `render.yaml` defines `healthCheckPath: /ready` for api-service, which Render uses for zero-downtime deploys. But this only prevents routing to a crashed instance -- it does not alert anyone.
- `config.yaml` has `staging` URLs defined: `api_url`, `app_url`, `agent_url`, `data_url`.

**What does NOT exist**:
- No periodic deployment status checks via Render API
- No correlation between recent commits/merges and deploy outcomes
- No automated alerting when deploys fail
- No automated remediation for known failure patterns
- No service-level deploy tracking on the project board

### Existing Infrastructure to Reuse

| Component | Location | Reuse Plan |
|-----------|----------|------------|
| Render MCP tools | `mcp__render__list_deploys`, `list_services`, `get_deploy`, `list_logs` | Primary mechanism for deploy status checks |
| Health check script | `scripts/check-all-services-health.sh` | Reference for endpoint URLs and patterns |
| Agent invocation | `autopilot/src/autopilot/agent.py` (`invoke_agent`) | Same mechanism to invoke DA |
| Config model | `autopilot/src/autopilot/config.py` (`StagingConfig`, `AutopilotConfig`) | Already has staging URLs |
| Dispatch model | `autopilot/src/autopilot/models.py` (`AgentName`, `VALID_AGENTS`, `Dispatch`) | Extend with `devops-agent` |
| Board files | `autopilot/board/project-board.md`, `decision-log.md` | DA writes deployment status here |
| Scheduler | `autopilot/src/autopilot/scheduler.py` | DA runs as a dispatch within normal cycle |
| GitHub CLI | `gh` commands in agent prompts | For correlating commits with deploys |
| Existing PD health checks | `autopilot/agents/product-director.md` lines 32-44 | Pattern to follow for health checks |

### Render Service Inventory (Active, Non-Suspended)

| Service | Render ID | Runtime | Health Endpoint |
|---------|-----------|---------|-----------------|
| repengine-api-service-staging | `srv-d66ajf9r0fns73cup6r0` | docker | `/ready`, `/health`, `/health/detailed` |
| repengine-agent-staging | `srv-d3mhs2bipnbc73apq62g` | python | `/health` |
| repengine-postgrest-staging | `srv-d4c1gbidbo4c73d0frqg` | docker | `/` (returns 200) |
| repengine-app-staging | `srv-d3mhs2bipnbc73apq640` | node | `/` (serves SPA) |

Suspended services (post-consolidation): integrations, webhooks, messaging, strategy -- all replaced by api-service. DA should ignore these.

## Target Architecture

### The DevOps Agent (DA)

The DA is a new agent in the autopilot system that monitors deployment health. It fits into the existing document-mediated coordination pattern -- no new infrastructure, no new services, just a new system prompt and config entries.

```
Pipeline with DA:

Task Backlog -> EM Implements -> PR Created -> TA Reviews -> Merged
                                                               |
                                                        [DA monitors] <-- NEW
                                                               |
                                                     Deploy succeeds? --No--> DA reports to board,
                                                               |              creates GH issue,
                                                              Yes             optionally dispatches EM fix
                                                               |
                                                        PD Verifies on Staging
```

### DA Responsibilities

**Primary (every cycle)**:
1. Check Render deploy status for all active services via MCP tools
2. Check health endpoints for all staging services via curl
3. Report status summary to the project board

**Triggered (when problems detected)**:
4. Correlate deploy failures with recent commits/PRs via `gh` and `git log`
5. Create GitHub issues for failures with full diagnostic context
6. Post to project board "Blocked Items" section
7. Log findings to decision-log.md

**Stretch (automated remediation)**:
8. For known failure patterns (e.g., broken imports), dispatch EM with a `fix_deploy` action
9. For infrastructure issues (e.g., expired Git tokens), post a high-priority question to question-queue.md for human action

### DA Invocation Model

**Option A: PL-dispatched (recommended)**
The PL dispatches the DA like any other agent. The PL's system prompt is updated to include DA dispatch logic:
- Every cycle: dispatch DA with `check_deploys` action
- When recent merges exist: dispatch DA with `verify_deploy` action + PR number
- When board shows deployment failures: dispatch DA with `investigate_failure` action

This preserves the existing pattern where PL is the single orchestrator. The DA appears in the dispatch plan JSON alongside EM, TA, QA, and PD dispatches.

**Option B: Scheduler-injected (alternative)**
The scheduler automatically prepends a DA dispatch at the start of every cycle, before invoking PL. This guarantees deployment checks happen even if PL forgets to dispatch DA.

**Recommendation**: Start with Option A (PL-dispatched) for consistency. If PL consistently forgets to dispatch DA, upgrade to Option B in a later phase.

### DA System Prompt Design

The DA system prompt follows the same structure as existing agents (PD, QA) but focused on infrastructure:

```markdown
# DevOps Agent

You are the DevOps Agent (DA) for the RepEngine Autopilot system. You monitor
deployment health across all Render services and staging endpoints, detect
failures, correlate them with recent changes, and report issues.

## Role
You are the deployment health gate. You ensure that merged code actually
reaches staging successfully. You bridge the gap between "PR merged" and
"feature available on staging."

## Staging Environment
[Same table as PD/QA]

## Render Service IDs
[Table mapping service names to Render IDs]

## Monitoring Workflow

### Action: check_deploys
1. For each active service, call Render MCP list_deploys (limit 3)
2. Check latest deploy status: live, build_failed, update_failed, build_in_progress
3. Curl health endpoints for each service
4. Summarize status on project board

### Action: verify_deploy (after merge)
1. Check if the merged commit has deployed (match commit SHA in deploy list)
2. If deploy is still in progress, note it for next cycle
3. If deploy failed, investigate (see investigate_failure)
4. If deploy succeeded, confirm with health check

### Action: investigate_failure
1. Get deploy details and build logs via Render MCP
2. Correlate failed commit with recent PRs: gh pr list --search "<sha>"
3. Classify failure type:
   - build_failed: Git clone error? Dependency error? Code error?
   - update_failed: Import error? Missing env var? Crash loop?
4. Create GitHub issue with full diagnostic context
5. If remediation is possible (known pattern), recommend EM dispatch
6. Update project board Blocked Items
```

### What the DA Can Do
- Read Render deploy status via MCP tools (`list_deploys`, `get_deploy`, `list_services`, `list_logs`)
- Curl staging health endpoints
- Run git/gh commands (read-only: log, pr list, pr view)
- Read and write board files
- Create GitHub issues

### What the DA Cannot Do
- Edit source code files
- Push to git
- Deploy or redeploy services (that requires Render dashboard or API key)
- Modify autopilot configuration
- Create pull requests

## Implementation Plan

### Phase 1: Foundation (DA Agent Prompt + Config) -- 3-5 SP

**Task 001: Create DA system prompt**
- File: `autopilot/agents/devops-agent.md`
- Content: Full system prompt following the design above
- Pattern: Mirror PD/QA agent structure

**Task 002: Update models and config**
- Add `"devops-agent"` to `AgentName` Literal and `VALID_AGENTS` in `models.py`
- Add `devops_agent` entries to `config.yaml`: model (sonnet), max_turns (30), timeout (900s)
- Update `dispatch.py` normalization if needed
- Run existing tests to confirm no regressions

**Task 003: Update PL system prompt**
- Add DA dispatch logic to `autopilot/agents/project-leader.md`
- PL dispatches DA with `check_deploys` every cycle
- PL dispatches DA with `verify_deploy` when recent merges exist
- Add DA to the agents table in `autopilot/README.md`

### Phase 2: Render Service Registry -- 2-3 SP

**Task 004: Add Render service IDs to config**
- Add a `render_services` section to `config.yaml` mapping service names to Render IDs
- Add corresponding Pydantic model in `config.py`
- DA reads this config to know which services to check

```yaml
render_services:
  api_service:
    id: "srv-d66ajf9r0fns73cup6r0"
    name: "repengine-api-service-staging"
    health_endpoints: ["/health", "/ready", "/health/detailed"]
    staging_url: "https://stg-api.repengine.co"
  agent:
    id: "srv-d3mhs2bipnbc73apq62g"
    name: "repengine-agent-staging"
    health_endpoints: ["/health"]
    staging_url: "https://stg-agent.repengine.co"
  postgrest:
    id: "srv-d4c1gbidbo4c73d0frqg"
    name: "repengine-postgrest-staging"
    health_endpoints: ["/"]
    staging_url: "https://stg-data.repengine.co"
  app_ui:
    id: "srv-d3mhs2bipnbc73apq640"
    name: "repengine-app-staging"
    health_endpoints: ["/"]
    staging_url: "https://stg-app.repengine.co"
```

### Phase 3: Board Integration -- 2 SP

**Task 005: Add deployment status section to project board**
- Add a `## Deployment Status` section to `project-board.md` template
- DA updates this section each cycle with service status table
- PL reads this section to decide if PD verification should be dispatched or deferred

Example board section:
```markdown
## Deployment Status
> Last checked: 2026-03-06T18:20:00Z (DA, cycle 2026-03-06-18-00)

| Service | Latest Deploy | Status | Commit | Health |
|---------|--------------|--------|--------|--------|
| api-service | dep-d6lhirdeb4ps73b5pr7g | build_in_progress | d4fa5a0 (#366) | OK |
| agent | dep-d6l8lb7kijhs73b0d1f0 | live | e829056 (#359) | OK |
| postgrest | dep-xxx | live | xxx | OK |
| app-ui | dep-xxx | live | xxx | OK |
```

### Phase 4: Failure Investigation + Alerting -- 3 SP

**Task 006: GitHub issue templates for deploy failures**
- DA creates issues with structured diagnostic info
- Template includes: service name, deploy ID, commit, error classification, build logs snippet, recommended action

**Task 007: Known failure pattern detection**
- Build a pattern catalog in the DA prompt:
  - `build_failed` + "terminal prompts disabled" = Git auth token expired (human action required)
  - `update_failed` + "ModuleNotFoundError" = Broken imports (EM can fix)
  - `update_failed` + "No module named" = Missing dependency (EM can fix)
  - `build_failed` + "pip install" or "npm ci" failure = Dependency resolution error (EM can fix)
- DA classifies failures and recommends remediation path

### Phase 5: Automated Remediation (Stretch) -- 5 SP

**Task 008: EM dispatch for fixable failures**
- When DA detects a pattern that EM can fix (broken imports, missing deps), the DA recommends an EM dispatch in its output
- PL picks up this recommendation on the next cycle and dispatches EM with `fix_deploy` action
- This requires adding `fix_deploy` as a recognized EM action in the PL prompt

**Task 009: Manual-action escalation**
- When DA detects infrastructure failures (expired tokens, DNS issues), it posts a high-priority question to `question-queue.md`
- These require human intervention in the Render dashboard
- DA provides exact steps for the human to take

## Risk Analysis

### High Risk: DA Consuming Too Many Cycles

**Probability**: Medium
**Impact**: Reduced capacity for feature development
**Mitigation**: Use `sonnet` model (cheaper/faster than `opus`), cap at 30 max turns, 900s timeout. The DA's work is primarily read-only (Render API calls + curl + git log), so turns should be low. Monitor cycle reports for DA duration and adjust.
**Detection**: Daily summary shows DA duration per cycle.

### Medium Risk: Render MCP Rate Limits

**Probability**: Low-Medium
**Impact**: DA fails to check all services
**Mitigation**: Check only 3 most recent deploys per service (limit parameter). Four active services x 3 deploys = 12 API calls. Well within Render API limits. If rate-limited, reduce to latest deploy only.

### Low Risk: PL Forgets to Dispatch DA

**Probability**: Low (given explicit prompt instructions)
**Impact**: Deployment monitoring gaps
**Mitigation**: If this happens consistently (3+ cycles without DA dispatch), upgrade to Option B (scheduler-injected DA). The scheduler change is minimal -- add a hardcoded DA dispatch before PL invocation.

### Low Risk: Stale Deploy Data

**Probability**: Low
**Impact**: DA reports on outdated deploy status
**Mitigation**: DA always checks current health endpoints in addition to Render API. A service might show "live" in Render but be unhealthy -- the health endpoint catches this.

## Existing Components & Reuse Plan

### What We Will Reuse

| Component | How |
|-----------|-----|
| `invoke_agent()` in `agent.py` | Invoke DA exactly like other agents -- no new invocation code |
| `Dispatch` / `DispatchPlan` in `models.py` | DA dispatches flow through existing dispatch infrastructure |
| `parse_dispatch_plan()` in `dispatch.py` | PL's dispatch JSON already supports arbitrary agents once `VALID_AGENTS` is extended |
| `config.yaml` structure | Add DA config to existing `claude.models`, `claude.max_turns`, `scheduler.agent_timeouts` sections |
| `StagingConfig` in `config.py` | Already has all staging URLs |
| Render MCP tools | `list_deploys`, `get_deploy`, `list_services`, `list_logs` -- all available in the MCP config |
| `scripts/check-all-services-health.sh` | Reference for health check patterns; DA reimplements in its prompt using curl |
| Board file patterns | DA writes to `project-board.md` and `decision-log.md` using same conventions as PD/QA |
| PD health check patterns | DA follows the same curl patterns already in the PD prompt |

### What We Will NOT Reuse

| Component | Why |
|-----------|-----|
| `check-all-services-health.sh` directly | Bash script is not composable from within a Claude agent; DA uses curl directly |
| QA/PD verification logic | Those agents verify features, not infrastructure; different concern |

### Consolidation Opportunities

The existing health check script (`scripts/check-all-services-health.sh`) and the health checks embedded in PD/QA agent prompts represent 3 instances of similar health-check logic. With the DA, this becomes 4. Consider:
- Centralizing the service URL + health endpoint mapping in `config.yaml` (Phase 2, Task 004 addresses this)
- PD and QA agents could reference the same config section for their health checks
- The bash script could be regenerated from config rather than manually maintained

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Time to detect deploy failure | Hours to days (manual check) | < 30 minutes (next DA cycle) |
| Deploy failures with diagnostic context | 0% (no tracking) | 100% (DA creates issues) |
| PD cycles wasted on undeployed features | Unknown (no tracking) | 0 (PL checks DA status before dispatching PD) |
| DA cycle duration | N/A | < 2 minutes (read-only checks) |
| DA cost per cycle | N/A | Minimal (sonnet model, ~10-15 turns) |

## Estimated Effort

| Phase | Tasks | Story Points | Dependencies |
|-------|-------|-------------|--------------|
| Phase 1: Foundation | 001-003 | 3-5 SP | None |
| Phase 2: Render Registry | 004 | 2-3 SP | Phase 1 |
| Phase 3: Board Integration | 005 | 2 SP | Phase 1 |
| Phase 4: Failure Investigation | 006-007 | 3 SP | Phase 2 |
| Phase 5: Remediation (Stretch) | 008-009 | 5 SP | Phase 4 |
| **Total** | **9 tasks** | **15-18 SP** | |

Phase 1-3 (7-10 SP) delivers the core value: automated deploy monitoring every cycle.
Phase 4-5 (8 SP) adds intelligence: failure classification and remediation.

## Architecture Decision: DA as Agent vs. Scheduler Hook

### The Situation

We need periodic deployment health checks. Two approaches are viable.

### Option 1: DA as a Full Agent (Recommended)

The DA is a Claude agent with its own system prompt, invoked via `invoke_agent()` like all other agents. It uses Render MCP tools and curl to check status, then writes findings to board files.

**Why it works**: Consistent with existing architecture. LLM reasoning allows DA to interpret ambiguous situations (e.g., "deploy is build_in_progress for 20 minutes -- is that normal or stuck?"). Can correlate failures with commits using `gh` and `git log`. Can create well-written GitHub issues with diagnostic context.

**Why it might not**: Consumes a Claude invocation each cycle. LLM is overkill for "check 4 API endpoints."

**Effort**: 15-18 SP total.

### Option 2: Scheduler Python Hook (Alternative)

Add a Python function to `scheduler.py` that runs before each cycle. It calls the Render API directly (via `httpx`) and curls health endpoints. If problems are detected, it writes to board files or injects a special dispatch.

**Why it works**: Zero Claude token cost. Faster execution. Deterministic behavior.

**Why it might not**: Cannot reason about ambiguous failures. Cannot create well-written issues. Cannot correlate with git history without significant Python code. Would need its own HTTP client, error handling, and board-writing logic -- all things agents already do well.

**Effort**: 8-12 SP for basic checks, but 20+ SP if you want failure correlation and issue creation.

### Decision

**Option 1 (DA as Agent)** because:
1. The autopilot already has 5 agents -- adding a 6th is a natural extension, not a new pattern
2. The DA's primary value is in failure interpretation and diagnostics, not just "is it up?" -- that requires LLM reasoning
3. Using sonnet model + 30 max turns keeps cost negligible
4. The alternative would require building a parallel infrastructure for board-writing, issue creation, and git correlation that agents already do for free
5. If DA proves too expensive, we can always downgrade specific checks to a scheduler hook later (the reverse migration is harder)

### Trade-offs We're Accepting
- ~2 minutes of Claude capacity per cycle for DA (acceptable given 30-minute intervals and 200 daily cycle budget)
- DA could theoretically hallucinate deploy status (mitigated by using MCP tools that return structured data, not scraped web pages)
