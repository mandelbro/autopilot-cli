# Autopilot CLI

A general-purpose autonomous development orchestrator. Autopilot CLI manages multi-agent development workflows with task management, anti-pattern enforcement, deployment monitoring, and interactive REPL — all from the terminal.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- [just](https://github.com/casey/just)
- [asdf](https://asdf-vm.com/) (optional, manages tool versions via `.tool-versions`)

## Installation

```bash
# Clone and install in development mode
git clone https://github.com/mandelbro/autopilot-cli.git
cd autopilot-cli
asdf install && just init
```

## Usage

```bash
# Show help
just run --help

# Show version
just run --version
```

## Development

This project uses [just](https://github.com/casey/just) as a task runner and [uv](https://docs.astral.sh/uv/) for package management.

```bash
# Install dev dependencies
just init              # uv sync --extra dev

# Run all checks (format, lint, typecheck, test)
just

# Individual commands
just test              # uv run pytest
just lint              # uv run ruff check --fix src/ tests/
just format            # uv run ruff format src/ tests/
just typecheck         # uv run pyright
just coverage          # uv run pytest --cov=autopilot --cov-report=term-missing --cov-fail-under=80

# Clean build artifacts
just clean
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

## Troubleshooting

If `just run` fails with `ModuleNotFoundError: No module named 'autopilot'`, rebuild the virtual environment:

```bash
rm -rf .venv && just init
```

## License

MIT
