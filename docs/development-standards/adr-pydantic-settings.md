# ADR: Adopt pydantic-settings for Environment Variable Configuration

## Status

**Accepted** — 2026-03-15

## Context

The current configuration system (`src/autopilot/core/config.py`) uses Pydantic `BaseModel` with a three-level YAML merge (global → project → CLI). Environment variable names are referenced in config fields (e.g., `RenderServiceConfig.api_key_env = "RENDER_API_KEY"`) but their values are never read from the environment. This creates a gap:

- Secrets must be hardcoded in YAML files or passed through other mechanisms
- Deployment configuration cannot be overridden per-environment without editing YAML
- The project does not follow 12-factor app principles for configuration
- `python-dev-standards.md` recommends Pydantic Settings for secret management

### Current State

- `ClaudeConfig` has fields (`extra_flags`, `mcp_config`, `claude_flow_version`) that may benefit from env var override
- `RenderServiceConfig.api_key_env` stores the env var *name* ("RENDER_API_KEY") but never reads its value
- All config models use `frozen=True` which is compatible with `BaseSettings`

## Decision Drivers

1. **12-factor compliance**: Secrets and deployment config should come from environment
2. **Secret management**: API keys should never live in committed YAML files
3. **Deployment flexibility**: Different environments need different config without file changes
4. **Backward compatibility**: Existing YAML-based config must continue to work

## Options Considered

### Option A: Add pydantic-settings with BaseSettings for secret-bearing models only (Recommended)

Create a `SecretSettings` class using `BaseSettings` for fields that should read from environment variables. Keep all other config models as `BaseModel` with YAML loading.

**Pros:**
- Minimal change surface — only secret-bearing fields are affected
- YAML config continues to work unchanged
- Environment variables override YAML values (standard pydantic-settings precedence)
- `.env` file support out of the box
- Aligns with `python-dev-standards.md` pattern

**Cons:**
- Adds one new dependency (`pydantic-settings>=2.2`)
- Two config loading mechanisms (YAML + env) may confuse contributors initially

### Option B: Convert all config models to BaseSettings with env prefix

Replace all `BaseModel` config classes with `BaseSettings`, giving every field an environment variable binding.

**Pros:**
- Fully 12-factor compliant
- Every config field overridable via env

**Cons:**
- Massive env var namespace (`AUTOPILOT_SCHEDULER_INTERVAL_SECONDS`, etc.)
- YAML files become redundant for most settings
- Breaking change for existing config workflows
- Over-engineering for non-secret fields that are fine in YAML

### Option C: Keep current approach; read env vars manually

Add `os.environ.get()` calls wherever env vars are needed.

**Pros:**
- No new dependency
- Simple to understand

**Cons:**
- No validation or type coercion
- No `.env` file support
- Manual boilerplate for each env var
- Does not align with `python-dev-standards.md`

## Decision

**Option A** — Add `pydantic-settings` with `BaseSettings` for secret-bearing config fields only.

### Implementation

1. Add `pydantic-settings>=2.2` to dependencies
2. Create `SecretSettings(BaseSettings)` class with:
   - `render_api_key: str = ""` (reads from `RENDER_API_KEY` env var)
   - `model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)`
3. Integrate into `AutopilotConfig` as a `secrets: SecretSettings` field
4. Update `RenderServiceConfig` to reference the actual secret value instead of the env var name
5. Maintain backward compatibility: YAML config still works, env vars take precedence

## Consequences

### Positive

- Secrets no longer need to be in YAML files
- `.env` file support for local development
- Environment variable overrides work automatically
- Aligns with established `python-dev-standards.md` patterns
- Type-safe env var parsing with validation

### Negative

- One additional dependency (`pydantic-settings`)
- Slight increase in config complexity (two loading mechanisms)
- Contributors need to understand which fields are env-var-backed
