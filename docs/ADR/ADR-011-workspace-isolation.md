# ADR-011: Workspace Isolation via Fresh Repository Clones

**Status**: Accepted
**Date**: 2026-03-14
**Authors**: Technical Architect
**Reviewers**: Project Lead

## Context

The current Autopilot CLI design (RFC Section 3.4.3, ADR-2) assumes agents work directly in the developer's existing project checkout. This creates several problems when using autopilot across multiple active projects or in production workflows:

1. **Developer working tree contamination**: Agent-generated changes (dirty files, branch switches, stashed work) interfere with the developer's own work in the same directory.
2. **Concurrent session conflicts**: Two daemons targeting the same repo checkout will conflict on git state (branches, locks, index).
3. **No rollback safety**: If an agent corrupts the working tree, the developer must manually recover.
4. **RepEngine friction**: When using autopilot for projects like RepEngine, the operator must manually clone fresh copies of the repository before starting sessions — this should be automated.
5. **CI analogy**: CI/CD systems universally use fresh checkouts per job. Autonomous agent sessions are analogous to CI jobs and should have the same isolation guarantees.

## Decision

Introduce a **WorkspaceManager** component that provides isolated, fresh repository clones for each active session:

1. When `session start` is invoked (or a daemon starts a cycle), the WorkspaceManager clones the project's repository into a managed temporary directory.
2. All agent work occurs in the cloned workspace, not the developer's checkout.
3. On session completion, results (branches, commits) are pushed to the remote, and the workspace is cleaned up.
4. On session failure, the workspace is preserved for debugging (configurable auto-cleanup).

### Workspace Lifecycle

```
session start
  -> WorkspaceManager.create(project) -> clone repo into ~/.autopilot/workspaces/<project>-<session-id>/
  -> Configure clone (.autopilot/ config copied from source)
  -> All agent invocations use workspace_dir as cwd
  -> On success: push branches to origin, cleanup workspace
  -> On failure: preserve workspace, log location for debugging
  -> On explicit cleanup: remove workspace directory
```

### Configuration

```yaml
workspace:
  enabled: true                    # false = legacy in-place mode
  base_dir: "~/.autopilot/workspaces"  # where clones live
  cleanup_on_success: true         # auto-remove after successful session
  cleanup_on_failure: false        # preserve for debugging
  clone_depth: 0                   # 0 = full clone, N = shallow
  max_workspaces: 5                # limit disk usage
```

### Integration Points

- `WorkspaceManager` is called by `Scheduler` at cycle start and by `Daemon` at session start.
- `AgentInvoker` receives the workspace directory as `cwd` instead of the project root.
- `SessionManager` tracks workspace paths in session metadata.
- `ProjectRegistry` stores the source repository URL for cloning.

## Consequences

### Positive
- Developers can continue working in their checkout while agents run autonomously.
- Multiple concurrent sessions for the same project are safe (each gets its own clone).
- Agent failures cannot corrupt the developer's working tree.
- Aligns with CI/CD best practices for reproducible, isolated execution.
- Enables future features like parallel branch experimentation.

### Negative
- Disk usage increases (each workspace is a full clone, mitigated by shallow clones and cleanup).
- Clone time adds latency to session startup (~5-30s depending on repo size).
- Configuration must handle the distinction between "source project" and "workspace directory."
- Existing code paths that assume `project_dir == cwd` need updating.

### Neutral
- The `workspace.enabled: false` flag preserves backward compatibility for users who prefer in-place mode.
- The `ProjectRegistry` needs a `repository_url` field to know where to clone from.

## Alternatives Considered

1. **Git worktrees** — Use `git worktree add` instead of full clones. Lighter on disk but shares the `.git` directory, creating contention risks. Also doesn't work if the source isn't a git repo.
2. **In-place with stash/restore** — Stash developer changes, run agents, restore. Fragile: stash conflicts, incomplete restores, no concurrent session support.
3. **Container-based isolation** — Run agents in Docker containers. Maximum isolation but adds Docker dependency and complexity far beyond what's needed.

## References

- RFC Section 3.4.3: Directory Layout Per Project
- RFC Section 4.4: Per-Project Daemons vs Single Daemon
- RFC Section 3.8: Error Recovery (Git state recovery)
- ADR-2: `.autopilot/` inside project root
- ADR-4: Per-project daemons
