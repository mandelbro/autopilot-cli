## Summary (tasks-10.md)

- **Tasks in this file**: 4
- **Task IDs**: 091 - 094
- **Total Points**: 11

### Dev Standards Compliance: Logging, Strict Types, Pre-commit, Config

---

## Tasks

### Task ID: 091

- **Title**: Structured logging module with structlog
- **File**: src/autopilot/logging.py, src/autopilot/cli/app.py
- **Complete**: [ ]
- **Sprint Points**: 2

- **User Story (business-facing)**: As a system operator, I want structured JSON logging throughout the CLI, so that log output is machine-parsable, consistently formatted, and filterable by log level in production.
- **Outcome (what this delivers)**: A `configure_logging()` function using structlog that is called at CLI startup, replacing any ad-hoc print/logging calls with structured, leveled, timestamped JSON output per `python-dev-standards.md`.

#### Prompt:

```markdown
**Objective:** Create the structured logging module using the structlog dependency (already installed but unused) and wire it into the CLI entry point.

**Files to Create/Modify:**
- `src/autopilot/logging.py` (create)
- `src/autopilot/cli/app.py` (modify -- add `configure_logging()` call)
- `tests/test_logging.py` (create)

**Specification References:**
- `docs/development-standards/python-dev-standards.md`: Logging (structured, consistent) section
- `docs/development-standards/python-dev-standards.md`: Repository Structure Standard (`logging.py` placement)

**Prerequisite Requirements:**
1. Review `docs/development-standards/python-dev-standards.md` for the exact `configure_logging()` pattern
2. Review `src/autopilot/cli/app.py` to understand the current CLI entry point structure
3. Write tests first in `tests/test_logging.py`
4. Use context7 for structlog v24+ best practices if needed

**Detailed Instructions:**
1. Create `src/autopilot/logging.py` with:
   - `configure_logging(level: str = "INFO") -> None` function
   - Uses `structlog.configure()` with processors: `TimeStamper(fmt="iso")`, `add_log_level`, `JSONRenderer()`
   - Sets `wrapper_class` to `structlog.make_filtering_bound_logger(logging.getLevelName(level))`
   - Calls `logging.basicConfig(level=level)` for stdlib compatibility
2. Modify `src/autopilot/cli/app.py`:
   - Import `configure_logging` from `autopilot.logging`
   - Call `configure_logging()` in the Typer app callback (or at module level if no callback exists)
   - Add `--log-level` option (default "INFO") to control verbosity
3. Write tests in `tests/test_logging.py`:
   - Test that `configure_logging()` calls `structlog.configure` with expected processors
   - Test that different log levels are respected
   - Test that output is valid JSON when rendered

**Acceptance Criteria:**
- [ ] `src/autopilot/logging.py` exists with `configure_logging()` function
- [ ] structlog is configured with ISO timestamps, log level, and JSON rendering
- [ ] CLI entry point calls `configure_logging()` at startup
- [ ] `--log-level` flag controls verbosity
- [ ] All tests in `tests/test_logging.py` pass
- [ ] `uv run ruff check src/autopilot/logging.py` passes
- [ ] `uv run pyright src/autopilot/logging.py` passes
```

---

### Task ID: 092

- **Title**: Upgrade Pyright to strict mode and fix type errors
- **File**: pyproject.toml, src/autopilot/**/*.py
- **Complete**: [ ]
- **Sprint Points**: 5

- **User Story (business-facing)**: As a developer, I want strict type checking enforced across the codebase, so that type-related bugs are caught at development time and the codebase maintains a high standard of type safety per `python-dev-standards.md`.
- **Outcome (what this delivers)**: Pyright running in strict mode with zero errors, catching implicit `Any` types, missing return annotations, and unsafe None access across all source files.

#### Prompt:

