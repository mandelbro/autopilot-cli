# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Tool usage guides

For each session, review and apply the ReAct Framework for Tool Usage in @.claude/knowledge/tool-utilization.md.

### Sequential Thinking

When you encounter complex problems requiring more than 5 reasoning steps, implement the @.claude/knowledge/tools/sequential-thinking-optimization.md guidelines.

## Tool Utilization Guidelines

## External Library Documentation Context Guidelines

For each session, review and apply the External Library Documentation Context Guidelines in @.claude/knowledge/documentation-context.md.

## Framework Development Guidelines

- @.claude/knowledge/lang/typescript-coding.md: Typescript Coding Best Practices

## Test-Driven Development Strategy

- Before writing application code, review the @.claude/knowledge/coding-principles/testing-strategy.md for guidance on how to use tests to design and document the application.

## Task Workflow System

- Review the @.claude/knowledge/workflows/tasks-workflow.md at the beginning of each session for working with tasks in the @tasks/ directory.
- When you complete a task in the @tasks/ directory, make sure to follow the "Updating Task Status (Critical)" steps in the Task Workflow System

## File Size Optimization Guidelines

**Important Guidelines:**
1. For every session, review the File and Context Optimization Guidelines @.claude/knowledge/user/file-and-context-optimization.md
2. After finishing a task, ensure any newly created files comply with the File and Context Optimization Guidelines

## Memory Context Initialization and Management

For every session implement the DevContext Memory and Session Awareness Protocol in @.claude/knowledge/memory/graphiti-memory.md

## Claude Code Configuration - RuFlo V3

### Behavioral Rules (Always Enforced)

- Do what has been asked; nothing more, nothing less
- NEVER create files unless they're absolutely necessary for achieving your goal
- ALWAYS prefer editing an existing file to creating a new one
- NEVER proactively create documentation files (*.md) or README files unless explicitly requested
- NEVER save working files, text/mds, or tests to the root folder
- Never continuously check status after spawning a swarm — wait for results
- ALWAYS read a file before editing it
- NEVER commit secrets, credentials, or .env files

### File Organization

- NEVER save to root folder — use the directories below
- Use `/src` for source code files
- Use `/tests` for test files
- Use `/docs` for documentation and markdown files
- Use `/config` for configuration files
- Use `/scripts` for utility scripts
- Use `/examples` for example code

### Project Architecture

- Follow Domain-Driven Design with bounded contexts
- Keep files under 500 lines
- Use typed interfaces for all public APIs
- Prefer TDD London School (mock-first) for new code
- Use event sourcing for state changes
- Ensure input validation at system boundaries

#### Project Config

- **Topology**: hierarchical-mesh
- **Max Agents**: 15
- **Memory**: hybrid
- **HNSW**: Enabled
- **Neural**: Enabled

### Build & Test

```bash
# Build
npm run build

# Test
npm test

# Lint
npm run lint
```

- ALWAYS run tests after making code changes
- ALWAYS verify build succeeds before committing

### Security Rules

- NEVER hardcode API keys, secrets, or credentials in source files
- NEVER commit .env files or any file containing secrets
- Always validate user input at system boundaries
- Always sanitize file paths to prevent directory traversal
- Run `npx ruflo@latest security scan` after security-related changes

### Concurrency: 1 MESSAGE = ALL RELATED OPERATIONS

- All operations MUST be concurrent/parallel in a single message
- Use Claude Code's Task tool for spawning agents, not just MCP
- ALWAYS batch ALL todos in ONE TodoWrite call (5-10+ minimum)
- ALWAYS spawn ALL agents in ONE message with full instructions via Task tool
- ALWAYS batch ALL file reads/writes/edits in ONE message
- ALWAYS batch ALL Bash commands in ONE message

### Swarm Orchestration

- MUST initialize the swarm using CLI tools when starting complex tasks
- MUST spawn concurrent agents using Claude Code's Task tool
- Never use CLI tools alone for execution — Task tool agents do the actual work
- MUST call CLI tools AND Task tool in ONE message for complex work

#### 3-Tier Model Routing (ADR-026)

