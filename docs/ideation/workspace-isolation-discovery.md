# Discovery: Workspace Isolation for Autonomous Sessions

## Problem Statement

The Autopilot CLI currently operates directly in the developer's project checkout. When running autonomous agent sessions, this creates conflicts between agent-generated changes and the developer's own work. Operators must manually clone fresh copies of repositories before starting sessions — a workflow that should be automated and managed by the tool itself.

### Current State
- `session start` launches agents that work in the project's existing directory
- `AgentInvoker` uses the project root as `cwd` for all subprocess calls
- `Scheduler` validates git state but does not isolate it
- `ProjectRegistry` stores project paths but not repository URLs
- No mechanism exists to create, track, or clean up temporary workspaces

### Pain Points
- Developer must manually `git clone` before each autonomous session
- Concurrent sessions on the same repo conflict on git state
- Agent failures can leave dirty files in the developer's working tree
- No isolation between agent work and developer work

## Proposed Solution

Implement a `WorkspaceManager` module that automates fresh repository cloning per session, with lifecycle management, configuration, and integration into the existing scheduler/daemon/session pipeline.

### Key Technical Decisions

- **Full clones over git worktrees**: Worktrees share `.git` directory creating contention; clones are fully isolated
- **Managed directory under `~/.autopilot/workspaces/`**: Central location, easy cleanup, gitignored from projects
- **Configurable via `workspace` config section**: Opt-in with `workspace.enabled: true`, backward-compatible
- **Cleanup policy**: Auto-cleanup on success, preserve on failure for debugging

## Architecture Overview

```
WorkspaceManager
  ├── create(project, session_id) -> WorkspaceInfo
  │     └── git clone <repo_url> ~/.autopilot/workspaces/<project>-<session-id>/
  ├── configure(workspace) -> None
  │     └── Copy .autopilot/ config, set up agent prompts
  ├── cleanup(workspace_id) -> None
  │     └── Remove workspace directory, update session metadata
  └── list_workspaces() -> list[WorkspaceInfo]
        └── Active and stale workspace inventory
```

### Integration Points
- `Scheduler.run_cycle()` calls `WorkspaceManager.create()` before dispatching agents
- `AgentInvoker` receives workspace path as `cwd`
- `SessionManager` stores workspace path in session metadata
- `Daemon.start()` creates workspace at session start
- `ProjectRegistry` extended with `repository_url` field
- CLI: `session cleanup` command for manual workspace management

## Architecture Decision Records

### ADR-011: Workspace Isolation via Fresh Repository Clones
- **Status**: Accepted
- **Decision**: Use full git clones into managed directories for workspace isolation
- **Consequences**: Disk usage increases but isolation is complete; backward-compatible via config flag

## Implementation Phases

### Phase 1: Core WorkspaceManager (Effort: medium, ~8-13 story points)

- [ ] `WorkspaceManager` class with create/cleanup/list operations
- [ ] `WorkspaceConfig` Pydantic model in config.py
- [ ] `WorkspaceInfo` data model for tracking workspace state
- [ ] Extend `ProjectRegistry` with `repository_url` field
- [ ] Git clone subprocess with depth and branch configuration
- [ ] Workspace directory structure creation and .autopilot config copying
- [ ] Tests for workspace lifecycle

### Phase 2: Pipeline Integration (Effort: medium, ~8-13 story points)

- [ ] Integrate `WorkspaceManager` into `Scheduler.run_cycle()`
- [ ] Update `AgentInvoker` to accept workspace `cwd` parameter
- [ ] Update `Daemon` to create workspace at session start
- [ ] Store workspace path in `SessionManager` metadata
- [ ] Handle workspace cleanup on session end (success/failure)
- [ ] Tests for integrated workspace flow

### Phase 3: CLI and Operations (Effort: small, ~5-8 story points)

- [ ] `session workspace list` CLI command
- [ ] `session workspace cleanup` CLI command (with --all, --stale flags)
- [ ] Stale workspace detection (orphaned workspaces from crashed sessions)
- [ ] Disk usage reporting for workspace directory
- [ ] Update `autopilot init` to prompt for repository URL
- [ ] Tests for CLI workspace commands

## Deferred Items

The following items are recognized but explicitly deferred to future iterations:

- **Clone caching**: Using `git clone --reference` from a local cached bare repo to speed up repeated clones of the same repository. The current `clone_depth` option provides adequate mitigation for startup latency. Clone caching will be revisited if clone times exceed the 30-second target for repos under 1GB.
- **Push-to-remote orchestration**: After agents complete work in a workspace, pushing branches to origin is currently the agent's responsibility (via git commands in the agent prompt). A future iteration may add explicit push orchestration to WorkspaceManager with retry logic and conflict resolution.

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Large repos take long to clone | Medium | Startup latency | Shallow clone option (`clone_depth`), cache recent clones |
| Disk space exhaustion | Medium | Sessions fail to start | `max_workspaces` limit, auto-cleanup, stale detection |
| Config divergence between source and workspace | Low | Agent uses wrong settings | Copy config at clone time, validate before session start |
| Push failures from workspace | Low | Work is lost | Preserve workspace on push failure, log for manual recovery |

## Success Metrics

- Session startup adds < 30s latency for repos under 1GB
- Zero git conflicts between developer work and agent work
- Workspaces auto-cleaned within 1 hour of successful session
- Stale workspace detection catches 100% of orphaned workspaces
