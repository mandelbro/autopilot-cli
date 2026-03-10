# UAT Framework -- Detailed UX Notes

**Date**: 2026-03-10
**Revised**: 2026-03-10
**Author**: Norwood (Technical Discovery Agent)
**Reviewer**: Ive (UX Design Agent)
**Companion to**: `docs/ideation/autopilot-uat-discovery.md`
**References**: `docs/ideation/ux-design.md` (all sections)

---

## Revision Summary

This document was revised for consistency with the Autopilot CLI UX Design Document (`ux-design.md`). Key changes:

1. **Command structure** restructured from flags to verb-noun subcommands per UX Design Section 2.1
2. **Status indicators** aligned with the color palette and fallback symbols from UX Design Section 9.1
3. **Progressive disclosure** levels corrected from 4 to 3, consistent with the UX Design's Default/Detail/Verbose framework (Section 7)
4. **Keyboard shortcuts** revised to avoid conflicts with Watch mode shortcuts (Section 10.2)
5. **Notification tiers** updated to include terminal bell for Critical tier per UX Design Section 6.1
6. **Dashboard integration** now documents the metrics trade-off explicitly
7. **Accessibility** expanded with screen reader output examples per UX Design Section 11.2
8. **Missing patterns** added: empty states, natural language input, `/help` integration, `--json` flag, exit codes, configuration defaults

---

## 1. Command Structure

### 1.1 Verb-Noun Pattern

The UX Design document (Section 2.1) establishes a verb-noun command pattern: `autopilot session start`, `autopilot plan discover`, `autopilot report summary`. UAT commands follow this pattern using `uat` as the noun with action subcommands.

All commands work both as one-shot CLI invocations (`autopilot uat run 042`) and as REPL slash commands (`/uat run 042`).

### Primary Commands

```
/uat run <task-id>             Run UAT on a single completed task
/uat run <start>-<end>         Run UAT on a range of tasks
/uat run --sprint <N>          Run UAT on all completed tasks in sprint N
/uat run --all                 Run UAT on all completed tasks

/uat coverage                  Show spec coverage summary
/uat gaps                      Show uncovered requirements
/uat gaps --phase <N>          Show gaps for specific implementation phase
/uat matrix                    Show full traceability matrix
/uat matrix --export json      Export matrix as JSON

/uat config                    Show current UAT configuration
/uat rebuild-index             Rebuild spec index from source docs
```

Design notes:
- `run` is the primary verb. When the user types `/uat 042`, the REPL infers `run` (same pattern as `gh pr 123` inferring `view`).
- Reporting subcommands (`coverage`, `gaps`, `matrix`) are nouns because they are views, not actions. This matches `/report summary`, `/report quality` in the existing design.
- The `--sprint` and `--all` flags stay on `run` because they modify the target, not the action.

### 1.2 Tab Completion

Following UX Design Section 3.2 (tab completion for all commands):

```
autopilot [my-app] > /uat <TAB>
  run         coverage    gaps        matrix      config      rebuild-index

autopilot [my-app] > /uat run <TAB>
  042         043         044         --sprint    --all

autopilot [my-app] > /uat run --sprint <TAB>
  1           2           3           4

autopilot [my-app] > /uat gaps --phase <TAB>
  1           2           3           4           5           6
```

Task ID completion shows only completed tasks that have not yet passed UAT. Sprint completion shows only sprints with completed tasks.

### 1.3 Natural Language Support

Following UX Design Section 3.4 (natural language as a valid input mode):

```
autopilot [my-app] > run UAT on task 42
autopilot [my-app] > how is our spec coverage looking?
autopilot [my-app] > what requirements are we missing for phase 2?
autopilot [my-app] > show me all UAT failures this sprint
```

The REPL interprets these as their equivalent slash commands. Natural language is particularly useful for exploratory queries like coverage and gaps, where the user may not remember the exact subcommand.

### 1.4 Scriptable Output

Following UX Design Section 12.1 (from gh CLI: `--json` flag for scriptable output on all list commands):

