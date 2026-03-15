"""Environment-variable-backed secret configuration using pydantic-settings.

Provides a ``SecretSettings`` class for fields that should be loaded from
environment variables (API keys, tokens, secrets). YAML config continues
to work for non-secret fields; env vars take precedence.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class SecretSettings(BaseSettings):
    """Secret configuration loaded from environment variables.

    Fields read from env vars automatically. A ``.env`` file in the
    project root is also supported for local development.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        frozen=True,
    )

    render_api_key: str = ""
