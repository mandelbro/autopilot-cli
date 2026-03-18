set dotenv-load := true

default: format lint typecheck test

# Install all dependencies
init:
    uv sync --extra dev

# Run the autopilot CLI (pass args after --)
run *ARGS:
    uv run autopilot {{ARGS}}

# Run tests
test:
    uv run pytest

# Run tests with coverage
coverage:
    uv run pytest --cov=autopilot --cov-report=term-missing --cov-fail-under=80

# Lint and auto-fix (python -m bypasses asdf shim conflicts)
lint:
    uv run python -m ruff check --fix src/ tests/

# Format code
format:
    uv run python -m ruff format src/ tests/

# Type check
typecheck:
    uv run python -m pyright

# Clean build artifacts
clean:
    rm -rf .pytest_cache .ruff_cache .pyright __pycache__ dist build *.egg-info
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