```
autopilot [my-app] > /uat coverage --json
autopilot [my-app] > /uat run 042 --json
autopilot [my-app] > /uat gaps --phase 2 --json
```

All commands that produce structured output support `--json` for piping to `jq` or consuming in scripts. This is consistent with the convention established in `/report export`.

---

## 2. Output Formatting

All UAT output follows the Rich formatting patterns from UX Design Section 3.5 (Output Patterns) and the visual language from Section 9.

### 2.1 Status Indicators

Consistent with the project's color palette (UX Design Section 9.1), UAT status indicators use both color and a non-color fallback symbol. The text label is always present for accessibility.

```
  COLOR         STATUS      SYMBOL   FALLBACK
  ──────────────────────────────────────────────────
  Green         PASS        check    [ok] PASS
  Red           FAIL        cross    [!!] FAIL
  Yellow/Amber  PARTIAL     warn     [!]  PARTIAL
  Dim/Gray      SKIP        dash     (--) SKIP
  Red bg        ERROR       bang     [!!] ERROR
```

In normal terminal output with color and unicode enabled:

```
  PASS     check  Green text
  FAIL     cross  Red text
  PARTIAL  warn   Yellow text
  SKIP     --     Dim text
  ERROR    !!     Red background, white text
```

In high-contrast mode (`accessibility.high-contrast: true`):

```
  [ok] PASS
  [!!] FAIL
  [!]  PARTIAL
  (--) SKIP
  [!!] ERROR
```

### 2.2 Score Presentation

UAT scores (0.0-1.0) use the same thresholds as the verification-quality skill's truth scores for visual consistency:

```
  RANGE        COLOR          LABEL             FALLBACK
  ──────────────────────────────────────────────────────────
  0.95-1.00    Green, bold    "Excellent"       [ok]
  0.85-0.94    Green          "Good"            [ok]
  0.75-0.84    Yellow         "Needs Attention" [!]
  0.00-0.74    Red            "Critical"        [!!]
```

### 2.3 Progress Bars

For batch UAT operations, use Rich progress bars consistent with UX Design Section 8.1 (long-running operations). Progress bars always include a numeric percentage alongside the visual bar.

```
autopilot [my-app] > /uat run --sprint 3

  Running UAT for Sprint 3 (14 completed tasks)...

  Initializing UAT swarm .... done (4 workers)

  Task 040  PASS  0.97  acceptance: 5/5, behavioral: 2/2, compliance: 4/4
  Task 041  PASS  0.95  acceptance: 4/4, behavioral: 3/3, compliance: 6/6
  Task 042  FAIL  0.92  acceptance: 4/5, behavioral: 2/2, compliance: 6/6
  [████████████████████░░░░░░░░░░░░░░░░░░░░]  3/14 tasks  21%  est. 28s

  Ctrl+Z to run in background. Ctrl+C to cancel.
```

When run in background (Ctrl+Z):

```
  UAT running in background for Sprint 3. /jobs to check status.

autopilot [my-app] >
  ...

  -- Background job complete ------------------------------------------
  UAT Sprint 3: 12/14 passing (85.7%). /uat run --sprint 3 for details.
  ----------------------------------------------------------------------
```

---

## 3. Notification Integration

Following UX Design Section 6 (Notification and Alerting), UAT events map to notification tiers.

### 3.1 Tier Mapping

```
  TIER        TRIGGER                           DELIVERY
  ──────────────────────────────────────────────────────────────────
  Critical    UAT score < 0.75 on any task      In-REPL + OS notification
              (gated mode: task reopened)        + terminal bell

  Action      UAT failure in advisory mode       In-REPL + prompt badge
              (human should review)

  Info        UAT pass                           In-REPL (if idle)
              UAT batch complete                 Queryable via /log

  Silent      UAT skipped (trivial task)         Queryable via /log only
              Spec index rebuild                 Queryable via /log only
```