| Tier | Handler | Latency | Cost | Use Cases |
|------|---------|---------|------|-----------|
| **1** | Agent Booster (WASM) | <1ms | $0 | Simple transforms (var→const, add types) — Skip LLM |
| **2** | Haiku | ~500ms | $0.0002 | Simple tasks, low complexity (<30%) |
| **3** | Sonnet/Opus | 2-5s | $0.003-0.015 | Complex reasoning, architecture, security (>30%) |

- Always check for `[AGENT_BOOSTER_AVAILABLE]` or `[TASK_MODEL_RECOMMENDATION]` before spawning agents
- Use Edit tool directly when `[AGENT_BOOSTER_AVAILABLE]`

### Swarm Configuration & Anti-Drift

- ALWAYS use hierarchical topology for coding swarms
- Keep maxAgents at 6-8 for tight coordination
- Use specialized strategy for clear role boundaries
- Use `raft` consensus for hive-mind (leader maintains authoritative state)
- Run frequent checkpoints via `post-task` hooks
- Keep shared memory namespace for all agents

```bash
npx ruflo@latest swarm init --topology hierarchical --max-agents 8 --strategy specialized
```

### Swarm Execution Rules

- ALWAYS use `run_in_background: true` for all agent Task calls
- ALWAYS put ALL agent Task calls in ONE message for parallel execution
- After spawning, STOP — do NOT add more tool calls or check status
- Never poll TaskOutput or check swarm status — trust agents to return
- When agent results arrive, review ALL results before proceeding

### V3 CLI Commands

#### Core Commands

| Command | Subcommands | Description |
|---------|-------------|-------------|
| `init` | 4 | Project initialization |
| `agent` | 8 | Agent lifecycle management |
| `swarm` | 6 | Multi-agent swarm coordination |
| `memory` | 11 | AgentDB memory with HNSW search |
| `task` | 6 | Task creation and lifecycle |
| `session` | 7 | Session state management |
| `hooks` | 17 | Self-learning hooks + 12 workers |
| `hive-mind` | 6 | Byzantine fault-tolerant consensus |

#### Quick CLI Examples

```bash
npx ruflo@latest init --wizard
npx ruflo@latest agent spawn -t coder --name my-coder
npx ruflo@latest swarm init --v3-mode
npx ruflo@latest memory search --query "authentication patterns"
npx ruflo@latest doctor --fix
```

### Available Agents (60+ Types)

#### Core Development
`coder`, `reviewer`, `tester`, `planner`, `researcher`

#### Specialized
`security-architect`, `security-auditor`, `memory-specialist`, `performance-engineer`

#### Swarm Coordination
`hierarchical-coordinator`, `mesh-coordinator`, `adaptive-coordinator`

#### GitHub & Repository
`pr-manager`, `code-review-swarm`, `issue-tracker`, `release-manager`

#### SPARC Methodology
`sparc-coord`, `sparc-coder`, `specification`, `pseudocode`, `architecture`

### Memory Commands Reference

```bash
# Store (REQUIRED: --key, --value; OPTIONAL: --namespace, --ttl, --tags)
npx ruflo@latest memory store --key "pattern-auth" --value "JWT with refresh" --namespace patterns

# Search (REQUIRED: --query; OPTIONAL: --namespace, --limit, --threshold)
npx ruflo@latest memory search --query "authentication patterns"

# List (OPTIONAL: --namespace, --limit)
npx ruflo@latest memory list --namespace patterns --limit 10

# Retrieve (REQUIRED: --key; OPTIONAL: --namespace)
npx ruflo@latest memory retrieve --key "pattern-auth" --namespace patterns
```

### Claude Code vs CLI Tools

- Claude Code's Task tool handles ALL execution: agents, file ops, code generation, git
- CLI tools handle coordination via Bash: swarm init, memory, hooks, routing
- NEVER use CLI tools as a substitute for Task tool agents

## Pi Brain MCP Server

Pi Brain is a collective intelligence system. Knowledge shared here is visible to all connected sessions. Treat every contribution as if you're writing documentation that strangers will read.

