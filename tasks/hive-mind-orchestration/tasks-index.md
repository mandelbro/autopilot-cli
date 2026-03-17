## Overall Project Task Summary

- **Total Tasks**: 17
- **Pending**: 14
- **Complete**: 3
- **Total Points**: 22
- **Points Complete**: 4

## Project: Hive-Mind Orchestration Integration

- Task Source File: `docs/discovery/hive-mind-orchestration.md`
- **Description**: Replace autopilot's current swarm-init-plus-individual-spawn workflow with a single `hive-mind spawn` command that batches tasks, runs quality gates, creates PRs, and loops through code review autonomously. Evolves the `HiveMindManager`, adds `HiveObjectiveBuilder` with Jinja2 templates, new `autopilot hive` CLI commands, and integration wiring with existing orchestration infrastructure. Total: 22 discovery points across 6 phases.

## Task File Index

- `tasks/hive-mind-orchestration/tasks-1.md`: Contains Tasks 001 - 007 (7 tasks, 10 points) -- Phase 1: Config & Models, Phase 2: Objective Template System
- `tasks/hive-mind-orchestration/tasks-2.1.md`: Contains Tasks 008 - 013 (6 tasks, 8 points) -- Phase 3: HiveMindManager Evolution, Phase 4: CLI Commands, Phase 5a: Integration Wiring
- `tasks/hive-mind-orchestration/tasks-2.2.md`: Contains Tasks 014 - 017 (4 tasks, 4 points) -- Phase 5b: Test Coverage

## Phase Mapping

| Phase | Description | Task IDs | Discovery Points | Task Points |
|-------|-------------|----------|-----------------|-------------|
| 1 | Configuration and Models | 001-003 | 3 | 4 |
| 2 | Objective Template System | 004-007 | 5 | 6 |
| 3 | HiveMindManager Evolution | 008-009 | 3 | 3 |
| 4 | CLI Commands | 010-011 | 3 | 3 |
| 5a | Integration Wiring | 012-013 | 3 | 2 |
| 5b | Test Coverage | 014-017 | 5 | 4 |

## Sprint Grouping Recommendation

| Sprint | Tasks | Points | Theme |
|--------|-------|--------|-------|
| 1 | 001-007 | 10 | Foundation: Config + Models + Template System |
| 2 | 008-017 | 12 | Manager Evolution + CLI + Integration + Tests |

## Architecture Decision

Implementations must follow **Option 1: Thin Wrapper** from the discovery document:
- Autopilot builds the objective prompt via Jinja2 templates
- Calls `hive-mind spawn` once
- Monitors the process
- The hive-mind handles batch grouping, PR creation, code review loops, and merging internally via the objective prompt instructions

## Key Design Constraints

- **`npx ruflo@latest`**: Always use `@latest` (not pinned version) for `hive-mind spawn` to ensure subcommand availability
- **`--claude` mode**: Process blocks for hours; use `subprocess.Popen` (non-blocking) with PID tracking
- **No structured output**: ruflo returns plaintext only; results are derived from exit code + git state
- **Frozen Pydantic models**: All config models use `ConfigDict(frozen=True)`
- **`render_to_string`**: New method on `TemplateRenderer` for string output (existing `render_to` writes to filesystem)
- **`_active_processes`**: Popen objects stored on `HiveMindManager._active_processes` dict (not in `HiveSession.metadata`) — Popen is not serializable
- **API signatures**: `ResourceBroker.can_spawn_agent(project) -> tuple[bool, str]`; `UsageTracker.record_cycle(project)`; `SessionManager.create_session(project, session_type, agent_name, *, pid, cycle_id) -> Session`

## Deferred Integration Work

The following discovery document Phase 5a integrations are **not covered** by current tasks and are deferred to a future sprint:

- **HookRunner integration**: `run_hooks("pre_hive" / "post_hive")` lifecycle hooks (discovery lines 672-673)
- **CircuitBreaker integration**: Circuit-breaking for consecutive hive-mind failures (discovery lines 674-675)
- **SessionManager metadata extension**: Adding `metadata: dict[str, Any]` parameter to `SessionManager.create_session()` for storing namespace/task_file/task_ids
