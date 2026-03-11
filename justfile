set dotenv-load := true

default: lint typecheck test

# Install all dependencies
init:
    uv sync --extra dev

# Run tests
test:
    uv run pytest

# Run tests with coverage
coverage:
    uv run pytest --cov=autopilot --cov-report=term-missing --cov-fail-under=80

# Lint and auto-fix
lint:
    uv run ruff check --fix src/ tests/

# Format code
format:
    uv run ruff format src/ tests/

# Type check
typecheck:
    uv run pyright

# Clean build artifacts
clean:
    rm -rf .pytest_cache .ruff_cache .pyright __pycache__ dist build *.egg-info
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
