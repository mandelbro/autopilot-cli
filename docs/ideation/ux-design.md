# Autopilot CLI -- UX Design Document

**Version**: 1.0
**Date**: 2026-03-06
**Author**: Ive (UX Design Agent)
**Status**: Design Proposal

---

## Table of Contents

1. [Design Philosophy](#1-design-philosophy)
2. [Information Architecture](#2-information-architecture)
3. [REPL Experience](#3-repl-experience)
4. [Dashboard Design](#4-dashboard-design)
5. [Workflow UX](#5-workflow-ux)
6. [Notification and Alerting](#6-notification-and-alerting)
7. [Progressive Disclosure](#7-progressive-disclosure)
8. [Error and Edge Cases](#8-error-and-edge-cases)
9. [Visual Language](#9-visual-language)
10. [Keyboard Shortcuts](#10-keyboard-shortcuts)
11. [Accessibility](#11-accessibility)
12. [Reference Patterns](#12-reference-patterns)

---

## 1. Design Philosophy

### Core Principle: Conversation, Not Operation

The user is a technical architect directing a team. The CLI should feel like talking to a capable tech lead -- not like operating a control panel. Every interaction should reduce cognitive load, surface what matters, and stay out of the way when work is flowing.

### Design Values

**Trust through transparency.** Autonomous agents making code changes is inherently anxiety-inducing. Every action the system takes should be traceable, explainable, and reversible. The architect should never wonder "what just happened?"

**Attention is sacred.** Only interrupt the user for things that genuinely need human judgment. Everything else should be queryable but not pushed. The default state is quiet competence, not noisy progress.

**Speed to insight.** The most common question is "how is my project doing?" The answer should be visible in under 2 seconds from any state in the application.

**Expert-friendly, not expert-hostile.** Support both guided flows (wizards, prompts) and direct commands (flags, batch operations). Never force an expert through a wizard they don't need.

**Recoverable by default.** Every operation can be paused, resumed, undone, or abandoned. No one-way doors without explicit confirmation.

---

## 2. Information Architecture

### 2.1 Command Hierarchy

The CLI uses a **verb-noun** pattern consistent with `gh`, `kubectl`, and modern CLI conventions. Every subcommand works both as a one-shot CLI call and as a REPL slash command.

```
autopilot                          # Enter REPL (primary interface)
autopilot --help                   # Show top-level help
autopilot --version                # Print version

autopilot init                     # New project wizard
autopilot init --from <config>     # Initialize from existing config

autopilot project list             # List all projects
autopilot project show [name]      # Show project details
autopilot project switch <name>    # Set active project context
autopilot project archive <name>   # Archive a project
autopilot project config           # Edit project settings

autopilot plan discover            # Generate technical discovery document
autopilot plan tasks               # Generate task breakdown from discovery
autopilot plan estimate            # Estimate task complexity
autopilot plan enqueue             # Move approved tasks to execution queue
autopilot plan show                # Show current plan status

autopilot session start            # Begin autonomous development session
autopilot session pause            # Pause (agents finish current step)
autopilot session resume           # Resume paused session
autopilot session stop             # Stop (agents wrap up gracefully)
autopilot session status           # Show session state
autopilot session log              # View session event log

autopilot watch                    # Enter live monitoring TUI
autopilot watch --agent <id>       # Follow a specific agent

autopilot ask list                 # Show pending agent questions
autopilot ask <id>                 # Answer a specific question
autopilot ask --priority           # Show only high-priority questions

autopilot review list              # Show pending decisions
autopilot review show <id>         # Show decision details
autopilot review approve <ids>     # Approve one or more decisions
autopilot review reject <id>       # Reject with guidance
autopilot review policy            # View/edit auto-approval rules

autopilot report summary           # Project health summary
autopilot report velocity          # Sprint velocity metrics
autopilot report quality           # Code quality trends
autopilot report decisions         # Decision audit trail
autopilot report export            # Export to markdown/JSON

autopilot config set <key> <val>   # Set global config
autopilot config get <key>         # Get config value
autopilot config list              # Show all config
```

### 2.2 Information Hierarchy

Three levels of detail, accessible from any point:

```
Level 0 -- Prompt Line     What needs attention right now
Level 1 -- Dashboard       Project health at a glance (the default view)
Level 2 -- Detail Views    Deep inspection of any entity
```

### 2.3 Navigation Model

```
                    +------------------+
                    |   REPL Prompt    |  <-- Home state
                    +------------------+
                           |
          +----------------+----------------+
          |                |                |
   /dashboard        /watch           /ask list
   (overview)     (live TUI)      (question queue)
          |                |                |
          v                v                v
   /project show    agent stream     /ask <id>
   /plan show       task detail      answer flow
   /report          event log
```

The user always returns to the REPL prompt. There is no deep navigation tree. Every view is one command away from home.

---

## 3. REPL Experience

### 3.1 First Launch

When the user runs `autopilot` for the first time with no existing projects:

```
  Autopilot CLI v1.0.0

  Welcome. Autopilot orchestrates autonomous AI agents to build software
  from your technical vision.

  Get started:

    /init          Create your first project
    /help          See all commands
    /config        Configure defaults

  Tip: You can type natural language or use slash commands.

autopilot >
```

Design notes:
- No ASCII art logo. Clean, professional, fast.
- Three actionable next steps, not a wall of text.
- The tip about natural language sets the expectation that this is conversational.

### 3.2 Normal Startup (With Active Projects)

```
  Autopilot CLI v1.0.0

  Active project: my-saas-app
  Session: running (3 agents, 2h 14m elapsed)
  Attention: 1 question pending, 1 review ready

autopilot [my-saas-app] (3 running | ! 1 question) >
```

Design notes:
- Immediately shows what matters: active project, session state, pending items.
- The prompt encodes the most critical state so the user never has to ask "what's happening?"
- The `!` marker signals something needs human attention.

### 3.3 Prompt Format

The prompt is context-sensitive and encodes real-time state:

```
# No project selected
autopilot >

# Project selected, no session
autopilot [project-name] >

# Session running, all clear
autopilot [project-name] (3 running) >

# Session running, attention needed (yellow/amber)
autopilot [project-name] (3 running | ! 2 questions) >

# Session paused
autopilot [project-name] (paused) >

# Session stopped, viewing results
autopilot [project-name] (idle) >
```

Color coding in the prompt:
- Project name: **cyan** (informational)
- Running count: **green** (healthy)
- Attention marker: **yellow/amber** (action needed)
- Error state: **red** (something broke)
- Paused: **dim/gray** (intentionally inactive)

### 3.4 Input Modes

The REPL accepts three types of input:

**Slash commands** -- Direct, predictable, scriptable:
```
autopilot [my-app] > /session start
autopilot [my-app] > /ask list
autopilot [my-app] > /review approve 1-3
```

**Natural language** -- For exploration and complex requests:
```
autopilot [my-app] > show me what the agents are working on
autopilot [my-app] > how is the auth feature progressing?
autopilot [my-app] > pause everything, I need to review the database schema decisions
```

**Quick actions** -- Single-key responses in context:
```
  Agent alpha asks: Should I use PostgreSQL or SQLite for the session store?
  Context: Production deployment, expected 10k concurrent users
  Suggested: PostgreSQL

  [1] PostgreSQL  [2] SQLite  [3] Let me explain...  [s] Skip for now

>
```

### 3.5 Output Patterns

**Streaming output** for long operations (like Claude Code):
```
autopilot [my-app] > /plan discover

  Analyzing codebase...
  Reading src/ .............. 847 files
  Reading tests/ ............ 124 files
  Analyzing dependencies .... done
  Generating discovery document...

  --- Technical Discovery: my-saas-app ---

  [discovery content streams here, rendered as markdown]

  Discovery saved to .autopilot/discovery/2026-03-06.md
  Review and edit, then run /plan tasks to generate the backlog.

autopilot [my-app] >
```

**Structured output** for data (tables, not walls of text):
```
autopilot [my-app] > /project list

  PROJECT          STATUS    SESSION    AGENTS   TASKS        ATTENTION
  my-saas-app      active    running    3/3      12/47 done   1 question
  internal-tools   active    paused     0/2      3/8 done     --
  docs-site        archived  --         --       done         --

autopilot [my-app] >
```

**Compact confirmations** for quick actions:
```
autopilot [my-app] > /review approve 4
  Approved: "Use Redis for rate limiting" (agent-beta will proceed)
```

---

## 4. Dashboard Design

### 4.1 Default Dashboard (/dashboard)

Triggered by `/dashboard` or simply pressing Enter on an empty prompt when a project is active. Designed to fit in a standard 80x24 terminal.

```
  MY-SAAS-APP                                         Session: 2h 14m
  ─────────────────────────────────────────────────────────────────────

  AGENTS                          TASKS
  alpha   implementing auth-api   Queued      ████████░░░░  18
  beta    reviewing db-schema     In Progress ████░░░░░░░░   4
  gamma   writing tests           Done        ██████████░░  25
                                  Blocked     █░░░░░░░░░░░   1
                                                          ──────
                                                     Total  48

  ATTENTION NEEDED
  ! Question from alpha: Which OAuth provider should we integrate?
    Asked 12m ago -- /ask 7 to respond

  RECENT ACTIVITY                                         last 30 min
  14:23  beta   Completed: database migration scripts
  14:18  gamma  Started: unit tests for user service
  14:15  alpha  Decision: chose JWT over session cookies (auto-approved)
  14:02  beta   Started: review of schema design

  QUALITY                    SESSION METRICS
  Test coverage   78%        Tasks completed   6
  Lint issues     3          Decisions made    11
  Type errors     0          Questions asked   3
                             Tokens used       1.2M
```

Design notes:
- Two-column layout maximizes information density without feeling cramped.
- Agents section is always visible. You should always know what your team is doing.
- "Attention Needed" is visually prominent and includes the direct command to act.
- Recent activity shows a timeline, not a dump. Five most recent events.
- Quality and session metrics are secondary -- glanceable but not the focus.
- Total width: 72 characters. Fits comfortably in 80-column terminals.

### 4.2 Compact Dashboard (Narrow Terminals)

For terminals under 80 columns, or when invoked with `/dashboard --compact`:

```
  MY-SAAS-APP  running 2h14m  3 agents  25/48 tasks
  ────────────────────────────────────────────────
  ! 1 question pending (/ask 7)

  alpha  implementing auth-api
  beta   reviewing db-schema
  gamma  writing tests

  Last: beta completed database migration scripts (2m ago)
```

### 4.3 Multi-Project Overview

When the user has multiple active projects:

```
  ALL PROJECTS
  ─────────────────────────────────────────────────────────────────────

  my-saas-app                                              ! ATTENTION
  running  3 agents  25/48 tasks  1 question pending

  internal-tools
  paused   0 agents  3/8 tasks   --

  docs-site
  archived  complete

  Tip: /project switch <name> to change active project
```

---

## 5. Workflow UX

### 5.1 New Project Flow (/init)

The init wizard balances thoroughness with speed. It auto-detects what it can and asks only what it must.

```
autopilot > /init

  Let's set up a new project.

  Project name: my-saas-app
  Repository: . (auto-detected: git@github.com:org/my-saas-app.git)

  Analyzing repository...
  Detected: TypeScript, React, Node.js, PostgreSQL, Docker

  Tech stack looks right? [Y/n] y

  What are you building? (one sentence)
  > A multi-tenant SaaS platform for managing restaurant supply chains

  Quality standards:
  [x] Enforce test coverage minimum (default: 80%)
  [x] Require type safety (no any/unknown)
  [x] Lint checks must pass
  [ ] Require documentation for public APIs
  [ ] Require accessibility compliance (WCAG 2.1 AA)

  Use arrow keys to toggle, Enter to confirm.

  How many concurrent agents? [1-5, default: 3] 3

  Auto-approve low-risk decisions? (renaming, formatting, test fixes)
  [Y/n] y

  Project created: my-saas-app
  Config saved to .autopilot/config.yaml

  Next steps:
    /plan discover    Generate technical discovery document
    /plan tasks       Create task backlog
    /session start    Begin autonomous development

autopilot [my-saas-app] >
```

Design notes:
- Auto-detection reduces questions. The user confirms, not configures.
- Quality standards use a checkbox selector, not yes/no for each item.
- Defaults are opinionated and clearly shown. Experts override; beginners accept.
- Clear next steps at the end. The user is never left wondering "now what?"

**Express mode** for experienced users:

```
autopilot > /init --from project-template.yaml
  Project created: my-saas-app (from template)
  3 agents configured, quality gates enabled
```

### 5.2 Planning Flow

Planning is a sequential pipeline. Each step produces an artifact that the next step consumes. The user reviews and approves between each step.

```
  PLANNING PIPELINE

  [1] Discover  -->  [2] Tasks  -->  [3] Estimate  -->  [4] Enqueue
       ^                                                      |
       |              (review between each step)              |
       +------------------------------------------------------+
                    (iterate as needed)
```

**Step 1: Discovery**

```
autopilot [my-app] > /plan discover

  Generating technical discovery document...

  Analyzing:
    Architecture patterns .... done
    Dependency graph ......... done
    Test infrastructure ...... done
    Code quality baseline .... done
    Security posture ......... done

  --- Discovery Document ---

  [rendered markdown: architecture overview, tech debt inventory,
   risk areas, recommended approach, open questions]

  Saved to .autopilot/discovery/2026-03-06.md

  Review this document. Edit it directly or use /plan discover --revise
  to regenerate with corrections. When satisfied, run /plan tasks.

autopilot [my-app] >
```

**Step 2: Task Breakdown**

```
autopilot [my-app] > /plan tasks

  Generating task breakdown from discovery...

  PROPOSED TASKS                                          Priority
  ─────────────────────────────────────────────────────────────────
   1  Set up authentication service                       P0
   2  Create user management API                          P0
   3  Implement tenant isolation layer                    P0
   4  Build database migration framework                  P1
   5  Add rate limiting middleware                         P1
   6  Create API documentation generator                  P2
   7  Set up monitoring and alerting                      P1
   8  Implement webhook system                            P2
  ... (12 more tasks)

  20 tasks generated. Actions:
    /plan tasks --edit        Open task list in $EDITOR
    /plan tasks --reorder     Interactive priority adjustment
    /plan tasks --add         Add a task manually
    /plan tasks --remove <n>  Remove a task
    /plan estimate            Proceed to estimation

  Accept this breakdown? [Y/n/edit]
```

**Step 3: Estimation**

```
autopilot [my-app] > /plan estimate

  Estimating task complexity...

  TASK                                    SIZE    CONFIDENCE  RISK
  ─────────────────────────────────────────────────────────────────
  Set up authentication service           L       high        low
  Create user management API              M       high        low
  Implement tenant isolation layer        XL      medium      high
  Build database migration framework      M       high        low
  ...

  Summary: 3 XL, 5 L, 8 M, 4 S tasks
  Estimated session time: ~18 hours (with 3 agents)

  Proceed to enqueue? [Y/n]
```

**Step 4: Enqueue**

```
autopilot [my-app] > /plan enqueue

  Enqueued 20 tasks for execution.
  P0 tasks will execute first (5 tasks).

  Ready to start? Run /session start to begin autonomous development.
  Or /plan show to review the queue.
```

### 5.3 Monitoring Flow

Two modes: passive (REPL prompt) and active (watch TUI).

**Passive monitoring** -- The REPL prompt always shows state:
```
autopilot [my-app] (3 running | ! 1 question) >
```

Typing Enter on an empty line shows the dashboard (see Section 4.1).

**Active monitoring** -- `/watch` enters a full-screen TUI:

```
  AUTOPILOT WATCH                        my-saas-app  Session: 2h 14m
  ═════════════════════════════════════════════════════════════════════

  AGENT ALPHA                            implementing: auth-api (#1)
  ┌─────────────────────────────────────────────────────────────────┐
  │ Creating src/services/auth.ts                                   │
  │ Writing JWT token generation logic...                           │
  │ ▍                                                               │
  └─────────────────────────────────────────────────────────────────┘

  AGENT BETA                             reviewing: db-schema (#3)
  ┌─────────────────────────────────────────────────────────────────┐
  │ Analyzing schema for tenant isolation patterns                  │
  │ Checking foreign key constraints...                             │
  │ ▍                                                               │
  └─────────────────────────────────────────────────────────────────┘

  AGENT GAMMA                            testing: user-service (#2)
  ┌─────────────────────────────────────────────────────────────────┐
  │ Running test suite: 14/22 passing                               │
  │ Fixing: test_user_creation_with_duplicate_email                 │
  │ ▍                                                               │
  └─────────────────────────────────────────────────────────────────┘

  ───────────────────────────────────────────────────────────────────
  [Tab] cycle agents  [1-3] focus agent  [q] back to REPL
  [p] pause all  [?] help  [a] answer questions (1 pending)
```

Design notes:
- Each agent gets a panel showing its current stream of activity.
- The blinking cursor (block character) indicates live streaming.
- Keyboard shortcuts are always visible at the bottom.
- Pressing a number key focuses that agent, showing full output history.
- The `a` shortcut jumps directly to the question queue -- the most common action from watch mode.

**Focused agent view** (pressing `1` in watch mode):

```
  AGENT ALPHA                            implementing: auth-api (#1)
  ═════════════════════════════════════════════════════════════════════

  14:18:03  Reading existing auth patterns in codebase
  14:18:07  Found: src/middleware/auth-legacy.ts (deprecated pattern)
  14:18:12  Decision: Create new auth service, migrate later
            (auto-approved: low risk)
  14:18:15  Creating src/services/auth/index.ts
  14:18:22  Creating src/services/auth/jwt.ts
  14:18:34  Writing token generation with RS256 signing
  14:18:41  Creating src/services/auth/middleware.ts
  14:18:55  Running type checks... passed
  14:19:02  Running lint... 1 warning (unused import), fixing...
  14:19:05  Running tests... 3/3 passing
  14:19:08  Committing: "feat(auth): add JWT auth service"
  14:19:12  Moving to next subtask: refresh token rotation
  14:19:15  ▍

  ───────────────────────────────────────────────────────────────────
  [Esc] back to overview  [p] pause this agent  [q] back to REPL
  [/] search logs  [d] show decision history
```

### 5.4 Question/Answer Flow

When an agent needs human input, this is the highest-priority interaction. The UX must make answering fast and informed.

**Notification in REPL:**
```
  ── Agent alpha has a question ──────────────────────────────────
  Which OAuth provider should we integrate for SSO?
  Context: Enterprise customers need SAML/OIDC support.
  /ask 7 to respond
  ────────────────────────────────────────────────────────────────

autopilot [my-app] (3 running | ! 1 question) >
```

**Answering a question:**
```
autopilot [my-app] > /ask 7

  QUESTION #7 from Agent Alpha                     asked 12 minutes ago
  ─────────────────────────────────────────────────────────────────────

  Which OAuth provider should we integrate for SSO?

  CONTEXT
  Agent is implementing enterprise authentication (#task-14).
  The codebase currently has no SSO integration.
  Enterprise customers have requested SAML and OIDC support.

  AGENT'S ANALYSIS
  Considered three options:
    1. Auth0     -- Mature, expensive, full SAML/OIDC support
    2. Keycloak  -- Open source, self-hosted, full protocol support
    3. Custom    -- Build on passport.js, flexible but maintenance burden

  Agent recommends: Auth0 (fastest to ship, well-documented)

  YOUR RESPONSE
  [1] Auth0  [2] Keycloak  [3] Custom  [4] Write custom guidance

> 2

  Sent: Use Keycloak.
  Provide additional context? [y/N] y

  > We're self-hosting everything for data sovereignty. Use the
  > official Keycloak Node.js adapter. Prioritize OIDC over SAML.

  Guidance sent. Agent alpha will resume with Keycloak + OIDC.
```

Design notes:
- Questions always show context: what the agent is doing, what it considered, what it recommends.
- Quick-select numbered options for common cases.
- Option to add free-text guidance for nuanced answers.
- Timestamp shows urgency. If a question has been waiting 30+ minutes, it's highlighted.

**Batch answering:**
```
autopilot [my-app] > /ask list

  PENDING QUESTIONS
  ─────────────────────────────────────────────────────────────────
  #7   alpha   Which OAuth provider for SSO?              12m ago
  #8   beta    Should tenant data use schemas or DBs?      3m ago

  /ask 7 or /ask 8 to respond
  /ask --skip-all to let agents use their recommendations
```

### 5.5 Review Flow

For decisions that require explicit human approval (based on risk level and auto-approval settings).

```
autopilot [my-app] > /review list

  PENDING REVIEWS
  ─────────────────────────────────────────────────────────────────
  #12  beta   Add new DB index on users.tenant_id         risk: low
  #13  alpha  Refactor auth to use dependency injection    risk: medium
  #14  gamma  Delete deprecated legacy API routes          risk: high

  /review show <id> for details
  /review approve <ids> to approve (e.g., /review approve 12,13)
```

```
autopilot [my-app] > /review show 14

  REVIEW #14                                              risk: HIGH
  ─────────────────────────────────────────────────────────────────

  Delete deprecated legacy API routes

  AGENT: gamma
  TASK: Clean up technical debt (#task-22)

  WHAT WILL HAPPEN
  - Delete src/routes/v1/ (14 files, 1,847 lines)
  - Remove v1 route registration from app.ts
  - Update API documentation to remove v1 references

  WHY
  v1 routes have been deprecated since 2025-09. No traffic in logs
  for 90 days. Maintaining them blocks the new routing architecture.

  RISK ASSESSMENT
  - External consumers may still reference v1 endpoints
  - No feature flags; this is a hard removal
  - Rollback: git revert (clean commit boundary)

  ALTERNATIVES CONSIDERED
  - Keep v1 with deprecation warnings (rejected: maintenance cost)
  - Redirect v1 to v2 equivalents (possible but adds complexity)

  [a] Approve  [r] Reject  [d] Discuss  [s] Skip for now
> d

  Your guidance:
  > Add 301 redirects from v1 to v2 equivalents for 90 more days,
  > then delete. Create a migration guide for any external consumers.

  Guidance sent. Agent gamma will revise the approach.
```

---

## 6. Notification and Alerting

### 6.1 Notification Tiers

```
  TIER        DELIVERY                    EXAMPLES
  ────────────────────────────────────────────────────────────────
  Critical    In-REPL + OS notification   Agent crashed, build broken,
              + terminal bell             security vulnerability found

  Action      In-REPL + prompt badge      Question pending, review needed,
                                          decision blocked

  Info        In-REPL (if idle)           Task completed, test passed,
              Queryable via /log          commit created

  Silent      Queryable via /log only     Token usage, internal retries,
                                          routine operations
```

### 6.2 In-REPL Notifications

Notifications appear between the last output and the prompt. They never interrupt mid-typing.

```
  [user is typing a command...]

autopilot [my-app] > /project show

  [project details output]

  ── Notification ─────────────────────────────────────────────
  Agent beta completed: database migration scripts (#task-4)
  Agent alpha asks: Which OAuth provider for SSO? (/ask 7)
  ──────────────────────────────────────────────────────────────

autopilot [my-app] (3 running | ! 1 question) >
```

Design notes:
- Notifications batch. If three things happened while output was rendering, they appear together.
- Notifications never scroll away user-requested output.
- The prompt updates immediately to reflect new state.

### 6.3 OS-Level Notifications

For critical and action-tier events, when the terminal is not in focus:

```
  +----------------------------------------------+
  |  Autopilot CLI                                |
  |  Agent alpha is blocked -- question pending   |
  |  my-saas-app  /ask 7 to respond              |
  +----------------------------------------------+
```

Configurable via:
```
autopilot config set notifications.os true       # enable OS notifications
autopilot config set notifications.os false      # disable
autopilot config set notifications.sound true    # terminal bell
```

### 6.4 Idle Behavior

When the REPL is open but the user hasn't typed in 5+ minutes, and there are pending actions:

```
  ── Reminder (5m idle) ──────────────────────────────────────────
  1 question pending for 17 minutes. Agent alpha is blocked.
  /ask 7 to respond, or /ask --skip-all to use agent recommendations.
  ────────────────────────────────────────────────────────────────
```

Reminders are gentle and infrequent (every 5 minutes, max 3 times). They stop if the user dismisses with `/dismiss`.

---

## 7. Progressive Disclosure

### 7.1 Default vs Drill-Down

Every view has a default density and a detailed mode.

```
  COMMAND               DEFAULT (Level 1)           DETAIL (Level 2)
  ─────────────────────────────────────────────────────────────────────
  /dashboard            Project summary, agents,    + full metrics,
                        attention items              token costs, trends

  /session status       State, duration, agents     + per-agent breakdown,
                                                     task queue, decisions

  /plan show            Task list with status        + estimates, deps,
                                                     risk flags, history

  /report summary       Key metrics, trends          + charts (sparklines),
                                                     historical comparison
```

Drill-down is triggered by:
- Adding `--verbose` or `-v` flag
- Appending a specific entity ID (e.g., `/session status --agent alpha`)
- Using the `show` subcommand (e.g., `/plan show 14`)

### 7.2 Information Density Modes

Global setting that affects all views:

```
autopilot config set display.mode compact     # Minimal, data-dense
autopilot config set display.mode normal      # Default, balanced
autopilot config set display.mode verbose     # Maximum detail
```

**Compact mode** -- For experienced users on small terminals:
```
autopilot [my-app] > /dashboard
  3 agents running  25/48 tasks  ! 1 question  78% coverage  2h14m
```

**Normal mode** -- The default (see Section 4.1 dashboard).

**Verbose mode** -- For debugging or deep review:
```
  Adds: token usage per agent, decision rationale, full task dependency
  graph, quality gate details, git commit hashes, timing breakdowns
```

### 7.3 Contextual Help

Help adapts to what the user is doing:

```
autopilot [my-app] > /help

  COMMANDS (in current context: project active, session running)

  Most relevant right now:
    /ask list         1 question pending -- agents are blocked
    /review list      1 review ready
    /watch            Monitor agent activity live

  Session management:
    /session pause    Pause all agents
    /session stop     Stop session gracefully
    /session status   Detailed session state

  Planning:
    /plan show        View task queue and progress

  Type /help <command> for details on any command.
```

The help output reorders based on context. If there are pending questions, that command appears first.

---

## 8. Error and Edge Cases

### 8.1 Long-Running Operations

Any operation taking more than 2 seconds shows a progress indicator:

```
autopilot [my-app] > /plan discover

  Analyzing codebase... (847 files)
  [████████████████████░░░░░░░░░░░░░░░░] 58%  est. 45s remaining

  Ctrl+Z to run in background, Ctrl+C to cancel.
```

**Background operations:**
```
  [Ctrl+Z pressed]
  Discovery running in background. /jobs to check status.

autopilot [my-app] >
  [...user does other things...]

  ── Background job complete ──────────────────────────────────
  Discovery document generated. /plan show to review.
  ──────────────────────────────────────────────────────────────
```

### 8.2 Agent Failures

```
  ── Agent Failure ────────────────────────────────────────────
  Agent beta crashed while implementing tenant isolation (#task-3)

  Error: Test suite timed out after 120s
  Attempt: 2 of 3 (auto-retry in 30s)

  Actions:
    /session agent beta --logs    View full error log
    /session agent beta --retry   Retry immediately
    /session agent beta --skip    Skip this task
    /session agent beta --stop    Stop this agent
  ──────────────────────────────────────────────────────────────
```

After 3 failed retries:

```
  ── Agent Escalation ─────────────────────────────────────────
  Agent beta failed 3 times on: tenant isolation (#task-3)

  The agent could not resolve:
    Test "tenant_data_isolation" fails with timeout.
    Root cause appears to be a circular dependency in the
    tenant context provider.

  This task has been moved to "blocked" status.
  Other agents continue working on independent tasks.

  Actions:
    /ask 12                       Review the agent's analysis
    /plan tasks --unblock 3       Provide guidance and retry
    /plan tasks --reassign 3      Assign to a different agent
    /plan tasks --defer 3         Move to backlog
  ──────────────────────────────────────────────────────────────
```

Design notes:
- Auto-retry with backoff before bothering the user.
- Clear explanation of what failed and what the agent tried.
- Multiple resolution paths. The user chooses based on their judgment.
- Other agents keep working. One failure does not stall the pipeline.

### 8.3 Session Recovery

If the CLI process crashes or the terminal closes:

```
autopilot [my-app] > /session start

  Existing session detected (started 2h ago, interrupted 14m ago).

  Session state:
    3 agents were active
    Agent alpha: mid-task (auth-api, 60% complete)
    Agent beta: between tasks
    Agent gamma: running tests

  [R] Resume from interruption point
  [N] Start fresh (current progress preserved in git)
  [S] Show detailed recovery report

> R

  Resuming session...
  Agent alpha: restarting auth-api from last checkpoint
  Agent beta: picking up next task in queue
  Agent gamma: re-running test suite

  Session resumed. 3 agents active.
```

### 8.4 Network/API Failures

```
  ── Connection Issue ─────────────────────────────────────────
  Lost connection to AI provider (Claude API).
  Agents paused automatically. Work in progress is saved.

  Retrying in 15s... (attempt 1/5)
  Or: /session resume --when-connected to auto-resume on reconnect.
  ──────────────────────────────────────────────────────────────
```

### 8.5 Destructive Operation Safeguards

Any operation that deletes data or is irreversible requires confirmation:

```
autopilot [my-app] > /project archive my-saas-app

  This will:
  - Stop the active session (3 agents running)
  - Archive all project data
  - Project will be hidden from /project list (use --archived to see)

  Project data is preserved and can be unarchived.
  Type the project name to confirm: my-saas-app
```

---

## 9. Visual Language

### 9.1 Color Palette

All colors must have non-color alternatives (symbols, text labels) for accessibility.

```
  COLOR         USAGE                           FALLBACK SYMBOL
  ─────────────────────────────────────────────────────────────────
  Cyan          Project names, informational    [i]
  Green         Success, healthy, running       [ok]
  Yellow/Amber  Attention needed, warnings      [!]
  Red           Errors, failures, critical      [!!]
  Dim/Gray      Inactive, secondary info        (parentheses)
  White/Bold    Headers, emphasis               UPPERCASE
  Blue          Links, actionable items         [>]
```

### 9.2 Typography Conventions

```
  ELEMENT                 STYLE               EXAMPLE
  ─────────────────────────────────────────────────────────────────
  Section headers         UPPERCASE bold       AGENTS
  Table headers           UPPERCASE dim        PROJECT  STATUS
  Commands                Monospace/dim        /ask 7
  Agent names             Bold                 alpha
  Task names              Normal               auth-api
  Status labels           Colored              running  paused
  Numbers/metrics         Bold                 25/48
  Timestamps              Dim                  14:23
  Separators              Box-drawing chars    ─────────
```

### 9.3 Progress Indicators

```
  Determinate:    [████████████░░░░░░░░░░░░] 52%
  Indeterminate:  Analyzing codebase... ⠋
  Task status:    ● done  ○ queued  ◉ in progress  ◌ blocked
  Sparklines:     Velocity: ▁▂▃▅▇▆▅▃ (8 sprints)
```

### 9.4 Spacing and Layout

- One blank line between sections.
- Two-space indent for nested content.
- Right-align numeric columns.
- Max width: 72 characters for content (fits in 80-col terminal with margins).
- Tables use variable-width columns with minimum padding of 2 spaces.

---

## 10. Keyboard Shortcuts

### 10.1 REPL Mode

```
  SHORTCUT        ACTION
  ─────────────────────────────────────────────────────────
  Enter (empty)   Show dashboard
  Ctrl+C          Cancel current operation / clear input
  Ctrl+D          Exit REPL
  Ctrl+Z          Background current operation
  Ctrl+L          Clear screen, redraw prompt
  Tab             Auto-complete commands and arguments
  Up/Down         Command history
  Ctrl+R          Search command history
```

### 10.2 Watch Mode (TUI)

```
  SHORTCUT        ACTION
  ─────────────────────────────────────────────────────────
  q / Esc         Return to REPL
  Tab             Cycle between agent panels
  1-5             Focus specific agent
  p               Pause all agents
  r               Resume all agents
  a               Jump to question queue
  d               Show decision log
  /               Search/filter logs
  ?               Show help overlay
  f               Toggle full-screen for focused agent
```

### 10.3 Interactive Prompts

```
  SHORTCUT        ACTION
  ─────────────────────────────────────────────────────────
  1-9             Quick-select numbered option
  y/n             Yes/No confirmation
  e               Open in $EDITOR
  s               Skip / defer
  Esc             Cancel and return to prompt
```

---

## 11. Accessibility

### 11.1 Requirements

- All color-coded information must have a non-color alternative (symbol, label, or position).
- Screen reader mode: `autopilot config set accessibility.screen-reader true` outputs plain text without box-drawing characters or progress animations.
- High contrast mode: `autopilot config set accessibility.high-contrast true` uses only bold/normal weight instead of color.
- All interactive prompts must be navigable with keyboard only (no mouse required -- this is a CLI, so this is inherently met).
- Timing: idle reminders and auto-retry delays are configurable. No time-limited interactions.

### 11.2 Screen Reader Output

When screen reader mode is enabled:

```
  Dashboard for project my-saas-app.
  Session running for 2 hours 14 minutes.
  3 agents active.
  Attention: 1 question pending from agent alpha.
  Tasks: 25 of 48 complete.

  Agent alpha: implementing auth-api, task 1.
  Agent beta: reviewing database schema, task 3.
  Agent gamma: writing tests, task 2.
```

No box-drawing characters, no progress bars, no color escapes. Pure structured text.

---

## 12. Reference Patterns

### 12.1 Patterns Borrowed From Reference Tools

**From Claude Code CLI:**
- Conversational REPL as the primary interface
- Streaming output for long operations
- Slash commands for direct actions
- Context-sensitive prompt showing active state
- Natural language input alongside structured commands

**From gh CLI:**
- Verb-noun command hierarchy (`gh pr list` -> `autopilot session start`)
- Interactive fallback when required arguments are missing
- `--json` flag for scriptable output on all list commands
- Web fallback for complex views (`autopilot report --web` opens a browser dashboard)

**From lazygit:**
- Keyboard-driven TUI for the watch/monitor mode
- Panel-based layout for simultaneous visibility of related information
- Single-key shortcuts for common operations
- Status bar showing available actions

**From k9s:**
- Live-updating resource views (agents as the primary resource)
- Drill-down navigation (overview -> agent -> task -> log)
- Filtering and search across logs
- Color-coded status indicators

**From htop:**
- Dense but readable information display
- Header area with summary metrics (always visible)
- Sortable, filterable list of active processes (agents/tasks)
- Function key shortcuts displayed at the bottom

### 12.2 Patterns Intentionally Avoided

**Wizard fatigue.** Tools that force step-by-step flows for every action. Autopilot uses wizards only for first-time setup. After that, direct commands.

**Dashboard overload.** Tools that show everything at once. Autopilot shows what needs attention, and the rest is one command away.

**Silent autonomy.** Tools that do things without telling you. Autopilot surfaces every decision and action, categorized by importance.

**Modal hell.** Tools with deep navigation stacks where you lose your place. Autopilot has a flat navigation model: every view is one command from the REPL prompt.

---

## Appendix A: Command Quick Reference

```
  /init                    Create new project
  /project list|show|switch|archive
  /plan discover|tasks|estimate|enqueue|show
  /session start|pause|resume|stop|status|log
  /watch                   Live monitoring TUI
  /ask list|<id>           Agent question queue
  /review list|show|approve|reject|policy
  /report summary|velocity|quality|decisions|export
  /dashboard               Project overview (also: press Enter)
  /config set|get|list     Configuration
  /jobs                    Background operations
  /help [command]          Context-sensitive help
  /dismiss                 Dismiss notifications
  /exit                    Leave the REPL
```

## Appendix B: Configuration Defaults

```yaml
# .autopilot/config.yaml (project-level)
project:
  name: ""
  repo: "."
  tech_stack: auto-detect

agents:
  max_concurrent: 3
  auto_retry_count: 3
  auto_retry_delay: 30s

quality:
  test_coverage_minimum: 80
  require_type_safety: true
  require_lint_pass: true
  require_docs: false
  require_accessibility: false

approval:
  auto_approve_low_risk: true
  auto_approve_medium_risk: false
  require_approval_for_deletions: true
  require_approval_for_schema_changes: true

notifications:
  os_notifications: true
  terminal_bell: false
  idle_reminder_interval: 5m
  idle_reminder_max: 3

display:
  mode: normal          # compact | normal | verbose
  color: true
  unicode: true
  max_width: auto       # auto detects terminal width

accessibility:
  screen_reader: false
  high_contrast: false
```

## Appendix C: Exit Codes

```
  CODE    MEANING
  ─────────────────────────────────────────────
  0       Success
  1       General error
  2       Invalid arguments
  3       Project not found
  4       Session error (agent failure)
  5       Network/API error
  10      Interrupted by user (Ctrl+C)
  11      Session interrupted (unclean shutdown)
```

---

*End of UX Design Document*
