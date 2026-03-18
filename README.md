# Autopilot CLI

[![PyPI version](https://img.shields.io/pypi/v/autopilot-cli.svg)](https://pypi.org/project/autopilot-cli/)
[![Python 3.12+](https://img.shields.io/pypi/pyversions/autopilot-cli.svg)](https://pypi.org/project/autopilot-cli/)
[![CI](https://github.com/mandelbro/autopilot-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/mandelbro/autopilot-cli/actions/workflows/ci.yml)
[![License](https://img.shields.io/pypi/l/autopilot-cli.svg)](https://github.com/mandelbro/autopilot-cli/blob/main/LICENSE)

Autonomous multi-agent development orchestrator. Autopilot CLI manages multi-agent development workflows with task management, anti-pattern enforcement, hive-mind coordination, deployment monitoring, and interactive REPL — all from the terminal.

## Features

- **Task Management** — Sprint planning, task tracking, and velocity reporting with Fibonacci point estimation
- **Anti-Pattern Enforcement** — 11-category detection engine across 5 enforcement layers (editor, pre-commit, CI, guardrails, protected regions)
- **Hive-Mind Orchestration** — Spawn multi-agent sessions via claude-flow with Jinja2 objective templates, resource gating, and session tracking
- **Agent Coordination** — Document-mediated communication via markdown board files, question queues, and decision tracking
- **Session Lifecycle** — Daemon-based autonomous sessions with usage quotas, circuit breakers, and workspace isolation
- **Deployment Monitoring** — Health checking for services with Render integration
- **Interactive REPL** — Rich terminal UI with prompt-toolkit and command history
- **Configuration** — Pydantic v2 models with three-level YAML merge (global, project, CLI)

## Installation

```bash
pip install autopilot-cli
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv pip install autopilot-cli
```

Requires Python 3.12+.

## Quick Start

```bash
# Initialize a project
autopilot init --name my-project

# Start an autonomous session
autopilot start

# Run a single cycle
autopilot cycle

# Enter interactive REPL
autopilot

# Show all commands
autopilot --help
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `autopilot init` | Initialize a new project |
| `autopilot start` | Start an autonomous session daemon |
| `autopilot stop` | Stop the running session |
| `autopilot cycle` | Run a single scheduler cycle |
| `autopilot watch` | Live dashboard |
| `autopilot task` | Task management and sprint planning |
| `autopilot session` | Session lifecycle (start, stop, pause, resume, list) |
| `autopilot enforce` | Anti-pattern enforcement engine |
| `autopilot hive` | Hive-mind orchestration (spawn, status, stop) |
| `autopilot project` | Project registry management |
| `autopilot config` | Configuration management |
| `autopilot report` | Reporting and analytics |

## Development

This project uses [just](https://github.com/casey/just) as a task runner and [uv](https://docs.astral.sh/uv/) for package management.

### Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- [just](https://github.com/casey/just)

### Setup

```bash
git clone https://github.com/mandelbro/autopilot-cli.git
cd autopilot-cli
asdf install # installs python, uv, and just
just init
```

### Running locally

```bash
# Run the CLI via just (pass args after --)
just run -- --help
just run -- init --name my-project
just run -- hive spawn tasks/tasks-1.md --task-ids 001-008 --dry-run

# Or directly with uv
uv run autopilot --help
```

### Commands

```bash
# Run all checks (format, lint, typecheck, test)
just

# Individual commands
just test          # uv run pytest
just lint          # uv run ruff check --fix src/ tests/
just format        # uv run ruff format src/ tests/
just typecheck     # uv run pyright
just coverage      # pytest --cov --cov-fail-under=80
```

## Project Structure

```
src/autopilot/
  cli/           # Typer CLI application and display helpers
  core/          # Configuration (Pydantic), data models, project management
  coordination/  # Board management, question queue, announcements
  enforcement/   # Anti-pattern enforcement engine and rules
  monitoring/    # Deployment health checking
  orchestration/ # Agent dispatch, scheduling, hive-mind coordination
  reporting/     # Metrics and reports
  uat/           # User acceptance testing pipeline
  utils/         # Shared utilities (subprocess, paths, git, sanitizer)
```

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.