```markdown
**Objective:** Change Pyright from `standard` to `strict` type checking mode and resolve all resulting type errors across the codebase.

**Files to Create/Modify:**
- `pyproject.toml` (modify `typeCheckingMode`)
- All files under `src/autopilot/` that produce type errors under strict mode

**Specification References:**
- `docs/development-standards/python-dev-standards.md`: Pyright strict mode configuration
- Current `pyproject.toml` line 59: `typeCheckingMode = "standard"` (must become `"strict"`)

**Prerequisite Requirements:**
1. Run `uv run pyright src/` with current `standard` mode to establish baseline (should be zero errors)
2. Change `typeCheckingMode` to `"strict"` in `pyproject.toml`
3. Run `uv run pyright src/` again to identify all new errors
4. Catalog the errors before making fixes

**Detailed Instructions:**
1. In `pyproject.toml`, change line 59 from `typeCheckingMode = "standard"` to `typeCheckingMode = "strict"`
2. Run `uv run pyright src/` and capture the full error list
3. Fix each error category systematically:
   - **Missing return type annotations**: Add explicit return types to all functions
   - **Implicit Any**: Add explicit type annotations where types are inferred as `Any`
   - **Missing parameter types**: Ensure all function parameters have type annotations
   - **Unsafe None access**: Add proper None checks or use `assert` guards
   - **Import-related type issues**: Add `type: ignore` comments ONLY as last resort with justification
4. After fixing, verify:
   - `uv run pyright src/` reports zero errors
   - `uv run ruff check src/` still passes
   - `uv run pytest` still passes (no behavior changes)
5. Do NOT add `# type: ignore` unless absolutely necessary (e.g., third-party library stubs missing). If used, add a comment explaining why.

**Acceptance Criteria:**
- [ ] `pyproject.toml` has `typeCheckingMode = "strict"`
- [ ] `uv run pyright src/` reports zero errors in strict mode
- [ ] No `# type: ignore` comments without justification
- [ ] All existing tests continue to pass
- [ ] `uv run ruff check src/` passes
- [ ] No behavioral changes to any module (type-only fixes)
```

---

### Task ID: 093

- **Title**: Add pre-commit hooks configuration
- **File**: .pre-commit-config.yaml
- **Complete**: [ ]
- **Sprint Points**: 1

- **User Story (business-facing)**: As a developer, I want pre-commit hooks for formatting and linting, so that code quality checks run automatically before every commit and prevent non-compliant code from entering the repository.
- **Outcome (what this delivers)**: A `.pre-commit-config.yaml` with ruff check, ruff format, and basic file hygiene hooks that run on every `git commit`.

#### Prompt:

```markdown
**Objective:** Create `.pre-commit-config.yaml` with ruff and file hygiene hooks per `python-dev-standards.md`.

**Files to Create/Modify:**
- `.pre-commit-config.yaml` (create)

**Specification References:**
- `docs/development-standards/python-dev-standards.md`: `.pre-commit-config.yaml` section
- Current ruff version in `pyproject.toml`: `ruff>=0.9`

**Prerequisite Requirements:**
1. Review `docs/development-standards/python-dev-standards.md` for the exact pre-commit config template
2. Check the latest stable ruff-pre-commit hook version via context7 or web search
3. Verify `pre-commit` is available or add it to dev dependencies

**Detailed Instructions:**
1. Create `.pre-commit-config.yaml` at project root with:
   ```yaml
   repos:
     - repo: https://github.com/astral-sh/ruff-pre-commit
       rev: v0.9.10  # Pin to version compatible with ruff>=0.9 in pyproject.toml
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
2. Add `pre-commit>=3.0` to the `[project.optional-dependencies] dev` list in `pyproject.toml`
3. Verify the hooks work by running:
   - `uv run pre-commit install`
   - `uv run pre-commit run --all-files`
4. Fix any issues surfaced by the hooks (trailing whitespace, missing EOF newlines)

**Acceptance Criteria:**
- [ ] `.pre-commit-config.yaml` exists at project root
- [ ] Ruff check and ruff format hooks are configured
- [ ] File hygiene hooks (end-of-file-fixer, trailing-whitespace) are configured
- [ ] `pre-commit` is listed in dev dependencies
- [ ] `uv run pre-commit run --all-files` passes with no errors
```

