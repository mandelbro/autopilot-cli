# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Test Commands

```bash
# Install dependencies
uv sync --extra dev

# Run all checks (lint + typecheck + test) — the default just target
just

# Individual commands
just test          # uv run pytest
just lint          # uv run ruff check --fix src/ tests/
just format        # uv run ruff format src/ tests/
just typecheck     # uv run pyright
just coverage      # pytest --cov=autopilot --cov-report=term-missing --cov-fail-under=80

# Run a single test file
uv run pytest tests/core/test_config.py

# Run a single test by name
uv run pytest -k "test_merge_missing_global"
```

The CLI entry point is `autopilot` (defined in `pyproject.toml` as `autopilot.cli.app:app`).

## Architecture

**autopilot-cli** is a Python 3.12+ CLI tool built with Typer + Rich that orchestrates autonomous multi-agent development workflows. It uses Pydantic v2 for all configuration and data models, structlog for logging, and YAML for config files.

### Domain Modules (`src/autopilot/`)

- **`core/`** — Configuration (`AutopilotConfig` with three-level YAML merge: global → project → CLI), data models (Pydantic), task management, sprint planning, session lifecycle, project registry, agent registry, and Jinja2-based templates
- **`cli/`** — Typer application with subcommand groups (`task`, `session`, `enforce`, `project`, `sprint`, `report`, `agent`, `config`). Running with no args enters an interactive REPL (`prompt-toolkit`). Display helpers use Rich
- **`orchestration/`** — Scheduler (interval/event/hybrid strategies), Daemon (background session runner), AgentInvoker (subprocess-based agent dispatch), Dispatcher (plan parsing), CircuitBreaker, UsageTracker, HiveMind consensus
- **`enforcement/`** — Anti-pattern detection engine with 11 rule categories in `rules/` (duplication, conventions, overengineering, security, error_handling, dead_code, type_safety, test_quality, comments, deprecated, async_misuse). All rules extend `rules/base.py`. Enforcement runs across 5 layers: editor-time, pre-commit, CI, guardrails, protected regions. Uses `ruff_runner.py` for delegating to ruff
- **`coordination/`** — Document-mediated agent communication via markdown board files (`board.py`), question queues, decision tracking, announcements
- **`monitoring/`** — Deployment health checking for services (Render integration, health endpoints)
- **`reporting/`** — Cycle reports, velocity metrics, daily summaries, decision logs
- **`uat/`** — User acceptance testing pipeline: spec indexing, test generation, test execution, traceability matrix, reporting
- **`utils/`** — Subprocess runner, path resolution (`find_autopilot_dir`, `get_global_dir`), git helpers, input sanitizer, SQLite database wrapper

### Key Patterns

- **Frozen Pydantic models** — All config models use `ConfigDict(frozen=True)` for immutability
- **Three-level config merge** — `AutopilotConfig.merge(global_path, project_path)` with `_deep_merge` for nested dict override
- **Project layout** — autopilot stores state in `.autopilot/` within the project root (subdirs: `agents/`, `board/`, `tasks/`, `state/`, `logs/`, `enforcement/`)
- **Test fixtures** — `tests/conftest.py` provides `project_dir`, `autopilot_dir`, and `global_dir` fixtures using `tmp_path`

### Tooling

- **Package manager**: `uv` with `hatchling` build backend
- **Linting**: ruff (rules: E, F, W, I, N, UP, B, SIM, TCH; line-length 100; E501 ignored)
- **Type checking**: pyright in `standard` mode (only checks `src/`, excludes `tests/`)
- **Testing**: pytest with `src` on pythonpath, verbose output, short tracebacks

## Task Workflow

Tasks are tracked in `tasks/` directory. See @.claude/knowledge/workflows/tasks-workflow.md for the full workflow. Key points:
- `tasks/tasks-index.md` is the index with overall progress
- `tasks/tasks-N.md` files contain individual tasks (max 10 per file, <500 lines)
- After completing a task: run tests, run lint/typecheck, mark `Complete: [x]`, update index counts