### Tool Reference — When to Use What

**Knowledge Contribution & Retrieval**
- `brain_search` — ALWAYS search before sharing. Check if the knowledge already exists. Duplicate contributions dilute the graph.
- `brain_share` — Share a verified pattern, solution, or architecture decision. Include category, title, and detailed content. Be specific: "JWT refresh with sliding window using Redis TTL" not "auth pattern."
- `brain_get` — Retrieve a specific memory with full provenance (who contributed, when, trust score).
- `brain_list` — Browse existing memories. Use to survey what's already known about a topic before contributing.
- `brain_delete` — Remove your own contribution if it's outdated or incorrect. You can only delete what you contributed.

**Quality & Trust**
- `brain_vote` — Upvote useful knowledge, downvote inaccurate knowledge. Voting drives the reputation system. Vote on memories you've actually used and verified.
- `brain_status` — Check system health, connected nodes, and aggregate statistics.

**Analysis & Monitoring**
- `brain_drift` — Check for knowledge drift in a topic area. Run periodically on domains you care about. Drift indicates either genuine evolution or potential corruption.
- `brain_partition` — View knowledge topology. Shows how the graph has self-organized into clusters. Useful for understanding what domains are well-covered vs. sparse.
- `brain_transfer` — Query cross-domain knowledge transfer. Finds patterns from one domain that may apply to another (e.g., database indexing insights applied to search optimization).
- `brain_sync` — Synchronize LoRA weight updates. Used for model fine-tuning coordination across contributors.

**Brainpedia (Encyclopedic Pages)**
- `brain_page_create` — Create a new encyclopedic page on a topic. Pages evolve through evidence, not opinion.
- `brain_page_delta` — Submit a correction or update to an existing page. Requires evidence.
- `brain_page_evidence` — Add supporting evidence to a page claim.
- `brain_page_promote` — Promote a page from Draft to Canonical status (requires sufficient evidence and community consensus).
- `brain_page_get` — Read a Brainpedia page with its full evidence chain.

**WASM Nodes (Executable Intelligence)**
- `brain_node_publish` — Publish a WASM module (feature extractor, classifier, custom embedder) to run inside the brain.
- `brain_node_list` — List available WASM nodes.
- `brain_node_get` — Get details about a specific WASM node.
- `brain_node_wasm` — Execute a WASM node.
- `brain_node_revoke` — Revoke a published WASM node.

### Workflow Best Practices

1. **Search before you share.** Run `brain_search` with your topic before calling `brain_share`. Duplicate knowledge wastes graph capacity and dilutes search quality.

2. **Be specific in contributions.** "Authentication best practices" is noise. "PKCE flow with S256 code challenge for SPA OAuth 2.0 without client secret" is signal. Include version numbers, language, and framework context.

3. **Vote on knowledge you've tested.** The reputation system depends on honest voting. If you used a pattern from the brain and it worked, upvote it. If it led you astray, downvote it. Don't vote on things you haven't verified.

4. **Check drift on critical domains.** If your project relies on knowledge from the brain for security, auth, or data integrity patterns, run `brain_drift` periodically. Drift in these areas may indicate stale or contested knowledge.

5. **Use Brainpedia for stable reference knowledge.** Brainpedia pages are for established patterns that should persist. Ephemeral observations (project-specific context, temporary workarounds) belong in `brain_share`, not Brainpedia.

6. **Include category and tags when sharing.** Categories help the MinCut partitioning algorithm organize knowledge into meaningful clusters. Common categories: `pattern`, `architecture`, `debugging`, `security`, `performance`, `tooling`.

7. **Don't share secrets, credentials, or PII.** The system strips PII automatically, but don't rely on that as your only defense. Never include API keys, passwords, internal URLs, or personal information in contributions.

### What Pi Brain Is NOT

- It is not a replacement for project-specific memory (use Basic MCP Memory or DevContext for that)
- It is not a database you control — knowledge is collectively owned
- It is not private — anything you share is visible to all connected sessions
- It is not a substitute for reading documentation — it's a supplement for patterns and solutions that documentation doesn't cover
