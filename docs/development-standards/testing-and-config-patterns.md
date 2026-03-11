## Testing and Configuration Patterns

### Purpose
Establish consistent patterns for sanitized test environments, CORS origins normalization, and connection checks across services.

### 1) Sanitized Test Environments
- Root `just` targets run tests for each service with a sanitized env using `env -u` to unset service-specific variables (e.g., `SUPABASE_URL`, `SERVICE_API_KEY`, provider keys, `CORS_ALLOWED_ORIGINS`).
- Benefit: Prevents import-time `SettingsError` during pytest collection due to root `.env` values and ensures deterministic defaults.
- Apply to: individual service test targets, `test-all-parallel`, and `all-sequential` workflows.

### 2) CORS Origins Normalization (Shared Helper)
- Prefer the shared helper `repengine_common.settings.normalize_cors_origins`.
- Pattern (Pydantic v2):
  - Define `CORS_ALLOWED_ORIGINS_RAW: str` with `validation_alias=AliasChoices("CORS_ALLOWED_ORIGINS", "CORS_ALLOWED_ORIGINS_RAW")`.
  - Expose `CORS_ALLOWED_ORIGINS: list[str]` as a computed property that calls the helper.
  - Input formats supported: JSON array string (e.g., `"[\"http://a\",\"http://b\"]"`), comma-separated string (e.g., `"http://a,http://b"`), or `list[str]`.
- Backward compatibility: If a service runs against an older installed `repengine_common`, define a tiny local fallback `normalize_cors_origins` delegating to JSON-array parsing first, then comma-separated parsing.

### 3) Connection Checks: Skip When Unconfigured
- Functions like `test_connection()` should return success (True) and log a skip when required env vars aren’t set, rather than failing tests.
- Rationale: Supports local/CI contexts where env may be intentionally empty; avoids brittle test suites.

### 4) Consistency & Consolidation
- New services must adopt these patterns.
- If three variations of the same behavior appear, consolidate into the shared helper (`repengine_common.settings`) or root `just` workflows.

### References
- Shared helper: `render/repengine-common/src/repengine_common/settings.py`
- Examples:
  - `render/messaging-service/render/messaging_service/core/config.py`
  - `render/integrations/src/integrations/core/config.py`
  - `render/webhook-service/ingestion_agent/upsert.py` (skip-when-unconfigured)