---

### Task ID: 094

- **Title**: Evaluate pydantic-settings for environment variable config
- **File**: docs/development-standards/adr-pydantic-settings.md, src/autopilot/core/config.py
- **Complete**: [ ]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a system operator, I want API keys and secrets loaded from environment variables automatically, so that I do not need to hardcode sensitive values in YAML config files and the tool follows 12-factor app principles.
- **Outcome (what this delivers)**: An ADR documenting whether `pydantic-settings` should be adopted, and if approved, implementation of `BaseSettings` for config models that reference environment variables (`ClaudeConfig`, `RenderServiceConfig`), with `.env` file support.

#### Prompt:

```markdown
**Objective:** Evaluate whether `pydantic-settings` (`BaseSettings`) should replace or augment the current Pydantic `BaseModel` config for environment-variable-backed settings, and implement if the evaluation is favorable.

**Files to Create/Modify:**
- `docs/development-standards/adr-pydantic-settings.md` (create -- evaluation document)
- `src/autopilot/core/config.py` (modify if adopting)
- `tests/core/test_config.py` (modify if adopting)

**Specification References:**
- `docs/development-standards/python-dev-standards.md`: Settings (12-factor with Pydantic Settings) section
- Current `src/autopilot/core/config.py`: `ClaudeConfig` and `RenderServiceConfig` reference env var names but do not read them
- `ClaudeConfig.extra_flags`, `ClaudeConfig.mcp_config`, `ClaudeConfig.claude_flow_version` -- may benefit from env overlay
- `RenderServiceConfig.api_key_env` -- stores the env var NAME ("RENDER_API_KEY") but never reads its value

**Prerequisite Requirements:**
1. Read `src/autopilot/core/config.py` to understand current config architecture
2. Use context7 for pydantic-settings v2 best practices and `BaseSettings` patterns
3. Identify all config fields that should be overridable via environment variables
4. Write the evaluation ADR before implementing any code changes

**Detailed Instructions:**

**Phase 1: Evaluation (required)**
1. Write `docs/development-standards/adr-pydantic-settings.md` covering:
   - **Context**: Current config loads from YAML only; env var names are referenced but not read
   - **Decision drivers**: 12-factor compliance, secret management, deployment flexibility
   - **Options considered**:
     a. Add `pydantic-settings` with `BaseSettings` for secret-bearing models only
     b. Convert all config models to `BaseSettings` with env prefix
     c. Keep current approach; read env vars manually where needed
   - **Recommendation** with rationale
   - **Consequences** (positive and negative)

**Phase 2: Implementation (if evaluation recommends adoption)**
2. Add `pydantic-settings>=2.2` to dependencies in `pyproject.toml`
3. Create a `SecretConfig` or similar `BaseSettings` subclass for fields that should read from env vars:
   - `RENDER_API_KEY` (currently referenced by name only)
   - Any Claude API configuration that may need env var override
4. Maintain backward compatibility: YAML config still works, env vars override YAML values
5. Update tests to verify env var override behavior using `monkeypatch`
6. Do NOT convert all config models -- only those with secret/deployment-sensitive fields

**Acceptance Criteria:**
- [ ] ADR document exists at `docs/development-standards/adr-pydantic-settings.md`
- [ ] ADR includes clear recommendation with tradeoffs
- [ ] If adopting: `pydantic-settings` added to dependencies
- [ ] If adopting: Secret-bearing config fields read from environment variables
- [ ] If adopting: YAML config continues to work (backward compatible)
- [ ] If adopting: Tests verify env var override behavior
- [ ] `uv run pyright src/` passes
- [ ] `uv run ruff check src/` passes
```