Note: Critical tier includes terminal bell, consistent with UX Design Section 6.1 which specifies "In-REPL + OS notification + terminal bell" for critical events. Terminal bell is configurable via `autopilot config set notifications.sound true|false`.

### 3.2 In-REPL Notification Examples

Notifications appear between the last output and the prompt. They never interrupt mid-typing (UX Design Section 6.2).

**UAT pass (Info tier):**

```
  -- UAT Complete -------------------------------------------------
  Task 043: PASS (0.97) -- 11/11 tests passing
  -----------------------------------------------------------------

autopilot [my-app] (3 running) >
```

**UAT failure in advisory mode (Action tier):**

```
  -- UAT Failure ---------------------------------------------------
  Task 042: FAIL (0.92) -- 12/13 tests, 1 failure
  Default value mismatch: interval_seconds (RFC 3.4.1)
  /uat run 042 for details
  -----------------------------------------------------------------

autopilot [my-app] (3 running | ! 1 UAT failure) >
```

**UAT failure in gated mode (Critical tier):**

```
  -- UAT GATE FAILED -----------------------------------------------
  Task 042 reverted to IN PROGRESS
  Reason: Default value mismatch (RFC 3.4.1)
  UAT feedback attached to task. Fix and re-mark as complete.
  /uat run 042 for full report
  -----------------------------------------------------------------

autopilot [my-app] (3 running | !! UAT gate) >
```

The double-bang (`!!`) in the prompt badge follows the UX Design color palette: red for errors/critical (Section 9.1, fallback symbol `[!!]`). This distinguishes UAT critical events from agent questions (single `!`, yellow/amber).

---

## 4. Dashboard Integration

Following UX Design Section 4 (Dashboard Design), UAT integrates into the existing dashboard layout.

### 4.1 Default Dashboard Addition

The dashboard (80x24 terminal, 72-character content width) adds UAT metrics to the existing layout. UAT replaces two SESSION METRICS items ("Decisions made" and "Questions asked") with "UAT pass rate" and "Spec coverage". This trade-off is intentional: decisions and questions are transient session state visible in the prompt badge and ATTENTION NEEDED section, while UAT metrics are persistent quality indicators that belong in the QUALITY/METRICS area.

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
  ! UAT failure on Task 042: default mismatch (RFC 3.4.1)
    /uat run 042 to review

  RECENT ACTIVITY                                         last 30 min
  14:23  uat    Task 043 PASS (0.97)
  14:18  gamma  Started: unit tests for user service
  14:15  uat    Task 042 FAIL (0.92) -- default mismatch
  14:02  beta   Started: review of schema design

  QUALITY                    SESSION METRICS
  Test coverage   78%        Tasks completed   6
  Lint issues     3          UAT pass rate    83%
  Type errors     0          Spec coverage    46%
                             Tokens used       1.2M
```

Changes from the base dashboard (UX Design Section 4.1):
- UAT failures appear in ATTENTION NEEDED (they are actionable items, same as agent questions)
- UAT pass/fail events appear in RECENT ACTIVITY with "uat" as the agent name
- SESSION METRICS replaces "Decisions made" and "Questions asked" with "UAT pass rate" and "Spec coverage"
- Total content width stays at 72 characters

When no UAT has been run yet, the dashboard shows dashes for UAT metrics:

```
  QUALITY                    SESSION METRICS
  Test coverage   78%        Tasks completed   6
  Lint issues     3          UAT pass rate     --
  Type errors     0          Spec coverage     --
                             Tokens used       1.2M
```

### 4.2 Compact Dashboard

For narrow terminals (under 80 columns), UAT adds one line:

```
  MY-SAAS-APP  running 2h14m  3 agents  25/48 tasks  UAT: 83% pass
  ────────────────────────────────────────────────────────────────
  ! 1 UAT failure (/uat run 042)
