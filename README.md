# Autopilot CLI

A general-purpose autonomous development orchestrator. Autopilot CLI manages multi-agent development workflows with task management, anti-pattern enforcement, deployment monitoring, and interactive REPL — all from the terminal.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended)

## Installation

```bash
# Clone and install in development mode
git clone https://github.com/mandelbro/autopilot-cli.git
cd autopilot-cli
uv pip install -e ".[dev]"
```

## Usage

```bash
# Show help
autopilot --help

# Show version
autopilot --version
```

## Development

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/ tests/

# Type check
pyright
```

## Project Structure

```
src/autopilot/
  cli/           # Typer CLI application and display helpers
  core/          # Configuration (Pydantic), data models, project management
  coordination/  # Board management, question queue, announcements
  enforcement/   # Anti-pattern enforcement engine and rules
  monitoring/    # Deployment health checking
  orchestration/ # Agent dispatch and cycle management
  reporting/     # Metrics and reports
  utils/         # Shared utilities (subprocess, paths, git, sanitizer)
```

## Architecture

- **Configuration**: Pydantic v2 models with YAML I/O and three-level config merging (global, project, CLI)
- **Enforcement**: 11-category anti-pattern detection with 5 enforcement layers (editor, pre-commit, CI, guardrails, protected regions)
- **Coordination**: Document-mediated agent communication via markdown board files
- **CLI**: Typer + Rich for terminal UI with interactive REPL

## License

MIT
