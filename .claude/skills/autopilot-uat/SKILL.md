---
name: "autopilot-uat"
description: "Run User Acceptance Testing against task specifications. Verifies that implemented tasks meet their acceptance criteria, match RFC/discovery/UX design requirements, and maintains a traceability matrix mapping tasks to specification sections. Invoke as /autopilot-uat."
version: "1.0.0"
category: "testing"
tags: ["uat", "acceptance-testing", "traceability", "specification-compliance", "quality-gates"]
---

# Autopilot UAT Skill

## What This Skill Does

The `/autopilot-uat` skill runs User Acceptance Testing against completed tasks, verifying that implementations match their acceptance criteria and the project's RFC, discovery, and UX design specifications. It generates four categories of tests (acceptance, behavioral, specification compliance, and UX compliance), maintains a traceability matrix mapping every task to the spec sections it implements, and produces per-task and sprint-level UAT reports with pass/fail scores. UAT runs in parallel alongside development via claude-flow swarm coordination, catching specification drift per-task rather than after the fact.

## Prerequisites

- Python 3.11+ with pytest installed
- Autopilot CLI project with task files in `tasks/` directory
- Specification documents in `docs/ideation/` (RFC.md, discovery.md, ux-design.md)
- claude-flow installed (`npx claude-flow@alpha`) for swarm-based parallel execution

## Quick Start

```bash
# Run UAT on a single completed task
/autopilot-uat 042

# Run UAT on a range of tasks
/autopilot-uat 040-050

# Run UAT on all completed tasks in a sprint
/autopilot-uat --sprint 3

# Generate the traceability matrix
/autopilot-uat matrix

# View specification coverage report
/autopilot-uat coverage
```

---

## Detailed Usage

### Single Task UAT

Run acceptance testing against a specific completed task:

```bash
# Basic single-task UAT
/autopilot-uat 042

# Verbose output with full test details
/autopilot-uat 042 --verbose

# Generate tests without executing them
/autopilot-uat 042 --dry-run

# Re-run UAT after fixing failures
/autopilot-uat 042 --rerun
```

The UAT pipeline for a single task:
1. Loads task context from `tasks/tasks-N.md` (user story, acceptance criteria, file path, spec references)
2. Cross-references the task against RFC, discovery, and UX design specifications
3. Generates pytest test cases in four categories (acceptance, behavioral, compliance, UX)
4. Executes tests and collects results
5. Produces a scored report with pass/fail per criterion

### Sprint UAT

Run UAT across all completed tasks in a sprint:

```bash
# UAT for current sprint
/autopilot-uat --sprint current

# UAT for a specific sprint by number
/autopilot-uat --sprint 3

# Parallel execution via swarm (recommended for >5 tasks)
/autopilot-uat --sprint 3 --parallel --max-agents 4
```

### Traceability Matrix

Generate and view the specification traceability matrix:

```bash
# Generate full traceability matrix
/autopilot-uat matrix

# View coverage for a specific RFC section
/autopilot-uat matrix --section "3.5"

# Export matrix as JSON
/autopilot-uat matrix --format json --output traceability.json

# Show unmapped specifications (spec requirements with no task)
/autopilot-uat matrix --unmapped
```

### Specification Coverage

View how much of each specification document is covered by completed tasks:

```bash
# Full coverage report
/autopilot-uat coverage

# Coverage for specific document
/autopilot-uat coverage --doc rfc
/autopilot-uat coverage --doc discovery
/autopilot-uat coverage --doc ux

# Coverage by phase
/autopilot-uat coverage --phase 2
```

### Configuration Options

Configure UAT behavior in `.autopilot/uat.yaml`:

```yaml
uat:
  # Score threshold for pass/fail (0.0-1.0)
  pass_threshold: 0.85

  # Quality gate: block task completion on UAT failure
  quality_gate: true

  # Test categories to run
  categories:
    acceptance: true
    behavioral: true
    compliance: true
    ux: true

  # Parallel execution settings
  parallel:
    enabled: true
    max_agents: 4
    topology: hierarchical

  # Specification document paths
  specs:
    rfc: docs/ideation/RFC.md
    discovery: docs/ideation/discovery.md
    ux_design: docs/ideation/ux-design.md

  # Test output directory
  test_output: tests/uat/
```

