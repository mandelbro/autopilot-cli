## Overall Project Task Summary

- **Total Tasks**: 21
- **Pending**: 1
- **Complete**: 20
- **Total Points**: 49
- **Points Complete**: 47

## Project: Debugging Agent with Plugin Architecture

- Task Source File: `docs/ideation/debugging-agent-plugin-architecture-discovery.md`
- **Description**: Add an autonomous debugging agent to autopilot-cli that tests acceptance criteria against live environments, diagnoses failures, fixes code, drafts regression tests, and performs UX review. Debugging tool backends (Browser MCP for web apps, Desktop Agent for native apps) ship as plugins behind a `DebuggingTool` Protocol. Includes CLI management commands, config integration, and orchestration pipeline hooks. Total: 36 discovery points across 8 phases, decomposed into 21 implementation tasks (49 points with TDD overhead).

## Task File Index

- `tasks/debugging-agent-plugin-architecture/tasks-1.1.md`: Contains Tasks 001 - 005 (5 tasks, 11 points) -- Phase 1: Core Models & Protocol, Phase 2 Start: Pipeline Support Functions
- `tasks/debugging-agent-plugin-architecture/tasks-1.2.md`: Contains Tasks 006 - 010b (6 tasks, 12 points) -- Phase 2: Plugin Loader, Phase 3a: Browser MCP Core, Phase 3b: Browser MCP Diagnostics & UX
- `tasks/debugging-agent-plugin-architecture/tasks-2.1.md`: Contains Tasks 011 - 014-1 (5 tasks, 13 points) -- Phase 4a: CLI Integration, Phase 4b: Agent Integration, Result Collection
- `tasks/debugging-agent-plugin-architecture/tasks-2.2.md`: Contains Tasks 015 - 019 (5 tasks, 13 points) -- Phase 5: Desktop Agent Plugin, Phase 6: Orchestration Integration, Documentation

## Phase Mapping

| Phase | Description | Task IDs | Discovery Points | Task Points |
|-------|-------------|----------|-----------------|-------------|
| 1 | Core Models & Plugin Protocol | 001-004 | 5 | 8 |
| 2 | Pipeline Support Functions & Plugin Loader | 005-007 | 5 | 7 |
| 3a | Browser MCP Plugin -- Core | 008, 010a | 5 | 4 |
| 3b | Browser MCP Plugin -- Diagnostics & UX | 009, 010b | 5 | 4 |
| 4a | CLI Integration -- Commands | 011-013 | 5 | 8 |
| 4b | Agent Integration + Result Collection | 014, 014-1 | 3 | 5 |
| 5 | Desktop Agent Plugin | 015-017 | 5 | 8 |
| 6a | Orchestration Integration | 018 | 3 | 3 |
| 6b | Documentation | 019 | — | 2 |

## Sprint Grouping Recommendation

| Sprint | Tasks | Points | Theme |
|--------|-------|--------|-------|
| 1 | 001-007 | 15 | Foundation: Protocol + Models + Config + Pipeline + Loader + Tests |
| 2 | 008-010b, 011-012 | 14 | Browser MCP Plugin + CLI Core + Plugin Mgmt |
| 3 | 013, 014, 014-1, 015-017 | 15 | CLI Tests + Agent Integration + Desktop Plugin |
| 4 | 018-019 | 5 | Orchestration Integration + Documentation |

Sprint 2: 3+1+3+1+3+3 = 14. Sprint 3: 2+3+2+3+3+2 = 15. Sprint 4 is lightweight — can be combined with Sprint 3 if capacity allows (total would be 20).

## Architecture Decision Records

Implementations must follow these ADRs from the discovery document:

- **ADR-D01**: `typing.Protocol` with `@runtime_checkable` for `DebuggingTool` interface; config-based plugin registration with CLI management commands
- **ADR-D02**: Synchronous protocol methods; async plugins manage their own event loop internally via `asyncio.run()`
- **ADR-D03**: Debugging agent is a standard LLM-orchestrated agent (`.md` prompt, `AgentRegistry`, `AgentInvoker`)
- **ADR-D04**: Guardrails via tool responses + system prompt + post-run validation (not code-controlled pipeline)
- **ADR-D05**: Config mutation via load-modify-save pattern (never mutate frozen models)
- **ADR-D06**: Two-tier test strategy (unit tests always, integration tests guarded by `AUTOPILOT_INTEGRATION_TESTS=1`)
- **ADR-D07**: Protocol versioning via `PROTOCOL_VERSION` module-level constant
