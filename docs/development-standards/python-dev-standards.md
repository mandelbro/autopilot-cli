# Discovery: Python Application Development Standards (2025 Stack)

## Executive Summary
We standardize on a fast, maintainable Python stack optimized for developer velocity and production reliability:

- uv for dependency and environment management
- Ruff for formatting + linting in one tool
- pytest (+ pytest-asyncio) for tests; coverage baked in
- Pyright for type checking (fast, strict, CI-friendly)
- just for repeatable local/CI tasks
- Multi-stage Docker builds for small, reproducible images
- src/ layout with clear module boundaries and Pydantic Settings for config
- Structured logging, 12-factor config, and simple, enforceable conventions

This replaces fragmented toolchains (pip/poetry + black + isort + flake8) with a leaner, faster setup while raising quality.

## Target Environment
- Python: 3.13.x
- Frameworks commonly used: FastAPI, httpx, Pydantic v2
- Platforms: Local dev, Docker, Render, Supabase-connected services

## Architecture Decisions (Concise ADRs)
1. Dependency Manager: uv
   - Why: 10–100x faster, lockfiles, deterministic, great UX
   - Trade-off: Newer tool; team training required
2. Code Quality: Ruff
   - Why: Single, fast tool for format + lint; fewer moving parts
   - Trade-off: Some flake8 plugins not mirrored; acceptable
3. Types: Pyright
   - Why: Very fast, good error quality, strict modes, great editor support
   - Trade-off: Separate config file (pyrightconfig.json)
4. Tasks: just
   - Why: Developer-friendly, cross-platform, easy onboarding
5. Containers: Multi-stage Docker
   - Why: Smaller images, faster builds, clearer dev/prod boundaries

## Repository Structure Standard
```
repo/
├─ src/
│  └─ <package_name>/
│     ├─ __init__.py
│     ├─ main.py                  # entrypoint (FastAPI or CLI)
│     ├─ api/                     # routers/controllers
│     ├─ core/                    # domain logic
│     ├─ services/                # external integrations (Supabase, Slack, Gmail)
│     ├─ config.py                # Pydantic Settings
│     └─ logging.py               # structured logging setup
├─ tests/                         # mirrors src structure
├─ pyproject.toml
├─ uv.lock                        # committed lockfile
├─ pyrightconfig.json
├─ justfile
├─ Dockerfile
└─ .pre-commit-config.yaml
```

## Configuration Baseline

### pyproject.toml (uv + Ruff + pytest)
```toml
[project]
name = "repengine-service"
version = "0.1.0"
description = "RepEngine Python service standards"
requires-python = ">=3.13"
dependencies = [
  "fastapi>=0.104",
  "uvicorn[standard]>=0.24",
  "pydantic>=2.6",
  "pydantic-settings>=2.2",
  "httpx>=0.27",
  "structlog>=23.2",
]

[tool.uv]
dev-dependencies = [
  "pytest>=8.2",
  "pytest-asyncio>=0.23",
  "pytest-cov>=5.0",
  "ruff>=0.5",
]

[tool.pytest.ini_options]
addopts = "-q --cov=src --cov-report=term-missing"
testpaths = ["tests"]
pythonpath = ["src"]

[tool.ruff]
line-length = 100
target-version = "py313"
fix = true

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "N"]
ignore = ["E501"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
```

### pyrightconfig.json (type checking)
```json
{
  "venvPath": ".venv",
  "typeCheckingMode": "strict",
  "reportMissingTypeStubs": false,
  "reportUnknownVariableType": true,
  "reportUnknownMemberType": true,
  "pythonVersion": "3.13",
  "include": ["src"],
  "exclude": ["**/__pycache__", "**/.venv", "**/build", "**/dist"]
}
```

### justfile (developer workflow)
```just
set dotenv-load := true

default: lint test typecheck

init:
    uv sync --all-extras --dev

run:
    uv run uvicorn src.<package_name>.main:app --reload --host 0.0.0.0 --port 8000

test:
    uv run pytest

coverage:
    uv run pytest --cov=src --cov-report=term-missing

lint:
    uv run ruff check --fix . && uv run ruff format .

typecheck:
    uv run pyright

format:
    uv run ruff format .

clean:
    rm -rf .pytest_cache .ruff_cache .mypy_cache .pytype **/__pycache__

docker-build:
    docker build -t repengine-python:latest .

docker-run:
    docker run --rm -p 8000:8000 repengine-python:latest
```

### Dockerfile (multi-stage, uv-native)
```dockerfile
# syntax=docker/dockerfile:1.7
FROM python:3.13-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1
WORKDIR /app

# Install uv
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/* \
 && curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

FROM base AS deps
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

FROM base AS runtime
COPY --from=deps /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:${PATH}"
COPY src ./src
EXPOSE 8000
CMD ["uvicorn", "src.<package_name>.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### .pre-commit-config.yaml (optional but recommended)
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.5.7
    hooks:
      - id: ruff
        args: ["--fix"]
      - id: ruff-format
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: end-of-file-fixer
      - id: trailing-whitespace
```

## Application Patterns

### Settings (12-factor with Pydantic Settings)
```python
# src/<package_name>/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_", case_sensitive=False)

    environment: str = "development"
    log_level: str = "INFO"
    service_api_key: str
    supabase_url: str
    supabase_service_role_key: str
```

### Logging (structured, consistent)
```python
# src/<package_name>/logging.py
import logging
import structlog


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=level)
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level)),
    )
```

### FastAPI Entry Point
```python
# src/<package_name>/main.py
from fastapi import FastAPI
from .config import AppSettings
from .logging import configure_logging


settings = AppSettings()
configure_logging(settings.log_level)
app = FastAPI(title="RepEngine Service", version="0.1.0")


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "service": "repengine", "env": settings.environment}
```

## Testing Standards
- Tests live in `tests/` mirroring `src/`
- Use `pytest-asyncio` for async tests
- Enforce coverage thresholds in CI with `--cov`

Example async test:
```python
import pytest
from httpx import AsyncClient
from src.<package_name>.main import app


@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        res = await ac.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"
```

## CI/CD Guidance
- Use `just lint`, `just typecheck`, `just test` as CI steps
- Cache uv and Docker layers for speed
- Block merges on type errors, Ruff violations, and <100% coverage for new/changed code paths

## Security & Compliance
- Secrets via environment variables (never in code)
- Service-to-service auth with Bearer keys
- Keep images minimal (no build tools in runtime)
- Optional: `pip-audit` or `uvx pip-audit` in scheduled jobs

## Migration Notes (if coming from pip/poetry)
1) Create `pyproject.toml` as above
2) `uv add <deps>` and `uv add --dev <dev-deps>`
3) Remove legacy config files (setup.cfg, poetry.lock) once parity validated

## Success Criteria
- Cold start dev setup < 2 minutes (`uv sync`)
- Lint + format < 2 seconds on typical change set (Ruff)
- CI end-to-end < 5 minutes with caching
- Docker image < 200MB, deterministic build