```

When no UAT has run, the UAT segment is omitted from the compact view to save space.

---

## 5. Watch Mode Integration

When UAT is running in the background, the `/watch` TUI shows UAT activity.

### 5.1 UAT Agent Panel (when UAT is active)

```
  AUTOPILOT WATCH                        my-saas-app  Session: 2h 14m
  =====================================================================

  AGENT ALPHA                            implementing: auth-api (#1)
  +-------------------------------------------------------------+
  | Creating src/services/auth.ts                                 |
  | Writing JWT token generation logic...                         |
  |                                                               |
  +-------------------------------------------------------------+

  AGENT BETA                             reviewing: db-schema (#3)
  +-------------------------------------------------------------+
  | Analyzing schema for tenant isolation patterns                |
  |                                                               |
  +-------------------------------------------------------------+

  UAT                                    testing: Task 042 (2/4 phases)
  +-------------------------------------------------------------+
  | Cross-referencing specs: RFC 3.4.1, ADR-5                     |
  | Generating compliance tests... 6 tests                        |
  |                                                               |
  +-------------------------------------------------------------+

  -------------------------------------------------------------------
  [Tab] cycle agents  [1-3] focus agent  [u] UAT details  [q] REPL
```

### 5.2 Focused UAT View (pressing `u` in Watch mode)

```
  UAT                                    testing: Task 042 (2/4 phases)
  =====================================================================

  14:20:01  Loading task context for Task 042
  14:20:02  Spec refs found: RFC 3.4.1, Discovery ADR-5
  14:20:03  Phase 1/4: Generating acceptance tests... 5 tests
  14:20:05  Phase 2/4: Generating behavioral tests... 2 tests
  14:20:08  Phase 3/4: Generating compliance tests... 6 tests
  14:20:12  Phase 4/4: Running 13 tests via pytest
  14:20:14  Results: 12/13 passing (1 failure in acceptance)
  14:20:14  [cursor]

  -------------------------------------------------------------------
  [Esc] back to overview  [q] back to REPL  [/] search logs
```

Design notes:
- The focused UAT view follows the same pattern as the focused agent view in UX Design Section 5.3 (timestamps, sequential activity log, search with `/`).
- The `[u]` shortcut is unique to Watch mode and does not conflict with other Watch mode shortcuts (Section 10.2).

### 5.3 Watch Mode When UAT is Inactive

When no UAT is running, the UAT panel does not appear in Watch mode. The agent list adjusts to fill available space. This follows the "Attention is sacred" principle -- do not show empty panels.

---

## 6. Report Integration

### 6.1 `/report summary` Addition

The existing summary report (UX Design Section 7.1) includes UAT metrics:

```
autopilot [my-app] > /report summary

  PROJECT SUMMARY: my-saas-app
  ---------------------------------------------------------------------

  Sprint 3 progress:                        14/21 tasks (66%)
  Velocity (last 3 sprints):                18, 22, 19 pts/sprint

  QUALITY METRICS
  Test coverage:        78%                 Trend: stable
  Lint violations:      3                   Trend: decreasing
  UAT pass rate:        85.7%              Trend: improving
  Spec coverage:        46.3%              Trend: increasing
  Truth score:          0.94               Trend: stable

  COMBINED QUALITY SCORE                              0.91
    Truth score (40%):   0.94
    UAT score (60%):     0.89

  UAT HIGHLIGHTS
  Failing: Task 042 (RFC 3.4.1), Task 047 (RFC 3.8)
  New coverage this sprint: +12 requirements (+5.5%)
  Spec gaps in current phase: 3 requirements unassigned
```

When UAT has not been configured or run, the QUALITY METRICS section omits UAT rows and the COMBINED QUALITY SCORE shows only the truth score. This avoids showing confusing zeroes.

### 6.2 `/report quality` Addition

The quality report includes UAT trend data:

```
autopilot [my-app] > /report quality

  QUALITY TREND: my-saas-app (last 30 days)
  ---------------------------------------------------------------------

  UAT PASS RATE
  Sprint 1:  ████████████████████████████████░░░░░░  80%  (8/10)
  Sprint 2:  █████████████████████████████████████░  92%  (12/13)
  Sprint 3:  ██████████████████████████████████░░░░  86%  (12/14)

  SPECIFICATION COVERAGE
  Sprint 1:  ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░  22%
  Sprint 2:  ██████████████░░░░░░░░░░░░░░░░░░░░░░░  38%
  Sprint 3:  ██████████████████░░░░░░░░░░░░░░░░░░░  46%

  MOST COMMON FAILURE CATEGORIES
  1. Default value mismatches (RFC data model)          4 occurrences
  2. Missing error handling paths (RFC error recovery)  3 occurrences
  3. Output width violations (UX dashboard constraints) 2 occurrences
```

---

## 7. Error UX Patterns

### 7.1 UAT Pipeline Errors vs Test Failures

The UX must clearly distinguish between:
- **Test failure**: The implementation does not match the specification (actionable by developer)
- **Pipeline error**: The UAT framework itself has a problem (actionable by UAT maintainer)

This follows UX Design Section 8 (Error and Edge Cases), which requires clear explanations, actionable next steps, and recovery paths.

**Test failure presentation:**

```
  FAIL  Default values match RFC specification
        Expected: interval_seconds = 1800 (RFC 3.4.1, SchedulerConfig)
        Actual:   interval_seconds = 900
        File: src/autopilot/core/config.py:42
        Fix: Update default value to match RFC specification
```

Elements:
- Red `FAIL` prefix with cross symbol (or `[!!] FAIL` in high-contrast mode)
- Clear expected vs actual
- Spec reference with section number
- File and line number for the implementation
- AI-generated fix suggestion

**Pipeline error presentation:**

```
  [!!] UAT pipeline error (not a test failure)
  ---------------------------------------------------------------------

  Could not run UAT for Task 042:
  pytest exited with code 2 (collection error)

  Error: ModuleNotFoundError: No module named 'autopilot.core.config'

  This means the implementation file may not exist yet or has import
  issues. UAT cannot test code that does not import.

  Next steps:
  1. Verify the task's implementation file exists
  2. Check that all imports resolve
  3. Re-run: /uat run 042
```

Elements:
- Red background `ERROR` prefix (or `[!!] ERROR` in high-contrast mode)
- Explicit "not a test failure" label to prevent confusion
- Technical error details
- Human-readable explanation
- Numbered actionable next steps

### 7.2 Graceful Degradation

When parts of the UAT pipeline fail, the framework degrades gracefully:

```
  UAT RESULTS: Task 042                               Score: 0.83 *
  ---------------------------------------------------------------------

  * Score based on partial results (compliance tests could not run)

  ACCEPTANCE CRITERIA                                      4/5 PASS
    PASS  ...
    FAIL  ...

  BEHAVIORAL                                               2/2 PASS

  SPECIFICATION COMPLIANCE                                 SKIPPED
    Could not generate compliance tests: spec index missing for
    RFC Section 3.4.1. Run /uat rebuild-index.

  Score excludes skipped categories. Run again after fixing for
  a complete assessment.
```

The asterisk (`*`) on the score and the explicit "partial results" note ensure the user knows the assessment is incomplete.

### 7.3 Empty States

**No completed tasks:**

```
autopilot [my-app] > /uat run --all

  No completed tasks found. UAT runs against tasks marked complete.

  Current task status:
    In Progress  4     Queued  18     Blocked  1

  UAT will run automatically when tasks are completed (if auto_trigger
  is enabled). Or run /uat run <task-id> manually after marking a task
  complete.
```

**Task not complete:**

```
autopilot [my-app] > /uat run 042

  Task 042 is not marked complete (status: IN PROGRESS).
  UAT only runs against completed tasks.

  Mark as complete first, or use /uat run 042 --force to test anyway.
```

**No spec index:**

```
autopilot [my-app] > /uat coverage

  No specification index found. UAT needs to index the RFC, discovery,
  and UX design documents before it can track coverage.

  Run /uat rebuild-index to build the index (takes ~30s).
```

Design notes:
- Empty states always explain why there is nothing to show.
- Empty states always provide a concrete next action.
- This follows UX Design Section 8 which requires recovery paths for every error state.

---

## 8. Progressive Disclosure for UAT

Following UX Design Section 7 (Progressive Disclosure), UAT output supports three detail levels consistent with the document's Default/Detail/Verbose framework.

### Level 1: Default (summary)

The default output is a compact summary. The user gets the verdict immediately.

```
autopilot [my-app] > /uat run 042

  Task 042: FAIL (0.92) -- 12/13 tests, 1 failure in acceptance criteria
  /uat run 042 --verbose for full report
```

This follows the compact confirmation pattern from UX Design Section 3.5 ("Compact confirmations for quick actions").

### Level 2: Detail (full report)

Triggered by running the command again or by pressing `[v]` in the contextual shortcuts. Shows the full per-task report with categories, pass/fail per test, and spec references.

```
autopilot [my-app] > /uat run 042 --detail

  UAT RESULTS: Task 042                                    Score: 0.92
  ---------------------------------------------------------------------

  ACCEPTANCE CRITERIA                                      4/5 PASS
    PASS  Config model validates all fields per RFC 3.4.1
    PASS  All tests associated with this task are passing
    PASS  File complies with optimization guidelines
    PASS  Pydantic models use strict validation
    FAIL  Default values match RFC specification
          interval_seconds: expected 1800, got 900
          Ref: RFC Section 3.4.1

  BEHAVIORAL                                               2/2 PASS
    PASS  User can create config with defaults
    PASS  Config rejects invalid strategy values

  SPECIFICATION COMPLIANCE                                 6/6 PASS
    PASS  RFC 3.4.1: All config fields present
    PASS  RFC 3.4.1: Type annotations match spec
    PASS  Discovery ADR-5: YAML format supported
    (3 more passing)

  UX COMPLIANCE                                            N/A
    No UX requirements mapped to this task.

  Overall: 12/13 tests passing (92.3%)
  Recommendation: Fix interval_seconds default, re-run with /uat run 042
```

### Level 3: Verbose (`--verbose` or `-v` flag)

Full diagnostic output including task context, cross-reference analysis, individual test details with tracebacks, and generated test file location.

```
autopilot [my-app] > /uat run 042 -v

  UAT RESULTS: Task 042                                    Score: 0.92
  ---------------------------------------------------------------------

  TASK CONTEXT
  Title: Implement SchedulerConfig model
  File: src/autopilot/core/config.py
  Sprint Points: 3
  User Story: As a technical architect, I want a validated config model...
  Spec References: RFC 3.4.1, Discovery ADR-5

  CROSS-REFERENCE ANALYSIS
  RFC 3.4.1 SchedulerConfig:
    Fields specified: strategy, interval_seconds, cycle_timeout_seconds,
                      agent_timeout_seconds, agent_timeouts,
                      consecutive_timeout_limit
    Fields found: all 6 present
    Types match: yes
    Defaults match: 5/6 (interval_seconds mismatch)

  Discovery ADR-5:
    YAML format required: yes, verified
    Deep nesting support: yes, verified

  TEST DETAILS
  ---------------------------------------------------------------------

  test_task_042_config_model_validates_scheduler_fields
    Category: acceptance
    Status: PASS
    Duration: 0.003s
    Spec: RFC 3.4.1

  test_task_042_config_defaults_match_rfc
    Category: acceptance
    Status: FAIL
    Duration: 0.002s
    Spec: RFC 3.4.1
    Expected: SchedulerConfig().interval_seconds == 1800
    Actual:   SchedulerConfig().interval_seconds == 900
    Traceback:
      tests/uat/test_uat_task_042.py:23
      > assert config.interval_seconds == 1800
      E assert 900 == 1800

  ... (remaining 11 tests)

  GENERATED TEST FILE
  Location: tests/uat/test_uat_task_042.py (13 tests, 45 lines)
```

Design notes:
- The original document had 4 levels including a "Debug" level with `--debug` flag. This has been folded into `--verbose` with an additional `--debug` flag available when needed, but not documented as a primary disclosure level. Debug output is an operational concern for UAT maintainers, not a user-facing disclosure tier.
- The global `display.mode` setting (compact/normal/verbose from UX Design Section 7.2) also affects UAT output density.

---

## 9. Keyboard Shortcuts

Following UX Design Section 10 (Keyboard Shortcuts), UAT adds context-specific shortcuts.

### 9.1 After UAT Results Are Shown

```
After UAT results are shown:
  [v] Show detailed report (Level 2)
  [f] Show only failures
  [t] Show traceability for this task
  [n] Run UAT for next completed task
  [e] Open implementation file in $EDITOR
```

These shortcuts are contextual -- they only appear and function immediately after a UAT result is displayed, following the UX Design's principle of contextual actions.

Design notes:
- The original document used `[r]` for "re-run UAT". This conflicts with Watch mode's `[r]` for "resume all agents" (UX Design Section 10.2). Changed to omit `[r]` from the post-result context. Re-running is available via the command itself: `/uat run 042`.
- `[v]` for verbose/detail follows the pattern of progressive drill-down rather than requiring the user to retype the command with a flag.

### 9.2 Watch Mode UAT Shortcuts

When the UAT panel is focused in Watch mode:

```
  [Esc] back to overview
  [/]   search UAT logs
  [q]   back to REPL
```

These follow the focused agent view shortcuts from UX Design Section 5.3. The `[u]` key in the Watch mode overview switches focus to the UAT panel.

---

## 10. Help Integration

Following UX Design Section 7.3 (Contextual Help), the `/help` command surfaces UAT commands based on context.

**When UAT failures exist:**

```
autopilot [my-app] > /help

  COMMANDS (in current context: project active, session running)

  Most relevant right now:
    /ask list         1 question pending -- agents are blocked
    /uat run 042      1 UAT failure pending review
    /watch            Monitor agent activity live

  Quality:
    /uat coverage     Spec coverage: 46%
    /uat gaps         3 uncovered requirements in current phase
    /report quality   Quality trends over time

  Type /help uat for all UAT commands.
```

**UAT-specific help:**

```
autopilot [my-app] > /help uat

  UAT -- User Acceptance Testing against specifications

  Run tests:
    /uat run <id>       Test a single completed task
    /uat run --sprint N Test all completed tasks in sprint N
    /uat run --all      Test all completed tasks

  View results:
    /uat coverage       Spec coverage summary
    /uat gaps           Uncovered requirements
    /uat matrix         Full traceability matrix

  Maintenance:
    /uat config         Current UAT settings
    /uat rebuild-index  Rebuild spec index from source docs

  Examples:
    /uat run 042              Run UAT on task 42
    /uat gaps --phase 2       Show phase 2 gaps
    /uat matrix --export json Export matrix as JSON
    /uat run --sprint 3 -v    Verbose sprint report
```

---

## 11. Accessibility

Following UX Design Section 11 (Accessibility).

### 11.1 Requirements

- All UAT status indicators use both color AND text labels (never color alone)
- Score thresholds have text descriptions ("Excellent", "Good", "Needs Attention", "Critical") alongside numeric values
- Progress bars include numeric percentages alongside visual bars
- Screen reader compatibility: all Rich panels include meaningful titles
- High-contrast mode uses bold/normal weight and text-based fallback symbols instead of color (see Section 2.1 above)
- No time-limited interactions. UAT results persist and can be re-queried at any time.

### 11.2 Screen Reader Output

When `accessibility.screen-reader: true` (UX Design Section 11.2), UAT output omits box-drawing characters, progress bars, and color escapes:

**UAT result in screen reader mode:**

```
UAT Results for Task 042.
Score: 0.92, Good.
Overall: 12 of 13 tests passing, 1 failure.

Acceptance Criteria: 4 of 5 passing.
  Pass: Config model validates all fields per RFC 3.4.1.
  Pass: All tests associated with this task are passing.
  Pass: File complies with optimization guidelines.
  Pass: Pydantic models use strict validation.
  Fail: Default values match RFC specification.
    Expected: interval seconds equals 1800, per RFC Section 3.4.1.
    Actual: interval seconds equals 900.

Behavioral: 2 of 2 passing.
Specification Compliance: 6 of 6 passing.

Recommendation: Fix interval seconds default value, then re-run UAT.
```

**Coverage in screen reader mode:**

```
Specification Coverage, updated March 10, 2026.

RFC coverage:
  Section 3.1 Architecture Overview: 12 of 12, 100 percent.
  Section 3.2 Package Structure: 8 of 12, 67 percent.
  Section 3.3 Orchestration Flow: 2 of 15, 13 percent.
  Section 3.4 Data Model: 20 of 24, 83 percent.
  Section 3.5 Enforcement Engine: 0 of 30, 0 percent.

Overall: 101 of 218 requirements covered, 46.3 percent.
```

No box-drawing characters, no progress bars, no color escapes. Pure structured text with spelled-out numbers and percentages.

---

## 12. Recoverability

Following the design value "Recoverable by default" (UX Design Section 1):

### 12.1 Batch UAT Operations

- **Pause**: `Ctrl+Z` moves the batch UAT to background (accessible via `/jobs`).
- **Cancel**: `Ctrl+C` stops the batch. Tasks already assessed retain their results. Remaining tasks are marked as "not tested".
- **Resume**: After cancellation, `/uat run --sprint 3` detects previously completed assessments and only runs remaining tasks. It does not re-run passed tasks unless `--force` is specified.

### 12.2 Gated Mode Reversal

When gated mode reverts a task to IN PROGRESS, the developer can:
- Fix the issue and re-mark as complete (UAT re-triggers automatically)
- Override the gate: `/uat config set mode advisory` then re-mark complete
- Dispute the result: `/uat run 042 --force` to re-run UAT and get a fresh assessment

No UAT action is a one-way door.

---

## Appendix A: UAT Configuration Defaults

Following UX Design Appendix B (Configuration Defaults), UAT adds the following to `.autopilot/config.yaml`:

```yaml
# UAT configuration
uat:
  mode: "advisory"              # "advisory" | "gated"
  threshold: 0.90               # Minimum score to pass (gated mode only)
  auto_trigger: true            # Run UAT on task completion
  parallel_workers: 4           # Max concurrent UAT agents
  model: "sonnet"               # Model for UAT agents (cost optimization)
  timeout_seconds: 300          # 5-minute timeout per task UAT
  categories:
    acceptance: true
    behavioral: true
    compliance: true
    ux: true
```

These settings are editable via `/uat config` or directly in the YAML file.

## Appendix B: UAT Exit Codes

Following UX Design Appendix C (Exit Codes), UAT adds codes for one-shot CLI usage:

```
  CODE    MEANING
  ─────────────────────────────────────────────
  0       All UAT tests passed
  1       One or more UAT tests failed
  2       UAT pipeline error (not a test failure)
  3       No completed tasks found
  4       Spec index missing or corrupted
  10      Interrupted by user (Ctrl+C)
```

These codes are relevant for CI/CD integration or scripting. Within the REPL, exit codes are not surfaced -- the output formatting handles status communication.

## Appendix C: Command Quick Reference

```
  /uat run <id>                Run UAT on a single task
  /uat run <start>-<end>       Run UAT on a range of tasks
  /uat run --sprint <N>        Run UAT for a sprint
  /uat run --all               Run UAT on all completed tasks
  /uat coverage                Spec coverage summary
  /uat gaps                    Uncovered requirements
  /uat gaps --phase <N>        Gaps for a specific phase
  /uat matrix                  Full traceability matrix
  /uat matrix --export json    Export matrix as JSON
  /uat config                  Show UAT configuration
  /uat rebuild-index           Rebuild spec index
```

All commands support `--json` for scriptable output and `-v`/`--verbose` for detailed output.

---

*End of UX Notes*