### Custom Test Patterns

Add project-specific UAT patterns:

```bash
# Register a custom compliance check
/autopilot-uat pattern add --name "sqlite-wal" \
  --spec "RFC 3.4.2" \
  --check "SQLite uses WAL mode for concurrent access"

# List registered patterns
/autopilot-uat pattern list

# Remove a pattern
/autopilot-uat pattern remove --name "sqlite-wal"
```

### Batch Execution

Run UAT across multiple tasks with swarm coordination:

```bash
# Batch UAT on all completed tasks
/autopilot-uat --all --parallel

# Batch with custom agent count
/autopilot-uat --all --parallel --max-agents 6

# Batch with JSON report output
/autopilot-uat --all --format json --output uat-report.json
```

---

## Reference

### Test Categories

| Category | Source | What It Verifies |
|----------|--------|------------------|
| Acceptance | Task prompt acceptance criteria | Each `- [ ]` criterion in the task prompt becomes a test |
| Behavioral | Task user story | User-facing behavior described in "As a... I want... so that..." |
| Compliance | RFC and discovery sections | Implementation matches technical specification details |
| UX | UX design document | CLI output, REPL behavior, and UI constraints match UX spec |

### UAT Result Schema

UAT results follow the schema defined in `resources/schemas/uat-result.schema.json`. Key fields:

- `task_id`: The task under test
- `score`: Composite score (0.0-1.0)
- `overall_pass`: Whether score meets the configured threshold
- `categories`: Per-category results (acceptance, behavioral, compliance, ux)
- `test_count`, `pass_count`, `fail_count`, `skip_count`: Test execution counts
- `failures`: Detailed failure information with spec references and fix suggestions

### Traceability Matrix Schema

The traceability matrix follows `resources/schemas/traceability-matrix.schema.json`. Key fields:

- `task_id`: The mapped task
- `rfc_sections`: RFC sections this task implements
- `discovery_requirements`: Discovery requirements covered
- `ux_elements`: UX design elements addressed
- `coverage_score`: How much of the mapped spec is covered (0.0-1.0)

### Score Interpretation

| Score Range | Meaning | Action |
|-------------|---------|--------|
| 0.95-1.0 | Excellent | Task fully meets specification |
| 0.85-0.94 | Good | Minor gaps, review recommended |
| 0.70-0.84 | Warning | Significant specification drift, fix required |
| < 0.70 | Critical | Task does not meet specification, revert to IN PROGRESS |

### Exit Codes

- `0`: All UAT tests passed (score >= threshold)
- `1`: UAT tests failed (score < threshold)
- `2`: Error during UAT execution (invalid task ID, missing spec files)

### Troubleshooting

**"Task not found" error:**
Ensure the task ID exists in `tasks/tasks-index.md` and the corresponding `tasks/tasks-N.md` file is present.

**"No spec references found" warning:**
The task prompt does not contain explicit RFC/discovery/UX references. UAT will fall back to keyword matching. Add explicit spec references to the task prompt for better traceability.

**Low coverage scores:**
Run `/autopilot-uat matrix --unmapped` to identify specification sections with no task mapping. These may need new tasks created to cover them.

**Parallel execution failures:**
Ensure claude-flow is installed and the swarm can initialize. Run `npx claude-flow@alpha swarm init --topology hierarchical --max-agents 4` to verify.

### Related Skills

- `verification-quality`: Code-level truth scoring and verification (complements UAT's spec-level checks)
- `swarm-orchestration`: Multi-agent coordination for parallel UAT execution
- `hooks-automation`: Automatic UAT triggering via post-task hooks

### Directory Structure

```
.claude/skills/autopilot-uat/
  SKILL.md                          # This file
  scripts/                          # UAT execution scripts
  resources/
    templates/                      # Test generation templates
    schemas/
      traceability-matrix.schema.json  # Traceability matrix JSON schema
      uat-result.schema.json           # UAT result JSON schema
```
